"""Find "<street> between <cross> and <cross>" in a chat message."""

from __future__ import annotations

import re

from . import llm

RANGE = re.compile(r"\b(between|from)\b(?P<a>.+?)\b(and|to|through|thru|until)\b(?P<b>.+)", re.I)
BRIEF = re.compile(r"\b(hearing brief|full report|brief|pdf|report)\b", re.I)


def regex_stretch(text: str, index) -> dict:
    hits = index.mentions(text)
    out = {"street": None, "from_cross": None, "to_cross": None}
    if not hits:
        return out
    m = RANGE.search(text)
    crosses: list[str] = []
    if m:
        a = index.mentions(m.group("a"))
        b = index.mentions(m.group("b"))
        if a and b:
            crosses = [a[0][1], b[0][1]]
    rest = [name for _, name in hits if name not in crosses]
    out["street"] = rest[0] if rest else None
    if crosses and out["street"]:
        out["from_cross"], out["to_cross"] = crosses
    return out


async def parse_stretch(text: str, index, use_llm: bool = True) -> dict:
    out = regex_stretch(text, index)
    if out["street"] is None and use_llm:
        guess = await llm.extract_stretch(text, sorted(index.by_street))
        if guess:
            out = {k: index.canonical(guess.get(k)) for k in ("street", "from_cross", "to_cross")}
    return out


def wants_brief(text: str) -> bool:
    return bool(BRIEF.search(text))
