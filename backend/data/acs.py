"""ACS 5-year commute + tract demographics -> data/backend/acs.json

Cache: data/cache/census_acs/*.json (+ .params.json without the key)
Tract centroids: Census Gazetteer 2023 tracts for CA (INTPTLAT/INTPTLONG).
"""
import hashlib
import json
import sys

import common as c

YEAR = 2023
BASE = f"https://api.census.gov/data/{YEAR}/acs/acs5"
GAZ_URL = f"https://www2.census.gov/geo/docs/maps-data/data/gazetteer/{YEAR}_Gazetteer/{YEAR}_gaz_tracts_06.txt"
SF = {"state": "06", "county": "075"}


def acs_get(group_or_vars, geo_for, geo_in=None, offline=False):
    """Fetch ACS variables; cached by request signature."""
    sig = json.dumps([YEAR, group_or_vars, geo_for, geo_in], sort_keys=True)
    h = hashlib.md5(sig.encode()).hexdigest()[:10]
    label = group_or_vars if isinstance(group_or_vars, str) else "vars"
    path = c.cache_path("census_acs", f"{label.replace('(', '_').replace(')', '')}_{geo_for.split(':')[0]}_{h}.json")
    if path.exists():
        return json.loads(path.read_text())
    if offline:
        raise RuntimeError(f"not cached: {sig}")
    env = c.load_env()
    params = {"get": ("NAME," + group_or_vars) if not group_or_vars.startswith("group(") else group_or_vars,
              "for": geo_for}
    if geo_in:
        params["in"] = geo_in
    with c.http_client() as cl:
        r = cl.get(BASE, params=dict(params, key=env.get("CENSUS_API_KEY", "")))
        r.raise_for_status()
        data = r.json()
    path.write_text(json.dumps(data))
    c.write_params(path, dict(params, url=BASE))
    c.log_usage("census_acs", f"ACS5 {YEAR} {params['get'][:60]} for={geo_for}", "free (keyed)")
    return data


def rows_to_dicts(data):
    hdr = data[0]
    return [dict(zip(hdr, r)) for r in data[1:]]


def num(v):
    try:
        x = float(v)
        return None if x < -1e5 else x  # ACS null sentinels like -666666666
    except (TypeError, ValueError):
        return None


def shares(d, mapping, total_key):
    tot = sum(num(d[v]) or 0 for v in mapping.values())
    out = {k: round((num(d[v]) or 0) / tot, 5) if tot else None for k, v in mapping.items()}
    return {"counts": {k: num(d[v]) for k, v in mapping.items()}, "total": num(d[total_key]), "shares": out}


def mode_map(t, workplace):
    if t == "B08406":
        m = {"drove_alone": 3, "carpool": 4, "bus": 9, "subway_elevated_rail": 10, "commuter_rail": 11,
             "light_rail_streetcar": 12, "ferry": 13, "bicycle": 14, "walk": 15,
             "taxi_motorcycle_other": 16, "work_from_home": 17}
    else:  # B08301
        m = {"drove_alone": 3, "carpool": 4, "bus": 11, "subway_elevated_rail": 12, "commuter_rail": 13,
             "light_rail_streetcar": 14, "ferry": 15, "taxi_motorcycle_other": (16, 17, 20), "bicycle": 18,
             "walk": 19, "work_from_home": 21}
    return m


def mode_shares(t, offline):
    data = acs_get(f"group({t})", "county:075", "state:06", offline)
    d = rows_to_dicts(data)[0]
    m = mode_map(t, t == "B08406")
    counts = {}
    for k, v in m.items():
        vs = v if isinstance(v, tuple) else (v,)
        counts[k] = sum(num(d[f"{t}_{i:03d}E"]) or 0 for i in vs)
    tot = sum(counts.values())
    commute_tot = tot - counts["work_from_home"]
    return {
        "table": t,
        "total_workers": num(d[f"{t}_001E"]),
        "counts": counts,
        "shares": {k: round(v / tot, 5) for k, v in counts.items()},
        "shares_excluding_wfh": {k: round(v / commute_tot, 5) for k, v in counts.items() if k != "work_from_home"},
    }


TIME_BINS = ["00:00-04:59", "05:00-05:29", "05:30-05:59", "06:00-06:29", "06:30-06:59", "07:00-07:29",
             "07:30-07:59", "08:00-08:29", "08:30-08:59", "09:00-09:59", "10:00-10:59", "11:00-11:59",
             "12:00-15:59", "16:00-23:59"]


def time_bins(t, offline):
    data = acs_get(f"group({t})", "county:075", "state:06", offline)
    d = rows_to_dicts(data)[0]
    counts = [num(d[f"{t}_{i:03d}E"]) or 0 for i in range(2, 16)]
    tot = sum(counts)
    return {"table": t, "bins": TIME_BINS, "counts": counts, "shares": [round(x / tot, 5) for x in counts],
            "total": num(d[f"{t}_001E"])}


def travel_time(t, bins, rng, offline):
    data = acs_get(f"group({t})", "county:075", "state:06", offline)
    d = rows_to_dicts(data)[0]
    counts = [num(d[f"{t}_{i:03d}E"]) or 0 for i in rng]
    tot = sum(counts)
    return {"table": t, "bins_minutes": bins, "counts": counts, "shares": [round(x / tot, 5) for x in counts]}


def gazetteer(offline):
    p = c.cache_path("census_gazetteer", f"{YEAR}_gaz_tracts_06.txt")
    if not p.exists():
        if offline:
            raise RuntimeError("gazetteer not cached")
        c.download(GAZ_URL, p, "census_gazetteer")
    out = {}
    lines = p.read_text(encoding="latin-1").splitlines()
    hdr = [h.strip() for h in lines[0].split("\t")]
    for ln in lines[1:]:
        r = dict(zip(hdr, [x.strip() for x in ln.split("\t")]))
        out[r["GEOID"]] = (float(r["INTPTLAT"]), float(r["INTPTLONG"]), float(r["ALAND"]))
    return out


TRACT_VARS = {
    "population": "B01003_001E",
    "households": "B11001_001E",
    "median_household_income": "B19013_001E",
    "avg_household_size": "B25010_001E",
    "hh_vehicles_total": "B08201_001E",
    "hh_vehicles_0": "B08201_002E",
    "hh_vehicles_1": "B08201_003E",
    "hh_vehicles_2": "B08201_004E",
    "hh_vehicles_3": "B08201_005E",
    "hh_vehicles_4plus": "B08201_006E",
    "housing_units": "B25001_001E",
    "workers_16plus_resident": "B08301_001E",
}


def tracts(offline):
    gz = gazetteer(offline)
    vars_ = ",".join(TRACT_VARS.values())
    data = acs_get(vars_, "tract:*", "state:06 county:075", offline)
    out = []
    for d in rows_to_dicts(data):
        geoid = d["state"] + d["county"] + d["tract"]
        if geoid not in gz:
            continue
        lat, lon, aland = gz[geoid]
        if not c.in_bbox(lat, lon):
            continue
        x, z = c.to_xz(lat, lon)
        rec = {"geoid": geoid, "name": d["NAME"], "lat": lat, "lon": lon, "x": round(x, 1), "z": round(z, 1),
               "land_area_m2": aland}
        for k, v in TRACT_VARS.items():
            rec[k] = num(d[v])
        hh = rec["households"] or 0
        rec["persons_per_household"] = round(rec["population"] / hh, 3) if hh else None
        vt = rec["hh_vehicles_total"] or 0
        if vt:
            rec["vehicles_share"] = {k: round((rec[f"hh_vehicles_{k}"] or 0) / vt, 4) for k in ("0", "1", "2", "3", "4plus")}
            rec["vehicles_per_household"] = round(sum((rec[f"hh_vehicles_{k}"] or 0) * w for k, w in
                                                      (("1", 1), ("2", 2), ("3", 3), ("4plus", 4.3))) / vt, 3)
        out.append(rec)
    return sorted(out, key=lambda r: r["geoid"])


def main(offline=False):
    wp = mode_shares("B08406", offline)
    res = mode_shares("B08301", offline)
    dep_res = time_bins("B08302", offline)
    arr_wp = time_bins("B08602", offline)
    tt_res = travel_time("B08303", ["<5", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44",
                                    "45-59", "60-89", "90+"], range(2, 14), offline)
    tt_wp = travel_time("B08534", ["<10", "10-14", "15-19", "20-24", "25-29", "30-34", "35-44", "45-59", "60+"],
                        range(2, 11), offline)
    # mean travel time (minutes) = aggregate / commuters (non-WFH)
    agg_res = rows_to_dicts(acs_get("group(B08136)", "county:075", "state:06", offline))[0]
    agg_wp = rows_to_dicts(acs_get("group(B08536)", "county:075", "state:06", offline))[0]
    mean_res = num(agg_res["B08136_001E"]) / (res["total_workers"] - res["counts"]["work_from_home"])
    mean_wp = num(agg_wp["B08536_001E"]) / (wp["total_workers"] - wp["counts"]["work_from_home"])
    tr = tracts(offline)
    tot_pop = sum(t["population"] or 0 for t in tr)
    tot_hh = sum(t["households"] or 0 for t in tr)
    out = {
        "meta": {
            "sources": [BASE, GAZ_URL],
            "dataset": f"ACS 5-year {YEAR - 4}-{YEAR}",
            "fetched_at": c.now_iso(),
            "tables": {
                "B08406": "Means of transportation to work, WORKPLACE geography (people who work in SF County)",
                "B08301": "Means of transportation to work, residence geography (SF County residents)",
                "B08302": "Time leaving home to go to work, residence geography (SF residents; excludes WFH)",
                "B08602": "Time ARRIVING at work from home, WORKPLACE geography (people working in SF; excludes WFH)",
                "B08303": "Travel time to work, residence geography (excludes WFH)",
                "B08534": "Travel time to work, workplace geography (excludes WFH)",
                "B08136/B08536": "Aggregate travel time (residence / workplace) -> mean minutes",
                "tract vars": TRACT_VARS,
            },
            "notes": [
                "Workplace-geography tables are only published down to county/place level, not tract; SF County is used for the FiDi/SoMa workplace mix.",
                "There is no ACS 'time leaving home' table for workplace geography; B08602 (time arriving at work) is the workplace analogue.",
                "Tracts included = SF tracts whose Gazetteer internal point (INTPTLAT/LONG) lies in the sim bbox.",
                "vehicles_per_household treats '4 or more' as 4.3.",
            ],
            "caveats": [
                "5-year estimates pool 2019-2023, spanning the pandemic; WFH share is elevated vs pre-2020 and partly vs 2026.",
                "FiDi workplace mode share is more transit-heavy than the SF County average (county includes outer neighborhoods).",
                "Tract-level medians/margins of error not included; small tracts have large MOE.",
            ],
        },
        "workplace_sf_county": {"mode": wp, "arrival_time": arr_wp, "travel_time": tt_wp,
                                "mean_travel_time_min": round(mean_wp, 2)},
        "residents_sf_county": {"mode": res, "departure_time": dep_res, "travel_time": tt_res,
                                "mean_travel_time_min": round(mean_res, 2)},
        "tracts_in_bbox": tr,
        "tracts_summary": {"n": len(tr), "population": tot_pop, "households": tot_hh,
                           "persons_per_household": round(tot_pop / tot_hh, 3) if tot_hh else None},
    }
    c.write_out("acs.json", out)
    return out


if __name__ == "__main__":
    o = main(offline="--offline" in sys.argv)
    print(json.dumps(o["workplace_sf_county"]["mode"]["shares"], indent=1))
    print(o["tracts_summary"])
