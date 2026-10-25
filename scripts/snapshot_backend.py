"""Freeze real backend results into mockup/backend-snapshot/ for offline and published pages.

The snapshot holds what the scripted demo needs: the world, the baseline, the hero plan
(2nd St car-free), Maria's agent view, and one planner / posts / explain response.
Narrative calls hit the Claude API, so each runs once and is reused (pass --no-narrative to skip).

Results keep a 15k-trip sample (~37% at 20k is 5 MB raw) so a published artifact stays light; live mode gets every trip.

Usage: python3 scripts/snapshot_backend.py [--api http://localhost:8787] [--max-trips 15000] [--no-narrative]
"""
import argparse
import json
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parent.parent
out = root / "mockup/backend-snapshot"


def call(api, path, body=None, timeout=120):
    req = urllib.request.Request(api + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"content-type": "application/json"}, method="GET" if body is None else "POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def save(name, obj):
    (out / name).write_text(json.dumps(obj, separators=(",", ":")))
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8787")
    ap.add_argument("--no-narrative", action="store_true")
    ap.add_argument("--max-trips", type=int, default=15000)
    a = ap.parse_args()
    out.mkdir(parents=True, exist_ok=True)
    prev = json.loads((out / "index.json").read_text()) if (out / "index.json").exists() else {}

    world = call(a.api, "/world")
    hero = world["hero"]
    idx = {"version": call(a.api, "/health").get("version"), "world": save("world.json", world),
           "results": {}, "edits": {}, "agents": {}, "narrative": prev.get("narrative", {})}
    mt = f"max_trips={a.max_trips}"
    idx["results"]["baseline"] = save("baseline.json", call(a.api, f"/baseline?{mt}"))
    plan = call(a.api, f"/scenario?{mt}", {"name": "2nd St car-free", "edits": {"pedestrianized": hero["street_edges"]}})
    idx["results"][plan["id"]] = save(f"plan-{plan['id']}.json", plan)
    idx["edits"][plan["id"]] = plan["edits"]
    for sid in ("baseline", plan["id"]):
        idx["agents"][f"{sid}:{hero['agent_id']}"] = save(f"agent-{sid}-{hero['agent_id']}.json",
                                                          call(a.api, f"/scenario/{sid}/agent/{hero['agent_id']}"))

    if not a.no_narrative:
        n = idx["narrative"]
        if "planner" not in n:
            n["planner"] = call(a.api, "/narrative/planner",
                                {"goal": "Boost small business in SoMa without slowing Bay Bridge traffic"}, timeout=180)
        for opt in (n.get("planner") or {}).get("options", []):
            rid = opt.get("result_id")
            if rid and rid not in idx["results"]:
                # Results live in the API's memory cache; after a restart, re-run the option's edits.
                r = call(a.api, f"/scenario?{mt}", {"name": opt.get("title", ""), "edits": opt["edits"]})
                if r["id"] != rid:
                    opt["result_id"] = rid = r["id"]
                idx["results"][rid] = save(f"plan-{rid}.json", r)
                idx["edits"][rid] = r["edits"]
        # The demo applies each option ON TOP of 2nd St, so freeze those combined plans too.
        for opt in (n.get("planner") or {}).get("options", []):
            e = opt["edits"]
            combo = {"pedestrianized": sorted(set(hero["street_edges"]) | set(e.get("pedestrianized", []))),
                     "blocks": e.get("blocks", {}), "policies": e.get("policies", []), "reopened": e.get("reopened", [])}
            r = call(a.api, f"/scenario?{mt}", {"name": "2nd St + " + opt.get("title", ""), "edits": combo})
            opt["combined_result_id"] = r["id"]
            idx["results"][r["id"]] = save(f"plan-{r['id']}.json", r)
            idx["edits"][r["id"]] = r["edits"]
        n.setdefault("posts", {})
        if plan["id"] not in n["posts"]:
            n["posts"][plan["id"]] = call(a.api, "/narrative/posts", {"scenario": plan["id"], "n": 8})
        n.setdefault("explain", {})
        if plan["id"] not in n["explain"]:
            n["explain"][plan["id"]] = call(a.api, "/narrative/explain",
                                            {"scenario": plan["id"], "question": "Why did revenue on 2nd St go up?"})

    (out / "index.json").write_text(json.dumps(idx, indent=1))
    size = sum(p.stat().st_size for p in out.glob("*.json"))
    print(f"snapshot: {len(idx['results'])} results, {size / 1e6:.1f} MB in {out}")


if __name__ == "__main__":
    main()
