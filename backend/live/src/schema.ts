// Tables for the live layer. SpacetimeDB holds the shared plan (edits), who is here (presence)
// and the latest engine result; the Python engine on :8787 does the compute.
import { schema, table, t } from 'spacetimedb/server';

// Singleton (id 1): the live plan everyone edits.
// status: 'pending' (edits waiting for the debounce) | 'computing' | 'ready' | 'error'.
// editVersion bumps on every edit; resultVersion is the editVersion the current result reflects.
const scenario = table(
  { name: 'scenario', public: true },
  {
    id: t.u32().primaryKey(),
    name: t.string(),
    planId: t.string(), // API scenario id of the latest result ('' until the first run)
    status: t.string(),
    day: t.u8(), // replanning day k of `days`; the engine reports only the final day
    days: t.u8(),
    editVersion: t.u32(),
    resultVersion: t.u32(),
    error: t.string(),
    updatedAt: t.timestamp(),
  }
);

// One row per car-free street edge (edge id = index into world.edges).
const streetEdit = table(
  { name: 'street_edit', public: true },
  {
    edgeId: t.u32().primaryKey(),
    author: t.identity(),
    authorName: t.string(),
    at: t.timestamp(),
  }
);

// One row per edited building (building id = index into world.buildings). zone '' keeps its own use.
const blockEdit = table(
  { name: 'block_edit', public: true },
  {
    buildingId: t.u32().primaryKey(),
    scale: t.f32(),
    zone: t.string(),
    author: t.identity(),
    authorName: t.string(),
    at: t.timestamp(),
  }
);

const player = table(
  { name: 'player', public: true },
  {
    identity: t.identity().primaryKey(),
    name: t.string(),
    color: t.string(),
    online: t.bool(),
    cursorX: t.f32(), // world coordinates (metres, same frame as world.json x/z)
    cursorZ: t.f32(),
    lastSeen: t.timestamp(),
  }
);

// Human-readable feed ("Planner 2 made 2nd Street car-free").
const activity = table(
  { name: 'activity', public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    who: t.string(),
    color: t.string(),
    text: t.string(),
    at: t.timestamp(),
  }
);

// Singleton (id 1): the latest POST /scenario?lite=1 result for the live plan.
// metricsJson / deltaJson are the API's `metrics` and `delta` objects verbatim.
const resultSummary = table(
  { name: 'result_summary', public: true },
  {
    id: t.u32().primaryKey(),
    scenarioId: t.string(),
    editVersion: t.u32(),
    cached: t.bool(),
    settleMs: t.u32(),
    valueMobility: t.f64(),
    valueSocial: t.f64(),
    valueEconomy: t.f64(),
    valueHealth: t.f64(),
    valueEnvironment: t.f64(),
    valueTotal: t.f64(),
    metricsJson: t.string(),
    deltaJson: t.string(),
    carDay: t.array(t.f32()), // indexed by edge id
    pedDay: t.array(t.f32()),
    updatedAt: t.timestamp(),
  }
);

// Private singleton (id 1). owner is whoever published the module (init's sender); only they can
// change engineUrl. SpacetimeDB refuses module HTTP to private addresses, so engineUrl must be a
// public address (see README: "Engine URL").
const config = table(
  { name: 'config' },
  {
    id: t.u32().primaryKey(),
    owner: t.identity(),
    engineUrl: t.string(),
  }
);

// Debounce timer for the compute call. At most one pending row at a time.
const computeJob = table(
  { name: 'compute_job' },
  {
    scheduledId: t.u64().primaryKey().autoInc(),
    scheduledAt: t.scheduleAt(),
  }
);

const spacetimedb = schema({
  scenario, streetEdit, blockEdit, player, activity, resultSummary, config, computeJob,
});
export default spacetimedb;
export { computeJob };
