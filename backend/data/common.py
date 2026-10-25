"""Shared helpers for the data pipelines: paths, coordinates, cache, usage log.

Never log or persist API key values. Keys are read from the project .env.
"""
import datetime as _dt
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "data" / "backend"
WORLD_PATH = ROOT / "data" / "processed" / "world.json"
USAGE = CACHE / "USAGE.md"
UA = "CommonGround-CalHacks/1.0 (max@thiersch.com)"

# local-meter projection used by world.json
LON0, LAT0 = -122.3987, 37.7887
KX = math.cos(math.radians(LAT0)) * 111320.0
KZ = 110540.0

# area bbox (lat/lon)
S, W, N, E = 37.7800, -122.4095, 37.7975, -122.3880


def to_xz(lat, lon):
    return ((lon - LON0) * KX, -(lat - LAT0) * KZ)


def to_latlon(x, z):
    return (LAT0 - z / KZ, LON0 + x / KX)


def in_bbox(lat, lon, pad_deg=0.0):
    return (S - pad_deg) <= lat <= (N + pad_deg) and (W - pad_deg) <= lon <= (E + pad_deg)


def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except Exception:
        pass
    return os.environ


def load_world():
    with open(WORLD_PATH) as f:
        return json.load(f)


def now_iso():
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def cache_path(service, name):
    p = CACHE / service / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_params(path, params):
    """Write a sidecar .params.json; strips anything that looks like a secret."""
    safe = {k: v for k, v in params.items()
            if not any(s in k.lower() for s in ("key", "token", "secret", "password"))}
    safe["fetched_at"] = now_iso()
    Path(str(path) + ".params.json").write_text(json.dumps(safe, indent=2))


def log_usage(service, what, cost):
    USAGE.parent.mkdir(parents=True, exist_ok=True)
    new = not USAGE.exists()
    with open(USAGE, "a") as f:
        if new:
            f.write("# External API usage log\n\n| time (UTC) | service | what | approx cost |\n|---|---|---|---|\n")
        f.write(f"| {now_iso()} | {service} | {what} | {cost} |\n")


def write_out(name, obj):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    with open(p, "w") as f:
        json.dump(obj, f, separators=(",", ":"))
    print(f"wrote {p} ({p.stat().st_size/1024:.1f} KB)")
    return p


def http_client(**kw):
    import httpx
    headers = {"User-Agent": UA}
    headers.update(kw.pop("headers", {}))
    return httpx.Client(headers=headers, timeout=kw.pop("timeout", 120), follow_redirects=True, **kw)


def download(url, path, service, cost="free", params=None):
    """Download url to path unless cached. Returns path."""
    path = Path(path)
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    with http_client(timeout=600) as c:
        with c.stream("GET", url) as r:
            r.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in r.iter_bytes(1 << 20):
                    f.write(chunk)
    tmp.rename(path)
    write_params(path, dict(params or {}, url=url))
    log_usage(service, f"GET {url}", cost)
    return path


# ---------- geometry ----------
def point_in_ring(x, y, ring):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y):
            xint = (xj - xi) * (y - yi) / ((yj - yi) or 1e-30) + xi
            if x < xint:
                inside = not inside
        j = i
    return inside


def point_in_polygon(x, y, poly):
    """poly = [outer_ring, hole1, ...]"""
    if not poly or not point_in_ring(x, y, poly[0]):
        return False
    return not any(point_in_ring(x, y, h) for h in poly[1:])


def point_in_multipolygon(x, y, mpoly):
    return any(point_in_polygon(x, y, p) for p in mpoly)


def ring_area(ring):
    a = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % len(ring)][0], ring[(i + 1) % len(ring)][1]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy)


def polyline_dist(px, py, pl):
    if len(pl) == 1:
        return math.hypot(px - pl[0][0], py - pl[0][1])
    return min(seg_dist(px, py, pl[i][0], pl[i][1], pl[i + 1][0], pl[i + 1][1]) for i in range(len(pl) - 1))
