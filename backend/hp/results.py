"""Turn engine results into the API's ScenarioResult: deltas vs baseline, $ valuation, trip samples and
agent diaries. See docs/contracts/sim-api.md."""
import math

import numpy as np

from .engine import CAR, TRANSIT, WALK, BIKE, hash_uniform
from .population import KIND_NAMES, REGIONS, THROUGH, TIERS, WORKER, RESIDENT, VISITOR, agent_name

MODE_NAMES = ["car", "transit", "walk", "bike"]


def _round(x, nd=2):
    if isinstance(x, (float, np.floating)):
        if not math.isfinite(x):
            return None
        return round(float(x), nd)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, dict):
        return {k: _round(v, nd) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round(v, nd) for v in x]
    if isinstance(x, np.ndarray):
        return _round(x.tolist(), nd)
    return x


def delta(a, b):
    """b - a for nested numeric dicts."""
    if isinstance(a, dict):
        return {k: delta(a.get(k), b.get(k)) for k in b if k in a}
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return b - a
    return None


def valuation(P, base, plan):
    """$ per year vs baseline by pillar, with every line itemized."""
    bm, pm = base["metrics"], plan["metrics"]
    bs, ps = base["_state"], plan["_state"]
    D = P["workdays_per_year"]
    vot = P["vot_personal_usd_per_hr"]
    S = pm["scale"]
    lines = []

    def line(pillar, label, qty, unit, usd):
        lines.append({"pillar": pillar, "label": label, "qty": qty, "unit": unit, "usd_per_yr": usd})
        return usd

    # Mobility: commuter consumer surplus (logit log-sum, 2 trips/day), through traffic, background traffic.
    cs_b, cs_p = bs["cs_by_id"], ps["cs_by_id"]
    common = [i for i in cs_p if i in cs_b]
    dcs = sum(cs_p[i] - cs_b[i] for i in common) * 2 * S
    mob = line("mobility", "Commuter time & cost (logit consumer surplus)", dcs, "$/day", dcs * D)
    tb, tp = bs["through_min_by_id"], ps["through_min_by_id"]
    dthr_min = sum(tp.get(i, tb[i] + P["bypass_penalty_min"]) - tb[i] for i in tb) * S
    mob += line("mobility", "Through-traffic travel time", -dthr_min / 60, "veh-h/day", -dthr_min / 60 * vot * D)
    bg = bs["bg"]
    dbg = (pm["delay_hours"] - bm["delay_hours"]) * bg
    mob += line("mobility", "Delay to other traffic (taxis, freight, buses)", -dbg, "veh-h/day", -dbg * vot * 1.2 * D)
    # Environment
    dco2 = pm["co2_tonnes"] - bm["co2_tonnes"]
    env = line("environment", "CO₂ (social cost of carbon)", -dco2, "t/day", -dco2 * P["scc_usd_per_tonne"] * D)
    # Crash costs and health (WHO HEAT x VSL) are deliberately not monetized: product decision, they dominated the total.
    # deaths_averted_per_yr and walking minutes stay available as plain metrics.
    hea = 0.0
    # Economy
    drev = pm["revenue"] - bm["revenue"]
    eco = line("economy", "Local value added from business revenue (net new share)", drev, "$/day",
               drev * P["retail_value_added_share"] * P.values.get("retail_net_new_share", 0.5) * D)
    eco += line("economy", "City sales-tax revenue", drev, "$/day", drev * P["city_share_of_sales_tax"] * D)
    dch = pm.get("charges_paid_usd", 0) - bm.get("charges_paid_usd", 0)
    eco += line("economy", "Congestion charge / parking revenue to the city (transfer)", dch, "$/day", dch * D)
    fd = pm["floor_delta_m2"]
    eco += line("economy", "Property tax on new floor area", fd, "m²", fd * P.values.get("assessed_value_usd_per_m2", 5000) * P["sf_property_tax_rate"])
    # Social
    dties = pm["new_ties"] - bm["new_ties"]
    soc = line("social", "New acquaintances formed (weak ties)", dties, "ties/yr", dties * P["value_of_weak_tie_usd_per_yr"])
    denc = pm["encounters"] - bm["encounters"]
    soc += line("social", "Chance encounters in shared places", denc, "/day", denc * P["value_per_encounter_usd"] * D)
    dnb = pm["neighbor_ties"] - bm["neighbor_ties"]
    soc += line("social", "Neighbouring on calmer streets (Appleyard)", dnb, "friendships", dnb * P["value_of_weak_tie_usd_per_yr"] * 0.5)
    factors = {k: P[k] for k in ("vot_personal_usd_per_hr", "workdays_per_year", "scc_usd_per_tonne", "crash_cost_usd_per_vmt", "vsl_usd",
                                 "retail_value_added_share", "city_share_of_sales_tax", "sf_property_tax_rate", "value_of_weak_tie_usd_per_yr",
                                 "value_per_encounter_usd", "heat_walk_rr", "co2_kg_per_vmt")}
    return {"mobility": mob, "social": soc, "economy": eco, "health": hea, "environment": env,
            "total": mob + soc + eco + env, "factors": factors, "lines": lines}


def rent_pressure(P, base, plan):
    """% change in rent pressure from foot traffic and access near homes (shown as a trade-off, not monetized)."""
    bp, pp = base["edges"]["ped_day"], plan["edges"]["ped_day"]
    rel = (pp.sum() - bp.sum()) / max(bp.sum(), 1)
    dacc = plan["metrics"]["access_15min"] - base["metrics"]["access_15min"]
    return 100 * P["rent_walkability_elasticity"] * (rel / 0.10 + dacc / 0.10)


# ───────────────────────── trips ─────────────────────────
def leg_steps(ctx, L):
    if L["mode"] in ("walk", "bike"):
        return [int(e) * 2 + int(r) for e, r in zip(L["edges"], L["rev"])]
    return ctx.car_leg_steps(L)


def leg_json(ctx, L):
    w = ctx.e.w
    steps = leg_steps(ctx, L)
    if not steps:
        return None
    pop = ctx.pop
    i = L["row"]
    if L["mode"] == "car":
        dur = float(sum(w.edge_free_s[s >> 1] * ctx.cong[min(23, int(L["t"] // 3600)), s >> 1] for s in steps))
        th, tt = _trim(w, steps)
    else:
        dur = L["dur"]; th = tt = 0
    return {"agent_id": int(pop.id[i]), "mode": "car" if L["mode"] == "car" else ("bike" if L["mode"] == "bike" else "ped"),
            "purpose": L["purpose"], "t_start": round(L["t"], 1), "t_end": round(L["t"] + dur, 1), "steps": steps,
            "trim_head": th, "trim_tail": tt, "poi": int(L.get("poi", -1)), "dwell": round(L.get("dwell", 0.0), 1),
            "inlet_in": int(L.get("inlet_in", -1)), "inlet_out": int(L.get("inlet_out", -1))}


def _trim(w, steps):
    pts = []
    for s in steps:
        p = w.edge_pts[s >> 1]
        p = p[::-1] if s & 1 else p
        pts.extend(p if not pts else p[1:])
    far = lambda q: math.hypot(q[0], q[1]) > 1450
    h = t = 0
    while len(pts) - h - t > 2 and far(pts[h]) and far(pts[h + 1]):
        h += 1
    while len(pts) - h - t > 2 and far(pts[-1 - t]) and far(pts[-2 - t]):
        t += 1
    return h, t


def trip_sample(res, max_trips=4000, must=()):
    st = res["_state"]
    ctx, legs = st["ctx"], st["legs"]
    pop = ctx.pop
    all_legs = [L for L in legs.walks + legs.cars if not L.get("visitor")]
    share = min(1.0, max_trips / max(len(all_legs), 1))
    pick = hash_uniform(pop.id, 17, 23) < share
    must = set(must)
    items = []
    for L in all_legs:
        i = L["row"]
        if pick[i] or int(pop.id[i]) in must:
            j = leg_json(ctx, L)
            if j:
                items.append(j)
    items.sort(key=lambda x: x["t_start"])
    return {"sample_share": round(share, 4), "items": items}


# ───────────────────────── agents ─────────────────────────
def agent_view(res, agent_id, P, poi_names):
    st = res["_state"]
    ctx = st["ctx"]
    pop = ctx.pop
    rows = np.where(pop.id == agent_id)[0]
    if not len(rows):
        return None
    i = int(rows[0])
    legs = [L for L in st["legs"].walks + st["legs"].cars if L["row"] == i]
    legs.sort(key=lambda L: L["t"])
    trips = [j for j in (leg_json(ctx, L) for L in legs) if j]
    mode = "gone" if st["gone"][i] else MODE_NAMES[int(st["mode"][i])]
    diary = []
    for t in trips:
        if t["purpose"] == "commute_in":
            how = {"car": "Drove in", "ped": "Walked in", "bike": "Cycled in"}[t["mode"]]
            g = ctx.e.w.inlets[t["inlet_in"]] if 0 <= t["inlet_in"] < len(ctx.e.w.inlets) else None
            src = (f"from {g['name']} BART" if g["mode"] == "ped" else f"via {g['name']}") if g else ""
            diary.append({"t": t["t_start"], "kind": "arrive", "text": f"{how} {src}".strip()})
        elif t["purpose"] in ("coffee_am", "lunch", "coffee", "errand", "evening", "visit", "visit2", "visit3"):
            label = {"coffee_am": "Morning coffee", "visit": "Shopping", "visit2": "Lunch", "visit3": "Coffee"}.get(t["purpose"], t["purpose"].capitalize())
            diary.append({"t": t["t_end"], "kind": "visit", "poi": t["poi"], "text": f"{label} at {poi_names.get(t['poi'], 'a local spot')}"})
        elif t["purpose"] == "commute_out":
            diary.append({"t": t["t_start"], "kind": "depart", "text": "Headed home"})
    if mode == "gone":
        diary.append({"t": float(pop.arrive[i]), "kind": "leave", "text": "Skipped the drive today (worked from home)"})
    ties = [{"agent_id": b if a == agent_id else a, "name": agent_name(b if a == agent_id else a), "where_poi": q, "t": t}
            for (a, b, q, t) in st["tie_pairs"] if agent_id in (a, b)]
    r = int(pop.region[i])
    probs = None
    if pop.kind[i] == WORKER and getattr(ctx, "V", None) is not None:
        v = np.asarray(ctx.V[i], float)
        ok = np.isfinite(v)
        if ok.any():
            ex = np.where(ok, np.exp(v - v[ok].max()), 0.0)   # multinomial logit over the deterministic utilities
            probs = {MODE_NAMES[k]: round(float(ex[k] / ex.sum()), 3) for k in range(len(v))}
    return {"agent_id": int(agent_id), "name": agent_name(int(agent_id)), "kind": KIND_NAMES[int(pop.kind[i])],
            "income_tier": int(pop.tier[i]), "region": REGIONS[r]["name"], "work_building": int(pop.bld[i]) if pop.kind[i] == WORKER else -1,
            "home_building": int(pop.bld[i]) if pop.kind[i] == RESIDENT else -1, "car_available": bool(pop.car[i]),
            "mode": mode, "mode_probs": probs, "trips": trips, "diary": diary, "ties": ties}


def agents_sample(res, base, must=(), n=40):
    """Hero agents plus agents whose mode changed vs the baseline (for highlights and the citizen feed)."""
    sp, sb = res["_state"], base["_state"]
    pp, pb = sp["pop"], sb["pop"]
    rb = {int(i): k for k, i in enumerate(pb.id)}

    def mode(st, k):
        return "gone" if st["gone"][k] else MODE_NAMES[int(st["mode"][k])]
    out, seen = [], set()
    order = [k for k in range(pp.n) if int(pp.id[k]) in set(must)] + list(range(pp.n))
    for k in order:
        aid = int(pp.id[k])
        if aid in seen or pp.kind[k] == THROUGH:
            continue
        j = rb.get(aid)
        mb = mode(sb, j) if j is not None else None
        mp = mode(sp, k)
        if aid in set(must) or (res is not base and mb != mp):
            seen.add(aid)
            out.append({"agent_id": aid, "name": agent_name(aid), "kind": KIND_NAMES[int(pp.kind[k])], "income_tier": int(pp.tier[k]),
                        "region": REGIONS[int(pp.region[k])]["name"], "baseline_mode": mb, "plan_mode": mp, "new_agent": j is None})
        if len(out) >= n:
            break
    return out


# ───────────────────────── full result ─────────────────────────
def to_json(engine, res, base, lite=False, sample_must=(), max_trips=4000):
    P = engine.P
    m = dict(res["metrics"])
    if res is not base:
        m["rent_pressure_index"] = rent_pressure(P, base, res)
        val = valuation(P, base, res)
    else:
        val = {"mobility": 0.0, "social": 0.0, "economy": 0.0, "health": 0.0, "environment": 0.0, "total": 0.0,
               "factors": {}, "lines": []}
    d = delta(base["metrics"], m)
    E = res["edges"]
    out = {
        "id": res["id"], "name": res.get("name"), "edits": res["edits"], "settle": res["settle"], "cached": res.get("cached", False),
        "metrics": m, "delta": d, "value": val,
        "edges": {"car_day": E["car_day"], "ped_day": E["ped_day"], "bike_day": E["bike_day"],
                  "congestion_am": E["congestion_am"], "congestion_pm": E["congestion_pm"],
                  "car_free": sorted(res["_state"]["closed"])},
        "pois": {"visits_day": res["pois"]["visits_day"], "revenue_day": res["pois"]["revenue_day"], "walkby_day": res["pois"]["walkby_day"]},
        "blocks": res["blocks"],
        "inlets": res["inlets"],
        "ties_sample": res["ties_sample"],
        "assumptions": P.assumptions(),
    }
    if not lite:
        out["edges"]["car_hour"] = E["car_hour"].T
        out["edges"]["ped_hour"] = E["ped_hour"].T
        out["pois"]["visits_hour"] = res["pois"]["visits_hour"].T
        out["trips"] = trip_sample(res, max_trips=max_trips, must=sample_must)
    out["virtual_pois"] = res.get("virtual_pois", [])
    out["agents_sample"] = agents_sample(res, base, must=sample_must)
    return _round(out, 2)
