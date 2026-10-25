"""Snapshot export for the Droid live agent: everything simq needs, written as JSON under droid/workspace/
so Droid's sandbox needs no network and no access to the engine.

workspace/_world.json        edges (name, class, nodes, midpoint, bbox), buildings, POIs, inlets, blocks, hero
workspace/<sid>/scenario.json  S.result_json(sid, lite=False) minus the trip sample
workspace/<sid>/agents.json    changed agents (summary) + full baseline/plan views for the hero pair and a sample"""
import json
import os
import shutil
import threading
import time
from pathlib import Path

import numpy as np

WORKSPACE = Path(__file__).resolve().parent / "workspace"
MAX_VIEWS = 120
_lock = threading.Lock()
_OWNER = f"{os.getpid()}-{time.time():.0f}"  # snapshots from an earlier server process are stale


def _dump(path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, separators=(",", ":"), default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
    tmp.replace(path)


def _world(S):
    w, eng = S.world, S.eng
    raw = w.raw
    edges = []
    for i in range(w.E):
        pts = np.array(w.edge_pts[i], float)
        edges.append({"id": i, "name": w.edge_name[i], "cls": w.edge_cls[i], "a": int(w.edge_a[i]), "b": int(w.edge_b[i]),
                      "len": round(float(w.edge_len[i]), 1), "car": bool(w.edge_car[i]), "x": round(float(w.edge_mid[i][0]), 1),
                      "z": round(float(w.edge_mid[i][1]), 1),
                      "bbox": [round(float(v), 1) for v in (*pts.min(0), *pts.max(0))]})
    blds = [{"id": i, "name": b.get("n") or "", "kind": w.bld_kind[i], "x": round(float(w.bld_c[i][0]), 1),
             "z": round(float(w.bld_c[i][1]), 1), "block": int(w.block_of[i])} for i, b in enumerate(raw["buildings"])]
    pois = []
    for p in w.pois:
        g = eng.poi_google.get(p["id"], {})
        pois.append({"id": p["id"], "name": p["name"], "cat": p["category"], "x": round(p["x"], 1), "z": round(p["z"], 1),
                     "building": int(eng.poi_bld[p["id"]]), "rating": g.get("rating"), "reviews": g.get("reviews")})
    blocks = {}
    for b in blds:
        blocks.setdefault(b["block"], []).append((b["x"], b["z"]))
    blocks = [{"id": k, "x": round(float(np.mean([p[0] for p in v])), 1), "z": round(float(np.mean([p[1] for p in v])), 1),
               "bbox": [min(p[0] for p in v), min(p[1] for p in v), max(p[0] for p in v), max(p[1] for p in v)], "buildings": len(v)}
              for k, v in sorted(blocks.items())]
    inlets = [{k: g[k] for k in ("i", "key", "name", "mode", "x", "z")} for g in w.inlets]
    from hp.config import VALIDATION_DIR
    try:
        validation = json.loads((VALIDATION_DIR / "validation.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        validation = []
    return {"edges": edges, "buildings": blds, "pois": pois, "blocks": blocks, "inlets": inlets, "hero": S.hero, "validation": validation,
            "base_car_free_edges": [int(e) for e in eng.base_closed], "scale_people_per_agent": eng.scale}


def _agents(S, sid):
    from hp import api
    from hp.population import KIND_NAMES, REGIONS, THROUGH, agent_name
    from hp.results import MODE_NAMES
    sb, sp = S.base["_state"], S.scen[sid]["_state"]
    pb, pp = sb["pop"], sp["pop"]
    rb = {int(i): k for k, i in enumerate(pb.id)}

    def mode(st, k):
        return None if k is None else ("stayed home / skipped trip" if st["gone"][k] else MODE_NAMES[int(st["mode"][k])])
    changed = []
    for k in range(pp.n):
        if pp.kind[k] == THROUGH:
            continue
        aid = int(pp.id[k]); j = rb.get(aid)
        mb, mp = mode(sb, j), mode(sp, k)
        if mb != mp:
            changed.append({"id": aid, "name": agent_name(aid), "kind": KIND_NAMES[int(pp.kind[k])], "region": REGIONS[int(pp.region[k])]["name"],
                            "income_tier": ["low", "mid", "high"][int(pp.tier[k])], "building": int(pp.bld[k]),
                            "baseline_mode": mb, "plan_mode": mp})
    hero = [S.hero["agent_id"], S.hero["friend_id"]] if S.hero else []
    sample = [a["agent_id"] for a in S.result_json(sid, True)["agents_sample"]]
    ids = list(dict.fromkeys(hero + sample + [c["id"] for c in changed]))[:MAX_VIEWS]
    views = {}
    for aid in ids:
        try:
            views[str(aid)] = api.agent(sid, aid)
        except Exception:
            pass
    return {"changed": changed, "views": views, "hero": hero}


def export(S, sid):
    """Write the snapshot for `sid` (idempotent per scenario id). Returns the scenario directory."""
    with _lock:
        owner = WORKSPACE / "_owner"
        if not owner.exists() or owner.read_text() != _OWNER:
            reset()
            WORKSPACE.mkdir()
            owner.write_text(_OWNER)
        wf = WORKSPACE / "_world.json"
        if not wf.exists():
            _dump(wf, _world(S))
        d = WORKSPACE / sid
        if (d / "agents.json").exists():
            return d
        d.mkdir(exist_ok=True)
        for s in {sid, "baseline"}:
            sd = WORKSPACE / s
            sd.mkdir(exist_ok=True)
            if not (sd / "scenario.json").exists():
                j = dict(S.result_json(s, False))
                j.pop("trips", None)
                _dump(sd / "scenario.json", j)
        _dump(d / "agents.json", _agents(S, sid))
        return d


def reset():
    """Drop all snapshots."""
    if WORKSPACE.exists():
        shutil.rmtree(WORKSPACE)
