"""Fetch (and cache) the OpenStreetMap data for one city environment.

Usage: python3 scripts/fetch_city.py chicago|nyc [--force]

Four Overpass queries, each cached under data/raw/<city>/ and skipped when the file exists:
core (simulation box), context (surrounding city), coast (coastline + water), parts (building parts, roofs).
"""
import json
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from cities import CITIES, context_bbox, paths  # noqa: E402

MIRRORS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
           "https://overpass.private.coffee/api/interpreter"]
HW_CORE = "motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|tertiary_link|residential|unclassified|living_street|pedestrian|service"
HW_CTX = "motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|tertiary|residential|unclassified|pedestrian"


def bb(b):
    return f"({b[0]:.5f},{b[1]:.5f},{b[2]:.5f},{b[3]:.5f})"


def queries(city):
    c = CITIES[city]["bbox"]
    pad = (c[0] - 0.0010, c[1] - 0.0012, c[2] + 0.0010, c[3] + 0.0012)
    ctx = context_bbox(city)
    wide = context_bbox(city, 3.6)
    return {
        "core": f"""[out:json][timeout:240];(way["building"]{bb(c)};relation["building"]{bb(c)};way["highway"~"^({HW_CORE})$"]{bb(pad)};
node["railway"="subway_entrance"]{bb(c)};node["railway"="station"]{bb(c)};node["public_transport"="station"]{bb(c)};
node["station"="subway"]{bb(c)};way["leisure"~"park|plaza"]{bb(c)};way["place"="square"]{bb(c)};
node["amenity"~"cafe|restaurant|fast_food|bar|pub"]{bb(c)};node["shop"]{bb(c)};);out geom tags;""",
        "context": f"""[out:json][timeout:300];(way["building"]{bb(ctx)};way["highway"~"^({HW_CTX})$"]{bb(wide)};
way["leisure"="park"]{bb(ctx)};);out geom tags;""",
        "coast": f"""[out:json][timeout:180];(way["natural"="coastline"]{bb(wide)};way["natural"="water"]{bb(wide)};
relation["natural"="water"]{bb(wide)};way["waterway"="riverbank"]{bb(wide)};);out geom tags;""",
        **({"shore": f"""[out:json][timeout:180];relation["natural"="water"]["name"="{CITIES[city]['lake']}"];way(r){bb(wide)};out geom tags;"""}
           if CITIES[city].get("lake") else {}),
        "parts": f"""[out:json][timeout:240];(way["building:part"]{bb(pad)};way["building"]["roof:shape"]{bb(pad)};
way["building"]["building:colour"]{bb(pad)};way["building"]["building:material"]{bb(pad)};);out geom tags;""",
    }


def fetch(q, out):
    """POST the query with curl (system certificates), trying each mirror, with exponential backoff."""
    import subprocess
    wait = 15
    tmp = out.with_suffix(".tmp")
    for attempt in range(6):
        for url in MIRRORS:
            r = subprocess.run(["curl", "-s", "-m", "330", "-A", "HumanProject-hackathon/0.1", "--data-urlencode", f"data={q}",
                                url, "-o", str(tmp)], capture_output=True)
            try:
                data = tmp.read_bytes()
                if data[:1] == b"{":
                    json.loads(data)
                    tmp.replace(out)
                    return True
                print(f"  {url.split('/')[2]}: {data[:60]!r}", flush=True)
            except (OSError, ValueError) as ex:
                print(f"  {url.split('/')[2]}: {type(ex).__name__} (curl exit {r.returncode})", flush=True)
        print(f"  retry in {wait}s", flush=True)
        time.sleep(wait)
        wait *= 2
    return False


def main(city, force=False):
    p = paths(city)
    p["raw"].mkdir(parents=True, exist_ok=True)
    for name, q in queries(city).items():
        out = p.get(name, p["raw"] / f"osm_{name}.json")
        if out.exists() and out.stat().st_size > 1000 and not force:
            print(f"{city}/{name}: cached ({out.stat().st_size / 1e6:.1f} MB)")
            continue
        print(f"{city}/{name}: fetching…", flush=True)
        ok = fetch(q, out)
        print(f"{city}/{name}: {'ok' if ok else 'FAILED'} {out.stat().st_size / 1e6:.1f} MB" if ok else f"{city}/{name}: FAILED", flush=True)
        time.sleep(3)


if __name__ == "__main__":
    main(sys.argv[1], "--force" in sys.argv)
