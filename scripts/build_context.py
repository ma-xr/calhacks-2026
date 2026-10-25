"""Build the faded San Francisco context around the simulation area.

Usage: python3 scripts/build_context.py data/raw/osm_context_2026-10-24.json data/processed/context.json

Same local-meter frame as world.json. Everything inside the simulation bbox is dropped (the
simulation renders it). Compact encoding:
  buildings: [h, x0, z0, x1, z1, ...]   (meters, ints)
  roads:     [cls, nameIdx, x0, z0, ...]  (cls index into CLASSES)
  parks / water: [x0, z0, x1, z1, ...]
"""
import json
import math
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from build_world import BBOX, parse_height, simplify, xz  # noqa: E402

CLASSES = ["motorway", "trunk", "primary", "secondary", "tertiary", "residential", "pedestrian"]
CLS = {"motorway": 0, "motorway_link": 0, "trunk": 1, "trunk_link": 1, "primary": 2, "primary_link": 2,
       "secondary": 3, "secondary_link": 3, "tertiary": 4, "residential": 5, "unclassified": 5, "pedestrian": 6}
MAX_R = 2600  # meters from origin; beyond this everything has faded out anyway


def coast_land(path, S=6000):
    """Land polygons from OSM coastline (land is left of the line). Returns flat [x0, z0, ...] lists."""
    try:
        els = json.load(open(path))["elements"]
    except (OSError, ValueError):
        return []
    segs = [[xz(g["lat"], g["lon"]) for g in w["geometry"]] for w in els if "geometry" in w]
    chains = []
    while segs:
        c = segs.pop(0)
        grown = True
        while grown:
            grown = False
            for i, sg in enumerate(segs):
                if sg[0] == c[-1]:
                    c += sg[1:]; segs.pop(i); grown = True; break
                if sg[-1] == c[0]:
                    c = sg[:-1] + c; segs.pop(i); grown = True; break
        chains.append(c)
    polys = []
    for c in chains:
        if c[0] != c[-1]:
            if len(c) < 50:
                continue
            # Close an open coastline through a far square, walking counter-clockwise (north-up frame) so land stays left.
            def to_edge(p):
                x, y = p[0], -p[1]
                k = S / max(abs(x), abs(y), 1e-6)
                return (x * k, y * k)
            def ang(p):
                return math.atan2(p[1], p[0]) % (2 * math.pi)
            e, st = to_edge(c[-1]), to_edge(c[0])
            path = [e]
            corners = [(S, S), (-S, S), (-S, -S), (S, -S)]
            a, b = ang(e), ang(st)
            if b < a:
                b += 2 * math.pi
            seq = [(ang(q) + (2 * math.pi if ang(q) < a else 0), q) for q in corners]
            seq += [(t + 2 * math.pi, q) for t, q in seq]
            path += [q for t, q in sorted(seq) if a < t < b]
            path.append(st)
            ring = c + [(x, -y) for x, y in path]
        else:
            ring = c[:-1]
        ring = simplify(ring, 2.0)
        polys.append([round(v) for p in ring for v in p])
    return polys


def main(src, dst):
    s, w, n, e = BBOX
    x0, z1 = xz(s, w)
    x1, z0 = xz(n, e)
    inside = lambda x, z: x0 < x < x1 and z0 < z < z1  # noqa: E731
    els = json.load(open(src))["elements"]
    bld, roads, parks, water, names, nidx = [], [], [], [], [], {}
    for el in els:
        t = el.get("tags", {})
        if "geometry" not in el:
            continue
        pts = [xz(g["lat"], g["lon"]) for g in el["geometry"]]
        if "building" in t:
            cx = sum(p[0] for p in pts) / len(pts)
            cz = sum(p[1] for p in pts) / len(pts)
            if inside(cx, cz) or math.hypot(cx, cz) > MAX_R:
                continue
            area = abs(sum(pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1] for i in range(len(pts)))) / 2
            if area < 45:
                continue
            pts = simplify(pts, 1.2)
            if pts[0] == pts[-1]:
                pts = pts[:-1]
            if len(pts) < 3:
                continue
            h = parse_height(t) or (12 if area < 400 else 16)
            bld.append([round(min(h, 300))] + [round(v) for p in pts for v in p])
        elif t.get("highway") in CLS:
            if all(inside(*p) for p in pts) or min(math.hypot(*p) for p in pts) > MAX_R:
                continue
            nm = t.get("name", t.get("ref", ""))
            if nm not in nidx:
                nidx[nm] = len(names)
                names.append(nm)
            roads.append([CLS[t["highway"]], nidx[nm]] + [round(v) for p in simplify(pts, 1.5) for v in p])
        elif t.get("natural") == "water" or t.get("leisure") == "park":
            if len(pts) < 4:
                continue
            (water if t.get("natural") == "water" else parks).append([round(v) for p in simplify(pts, 2) for v in p])
    land = coast_land(src.replace("osm_context", "osm_coast"))
    out = {"classes": CLASSES, "land": land, "names": names, "buildings": bld, "roads": roads, "parks": parks, "water": water,
           "simBox": {"x0": x0, "x1": x1, "z0": z0, "z1": z1}, "attribution": "© OpenStreetMap contributors (ODbL)"}
    json.dump(out, open(dst, "w"), separators=(",", ":"))
    print(f"context: {len(bld)} buildings, {len(roads)} roads, {len(parks)} parks, {len(water)} water")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
