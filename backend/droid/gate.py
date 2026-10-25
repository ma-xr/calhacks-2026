"""Test gate for a Droid-written policy. Run from backend/:  .venv/bin/python -m droid.gate <kind>

Checks, in order (all must pass before a human can approve):
  1. files      hp/policies/generated/<kind>.py and test_<kind>.py exist
  2. static     AST scan: only numpy/math (+ pytest, hp.policies in the test); no I/O, eval, randomness, dunders
  3. load       the module imports with networking disabled and matches the plugin interface
  4. pytest     the generated test + the engine suite (backend/tests) pass
  5. determinism  the same edits evaluated twice give identical metrics
  6. sanity     metrics are finite and in a sane range vs the baseline, and the policy changes something

The last stdout line is `GATE_RESULT {json}`."""
import ast
import hashlib
import io
import json
import math
import re
import socket
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
GEN = BACKEND / "hp" / "policies" / "generated"
HEADLINE = ("vmt", "delay_hours", "charges_paid_usd", "through_charges_paid_usd", "revenue", "visits", "walk_minutes", "co2_tonnes", "people")

MOD_IMPORTS = {"numpy", "math"}
TEST_IMPORTS = MOD_IMPORTS | {"pytest", "hp.policies", "hp.policies.testing", "hp"}
BAD_NAMES = {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint", "globals", "locals", "vars",
             "setattr", "delattr", "getattr", "memoryview", "exit", "quit"}
BAD_ATTRS = {"random", "load", "loads", "save", "savez", "savez_compressed", "savetxt", "loadtxt", "fromfile", "tofile",
             "genfromtxt", "memmap", "system", "popen", "DataSource", "ctypeslib", "lib", "write_text",
             "read_text", "unlink", "rmtree", "environ"}


def static_check(path, allowed):
    errs = []
    tree = ast.parse(path.read_text(), filename=path.name)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name not in allowed:
                    errs.append(f"line {node.lineno}: import {a.name} not allowed")
        elif isinstance(node, ast.ImportFrom):
            mod = ("." * node.level) + (node.module or "")
            if mod not in allowed:
                errs.append(f"line {node.lineno}: from {mod} import … not allowed")
        elif isinstance(node, ast.Name) and node.id in BAD_NAMES:
            errs.append(f"line {node.lineno}: {node.id} not allowed")
        elif isinstance(node, ast.Attribute) and (node.attr in BAD_ATTRS or node.attr.startswith("__")):
            errs.append(f"line {node.lineno}: .{node.attr} not allowed")
    return errs


def no_network():
    def refuse(*a, **k):
        raise PermissionError("network access is disabled in the policy gate")
    socket.socket.connect = refuse
    socket.socket.connect_ex = refuse
    socket.create_connection = refuse
    socket.getaddrinfo = refuse


def finite(x):
    if isinstance(x, dict):
        return all(finite(v) for v in x.values())
    if isinstance(x, (list, tuple)):
        return all(finite(v) for v in x)
    if isinstance(x, float):
        return math.isfinite(x)
    return True


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def gate(kind):
    t0 = time.time()
    mod_p, test_p = GEN / f"{kind}.py", GEN / f"test_{kind}.py"
    checks, out = [], {"kind": kind, "files": {mod_p.name: sha(mod_p), test_p.name: sha(test_p)}}

    def check(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
        return ok

    def done():
        out.update(passed=all(c["ok"] for c in checks) and len(checks) == 6, checks=checks, seconds=round(time.time() - t0, 1))
        print("GATE_RESULT " + json.dumps(out))
        return 0 if out["passed"] else 1

    if not check("files", mod_p.exists() and test_p.exists(), f"{mod_p.name}, {test_p.name}"):
        return done()
    errs = static_check(mod_p, MOD_IMPORTS) + [f"{test_p.name} {e}" for e in static_check(test_p, TEST_IMPORTS)]
    if not check("static", not errs, "; ".join(errs[:8]) or "imports and calls are allowed"):
        return done()

    no_network()
    sys.path.insert(0, str(BACKEND))
    from hp import policies as PL
    from hp.policies import testing
    try:
        mod = PL.load_file(mod_p)
        ok = mod.KIND == kind and isinstance(getattr(mod, "PARAMS", {}), dict) and isinstance(getattr(mod, "EXAMPLE", {}), dict)
        detail = f"KIND={mod.KIND!r}, hooks={[h for h in PL.HOOKS if hasattr(mod, h)] + (['apply'] if hasattr(mod, 'apply') else [])}"
        if not ok:
            detail += f" (KIND must be {kind!r}; PARAMS and EXAMPLE must be dicts)"
    except Exception as e:
        ok, detail = False, repr(e)
    if not check("load", ok, detail):
        return done()

    import pytest
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = pytest.main([str(test_p), str(BACKEND / "tests"), "-q", "-p", "no:cacheprovider", "--rootdir", str(BACKEND), "-W", "ignore"])
    out["pytest_output"] = buf.getvalue()[-6000:]
    print(out["pytest_output"])
    if not check("pytest", code == 0, out["pytest_output"].strip().splitlines()[-1] if out["pytest_output"].strip() else f"exit {code}"):
        return done()

    try:
        mod = PL.load_file(mod_p)
        params = PL.resolve_params(mod, getattr(mod, "EXAMPLE", {}))
        PL.register(mod)
        e = testing.calibrated_engine()
        edits = {"policies": [{"kind": kind, "params": params}]}
        r1, r2 = e.evaluate(edits)["metrics"], e.evaluate(edits)["metrics"]
        same = json.dumps(r1, sort_keys=True, default=str) == json.dumps(r2, sort_keys=True, default=str)
        detail = "two runs gave identical metrics" if same else "metrics differ between two runs of the same edits"
    except Exception as ex:
        same, detail, r1 = False, repr(ex), None
    if not check("determinism", same, detail):
        return done()

    b = e.baseline["metrics"]
    probs = []
    if not finite(r1):
        probs.append("non-finite metric")
    for k, lo, hi in (("vmt", .5, 1.5), ("revenue", .5, 1.5), ("people", .8, 1.2), ("visits", .5, 1.5)):
        ratio = r1[k] / b[k] if b[k] else 1.0
        if not lo <= ratio <= hi:
            probs.append(f"{k} ratio {ratio:.2f} outside [{lo}, {hi}]")
    if r1["delay_hours"] < 0:
        probs.append("negative delay")
    delta = {k: {"baseline": b.get(k, 0), "policy": r1.get(k, 0), "delta": r1.get(k, 0) - b.get(k, 0)} for k in HEADLINE}
    delta["car_commuters"] = {"baseline": b["commuters"]["car"], "policy": r1["commuters"]["car"],
                              "delta": r1["commuters"]["car"] - b["commuters"]["car"]}
    changed = any(abs(v["delta"]) > 1e-9 for v in delta.values())
    if not changed:
        probs.append(f"no measurable effect at EXAMPLE params {params}")
    out["example_edit"] = edits
    out["metrics"] = delta
    check("sanity", not probs, "; ".join(probs) or f"effect at {params}: " + ", ".join(
        f"{k} {v['delta']:+.4g}" for k, v in delta.items() if abs(v["delta"]) > 1e-9))
    return done()


if __name__ == "__main__":
    if len(sys.argv) != 2 or not re.match(r"^[a-z][a-z0-9_]{1,40}$", sys.argv[1]):
        print("usage: python -m droid.gate <kind>")
        sys.exit(2)
    sys.exit(gate(sys.argv[1]))
