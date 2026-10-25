// Tables for the living city. Static geometry (roads, buildings, POIs) lives in world.json,
// which the module and the viewer share; tables hold only what changes.
import { schema, table, t } from 'spacetimedb/server';

// One row per scenario. Scenario 1 is the locked baseline; every other scenario is a plan.
const scenario = table(
  { name: 'scenario', public: true },
  {
    id: t.u32().primaryKey(),
    name: t.string(),
    isPlan: t.bool(),
    // 'ready' or 'settling'. While settling, `day` counts replanning days done (of SETTLE_DAYS).
    status: t.string(),
    day: t.u8(),
    editVersion: t.u32(),
    settledVersion: t.u32(),
    updatedAt: t.timestamp(),
  }
);

// ── Edits (the plan) ──
// id = scenarioId << 32 | edgeId, so a street is pedestrianized at most once per scenario.
const streetEdit = table(
  { name: 'street_edit', public: true },
  {
    id: t.u64().primaryKey(),
    scenarioId: t.u32().index('btree'),
    edgeId: t.u32(),
    author: t.identity(),
    authorName: t.string(),
    at: t.timestamp(),
  }
);
// id = scenarioId << 32 | buildingId. zone '' keeps the building's own use.
const blockEdit = table(
  { name: 'block_edit', public: true },
  {
    id: t.u64().primaryKey(),
    scenarioId: t.u32().index('btree'),
    buildingId: t.u32(),
    scale: t.f32(),
    zone: t.string(),
    author: t.identity(),
    authorName: t.string(),
    at: t.timestamp(),
  }
);
// City-wide levers. kind: 'congestion_charge' (target = car inlet key or '' for all) | 'parking_price'.
const policy = table(
  { name: 'policy', public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    scenarioId: t.u32().index('btree'),
    kind: t.string(),
    target: t.string(),
    amount: t.f32(),
    author: t.identity(),
    authorName: t.string(),
    at: t.timestamp(),
  }
);

// ── Settle loop ──
// One scheduled row per scenario that is settling. Each run is one replanning day.
const settleJob = table(
  { name: 'settle_job' },
  {
    scheduledId: t.u64().primaryKey().autoInc(),
    scheduledAt: t.scheduleAt(),
    scenarioId: t.u32().index('btree'),
    editVersion: t.u32(),
    day: t.u8(),
    cong: t.array(t.f32()),
  }
);

// ── Results ──
// Daily totals and City Value vs the baseline ($/yr; zero for the baseline itself).
const metrics = table(
  { name: 'metrics', public: true },
  {
    scenarioId: t.u32().primaryKey(),
    persons: t.u32(),
    car: t.u32(),
    transit: t.u32(),
    gone: t.u32(),
    vmt: t.f64(),
    vehH: t.f64(),
    delayH: t.f64(),
    walkMin: t.f64(),
    revenue: t.f64(),
    encounters: t.f64(),
    ties: t.f64(),
    jobs: t.f64(),
    residents: t.f64(),
    floorDelta: t.f64(),
    tierTime: t.array(t.f32()),
    tierWalk: t.array(t.f32()),
    valueMobility: t.f64(),
    valueSocial: t.f64(),
    valueEconomy: t.f64(),
    valueHealth: t.f64(),
    valueTotal: t.f64(),
    updatedAt: t.timestamp(),
  }
);
// Per-edge arrays indexed by world.json edge id: car and pedestrian trips/day, congestion factor.
const edgeFlow = table(
  { name: 'edge_flow', public: true },
  {
    scenarioId: t.u32().primaryKey(),
    carFlow: t.array(t.f32()),
    pedFlow: t.array(t.f32()),
    cong: t.array(t.f32()),
  }
);
// Visits/day per business. Base POIs are indexed by engine BASE_POIS id; plan-only shops are rows below.
const poiVisits = table(
  { name: 'poi_visits', public: true },
  {
    scenarioId: t.u32().primaryKey(),
    visits: t.array(t.f32()),
  }
);
const virtualPoi = table(
  { name: 'virtual_poi', public: true },
  {
    id: t.u64().primaryKey(),
    scenarioId: t.u32().index('btree'),
    poiId: t.u32(),
    name: t.string(),
    category: t.string(),
    x: t.f32(),
    z: t.f32(),
    visits: t.f32(),
  }
);
// id = scenarioId << 32 | personId. mode: 'car' | 'transit' | 'gone' (trip evaporated).
const sim = table(
  { name: 'sim', public: true },
  {
    id: t.u64().primaryKey(),
    scenarioId: t.u32().index('btree'),
    personId: t.u32(),
    name: t.string(),
    kind: t.string(),
    income: t.u8(),
    region: t.string(),
    mode: t.string(),
    homeBuilding: t.i32(),
    officeBuilding: t.i32(),
    lunchPoi: t.i32(),
  }
);
// id = scenarioId << 32 | personId * 16 + leg. steps: edgeId * 2 + (1 if walked b→a).
// The viewer interpolates movement from t0/dur, so the server writes only when plans change.
const trip = table(
  { name: 'trip', public: true },
  {
    id: t.u64().primaryKey(),
    scenarioId: t.u32().index('btree'),
    personId: t.u32(),
    leg: t.string(),
    mode: t.string(),
    t0: t.f32(),
    dur: t.f32(),
    len: t.f32(),
    steps: t.array(t.u32()),
    trimHead: t.u16(),
    trimTail: t.u16(),
    poiId: t.i32(),
    dwell: t.f32(),
    inlet: t.i8(),
    outlet: t.i8(),
  }
);
// Social ties formed at a shared lunch or outing (capped sample per scenario).
const tie = table(
  { name: 'tie', public: true },
  {
    id: t.u64().primaryKey(),
    scenarioId: t.u32().index('btree'),
    a: t.u32(),
    b: t.u32(),
    poiId: t.u32(),
  }
);

// ── People and narration ──
const player = table(
  { name: 'player', public: true },
  {
    identity: t.identity().primaryKey(),
    name: t.string(),
    color: t.string(),
    online: t.bool(),
    scenarioId: t.u32(),
    cursorX: t.f32(),
    cursorZ: t.f32(),
    lastSeen: t.timestamp(),
  }
);
// Citizen feed. Written by the narrator (Claude) from the sims' actual trips. personId -1 = no sim.
const citizenPost = table(
  { name: 'citizen_post', public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    scenarioId: t.u32().index('btree'),
    personId: t.i32(),
    author: t.string(),
    text: t.string(),
    tag: t.string(),
    at: t.timestamp(),
  }
);
// Human-readable log of who changed what ("Maximilian Thiersch made 2nd St car-free").
const activity = table(
  { name: 'activity', public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    scenarioId: t.u32().index('btree'),
    who: t.string(),
    text: t.string(),
    at: t.timestamp(),
  }
);
// Singleton (id 0): demo heroes picked from the baseline at init.
const worldMeta = table(
  { name: 'world_meta', public: true },
  {
    id: t.u32().primaryKey(),
    scale: t.u32(),
    mariaId: t.u32(),
    devId: t.u32(),
    heroEdges: t.array(t.u32()),
  }
);

const spacetimedb = schema({
  scenario, streetEdit, blockEdit, policy, settleJob,
  metrics, edgeFlow, poiVisits, virtualPoi, sim, trip, tie,
  player, citizenPost, activity, worldMeta,
});
export default spacetimedb;
export { settleJob };
