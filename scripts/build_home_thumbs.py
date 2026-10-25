#!/usr/bin/env python3
"""Build the project thumbnails for the homepage (mockup/home/thumbs/*.svg).

  sf.svg        real footprints + roads from data/processed/world.json (roads carry class="rd" so the
                page can run animated dots along them)
  oakland.svg, barcelona.svg, nyc.svg, berlin.svg
                stylized, deterministic street-pattern sketches for projects still in setup. They are
                illustrations of the city form, not data.

Run: python3 scripts/build_home_thumbs.py
"""
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "mockup" / "home" / "thumbs"

BG = "#0b1730"
BLD = ["#1d3358", "#264372", "#31558c", "#4a74b0"]   # low → tall
ROAD = "#3b5f93"
MAJOR = "#5d86c0"
PARK = "#173a35"
WATER = "#0a2244"


def f(v):
    return f"{v:.0f}"


def ring(pts):
    return "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"


def line(pts):
    return "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts)


def svg(w, h, body, x0=0, y0=0):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{f(x0)} {f(y0)} {f(w)} {f(h)}" '
            f'preserveAspectRatio="xMidYMid slice">\n<rect x="{f(x0)}" y="{f(y0)}" width="{f(w)}" height="{f(h)}" fill="{BG}"/>\n'
            + body + "\n</svg>\n")


# ---------------------------------------------------------------- San Francisco (real data)
def build_sf():
    w = json.loads((ROOT / "data/processed/world.json").read_text())
    b = w["bbox"]
    parks = "".join(ring(p["p"]) for p in w["parks"])
    tiers = [[], [], [], []]
    for bd in w["buildings"]:
        h = bd["h"]
        t = 0 if h < 25 else 1 if h < 60 else 2 if h < 120 else 3
        tiers[t].append(ring(bd["p"]))
    minor, major, ped = [], [], []
    for e in w["edges"]:
        c = e["c"]
        if c in ("pedestrian", "living_street"):
            ped.append(line(e["p"]))
        elif c in ("primary", "secondary", "motorway", "primary_link", "motorway_link", "trunk"):
            major.append(line(e["p"]))
        else:
            minor.append(line(e["p"]))
    body = [f'<path fill="{PARK}" d="{parks}"/>',
            f'<g fill="none" stroke-linecap="round" stroke-linejoin="round">',
            f'<path stroke="{ROAD}" stroke-width="5" opacity=".7" d="{"".join(minor)}"/>',
            f'<path stroke="#6e5a2e" stroke-width="4" stroke-dasharray="6 6" opacity=".55" d="{"".join(ped)}"/>',
            "</g>"]
    for t, ds in enumerate(tiers):
        body.append(f'<path fill="{BLD[t]}" d="{"".join(ds)}"/>')
    # Major roads on top, one path each so the page can sample them for moving dots.
    body.append(f'<g fill="none" stroke="{MAJOR}" stroke-width="7" stroke-linecap="round" opacity=".8">')
    body += [f'<path class="rd" d="{d}"/>' for d in major]
    body.append("</g>")
    return svg(b["x1"] - b["x0"], b["z1"] - b["z0"], "\n".join(body), b["x0"], b["z0"])


# ---------------------------------------------------------------- stylized cities
W, H = 1000, 625


def blocks_grid(rng, ox, oy, ang, bw, bh, street, nx, ny, clip=None, jitter=0.0, split=0.4):
    """Rotated grid of blocks, each subdivided into a few footprints."""
    ca, sa = math.cos(ang), math.sin(ang)
    rot = lambda x, y: (ox + x * ca - y * sa, oy + x * sa + y * ca)
    out = [[], [], [], []]
    for i in range(-nx, nx):
        for j in range(-ny, ny):
            x, y = i * (bw + street), j * (bh + street)
            cx, cy = rot(x + bw / 2, y + bh / 2)
            if not (-80 < cx < W + 80 and -80 < cy < H + 80):
                continue
            if clip and not clip(cx, cy):
                continue
            if rng.random() < 0.06:
                continue
            # split the block into 2-4 lots
            lots = [(x, y, bw, bh)]
            for _ in range(rng.randint(1, 2)):
                nl = []
                for (lx, ly, lw, lh) in lots:
                    if rng.random() < split and lw > 18:
                        k = rng.uniform(.35, .65) * lw
                        nl += [(lx, ly, k - 2, lh), (lx + k + 2, ly, lw - k - 2, lh)]
                    elif lh > 18:
                        k = rng.uniform(.35, .65) * lh
                        nl += [(lx, ly, lw, k - 2), (lx, ly + k + 2, lw, lh - k - 2)]
                    else:
                        nl.append((lx, ly, lw, lh))
                lots = nl
            for (lx, ly, lw, lh) in lots:
                j_ = lambda: rng.uniform(-jitter, jitter)
                pts = [(lx + j_(), ly + j_()), (lx + lw + j_(), ly + j_()), (lx + lw + j_(), ly + lh + j_()), (lx + j_(), ly + lh + j_())]
                out[min(3, int(rng.random() ** 2.2 * 4))].append(ring([rot(px, py) for px, py in pts]))
    return out


def tiers_svg(tiers):
    return "\n".join(f'<path fill="{BLD[t]}" d="{"".join(ds)}"/>' for t, ds in enumerate(tiers) if ds)


def merge(*ts):
    return [sum((t[k] for t in ts), []) for k in range(4)]


def build_barcelona():
    # Cerdà's Eixample: chamfered perimeter blocks with open courtyards.
    rng = random.Random(7)
    ang = math.radians(-45 + 1.5)
    ca, sa = math.cos(ang), math.sin(ang)
    rot = lambda x, y: (500 + x * ca - y * sa, 312 + x * sa + y * ca)
    bw, st = 64, 14
    oct_ = lambda x, y, s, c: [(x + c, y), (x + s - c, y), (x + s, y + c), (x + s, y + s - c),
                               (x + s - c, y + s), (x + c, y + s), (x, y + s - c), (x, y + c)]
    tiers, yards = [[], [], [], []], []
    for i in range(-12, 12):
        for j in range(-12, 12):
            x, y = i * (bw + st), j * (bw + st)
            cx, cy = rot(x + bw / 2, y + bw / 2)
            if not (-80 < cx < W + 80 and -80 < cy < H + 80):
                continue
            tiers[min(3, int(rng.random() ** 2 * 4))].append(ring([rot(*p) for p in oct_(x, y, bw, 14)]))
            if rng.random() < .85:
                k = rng.uniform(15, 20)
                yards.append(ring([rot(*p) for p in oct_(x + k, y + k, bw - 2 * k, 6)]))
    body = tiers_svg(tiers) + f'\n<path fill="{BG}" d="{"".join(yards)}"/>'
    diag = f'<path d="M-40 520L1040 150" stroke="{MAJOR}" stroke-width="16" opacity=".85" fill="none"/>'
    gv = f'<path d="M-40 360L1040 330" stroke="{MAJOR}" stroke-width="10" opacity=".6" fill="none"/>'
    return svg(W, H, body + "\n" + diag + "\n" + gv)


def build_nyc():
    rng = random.Random(11)
    shore = [(-50, 40), (240, 30), (520, 60), (760, 160), (860, 330), (820, 470), (690, 560), (520, 600), (380, 640), (-50, 660)]
    water = f'<rect width="{W}" height="{H}" fill="{WATER}"/>'
    land = f'<path fill="{BG}" d="{ring(shore)}"/>'

    def inside(x, y):
        n, c = len(shore), False
        for k in range(n):
            (x1, y1), (x2, y2) = shore[k], shore[(k + 1) % n]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                c = not c
        return c
    a = blocks_grid(rng, 260, 220, math.radians(29), 36, 70, 9, 14, 10, clip=lambda x, y: inside(x, y) and x < 470, jitter=2)
    b = blocks_grid(rng, 640, 360, math.radians(-8), 30, 34, 8, 14, 10, clip=lambda x, y: inside(x, y) and x >= 470, jitter=3, split=.6)
    bway = f'<path d="M180 640L600 260L720 170" stroke="{MAJOR}" stroke-width="10" opacity=".75" fill="none"/>'
    return svg(W, H, water + "\n" + land + "\n" + tiers_svg(merge(a, b)) + "\n" + bway)


def build_berlin():
    rng = random.Random(3)
    river = [(-40, 260), (140, 300), (300, 250), (450, 330), (600, 300), (760, 380), (1040, 340)]
    t = blocks_grid(rng, 500, 312, math.radians(6), 78, 58, 13, 10, 10, jitter=4, split=.55,
                    clip=lambda x, y: not any(math.hypot(x - rx, y - ry) < 55 for rx, ry in river))
    r = f'<path d="{line(river)}" stroke="{WATER}" stroke-width="58" fill="none" stroke-linejoin="round" stroke-linecap="round"/>'
    udl = f'<path d="M-40 200L1040 150" stroke="{MAJOR}" stroke-width="14" opacity=".75" fill="none"/>'
    fried = f'<path d="M560 -20L590 660" stroke="{MAJOR}" stroke-width="9" opacity=".6" fill="none"/>'
    return svg(W, H, tiers_svg(t) + "\n" + r + "\n" + udl + "\n" + fried)


def build_oakland():
    rng = random.Random(5)
    lake = (760, 300, 150, 110)
    t = blocks_grid(rng, 420, 300, math.radians(-27), 52, 42, 11, 13, 13, jitter=2, split=.45,
                    clip=lambda x, y: ((x - lake[0]) / lake[2]) ** 2 + ((y - lake[1]) / lake[3]) ** 2 > 1.15)
    lk = f'<ellipse cx="{lake[0]}" cy="{lake[1]}" rx="{lake[2]}" ry="{lake[3]}" fill="{WATER}" transform="rotate(-20 {lake[0]} {lake[1]})"/>'
    bwy = f'<path d="M80 660L620 -20" stroke="{MAJOR}" stroke-width="11" opacity=".7" fill="none"/>'
    i980 = f'<path d="M-40 140L420 420L560 660" stroke="{ROAD}" stroke-width="18" opacity=".7" fill="none"/>'
    return svg(W, H, tiers_svg(t) + "\n" + lk + "\n" + i980 + "\n" + bwy)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in [("sf", build_sf), ("oakland", build_oakland), ("barcelona", build_barcelona),
                     ("nyc", build_nyc), ("berlin", build_berlin)]:
        s = fn()
        (OUT / f"{name}.svg").write_text(s)
        print(f"{name}.svg  {len(s) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
