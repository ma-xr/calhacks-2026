// Tables for the live layer. SpacetimeDB holds workspaces (teams), their members and invites, every
// workspace's plans (edits), who is here (presence) and each plan's latest engine result; the Python
// engine on :8787 does the compute.
import { schema, table, t } from 'spacetimedb/server';

// ── Workspaces ──
// A team that shares plans. The creator is its first admin.
const workspace = table(
  { name: 'workspace', public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    name: t.string(),
    description: t.string(),
    color: t.string(),
    owner: t.identity(),
    createdAt: t.timestamp(),
    updatedAt: t.timestamp(),
  }
);

// role: 'admin' (manage members, invites, the workspace) | 'editor' (edit plans) | 'viewer' (watch).
const member = table(
  {
    name: 'member', public: true,
    indexes: [{ accessor: 'by_ws_identity', algorithm: 'btree', columns: ['workspaceId', 'identity'] }],
  },
  {
    id: t.u64().primaryKey().autoInc(),
    workspaceId: t.u64(),
    identity: t.identity().index('btree'),
    role: t.string(),
    joinedAt: t.timestamp(),
  }
);

// Private: invite links. Admins see their workspaces' invites through the my_invite view.
const invite = table(
  { name: 'invite' },
  {
    code: t.string().primaryKey(),
    workspaceId: t.u64().index('btree'),
    role: t.string(),
    createdBy: t.identity(),
    createdAt: t.timestamp(),
    uses: t.u32(),
  }
);

// ── Plans ──
// One row per plan. status: 'pending' (edits waiting for a compute) | 'computing' | 'ready' | 'error'.
// editVersion bumps on every edit; resultVersion is the editVersion the current result reflects.
// A compute runs in the module (when config.engineUrl is set) or in a member's browser that can reach
// the engine (claimCompute / reportResult); computingBy/computingSince make sure only one runs at a time.
const scenario = table(
  { name: 'scenario', public: true },
  {
    id: t.u32().primaryKey().autoInc(),
    workspaceId: t.u64().index('btree'),
    name: t.string(),
    description: t.string(),
    createdBy: t.string(),
    stage: t.string(), // the team's workflow: 'draft' | 'review' | 'approved' | 'archived'
    planId: t.string(), // API scenario id of the latest result ('' until the first run)
    status: t.string(),
    day: t.u8(), // replanning day k of `days`; the engine reports only the final day
    days: t.u8(),
    editVersion: t.u32(),
    resultVersion: t.u32(),
    error: t.string(),
    computingBy: t.string(), // identity hex of the browser running the compute, '' = module or nobody
    computingSince: t.timestamp(),
    createdAt: t.timestamp(),
    updatedAt: t.timestamp(),
  }
);

// One row per car-free street edge per plan. id = scenarioId << 32 | edgeId (edge id = index into world.edges).
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

// One row per edited building per plan. id = scenarioId << 32 | buildingId. zone '' keeps its own use.
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

// ── People ──
// workspaceId / scenarioId: where this person is right now (0 = nowhere), for presence and cursors.
const player = table(
  { name: 'player', public: true },
  {
    identity: t.identity().primaryKey(),
    name: t.string(),
    color: t.string(),
    online: t.bool(),
    workspaceId: t.u64(),
    scenarioId: t.u32(),
    cursorX: t.f32(), // world coordinates (metres, same frame as world.json x/z)
    cursorZ: t.f32(),
    lastSeen: t.timestamp(),
  }
);

// Human-readable feed per workspace ("Maya made 3 street segments car-free"). scenarioId 0 = workspace-level.
const activity = table(
  { name: 'activity', public: true },
  {
    id: t.u64().primaryKey().autoInc(),
    workspaceId: t.u64().index('btree'),
    scenarioId: t.u32(),
    who: t.string(),
    color: t.string(),
    text: t.string(),
    at: t.timestamp(),
  }
);

// The latest POST /scenario?lite=1 result per plan (id = scenario id).
// metricsJson / deltaJson are the API's `metrics` and `delta` objects verbatim.
const resultSummary = table(
  { name: 'result_summary', public: true },
  {
    id: t.u32().primaryKey(),
    workspaceId: t.u64().index('btree'),
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
// public address (see README: "Engine URL"). '' = computes run in members' browsers only.
const config = table(
  { name: 'config' },
  {
    id: t.u32().primaryKey(),
    owner: t.identity(),
    engineUrl: t.string(),
  }
);

// Debounce timer for a plan's module-side compute. At most one pending row per plan.
const computeJob = table(
  { name: 'compute_job' },
  {
    scheduledId: t.u64().primaryKey().autoInc(),
    scheduledAt: t.scheduleAt(),
    scenarioId: t.u32().index('btree'),
  }
);

const spacetimedb = schema({
  workspace, member, invite, scenario, streetEdit, blockEdit, player, activity, resultSummary, config, computeJob,
});
export default spacetimedb;
export { computeJob, invite };
