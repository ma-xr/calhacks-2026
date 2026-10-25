"""Build mockup/methods/index.html: the technical Methods appendix, with every number baked in from the
real engine, the research parameter table and the data pipeline outputs (so the page works offline).

Run with the backend venv (the engine is imported read-only; nothing in backend/ is written):
  backend/.venv/bin/python scripts/build_methods.py                 # boots the engine (~20 s), writes the page
  backend/.venv/bin/python scripts/build_methods.py --cache f.json  # reuse / write collected numbers in f.json
"""
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "mockup" / "methods" / "index.html"
TEMPLATE_MARK = "/*__METHODS_DATA__*/"


# ───────────────────────── collect ─────────────────────────
def collect():
    import io
    from contextlib import redirect_stdout
    sys.path.insert(0, str(ROOT / "backend"))
    import numpy as np
    with redirect_stdout(io.StringIO()):
        from hp.api import State
        from hp import results as R
        from hp.engine import CAR, TRANSIT, WALK, BIKE
        from hp.population import REGIONS, TIERS, WORKER

    t0 = time.time()
    S = State()
    S.boot()                       # same boot as the API: calibrate, baseline, hero plan (2nd St car-free)
    eng, w, P = S.eng, S.world, S.P
    base = S.base
    plan = S.scen[S.hero["plan_id"]]
    boot_s = time.time() - t0

    # Re-evaluate the baseline once more to record its per-day gaps (identical procedure; deterministic).
    b2 = eng.evaluate({})
    val = R.valuation(P, base, plan)

    # ── equity ledger: workers by home region × income tier ──
    def per_agent(res):
        st = res["_state"]; ctx = st["ctx"]; pop = st["pop"]
        n = pop.n
        Rg = REGIONS
        car_out = np.array([Rg[r]["car_min"] for r in pop.region], float)
        tr_out = np.array([Rg[r]["tr_min"] for r in pop.region], float)
        walk_out = np.array([Rg[r]["walk_m"] if Rg[r]["walk_m"] is not None else np.nan for r in pop.region], float)
        bike_out = np.array([Rg[r]["bike_m"] if Rg[r]["bike_m"] is not None else np.nan for r in pop.region], float)
        st_walk, walk_in, bike_in = ctx._walk_welfare                     # physical (welfare) network
        t = np.full((n, 4), np.nan)
        t[:, CAR] = car_out + ctx.car_in_min + 4
        t[:, TRANSIT] = tr_out + 5 + st_walk / 60
        t[:, WALK] = (np.nan_to_num(walk_out, nan=1e9) / P["walking_speed_m_s"] + walk_in) / 60
        t[:, BIKE] = (np.nan_to_num(bike_out, nan=1e9) / P["bike_speed_m_s"] + bike_in) / 60
        fare = np.array([P["bart_fare_usd"].get(Rg[r]["fare"], 3.0) for r in pop.region])
        toll = np.array([P["bridge_toll_usd"] / 2 if Rg[r]["toll"] else 0.0 for r in pop.region])
        miles = np.array([Rg[r]["miles"] for r in pop.region], float)
        car_cost = P["daily_parking_cost_fidi_usd"] / 2 + toll + P["vehicle_operating_cost_usd_per_mile"] * (miles + 1.5) + ctx.charge + ctx.fx.car_cost_usd
        mode, gone = st["mode"], st["gone"]
        rows = np.arange(n)
        tt = t[rows, mode] * 2                                                # min/day, chosen mode, both legs
        cost = np.where(mode == CAR, car_cost, np.where(mode == TRANSIT, fare, 0.0)) * 2
        out = {}
        for k in np.where(pop.kind == WORKER)[0]:
            out[int(pop.id[k])] = (int(pop.region[k]), int(pop.tier[k]), int(mode[k]), bool(gone[k]),
                                   float(tt[k]) if not gone[k] else None, float(cost[k]) if not gone[k] else None)
        return out, st["cs_by_id"]

    A_b, cs_b = per_agent(base)
    A_p, cs_p = per_agent(plan)
    scale = int(eng.scale); D = P["workdays_per_year"]
    groups = {}
    for aid, (r, tier, mb, gb, tb, cb) in A_b.items():
        if aid not in A_p:
            continue
        _, _, mp, gp, tp, cp = A_p[aid]
        g = groups.setdefault((r, tier), {"n": 0, "car_b": 0, "car_p": 0, "gone_p": 0, "tr_b": 0, "tr_p": 0, "act_b": 0, "act_p": 0,
                                          "dt": [], "dc": [], "dcs": [], "switch": 0})
        g["n"] += 1
        g["car_b"] += (mb == CAR and not gb); g["car_p"] += (mp == CAR and not gp); g["gone_p"] += gp
        g["tr_b"] += (mb == TRANSIT and not gb); g["tr_p"] += (mp == TRANSIT and not gp)
        g["act_b"] += (mb in (WALK, BIKE) and not gb); g["act_p"] += (mp in (WALK, BIKE) and not gp)
        g["switch"] += (mb != mp) or (gb != gp)
        if tb is not None and tp is not None and math.isfinite(tb) and math.isfinite(tp):
            g["dt"].append(tp - tb); g["dc"].append(cp - cb)
        if aid in cs_b and aid in cs_p:
            g["dcs"].append(cs_p[aid] - cs_b[aid])
    ledger = []
    for (r, tier), g in sorted(groups.items()):
        n = g["n"]
        dcs = np.array(g["dcs"]) if g["dcs"] else np.zeros(0)
        ledger.append({
            "region": REGIONS[r]["key"], "region_name": REGIONS[r]["name"], "tier": TIERS[tier],
            "agents": n, "people": n * scale,
            "car_b": g["car_b"] / n, "car_p": g["car_p"] / n, "transit_b": g["tr_b"] / n, "transit_p": g["tr_p"] / n,
            "active_b": g["act_b"] / n, "active_p": g["act_p"] / n, "gone_p": g["gone_p"] / n,
            "switchers": g["switch"] * scale,
            "dt_min_day": float(np.mean(g["dt"])) if g["dt"] else None,
            "dcost_usd_day": float(np.mean(g["dc"])) if g["dc"] else None,
            "dcs_usd_yr_pp": float(dcs.mean() * 2 * D) if len(dcs) else None,
            "dcs_usd_yr_total": float(dcs.sum() * 2 * D * scale) if len(dcs) else None,
            "worst_pp": float(dcs.min() * 2 * D) if len(dcs) else None,
            "losers_share": float((dcs < -1e-9).mean()) if len(dcs) else None,
        })
    ledger_total = sum(x["dcs_usd_yr_total"] or 0 for x in ledger)
    mob_line = next(l for l in val["lines"] if l["label"].startswith("Commuter time"))

    # ── regions for the map ──
    rs = S.I.home_region_share() or {}
    regions = [{"key": r["key"], "name": r["name"], "share": rs.get(r["key"], 0), "car_min": r["car_min"], "tr_min": r["tr_min"],
                "miles": r["miles"], "toll": r["toll"], "fare": r["fare"]} for r in REGIONS]

    bm, pm = base["metrics"], plan["metrics"]
    keep = ("people", "agents", "scale", "trips", "commuters", "vmt", "vmt_total", "veh_hours", "delay_hours", "delay_hours_total",
            "visits", "revenue", "encounters", "new_ties", "neighbor_ties", "jobs", "residents", "co2_tonnes", "access_15min",
            "walker_visits_per_day", "driver_visits_per_day")
    I = S.I
    biz = I.businesses["meta"]
    out = {
        "built": time.strftime("%Y-%m-%d %H:%M"), "boot_s": round(boot_s, 1),
        "world": {"nodes": int(w.N), "edges": int(w.E), "buildings": int(w.B), "pois": int(w.P),
                  "car_edges": int(np.sum(w.edge_car)), "inlets": len(w.inlets),
                  "car_inlets": sum(1 for g in w.inlets if g["mode"] == "car"), "rail_inlets": len(w.rail_inlets),
                  "base_car_free_edges": len(eng.base_closed), "blocks": int(w.n_blocks),
                  "bbox": (I.lodes.get("meta") or {}).get("notes", [""])[0]},
        "population": {"present_workers": eng.pb.present_workers, "residents": eng.pb.residents, "scale": scale,
                       "agents": int(eng.pb.base.n),
                       "by_kind": {k: int(np.sum(eng.pb.base.kind == i)) for i, k in enumerate(["worker", "resident", "visitor", "through"])},
                       "tier_share": eng.pb.tier_share, "region_share": rs},
        "inputs": {
            "lodes_jobs": I.lodes["jobs_total"], "lodes_blocks": I.lodes["n_work_blocks"], "lodes_far": I.lodes["far_home_jobs"],
            "lodes_od_in_state": I.lodes["od_in_state_jobs"], "lodes_earn": I.lodes["jobs_by_earnings"],
            "acs": I.acs["tracts_summary"],
            "landuse_buildings": len(I.landuse["buildings"]),
            "landuse_office_sqft": float(sum((b.get("office_sqft") or 0) for b in I.landuse["buildings"])),
            "biz_places": biz["n_places"], "biz_popular": biz["n_with_popular_times"], "biz_matched": biz["n_matched_poi"],
            "bart": {k: {"exits": v["weekday_exits"], "entries": v["weekday_entries"]} for k, v in I.transit["stations"].items()},
            "bart_month": I.transit["meta"].get("report_month"), "bart_hourly": I.transit["meta"].get("hourly_profile_period"),
            "counts_bike": sum(1 for c in I.traffic_counts["counts"] if c.get("mode") == "bicycle"),
            "counts_mv": sum(1 for c in I.traffic_counts["counts"] if c.get("mode") == "motor_vehicle"),
        },
        "calibration": {"asc": dict(eng.asc), "target": eng.calibration["target"], "beta_t": P["beta_time_per_min"],
                        "modeled": {k: base["metrics"]["commuters"][k] for k in ("car", "transit", "walk", "bike")}},
        "settle": {"baseline": b2["settle"], "plan": plan["settle"], "msa_days": P["settle_days_plan"],
                   "calib_days": 4 * 4 + P["settle_days_baseline"]},
        "base": {k: bm[k] for k in keep}, "plan": {k: pm[k] for k in keep},
        "value": {k: val[k] for k in ("mobility", "social", "economy", "environment", "total")},
        "value_lines": val["lines"],
        "hero": {"street": "2nd Street (Market → Folsom)", "edges": len(S.hero["street_edges"]), "plan_id": S.hero["plan_id"]},
        "ledger": ledger, "ledger_total": ledger_total, "ledger_check": mob_line["usd_per_yr"],
        "regions": regions,
    }
    return json.loads(json.dumps(out, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


def research():
    params = json.loads((ROOT / "research/parameters/parameters.json").read_text())
    val = json.loads((ROOT / "research/validation/validation.json").read_text())
    return params, val




# ───────────────────────── formatting ─────────────────────────
def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def n0(x):
    return f"{round(x):,}"


def usd(x, sign=False):
    a = abs(x); s = ("+" if x > 0 else "−" if x < 0 else "") if sign else ("−" if x < 0 else "")
    if a >= 1e6:
        return f"{s}${a / 1e6:.2f}M"
    if a >= 1e3:
        return f"{s}${a / 1e3:.1f}k"
    return f"{s}${a:.2f}" if a < 10 else f"{s}${a:,.0f}"


def pct(x, sign=True, nd=1):
    v = x * 100
    return (f"{v:+.{nd}f}%" if sign else f"{v:.{nd}f}%").replace("-", "−")


def short_title(t, n=90):
    t = t or ""
    return t if len(t) <= n else t[:n - 1].rstrip() + "…"


def pval(v):
    if isinstance(v, dict):
        parts = []
        for k, x in v.items():
            parts.append(f"{k}: {pval(x)}")
        return "; ".join(parts)
    if isinstance(v, float):
        if abs(v) >= 1e5:
            return f"{v:,.0f}"
        return f"{v:g}"
    if isinstance(v, int):
        return f"{v:,}" if abs(v) >= 10000 else str(v)
    return esc(v)


class Refs:
    """Numbered references, in first-cited order."""

    def __init__(self, fixed, params):
        self.fixed = {r["id"]: r for r in fixed}
        self.params = params
        self.order = []

    def _key(self, rid):
        if rid not in self.order:
            self.order.append(rid)
        return self.order.index(rid) + 1

    def cite(self, *rids):
        nums = [self._key(r) for r in rids]
        return "<span class=cite>[" + ", ".join(f'<a href="#ref-{n}">{n}</a>' for n in nums) + "]</span>"

    def param_ref(self, key):
        """Reference for a research parameter's source (data/literature only)."""
        m = self.params[key]
        url = m.get("source") or ""
        rid = "url:" + url
        if rid not in self.fixed:
            self.fixed[rid] = {"id": rid, "text": esc(m.get("source_title") or url), "url": url}
        return self.cite(rid)

    def html(self):
        out = []
        for i, rid in enumerate(self.order, 1):
            r = self.fixed[rid]
            link = f' <a class=url href="{esc(r["url"])}" target=_blank rel=noopener>{esc(r["url"])}</a>' if r.get("url") else ""
            out.append(f'<li id="ref-{i}"><span class=refn>[{i}]</span><span>{r["text"]}{link}</span></li>')
        return "<ol class=refs>" + "".join(out) + "</ol>"


FIXED_REFS = [
    {"id": "cairns2002", "text": "Cairns, S., Atkins, S., Goodwin, P. (2002). Disappearing traffic? The story so far. <i>Proc. ICE Municipal Engineer</i> 151(1):13–22.", "url": "https://nacto.org/wp-content/uploads/disappearing_traffic_cairns.pdf"},
    {"id": "matsim", "text": "Horni, A., Nagel, K., Axhausen, K. W. (eds.) (2016). <i>The Multi-Agent Transport Simulation MATSim</i>. Ubiquity Press.", "url": "https://doi.org/10.5334/baw"},
    {"id": "sheffi", "text": "Sheffi, Y. (1985). <i>Urban Transportation Networks: Equilibrium Analysis with Mathematical Programming Methods</i>. Prentice-Hall.", "url": "http://web.mit.edu/sheffi/www/selectedMedia/sheffi_urban_trans_networks.pdf"},
    {"id": "wardrop", "text": "Wardrop, J. G. (1952). Some theoretical aspects of road traffic research. <i>Proc. ICE</i> Part II 1(3):325–378.", "url": ""},
    {"id": "fhwa", "text": "FHWA. HPMS Field Manual, Appendix N: procedures for estimating highway capacity (BPR link-performance function).", "url": "https://www.fhwa.dot.gov/ohim/hpmsmanl/appn5.cfm"},
    {"id": "tm1cap", "text": "MTC Travel Model One. <code>SpeedCapacity_1hour.block</code>, <code>SpeedFlowCurve.block</code>, <code>HwyAssign.job</code>.", "url": "https://github.com/BayAreaMetro/travel-model-one/tree/master/model-files/scripts"},
    {"id": "tm1mc", "text": "MTC Travel Model One. <code>ModeChoice.xls</code> (tour mode choice UEC).", "url": "https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/model/ModeChoice.xls"},
    {"id": "sfcta_asim", "text": "SFCTA ActivitySim (SF-CHAMP successor). Tour mode choice coefficients and constants.", "url": "https://github.com/sfcta/activitysim-sfcta/tree/main/configs"},
    {"id": "koppelman", "text": "Koppelman, F. S., Bhat, C. (2006). <i>A Self Instructing Course in Mode Choice Modeling: Multinomial and Nested Logit Models</i>. FTA.", "url": "https://www.caee.utexas.edu/prof/bhat/COURSES/LM_Draft_060131Final-060630.pdf"},
    {"id": "usdot_vtt", "text": "USDOT (2016). Revised Departmental Guidance on Valuation of Travel Time in Economic Analysis.", "url": "https://www.transportation.gov/sites/dot.gov/files/docs/Revised%20Departmental%20Guidance%20on%20Valuation%20of%20Travel%20Time%20in%20Economic%20Analysis%20-%20September%202016.pdf"},
    {"id": "litman", "text": "Litman, T. (2026). <i>Understanding Transport Demands and Elasticities</i>. Victoria Transport Policy Institute.", "url": "https://www.vtpi.org/elasticities.pdf"},
    {"id": "huff", "text": "Esri. Understanding the Huff model (ArcGIS Business Analyst documentation).", "url": "https://pro.arcgis.com/en/pro-app/3.2/tool-reference/business-analyst/understanding-huff-model.htm"},
    {"id": "appleyard", "text": "Appleyard, D. (1981). <i>Livable Streets</i>. University of California Press (street-traffic and neighbouring study, 1969–71); summary via Streetfilms transcript.", "url": "https://amara.org/videos/WrBmfcwZMu7b/en/103981"},
    {"id": "granovetter", "text": "Granovetter, M. (1973). The strength of weak ties. <i>American Journal of Sociology</i> 78(6):1360–1380.", "url": "https://en.wikipedia.org/wiki/Interpersonal_ties"},
    {"id": "copenhagen", "text": "Sapiezynski, P. et al. (2019). Interaction data from the Copenhagen Networks Study. <i>Scientific Data</i> 6:315.", "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6906316/"},
    {"id": "inrix", "text": "INRIX (2020). Full car ban on Market Street: little impact on surrounding roads.", "url": "https://inrix.com/blog/full-car-ban-on-market-street-little-impact-on-surrounding-roads/"},
    {"id": "sfmta_market", "text": "SFMTA Board of Directors (2021). Better Market Street car-free evaluation.", "url": "https://sfmta.com/media/25169/download"},
    {"id": "osm", "text": "OpenStreetMap contributors. Road graph, buildings, POIs and parks via the Overpass API (ODbL).", "url": "https://www.openstreetmap.org"},
    {"id": "lodes", "text": "U.S. Census Bureau, LEHD Origin-Destination Employment Statistics (LODES8), California 2023: WAC S000 JT00, OD main JT00, crosswalk.", "url": "https://lehd.ces.census.gov/data/lodes/LODES8/ca/"},
    {"id": "acs", "text": "U.S. Census Bureau, American Community Survey 5-year estimates 2019–2023 (api.census.gov), 2023 Gazetteer tracts.", "url": "https://api.census.gov/data/2023/acs/acs5"},
    {"id": "datasf_lu", "text": "DataSF. San Francisco Land Use (c5ge-t6pj, current; fdfd-xptc, 2023 archive) and Zoning Districts (3i4a-hu95).", "url": "https://data.sf.gov/resource/c5ge-t6pj.json"},
    {"id": "apify", "text": "Google Maps places and popular times, scraped with the Apify actor compass/crawler-google-places (run vbfPXBeCW7izCHgG1).", "url": "https://apify.com/compass/crawler-google-places"},
    {"id": "bart", "text": "BART. Monthly ridership report, September 2026 (average weekday OD); hourly OD 2025.", "url": "https://www.bart.gov/sites/default/files/2026-10/Ridership_202609.xlsx"},
    {"id": "bart_hourly", "text": "BART. Hourly origin-destination ridership, 2025.", "url": "https://afcweb.bart.gov/ridership/origin-destination/date-hour-soo-dest-2025.csv.gz"},
    {"id": "sfmta_bike", "text": "SFMTA manual bicycle counts (DataSF v4v2-5x7s), PM peak, 2015–2017.", "url": "https://data.sf.gov/resource/v4v2-5x7s.json"},
    {"id": "caltrans", "text": "Caltrans. Traffic Census AADT (state highway count points), ArcGIS FeatureServer.", "url": "https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/Traffic_AADT/FeatureServer/0"},
    {"id": "kastle", "text": "Kastle Systems. Back to Work Barometer (weekly office occupancy, % of pre-pandemic).", "url": "https://www.kastle.com/safety-wellness/getting-america-back-to-work/"},
    {"id": "gtfs", "text": "BART GTFS feed (fare_rules / fare_attributes).", "url": "https://www.bart.gov/dev/schedules/google_transit.zip"},
]


def ptable(P, keys, R, symbols=None):
    """Parameter table: only keys whose status in parameters.json is data or literature."""
    symbols = symbols or {}
    rows = []
    for k in keys:
        m = P.get(k)
        if not m or m.get("status") not in ("data", "literature"):
            continue
        rng = ""
        if m.get("low") is not None or m.get("high") is not None:
            rng = f'<div class=rng>range {pval(m.get("low")) if m.get("low") is not None else "–"} … {pval(m.get("high")) if m.get("high") is not None else "–"}</div>'
        sym = f"\\({symbols[k]}\\)" if k in symbols else ""
        rows.append(f'<tr><td><code>{esc(k)}</code></td><td>{sym}</td><td class=pv>{pval(m["value"])}{rng}</td>'
                    f'<td>{esc(m.get("unit") or "")}</td><td><span class="badge {m["status"]}">{m["status"]}</span></td>'
                    f'<td>{R.param_ref(k)} <span class=srct>{esc(short_title(m.get("source_title"), 70))}</span></td></tr>')
    return ('<div class=tw><table class="ptab"><thead><tr><th>Parameter</th><th>Symbol</th><th>Value</th><th>Unit</th><th>Status</th><th>Source</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


def fill(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace("{{" + k + "}}", str(v))
    return tpl


# ───────────────────────── sections ─────────────────────────
def vrow(V, case_prefix, q_prefix):
    for r in V:
        if r["case"].startswith(case_prefix) and r["quantity"].startswith(q_prefix):
            return r
    return None


def sections(D, P, V, R):
    c = R.cite
    pr = R.param_ref
    pop, inp, wd, cal, st = D["population"], D["inputs"], D["world"], D["calibration"], D["settle"]
    bm, pm = D["base"], D["plan"]
    S = []

    # 1 ─ overview
    S.append(("overview", "System overview", fill(r"""
<p class=lede>The Human Project simulates one weekday in San Francisco's Financial District and upper SoMa as a swarm of
{{agents}} software agents, each standing for \(s = {{scale}}\) real people ({{people}} people present in the baseline).
A run is a fixed point of a MATSim-style loop {{c_matsim}}: agents choose modes on yesterday's congested travel times,
cars are loaded onto the OpenStreetMap road graph, link costs are updated with a BPR function, and the day is replayed.
After the last replanning day a final day is simulated in full: walking legs, Huff destination choice, walk-by retail,
co-presence encounters and the dollar valuation. A plan (closing streets to cars, rezoning, prices, plugin policies) is
evaluated by exactly the same procedure as the baseline, with common random numbers, so a plan with no edits reproduces
the baseline bit for bit and differences are effects, not sampling noise.</p>
<div class=stats>
 <div><b>{{agents}}</b><span>agents</span></div>
 <div><b>{{scale}}</b><span>people per agent</span></div>
 <div><b>{{people}}</b><span>people represented</span></div>
 <div><b>{{edges}}</b><span>street edges ({{nodes}} nodes)</span></div>
 <div><b>{{inlets}}</b><span>map inlets ({{car_inlets}} car, {{rail}} rail)</span></div>
 <div><b>{{days}}</b><span>replanning days per plan</span></div>
</div>
<figure class=fig>{{svg}}<figcaption><b>Figure 1.</b> Pipeline. Solid arrows carry data; the dashed loop is the replanning
fixed point (Section 6). Policy plugins enter through three hooks (Section 11) and only after passing the Droid gate.</figcaption></figure>
<p>Evaluation cost on this machine: engine boot (ASC calibration, baseline and hero plan) {{boot}} s; one plan {{plan_ms}} ms
(5 replanning days + final day).</p>
""", agents=n0(pop["agents"]), scale=pop["scale"], people=n0(bm["people"]), edges=n0(wd["edges"]), nodes=n0(wd["nodes"]),
        inlets=wd["inlets"], car_inlets=wd["car_inlets"], rail=wd["rail_inlets"], days=st["msa_days"], c_matsim=c("matsim"),
        svg=PIPELINE_SVG, boot=D["boot_s"], plan_ms=st["plan"]["ms"])))

    # 2 ─ data
    bart = inp["bart"]
    rows = [
        ("OpenStreetMap (Overpass)", "2026 extract", "Road graph, building footprints, POIs, parks, rail stations", f'{n0(wd["nodes"])} nodes · {n0(wd["edges"])} edges ({n0(wd["car_edges"])} drivable) · {n0(wd["buildings"])} buildings · {n0(wd["pois"])} POIs · {wd["inlets"]} inlets', "osm"),
        ("LEHD LODES8 (WAC, OD)", "2023", "Jobs per work block (control total), earnings tiers, home region of workers", f'{n0(inp["lodes_jobs"])} jobs in {inp["lodes_blocks"]} work blocks · {n0(inp["lodes_od_in_state"])} in-state OD jobs · {n0(inp["lodes_far"])} with homes &gt;150 km (excluded)', "lodes"),
        ("ACS 5-year", "2019–2023", "Resident control total and household size of the tracts in the area", f'{inp["acs"]["n"]} tracts · {n0(inp["acs"]["population"])} residents · {n0(inp["acs"]["households"])} households · {inp["acs"]["persons_per_household"]:.3f} persons/household', "acs"),
        ("DataSF Land Use + Zoning", "2026 snapshot, 2023 archive", "Floor area by use per building (office, retail, hotel, other, units)", f'{n0(inp["landuse_buildings"])} building records · {inp["landuse_office_sqft"] / 1e6:.1f}M sqft office', "datasf_lu"),
        ("Google Maps via Apify", "fetched 2026-10-24", "POI quality (rating, reviews), hourly popular-times profiles by category", f'{inp["biz_places"]} places · {inp["biz_matched"]} matched to OSM POIs · {inp["biz_popular"]} with popular times', "apify"),
        ("BART ridership", f'{inp["bart_month"]} (daily); {esc(inp["bart_hourly"])} (hourly)', "Validation of rail-inlet arrivals (volume and hourly shape)", " · ".join(f'{k}: {n0(v["exits"])} weekday exits' for k, v in bart.items()), "bart"),
        ("SFMTA manual bike counts", "2015–2017", "Validation of cycling volumes (PM peak)", f'{inp["counts_bike"]} count sites', "sfmta_bike"),
        ("Caltrans Traffic Census AADT", "current layer", "Freeway approach volumes (context; no SF surface-street car counts exist on DataSF)", f'{inp["counts_mv"]} count points (I-80 / Bay Bridge ramps)', "caltrans"),
        ("Kastle Back to Work Barometer", "2026", "Office occupancy rate applied to office jobs", f'occupancy {P["sf_office_occupancy_rate"]["value"]:.3f}', "kastle"),
        ("BART GTFS", "v72, 2026", "One-way Clipper fares by home region", "fare_rules / fare_attributes", "gtfs"),
    ]
    trs = "".join(f"<tr><td><b>{a}</b> {c(ref)}</td><td>{b}</td><td>{f}</td><td class=rec>{n}</td></tr>" for a, b, f, n, ref in rows)
    S.append(("data", "Data sources", f"""
<p>All inputs are cached JSON files written by <code>backend/data/*.py</code>; the counts below are read from those files at build time.
Raw API responses are cached with their query parameters; credentials are never written.</p>
<div class=tw><table><thead><tr><th>Dataset</th><th>Vintage</th><th>Feeds</th><th>Records</th></tr></thead><tbody>{trs}</tbody></table></div>
<p class=note>Study area: {esc(wd["bbox"])}</p>"""))

    # 3 ─ population
    tier = pop["tier_share"]; rs = pop["region_share"]; bk = pop["by_kind"]
    reg_rows = "".join(f'<tr><td>{esc(r["name"])}</td><td class=num>{pct(rs.get(r["key"], 0), False)}</td><td class=num>{r["car_min"]}</td><td class=num>{r["tr_min"]}</td><td class=num>{r["miles"]}</td><td>{"yes" if r["toll"] else "–"}</td></tr>' for r in D["regions"])
    S.append(("population", "Synthetic population", fill(r"""
<p>Jobs are placed per building from floor area and job densities, then scaled to the LODES control total; residents from
dwelling units and household size, scaled to the ACS total. For building \(b\) with office, retail, hotel and other floor
areas \(F_b^{\cdot}\) (ft²) and units \(U_b\):</p>
$$J_b^{\mathrm{off}} = (1-v)\,\frac{F_b^{\mathrm{off}}}{a_{\mathrm{off}}},\qquad
  J_b^{\mathrm{oth}} = \frac{F_b^{\mathrm{ret}}}{a_{\mathrm{ret}}}+\frac{F_b^{\mathrm{hot}}}{a_{\mathrm{hot}}}+\frac{F_b^{\mathrm{cie}}}{a_{\mathrm{cie}}},\qquad
  R_b = U_b\,h \tag{1}$$
$$J_b \leftarrow J_b\,\frac{J^{\mathrm{LODES}}}{\sum_{b'} J_{b'}},\qquad R_b \leftarrow R_b\,\frac{R^{\mathrm{ACS}}}{\sum_{b'} R_{b'}} \tag{2}$$
<p>with \(v\) the FiDi office vacancy rate and \(a_\cdot\) floor area per job. Buildings without a DataSF record fall back to
an OSM-type template. Only part of the job base is in the area on a given weekday: office jobs scale with the Kastle
badge-swipe occupancy \(o\), other jobs with an attendance share \(\rho\):</p>
$$W_b = o\,J_b^{\mathrm{off}} + \rho\,J_b^{\mathrm{oth}},\qquad s = \operatorname{round}\!\Big(\textstyle\sum_b W_b \,/\, N^{*}\Big) \tag{3}$$
<p>where \(N^{*}\) is the worker-agent budget. This gives \(\sum_b W_b = {{present}}\) present workers and \(s = {{scale}}\)
people per agent. Agents are allocated to buildings by largest remainder of \(W_b/s\) (deterministic), giving
{{nw}} worker, {{nr}} resident, {{nv}} visitor and {{nt}} through-traffic agents ({{agents}} total).</p>
<p><b>Attributes.</b> Earnings tier is drawn from the LODES WAC earnings split (SE01/02/03 = {{t_low}} / {{t_mid}} / {{t_high}});
home region given tier from LODES OD by earnings, with the "other" region shrunk to the share that excludes homes more than
150 km away (head-office reporting artifacts). Each region carries the part of the trip that lies outside the map:</p>
<div class=tw><table><thead><tr><th>Home region</th><th>Share of jobs (LODES, excl. far)</th><th>Car min outside map</th><th>Transit min outside map</th><th>Car miles outside</th><th>Bridge toll</th></tr></thead><tbody>{{reg_rows}}</tbody></table></div>
<p>Arrival times, work hours, lunch, coffee, errand and evening activities are drawn per agent once (seed 2026). Each agent also
carries a persistent Gumbel vector \(\boldsymbol\varepsilon_i \in \mathbb{R}^4\) for mode choice and a hash-seeded uniform stream for
destination noise, so baseline and plan share the same draws (common random numbers). Rezoning or densifying a building keeps
or removes base agents by a fixed relocation uniform and appends new agents with stable ids.</p>
{{ptab}}
""", present=n0(pop["present_workers"]), scale=pop["scale"], nw=n0(bk["worker"]), nr=n0(bk["resident"]), nv=n0(bk["visitor"]),
        nt=n0(bk["through"]), agents=n0(pop["agents"]), t_low=pct(tier["low"], False), t_mid=pct(tier["mid"], False),
        t_high=pct(tier["high"], False), reg_rows=reg_rows,
        ptab=ptable(P, ["sf_office_occupancy_rate", "fidi_office_vacancy_rate", "office_sqft_per_job", "retail_sqft_per_job", "hotel_sqft_per_job",
                        "persons_per_household_downtown", "home_region_share_downtown_workers", "income_tier_share_downtown_workers"], R,
                    {"sf_office_occupancy_rate": "o", "fidi_office_vacancy_rate": "v", "office_sqft_per_job": "a_{\\mathrm{off}}",
                     "retail_sqft_per_job": "a_{\\mathrm{ret}}", "hotel_sqft_per_job": "a_{\\mathrm{hot}}", "persons_per_household_downtown": "h"}))))

    # 4 ─ activities + Huff
    S.append(("destinations", "Activity and destination choice", fill(r"""
<p>Each present worker takes part in activity \(a\in\{\)morning coffee, lunch, afternoon coffee, errand, evening\(\}\) with a
Bernoulli draw of probability \(p_a\) (lunch out: \(p_{\mathrm{lunch}} = {{lunch}}\) {{c_lunch}}); residents and visitors have
their own activity sets. The destination of every activity is a Huff / multinomial-logit choice among POIs of the
matching categories, with walking distance on the street graph {{c_huff}}:</p>
$$U_{ij} = \ln\!\big(w_{c(j)}\,q_j\,\alpha_j\big) + b_{\mathrm{cf}}\,\mathbb{1}[j \text{ fronts a car-free edge}] - \lambda\,d_{ij} + \varepsilon_{ij},
\qquad j^{*}_i = \arg\max_{j:\,d_{ij}\le r_a} U_{ij} \tag{4}$$
<p>Here \(w_c\) weights category \(c\) for the purpose, \(\alpha_j\) is the plugin attractiveness multiplier (Eq. 30),
\(\lambda\) the distance decay per metre, \(r_a\) a purpose radius and \(\varepsilon_{ij}\) a Gumbel draw from a hash of
(agent, POI, purpose), identical across scenarios. Taking the argmax over Gumbel-perturbed utilities is an exact draw from
the logit probabilities \(P_{ij} = e^{V_{ij}}/\sum_k e^{V_{ik}}\). POI quality comes from Google rating \(g_j\) and review count \(n_j\)
when the POI is matched ({{matched}} of {{pois}}), otherwise from a deterministic draw:</p>
$$q_j = \operatorname{clip}\!\Big(\big(g_j/\bar g\big)^{2}\,\big(\kappa_0 + \kappa_1\ln(1+n_j)\big),\; q_{\min},\, q_{\max}\Big) \tag{5}$$
<p><b>Walk-by visits.</b> Pedestrians passing a POI's frontage edges \(E_j\) stop with a category capture rate \(\gamma_c\),
shaped by an hourly propensity taken from the Google popular-times profile \(g_c(h)\) of that category:</p>
$$\pi_c(h) = \frac{g_c(h)}{\tfrac{1}{16}\sum_{h'=7}^{22} g_c(h')},\qquad
  I_j(h) = \pi_{c(j)}(h)\,\gamma_{c(j)}\,q_j\,(1+b_{\mathrm{cf}}\mathbb{1}_j^{\mathrm{cf}})\sum_{e\in E_j} f^{\mathrm{ped}}_e(h) \tag{6}$$
$$\text{Revenue}_j = \tau_{c(j)} \sum_h \big(s\,N^{\mathrm{dest}}_j(h) + I_j(h)\big) \tag{7}$$
<p>with \(f^{\mathrm{ped}}_e(h)\) people per hour on edge \(e\), \(N^{\mathrm{dest}}_j(h)\) destination arrivals (agents) and
\(\tau_c\) the average ticket. Baseline: {{visits}} visits and {{revenue}} revenue per weekday across {{pois}} POIs.</p>
{{ptab}}
""", lunch=P["lunch_out_share_office_workers"]["value"], c_lunch=pr("lunch_out_share_office_workers"), c_huff=c("huff"),
        matched=inp["biz_matched"], pois=n0(wd["pois"]), visits=n0(bm["visits"]), revenue=usd(bm["revenue"]),
        ptab=ptable(P, ["lunch_out_share_office_workers", "avg_ticket_usd", "walking_speed_m_s", "walk_detour_factor"], R,
                    {"lunch_out_share_office_workers": "p_{\\mathrm{lunch}}", "avg_ticket_usd": "\\tau_c", "walking_speed_m_s": "v_{\\mathrm{walk}}"}))))

    # 5 ─ mode choice
    asc = cal["asc"]; tgt = cal["target"]; mod = cal["modeled"]; tot = sum(mod.values())
    cal_rows = "".join(f'<tr><td>{k}</td><td class=num>{pct(tgt[k], False)}</td><td class=num>{pct(mod[k] / tot, False)}</td><td class=num>{(mod[k] / tot - tgt[k]) * 100:+.1f} pp</td><td class=num>{("%.3f" % asc[k]) if k in asc else "0 (reference)"}</td></tr>'.replace("-", "−") for k in ("car", "transit", "walk", "bike"))
    acs24 = P["sf_county_worker_mode_share_acs2024"]["value"]; sfcta = P["downtown_trip_mode_share_sfcta"]["value"]
    S.append(("modechoice", "Mode choice (multinomial logit)", fill(r"""
<p>Workers choose among car, transit (BART / Muni), walk and bike with a multinomial logit {{c_kb}}. Systematic utilities, in
minutes \(t\) and dollars \(c\), one way:</p>
$$\begin{aligned}
V_i^{\mathrm{car}} &= \mathrm{ASC}_{\mathrm{car}} + \beta_t\big(t^{\mathrm{out}}_{r} + \bar t^{\mathrm{in}}_i + t^{\mathrm{park}}\big) + \beta_{c,i}\,c^{\mathrm{car}}_i\\
V_i^{\mathrm{tr}} &= \beta_t\big(t^{\mathrm{tr,out}}_{r} + \mu\,t^{\mathrm{wait}} + \mu\,t^{\mathrm{acc}}_i\big) + \beta_{c,i}\,\phi_{r}\\
V_i^{\mathrm{walk}} &= \mathrm{ASC}_{\mathrm{walk}} + \beta_t\,\mu\,t^{\mathrm{walk}}_i, \qquad t^{\mathrm{walk}}_i < T_{\mathrm{walk}}\\
V_i^{\mathrm{bike}} &= \mathrm{ASC}_{\mathrm{bike}} + \beta_t\,\mu_{b}\,t^{\mathrm{bike}}_i, \qquad t^{\mathrm{bike}}_i < T_{\mathrm{bike}}
\end{aligned} \tag{8}$$
<p>\(\bar t^{\mathrm{in}}_i = \tfrac12(t^{\mathrm{AM}}_i + t^{\mathrm{PM}}_i)\) is the congested in-map car time from the cheapest
inlet of the agent's home region (Eq. 13), \(\mu\) the walk/wait time multiplier, \(t^{\mathrm{acc}}_i\) the station-to-office
walk and \(\phi_r\) the BART fare. Car is unavailable (\(V=-\infty\)) without a car or without a reachable parking node. The money
coefficient converts the time coefficient with the agent's value of time:</p>
$$\beta_{c,i} = \frac{60\,\beta_t}{\mathrm{VOT}\cdot m_{k(i)}},\qquad
  c^{\mathrm{car}}_i = \tfrac12 c^{\mathrm{park}} + \tfrac12 c^{\mathrm{toll}}_r + c^{\mathrm{voc}}\,(\ell_r + \ell_0) + c^{\mathrm{charge}}_i + c^{\mathrm{plug}}_i \tag{9}$$
<p>where \(m_k\) scales VOT by income tier \(k\) and \(\ell_r\) is the out-of-map mileage. Choice is the argmax of utility plus the
agent's persistent Gumbel draw, which is an exact sample from the logit probabilities:</p>
$$m_i = \arg\max_{m}\big(V_i^{m} + \varepsilon_{im}\big),\quad \varepsilon_{im}\sim\mathrm{Gumbel}(0,1)
\;\;\Longleftrightarrow\;\; P_i(m) = \frac{e^{V_i^m}}{\sum_{m'} e^{V_i^{m'}}} \tag{10}$$
<p>\(\beta_t\) is set in the engine defaults (it is not one of the sourced research parameters); the cited regional models use
work-tour in-vehicle-time coefficients of {{tm1}} (MTC TM1) {{c_tm1}} and {{sfcta}} utils/min (SFCTA ActivitySim) {{c_sfcta}}.</p>
<h3>Calibration of the alternative-specific constants</h3>
<p>Transit is the reference alternative. During the cold start the ASCs are updated after each block of replanning days
by the standard log-ratio correction toward the target worker split \(\sigma^{*}\):</p>
$$\mathrm{ASC}_m \leftarrow \mathrm{ASC}_m + \ln\frac{\sigma^{*}_m}{\hat\sigma_m} - \ln\frac{\sigma^{*}_{\mathrm{tr}}}{\hat\sigma_{\mathrm{tr}}},\qquad m\in\{\mathrm{car},\mathrm{walk},\mathrm{bike}\} \tag{11}$$
<p>Four blocks of 4 days are followed by {{final}} settling days ({{cald}} days in all). The target split is an
<b>assumed</b> downtown worker split (car = drive alone + carpool, renormalized without "other" and WFH); it is not a cited
value. For context, the two sourced splits it sits between: ACS 2024 SF-County workplace commuters drive alone {{acs_da}},
carpool {{acs_cp}}, transit {{acs_tr}}, walk {{acs_wk}}, bike {{acs_bk}} {{c_acs}}; SFCTA downtown trips (2023) auto {{sf_auto}},
transit {{sf_tr}}, walk+bike {{sf_wb}} {{c_sfc}}.</p>
<div class=tw><table><thead><tr><th>Mode</th><th>Target (assumed)</th><th>Model (baseline)</th><th>Residual</th><th>Estimated ASC</th></tr></thead><tbody>{{cal_rows}}</tbody></table></div>
<figure class=fig id=fig-cal></figure>
{{ptab}}
""", c_kb=c("koppelman"), tm1=P["mtc_tm1_ivt_coef_work_per_min"]["value"], c_tm1=pr("mtc_tm1_ivt_coef_work_per_min"),
        sfcta=P["sfcta_ivt_coef_work_per_min"]["value"], c_sfcta=pr("sfcta_ivt_coef_work_per_min"), final=st["calib_days"] - 16,
        cald=st["calib_days"], acs_da=pct(acs24["drive_alone"], False), acs_cp=pct(acs24["carpool"], False), acs_tr=pct(acs24["transit"], False),
        acs_wk=pct(acs24["walk"], False), acs_bk=pct(acs24["bike"], False), c_acs=pr("sf_county_worker_mode_share_acs2024"),
        sf_auto=pct(sfcta["y2023"]["auto"], False), sf_tr=pct(sfcta["y2023"]["transit"], False), sf_wb=pct(sfcta["y2023"]["walk_bike"], False),
        c_sfc=pr("downtown_trip_mode_share_sfcta"), cal_rows=cal_rows,
        ptab=ptable(P, ["vot_personal_usd_per_hr", "walk_wait_time_multiplier", "daily_parking_cost_fidi_usd", "bart_fare_usd", "bridge_toll_usd",
                        "vehicle_operating_cost_usd_per_mile", "mtc_tm1_ivt_coef_work_per_min", "sfcta_ivt_coef_work_per_min",
                        "sf_county_worker_mode_share_acs2024", "downtown_trip_mode_share_sfcta"], R,
                    {"vot_personal_usd_per_hr": "\\mathrm{VOT}", "walk_wait_time_multiplier": "\\mu", "daily_parking_cost_fidi_usd": "c^{\\mathrm{park}}",
                     "bart_fare_usd": "\\phi_r", "bridge_toll_usd": "c^{\\mathrm{toll}}", "vehicle_operating_cost_usd_per_mile": "c^{\\mathrm{voc}}"}))))

    # 6 ─ assignment
    gb, gp = st["baseline"]["gaps"], st["plan"]["gaps"]
    S.append(("assignment", "Network assignment", fill(r"""
<p>Cars are assigned per hour of day \(h\) on the directed OSM car graph. Link travel time follows the BPR function
{{c_bpr}}, with modeled agent volume inflated by the share \(\sigma_{\mathrm{bg}}\) of traffic not represented by agents
(taxis/TNC, freight, buses) and capped at \(f_{\max}\):</p>
$$f_e(h) = \min\!\Big(1 + \alpha\Big(\frac{x_e(h)}{(1-\sigma_{\mathrm{bg}})\,C_e}\Big)^{\beta},\; f_{\max}\Big),\qquad
  C_e = n^{\mathrm{lanes}}_e\,\bar C_{\mathrm{class}(e)},\qquad \tau_e(h) = \tau^{0}_e\, f_e(h)\,\chi_e \tag{12}$$
<p>\(\chi_e\) is the product of plugin edge factors (Eq. 30). A car edge closed in a plan is removed from the graph; parking is
restricted to the main strongly connected component of the open graph so every driver can enter and leave.</p>
<p><b>Inlets and routing.</b> {{car_inlets}} car inlets are generated from every road crossing the map edge. A home region may use
a set of inlets \(\mathcal I_r\), each with a head-start cost \(o_{ri}\) (extra outside minutes plus a road-class penalty).
One multi-source Dijkstra tree per (region, hour) gives every node its cheapest entry:</p>
$$t^{\mathrm{AM}}_{i} = \min_{k\in\mathcal I_{r(i)}}\big(o_{rk} + \mathrm{SP}_h(k \to p_i)\big),\qquad
  t^{\mathrm{PM}}_{i} = \min_{k\in\mathcal I_{r(i)}}\big(o_{rk} + \mathrm{SP}_h(p_i \to k)\big) \tag{13}$$
<p>with \(p_i\) the parking node. A virtual super-source links to every entry with its offset, so a closure moves drivers to
another inlet. Edge volumes \(x_e(h)\) are accumulated by subtree sums over each tree (no per-trip path walk), each agent
carrying \(s/\omega\) vehicles (\(\omega\) persons per commuter car). An inlet toll enters the AM tree as time at VOT.</p>
<h3>Replanning and MSA</h3>
<p>Day \(k\) re-runs mode choice on the current link factors, loads cars, and averages volumes by the method of successive
averages {{c_sheffi}}; plans are warm-started from the calibrated state, which counts as the first iterate:</p>
$$\bar{\mathbf x}_{k} = \bar{\mathbf x}_{k-1} + \frac{1}{k+1}\big(\mathbf x_k - \bar{\mathbf x}_{k-1}\big),\qquad
  \mathbf f_k = \mathrm{BPR}(\bar{\mathbf x}_k) \tag{14}$$
$$\mathrm{gap}_k = \frac{\sum_{h,e}\big|\bar x_{k,he} - \bar x_{k-1,he}\big|}{\sum_{h,e}\bar x_{k-1,he}},\qquad
  \text{converged} \iff \mathrm{gap}_{K} < 0.03,\quad K = {{K}} \tag{15}$$
<p>This is a relative change in averaged flows, not a Wardrop relative gap {{c_wardrop}}; it measures how much the averaged state
still moves. After day \(K\) one more choice + loading pass produces the reported day. Measured per-day gaps
(engine run at build time):</p>
<figure class=fig id=fig-gap></figure>
<p class=note><b>Honest reading.</b> Neither run meets the 0.03 criterion at day {{K}}: the baseline ends at {{gbl}}, the 2nd St plan at
{{gpl}}, and both results carry <code>"converged": false</code> in the API. The gap rises on day 2 because the first day's mode
shift is absorbed into the average at weight 1/2. Plans are scored as differences against a baseline settled by the same
procedure, which cancels part of the residual movement, but not all of it.</p>
{{ptab}}
""", c_bpr=c("fhwa"), car_inlets=wd["car_inlets"], c_sheffi=c("sheffi"), K=st["msa_days"], c_wardrop=c("wardrop"),
        gbl=f'{gb[-1]:.4f}', gpl=f'{gp[-1]:.4f}',
        ptab=ptable(P, ["bpr_alpha", "bpr_beta", "lane_capacity_vph", "urban_free_flow_speed_kmh", "downtown_arterial_speed_mph_2025", "bay_bridge_aadt"], R,
                    {"bpr_alpha": "\\alpha", "bpr_beta": "\\beta", "lane_capacity_vph": "\\bar C_{\\mathrm{class}}"}))))

    # 7 ─ evaporation
    ev = vrow(V, "Car-free Market", "Traffic evaporation")
    S.append(("evaporation", "Traffic evaporation and trip suppression", fill(r"""
<p>Removing road capacity does not simply move all traffic elsewhere; part of it disappears {{c_cairns}}. The engine represents
this in two ways. <b>Commuter suppression:</b> in a plan, a worker who drives and whose in-map car time rose against the baseline
skips the car trip (works from home, combines trips) with probability</p>
$$p^{\mathrm{gone}}_i = \operatorname{clip}\!\Big(-\varepsilon_{T}\,\frac{\max(0,\;\bar t^{\mathrm{in}}_i - \bar t^{\mathrm{in,base}}_i)}{t^{\mathrm{out}}_r + \bar t^{\mathrm{in,base}}_i},\; 0,\; p_{\max}\Big),
\qquad \text{gone}_i = \mathbb 1\big[u_i < p^{\mathrm{gone}}_i\big] \tag{16}$$
<p>with \(\varepsilon_T = {{eps}}\) the short-run elasticity of car trips with respect to travel time {{c_eps}} and \(u_i\) a fixed
per-agent uniform. <b>Through-traffic:</b> each through vehicle compares crossing the area with a freeway bypass:</p>
$$\text{stay}_i \iff \beta_t\,t^{\mathrm{thr}}_i + \beta_{c,i}\,c^{\mathrm{plug}}_i + \varepsilon_{i0} \;>\; \beta_t\big(t^{\mathrm{free}}_i + t^{\mathrm{byp}}\big) + \varepsilon_{i1} \tag{17}$$
<p>and in a plan is additionally suppressed by Eq. 16 with denominator \(t^{\mathrm{thr,base}}_i + t_0\). Validation against the
Cairns et al. definition (Δ area traffic ÷ prior traffic on the treated street) for car-free Market St gives
<b>{{ev_m}}</b> against a median of <b>{{ev_t}}</b>. The model ratio is unstable because its denominator, private-car VMT on the
pre-2020 Market St (where forced turns already made through-driving impractical), is small; see Section 12.</p>
{{ptab}}
""", c_cairns=c("cairns2002"), eps=P["car_trip_time_elasticity"]["value"], c_eps=pr("car_trip_time_elasticity"),
        ev_m=f'{ev["model"]:.2f}'.replace("-", "−") if ev else "–", ev_t=f'{ev["target"]:.2f}'.replace("-", "−") if ev else "–",
        ptab=ptable(P, ["car_trip_time_elasticity", "traffic_evaporation_median", "cairns_central_shopping_median", "parking_price_elasticity_vehicle_trips"], R,
                    {"car_trip_time_elasticity": "\\varepsilon_T"}))))

    # 8 ─ social
    fr = P["appleyard_friends_by_traffic"]["value"]
    S.append(("social", "Social ties: co-presence model", fill(r"""
<p>Encounters are counted from co-presence. Every destination visit \((i, j, t, d)\) occupies time bins of width \(\Delta\) at POI \(j\).
In a bin with \(n_{jb}\) agents (\(N_{jb} = s\,n_{jb}\) people), each person registers at most \(K\) others:</p>
$$E = \sum_{j,b} \tfrac12\,N_{jb}\,\min(N_{jb}-1,\,K) \;+\; E^{\mathrm{street}},\qquad
  E^{\mathrm{hab}} = \sum_{j,b} \tfrac12\,N_{jb}\min(N_{jb}-1,K)\,\frac{n^{\mathrm{hab}}_{jb}}{n_{jb}} + \theta\,E^{\mathrm{street}} \tag{18}$$
<p>\(n^{\mathrm{hab}}\) counts habitual agents (workers and residents, who repeat their routine). On car-free edges a share \(\delta\)
of passers-by lingers and meets others in the same way:</p>
$$E^{\mathrm{street}} = \sum_{h}\sum_{e\,\in\,\mathrm{cf}} \tfrac12\,L_{eh}\,\min\!\big(\max(L_{eh}-1,0),K\big),\qquad L_{eh} = \delta\,f^{\mathrm{ped}}_{e}(h) \tag{19}$$
<p>Repeated co-presence turns into weak ties {{c_gran}} at rate \(p_{\mathrm{tie}}\) per repeat, with \(R\) repeat days out of \(D\)
workdays (time-binned co-location as a proximity proxy follows {{c_cns}}):</p>
$$\Delta T^{\mathrm{weak}} = E^{\mathrm{hab}}\;p_{\mathrm{tie}}\;\frac{R}{D}\quad[\text{ties/yr}] \tag{20}$$
<p><b>Neighbouring.</b> Residents' friends on their own street fall with traffic, following Appleyard's San Francisco street study
{{c_app}} ({{light}} / {{moderate}} / {{heavy}} friends per resident on light / moderate / heavy streets). With \(A_e\) the daily
vehicles on the resident's home edge (agents plus background), \(F(A)\) is piecewise-linear through those three levels at
breakpoints \(A_1<A_2<A_3\):</p>
$$N^{\mathrm{nbr}} = s\sum_{i\in\mathrm{res}} F\big(A_{e(i)}\big) \tag{21}$$
<p>Baseline: {{enc}} encounters per weekday, {{ties}} new weak ties per year, {{nbr}} neighbour friendships.</p>
{{ptab}}
""", c_gran=c("granovetter"), c_cns=c("copenhagen"), c_app=c("appleyard"), light=fr["light"], moderate=fr["moderate"], heavy=fr["heavy"],
        enc=n0(bm["encounters"]), ties=n0(bm["new_ties"]), nbr=n0(bm["neighbor_ties"]),
        ptab=ptable(P, ["appleyard_friends_by_traffic"], R))))

    # 9 ─ valuation
    vl = D["value_lines"]; vv = D["value"]
    lrows = "".join(f'<tr><td>{esc(l["pillar"])}</td><td>{esc(l["label"])}</td><td class=num>{l["qty"]:,.1f} {esc(l["unit"])}</td><td class="num {"pos" if l["usd_per_yr"] > 0 else "neg" if l["usd_per_yr"] < 0 else ""}">{usd(l["usd_per_yr"], True)}</td></tr>' for l in vl)
    S.append(("valuation", "Economic and valuation model", fill(r"""
<p>City Value is the annualized change of a plan against the baseline, itemized by pillar: mobility, social, economy and environment.
Health is deliberately not valued: physical-activity benefits (WHO HEAT × VSL) dominated every total, so active minutes and
deaths averted are reported as plain metrics only. Crash costs are likewise not monetized. With \(D\) workdays per year:</p>
<p><b>Mobility</b> is the change in commuter consumer surplus, the logit log-sum converted to dollars {{c_kb}}, computed on
physical (bonus-free) walking distances so that a street's amenity is not counted both as time saved and as street life:</p>
$$\mathrm{CS}_i = \frac{1}{-\beta_{c,i}}\,\ln\sum_{m\in\mathcal A_i} e^{V^{\mathrm{w}}_{im}} \quad[\$/\text{trip}] \tag{22}$$
$$\Delta\mathcal V_{\mathrm{mob}} = 2sD\sum_{i\in\mathrm{workers}}\big(\mathrm{CS}^{\mathrm{plan}}_i - \mathrm{CS}^{\mathrm{base}}_i\big)
  \;-\; sD\,\mathrm{VOT}\sum_{i\in\mathrm{thr}}\frac{\Delta t^{\mathrm{thr}}_i}{60} \;-\; D\,\mathrm{VOT}\,\psi\,\frac{\sigma_{\mathrm{bg}}}{1-\sigma_{\mathrm{bg}}}\,\Delta H^{\mathrm{delay}} \tag{23}$$
<p>where a through vehicle that switches to the bypass is charged \(t^{\mathrm{byp}}\), and \(\Delta H^{\mathrm{delay}}\) is the change in
agent vehicle-hours of delay, scaled to background traffic with weight \(\psi\).</p>
<p><b>Environment:</b> CO₂ from in-map VMT (agents + background) and out-of-map commute VMT, at the social cost of carbon:</p>
$$\Delta\mathcal V_{\mathrm{env}} = -D\,\mathrm{SCC}\;\frac{e_{\mathrm{CO_2}}}{1000}\;\Delta\Big(\mathrm{VMT}^{\mathrm{in}}\tfrac{1}{1-\sigma_{\mathrm{bg}}} + \mathrm{VMT}^{\mathrm{out}}\Big) \tag{24}$$
<p><b>Economy:</b> local value added on the net-new part of revenue, the city's share of sales tax, charge and parking revenue (a transfer
to the city) and property tax on new floor area \(\Delta F\):</p>
$$\Delta\mathcal V_{\mathrm{eco}} = D\,\Delta\mathrm{Rev}\,\big(\nu\,\eta + t_{\mathrm{city}}\big) + D\,\Delta\mathrm{Charges} + \Delta F\,P_{\mathrm{assessed}}\,t_{\mathrm{prop}} \tag{25}$$
<p><b>Social:</b> weak ties and chance encounters at a per-tie and per-encounter value \(\upsilon_{\mathrm{tie}}, \upsilon_{\mathrm{enc}}\), neighbour
friendships at half a tie:</p>
$$\Delta\mathcal V_{\mathrm{soc}} = \upsilon_{\mathrm{tie}}\,\Delta T^{\mathrm{weak}} + D\,\upsilon_{\mathrm{enc}}\,\Delta E + \tfrac12\,\upsilon_{\mathrm{tie}}\,\Delta N^{\mathrm{nbr}} \tag{26}$$
$$\mathcal V = \Delta\mathcal V_{\mathrm{mob}} + \Delta\mathcal V_{\mathrm{soc}} + \Delta\mathcal V_{\mathrm{eco}} + \Delta\mathcal V_{\mathrm{env}} \tag{27}$$
<p>Rent pressure is reported beside the total as a trade-off and not monetized. The map client shows the engine's itemized
<code>value</code> when it is online; its offline fallback is a simplified toy and is not described here.</p>
<h3>Worked example: {{street}} car-free (hero plan <code>{{pid}}</code>)</h3>
<p>Total <b>{{total}}/yr</b>: mobility {{mob}}, social {{soc}}, economy {{eco}}, environment {{env}}. Every line as the engine itemizes it:</p>
<div class=tw><table><thead><tr><th>Pillar</th><th>Line</th><th>Quantity</th><th>$/yr</th></tr></thead><tbody>{{lrows}}</tbody></table></div>
{{ptab}}
""", c_kb=c("koppelman"), street=D["hero"]["street"], pid=D["hero"]["plan_id"], total=usd(vv["total"], True), mob=usd(vv["mobility"], True),
        soc=usd(vv["social"], True), eco=usd(vv["economy"], True), env=usd(vv["environment"], True), lrows=lrows,
        ptab=ptable(P, ["vot_personal_usd_per_hr", "co2_kg_per_vmt", "scc_usd_per_tonne", "retail_value_added_share", "city_share_of_sales_tax", "sf_sales_tax_rate"], R,
                    {"vot_personal_usd_per_hr": "\\mathrm{VOT}", "co2_kg_per_vmt": "e_{\\mathrm{CO_2}}", "scc_usd_per_tonne": "\\mathrm{SCC}",
                     "retail_value_added_share": "\\nu", "city_share_of_sales_tax": "t_{\\mathrm{city}}"}))))

    # 10 ─ equity
    S.append(("equity", "Who wins, who pays: ledger and equity map", fill(r"""
<p>The mobility line of Eq. 23 is a sum over people, so it can be split. For a group \(G\) of workers (home region × income tier),
matched by agent id between baseline and plan:</p>
$$\Delta\mathcal V_G = 2sD\sum_{i\in G}\Delta\mathrm{CS}_i,\qquad
  \overline{\Delta\mathcal V}_G = \frac{2D}{|G|}\sum_{i\in G}\Delta\mathrm{CS}_i\quad[\$/\text{yr per person}],\qquad
  \sum_G \Delta\mathcal V_G = \Delta\mathcal V_{\mathrm{commuters}} \tag{28}$$
<p>Travel time is the time term of the agent's chosen mode in Eq. 8 on physical distances, both legs; money is that mode's
out-of-pocket cost from Eq. 9 (car) or the fare (transit), both legs. Both are averaged over agents who travel in both runs.
Check: the groups sum to <b>{{lt}}</b>/yr, the engine's commuter consumer-surplus line is <b>{{lc}}</b>/yr.
This ledger covers commuters only: through-traffic, background traffic and the non-mobility pillars are not attributed to groups.</p>
<figure class=fig><div id=eqmap></div><figcaption><b>Figure 4.</b> Equity map, {{street}} car-free vs baseline. Schematic Bay Area, not to scale.
Bubble area ∝ people represented; colour = mean Δ$/yr per person (diverging, red = loses, green = gains, grey ≈ 0). Hover a region for its income tiers.</figcaption></figure>
<div class=tw><table id=ledger class=sortable><thead><tr>
<th data-k=region_name>Home region</th><th data-k=tier>Income</th><th data-k=people class=num>People</th>
<th data-k=car_b class=num>Car share base → plan</th><th data-k=switchers class=num>Switchers</th>
<th data-k=dt_min_day class=num>Δ min/day</th><th data-k=dcost_usd_day class=num>Δ $/day cost</th>
<th data-k=dcs_usd_yr_pp class=num>Δ $/yr per person</th><th data-k=dcs_usd_yr_total class=num>Group Δ $/yr</th></tr></thead><tbody></tbody></table></div>
<p class=note>Click a column to sort. Switchers = people whose mode (or skip) differs between runs. Most losses come from drivers and
would-be drivers facing traffic diverted from 2nd St; the log-sum also counts the worsened car option for people who did not drive.</p>
""", lt=usd(D["ledger_total"], True), lc=usd(D["ledger_check"], True), street=D["hero"]["street"])))

    # 11 ─ policy + gate
    S.append(("policy", "Policy plugin calculus and the Droid verification gate", fill(r"""
<p>Besides built-in levers (street closures, rezoning, density, congestion charge, parking price), new policies are Python modules
written by the Droid policy compiler. A module declares <code>KIND</code>, <code>PARAMS</code> (with defaults and bounds) and any of three
pure-numpy hooks over read-only views of agents, edges and POIs. For active plugins \(p\in\mathcal P\), effects compose as</p>
$$c^{\mathrm{plug}}_i = \sum_{p\in\mathcal P} c_{p,i},\qquad c_{p,i}\in[-100,\,500]\;\$ \;\;\text{(car\_cost\_usd: per one-way car trip)} \tag{29}$$
$$\chi_e = \prod_{p\in\mathcal P}\chi_{p,e},\qquad \alpha_j = \prod_{p\in\mathcal P}\alpha_{p,j},\qquad \chi_{p,e},\alpha_{p,j}\in[0.05,\,20] \tag{30}$$
<p>\(c^{\mathrm{plug}}\) enters the car utility (Eq. 9), the through-traffic stay/bypass choice (Eq. 17) and charges paid;
\(\chi\) multiplies car link costs (Eq. 12); \(\alpha\) multiplies Huff attractiveness (Eq. 4). Parameters are clipped to their declared
bounds, arrays are checked for shape and finiteness, and out-of-range values abort the scenario. Only modules recorded in
<code>approved.json</code> are registered.</p>
<h3>Gate (<code>backend/droid/gate.py</code>)</h3>
<p>A generated policy must pass six checks, in order, before a human can approve it:</p>
<div class=tw><table><thead><tr><th>#</th><th>Check</th><th>Condition</th></tr></thead><tbody>
<tr><td>1</td><td>files</td><td><code>generated/&lt;kind&gt;.py</code> and <code>test_&lt;kind&gt;.py</code> exist</td></tr>
<tr><td>2</td><td>static</td><td>AST scan: imports limited to numpy, math (tests also pytest, hp.policies); no <code>open/exec/eval/compile/__import__/getattr</code>…, no I/O or randomness attributes (<code>random, load, save, system, environ</code>…), no dunder attributes</td></tr>
<tr><td>3</td><td>load</td><td>imports with sockets disabled; <code>KIND</code> matches; <code>PARAMS</code> and <code>EXAMPLE</code> are dicts</td></tr>
<tr><td>4</td><td>pytest</td><td>the generated test and the full engine suite pass</td></tr>
<tr><td>5</td><td>determinism</td><td>same edits evaluated twice give identical metrics (JSON equality)</td></tr>
<tr><td>6</td><td>sanity</td><td>all metrics finite; \(\mathrm{VMT},\mathrm{Rev},\mathrm{Visits}\in[0.5,1.5]\times\) baseline, \(\mathrm{People}\in[0.8,1.2]\times\); delay ≥ 0; at least one headline metric changes</td></tr>
</tbody></table></div>
$$\mathrm{pass} = \bigwedge_{k=1}^{6}\mathrm{check}_k,\qquad \frac{m^{\mathrm{policy}}}{m^{\mathrm{base}}}\in[\ell_m,u_m]\;\;\forall m\in\{\mathrm{VMT},\mathrm{Rev},\mathrm{Visits},\mathrm{People}\} \tag{31}$$
""")))

    # 12 ─ validation
    S.append(("validation", "Calibration and validation", validation_html(D, P, V, R)))
    return S


def validation_html(D, P, V, R):
    c = R.cite

    def fmtv(r):
        q = r["quantity"]
        isr = "ratio" in q or "correlation" in q or "Pearson" in q or "evaporation" in q.lower()
        f = (lambda x: "—" if x is None else f"{x:.2f}".replace("-", "−")) if isr else (lambda x: "—" if x is None else pct(x))
        return f(r["model"]), f(r["target"])

    def table(case, extra_src=None):
        rows = [r for r in V if r["case"] == case]
        out = []
        for r in rows:
            m, t = fmtv(r)
            src = r.get("source") or ""
            if case.startswith("Calibration"):
                s = "assumed target (Section 5)"
            elif src.startswith("http"):
                key = next((k for k, v in P.items() if isinstance(v, dict) and v.get("source") == src and v.get("status") in ("data", "literature")), None)
                if key:
                    s = R.param_ref(key)
                else:
                    R.fixed.setdefault("url:" + src, {"id": "url:" + src, "text": "BART ridership reports" if "bart.gov" in src else esc(src), "url": src})
                    s = c("url:" + src)
            elif "Google" in src:
                s = c("apify") + " " + esc(src)
            elif "BART hourly" in src:
                s = c("bart_hourly") + " " + esc(src)
            elif "SFMTA manual" in src:
                s = c("sfmta_bike") + " " + esc(src)
            else:
                s = esc(src)
            out.append(f'<tr><td>{esc(r["quantity"])}</td><td class=num>{m}</td><td class=num>{t}</td><td>{s}</td><td class=note2>{esc(r["note"] or "")}</td></tr>')
        return ('<div class=tw><table><thead><tr><th>Quantity</th><th>Model</th><th>Observed / literature</th><th>Source</th><th>Notes</th></tr></thead><tbody>'
                + "".join(out) + "</tbody></table></div>")

    return fill(r"""
<p>Two kinds of evidence are kept apart. <b>Calibrated</b> rows were fitted on purpose (the three ASCs, Eq. 11) and show the fit only.
<b>Validation</b> rows were not fitted: the model was not tuned to hit them, and differences are reported as they come out. Rows
below are from <code>research/validation/validation.json</code>, generated by <code>backend/hp/validation.py</code>
(one weekday, {{agents}} agents at {{scale}} people per agent). Observed values are research parameters with status data or literature.</p>
<h3>Mode split (calibrated)</h3>
{{t_cal}}
<h3>Car-free Market Street, Jan 29 2020 (validation)</h3>
<p>Counterfactual: Market St reopened to private cars as before 2020 (with the forced turns modeled as a travel-time factor on the
reopened edges) against today's car-free Market St {{c_m}} {{c_inrix}}.</p>
{{t_mkt}}
<figure class=fig id=fig-val></figure>
<h3>Pedestrianizing 2nd St, Market → Folsom (validation)</h3>
{{t_ped}}
<h3>Business visit timing vs Google popular times</h3>
<p>Partly calibrated: the walk-in propensity \(\pi_c(h)\) in Eq. 6 uses these shapes; destination trips do not.</p>
{{t_pop}}
<figure class=fig id=fig-pop></figure>
<h3>Rail arrivals vs BART</h3>
{{t_bart}}
<h3>Cycling vs SFMTA counts</h3>
{{t_bike}}
<div class=gaps><h3>Open gaps</h3><ul>
<li><b>Muni on Market St:</b> about 0% against +6% observed. With car traffic spread over all {{ci}} inlets, the restricted pre-2020 Market carries
too few cars in the counterfactual to slow buses.</li>
<li><b>Cycling on Market St:</b> about +98% against +25%; cycling route choice responds too strongly to car-free streets.</li>
<li><b>Cycling volume:</b> modeled cyclists at the count sites are a small fraction of the 2015–17 counts (ratio in the table); through-cyclists and
non-commute cycling are not modeled.</li>
<li><b>Rail volume:</b> arrivals at the three rail inlets are 2–3× BART exits, because each inlet also carries Muni Metro, bus and ferry riders.
The hourly shape matches well (r ≥ 0.84).</li>
<li><b>Evaporation ratio:</b> unstable, since its denominator (pre-2020 private-car VMT on Market) is small.</li>
<li><b>Walker vs driver visit frequency:</b> 1.18 against the reported ≈2×.</li>
<li><b>Convergence:</b> the 0.03 MSA criterion is not met after 5 days (Section 6).</li>
</ul></div>
""", agents=n0(D["population"]["agents"]), scale=D["population"]["scale"], ci=D["world"]["car_inlets"],
        c_m=c("sfmta_market"), c_inrix=c("inrix"),
        t_cal=table("Calibration: downtown worker mode split"),
        t_mkt=table("Car-free Market Street (Jan 29, 2020)"), t_ped=table("Pedestrianizing 2nd St (Market → Folsom)"),
        t_pop=table("Business visit timing vs Google popular times"), t_bart=table("Transit arrivals vs BART ridership"),
        t_bike=table("Cycling vs SFMTA counts"))


def _box(x, y, w, h, t1, t2="", cls=""):
    lines = t2.split("|") if t2 else []
    tx = "".join(f'<text x="{x + w / 2}" y="{y + 36 + 13 * k}" class=t2>{esc(l)}</text>' for k, l in enumerate(lines))
    return (f'<g class="bx {cls}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9"/>'
            f'<text x="{x + w / 2}" y="{y + 20}" class=t1>{esc(t1)}</text>{tx}</g>')


def _arrow(x1, y1, x2, y2, cls=""):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="ar {cls}" marker-end="url(#ah)"/>'


def pipeline_svg():
    W, H, bw, bh = 150, 0, 150, 66
    xs = [20, 195, 370, 545, 720]
    y0, y1, y2 = 18, 128, 248
    g = []
    g.append(_box(xs[0], y0, bw, 56, "OpenStreetMap", "roads · buildings · POIs", "src"))
    g.append(_box(xs[1], y0, bw, 56, "LODES · ACS · DataSF", "jobs · residents · floor area", "src"))
    g.append(_box(xs[2], y0, bw + 175, 56, "Research parameters", "77 keys: value · unit · status · source", "src"))
    g.append(_box(xs[4], y0, bw, 56, "Google popular times", "POI quality · hourly shape", "src"))
    g.append(_box(xs[0], y1, bw, bh, "World graph", "nodes · edges · inlets|blocks · POIs"))
    g.append(_box(xs[1], y1, bw, bh, "Population", "§3  occupancy × LODES|ACS · s people/agent"))
    g.append(_box(xs[2], y1, bw, bh, "Mode choice", "§5  MNL, Gumbel ε|ASC calibration", "k"))
    g.append(_box(xs[3], y1, bw, bh, "Assignment", "§6  BPR · inlet trees|MSA gap", "k"))
    g.append(_box(xs[4], y1, bw, bh, "Final day", "§4 §8  Huff · walk-by|co-presence · ties"))
    g.append(_box(xs[0], y2, bw, 56, "Droid gate", "§11  6 checks", "gate"))
    g.append(_box(xs[1], y2, bw + 175, 56, "Policy plugins", "c_plug → §5 · χ_e → §6 · α_j → §4", "gate"))
    g.append(_box(xs[3], y2, bw, 56, "Validation", "§12  BART · SFMTA · INRIX"))
    g.append(_box(xs[4], y2, bw, 56, "City Value", "§9 §10  $/yr · ledger", "k"))
    for a, b in ((0, 1), (1, 2), (3, 4)):
        g.append(_arrow(xs[a] + bw, y1 + bh / 2, xs[b] - 4, y1 + bh / 2))
    g.append(_arrow(xs[2] + bw, y1 + 22, xs[3] - 4, y1 + 22))
    g.append(f'<path d="M{xs[3]} {y1 + 46} C {xs[3] - 14} {y1 + 46}, {xs[2] + bw + 14} {y1 + 46}, {xs[2] + bw + 4} {y1 + 46}" class="ar loop" marker-end="url(#ah)"/>')
    g.append(f'<text x="{xs[2] + bw + 12.5}" y="{y1 - 6}" class="t2 lbl">K = 5 days</text>')
    for k in (0, 1, 4):
        g.append(_arrow(xs[k] + bw / 2, y0 + 56, xs[k] + bw / 2, y1 - 4, "src"))
    g.append(_arrow(xs[2] + bw / 2, y0 + 56, xs[2] + bw / 2, y1 - 4, "src"))
    g.append(_arrow(xs[3] + bw / 2, y0 + 56, xs[3] + bw / 2, y1 - 4, "src"))
    g.append(_arrow(xs[0] + bw, y2 + 28, xs[1] - 4, y2 + 28, "gate"))
    g.append(_arrow(xs[2] + bw / 2, y2, xs[2] + bw / 2, y1 + bh + 4, "gate"))
    g.append(_arrow(xs[4] + bw / 2, y1 + bh, xs[4] + bw / 2, y2 - 4))
    g.append(_arrow(xs[4] + 20, y1 + bh, xs[3] + bw - 20, y2 - 4))
    return ('<svg class=pipe viewBox="0 0 890 322" role="img" aria-label="Simulation pipeline"><defs><marker id=ah viewBox="0 0 10 10" refX=9 refY=5 '
            'markerWidth=7 markerHeight=7 orient=auto-start-reverse><path d="M0 0 L10 5 L0 10 z" class=ahp /></marker></defs>' + "".join(g) + "</svg>")


PIPELINE_SVG = pipeline_svg()


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Methods · The Human Project</title>
<meta name="description" content="Technical appendix: synthetic population, logit mode choice, BPR/MSA assignment, Huff destinations, co-presence ties, valuation, equity ledger, policy plugin gate, calibration and validation.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css" crossorigin="anonymous">
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js" crossorigin="anonymous"></script>
<script defer src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js" crossorigin="anonymous"></script>
<style>
:root {
  --bg: #07101f;
  --bg2: #0c1830;
  --panel: rgba(16, 32, 60, .80);
  --line: rgba(255, 255, 255, .08);
  --line-hi: rgba(255, 255, 255, .16);
  --fill: rgba(255, 255, 255, .055);
  --fill-hi: rgba(255, 255, 255, .10);
  --hi: #7fd3ff;
  --accent: #3b9cff;
  --fg: #f3f7fc;
  --dim: #a9bad1;
  --mute: #7b8fab;
  --good: #4fdc7a;
  --bad: #ff5d5d;
  --warn: #ffd23a;
  --s1: #3b8fe6;       /* chart series 1: model */
  --s2: #c98a1e;       /* chart series 2: observed / plan */
  --div-neg: #d9534f;  /* diverging: loses */
  --div-mid: #8a94a6;  /* diverging: neutral */
  --div-pos: #3fae66;  /* diverging: gains */
  --grid: rgba(255, 255, 255, .07);
  --f: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  --r: 10px;
  color-scheme: dark;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 16px; }
body { margin: 0; background: var(--bg); background-image: radial-gradient(1200px 600px at 70% -10%, rgba(59,156,255,.10), transparent 60%);
  color: var(--fg); font-family: var(--f); font-size: 15px; line-height: 1.62; -webkit-font-smoothing: antialiased; overflow-x: hidden; }
a { color: var(--hi); text-decoration: none; } a:hover { text-decoration: underline; }
code, .num, .mono { font-family: var(--mono); font-size: .86em; }
code { background: var(--fill); padding: 1px 5px; border-radius: 5px; color: #d9e6f5; word-break: break-word; }
.layout { display: grid; grid-template-columns: 250px minmax(0, 1fr); max-width: 1220px; margin: 0 auto; gap: 40px; padding: 0 28px; }
aside.toc { position: sticky; top: 0; align-self: start; height: 100vh; overflow-y: auto; padding: 28px 0 24px; }
.toc .brand { font-weight: 800; letter-spacing: -.01em; font-size: 15px; }
.toc .brand span { color: var(--hi); }
.toc .sub { color: var(--mute); font-size: 12px; margin: 2px 0 18px; font-family: var(--mono); }
.toc ol { list-style: none; padding: 0; margin: 0; counter-reset: s; }
.toc li a { display: flex; gap: 10px; padding: 5px 10px; border-radius: 7px; color: var(--dim); font-size: 13px; line-height: 1.35; }
.toc li a:hover { background: var(--fill); text-decoration: none; color: var(--fg); }
.toc li a.on { background: var(--fill-hi); color: var(--fg); box-shadow: inset 2px 0 0 var(--accent); }
.toc li a b { font-family: var(--mono); font-weight: 500; color: var(--mute); min-width: 18px; }
main { min-width: 0; padding: 40px 0 120px; max-width: 900px; }
header.hd { border-bottom: 1px solid var(--line); padding-bottom: 22px; margin-bottom: 8px; }
.kicker { font-family: var(--mono); font-size: 12px; color: var(--hi); letter-spacing: .08em; text-transform: uppercase; }
h1 { font-size: 34px; line-height: 1.15; letter-spacing: -.02em; margin: 8px 0 10px; font-weight: 800; }
.meta { color: var(--mute); font-size: 12.5px; font-family: var(--mono); }
section { padding-top: 34px; border-top: 1px solid var(--line); margin-top: 34px; }
section:first-of-type { border-top: 0; margin-top: 0; }
h2 { font-size: 22px; letter-spacing: -.01em; margin: 0 0 14px; display: flex; gap: 12px; align-items: baseline; }
h2 .sn { font-family: var(--mono); color: var(--accent); font-weight: 500; font-size: 17px; }
h3 { font-size: 15.5px; margin: 26px 0 8px; color: var(--fg); }
p { margin: 10px 0; color: #dde6f2; }
.lede { font-size: 16px; color: var(--fg); }
.note, .note2 { color: var(--dim); font-size: 13px; }
.cite a { font-family: var(--mono); font-size: 12px; }
.katex { font-size: 1.06em; }
.katex-display { overflow-x: auto; overflow-y: hidden; padding: 12px 6px; margin: 14px 0; background: var(--fill); border: 1px solid var(--line); border-radius: var(--r); }
.katex-display > .katex { color: #eef4fb; }
.tw { overflow-x: auto; margin: 12px 0 16px; border: 1px solid var(--line); border-radius: var(--r); background: rgba(255,255,255,.02); }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { text-align: left; padding: 8px 11px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { color: var(--mute); font-weight: 600; font-size: 11.5px; text-transform: uppercase; letter-spacing: .04em; background: rgba(255,255,255,.03); white-space: nowrap; }
tr:last-child td { border-bottom: 0; }
td.num, th.num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
td.pos { color: var(--good); } td.neg { color: var(--bad); }
.ptab td:first-child { white-space: nowrap; }
.ptab td:first-child code { font-size: 11.5px; }
.pv { font-family: var(--mono); font-size: 12px; min-width: 120px; max-width: 260px; overflow-wrap: anywhere; }
.ptab td:last-child { min-width: 200px; }
.rng { color: var(--mute); font-size: 11px; }
.rec { font-family: var(--mono); font-size: 12px; min-width: 220px; }
.srct { color: var(--dim); font-size: 12px; }
.badge { font-family: var(--mono); font-size: 10.5px; padding: 2px 7px; border-radius: 999px; border: 1px solid var(--line-hi); white-space: nowrap; }
.badge.data { color: var(--good); border-color: rgba(79,220,122,.35); }
.badge.literature { color: var(--hi); border-color: rgba(127,211,255,.35); }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin: 18px 0; }
.stats div { background: var(--fill); border: 1px solid var(--line); border-radius: var(--r); padding: 12px 14px; }
.stats b { display: block; font-family: var(--mono); font-size: 21px; font-weight: 600; color: var(--fg); }
.stats span { color: var(--mute); font-size: 12px; }
figure.fig { margin: 16px 0; padding: 14px; background: var(--fill); border: 1px solid var(--line); border-radius: var(--r); }
figure.fig:empty { display: none; }
figcaption { color: var(--dim); font-size: 12.5px; margin-top: 8px; }
.ctitle { font-size: 13px; font-weight: 600; margin: 0 0 6px; }
.legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: var(--dim); margin: 2px 0 6px; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
svg { display: block; width: 100%; height: auto; }
svg text { font-family: var(--f); }
.ax text, .tick { fill: var(--mute); font-size: 11px; font-family: var(--mono); }
.gl { stroke: var(--grid); }
.dl { fill: var(--dim); font-size: 11px; font-family: var(--mono); }
.pipe .bx rect { fill: var(--bg2); stroke: var(--line-hi); }
.pipe .bx.k rect { stroke: var(--accent); }
.pipe .bx.src rect { fill: rgba(255,255,255,.03); stroke-dasharray: 3 3; }
.pipe .bx.gate rect { stroke: #b46cff; }
.pipe .t1 { fill: var(--fg); font-size: 12.5px; font-weight: 600; text-anchor: middle; }
.pipe .t2 { fill: var(--dim); font-size: 10px; font-family: var(--mono); text-anchor: middle; }
.pipe .lbl { fill: var(--hi); }
.pipe .ar { stroke: var(--dim); stroke-width: 1.4; fill: none; }
.pipe .ar.src { stroke: var(--mute); stroke-dasharray: 2 3; }
.pipe .ar.gate { stroke: #b46cff; }
.pipe .ar.loop { stroke: var(--hi); stroke-dasharray: 4 3; }
.pipe .ahp { fill: var(--dim); }
ol.refs { list-style: none; padding: 0; margin: 0; font-size: 13px; }
ol.refs li { display: grid; grid-template-columns: 40px minmax(0, 1fr); gap: 4px; padding: 7px 0; border-bottom: 1px solid var(--line); color: #dde6f2; }
ol.refs .refn { font-family: var(--mono); color: var(--mute); }
ol.refs .url { display: block; font-family: var(--mono); font-size: 11px; word-break: break-all; color: var(--hi); opacity: .85; }
.gaps { border: 1px solid rgba(255,210,58,.25); background: rgba(255,210,58,.05); border-radius: var(--r); padding: 4px 18px 8px; margin-top: 22px; }
.gaps h3 { color: var(--warn); }
.gaps li { margin: 6px 0; color: #dde6f2; font-size: 14px; }
#tip { position: fixed; pointer-events: none; z-index: 50; background: #0f1f3b; border: 1px solid var(--line-hi); border-radius: 8px; padding: 8px 10px; font-size: 12px;
  color: var(--fg); box-shadow: 0 10px 30px rgba(0,0,0,.4); max-width: 320px; display: none; line-height: 1.45; }
#tip .tk { color: var(--mute); }
#tip table { font-size: 11.5px; margin-top: 4px; } #tip td, #tip th { padding: 2px 6px; border: 0; white-space: nowrap; }
.sortable th { cursor: pointer; user-select: none; }
.sortable th:hover { color: var(--fg); }
.sortable th.asc::after { content: " ▲"; } .sortable th.desc::after { content: " ▼"; }
.swatch { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 6px; vertical-align: 0; }
#eqmap svg { max-width: 600px; margin: 0 auto; }
.eqm .bay { fill: #0d2747; stroke: rgba(127,211,255,.25); }
.eqm .land { fill: #13233d; stroke: rgba(255,255,255,.10); }
.eqm .ocean { fill: #081a33; }
.eqm .study { fill: none; stroke: var(--hi); stroke-width: 1.6; stroke-dasharray: 3 2; }
.eqm .bub { stroke: var(--bg); stroke-width: 2; cursor: pointer; }
.eqm .bub:hover { stroke: var(--fg); }
.eqm .rl { fill: var(--fg); font-size: 12px; font-weight: 600; pointer-events: none; }
.eqm .rv { fill: var(--dim); font-size: 10.5px; font-family: var(--mono); pointer-events: none; }
.eqm .wl { fill: rgba(127,211,255,.45); font-size: 11px; font-style: italic; }
.dscale { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--mute); font-family: var(--mono); margin-top: 6px; flex-wrap: wrap; }
.dscale .bar { width: 160px; height: 9px; border-radius: 5px; background: linear-gradient(90deg, var(--div-neg), var(--div-mid), var(--div-pos)); }
/* sticky losers strip */
#losers { position: fixed; right: 16px; top: 16px; width: 270px; z-index: 40; background: rgba(12, 24, 48, .94); border: 1px solid var(--line-hi);
  border-radius: 12px; padding: 12px 14px; box-shadow: 0 10px 30px rgba(0,0,0,.35); backdrop-filter: blur(8px); font-size: 12.5px; }
#losers h4 { margin: 0 0 6px; font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--mute); display: flex; justify-content: space-between; gap: 8px; }
#losers h4 a { text-transform: none; letter-spacing: 0; font-weight: 500; }
#losers .row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; padding: 3px 0; border-bottom: 1px dashed var(--line); }
#losers .row:last-child { border-bottom: 0; }
#losers .g { color: var(--fg); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
#losers .v { font-family: var(--mono); font-size: 11.5px; text-align: right; white-space: nowrap; }
#losers .v.l { color: var(--bad); } #losers .v.w { color: var(--good); }
#losers .sub { color: var(--mute); font-size: 10.5px; font-family: var(--mono); }
#losers .sep { margin-top: 8px; }
@media (max-width: 1500px) {
  #losers { top: auto; bottom: 0; right: 0; left: 0; width: auto; border-radius: 12px 12px 0 0; padding: 8px 16px; display: grid;
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); gap: 4px 22px; max-height: 40vh; overflow-y: auto; }
  #losers .sep { margin-top: 0; }
  #losers .row { padding: 1px 0; }
  main { padding-bottom: 210px; }
}
@media (max-width: 900px) {
  .layout { grid-template-columns: minmax(0, 1fr); gap: 0; padding: 0 16px; }
  aside.toc { position: static; height: auto; padding: 22px 0 0; }
  .toc ol { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 8px; }
  main { padding-top: 16px; }
  h1 { font-size: 27px; }
}
@media (max-width: 560px) {
  #losers { grid-template-columns: minmax(0, 1fr); }
  #losers .wins { display: none; }
  .toc ol { grid-template-columns: minmax(0, 1fr); }
}
</style>
</head>
<body>
<div class="layout">
<aside class="toc" aria-label="Contents">
  <div class="brand">The Human <span>Project</span></div>
  <div class="sub">Methods · technical appendix</div>
  <ol>{{TOC}}</ol>
</aside>
<main>
<header class="hd">
  <div class="kicker">Technical appendix</div>
  <h1>Methods: an agent-swarm model of a weekday in FiDi / SoMa</h1>
  <div class="meta">Engine v0.2 · numbers generated {{BUILT}} by <code>scripts/build_methods.py</code> from the engine, <code>research/parameters/parameters.json</code> and <code>research/validation/validation.json</code></div>
</header>
{{SECTIONS}}
</main>
</div>
<div id="losers" aria-label="Biggest losers and winners of the hero plan"></div>
<div id="tip"></div>
<script>
const DATA = /*__METHODS_DATA__*/;
</script>
<script>
(function () {
const $ = (s, r = document) => r.querySelector(s);
const NS = 'http://www.w3.org/2000/svg';
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const fmt$ = (x, d = 0) => (x < 0 ? '−' : x > 0 ? '+' : '') + '$' + Math.abs(x).toLocaleString('en-US', { maximumFractionDigits: d, minimumFractionDigits: d });
const fmtK$ = (x) => { const a = Math.abs(x), s = x < 0 ? '−' : x > 0 ? '+' : ''; return a >= 1e6 ? s + '$' + (a / 1e6).toFixed(2) + 'M' : a >= 1e3 ? s + '$' + (a / 1e3).toFixed(1) + 'k' : s + '$' + a.toFixed(0); };
const fmtN = (x) => Math.round(x).toLocaleString('en-US');
const pp = (x) => (x * 100).toFixed(1) + '%';
const sgn = (x, d = 2) => Math.abs(x) < 0.5 * Math.pow(10, -d) ? (0).toFixed(d) : (x < 0 ? '−' : '+') + Math.abs(x).toFixed(d);
const TIER = { low: 'low income', mid: 'mid income', high: 'high income' };
const tip = $('#tip');
function showTip(html, ev) { tip.innerHTML = html; tip.style.display = 'block'; moveTip(ev); }
function moveTip(ev) { const w = tip.offsetWidth, h = tip.offsetHeight; let x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + w > innerWidth - 8) x = ev.clientX - w - 14; if (y + h > innerHeight - 8) y = ev.clientY - h - 14; tip.style.left = Math.max(8, x) + 'px'; tip.style.top = Math.max(8, y) + 'px'; }
function hideTip() { tip.style.display = 'none'; }
function el(tag, attrs, parent, text) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (text != null) e.textContent = text; if (parent) parent.appendChild(e); return e; }
function hover(node, html) { node.addEventListener('mouseenter', (e) => showTip(html, e)); node.addEventListener('mousemove', moveTip); node.addEventListener('mouseleave', hideTip); }
function legend(items) { return '<div class=legend>' + items.map(([c, t]) => `<span><i style="background:${c}"></i>${t}</span>`).join('') + '</div>'; }

// ── Figure: MSA gaps ──
(function gapChart() {
  const f = $('#fig-gap'); if (!f) return;
  const b = DATA.settle.baseline.gaps, p = DATA.settle.plan.gaps;
  f.innerHTML = '<div class=ctitle>Figure 3. Relative flow change per replanning day (Eq. 15)</div>' + legend([[css('--s1'), 'Baseline'], [css('--s2'), '2nd St car-free plan']]);
  const W = 660, H = 240, m = { l: 46, r: 118, t: 12, b: 34 };
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'MSA gap per day' }, f);
  const ymax = Math.max(...b, ...p, 0.03) * 1.15, n = b.length;
  const X = (i) => m.l + (i) * (W - m.l - m.r) / (n - 1), Y = (v) => H - m.b - v / ymax * (H - m.t - m.b);
  for (let v = 0; v <= ymax; v += 0.02) { el('line', { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), class: 'gl' }, svg); el('text', { x: m.l - 8, y: Y(v) + 4, 'text-anchor': 'end', class: 'tick' }, svg, v.toFixed(2)); }
  for (let i = 0; i < n; i++) el('text', { x: X(i), y: H - m.b + 18, 'text-anchor': 'middle', class: 'tick' }, svg, 'day ' + (i + 1));
  el('line', { x1: m.l, x2: W - m.r, y1: Y(0.03), y2: Y(0.03), stroke: css('--warn'), 'stroke-dasharray': '5 4', 'stroke-width': 1.2 }, svg);
  el('text', { x: m.l + 6, y: Y(0.03) - 6, class: 'dl', fill: css('--warn') }, svg, 'convergence criterion 0.03');
  [[b, css('--s1'), 'Baseline'], [p, css('--s2'), 'Plan']].forEach(([s, c, name]) => {
    el('path', { d: s.map((v, i) => (i ? 'L' : 'M') + X(i) + ' ' + Y(v)).join(' '), fill: 'none', stroke: c, 'stroke-width': 2 }, svg);
    s.forEach((v, i) => { const g = el('g', {}, svg); el('circle', { cx: X(i), cy: Y(v), r: 12, fill: 'transparent' }, g); el('circle', { cx: X(i), cy: Y(v), r: 4.5, fill: c, stroke: css('--bg2'), 'stroke-width': 2 }, g);
      hover(g, `<b>${name}</b>, day ${i + 1}<br><span class=tk>gap</span> ${v.toFixed(4)}`); });
    el('text', { x: X(n - 1) + 8, y: Y(s[n - 1]) + (name === 'Plan' ? -4 : 12), class: 'dl' }, svg, name + ' ' + s[n - 1].toFixed(4));
  });
})();

// ── Figure: calibration ──
(function calChart() {
  const f = $('#fig-cal'); if (!f) return;
  const t = DATA.calibration.target, mo = DATA.calibration.modeled, tot = Object.values(mo).reduce((a, b) => a + b, 0);
  const modes = ['car', 'transit', 'walk', 'bike'];
  f.innerHTML = '<div class=ctitle>Figure 2. Worker mode split after calibration</div>' + legend([[css('--s1'), 'Model (baseline)'], [css('--s2'), 'Target (assumed)']]);
  const W = 640, row = 44, H = modes.length * row + 30, l = 70, r = 60;
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Mode split model vs target' }, f);
  const X = (v) => l + v / 0.6 * (W - l - r);
  for (let v = 0; v <= 0.6001; v += 0.1) { el('line', { x1: X(v), x2: X(v), y1: 4, y2: H - 22, class: 'gl' }, svg); el('text', { x: X(v), y: H - 6, 'text-anchor': 'middle', class: 'tick' }, svg, (v * 100).toFixed(0) + '%'); }
  modes.forEach((k, i) => {
    const y = 8 + i * row; el('text', { x: l - 10, y: y + 18, 'text-anchor': 'end', class: 'tick', fill: css('--dim') }, svg, k);
    [[mo[k] / tot, css('--s1'), 'Model'], [t[k], css('--s2'), 'Target (assumed)']].forEach(([v, c, nm], j) => {
      const g = el('g', {}, svg); const yy = y + j * 15;
      el('rect', { x: l, y: yy - 2, width: W - l - r, height: 15, fill: 'transparent' }, g);
      el('rect', { x: l, y: yy, width: Math.max(1, X(v) - l), height: 12, rx: 3, fill: c }, g);
      el('text', { x: X(v) + 6, y: yy + 10, class: 'dl' }, g, pp(v));
      hover(g, `<b>${k}</b> · ${nm}<br>${pp(v)}`);
    });
  });
})();

// ── Figure: validation dumbbells ──
(function valChart() {
  const f = $('#fig-val'); if (!f) return;
  const want = [['Muni speed on Market St', 'Muni speed, Market St'], ['Worst parallel-street slowdown', 'Worst parallel street'], ['Cycling on Market St', 'Cycling, Market St'],
    ['Foot traffic on the treated street', 'Footfall, 2nd St'], ['Revenue of', 'Fronting revenue, 2nd St']];
  const rows = want.map(([q, lab]) => { const r = DATA.validation.find((x) => x.quantity.startsWith(q)); return r ? { lab, m: r.model, t: r.target, q: r.quantity } : null; }).filter(Boolean);
  f.innerHTML = '<div class=ctitle>Figure 5. Validation: model vs observed change (not fitted)</div>' + legend([[css('--s1'), 'Model'], [css('--s2'), 'Observed / literature']]);
  const W = 660, row = 34, H = rows.length * row + 34, l = 185, r = 125;
  const lo = Math.min(0, ...rows.map((d) => Math.min(d.m, d.t))), hi = Math.max(...rows.map((d) => Math.max(d.m, d.t))) * 1.08;
  const X = (v) => l + (v - lo) / (hi - lo) * (W - l - r);
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Validation dumbbell chart' }, f);
  for (let v = 0; v <= hi; v += 0.2) { el('line', { x1: X(v), x2: X(v), y1: 4, y2: H - 24, class: 'gl' }, svg); el('text', { x: X(v), y: H - 8, 'text-anchor': 'middle', class: 'tick' }, svg, '+' + (v * 100).toFixed(0) + '%'); }
  rows.forEach((d, i) => {
    const y = 16 + i * row, g = el('g', {}, svg);
    el('rect', { x: 0, y: y - 14, width: W, height: row - 4, fill: 'transparent' }, g);
    el('text', { x: l - 12, y: y + 4, 'text-anchor': 'end', class: 'tick', fill: css('--dim') }, g, d.lab);
    el('line', { x1: X(d.m), x2: X(d.t), y1: y, y2: y, stroke: css('--line-hi'), 'stroke-width': 2 }, g);
    el('circle', { cx: X(d.t), cy: y, r: 6, fill: css('--s2'), stroke: css('--bg2'), 'stroke-width': 2 }, g);
    el('circle', { cx: X(d.m), cy: y, r: 6, fill: css('--s1'), stroke: css('--bg2'), 'stroke-width': 2 }, g);
    el('text', { x: Math.max(X(d.m), X(d.t)) + 12, y: y + 4, class: 'dl' }, g, sgn(d.m * 100, 1) + '% vs ' + sgn(d.t * 100, 1) + '%');
    hover(g, `<b>${d.q}</b><br><span class=tk>model</span> ${sgn(d.m * 100, 1)}% · <span class=tk>observed</span> ${sgn(d.t * 100, 1)}%`);
  });
})();

// ── Figure: popular-times r ──
(function popChart() {
  const f = $('#fig-pop'); if (!f) return;
  const rows = DATA.validation.filter((x) => x.quantity.startsWith('Hourly visit profile correlation')).map((x) => ({ c: x.quantity.split(': ')[1], r: x.model, t: x.target }));
  f.innerHTML = '<div class=ctitle>Figure 6. Pearson r of modeled hourly visits vs Google popular times, by category</div>';
  const W = 640, row = 28, H = rows.length * row + 30, l = 90, r = 50, X = (v) => l + v * (W - l - r);
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Popular times correlation' }, f);
  for (let v = 0; v <= 1.0001; v += 0.2) { el('line', { x1: X(v), x2: X(v), y1: 4, y2: H - 22, class: 'gl' }, svg); el('text', { x: X(v), y: H - 6, 'text-anchor': 'middle', class: 'tick' }, svg, v.toFixed(1)); }
  rows.forEach((d, i) => { const y = 8 + i * row, g = el('g', {}, svg);
    el('rect', { x: 0, y: y - 4, width: W, height: row, fill: 'transparent' }, g);
    el('text', { x: l - 10, y: y + 12, 'text-anchor': 'end', class: 'tick', fill: css('--dim') }, g, d.c.replace('_', ' '));
    el('rect', { x: l, y: y + 2, width: X(d.r) - l, height: 14, rx: 3, fill: css('--s1') }, g);
    el('text', { x: X(d.r) + 6, y: y + 13, class: 'dl' }, g, d.r.toFixed(2));
    hover(g, `<b>${d.c}</b><br>r = ${d.r.toFixed(3)} <span class=tk>(reference ${d.t})</span>`); });
  const t = rows.length ? rows[0].t : 0.8; el('line', { x1: X(t), x2: X(t), y1: 2, y2: H - 22, stroke: css('--warn'), 'stroke-dasharray': '4 3' }, svg);
  el('text', { x: X(t) + 4, y: H - 26, class: 'dl', fill: css('--warn') }, svg, 'r = ' + t);
})();

// ── Equity: diverging scale ──
const L = DATA.ledger;
const maxAbs = Math.max(...L.map((g) => Math.abs(g.dcs_usd_yr_pp || 0)), 1e-9);
function hex2rgb(h) { const n = parseInt(h.replace('#', ''), 16); return [n >> 16 & 255, n >> 8 & 255, n & 255]; }
function mix(a, b, t) { const A = hex2rgb(a), B = hex2rgb(b); return `rgb(${A.map((x, i) => Math.round(x + (B[i] - x) * t)).join(',')})`; }
function divColor(v) { const t = Math.max(-1, Math.min(1, v / maxAbs)); return t < 0 ? mix(css('--div-mid'), css('--div-neg'), -t) : mix(css('--div-mid'), css('--div-pos'), t); }
function gname(g) { return `${g.region_name} · ${TIER[g.tier]}`; }

// ── Equity map ──
(function eqMap() {
  const host = $('#eqmap'); if (!host) return;
  const POS = { north_bay: [190, 80], sf_north: [288, 180], sf_west: [200, 252], sf_southeast_mission: [262, 326], sf_in_area: [305, 246],
    east_bay: [480, 205], peninsula_south_bay: [330, 440], other: [562, 448] };
  const LBL = { sf_north: 'left', sf_west: 'left', sf_in_area: 'right' };
  const W = 640, H = 520;
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, class: 'eqm', role: 'img', 'aria-label': 'Equity map of home regions' }, host);
  el('rect', { x: 0, y: 0, width: W, height: H, class: 'ocean', rx: 8 }, svg);
  // schematic land masses (not to scale)
  el('path', { class: 'land', d: 'M95 20 L330 20 L318 120 L292 150 L250 165 L214 152 L190 130 L150 140 L120 112 L100 70 Z' }, svg);               // North Bay / Marin
  el('path', { class: 'land', d: 'M140 176 L300 168 L322 214 L326 262 L344 330 L384 400 L432 470 L452 512 L262 512 L216 450 L180 380 L150 300 Z' }, svg); // SF + Peninsula
  el('path', { class: 'land', d: 'M360 40 L630 40 L630 512 L520 512 L470 420 L420 330 L380 250 L372 170 L350 110 Z' }, svg);                    // East Bay
  el('path', { class: 'bay', d: 'M318 120 L350 110 L372 170 L380 250 L420 330 L470 420 L520 512 L452 512 L430 470 L380 400 L340 330 L318 260 L320 214 L300 172 L292 150 Z' }, svg);
  el('text', { x: 40, y: 330, class: 'wl' }, svg, 'Pacific');
  el('text', { x: 360, y: 300, class: 'wl', transform: 'rotate(60 360 300)' }, svg, 'SF Bay');
  el('rect', { x: 279, y: 222, width: 52, height: 48, class: 'study' }, svg);
  el('text', { x: 305, y: 284, class: 'rv', 'text-anchor': 'middle', fill: css('--hi') }, svg, 'study area');
  el('rect', { x: 505, y: 405, width: 115, height: 96, rx: 8, fill: 'rgba(255,255,255,.03)', stroke: 'rgba(255,255,255,.12)', 'stroke-dasharray': '3 3' }, svg);
  const by = {}; L.forEach((g) => { (by[g.region] = by[g.region] || []).push(g); });
  const maxP = Math.max(...Object.values(by).map((a) => a.reduce((s, g) => s + g.people, 0)));
  const regions = DATA.regions.slice().sort((a, b) => (by[b.key] || []).reduce((s, g) => s + g.people, 0) - (by[a.key] || []).reduce((s, g) => s + g.people, 0));
  regions.forEach((r) => {
    const gs = by[r.key] || []; if (!gs.length) return;
    const ppl = gs.reduce((s, g) => s + g.people, 0), tot = gs.reduce((s, g) => s + (g.dcs_usd_yr_total || 0), 0), per = tot / ppl * 1;
    const perpp = gs.reduce((s, g) => s + (g.dcs_usd_yr_pp || 0) * g.people, 0) / ppl;
    const [x, y] = POS[r.key]; const rad = 7 + 40 * Math.sqrt(ppl / maxP);
    const g = el('g', {}, svg);
    el('circle', { cx: x, cy: y, r: rad, fill: divColor(perpp), class: 'bub', 'fill-opacity': .92 }, g);
    const side = LBL[r.key], lx = side === 'left' ? x - rad - 8 : side === 'right' ? x + rad + 8 : x, ly = side ? y - 2 : y + rad + 14, an = side === 'left' ? 'end' : side === 'right' ? 'start' : 'middle';
    el('text', { x: lx, y: ly, class: 'rl', 'text-anchor': an }, svg, r.name);
    el('text', { x: lx, y: ly + 13, class: 'rv', 'text-anchor': an }, svg, fmt$(perpp, 2) + '/yr pp');
    const tiers = gs.slice().sort((a, b) => ['low', 'mid', 'high'].indexOf(a.tier) - ['low', 'mid', 'high'].indexOf(b.tier));
    const tbl = '<table><tr><th>tier</th><th>people</th><th>Δ$/yr pp</th><th>Δ min/day</th><th>car</th></tr>' + tiers.map((t) =>
      `<tr><td><span class=swatch style="background:${divColor(t.dcs_usd_yr_pp)}"></span>${t.tier}</td><td>${fmtN(t.people)}</td><td>${fmt$(t.dcs_usd_yr_pp, 2)}</td><td>${t.dt_min_day == null ? '–' : sgn(t.dt_min_day)}</td><td>${pp(t.car_b)}→${pp(t.car_p)}</td></tr>`).join('') + '</table>';
    hover(g, `<b>${r.name}</b> <span class=tk>${fmtN(ppl)} commuters</span><br>group total ${fmtK$(tot)}/yr · mean ${fmt$(perpp, 2)}/yr per person` + tbl);
  });
  const sc = document.createElement('div'); sc.className = 'dscale';
  sc.innerHTML = `<span>${fmt$(-maxAbs, 2)}</span><span class=bar></span><span>${fmt$(maxAbs, 2)}</span><span>per person per year (symmetric scale)</span>`;
  host.appendChild(sc);
})();

// ── Ledger table ──
(function ledger() {
  const t = $('#ledger'); if (!t) return;
  const tb = t.tBodies[0]; let key = 'dcs_usd_yr_pp', dir = 1;
  function render() {
    const rows = L.slice().sort((a, b) => { const x = a[key], y = b[key]; return (typeof x === 'string' ? x.localeCompare(y) : (x ?? 0) - (y ?? 0)) * dir; });
    tb.innerHTML = rows.map((g) => `<tr><td><span class=swatch style="background:${divColor(g.dcs_usd_yr_pp)}"></span>${g.region_name}</td><td>${g.tier}</td><td class=num>${fmtN(g.people)}</td>
      <td class=num>${pp(g.car_b)} → ${pp(g.car_p)}</td><td class=num>${fmtN(g.switchers)}</td><td class=num>${g.dt_min_day == null ? '–' : sgn(g.dt_min_day)}</td>
      <td class=num>${g.dcost_usd_day == null ? '–' : fmt$(g.dcost_usd_day, 2)}</td><td class="num ${g.dcs_usd_yr_pp < 0 ? 'neg' : g.dcs_usd_yr_pp > 0 ? 'pos' : ''}">${fmt$(g.dcs_usd_yr_pp, 2)}</td>
      <td class="num ${g.dcs_usd_yr_total < 0 ? 'neg' : g.dcs_usd_yr_total > 0 ? 'pos' : ''}">${fmtK$(g.dcs_usd_yr_total)}</td></tr>`).join('');
    t.querySelectorAll('th').forEach((th) => { th.classList.toggle('asc', th.dataset.k === key && dir > 0); th.classList.toggle('desc', th.dataset.k === key && dir < 0); });
  }
  t.querySelectorAll('th').forEach((th) => th.addEventListener('click', () => { if (key === th.dataset.k) dir = -dir; else { key = th.dataset.k; dir = 1; } render(); }));
  render();
})();

// ── Sticky losers / winners strip ──
(function strip() {
  const box = $('#losers'); const s = L.filter((g) => g.dcs_usd_yr_pp != null).slice().sort((a, b) => a.dcs_usd_yr_pp - b.dcs_usd_yr_pp);
  const line = (g, cls) => `<div class=row title="${gname(g)}: ${fmtN(g.people)} people, group ${fmtK$(g.dcs_usd_yr_total)}/yr"><span class=g>${g.region_name} <span class=sub>${g.tier}</span></span><span class="v ${cls}">${fmt$(g.dcs_usd_yr_pp, 2)}/yr, ${g.dt_min_day == null ? '' : sgn(g.dt_min_day) + ' min'}</span></div>`;
  const lose = s.filter((g) => g.dcs_usd_yr_pp < 0).slice(0, 4), win = s.filter((g) => g.dcs_usd_yr_pp > 0).slice(-3).reverse();
  box.innerHTML = `<div><h4><span>Biggest losers · 2nd St car-free</span><a href="#equity">ledger ↓</a></h4>${lose.map((g) => line(g, 'l')).join('')}</div>` +
    `<div class="sep wins"><h4><span>Top winners</span></h4>${win.map((g) => line(g, 'w')).join('')}<div class=sub style="margin-top:4px">per commuter, commute surplus (Eq. 28)</div></div>`;
})();

// ── TOC highlight ──
const links = [...document.querySelectorAll('.toc a')];
const io = new IntersectionObserver((es) => { es.forEach((e) => { if (e.isIntersecting) links.forEach((a) => a.classList.toggle('on', a.getAttribute('href') === '#' + e.target.id)); }); }, { rootMargin: '-15% 0px -75% 0px' });
document.querySelectorAll('main section').forEach((s) => io.observe(s));

// ── KaTeX ──
function math() { if (!window.renderMathInElement) return false;
  renderMathInElement(document.querySelector('main'), { delimiters: [{ left: '$$', right: '$$', display: true }, { left: '\\(', right: '\\)', display: false }], throwOnError: false, strict: 'ignore' }); return true; }
window.addEventListener('DOMContentLoaded', () => { if (!math()) window.addEventListener('load', math); });
})();
</script>
</body>
</html>
"""


def render(D, P, V):
    R = Refs(FIXED_REFS, P)
    secs = sections(D, P, V, R)
    lit_ids = ["matsim", "sheffi", "tm1cap", "tm1mc", "sfcta_asim", "usdot_vtt", "litman", "osm", "lodes", "acs", "datasf_lu", "apify", "bart", "sfmta_bike", "caltrans", "kastle", "gtfs"]
    for rid in lit_ids:
        R._key(rid)
    secs.append(("references", "References", '<p>Literature, data and parameter sources in order of first citation. Parameter sources are taken from '
                 '<code>research/parameters/parameters.json</code> (status data or literature only).</p>' + R.html()))
    toc = "".join(f'<li><a href="#{sid}"><b>{i}</b><span>{esc(t)}</span></a></li>' for i, (sid, t, _) in enumerate(secs, 1))
    body = "".join(f'<section id="{sid}"><h2><span class=sn>{i}</span>{esc(t)}</h2>{h}</section>' for i, (sid, t, h) in enumerate(secs, 1))
    blob = {"settle": D["settle"], "calibration": D["calibration"], "ledger": D["ledger"], "regions": D["regions"],
            "validation": [{"quantity": r["quantity"], "model": r["model"], "target": r["target"]} for r in V]}
    html = TEMPLATE.replace("{{TOC}}", toc).replace("{{SECTIONS}}", body).replace("{{BUILT}}", D["built"])
    return html.replace(TEMPLATE_MARK, json.dumps(blob, separators=(",", ":")).replace("</", "<\\/"))


if __name__ == "__main__":
    args = sys.argv[1:]
    cache = Path(args[args.index("--cache") + 1]) if "--cache" in args else None
    if cache and cache.exists():
        data = json.loads(cache.read_text())
    else:
        data = collect()
        if cache:
            cache.write_text(json.dumps(data, indent=1))
    params, val = research()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(data, params, val))
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.0f} KB)")
