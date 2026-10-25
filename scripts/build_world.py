"""Convert an Overpass snapshot of FiDi + upper SoMa into a compact world file.

Usage: python3 scripts/build_world.py data/raw/osm_fidi_soma_2026-10-24.json data/processed/world.json

Coordinates are local meters: x east, z south, origin at LAT0/LON0.
"""
import json
import math
import sys
from collections import defaultdict

CITY = "sf"
LAT0, LON0 = 37.7887, -122.3987
KX = math.cos(math.radians(LAT0)) * 111320.0
KZ = 110540.0
BBOX = (37.7800, -122.4095, 37.7975, -122.3880)  # s, w, n, e

CAR_CLASSES = {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link",
               "secondary", "secondary_link", "tertiary", "tertiary_link", "residential",
               "unclassified", "living_street"}
PED_CLASSES = (CAR_CLASSES - {"motorway", "motorway_link", "trunk", "trunk_link"}) | {"pedestrian"}
ROAD_CLASSES = CAR_CLASSES | {"pedestrian"}


def configure(city):
    """Switch the module to another city's frame and simulation box (see scripts/cities.py)."""
    global LAT0, LON0, KX, BBOX, CITY
    from cities import CITIES
    CITY = city
    c = CITIES[city]
    LAT0, LON0 = c["center"]
    KX = math.cos(math.radians(LAT0)) * 111320.0
    BBOX = tuple(c["bbox"])


def xz(lat, lon):
    return (round((lon - LON0) * KX, 1), round(-(lat - LAT0) * KZ, 1))


def parse_height(tags):
    h = tags.get("height") or tags.get("building:height")
    if h:
        try:
            return float(h.replace("m", "").strip().split(";")[0])
        except ValueError:
            pass
    lv = tags.get("building:levels")
    if lv:
        try:
            return float(lv.split(";")[0]) * 3.6
        except ValueError:
            pass
    return None


def kind_of(tags, h):
    b = tags.get("building", "yes")
    if b in ("apartments", "residential", "house", "dormitory"):
        return "res"
    if b in ("office",):
        return "office"
    if b in ("retail", "commercial", "supermarket", "kiosk"):
        return "retail"
    if b in ("hotel",):
        return "hotel"
    if b in ("parking", "garage", "garages"):
        return "parking"
    if b in ("church", "civic", "public", "government", "museum", "train_station", "transportation"):
        return "civic"
    if h and h > 45:
        return "office"
    return "mixed"


def simplify(pts, tol=0.6):
    """Drop nearly collinear points (cheap Douglas-Peucker stand-in)."""
    if len(pts) <= 4:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        ax, az = out[-1]
        bx, bz = pts[i]
        cx, cz = pts[i + 1]
        area = abs((bx - ax) * (cz - az) - (bz - az) * (cx - ax))
        base = math.hypot(cx - ax, cz - az) or 1
        if area / base > tol:
            out.append(pts[i])
    out.append(pts[-1])
    return out


def outer_ring(rel):
    """Largest closed ring assembled from a multipolygon relation's outer members (geometry as [{lat, lon}])."""
    segs = [[(g["lat"], g["lon"]) for g in m["geometry"]] for m in rel["members"]
            if m.get("role") in ("outer", "") and m.get("geometry")]
    rings = []
    while segs:
        c = segs.pop(0)
        grown = True
        while grown and c[0] != c[-1]:
            grown = False
            for i, sg in enumerate(segs):
                if sg[0] == c[-1]: c += sg[1:]
                elif sg[-1] == c[-1]: c += sg[::-1][1:]
                elif sg[-1] == c[0]: c = sg[:-1] + c
                elif sg[0] == c[0]: c = sg[::-1][:-1] + c
                else: continue
                segs.pop(i); grown = True; break
        if c[0] == c[-1] and len(c) >= 4:
            rings.append(c)
    if not rings:
        return None
    area = lambda r: abs(sum(a[1] * b[0] - b[1] * a[0] for a, b in zip(r, r[1:])))  # noqa: E731
    return [{"lat": la, "lon": lo} for la, lo in max(rings, key=area)]


def main(src, dst):
    els = json.load(open(src))["elements"]
    s, w, n, e = BBOX

    buildings, roads, pois, parks = [], [], [], []
    stations = defaultdict(list)

    for el in els:
        t = el.get("tags", {})
        if el["type"] == "relation" and "building" in t and el.get("members"):
            ring = outer_ring(el)          # multipolygon buildings (e.g. the Art Institute): use the largest outer ring
            if not ring:
                continue
            el = {**el, "type": "way", "geometry": ring}
        if el["type"] == "way" and "building" in t and "geometry" in el:
            pts = simplify([xz(g["lat"], g["lon"]) for g in el["geometry"]])
            if len(pts) < 4:
                continue
            if pts[0] == pts[-1]:
                pts = pts[:-1]
            h = parse_height(t)
            k = kind_of(t, h)
            if h is None:
                h = {"office": 40, "res": 18, "retail": 10, "hotel": 30, "parking": 14,
                     "civic": 16}.get(k, 14)
            cx = sum(p[0] for p in pts) / len(pts)
            cz = sum(p[1] for p in pts) / len(pts)
            b = {"p": pts, "h": round(min(h, 560), 1), "k": k, "c": [round(cx, 1), round(cz, 1)]}
            if t.get("name"):
                b["n"] = t["name"]
            buildings.append(b)
        elif el["type"] == "way" and t.get("highway") in ROAD_CLASSES and "geometry" in el:
            roads.append(el)
        elif el["type"] == "way" and (t.get("leisure") in ("park", "plaza") or t.get("place") == "square"
                                      or t.get("highway") == "pedestrian" and t.get("area") == "yes"):
            if "geometry" in el:
                parks.append({"p": [xz(g["lat"], g["lon"]) for g in el["geometry"]],
                              "n": t.get("name", "")})
        elif el["type"] == "node":
            x, z = xz(el["lat"], el["lon"])
            if t.get("railway") == "subway_entrance":
                stations["_entr"].append((x, z, t.get("name", "")))
            elif t.get("public_transport") == "station":
                nm = t.get("name", "Station")
                if nm in ("Brannan", "Folsom"):  # Muni surface stops on the Embarcadero
                    continue
                stations[nm].append((x, z))
            elif t.get("amenity") in ("cafe", "restaurant", "fast_food", "bar", "pub") or "shop" in t:
                if not t.get("name"):
                    continue
                cat = t.get("amenity") or "shop"
                if cat in ("pub",):
                    cat = "bar"
                pois.append({"x": x, "z": z, "n": t["name"], "c": cat})

    # Group subway entrances by nearest station.
    st_centers = {nm: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v))
                  for nm, v in stations.items() if nm != "_entr"}
    st_out = {nm: {"name": nm, "c": [round(c[0], 1), round(c[1], 1)], "e": []} for nm, c in st_centers.items()}
    for x, z, _ in stations.get("_entr", []):
        best = min(st_centers, key=lambda k: (st_centers[k][0] - x) ** 2 + (st_centers[k][1] - z) ** 2)
        if math.hypot(st_centers[best][0] - x, st_centers[best][1] - z) < 450:
            st_out[best]["e"].append([x, z])
    for v in st_out.values():
        if not v["e"]:
            v["e"].append(v["c"])

    # Road graph, split at shared nodes and way ends.
    # Overpass "out geom" omits node ids, so shared nodes are matched by coordinate.
    for r in roads:
        r["nodes"] = [(g["lat"], g["lon"]) for g in r["geometry"]]
    use = defaultdict(int)
    for r in roads:
        for i, nd in enumerate(r["nodes"]):
            use[nd] += 2 if i in (0, len(r["nodes"]) - 1) else 1
    key = {nd for nd, c in use.items() if c >= 2}
    node_xyz, node_idx = [], {}

    def nid(osm_id, lat, lon):
        if osm_id not in node_idx:
            node_idx[osm_id] = len(node_xyz)
            node_xyz.append(xz(lat, lon))
        return node_idx[osm_id]

    names, name_idx = [], {}

    def name_id(nm):
        if nm not in name_idx:
            name_idx[nm] = len(names)
            names.append(nm)
        return name_idx[nm]

    edges = []
    for r in roads:
        t = r["tags"]
        cls = t["highway"]
        ow = t.get("oneway", "yes" if cls in ("motorway", "motorway_link") else "no")
        ow = 1 if ow in ("yes", "true", "1") else (-1 if ow == "-1" else 0)
        nm = name_id(t.get("name", t.get("ref", "")))
        lanes = t.get("lanes")
        try:
            lanes = int(str(lanes).split(";")[0]) if lanes else None
        except ValueError:
            lanes = None
        geo, nds = r["geometry"], r["nodes"]
        start = 0
        for i in range(1, len(nds)):
            if nds[i] in key or i == len(nds) - 1:
                pts = [xz(g["lat"], g["lon"]) for g in geo[start:i + 1]]
                ln = sum(math.hypot(pts[j + 1][0] - pts[j][0], pts[j + 1][1] - pts[j][1]) for j in range(len(pts) - 1))
                if ln > 0.5:
                    a = nid(nds[start], geo[start]["lat"], geo[start]["lon"])
                    b = nid(nds[i], geo[i]["lat"], geo[i]["lon"])
                    edges.append({"a": a, "b": b, "c": cls, "n": nm, "o": ow, "l": round(ln, 1),
                                  "ln": lanes, "p": simplify(pts, 0.3)})
                start = i

    # Gateways. Two kinds, both kept:
    #  "end":   road ends (degree 1) near the bbox edge. The original rule; the legacy inlets use these.
    #  "cross": every car-usable road edge that crosses the bbox boundary (one end inside, one outside).
    #           OSM ways are not clipped, so most arterials continue past the edge and never leave a clean dead end.
    deg = defaultdict(int)
    for ed in edges:
        deg[ed["a"]] += 1
        deg[ed["b"]] += 1
    gw = []
    xs = [xz(s, w)[0], xz(n, e)[0]]
    zs = [xz(n, e)[1], xz(s, w)[1]]

    def inside(p):
        return xs[0] < p[0] < xs[1] and zs[0] < p[1] < zs[1]

    def side_of(p):
        d = {"west": abs(p[0] - xs[0]), "east": abs(p[0] - xs[1]), "north": abs(p[1] - zs[0]), "south": abs(p[1] - zs[1])}
        return min(d, key=d.get)

    def hw_label(x, name=""):
        if CITY == "sf":   # SF's two freeway gateways keep the names the engine and pages key on
            return "I-80 · Bay Bridge" if x > 1000 else "US-101 / I-80 West"
        return name or "Freeway"

    def boundary_point(pts):
        """Where a polyline first crosses the bbox boundary (linear interpolation on the crossing segment)."""
        for j in range(len(pts) - 1):
            p, q = pts[j], pts[j + 1]
            if inside(p) != inside(q):
                lo, hi = (p, q) if inside(p) else (q, p)
                for _ in range(30):  # bisection on the segment
                    mid = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2)
                    lo, hi = (mid, hi) if inside(mid) else (lo, mid)
                return [round(lo[0], 1), round(lo[1], 1)]
        return [round(pts[0][0], 1), round(pts[0][1], 1)]

    for ed in edges:
        for end, other in (("a", "b"), ("b", "a")):
            v = ed[end]
            if deg[v] != 1:
                continue
            x, z = node_xyz[v]
            margin = min(abs(x - xs[0]), abs(x - xs[1]), abs(z - zs[0]), abs(z - zs[1]))
            hw = ed["c"].startswith("motorway")
            if not hw and margin > 140 or ed["c"] not in CAR_CLASSES or ed["c"] in ("residential", "unclassified", "living_street", "tertiary_link"):
                continue
            inbound = ed["o"] == 0 or (ed["o"] == 1 and end == "a") or (ed["o"] == -1 and end == "b")
            outbound = ed["o"] == 0 or (ed["o"] == 1 and end == "b") or (ed["o"] == -1 and end == "a")
            label = hw_label(x, names[ed["n"]]) if hw else names[ed["n"]]
            gw.append({"node": v, "in": inbound, "out": outbound, "hw": hw, "name": label, "cls": ed["c"],
                       "src": "end", "side": side_of((x, z)), "lanes": ed.get("ln")})

    THROUGH_MINOR = ("residential", "unclassified")
    for ei, ed in enumerate(edges):
        if ed["c"] not in CAR_CLASSES or ed["c"] == "living_street":
            continue
        pa, pb = node_xyz[ed["a"]], node_xyz[ed["b"]]
        if inside(pa) == inside(pb):
            continue
        out_end, in_end = ("a", "b") if not inside(pa) else ("b", "a")
        # Minor streets count only if they connect through to the network inside (reach an intersection).
        if ed["c"] in THROUGH_MINOR and deg[ed[in_end]] < 3:
            continue
        o = ed["o"]
        inbound = o == 0 or (o == 1 and out_end == "a") or (o == -1 and out_end == "b")
        outbound = o == 0 or (o == 1 and out_end == "b") or (o == -1 and out_end == "a")
        hw = ed["c"].startswith("motorway")
        v = ed[out_end]
        bp = boundary_point(ed["p"])
        label = hw_label(node_xyz[v][0], names[ed["n"]]) if hw else (names[ed["n"]] or ed["c"].replace("_", " ").capitalize())
        gw.append({"node": v, "in": inbound, "out": outbound, "hw": hw, "name": label, "cls": ed["c"],
                   "src": "cross", "side": side_of(bp), "edge": ei, "at": bp, "lanes": ed.get("ln")})

    world = {
        "origin": [LAT0, LON0],
        "bbox": {"x0": xs[0], "x1": xs[1], "z0": zs[0], "z1": zs[1]},
        "buildings": buildings,
        "nodes": node_xyz,
        "edges": edges,
        "names": names,
        "stations": list(st_out.values()),
        "gateways": gw,
        "pois": pois,
        "parks": parks,
        "attribution": "© OpenStreetMap contributors (ODbL)",
    }
    json.dump(world, open(dst, "w"), separators=(",", ":"))
    print(f"buildings={len(buildings)} nodes={len(node_xyz)} edges={len(edges)} pois={len(pois)} "
          f"stations={[(v['name'], len(v['e'])) for v in st_out.values()]} gateways={len(gw)} parks={len(parks)}")
    print(f"{'src':5} {'side':5} {'street':28} {'class':14} dir     node")
    for g in sorted(gw, key=lambda g: (g["src"], g["side"], g["name"])):
        d = ("in " if g["in"] else "   ") + ("out" if g["out"] else "   ")
        print(f"{g['src']:5} {g['side']:5} {g['name'][:28]:28} {g['cls']:14} {d}  {g['node']}")


if __name__ == "__main__":
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    if "--city" in sys.argv:
        configure(sys.argv[sys.argv.index("--city") + 1])
    main(sys.argv[1], sys.argv[2])
