"""Build the faded city context around the simulation area (any city in scripts/cities.py).

Usage: python3 scripts/build_context.py <osm_context.json> <context.json> [--city sf|chicago|nyc]

The coastline and water polygons are read from the sibling file whose name has "osm_context" replaced
by "osm_coast". Same local-meter frame as world.json. Buildings inside the simulation bbox are dropped
(the simulation renders them). Compact encoding:
  buildings: [h, x0, z0, x1, z1, ...]   (meters, ints)
  roads:     [cls, nameIdx, x0, z0, ...]  (cls index into CLASSES)
  land / parks / water: [x0, z0, x1, z1, ...]
"""
import json
import math
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import build_world as BW  # noqa: E402

CLASSES = ["motorway", "trunk", "primary", "secondary", "tertiary", "residential", "pedestrian"]
CLS = {"motorway": 0, "motorway_link": 0, "trunk": 1, "trunk_link": 1, "primary": 2, "primary_link": 2,
       "secondary": 3, "secondary_link": 3, "tertiary": 4, "residential": 5, "unclassified": 5, "pedestrian": 6}
MAX_R = 2600  # meters from origin; beyond this everything has faded out anyway


def _chain(segs):
    """Join polylines that share endpoints (direction kept where possible). Returns closed rings and open chains."""
    segs = [list(s) for s in segs if len(s) >= 2]
    out = []
    while segs:
        c = segs.pop(0)
        grown = True
        while grown and c[0] != c[-1]:
            grown = False
            for i, sg in enumerate(segs):
                if sg[0] == c[-1]:
                    c += sg[1:]
                elif sg[-1] == c[0]:
                    c = sg[:-1] + c
                elif sg[-1] == c[-1]:
                    c += sg[::-1][1:]
                elif sg[0] == c[0]:
                    c = sg[::-1][:-1] + c
                else:
                    continue
                segs.pop(i)
                grown = True
                break
        out.append(c)
    return out


def _clip(chain, S):
    """Clip a polyline (x, y north-up) to the square [-S, S]^2. Returns the inside pieces; endpoints on the edge."""
    inside = lambda p: -S <= p[0] <= S and -S <= p[1] <= S  # noqa: E731
    pieces, cur = [], []
    for a, b in zip(chain, chain[1:]):
        ia, ib = inside(a), inside(b)
        if ia and not cur:
            cur = [a]
        # Liang-Barsky for the segment a-b
        t0, t1, dx, dy = 0.0, 1.0, b[0] - a[0], b[1] - a[1]
        ok = True
        for p, q in ((-dx, a[0] + S), (dx, S - a[0]), (-dy, a[1] + S), (dy, S - a[1])):
            if p == 0:
                if q < 0:
                    ok = False
                continue
            r = q / p
            if p < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
        if not ok or t0 > t1:
            continue
        pa = (a[0] + t0 * dx, a[1] + t0 * dy)
        pb = (a[0] + t1 * dx, a[1] + t1 * dy)
        if not cur:
            cur = [pa]
        cur.append(pb)
        if not ib:
            pieces.append(cur)
            cur = []
    if len(cur) >= 2:
        pieces.append(cur)
    return pieces


def coast_land(path, S=3500):
    """Land polygons from OSM coastline (land lies left of the line), clipped to a square of half-size S.
    Handles any number of shorelines, e.g. both sides of Manhattan. Returns flat [x0, z0, ...] lists."""
    try:
        els = json.load(open(path))["elements"]
    except (OSError, ValueError):
        return []
    lines = [[BW.xz(g["lat"], g["lon"]) for g in w["geometry"]] for w in els
             if w.get("type") == "way" and w.get("tags", {}).get("natural") == "coastline" and "geometry" in w]
    # A named lake's shoreline (e.g. Lake Michigan, mapped as a water area, not coastline): direction unknown.
    shore = path.replace("osm_coast", "osm_shore")
    oriented = True
    try:
        sw = json.load(open(shore))["elements"]
        extra = [[BW.xz(g["lat"], g["lon"]) for g in w["geometry"]] for w in sw if w.get("type") == "way" and "geometry" in w]
        if extra:
            lines += extra
            oriented = False
    except (OSError, ValueError):
        pass
    if not lines:
        return [[-S, -S, S, -S, S, S, -S, S]]   # no coast nearby: everything is land, water polygons draw on top
    polys = _trace(lines, S)
    if not oriented and not _covers(polys, 0.0, 0.0):  # the simulation center must be land: flip the shoreline
        polys = _trace([l[::-1] for l in lines], S)
    out = []
    for ring in polys:
        pts = BW.simplify([(x, -y) for x, y in ring], 2.0)
        if len(pts) >= 3:
            out.append([round(v) for p in pts for v in p])
    return out


def _covers(polys, x, y):
    for ring in polys:
        ins, n = False, len(ring)
        for i in range(n):
            x1, y1 = ring[i]
            x2, y2 = ring[(i + 1) % n]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                ins = not ins
        if ins:
            return True
    return False


def _trace(lines, S):
    """Clip shorelines (land on the left) to the square and close them along its edge into land rings (north-up)."""
    polys = []
    pieces = []
    for c in _chain(lines):
        xy = [(x, -z) for x, z in c]             # north-up frame
        if xy[0] == xy[-1] and all(-S <= p[0] <= S and -S <= p[1] <= S for p in xy):
            polys.append(xy[:-1])                  # island fully inside
            continue
        pieces += [p for p in _clip(xy, S) if len(p) >= 2]
    # Walk the square counter-clockwise from each piece's exit to the next piece's entry.
    def perim(p):
        x, y = p
        if abs(x - S) < 1e-6 and y < S:
            return y + S
        if abs(y - S) < 1e-6:
            return 2 * S + (S - x)
        if abs(x + S) < 1e-6:
            return 4 * S + (S - y)
        return 6 * S + (x + S)
    P = 8 * S
    corners = [(2 * S, (S, S)), (4 * S, (-S, S)), (6 * S, (-S, -S)), (0.0, (S, -S))]
    used = set()
    for i0 in range(len(pieces)):
        if i0 in used:
            continue
        ring, i = [], i0
        for _ in range(len(pieces) + 1):
            used.add(i)
            ring += pieces[i]
            te = perim(pieces[i][-1])
            nxt = min((j for j in range(len(pieces)) if j not in used or j == i0),
                      key=lambda j: (perim(pieces[j][0]) - te) % P)
            span = (perim(pieces[nxt][0]) - te) % P
            ring += [cp for d, cp in sorted(((tc - te) % P, cp) for tc, cp in corners) if 0 < d < span]
            if nxt == i0:
                break
            i = nxt
        polys.append(ring)
    return polys


def water_polys(path):
    """Rivers and lakes (natural=water ways and multipolygon outers, waterway=riverbank)."""
    try:
        els = json.load(open(path))["elements"]
    except (OSError, ValueError):
        return []
    rings = []
    for el in els:
        t = el.get("tags", {})
        if not (t.get("natural") == "water" or t.get("waterway") == "riverbank"):
            continue
        if el["type"] == "way" and "geometry" in el:
            rings.append([BW.xz(g["lat"], g["lon"]) for g in el["geometry"]])
        elif el["type"] == "relation":
            outers = [[BW.xz(g["lat"], g["lon"]) for g in m["geometry"]] for m in el.get("members", [])
                      if m.get("role") == "outer" and m.get("geometry")]
            rings += [r for r in _chain(outers) if r[0] == r[-1]]
    out = []
    for r in rings:
        if len(r) < 4 or min(math.hypot(*p) for p in r) > MAX_R + 1500:
            continue
        pts = BW.simplify(r[:-1] if r[0] == r[-1] else r, 2.0)
        if len(pts) >= 3:
            out.append([round(v) for p in pts for v in p])
    return out


def main(src, dst):
    s, w, n, e = BW.BBOX
    x0, z1 = BW.xz(s, w)
    x1, z0 = BW.xz(n, e)
    inside = lambda x, z: x0 < x < x1 and z0 < z < z1  # noqa: E731
    els = json.load(open(src))["elements"]
    bld, roads, parks, water, names, nidx = [], [], [], [], [], {}
    for el in els:
        t = el.get("tags", {})
        if "geometry" not in el:
            continue
        pts = [BW.xz(g["lat"], g["lon"]) for g in el["geometry"]]
        if "building" in t:
            cx = sum(p[0] for p in pts) / len(pts)
            cz = sum(p[1] for p in pts) / len(pts)
            if inside(cx, cz) or math.hypot(cx, cz) > MAX_R:
                continue
            area = abs(sum(pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1] for i in range(len(pts)))) / 2
            if area < 45:
                continue
            pts = BW.simplify(pts, 1.2)
            if pts[0] == pts[-1]:
                pts = pts[:-1]
            if len(pts) < 3:
                continue
            h = BW.parse_height(t) or (12 if area < 400 else 16)
            bld.append([round(min(h, 400))] + [round(v) for p in pts for v in p])
        elif t.get("highway") in CLS:
            if all(inside(*p) for p in pts) or min(math.hypot(*p) for p in pts) > MAX_R:
                continue
            nm = t.get("name", t.get("ref", ""))
            if nm not in nidx:
                nidx[nm] = len(names)
                names.append(nm)
            roads.append([CLS[t["highway"]], nidx[nm]] + [round(v) for p in BW.simplify(pts, 1.5) for v in p])
        elif t.get("natural") == "water" or t.get("leisure") == "park":
            if len(pts) < 4:
                continue
            (water if t.get("natural") == "water" else parks).append([round(v) for p in BW.simplify(pts, 2) for v in p])
    coast = src.replace("osm_context", "osm_coast")
    land = coast_land(coast)
    water += water_polys(coast)
    out = {"classes": CLASSES, "land": land, "names": names, "buildings": bld, "roads": roads, "parks": parks, "water": water,
           "simBox": {"x0": x0, "x1": x1, "z0": z0, "z1": z1}, "attribution": "© OpenStreetMap contributors (ODbL)"}
    json.dump(out, open(dst, "w"), separators=(",", ":"))
    print(f"context: {len(bld)} buildings, {len(roads)} roads, {len(parks)} parks, {len(water)} water, {len(land)} land")


if __name__ == "__main__":
    if "--city" in sys.argv:
        BW.configure(sys.argv[sys.argv.index("--city") + 1])
    main(sys.argv[1], sys.argv[2])
