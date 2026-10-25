"""simq: read-only query CLI over a scenario snapshot (droid/workspace, written by live_export). It is the only
command the Droid live agent may run. Stdlib only, no network, no writes.

    python -m droid.simq [--scenario <sid>] <command> [args]

Commands:
  summary [--time hh:mm]                     headline metrics, deltas vs baseline, value by pillar, edits
  streets [--sort car_delta|ped_delta|car|ped|congestion_am|congestion_pm] [--top N] [--asc]
  edges   [--sort car_delta|ped_delta|car|ped|congestion_am|congestion_pm] [--top N] [--asc] [--hour hh]
  street "<name>"                            per-segment flows and edge ids
  stretch "<name>" "<from>" "<to>"           segments of <name> between two cross streets
  pois [--sort revenue_delta|visits_delta|visits|revenue] [--asc] [--category cafe] [--near x z r] [--top N]
  poi <id|name>
  agent <id|name>                            baseline vs plan day (diary) for exported agents
  agents [--changed] [--from MODE] [--to MODE] [--top N]
  block <id> | blocks [--sort jobs|residents|visits|revenue|revenue_delta|jobs_delta|residents_delta] [--top N] [--asc]
  inlets [--top N] [--sort volume|delta]     rail stations + top car gateways (of ~60) with totals, peak hours
  inlet <key|name|i>                         one inlet: entered/left, by hour vs baseline
  hour <hh:mm>                               car/foot volumes, visits and inlet arrivals in that hour
  value                                      $ value line items vs baseline
  assumptions [--grep text]                  parameters with status assumed/calibrated
  validation                                 model vs observed checks
  find "<text>"                              fuzzy search over streets, POIs, buildings, agents, inlets

Units: car_day = vehicles/day on an edge (incl. background traffic), ped_day = people/day on foot, congestion = travel-time
factor (1 = free flow), revenue/visits per weekday, value $ per year. Coordinates x, z are local meters (world.json)."""
import argparse
import difflib
import json
import sys
from pathlib import Path

WS = Path(__file__).resolve().parent / "workspace"
_cache = {}


def load(name, sid=None):
    p = WS / (sid or "") / name
    if p not in _cache:
        try:
            _cache[p] = json.loads(p.read_text())
        except FileNotFoundError:
            sys.exit(f"error: no snapshot {p.relative_to(WS)} (the API exports it before Droid runs)")
    return _cache[p]


def r(v, nd=1):
    if isinstance(v, float):
        return round(v, nd) if abs(v) < 1e6 else round(v)
    if isinstance(v, dict):
        return {k: r(x, nd) for k, x in v.items()}
    if isinstance(v, list):
        return [r(x, nd) for x in v]
    return v


NOTE = None


def out(obj):
    if NOTE and isinstance(obj, dict):
        obj = {**obj, "scenario_note": NOTE}
    print(json.dumps(r(obj), ensure_ascii=False, separators=(", ", ": ")))


def hh(s):
    s = str(s)
    h = int(s.split(":")[0])
    if not 0 <= h <= 23:
        sys.exit("error: hour must be 00-23")
    return h


class Ctx:
    def __init__(self, sid):
        self.sid = sid
        self.W = load("_world.json")
        self.P = load("scenario.json", sid)
        self.B = load("scenario.json", "baseline")
        self.E = self.W["edges"]

    def ev(self, key, i, base=False):
        src = (self.B if base else self.P)["edges"]
        return src[key][i]

    def street_names(self):
        return sorted({e["name"] for e in self.E if e["name"]})

    def match_street(self, name):
        names = self.street_names()
        low = {n.lower(): n for n in names}
        q = name.lower().strip()
        if q in low:
            return low[q]
        for n in names:  # "2nd" -> "2nd Street", "howard st" -> "Howard Street"
            if n.lower().startswith(q.replace(" st", " street").rstrip(".")) or n.lower().split(" ")[0] == q.split(" ")[0]:
                return n
        m = difflib.get_close_matches(name, names, n=1, cutoff=0.5)
        if not m:
            sys.exit(f"error: no street like {name!r}; try: find \"{name}\"")
        return m[0]

    def edge_row(self, i, hour=None):
        e = self.E[i]
        row = {"edge": i, "x": e["x"], "z": e["z"], "car_day": self.ev("car_day", i), "car_day_base": self.ev("car_day", i, True),
               "ped_day": self.ev("ped_day", i), "ped_day_base": self.ev("ped_day", i, True),
               "congestion_am": self.ev("congestion_am", i), "congestion_pm": self.ev("congestion_pm", i),
               "car_free": i in set(self.P["edges"]["car_free"])}
        if hour is not None:
            row["car_in_hour"] = self.P["edges"]["car_hour"][i][hour]
            row["ped_in_hour"] = self.P["edges"]["ped_hour"][i][hour]
        return row

    def street_agg(self, name, ids=None):
        ids = ids if ids is not None else [e["id"] for e in self.E if e["name"] == name]
        L = sum(self.E[i]["len"] for i in ids) or 1.0

        def wmean(key, base=False):
            return sum(self.ev(key, i, base) * self.E[i]["len"] for i in ids) / L
        car, carb, ped, pedb = wmean("car_day"), wmean("car_day", True), wmean("ped_day"), wmean("ped_day", True)
        bb = [min(self.E[i]["bbox"][0] for i in ids), min(self.E[i]["bbox"][1] for i in ids),
              max(self.E[i]["bbox"][2] for i in ids), max(self.E[i]["bbox"][3] for i in ids)]
        cf = set(self.P["edges"]["car_free"])
        return {"street": name, "edges": ids, "length_m": L, "x": sum(self.E[i]["x"] * self.E[i]["len"] for i in ids) / L,
                "z": sum(self.E[i]["z"] * self.E[i]["len"] for i in ids) / L, "bbox": bb,
                "car_day": car, "car_delta": car - carb, "ped_day": ped, "ped_delta": ped - pedb,
                "congestion_am": max(self.ev("congestion_am", i) for i in ids), "congestion_pm": max(self.ev("congestion_pm", i) for i in ids),
                "car_free_edges": [i for i in ids if i in cf]}

    def pois(self):
        P, B = self.P["pois"], self.B["pois"]
        rows = []
        for p in self.W["pois"]:
            i = p["id"]
            rows.append({**p, "visits": P["visits_day"][i], "visits_base": B["visits_day"][i], "visits_delta": P["visits_day"][i] - B["visits_day"][i],
                         "revenue": P["revenue_day"][i], "revenue_base": B["revenue_day"][i], "revenue_delta": P["revenue_day"][i] - B["revenue_day"][i]})
        return rows

    def find_poi(self, q):
        if str(q).isdigit():
            i = int(q)
            return next((p for p in self.pois() if p["id"] == i), None)
        names = {p["name"]: p for p in self.pois()}
        m = difflib.get_close_matches(q, list(names), n=1, cutoff=0.5) or [n for n in names if q.lower() in n.lower()][:1]
        return names[m[0]] if m else None


def cmd_summary(c, a):
    m, d, v = c.P["metrics"], c.P["delta"], c.P["value"]
    keep = ("people", "commuters", "vmt_total", "delay_hours_total", "walk_minutes", "ped_trips", "visits", "revenue", "encounters",
            "new_ties", "jobs", "residents", "co2_tonnes", "deaths_averted_per_yr", "charges_paid_usd", "through_charges_paid_usd",
            "rent_pressure_index", "access_15min")
    ed = c.P["edits"]
    streets = sorted({c.E[i]["name"] for i in ed.get("pedestrianized", []) if c.E[i]["name"]})
    o = {"scenario": c.sid, "name": c.P.get("name"), "is_baseline": c.sid == "baseline",
         "edits": {"car_free_streets": streets, "pedestrianized_edges": ed.get("pedestrianized", []), "reopened_edges": ed.get("reopened", []),
                   "blocks": ed.get("blocks", {}), "policies": ed.get("policies", [])},
         "metrics": {k: m.get(k) for k in keep if k in m},
         "delta_vs_baseline": {k: d.get(k) for k in keep if k in d},
         "value_usd_per_yr": {k: v.get(k) for k in ("mobility", "social", "economy", "health", "environment", "total")},
         "scale_people_per_agent": c.W["scale_people_per_agent"],
         "baseline_note": "baseline = 2026 reality; Market St (10th to Main) car-free since 2020 (edges " + str(len(c.W["base_car_free_edges"])) + ")"}
    if a.time:
        o["hour"] = cmd_hour(c, argparse.Namespace(hhmm=a.time), ret=True)
    out(o)


def _sort(rows, key, asc, top):
    rows = sorted(rows, key=lambda x: (x[key] if x[key] is not None else 0), reverse=not asc)
    return rows[:top]


def cmd_streets(c, a):
    rows = [c.street_agg(n) for n in c.street_names()]
    rows = [x for x in rows if x["length_m"] > 60]
    out({"sort": a.sort, "streets": [{k: x[k] for k in ("street", "x", "z", "bbox", "car_day", "car_delta", "ped_day", "ped_delta",
                                                         "congestion_am", "congestion_pm", "length_m")} | {"edges": x["edges"][:40]}
                                     for x in _sort(rows, a.sort, a.asc, a.top)],
         "note": "car_day/ped_day are length-weighted means over the street's edges"})


def cmd_edges(c, a):
    h = hh(a.hour) if a.hour is not None else None
    rows = [c.edge_row(i, h) | {"name": c.E[i]["name"], "cls": c.E[i]["cls"]} for i in range(len(c.E)) if c.E[i]["car"] or a.sort.startswith("ped")]
    for x in rows:
        x["car_delta"], x["ped_delta"] = x["car_day"] - x["car_day_base"], x["ped_day"] - x["ped_day_base"]
        x["car"], x["ped"] = x.get("car_in_hour", x["car_day"]), x.get("ped_in_hour", x["ped_day"])
    out({"sort": a.sort, "hour": h, "edges": _sort(rows, a.sort, a.asc, a.top)})


def cmd_street(c, a):
    n = c.match_street(a.name)
    agg = c.street_agg(n)
    out({**agg, "segments": [c.edge_row(i) for i in agg["edges"]]})


def cmd_stretch(c, a):
    n, f, t = c.match_street(a.name), c.match_street(a.frm), c.match_street(a.to)
    on = [e for e in c.E if e["name"] == n]

    def node_of(cross):
        ns = {x for e in c.E if e["name"] == cross for x in (e["a"], e["b"])}
        return next((x for e in on for x in (e["a"], e["b"]) if x in ns), None)
    s, g = node_of(f), node_of(t)
    if s is None or g is None:
        sys.exit(f"error: {n} does not cross {f if s is None else t}")
    adj = {}
    for e in on:
        adj.setdefault(e["a"], []).append((e["b"], e["id"])); adj.setdefault(e["b"], []).append((e["a"], e["id"]))
    prev, q = {s: None}, [s]
    while q:
        u = q.pop(0)
        for v, i in adj.get(u, []):
            if v not in prev:
                prev[v] = (u, i); q.append(v)
    ids, v = [], g
    while prev.get(v):
        u, i = prev[v]; ids.append(i); v = u
    if not ids:
        sys.exit("error: no path along the street between those crossings")
    agg = c.street_agg(n, ids)
    out({**agg, "stretch": f"{n} from {f} to {t}", "segments": [c.edge_row(i) for i in ids]})


def cmd_pois(c, a):
    rows = c.pois()
    if a.category:
        rows = [p for p in rows if p["cat"] == a.category]
    if a.near:
        x, z, rad = map(float, a.near)
        rows = [p for p in rows if (p["x"] - x) ** 2 + (p["z"] - z) ** 2 <= rad * rad]
    rows = _sort(rows, a.sort, a.asc, a.top)
    out({"sort": a.sort, "ascending": a.asc, "pois": [{k: p[k] for k in ("id", "name", "cat", "x", "z", "building", "rating", "visits", "visits_delta",
                                                                          "revenue", "revenue_delta")} for p in rows],
         "note": "revenue $ per weekday, visits per weekday"})


def cmd_poi(c, a):
    p = c.find_poi(a.q)
    if not p:
        sys.exit(f"error: no POI like {a.q!r}")
    vh, vb = c.P["pois"]["visits_hour"][p["id"]], c.B["pois"]["visits_hour"][p["id"]]
    peak = max(range(24), key=lambda h: vh[h])
    near = sorted(c.E, key=lambda e: (e["x"] - p["x"]) ** 2 + (e["z"] - p["z"]) ** 2)[:3]
    out({**p, "walkby_day": c.P["pois"]["walkby_day"][p["id"]], "walkby_day_base": c.B["pois"]["walkby_day"][p["id"]],
         "peak_hour": peak, "visits_by_hour": vh, "visits_by_hour_base": vb,
         "fronting_edges": [{"edge": e["id"], "name": e["name"], "car_free": e["id"] in set(c.P["edges"]["car_free"]),
                             "ped_day": c.ev("ped_day", e["id"]), "ped_day_base": c.ev("ped_day", e["id"], True)} for e in near]})


def _agents(c):
    return load("agents.json", c.sid)


def cmd_agent(c, a):
    A = _agents(c)
    q = a.q
    views = A["views"]
    if q.lower() in ("maria", "maria o.", "hero"):
        q = str(c.W["hero"]["agent_id"])
    elif q.lower() in ("dev", "dev p.", "friend"):
        q = str(c.W["hero"]["friend_id"])
    if not q.isdigit():
        names = {v["name"]: k for k, v in views.items()}
        names.update({x["name"]: str(x["id"]) for x in A["changed"]})
        m = difflib.get_close_matches(q, list(names), n=1, cutoff=0.6)
        if not m:
            sys.exit(f"error: no exported agent like {q!r}")
        q = names[m[0]]
    v = views.get(q)
    if v is None:
        ch = next((x for x in A["changed"] if str(x["id"]) == q), None)
        if not ch:
            sys.exit(f"error: agent {q} has no exported diary (only the hero pair, the sample and changed agents)")
        return out({"agent": ch, "note": "summary only; diary not exported for this agent"})
    W = c.W
    bld = v.get("work_building", -1) if v.get("work_building", -1) >= 0 else v.get("home_building", -1)
    loc = W["buildings"][bld] if 0 <= bld < len(W["buildings"]) else None

    def day(d):
        return {"mode": d.get("mode"), "diary": [{"time": f"{int(x['t'] // 3600):02d}:{int(x['t'] % 3600 // 60):02d}", "text": x["text"],
                                                  **({"poi": x["poi"]} if x.get("poi", -1) >= 0 else {})} for x in (d.get("diary") or [])]}
    out({"agent_id": v["agent_id"], "name": v["name"], "kind": v["kind"], "region": v["region"], "income_tier": v["income_tier"],
         "car_available": v["car_available"], "building": bld, "building_name": loc and loc["name"], "x": loc and loc["x"], "z": loc and loc["z"],
         "is_hero": v["agent_id"] in A["hero"], "baseline": day(v["baseline"]), "plan": day(v["plan"]),
         "ties": list({t["agent_id"]: {"agent_id": t["agent_id"], "name": t["name"], "poi": t.get("where_poi"), "new_in_plan": t.get("new_in_plan")}
                       for t in v["ties"]}.values())[:6]})


def cmd_agents(c, a):
    ch = _agents(c)["changed"]
    if a.frm:
        ch = [x for x in ch if (x["baseline_mode"] or "").startswith(a.frm)]
    if a.to:
        ch = [x for x in ch if (x["plan_mode"] or "").startswith(a.to)]
    trans = {}
    for x in ch:
        k = f"{x['baseline_mode']} -> {x['plan_mode']}"
        trans[k] = trans.get(k, 0) + 1
    S = c.W["scale_people_per_agent"]
    out({"changed_agents": len(ch), "people_represented": len(ch) * S, "by_transition_agents": dict(sorted(trans.items(), key=lambda kv: -kv[1])),
         "sample": [x | ({"x": c.W["buildings"][x["building"]]["x"], "z": c.W["buildings"][x["building"]]["z"]} if x["building"] >= 0 else {})
                    for x in ch[:a.top]], "note": f"each agent represents {S} people"})


def _blocks(c):
    P, B = c.P["blocks"], c.B["blocks"]
    rows = []
    for b in c.W["blocks"]:
        i = b["id"]
        row = dict(b)
        for k in ("jobs", "residents", "visits", "revenue"):
            row[k], row[k + "_delta"] = P[k][i], P[k][i] - B[k][i]
        rows.append(row)
    return rows


def cmd_block(c, a):
    row = next((b for b in _blocks(c) if b["id"] == a.id), None)
    if not row:
        sys.exit("error: unknown block")
    row["buildings_list"] = [{k: b[k] for k in ("id", "name", "kind", "x", "z")} for b in c.W["buildings"] if b["block"] == a.id][:30]
    row["pois"] = [{k: p[k] for k in ("id", "name", "cat", "revenue", "revenue_delta")} for p in c.pois() if 0 <= p["building"] < len(c.W["buildings"])
                   and c.W["buildings"][p["building"]]["block"] == a.id][:20]
    out(row)


def cmd_blocks(c, a):
    out({"sort": a.sort, "blocks": _sort(_blocks(c), a.sort, a.asc, a.top)})


def _inlet_rows(c):
    P, B = c.P["inlets"], c.B["inlets"]
    rows = []
    for g in c.W["inlets"]:
        p, b = P[g["i"]], B[g["i"]]
        eh = p["entered_hour"]
        rows.append({**g, "kind": "rail station (BART/Muni Metro + buses/ferries)" if g["mode"] == "ped" else "car gateway",
                     "entered": p["entered"], "entered_base": b["entered"], "entered_delta": p["entered"] - b["entered"],
                     "left": p["left"], "left_base": b["left"], "peak_entry_hour": max(range(24), key=lambda h: eh[h]),
                     "_hourly": eh})
    return rows


def cmd_inlets(c, a):
    rows = _inlet_rows(c)
    tot = {}
    for r in rows:
        t = tot.setdefault(r["mode"], {"inlets": 0, "entered": 0.0, "entered_base": 0.0})
        t["inlets"] += 1; t["entered"] += r["entered"]; t["entered_base"] += r["entered_base"]
    key = "entered_delta" if a.sort == "delta" else "entered"
    rail = [r for r in rows if r["mode"] == "ped"]
    car = sorted((r for r in rows if r["mode"] != "ped"), key=lambda r: -abs(r[key]) if key == "entered_delta" else -r[key])
    strip = lambda r: {k: v for k, v in r.items() if not k.startswith("_")}
    out({"totals_by_mode": {"rail": tot.get("ped"), "car": tot.get("car")},
         "rail_inlets": [strip(r) for r in rail],
         f"car_inlets_top_{a.top}_by_{key}": [strip(r) for r in car[:a.top]],
         "car_inlets_not_shown": max(0, len(car) - a.top),
         "note": "people/day for rail inlets, vehicles/day for car gateways (modeled agents x scale). Rail inlets also carry "
                 "Muni Metro, buses and ferries (validation gap: 2-3x BART exits). `inlet <key|name>` gives one inlet by hour."})


def cmd_inlet(c, a):
    rows = _inlet_rows(c)
    q = a.q.lower()
    r = next((x for x in rows if x["key"].lower() == q or str(x["i"]) == q), None)
    if r is None:
        names = {x["name"]: x for x in rows}
        m = difflib.get_close_matches(a.q, list(names), n=1, cutoff=0.5) or [n for n in names if q in n.lower()][:1]
        r = names[m[0]] if m else None
    if r is None:
        sys.exit(f"error: no inlet like {a.q!r}; try: inlets")
    hb = c.B["inlets"][r["i"]]["entered_hour"]
    out({**{k: v for k, v in r.items() if not k.startswith("_")}, "entered_by_hour": r["_hourly"], "entered_by_hour_base": hb})


def cmd_hour(c, a, ret=False):
    h = hh(a.hhmm)
    E = c.P["edges"]
    car = sorted(range(len(c.E)), key=lambda i: -E["car_hour"][i][h])[:8]
    ped = sorted(range(len(c.E)), key=lambda i: -E["ped_hour"][i][h])[:8]
    vis = c.P["pois"]["visits_hour"]
    top_p = sorted(range(len(vis)), key=lambda i: -vis[i][h])[:8]
    W = c.W
    o = {"hour": f"{h:02d}:00-{h:02d}:59",
         "car_veh_on_busiest_edges": [{"edge": i, "name": c.E[i]["name"], "x": c.E[i]["x"], "z": c.E[i]["z"], "veh": E["car_hour"][i][h],
                                       **({"congestion": E["congestion_am" if h == 8 else "congestion_pm"][i]} if h in (8, 17) else {})} for i in car],
         "ped_on_busiest_edges": [{"edge": i, "name": c.E[i]["name"], "x": c.E[i]["x"], "z": c.E[i]["z"], "people": E["ped_hour"][i][h]} for i in ped],
         "visits_total": sum(v[h] for v in vis),
         "busiest_pois": [{"id": i, "name": W["pois"][i]["name"] if i < len(W["pois"]) else "virtual", "visits": vis[i][h]} for i in top_p],
         "inlet_entries_top10": [{"i": g["i"], "key": g["key"], "name": g["name"], "mode": g["mode"], "x": g["x"], "z": g["z"],
                                  "entered": c.P["inlets"][g["i"]]["entered_hour"][h]}
                                 for g in sorted(W["inlets"], key=lambda g: -c.P["inlets"][g["i"]]["entered_hour"][h])[:10]],
         "note": "congestion factors are only stored for 08:00 (AM) and 17:00 (PM)"}
    if ret:
        return o
    out(o)


def cmd_value(c, a):
    v = c.P["value"]
    out({k: v.get(k) for k in ("mobility", "social", "economy", "health", "environment", "total")} | {"lines": v.get("lines", [])})


def cmd_assumptions(c, a):
    rows = c.P.get("assumptions", [])
    if a.grep:
        rows = [x for x in rows if a.grep.lower() in (x["key"] + " " + str(x.get("note"))).lower()]
    out({"assumptions": rows[:60]})


def cmd_validation(c, a):
    out({"validation": c.W.get("validation", [])})


def cmd_find(c, a):
    q = a.text.lower()
    W = c.W

    def score(n):
        n = (n or "").lower()
        return 1.0 if q in n else difflib.SequenceMatcher(None, q, n).ratio()
    res = []
    for n in c.street_names():
        res.append((score(n), {"type": "street", "name": n}))
    for p in W["pois"]:
        res.append((score(p["name"]), {"type": "poi", "id": p["id"], "name": p["name"], "cat": p["cat"], "x": p["x"], "z": p["z"]}))
    for b in W["buildings"]:
        if b["name"]:
            res.append((score(b["name"]), {"type": "building", "id": b["id"], "name": b["name"], "x": b["x"], "z": b["z"], "block": b["block"]}))
    for g in W["inlets"]:
        res.append((score(g["name"] + " " + g["key"]), {"type": "inlet", "i": g["i"], "key": g["key"], "name": g["name"], "x": g["x"], "z": g["z"]}))
    A = _agents(c)
    for k, v in A["views"].items():
        res.append((score(v["name"]), {"type": "agent", "id": int(k), "name": v["name"]}))
    pri = {"inlet": 0, "street": 1, "poi": 2, "agent": 3, "building": 4}
    res = [x for s, x in sorted(res, key=lambda t: (-t[0], pri[t[1]["type"]])) if s >= 0.55][:12]
    out({"query": a.text, "matches": res})


def main(argv=None):
    ap = argparse.ArgumentParser(prog="simq", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", default="baseline")
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("summary"); s.add_argument("--time")
    sorts = ["car_delta", "ped_delta", "car", "ped", "congestion_am", "congestion_pm"]
    s = sp.add_parser("streets"); s.add_argument("--sort", default="car", choices=sorts); s.add_argument("--top", type=int, default=10); s.add_argument("--asc", action="store_true")
    s = sp.add_parser("edges"); s.add_argument("--sort", default="car", choices=sorts); s.add_argument("--top", type=int, default=10); s.add_argument("--asc", action="store_true"); s.add_argument("--hour")
    s = sp.add_parser("street"); s.add_argument("name")
    s = sp.add_parser("stretch"); s.add_argument("name"); s.add_argument("frm"); s.add_argument("to")
    s = sp.add_parser("pois"); s.add_argument("--sort", default="revenue", choices=["revenue_delta", "visits_delta", "visits", "revenue"])
    s.add_argument("--asc", action="store_true"); s.add_argument("--category"); s.add_argument("--near", nargs=3); s.add_argument("--top", type=int, default=10)
    s = sp.add_parser("poi"); s.add_argument("q")
    s = sp.add_parser("agent"); s.add_argument("q")
    s = sp.add_parser("agents"); s.add_argument("--changed", action="store_true"); s.add_argument("--from", dest="frm"); s.add_argument("--to"); s.add_argument("--top", type=int, default=12)
    s = sp.add_parser("block"); s.add_argument("id", type=int)
    s = sp.add_parser("blocks"); s.add_argument("--sort", default="jobs", choices=["jobs", "residents", "visits", "revenue", "jobs_delta", "residents_delta", "visits_delta", "revenue_delta"])
    s.add_argument("--top", type=int, default=10); s.add_argument("--asc", action="store_true")
    s = sp.add_parser("inlets"); s.add_argument("--top", type=int, default=15); s.add_argument("--sort", default="volume", choices=["volume", "delta"])
    s = sp.add_parser("inlet"); s.add_argument("q")
    s = sp.add_parser("hour"); s.add_argument("hhmm")
    sp.add_parser("value")
    s = sp.add_parser("assumptions"); s.add_argument("--grep")
    sp.add_parser("validation")
    s = sp.add_parser("find"); s.add_argument("text")
    a = ap.parse_args(argv)
    a.top = max(1, min(getattr(a, "top", 10) or 10, 50))
    if not a.scenario.replace("_", "").isalnum():
        sys.exit("error: bad scenario id")
    c = Ctx(a.scenario)
    if a.scenario == "baseline":
        globals()["NOTE"] = "baseline: all *_delta / *_base comparisons are 0 by definition"
    globals()["cmd_" + a.cmd](c, a)


if __name__ == "__main__":
    main()
