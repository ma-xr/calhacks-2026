"""Proposal lifecycle for the Droid policy compiler.

POST /policies/propose -> a Proposal is queued; one worker thread runs `node droid/runner.mjs` per proposal
(Factory Droid SDK), folds its JSON events into the proposal (plan, todos, steps, permissions, gate runs) and
computes the diff. A proposal whose gate passed is `ready`; POST /policies/{id}/approve checks the files are
byte-identical to what the gate tested, records them in hp/policies/generated/approved.json and hot-loads the module."""
import difflib
import hashlib
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from hp import policies as PL
from hp.config import secret

BACKEND = Path(__file__).resolve().parent.parent
RUNS = Path(__file__).resolve().parent / "runs"
RUNNER = Path(__file__).resolve().parent / "runner.mjs"
NODE = shutil.which("node") or "node"
TIMEOUT_S = int(os.environ.get("DROID_TIMEOUT_S", "600"))
MAX_FIX_TURNS = 2


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


class Store:
    def __init__(self):
        self.lock = threading.Lock()
        self.items = {}
        self.q = queue.Queue()
        RUNS.mkdir(exist_ok=True)
        for f in sorted(RUNS.glob("*.json")):
            try:
                p = json.loads(f.read_text())
            except json.JSONDecodeError:
                continue
            if p.get("status") in ("queued", "planning", "implementing", "testing"):
                p["status"], p["error"] = "failed", "server restarted during the run"
            self.items[p["id"]] = p
        threading.Thread(target=self._worker, daemon=True).start()

    # ── records ──
    def save(self, p):
        p["updated_at"] = time.time()
        (RUNS / f"{p['id']}.json").write_text(json.dumps(p, indent=1))

    def list(self):
        with self.lock:
            return sorted(self.items.values(), key=lambda p: -p["created_at"])

    def get(self, pid):
        return self.items.get(pid)

    def taken_kinds(self):
        on_disk = {f.stem for f in PL.GENERATED.glob("*.py") if not f.stem.startswith(("test_", "__"))}
        live = {p.get("kind") for p in self.items.values() if p.get("kind") and p["status"] not in ("rejected", "failed")}
        return sorted((on_disk | live | set(PL.approved())) - {None})

    def propose(self, request):
        pid = time.strftime("%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
        p = {"id": pid, "request": request, "status": "queued", "created_at": time.time(), "kind": None, "plan": None,
             "files": [], "todos": [], "steps": [], "permissions": [], "messages": [], "gates": [], "diff": "",
             "error": None, "session": None, "example_edit": None, "metrics": None,
             "trigger": "POST /policies/propose", "timeout_s": TIMEOUT_S}
        with self.lock:
            self.items[pid] = p
            self.save(p)
        self.q.put(pid)
        return p

    # ── the run ──
    def _worker(self):
        while True:
            pid = self.q.get()
            p = self.items[pid]
            try:
                self._run(p)
            except Exception as e:  # never kill the worker
                p["status"], p["error"] = "failed", repr(e)
            self.save(p)

    def _run(self, p):
        key = secret("FACTORY_API_KEY")
        if not key:
            p["status"], p["error"] = "failed", "FACTORY_API_KEY missing from .env"
            return
        p["status"], p["started_at"] = "planning", time.time()
        self.save(p)
        job = {"id": p["id"], "request": p["request"], "backend": str(BACKEND), "taken_kinds": self.taken_kinds(),
               "gate_python": sys.executable, "timeout_s": TIMEOUT_S, "max_fix_turns": MAX_FIX_TURNS,
               "model": os.environ.get("DROID_MODEL") or None}
        env = {"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""), "FACTORY_API_KEY": key}
        proc = subprocess.Popen([NODE, str(RUNNER)], cwd=str(RUNNER.parent), env=env, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        proc.stdin.write(json.dumps(job))
        proc.stdin.close()
        killer = threading.Timer(TIMEOUT_S + 30, proc.kill)
        killer.start()
        before = {}
        steps = {}
        try:
            for line in proc.stdout:
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._event(p, ev, steps, before)
                self.save(p)
        finally:
            killer.cancel()
            proc.wait()
        err = proc.stderr.read()
        if p["status"] not in ("ready", "failed"):
            p["status"] = "failed"
            p["error"] = p["error"] or ("runner exited without a result: " + err[-600:].replace(key, "***"))
        p["finished_at"] = time.time()
        p["diff"] = self._diff(p, before)

    def _event(self, p, ev, steps, before):
        k = ev.get("ev")
        if k == "session":
            p["session"] = {"id": ev["session_id"], "tools": ev["tools"], "disabled_tools": ev["disabled"]}
        elif k == "turn":
            p["messages"].append({"role": "host", "turn": ev["label"], "t": ev["t"]})
            if ev["label"] == "implement":
                p["status"] = "implementing"
        elif k == "plan":
            p["plan"], p["kind"], p["files"], p["gate_command"] = ev["plan"], ev["plan"]["kind"], ev["files"], ev["gate"]
            for f in p["files"]:
                path = BACKEND / f
                before[f] = path.read_text() if path.exists() else ""
        elif k == "todo":
            p["todos"] = ev["todos"]
        elif k == "step":
            s = {"id": ev["id"], "tool": ev["tool"], "summary": ev["summary"], "input": ev.get("input"), "t": ev["t"],
                 "output": None, "is_error": None}
            steps[ev["id"]] = s
            p["steps"].append(s)
        elif k == "step_result":
            s = steps.get(ev["id"])
            if s:
                s["output"], s["is_error"] = ev["output"], ev["is_error"]
        elif k == "permission":
            p["permissions"].append({k2: ev[k2] for k2 in ("tool", "target", "ok", "allowed", "t")})
        elif k == "text":
            p["messages"].append({"role": "droid", "text": ev["text"], "t": ev["t"]})
        elif k == "gate":
            r = ev["result"]
            p["status"] = "testing"
            p["gates"].append({"attempt": ev["attempt"], "passed": r.get("passed", False), "checks": r.get("checks", []),
                               "files_sha256": r.get("files"), "output": ev["output"], "t": ev["t"]})
            if r.get("passed"):
                p["example_edit"], p["metrics"] = r.get("example_edit"), r.get("metrics")
        elif k == "usage":
            p["tokens"] = ev.get("tokens")
        elif k == "error":
            p["error"] = ev["message"]
        elif k == "done":
            p["status"] = "ready" if ev.get("success") else "failed"

    def _diff(self, p, before):
        out = []
        for f in p["files"]:
            path = BACKEND / f
            new = path.read_text() if path.exists() else ""
            old = before.get(f, "")
            out += difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                        fromfile="/dev/null" if not old else f"a/backend/{f}", tofile=f"b/backend/{f}")
        return "".join(out)

    # ── human decisions ──
    def approve(self, pid):
        p = self.items[pid]
        if p["status"] != "ready":
            raise ValueError(f"proposal is {p['status']}, only a ready proposal (gate passed) can be approved")
        gate = next((g for g in reversed(p["gates"]) if g["passed"]), None)
        mod_f, test_f = (BACKEND / f for f in p["files"])
        if not gate or gate["files_sha256"] != {mod_f.name: _sha(mod_f), test_f.name: _sha(test_f)}:
            raise ValueError("files changed since the gate passed; propose again")
        mod = PL.load_file(mod_f)
        data = PL.approved()
        data[mod.KIND] = {"file": mod_f.name, "test": test_f.name, "proposal": pid, "title": getattr(mod, "TITLE", mod.KIND),
                          "sha256": gate["files_sha256"], "approved_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        PL.APPROVED.write_text(json.dumps(data, indent=1))
        PL.register(mod)
        p["status"], p["approved_at"] = "approved", time.time()
        self.save(p)
        return p

    def reject(self, pid):
        p = self.items[pid]
        if p["status"] in ("approved",):
            raise ValueError("already approved")
        if p["status"] in ("queued", "planning", "implementing", "testing"):
            raise ValueError("still running")
        if p.get("kind") not in PL.approved():  # never delete an approved module
            for f in p["files"]:
                (BACKEND / f).unlink(missing_ok=True)
        p["status"], p["rejected_at"] = "rejected", time.time()
        self.save(p)
        return p


STORE = None


def store():
    global STORE
    if STORE is None:
        STORE = Store()
    return STORE
