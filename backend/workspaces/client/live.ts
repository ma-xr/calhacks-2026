// Browser/Node client for the live layer. Bundled with the SpacetimeDB SDK into client/dist/live.mjs,
// so a page without a bundler can `import { connectLive } from './live.mjs'`.
//
// One connection carries everything a person can see: their workspaces, each workspace's members,
// invites (admins only), plans with their latest results, presence and activity. With `engine` set,
// the page also runs computes for pending plans (claimCompute -> POST /scenario?lite=1 -> reportResult),
// so the shared results work without a public engine URL.
import { DbConnection } from './module_bindings';

export { DbConnection };

export type Role = 'admin' | 'editor' | 'viewer';
export type Stage = 'draft' | 'review' | 'approved' | 'archived';
export type Value = { mobility: number; social: number; economy: number; health: number; environment: number; total: number };
export type Person = { id: string; name: string; color: string; online: boolean; workspaceId: string; scenarioId: number; x: number; z: number; lastSeen: Date; me: boolean };
export type Member = Person & { role: Role; joinedAt: Date };
export type Plan = {
  id: number; workspaceId: string; name: string; description: string; createdBy: string; stage: Stage;
  planId: string; status: string; day: number; days: number; editVersion: number; resultVersion: number; error: string;
  computingBy: string; createdAt: Date; updatedAt: Date;
  streets: number; blocks: number; value: Value | null; here: Person[];
};
export type Invite = { code: string; role: Role; uses: number; createdAt: Date };
export type Activity = { id: string; workspaceId: string; scenarioId: number; who: string; color: string; text: string; at: Date };
export type Workspace = {
  id: string; name: string; description: string; color: string; ownerId: string; createdAt: Date; updatedAt: Date;
  myRole: Role; members: Member[]; plans: Plan[]; invites: Invite[]; activity: Activity[]; here: Person[];
};
export type State = {
  connected: boolean; ready: boolean; me: Person | null; workspaces: Workspace[];
  engine: 'off' | 'probing' | 'up' | 'down';
};
// Everything the simulator needs about one plan (the shape older pages used for the single live plan).
export type PlanState = {
  scenario: Plan | null;
  result: {
    scenarioId: string; editVersion: number; cached: boolean; settleMs: number; value: Value;
    metrics: any; delta: any; carDay: number[]; pedDay: number[];
  } | null;
  streets: Set<number>;
  blocks: Map<number, { scale: number; zone: string; authorName: string }>;
  players: Person[]; // people with this plan open
  activity: Activity[];
  role: Role | null;
};

export type LiveOptions = {
  uri?: string; // default ws://<page host>:3000 (ws://localhost:3000 outside a browser)
  db?: string; // default 'commonground'
  token?: string; // identity token; default: the one this browser stored under tokenKey
  tokenKey?: string; // localStorage key for the token (default 'commonground-token')
  name?: string; // calls set_name once connected
  color?: string;
  engine?: string | false; // engine base URL (e.g. http://localhost:8787) to compute pending plans from this page
  onChange?: (state: State, table: string) => void;
  onError?: (err: unknown) => void;
};

const date = (t: { microsSinceUnixEpoch: bigint }) => new Date(Number(t.microsSinceUnixEpoch / 1000n));
const big = (id: string | bigint | number) => BigInt(id);

export function connectLive(opts: LiveOptions = {}) {
  const host = (globalThis as any).location?.hostname || 'localhost';
  const uri = opts.uri ?? `ws://${host}:3000`;
  const tokenKey = opts.tokenKey ?? 'commonground-token';
  const store = {
    get: () => { try { return globalThis.localStorage?.getItem(tokenKey) ?? undefined; } catch { return undefined; } },
    set: (t: string) => { try { globalThis.localStorage?.setItem(tokenKey, t); } catch { /* private mode */ } },
  };
  let myHex = '', connected = false, ready = false;
  let engineState: State['engine'] = opts.engine ? 'probing' : 'off';
  let cursorTimer: ReturnType<typeof setTimeout> | null = null;
  let pendingCursor: { x: number; z: number } | null = null;
  const identities = new Map<string, any>(); // hex -> Identity, for role changes and removals

  const person = (p: any): Person => {
    const id = p.identity.toHexString();
    identities.set(id, p.identity);
    return { id, name: p.name, color: p.color, online: p.online, workspaceId: String(p.workspaceId), scenarioId: p.scenarioId, x: p.cursorX, z: p.cursorZ, lastSeen: date(p.lastSeen), me: id === myHex };
  };
  const valueOf = (r: any): Value => ({ mobility: r.valueMobility, social: r.valueSocial, economy: r.valueEconomy, health: r.valueHealth, environment: r.valueEnvironment, total: r.valueTotal });

  const snapshot = (): State => {
    const db = conn.db;
    const players = new Map<string, Person>();
    for (const p of db.player.iter()) { const x = person(p); players.set(x.id, x); }
    const mine = new Map<string, Role>();
    const membersOf = new Map<string, Member[]>();
    for (const m of db.member.iter()) {
      const id = m.identity.toHexString(), ws = String(m.workspaceId);
      identities.set(id, m.identity);
      if (id === myHex) mine.set(ws, m.role as Role);
      const p = players.get(id) ?? { id, name: 'Someone', color: '#999999', online: false, workspaceId: '0', scenarioId: 0, x: 0, z: 0, lastSeen: date(m.joinedAt), me: id === myHex };
      (membersOf.get(ws) ?? membersOf.set(ws, []).get(ws)!).push({ ...p, role: m.role as Role, joinedAt: date(m.joinedAt) });
    }
    const counts = new Map<number, { s: number; b: number }>();
    const bump = (sc: number, k: 's' | 'b') => { const c = counts.get(sc) ?? { s: 0, b: 0 }; c[k]++; counts.set(sc, c); };
    for (const e of db.streetEdit.iter()) bump(e.scenarioId, 's');
    for (const b of db.blockEdit.iter()) bump(b.scenarioId, 'b');
    const results = new Map<number, any>();
    for (const r of db.resultSummary.iter()) results.set(r.id, r);
    const plansOf = new Map<string, Plan[]>();
    for (const s of db.scenario.iter()) {
      const ws = String(s.workspaceId), r = results.get(s.id), c = counts.get(s.id);
      (plansOf.get(ws) ?? plansOf.set(ws, []).get(ws)!).push({
        id: s.id, workspaceId: ws, name: s.name, description: s.description, createdBy: s.createdBy, stage: s.stage as Stage, planId: s.planId, status: s.status,
        day: s.day, days: s.days, editVersion: s.editVersion, resultVersion: s.resultVersion, error: s.error, computingBy: s.computingBy,
        createdAt: date(s.createdAt), updatedAt: date(s.updatedAt), streets: c?.s ?? 0, blocks: c?.b ?? 0,
        value: r ? valueOf(r) : null, here: [...players.values()].filter(p => p.online && p.scenarioId === s.id),
      });
    }
    const invitesOf = new Map<string, Invite[]>();
    for (const i of (db as any).myInvite.iter()) {
      const ws = String(i.workspaceId);
      (invitesOf.get(ws) ?? invitesOf.set(ws, []).get(ws)!).push({ code: i.code, role: i.role, uses: i.uses, createdAt: date(i.createdAt) });
    }
    const activityOf = new Map<string, Activity[]>();
    for (const a of db.activity.iter()) {
      const ws = String(a.workspaceId);
      (activityOf.get(ws) ?? activityOf.set(ws, []).get(ws)!).push({ id: String(a.id), workspaceId: ws, scenarioId: a.scenarioId, who: a.who, color: a.color, text: a.text, at: date(a.at) });
    }
    const workspaces: Workspace[] = [];
    for (const w of db.workspace.iter()) {
      const id = String(w.id), myRole = mine.get(id);
      if (!myRole) continue;
      workspaces.push({
        id, name: w.name, description: w.description, color: w.color, ownerId: w.owner.toHexString(), createdAt: date(w.createdAt), updatedAt: date(w.updatedAt), myRole,
        members: (membersOf.get(id) ?? []).sort((a, b) => ROLE_ORDER[b.role] - ROLE_ORDER[a.role] || a.joinedAt.getTime() - b.joinedAt.getTime()),
        plans: (plansOf.get(id) ?? []).sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime()),
        invites: (invitesOf.get(id) ?? []).sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime()),
        activity: (activityOf.get(id) ?? []).sort((a, b) => a.at.getTime() - b.at.getTime()).slice(-80),
        here: [...players.values()].filter(p => p.online && p.workspaceId === id),
      });
    }
    workspaces.sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime());
    return { connected, ready, me: players.get(myHex) ?? null, workspaces, engine: engineState };
  };

  const planState = (scenarioId: number): PlanState => {
    const db = conn.db;
    const st = snapshot();
    let scenario: Plan | null = null, role: Role | null = null;
    for (const w of st.workspaces) for (const p of w.plans) if (p.id === scenarioId) { scenario = p; role = w.myRole; }
    const r = db.resultSummary.id.find(scenarioId);
    const ws = scenario ? st.workspaces.find(w => w.id === scenario!.workspaceId) : null;
    return {
      scenario, role,
      result: r ? {
        scenarioId: r.scenarioId, editVersion: r.editVersion, cached: r.cached, settleMs: r.settleMs, value: valueOf(r),
        metrics: JSON.parse(r.metricsJson), delta: JSON.parse(r.deltaJson), carDay: r.carDay, pedDay: r.pedDay,
      } : null,
      streets: new Set([...db.streetEdit.scenarioId.filter(scenarioId)].map(e => e.edgeId)),
      blocks: new Map([...db.blockEdit.scenarioId.filter(scenarioId)].map(b => [b.buildingId, { scale: b.scale, zone: b.zone, authorName: b.authorName }])),
      players: [...db.player.iter()].map(person).filter(p => p.scenarioId === scenarioId),
      activity: (ws?.activity ?? []).filter(a => a.scenarioId === scenarioId || a.scenarioId === 0),
    };
  };

  let notifyQueued = '';
  const changed = (table: string) => () => {
    if (!ready) return;
    // Coalesce bursts (a settle rewrites many rows) into one callback per frame.
    if (notifyQueued) { if (notifyQueued !== table) notifyQueued = '*'; return; }
    notifyQueued = table;
    queueMicrotask(() => { const t = notifyQueued; notifyQueued = ''; opts.onChange?.(snapshot(), t); kickCompute(); });
  };
  const emitNow = (table: string) => opts.onChange?.(snapshot(), table);

  const conn = DbConnection.builder()
    .withUri(uri)
    .withDatabaseName(opts.db ?? 'commonground')
    .withToken(opts.token ?? store.get())
    .onConnect((c, identity, token) => {
      myHex = identity.toHexString();
      connected = true;
      store.set(token);
      c.subscriptionBuilder()
        .onApplied(() => {
          ready = true;
          if (opts.name) c.reducers.setName({ name: opts.name });
          if (opts.color) c.reducers.setColor({ color: opts.color });
          emitNow('*');
          kickCompute();
        })
        .onError((_ctx: unknown) => opts.onError?.(new Error('subscription failed')))
        .subscribe([
          'SELECT * FROM workspace', 'SELECT * FROM member', 'SELECT * FROM my_invite', 'SELECT * FROM scenario',
          'SELECT * FROM result_summary', 'SELECT * FROM street_edit', 'SELECT * FROM block_edit',
          'SELECT * FROM player', 'SELECT * FROM activity',
        ]);
    })
    .onDisconnect(() => { connected = false; emitNow('*'); })
    .onConnectError((_ctx, err) => opts.onError?.(err))
    .build();

  for (const [name, table] of Object.entries({
    workspace: conn.db.workspace, member: conn.db.member, my_invite: (conn.db as any).myInvite, scenario: conn.db.scenario,
    result_summary: conn.db.resultSummary, street_edit: conn.db.streetEdit, block_edit: conn.db.blockEdit,
    player: conn.db.player, activity: conn.db.activity,
  })) {
    const cb = changed(name);
    (table as any).onInsert?.(cb);
    (table as any).onDelete?.(cb);
    (table as any).onUpdate?.(cb);
  }

  // ── browser-side compute ──
  const engineBase = opts.engine ? String(opts.engine).replace(/\/$/, '') : '';
  const working = new Set<number>();
  let lastProbe = 0;
  async function probeEngine() {
    if (!engineBase || engineState === 'up') return engineState === 'up';
    if (Date.now() - lastProbe < 15000 && engineState === 'down') return false;
    lastProbe = Date.now();
    try {
      const r = await fetch(`${engineBase}/health`, { cache: 'no-store' });
      const h = r.ok ? await r.json() : null;
      engineState = h && h.baseline_ready ? 'up' : 'down';
    } catch { engineState = 'down'; }
    emitNow('engine');
    return engineState === 'up';
  }
  let kickTimer: ReturnType<typeof setTimeout> | null = null;
  function kickCompute() {
    if (!engineBase || kickTimer) return;
    kickTimer = setTimeout(() => { kickTimer = null; runPending(); }, 400); // debounce paint strokes
  }
  async function runPending() {
    if (!ready || !(await probeEngine())) { if (engineBase && engineState === 'down') setTimeout(kickCompute, 15000); return; }
    const now = Date.now();
    for (const s of conn.db.scenario.iter()) {
      if (working.has(s.id) || s.editVersion <= s.resultVersion) continue;
      const stale = s.status === 'computing' && now - date(s.computingSince).getTime() > 30000;
      if (s.status !== 'pending' && !stale) continue;
      if (![...conn.db.member.by_ws_identity.filter([s.workspaceId, identities.get(myHex)])].length) continue;
      runOne(s.id, s.editVersion);
      return; // one at a time: the engine computes serially anyway
    }
  }
  async function runOne(scenarioId: number, editVersion: number) {
    working.add(scenarioId);
    try {
      await conn.reducers.claimCompute({ scenarioId, editVersion });
      // The claim is ours once the row says so (the update may land just after the reducer resolves).
      let s: any = null;
      for (let i = 0; i < 20; i++) {
        s = conn.db.scenario.id.find(scenarioId);
        if (!s || s.computingBy === myHex || s.editVersion !== editVersion) break;
        await new Promise(r => setTimeout(r, 50));
      }
      if (!s || s.computingBy !== myHex || s.editVersion !== editVersion) return;
      const pedestrianized = [...conn.db.streetEdit.scenarioId.filter(scenarioId)].map(e => e.edgeId).sort((a, b) => a - b);
      const blocks: Record<string, { scale: number; zone?: string }> = {};
      for (const b of conn.db.blockEdit.scenarioId.filter(scenarioId)) blocks[String(b.buildingId)] = b.zone ? { scale: b.scale, zone: b.zone } : { scale: b.scale };
      let report: any;
      try {
        const res = await fetch(`${engineBase}/scenario?lite=1`, {
          method: 'POST', headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ name: s.name, edits: { pedestrianized, blocks } }),
        });
        const text = await res.text();
        if (!res.ok) throw new Error(`engine ${res.status}: ${text.slice(0, 200)}`);
        const r = JSON.parse(text), v = r.value;
        report = {
          planId: r.id, cached: !!r.cached, settleMs: Math.round(r.settle?.ms ?? 0), days: r.settle?.days ?? 5,
          valueMobility: v.mobility, valueSocial: v.social, valueEconomy: v.economy, valueHealth: v.health, valueEnvironment: v.environment ?? 0, valueTotal: v.total,
          metricsJson: JSON.stringify(r.metrics), deltaJson: JSON.stringify(r.delta), carDay: r.edges.car_day, pedDay: r.edges.ped_day, error: '',
        };
      } catch (e) {
        engineState = 'down';
        report = {
          planId: '', cached: false, settleMs: 0, days: 0, valueMobility: 0, valueSocial: 0, valueEconomy: 0, valueHealth: 0, valueEnvironment: 0, valueTotal: 0,
          metricsJson: '{}', deltaJson: '{}', carDay: [], pedDay: [], error: `engine error: ${String((e as Error)?.message ?? e).slice(0, 200)}`,
        };
      }
      await conn.reducers.reportResult({ scenarioId, editVersion, ...report });
    } catch (e) {
      opts.onError?.(e);
    } finally {
      working.delete(scenarioId);
      kickCompute();
    }
  }

  const call = <T>(p: Promise<T> | T) => Promise.resolve(p).catch(err => { opts.onError?.(err); throw err; });
  const ident = (hex: string) => { const i = identities.get(hex); if (!i) throw new Error('unknown member'); return i; };
  return {
    conn,
    state: snapshot,
    planState,
    identity: () => myHex,
    // workspaces
    createWorkspace: (name: string, description = '') => call(conn.reducers.createWorkspace({ name, description })),
    updateWorkspace: (workspaceId: string, name: string, description = '') => call(conn.reducers.updateWorkspace({ workspaceId: big(workspaceId), name, description })),
    deleteWorkspace: (workspaceId: string) => call(conn.reducers.deleteWorkspace({ workspaceId: big(workspaceId) })),
    // members and invites
    createInvite: (workspaceId: string, role: Role = 'editor') => call(conn.reducers.createInvite({ workspaceId: big(workspaceId), role })),
    revokeInvite: (code: string) => call(conn.reducers.revokeInvite({ code })),
    join: (code: string) => call(conn.reducers.joinWorkspace({ code })),
    setRole: (workspaceId: string, memberId: string, role: Role) => call(conn.reducers.setMemberRole({ workspaceId: big(workspaceId), identity: ident(memberId), role })),
    removeMember: (workspaceId: string, memberId: string) => call(conn.reducers.removeMember({ workspaceId: big(workspaceId), identity: ident(memberId) })),
    leave: (workspaceId: string) => call(conn.reducers.removeMember({ workspaceId: big(workspaceId), identity: ident(myHex) })),
    // plans
    createPlan: (workspaceId: string, name: string, description = '', copyFrom = 0) => call(conn.reducers.createPlan({ workspaceId: big(workspaceId), name, description, copyFrom })),
    updatePlan: (scenarioId: number, name: string, description = '') => call(conn.reducers.updatePlan({ scenarioId, name, description })),
    setStage: (scenarioId: number, stage: Stage) => call(conn.reducers.setPlanStage({ scenarioId, stage })),
    deletePlan: (scenarioId: number) => call(conn.reducers.deletePlan({ scenarioId })),
    recompute: (scenarioId: number) => call(conn.reducers.recompute({ scenarioId })),
    // edits
    setPedestrian: (scenarioId: number, edgeIds: number[], on = true) => call(conn.reducers.setPedestrian({ scenarioId, edgeIds, on })),
    setBlock: (scenarioId: number, buildingIds: number[], scale: number, zone = '') => call(conn.reducers.setBlock({ scenarioId, buildingIds, scale, zone })),
    reset: (scenarioId: number) => call(conn.reducers.reset({ scenarioId })),
    // people
    setName: (name: string) => call(conn.reducers.setName({ name })),
    setColor: (color: string) => call(conn.reducers.setColor({ color })),
    setPresence: (workspaceId: string | number, scenarioId = 0) => call(conn.reducers.setPresence({ workspaceId: big(workspaceId || 0), scenarioId })),
    // Throttled to ~10/s so a moving pointer doesn't flood the server.
    setCursor: (x: number, z: number) => {
      pendingCursor = { x, z };
      if (cursorTimer) return;
      cursorTimer = setTimeout(() => {
        cursorTimer = null;
        if (pendingCursor) conn.reducers.setCursor(pendingCursor);
        pendingCursor = null;
      }, 100);
    },
    disconnect: () => conn.disconnect(),
  };
}

const ROLE_ORDER: Record<Role, number> = { viewer: 0, editor: 1, admin: 2 };
