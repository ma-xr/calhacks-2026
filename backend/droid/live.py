"""Droid live agent: ask anything about the current scenario. Droid answers from `simq` output only and points the map.

POST /droid/ask -> export the scenario snapshot (live_export) -> send the question to the warm Droid session for this
conversation (live.mjs daemon, one Node process) -> stream its simq steps -> parse its answer JSON -> drop references
that don't exist -> compute focus/highlights from their geometry. If Droid fails or times out, the Claude
/narrative/explain text is returned with no references."""
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

import numpy as np

from hp.config import secret

from . import live_export
from .simq import __doc__ as SIMQ_DOC

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
NODE = shutil.which("node") or "node"
MODEL = os.environ.get("DROID_LIVE_MODEL", "claude-sonnet-5-5")
EFFORT = os.environ.get("DROID_LIVE_EFFORT", "low")
TIMEOUT_S = int(os.environ.get("DROID_LIVE_TIMEOUT_S", "40"))
REF_TYPES = ("street", "edge", "building", "block", "poi", "agent", "inlet")
INFO_VIEWS = ("traffic", "foot", "workplaces", "residents", "visits", "zoning", "connections", "revenue")
SIMQ = f"{sys.executable} -m droid.simq"

SYSTEM = f"""
You are Droid, the live analyst inside "CommonGround", an agent-based simulation of one weekday in San Francisco's
Financial District and SoMa (commuters, residents, visitors, through-traffic; car/transit/walk/bike; businesses).
You answer questions about the scenario on screen and point the map at the places you mention.

TOOLS: the ONLY thing you can run is the simq query CLI, from the backend directory:
  {SIMQ} --scenario <scenario id> <command> [args]
You may run several simq calls: one Execute per call inside one Script with Promise.allSettled (fastest), or one
command joined with `;` / `&&` (optionally `cd <backend>` and `P=<venv python>` first). Plain arguments only: no pipes,
redirects, $(...) or other programs. A command that breaks these rules is cancelled ("Tool execution cancelled"): then
retry with plain single simq commands, never stop after a cancellation. Do not run anything else (no ls/cat/python -c),
do not read or write files. 1-4 simq calls is usually enough.

{SIMQ_DOC}

RULES
- Use ONLY numbers that appear in simq output. Never invent, estimate or extrapolate a figure. Round sensibly.
- Cite EVERY place, business, person or gateway you mention as a reference, with the ids simq printed.
- If a figure rests on a parameter whose status is "assumed" (see `assumptions`), say so briefly.
- If the model doesn't cover something (e.g. parking garages, transit crowding, weekends), say so instead of guessing.
- The baseline is 2026 reality (Market St car-free from 10th to Main since 2020). A plan's deltas are vs that baseline.
- Times: hours are 0-23 local; time_s is seconds since midnight.
- On the BASELINE every *_delta is 0 by definition. A question about a change ("why did X go up", "who loses") has no
  answer there: say so in one sentence, name the hero plan id from the prompt as the scenario to compare, still cite
  the place the user asked about (e.g. the street), and give its current level instead. Never cite unrelated places.
- Even when data is missing or a command fails, ALWAYS end with the JSON block.

ANSWER FORMAT: your final message must contain exactly one ```json block with:
{{"answer": "<markdown, at most 120 words, plain language for a planner or a cafe owner>",
  "references": [{{"type": "street|edge|building|block|poi|agent|inlet", "ids": [int], "label": "short name",
                  "why": "why it matters to the answer", "value": "optional key number from simq, with unit"}}],
  "focus": {{"x": m, "z": m, "radius_m": m}} or null,
  "highlights": {{"edges": [], "buildings": [], "pois": [], "agents": []}},
  "info_view": "traffic|foot|workplaces|residents|visits|zoning|connections|revenue" (the map layer that best shows it),
  "time_s": seconds since midnight to jump the clock to (optional),
  "grounding": ["the simq commands you used"]}}
For type "street" use the edge ids simq listed for it (a stretch's edges when you talk about a stretch). ids for inlet = its "i".
Order references by importance; the first one is where the camera goes if you omit focus.
"""


class Daemon:
    """One live.mjs process for all conversations; events are routed to the asking request by rid."""

    def __init__(self):
        self.proc = None
        self.lock = threading.Lock()
        self.queues = {}

    def _start(self):
        key = secret("FACTORY_API_KEY")
        if not key:
            raise RuntimeError("FACTORY_API_KEY missing from .env")
        cfg = {"backend": str(BACKEND), "python": sys.executable, "model": MODEL, "effort": EFFORT, "system": SYSTEM}
        env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""), "FACTORY_API_KEY": key}
        self.proc = subprocess.Popen([NODE, str(HERE / "live.mjs"), json.dumps(cfg)], cwd=str(HERE), env=env, text=True,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=1)
        ready = self.proc.stdout.readline()
        if '"ready"' not in ready:
            raise RuntimeError("live daemon failed to start: " + ready[:200].replace(key, "***"))
        threading.Thread(target=self._read, args=(self.proc,), daemon=True).start()

    def _read(self, proc):
        for line in proc.stdout:
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = self.queues.get(ev.get("rid"))
            if q:
                q.put(ev)
        for q in list(self.queues.values()):  # daemon died: unblock everyone
            q.put({"ev": "error", "message": "live daemon exited"})

    def send(self, msg):
        with self.lock:
            if self.proc is None or self.proc.poll() is not None:
                self._start()
            self.proc.stdin.write(json.dumps(msg) + "\n")
            self.proc.stdin.flush()

    def ask(self, conv, prompt, timeout_s):
        rid = uuid.uuid4().hex[:10]
        q = self.queues[rid] = queue.Queue()
        try:
            self.send({"op": "ask", "rid": rid, "conv": conv, "prompt": prompt, "timeout_s": timeout_s})
            deadline = time.time() + timeout_s + 15
            while True:
                try:
                    ev = q.get(timeout=max(0.1, deadline - time.time()))
                except queue.Empty:
                    yield {"ev": "error", "message": "timed out"}
                    return
                yield ev
                if ev["ev"] in ("done", "error"):
                    return
        finally:
            self.queues.pop(rid, None)


DAEMON = Daemon()
_conv_locks = {}
_conv_meta = {}


# ── geometry + validation ──
def _geo(S, sid):
    w, res = S.world, S.scen[sid]
    pop_ids = set(int(i) for i in res["_state"]["pop"].id) | set(int(i) for i in S.base["_state"]["pop"].id)
    virt = {v["id"]: v for v in res.get("virtual_pois", [])}
    return w, pop_ids, virt


def _agent_xy(S, sid, aid):
    for res in (S.scen[sid], S.base):
        pop = res["_state"]["pop"]
        k = np.where(pop.id == aid)[0]
        if len(k) and pop.bld[k[0]] >= 0:
            return S.world.bld_c[pop.bld[k[0]]]
    return None


def clean_answer(S, sid, raw, steps):
    """Validate Droid's answer JSON against the world/scenario; fill focus, highlights and grounding."""
    w, pop_ids, virt = _geo(S, sid)
    refs, groups, hl = [], [], {"edges": set(), "buildings": set(), "pois": set(), "agents": set()}
    names = {}
    for r in raw.get("references") or []:
        t = r.get("type")
        if t not in REF_TYPES:
            continue
        ids = []
        for i in r.get("ids") or []:
            try:
                ids.append(int(i))
            except (TypeError, ValueError):
                pass
        if t == "street" and not ids and r.get("label"):
            if not names:
                for e, n in enumerate(w.edge_name):
                    names.setdefault(n.lower(), []).append(e)
            ids = names.get(str(r["label"]).lower(), [])
        valid = {"street": lambda i: 0 <= i < w.E, "edge": lambda i: 0 <= i < w.E, "building": lambda i: 0 <= i < w.B,
                 "block": lambda i: 0 <= i < w.n_blocks, "poi": lambda i: 0 <= i < w.P or i in virt,
                 "agent": lambda i: i in pop_ids, "inlet": lambda i: 0 <= i < len(w.inlets)}[t]
        ids = [i for i in dict.fromkeys(ids) if valid(i)]
        if not ids:
            continue
        refs.append({"type": t, "ids": ids, "label": str(r.get("label") or "")[:80], "why": str(r.get("why") or "")[:200],
                     **({"value": str(r["value"])[:60]} if r.get("value") not in (None, "") else {})})
        pts = []
        groups.append(pts)
        for i in ids:
            if t in ("street", "edge"):
                hl["edges"].add(i)
                pts += [tuple(p) for p in w.edge_pts[i]]
            elif t == "building":
                hl["buildings"].add(i); pts.append(tuple(w.bld_c[i]))
            elif t == "block":
                bl = np.where(w.block_of == i)[0]
                hl["buildings"].update(int(b) for b in bl[:60]); pts += [tuple(w.bld_c[b]) for b in bl]
            elif t == "poi":
                if i < w.P:
                    hl["pois"].add(i); pts.append(tuple(w.poi_xy[i]))
                else:
                    pts.append((virt[i]["x"], virt[i]["z"]))
            elif t == "agent":
                hl["agents"].add(i)
                xy = _agent_xy(S, sid, i)
                if xy is not None:
                    pts.append(tuple(xy))
            elif t == "inlet":
                g = w.inlets[i]; pts.append((g["x"], g["z"]))
    # Droid's own highlights, validated the same way
    h = raw.get("highlights") or {}
    for k, ok in (("edges", lambda i: 0 <= i < w.E), ("buildings", lambda i: 0 <= i < w.B), ("pois", lambda i: 0 <= i < w.P),
                  ("agents", lambda i: i in pop_ids)):
        for i in h.get(k) or []:
            if isinstance(i, (int, float)) and ok(int(i)):
                hl[k].add(int(i))
    # Focus from geometry: the first reference leads; later ones join the frame when within 700 m of it.
    focus = None
    groups = [g for g in groups if g]
    if groups:
        lead = np.array(groups[0], float)
        c0 = (lead.min(0) + lead.max(0)) / 2
        P = [lead] + [np.array(g, float) for g in groups[1:] if np.linalg.norm(np.mean(g, 0) - c0) < 700]
        P = np.concatenate(P)
        lo, hi = P.min(0), P.max(0)
        c = (lo + hi) / 2
        focus = {"x": round(float(c[0]), 1), "z": round(float(c[1]), 1),
                 "radius_m": round(float(np.clip(np.linalg.norm(hi - lo) / 2 * 1.15, 120, 1000)), 0)}
    else:  # no usable references: accept Droid's own focus if it is on the map
        f = raw.get("focus")
        bb = w.raw.get("bbox", {"x0": -1000, "x1": 1000, "z0": -1000, "z1": 1000})
        if (isinstance(f, dict) and all(isinstance(f.get(k), (int, float)) for k in ("x", "z", "radius_m"))
                and bb["x0"] - 300 <= f["x"] <= bb["x1"] + 300 and bb["z0"] - 300 <= f["z"] <= bb["z1"] + 300):
            focus = {"x": float(f["x"]), "z": float(f["z"]), "radius_m": float(np.clip(f["radius_m"], 80, 1500))}
    out = {"answer": str(raw.get("answer") or "").strip(), "references": refs, "focus": focus,
           "highlights": {k: sorted(v) for k, v in hl.items()},
           "grounding": [str(g) for g in (raw.get("grounding") or [])][:12] or [s["simq"] for s in steps]}
    if raw.get("info_view") in INFO_VIEWS:
        out["info_view"] = raw["info_view"]
    if isinstance(raw.get("time_s"), (int, float)) and 0 <= raw["time_s"] < 86400:
        out["time_s"] = float(raw["time_s"])
    return out


def parse_json_block(text):
    for m in reversed(list(re.finditer(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text or ""))):
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
    i, j = (text or "").find("{"), (text or "").rfind("}")
    if 0 <= i < j:
        try:
            return json.loads(text[i:j + 1])
        except json.JSONDecodeError:
            pass
    return None


def _prompt(S, sid, body, first):
    view = body.get("view") or {}
    lines = [f"SCENARIO: {sid}" + (" (baseline, 2026 reality)" if sid == "baseline" else f" ({S.scen[sid].get('name') or 'plan'}, compared with the baseline)")]
    if first and S.hero:
        lines.append(f"Hero pair: Maria O. = agent {S.hero['agent_id']}, Dev P. = agent {S.hero['friend_id']}; hero plan = {S.hero['plan_id']} (2nd St car-free).")
    if isinstance(view.get("time_s"), (int, float)):
        t = int(view["time_s"])
        lines.append(f"Viewer's clock: {t // 3600:02d}:{t % 3600 // 60:02d} (time_s={t}).")
    sel = view.get("selected") or {}
    if sel.get("type") and sel.get("id") is not None:
        lines.append(f"Viewer has selected {sel['type']} {sel['id']}.")
    lines.append(f"QUESTION: {body['question']}")
    return "\n".join(lines)


def _fold(ev, steps, denied):
    """Daemon event -> SSE step events (running, then done / error / denied)."""
    k = ev["ev"]
    if k == "step":
        steps[ev["id"]] = {"id": ev["id"], "label": ev["label"], "command": ev["command"], "simq": ev["simq"], "status": "running"}
        yield "step", steps[ev["id"]]
    elif k == "step_result" and ev["id"] in steps:
        s = steps[ev["id"]]
        s.update(status="error" if ev["is_error"] else "done", output=ev["output"])
        yield "step", s
    elif k == "permission" and not ev["allowed"]:
        denied.append(ev["target"])
        yield "step", {"id": f"denied-{len(denied)}", "label": "Blocked: only plain simq commands are allowed; Droid will retry",
                       "command": ev["target"], "status": "denied"}


def ask(S, body):
    """Generator of (event, data): ('step', {...}) for each simq call, then ('answer', {...})."""
    from hp.narrative import explain
    sid = body.get("scenario") or "baseline"
    q = (body.get("question") or "").strip()
    conv = body.get("conversation_id") or uuid.uuid4().hex[:12]
    t0 = time.time()
    lock = _conv_locks.setdefault(conv, threading.Lock())
    with lock:
        live_export.export(S, sid)
        first = conv not in _conv_meta
        _conv_meta[conv] = {"last": time.time(), "scenario": sid}
        steps, denied, text, err, ms = {}, [], "", None, None
        prompt = _prompt(S, sid, {**body, "question": q}, first)
        for attempt in range(2):
            for ev in DAEMON.ask(conv, prompt, max(10, TIMEOUT_S - int(time.time() - t0))):
                yield from _fold(ev, steps, denied)
                if ev["ev"] == "done":
                    text, ms, err = ev["text"], ev.get("ms"), None
                elif ev["ev"] == "error":
                    err, text = ev["message"], ev.get("text") or ""
            raw = parse_json_block(text)
            if (raw and raw.get("answer")) or attempt or time.time() - t0 > TIMEOUT_S - 12 or (err and "timed out" in err):
                break
            # One repair turn in the same warm session: a blocked command or no answer JSON.
            why = f"Your command was blocked: {denied[-1]!r}. " if denied else "Your reply had no answer JSON block. "
            prompt = (why + "Retry now with plain single simq commands (one simq call per Execute, no pipes, no other "
                      "programs), then end with exactly one ```json block in the answer format. Same question: " + q)
        if raw and raw.get("answer"):
            out = clean_answer(S, sid, raw, list(steps.values()))
            out["source"] = "droid"
        else:
            try:
                ex = explain({"scenario": sid, "question": q})
                ans = ex["answer"]
            except Exception as e:  # narrative layer unavailable too
                ans = f"Sorry, I couldn't answer that right now ({type(e).__name__})."
            out = {"answer": ans, "references": [], "focus": None, "highlights": {"edges": [], "buildings": [], "pois": [], "agents": []},
                   "grounding": [s["simq"] for s in steps.values()], "source": "narrative_fallback",
                   "fallback_reason": err or "Droid returned no answer JSON"}
        out.update(conversation_id=conv, scenario=sid, latency_s=round(time.time() - t0, 1), droid_ms=ms)
        yield "answer", out


def close(conv):
    _conv_meta.pop(conv, None)
    try:
        DAEMON.send({"op": "close", "conv": conv})
    except Exception:
        pass
