"""Helpers for policy unit tests (used by Droid's generated tests and by the gate).

    from hp.policies import testing
    mod = testing.load_policy("through_charge")          # imports hp/policies/generated/through_charge.py
    view = testing.view()                          # CtxView of the baseline weekday (real agents, edges, POIs)
    out = testing.run(mod, view, {"amount": 5})    # validated hook arrays
    m = testing.metrics({"amount": 5}, mod)        # full engine run (calibrates once per process, ~5 s)
"""
from functools import lru_cache

from . import GENERATED, CtxView, load_file, register, resolve_params, run_module


@lru_cache(maxsize=1)
def engine():
    from ..engine import Engine
    from ..inputs import Inputs
    from ..params import Params
    from ..world import World
    return Engine(World(), Params(), Inputs())


def calibrated_engine():
    e = engine()
    if e.baseline is None:
        e.calibrate()
    return e


@lru_cache(maxsize=1)
def view():
    from ..engine import Ctx, edits_key
    from ..network import CarNet
    e = engine()
    norm, _ = edits_key({})
    closed = e.closed_for(norm)
    ctx = Ctx(e, e.pb.base, CarNet(e.w, closed), e.walknet(closed), norm, closed)
    return CtxView(ctx)


def load_policy(slug):
    return load_file(GENERATED / f"{slug}.py")


def run(mod, v=None, params=None):
    return run_module(mod, v or view(), resolve_params(mod, params or {}))


def metrics(params, mod):
    """Baseline vs policy metrics from a full engine evaluation (registers `mod` in this process)."""
    register(mod)
    e = calibrated_engine()
    r = e.evaluate({"policies": [{"kind": mod.KIND, "params": resolve_params(mod, params)}]})
    return e.baseline["metrics"], r["metrics"]
