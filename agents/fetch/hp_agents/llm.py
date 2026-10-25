"""ASI:One (asi1) chat completions: parsing free-form requests and writing the brief's summary.

The LLM never invents numbers: it extracts street names, or rewrites facts it is handed.
Everything still works without a key (regex parsing, no executive summary).
"""

from __future__ import annotations

import json
import re

import httpx

from .config import ASI_ONE_API_KEY, ASI_ONE_MODEL, ASI_ONE_URL


async def complete(system: str, user: str, max_tokens: int = 600) -> str | None:
    if not ASI_ONE_API_KEY:
        return None
    body = {"model": ASI_ONE_MODEL, "temperature": 0.1, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    try:
        async with httpx.AsyncClient(timeout=45) as c:
            r = await c.post(ASI_ONE_URL, json=body, headers={"Authorization": f"Bearer {ASI_ONE_API_KEY}"})
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError):
        return None


async def extract_stretch(text: str, streets: list[str]) -> dict | None:
    system = (
        "You map a request about San Francisco streets to JSON. Use only names from this list: "
        + "; ".join(streets)
        + '. Reply with JSON only: {"street": name|null, "from_cross": name|null, "to_cross": name|null}. '
        "street is the street to make car-free; from_cross/to_cross are the cross streets that bound it."
    )
    out = await complete(system, text, 120)
    if not out:
        return None
    m = re.search(r"\{.*\}", out, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


async def brief_summary(label: str, facts: dict) -> str | None:
    system = (
        "You write the executive summary of a city-council hearing brief. Use ONLY numbers present in the "
        "JSON facts, copied exactly; never estimate or add new figures. 120-180 words, plain prose, "
        "neutral tone: what the plan does, who gains, who bears costs, and what to watch."
    )
    return await complete(system, f"Plan: car-free {label}\nFacts:\n{json.dumps(facts, default=str)[:12000]}", 400)
