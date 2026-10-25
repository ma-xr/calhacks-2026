"""Build every data file for one city environment from its cached OSM downloads.

Usage:
  python3 scripts/fetch_city.py chicago      # once: downloads (cached in data/raw/chicago/)
  python3 scripts/build_city.py chicago      # writes data/processed/chicago/{world,context,buildings_detail,city}.json
  python3 scripts/build_city.py sf           # SF: writes only city.json (world/context/parts are built by the
                                             # original commands, which the engine depends on); --all rebuilds them too
"""
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import build_world as BW  # noqa: E402
import build_context as BC  # noqa: E402
import build_parts as BP  # noqa: E402
from cities import CITIES, paths  # noqa: E402


def city_json(city, out):
    c = CITIES[city]
    w = json.load(open(out / "world.json"))
    x0, z1 = BW.xz(c["bbox"][0], c["bbox"][1])
    x1, z0 = BW.xz(c["bbox"][2], c["bbox"][3])
    by_name = {}
    for i, b in enumerate(w["buildings"]):
        if b.get("n") and (b["n"] not in by_name or b["h"] > w["buildings"][by_name[b["n"]]]["h"]):
            by_name[b["n"]] = i
    wanted = c.get("landmarks") or []

    def find(n):   # exact name, else the tallest building whose name contains it (OSM names vary: "Chicago Union Station")
        if n in by_name:
            return by_name[n]
        hits = [i for nm, i in by_name.items() if n.lower() in nm.lower()]
        return max(hits, key=lambda i: w["buildings"][i]["h"]) if hits else None
    found = [(n, find(n)) for n in wanted]
    detail = json.load(open(out / "buildings_detail.json")).get("parts", {}) if (out / "buildings_detail.json").exists() else {}
    top = lambda i: max([w["buildings"][i]["h"]] + [p["h"] for p in detail.get(str(i), [])])  # noqa: E731  (Willis: podium 10 m, parts 527 m)
    landmarks = [{"name": w["buildings"][i]["n"], "id": i, "x": w["buildings"][i]["c"][0], "z": w["buildings"][i]["c"][1],
                  "h": top(i)} for n, i in found if i is not None]
    by_name = {**by_name, **{n: i for n, i in found if i is not None}}
    if len(landmarks) < 4:   # fall back to the tallest named buildings
        tall = sorted((b for b in w["buildings"] if b.get("n")), key=lambda b: -b["h"])[:6]
        landmarks += [{"name": b["n"], "id": w["buildings"].index(b), "x": b["c"][0], "z": b["c"][1], "h": b["h"]}
                      for b in tall if b["n"] not in {l["name"] for l in landmarks}]
    stations = sorted(w["stations"], key=lambda s: -len(s["e"]))
    info = {"id": city, "name": c["name"], "area": c["area"], "center": list(c["center"]),
            "box": {"x0": x0, "x1": x1, "z0": z0, "z1": z1},
            "districts": [{"label": d[0], "x": d[1], "z": d[2]} for d in c.get("districts", [])],
            "landmarks": landmarks, "stations": [{"name": s["name"], "x": s["c"][0], "z": s["c"][1], "entrances": len(s["e"])} for s in stations],
            "engine": city == "sf"}
    json.dump(info, open(out / "city.json", "w"), indent=1)
    missing = [n for n in wanted if n not in by_name]
    print(f"city.json: {len(landmarks)} landmarks, {len(stations)} stations" + (f" (not found: {', '.join(missing)})" if missing else ""))


def main(city, all_=False):
    BW.configure(city)
    p = paths(city)
    out = p["out"]
    out.mkdir(parents=True, exist_ok=True)
    if city != "sf" or all_:
        BW.main(str(p["core"]), str(out / "world.json"))
        BC.main(str(p["context"]), str(out / "context.json"))
        BP.main(str(p["parts"]), str(out / "buildings_detail.json"), str(out / "world.json"))
    city_json(city, out)


if __name__ == "__main__":
    main(sys.argv[1], "--all" in sys.argv)
