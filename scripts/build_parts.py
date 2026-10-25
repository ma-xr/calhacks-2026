"""Attach OSM building:part geometry, roof shapes, colours and materials to world.json buildings.

Usage: python3 scripts/build_parts.py data/raw/osm_parts_2026-10-24.json data/processed/buildings_detail.json

Output, keyed by world building index:
  parts: { "<bid>": [ {"p": [x0, z0, ...], "h": top, "mh": base, "roof": shape, "rh": roof height, "col": "#rrggbb"|null, "mat": str|null} ] }
  tags:  { "<bid>": {"roof", "rh", "col", "mat"} }   for buildings without parts
"""
import json
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import build_world as _BW  # noqa: E402
simplify = _BW.simplify
xz = lambda lat, lon: _BW.xz(lat, lon)  # noqa: E731  (late-bound so --city takes effect)

COLOURS = {"white": "#f2f2ee", "grey": "#9a9a9a", "gray": "#9a9a9a", "black": "#2a2a2a", "red": "#9a3b2e", "brown": "#7a5a43",
           "beige": "#d8c8a8", "yellow": "#d8c060", "blue": "#5a7aa0", "silver": "#c8ccd0", "tan": "#cdb48c", "cream": "#efe6cf"}


def num(v):
    if v is None:
        return None
    m = re.match(r"\s*([0-9.]+)", str(v))
    return float(m.group(1)) if m else None


def colour(v):
    if not v:
        return None
    v = v.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{6}", v):
        return v
    return COLOURS.get(v)


def heights(t):
    h = num(t.get("height"))
    if h is None and num(t.get("building:levels")) is not None:
        h = num(t["building:levels"]) * 3.6 + (num(t.get("roof:levels")) or 0) * 3.0
    mh = num(t.get("min_height"))
    if mh is None and num(t.get("building:min_level")) is not None:
        mh = num(t["building:min_level"]) * 3.6
    return h, mh or 0.0


def inside(poly, x, z):
    ins, n = False, len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
            ins = not ins
    return ins


def main(src, dst, world="data/processed/world.json"):
    B = json.load(open(world))["buildings"]
    els = json.load(open(src))["elements"]
    parts, tags = {}, {}

    def owner(cx, cz):
        for i, b in enumerate(B):
            if abs(b["c"][0] - cx) < 220 and abs(b["c"][1] - cz) < 220 and inside(b["p"], cx, cz):
                return i
        return None

    for el in els:
        t = el.get("tags", {})
        if "geometry" not in el:
            continue
        pts = [xz(g["lat"], g["lon"]) for g in el["geometry"]]
        if pts[0] == pts[-1]:
            pts = pts[:-1]
        if len(pts) < 3:
            continue
        cx = sum(p[0] for p in pts) / len(pts)
        cz = sum(p[1] for p in pts) / len(pts)
        bid = owner(cx, cz)
        if bid is None:
            continue
        info = {"roof": t.get("roof:shape"), "rh": num(t.get("roof:height")),
                "col": colour(t.get("building:colour") or t.get("colour")), "mat": t.get("building:material")}
        if "building:part" in t:
            h, mh = heights(t)
            if h is None:
                h = B[bid]["h"]
            if h <= mh + 0.5:
                continue
            parts.setdefault(str(bid), []).append({"p": [round(v, 1) for p in simplify(pts, 0.4) for v in p],
                                                   "h": round(h, 1), "mh": round(mh, 1), **info})
        elif any(info.values()):
            tags[str(bid)] = info
    json.dump({"parts": parts, "tags": tags}, open(dst, "w"), separators=(",", ":"))
    print(f"detail: {len(parts)} buildings with {sum(len(v) for v in parts.values())} parts, {len(tags)} tagged")


if __name__ == "__main__":
    import build_world as BW
    if "--city" in sys.argv:
        BW.configure(sys.argv[sys.argv.index("--city") + 1])
    main(sys.argv[1], sys.argv[2], *(sys.argv[sys.argv.index("--world") + 1:sys.argv.index("--world") + 2] if "--world" in sys.argv else []))
