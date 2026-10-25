"""Traffic counts in the bbox -> data/backend/traffic_counts.json

DataSF (data.sf.gov) has no general SFMTA motor-vehicle count dataset (catalog searched 2026-10-24 for
"traffic count", "traffic volume", "vehicle counts", "ADT", "volume"). Used instead:
  1. Caltrans Traffic Census AADT points (state highways: I-80 / Bay Bridge approach, ramps)
     https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/Traffic_AADT/FeatureServer/0
  2. DataSF "Bike Volume - Manual Counts" (v4v2-5x7s): SFMTA PM-peak bicycle counts 2006-2017
Cache: data/cache/caltrans/aadt_bbox.json, data/cache/datasf/v4v2-5x7s_bbox_p0.json
"""
import json
import math
import re
import sys

import common as c
from landuse import Grid

AADT_URL = "https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/Traffic_AADT/FeatureServer/0/query"
BIKE_DS = "v4v2-5x7s"
PAD = 0.002  # deg, fetch slightly beyond bbox, keep only within bbox + 40 m below


def fetch_aadt(offline):
    p = c.cache_path("caltrans", "aadt_bbox.json")
    if p.exists():
        return json.loads(p.read_text())
    if offline:
        raise RuntimeError("aadt not cached")
    params = {"where": "1=1", "geometry": f"{c.W - PAD},{c.S - PAD},{c.E + PAD},{c.N + PAD}",
              "geometryType": "esriGeometryEnvelope", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
              "outFields": "*", "outSR": 4326, "f": "json"}
    with c.http_client() as cl:
        r = cl.get(AADT_URL, params=params)
        r.raise_for_status()
        d = r.json()
    p.write_text(json.dumps(d))
    c.write_params(p, dict(params, url=AADT_URL))
    c.log_usage("caltrans", f"AADT bbox query ({len(d.get('features', []))} pts)", "free")
    return d


def fetch_bike(offline):
    p = c.cache_path("datasf", f"{BIKE_DS}_bbox_p0.json")
    if p.exists():
        return json.loads(p.read_text())
    if offline:
        raise RuntimeError("bike not cached")
    env = c.load_env()
    params = {"$where": f"within_box(shape, {c.N + PAD}, {c.W - PAD}, {c.S - PAD}, {c.E + PAD})", "$limit": 5000}
    with c.http_client(headers={"X-App-Token": env.get("SODA_APP_TOKEN", "")}) as cl:
        r = cl.get(f"https://data.sf.gov/resource/{BIKE_DS}.json", params=params)
        r.raise_for_status()
        d = r.json()
    p.write_text(json.dumps(d))
    c.write_params(p, dict(params, url=f"https://data.sf.gov/resource/{BIKE_DS}.json"))
    c.log_usage("datasf", f"{BIKE_DS} bbox ({len(d)} rows)", "free")
    return d


ABBR = {"st": "street", "ave": "avenue", "av": "avenue", "blvd": "boulevard", "dr": "drive", "pl": "place",
        "ter": "terrace", "hwy": "highway", "fwy": "freeway", "rd": "road", "ln": "lane", "ctr": "center"}


def nname(s):
    s = re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())
    toks = [ABBR.get(t, t) for t in s.split()]
    return " ".join(toks)


def street_core(s):
    t = nname(s).split()
    return " ".join(x for x in t if x not in ("street", "avenue", "boulevard", "the", "of", "place", "drive"))


def build_edge_index(world):
    g = Grid(50)
    for i, e in enumerate(world["edges"]):
        xs = [p[0] for p in e["p"]]
        zs = [p[1] for p in e["p"]]
        g.add(i, (min(xs), min(zs), max(xs), max(zs)))
    return g


def nearest_edge(world, g, x, z, names=(), classes=None, maxd=40.0):
    best = None
    for ei in g.query(x, z, maxd):
        e = world["edges"][ei]
        d = c.polyline_dist(x, z, e["p"])
        if d > maxd:
            continue
        en = street_core(world["names"][e["n"]])
        nm = bool(en) and any(street_core(n) and (street_core(n) in en or en in street_core(n)) for n in names)
        cls_ok = classes is None or e.get("c") in classes
        score = d - (25 if nm else 0) - (15 if cls_ok and classes else 0)
        if best is None or score < best[0]:
            best = (score, ei, d, nm)
    if not best:
        return None, None, False
    return best[1], round(best[2], 1), best[3]


def toint(v):
    try:
        return int(float(str(v).replace(",", "")))
    except (TypeError, ValueError):
        return None


def main(offline=False):
    world = c.load_world()
    g = build_edge_index(world)
    bb = world["bbox"]

    def inside(x, z):
        return bb["x0"] - 40 <= x <= bb["x1"] + 40 and bb["z0"] - 40 <= z <= bb["z1"] + 40

    out = []
    aadt = fetch_aadt(offline)
    for f in aadt.get("features", []):
        a, geo = f["attributes"], f.get("geometry") or {}
        lon, lat = geo.get("x"), geo.get("y")
        if lon is None:
            continue
        x, z = c.to_xz(lat, lon)
        if not inside(x, z):
            continue
        rte = a.get("RTE")
        names = [a.get("DESCRIPTION") or "", "Bay Bridge", "James Lick Freeway", "Interstate 80", f"I {rte}", "Embarcadero Freeway"]
        ei, d, nm = nearest_edge(world, g, x, z, names, classes=("motorway", "motorway_link", "trunk", "trunk_link", "primary"))
        out.append({
            "source": "caltrans_aadt", "id": f"caltrans_{a.get('OBJECTID')}",
            "lat": lat, "lon": lon, "x": round(x, 1), "z": round(z, 1),
            "street": a.get("DESCRIPTION"), "route": f"{rte}{a.get('RTE_SFX') or ''}", "postmile": a.get("PM"),
            "back_aadt": toint(a.get("BACK_AADT")), "ahead_aadt": toint(a.get("AHEAD_AADT")),
            "back_peak_hour": toint(a.get("BACK_PEAK_HOUR")), "ahead_peak_hour": toint(a.get("AHEAD_PEAK_HOUR")),
            "back_peak_month_adt": toint(a.get("BACK_PEAK_MADT")), "ahead_peak_month_adt": toint(a.get("AHEAD_PEAK_MADT")),
            "adt": max([v for v in (toint(a.get("BACK_AADT")), toint(a.get("AHEAD_AADT"))) if v] or [0]) or None,
            "peak_hour_volume": max([v for v in (toint(a.get("BACK_PEAK_HOUR")), toint(a.get("AHEAD_PEAK_HOUR"))) if v] or [0]) or None,
            "direction": "both (back = before postmile, ahead = after postmile; Caltrans counts are two-way totals)",
            "date": "Caltrans traffic census, latest published year in service (count year Oct-Sep)",
            "mode": "motor_vehicle",
            "nearest_edge_id": ei, "edge_dist_m": d, "edge_name_match": nm,
        })

    bike = fetch_bike(offline)
    yrs = ["yr2017_pm", "yr2016_pm", "yr2015_pm", "yr2014_pm", "yr2013_pm", "yr2011_pm", "yr2010_pm", "yr2009_pm"]
    for r in bike:
        shp = r.get("shape") or {}
        if not shp.get("coordinates"):
            continue
        lon, lat = shp["coordinates"]
        x, z = c.to_xz(lat, lon)
        if not inside(x, z):
            continue
        counts = {k[2:6]: toint(r.get(k)) for k in yrs if toint(r.get(k)) is not None and toint(r.get(k)) >= 0}
        if not counts:
            continue
        latest = max(counts)
        streets = [s.strip() for s in re.split(r"&| and |/", r.get("location") or "") if s.strip()]
        ei, d, nm = nearest_edge(world, g, x, z, streets)
        out.append({
            "source": "sfmta_bike_manual_count", "id": f"bike_{r.get('loc_id')}",
            "lat": lat, "lon": lon, "x": round(x, 1), "z": round(z, 1),
            "street": r.get("location"), "pm_peak_2h_bikes": counts[latest], "year": int(latest),
            "counts_by_year": counts, "adt": None, "peak_hour_volume": round(counts[latest] / 2),
            "direction": "all approaches (intersection total)", "date": f"{latest}-09 (2nd week Sep, 4-6 PM)",
            "mode": "bicycle",
            "nearest_edge_id": ei, "edge_dist_m": d, "edge_name_match": nm,
        })

    n_mv = sum(1 for o in out if o["mode"] == "motor_vehicle")
    meta = {
        "sources": [AADT_URL, f"https://data.sf.gov/resource/{BIKE_DS}.json"],
        "fetched_at": c.now_iso(),
        "notes": [
            "No SFMTA motor-vehicle traffic count dataset exists on DataSF (data.sf.gov) as of 2026-10-24 (catalog searched for traffic count / traffic volume / vehicle counts / ADT / volume); the only city count data is bicycle manual counts.",
            "Motor vehicles: Caltrans traffic census AADT points on state highways inside the bbox (I-80 Bay Bridge approach and ramps). adt = max(back_aadt, ahead_aadt); peak_hour_volume = max(back/ahead peak hour). Two-way totals.",
            "Bicycles: SFMTA manual PM-peak (4-6 PM) intersection counts; peak_hour_volume = latest 2h count / 2.",
            "nearest_edge_id: nearest world.json edge within 40 m by point-to-polyline distance, with a 25 m bonus for street-name match (and a 15 m bonus for highway classes for Caltrans points).",
            "Caltrans PeMS was not used: station data requires a (free) account login.",
        ],
        "caveats": [
            "Caltrans points measure freeway mainline/ramp flow, not surface streets; surface-street volumes in FiDi must be modeled.",
            "Bike counts are 2017 or older (pre-pandemic).",
        ],
        "n_points": len(out), "n_motor_vehicle": n_mv, "n_bicycle": len(out) - n_mv,
        "n_matched_edge": sum(1 for o in out if o["nearest_edge_id"] is not None),
    }
    c.write_out("traffic_counts.json", {"meta": meta, "counts": out})
    return out


if __name__ == "__main__":
    o = main(offline="--offline" in sys.argv)
    for r in o:
        print(r["source"], r["street"], r["adt"], r["peak_hour_volume"], r["nearest_edge_id"], r["edge_dist_m"], r["edge_name_match"])
