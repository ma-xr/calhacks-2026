"""Synthetic population: workers (LODES jobs × office occupancy), residents (units × household size),
visitors and through-traffic. Agents are stored column-wise in numpy arrays. Baseline and plans
share the same base agents (common random numbers), so differences are effects, not noise."""
import math

import numpy as np

WORKER, RESIDENT, VISITOR, THROUGH = 0, 1, 2, 3
KIND_NAMES = ["worker", "resident", "visitor", "through"]
TIERS = ["low", "mid", "high"]
MODES = ["car", "transit", "walk", "bike"]
SQM_PER_SQFT = 0.0929
M2_PER_UNIT = 80.0

# Home regions: which inlet they use and what the part of the trip outside our map costs.
# car_min / tr_min: minutes outside the map; walk_m: walking distance outside the map (None = not walkable).
REGIONS = [
    {"key": "east_bay", "name": "East Bay", "car": "i80", "bart": "emb", "car_min": 32, "tr_min": 30, "fare": "east_bay", "toll": True, "miles": 12, "walk_m": None, "bike_m": None},
    {"key": "peninsula_south_bay", "name": "Peninsula", "car": "us101", "bart": "mont", "car_min": 38, "tr_min": 46, "fare": "peninsula", "toll": False, "miles": 20, "walk_m": None, "bike_m": None},
    {"key": "sf_west", "name": "Western SF", "car": "mkt", "bart": "pow", "car_min": 18, "tr_min": 24, "fare": "sf", "toll": False, "miles": 4, "walk_m": None, "bike_m": 4500},
    {"key": "sf_southeast_mission", "name": "Mission", "car": "fol", "bart": "pow", "car_min": 14, "tr_min": 19, "fare": "sf", "toll": False, "miles": 3, "walk_m": 2600, "bike_m": 2800},
    {"key": "sf_north", "name": "North Beach", "car": "bwy", "bart": "mont", "car_min": 10, "tr_min": 17, "fare": "sf", "toll": False, "miles": 2, "walk_m": 1300, "bike_m": 1500},
    {"key": "north_bay", "name": "North Bay", "car": "bwy", "bart": "emb", "car_min": 40, "tr_min": 45, "fare": "north_bay", "toll": True, "miles": 18, "walk_m": None, "bike_m": None},
    {"key": "sf_in_area", "name": "Downtown resident", "car": "fol", "bart": "mont", "car_min": 0, "tr_min": 6, "fare": "sf", "toll": False, "miles": 0, "walk_m": 0, "bike_m": 0},
    {"key": "other", "name": "Elsewhere", "car": "i80", "bart": "emb", "car_min": 45, "tr_min": 50, "fare": "east_bay", "toll": True, "miles": 25, "walk_m": None, "bike_m": None},
]
REGION_IDX = {r["key"]: i for i, r in enumerate(REGIONS)}
FALLBACK_REGION_SHARE = {"east_bay": .30, "peninsula_south_bay": .20, "sf_west": .18, "sf_southeast_mission": .12,
                         "sf_north": .08, "north_bay": .05, "sf_in_area": .03, "other": .04}
FIRST = ['Maria', 'Dev', 'Ana', 'James', 'Wei', 'Priya', 'Luis', 'Sam', 'Grace', 'Omar', 'Hana', 'Tom', 'Rosa', 'Kenji', 'Aisha', 'Ben', 'Lena', 'Marco', 'Nia', 'Raj', 'Elena', 'Chris', 'Mei', 'Jorge', 'Sofia', 'Andre', 'Yuki', 'Dana', 'Ivan', 'Leah']
LAST = ['Okafor', 'Patel', 'Nguyen', 'Garcia', 'Chen', 'Kim', 'Rossi', 'Lopez', 'Wright', 'Haddad', 'Sato', 'Murphy', 'Silva', 'Cohen', 'Diaz', 'Park', 'Reyes', 'Ali', 'Lee', 'Novak']


NAME_OVERRIDES = {}  # demo heroes (set by the API at startup)


def agent_name(aid):
    if aid in NAME_OVERRIDES:
        return NAME_OVERRIDES[aid]
    h = (aid * 2654435761) & 0xffffffff
    return f"{FIRST[h % len(FIRST)]} {LAST[(h // 31) % len(LAST)][0]}."


# ───────────────────────── capacities ─────────────────────────
def zone_template(zone, floor_m2, P):
    """Jobs (office, other) and residents a building of this zone and floor area holds."""
    off_m2 = P["office_sqft_per_job"] * SQM_PER_SQFT
    ret_m2 = P["retail_sqft_per_job"] * SQM_PER_SQFT
    pph = P["sf_persons_per_household"]
    if zone == "park":  # open space: the building is gone
        return 0.0, 0.0, 0.0
    if zone == "office":
        return floor_m2 * .92 / off_m2, floor_m2 * .08 / ret_m2, 0.0
    if zone == "retail":
        return 0.0, floor_m2 / ret_m2, 0.0
    if zone == "res":
        return 0.0, floor_m2 * .05 / ret_m2, floor_m2 * .9 / M2_PER_UNIT * pph
    # mixed: ground-floor retail, offices, homes above
    return floor_m2 * .35 / off_m2, floor_m2 * .12 / ret_m2, floor_m2 * .5 / M2_PER_UNIT * pph


def base_capacity(world, P, inputs):
    """Per building: office jobs, other jobs and residents (people), before occupancy."""
    B = world.B
    off, oth, res = np.zeros(B), np.zeros(B), np.zeros(B)
    lu = inputs.landuse_by_building()
    sqm = SQM_PER_SQFT
    for b in range(B):
        if not world.bld_inside[b]:
            continue
        r = lu.get(b) if lu else None
        if r:
            o = (r.get("office_sqft") or 0) * sqm
            rt = (r.get("retail_sqft") or 0) * sqm
            ht = (r.get("hotel_sqft") or 0) * sqm
            ot = (r.get("other_sqft") or 0) * sqm
            units = r.get("res_units") or 0
            if o + rt + ht + ot + units > 0:
                off[b] = o / (P["office_sqft_per_job"] * sqm)
                oth[b] = rt / (P["retail_sqft_per_job"] * sqm) + ht / (P["hotel_sqft_per_job"] * sqm) + ot / (P["other_sqft_per_job"] * sqm)
                res[b] = units * P["sf_persons_per_household"]
                continue
        k, fa = world.bld_kind[b], world.bld_floor_area[b]
        if k == "office":
            o, t, r_ = zone_template("office", fa, P)
        elif k == "res":
            o, t, r_ = zone_template("res", fa, P)
        elif k in ("retail",):
            o, t, r_ = zone_template("retail", fa, P)
        elif k == "hotel":
            o, t, r_ = 0.0, fa / (P["hotel_sqft_per_job"] * sqm), 0.0
        elif k == "civic":
            o, t, r_ = 0.0, fa / (P["other_sqft_per_job"] * sqm), 0.0
        elif k == "parking":
            o, t, r_ = 0.0, 0.0, 0.0
        else:  # OSM "mixed"/untagged: towers are mostly offices, low-rise SoMa is mixed
            o, t, r_ = zone_template("office" if world.bld_h[b] > 45 else "mixed", fa, P)
        off[b], oth[b], res[b] = o, t, r_
    # Office space is partly vacant.
    off *= (1 - P["fidi_office_vacancy_rate"])
    # Control totals: LODES jobs located in the area; ACS population of the tracts in the area.
    jt = inputs.jobs_total()
    if jt:
        k = jt / max(off.sum() + oth.sum(), 1)
        off *= k; oth *= k
    rt = inputs.residents_total()
    if rt:
        res *= rt / max(res.sum(), 1)
    return off, oth, res


def edited_capacity(world, P, base, edits):
    off, oth, res = (a.copy() for a in base)
    for b, ed in edits.get("blocks", {}).items():
        b = int(b)
        if b < 0 or b >= world.B or not world.bld_inside[b]:
            continue
        s = float(ed.get("scale", 1.0))
        z = ed.get("zone")
        if z:
            o, t, r = zone_template(z, world.bld_floor_area[b] * s, P)
            off[b], oth[b], res[b] = o * (1 - P["fidi_office_vacancy_rate"] * .5), t, r
        else:
            off[b] *= s; oth[b] *= s; res[b] *= s
    return off, oth, res


# ───────────────────────── population ─────────────────────────
class Population:
    """Column store. Arrays are aligned by row; `id` is the stable agent id."""
    FIELDS = ["id", "kind", "bld", "region", "tier", "car", "arrive", "leave", "lunch", "lunch_t", "lunch_dur",
              "coffee", "coffee_t", "errand", "errand_t", "evening", "eve_t", "eve_dur", "commute_out", "open",
              "u_gone", "u_reloc", "in_inlet", "out_inlet", "eps"]

    def __init__(self, **cols):
        for k in self.FIELDS:
            setattr(self, k, cols[k])
        self.n = len(self.id)

    def take(self, mask):
        return Population(**{k: getattr(self, k)[mask] for k in self.FIELDS})

    @staticmethod
    def concat(a, b):
        return Population(**{k: np.concatenate([getattr(a, k), getattr(b, k)]) for k in Population.FIELDS})


def inlet_capacity(g, P):
    """Vehicles per hour a car inlet can carry: lanes × per-lane capacity of its road class."""
    return float(g.get("lanes") or 1) * P["lane_capacity_vph"].get(g.get("cls"), 600)


def inlet_penalty_s(g, P):
    return 60.0 * P["inlet_class_penalty_min"].get(g.get("cls"), 2.5)


def through_eligible(g, P):
    """Surface inlets through-traffic may use: not freeways, class penalty within the limit."""
    return (g["mode"] == "car" and not str(g.get("cls", "")).startswith("motorway")
            and P["inlet_class_penalty_min"].get(g.get("cls"), 2.5) <= P["through_inlet_max_penalty_min"])


def _clip_normal(rng, n, mu, sd, lo, hi):
    return np.clip(rng.normal(mu, sd, n), lo, hi)


def _alloc(weights, total, rng):
    """Deterministic integer allocation of `total` agents across buildings (largest remainder)."""
    w = np.maximum(weights, 0)
    if w.sum() <= 0 or total <= 0:
        return np.zeros(len(w), int)
    exact = w / w.sum() * total
    n = np.floor(exact).astype(int)
    rem = int(total - n.sum())
    if rem > 0:
        frac = exact - n + rng.random(len(w)) * 1e-6
        n[np.argsort(-frac)[:rem]] += 1
    return n


class PopulationBuilder:
    def __init__(self, world, P, inputs):
        self.w, self.P, self.inputs = world, P, inputs
        self.base_cap = base_capacity(world, P, inputs)
        off, oth, res = self.base_cap
        present = off * P["sf_office_occupancy_rate"] + oth * P["nonoffice_attendance_rate"]
        self.present_workers = float(present.sum())
        self.residents = float(res.sum())
        self.scale = max(1, int(round(self.present_workers / P["target_worker_agents"])))
        self.region_share = inputs.home_region_share() or FALLBACK_REGION_SHARE
        self.region_share_by_tier = self._tier_region_share()
        self.tier_share = inputs.earnings_share() or {"low": .14, "mid": .21, "high": .65}
        self.base = self._build_base()

    def _tier_region_share(self):
        by = self.inputs.home_region_share_by_earnings()
        if not by:
            return None
        key = {"SE01": "low", "SE02": "mid", "SE03": "high", "low": "low", "mid": "mid", "high": "high"}
        return {key[k]: v for k, v in by.items() if k in key}

    def _region_probs(self, tier):
        sh = (self.region_share_by_tier or {}).get(tier) or self.region_share
        p = np.array([sh.get(r["key"], 0.0) for r in REGIONS], float)
        # By-earnings shares include far-away "homes" (HQ reporting); shrink "other" to the filtered level.
        full, excl = (self.inputs.lodes or {}).get("home_region_share"), (self.inputs.lodes or {}).get("home_region_share_excl_far")
        if full and excl and full.get("other"):
            p[REGION_IDX["other"]] *= excl["other"] / full["other"]
        return p / p.sum()

    # Shared attribute sampler for a batch of workers (ids fixed by caller).
    def _workers(self, ids, blds, rng, office_frac):
        n = len(ids)
        P = self.P
        tiers = rng.choice(3, n, p=[self.tier_share[t] for t in TIERS])
        region = np.zeros(n, int)
        for t in range(3):
            m = tiers == t
            region[m] = rng.choice(len(REGIONS), m.sum(), p=self._region_probs(TIERS[t]))
        car_av = rng.random(n) < np.array([P["car_availability_by_income"][TIERS[t]] for t in tiers])
        # Office workers arrive ~8:45 ± 50 min; retail/hotel staff are spread wider and later.
        is_off = rng.random(n) < office_frac
        arrive = np.where(is_off, _clip_normal(rng, n, 525, 48, 390, 690), _clip_normal(rng, n, 570, 110, 360, 840)) * 60
        hours = np.where(is_off, _clip_normal(rng, n, 8.6, .9, 6, 11), _clip_normal(rng, n, 8.0, 1.2, 4, 11)) * 3600
        return dict(
            id=ids, kind=np.full(n, WORKER), bld=blds, region=region, tier=tiers, car=car_av,
            arrive=arrive, leave=np.minimum(arrive + hours, 23.5 * 3600),
            lunch=rng.random(n) < P["lunch_out_share_office_workers"], lunch_t=_clip_normal(rng, n, 742, 26, 680, 840) * 60,
            lunch_dur=(18 + rng.random(n) * 30) * 60,
            coffee=rng.random(n) < P["coffee_trip_share"], coffee_t=(855 + rng.random(n) * 90) * 60,
            errand=rng.random(n) < .12, errand_t=_clip_normal(rng, n, 1060, 30, 980, 1150) * 60,
            evening=rng.random(n) < .18, eve_t=_clip_normal(rng, n, 1070, 25, 1020, 1140) * 60, eve_dur=(35 + rng.random(n) * 50) * 60,
            commute_out=np.zeros(n, bool), open=rng.random(n), u_gone=rng.random(n), u_reloc=rng.random(n),
            in_inlet=np.full(n, -1), out_inlet=np.full(n, -1), eps=rng.gumbel(size=(n, 4)),
        )

    def _residents(self, ids, blds, rng):
        n = len(ids)
        tiers = rng.choice(3, n, p=[.32, .30, .38])
        car_av = rng.random(n) < np.array([.35, .5, .65])[tiers]
        return dict(
            id=ids, kind=np.full(n, RESIDENT), bld=blds, region=np.full(n, REGION_IDX["sf_in_area"]), tier=tiers, car=car_av,
            arrive=_clip_normal(rng, n, 1100, 50, 960, 1260) * 60, leave=_clip_normal(rng, n, 470, 40, 400, 560) * 60,
            lunch=np.zeros(n, bool), lunch_t=np.zeros(n), lunch_dur=np.zeros(n),
            coffee=rng.random(n) < .25, coffee_t=(540 + rng.random(n) * 240) * 60,
            errand=rng.random(n) < .55, errand_t=(600 + rng.random(n) * 420) * 60,
            evening=rng.random(n) < .45, eve_t=(1110 + rng.random(n) * 150) * 60, eve_dur=(40 + rng.random(n) * 60) * 60,
            commute_out=rng.random(n) < .32, open=rng.random(n), u_gone=rng.random(n), u_reloc=rng.random(n),
            in_inlet=np.full(n, -1), out_inlet=np.full(n, -1), eps=rng.gumbel(size=(n, 4)),
        )

    def _build_base(self):
        P, w = self.P, self.w
        rng = np.random.default_rng(2026)
        off, oth, res = self.base_cap
        present = off * P["sf_office_occupancy_rate"] + oth * P["nonoffice_attendance_rate"]
        nw = int(round(self.present_workers / self.scale))
        per_b = _alloc(present * (w.bld_ped_node >= 0) * (w.bld_car_node >= 0), nw, rng)
        blds = np.repeat(np.arange(w.B), per_b)
        office_frac = np.repeat(np.where(present > 0, off * P["sf_office_occupancy_rate"] / np.maximum(present, 1e-9), 0), per_b)
        cols = self._workers(np.arange(len(blds)), blds, rng, office_frac)
        workers = Population(**cols)
        nr = int(round(self.residents / self.scale))
        per_r = _alloc(res * (w.bld_ped_node >= 0), nr, rng)
        rb = np.repeat(np.arange(w.B), per_r)
        residents = Population(**self._residents(np.arange(len(rb)) + 60000, rb, rng))
        visitors = self._visitors(rng)
        through = self._through(rng)
        return Population.concat(Population.concat(workers, residents), Population.concat(visitors, through))

    def _visitors(self, rng):
        """Daytime shoppers/tourists, plus evening diners and bar-goers coming into the area."""
        P, w = self.P, self.w
        # Visitors driving in arrive over every car inlet with entries, in proportion to its lane capacity.
        cars = [g for g in w.inlets if g["mode"] == "car" and g["entries"]]
        car_ids = [g["i"] for g in cars]
        cap = np.array([inlet_capacity(g, P) for g in cars], float)
        car_p = cap / cap.sum()
        parts = []
        for seg, total, base_id in (("day", P["visitors_per_day"], 80000), ("evening", P["evening_visitors_per_day"], 86000)):
            n = int(round(total / self.scale))
            ids = np.arange(n) + base_id
            transit = rng.random(n) < (.65 if seg == "day" else .55)
            bart = rng.choice([w.inlet_by_key[k]["i"] for k in ("emb", "mont", "pow")], n, p=[.2, .3, .5])
            car_in = rng.choice(car_ids, n, p=car_p)
            inlet = np.where(transit, bart, car_in)
            if seg == "day":
                arrive = _clip_normal(rng, n, 760, 120, 600, 1080) * 60
                leave = arrive + (90 + rng.random(n) * 150) * 60
                lunch, errand, evening = rng.random(n) < .6, np.ones(n, bool), np.zeros(n, bool)
                eve_t, eve_dur = np.zeros(n), np.zeros(n)
            else:
                arrive = _clip_normal(rng, n, 1125, 45, 1050, 1260) * 60
                eve_dur = (60 + rng.random(n) * 90) * 60
                eve_t = arrive + 600
                leave = eve_t + eve_dur + 600
                lunch, errand, evening = np.zeros(n, bool), np.zeros(n, bool), np.ones(n, bool)
            parts.append(Population(
                id=ids, kind=np.full(n, VISITOR), bld=np.full(n, -1), region=np.full(n, REGION_IDX["other"]), tier=rng.choice(3, n, p=[.25, .4, .35]),
                car=~transit, arrive=arrive, leave=leave,
                lunch=lunch, lunch_t=arrive + (30 + rng.random(n) * 60) * 60, lunch_dur=(30 + rng.random(n) * 30) * 60,
                coffee=(rng.random(n) < .3) & (seg == "day"), coffee_t=arrive + (10 + rng.random(n) * 30) * 60,
                errand=errand, errand_t=arrive + (5 + rng.random(n) * 20) * 60,
                evening=evening, eve_t=eve_t, eve_dur=eve_dur,
                commute_out=np.zeros(n, bool), open=rng.random(n), u_gone=rng.random(n), u_reloc=rng.random(n),
                in_inlet=inlet, out_inlet=inlet, eps=rng.gumbel(size=(n, 4))))
        return Population.concat(*parts)

    def _through(self, rng):
        P = self.P
        n = int(round(P["through_vehicles_per_day"] / self.scale))
        ids = np.arange(n) + 90000
        # Through-trips run between two different sides of the map, weighted by the lane capacity of each
        # side's eligible inlets. The engine routes each trip from the cheapest inlet on its origin side to the
        # cheapest on its destination side; in_inlet/out_inlet only record the main inlet of each side.
        w = self.w
        sides = ["north", "east", "south", "west"]
        elig = [g for g in w.inlets if through_eligible(g, P)]
        w_in = {sd: sum(inlet_capacity(g, P) for g in elig if g["side"] == sd and g["entries"]) for sd in sides}
        w_out = {sd: sum(inlet_capacity(g, P) for g in elig if g["side"] == sd and g["exits"]) for sd in sides}
        pairs = [(a, b) for a in sides for b in sides if a != b and w_in[a] > 0 and w_out[b] > 0]
        pw = np.array([w_in[a] * w_out[b] for a, b in pairs], float)
        k = rng.choice(len(pairs), n, p=pw / pw.sum())

        def main_inlet(sd, key):
            return max((g for g in elig if g["side"] == sd and g[key]), key=lambda g: inlet_capacity(g, P))["i"]
        rep_in = {sd: main_inlet(sd, "entries") for sd in sides if w_in[sd] > 0}
        rep_out = {sd: main_inlet(sd, "exits") for sd in sides if w_out[sd] > 0}
        pairs = [(rep_in[a], rep_out[b]) for a, b in pairs]
        hour_w = np.array([.2, .1, .1, .1, .3, .9, 2.4, 4.6, 5.6, 4.4, 3.6, 3.6, 3.8, 3.8, 4.0, 4.6, 5.4, 6.0, 5.2, 3.6, 2.6, 2.0, 1.4, .8])
        hrs = rng.choice(24, n, p=hour_w / hour_w.sum())
        t = (hrs + rng.random(n)) * 3600
        cols = dict(
            id=ids, kind=np.full(n, THROUGH), bld=np.full(n, -1), region=np.full(n, REGION_IDX["other"]), tier=rng.choice(3, n, p=[.3, .4, .3]),
            car=np.ones(n, bool), arrive=t, leave=t, lunch=np.zeros(n, bool), lunch_t=np.zeros(n), lunch_dur=np.zeros(n),
            coffee=np.zeros(n, bool), coffee_t=np.zeros(n), errand=np.zeros(n, bool), errand_t=np.zeros(n),
            evening=np.zeros(n, bool), eve_t=np.zeros(n), eve_dur=np.zeros(n), commute_out=np.zeros(n, bool),
            open=np.zeros(n), u_gone=rng.random(n), u_reloc=rng.random(n),
            in_inlet=np.array([pairs[i][0] for i in k]), out_inlet=np.array([pairs[i][1] for i in k]), eps=rng.gumbel(size=(n, 4)),
        )
        return Population(**cols)

    # ── plan population: base agents kept or removed per building, new agents appended ──
    def for_edits(self, edits):
        if not edits.get("blocks"):
            return self.base
        P, w = self.P, self.w
        off0, oth0, res0 = self.base_cap
        off1, oth1, res1 = edited_capacity(w, P, self.base_cap, edits)
        pres0 = off0 * P["sf_office_occupancy_rate"] + oth0 * P["nonoffice_attendance_rate"]
        pres1 = off1 * P["sf_office_occupancy_rate"] + oth1 * P["nonoffice_attendance_rate"]
        base = self.base
        keep = np.ones(base.n, bool)
        extra = []
        for b in {int(k) for k in edits["blocks"]}:
            if b < 0 or b >= w.B:
                continue
            for kind, c0, c1, id0 in ((WORKER, pres0[b], pres1[b], 100000), (RESIDENT, res0[b], res1[b], 200000)):
                rows = np.where((base.bld == b) & (base.kind == kind))[0]
                n1 = int(round(c1 / self.scale))
                if n1 < len(rows):
                    # Drop the agents with the highest u_reloc first (deterministic).
                    drop = rows[np.argsort(-base.u_reloc[rows])[:len(rows) - n1]]
                    keep[drop] = False
                elif n1 > len(rows):
                    k = min(n1 - len(rows), 399)
                    rng = np.random.default_rng(b * 31 + 7 + kind)
                    ids = id0 + b * 400 + np.arange(k)
                    blds = np.full(k, b)
                    cols = self._workers(ids, blds, rng, np.full(k, .7)) if kind == WORKER else self._residents(ids, blds, rng)
                    extra.append(Population(**cols))
        pop = base.take(keep)
        for e in extra:
            pop = Population.concat(pop, e)
        return pop
