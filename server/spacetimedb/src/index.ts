// Reducers for The Human Project. Edits mark a scenario dirty and schedule the settle loop;
// each scheduled run is one MATSim-style replanning day, so every client watches the city re-settle.
import { SenderError, t, type InferSchema, type ReducerCtx } from 'spacetimedb/server';
import { ScheduleAt } from 'spacetimedb';
import spacetimedb, { settleJob } from './schema';
import {
  BASE_POIS, HERO, HERO_EDGES, INLETS, LEGS, SCALE, SETTLE_DAYS, ZONES,
  applyHeroes, canEditBuilding, canPedestrianize, cityValue, finalize, pickHeroes, replanDay, settleAll,
  EDGES, type Edits, type Metrics, type SettleResult,
} from './engine';

export default spacetimedb;
type Ctx = ReducerCtx<InferSchema<typeof spacetimedb>>;

const BASELINE = 1;
const PLAN_A = 2;
const DEBOUNCE_US = 250_000n; // wait for a paint stroke to finish before replanning
const DAY_GAP_US = 120_000n;  // pause between replanning days so viewers see progress
const COLORS = ['#ffb547', '#4fc3f7', '#ff6b9d', '#9ccc65', '#ba68c8', '#ffd54f', '#4db6ac', '#f06292'];

const key = (scenarioId: number, n: number) => (BigInt(scenarioId) << 32n) | BigInt(n);
const after = (ctx: Ctx, us: bigint) => ScheduleAt.time(ctx.timestamp.microsSinceUnixEpoch + us);

// Module globals reset whenever the host starts a fresh instance, so re-pin the heroes lazily.
function ensureHeroes(ctx: Ctx) {
  const meta = ctx.db.worldMeta.id.find(0);
  if (meta) applyHeroes(meta.mariaId, meta.devId);
}

function editsOf(ctx: Ctx, scenarioId: number): Edits {
  const sc = ctx.db.scenario.id.find(scenarioId);
  const ped = new Set<number>();
  for (const e of ctx.db.streetEdit.scenarioId.filter(scenarioId)) ped.add(e.edgeId);
  const blocks = new Map<number, { scale: number; zone: string }>();
  for (const b of ctx.db.blockEdit.scenarioId.filter(scenarioId)) blocks.set(b.buildingId, { scale: b.scale, zone: b.zone });
  const policies = [...ctx.db.policy.scenarioId.filter(scenarioId)].map(p => ({ kind: p.kind, target: p.target, amount: p.amount }));
  return { isPlan: !!sc?.isPlan, ped, blocks, policies };
}

// Baseline car routes drive traffic evaporation in plans: drivers whose old route is closed may switch or skip.
let baseRoutesCache: { version: number; routes: Map<number, number[]> } | null = null;
function baseCarRoutes(ctx: Ctx) {
  const base = ctx.db.scenario.id.find(BASELINE);
  const version = base?.settledVersion ?? 0;
  if (baseRoutesCache && baseRoutesCache.version === version) return baseRoutesCache.routes;
  const routes = new Map<number, number[]>();
  for (const tr of ctx.db.trip.scenarioId.filter(BASELINE)) if (tr.mode === 'car' && tr.leg === 'am') routes.set(tr.personId, tr.steps.map(s => s >> 1));
  baseRoutesCache = { version, routes };
  return routes;
}

function playerName(ctx: Ctx) {
  return ctx.db.player.identity.find(ctx.sender)?.name ?? 'Someone';
}
function logActivity(ctx: Ctx, scenarioId: number, text: string) {
  ctx.db.activity.insert({ id: 0n, scenarioId, who: playerName(ctx), text, at: ctx.timestamp });
}
function requirePlan(ctx: Ctx, scenarioId: number) {
  const sc = ctx.db.scenario.id.find(scenarioId);
  if (!sc) throw new SenderError(`no scenario ${scenarioId}`);
  if (!sc.isPlan) throw new SenderError('the baseline is locked; edit a plan instead');
  return sc;
}

// Mark the scenario dirty and make sure a settle job is queued. A running job notices the new
// editVersion and restarts from day 0, so rapid edits collapse into one settle.
function requestSettle(ctx: Ctx, scenarioId: number) {
  const sc = ctx.db.scenario.id.find(scenarioId)!;
  const editVersion = sc.editVersion + 1;
  ctx.db.scenario.id.update({ ...sc, editVersion, status: 'settling', day: 0, updatedAt: ctx.timestamp });
  const pending = [...ctx.db.settleJob.scenarioId.filter(scenarioId)];
  if (!pending.length) ctx.db.settleJob.insert({ scheduledId: 0n, scheduledAt: after(ctx, DEBOUNCE_US), scenarioId, editVersion, day: 0, cong: [] });
}

// ───────────────────────── writing results (diffed, so subscribers get small updates) ─────────────────────────
function writeResult(ctx: Ctx, scenarioId: number, r: SettleResult) {
  const m = r.metrics;
  const base = scenarioId === BASELINE ? m : metricsOf(ctx, BASELINE) ?? m;
  const v = scenarioId === BASELINE ? { mobility: 0, social: 0, economy: 0, health: 0, total: 0 } : cityValue(base, m);
  const row = {
    scenarioId, persons: m.persons, car: m.car, transit: m.transit, gone: m.gone, vmt: m.vmt, vehH: m.vehH, delayH: m.delayH,
    walkMin: m.walkMin, revenue: m.revenue, encounters: m.encounters, ties: m.ties, jobs: m.jobs, residents: m.residents,
    floorDelta: m.floorDelta, tierTime: m.tierTime, tierWalk: m.tierWalk,
    valueMobility: v.mobility, valueSocial: v.social, valueEconomy: v.economy, valueHealth: v.health, valueTotal: v.total,
    updatedAt: ctx.timestamp,
  };
  if (ctx.db.metrics.scenarioId.find(scenarioId)) ctx.db.metrics.scenarioId.update(row); else ctx.db.metrics.insert(row);

  const flow = { scenarioId, carFlow: [...r.carFlow], pedFlow: [...r.pedFlow], cong: [...r.cong] };
  if (ctx.db.edgeFlow.scenarioId.find(scenarioId)) ctx.db.edgeFlow.scenarioId.update(flow); else ctx.db.edgeFlow.insert(flow);

  const visits = { scenarioId, visits: BASE_POIS.map(q => r.visits.get(q.id) ?? 0) };
  if (ctx.db.poiVisits.scenarioId.find(scenarioId)) ctx.db.poiVisits.scenarioId.update(visits); else ctx.db.poiVisits.insert(visits);
  for (const old of [...ctx.db.virtualPoi.scenarioId.filter(scenarioId)]) ctx.db.virtualPoi.id.delete(old.id);
  for (const q of r.pois) if (q.virtual) ctx.db.virtualPoi.insert({ id: key(scenarioId, q.id), scenarioId, poiId: q.id, name: q.n, category: q.c, x: q.x, z: q.z, visits: r.visits.get(q.id) ?? 0 });

  // Sims
  const oldSims = new Map([...ctx.db.sim.scenarioId.filter(scenarioId)].map(s => [s.id, s]));
  for (const p of r.persons) {
    const id = key(scenarioId, p.id);
    const s = {
      id, scenarioId, personId: p.id, name: p.name, kind: p.kind, income: p.income,
      region: p.reg?.name ?? 'Resident', mode: r.modes.get(p.id) ?? 'transit',
      homeBuilding: p.home?.id ?? -1, officeBuilding: p.office?.id ?? -1, lunchPoi: r.lunchAt.get(p.id)?.id ?? -1,
    };
    const o = oldSims.get(id); oldSims.delete(id);
    if (!o) ctx.db.sim.insert(s);
    else if (o.mode !== s.mode || o.lunchPoi !== s.lunchPoi || o.name !== s.name || o.officeBuilding !== s.officeBuilding) ctx.db.sim.id.update(s);
  }
  for (const id of oldSims.keys()) ctx.db.sim.id.delete(id);

  // Trips
  const oldTrips = new Map([...ctx.db.trip.scenarioId.filter(scenarioId)].map(tr => [tr.id, tr]));
  for (const tr of r.trips) {
    const id = key(scenarioId, tr.personId * 16 + LEGS.indexOf(tr.leg));
    const row = { id, scenarioId, personId: tr.personId, leg: tr.leg, mode: tr.mode, t0: tr.t0, dur: tr.dur, len: tr.len, steps: tr.steps,
      trimHead: tr.trimHead, trimTail: tr.trimTail, poiId: tr.poiId, dwell: tr.dwell, inlet: tr.inlet, outlet: tr.outlet };
    const o = oldTrips.get(id); oldTrips.delete(id);
    if (!o) { ctx.db.trip.insert(row); continue; }
    const changed = o.mode !== row.mode || Math.abs(o.t0 - row.t0) > 1 || Math.abs(o.dur - row.dur) > Math.max(2, o.dur * .02) ||
      o.poiId !== row.poiId || o.steps.length !== row.steps.length || o.steps.some((s, i) => s !== row.steps[i]);
    if (changed) ctx.db.trip.id.update(row);
  }
  for (const id of oldTrips.keys()) ctx.db.trip.id.delete(id);

  // Ties (small capped sample, rewritten in place)
  const oldTies = new Set([...ctx.db.tie.scenarioId.filter(scenarioId)].map(x => x.id));
  r.tiePairs.forEach(([a, b, poiId], i) => {
    const id = key(scenarioId, i); const row = { id, scenarioId, a, b, poiId };
    if (oldTies.delete(id)) ctx.db.tie.id.update(row); else ctx.db.tie.insert(row);
  });
  for (const id of oldTies) ctx.db.tie.id.delete(id);
}

function metricsOf(ctx: Ctx, scenarioId: number): Metrics | null {
  const m = ctx.db.metrics.scenarioId.find(scenarioId);
  if (!m) return null;
  return { car: m.car, transit: m.transit, gone: m.gone, vmt: m.vmt, vehH: m.vehH, delayH: m.delayH, walkMin: m.walkMin, revenue: m.revenue,
    encounters: m.encounters, ties: m.ties, jobs: m.jobs, residents: m.residents, floorDelta: m.floorDelta, persons: m.persons,
    tierTime: m.tierTime, tierWalk: m.tierWalk };
}

function markReady(ctx: Ctx, scenarioId: number, editVersion: number) {
  const sc = ctx.db.scenario.id.find(scenarioId)!;
  ctx.db.scenario.id.update({ ...sc, status: 'ready', day: SETTLE_DAYS, settledVersion: editVersion, updatedAt: ctx.timestamp });
}

// ───────────────────────── lifecycle ─────────────────────────
export const init = spacetimedb.init(ctx => {
  const now = ctx.timestamp;
  ctx.db.scenario.insert({ id: BASELINE, name: 'Baseline', isPlan: false, status: 'settling', day: 0, editVersion: 1, settledVersion: 0, updatedAt: now });
  ctx.db.scenario.insert({ id: PLAN_A, name: 'Plan A', isPlan: true, status: 'settling', day: 0, editVersion: 1, settledVersion: 0, updatedAt: now });
  const empty = (isPlan: boolean): Edits => ({ isPlan, ped: new Set(), blocks: new Map(), policies: [] });
  // Pick the demo heroes from a first baseline run, pin them, then settle for real.
  const heroes = pickHeroes(settleAll(empty(false), null));
  applyHeroes(heroes.mariaId, heroes.devId);
  ctx.db.worldMeta.insert({ id: 0, scale: SCALE, mariaId: heroes.mariaId, devId: heroes.devId, heroEdges: HERO_EDGES });
  const base = settleAll(empty(false), null);
  writeResult(ctx, BASELINE, base);
  markReady(ctx, BASELINE, 1);
  // An untouched plan equals the baseline.
  writeResult(ctx, PLAN_A, base);
  markReady(ctx, PLAN_A, 1);
  console.info(`init: ${base.persons.length} sims, ${base.trips.length} trips, maria=${heroes.mariaId}`);
});

export const onConnect = spacetimedb.clientConnected(ctx => {
  const p = ctx.db.player.identity.find(ctx.sender);
  if (p) { ctx.db.player.identity.update({ ...p, online: true, lastSeen: ctx.timestamp }); return; }
  const n = [...ctx.db.player.iter()].length;
  ctx.db.player.insert({ identity: ctx.sender, name: `Planner ${n + 1}`, color: COLORS[n % COLORS.length], online: true, scenarioId: PLAN_A, cursorX: 0, cursorZ: 0, lastSeen: ctx.timestamp });
});

export const onDisconnect = spacetimedb.clientDisconnected(ctx => {
  const p = ctx.db.player.identity.find(ctx.sender);
  if (p) ctx.db.player.identity.update({ ...p, online: false, lastSeen: ctx.timestamp });
});

// ───────────────────────── settle loop (scheduled) ─────────────────────────
export const settleStep = spacetimedb.reducer({ onSchedule: settleJob }, { job: settleJob.rowType }, (ctx, { job }) => {
  const sc = ctx.db.scenario.id.find(job.scenarioId);
  if (!sc) return;
  ensureHeroes(ctx);
  // Edited again mid-settle: start over from day 0 with the newest edits.
  const restart = job.editVersion !== sc.editVersion;
  const day = restart ? 0 : job.day;
  const edits = editsOf(ctx, sc.id);
  const routes = sc.isPlan ? baseCarRoutes(ctx) : null;
  const res = replanDay(edits, restart || !job.cong.length ? null : Float32Array.from(job.cong), routes);
  if (day + 1 < SETTLE_DAYS) {
    ctx.db.scenario.id.update({ ...sc, status: 'settling', day: day + 1, updatedAt: ctx.timestamp });
    ctx.db.settleJob.insert({ scheduledId: 0n, scheduledAt: after(ctx, DAY_GAP_US), scenarioId: sc.id, editVersion: sc.editVersion, day: day + 1, cong: [...res.cong] });
    return;
  }
  writeResult(ctx, sc.id, finalize(edits, res));
  markReady(ctx, sc.id, sc.editVersion);
});

// Force a settle (e.g. after a hot-swapped engine change).
export const settleNow = spacetimedb.reducer({ scenarioId: t.u32() }, (ctx, { scenarioId }) => {
  if (!ctx.db.scenario.id.find(scenarioId)) throw new SenderError(`no scenario ${scenarioId}`);
  requestSettle(ctx, scenarioId);
});

// ───────────────────────── edits ─────────────────────────
export const setPedestrian = spacetimedb.reducer(
  { scenarioId: t.u32(), edgeIds: t.array(t.u32()), on: t.bool() },
  (ctx, { scenarioId, edgeIds, on }) => {
    requirePlan(ctx, scenarioId);
    const ids = [...new Set(edgeIds)].filter(canPedestrianize);
    if (!ids.length) throw new SenderError('no editable streets in that selection (highways cannot be closed)');
    let changed = 0;
    for (const edgeId of ids) {
      const id = key(scenarioId, edgeId); const exists = ctx.db.streetEdit.id.find(id);
      if (on && !exists) { ctx.db.streetEdit.insert({ id, scenarioId, edgeId, author: ctx.sender, authorName: playerName(ctx), at: ctx.timestamp }); changed++; }
      if (!on && exists) { ctx.db.streetEdit.id.delete(id); changed++; }
    }
    if (!changed) return;
    const names = [...new Set(ids.map(i => EDGES[i].name).filter(Boolean))].slice(0, 3).join(', ') || 'a street';
    logActivity(ctx, scenarioId, on ? `made ${names} car-free` : `reopened ${names} to cars`);
    requestSettle(ctx, scenarioId);
  }
);

export const setBlock = spacetimedb.reducer(
  { scenarioId: t.u32(), buildingIds: t.array(t.u32()), scale: t.f32(), zone: t.string() },
  (ctx, { scenarioId, buildingIds, scale, zone }) => {
    requirePlan(ctx, scenarioId);
    if (!(scale >= 0.25 && scale <= 4)) throw new SenderError('density scale must be between 0.25 and 4');
    if (zone && !ZONES.includes(zone)) throw new SenderError(`zone must be one of ${ZONES.join(', ')} or ''`);
    const ids = [...new Set(buildingIds)].filter(canEditBuilding);
    if (!ids.length) throw new SenderError('no editable buildings in that selection');
    for (const buildingId of ids) {
      const id = key(scenarioId, buildingId); const exists = ctx.db.blockEdit.id.find(id);
      const reset = scale === 1 && !zone;
      if (reset) { if (exists) ctx.db.blockEdit.id.delete(id); continue; }
      const row = { id, scenarioId, buildingId, scale, zone, author: ctx.sender, authorName: playerName(ctx), at: ctx.timestamp };
      if (exists) ctx.db.blockEdit.id.update(row); else ctx.db.blockEdit.insert(row);
    }
    logActivity(ctx, scenarioId, `set ${ids.length} building${ids.length > 1 ? 's' : ''} to ${Math.round(scale * 100)}% density${zone ? ` (${zone})` : ''}`);
    requestSettle(ctx, scenarioId);
  }
);

const POLICY_KINDS = ['congestion_charge', 'parking_price'];
export const setPolicy = spacetimedb.reducer(
  { scenarioId: t.u32(), kind: t.string(), target: t.string(), amount: t.f32() },
  (ctx, { scenarioId, kind, target, amount }) => {
    requirePlan(ctx, scenarioId);
    if (!POLICY_KINDS.includes(kind)) throw new SenderError(`unknown policy kind ${kind}`);
    if (target && !INLETS.some(g => g.mode === 'car' && g.key === target)) throw new SenderError(`unknown car inlet ${target}`);
    if (!(amount >= 0 && amount <= 50)) throw new SenderError('amount must be between $0 and $50');
    for (const p of [...ctx.db.policy.scenarioId.filter(scenarioId)]) if (p.kind === kind && p.target === target) ctx.db.policy.id.delete(p.id);
    if (amount > 0) ctx.db.policy.insert({ id: 0n, scenarioId, kind, target, amount, author: ctx.sender, authorName: playerName(ctx), at: ctx.timestamp });
    logActivity(ctx, scenarioId, amount > 0 ? `set ${kind.replace('_', ' ')} $${amount.toFixed(2)}${target ? ` at ${target}` : ''}` : `removed ${kind.replace('_', ' ')}`);
    requestSettle(ctx, scenarioId);
  }
);

export const resetScenario = spacetimedb.reducer({ scenarioId: t.u32() }, (ctx, { scenarioId }) => {
  requirePlan(ctx, scenarioId);
  for (const e of [...ctx.db.streetEdit.scenarioId.filter(scenarioId)]) ctx.db.streetEdit.id.delete(e.id);
  for (const b of [...ctx.db.blockEdit.scenarioId.filter(scenarioId)]) ctx.db.blockEdit.id.delete(b.id);
  for (const p of [...ctx.db.policy.scenarioId.filter(scenarioId)]) ctx.db.policy.id.delete(p.id);
  logActivity(ctx, scenarioId, 'reset the plan');
  requestSettle(ctx, scenarioId);
});

// New plan, optionally copying another scenario's edits.
export const createScenario = spacetimedb.reducer({ name: t.string(), copyFrom: t.u32() }, (ctx, { name, copyFrom }) => {
  const id = Math.max(...[...ctx.db.scenario.iter()].map(s => s.id)) + 1;
  ctx.db.scenario.insert({ id, name: name.slice(0, 40) || `Plan ${id}`, isPlan: true, status: 'settling', day: 0, editVersion: 0, settledVersion: 0, updatedAt: ctx.timestamp });
  if (copyFrom) {
    for (const e of ctx.db.streetEdit.scenarioId.filter(copyFrom)) ctx.db.streetEdit.insert({ ...e, id: key(id, e.edgeId), scenarioId: id });
    for (const b of ctx.db.blockEdit.scenarioId.filter(copyFrom)) ctx.db.blockEdit.insert({ ...b, id: key(id, b.buildingId), scenarioId: id });
    for (const p of ctx.db.policy.scenarioId.filter(copyFrom)) ctx.db.policy.insert({ ...p, id: 0n, scenarioId: id });
  }
  logActivity(ctx, id, `created ${name || `Plan ${id}`}`);
  requestSettle(ctx, id);
});

// ───────────────────────── people ─────────────────────────
export const setName = spacetimedb.reducer({ name: t.string() }, (ctx, { name }) => {
  const p = ctx.db.player.identity.find(ctx.sender);
  const clean = name.trim().slice(0, 24);
  if (!p || !clean) throw new SenderError('name required');
  ctx.db.player.identity.update({ ...p, name: clean });
});

export const setCursor = spacetimedb.reducer({ scenarioId: t.u32(), x: t.f32(), z: t.f32() }, (ctx, { scenarioId, x, z }) => {
  const p = ctx.db.player.identity.find(ctx.sender);
  if (p) ctx.db.player.identity.update({ ...p, scenarioId, cursorX: x, cursorZ: z, lastSeen: ctx.timestamp });
});

// Narrator output (Claude). Posts should be grounded in the sim's trips; the viewer links them to the sim.
export const postCitizen = spacetimedb.reducer(
  { scenarioId: t.u32(), personId: t.i32(), author: t.string(), text: t.string(), tag: t.string() },
  (ctx, { scenarioId, personId, author, text, tag }) => {
    if (!ctx.db.scenario.id.find(scenarioId)) throw new SenderError(`no scenario ${scenarioId}`);
    if (!text.trim()) throw new SenderError('empty post');
    ctx.db.citizenPost.insert({ id: 0n, scenarioId, personId, author: author.slice(0, 40), text: text.slice(0, 400), tag: tag.slice(0, 24), at: ctx.timestamp });
  }
);
