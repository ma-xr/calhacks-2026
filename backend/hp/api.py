"""HTTP API (FastAPI) on :8787. Contract: docs/contracts/sim-api.md."""
import json
import queue
import threading
import time
from collections import OrderedDict

import numpy as np
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from . import policies as PL
from . import results as R
from .engine import CAR, Engine, edits_key
from .inputs import Inputs
from .params import Params
from .population import REGIONS, WORKER, agent_name
from .world import World

app = FastAPI(title="The Human Project — sim API", version="0.2")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(GZipMiddleware, minimum_size=2000)


class State:
    def __init__(self):
        self.ready = False
        self.lock = threading.Lock()
        self.scen = OrderedDict()  # id -> raw engine result
        self.json_cache = {}       # (id, lite) -> dict
        self.hero = None
        self.error = None

    def boot(self):
        t = time.time()
        self.world = World()
        self.P = Params()
        self.I = Inputs()
        self.eng = Engine(self.world, self.P, self.I)
        self.eng.calibrate()
        self.base = self.eng.baseline
        self.scen["baseline"] = self.base
        self._pick_hero()
        self.ready = True
        self.boot_s = round(time.time() - t, 1)

    def _pick_hero(self):
        """Maria: an East Bay driver whose office is near 2nd St and who switches to BART when 2nd St goes car-free.
        Dev: a coworker in the same building who also goes out for lunch."""
        w, eng = self.world, self.eng
        hero_edges = w.stretch("2nd Street", "Market Street", "Folsom Street")
        plan = eng.evaluate({"pedestrianized": hero_edges})
        plan["name"] = "2nd St car-free"
        self.scen[plan["id"]] = plan
        bs, ps = self.base["_state"], plan["_state"]
        pop_b, pop_p = bs["pop"], ps["pop"]
        mid = w.edge_mid[hero_edges[len(hero_edges) // 2]] if hero_edges else np.zeros(2)
        rowp = {int(i): k for k, i in enumerate(pop_p.id)}
        best, bd = None, 1e18
        for k in np.where((pop_b.kind == WORKER) & pop_b.lunch & (bs["mode"] == CAR))[0]:
            aid = int(pop_b.id[k])
            j = rowp.get(aid)
            if j is None or REGIONS[pop_b.region[k]]["key"] != "east_bay":
                continue
            switched = ps["mode"][j] != CAR or ps["gone"][j]
            d = float(np.hypot(*(w.bld_c[pop_b.bld[k]] - mid))) - (600 if switched else 0)
            if d < bd:
                bd, best = d, k
        if best is None:
            best = int(np.where(pop_b.kind == WORKER)[0][0])
        maria = int(pop_b.id[best])
        from .population import NAME_OVERRIDES
        same = np.where((pop_b.kind == WORKER) & (pop_b.bld == pop_b.bld[best]) & pop_b.lunch & (pop_b.id != maria))[0]
        dev = int(pop_b.id[same[0]]) if len(same) else int(pop_b.id[(best + 1) % pop_b.n])
        NAME_OVERRIDES.update({maria: "Maria O.", dev: "Dev P."})
        # Scripted demo pair (documented): Dev keeps Maria's lunch habits, so they share a lunch spot and time.
        pop = eng.pb.base
        im, idv = int(np.where(pop.id == maria)[0][0]), int(np.where(pop.id == dev)[0][0])
        pop.lunch[[im, idv]] = True
        pop.lunch_t[im], pop.lunch_t[idv] = 735 * 60, 738 * 60
        pop.lunch_dur[[im, idv]] = 35 * 60
        pop.open[[im, idv]] = 0.9
        eng.noise_alias = {dev: maria}
        self.base = eng.baseline = eng.evaluate({})
        self.scen.clear(); self.scen["baseline"] = self.base
        plan = eng.evaluate({"pedestrianized": hero_edges}); plan["name"] = "2nd St car-free"
        self.scen[plan["id"]] = plan
        self.hero = {"agent_id": maria, "name": agent_name(maria), "friend_id": dev, "friend_name": agent_name(dev),
                     "street": "2nd Street", "street_edges": hero_edges, "plan_id": plan["id"]}

    def result_json(self, sid, lite, max_trips=4000):
        max_trips = int(min(max(max_trips, 0), MAX_TRIPS_CAP))
        k = (sid, lite, max_trips)
        if k not in self.json_cache:
            res = self.scen[sid]
            must = (self.hero["agent_id"], self.hero["friend_id"]) if self.hero else ()
            self.json_cache[k] = R.to_json(self.eng, res, self.base, lite=lite, sample_must=must, max_trips=max_trips)
            if len(self.json_cache) > 40:
                self.json_cache.pop(next(iter(self.json_cache)))
        return self.json_cache[k]

    def run(self, edits, name=None, progress=None):
        norm, key = edits_key(edits)
        sid = "baseline" if not (norm["pedestrianized"] or norm["blocks"] or norm["policies"] or norm["reopened"]) else key
        if sid in self.scen:
            self.scen.move_to_end(sid)
            res = self.scen[sid]
            res["cached"] = True
            return sid
        with self.lock:
            res = self.eng.evaluate(edits, progress=progress)
        res["name"] = name
        res["cached"] = False
        self.scen[sid] = res
        while len(self.scen) > 14:
            k = next(iter(self.scen))
            if k in ("baseline", self.hero["plan_id"]):
                self.scen.move_to_end(k)
                continue
            self.scen.pop(k)
            for ck in [c for c in self.json_cache if c[0] == k]:
                self.json_cache.pop(ck, None)
        return sid


MAX_TRIPS_CAP = 100000  # more than every trip of the day; the sample share reaches 1.0 before this
S = State()


@app.on_event("startup")
def _startup():
    def boot():
        try:
            S.boot()
        except Exception as e:  # surfaced on /health
            S.error = repr(e)
            raise
    threading.Thread(target=boot, daemon=True).start()


def _need_ready():
    if not S.ready:
        raise HTTPException(503, detail={"error": "warming up", "detail": S.error})


@app.get("/health")
def health():
    return {"ok": S.error is None, "baseline_ready": S.ready, "version": app.version, "error": S.error,
            "boot_s": getattr(S, "boot_s", None), "data": S.I.status() if S.ready else None}


@app.get("/world")
def world():
    _need_ready()
    w, P, eng = S.world, S.P, S.eng
    pois = []
    for p in w.pois:
        g = eng.poi_google.get(p["id"], {})
        pois.append({**p, "rating": g.get("rating"), "reviews": g.get("reviews"), "price_level": g.get("price_level"),
                     "has_popular_times": bool(g.get("popular_times")), "quality": round(float(eng.poi_q[p["id"]]), 3),
                     "building": int(eng.poi_bld[p["id"]])})
    rs = eng.pb.region_share
    return R._round({
        "scale": eng.scale,
        # Variable-length list: 3 rail inlets plus every car inlet generated from the roads crossing the map edge.
        "inlets": [{**{k: g[k] for k in ("i", "key", "name", "mode", "x", "z")}, "side": g.get("side"), "legacy": g.get("legacy", False),
                    **({"cls": g["cls"], "lanes": g["lanes"], "at": g["at"], "has_entry": bool(g["entries"]), "has_exit": bool(g["exits"]),
                        "edges": g.get("edges", [])} if g["mode"] == "car" else {})} for g in w.inlets],
        "regions": [{"key": r["key"], "name": r["name"], "share": rs.get(r["key"], 0), "car_inlet": w.inlet_by_key[r["car"]]["i"],
                     "car_inlets": {w.inlets[i]["key"]: round(off / 60, 1) for i, off in sorted(eng.region_access[k].items(), key=lambda kv: kv[1])},
                     "bart_inlet": w.inlet_by_key[r["bart"]]["i"], "minutes_outside_by_car": r["car_min"], "minutes_outside_by_transit": r["tr_min"]} for k, r in enumerate(REGIONS)],
        "pois": pois,
        "block_of": w.block_of.tolist(), "n_blocks": w.n_blocks,
        "editable_edges": [e for e in w.editable_edges if e not in set(eng.base_closed)],
        "base_car_free_edges": eng.base_closed,
        "zones": ["res", "office", "retail", "mixed"],
        "population": {"present_workers": eng.pb.present_workers, "residents": eng.pb.residents, "agents": int(eng.pb.base.n)},
        "calibration": getattr(eng, "calibration", None),
        "params": P.meta,
        "hero": S.hero,
        "data": S.I.status(),
    })


@app.get("/baseline")
def baseline(lite: bool = Query(False), max_trips: int = Query(4000)):
    _need_ready()
    return JSONResponse(S.result_json("baseline", lite, max_trips))


@app.get("/scenario/{sid}")
def get_scenario(sid: str, lite: bool = Query(False), max_trips: int = Query(4000)):
    _need_ready()
    if sid not in S.scen:
        raise HTTPException(404, "unknown scenario (it may have been evicted; POST the edits again)")
    return JSONResponse(S.result_json(sid, lite, max_trips))


def _clean_edits(body):
    edits = body.get("edits", body) or {}
    w = S.world
    ped = [int(e) for e in edits.get("pedestrianized", []) if 0 <= int(e) < w.E]
    reo = [int(e) for e in edits.get("reopened", []) if 0 <= int(e) < w.E]
    blocks = {}
    for k, v in (edits.get("blocks") or {}).items():
        b = int(k)
        if not (0 <= b < w.B):
            continue
        sc = float(v.get("scale", 1.0))
        z = v.get("zone") or ""
        if not (0.25 <= sc <= 4.0):
            raise HTTPException(400, f"block {b}: scale must be 0.25–4")
        if z and z not in ("res", "office", "retail", "mixed"):
            raise HTTPException(400, f"block {b}: unknown zone {z}")
        blocks[str(b)] = {"scale": sc, "zone": z}
    pols = []
    for p in edits.get("policies", []) or []:
        if p.get("kind") not in PL.BUILTIN_KINDS and p.get("kind") not in PL.kinds():
            raise HTTPException(400, f"unknown policy kind {p.get('kind')}")
        tgt = p.get("target") or ""
        if p["kind"] == "congestion_charge" and tgt and (tgt not in w.inlet_by_key or w.inlet_by_key[tgt]["mode"] != "car"):
            raise HTTPException(400, f"unknown car inlet {tgt!r}; see GET /world → inlets")
        pol = {"kind": p["kind"], "target": tgt, "amount": float(p.get("amount", 0))}
        if p["kind"] not in PL.BUILTIN_KINDS and isinstance(p.get("params"), dict):  # plugin params, clipped to its PARAMS
            pol["params"] = PL.resolve_params(PL.get(p["kind"]), PL.policy_params(p))
        pols.append(pol)
    return {"pedestrianized": ped, "reopened": reo, "blocks": blocks, "policies": pols}


@app.post("/scenario")
def post_scenario(body: dict = Body(...), stream: bool = Query(False), lite: bool = Query(False), max_trips: int = Query(4000)):
    _need_ready()
    edits = _clean_edits(body)
    name = body.get("name")
    if not stream:
        sid = S.run(edits, name)
        return JSONResponse(S.result_json(sid, lite, max_trips))
    q = queue.Queue()

    def work():
        try:
            sid = S.run(edits, name, progress=lambda k, n, gap=None: q.put(("progress", {"day": k, "days": n, "gap": gap, "label": f"Replanning day {k}/{n}"})))
            q.put(("result", S.result_json(sid, lite, max_trips)))
        except Exception as e:
            q.put(("error", {"error": repr(e)}))
    threading.Thread(target=work, daemon=True).start()

    def gen():
        while True:
            ev, data = q.get()
            yield f"event: {ev}\ndata: {json.dumps(data)}\n\n"
            if ev in ("result", "error"):
                break
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/scenario/{sid}/agent/{aid}")
def agent(sid: str, aid: int):
    _need_ready()
    if sid not in S.scen:
        raise HTTPException(404, "unknown scenario")
    names = {p["id"]: p["name"] for p in S.world.pois}
    b = R.agent_view(S.base, aid, S.P, names)
    p = R.agent_view(S.scen[sid], aid, S.P, names)
    if not b and not p:
        raise HTTPException(404, "unknown agent")
    prof = dict(p or b)
    for k in ("trips", "diary", "mode", "mode_probs", "ties"):
        prof.pop(k, None)
    btie = {t["agent_id"] for t in (b or {}).get("ties", [])}
    ties = [{**t, "new_in_plan": t["agent_id"] not in btie} for t in (p or {}).get("ties", [])]
    return R._round({**prof, "baseline": {k: (b or {}).get(k) for k in ("mode", "mode_probs", "trips", "diary")},
                     "plan": {k: (p or {}).get(k) for k in ("mode", "mode_probs", "trips", "diary")}, "ties": ties})


@app.get("/scenarios")
def list_scenarios():
    _need_ready()
    return [{"id": k, "name": v.get("name"), "edits": v["edits"], "value_total": S.result_json(k, True)["value"]["total"]} for k, v in S.scen.items()]


# Droid policy compiler (Factory) — mounted from backend/droid
try:
    from droid.api import live_router as droid_live_router, router as droid_router
    app.include_router(droid_router)
    app.include_router(droid_live_router)
except ImportError:  # pragma: no cover
    pass

# Narrative layer (Claude) — mounted from narrative.py
try:
    from .narrative import router as narrative_router
    app.include_router(narrative_router)
except ImportError:  # pragma: no cover
    pass
