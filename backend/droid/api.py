"""HTTP routes for the Droid panel (mounted into hp.api)."""
from fastapi import APIRouter, Body, HTTPException

from hp import policies as PL

from .service import store

router = APIRouter(prefix="/policies", tags=["droid"])
BUILTINS = [
    {"kind": "congestion_charge", "title": "Congestion charge", "builtin": True,
     "description": "AM-peak (7–10) $ charge for cars entering; target = inlet key or empty for all",
     "params": {"amount": {"default": 5, "min": 0, "max": 50, "unit": "USD"}, "target": {"default": ""}}},
    {"kind": "parking_price", "title": "Parking price change", "builtin": True,
     "description": "$ per day added to downtown parking", "params": {"amount": {"default": 5, "min": -30, "max": 50, "unit": "USD/day"}}},
]
SUMMARY = ("id", "request", "status", "kind", "created_at", "updated_at", "error", "example_edit", "metrics")


def _view(p, full=True):
    if not full:
        return {k: p.get(k) for k in SUMMARY} | {"title": (p.get("plan") or {}).get("title"),
                                                   "gate_passed": any(g["passed"] for g in p["gates"])}
    return p


@router.post("/propose")
def propose(body: dict = Body(...)):
    req = (body.get("request") or "").strip()
    if not 3 <= len(req) <= 500:
        raise HTTPException(400, "request must be 3–500 characters")
    return store().propose(req)


@router.get("")
def list_policies(full: bool = True):
    """Policy Book (built-ins + approved plugins) and every Droid proposal with plan, steps, diff and test output."""
    s = store()
    return {"policies": BUILTINS + [{**c, "builtin": False} for c in PL.catalog()],
            "load_errors": PL.LOAD_ERRORS,
            "proposals": [_view(p, full) for p in s.list()]}


@router.get("/{pid}")
def get_proposal(pid: str):
    p = store().get(pid)
    if not p:
        raise HTTPException(404, "unknown proposal")
    return p


def _decide(pid, fn):
    s = store()
    if not s.get(pid):
        raise HTTPException(404, "unknown proposal")
    try:
        return fn(pid)
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.post("/{pid}/approve")
def approve(pid: str):
    p = _decide(pid, store().approve)
    return {"proposal": p, "policy": next(c for c in PL.catalog() if c["kind"] == p["kind"]),
            "try_it": {"POST /scenario": {"name": (p.get("plan") or {}).get("title"), "edits": p["example_edit"]}}}


@router.post("/{pid}/reject")
def reject(pid: str):
    return _decide(pid, store().reject)


# ── Droid live agent (read-only Q&A over the current scenario) ──
live_router = APIRouter(prefix="/droid", tags=["droid"])


@live_router.post("/ask")
def droid_ask(body: dict = Body(...), stream: bool = False):
    import json
    import queue
    import threading

    from fastapi.responses import JSONResponse, StreamingResponse
    from hp.api import S, _need_ready

    from . import live
    _need_ready()
    sid = body.get("scenario") or "baseline"
    if sid not in S.scen:
        raise HTTPException(404, "unknown scenario (it may have been evicted; POST /scenario again)")
    q = (body.get("question") or "").strip()
    if not 2 <= len(q) <= 600:
        raise HTTPException(400, "question must be 2–600 characters")
    body = {**body, "scenario": sid, "question": q}
    if not stream:
        ans = None
        for ev, data in live.ask(S, body):
            if ev == "answer":
                ans = data
        return JSONResponse(ans)
    qq = queue.Queue()

    def work():
        try:
            for ev, data in live.ask(S, body):
                qq.put((ev, data))
        except Exception as e:
            qq.put(("error", {"error": repr(e)}))
        qq.put(None)
    threading.Thread(target=work, daemon=True).start()

    def gen():
        while (item := qq.get()) is not None:
            yield f"event: {item[0]}\ndata: {json.dumps(item[1])}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@live_router.delete("/conversations/{conv}")
def droid_close(conv: str):
    from . import live
    live.close(conv)
    return {"closed": conv}
