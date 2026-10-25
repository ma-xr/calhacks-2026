// Browser/Node client for the live layer. Bundled with the SpacetimeDB SDK into client/dist/live.mjs,
// so a page without a bundler can `import { connectLive } from './live.mjs'`.
import { DbConnection } from './module_bindings';

export { DbConnection };

export type LiveState = {
  scenario: { planId: string; status: string; day: number; days: number; editVersion: number; resultVersion: number; error: string } | null;
  result: {
    scenarioId: string; editVersion: number; cached: boolean; settleMs: number;
    value: { mobility: number; social: number; economy: number; health: number; environment: number; total: number };
    metrics: any; delta: any; carDay: number[]; pedDay: number[];
  } | null;
  streets: Set<number>; // car-free edge ids in the live plan
  blocks: Map<number, { scale: number; zone: string; authorName: string }>;
  players: Array<{ id: string; name: string; color: string; online: boolean; x: number; z: number; me: boolean }>;
  activity: Array<{ who: string; color: string; text: string; at: Date }>;
};

export type LiveOptions = {
  uri?: string; // default ws://<page host>:3000 (ws://localhost:3000 outside a browser)
  db?: string; // default 'human-live'
  name?: string; // calls set_name once connected
  onChange?: (state: LiveState, table: string) => void;
  onError?: (err: unknown) => void;
};

const TOKEN_KEY = 'human-live-token';
const store = {
  get: () => { try { return globalThis.localStorage?.getItem(TOKEN_KEY) ?? undefined; } catch { return undefined; } },
  set: (t: string) => { try { globalThis.localStorage?.setItem(TOKEN_KEY, t); } catch { /* private mode */ } },
};

export function connectLive(opts: LiveOptions = {}) {
  const host = (globalThis as any).location?.hostname || 'localhost';
  const uri = opts.uri ?? `ws://${host}:3000`;
  let myHex = '';
  let cursorTimer: ReturnType<typeof setTimeout> | null = null;
  let pendingCursor: { x: number; z: number } | null = null;

  const snapshot = (): LiveState => {
    const db = conn.db;
    const sc = db.scenario.id.find(1);
    const r = db.resultSummary.id.find(1);
    return {
      scenario: sc ? { planId: sc.planId, status: sc.status, day: sc.day, days: sc.days, editVersion: sc.editVersion, resultVersion: sc.resultVersion, error: sc.error } : null,
      result: r ? {
        scenarioId: r.scenarioId, editVersion: r.editVersion, cached: r.cached, settleMs: r.settleMs,
        value: { mobility: r.valueMobility, social: r.valueSocial, economy: r.valueEconomy, health: r.valueHealth, environment: r.valueEnvironment, total: r.valueTotal },
        metrics: JSON.parse(r.metricsJson), delta: JSON.parse(r.deltaJson), carDay: r.carDay, pedDay: r.pedDay,
      } : null,
      streets: new Set([...db.streetEdit.iter()].map(e => e.edgeId)),
      blocks: new Map([...db.blockEdit.iter()].map(b => [b.buildingId, { scale: b.scale, zone: b.zone, authorName: b.authorName }])),
      players: [...db.player.iter()].map(p => {
        const id = p.identity.toHexString();
        return { id, name: p.name, color: p.color, online: p.online, x: p.cursorX, z: p.cursorZ, me: id === myHex };
      }),
      activity: [...db.activity.iter()]
        .map(a => ({ who: a.who, color: a.color, text: a.text, at: new Date(Number(a.at.microsSinceUnixEpoch / 1000n)) }))
        .sort((a, b) => a.at.getTime() - b.at.getTime()),
    };
  };
  const changed = (table: string) => () => opts.onChange?.(snapshot(), table);

  const conn = DbConnection.builder()
    .withUri(uri)
    .withDatabaseName(opts.db ?? 'human-live')
    .withToken(store.get())
    .onConnect((c, identity, token) => {
      myHex = identity.toHexString();
      store.set(token);
      c.subscriptionBuilder()
        .onApplied(() => {
          if (opts.name) c.reducers.setName({ name: opts.name });
          opts.onChange?.(snapshot(), '*');
        })
        .onError((_ctx: unknown) => opts.onError?.(new Error('subscription failed')))
        .subscribe([
          'SELECT * FROM scenario', 'SELECT * FROM result_summary', 'SELECT * FROM street_edit',
          'SELECT * FROM block_edit', 'SELECT * FROM player', 'SELECT * FROM activity',
        ]);
    })
    .onConnectError((_ctx, err) => opts.onError?.(err))
    .build();

  for (const [name, table] of Object.entries({
    scenario: conn.db.scenario, result_summary: conn.db.resultSummary, street_edit: conn.db.streetEdit,
    block_edit: conn.db.blockEdit, player: conn.db.player, activity: conn.db.activity,
  })) {
    const cb = changed(name);
    (table as any).onInsert(cb);
    (table as any).onDelete(cb);
    (table as any).onUpdate?.(cb);
  }

  const call = <T>(p: Promise<T> | T) => Promise.resolve(p).catch(err => { opts.onError?.(err); throw err; });
  return {
    conn,
    state: snapshot,
    setPedestrian: (edgeIds: number[], on = true) => call(conn.reducers.setPedestrian({ edgeIds, on })),
    setBlock: (buildingIds: number[], scale: number, zone = '') => call(conn.reducers.setBlock({ buildingIds, scale, zone })),
    reset: () => call(conn.reducers.reset({})),
    setName: (name: string) => call(conn.reducers.setName({ name })),
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
