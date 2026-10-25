"""Street index: turns "2nd St between Market and Folsom" into engine edge ids.

The engine's `GET /world` has edge ids but no street names or geometry, so names and
polylines come from `data/processed/world.json` (same edge ids, see docs/contracts/sim-api.md).
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

from .config import WORLD_JSON

ORDINALS = {
    "1st": "first", "2nd": "second", "3rd": "third", "4th": "fourth", "5th": "fifth",
    "6th": "sixth", "7th": "seventh", "8th": "eighth", "9th": "ninth", "10th": "tenth",
}
SUFFIXES = {"street": "st", "avenue": "ave", "place": "pl", "alley": "aly", "lane": "ln", "court": "ct"}
# Roads that are never a "street" a planner means (ramps, highways, unnamed links).
SKIP_CLASSES = {"motorway", "motorway_link", "trunk", "trunk_link"}


@dataclass
class Stretch:
    street: str
    from_cross: str | None
    to_cross: str | None
    edges: list[int]
    length_m: float

    @property
    def label(self) -> str:
        if self.from_cross and self.to_cross:
            return f"{self.street} between {self.from_cross} and {self.to_cross}"
        return f"{self.street} (whole street in the model)"


class StreetIndex:
    def __init__(self, world: dict, editable: set[int] | None = None):
        self.names: list[str] = world["names"]
        self.edges: list[dict] = world["edges"]
        self.nodes: list[list[float]] = world["nodes"]
        self.editable = editable
        self.by_street: dict[str, list[int]] = defaultdict(list)
        self.node_edges: dict[int, list[int]] = defaultdict(list)
        for i, e in enumerate(self.edges):
            self.node_edges[e["a"]].append(i)
            self.node_edges[e["b"]].append(i)
            name = self.names[e["n"]]
            if name and e["c"] not in SKIP_CLASSES:
                self.by_street[name].append(i)
        self._aliases = self._build_aliases()

    # ---- name matching -------------------------------------------------
    def _build_aliases(self) -> list[tuple[str, str]]:
        out: dict[str, str] = {}
        for name in self.by_street:
            low = name.lower()
            forms = {low}
            words = low.split()
            if words[-1] in SUFFIXES:
                base = " ".join(words[:-1])
                forms |= {base, f"{base} {SUFFIXES[words[-1]]}", f"{base} {SUFFIXES[words[-1]]}."}
            for f in list(forms):
                first = f.split()[0]
                if first in ORDINALS:
                    forms.add(f.replace(first, ORDINALS[first], 1))
            for f in forms:
                # Shorter aliases never steal a longer street's name ("Montgomery" vs "New Montgomery").
                out.setdefault(f, name)
        return sorted(out.items(), key=lambda kv: -len(kv[0]))

    def mentions(self, text: str) -> list[tuple[int, str]]:
        """Street names mentioned in `text`, as (position, canonical name), in order."""
        low = text.lower()
        taken = [False] * len(low)
        found: list[tuple[int, str]] = []
        for alias, name in self._aliases:
            for m in re.finditer(r"(?<![\w])" + re.escape(alias) + r"(?![\w])", low):
                if any(taken[m.start():m.end()]):
                    continue
                for k in range(m.start(), m.end()):
                    taken[k] = True
                found.append((m.start(), name))
        return sorted(found)

    def canonical(self, name: str | None) -> str | None:
        if not name:
            return None
        hits = self.mentions(name)
        return hits[0][1] if hits else None

    # ---- geometry --------------------------------------------------------
    def _axis(self, street: str):
        """Principal axis of the street, so nodes can be ordered along it."""
        pts = [self.nodes[n] for i in self.by_street[street] for n in (self.edges[i]["a"], self.edges[i]["b"])]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        sxx = sum((p[0] - cx) ** 2 for p in pts)
        syy = sum((p[1] - cy) ** 2 for p in pts)
        sxy = sum((p[0] - cx) * (p[1] - cy) for p in pts)
        ang = 0.5 * math.atan2(2 * sxy, sxx - syy)
        ux, uy = math.cos(ang), math.sin(ang)
        return lambda node: (self.nodes[node][0] - cx) * ux + (self.nodes[node][1] - cy) * uy

    def cross_streets(self, street: str) -> list[str]:
        """Cross streets in order along `street` (only ones it actually intersects in the model)."""
        proj = self._axis(street)
        at: dict[str, list[float]] = defaultdict(list)
        for i in self.by_street.get(street, []):
            for node in (self.edges[i]["a"], self.edges[i]["b"]):
                for j in self.node_edges[node]:
                    other = self.names[self.edges[j]["n"]]
                    if other and other != street and self.edges[j]["c"] not in SKIP_CLASSES:
                        at[other].append(proj(node))
        return [name for name, _ in sorted(at.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))]

    def stretch(self, street: str, from_cross: str | None = None, to_cross: str | None = None) -> Stretch:
        street_edges = self.by_street.get(street)
        if not street_edges:
            raise ValueError(f"I don't have {street} in the model area (SF FiDi + SoMa).")
        proj = self._axis(street)

        def cross_pos(cross: str) -> float:
            ts = []
            for i in street_edges:
                for node in (self.edges[i]["a"], self.edges[i]["b"]):
                    if any(self.names[self.edges[j]["n"]] == cross for j in self.node_edges[node]):
                        ts.append(proj(node))
            if not ts:
                raise ValueError(f"{cross} doesn't cross {street} in the model. Try one of: "
                                 + ", ".join(self.cross_streets(street)))
            return sum(ts) / len(ts)

        if from_cross and to_cross:
            lo, hi = sorted((cross_pos(from_cross), cross_pos(to_cross)))
            eps = 3.0
            chosen = [i for i in street_edges
                      if lo - eps <= proj(self.edges[i]["a"]) <= hi + eps
                      and lo - eps <= proj(self.edges[i]["b"]) <= hi + eps]
        else:
            chosen = list(street_edges)
        if self.editable is not None:
            chosen = [i for i in chosen if i in self.editable]
        if not chosen:
            raise ValueError(f"No editable road on {street} between {from_cross} and {to_cross}.")
        return Stretch(street, from_cross, to_cross, sorted(chosen),
                       round(sum(self.edges[i]["l"] for i in chosen), 1))

    def edge_name(self, i: int) -> str:
        return self.names[self.edges[i]["n"]] or "an unnamed link"

    def pois_near(self, edges: list[int], pois: list[dict], radius: float = 35.0) -> list[int]:
        """POI ids within `radius` metres of the given edges (shops fronting the stretch)."""
        segs = []
        for i in edges:
            p = self.edges[i]["p"]
            segs += list(zip(p, p[1:]))

        def dist(px, pz, a, b):
            dx, dz = b[0] - a[0], b[1] - a[1]
            L = dx * dx + dz * dz or 1e-9
            t = max(0.0, min(1.0, ((px - a[0]) * dx + (pz - a[1]) * dz) / L))
            return math.hypot(px - a[0] - t * dx, pz - a[1] - t * dz)

        return [p["id"] for p in pois if any(dist(p["x"], p["z"], a, b) <= radius for a, b in segs)]


@lru_cache(maxsize=1)
def load_index(editable: frozenset[int] | None = None) -> StreetIndex:
    with open(WORLD_JSON) as f:
        return StreetIndex(json.load(f), set(editable) if editable else None)
