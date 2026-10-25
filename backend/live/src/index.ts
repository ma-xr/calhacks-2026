// Live layer for CommonGround. Edits from every connected client land in street_edit / block_edit;
// each edit bumps the plan's editVersion and arms a short debounce. When it fires, the `compute`
// procedure POSTs the merged edits to the Python engine and writes the result back, so every
// subscriber sees the same plan and the same numbers.
import { SenderError, t, type InferSchema, type ReducerCtx } from 'spacetimedb/server';
import { ScheduleAt, TimeDuration } from 'spacetimedb';
import spacetimedb, { computeJob } from './schema';

export default spacetimedb;
type Ctx = ReducerCtx<InferSchema<typeof spacetimedb>>;

const DEFAULT_ENGINE_URL = 'http://localhost:8787/scenario?lite=1'; // blocked by the host; see set_engine_url
const LIVE = 1;
const DEBOUNCE_US = 400_000n; // let a paint stroke finish before computing
const FETCH_TIMEOUT_MS = 20_000;
const ZONES = ['res', 'office', 'retail', 'mixed'];
const COLORS = ['#ffb547', '#4fc3f7', '#ff6b9d', '#9ccc65', '#ba68c8', '#ffd54f', '#4db6ac', '#f06292'];

function me(ctx: Ctx) {
  return ctx.db.player.identity.find(ctx.sender);
}
function logActivity(ctx: Ctx, text: string, who = me(ctx)?.name ?? 'Someone', color = me(ctx)?.color ?? '#999999') {
  ctx.db.activity.insert({ id: 0n, who, color, text, at: ctx.timestamp });
}

// Mark the plan dirty and make sure a compute is queued.
function requestCompute(ctx: Ctx) {
  const sc = ctx.db.scenario.id.find(LIVE)!;
  ctx.db.scenario.id.update({ ...sc, editVersion: sc.editVersion + 1, status: 'pending', day: 0, error: '', updatedAt: ctx.timestamp });
  if (!ctx.db.computeJob.count()) {
    ctx.db.computeJob.insert({ scheduledId: 0n, scheduledAt: ScheduleAt.time(ctx.timestamp.microsSinceUnixEpoch + DEBOUNCE_US) });
  }
}

// ───────────────────────── lifecycle ─────────────────────────
export const init = spacetimedb.init(ctx => {
  ctx.db.config.insert({ id: 1, owner: ctx.sender, engineUrl: DEFAULT_ENGINE_URL });
  ctx.db.scenario.insert({
    id: LIVE, name: 'Live plan', planId: '', status: 'pending', day: 0, days: 5,
    editVersion: 1, resultVersion: 0, error: '', updatedAt: ctx.timestamp,
  });
  // First compute fills result_summary with the untouched plan (= baseline).
  ctx.db.computeJob.insert({ scheduledId: 0n, scheduledAt: ScheduleAt.time(ctx.timestamp.microsSinceUnixEpoch + DEBOUNCE_US) });
});

export const onConnect = spacetimedb.clientConnected(ctx => {
  const p = ctx.db.player.identity.find(ctx.sender);
  if (p) { ctx.db.player.identity.update({ ...p, online: true, lastSeen: ctx.timestamp }); return; }
  const n = Number(ctx.db.player.count());
  ctx.db.player.insert({
    identity: ctx.sender, name: `Planner ${n + 1}`, color: COLORS[n % COLORS.length],
    online: true, cursorX: 0, cursorZ: 0, lastSeen: ctx.timestamp,
  });
});

export const onDisconnect = spacetimedb.clientDisconnected(ctx => {
  const p = ctx.db.player.identity.find(ctx.sender);
  if (p) ctx.db.player.identity.update({ ...p, online: false, lastSeen: ctx.timestamp });
});

// ───────────────────────── compute (scheduled procedure) ─────────────────────────
type EngineResult = {
  id: string;
  cached?: boolean;
  settle?: { days?: number; ms?: number };
  metrics: unknown;
  delta: unknown;
  value: { mobility: number; social: number; economy: number; health: number; environment?: number; total: number };
  edges: { car_day: number[]; ped_day: number[] };
};

export const compute = spacetimedb.procedure(
  { onSchedule: computeJob },
  { job: computeJob.rowType },
  t.unit(),
  (ctx, { job }) => {
    // 1. Snapshot the merged edits.
    const snap = ctx.withTx(tx => {
      const sc = tx.db.scenario.id.find(LIVE);
      if (!sc) return null;
      tx.db.scenario.id.update({ ...sc, status: 'computing', day: 0, updatedAt: tx.timestamp });
      const pedestrianized = [...tx.db.streetEdit.iter()].map(e => e.edgeId).sort((a, b) => a - b);
      const blocks: Record<string, { scale: number; zone?: string }> = {};
      for (const b of tx.db.blockEdit.iter()) blocks[String(b.buildingId)] = b.zone ? { scale: b.scale, zone: b.zone } : { scale: b.scale };
      return { version: sc.editVersion, url: tx.db.config.id.find(1)?.engineUrl ?? DEFAULT_ENGINE_URL, body: JSON.stringify({ name: sc.name, edits: { pedestrianized, blocks } }) };
    });
    if (!snap) return {};

    // 2. Call the engine outside any transaction.
    let result: EngineResult | null = null;
    let error = '';
    try {
      const res = ctx.http.fetch(snap.url, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: snap.body,
        timeout: TimeDuration.fromMillis(FETCH_TIMEOUT_MS),
      });
      const text = res.text();
      if (res.status !== 200) error = `engine ${res.status}: ${text.slice(0, 200)}`;
      else result = JSON.parse(text) as EngineResult;
    } catch (e) {
      error = `engine unreachable at ${snap.url}: ${String(e).slice(0, 200)}`;
      if (/private or special-purpose/.test(error)) error += ' (point set_engine_url at a public address, see backend/live/README.md)';
    }

    // 3. Write the result, unless a newer result already landed.
    ctx.withTx(tx => {
      const sc = tx.db.scenario.id.find(LIVE);
      if (!sc || snap.version < sc.resultVersion) return;
      const stale = sc.editVersion > snap.version;
      if (result) {
        const v = result.value;
        const row = {
          id: LIVE, scenarioId: result.id, editVersion: snap.version, cached: !!result.cached,
          settleMs: Math.round(result.settle?.ms ?? 0),
          valueMobility: v.mobility, valueSocial: v.social, valueEconomy: v.economy, valueHealth: v.health,
          valueEnvironment: v.environment ?? 0, valueTotal: v.total,
          metricsJson: JSON.stringify(result.metrics), deltaJson: JSON.stringify(result.delta),
          carDay: result.edges.car_day, pedDay: result.edges.ped_day, updatedAt: tx.timestamp,
        };
        if (tx.db.resultSummary.id.find(LIVE)) tx.db.resultSummary.id.update(row); else tx.db.resultSummary.insert(row);
        const days = result.settle?.days ?? sc.days;
        tx.db.scenario.id.update({
          ...sc, planId: result.id, resultVersion: snap.version, days, day: days,
          status: stale ? 'pending' : 'ready', error: '', updatedAt: tx.timestamp,
        });
        if (!stale && snap.version > 1) {
          const k = Math.round(v.total / 1000);
          tx.db.activity.insert({ id: 0n, who: 'Engine', color: '#cccccc', text: `plan settled: ${k >= 0 ? '+' : '-'}$${Math.abs(k).toLocaleString('en-US')}k/yr`, at: tx.timestamp });
        }
      } else {
        tx.db.scenario.id.update({ ...sc, status: stale ? 'pending' : 'error', error, updatedAt: tx.timestamp });
        tx.db.activity.insert({ id: 0n, who: 'Engine', color: '#cccccc', text: error, at: tx.timestamp });
      }
      // Edits arrived while we were computing: make sure another run is queued.
      const otherPending = [...tx.db.computeJob.iter()].some(j => j.scheduledId !== job.scheduledId);
      if (stale && !otherPending) {
        tx.db.computeJob.insert({ scheduledId: 0n, scheduledAt: ScheduleAt.time(tx.timestamp.microsSinceUnixEpoch + DEBOUNCE_US) });
      }
    });
    return {};
  }
);

// Owner only: where the compute procedure POSTs the edits. Must be a public address.
export const setEngineUrl = spacetimedb.reducer({ url: t.string() }, (ctx, { url }) => {
  const cfg = ctx.db.config.id.find(1);
  if (!cfg || !cfg.owner.equals(ctx.sender)) throw new SenderError('only the database owner can set the engine url');
  if (!/^https?:\/\//.test(url)) throw new SenderError('url must start with http:// or https://');
  ctx.db.config.id.update({ ...cfg, engineUrl: url });
  requestCompute(ctx);
});

// Re-run the engine on the current edits (e.g. after restarting the engine).
export const recompute = spacetimedb.reducer(ctx => {
  requestCompute(ctx);
});

// ───────────────────────── edits ─────────────────────────
export const setPedestrian = spacetimedb.reducer(
  { edgeIds: t.array(t.u32()), on: t.bool() },
  (ctx, { edgeIds, on }) => {
    const ids = [...new Set(edgeIds)];
    if (!ids.length) throw new SenderError('no streets selected');
    if (ids.length > 2000) throw new SenderError('too many streets in one edit');
    const name = me(ctx)?.name ?? 'Someone';
    let changed = 0;
    for (const edgeId of ids) {
      const exists = ctx.db.streetEdit.edgeId.find(edgeId);
      if (on && !exists) { ctx.db.streetEdit.insert({ edgeId, author: ctx.sender, authorName: name, at: ctx.timestamp }); changed++; }
      if (!on && exists) { ctx.db.streetEdit.edgeId.delete(edgeId); changed++; }
    }
    if (!changed) return;
    logActivity(ctx, `${on ? 'made' : 'reopened'} ${changed} street segment${changed > 1 ? 's' : ''} ${on ? 'car-free' : 'to cars'}`);
    requestCompute(ctx);
  }
);

// scale 1 with zone '' clears the edit.
export const setBlock = spacetimedb.reducer(
  { buildingIds: t.array(t.u32()), scale: t.f32(), zone: t.string() },
  (ctx, { buildingIds, scale, zone }) => {
    const ids = [...new Set(buildingIds)];
    if (!ids.length) throw new SenderError('no buildings selected');
    if (!(scale >= 0.25 && scale <= 4)) throw new SenderError('density scale must be between 0.25 and 4');
    if (zone && !ZONES.includes(zone)) throw new SenderError(`zone must be one of ${ZONES.join(', ')} or ''`);
    const name = me(ctx)?.name ?? 'Someone';
    const clear = scale === 1 && !zone;
    for (const buildingId of ids) {
      const exists = ctx.db.blockEdit.buildingId.find(buildingId);
      if (clear) { if (exists) ctx.db.blockEdit.buildingId.delete(buildingId); continue; }
      const row = { buildingId, scale, zone, author: ctx.sender, authorName: name, at: ctx.timestamp };
      if (exists) ctx.db.blockEdit.buildingId.update(row); else ctx.db.blockEdit.insert(row);
    }
    const n = `${ids.length} building${ids.length > 1 ? 's' : ''}`;
    logActivity(ctx, clear ? `reset ${n}` : `set ${n} to ${Math.round(scale * 100)}% density${zone ? ` (${zone})` : ''}`);
    requestCompute(ctx);
  }
);

export const reset = spacetimedb.reducer(ctx => {
  for (const e of [...ctx.db.streetEdit.iter()]) ctx.db.streetEdit.edgeId.delete(e.edgeId);
  for (const b of [...ctx.db.blockEdit.iter()]) ctx.db.blockEdit.buildingId.delete(b.buildingId);
  logActivity(ctx, 'reset the plan');
  requestCompute(ctx);
});

// ───────────────────────── people ─────────────────────────
export const setName = spacetimedb.reducer({ name: t.string() }, (ctx, { name }) => {
  const p = me(ctx);
  const clean = name.trim().slice(0, 24);
  if (!p || !clean) throw new SenderError('name required');
  ctx.db.player.identity.update({ ...p, name: clean });
});

export const setCursor = spacetimedb.reducer({ x: t.f32(), z: t.f32() }, (ctx, { x, z }) => {
  const p = me(ctx);
  if (p) ctx.db.player.identity.update({ ...p, cursorX: x, cursorZ: z, lastSeen: ctx.timestamp });
});
