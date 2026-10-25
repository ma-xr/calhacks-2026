"""Narrative layer (Claude). It never computes numbers: every figure it may quote comes from the engine
and is passed in as grounding, and the planner can only propose edits that the engine then evaluates.
Responses are cached under data/cache/anthropic/ by request hash."""
import hashlib
import json
import os

import numpy as np
from fastapi import APIRouter, Body, HTTPException

from .config import CACHE, secret

router = APIRouter(prefix="/narrative")
MODEL = os.environ.get("HP_NARRATIVE_MODEL", "claude-sonnet-5-5")
FAST = os.environ.get("HP_NARRATIVE_FAST_MODEL", "claude-haiku-5-5")
_client = None


def client():
    global _client
    if _client is None:
        import anthropic
        key = secret("ANTHROPIC_API_KEY")
        if not key:
            raise HTTPException(503, "ANTHROPIC_API_KEY missing")
        _client = anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com")
    return _client


def _engine_fingerprint():
    """Changes whenever the model's results change (new data, parameters or code), so cached narration that
    quotes old numbers is never served. Scenario ids hash only the edits, so they alone can't tell."""
    try:
        from .api import S
        m = S.base["metrics"]
        return hashlib.sha1(json.dumps([m.get("people"), m.get("vmt_total"), m.get("revenue"), m.get("delay_hours_total"),
                                        len(S.world.inlets)], default=str).encode()).hexdigest()[:10]
    except Exception:
        return ""


def _cached(kind, payload, fn):
    h = hashlib.sha1(json.dumps([kind, payload, _engine_fingerprint()], sort_keys=True, default=str).encode()).hexdigest()[:16]
    d = CACHE / "anthropic"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{kind}-{h}.json"
    if f.exists():
        return json.loads(f.read_text())
    out = fn()
    f.write_text(json.dumps(out, indent=1))
    return out


def _text(resp):
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()


def _S():
    from .api import S
    if not S.ready:
        raise HTTPException(503, "warming up")
    return S


# ───────────────────────── grounding ─────────────────────────
def grounding(S, sid):
    from . import results as R
    if sid not in S.scen:
        raise HTTPException(404, "unknown scenario")
    j = S.result_json(sid, True)
    w = S.world
    base, plan = S.base, S.scen[sid]
    dcar = plan["edges"]["car_day"] - base["edges"]["car_day"]
    dped = plan["edges"]["ped_day"] - base["edges"]["ped_day"]

    def by_street(d, n=6):
        agg = {}
        for e in np.argsort(-np.abs(d))[:80]:
            nm = w.edge_name[e] or "unnamed street"
            agg[nm] = agg.get(nm, 0) + float(d[e])
        top = sorted(agg.items(), key=lambda kv: -abs(kv[1]))[:n]
        return [{"street": k, "change_per_day": round(v)} for k, v in top]
    drev = plan["pois"]["revenue_day"] - base["pois"]["revenue_day"]
    top_poi = [{"poi": int(i), "name": w.pois[i]["name"], "category": w.pois[i]["category"], "revenue_change_per_day": round(float(drev[i])),
                "visits_base": round(float(base["pois"]["visits_day"][i])), "visits_plan": round(float(plan["pois"]["visits_day"][i]))}
               for i in list(np.argsort(-drev)[:5]) + list(np.argsort(drev)[:5]) if abs(drev[i]) > 1]
    m, d = j["metrics"], j["delta"]
    keep = ("people", "commuters", "vmt_total", "delay_hours_total", "walk_minutes", "visits", "revenue", "encounters", "new_ties",
            "neighbor_ties", "jobs", "residents", "access_15min", "co2_tonnes", "deaths_averted_per_yr", "rent_pressure_index", "by_income")
    return {
        "scenario": {"id": sid, "name": plan.get("name"), "edits": j["edits"],
                     "edited_streets": sorted({w.edge_name[e] for e in j["edits"]["pedestrianized"] if w.edge_name[e]})},
        "metrics_plan": {k: m.get(k) for k in keep}, "delta_vs_baseline": {k: d.get(k) for k in keep if k in d},
        "value_usd_per_yr": {k: j["value"][k] for k in ("mobility", "social", "economy", "environment", "total")},
        "value_lines": j["value"]["lines"],
        "car_traffic_change_by_street": by_street(dcar), "foot_traffic_change_by_street": by_street(dped),
        "biggest_business_changes": top_poi,
        "assumptions_flagged": [a["key"] for a in j["assumptions"] if a["status"] == "assumed"][:25],
        "scale_people_per_agent": S.eng.scale,
    }


SYSTEM = """You are the narrator of The Human Project, an agent-based simulation of San Francisco's Financial District and upper SoMa.
Rules:
- Use ONLY numbers present in the GROUNDING JSON. Never invent or estimate a figure; if something is not in the grounding, say the model does not report it.
- Round sensibly and say "per weekday" or "per year" exactly as the grounding does.
- Be honest about trade-offs and losers, and mention when a result rests on an "assumed" parameter.
- Plain, concrete language for a city planner or a café owner. No hype."""


@router.post("/explain")
def explain(body: dict = Body(...)):
    S = _S()
    sid, q = body.get("scenario", "baseline"), (body.get("question") or "").strip()
    if not q:
        raise HTTPException(400, "question required")
    g = grounding(S, sid)

    def run():
        r = client().messages.create(model=MODEL, max_tokens=700, system=SYSTEM,
                                     messages=[{"role": "user", "content": f"GROUNDING:\n{json.dumps(g)}\n\nQUESTION: {q}\n\nAnswer in under 150 words."}])
        return {"answer": _text(r), "grounding": {"scenario": sid, "keys": list(g.keys())}, "model": MODEL}
    return _cached("explain", [sid, q], run)


@router.post("/diary")
def diary(body: dict = Body(...)):
    S = _S()
    from .api import agent
    sid, aid = body.get("scenario", "baseline"), int(body.get("agent_id", S.hero["agent_id"]))
    a = agent(sid, aid)
    slim = {k: a[k] for k in ("name", "kind", "income_tier", "region", "car_available")}
    slim["baseline_day"] = {"mode": a["baseline"]["mode"], "diary": a["baseline"]["diary"]}
    slim["plan_day"] = {"mode": a["plan"]["mode"], "diary": a["plan"]["diary"]}
    slim["ties"] = a["ties"][:4]

    def run():
        r = client().messages.create(model=FAST, max_tokens=400, system=SYSTEM + "\nWrite in first person as this simulated person. Times in GROUNDING are seconds since midnight; convert to clock times.",
                                     messages=[{"role": "user", "content": f"GROUNDING:\n{json.dumps(slim)}\n\nWrite a 4-6 sentence diary of the plan day, noting what changed versus the usual (baseline) day."}])
        return {"text": _text(r), "agent_id": aid, "model": FAST}
    return _cached("diary", [sid, aid, slim], run)


@router.post("/posts")
def posts(body: dict = Body(...)):
    S = _S()
    sid, n = body.get("scenario", "baseline"), max(1, min(10, int(body.get("n", 6))))
    g = grounding(S, sid)
    st_b, st_p = S.base["_state"], S.scen[sid]["_state"]
    pb, pp = st_b["pop"], st_p["pop"]
    row_b = {int(i): k for k, i in enumerate(pb.id)}
    people = []
    from .population import agent_name, KIND_NAMES
    from .results import MODE_NAMES
    for k in range(pp.n):
        aid = int(pp.id[k]); j = row_b.get(aid)
        mp = "gone" if st_p["gone"][k] else MODE_NAMES[int(st_p["mode"][k])]
        mb = None if j is None else ("gone" if st_b["gone"][j] else MODE_NAMES[int(st_b["mode"][j])])
        if mb != mp and pp.kind[k] in (0, 1):
            people.append({"agent_id": aid, "name": agent_name(aid), "kind": KIND_NAMES[int(pp.kind[k])], "baseline_mode": mb, "plan_mode": mp})
        if len(people) >= n:
            break

    def run():
        r = client().messages.create(model=FAST, max_tokens=900, system=SYSTEM,
                                     messages=[{"role": "user", "content": f"GROUNDING:\n{json.dumps(g)}\n\nPEOPLE WHOSE DAY CHANGED:\n{json.dumps(people)}\n\n"
                                                f"Write {n} short citizen posts (max 200 characters each) reacting to this plan, one per person listed (or plausible residents/workers if fewer are listed), using only facts from the grounding. "
                                                "Return ONLY a JSON array of objects with keys agent_id (or null), name, text, tag (one of: commute, business, social, health, complaint)."}])
        txt = _text(r)
        try:
            arr = json.loads(txt[txt.index("["): txt.rindex("]") + 1])
        except Exception:
            arr = [{"agent_id": None, "name": "Citizen", "text": txt[:200], "tag": "social"}]
        return {"posts": arr[:n], "model": FAST}
    return _cached("posts", [sid, n], run)


# ───────────────────────── AI planner (tool use) ─────────────────────────
def _street_catalog(S):
    w, base = S.world, S.base
    agg = {}
    editable = set(S.eng.base_closed)
    for e in w.editable_edges:
        if e in editable or not w.edge_name[e]:
            continue
        a = agg.setdefault(w.edge_name[e], {"street": w.edge_name[e], "cars_per_day": 0.0, "walkers_per_day": 0.0, "segments": 0})
        a["cars_per_day"] = max(a["cars_per_day"], float(base["edges"]["car_day"][e]))
        a["walkers_per_day"] = max(a["walkers_per_day"], float(base["edges"]["ped_day"][e]))
        a["segments"] += 1
    rows = sorted(agg.values(), key=lambda r: -r["walkers_per_day"])[:45]
    return [{k: (round(v) if isinstance(v, float) else v) for k, v in r.items()} for r in rows]


TOOLS = [
    {"name": "list_inlets", "description": "Car inlets (every road crossing the map edge): key, name, side, road class, cars entering per day today. Use a key for a toll at one inlet.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "list_streets", "description": "Streets that can be made car-free, with today's peak-segment cars/day and walkers/day.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "evaluate_plan", "description": "Run the simulation for a plan and get its deltas vs today and $/yr value. Streets are given by name, optionally limited to the stretch between two cross streets.",
     "input_schema": {"type": "object", "properties": {
         "title": {"type": "string"},
         "car_free": {"type": "array", "items": {"type": "object", "properties": {"street": {"type": "string"}, "from": {"type": "string"}, "to": {"type": "string"}}, "required": ["street"]}},
         "congestion_charge_usd": {"type": "number", "description": "AM-peak charge for cars entering (0 = none)"},
         "congestion_charge_inlet": {"type": "string", "description": "car inlet key from list_inlets, or empty for all"}},
         "required": ["title", "car_free"]}},
]


def _plan_edits(S, args):
    w = S.world
    ped = []
    for s in args.get("car_free", []):
        name = s.get("street", "")
        if s.get("from") and s.get("to"):
            seg = w.stretch(name, s["from"], s["to"])
        else:
            seg = [e for e in w.edges_named(name) if w.edge_car[e] and not w.edge_hw[e]]
        ped += seg
    pols = []
    if args.get("congestion_charge_usd"):
        pols.append({"kind": "congestion_charge", "target": args.get("congestion_charge_inlet") or "", "amount": float(args["congestion_charge_usd"])})
    return {"pedestrianized": sorted(set(ped)), "blocks": {}, "policies": pols}


@router.post("/planner")
def planner(body: dict = Body(...)):
    S = _S()
    goal = (body.get("goal") or "").strip()
    if not goal:
        raise HTTPException(400, "goal required")

    def run():
        msgs = [{"role": "user", "content": f"GOAL: {goal}\n\nPropose up to 3 distinct plans. Evaluate EACH with evaluate_plan before recommending it. "
                                            "Then reply with ONLY a JSON array: [{\"title\", \"result_id\", \"rationale\" (2 sentences citing evaluated numbers and trade-offs)}]."}]
        evaluated = {}
        for _ in range(8):
            r = client().messages.create(model=MODEL, max_tokens=1500, tools=TOOLS, messages=msgs,
                                         system=SYSTEM + "\nYou are the city's planning assistant. You can only propose car-free streets and congestion charges. Prefer specific stretches between cross streets.")
            msgs.append({"role": "assistant", "content": r.content})
            if r.stop_reason != "tool_use":
                break
            results = []
            for b in r.content:
                if getattr(b, "type", "") != "tool_use":
                    continue
                if b.name == "list_streets":
                    out = _street_catalog(S)
                elif b.name == "list_inlets":
                    out = [{"key": g["key"], "name": g["name"], "side": g["side"], "class": g["cls"],
                            "cars_entering_per_day": round(S.base["inlets"][g["i"]]["entered"])}
                           for g in (S.world.inlets[i] for i in S.world.car_inlets)]
                    out.sort(key=lambda r: -r["cars_entering_per_day"])
                else:
                    edits = _plan_edits(S, b.input)
                    if not edits["pedestrianized"] and not edits["policies"]:
                        out = {"error": "no valid streets found; check names with list_streets and cross-street spelling"}
                    else:
                        sid = S.run(edits, b.input.get("title"))
                        j = S.result_json(sid, True)
                        d = j["delta"]
                        out = {"result_id": sid, "value_total_usd_per_yr": j["value"]["total"],
                               "value_by_pillar": {k: j["value"][k] for k in ("mobility", "social", "economy", "environment")},
                               "delta": {k: d.get(k) for k in ("commuters", "delay_hours_total", "revenue", "new_ties", "co2_tonnes", "rent_pressure_index")},
                               "edges_closed": len(edits["pedestrianized"])}
                        evaluated[sid] = {"title": b.input.get("title"), "edits": edits, "value_total": j["value"]["total"], "deltas": out["delta"]}
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out)})
            msgs.append({"role": "user", "content": results})
        txt = _text(r)
        try:
            picks = json.loads(txt[txt.index("["): txt.rindex("]") + 1])
        except Exception:
            picks = [{"title": v["title"], "result_id": k, "rationale": ""} for k, v in evaluated.items()]
        options = []
        for p in picks[:3]:
            ev = evaluated.get(p.get("result_id"))
            if ev:
                options.append({"title": p.get("title") or ev["title"], "edits": ev["edits"], "rationale": p.get("rationale", ""),
                                "result_id": p["result_id"], "value_total": ev["value_total"], "deltas": ev["deltas"]})
        return {"goal": goal, "options": options, "evaluated": len(evaluated), "model": MODEL}
    return _cached("planner", [goal], run)
