"""Census LODES8 (LEHD) -> data/backend/lodes.json

Inputs (cached in data/cache/lodes/):
  ca_xwalk.csv.gz              block geography crosswalk (blklatdd, blklondd, county, tract)
  ca_wac_S000_JT00_<Y>.csv.gz  workplace area characteristics (jobs by earnings CE, sector CNS)
  ca_od_main_JT00_<Y>.csv.gz   origin-destination, both home+work in CA (SE01..SE03)
"""
import csv
import gzip
import json
import sys
from collections import defaultdict

import common as c

YEAR = 2023
BASE = "https://lehd.ces.census.gov/data/lodes/LODES8/ca/"
FILES = {
    "xwalk": "ca_xwalk.csv.gz",
    "wac": f"wac/ca_wac_S000_JT00_{YEAR}.csv.gz",
    "od": f"od/ca_od_main_JT00_{YEAR}.csv.gz",
}

CNS_LABELS = {
    "CNS01": "Agriculture, Forestry, Fishing and Hunting (NAICS 11)",
    "CNS02": "Mining, Quarrying, and Oil and Gas Extraction (21)",
    "CNS03": "Utilities (22)",
    "CNS04": "Construction (23)",
    "CNS05": "Manufacturing (31-33)",
    "CNS06": "Wholesale Trade (42)",
    "CNS07": "Retail Trade (44-45)",
    "CNS08": "Transportation and Warehousing (48-49)",
    "CNS09": "Information (51)",
    "CNS10": "Finance and Insurance (52)",
    "CNS11": "Real Estate and Rental and Leasing (53)",
    "CNS12": "Professional, Scientific, and Technical Services (54)",
    "CNS13": "Management of Companies and Enterprises (55)",
    "CNS14": "Administrative and Support and Waste Management (56)",
    "CNS15": "Educational Services (61)",
    "CNS16": "Health Care and Social Assistance (62)",
    "CNS17": "Arts, Entertainment, and Recreation (71)",
    "CNS18": "Accommodation and Food Services (72)",
    "CNS19": "Other Services except Public Administration (81)",
    "CNS20": "Public Administration (92)",
}
EARN_LABELS = {"SE01": "$1,250/month or less", "SE02": "$1,251-$3,333/month", "SE03": "more than $3,333/month"}

COUNTY_REGION = {
    "06001": "east_bay", "06013": "east_bay", "06095": "east_bay",          # Alameda, Contra Costa, Solano
    "06081": "peninsula_south_bay", "06085": "peninsula_south_bay",        # San Mateo, Santa Clara
    "06041": "north_bay", "06097": "north_bay", "06055": "north_bay",      # Marin, Sonoma, Napa
}
REGIONS = ["east_bay", "peninsula_south_bay", "sf_west", "sf_southeast_mission", "sf_north", "sf_in_area",
           "north_bay", "other"]
SF_WEST_LON = -122.44
SF_NORTH_LAT = 37.79
FAR_KM = 150  # homes farther than this (straight line) are treated as non-daily commuters in *_excl_far


def files(offline):
    out = {}
    for k, f in FILES.items():
        p = c.cache_path("lodes", f.split("/")[-1])
        if not p.exists():
            if offline:
                raise RuntimeError(f"{p} not cached")
            c.download(BASE + f, p, "LODES")
        out[k] = p
    return out


def classify(county, lat, lon):
    if county == "06075":
        if c.in_bbox(lat, lon):
            return "sf_in_area"
        if lon < SF_WEST_LON:
            return "sf_west"
        if lat > SF_NORTH_LAT:
            return "sf_north"
        return "sf_southeast_mission"
    return COUNTY_REGION.get(county, "other")


def norm(d):
    t = sum(d.values())
    return {k: round(v / t, 5) if t else 0 for k, v in d.items()}


def main(offline=False):
    fp = files(offline)
    blk = {}  # block -> (lat, lon, county, county name)
    with gzip.open(fp["xwalk"], "rt", encoding="latin-1") as f:
        for r in csv.DictReader(f):
            blk[r["tabblk2020"]] = (float(r["blklatdd"]), float(r["blklondd"]), r["cty"], r["ctyname"])
    in_area = {b for b, v in blk.items() if v[2] == "06075" and c.in_bbox(v[0], v[1])}
    print("blocks in bbox:", len(in_area))

    wac = {}
    with gzip.open(fp["wac"], "rt") as f:
        for r in csv.DictReader(f):
            if r["w_geocode"] in in_area:
                wac[r["w_geocode"]] = r
    jobs_total = sum(int(r["C000"]) for r in wac.values())
    by_sector = {k: sum(int(r[k]) for r in wac.values()) for k in CNS_LABELS}
    by_earn_wac = {f"SE0{i}": sum(int(r[f"CE0{i}"]) for r in wac.values()) for i in (1, 2, 3)}

    # OD: home origins for jobs in area
    reg = defaultdict(float)
    reg_e = {k: defaultdict(float) for k in EARN_LABELS}
    county_ct = defaultdict(float)
    od_total = 0
    far = 0
    reg_near = defaultdict(float)
    od_by_block = defaultdict(lambda: [0, 0, 0, 0])
    with gzip.open(fp["od"], "rt") as f:
        rd = csv.reader(f)
        hdr = next(rd)
        iw, ih, iS, i1, i2, i3 = (hdr.index(k) for k in ("w_geocode", "h_geocode", "S000", "SE01", "SE02", "SE03"))
        for r in rd:
            w = r[iw]
            if w not in in_area:
                continue
            h = r[ih]
            n = int(r[iS])
            hb = blk.get(h)
            region = classify(hb[2], hb[0], hb[1]) if hb else "other"
            reg[region] += n
            if hb and (abs(hb[0] - 37.79) * 111.0) ** 2 + (abs(hb[1] + 122.40) * 88.0) ** 2 > FAR_KM ** 2:
                far += n
            else:
                reg_near[region] += n
            for k, i in (("SE01", i1), ("SE02", i2), ("SE03", i3)):
                reg_e[k][region] += int(r[i])
            county_ct[hb[3] if hb else "unknown"] += n
            od_total += n
            ob = od_by_block[w]
            ob[0] += n
            ob[1] += int(r[i1])
            ob[2] += int(r[i2])
            ob[3] += int(r[i3])

    work_blocks = []
    for b in sorted(in_area):
        r = wac.get(b)
        if not r or int(r["C000"]) == 0:
            continue
        lat, lon = blk[b][0], blk[b][1]
        x, z = c.to_xz(lat, lon)
        work_blocks.append({
            "block_id": b, "x": round(x, 1), "z": round(z, 1), "jobs": int(r["C000"]),
            "jobs_by_earnings": {f"SE0{i}": int(r[f"CE0{i}"]) for i in (1, 2, 3)},
            "jobs_by_sector": {k: int(r[k]) for k in CNS_LABELS if int(r[k])},
            "od_in_state_jobs": od_by_block[b][0] if b in od_by_block else 0,
        })
    work_blocks.sort(key=lambda w: -w["jobs"])

    top_counties = sorted(county_ct.items(), key=lambda kv: -kv[1])[:20]
    out = {
        "meta": {
            "sources": [BASE + FILES["xwalk"], BASE + FILES["wac"], BASE + FILES["od"]],
            "year": YEAR,
            "fetched_at": c.now_iso(),
            "notes": [
                "Work blocks = 2020 census blocks in SF County whose internal point (xwalk blklatdd/blklondd) lies in bbox S37.7800 W-122.4095 N37.7975 E-122.3880.",
                "jobs_total, jobs_by_earnings, jobs_by_sector come from WAC (all jobs, JT00 = all job types, S000 segment). WAC earnings columns CE01..CE03 are reported under SE01..SE03 keys here.",
                "home_region_share uses OD main (home and work both in CA); out-of-state homes (od_aux) are excluded (~small).",
                "Region rule: east_bay = Alameda+Contra Costa+Solano; peninsula_south_bay = San Mateo+Santa Clara; north_bay = Marin+Sonoma+Napa; SF homes: sf_in_area if home block point is inside the sim bbox, else sf_west if lon < -122.44, else sf_north if lat > 37.79, else sf_southeast_mission; every other CA county = other (Sacramento, San Joaquin, LA, ...).",
                f"home_region_share_excl_far drops jobs whose home block is > {FAR_KM} km straight-line from FiDi (LA, San Diego etc.), which are mostly HQ-reporting artifacts or non-daily commuters; recommended for agent generation.",
                "Coordinates x,z in world.json local meters (x east, z south).",
                "Earnings: SE01 <= $1,250/mo, SE02 $1,251-3,333/mo, SE03 > $3,333/mo.",
            ],
            "caveats": [
                "LODES counts jobs (primary + secondary, JT00), not people; one person may hold 2 jobs.",
                "LODES assigns jobs to the employer's reported worksite; multi-establishment firms sometimes report HQ address, inflating FiDi counts (a known LODES issue) and remote workers are counted at the worksite.",
                "Block-level LODES has noise infusion (differential privacy-like); small blocks are fuzzy.",
                f"OD in-state total ({od_total}) < WAC total ({jobs_total}) mainly due to out-of-state residents and federal jobs coverage differences.",
            ],
            "earnings_labels": EARN_LABELS,
            "region_rule": {"sf_west_lon": SF_WEST_LON, "sf_north_lat": SF_NORTH_LAT, "county_region": COUNTY_REGION},
        },
        "jobs_total": jobs_total,
        "jobs_by_earnings": by_earn_wac,
        "jobs_by_sector": {k: {"label": CNS_LABELS[k], "jobs": v, "share": round(v / jobs_total, 5)} for k, v in by_sector.items()},
        "od_in_state_jobs": od_total,
        "home_region_share": {k: norm(reg).get(k, 0) for k in REGIONS},
        "home_region_share_excl_far": {k: norm(reg_near).get(k, 0) for k in REGIONS},
        "far_home_jobs": far,
        "home_region_counts": {k: reg.get(k, 0) for k in REGIONS},
        "home_region_share_by_earnings": {e: {k: norm(reg_e[e]).get(k, 0) for k in REGIONS} for e in EARN_LABELS},
        "home_county_top20": [{"county": k, "jobs": v, "share": round(v / od_total, 5)} for k, v in top_counties],
        "n_work_blocks": len(work_blocks),
        "work_blocks": work_blocks,
    }
    c.write_out("lodes.json", out)
    return out


if __name__ == "__main__":
    o = main(offline="--offline" in sys.argv)
    print("jobs_total", o["jobs_total"], o["jobs_by_earnings"])
    print(json.dumps(o["home_region_share"], indent=1))
