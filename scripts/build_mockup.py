"""Inject the processed world file (and the backend connector) into a mockup template.

Usage:
  python3 scripts/build_mockup.py                      # mockup/template.html -> mockup/blockwise-demo.html
  python3 scripts/build_mockup.py <template> <output>  # any variant
  python3 scripts/build_mockup.py <template> <output> --city chicago   # another city's data (see scripts/cities.py)

--city picks data/processed/<city>/ (SF: data/processed/) for world, context and building detail, and replaces
__CITY__ with that city's city.json. The engine snapshot is only copied for SF.

If the template contains /*__HP_BACKEND__*/, mockup/lib/hp-backend.js is inlined there and
mockup/backend-snapshot/ is copied next to the output as backend-snapshot/.
If it contains /*__HP_CONTEXT__*/, mockup/lib/hp-context.js (with data/processed/context.json) is inlined there.
If it contains /*__HP_BUILDINGS__*/, mockup/lib/hp-buildings.js (with data/processed/buildings_detail.json) is inlined there.
Generic markers: /*__HP_LIB:<name>__*/ inlines mockup/lib/<name>.js (hp-live also copies live.mjs next to the output),
/*__HP_CSS:<name>__*/ inlines mockup/lib/<name>.css.
"""
import json
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:]]
city = "sf"
if "--city" in args:
    k = args.index("--city"); city = args[k + 1]; del args[k:k + 2]
src = Path(args[0]) if len(args) > 1 else root / "mockup/template.html"
dst = Path(args[1]) if len(args) > 1 else root / "mockup/blockwise-demo.html"
data = root / "data/processed" if city == "sf" else root / "data/processed" / city
world = json.loads((data / "world.json").read_text())
blob = json.dumps(world, separators=(",", ":")).replace("</", "<\\/")
html = src.read_text().replace("__WORLD__", blob)
if "__CITY__" in html:
    html = html.replace("__CITY__", (data / "city.json").read_text().replace("</", "<\\/"))
if "/*__HP_BACKEND__*/" in html:
    lib = (root / "mockup/lib/hp-backend.js").read_text().replace("</script", "<\\/script")
    html = html.replace("/*__HP_BACKEND__*/", lib)
    snap = root / "mockup/backend-snapshot"
    if snap.exists() and city == "sf":
        target = dst.parent / "backend-snapshot"
        if target.resolve() != snap.resolve():
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(snap, target)
if "/*__HP_CONTEXT__*/" in html:
    ctx = (data / "context.json").read_text().replace("</", "<\\/")
    lib = (root / "mockup/lib/hp-context.js").read_text().replace("</script", "<\\/script")
    html = html.replace("/*__HP_CONTEXT__*/", lib.replace("/*__HP_CONTEXT_DATA__*/null", ctx))
if "/*__HP_BUILDINGS__*/" in html:
    det = (data / "buildings_detail.json").read_text().replace("</", "<\\/")
    lib = (root / "mockup/lib/hp-buildings.js").read_text().replace("</script", "<\\/script")
    html = html.replace("/*__HP_BUILDINGS__*/", lib.replace("/*__HP_BUILDINGS_DATA__*/null", det))
# Generic: /*__HP_LIB:hp-ask__*/ inlines mockup/lib/hp-ask.js (and hp-ui.css via /*__HP_CSS:hp-ui__*/).
import re as _re
for name in sorted(set(_re.findall(r"/\*__HP_LIB:([a-z0-9-]+)__\*/", html))):
    lib = (root / f"mockup/lib/{name}.js").read_text().replace("</script", "<\\/script")
    html = html.replace(f"/*__HP_LIB:{name}__*/", lib)
    if name == "hp-live":   # the SpacetimeDB client is an ES module loaded at runtime from next to the page
        live = root / "backend/live/client/dist/live.mjs"
        if live.exists():
            shutil.copy(live, dst.parent / "live.mjs")
for name in sorted(set(_re.findall(r"/\*__HP_CSS:([a-z0-9-]+)__\*/", html))):
    html = html.replace(f"/*__HP_CSS:{name}__*/", (root / f"mockup/lib/{name}.css").read_text())
dst.write_text(html)
print(f"wrote {dst} ({len(html) / 1e6:.2f} MB)")
