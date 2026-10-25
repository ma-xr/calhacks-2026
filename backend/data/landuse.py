"""DataSF land use parcels + zoning districts -> data/backend/landuse.json

Datasets (data.sf.gov Socrata):
  c5ge-t6pj  San Francisco Land Use (current, 2026 snapshot): resunits, cie, med, mips(=office), retail, pdr, visitor
  fdfd-xptc  [ARCHIVED] SF Land Use 2023: adds `landuse` category, `res` (residential sqft), `restype`
  3i4a-hu95  Zoning Map - Zoning Districts
Cache: data/cache/datasf/<id>_bbox_p<page>.json
"""
import json
import math
import sys
from collections import defaultdict

import common as c

DOMAIN = "https://data.sf.gov/resource/"
DS = {"lu": "c5ge-t6pj", "lu23": "fdfd-xptc", "zoning": "3i4a-hu95"}
WKT = (f"POLYGON(({c.W} {c.S}, {c.E} {c.S}, {c.E} {c.N}, {c.W} {c.N}, {c.W} {c.S}))")
PAGE = 1000


def fetch_bbox(ds, offline=False):
    rows, page = [], 0
    while True:
        p = c.cache_path("datasf", f"{ds}_bbox_p{page}.json")
        if p.exists():
            batch = json.loads(p.read_text())
        else:
            if offline:
                raise RuntimeError(f"{p} not cached")
            env = c.load_env()
            params = {"$where": f"intersects(the_geom, '{WKT}')", "$limit": PAGE, "$offset": page * PAGE,
                      "$order": ":id"}
            with c.http_client(headers={"X-App-Token": env.get("SODA_APP_TOKEN", "")}) as cl:
                r = cl.get(DOMAIN + ds + ".json", params=params)
                r.raise_for_status()
                batch = r.json()
            p.write_text(json.dumps(batch))
            c.write_params(p, dict(params, url=DOMAIN + ds + ".json"))
            c.log_usage("datasf", f"{ds} bbox page {page} ({len(batch)} rows)", "free")
        rows += batch
        if len(batch) < PAGE:
            break
        page += 1
    return rows


def geom_xz(g):
    """GeoJSON (Multi)Polygon lon/lat -> list of polygons of rings in local meters."""
    if not g:
        return []
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    return [[[c.to_xz(pt[1], pt[0]) for pt in ring] for ring in poly] for poly in polys]


def bbox_of(mp):
    xs = [p[0] for poly in mp for p in poly[0]]
    zs = [p[1] for poly in mp for p in poly[0]]
    return (min(xs), min(zs), max(xs), max(zs))


def mp_area(mp):
    return sum(c.ring_area(poly[0]) - sum(c.ring_area(h) for h in poly[1:]) for poly in mp)


def mp_centroid(mp):
    ax = az = A = 0.0
    for poly in mp:
        r = poly[0]
        for i in range(len(r)):
            x1, z1 = r[i]
            x2, z2 = r[(i + 1) % len(r)]
            cr = x1 * z2 - x2 * z1
            A += cr
            ax += (x1 + x2) * cr
            az += (z1 + z2) * cr
    if abs(A) < 1e-9:
        xs = [p[0] for poly in mp for p in poly[0]]
        zs = [p[1] for poly in mp for p in poly[0]]
        return (sum(xs) / len(xs), sum(zs) / len(zs))
    return (ax / (3 * A), az / (3 * A))


class Grid:
    def __init__(self, cell=50.0):
        self.cell = cell
        self.g = defaultdict(list)

    def add(self, i, bb):
        cs = self.cell
        for gx in range(int(math.floor(bb[0] / cs)), int(math.floor(bb[2] / cs)) + 1):
            for gz in range(int(math.floor(bb[1] / cs)), int(math.floor(bb[3] / cs)) + 1):
                self.g[(gx, gz)].append(i)

    def query(self, x, z, r=0.0):
        cs = self.cell
        out = set()
        for gx in range(int(math.floor((x - r) / cs)), int(math.floor((x + r) / cs)) + 1):
            for gz in range(int(math.floor((z - r) / cs)), int(math.floor((z + r) / cs)) + 1):
                out.update(self.g.get((gx, gz), ()))
        return out


def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def derive_landuse(p):
    uses = {"RESIDENT": p["res_sqft"], "MIPS": p["office_sqft"], "RETAIL/ENT": p["retail_sqft"],
            "VISITOR": p["hotel_sqft"], "CIE": p["cie"], "MED": p["med"], "PDR": p["pdr"]}
    tot = sum(uses.values())
    if tot <= 0:
        return "OPENSPACE" if p.get("open_space") else ("PARKING" if p.get("parking") else "VACANT")
    top = max(uses, key=uses.get)
    return top if uses[top] / tot >= 0.8 else "MIXED" if top != "RESIDENT" else "MIXRES"


def main(offline=False):
    world = c.load_world()
    B = world["buildings"]
    lu = fetch_bbox(DS["lu"], offline)
    lu23 = fetch_bbox(DS["lu23"], offline)
    zon = fetch_bbox(DS["zoning"], offline)
    print("parcels", len(lu), "parcels2023", len(lu23), "zoning", len(zon))

    by23 = {}
    for r in lu23:
        by23.setdefault(r.get("mapblklot"), r)

    parcels = []
    for r in lu:
        mp = geom_xz(r.get("the_geom"))
        if not mp:
            continue
        r23 = by23.get(r.get("mapblklot"), {})
        res_sqft = f(r23.get("res"))
        p = {
            "id": r.get("mapblklot") or r.get("ludb_id"), "ludb_id": r.get("ludb_id"), "mp": mp,
            "bb": bbox_of(mp), "c": mp_centroid(mp), "area": mp_area(mp),
            "res_units": f(r.get("resunits")), "office_sqft": f(r.get("mips")), "retail_sqft": f(r.get("retail")),
            "hotel_sqft": f(r.get("visitor")), "cie": f(r.get("cie")), "med": f(r.get("med")), "pdr": f(r.get("pdr")),
            "total_comm": f(r.get("total_comm")), "res_sqft": res_sqft, "restype": r23.get("restype"),
            "landuse23": r23.get("landuse"), "open_space": r.get("open_space"), "parking": r.get("parking_lo") or r.get("garage"),
            "geography_type": r.get("geography_type"),
        }
        # current numbers drive the category; fall back to the 2023 label only when the parcel has no floor area
        der = derive_landuse(p)
        p["landuse"] = der if der not in ("VACANT",) or not p["landuse23"] else p["landuse23"]
        parcels.append(p)

    zones = []
    for r in zon:
        mp = geom_xz(r.get("the_geom"))
        if mp:
            zones.append({"code": r.get("zoning_sim") or r.get("zoning"), "name": r.get("districtna"), "gen": r.get("gen"),
                          "mp": mp, "bb": bbox_of(mp)})

    pg = Grid()
    for i, p in enumerate(parcels):
        pg.add(i, p["bb"])
    zg = Grid(100)
    for i, zz in enumerate(zones):
        zg.add(i, zz["bb"])
    bg = Grid()
    for i, b in enumerate(B):
        xs = [q[0] for q in b["p"]]
        zs = [q[1] for q in b["p"]]
        bg.add(i, (min(xs), min(zs), max(xs), max(zs)))

    def contains(p, x, z):
        bb = p["bb"]
        return bb[0] <= x <= bb[2] and bb[1] <= z <= bb[3] and c.point_in_multipolygon(x, z, p["mp"])

    # 1. building centroid in parcel
    b_parcel = {}
    for bi, b in enumerate(B):
        x, z = b["c"]
        hits = [pi for pi in pg.query(x, z) if contains(parcels[pi], x, z)]
        if hits:
            b_parcel[bi] = min(hits, key=lambda pi: parcels[pi]["area"])  # smallest (avoid big condo/common lots)
    parcel_bldgs = defaultdict(list)
    for bi, pi in b_parcel.items():
        parcel_bldgs[pi].append(bi)
    method = {bi: "centroid_in_parcel" for bi in b_parcel}

    # 2. parcels with no building: assign to building containing parcel centroid, else nearest bldg centroid <= 40 m
    extra = defaultdict(list)  # bi -> [pi] additional parcels
    n_rev = n_near_p = 0
    for pi, p in enumerate(parcels):
        if pi in parcel_bldgs:
            continue
        x, z = p["c"]
        cand = [bi for bi in bg.query(x, z) if c.point_in_ring(x, z, B[bi]["p"])]
        if cand:
            extra[cand[0]].append(pi)
            n_rev += 1
            continue
        best, bd = None, 40.0
        for bi in bg.query(x, z, 40):
            d = math.hypot(B[bi]["c"][0] - x, B[bi]["c"][1] - z)
            if d < bd:
                best, bd = bi, d
        if best is not None and (p["total_comm"] + p["res_units"]) > 0:
            extra[best].append(pi)
            n_near_p += 1

    # 3. buildings with no parcel: nearest parcel centroid within 40 m (attributes only, no sqft)
    b_attr_parcel = {}
    for bi, b in enumerate(B):
        if bi in b_parcel or bi in extra:
            continue
        x, z = b["c"]
        best, bd = None, 40.0
        for pi in pg.query(x, z, 40):
            d = math.hypot(parcels[pi]["c"][0] - x, parcels[pi]["c"][1] - z)
            if d < bd:
                best, bd = pi, d
        if best is not None:
            b_attr_parcel[bi] = best
            method[bi] = "nearest_parcel_attrs_only"

    def weight(bi):
        b = B[bi]
        return max(c.ring_area(b["p"]), 1.0) * max(b.get("h") or 0, 3.0)

    keys = ("res_units", "office_sqft", "retail_sqft", "hotel_sqft", "res_sqft", "cie", "med", "pdr")
    acc = [dict.fromkeys(keys, 0.0) for _ in B]
    pids = [[] for _ in B]
    for pi, bl in parcel_bldgs.items():
        W = sum(weight(bi) for bi in bl)
        for bi in bl:
            s = weight(bi) / W
            pids[bi].append(parcels[pi]["id"])
            for k in keys:
                acc[bi][k] += parcels[pi][k] * s
    for bi, pl in extra.items():
        for pi in pl:
            pids[bi].append(parcels[pi]["id"])
            for k in keys:
                acc[bi][k] += parcels[pi][k]
        method.setdefault(bi, "parcel_centroid_in_building_or_near")

    out_b = []
    for bi, b in enumerate(B):
        x, z = b["c"]
        zz = [zi for zi in zg.query(x, z) if zones[zi]["bb"][0] <= x <= zones[zi]["bb"][2]
              and zones[zi]["bb"][1] <= z <= zones[zi]["bb"][3] and c.point_in_multipolygon(x, z, zones[zi]["mp"])]
        zone = zones[zz[0]] if zz else None
        main_pi = b_parcel.get(bi, b_attr_parcel.get(bi, extra[bi][0] if extra.get(bi) else None))
        a = acc[bi]
        other = a["cie"] + a["med"] + a["pdr"]
        comm = a["office_sqft"] + a["retail_sqft"] + a["hotel_sqft"] + other
        out_b.append({
            "building_id": bi,
            "parcel_ids": pids[bi] if pids[bi] else ([parcels[main_pi]["id"]] if main_pi is not None else []),
            "match": method.get(bi, "none"),
            "landuse": parcels[main_pi]["landuse"] if main_pi is not None else None,
            "landuse_2023": parcels[main_pi]["landuse23"] if main_pi is not None else None,
            "zoning": zone["code"] if zone else None,
            "zoning_gen": zone["gen"] if zone else None,
            "res_units": round(a["res_units"], 2),
            "office_sqft": round(a["office_sqft"]),
            "retail_sqft": round(a["retail_sqft"]),
            "hotel_sqft": round(a["hotel_sqft"]),
            "other_sqft": round(other),
            "other_breakdown": {"cie": round(a["cie"]), "med": round(a["med"]), "pdr": round(a["pdr"])},
            "res_sqft": round(a["res_sqft"]),
            "bldg_sqft": round(comm + a["res_sqft"]),
        })

    # coverage
    tot = {k: sum(p[k] for p in parcels if c.in_bbox(*c.to_latlon(*p["c"]))) for k in keys}
    assigned = {k: sum(o[k] for o in out_b) for k in ("res_units", "office_sqft", "retail_sqft", "hotel_sqft")}
    cnt = defaultdict(int)
    for o in out_b:
        cnt[o["match"]] += 1
    meta = {
        "sources": [DOMAIN + DS["lu"] + ".json", DOMAIN + DS["lu23"] + ".json", DOMAIN + DS["zoning"] + ".json"],
        "fetched_at": c.now_iso(),
        "notes": [
            "Numbers (res_units, office=mips, retail, hotel=visitor, cie, med, pdr) come from the current SF Land Use dataset c5ge-t6pj (2026 snapshot). Residential sqft (res_sqft) and `landuse_2023` come from the archived 2023 dataset fdfd-xptc joined on mapblklot. `landuse` is derived from the current numbers (incl. res_sqft): dominant use if >=80% of floor area, else MIXED (or MIXRES if residential dominates); parcels with no floor area use the 2023 label, else OPENSPACE/PARKING/VACANT.",
            "other_sqft = cie (cultural/institutional/educational) + med (medical) + pdr (production/distribution/repair).",
            "bldg_sqft = office + retail + hotel + other + res_sqft (gross floor area by use, not a measured building GFA).",
            "Matching: (1) building centroid inside parcel polygon (smallest containing parcel); a parcel with several such buildings is split proportional to footprint area x height. (2) parcels containing no building centroid are attached whole to the building whose footprint contains the parcel centroid, else (if they have floor area) to the nearest building centroid within 40 m. (3) buildings still unmatched get landuse/zoning from the nearest parcel centroid within 40 m but zero sqft.",
            "Zoning = district containing the building centroid (3i4a-hu95 zoning_sim code; zoning_gen = general class).",
        ],
        "caveats": [
            "Land use sqft are Planning Dept estimates (from assessor + permits), not exact GFA; condo parcels can be split across many mapblklots.",
            "OSM footprints and parcels do not align perfectly; a few large towers spanning multiple lots may under/over-count.",
        ],
        "coverage": {
            "n_parcels_fetched": len(parcels), "n_zoning_districts": len(zones), "n_buildings": len(B),
            "buildings_by_match": dict(cnt),
            "buildings_with_zoning": sum(1 for o in out_b if o["zoning"]),
            "buildings_with_any_sqft": sum(1 for o in out_b if o["bldg_sqft"] > 0),
            "parcel_totals_centroid_in_bbox": {k: round(v) for k, v in tot.items()},
            "assigned_totals": {k: round(v) for k, v in assigned.items()},
            "parcels_reverse_matched": n_rev, "parcels_nearest_matched": n_near_p,
        },
    }
    out = {"meta": meta, "buildings": out_b}
    c.write_out("landuse.json", out)
    return out


if __name__ == "__main__":
    o = main(offline="--offline" in sys.argv)
    print(json.dumps(o["meta"]["coverage"], indent=1))
