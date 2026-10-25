"""Policy plugins: city levers the engine loads at runtime (the Droid policy compiler writes new ones).

A policy is a module in `hp/policies/generated/` with

    KIND = "through_charge"              # unique, [a-z0-9_]
    TITLE = "Through-traffic charge"     # shown in the UI
    DESCRIPTION = "..."
    PARAMS = {"amount": {"default": 5.0, "min": 0, "max": 50, "unit": "USD"}}

and either `apply(ctx_view, params) -> dict` or any of the hooks below. Each hook returns a numpy array:

    car_cost_usd(agents, params)       -> float[agents.n]  extra $ per one-way car trip (enters mode choice,
                                                           the through-traffic stay/bypass choice, and city revenue)
    edge_cost_factor(edges, params)    -> float[edges.n]   multiplier on car travel time per edge (1 = unchanged)
    poi_attractiveness(pois, params)   -> float[pois.n]    multiplier on destination attractiveness (1 = unchanged)

`apply` returns the same arrays keyed by hook name (any subset). Views are read-only, the code must be pure
numpy (no I/O, no network, no randomness) so the same edits always give the same metrics.

Built-in kinds (`congestion_charge`, `parking_price`) stay in the engine. Only modules listed in
`generated/approved.json` (written by POST /policies/{id}/approve) are registered."""
import importlib.util
import json
import re
import threading
from pathlib import Path

import numpy as np

BUILTIN_KINDS = ("congestion_charge", "parking_price")
HOOKS = ("car_cost_usd", "edge_cost_factor", "poi_attractiveness")
GENERATED = Path(__file__).parent / "generated"
APPROVED = GENERATED / "approved.json"
KIND_RE = re.compile(r"^[a-z][a-z0-9_]{1,40}$")

_lock = threading.Lock()
_registry = {}  # kind -> module


def _ro(a, dtype=None):
    a = np.array(a, dtype=dtype)
    a.setflags(write=False)
    return a


class Agents:
    """One row per agent. Kinds: worker (commuter into the area), resident, visitor, through (car trip
    crossing the area between two car inlets)."""

    def __init__(self, ctx):
        from ..population import KIND_NAMES, REGIONS, THROUGH
        pop, w = ctx.pop, ctx.e.w
        self.n = int(pop.n)
        self.id = _ro(pop.id)
        self.kind = _ro([KIND_NAMES[k] for k in pop.kind])          # "worker" | "resident" | "visitor" | "through"
        self.is_worker, self.is_resident, self.is_visitor, self.is_through = (_ro(self.kind == k) for k in KIND_NAMES)
        self.arrive_h = _ro(pop.arrive / 3600.0)                     # hour of day entering (through: crossing time)
        self.leave_h = _ro(pop.leave / 3600.0)
        self.income_tier = _ro(np.array(["low", "mid", "high"])[pop.tier])
        self.has_car = _ro(pop.car, bool)
        self.home_region = _ro([REGIONS[r]["key"] for r in pop.region])
        keys = [g["key"] for g in w.inlets]
        thr = pop.kind == THROUGH
        self.car_inlet = _ro([keys[i] for i in ctx.car_in])          # inlet a commuter's car enters by
        self.through_from = _ro(np.where(thr, [keys[i] if i >= 0 else "" for i in pop.in_inlet], ""))
        self.through_to = _ro(np.where(thr, [keys[i] if i >= 0 else "" for i in pop.out_inlet], ""))
        # Through trips run side to side and pick their actual inlets by route cost; these are the sides.
        sides = [g.get("side") or "" for g in w.inlets]
        self.through_from_side = _ro(np.where(thr, [sides[i] if i >= 0 else "" for i in pop.in_inlet], ""))
        self.through_to_side = _ro(np.where(thr, [sides[i] if i >= 0 else "" for i in pop.out_inlet], ""))
        self.building = _ro(pop.bld)


class Edges:
    """One row per street edge (ids match the frontend's world.json)."""

    def __init__(self, w, closed):
        self._w = w
        self.n = int(w.E)
        self.name = _ro(w.edge_name)
        self.road_class = _ro(w.edge_cls)
        self.lanes = _ro(w.edge_lanes)
        self.length_m = _ro(w.edge_len)
        self.mid_xz = _ro(w.edge_mid)
        self.is_car = _ro(w.edge_car, bool)
        self.is_freeway = _ro(w.edge_hw, bool)
        cf = np.zeros(self.n, bool)
        cf[list(closed)] = True
        self.car_free = _ro(cf)

    def named(self, street):
        """Boolean mask of edges called `street` (e.g. "Howard Street")."""
        return self.name == street

    def stretch(self, street, from_cross, to_cross):
        """Boolean mask of `street` between its crossings with two cross streets."""
        m = np.zeros(self.n, bool)
        m[self._w.stretch(street, from_cross, to_cross)] = True
        return m


class Pois:
    """One row per destination (shops, cafés, restaurants, bars; includes shops created by rezoning)."""

    def __init__(self, PO, edges_n):
        self.n = int(PO.n)
        self.category = _ro(PO.cat)
        self.xz = _ro(PO.xy, float)
        self.quality = _ro(PO.q, float)
        self.name = _ro(PO.names)
        self._edges = PO.edges
        self._E = edges_n

    def fronting(self, edge_mask):
        """Boolean mask of POIs that front any edge in `edge_mask`."""
        em = np.asarray(edge_mask, bool)
        return np.array([bool(e) and bool(em[list(e)].any()) for e in self._edges])


class CtxView:
    def __init__(self, ctx):
        w = ctx.e.w
        self.agents = Agents(ctx)
        self.edges = Edges(w, ctx.closed)
        self.pois = Pois(ctx.PO, w.E)
        self.inlets = [{"key": g["key"], "name": g["name"], "mode": g["mode"], "side": g.get("side"), "cls": g.get("cls")} for g in w.inlets]
        self.params = dict(ctx.e.P.values)


class Effects:
    """Summed effects of all plugin policies in one scenario (identity when there are none)."""

    def __init__(self, n, E, npoi):
        self.car_cost_usd = np.zeros(n)
        self.edge_cost_factor = np.ones(E)
        self.poi_attractiveness = np.ones(npoi)
        self.active = []


def default_apply(mod, view, params):
    out = {}
    if hasattr(mod, "car_cost_usd"):
        out["car_cost_usd"] = mod.car_cost_usd(view.agents, params)
    if hasattr(mod, "edge_cost_factor"):
        out["edge_cost_factor"] = mod.edge_cost_factor(view.edges, params)
    if hasattr(mod, "poi_attractiveness"):
        out["poi_attractiveness"] = mod.poi_attractiveness(view.pois, params)
    return out


def resolve_params(mod, given):
    """Defaults from PARAMS, numbers clipped to [min, max]; unknown keys dropped."""
    spec = getattr(mod, "PARAMS", {}) or {}
    out = {}
    for k, s in spec.items():
        v = (given or {}).get(k, s.get("default"))
        if isinstance(s.get("default"), (int, float)) and not isinstance(s.get("default"), bool):
            v = float(v)
            if "min" in s:
                v = max(v, float(s["min"]))
            if "max" in s:
                v = min(v, float(s["max"]))
        out[k] = v
    return out


def run_module(mod, view, params):
    """Call a policy module and validate its arrays (shape, finite, sane range)."""
    fn = getattr(mod, "apply", None)
    raw = fn(view, params) if fn else default_apply(mod, view, params)
    sizes = {"car_cost_usd": view.agents.n, "edge_cost_factor": view.edges.n, "poi_attractiveness": view.pois.n}
    out = {}
    for k, v in (raw or {}).items():
        if k not in HOOKS:
            raise ValueError(f"{getattr(mod, 'KIND', mod)}: unknown hook {k!r}")
        a = np.asarray(v, float)
        if a.ndim == 0:
            a = np.full(sizes[k], float(a))
        if a.shape != (sizes[k],):
            raise ValueError(f"{mod.KIND}.{k}: shape {a.shape}, expected ({sizes[k]},)")
        if not np.isfinite(a).all():
            raise ValueError(f"{mod.KIND}.{k}: non-finite values")
        if k == "car_cost_usd" and not ((a >= -100) & (a <= 500)).all():
            raise ValueError(f"{mod.KIND}.car_cost_usd outside [-100, 500] $")
        if k != "car_cost_usd" and not ((a >= 0.05) & (a <= 20)).all():
            raise ValueError(f"{mod.KIND}.{k} outside [0.05, 20]")
        out[k] = a
    return out


def effects(ctx):
    """Called by the engine's Ctx: evaluate every plugin policy in the scenario's edits."""
    pols = [p for p in ctx.edits.get("policies", []) if p["kind"] not in BUILTIN_KINDS]
    fx = Effects(ctx.n, ctx.e.w.E, ctx.PO.n)
    if not pols:
        return fx
    view = CtxView(ctx)
    for p in pols:
        mod = get(p["kind"])
        if mod is None:
            raise KeyError(f"policy kind {p['kind']!r} is not registered")
        out = run_module(mod, view, resolve_params(mod, policy_params(p)))
        fx.car_cost_usd = fx.car_cost_usd + out.get("car_cost_usd", 0.0)
        fx.edge_cost_factor = fx.edge_cost_factor * out.get("edge_cost_factor", 1.0)
        fx.poi_attractiveness = fx.poi_attractiveness * out.get("poi_attractiveness", 1.0)
        fx.active.append(p["kind"])
    return fx


def policy_params(p):
    """A policy edit's params: `params` dict plus the shared `target`/`amount` fields."""
    out = dict(p.get("params") or {})
    if p.get("amount") is not None and "amount" not in out:
        out["amount"] = p["amount"]
    if p.get("target") and "target" not in out:
        out["target"] = p["target"]
    return out


# ── registry ──
def load_file(path, name=None):
    """Import a policy module from a file (fresh each time, so re-approval hot-reloads)."""
    path = Path(path)
    name = name or f"hp.policies.generated.{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    kind = getattr(mod, "KIND", None)
    if not (isinstance(kind, str) and KIND_RE.match(kind)) or kind in BUILTIN_KINDS:
        raise ValueError(f"{path.name}: KIND must match {KIND_RE.pattern} and not be a built-in")
    if not (hasattr(mod, "apply") or any(hasattr(mod, h) for h in HOOKS)):
        raise ValueError(f"{path.name}: defines neither apply() nor a hook")
    return mod


def approved():
    try:
        data = json.loads(APPROVED.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def register(mod):
    with _lock:
        _registry[mod.KIND] = mod


def load_approved():
    """(Re)load every approved module. Returns {kind: error} for modules that failed to load."""
    errs = {}
    for kind, meta in approved().items():
        try:
            mod = load_file(GENERATED / meta["file"])
            if mod.KIND != kind:
                raise ValueError(f"KIND {mod.KIND!r} != approved {kind!r}")
            register(mod)
        except Exception as e:  # keep the engine up; surfaced on GET /policies
            errs[kind] = repr(e)
    return errs


def get(kind):
    with _lock:
        return _registry.get(kind)


def kinds():
    with _lock:
        return sorted(_registry)


def catalog():
    """Registered plugin policies for the UI / planner."""
    with _lock:
        mods = dict(_registry)
    return [{"kind": k, "title": getattr(m, "TITLE", k), "description": getattr(m, "DESCRIPTION", ""),
             "params": getattr(m, "PARAMS", {}), "file": Path(m.__file__).name} for k, m in sorted(mods.items())]


LOAD_ERRORS = load_approved()
