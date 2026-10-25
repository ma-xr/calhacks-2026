"""Static world: road graph, buildings, POIs, inlets and blocks, built once from world.json.

IDs match the frontend: edge = index into world.edges, building = index into world.buildings,
POI = index into the filtered POI list (same filter as the mockup's BASE_POIS).
"""
import json
import math

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

from .config import WORLD_JSON

FREE_SPEED = {"motorway": 22, "motorway_link": 13, "trunk": 16, "trunk_link": 11, "primary": 11, "primary_link": 9,
              "secondary": 10, "secondary_link": 8, "tertiary": 9, "tertiary_link": 7, "residential": 7,
              "unclassified": 7, "living_street": 4}  # m/s, includes signal delay at free flow
LANES = {"motorway": 4, "motorway_link": 1, "trunk": 3, "primary": 3, "secondary": 2, "tertiary": 2,
         "residential": 1, "unclassified": 1, "living_street": 1}
WIDTH = {"motorway": 18, "motorway_link": 8, "trunk": 16, "trunk_link": 8, "primary": 17, "primary_link": 8,
         "secondary": 14, "secondary_link": 8, "tertiary": 11, "tertiary_link": 7, "residential": 8,
         "unclassified": 8, "living_street": 6, "pedestrian": 6}
POI_CATS = ("cafe", "restaurant", "fast_food", "bar", "shop")
# Rail inlets plus the five legacy car inlets. Their keys and entrances are fixed (the Market St baseline and the
# "Mission carries Market's inflow" rule depend on them). Every other road that crosses the map edge becomes a
# generated car inlet (see World._inlets). Clients must read inlets from GET /world and never assume ids or order.
INLET_DEFS = [
    {"key": "emb", "name": "Embarcadero", "mode": "ped", "station": "Embarcadero"},
    {"key": "mont", "name": "Montgomery", "mode": "ped", "station": "Montgomery Street"},
    {"key": "pow", "name": "Powell", "mode": "ped", "station": "Powell Street"},
    {"key": "i80", "name": "I-80 · Bay Bridge", "mode": "car", "gw": ["I-80 · Bay Bridge"]},
    {"key": "us101", "name": "US-101", "mode": "car", "gw": ["US-101 / I-80 West"]},
    {"key": "mkt", "name": "Market St (west)", "mode": "car", "gw": ["Market Street", "Mission Street"]},  # Mission carries this inflow when Market is car-free
    {"key": "fol", "name": "Folsom · 6th St", "mode": "car", "gw": ["Folsom Street", "6th Street"]},
    {"key": "bwy", "name": "Broadway · Columbus", "mode": "car", "gw": ["Broadway", "Columbus Avenue"]},
]
CLASS_RANK = ["motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link",
              "tertiary", "tertiary_link", "unclassified", "residential", "living_street"]
LEGACY_SIDE = {"i80": "east", "us101": "south", "mkt": "west", "fol": "south", "bwy": "north"}
ABSORB_M = 300.0  # a crossing this close to a legacy entrance on the same street is the same entrance


def _slug(name):
    t = name.lower().replace("·", " ").replace("/", " ").replace("'", "")
    for a, b in ((" street", " st"), (" avenue", " av"), (" boulevard", " blvd"), (" place", " pl")):
        t = t.replace(a, b)
    return "_".join("".join(c if c.isalnum() else " " for c in t).split())


def _short(name):
    for a, b in ((" Street", " St"), (" Avenue", " Av"), (" Boulevard", " Blvd"), (" Place", " Pl")):
        name = name.replace(a, b)
    return name


def poly_area(p):
    a = 0.0
    for i in range(len(p)):
        x1, z1 = p[i - 1]
        x2, z2 = p[i]
        a += (x1 + x2) * (z1 - z2)
    return abs(a / 2)


def seg_dist(px, pz, x1, z1, x2, z2):
    dx, dz = x2 - x1, z2 - z1
    t = ((px - x1) * dx + (pz - z1) * dz) / ((dx * dx + dz * dz) or 1)
    t = min(1.0, max(0.0, t))
    return math.hypot(px - x1 - t * dx, pz - z1 - t * dz)


class World:
    def __init__(self, path=WORLD_JSON):
        W = json.loads(path.read_text())
        self.raw = W
        self.bbox = W["bbox"]
        self.nodes = np.array(W["nodes"], dtype=float)
        self.names = W["names"]
        self.N = len(self.nodes)
        self._edges(W["edges"])
        self._grids()
        self._buildings(W["buildings"])
        self._pois(W["pois"])
        self._inlets(W["stations"], W["gateways"])
        self._blocks()
        self._ramps()

    # ── roads ──
    def _edges(self, E):
        self.E = len(E)
        self.edge_a = np.array([e["a"] for e in E])
        self.edge_b = np.array([e["b"] for e in E])
        self.edge_len = np.array([max(e["l"], 1.0) for e in E])
        self.edge_cls = [e["c"] for e in E]
        self.edge_name = [self.names[e["n"]] if 0 <= e["n"] < len(self.names) else "" for e in E]
        self.edge_pts = [e["p"] for e in E]
        self.edge_oneway = np.array([e["o"] for e in E])
        self.edge_car = np.array([c in FREE_SPEED for c in self.edge_cls])
        self.edge_hw = np.array([c.startswith("motorway") for c in self.edge_cls])
        self.edge_ped = np.array([not (c.startswith("motorway") or c.startswith("trunk")) for c in self.edge_cls])
        self.edge_lanes = np.array([e.get("ln") or LANES.get(e["c"], 1) for e in E], dtype=float)
        self.edge_width = np.array([WIDTH.get(c, 8) for c in self.edge_cls], dtype=float)
        self.edge_free_s = np.array([self.edge_len[i] / FREE_SPEED.get(c, 7) for i, c in enumerate(self.edge_cls)])
        mid = [p[len(p) // 2] for p in self.edge_pts]
        self.edge_mid = np.array(mid, dtype=float)
        # Directed car arcs and undirected walk arcs (two arcs per edge).
        ca_e, ca_f, ca_t = [], [], []
        for i in range(self.E):
            if not self.edge_car[i]:
                continue
            if self.edge_oneway[i] >= 0:
                ca_e.append(i); ca_f.append(self.edge_a[i]); ca_t.append(self.edge_b[i])
            if self.edge_oneway[i] <= 0:
                ca_e.append(i); ca_f.append(self.edge_b[i]); ca_t.append(self.edge_a[i])
        self.car_arc_edge = np.array(ca_e); self.car_arc_from = np.array(ca_f); self.car_arc_to = np.array(ca_t)
        pa_e, pa_f, pa_t = [], [], []
        for i in range(self.E):
            if self.edge_ped[i]:
                pa_e += [i, i]; pa_f += [self.edge_a[i], self.edge_b[i]]; pa_t += [self.edge_b[i], self.edge_a[i]]
        self.ped_arc_edge = np.array(pa_e); self.ped_arc_from = np.array(pa_f); self.ped_arc_to = np.array(pa_t)
        car_out = np.zeros(self.N, int); car_in = np.zeros(self.N, int); local_out = np.zeros(self.N, int)
        np.add.at(car_out, self.car_arc_from, 1); np.add.at(car_in, self.car_arc_to, 1)
        np.add.at(local_out, self.car_arc_from[~self.edge_hw[self.car_arc_edge]], 1)
        self.is_local_car = (car_out > 0) & (car_in > 0) & (local_out > 0)
        ped_deg = np.zeros(self.N, int); np.add.at(ped_deg, self.ped_arc_from, 1)
        self.is_ped = ped_deg > 0
        self.sinks = np.where((car_in > 0) & (car_out == 0))[0]
        # Snap places only to the main connected pieces (OSM has footway fragments and dead-end ramps).
        n = self.N
        gp = csr_matrix((np.ones(len(self.ped_arc_from)), (self.ped_arc_from, self.ped_arc_to)), shape=(n, n))
        _, lab = connected_components(gp, directed=False)
        main = np.bincount(lab[self.is_ped]).argmax() if self.is_ped.any() else 0
        self.ped_main = self.is_ped & (lab == main)
        gc = csr_matrix((np.ones(len(self.car_arc_from)), (self.car_arc_from, self.car_arc_to)), shape=(n, n))
        _, labc = connected_components(gc, directed=True, connection="strong")
        mainc = np.bincount(labc[self.is_local_car]).argmax()
        self.car_main = self.is_local_car & (labc == mainc)
        self.editable_edges = [i for i in range(self.E) if self.edge_car[i] and not self.edge_hw[i]]

    def graph(self, arc_from, arc_to, cost, arc_ids):
        """csr matrix of min arc cost per node pair, plus the arc id that achieves it. Infinite costs are dropped."""
        ok = np.isfinite(cost)
        f, t, c, ids = arc_from[ok], arc_to[ok], cost[ok], arc_ids[ok]
        order = np.lexsort((c, t, f))
        f, t, c, ids = f[order], t[order], c[order], ids[order]
        first = np.ones(len(f), bool)
        first[1:] = (f[1:] != f[:-1]) | (t[1:] != t[:-1])
        f, t, c, ids = f[first], t[first], c[first], ids[first]
        g = csr_matrix((c, (f, t)), shape=(self.N, self.N))
        arc_of = csr_matrix((ids + 1, (f, t)), shape=(self.N, self.N))
        return g, arc_of

    # ── spatial lookups ──
    def _grids(self):
        G = 60.0
        self._G = G
        self.node_grid = {}
        for i, (x, z) in enumerate(self.nodes):
            self.node_grid.setdefault((int(x // G), int(z // G)), []).append(i)
        self.seg_grid = {}
        for e, pts in enumerate(self.edge_pts):
            for j in range(len(pts) - 1):
                (x1, z1), (x2, z2) = pts[j], pts[j + 1]
                for (x, z) in ((x1, z1), (x2, z2), ((x1 + x2) / 2, (z1 + z2) / 2)):
                    self.seg_grid.setdefault((int(x // G), int(z // G)), set()).add((e, j))

    def nearest_node(self, x, z, ok):
        G = self._G
        best, bd = -1, float("inf")
        for r in range(6):
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    for i in self.node_grid.get((int(x // G) + dx, int(z // G) + dz), ()):
                        if not ok[i]:
                            continue
                        d = (self.nodes[i, 0] - x) ** 2 + (self.nodes[i, 1] - z) ** 2
                        if d < bd:
                            bd, best = d, i
            if best >= 0:
                break
        return best

    def edges_near(self, x, z, radius_extra=16.0, ped_only=True):
        G = self._G
        out = set()
        cx, cz = int(x // G), int(z // G)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for (e, j) in self.seg_grid.get((cx + dx, cz + dz), ()):
                    if ped_only and not self.edge_ped[e]:
                        continue
                    (x1, z1), (x2, z2) = self.edge_pts[e][j], self.edge_pts[e][j + 1]
                    if seg_dist(x, z, x1, z1, x2, z2) < self.edge_width[e] / 2 + radius_extra:
                        out.add(e)
        return sorted(out)

    def nearest_edge(self, x, z, max_d=40.0, name=None):
        G = self._G
        best, bd = -1, max_d
        cx, cz = int(x // G), int(z // G)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for (e, j) in self.seg_grid.get((cx + dx, cz + dz), ()):
                    (x1, z1), (x2, z2) = self.edge_pts[e][j], self.edge_pts[e][j + 1]
                    d = seg_dist(x, z, x1, z1, x2, z2) - (15 if name and name.lower() in self.edge_name[e].lower() else 0)
                    if d < bd:
                        bd, best = d, e
        return best

    def crosses_road(self, a, b):
        def o(p, q, r):
            v = float((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]))
            return (v > 0) - (v < 0)
        G = self._G
        steps = int(math.ceil(math.hypot(b[0] - a[0], b[1] - a[1]) / 30)) + 1
        cells = {(int((a[0] + (b[0] - a[0]) * i / steps) // G), int((a[1] + (b[1] - a[1]) * i / steps) // G)) for i in range(steps + 1)}
        for k in cells:
            for (e, j) in self.seg_grid.get(k, ()):
                if not self.edge_car[e] or self.edge_hw[e]:
                    continue
                c, d = self.edge_pts[e][j], self.edge_pts[e][j + 1]
                if o(a, b, c) != o(a, b, d) and o(c, d, a) != o(c, d, b):
                    return True
        return False

    def in_box(self, x, z, m=0.0):
        B = self.bbox
        return B["x0"] - m < x < B["x1"] + m and B["z0"] - m < z < B["z1"] + m

    # ── buildings ──
    def _buildings(self, B):
        self.B = len(B)
        self.bld = B
        self.bld_c = np.array([b["c"] for b in B], dtype=float)
        self.bld_h = np.array([b["h"] for b in B], dtype=float)
        self.bld_kind = [b["k"] for b in B]
        self.bld_area = np.array([poly_area(b["p"]) for b in B])
        self.bld_floors = np.maximum(1, np.round(self.bld_h / 3.6))
        self.bld_floor_area = self.bld_area * self.bld_floors  # m²
        self.bld_inside = np.array([self.in_box(x, z) for x, z in self.bld_c])
        self.bld_ped_node = np.array([self.nearest_node(x, z, self.ped_main) for x, z in self.bld_c])
        self.bld_car_node = np.array([self.nearest_node(x, z, self.car_main) for x, z in self.bld_c])
        # A few fallback parking nodes per building, for plans that close the street in front of it.
        cand = np.where(self.car_main)[0]
        cxy = self.nodes[cand]
        self.bld_car_cands = [cand[np.argsort((cxy[:, 0] - x) ** 2 + (cxy[:, 1] - z) ** 2)[:40]] for x, z in self.bld_c]

    # ── POIs ──
    def _pois(self, P):
        self.pois = []
        for p in P:
            if p["c"] in POI_CATS and self.in_box(p["x"], p["z"], 40):
                self.pois.append({"id": len(self.pois), "name": p["n"], "category": p["c"], "x": p["x"], "z": p["z"]})
        self.P = len(self.pois)
        self.poi_xy = np.array([[p["x"], p["z"]] for p in self.pois], dtype=float)
        self.poi_node = np.array([self.nearest_node(p["x"], p["z"], self.ped_main) for p in self.pois])
        self.poi_edges = [self.edges_near(p["x"], p["z"]) for p in self.pois]
        self.poi_cat = np.array([p["category"] for p in self.pois])
        # Non-food amenities (grocery, pharmacy, etc.) from the raw POI list feed the 15-minute access score.
        self.amenities = [p for p in P if self.in_box(p["x"], p["z"], 200)]

    # ── inlets / regions ──
    def _inlets(self, stations, gateways):
        self.stations = {}
        for s in stations:
            nodes = sorted({self.nearest_node(x, z, self.ped_main) for x, z in s["e"]} - {-1})
            self.stations[s["name"]] = {"name": s["name"], "c": s["c"], "nodes": nodes}

        legacy_gw = [g for g in gateways if g.get("src", "end") == "end"]

        def gw_nodes(names, d):
            return [g["node"] for g in legacy_gw if g["name"] in names and g[d]]

        def exits_for(entries, names):
            named = gw_nodes(names, "out")
            if named:
                return named
            out = []
            for en in entries:
                d = np.hypot(*(self.nodes[self.sinks] - self.nodes[en]).T)
                if len(d) and d.min() < 900:
                    out.append(int(self.sinks[d.argmin()]))
            return sorted(set(out)) or [int(self.sinks[0])]

        self.inlets = []
        consumed = []  # (node, name, hw) of gateways owned by the legacy car inlets
        for i, g in enumerate(INLET_DEFS):
            o = {"i": i, **{k: g[k] for k in ("key", "name", "mode")}, "legacy": True}
            if g["mode"] == "ped":
                st = self.stations[g["station"]]
                o["station"] = st["name"]; o["nodes"] = st["nodes"]; o["x"], o["z"] = st["c"]
                o["side"] = None
            else:
                o["entries"] = gw_nodes(g["gw"], "in"); o["exits"] = exits_for(o["entries"], g["gw"])
                x, z = self.nodes[o["entries"][0]]
                o["x"], o["z"] = float(x), float(z)
                mine = [q for q in legacy_gw if q["name"] in g["gw"]]
                consumed += [(q["node"], q["name"], q["hw"]) for q in mine]
                o["side"] = mine[0]["side"] if mine else None
                o["cls"] = min((q["cls"] for q in mine), key=CLASS_RANK.index)
                o["gateways"] = sorted({q["node"] for q in mine})
                o["edges"] = []
            self.inlets.append(o)

        # Generated car inlets: every other legacy road end and every boundary crossing, grouped by street and
        # side, minus crossings that are the same entrance as a legacy inlet.
        can_reach, reached = self._reach_main()

        def absorbed(q):
            x, z = self.nodes[q["node"]]
            for (v, nm, hw) in consumed:
                same = (nm == q["name"]) or (hw and q["hw"])
                if same and math.hypot(*(self.nodes[v] - (x, z))) <= ABSORB_M:
                    return True
            return False
        groups = {}
        taken = {v for v, _, _ in consumed}
        for q in gateways:
            if q["node"] in taken and q.get("src", "end") == "end":
                continue
            if absorbed(q):
                continue
            groups.setdefault((q["name"], q["side"]), []).append(q)
        gen = []
        for (nm, side), qs in groups.items():
            entries = sorted({q["node"] for q in qs if q["in"] and can_reach[q["node"]]})
            exits = sorted({q["node"] for q in qs if q["out"] and reached[q["node"]]})
            if not entries and not exits:
                continue
            cls = min((q["cls"] for q in qs), key=CLASS_RANK.index)
            at = next((q["at"] for q in qs if q.get("at")), None)
            if at is None:  # legacy road end outside the box: clamp it onto the boundary
                x, z = self.nodes[qs[0]["node"]]
                at = [float(np.clip(x, self.bbox["x0"], self.bbox["x1"])), float(np.clip(z, self.bbox["z0"], self.bbox["z1"]))]
            lanes = max((q.get("lanes") or LANES.get(q["cls"], 1)) for q in qs)
            gen.append({"key": f"{_slug(nm)}_{side}", "name": f"{_short(nm)} · {side}", "mode": "car", "legacy": False,
                        "side": side, "cls": cls, "lanes": lanes, "entries": entries, "exits": exits,
                        "x": float(at[0]), "z": float(at[1]), "gateways": sorted({q["node"] for q in qs}),
                        "edges": sorted({q["edge"] for q in qs if q.get("edge") is not None})})
        gen.sort(key=lambda g: (["north", "east", "south", "west"].index(g["side"]), g["key"]))
        for g in gen:
            g["i"] = len(self.inlets)
            self.inlets.append(g)
        for g in self.inlets:
            if g["mode"] == "car" and "lanes" not in g:
                g["lanes"] = LANES.get(g["cls"], 1)
            if g["mode"] == "car":
                g["at"] = [float(np.clip(g["x"], self.bbox["x0"], self.bbox["x1"])), float(np.clip(g["z"], self.bbox["z0"], self.bbox["z1"]))]
        for k, sd in LEGACY_SIDE.items():  # their road ends lie far outside the box, so pin the side by hand
            next(g for g in self.inlets if g["key"] == k)["side"] = sd
        self.inlet_by_key = {g["key"]: g for g in self.inlets}
        self.car_inlets = [g["i"] for g in self.inlets if g["mode"] == "car"]
        self.rail_inlets = [g["i"] for g in self.inlets if g["mode"] == "ped"]

    def _reach_main(self):
        """Nodes that can drive into the main car network, and nodes reachable from it (OSM edge pieces)."""
        from scipy.sparse.csgraph import breadth_first_order
        n = self.N
        g = csr_matrix((np.ones(len(self.car_arc_from)), (self.car_arc_from, self.car_arc_to)), shape=(n, n))
        root = int(np.where(self.car_main)[0][0])
        fwd = np.zeros(n, bool); fwd[breadth_first_order(g, root, directed=True, return_predecessors=False)] = True
        bwd = np.zeros(n, bool); bwd[breadth_first_order(g.T.tocsr(), root, directed=True, return_predecessors=False)] = True
        return bwd, fwd

    # ── blocks (variant A rule: union buildings within 70 m not separated by a road) ──
    def _blocks(self):
        BG = 70.0
        grid = {}
        for i, (x, z) in enumerate(self.bld_c):
            grid.setdefault((int(x // BG), int(z // BG)), []).append(i)
        par = list(range(self.B))

        def find(i):
            while par[i] != i:
                par[i] = par[par[i]]
                i = par[i]
            return i
        for b in range(self.B):
            cx, cz = int(self.bld_c[b, 0] // BG), int(self.bld_c[b, 1] // BG)
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((cx + dx, cz + dz), ()):
                        if j <= b or math.hypot(*(self.bld_c[j] - self.bld_c[b])) > 70:
                            continue
                        ra, rb = find(b), find(j)
                        if ra != rb and not self.crosses_road(tuple(map(float, self.bld_c[b])), tuple(map(float, self.bld_c[j]))):
                            par[ra] = rb
        ids = {}
        self.block_of = np.zeros(self.B, int)
        for i in range(self.B):
            r = find(i)
            if r not in ids:
                ids[r] = len(ids)
            self.block_of[i] = ids[r]
        self.n_blocks = len(ids)

    # ── freeway ramps (motorway_link), closable as a whole ──
    def _ramps(self):
        """Group motorway_link edges that share nodes into ramps. Each gets a name from the surface streets it meets,
        and is an on-ramp (street → freeway), off-ramp (freeway → street) or connector (freeway → freeway)."""
        link = [i for i in range(self.E) if self.edge_cls[i] == "motorway_link"]
        par = {}

        def find(x):
            while par.setdefault(x, x) != x:
                par[x] = par[par[x]]
                x = par[x]
            return x
        for e in link:
            par[find(int(self.edge_a[e]))] = find(int(self.edge_b[e]))
        groups = {}
        for e in link:
            groups.setdefault(find(int(self.edge_a[e])), []).append(e)
        surface = {}  # node -> surface street names meeting it
        for i in range(self.E):
            if self.edge_car[i] and not self.edge_hw[i]:
                for n in (int(self.edge_a[i]), int(self.edge_b[i])):
                    surface.setdefault(n, set()).add(self.edge_name[i])
        arcs = [k for k in range(len(self.car_arc_edge)) if self.edge_cls[self.car_arc_edge[k]] == "motorway_link"]
        self.ramps = []
        for es in sorted(groups.values(), key=lambda es: min(es)):
            ess = set(es)
            mine = [k for k in arcs if self.car_arc_edge[k] in ess]
            on = any(int(self.car_arc_from[k]) in surface for k in mine)
            off = any(int(self.car_arc_to[k]) in surface for k in mine)
            streets = sorted({nm for k in mine for n in (int(self.car_arc_from[k]), int(self.car_arc_to[k])) for nm in surface.get(n, ()) if nm})
            kind = "on" if on and not off else "off" if off and not on else "connector" if not (on or off) else "ramps"
            label = {"on": "on-ramp", "off": "off-ramp", "connector": "freeway connector", "ramps": "ramps"}[kind]
            where = " / ".join(_short(n) for n in streets[:2])
            mid = np.mean([self.edge_mid[e] for e in es], 0)
            self.ramps.append({"id": len(self.ramps), "name": f"{where} {label}" if where else label.capitalize(), "kind": kind,
                               "edges": sorted(int(e) for e in es), "x": float(mid[0]), "z": float(mid[1]),
                               "inside": bool(self.in_box(*mid)), "streets": streets})
        self.ramp_of = {e: r["id"] for r in self.ramps for e in r["edges"]}

    def edges_named(self, name):
        return [i for i, n in enumerate(self.edge_name) if n == name]

    def stretch(self, name, frm, to):
        """Edge ids along `name` between its crossings with streets `frm` and `to` (BFS)."""
        on = self.edges_named(name)

        def node_of(cross):
            ns = {int(n) for i in self.edges_named(cross) for n in (self.edge_a[i], self.edge_b[i])}
            for i in on:
                for n in (int(self.edge_a[i]), int(self.edge_b[i])):
                    if n in ns:
                        return n
            return None
        a, b = node_of(frm), node_of(to)
        if a is None or b is None:
            return []
        adj = {}
        for i in on:
            u, v = int(self.edge_a[i]), int(self.edge_b[i])
            adj.setdefault(u, []).append((v, i)); adj.setdefault(v, []).append((u, i))
        prev = {a: None}
        q = [a]
        while q:
            u = q.pop(0)
            if u == b:
                break
            for v, i in adj.get(u, []):
                if v not in prev:
                    prev[v] = (u, i); q.append(v)
        out, v = [], b
        while prev.get(v):
            u, i = prev[v]; out.append(i); v = u
        return out
