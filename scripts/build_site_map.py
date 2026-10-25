"""Write a compact city map for the workspace site (mockup/site/shared/city.json).

The site draws plan thumbnails and the landing-page map from it: street centrelines (indexed by the
same edge ids the engine and SpacetimeDB use) and building footprints, rounded to whole metres.

Usage: python3 scripts/build_site_map.py
"""
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
world = json.loads((root / "data/processed/world.json").read_text())
snap = json.loads((root / "mockup/backend-snapshot/world.json").read_text())

r = lambda pts: [[round(x), round(z)] for x, z in pts]
xs = [x for e in world["edges"] for x, _ in e["p"]]
zs = [z for e in world["edges"] for _, z in e["p"]]
bx = sorted(x for b in world["buildings"] for x, _ in b["p"])
bz = sorted(z for b in world["buildings"] for _, z in b["p"])
q = lambda a, f: a[int(f * (len(a) - 1))]
out = {
    "bbox": [min(xs), min(zs), max(xs), max(zs)],
    # The built-up area (2nd-98th percentile of building corners): the default map frame, without the bridge.
    "view": [q(bx, .02) - 150, q(bz, .02) - 150, q(bx, .98) + 150, q(bz, .98) + 150],
    "names": world["names"],
    # [class, name index, polyline]; the list index is the edge id.
    "edges": [[e["c"], e.get("n", -1), r(e["p"])] for e in world["edges"]],
    # [height m, use, footprint]
    "buildings": [[round(b.get("h", 10)), b.get("k", ""), r(b["p"])] for b in world["buildings"]],
    "hero": snap.get("hero", {}).get("street_edges", []),
}
dst = root / "mockup/site/shared/city.json"
dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(json.dumps(out, separators=(",", ":")))
print(f"wrote {dst} ({dst.stat().st_size / 1e3:.0f} kB)")
