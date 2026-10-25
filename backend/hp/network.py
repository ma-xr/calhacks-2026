"""Shortest-path machinery on the real road graph: car trees per (source, hour) with BPR congestion,
all-pairs walking, and flow loading by subtree accumulation (no per-trip path walks)."""
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

NO_PRED = -9999


class Tree:
    """Shortest-path tree from a set of source nodes. For reverse trees, pred[v] is the next node toward the root."""
    __slots__ = ("dist", "pred", "reverse", "_levels", "_roots")

    def __init__(self, dist, pred, reverse):
        self.dist, self.pred, self.reverse, self._levels, self._roots = dist, pred, reverse, None, None

    def roots(self):
        """For every node, the source node (entry or exit) its shortest path starts from; -1 if unreachable."""
        if self._roots is None:
            d = self.dist
            order = np.argsort(np.where(np.isfinite(d), d, np.inf)).tolist()
            pred = self.pred.tolist()
            fin = np.isfinite(d).tolist()
            r = [-1] * len(pred)
            for v in order:
                if not fin[v]:
                    break
                p = pred[v]
                r[v] = v if p < 0 else r[p]
            self._roots = np.array(r)
        return self._roots

    def levels(self):
        if self._levels is None:
            n = len(self.pred)
            depth = np.full(n, -1)
            root = self.pred < 0
            depth[root] = 0
            todo = np.where(~root)[0]
            d = 0
            while len(todo):
                d += 1
                p = self.pred[todo]
                ok = depth[p] >= 0
                if not ok.any():
                    break
                depth[todo[ok]] = depth[p[ok]] + 1
                todo = todo[~ok]
            order = np.argsort(-depth, kind="stable")
            ds = depth[order]
            self._levels = [order[ds == k] for k in range(int(ds.max()) if len(ds) else 0, 0, -1)]
        return self._levels

    def path_nodes(self, target):
        """Nodes from root to target (forward) or target to root (reverse)."""
        if target < 0 or not np.isfinite(self.dist[target]):
            return None
        out = [int(target)]
        v = int(target)
        for _ in range(5000):
            p = int(self.pred[v])
            if p < 0:
                break
            out.append(p)
            v = p
        if not self.reverse:
            out.reverse()
        return out


def subtree_sums(tree, loads):
    """s[v] = loads[v] + sum of s over v's children. Positive arc costs mean children are farther than
    parents, so one pass in descending-distance order is enough (plain lists: ~0.2 ms per tree)."""
    d = np.where(np.isfinite(tree.dist), tree.dist, -1.0)
    order = np.argsort(-d)
    order = order[(d[order] > 0) & (loads[order] > 0) | (d[order] > 0)]
    s = loads.astype(float).tolist()
    pred = tree.pred.tolist()
    for v in order.tolist():
        x = s[v]
        if x:
            p = pred[v]
            if p >= 0:
                s[p] += x
    s = np.array(s)
    v = np.where((tree.pred >= 0) & (s > 0))[0]
    return s, v, tree.pred[v]


class CarNet:
    """Directed car graph for one set of closed (car-free) edges."""

    def __init__(self, world, closed, cost_factor=None):
        self.w = world
        self.factor = cost_factor if cost_factor is not None else np.ones(world.E)
        ok = ~np.isin(world.car_arc_edge, list(closed)) if closed else np.ones(len(world.car_arc_edge), bool)
        self.arc_edge = world.car_arc_edge[ok]
        self.arc_from = world.car_arc_from[ok]
        self.arc_to = world.car_arc_to[ok]
        N = world.N
        # Dense lookup (u, v) -> arc index; parallel arcs keep the fastest at free flow.
        self.lookup = np.full((N, N), -1, dtype=np.int32)
        free = world.edge_free_s[self.arc_edge]
        for i in np.argsort(-free):
            self.lookup[self.arc_from[i], self.arc_to[i]] = i
        self.trees = {}
        self.graphs = {}
        # Valid parking: nodes in the main strongly connected piece of the open car network, so a car
        # can both reach them from an inlet and leave again after a street is closed.
        from scipy.sparse.csgraph import connected_components
        g = csr_matrix((np.ones(len(self.arc_from)), (self.arc_from, self.arc_to)), shape=(N, N))
        _, lab = connected_components(g, directed=True, connection="strong")
        main = np.bincount(lab[world.car_main]).argmax()
        self.open_node = world.car_main & (lab == main)

    def graph(self, cong, hour, reverse):
        k = (hour, reverse)
        g = self.graphs.get(k)
        if g is None:
            cost = self.w.edge_free_s[self.arc_edge] * cong[hour][self.arc_edge] * self.factor[self.arc_edge]
            g = csr_matrix((cost, (self.arc_from, self.arc_to)), shape=(self.w.N, self.w.N))
            if reverse:
                g = g.T.tocsr()
            self.graphs[k] = g
        return g

    def reset(self):
        self.trees = {}
        self.graphs = {}

    def tree(self, sources, hour, cong, reverse=False):
        key = (tuple(sources), hour, reverse)
        t = self.trees.get(key)
        if t is None:
            g = self.graph(cong, hour, reverse)
            dist, pred, _ = dijkstra(g, directed=True, indices=list(sources), min_only=True, return_predecessors=True)
            t = Tree(dist, pred, reverse)
            self.trees[key] = t
        return t

    def tree_multi(self, sources, hour, cong, reverse=False):
        """Tree from several entry (or exit) nodes, each with its own head-start cost in seconds: a virtual
        node links to every source, so each destination picks the source that is cheapest overall.
        `sources` is a tuple of (node, offset_s). Roots are the real source nodes (see Tree.roots)."""
        key = ("multi", sources, hour, reverse)
        t = self.trees.get(key)
        if t is None:
            N = self.w.N
            g = self.graph(cong, hour, reverse).tocoo()
            nodes = np.array([s[0] for s in sources]); off = np.array([s[1] for s in sources], float) + 0.01
            rows = np.concatenate([g.row, np.full(len(nodes), N)])
            cols = np.concatenate([g.col, nodes])
            data = np.concatenate([g.data, off])
            ga = csr_matrix((data, (rows, cols)), shape=(N + 1, N + 1))
            dist, pred = dijkstra(ga, directed=True, indices=N, return_predecessors=True)
            dist, pred = dist[:N], pred[:N].copy()
            pred[pred == N] = NO_PRED
            t = Tree(dist, pred, reverse)
            self.trees[key] = t
        return t

    def accumulate(self, tree, loads):
        """Arc flows when loads[v] travel between the tree root and v."""
        flow = np.zeros(len(self.arc_edge))
        if not loads.any():
            return flow
        s, v, p = subtree_sums(tree, loads)
        a = self.lookup[v, p] if tree.reverse else self.lookup[p, v]
        np.add.at(flow, a, s[v])
        return flow

    def path_steps(self, tree, target):
        """Path as steps (edge*2 + reversed) from root to target (or target to root for reverse trees)."""
        nodes = tree.path_nodes(target)
        if not nodes or len(nodes) < 2:
            return None
        w = self.w
        steps = []
        for u, v in zip(nodes[:-1], nodes[1:]):
            a = self.lookup[u, v]
            if a < 0:
                return None
            e = int(self.arc_edge[a])
            steps.append(e * 2 + (0 if w.edge_a[e] == u else 1))
        return steps


class WalkNet:
    """Undirected walking (and cycling) graph. Car-free streets feel shorter (comfort bonus)."""

    def __init__(self, world, car_free, walk_speed, walk_bonus, bike_speed, bike_bonus, bike_busy=1.1, route_noise=0.25):
        self.w = world
        w = world
        cf = np.zeros(w.E, bool)
        if car_free:
            cf[list(car_free)] = True
        cf |= np.array([c == "pedestrian" for c in w.edge_cls])
        self.car_free = cf
        e = w.ped_arc_edge
        busy = np.array([c in ("primary", "secondary") for c in w.edge_cls])
        mult = np.where(cf[e], 1 - walk_bonus, 1.0) * np.where(busy[e] & ~cf[e], 1.12, 1.0)
        self.walk_cost = w.edge_len[e] / walk_speed * mult  # perceived seconds
        self.walk_len = w.edge_len[e]
        g = csr_matrix((self.walk_cost, (w.ped_arc_from, w.ped_arc_to)), shape=(w.N, w.N))
        self.dist, self.pred = dijkstra(g, directed=True, return_predecessors=True)
        # Physical length along the perceived-shortest path, for access scores and walk minutes.
        gl = csr_matrix((self.walk_len, (w.ped_arc_from, w.ped_arc_to)), shape=(w.N, w.N))
        self.len_m, _ = dijkstra(gl, directed=True, return_predecessors=True)
        N = w.N
        self.lookup = np.full((N, N), -1, dtype=np.int32)
        for i in np.argsort(-self.walk_cost):
            self.lookup[w.ped_arc_from[i], w.ped_arc_to[i]] = i
        bmult = np.where(cf[e], 1 - bike_bonus, 1.0) * np.where(busy[e] & ~cf[e], bike_busy, 1.0)
        self.bike_cost = w.edge_len[e] / bike_speed * bmult
        # Cyclists differ in how they weigh streets: three seeded draws of edge-level noise (same draw for both directions).
        rng = np.random.default_rng(99)
        self._bike_g = []
        for k in range(3):
            noise = np.exp(rng.normal(0, route_noise, w.E))[e] if k else np.ones(len(e))
            self._bike_g.append(csr_matrix((self.bike_cost * noise, (w.ped_arc_from, w.ped_arc_to)), shape=(w.N, w.N)))
        self._bike_trees = {}
        self._paths = {}

    def bike_tree(self, src, k=0):
        t = self._bike_trees.get((src, k))
        if t is None:
            d, p, _ = dijkstra(self._bike_g[k], directed=True, indices=[src], min_only=True, return_predecessors=True)
            t = Tree(d, p, False)
            self._bike_trees[(src, k)] = t
        return t

    def edges(self, o, d):
        """Edge ids (and direction) of the walking path o -> d, memoized."""
        key = (o, d)
        r = self._paths.get(key)
        if r is not None:
            return r
        if o == d or o < 0 or d < 0 or not np.isfinite(self.dist[o, d]):
            r = (np.zeros(0, int), np.zeros(0, int))
        else:
            nodes = [d]
            v = d
            pr = self.pred[o]
            for _ in range(5000):
                v = int(pr[v])
                if v < 0:
                    break
                nodes.append(v)
            nodes.reverse()
            u = np.array(nodes[:-1]); v = np.array(nodes[1:])
            a = self.lookup[u, v]
            e = self.w.ped_arc_edge[a]
            r = (e, (self.w.edge_a[e] != u).astype(int))
        self._paths[key] = r
        return r

    def bike_edges(self, src, d, k=0):
        t = self.bike_tree(src, k)
        nodes = t.path_nodes(d)
        if not nodes or len(nodes) < 2:
            return np.zeros(0, int), np.zeros(0, int)
        u = np.array(nodes[:-1]); v = np.array(nodes[1:])
        a = self.lookup[u, v]
        e = self.w.ped_arc_edge[a]
        return e, (self.w.edge_a[e] != u).astype(int)
