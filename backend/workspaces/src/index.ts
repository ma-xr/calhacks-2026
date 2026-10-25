// Live layer for CommonGround. People form workspaces (teams), invite each other with links and
// edit the workspace's plans together. Edits from every connected client land in street_edit /
// block_edit; each edit bumps the plan's editVersion. A compute then POSTs the plan's merged edits to
// the Python engine and writes the result back, so every subscriber sees the same plan and the same
// numbers. The compute runs in the module (scheduled `compute` procedure, when config.engineUrl is a
// public address) or in a member's browser that can reach the engine (claimCompute / reportResult).
import { SenderError, t, type InferSchema, type ReducerCtx } from 'spacetimedb/server';
import { ScheduleAt, TimeDuration, type Identity } from 'spacetimedb';
import spacetimedb, { computeJob, invite } from './schema';

export default spacetimedb;
type Ctx = ReducerCtx<InferSchema<typeof spacetimedb>>;

const DEBOUNCE_US = 400_000n; // let a paint stroke finish before computing
const CLAIM_TTL_US = 30_000_000n; // a browser compute that hasn't reported in 30 s can be taken over
const FETCH_TIMEOUT_MS = 20_000;
const ZONES = ['res', 'office', 'retail', 'mixed'];
const ROLES = ['viewer', 'editor', 'admin'];
const STAGES = ['draft', 'review', 'approved', 'archived'];
const STAGE_LABELS: Record<string, string> = { draft: 'Draft', review: 'In review', approved: 'Approved', archived: 'Archived' };
const COLORS = ['#ffb547', '#4fc3f7', '#ff6b9d', '#9ccc65', '#ba68c8', '#ffd54f', '#4db6ac', '#f06292'];
const WS_COLORS = ['#3b9cff', '#ff7a45', '#22c55e', '#a855f7', '#f43f5e', '#eab308', '#14b8a6', '#6366f1'];
const CODE_ALPHABET = 'abcdefghjkmnpqrstuvwxyz23456789';

const key = (scenarioId: number, n: number) => (BigInt(scenarioId) << 32n) | BigInt(n);
const clip = (s: string, n: number) => s.trim().slice(0, n);

function me(ctx: Ctx) {
  return ctx.db.player.identity.find(ctx.sender);
}
function membership(ctx: Ctx, workspaceId: bigint, identity: Identity) {
  for (const m of ctx.db.member.by_ws_identity.filter([workspaceId, identity])) return m;
  return null;
}
// Throws unless the sender is a member of the workspace with at least `min` role.
function requireRole(ctx: Ctx, workspaceId: bigint, min: 'viewer' | 'editor' | 'admin') {
  const ws = ctx.db.workspace.id.find(workspaceId);
  if (!ws) throw new SenderError('workspace not found');
  const m = membership(ctx, workspaceId, ctx.sender);
  if (!m) throw new SenderError('you are not a member of this workspace');
  if (ROLES.indexOf(m.role) < ROLES.indexOf(min)) throw new SenderError(`only ${min === 'admin' ? 'admins' : 'editors and admins'} can do that`);
  return { ws, m };
}
function requirePlan(ctx: Ctx, scenarioId: number, min: 'viewer' | 'editor' | 'admin') {
  const sc = ctx.db.scenario.id.find(scenarioId);
  if (!sc) throw new SenderError('plan not found');
  requireRole(ctx, sc.workspaceId, min);
  return sc;
}
function logActivity(ctx: Ctx, workspaceId: bigint, scenarioId: number, text: string) {
  const p = me(ctx);
  ctx.db.activity.insert({ id: 0n, workspaceId, scenarioId, who: p?.name ?? 'Someone', color: p?.color ?? '#999999', text, at: ctx.timestamp });
}
function engineLog(ctx: Ctx, workspaceId: bigint, scenarioId: number, text: string) {
  ctx.db.activity.insert({ id: 0n, workspaceId, scenarioId, who: 'Engine', color: '#cccccc', text, at: ctx.timestamp });
}
function adminCount(ctx: Ctx, workspaceId: bigint) {
  let n = 0;
  for (const m of ctx.db.member.iter()) if (m.workspaceId === workspaceId && m.role === 'admin') n++;
  return n;
}
function newInviteCode(ctx: Ctx) {
  for (;;) {
    let code = '';
    for (let i = 0; i < 8; i++) code += CODE_ALPHABET[ctx.random.integerInRange(0, CODE_ALPHABET.length - 1)];
    if (!ctx.db.invite.code.find(code)) return code;
  }
}
function engineUrl(ctx: Ctx) {
  return ctx.db.config.id.find(1)?.engineUrl ?? '';
}

// Mark the plan dirty. With a module engine URL a scheduled compute is queued; otherwise a member's
// browser picks the plan up (status 'pending', editVersion > resultVersion).
function requestCompute(ctx: Ctx, scenarioId: number) {
  const sc = ctx.db.scenario.id.find(scenarioId);
  if (!sc) return;
  ctx.db.scenario.id.update({ ...sc, editVersion: sc.editVersion + 1, status: 'pending', day: 0, error: '', computingBy: '', updatedAt: ctx.timestamp });
  if (engineUrl(ctx) && ![...ctx.db.computeJob.scenarioId.filter(scenarioId)].length) {
    ctx.db.computeJob.insert({ scheduledId: 0n, scheduledAt: ScheduleAt.time(ctx.timestamp.microsSinceUnixEpoch + DEBOUNCE_US), scenarioId });
  }
}

function deletePlanRows(ctx: Ctx, scenarioId: number) {
  for (const e of [...ctx.db.streetEdit.scenarioId.filter(scenarioId)]) ctx.db.streetEdit.id.delete(e.id);
  for (const b of [...ctx.db.blockEdit.scenarioId.filter(scenarioId)]) ctx.db.blockEdit.id.delete(b.id);
  for (const j of [...ctx.db.computeJob.scenarioId.filter(scenarioId)]) ctx.db.computeJob.scheduledId.delete(j.scheduledId);
  ctx.db.resultSummary.id.delete(scenarioId);
  ctx.db.scenario.id.delete(scenarioId);
}

function insertPlan(ctx: Ctx, workspaceId: bigint, name: string, description: string) {
  return ctx.db.scenario.insert({
    id: 0, workspaceId, name, description, createdBy: me(ctx)?.name ?? 'Someone', stage: 'draft', planId: '', status: 'pending', day: 0, days: 5,
    editVersion: 0, resultVersion: 0, error: '', computingBy: '', computingSince: ctx.timestamp, createdAt: ctx.timestamp, updatedAt: ctx.timestamp,
  });
}

// ───────────────────────── lifecycle ─────────────────────────
export const init = spacetimedb.init(ctx => {
  ctx.db.config.insert({ id: 1, owner: ctx.sender, engineUrl: '' });
});

export const onConnect = spacetimedb.clientConnected(ctx => {
  const p = ctx.db.player.identity.find(ctx.sender);
  if (p) { ctx.db.player.identity.update({ ...p, online: true, lastSeen: ctx.timestamp }); return; }
  const n = Number(ctx.db.player.count());
  ctx.db.player.insert({
    identity: ctx.sender, name: `Planner ${n + 1}`, color: COLORS[n % COLORS.length],
    online: true, workspaceId: 0n, scenarioId: 0, cursorX: 0, cursorZ: 0, lastSeen: ctx.timestamp,
  });
});

export const onDisconnect = spacetimedb.clientDisconnected(ctx => {
  const p = ctx.db.player.identity.find(ctx.sender);
  if (p) ctx.db.player.identity.update({ ...p, online: false, lastSeen: ctx.timestamp });
});

// Admins see the invite links of their workspaces.
export const myInvite = spacetimedb.view(
  { name: 'my_invite', public: true },
  t.array(invite.rowType),
  ctx => {
    const out = [];
    for (const m of ctx.db.member.identity.filter(ctx.sender)) {
      if (m.role !== 'admin') continue;
      for (const i of ctx.db.invite.workspaceId.filter(m.workspaceId)) out.push(i);
    }
    return out;
  }
);

// ───────────────────────── workspaces ─────────────────────────
export const createWorkspace = spacetimedb.reducer({ name: t.string(), description: t.string() }, (ctx, { name, description }) => {
  const clean = clip(name, 48);
  if (!clean) throw new SenderError('workspace name required');
  const n = Number(ctx.db.workspace.count());
  const ws = ctx.db.workspace.insert({
    id: 0n, name: clean, description: clip(description, 280), color: WS_COLORS[n % WS_COLORS.length],
    owner: ctx.sender, createdAt: ctx.timestamp, updatedAt: ctx.timestamp,
  });
  ctx.db.member.insert({ id: 0n, workspaceId: ws.id, identity: ctx.sender, role: 'admin', joinedAt: ctx.timestamp });
  ctx.db.invite.insert({ code: newInviteCode(ctx), workspaceId: ws.id, role: 'editor', createdBy: ctx.sender, createdAt: ctx.timestamp, uses: 0 });
  logActivity(ctx, ws.id, 0, `created the workspace`);
  const plan = insertPlan(ctx, ws.id, 'Plan A', 'Start here: make a street car-free or rezone a block.');
  requestCompute(ctx, plan.id);
});

export const updateWorkspace = spacetimedb.reducer(
  { workspaceId: t.u64(), name: t.string(), description: t.string() },
  (ctx, { workspaceId, name, description }) => {
    const { ws } = requireRole(ctx, workspaceId, 'admin');
    const clean = clip(name, 48);
    if (!clean) throw new SenderError('workspace name required');
    ctx.db.workspace.id.update({ ...ws, name: clean, description: clip(description, 280), updatedAt: ctx.timestamp });
    if (clean !== ws.name) logActivity(ctx, workspaceId, 0, `renamed the workspace to ${clean}`);
  }
);

export const deleteWorkspace = spacetimedb.reducer({ workspaceId: t.u64() }, (ctx, { workspaceId }) => {
  requireRole(ctx, workspaceId, 'admin');
  for (const sc of [...ctx.db.scenario.workspaceId.filter(workspaceId)]) deletePlanRows(ctx, sc.id);
  for (const m of [...ctx.db.member.iter()]) if (m.workspaceId === workspaceId) ctx.db.member.id.delete(m.id);
  for (const i of [...ctx.db.invite.workspaceId.filter(workspaceId)]) ctx.db.invite.code.delete(i.code);
  for (const a of [...ctx.db.activity.workspaceId.filter(workspaceId)]) ctx.db.activity.id.delete(a.id);
  for (const p of [...ctx.db.player.iter()]) if (p.workspaceId === workspaceId) ctx.db.player.identity.update({ ...p, workspaceId: 0n, scenarioId: 0 });
  ctx.db.workspace.id.delete(workspaceId);
});

// ───────────────────────── members and invites ─────────────────────────
export const createInvite = spacetimedb.reducer({ workspaceId: t.u64(), role: t.string() }, (ctx, { workspaceId, role }) => {
  requireRole(ctx, workspaceId, 'admin');
  if (!ROLES.includes(role)) throw new SenderError(`role must be one of ${ROLES.join(', ')}`);
  ctx.db.invite.insert({ code: newInviteCode(ctx), workspaceId, role, createdBy: ctx.sender, createdAt: ctx.timestamp, uses: 0 });
});

export const revokeInvite = spacetimedb.reducer({ code: t.string() }, (ctx, { code }) => {
  const inv = ctx.db.invite.code.find(code);
  if (!inv) throw new SenderError('invite not found');
  requireRole(ctx, inv.workspaceId, 'admin');
  ctx.db.invite.code.delete(code);
});

export const joinWorkspace = spacetimedb.reducer({ code: t.string() }, (ctx, { code }) => {
  const inv = ctx.db.invite.code.find(code.trim().toLowerCase());
  if (!inv || !ctx.db.workspace.id.find(inv.workspaceId)) throw new SenderError('that invite link is invalid or was revoked');
  if (membership(ctx, inv.workspaceId, ctx.sender)) return;
  ctx.db.member.insert({ id: 0n, workspaceId: inv.workspaceId, identity: ctx.sender, role: inv.role, joinedAt: ctx.timestamp });
  ctx.db.invite.code.update({ ...inv, uses: inv.uses + 1 });
  logActivity(ctx, inv.workspaceId, 0, `joined as ${inv.role}`);
});

export const setMemberRole = spacetimedb.reducer(
  { workspaceId: t.u64(), identity: t.identity(), role: t.string() },
  (ctx, { workspaceId, identity, role }) => {
    requireRole(ctx, workspaceId, 'admin');
    if (!ROLES.includes(role)) throw new SenderError(`role must be one of ${ROLES.join(', ')}`);
    const m = membership(ctx, workspaceId, identity);
    if (!m) throw new SenderError('not a member');
    if (m.role === role) return;
    if (m.role === 'admin' && adminCount(ctx, workspaceId) <= 1) throw new SenderError('a workspace needs at least one admin');
    ctx.db.member.id.update({ ...m, role });
    const who = ctx.db.player.identity.find(identity)?.name ?? 'a member';
    logActivity(ctx, workspaceId, 0, `made ${who} ${role === 'admin' ? 'an admin' : `an ${role}`}`.replace('an viewer', 'a viewer'));
  }
);

// Admins remove anyone; everyone can remove themselves (leave).
export const removeMember = spacetimedb.reducer({ workspaceId: t.u64(), identity: t.identity() }, (ctx, { workspaceId, identity }) => {
  const self = identity.equals(ctx.sender);
  requireRole(ctx, workspaceId, self ? 'viewer' : 'admin');
  const m = membership(ctx, workspaceId, identity);
  if (!m) return;
  if (m.role === 'admin' && adminCount(ctx, workspaceId) <= 1) throw new SenderError(self ? 'make someone else an admin before leaving' : 'a workspace needs at least one admin');
  const who = ctx.db.player.identity.find(identity)?.name ?? 'a member';
  ctx.db.member.id.delete(m.id);
  logActivity(ctx, workspaceId, 0, self ? 'left the workspace' : `removed ${who}`);
});

// ───────────────────────── plans ─────────────────────────
// New plan, optionally copying another plan's edits (copyFrom 0 = empty).
export const createPlan = spacetimedb.reducer(
  { workspaceId: t.u64(), name: t.string(), description: t.string(), copyFrom: t.u32() },
  (ctx, { workspaceId, name, description, copyFrom }) => {
    requireRole(ctx, workspaceId, 'editor');
    const src = copyFrom ? ctx.db.scenario.id.find(copyFrom) : null;
    if (copyFrom && (!src || src.workspaceId !== workspaceId)) throw new SenderError('can only copy a plan from this workspace');
    const clean = clip(name, 48) || `Plan ${[...ctx.db.scenario.workspaceId.filter(workspaceId)].length + 1}`;
    const sc = insertPlan(ctx, workspaceId, clean, clip(description, 280));
    if (src) {
      for (const e of ctx.db.streetEdit.scenarioId.filter(src.id)) ctx.db.streetEdit.insert({ ...e, id: key(sc.id, e.edgeId), scenarioId: sc.id });
      for (const b of ctx.db.blockEdit.scenarioId.filter(src.id)) ctx.db.blockEdit.insert({ ...b, id: key(sc.id, b.buildingId), scenarioId: sc.id });
    }
    logActivity(ctx, workspaceId, sc.id, src ? `duplicated ${src.name} as ${clean}` : `created ${clean}`);
    requestCompute(ctx, sc.id);
  }
);

export const updatePlan = spacetimedb.reducer(
  { scenarioId: t.u32(), name: t.string(), description: t.string() },
  (ctx, { scenarioId, name, description }) => {
    const sc = requirePlan(ctx, scenarioId, 'editor');
    const clean = clip(name, 48);
    if (!clean) throw new SenderError('plan name required');
    ctx.db.scenario.id.update({ ...sc, name: clean, description: clip(description, 280), updatedAt: ctx.timestamp });
    if (clean !== sc.name) logActivity(ctx, sc.workspaceId, scenarioId, `renamed ${sc.name} to ${clean}`);
  }
);

export const setPlanStage = spacetimedb.reducer({ scenarioId: t.u32(), stage: t.string() }, (ctx, { scenarioId, stage }) => {
  const sc = requirePlan(ctx, scenarioId, 'editor');
  if (!STAGES.includes(stage)) throw new SenderError(`stage must be one of ${STAGES.join(', ')}`);
  if (stage === sc.stage) return;
  ctx.db.scenario.id.update({ ...sc, stage, updatedAt: ctx.timestamp });
  logActivity(ctx, sc.workspaceId, scenarioId, `moved ${sc.name} to ${STAGE_LABELS[stage]}`);
});

export const deletePlan = spacetimedb.reducer({ scenarioId: t.u32() }, (ctx, { scenarioId }) => {
  const sc = requirePlan(ctx, scenarioId, 'editor');
  deletePlanRows(ctx, scenarioId);
  logActivity(ctx, sc.workspaceId, 0, `deleted ${sc.name}`);
});

// ───────────────────────── edits ─────────────────────────
export const setPedestrian = spacetimedb.reducer(
  { scenarioId: t.u32(), edgeIds: t.array(t.u32()), on: t.bool() },
  (ctx, { scenarioId, edgeIds, on }) => {
    const sc = requirePlan(ctx, scenarioId, 'editor');
    const ids = [...new Set(edgeIds)];
    if (!ids.length) throw new SenderError('no streets selected');
    if (ids.length > 2000) throw new SenderError('too many streets in one edit');
    const name = me(ctx)?.name ?? 'Someone';
    let changed = 0;
    for (const edgeId of ids) {
      const id = key(scenarioId, edgeId), exists = ctx.db.streetEdit.id.find(id);
      if (on && !exists) { ctx.db.streetEdit.insert({ id, scenarioId, edgeId, author: ctx.sender, authorName: name, at: ctx.timestamp }); changed++; }
      if (!on && exists) { ctx.db.streetEdit.id.delete(id); changed++; }
    }
    if (!changed) return;
    logActivity(ctx, sc.workspaceId, scenarioId, `${on ? 'made' : 'reopened'} ${changed} street segment${changed > 1 ? 's' : ''} ${on ? 'car-free' : 'to cars'} in ${sc.name}`);
    requestCompute(ctx, scenarioId);
  }
);

// scale 1 with zone '' clears the edit.
export const setBlock = spacetimedb.reducer(
  { scenarioId: t.u32(), buildingIds: t.array(t.u32()), scale: t.f32(), zone: t.string() },
  (ctx, { scenarioId, buildingIds, scale, zone }) => {
    const sc = requirePlan(ctx, scenarioId, 'editor');
    const ids = [...new Set(buildingIds)];
    if (!ids.length) throw new SenderError('no buildings selected');
    if (!(scale >= 0.25 && scale <= 4)) throw new SenderError('density scale must be between 0.25 and 4');
    if (zone && !ZONES.includes(zone)) throw new SenderError(`zone must be one of ${ZONES.join(', ')} or ''`);
    const name = me(ctx)?.name ?? 'Someone';
    const clear = scale === 1 && !zone;
    for (const buildingId of ids) {
      const id = key(scenarioId, buildingId), exists = ctx.db.blockEdit.id.find(id);
      if (clear) { if (exists) ctx.db.blockEdit.id.delete(id); continue; }
      const row = { id, scenarioId, buildingId, scale, zone, author: ctx.sender, authorName: name, at: ctx.timestamp };
      if (exists) ctx.db.blockEdit.id.update(row); else ctx.db.blockEdit.insert(row);
    }
    const n = `${ids.length} building${ids.length > 1 ? 's' : ''}`;
    logActivity(ctx, sc.workspaceId, scenarioId, `${clear ? `reset ${n}` : `set ${n} to ${Math.round(scale * 100)}% density${zone ? ` (${zone})` : ''}`} in ${sc.name}`);
    requestCompute(ctx, scenarioId);
  }
);

export const reset = spacetimedb.reducer({ scenarioId: t.u32() }, (ctx, { scenarioId }) => {
  const sc = requirePlan(ctx, scenarioId, 'editor');
  for (const e of [...ctx.db.streetEdit.scenarioId.filter(scenarioId)]) ctx.db.streetEdit.id.delete(e.id);
  for (const b of [...ctx.db.blockEdit.scenarioId.filter(scenarioId)]) ctx.db.blockEdit.id.delete(b.id);
  logActivity(ctx, sc.workspaceId, scenarioId, `reset ${sc.name}`);
  requestCompute(ctx, scenarioId);
});

// Re-run the engine on the plan's current edits (e.g. after restarting the engine).
export const recompute = spacetimedb.reducer({ scenarioId: t.u32() }, (ctx, { scenarioId }) => {
  requirePlan(ctx, scenarioId, 'viewer');
  requestCompute(ctx, scenarioId);
});

// ───────────────────────── compute: module side (scheduled procedure) ─────────────────────────
type EngineResult = {
  id: string;
  cached?: boolean;
  settle?: { days?: number; ms?: number };
  metrics: unknown;
  delta: unknown;
  value: { mobility: number; social: number; economy: number; health: number; environment?: number; total: number };
  edges: { car_day: number[]; ped_day: number[] };
};
type ResultRow = {
  planId: string; cached: boolean; settleMs: number; days: number;
  valueMobility: number; valueSocial: number; valueEconomy: number; valueHealth: number; valueEnvironment: number; valueTotal: number;
  metricsJson: string; deltaJson: string; carDay: number[]; pedDay: number[];
};

function editsBody(ctx: Ctx, scenarioId: number, name: string) {
  const pedestrianized = [...ctx.db.streetEdit.scenarioId.filter(scenarioId)].map(e => e.edgeId).sort((a, b) => a - b);
  const blocks: Record<string, { scale: number; zone?: string }> = {};
  for (const b of ctx.db.blockEdit.scenarioId.filter(scenarioId)) blocks[String(b.buildingId)] = b.zone ? { scale: b.scale, zone: b.zone } : { scale: b.scale };
  return JSON.stringify({ name, edits: { pedestrianized, blocks } });
}

// Write a compute's outcome, unless a newer result already landed. Returns false when it was stale.
function writeResult(ctx: Ctx, scenarioId: number, version: number, result: ResultRow | null, error: string) {
  const sc = ctx.db.scenario.id.find(scenarioId);
  if (!sc || version < sc.resultVersion) return false;
  const stale = sc.editVersion > version;
  if (result) {
    const row = {
      id: scenarioId, workspaceId: sc.workspaceId, scenarioId: result.planId, editVersion: version, cached: result.cached, settleMs: result.settleMs,
      valueMobility: result.valueMobility, valueSocial: result.valueSocial, valueEconomy: result.valueEconomy, valueHealth: result.valueHealth,
      valueEnvironment: result.valueEnvironment, valueTotal: result.valueTotal,
      metricsJson: result.metricsJson, deltaJson: result.deltaJson, carDay: result.carDay, pedDay: result.pedDay, updatedAt: ctx.timestamp,
    };
    if (ctx.db.resultSummary.id.find(scenarioId)) ctx.db.resultSummary.id.update(row); else ctx.db.resultSummary.insert(row);
    ctx.db.scenario.id.update({
      ...sc, planId: result.planId, resultVersion: version, days: result.days || sc.days, day: result.days || sc.days,
      status: stale ? 'pending' : 'ready', error: '', computingBy: '', updatedAt: ctx.timestamp,
    });
    if (!stale && version > 1) {
      const k = Math.round(result.valueTotal / 1000);
      engineLog(ctx, sc.workspaceId, scenarioId, `${sc.name} settled: ${k >= 0 ? '+' : '-'}$${Math.abs(k).toLocaleString('en-US')}k/yr`);
    }
  } else {
    ctx.db.scenario.id.update({ ...sc, status: stale ? 'pending' : 'error', error, computingBy: '', updatedAt: ctx.timestamp });
    if (!stale) engineLog(ctx, sc.workspaceId, scenarioId, error);
  }
  return !stale;
}

export const compute = spacetimedb.procedure(
  { onSchedule: computeJob },
  { job: computeJob.rowType },
  t.unit(),
  (ctx, { job }) => {
    // 1. Snapshot the merged edits.
    const snap = ctx.withTx(tx => {
      const sc = tx.db.scenario.id.find(job.scenarioId);
      const url = tx.db.config.id.find(1)?.engineUrl ?? '';
      if (!sc || !url) return null;
      tx.db.scenario.id.update({ ...sc, status: 'computing', day: 0, computingBy: '', computingSince: tx.timestamp, updatedAt: tx.timestamp });
      return { version: sc.editVersion, url, body: editsBody(tx as unknown as Ctx, sc.id, sc.name) };
    });
    if (!snap) return {};

    // 2. Call the engine outside any transaction.
    let result: ResultRow | null = null;
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
      else {
        const r = JSON.parse(text) as EngineResult, v = r.value;
        result = {
          planId: r.id, cached: !!r.cached, settleMs: Math.round(r.settle?.ms ?? 0), days: r.settle?.days ?? 5,
          valueMobility: v.mobility, valueSocial: v.social, valueEconomy: v.economy, valueHealth: v.health,
          valueEnvironment: v.environment ?? 0, valueTotal: v.total,
          metricsJson: JSON.stringify(r.metrics), deltaJson: JSON.stringify(r.delta), carDay: r.edges.car_day, pedDay: r.edges.ped_day,
        };
      }
    } catch (e) {
      error = `engine unreachable at ${snap.url}: ${String(e).slice(0, 200)}`;
      if (/private or special-purpose/.test(error)) error += ' (point set_engine_url at a public address, see backend/live/README.md)';
    }

    // 3. Write the result; edits that arrived meanwhile get another run.
    ctx.withTx(tx => {
      const fresh = writeResult(tx as unknown as Ctx, job.scenarioId, snap.version, result, error);
      const otherPending = [...tx.db.computeJob.scenarioId.filter(job.scenarioId)].some(j => j.scheduledId !== job.scheduledId);
      if (!fresh && !otherPending && tx.db.scenario.id.find(job.scenarioId)) {
        tx.db.computeJob.insert({ scheduledId: 0n, scheduledAt: ScheduleAt.time(tx.timestamp.microsSinceUnixEpoch + DEBOUNCE_US), scenarioId: job.scenarioId });
      }
    });
    return {};
  }
);

// Owner only: where the compute procedure POSTs the edits. Must be a public address; '' turns module
// computes off so members' browsers do them.
export const setEngineUrl = spacetimedb.reducer({ url: t.string() }, (ctx, { url }) => {
  const cfg = ctx.db.config.id.find(1);
  if (!cfg || !cfg.owner.equals(ctx.sender)) throw new SenderError('only the database owner can set the engine url');
  if (url && !/^https?:\/\//.test(url)) throw new SenderError('url must start with http:// or https://');
  ctx.db.config.id.update({ ...cfg, engineUrl: url });
  for (const sc of [...ctx.db.scenario.iter()]) requestCompute(ctx, sc.id);
});

// ───────────────────────── compute: browser side ─────────────────────────
// A member's browser that can reach the engine claims a pending plan, runs POST /scenario itself and
// reports back. The claim lasts CLAIM_TTL_US so a closed tab doesn't stall the plan.
export const claimCompute = spacetimedb.reducer({ scenarioId: t.u32(), editVersion: t.u32() }, (ctx, { scenarioId, editVersion }) => {
  const sc = requirePlan(ctx, scenarioId, 'viewer');
  if (sc.editVersion !== editVersion || sc.resultVersion >= editVersion) return;
  const fresh = ctx.timestamp.microsSinceUnixEpoch - sc.computingSince.microsSinceUnixEpoch < CLAIM_TTL_US;
  if (sc.status === 'computing' && fresh) return;
  if (sc.status !== 'pending' && sc.status !== 'computing') return;
  ctx.db.scenario.id.update({ ...sc, status: 'computing', day: 0, computingBy: ctx.sender.toHexString(), computingSince: ctx.timestamp, updatedAt: ctx.timestamp });
});

export const reportResult = spacetimedb.reducer(
  {
    scenarioId: t.u32(), editVersion: t.u32(), planId: t.string(), cached: t.bool(), settleMs: t.u32(), days: t.u8(),
    valueMobility: t.f64(), valueSocial: t.f64(), valueEconomy: t.f64(), valueHealth: t.f64(), valueEnvironment: t.f64(), valueTotal: t.f64(),
    metricsJson: t.string(), deltaJson: t.string(), carDay: t.array(t.f32()), pedDay: t.array(t.f32()), error: t.string(),
  },
  (ctx, a) => {
    requirePlan(ctx, a.scenarioId, 'viewer');
    const result = a.error ? null : {
      planId: a.planId, cached: a.cached, settleMs: a.settleMs, days: a.days,
      valueMobility: a.valueMobility, valueSocial: a.valueSocial, valueEconomy: a.valueEconomy, valueHealth: a.valueHealth,
      valueEnvironment: a.valueEnvironment, valueTotal: a.valueTotal, metricsJson: a.metricsJson, deltaJson: a.deltaJson, carDay: a.carDay, pedDay: a.pedDay,
    };
    writeResult(ctx, a.scenarioId, a.editVersion, result, clip(a.error, 300));
  }
);

// ───────────────────────── people ─────────────────────────
export const setName = spacetimedb.reducer({ name: t.string() }, (ctx, { name }) => {
  const p = me(ctx);
  const clean = clip(name, 24);
  if (!p || !clean) throw new SenderError('name required');
  ctx.db.player.identity.update({ ...p, name: clean });
});

export const setColor = spacetimedb.reducer({ color: t.string() }, (ctx, { color }) => {
  const p = me(ctx);
  if (!p) throw new SenderError('not connected');
  if (!/^#[0-9a-fA-F]{6}$/.test(color)) throw new SenderError('color must be #rrggbb');
  ctx.db.player.identity.update({ ...p, color });
});

// Where this person is (0 = nowhere): drives "who's here" on dashboards and cursors in the simulator.
export const setPresence = spacetimedb.reducer({ workspaceId: t.u64(), scenarioId: t.u32() }, (ctx, { workspaceId, scenarioId }) => {
  const p = me(ctx);
  if (p) ctx.db.player.identity.update({ ...p, workspaceId, scenarioId, lastSeen: ctx.timestamp });
});

export const setCursor = spacetimedb.reducer({ x: t.f32(), z: t.f32() }, (ctx, { x, z }) => {
  const p = me(ctx);
  if (p) ctx.db.player.identity.update({ ...p, cursorX: x, cursorZ: z, lastSeen: ctx.timestamp });
});
