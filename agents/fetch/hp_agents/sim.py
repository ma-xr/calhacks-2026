"""Thin async client for the engine API on :8787 (docs/contracts/sim-api.md)."""

from __future__ import annotations

import httpx

from .config import SIM_API

_world: dict | None = None
_baseline: dict | None = None


async def world() -> dict:
    global _world
    if _world is None:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{SIM_API}/world")
            r.raise_for_status()
            _world = r.json()
    return _world


async def baseline() -> dict:
    global _baseline
    if _baseline is None:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.get(f"{SIM_API}/scenario/baseline", params={"lite": 1})
            r.raise_for_status()
            _baseline = r.json()
    return _baseline


async def pedestrianize(edges: list[int], name: str = "") -> dict:
    """Run a car-free plan. Identical edits come back from the engine's cache."""
    body = {"name": name or "ASI:One plan", "edits": {"pedestrianized": sorted(edges)}}
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(f"{SIM_API}/scenario", params={"lite": 1}, json=body)
        r.raise_for_status()
        return r.json()


async def health() -> dict:
    async with httpx.AsyncClient(timeout=5) as c:
        r = await c.get(f"{SIM_API}/health")
        r.raise_for_status()
        return r.json()
