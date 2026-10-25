"""The simulation engine: settle loop (MATSim-style replanning days), calibrated logit mode choice,
congestion-aware assignment, walking flows, Huff destination choice + walk-by retail, co-presence
social ties, land use, and the $ valuation. One call to `evaluate(edits)` simulates one weekday."""
import hashlib
import json
import math
import time

import numpy as np

from . import policies
from .network import CarNet, WalkNet
from .population import (MODES, REGIONS, RESIDENT, THROUGH, TIERS, VISITOR, WORKER, KIND_NAMES,
                         PopulationBuilder, agent_name, edited_capacity, inlet_capacity, inlet_penalty_s, through_eligible)

CAR, TRANSIT, WALK, BIKE = 0, 1, 2, 3
CAT_LUNCH = {"restaurant": 1.3, "fast_food": 1.1, "cafe": 0.8, "bar": 0.2, "shop": 0.0}
CAT_COFFEE = {"cafe": 1.0}
CAT_ERRAND = {"shop": 1.0, "cafe": 0.3, "fast_food": 0.2}
CAT_EVENING = {"restaurant": 1.0, "bar": 1.1, "cafe": 0.15}
CAT_VISIT = {"shop": 1.0, "restaurant": 0.5, "cafe": 0.4, "fast_food": 0.3, "bar": 0.1}
PURPOSE_SEED = {"coffee_am": 8, "lunch": 1, "coffee": 2, "errand": 3, "evening": 4, "visit": 5, "visit2": 6, "visit3": 7}
CAR_OCCUPANCY = 1.12  # persons per commuter car (drive alone + carpool mix)
MAX_SAMPLE_TRIPS = 4000


def hash_uniform(a, b, c):
    """Deterministic U(0,1) from integer arrays (common random numbers across scenarios)."""
    a = np.asarray(a, dtype=np.uint64); b = np.asarray(b, dtype=np.uint64)
    with np.errstate(over="ignore"):
        h = a * np.uint64(0x9E3779B97F4A7C15) ^ (b + np.uint64(0x632BE59BD9B4E019)) * np.uint64(0xC2B2AE3D27D4EB4F) ^ np.uint64(c * 0x165667B19E3779F9 & 0xFFFFFFFFFFFFFFFF)
        h ^= h >> np.uint64(33); h *= np.uint64(0xFF51AFD7ED558CCD); h ^= h >> np.uint64(33); h *= np.uint64(0xC4CEB9FE1A85EC53); h ^= h >> np.uint64(33)
    return (h >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def gumbel(u):
    u = np.clip(u, 1e-12, 1 - 1e-12)
    return -np.log(-np.log(u))


def edits_key(edits):
    norm = {"pedestrianized": sorted(int(e) for e in edits.get("pedestrianized", [])),
            "reopened": sorted(int(e) for e in edits.get("reopened", [])),
            "reopen_mode": edits.get("reopen_mode") if edits.get("reopen_mode") in ("pre2020",) else "",
            "blocks": {str(int(k)): {"scale": round(float(v.get("scale", 1)), 3), "zone": v.get("zone") or ""} for k, v in sorted(edits.get("blocks", {}).items(), key=lambda kv: int(kv[0]))},
            "policies": sorted([{"kind": p["kind"], "target": p.get("target") or "", "amount": round(float(p.get("amount", 0)), 2),
                                   **({"params": {k: p["params"][k] for k in sorted(p["params"])}} if p.get("params") else {})} for p in edits.get("policies", [])], key=lambda p: (p["kind"], p["target"]))}
    return norm, hashlib.sha1(json.dumps(norm, sort_keys=True).encode()).hexdigest()[:12]


class Engine:
    def __init__(self, world, params, inputs):
        self.w, self.P, self.I = world, params, inputs
        pph = inputs.persons_per_household()
        if pph:
            params.set("sf_persons_per_household", pph, status="data", note="ACS 2023 5-yr, tracts in the sim area")
        self.pb = PopulationBuilder(world, params, inputs)
        self.scale = self.pb.scale
        w = world
        self.gate_ped = {}  # car inlet -> nearest walk node (people walking/cycling in from that side)
        for g in w.inlets:
            if g["mode"] == "car":
                x, z = w.nodes[(g["entries"] or g["exits"])[0]]
                self.gate_ped[g["i"]] = w.nearest_node(x, z, w.ped_main)
        self._inlet_sets()
        self.cap = np.array([params["lane_capacity_vph"].get(c, 600) for c in w.edge_cls]) * w.edge_lanes
        self.base_closed = self._market_car_free()
        self.poi_bld = self._poi_buildings()
        self.hour_propensity = self._hour_propensity()
        self.poi_q = self._poi_quality()
        self.asc = {"car": -0.4, "walk": -0.6, "bike": -2.2}
        self._walknets = {}
        self.baseline = None
        self.noise_alias = {}  # agent id -> agent id whose destination noise it shares (scripted demo pair)

    # ── car inlets: who may enter and leave where ──
    def _inlet_sets(self):
        """For each home region, the car inlets its drivers may use, each with a head-start cost (extra outside
        minutes from `region_car_access` + a class penalty). Through-traffic gets the eligible surface inlets of
        each map side. Drivers then pick the cheapest inlet by route cost, so closures move them elsewhere."""
        w, P = self.w, self.P
        cars = [g for g in w.inlets if g["mode"] == "car"]
        self.region_access = []
        for r in REGIONS:
            best = {}
            for sel, extra in P["region_car_access"].get(r["key"], [["key:" + r["car"], 0]]):
                kind, val = sel.split(":", 1)
                hit = [g for g in cars if (g["key"] == val if kind == "key" else g["side"] == val)]
                for g in hit:
                    off = 60.0 * float(extra) + (0.0 if g["key"] == r["car"] else inlet_penalty_s(g, P))
                    best[g["i"]] = min(best.get(g["i"], np.inf), off)
            best.setdefault(w.inlet_by_key[r["car"]]["i"], 0.0)
            self.region_access.append(best)
        self.through_side = {}
        for sd in ("north", "east", "south", "west"):
            self.through_side[sd] = {g["i"]: inlet_penalty_s(g, P) for g in cars if g["side"] == sd and through_eligible(g, P)}

    def sources(self, access, which, extra=None):
        """Tree sources (node, offset_s) and node->inlet map for a set {inlet: offset_s}. `which` = entries|exits."""
        w = self.w
        best = {}
        for i, off in access.items():
            o = off + (extra or {}).get(i, 0.0)
            for n in w.inlets[i][which]:
                if n not in best or o < best[n][0]:
                    best[n] = (o, i)
        src = tuple(sorted((n, round(o, 1)) for n, (o, _) in best.items()))
        return src, {n: i for n, (o, i) in best.items()}

    # ── static helpers ──
    def _market_car_free(self):
        """Market St has been closed to private cars from 10th St to Main St since Jan 29, 2020 (Better Market
        Street). That is today's reality, so the baseline has it closed; edits may reopen it (validation)."""
        w = self.w
        mk = [i for i in w.edges_named("Market Street") if w.edge_car[i] and not w.edge_hw[i]]
        main = {int(n) for i in w.edges_named("Main Street") for n in (w.edge_a[i], w.edge_b[i])}
        xs = [w.nodes[n][0] for i in mk for n in (w.edge_a[i], w.edge_b[i]) if int(n) in main]
        x_main = min(xs) if xs else 1e9
        return sorted(i for i in mk if w.edge_mid[i][0] < x_main)

    def closed_for(self, norm):
        w = self.w
        closed = set(self.base_closed) - set(norm.get("reopened", []))
        closed |= {e for e in norm["pedestrianized"] if 0 <= e < w.E and w.edge_car[e] and not w.edge_hw[e]}
        return closed

    def cost_factor(self, norm):
        f = np.ones(self.w.E)
        if norm.get("reopen_mode") == "pre2020":
            f[[e for e in norm.get("reopened", []) if e in set(self.base_closed)]] = self.P["market_pre2020_cost_factor"]
        return f

    def _poi_buildings(self):
        w = self.w
        out = np.full(w.P, -1)
        for i, (x, z) in enumerate(w.poi_xy):
            d = np.hypot(w.bld_c[:, 0] - x, w.bld_c[:, 1] - z)
            j = int(d.argmin())
            if d[j] < 90:
                out[i] = j
        return out

    def _hour_propensity(self):
        """Per-category hourly multiplier on walk-in propensity, from Google popular-times shapes (calibrated):
        people don't wander into a bar at 8 am. Normalized so the mean over 7:00-22:00 is 1."""
        prof = ((self.I.businesses or {}).get("meta") or {}).get("avg_weekday_profile_by_category") or {}
        out = {}
        for cat in ("cafe", "restaurant", "fast_food", "bar", "shop"):
            v = prof.get(cat)
            v = v.get("weekday_profile") if isinstance(v, dict) else v
            if isinstance(v, list) and len(v) == 24 and max(v) > 0:
                a = np.array(v, float)
                out[cat] = a / a[7:23].mean()
            else:
                out[cat] = np.ones(24)
        return out

    def _poi_quality(self):
        """Attractiveness multiplier from Google rating/reviews when matched, else a deterministic 0.6–1.4 draw."""
        w = self.w
        q = 0.6 + hash_uniform(np.arange(w.P), 7, 11) * 0.8
        self.poi_google = {}
        biz = self.I.businesses_by_poi()
        if biz:
            for pid, r in biz.items():
                if 0 <= pid < w.P:
                    rating = r.get("rating") or 4.2
                    reviews = r.get("reviews") or 20
                    q[pid] = (rating / 4.3) ** 2 * (0.55 + 0.12 * math.log1p(reviews))
                    self.poi_google[pid] = r
        return np.clip(q, 0.25, 3.0)

    def walknet(self, car_free):
        key = frozenset(car_free)
        net = self._walknets.get(key)
        if net is None:
            P = self.P
            net = WalkNet(self.w, car_free, P["walking_speed_m_s"], P["car_free_walk_comfort_bonus"],
                          P["bike_speed_m_s"], P["car_free_bike_comfort_bonus"], P["busy_street_bike_penalty"], P["route_noise_sd"])
            if len(self._walknets) > 6:
                self._walknets.pop(next(iter(self._walknets)))
            self._walknets[key] = net
        return net

    # ───────────────────────── evaluate ─────────────────────────
    def calibrate(self, progress=None):
        """Cold start: calibrate mode-choice constants to the observed downtown mode split, settle traffic,
        and keep the resulting flows as the shared starting state. Then the baseline is evaluated by the
        exact same procedure as every plan, so a plan with no edits reproduces the baseline exactly."""
        P, w = self.P, self.w
        norm, _ = edits_key({})
        pop = self.pb.base
        closed = self.closed_for(norm)
        car = CarNet(w, closed)
        ctx = Ctx(self, pop, car, self.walknet(closed), norm, closed)
        vol_avg = np.zeros((24, w.E))
        cong = np.ones((24, w.E))
        k = 0
        rounds, per_round = 5, 4
        for r in range(rounds):
            for _ in range(per_round if r < rounds - 1 else P["settle_days_baseline"]):
                car.reset()
                ctx.choose(cong, None)
                vol = ctx.load_cars(cong)
                k += 1
                vol_avg += (vol - vol_avg) / k
                cong = self._bpr(vol_avg)
                if progress:
                    progress(k, (rounds - 1) * per_round + P["settle_days_baseline"])
            if r < rounds - 1:
                self._calibrate_asc(ctx)
        self.seed = {"vol": vol_avg, "cong": cong}
        self.baseline = None
        self.baseline = self.evaluate({}, progress=None)
        return self.baseline

    def evaluate(self, edits, progress=None):
        """One weekday under `edits`: replanning days warm-started from the calibrated state (MSA on flows)."""
        t0 = time.time()
        P, w = self.P, self.w
        norm, key = edits_key(edits)
        is_base = not (norm["pedestrianized"] or norm["blocks"] or norm["policies"] or norm["reopened"])
        closed = self.closed_for(norm)
        pop = self.pb.for_edits(norm)
        car = CarNet(w, closed, self.cost_factor(norm))
        walk = self.walknet(closed)
        ctx = Ctx(self, pop, car, walk, norm, closed)
        ref = None if (is_base or self.baseline is None) else self.baseline["_state"]
        days = P["settle_days_plan"]
        vol_avg = self.seed["vol"].copy()
        cong = self.seed["cong"].copy()
        gaps = []
        for k in range(days):
            car.reset()
            ctx.choose(cong, ref)
            vol = ctx.load_cars(cong)
            prev = vol_avg.copy()
            vol_avg += (vol - vol_avg) / (k + 2)
            gaps.append(float(np.abs(vol_avg - prev).sum() / max(prev.sum(), 1)))
            cong = self._bpr(vol_avg)
            if progress:
                progress(k + 1, days)
        car.reset()
        ctx.choose(cong, ref)
        vol = ctx.load_cars(cong)
        ctx.cong = cong
        res = ctx.finalize(vol)
        res["id"] = "baseline" if is_base else key
        res["edits"] = norm
        res["settle"] = {"days": days, "ms": int((time.time() - t0) * 1000), "converged": gaps[-1] < 0.03,
                         "gap": round(gaps[-1], 4)}
        return res

    def _bpr(self, vol):
        P = self.P
        modeled_share = 1 - P["background_traffic_share"]
        total = vol / modeled_share
        x = total / np.maximum(self.cap, 1)[None, :]
        f = 1 + P["bpr_alpha"] * np.power(x, P["bpr_beta"])
        f[:, ~self.w.edge_car] = 1
        return np.minimum(f, 8.0)

    def _calibrate_asc(self, ctx):
        tgt = self.P["downtown_sf_worker_mode_share"]
        drive = tgt.get("drive_alone", 0) + tgt.get("carpool", 0)
        t = {"car": drive, "transit": tgt.get("transit", 0), "walk": tgt.get("walk", 0), "bike": tgt.get("bike", 0)}
        s = sum(t.values()) or 1
        t = {k: v / s for k, v in t.items()}
        m = ctx.pop.kind == WORKER
        shares = {k: max(float(np.mean(ctx.mode[m] == i)), 1e-4) for i, k in enumerate(MODES)}
        for k in ("car", "walk", "bike"):
            self.asc[k] += math.log(t[k] / shares[k]) - math.log(t["transit"] / shares["transit"])
        self.calibration = {"target": t, "modeled_before_step": shares, "asc": dict(self.asc)}


class Ctx:
    """Everything for one scenario evaluation."""

    def __init__(self, eng, pop, car, walk, edits, closed):
        self.e, self.pop, self.car, self.walk, self.edits, self.closed = eng, pop, car, walk, edits, closed
        w, P = eng.w, eng.P
        n = pop.n
        self.n = n
        self.region = pop.region
        self.mode = np.full(n, TRANSIT)
        self.gone = np.zeros(n, bool)
        self.bld = pop.bld
        safe_b = np.maximum(pop.bld, 0)
        # Park at the nearest car node that is still open in this scenario.
        park = np.full(w.B, -1)
        for b in np.unique(pop.bld[pop.bld >= 0]):
            for c in w.bld_car_cands[b]:
                if car.open_node[c]:
                    park[b] = c
                    break
        self.car_node = np.where(pop.bld >= 0, park[safe_b], -1)
        self.ped_node = np.where(pop.bld >= 0, w.bld_ped_node[safe_b], -1)
        # Main car inlet of each home region: where walkers and cyclists from that direction come in. Drivers
        # choose their actual entry/exit inlet by route cost (see car_times); car_in/car_out hold those choices.
        self.prim_in = np.array([w.inlet_by_key[REGIONS[r]["car"]]["i"] for r in pop.region])
        self.car_in = self.prim_in.copy()
        self.car_out = self.prim_in.copy()
        self.bart_in = np.array([w.inlet_by_key[REGIONS[r]["bart"]]["i"] for r in pop.region])
        vot = P["vot_personal_usd_per_hr"] * np.array([0.6, 1.0, 1.6])[pop.tier]
        self.beta_t = P["beta_time_per_min"]
        self.beta_c = self.beta_t * 60 / vot  # utils per $
        self.vot = vot
        # Visitors: first stop picked from their arrival point; resolved in finalize. Their car (if any) parks near Union Square/FiDi.
        self.charge = self._policy_charge()
        self.PO = self._pois()
        # Plugin policies (hp/policies): extra $ per car trip, car edge-time factors, POI attractiveness.
        self.fx = policies.effects(self)
        car.factor = car.factor * self.fx.edge_cost_factor

    def _pois(self):
        """Base POIs plus plan-only shops created by rezoning a building to retail or mixed use."""
        w, e = self.e.w, self.e
        node, cat, q, edges, xy, bld, ids, names = list(w.poi_node), list(w.poi_cat), list(e.poi_q), list(w.poi_edges), list(map(tuple, w.poi_xy)), list(e.poi_bld), list(range(w.P)), [p["name"] for p in w.pois]
        for b, ed in sorted(self.edits.get("blocks", {}).items(), key=lambda kv: int(kv[0])):
            b = int(b); z = ed.get("zone")
            kind = w.bld_kind[b] if 0 <= b < w.B else None
            if z not in ("retail", "mixed") or kind in ("retail",) or (z == "mixed" and kind == "mixed"):
                continue
            n = int(np.clip(round(math.sqrt(w.bld_area[b]) / 14), 1, 4))
            for i in range(n):
                c = ["cafe", "restaurant", "shop", "fast_food"][i % 4]
                x, zz = w.bld_c[b][0] + (i - n / 2) * 8, w.bld_c[b][1] + 6
                node.append(w.nearest_node(x, zz, w.ped_main)); cat.append(c); q.append(1.1); edges.append(w.edges_near(x, zz))
                xy.append((x, zz)); bld.append(b); ids.append(5000 + b * 5 + i)
                names.append({"cafe": "New café", "restaurant": "New restaurant", "shop": "New shop", "fast_food": "New quick bite"}[c])
        class T: pass
        t = T()
        t.node, t.cat, t.q, t.edges, t.xy, t.bld, t.ids, t.names = np.array(node), np.array(cat), np.array(q), edges, np.array(xy), np.array(bld), np.array(ids), names
        t.n = len(ids)
        return t

    def _policy_charge(self):
        """Area-wide charges hit every AM-peak car commuter. A charge at one inlet is a toll on entering there:
        it is added to that inlet's entry cost in the AM peak, so drivers may switch to a neighbouring inlet."""
        pop, w = self.pop, self.e.w
        c = np.zeros(self.n)
        self.inlet_charge = {}
        for p in self.edits.get("policies", []):
            amt = float(p.get("amount", 0))
            if p["kind"] == "congestion_charge":
                tgt = p.get("target") or ""
                if tgt:
                    if tgt in w.inlet_by_key and w.inlet_by_key[tgt]["mode"] == "car":
                        i = w.inlet_by_key[tgt]["i"]
                        self.inlet_charge[i] = self.inlet_charge.get(i, 0.0) + amt
                    continue
                hit = (pop.arrive >= 7 * 3600) & (pop.arrive <= 10 * 3600)
                c += np.where(hit, amt, 0)
            elif p["kind"] == "parking_price":
                c += amt / 2  # per one-way trip
        return c

    # ── travel times ──
    def commute_sources(self, r, hour, which):
        """Tree sources for region r's drivers: its inlets' entries (AM) or exits (PM), with head-start costs.
        An inlet toll counts in the AM peak as time at the commuter VOT (×2: the logit averages AM and PM)."""
        e = self.e
        extra = None
        if which == "entries" and self.inlet_charge and 6 <= hour <= 9:
            sec_per_usd = 3600.0 / e.P["vot_personal_usd_per_hr"]
            extra = {i: 2 * amt * sec_per_usd for i, amt in self.inlet_charge.items()}
        return e.sources(e.region_access[int(r)], which, extra)

    def car_times(self, cong):
        """In-map AM and PM car seconds per worker (inf if unreachable), from the cheapest inlet of their region."""
        pop, car = self.pop, self.car
        am = np.full(self.n, np.inf); pm = np.full(self.n, np.inf)
        dep_am = np.clip(((pop.arrive - 600) // 3600).astype(int), 0, 23)
        dep_pm = np.clip((pop.leave // 3600).astype(int), 0, 23)
        wk = (pop.kind == WORKER) & (self.car_node >= 0)
        for r in np.unique(self.region[wk]):
            mr = wk & (self.region == r)
            for h in np.unique(dep_am[mr]):
                m = mr & (dep_am == h)
                t = car.tree_multi(self.commute_sources(r, int(h), "entries")[0], int(h), cong)
                am[m] = t.dist[self.car_node[m]]
            for h in np.unique(dep_pm[mr]):
                m = mr & (dep_pm == h)
                t = car.tree_multi(self.commute_sources(r, int(h), "exits")[0], int(h), cong, reverse=True)
                pm[m] = t.dist[self.car_node[m]]
        return am, pm

    def _inlet_tolls(self):
        """$ each driving worker pays at a tolled inlet: AM-peak arrivals that actually entered there."""
        pop = self.pop
        if not self.inlet_charge:
            return np.zeros(self.n)
        dep_am = np.clip(((pop.arrive - 600) // 3600).astype(int), 0, 23)
        amt = np.array([self.inlet_charge.get(int(i), 0.0) for i in self.car_in])
        return np.where((dep_am >= 6) & (dep_am <= 9), amt, 0.0)

    def resolve_car_inlets(self):
        """Which inlet each driving worker actually entered and left by (roots of their trees)."""
        pop, car, cong = self.pop, self.car, self.cong
        dep_am = np.clip(((pop.arrive - 600) // 3600).astype(int), 0, 23)
        dep_pm = np.clip((pop.leave // 3600).astype(int), 0, 23)
        wk = (pop.kind == WORKER) & (self.mode == CAR) & ~self.gone & (self.car_node >= 0)
        for r in np.unique(self.region[wk]):
            mr = wk & (self.region == r)
            for dep, which, rev, out in ((dep_am, "entries", False, self.car_in), (dep_pm, "exits", True, self.car_out)):
                for h in np.unique(dep[mr]):
                    m = np.where(mr & (dep == h))[0]
                    src, n2i = self.commute_sources(r, int(h), which)
                    roots = car.tree_multi(src, int(h), cong, reverse=rev).roots()[self.car_node[m]]
                    out[m] = [n2i.get(int(x), out[k]) for x, k in zip(roots, m)]

    def walk_in_times(self, wk=None):
        """Seconds walking from the inlet/station to the workplace (perceived), and cycling from the region gate.
        `wk` defaults to this scenario's walk network; welfare uses the bonus-free physical network instead."""
        pop, w = self.pop, self.e.w
        wk = wk or self.walk
        st_walk = np.full(self.n, np.inf)
        self.st_node = np.full(self.n, -1)
        for i in w.rail_inlets:
            nodes = w.inlets[i]["nodes"]
            m = (self.bart_in == i) & (self.ped_node >= 0)
            if not m.any():
                continue
            D = wk.dist[np.ix_(nodes, self.ped_node[m])]
            k = D.argmin(0)
            st_walk[m] = D[k, np.arange(m.sum())]
            self.st_node[m] = np.array(nodes)[k]
        gate = np.array([self.e.gate_ped.get(c, -1) for c in self.prim_in])
        self.gate = gate
        walk_in = np.where((gate >= 0) & (self.ped_node >= 0), wk.dist[np.maximum(gate, 0), np.maximum(self.ped_node, 0)], np.inf)
        bike_in = np.full(self.n, np.inf)
        draw = pop.id % 3
        for g in np.unique(gate[gate >= 0]):
            for k in range(3):
                m = (gate == g) & (self.ped_node >= 0) & (draw == k)
                if m.any():
                    bike_in[m] = wk.bike_tree(int(g), k).dist[self.ped_node[m]]
        # Downtown residents commuting within the area start at home.
        return st_walk, walk_in, bike_in

    # ── one replanning day ──
    def choose(self, cong, warm):
        e, P, pop = self.e, self.e.P, self.pop
        am, pm = self.car_times(cong)
        if not hasattr(self, "_walk_static"):
            self._walk_static = self.walk_in_times()
            # Welfare is measured on physical distances: closing a street to cars doesn't shorten anyone's walk, and its
            # amenity (comfort bonus) is credited under Street life / Economy, so it must not count again as time saved.
            # (On perceived distances the bonus also pushed walks under the 55-min availability cutoff, so a whole mode
            # appeared in the log-sum: 38 workers were worth ~60% of a "+$10M" alley closure.)
            welfare_net = self.e.walknet(frozenset())
            keep = (self.st_node, self.gate)   # walk_in_times sets these as a side effect; choices use the perceived ones
            self._walk_welfare = self._walk_static if welfare_net is self.walk else self.walk_in_times(welfare_net)
            self.st_node, self.gate = keep
        R = REGIONS
        car_out = np.array([R[r]["car_min"] for r in self.region], float)
        tr_out = np.array([R[r]["tr_min"] for r in self.region], float)
        walk_out = np.array([R[r]["walk_m"] if R[r]["walk_m"] is not None else np.nan for r in self.region], float)
        bike_out = np.array([R[r]["bike_m"] if R[r]["bike_m"] is not None else np.nan for r in self.region], float)
        fare = np.array([P["bart_fare_usd"].get(R[r]["fare"], 3.0) for r in self.region])
        toll = np.array([P["bridge_toll_usd"] / 2 if R[r]["toll"] else 0.0 for r in self.region])
        miles = np.array([R[r]["miles"] for r in self.region], float)
        car_in_min = (am + pm) / 2 / 60
        mult = P["walk_wait_time_multiplier"]
        bt, bc = self.beta_t, self.beta_c
        car_cost = P["daily_parking_cost_fidi_usd"] / 2 + toll + P["vehicle_operating_cost_usd_per_mile"] * (miles + 1.5) + self.charge + self.fx.car_cost_usd

        def utilities(st_walk, walk_in, bike_in):
            V = np.full((self.n, 4), -np.inf)
            V[:, CAR] = e.asc["car"] + bt * (car_out + car_in_min + 4) + bc * car_cost
            V[:, TRANSIT] = bt * (tr_out + 5 * mult + st_walk / 60 * mult) + bc * fare
            walk_total = (np.nan_to_num(walk_out, nan=1e9) / P["walking_speed_m_s"] + walk_in) / 60
            V[:, WALK] = np.where(walk_total < 55, e.asc["walk"] + bt * walk_total * mult, -np.inf)
            bike_total = (np.nan_to_num(bike_out, nan=1e9) / P["bike_speed_m_s"] + bike_in) / 60
            V[:, BIKE] = np.where(bike_total < 45, e.asc["bike"] + bt * bike_total * 1.5, -np.inf)
            V[~pop.car | ~np.isfinite(car_in_min), CAR] = -np.inf
            return V

        V = utilities(*self._walk_static)                                       # perceived: drives choices
        self.V_welfare = V if self._walk_welfare is self._walk_static else utilities(*self._walk_welfare)
        workers = pop.kind == WORKER
        U = V + pop.eps
        mode = np.argmax(U, 1)
        # Visitors: car if they came by car (set at creation), else transit.
        vis = pop.kind == VISITOR
        mode[vis] = np.where(pop.car[vis], CAR, TRANSIT)
        res = pop.kind == RESIDENT
        mode[res] = WALK
        thr = pop.kind == THROUGH
        mode[thr] = CAR
        gone = np.zeros(self.n, bool)
        self.car_in_min = car_in_min
        if warm is not None:
            # Trip suppression (traffic evaporation): car trips whose in-map time rose vs the baseline.
            base_t = warm["car_in_min_by_id"]
            bt_agents = np.array([base_t.get(int(i), np.nan) for i in pop.id])
            dt = car_in_min - bt_agents
            rel = np.where(np.isfinite(dt) & (dt > 0), dt / (car_out + bt_agents + 1e-9), 0)
            p_gone = np.clip(-P["car_trip_time_elasticity"] * rel, 0, 0.6)
            gone = workers & (mode == CAR) & (pop.u_gone < p_gone)
        # Through traffic: drive through the area, or take the freeway bypass (diverted out of the area).
        self.through_time = self._through_times(cong)
        if thr.any():
            t_in = self.through_time[thr] / 60
            free = self._through_free[thr] / 60
            byp = free + P["bypass_penalty_min"]
            stay = (bt * t_in + bc[thr] * self.fx.car_cost_usd[thr] + pop.eps[thr, 0]) > (bt * byp + pop.eps[thr, 1])
            g = np.zeros(self.n, bool)
            g[np.where(thr)[0][~stay]] = True
            gone |= g
            if warm is not None:
                base_t = warm["through_min_by_id"]
                b = np.array([base_t.get(int(i), np.nan) for i in pop.id[thr]])
                rel = np.where(np.isfinite(b) & (t_in > b), (t_in - b) / (b + 15), 0)
                sup = pop.u_gone[thr] < np.clip(-P["car_trip_time_elasticity"] * rel, 0, 0.6)
                gone[np.where(thr)[0][sup]] = True
        self.V, self.mode, self.gone = V, mode, gone

    def _through_groups(self):
        """Through agents grouped by (origin side, 2-hour departure bucket); the bucket keeps the tree count low."""
        pop, w = self.pop, self.e.w
        thr = np.where(pop.kind == THROUGH)[0]
        side_in = np.array([w.inlets[int(i)]["side"] for i in pop.in_inlet[thr]]) if len(thr) else np.array([])
        side_out = np.array([w.inlets[int(i)]["side"] for i in pop.out_inlet[thr]]) if len(thr) else np.array([])
        hours = np.clip((pop.arrive[thr] // 3600).astype(int), 0, 23)
        bucket = hours - hours % 2
        return thr, side_in, side_out, bucket

    def _through_route(self, car, cong, t_hour_fn):
        """Shortest in-map time for every through agent from the cheapest inlet on its origin side to the
        cheapest exit on its destination side, plus the chosen exit node and both inlets."""
        e, pop = self.e, self.pop
        thr, side_in, side_out, bucket = self._through_groups()
        dist = np.full(self.n, np.inf); target = np.full(self.n, -1); ein = np.full(self.n, -1); eout = np.full(self.n, -1)
        for sa in np.unique(side_in):
            src, n2i = e.sources(e.through_side[sa], "entries")
            if not src:
                continue
            for hb in np.unique(bucket[side_in == sa]):
                t = car.tree_multi(src, t_hour_fn(int(hb)), cong)
                roots = t.roots()
                for sb in np.unique(side_out[(side_in == sa) & (bucket == hb)]):
                    xsrc, x2i = e.sources(e.through_side[sb], "exits")
                    if not xsrc:
                        continue
                    nodes = np.array([n for n, _ in xsrc]); offs = np.array([o for _, o in xsrc])
                    d = t.dist[nodes] + offs
                    k = int(np.argmin(d))
                    rows = thr[(side_in == sa) & (side_out == sb) & (bucket == hb)]
                    dist[rows] = d[k]; target[rows] = nodes[k]
                    ein[rows] = n2i.get(int(roots[nodes[k]]), -1); eout[rows] = x2i[int(nodes[k])]
        return dist, target, ein, eout

    def _through_times(self, cong):
        w = self.e.w
        out, self._through_target, self._through_in, self._through_out = self._through_route(self.car, cong, lambda h: h)
        if not hasattr(self, "_through_free"):
            fc = CarNet(w, self.closed, self.car.factor)
            self._through_free = self._through_route(fc, np.ones((24, w.E)), lambda h: 0)[0]
        return out

    # ── car loading ──
    def load_cars(self, cong):
        """Vehicles per hour per edge from agents' car trips (scaled to real vehicles)."""
        e, w, pop, car = self.e, self.e.w, self.pop, self.car
        S = e.scale
        vol = np.zeros((24, w.E))
        drive = (self.mode == CAR) & ~self.gone
        occ = np.where(pop.kind == THROUGH, 1.0, CAR_OCCUPANCY)
        veh = S / occ
        dep_am = np.clip(((pop.arrive - 600) // 3600).astype(int), 0, 23)
        dep_pm = np.clip((pop.leave // 3600).astype(int), 0, 23)
        wk = drive & (pop.kind == WORKER) & (self.car_node >= 0)
        for r in np.unique(self.region[wk]):
            mr = wk & (self.region == r)
            for dep, which, rev in ((dep_am, "entries", False), (dep_pm, "exits", True)):
                for h in np.unique(dep[mr]):
                    m = mr & (dep == h)
                    t = car.tree_multi(self.commute_sources(r, int(h), which)[0], int(h), cong, reverse=rev)
                    loads = np.zeros(w.N)
                    np.add.at(loads, self.car_node[m], veh[m])
                    np.add.at(vol[h], car.arc_edge, car.accumulate(t, loads))
        thr, side_in, side_out, bucket = self._through_groups()
        go = drive[thr] & (self._through_target[thr] >= 0)
        hours = np.clip((pop.arrive[thr] // 3600).astype(int), 0, 23)
        for sa in np.unique(side_in[go]):
            src, _ = e.sources(e.through_side[sa], "entries")
            for hb in np.unique(bucket[go & (side_in == sa)]):
                t = car.tree_multi(src, int(hb), cong)
                for h in np.unique(hours[go & (side_in == sa) & (bucket == hb)]):
                    rows = thr[go & (side_in == sa) & (bucket == hb) & (hours == h)]
                    loads = np.zeros(w.N)
                    np.add.at(loads, self._through_target[rows], veh[rows])
                    np.add.at(vol[h], car.arc_edge, car.accumulate(t, loads))
        return vol

    # ───────────────────────── final day: trips, flows, retail, social, metrics ─────────────────────────
    def finalize(self, vol):
        e, P, w, pop = self.e, self.e.P, self.e.w, self.pop
        S = e.scale
        legs = Legs()
        legs.bind(self)
        self.resolve_car_inlets()
        # Commutes
        for i in np.where(pop.kind == WORKER)[0]:
            if self.gone[i]:
                continue
            m = self.mode[i]
            if m == CAR:
                legs.car(i, "commute_in", pop.arrive[i] - 600, self.car_in[i], -1, am=True)
                legs.car(i, "commute_out", pop.leave[i], -1, self.car_out[i], am=False)
            elif m == TRANSIT and self.st_node[i] >= 0:
                legs.walk(i, "commute_in", pop.arrive[i] - 480, int(self.st_node[i]), int(self.ped_node[i]), inlet_in=self.bart_in[i])
                legs.walk(i, "commute_out", pop.leave[i], int(self.ped_node[i]), int(self.st_node[i]), inlet_out=self.bart_in[i])
            elif m in (WALK, BIKE) and self.gate[i] >= 0:
                kind = "bike" if m == BIKE else "walk"
                legs.walk(i, "commute_in", pop.arrive[i] - 900, int(self.gate[i]), int(self.ped_node[i]), inlet_in=self.prim_in[i], mode=kind)
                legs.walk(i, "commute_out", pop.leave[i], int(self.ped_node[i]), int(self.gate[i]), inlet_out=self.prim_in[i], mode=kind)
        # Residents commuting out by transit
        res = np.where((pop.kind == RESIDENT) & pop.commute_out)[0]
        if len(res):
            near_st = self._nearest_station(self.ped_node[res])
            for i, (st, node, inl) in zip(res, near_st):
                if node < 0 or self.ped_node[i] < 0:
                    continue
                legs.walk(i, "commute_out", pop.leave[i], int(self.ped_node[i]), int(node), inlet_out=inl)
                legs.walk(i, "commute_in", pop.arrive[i], int(node), int(self.ped_node[i]), inlet_in=inl)
        # Visitors arrive at a station or park near their first stop.
        vis = np.where(pop.kind == VISITOR)[0]
        vis_origin = np.full(self.n, -1)
        for i in vis:
            inl = int(pop.in_inlet[i])
            g = w.inlets[inl]
            if g["mode"] == "ped":
                vis_origin[i] = g["nodes"][int(hash_uniform(pop.id[i], 3, 9) * len(g["nodes"]))]
            else:
                vis_origin[i] = e.gate_ped.get(inl, -1)
        # Destinations (Huff choice among POIs, walking)
        visits = []  # (agent_row, poi, t_arrive, dwell, purpose)

        def tour(rows, origin_nodes, cats, purpose, t_start, dwell, radius=900):
            if not len(rows):
                return
            pois = self.choose_poi(pop.id[rows], origin_nodes, cats, purpose, radius)
            for i, o, q, t, d in zip(rows, origin_nodes, pois, t_start, dwell):
                if q < 0:
                    continue
                qn = int(self.PO.node[q])
                out = legs.walk(i, purpose, t, int(o), qn, poi=q, dwell=d)
                arr = t + (out or 0)
                visits.append((i, q, arr, d, purpose))
                legs.walk(i, "return", arr + d, qn, int(o))

        present = ~self.gone & (self.ped_node >= 0)
        wk = (pop.kind == WORKER) & present
        am = wk & (hash_uniform(pop.id, 41, 5) < P["morning_coffee_share"])
        r = np.where(am)[0]; tour(r, self.ped_node[r], CAT_COFFEE, "coffee_am", pop.arrive[r] + 120, np.full(len(r), 300.0), 450)
        r = np.where(wk & pop.lunch)[0]; tour(r, self.ped_node[r], CAT_LUNCH, "lunch", pop.lunch_t[r], pop.lunch_dur[r])
        r = np.where(wk & pop.coffee)[0]; tour(r, self.ped_node[r], CAT_COFFEE, "coffee", pop.coffee_t[r], np.full(len(r), 600.0), 500)
        r = np.where(wk & pop.errand)[0]; tour(r, self.ped_node[r], CAT_ERRAND, "errand", pop.errand_t[r], np.full(len(r), 900.0))
        r = np.where(wk & pop.evening)[0]; tour(r, self.ped_node[r], CAT_EVENING, "evening", pop.eve_t[r], pop.eve_dur[r])
        rs = (pop.kind == RESIDENT) & (self.ped_node >= 0)
        r = np.where(rs & pop.coffee)[0]; tour(r, self.ped_node[r], CAT_COFFEE, "coffee", pop.coffee_t[r], np.full(len(r), 900.0), 600)
        r = np.where(rs & pop.errand)[0]; tour(r, self.ped_node[r], CAT_ERRAND, "errand", pop.errand_t[r], np.full(len(r), 1200.0))
        r = np.where(rs & pop.evening)[0]; tour(r, self.ped_node[r], CAT_EVENING, "evening", pop.eve_t[r], pop.eve_dur[r])
        vo = vis[vis_origin[vis] >= 0]
        if len(vo):
            for i in vo:
                inl = int(pop.in_inlet[i])
                if w.inlets[inl]["mode"] == "car":
                    legs.car(i, "commute_in", pop.arrive[i] - 600, inl, -1, am=True, visitor_node=True)
                else:
                    legs.mark_arrival(i, pop.arrive[i], inl)
            d_ = vo[pop.errand[vo]]
            tour(d_, vis_origin[d_], CAT_VISIT, "visit", pop.errand_t[d_], np.full(len(d_), 1500.0), 1300)
            ev = vo[pop.evening[vo]]
            tour(ev, vis_origin[ev], CAT_EVENING, "evening", pop.eve_t[ev], pop.eve_dur[ev], 1300)
            l = vo[pop.lunch[vo]]
            tour(l, vis_origin[l], CAT_LUNCH, "visit2", pop.lunch_t[l], pop.lunch_dur[l], 1300)
            c = vo[pop.coffee[vo]]
            tour(c, vis_origin[c], CAT_COFFEE, "visit3", pop.coffee_t[c], np.full(len(c), 900.0), 900)
            for i in vo:
                inl = int(pop.in_inlet[i])
                if w.inlets[inl]["mode"] == "car":
                    legs.car(i, "commute_out", pop.leave[i], -1, inl, am=False, visitor_node=True)
                else:
                    legs.mark_departure(i, pop.leave[i], inl)
        thr = np.where((pop.kind == THROUGH) & ~self.gone)[0]
        for i in thr:
            legs.car(i, "through", pop.arrive[i], int(self._through_in[i]), int(self._through_out[i]), am=True, through=True)
        self.legs = legs
        return self._outputs(vol, legs, visits, vis_origin)

    def car_leg_steps(self, L):
        """Road path of a car leg as steps (edge*2 + reversed), or None."""
        w, pop, car = self.e.w, self.pop, self.car
        i = L["row"]
        h = min(23, max(0, int(L["t"] // 3600)))
        if L.get("visitor"):
            return None
        if L["through"]:
            tgt = int(self._through_target[i])
            if tgt < 0:
                return None
            sa = w.inlets[int(pop.in_inlet[i])]["side"]
            src, _ = self.e.sources(self.e.through_side[sa], "entries")
            return car.path_steps(car.tree_multi(src, h - h % 2, self.cong), tgt)
        r = int(self.region[i])
        if L["am"]:
            return car.path_steps(car.tree_multi(self.commute_sources(r, h, "entries")[0], h, self.cong), int(self.car_node[i]))
        return car.path_steps(car.tree_multi(self.commute_sources(r, h, "exits")[0], h, self.cong, reverse=True), int(self.car_node[i]))

    def _nearest_station(self, nodes):
        w, wk = self.e.w, self.walk
        out = []
        for n in nodes:
            best = (None, -1, -1, np.inf)
            if n >= 0:
                for i in w.rail_inlets:
                    for s in w.inlets[i]["nodes"]:
                        d = wk.dist[n, s]
                        if d < best[3]:
                            best = (w.inlets[i]["key"], s, i, d)
            out.append(best[:3])
        return out

    def poi_bonus(self):
        """POIs fronting a car-free street get an attractiveness bonus (pleasant frontage, café seating)."""
        if not hasattr(self, "_poi_cf"):
            cf = self.walk.car_free
            planned = np.zeros(self.e.w.E, bool)
            if self.closed:
                planned[list(self.closed)] = True
            self._poi_cf = np.array([bool(edges) and planned[edges].any() for edges in self.PO.edges])
        return self._poi_cf

    def choose_poi(self, agent_ids, origins, cats, purpose, radius):
        """Huff/MNL destination choice: log(attractiveness) − decay·distance + car-free bonus + Gumbel noise (CRN)."""
        w, P = self.e.w, self.e.P
        catw = np.array([cats.get(c, 0.0) for c in self.PO.cat])
        ok = (catw > 0) & (self.PO.node >= 0)
        cand = np.where(ok)[0]
        out = np.full(len(origins), -1)
        if not len(cand):
            return out
        A = np.log(catw[cand] * self.PO.q[cand] * self.fx.poi_attractiveness[cand]) + P["car_free_poi_attractiveness_bonus"] * self.poi_bonus()[cand]
        decay = P["huff_distance_decay_per_m"]
        speed = P["walking_speed_m_s"]
        seed = PURPOSE_SEED[purpose]
        for s in range(0, len(origins), 1500):
            o = np.asarray(origins[s:s + 1500])
            ids = np.asarray(agent_ids[s:s + 1500])
            if self.e.noise_alias:
                ids = np.array([self.e.noise_alias.get(int(i), int(i)) for i in ids])
            D = self.walk.dist[np.ix_(np.maximum(o, 0), self.PO.node[cand])] * speed  # perceived meters
            U = A[None, :] - decay * D + gumbel(hash_uniform(ids[:, None] * 64 + seed, self.PO.ids[cand][None, :], seed))
            U[D > radius] = -np.inf
            k = U.argmax(1)
            good = np.isfinite(U[np.arange(len(o)), k]) & (o >= 0)
            out[s:s + 1500] = np.where(good, cand[k], -1)
        return out

    # ── outputs ──
    def _outputs(self, vol, legs, visits, vis_origin):
        e, P, w, pop = self.e, self.e.P, self.e.w, self.pop
        S = e.scale
        H = 24
        # Walking + cycling flows (people per hour per edge)
        ped_hour = np.zeros((H, w.E)); bike_hour = np.zeros((H, w.E))
        walk_m = np.zeros(self.n); bike_m = np.zeros(self.n)
        for mode, grid, acc in (("walk", ped_hour, walk_m), ("bike", bike_hour, bike_m)):
            Ls = [L for L in legs.walks if L["mode"] == mode and len(L["edges"])]
            if not Ls:
                continue
            ed = np.concatenate([L["edges"] for L in Ls])
            hr = np.repeat([min(23, int(L["t"] // 3600)) for L in Ls], [len(L["edges"]) for L in Ls])
            np.add.at(grid, (hr, ed), S)
            np.add.at(acc, [L["row"] for L in Ls], [L["len"] for L in Ls])
        car_hour = vol
        cong = self.cong
        # Cars: VMT and vehicle-hours in the map
        drive = (self.mode == CAR) & ~self.gone
        veh = np.where(pop.kind == THROUGH, S, S / CAR_OCCUPANCY)
        vmt_in = float((car_hour * w.edge_len[None, :]).sum() / 1609.34)
        veh_h = float((car_hour * (w.edge_free_s[None, :] * cong)).sum() / 3600)
        free_h = float((car_hour * w.edge_free_s[None, :]).sum() / 3600)
        bg = P["background_traffic_share"] / (1 - P["background_traffic_share"])
        miles_out = np.array([REGIONS[r]["miles"] for r in pop.region], float)
        wk = pop.kind == WORKER
        vmt_out = float(((drive & wk).astype(float) * miles_out * 2 * veh).sum())
        # Retail: destination visits + walk-by impulse visits (walkers only)
        cat = self.PO.cat
        NP = self.PO.n
        ticket = np.array([P["avg_ticket_usd"].get(c, 20) for c in cat])
        capture = np.array([P["impulse_capture_per_passerby"].get(c, 0.005) for c in cat])
        walkby_hour = np.zeros((H, NP))
        for j, edges in enumerate(self.PO.edges):
            if edges:
                walkby_hour[:, j] = ped_hour[:, edges].sum(1)
        bonus = self.poi_bonus()
        prop = np.stack([e.hour_propensity.get(c, np.ones(24)) for c in cat], 1)  # (24, NP)
        impulse_hour = walkby_hour * prop * (capture * self.PO.q * np.where(bonus, 1 + P["car_free_poi_attractiveness_bonus"], 1))[None, :]
        dest_hour = np.zeros((H, NP))
        for (i, q, t, d, purpose) in visits:
            dest_hour[min(23, int(t // 3600)), q] += S
        visits_hour = dest_hour + impulse_hour
        visits_day = visits_hour.sum(0)
        revenue_day = visits_day * ticket
        # Walker vs driver visit frequency (validation of the retail mechanism)
        visits_by_row = np.zeros(self.n)
        for (i, q, t, d, purpose) in visits:
            visits_by_row[i] += 1
        imp_rate = impulse_hour.sum() / max(ped_hour.sum(), 1)
        walker_rows = wk & ~self.gone & (self.mode != CAR)
        driver_rows = wk & drive
        walker_v = (visits_by_row[walker_rows].mean() if walker_rows.any() else 0) + imp_rate * (walk_m[walker_rows].mean() / 80 if walker_rows.any() else 0)
        driver_v = (visits_by_row[driver_rows].mean() if driver_rows.any() else 0) + imp_rate * (walk_m[driver_rows].mean() / 80 if driver_rows.any() else 0)
        # Social: co-presence at the same POI within the encounter window, plus lingering on car-free streets.
        win = P["encounter_window_min"] * 60
        bins = {}
        for (i, q, t, d, purpose) in visits:
            for b in range(int(t // win), int((t + d) // win) + 1):
                bins.setdefault((q, b), []).append(i)
        K = 6  # a person registers at most ~6 others in a bin
        habitual = np.isin(pop.kind, [WORKER, RESIDENT])
        enc = 0.0; enc_hab = 0.0
        tie_pairs = []
        for (q, b), rows in bins.items():
            n_people = len(rows) * S
            pairs = n_people * min(n_people - 1, K) / 2
            enc += pairs
            hab = sum(1 for r in rows if habitual[r])
            enc_hab += pairs * (hab / len(rows))
            if len(tie_pairs) < 900 and len(rows) > 1:
                rr = sorted(set(rows))
                for a_ in range(len(rr)):
                    for b_ in range(a_ + 1, min(len(rr), a_ + 4)):
                        A_, B_ = rr[a_], rr[b_]
                        same = pop.bld[A_] >= 0 and pop.bld[A_] == pop.bld[B_]
                        if habitual[A_] and habitual[B_] and (same or (pop.open[A_] > .72 and pop.open[B_] > .72)):
                            tie_pairs.append((int(pop.id[A_]), int(pop.id[B_]), int(q), int(b * win)))
        # Always report ties of the demo pair when they really are co-present (outside the sample cap).
        for dev, maria in e.noise_alias.items():
            rd, rm = np.where(pop.id == dev)[0], np.where(pop.id == maria)[0]
            if len(rd) and len(rm):
                for (q, b), rows in bins.items():
                    if rd[0] in rows and rm[0] in rows:
                        tie_pairs.insert(0, (int(maria), int(dev), int(q), int(b * win)))
                        break
        cf = np.zeros(w.E, bool)
        if self.closed:
            cf[list(self.closed)] = True
        linger = ped_hour[:, cf] * P["street_dwell_share_car_free"]
        street_enc = float((linger * np.minimum(np.maximum(linger - 1, 0), K) / 2).sum())
        enc += street_enc; enc_hab += street_enc * 0.6
        new_ties = enc_hab * P["tie_formation_prob_per_repeat_encounter"] * P["repeat_days_per_year"] / P["workdays_per_year"]
        # Appleyard: residents' friends on their street fall with traffic volume.
        car_day_people = car_hour.sum(0) * (1 + bg)
        res_rows = np.where(pop.kind == RESIDENT)[0]
        fr = P["appleyard_friends_by_traffic"]
        home_edge = self._home_edges(pop.bld[res_rows])
        adt = np.where(home_edge >= 0, car_day_people[np.maximum(home_edge, 0)], 0)
        friends = np.interp(adt, [0, 2000, 8000, 16000], [fr["light"] * 1.1, fr["light"], fr["moderate"], fr["heavy"]])
        neighbor_ties = float(friends.sum() * S)
        # Land use
        off, oth, resc = edited_capacity(w, P, e.pb.base_cap, self.edits) if self.edits.get("blocks") else e.pb.base_cap
        jobs = float((off + oth).sum()); residents = float(resc.sum())
        floor_delta = sum(w.bld_floor_area[int(b)] * (float(v.get("scale", 1)) - 1) for b, v in self.edits.get("blocks", {}).items() if 0 <= int(b) < w.B)
        access = self._access(res_rows)
        # Health: active minutes
        active_min = (walk_m / P["walking_speed_m_s"] + bike_m / P["bike_speed_m_s"]) / 60
        outside_walk = np.where(self.mode == TRANSIT, 8.0, 0.0) * (pop.kind == WORKER)  # walking at the home end of a transit trip
        active_min = active_min + outside_walk
        people_mask = np.isin(pop.kind, [WORKER, RESIDENT]) & ~self.gone
        rr, ref, cap_ = P["heat_walk_rr"], P["heat_walk_ref_min_per_week"], P["heat_walk_rr_cap"]
        red = np.minimum(cap_, (1 - rr) * active_min * 5 / ref)
        deaths_averted = float((red[people_mask] * S).sum() * P["us_crude_mortality_20_74"])
        # Commuter welfare: logit log-sum per worker (USD per trip), on physical walking distances (see choose()).
        V = getattr(self, "V_welfare", self.V)
        finite = np.isfinite(V)
        mx = np.where(finite.any(1), np.max(np.where(finite, V, -1e9), 1), 0)
        logsum = mx + np.log(np.sum(np.where(finite, np.exp(np.where(finite, V, -1e9) - mx[:, None]), 0), 1) + 1e-300)
        cs_usd = np.where(finite.any(1), logsum / -self.beta_c, np.nan)
        # Inlets
        ent = np.zeros((len(w.inlets), H)); left = np.zeros((len(w.inlets), H))
        rail = set(w.rail_inlets)
        for L in legs.all():
            if L.get("inlet_in", -1) >= 0:
                ent[L["inlet_in"], min(23, int(L["t"] // 3600))] += S
            if L.get("inlet_out", -1) >= 0:
                left[L["inlet_out"], min(23, int(L["t"] // 3600))] += S
        # By income tier
        by_income = {}
        for t, name in enumerate(TIERS):
            m = (pop.tier == t) & np.isin(pop.kind, [WORKER, RESIDENT])
            mw = m & (pop.kind == WORKER) & ~self.gone
            travel = np.where(self.mode == CAR, self.car_in_min + np.array([REGIONS[r]["car_min"] for r in pop.region]),
                              np.array([REGIONS[r]["tr_min"] for r in pop.region]) + active_min)
            by_income[name] = {"people": int(m.sum() * S), "travel_min": float(np.nanmean(np.where(np.isfinite(travel[mw]), travel[mw], np.nan))) if mw.any() else 0.0,
                               "walk_min": float(active_min[m].mean()) if m.any() else 0.0,
                               "car_share": float(np.mean(drive[mw])) if mw.any() else 0.0}
        # Blocks
        nb = w.n_blocks
        blk = {"jobs": np.zeros(nb), "residents": np.zeros(nb), "visits": np.zeros(nb), "revenue": np.zeros(nb)}
        np.add.at(blk["jobs"], w.block_of, (off + oth)); np.add.at(blk["residents"], w.block_of, resc)
        okp = self.PO.bld >= 0
        np.add.at(blk["visits"], w.block_of[self.PO.bld[okp]], visits_day[okp]); np.add.at(blk["revenue"], w.block_of[self.PO.bld[okp]], revenue_day[okp])
        # Market Street transit proxy (buses share lanes with cars on parts of Market)
        mk = np.array([n == "Market Street" for n in w.edge_name]) & w.edge_car
        am_c = cong[8]
        bus_share = P["bus_mixed_traffic_share"]
        market_bus_idx = float((w.edge_len[mk] * (1 + bus_share * (am_c[mk] - 1))).sum() / max(w.edge_len[mk].sum(), 1)) if mk.any() else 1.0

        trips_people = {"car": 0, "transit": 0, "walk": 0, "bike": 0, "gone": 0}
        commuters = {k: 0 for k in trips_people}
        for k, i in (("car", CAR), ("transit", TRANSIT), ("walk", WALK), ("bike", BIKE)):
            commuters[k] = int(((self.mode == i) & ~self.gone & wk).sum() * S)
        commuters["gone"] = int((self.gone & wk).sum() * S)
        n_walk_legs = sum(1 for L in legs.walks if L["mode"] == "walk")
        n_bike_legs = sum(1 for L in legs.walks if L["mode"] == "bike")
        trips_people["car"] = int(len(legs.cars) * S)
        trips_people["walk"] = int(n_walk_legs * S); trips_people["bike"] = int(n_bike_legs * S)
        trips_people["transit"] = int(commuters["transit"] * 2 + sum(1 for L in legs.walks if L["purpose"].startswith("commute") and L.get("inlet_in", -1) in rail and pop.kind[L["row"]] == RESIDENT) * S)
        trips_people["gone"] = int(self.gone.sum() * S)
        co2 = (vmt_in * (1 + bg) + vmt_out) * P["co2_kg_per_vmt"] / 1000
        people = int((~self.gone & (pop.kind != THROUGH)).sum() * S)
        metrics = {
            "people": people, "agents": int(self.n), "scale": S,
            "trips": trips_people, "commuters": commuters,
            "vmt": vmt_in, "vmt_total": vmt_in * (1 + bg) + vmt_out, "veh_hours": veh_h, "delay_hours": veh_h - free_h,
            "delay_hours_total": (veh_h - free_h) * (1 + bg),
            "walk_minutes": float((walk_m / P["walking_speed_m_s"] / 60).sum() * S), "active_minutes_per_person": float(active_min[people_mask].mean()) if people_mask.any() else 0.0,
            "ped_trips": int(n_walk_legs * S), "visits": float(visits_day.sum()), "revenue": float(revenue_day.sum()),
            "encounters": float(enc), "new_ties": float(new_ties), "ties": float(len(tie_pairs)), "neighbor_ties": neighbor_ties,
            "jobs": jobs, "residents": residents, "jobs_housing_ratio": jobs / max(residents / P["sf_persons_per_household"], 1),
            "floor_delta_m2": float(floor_delta), "access_15min": access, "co2_tonnes": float(co2),
            "deaths_averted_per_yr": deaths_averted, "rent_pressure_index": 0.0,
            "market_bus_time_index": market_bus_idx,
            "charges_paid_usd": float(((self.charge + 2 * self.fx.car_cost_usd + self._inlet_tolls()) * (drive & (pop.kind == WORKER))).sum() * S / CAR_OCCUPANCY),
            # Plugin charges paid by through-traffic: reported only. Through drivers are valued on time alone, so
            # counting this as city revenue would book a transfer as a gain.
            "through_charges_paid_usd": float((self.fx.car_cost_usd * (drive & (pop.kind == THROUGH))).sum() * S),
            "walker_visits_per_day": float(walker_v), "driver_visits_per_day": float(driver_v),
            "by_income": by_income,
        }
        return {
            "metrics": metrics,
            "_state": {"cong": cong, "car_in_min_by_id": {int(i): float(v) for i, v, m in zip(pop.id, self.car_in_min, drive) if np.isfinite(v)},
                       "through_min_by_id": {int(pop.id[i]): float(self.through_time[i] / 60) for i in np.where(pop.kind == THROUGH)[0] if np.isfinite(self.through_time[i])},
                       "cs_by_id": {int(i): float(c) for i, c, k in zip(pop.id, cs_usd, pop.kind) if k == WORKER and np.isfinite(c)},
                       "pop": pop, "mode": self.mode.copy(), "gone": self.gone.copy(), "legs": legs, "visits": visits,
                       "ped_hour": ped_hour, "bike_hour": bike_hour, "walk_m": walk_m, "active_min": active_min, "bg": bg,
                       "tie_pairs": tie_pairs, "closed": sorted(self.closed), "ctx": self, "logsum_usd": cs_usd,
                       "deaths_averted": deaths_averted, "neighbor_ties": neighbor_ties},
            "edges": {"car_day": car_hour.sum(0) * (1 + bg), "car_agents_day": car_hour.sum(0), "ped_day": ped_hour.sum(0), "bike_day": bike_hour.sum(0),
                      "congestion_am": cong[8], "congestion_pm": cong[17], "car_hour": car_hour * (1 + bg), "ped_hour": ped_hour},
            "pois": {"visits_day": visits_day[:w.P], "revenue_day": revenue_day[:w.P], "visits_hour": visits_hour[:, :w.P], "walkby_day": walkby_hour.sum(0)[:w.P]},
            "virtual_pois": [{"id": int(self.PO.ids[j]), "name": self.PO.names[j], "category": str(self.PO.cat[j]), "x": float(self.PO.xy[j][0]), "z": float(self.PO.xy[j][1]),
                              "building": int(self.PO.bld[j]), "visits_day": float(visits_day[j]), "revenue_day": float(revenue_day[j])} for j in range(w.P, NP)],
            "blocks": blk,
            "inlets": [{"i": i, "entered_hour": ent[i], "left_hour": left[i], "entered": float(ent[i].sum()), "left": float(left[i].sum())} for i in range(len(w.inlets))],
            "ties_sample": [{"a": a, "b": b, "poi": q, "t": t} for (a, b, q, t) in tie_pairs],
        }

    def _home_edges(self, blds):
        w = self.e.w
        if not hasattr(self.e, "_home_edge_cache"):
            self.e._home_edge_cache = {}
        cache = self.e._home_edge_cache
        out = np.full(len(blds), -1)
        for k, b in enumerate(blds):
            b = int(b)
            if b not in cache:
                x, z = w.bld_c[b]
                cache[b] = w.nearest_edge(x, z, 60)
            e = cache[b]
            out[k] = e if e >= 0 and w.edge_car[e] else -1
        return out

    def _access(self, res_rows):
        """Share of residents with food, café, shop, park and a station within a 15-minute (1.2 km) walk."""
        w, wk, pop = self.e.w, self.walk, self.pop
        if not len(res_rows):
            return 0.0
        homes = self.ped_node[res_rows]
        ok = homes >= 0
        if not ok.any():
            return 0.0
        L = wk.len_m
        groups = []
        for cats in (("restaurant", "fast_food"), ("cafe",), ("shop",)):
            nodes = w.poi_node[np.isin(w.poi_cat, cats) & (w.poi_node >= 0)]
            groups.append(np.unique(nodes))
        parks = []
        for pk in w.raw.get("parks", []):
            c = pk.get("c") or (pk.get("p") or [[0, 0]])[0]
            n = w.nearest_node(c[0], c[1], w.ped_main)
            if n >= 0:
                parks.append(n)
        groups.append(np.unique(parks) if parks else np.array([], int))
        groups.append(np.unique([s for i in w.rail_inlets for s in w.inlets[i]["nodes"]]))
        hn = homes[ok]
        allok = np.ones(len(hn), bool)
        for g in groups:
            if not len(g):
                continue
            allok &= (L[np.ix_(hn, g)] <= 1200).any(1)
        return float(allok.mean())


class Legs:
    """Collects agent legs. Car legs are resolved to paths later (sample only); walk legs carry edges."""

    def __init__(self):
        self.walks, self.cars, self.marks = [], [], []
        self.ctx = None

    def bind(self, ctx):
        self.ctx = ctx

    def walk(self, row, purpose, t, o, d, poi=-1, dwell=0.0, inlet_in=-1, inlet_out=-1, mode="walk"):
        ctx = self.ctx
        if o < 0 or d < 0:
            return None
        if mode == "bike":
            k = int(ctx.pop.id[row]) % 3
            edges, rev = ctx.walk.bike_edges(o, d, k) if o in ctx.e.gate_ped.values() else ctx.walk.bike_edges(d, o, k)
            if o not in ctx.e.gate_ped.values():
                edges, rev = edges[::-1], 1 - rev[::-1]
            speed = ctx.e.P["bike_speed_m_s"]
        else:
            edges, rev = ctx.walk.edges(o, d)
            speed = ctx.e.P["walking_speed_m_s"]
        length = float(ctx.e.w.edge_len[edges].sum()) if len(edges) else 0.0
        dur = length / speed
        self.walks.append({"row": row, "purpose": purpose, "t": float(t), "dur": dur, "edges": edges, "rev": rev, "len": length,
                           "poi": int(poi), "dwell": float(dwell), "inlet_in": int(inlet_in), "inlet_out": int(inlet_out), "mode": mode})
        return dur

    def car(self, row, purpose, t, inlet_in, inlet_out, am=True, through=False, visitor_node=False):
        self.cars.append({"row": row, "purpose": purpose, "t": float(t), "inlet_in": int(inlet_in), "inlet_out": int(inlet_out),
                          "am": am, "through": through, "visitor": visitor_node, "mode": "car"})

    def mark_arrival(self, row, t, inlet):
        self.marks.append({"row": row, "purpose": "arrive", "t": float(t), "inlet_in": int(inlet), "inlet_out": -1, "mode": "transit"})

    def mark_departure(self, row, t, inlet):
        self.marks.append({"row": row, "purpose": "depart", "t": float(t), "inlet_in": -1, "inlet_out": int(inlet), "mode": "transit"})

    def all(self):
        return self.walks + self.cars + self.marks
