// Sim engine: a port of the mockup's rules (mockup/variants/a-skyline/template.html) with no
// database access. Reducers feed it the edits and congestion state and write back what it returns.
// Everything here is deterministic: same world + same edits => same city.
import W from '../../../data/processed/world.json';

// ───────────────────────── world ─────────────────────────
type Pt = [number, number];
interface Edge { a: number; b: number; c: string; n: number; o: number; l: number; ln?: number; p: Pt[];
  id: number; car: boolean; ped: boolean; lanes: number; w: number; name: string; hw: boolean }
interface Building { p: Pt[]; h: number; k: string; c: Pt; n?: string;
  id: number; area: number; inside: boolean; pedNode: number; carNode: number; floor: number }
interface Station { name: string; c: Pt; e: Pt[]; nodes: number[] }
interface Arc { e: number; from: number; to: number; rev: boolean }

export const SCALE = 6; // 1 sim = 6 people
export const WORKDAYS = 250;
export const SETTLE_DAYS = 5;

const NODES = W.nodes as Pt[];
const NAMES = W.names as string[];
const BB = W.bbox as { x0: number; x1: number; z0: number; z1: number };
export const EDGES = W.edges as unknown as Edge[];
export const BLD = W.buildings as unknown as Building[];

const inBox = (x: number, z: number, m = 0) => x > BB.x0 - m && x < BB.x1 + m && z > BB.z0 - m && z < BB.z1 + m;
function mulberry32(a: number) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const hash2 = (a: number, b: number) => { let h = Math.imul(a + 0x9e3779b9, 0x85ebca6b) ^ Math.imul(b + 0x7f4a7c15, 0xc2b2ae35); h ^= h >>> 13; h = Math.imul(h, 0x27d4eb2f); h ^= h >>> 16; return (h >>> 0) / 4294967296; };
const gumbel = (u: number) => -Math.log(-Math.log(Math.min(Math.max(u, 1e-9), 1 - 1e-9)));
const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
function polyArea(p: Pt[]) { let a = 0; for (let i = 0, j = p.length - 1; i < p.length; j = i++) a += (p[j][0] + p[i][0]) * (p[j][1] - p[i][1]); return Math.abs(a / 2); }

// ───────────────────────── road graph ─────────────────────────
const SPEED: Record<string, number> = { motorway: 22, motorway_link: 13, trunk: 16, trunk_link: 11, primary: 11, primary_link: 9, secondary: 10, secondary_link: 8, tertiary: 9, tertiary_link: 7, residential: 7, unclassified: 7, living_street: 4 };
const LANES: Record<string, number> = { motorway: 4, motorway_link: 1, trunk: 3, primary: 3, secondary: 2, tertiary: 2, residential: 1, unclassified: 1, living_street: 1 };
const WIDTH: Record<string, number> = { motorway: 18, motorway_link: 8, trunk: 16, trunk_link: 8, primary: 17, primary_link: 8, secondary: 14, secondary_link: 8, tertiary: 11, tertiary_link: 7, residential: 8, unclassified: 8, living_street: 6, pedestrian: 6 };
EDGES.forEach((e, i) => {
  e.id = i; e.car = e.c in SPEED; e.ped = !e.c.startsWith('motorway') && !e.c.startsWith('trunk');
  e.lanes = e.ln || LANES[e.c] || 1; e.w = WIDTH[e.c] || 8; e.name = NAMES[e.n] || '';
  e.hw = e.c.startsWith('motorway');
});
const arcs: Arc[] = []; const carOut: number[][] = NODES.map(() => []), carIn: number[][] = NODES.map(() => []), pedOut: number[][] = NODES.map(() => []);
EDGES.forEach((e) => {
  if (!e.car) return;
  if (e.o >= 0) { const k = arcs.length; arcs.push({ e: e.id, from: e.a, to: e.b, rev: false }); carOut[e.a].push(k); carIn[e.b].push(k); }
  if (e.o <= 0) { const k = arcs.length; arcs.push({ e: e.id, from: e.b, to: e.a, rev: true }); carOut[e.b].push(k); carIn[e.a].push(k); }
});
const pedArcs: Arc[] = [];
EDGES.forEach((e) => { if (e.ped) { pedArcs.push({ e: e.id, from: e.a, to: e.b, rev: false }); pedOut[e.a].push(pedArcs.length - 1); pedArcs.push({ e: e.id, from: e.b, to: e.a, rev: true }); pedOut[e.b].push(pedArcs.length - 1); } });

class Heap { k: number[] = []; v: number[] = []; get size() { return this.k.length; }
  push(k: number, v: number) { const K = this.k, V = this.v; let i = K.length; K.push(k); V.push(v); while (i > 0) { const p = (i - 1) >> 1; if (K[p] <= k) break; K[i] = K[p]; V[i] = V[p]; i = p; } K[i] = k; V[i] = v; }
  pop(): [number, number] { const K = this.k, V = this.v; const rk = K[0], rv = V[0]; const lk = K.pop()!, lv = V.pop()!; const n = K.length; if (n) { let i = 0; for (;;) { const l = 2 * i + 1, r = l + 1; let m = i, mk = lk; if (l < n && K[l] < mk) { m = l; mk = K[l]; } if (r < n && K[r] < mk) { m = r; } if (m === i) break; K[i] = K[m]; V[i] = V[m]; i = m; } K[i] = lk; V[i] = lv; } return [rk, rv]; } }
interface Tree { dist: Float64Array; prev: Int32Array; reverse: boolean; arcList: Arc[] }
function dijkstra(sources: number[], outList: number[][], arcList: Arc[], cost: (a: Arc) => number, reverse: boolean): Tree {
  const n = NODES.length, dist = new Float64Array(n).fill(Infinity), prev = new Int32Array(n).fill(-1), h = new Heap();
  for (const s of sources) { dist[s] = 0; h.push(0, s); }
  while (h.size) { const [d, u] = h.pop(); if (d > dist[u]) continue;
    for (const ai of outList[u]) { const a = arcList[ai]; const c = cost(a); if (c === Infinity) continue; const v = reverse ? a.from : a.to; const nd = d + c; if (nd < dist[v]) { dist[v] = nd; prev[v] = ai; h.push(nd, v); } } }
  return { dist, prev, reverse, arcList };
}
// Arc ids from tree root to target (forward tree) or from target to root (reverse tree).
function treePath(tree: Tree, target: number): number[] | null {
  const out: number[] = []; let v = target, guard = 0;
  if (target < 0 || tree.dist[target] === Infinity) return null;
  while (tree.prev[v] !== -1 && guard++ < 5000) { const a = tree.arcList[tree.prev[v]]; out.push(tree.prev[v]); v = tree.reverse ? a.to : a.from; }
  if (!tree.reverse) out.reverse();
  return out;
}
const G = 60, nodeGrid = new Map<string, number[]>();
const gk = (x: number, z: number) => Math.floor(x / G) + ',' + Math.floor(z / G);
NODES.forEach(([x, z], i) => { const k = gk(x, z); if (!nodeGrid.has(k)) nodeGrid.set(k, []); nodeGrid.get(k)!.push(i); });
function nearestNode(x: number, z: number, ok: (i: number) => boolean) {
  let best = -1, bd = Infinity;
  for (let r = 0; r < 6 && best < 0; r++) for (let dx = -r; dx <= r; dx++) for (let dz = -r; dz <= r; dz++) {
    const list = nodeGrid.get((Math.floor(x / G) + dx) + ',' + (Math.floor(z / G) + dz)); if (!list) continue;
    for (const i of list) { if (!ok(i)) continue; const d = (NODES[i][0] - x) ** 2 + (NODES[i][1] - z) ** 2; if (d < bd) { bd = d; best = i; } }
  }
  return best;
}
const isLocalCar = (i: number) => carOut[i].length > 0 && carIn[i].length > 0 && carOut[i].some(a => !EDGES[arcs[a].e].hw);
const isPed = (i: number) => pedOut[i].length > 0;
const segGrid = new Map<string, [number, number][]>();
EDGES.forEach((e) => { for (let j = 0; j < e.p.length - 1; j++) { const [x1, z1] = e.p[j], [x2, z2] = e.p[j + 1]; const cells = new Set([gk(x1, z1), gk(x2, z2), gk((x1 + x2) / 2, (z1 + z2) / 2)]); for (const k of cells) { if (!segGrid.has(k)) segGrid.set(k, []); segGrid.get(k)!.push([e.id, j]); } } });
function segDist(px: number, pz: number, x1: number, z1: number, x2: number, z2: number) { const dx = x2 - x1, dz = z2 - z1; const t = clamp(((px - x1) * dx + (pz - z1) * dz) / (dx * dx + dz * dz || 1), 0, 1); return Math.hypot(px - x1 - t * dx, pz - z1 - t * dz); }

// ───────────────────────── places ─────────────────────────
BLD.forEach((b, i) => {
  b.id = i; b.area = polyArea(b.p); b.inside = inBox(b.c[0], b.c[1]);
  b.pedNode = nearestNode(b.c[0], b.c[1], isPed); b.carNode = nearestNode(b.c[0], b.c[1], isLocalCar);
  b.floor = b.area * Math.max(1, Math.round(b.h / 3.6));
});
export const ZONES = ['res', 'office', 'retail', 'mixed'];
const capOf = (kind: string, floor: number) => ({
  jobs: kind === 'office' ? floor / 18 : kind === 'mixed' ? floor / 60 : kind === 'retail' ? floor / 50 : kind === 'hotel' ? floor / 80 : kind === 'civic' ? floor / 70 : 0,
  res: kind === 'res' ? floor / 45 : kind === 'mixed' ? floor / 140 : 0,
});
const offices = BLD.filter(b => b.inside && b.pedNode >= 0 && b.carNode >= 0 && (b.k === 'office' || (b.k === 'mixed' && b.h > 24) || b.k === 'hotel'));
const homes = BLD.filter(b => b.inside && b.pedNode >= 0 && (b.k === 'res' || (b.k === 'mixed' && b.h < 70)));
export const CAT: Record<string, { w: number; ticket: number; capture: number; lunch: number; label: string }> = {
  cafe: { w: 1.2, ticket: 9, capture: .028, lunch: .8, label: 'Café' },
  restaurant: { w: 1.5, ticket: 26, capture: .012, lunch: 1.3, label: 'Restaurant' },
  fast_food: { w: 1.1, ticket: 13, capture: .02, lunch: 1.1, label: 'Quick bite' },
  bar: { w: 1, ticket: 30, capture: .008, lunch: .2, label: 'Bar' },
  shop: { w: .8, ticket: 38, capture: .009, lunch: 0, label: 'Shop' },
};
export interface Poi { id: number; x: number; z: number; n: string; c: string; node: number; q: number; edges: number[]; virtual?: boolean }
const PG = 120;
type PoiGrid = Map<string, Poi[]>;
function indexPois(list: Poi[]): PoiGrid { const g: PoiGrid = new Map(); list.forEach(p => { const k = Math.floor(p.x / PG) + ',' + Math.floor(p.z / PG); if (!g.has(k)) g.set(k, []); g.get(k)!.push(p); }); return g; }
function poisNear(grid: PoiGrid, x: number, z: number, r: number) { const out: Poi[] = []; const R = Math.ceil(r / PG); const cx = Math.floor(x / PG), cz = Math.floor(z / PG); for (let dx = -R; dx <= R; dx++) for (let dz = -R; dz <= R; dz++) { const l = grid.get((cx + dx) + ',' + (cz + dz)); if (l) for (const p of l) if (Math.hypot(p.x - x, p.z - z) < r) out.push(p); } return out; }
// Edges within ~22 m of each POI: its walk-by exposure.
function poiEdges(x: number, z: number) { const s = new Set<number>(); const cx = Math.floor(x / G), cz = Math.floor(z / G); for (let dx = -1; dx <= 1; dx++) for (let dz = -1; dz <= 1; dz++) { const l = segGrid.get((cx + dx) + ',' + (cz + dz)); if (l) for (const [ei, j] of l) { const e = EDGES[ei]; if (e.ped && segDist(x, z, e.p[j][0], e.p[j][1], e.p[j + 1][0], e.p[j + 1][1]) < e.w / 2 + 16) s.add(ei); } } return [...s]; }
// Base POI ids are their index in this list; the viewer must build the same list (CAT filter + 40 m box margin).
export const BASE_POIS: Poi[] = (W.pois as { x: number; z: number; n: string; c: string }[])
  .filter(p => CAT[p.c] && inBox(p.x, p.z, 40))
  .map((p, i) => ({ ...p, id: i, node: nearestNode(p.x, p.z, isPed), q: .6 + hash2(i, 7) * .8, edges: poiEdges(p.x, p.z) }));

// ───────────────────────── inlets: the only places people enter and leave ─────────────────────────
const STATIONS: Station[] = (W.stations as { name: string; c: Pt; e: Pt[] }[])
  .filter(s => ['Embarcadero', 'Montgomery Street', 'Powell Street'].includes(s.name))
  .map(s => ({ ...s, nodes: [...new Set(s.e.map(([x, z]) => nearestNode(x, z, isPed)))].filter(n => n >= 0) }));
const stationBy = (n: string) => STATIONS.find(s => s.name === n) || STATIONS[0];
const sinks = NODES.map((_, i) => i).filter(i => carIn[i].length && !carOut[i].length);
// Only the original road-end gateways: world.json now also lists every road crossing the map edge ("cross"),
// which this archived prototype doesn't use. The live engine (backend/hp) generates inlets from both.
const GATEWAYS = (W.gateways as { node: number; in: boolean; out: boolean; name: string; src?: string }[]).filter(g => g.src !== 'cross');
const gwNodes = (names: string[], dir: 'in' | 'out') => GATEWAYS.filter(g => names.includes(g.name) && g[dir]).map(g => g.node);
function exitsFor(entries: number[], names: string[]) {
  const named = gwNodes(names, 'out'); if (named.length) return named;
  const out: number[] = []; for (const en of entries) { let best = -1, bd = Infinity; for (const s of sinks) { const d = Math.hypot(NODES[s][0] - NODES[en][0], NODES[s][1] - NODES[en][1]); if (d < bd) { bd = d; best = s; } } if (best >= 0 && bd < 900) out.push(best); }
  return out.length ? [...new Set(out)] : sinks.slice(0, 1);
}
export interface Inlet { i: number; key: string; name: string; mode: 'car' | 'ped'; st?: Station; entries?: number[]; exits?: number[]; gw?: string[] }
export const INLETS: Inlet[] = ([
  { key: 'emb', name: 'Embarcadero', mode: 'ped', station: 'Embarcadero' },
  { key: 'mont', name: 'Montgomery', mode: 'ped', station: 'Montgomery Street' },
  { key: 'pow', name: 'Powell', mode: 'ped', station: 'Powell Street' },
  { key: 'i80', name: 'I-80 · Bay Bridge', mode: 'car', gw: ['I-80 · Bay Bridge'] },
  { key: 'us101', name: 'US-101', mode: 'car', gw: ['US-101 / I-80 West'] },
  { key: 'mkt', name: 'Market St (west)', mode: 'car', gw: ['Market Street'] },
  { key: 'fol', name: 'Folsom · 6th St', mode: 'car', gw: ['Folsom Street', '6th Street'] },
  { key: 'bwy', name: 'Broadway · Columbus', mode: 'car', gw: ['Broadway', 'Columbus Avenue'] },
] as { key: string; name: string; mode: 'car' | 'ped'; station?: string; gw?: string[] }[]).map((g, i) => {
  const o: Inlet = { i, key: g.key, name: g.name, mode: g.mode };
  if (g.mode === 'ped') o.st = stationBy(g.station!);
  else { o.gw = g.gw; o.entries = gwNodes(g.gw!, 'in'); o.exits = exitsFor(o.entries, g.gw!); }
  return o;
});
const inletBy = (k: string) => INLETS.find(g => g.key === k)!;
const STIN = new Map(INLETS.filter(g => g.st).map(g => [g.st!, g.i]));
interface Region { name: string; share: number; carBase: number; trBase: number; entries: number[]; exits: number[]; st: Station; carIn: number; bartIn: number }
// Each region has exactly one car inlet and one BART inlet.
export const REGIONS: Region[] = [
  { name: 'East Bay', share: .34, car: 'i80', bart: 'emb', carBase: 30, trBase: 27 },
  { name: 'Peninsula', share: .22, car: 'us101', bart: 'mont', carBase: 36, trBase: 40 },
  { name: 'Western SF', share: .22, car: 'mkt', bart: 'pow', carBase: 20, trBase: 22 },
  { name: 'Mission', share: .13, car: 'fol', bart: 'pow', carBase: 17, trBase: 18 },
  { name: 'North Beach', share: .09, car: 'bwy', bart: 'mont', carBase: 14, trBase: 19 },
].map(r => { const c = inletBy(r.car), b = inletBy(r.bart); return { name: r.name, share: r.share, carBase: r.carBase, trBase: r.trBase, entries: c.entries!, exits: c.exits!, st: b.st!, carIn: c.i, bartIn: b.i }; }).filter(r => r.entries.length);
const CAL = { cap: 330, hwcap: 1100, bpr: .15, pow: 4, max: 6 };

// ───────────────────────── population ─────────────────────────
const FIRST = ['Maria', 'Dev', 'Ana', 'James', 'Wei', 'Priya', 'Luis', 'Sam', 'Grace', 'Omar', 'Hana', 'Tom', 'Rosa', 'Kenji', 'Aisha', 'Ben', 'Lena', 'Marco', 'Nia', 'Raj', 'Elena', 'Chris', 'Mei', 'Jorge', 'Sofia', 'Andre', 'Yuki', 'Dana', 'Ivan', 'Leah'];
const LAST = ['Okafor', 'Patel', 'Nguyen', 'Garcia', 'Chen', 'Kim', 'Rossi', 'Lopez', 'Wright', 'Haddad', 'Sato', 'Murphy', 'Silva', 'Cohen', 'Diaz', 'Park', 'Reyes', 'Ali', 'Lee', 'Novak'];
function pickWeighted<T>(list: T[], wfn: (x: T) => number, r: () => number): T { let t = 0; const ws = list.map(x => { const w = wfn(x); t += w; return w; }); let u = r() * t; for (let i = 0; i < list.length; i++) { u -= ws[i]; if (u <= 0) return list[i]; } return list[list.length - 1]; }
function normal(r: () => number) { return Math.sqrt(-2 * Math.log(r() + 1e-9)) * Math.cos(2 * Math.PI * r()); }
export interface Person {
  id: number; kind: 'worker' | 'resident'; name: string; income: number; open: number; evap: number;
  // worker
  reg?: Region; office?: Building; asc?: number; eps?: number; entry?: number; exit?: number; arrive?: number; leave?: number;
  lunch?: boolean; lunchT?: number; lunchDur?: number; coffee?: boolean; coffeeT?: number;
  // resident
  home?: Building; commute?: boolean; st?: Station; out1?: number; back1?: number; errand?: boolean; errandT?: number; evening?: boolean; eveT?: number; eveDur?: number;
}
function makeWorker(id: number, r: () => number, office: Building): Person {
  const reg = pickWeighted(REGIONS, x => x.share, r);
  const income = r() < .28 ? 0 : r() < .62 ? 1 : 2;
  return {
    id, kind: 'worker', name: FIRST[Math.floor(r() * FIRST.length)] + ' ' + LAST[Math.floor(r() * LAST.length)][0] + '.',
    reg, office, income, asc: normal(r) * .9 - .2 + income * .35, eps: gumbel(r()) - gumbel(r()), evap: r(),
    entry: reg.entries[Math.floor(r() * reg.entries.length)], exit: reg.exits[Math.floor(r() * reg.exits.length)],
    arrive: clamp(510 + normal(r) * 45, 400, 640) * 60, leave: clamp(1050 + normal(r) * 55, 930, 1230) * 60,
    lunch: r() < .66, lunchT: clamp(740 + normal(r) * 24, 680, 830) * 60, lunchDur: (22 + r() * 22) * 60,
    coffee: r() < .22, coffeeT: (870 + r() * 80) * 60, open: r(),
  };
}
function makeResident(id: number, r: () => number, home: Building): Person {
  return {
    id, kind: 'resident', name: FIRST[Math.floor(r() * FIRST.length)] + ' ' + LAST[Math.floor(r() * LAST.length)][0] + '.',
    home, income: r() < .45 ? 0 : r() < .75 ? 1 : 2, open: r(), evap: r(),
    commute: r() < .5, st: STATIONS.reduce((a, s) => Math.hypot(s.c[0] - home.c[0], s.c[1] - home.c[1]) < Math.hypot(a.c[0] - home.c[0], a.c[1] - home.c[1]) ? s : a, STATIONS[0]),
    out1: clamp(450 + r() * 70, 430, 540) * 60, back1: clamp(1080 + r() * 60, 1040, 1180) * 60,
    errand: r() < .55, errandT: (540 + r() * 150) * 60, evening: r() < .6, eveT: (1110 + r() * 150) * 60, eveDur: (40 + r() * 50) * 60,
  };
}
const BASE_PERSONS: Person[] = (() => {
  const r = mulberry32(2026); const P: Person[] = [];
  for (let i = 0; i < 5200; i++) P.push(makeWorker(i, r, pickWeighted(offices, b => capOf(b.k, b.floor).jobs + 50, r)));
  for (let i = 0; i < 760; i++) P.push(makeResident(P.length, r, pickWeighted(homes, b => capOf(b.k, b.floor).res + 5, r)));
  return P;
})();
const PERSON_BY_ID = new Map(BASE_PERSONS.map(p => [p.id, p]));

// The demo's hero pair. Picked once from the baseline (see pickHeroes) and then pinned by id.
export const HERO = { name: 'Maria O.', friend: 'Dev P.', street: '2nd Street', from: 'Market Street', to: 'Folsom Street', mariaId: -1, devId: -1 };
export function applyHeroes(mariaId: number, devId: number) {
  const m = PERSON_BY_ID.get(mariaId), d = PERSON_BY_ID.get(devId);
  if (!m || !d || HERO.mariaId === mariaId) return;
  HERO.mariaId = mariaId; HERO.devId = devId;
  m.name = HERO.name; m.lunchT = 735 * 60; m.arrive = 505 * 60; m.open = .9;
  d.office = m.office; d.name = HERO.friend; d.lunch = true; d.lunchT = 738 * 60; d.open = .9;
}
export function stretch(name: string, from: string, to: string): number[] {
  const onName = EDGES.filter(e => e.name === name);
  const nodeOf = (cross: string) => { const ns = new Set(EDGES.filter(e => e.name === cross).flatMap(e => [e.a, e.b])); return onName.flatMap(e => [e.a, e.b]).find(n => ns.has(n)); };
  const a = nodeOf(from), b = nodeOf(to); if (a === undefined || b === undefined) return [];
  const adj = new Map<number, [number, number][]>(); for (const e of onName) { for (const [u, v] of [[e.a, e.b], [e.b, e.a]]) { if (!adj.has(u)) adj.set(u, []); adj.get(u)!.push([v, e.id]); } }
  const prev = new Map<number, [number, number] | null>([[a, null]]); const q = [a];
  while (q.length) { const u = q.shift()!; if (u === b) break; for (const [v, eid] of adj.get(u) || []) if (!prev.has(v)) { prev.set(v, [u, eid]); q.push(v); } }
  const out: number[] = []; let v = b; while (prev.get(v)) { const [u, eid] = prev.get(v)!; out.push(eid); v = u; } return out;
}
export const HERO_EDGES = stretch(HERO.street, HERO.from, HERO.to);
// Maria drives in over the Bay Bridge to an office near 2nd & Howard and her baseline route uses 2nd St.
export function pickHeroes(base: SettleResult): { mariaId: number; devId: number } {
  const hx = EDGES[HERO_EDGES[Math.floor(HERO_EDGES.length / 2)] ?? 0];
  const mx = hx.p[Math.floor(hx.p.length / 2)][0], mz = hx.p[Math.floor(hx.p.length / 2)][1];
  let best: Person | null = null, bd = Infinity;
  for (const p of BASE_PERSONS) {
    if (p.kind !== 'worker' || p.reg!.name !== 'East Bay' || base.modes.get(p.id) !== 'car' || !p.lunch) continue;
    const r = base.carRoutes.get(p.id) || []; const uses = r.some(e => HERO_EDGES.includes(e));
    const d = Math.hypot(p.office!.c[0] - mx, p.office!.c[1] - mz) - (uses ? 400 : 0); if (d < bd) { bd = d; best = p; }
  }
  if (!best) best = BASE_PERSONS.find(p => p.kind === 'worker')!;
  const dev = BASE_PERSONS.find(p => p.kind === 'worker' && p !== best && p.office === best!.office) || BASE_PERSONS.find(p => p.kind === 'worker' && p !== best)!;
  return { mariaId: best.id, devId: dev.id };
}

// ───────────────────────── scenario inputs ─────────────────────────
export interface BlockEdit { scale: number; zone: string }
export interface Policy { kind: string; target: string; amount: number }
export interface Edits { isPlan: boolean; ped: Set<number>; blocks: Map<number, BlockEdit>; policies: Policy[] }
// Value of time used to turn $ into utility: 0.06 utils/min at ~$19.6/hr => 0.18 utils per $.
const UTIL_PER_DOLLAR = .06 / (19.6 / 60);
// Policy kinds the engine understands. New kinds land here (the Droid policy compiler targets this).
function carCharge(p: Person, policies: Policy[]) {
  let c = 0;
  for (const q of policies) {
    if (q.kind === 'congestion_charge' && (!q.target || q.target === INLETS[p.reg!.carIn].key) && p.arrive! >= 420 * 60 && p.arrive! <= 600 * 60) c += q.amount;
    if (q.kind === 'parking_price') c += q.amount;
  }
  return c;
}

// Cached per-scenario context: population, POIs and shortest-path trees. Rebuilt when edits change.
class Ctx {
  persons: Person[] = []; pois: Poi[] = []; poiGrid: PoiGrid = new Map(); pedPoiBonus = new Set<number>();
  cong: Float32Array; cache = new Map<string, Tree>();
  constructor(public edits: Edits, cong?: Float32Array) { this.cong = cong ? Float32Array.from(cong) : new Float32Array(EDGES.length).fill(1); this.buildPopulation(); }
  carCost = (a: Arc) => this.edits.ped.has(a.e) ? Infinity : EDGES[a.e].l / SPEED[EDGES[a.e].c] * this.cong[a.e];
  pedCost = (a: Arc) => { const e = EDGES[a.e]; let m = this.edits.ped.has(a.e) ? .7 : 1; if (e.c === 'primary' || e.c === 'secondary') m *= 1.12; if (e.c === 'pedestrian') m *= .85; return e.l / 1.35 * m; };
  tree(kind: 'car' | 'carRev' | 'ped', key: string | number, sources: number[]) {
    const k = kind + ':' + key; let t = this.cache.get(k); if (t) return t;
    if (kind === 'car') t = dijkstra(sources, carOut, arcs, this.carCost, false);
    else if (kind === 'carRev') t = dijkstra(sources, carIn, arcs, this.carCost, true);
    else t = dijkstra(sources, pedOut, pedArcs, this.pedCost, false);
    this.cache.set(k, t); return t;
  }
  clearCarTrees() { for (const k of [...this.cache.keys()]) if (k.startsWith('car')) this.cache.delete(k); }
  pedTreeFrom(node: number) { return this.tree('ped', node, [node]); }
  stationTree(st: Station) { return this.tree('ped', 'st' + st.name, st.nodes); }
  // Persons and POIs: base pool plus anything the block edits add or remove.
  buildPopulation() {
    const P: Person[] = []; const removedJobs = new Map<number, number>(); const extra: Person[] = [];
    this.pois = BASE_POIS.slice();
    for (const [bid, ed] of this.edits.blocks) {
      const b = BLD[bid]; const z = ed.zone || b.k; const before = capOf(b.k, b.floor), after = capOf(z, b.floor * ed.scale);
      const dJobs = after.jobs - before.jobs, dRes = after.res - before.res; const r = mulberry32(bid * 31 + 7);
      if (dJobs < 0) removedJobs.set(bid, Math.min(1, -dJobs / Math.max(before.jobs, 1) * .65)); // vacant floors convert first
      for (let i = 0; i < Math.min(160, Math.round(Math.max(0, dJobs) / SCALE)); i++) extra.push(makeWorker(100000 + bid * 400 + i, r, b));
      for (let i = 0; i < Math.min(120, Math.round(Math.max(0, dRes) / SCALE)); i++) extra.push(makeResident(200000 + bid * 400 + i, r, b));
      if ((z === 'retail' || z === 'mixed') && z !== b.k) {
        const n = clamp(Math.round(Math.sqrt(b.area) / 14), 1, 4);
        for (let i = 0; i < n; i++) { const c = ['cafe', 'restaurant', 'shop', 'fast_food'][i % 4]; const x = b.c[0] + (i - n / 2) * 8, zz = b.c[1] + 6; this.pois.push({ x, z: zz, n: 'New ' + CAT[c].label.toLowerCase(), c, id: 5000 + bid * 5 + i, q: 1.1, virtual: true, node: nearestNode(x, zz, isPed), edges: poiEdges(x, zz) }); }
      }
    }
    for (const p of BASE_PERSONS) { if (p.kind === 'worker' && removedJobs.has(p.office!.id) && hash2(p.id, 3) < removedJobs.get(p.office!.id)!) continue; P.push(p); }
    this.persons = P.concat(extra); this.poiGrid = indexPois(this.pois);
    this.pedPoiBonus = new Set(); for (const p of this.pois) if (p.edges.some(e => this.edits.ped.has(e))) this.pedPoiBonus.add(p.id);
  }
  lunchSpot(p: Person, at: Building, t: number) {
    const cands = poisNear(this.poiGrid, at.c[0], at.c[1], 560).filter(q => CAT[q.c].lunch > 0 && q.node >= 0);
    let best: Poi | null = null, bu = -Infinity;
    for (const q of cands) { const d = Math.hypot(q.x - at.c[0], q.z - at.c[1]); const u = Math.log(CAT[q.c].lunch * q.q) - d / 170 + (this.pedPoiBonus.has(q.id) ? 1.0 : 0) + gumbel(hash2(p.id * 7 + t, q.id)); if (u > bu) { bu = u; best = q; } }
    return best;
  }
  modeOf(p: Person, baseRoute: number[] | undefined): Mode {
    if (p.kind !== 'worker') return 'transit';
    const tc = this.tree('car', p.entry!, [p.entry!]).dist[p.office!.carNode];
    const tw = this.stationTree(p.reg!.st).dist[p.office!.pedNode];
    if (tc === Infinity) return 'transit';
    const uCar = p.asc! - .06 * (p.reg!.carBase + tc / 60) - 1.95 - UTIL_PER_DOLLAR * carCharge(p, this.edits.policies);
    const uTr = -.06 * (p.reg!.trBase + 1.6 * tw / 60);
    let mode: Mode = uCar + p.eps! > uTr ? 'car' : 'transit';
    if (this.edits.isPlan && p.id === HERO.mariaId && this.edits.ped.size) mode = 'transit';
    // Traffic evaporation: some drivers whose old route is now closed change mode or skip the trip.
    if (this.edits.isPlan && mode === 'car' && baseRoute && baseRoute.some(e => this.edits.ped.has(e))) { if (p.evap < .03) return 'gone'; if (p.evap < .16) return 'transit'; }
    return mode;
  }
}
export type Mode = 'car' | 'transit' | 'gone';

// ───────────────────────── settle loop ─────────────────────────
export interface DayResult { cong: Float32Array; modes: Map<number, Mode>; carRoutes: Map<number, number[]>; carFlow: Float32Array }
// One "replanning day": choose modes and routes given the previous day's congestion.
export function replanDay(edits: Edits, cong: Float32Array | null, baseCarRoutes: Map<number, number[]> | null, ctx?: Ctx): DayResult {
  const c = ctx || new Ctx(edits, cong || undefined);
  c.clearCarTrees();
  const flow = new Float32Array(EDGES.length); const modes = new Map<number, Mode>(); const carRoutes = new Map<number, number[]>();
  for (const p of c.persons) {
    const m = c.modeOf(p, baseCarRoutes?.get(p.id)); modes.set(p.id, m);
    if (m !== 'car') continue;
    const path = treePath(c.tree('car', p.entry!, [p.entry!]), p.office!.carNode); if (!path) { modes.set(p.id, 'transit'); continue; }
    const edges = path.map(a => arcs[a].e); carRoutes.set(p.id, edges);
    for (const e of edges) flow[e] += 1;
  }
  for (let i = 0; i < EDGES.length; i++) { const e = EDGES[i]; if (!e.car) continue; const vph = flow[i] * SCALE / 2.2; const cap = e.lanes * (e.hw ? CAL.hwcap : CAL.cap); const f = 1 + CAL.bpr * Math.pow(vph / cap, CAL.pow); c.cong[i] = lerp(c.cong[i], Math.min(f, CAL.max), .6); }
  return { cong: c.cong, modes, carRoutes, carFlow: flow };
}

export const LEGS = ['am', 'pm', 'lunch', 'lunch2', 'coffee', 'coffee2', 'out', 'home', 'err', 'err2', 'eve', 'eve2'] as const;
export type Leg = typeof LEGS[number];
export interface Trip {
  personId: number; leg: Leg; mode: 'car' | 'ped'; t0: number; dur: number; len: number;
  // Each step is edgeId * 2 + (1 if walked b→a, else 0). The viewer rebuilds geometry from world.json.
  steps: number[]; trimHead: number; trimTail: number;
  poiId: number; dwell: number; inlet: number; outlet: number;
}
function makeTrip(p: Person, leg: Leg, t0: number, mode: 'car' | 'ped', path: number[] | null, arcList: Arc[], speed: number, poi: Poi | null, dwell: number, cong: Float32Array | null, reversed = false): Trip | null {
  if (!path || !path.length) return null;
  const pts: Pt[] = []; const steps: number[] = []; const edges: number[] = [];
  for (const ai of path) { const a = arcList[ai]; const e = EDGES[a.e]; const back = reversed ? !a.rev : a.rev; const pp = back ? e.p.slice().reverse() : e.p; edges.push(e.id); steps.push(e.id * 2 + (back ? 1 : 0));
    for (let j = 0; j < pp.length; j++) { if (pts.length && j === 0) continue; pts.push(pp[j]); } }
  // Cars enter and leave on long highway ramps; trim the far ends so they appear near the map.
  let trimHead = 0, trimTail = 0;
  if (mode === 'car') { const far = (q: Pt) => Math.hypot(q[0], q[1]) > 1450; while (pts.length - trimHead - trimTail > 2 && far(pts[trimHead]) && far(pts[trimHead + 1])) trimHead++; while (pts.length - trimHead - trimTail > 2 && far(pts[pts.length - 1 - trimTail]) && far(pts[pts.length - 2 - trimTail])) trimTail++; }
  const kept = pts.slice(trimHead, pts.length - trimTail);
  if (kept.length < 2) return null;
  let len = 0; for (let i = 1; i < kept.length; i++) len += Math.hypot(kept[i][0] - kept[i - 1][0], kept[i][1] - kept[i - 1][1]);
  let v = speed;
  if (mode === 'car') { let tt = 0; for (const id of edges) { const e = EDGES[id]; tt += e.l / SPEED[e.c] * (cong ? cong[id] : 1); } v = len / Math.max(tt, 1); }
  return { personId: p.id, leg, mode, t0, dur: len / v, len, steps, trimHead, trimTail, poiId: poi ? poi.id : -1, dwell: dwell || 0, inlet: -1, outlet: -1 };
}

export interface Metrics {
  car: number; transit: number; gone: number; vmt: number; vehH: number; delayH: number; walkMin: number; revenue: number;
  encounters: number; ties: number; jobs: number; residents: number; floorDelta: number; persons: number;
  tierTime: number[]; tierWalk: number[];
}
export interface SettleResult extends DayResult {
  persons: Person[]; pois: Poi[]; trips: Trip[]; lunchAt: Map<number, Poi>;
  pedFlow: Float32Array; visits: Map<number, number>; tiePairs: [number, number, number][]; metrics: Metrics;
}

// Turn the settled plans into timed trips, then daily projections.
export function finalize(edits: Edits, day: DayResult, ctx?: Ctx): SettleResult {
  const c = ctx || new Ctx(edits, day.cong);
  const T: Trip[] = []; const lunchAt = new Map<number, Poi>();
  const push = (tr: Trip | null, inlet = -1, outlet = -1) => { if (!tr) return null; tr.inlet = inlet; tr.outlet = outlet; T.push(tr); return tr; };
  for (const p of c.persons) {
    const m = day.modes.get(p.id); if (m === 'gone' || m === undefined) continue;
    if (p.kind === 'worker') {
      const o = p.office!;
      if (m === 'car') {
        const path = treePath(c.tree('car', p.entry!, [p.entry!]), o.carNode); push(path && makeTrip(p, 'am', p.arrive! - 600, 'car', path, arcs, 0, null, 0, c.cong), p.reg!.carIn);
        const pm = treePath(c.tree('carRev', p.exit!, [p.exit!]), o.carNode); push(pm && makeTrip(p, 'pm', p.leave!, 'car', pm, arcs, 0, null, 0, c.cong), -1, p.reg!.carIn);
      } else {
        const path = treePath(c.stationTree(p.reg!.st), o.pedNode);
        if (path) { push(makeTrip(p, 'am', p.arrive! - 500, 'ped', path, pedArcs, 1.35, null, 0, null), p.reg!.bartIn); push(makeTrip(p, 'pm', p.leave!, 'ped', path.slice().reverse(), pedArcs, 1.35, null, 0, null, true), -1, p.reg!.bartIn); }
      }
      if (p.lunch) { const q = c.lunchSpot(p, o, 1); if (q) { lunchAt.set(p.id, q); const path = treePath(c.pedTreeFrom(q.node), o.pedNode); if (path && path.length) { const out = push(makeTrip(p, 'lunch', p.lunchT!, 'ped', path.slice().reverse(), pedArcs, 1.35, q, p.lunchDur!, null, true)); if (out) push(makeTrip(p, 'lunch2', p.lunchT! + out.dur + p.lunchDur!, 'ped', path, pedArcs, 1.35, null, 0, null)); } } }
      if (p.coffee) { const q = c.lunchSpot(p, o, 2); if (q && q.c === 'cafe') { const path = treePath(c.pedTreeFrom(q.node), o.pedNode); if (path && path.length) { const out = push(makeTrip(p, 'coffee', p.coffeeT!, 'ped', path.slice().reverse(), pedArcs, 1.35, q, 600, null, true)); if (out) push(makeTrip(p, 'coffee2', p.coffeeT! + out.dur + 600, 'ped', path, pedArcs, 1.35, null, 0, null)); } } }
    } else {
      const h = p.home!; const sIn = STIN.get(p.st!) ?? -1;
      if (p.commute) { const path = treePath(c.stationTree(p.st!), h.pedNode); if (path && path.length) { push(makeTrip(p, 'out', p.out1!, 'ped', path.slice().reverse(), pedArcs, 1.35, null, 0, null, true), -1, sIn); push(makeTrip(p, 'home', p.back1!, 'ped', path, pedArcs, 1.35, null, 0, null), sIn); } }
      const outing = (t: number, dur: number, tag: 'err' | 'eve') => { const q = c.lunchSpot(p, h, tag === 'eve' ? 3 : 4); if (!q) return; const path = treePath(c.pedTreeFrom(q.node), h.pedNode); if (!path || !path.length) return; const out = push(makeTrip(p, tag, t, 'ped', path.slice().reverse(), pedArcs, 1.35, q, dur, null, true)); if (out) push(makeTrip(p, (tag + '2') as Leg, t + out.dur + dur, 'ped', path, pedArcs, 1.35, null, 0, null)); if (tag === 'eve') lunchAt.set(p.id + 1e7, q); };
      if (p.errand) outing(p.errandT!, 900, 'err'); if (p.evening) outing(p.eveT!, p.eveDur!, 'eve');
    }
  }
  T.sort((a, b) => a.t0 - b.t0);

  // Daily projections that feed the metrics, radar and City Value.
  const pedFlow = new Float32Array(EDGES.length); let vmt = 0, vehH = 0, freeH = 0, walkM = 0, car = 0, tr = 0, gone = 0;
  const tierTime = [0, 0, 0], tierWalk = [0, 0, 0], tierN = [0, 0, 0];
  const pmap = new Map(c.persons.map(p => [p.id, p]));
  for (const p of c.persons) { const m = day.modes.get(p.id); tierN[p.income]++; if (m === 'car') car++; else if (m === 'gone') gone++; else if (p.kind === 'worker') tr++; }
  for (const t of T) {
    const inc = pmap.get(t.personId)!.income;
    if (t.mode === 'car') { let tt = 0, ff = 0; for (const s of t.steps) { const id = s >> 1; const E = EDGES[id]; const f = E.l / SPEED[E.c]; ff += f; tt += f * c.cong[id]; } vmt += t.len / 1609; vehH += tt / 3600; freeH += ff / 3600; tierTime[inc] += tt / 60; }
    else { for (const s of t.steps) pedFlow[s >> 1]++; walkM += t.len / 80; tierWalk[inc] += t.len / 80; tierTime[inc] += t.len / 80; }
  }
  // Transit riders' in-vehicle time (outside the map) counts in the time budget.
  for (const p of c.persons) { const m = day.modes.get(p.id); if (p.kind === 'worker' && m === 'transit') tierTime[p.income] += p.reg!.trBase * 2; else if (p.kind === 'worker' && m === 'car') tierTime[p.income] += p.reg!.carBase * 2; }
  const visits = new Map<number, number>(); let revenue = 0;
  for (const q of c.pois) { let exp = 0; for (const e of q.edges) exp += pedFlow[e]; visits.set(q.id, exp * CAT[q.c].capture * q.q * (c.pedPoiBonus.has(q.id) ? 1.35 : 1)); }
  for (const [, q] of lunchAt) visits.set(q.id, (visits.get(q.id) || 0) + 1);
  for (const q of c.pois) { const v = (visits.get(q.id) || 0) * SCALE; visits.set(q.id, v); revenue += v * CAT[q.c].ticket; }
  // Encounters: people whose lunch or outing overlaps at the same place; ties form among coworkers and open people.
  const byPoi = new Map<number, number[]>(); for (const [pid, q] of lunchAt) { if (!byPoi.has(q.id)) byPoi.set(q.id, []); byPoi.get(q.id)!.push(pid); }
  let enc = 0, ties = 0; const tiePairs: [number, number, number][] = [];
  const when = (p: Person) => p.lunchT || p.eveT || 0;
  for (const [qid, ids] of byPoi) {
    const arr = ids.map(id => pmap.get(id % 1e7)).filter((p): p is Person => !!p).sort((a, b) => when(a) - when(b));
    for (let i = 0; i < arr.length; i++) for (let j = i + 1; j < arr.length; j++) {
      if (when(arr[j]) - when(arr[i]) > 1500) break; enc++;
      const same = arr[i].office && arr[i].office === arr[j].office; if (same || (arr[i].open > .72 && arr[j].open > .72)) { ties++; if (tiePairs.length < 900) tiePairs.push([arr[i].id, arr[j].id, qid]); }
    }
  }
  let streetEnc = 0; for (const e of edits.ped) streetEnc += pedFlow[e] * .06;
  let jobs = 0, res = 0, floorDelta = 0;
  for (const b of BLD) { if (!b.inside) continue; const ed = edits.blocks.get(b.id); const cc = ed ? capOf(ed.zone || b.k, b.floor * ed.scale) : capOf(b.k, b.floor); jobs += cc.jobs; res += cc.res; if (ed) floorDelta += b.floor * (ed.scale - 1); }
  const metrics: Metrics = { car, transit: tr, gone, vmt: vmt * SCALE, vehH: vehH * SCALE, delayH: (vehH - freeH) * SCALE, walkMin: walkM * SCALE, revenue,
    encounters: (enc + streetEnc) * SCALE, ties: ties * SCALE, jobs, residents: res, floorDelta, persons: c.persons.length,
    tierTime: tierTime.map((t, i) => t / Math.max(1, tierN[i])), tierWalk: tierWalk.map((t, i) => t / Math.max(1, tierN[i])) };
  return { ...day, persons: c.persons, pois: c.pois, trips: T, lunchAt, pedFlow, visits, tiePairs, metrics };
}

// Whole settle in one call (init, tests). Edits use the scheduled per-day path instead.
export function settleAll(edits: Edits, baseCarRoutes: Map<number, number[]> | null, days = SETTLE_DAYS): SettleResult {
  const ctx = new Ctx(edits);
  let day: DayResult | null = null;
  for (let d = 0; d < days; d++) day = replanDay(edits, null, baseCarRoutes, ctx);
  return finalize(edits, day!, ctx);
}

// ───────────────────────── City Value ($/yr vs baseline) ─────────────────────────
const VALUE = { vtt: 19.6, voc: .62, tie: 9, encounter: .1, va: .35, propTax: 11, healthPerMin: 25.1 };
export function cityValue(b: Metrics, p: Metrics) {
  const mobility = (-(p.delayH - b.delayH) * VALUE.vtt - (p.vmt - b.vmt) * VALUE.voc) * WORKDAYS;
  const social = ((p.ties - b.ties) * VALUE.tie + (p.encounters - b.encounters) * VALUE.encounter) * WORKDAYS;
  const economy = (p.revenue - b.revenue) * VALUE.va * WORKDAYS + p.floorDelta * VALUE.propTax * .15;
  const health = (p.walkMin - b.walkMin) * VALUE.healthPerMin;
  return { mobility, social, economy, health, total: mobility + social + economy + health };
}

// ───────────────────────── validation helpers for reducers ─────────────────────────
export const canPedestrianize = (edgeId: number) => edgeId >= 0 && edgeId < EDGES.length && EDGES[edgeId].car && !EDGES[edgeId].hw;
export const canEditBuilding = (bid: number) => bid >= 0 && bid < BLD.length && BLD[bid].inside;
export const personInfo = (id: number) => PERSON_BY_ID.get(id);
export const NUM_EDGES = EDGES.length;
