# Website live layer (SpacetimeDB)

The CommonGround website (`mockup/site/`) runs on this module, database **`commonground`**. It is separate from `backend/live/` (database `human-live`), which powers Go live inside the 3D app.

People form **workspaces** (teams), invite each other with links, and edit the workspace's **plans** together in real time. SpacetimeDB holds workspaces, members, invites, every plan's edits, presence and each plan's latest result. The Python engine on `:8787` stays the compute layer.

```
browsers ──ws──▶ SpacetimeDB :3000 (module `commonground`)
   create_workspace / join_workspace / create_plan / set_pedestrian / set_block / …   (reducers)
        │  every edit bumps the plan's edit_version and marks it 'pending'
        ▼
   compute, one of:
     a) a member's browser that can reach the engine: claim_compute → POST :8787/scenario?lite=1 → report_result
     b) the module itself (scheduled `compute` procedure), when set_engine_url points at a public address
        │  writes result_summary + scenario.status, which every subscriber gets pushed
        ▼
   subscribers re-render (same plan, same numbers, everyone's cursors)
```

Browser-side compute (a) is the default, because SpacetimeDB refuses module HTTP to private addresses (see "Engine URL"). Any page that runs the client with `engine` set (the website does) picks up pending plans of the workspaces its person belongs to. Claims expire after 30 s, so a closed tab doesn't stall a plan. Edits made during a compute are not lost: the result is written as stale and the plan goes back to `pending`.

Measured locally: a fresh plan takes about **3 s** from `set_pedestrian` to the pushed result (the engine takes about 2.7 s of that). A plan the engine has cached takes about 0.4 s.

## Run it

`run.ps1` at the repo root does all of this on Windows. By hand, with the engine running and the CLI (v2.13) installed:

```bash
spacetime start
# second terminal, from backend/workspaces/
npm install
npm run publish:local      # spacetime publish commonground --server local --yes
npm run e2e                # optional: two people, invite, shared edit, shared result, viewer refused
```

Use `spacetime publish commonground --server local --delete-data=always --yes` to start from an empty database (needed after most schema changes). After a schema change, run `npm run build:client` to regenerate `client/module_bindings/` and `client/dist/live.mjs` (it also copies the bundle to `mockup/site/live.mjs`).

### Engine URL (optional: module-side compute)

SpacetimeDB refuses procedure HTTP to **private or special-purpose addresses** (`localhost`, `127.0.0.1`, `10/8`, `192.168/16`, `172.16/12`, `fd00::/8`), and no config turns that off. To have the module compute without any browser open, put the engine behind a public URL and run `spacetime call commonground set_engine_url '"https://<public-host>/scenario?lite=1"' --server local`. Only the identity that published the module can call it; `''` switches back to browser-side compute.

## Roles

| Role | Can |
|---|---|
| `admin` | everything editors can, plus rename/delete the workspace, create and revoke invite links, change roles, remove members |
| `editor` | create, rename, duplicate, reset and delete plans; edit them; move them between workflow stages |
| `viewer` | watch plans live (results, cursors, activity); can't change anything |

A workspace always keeps at least one admin. Reducers check membership with `ctx.sender`.

## Schema

| Table | Key | What |
|---|---|---|
| `workspace` | `id` | `name`, `description`, `color`, `owner` |
| `member` | `id` (index `by_ws_identity`) | `workspace_id`, `identity`, `role`, `joined_at` |
| `invite` (private) | `code` | `workspace_id`, `role`, `uses`. Admins read their workspaces' links through the **`my_invite` view** |
| `scenario` | `id` | a plan: `workspace_id`, `name`, `description`, `stage` (`draft`, `review`, `approved`, `archived`), `status` (`pending`, `computing`, `ready`, `error`), `edit_version`, `result_version`, `plan_id` (API scenario id of the latest result), `computing_by` / `computing_since` (the browser claim) |
| `street_edit` | `id` = scenario << 32 \| edge | car-free edges per plan: `scenario_id`, `edge_id`, `author_name` |
| `block_edit` | `id` = scenario << 32 \| building | `scale` (0.25–4), `zone` (`res`, `office`, `retail`, `mixed`, or `''` for the building's own use) |
| `player` | `identity` | `name`, `color`, `online`, `workspace_id` / `scenario_id` (where they are now), `cursor_x` / `cursor_z` (world metres) |
| `activity` | `id` | feed per workspace: `scenario_id` (0 = workspace-level), `who`, `color`, `text` |
| `result_summary` | `id` = scenario id | `value_*` ($/yr vs baseline), `metrics_json` / `delta_json` (the API's `metrics` / `delta`), `car_day` / `ped_day` (per edge id) |
| `config` (private) | `id` = 1 | `owner`, `engine_url` |

Reducers: workspaces `create_workspace(name, description)` (also creates an editor invite and **Plan A**), `update_workspace`, `delete_workspace`; people `create_invite(workspace_id, role)`, `revoke_invite(code)`, `join_workspace(code)`, `set_member_role`, `remove_member` (yourself = leave); plans `create_plan(workspace_id, name, description, copy_from)`, `update_plan`, `set_plan_stage`, `delete_plan`; edits `set_pedestrian(scenario_id, edge_ids, on)`, `set_block(scenario_id, building_ids, scale, zone)`, `reset(scenario_id)`, `recompute(scenario_id)`; compute `claim_compute`, `report_result`, `set_engine_url` (owner only); presence `set_name`, `set_color`, `set_presence(workspace_id, scenario_id)`, `set_cursor(x, z)`.

Public tables are readable by any connected client (the site only shows a person their own workspaces). Invite codes are private. Moving the other tables behind per-member views is the next step if this leaves the demo stage.

## JS client

`client/dist/live.mjs` is a single ES module: the SpacetimeDB SDK, the generated bindings, and `connectLive`. It needs no bundler.

```js
import { connectLive } from './live.mjs';
const live = connectLive({
  tokenKey: 'commonground-token',        // localStorage key for this person's identity token
  engine: 'http://localhost:8787',     // optional: compute pending plans from this page
  onChange(state, table) {
    // state.me, state.engine ('up' | 'down' | …), state.workspaces: [{ id, name, myRole, members, plans, invites, activity, here }]
    // plan: { id, name, stage, status, editVersion, resultVersion, streets, blocks, value: { total, mobility, … }, here }
  },
});
await live.createWorkspace('SoMa Streets Team', 'Car-free 2nd St');
const plan = live.state().workspaces[0].plans[0];
live.setPedestrian(plan.id, [1070, 832], true);
live.planState(plan.id);   // { scenario, result (with metrics/delta), streets: Set, blocks: Map, players, activity, role }
```

The website (`mockup/site/`) uses it; `npm run bundle` copies it to `mockup/site/live.mjs`. For the full result (hourly arrays, trips, POIs), fetch `GET :8787/scenario/{result.scenarioId}`.

## Files

- `src/schema.ts`: tables · `src/index.ts`: reducers, the `my_invite` view, lifecycle and the `compute` procedure
- `client/live.ts` → `client/dist/live.mjs`: the browser client (`npm run build:client`; typecheck with `npx tsc --noEmit -p client`)
- `client/module_bindings/`: generated (`npm run generate`)
- `scripts/e2e.mjs`: end-to-end check

