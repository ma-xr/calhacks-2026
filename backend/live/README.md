# Live layer (SpacetimeDB)

Several people (judges on phones, us on laptops) edit **one shared plan** in real time. SpacetimeDB holds the plan, presence and the latest result; the Python engine on `:8787` stays the compute layer.

```
phones / laptops ──ws──▶ SpacetimeDB :3000 (module `human-live`)
   set_pedestrian / set_block / reset / set_name / set_cursor  (reducers)
        │  every edit bumps scenario.edit_version and arms a 400 ms debounce
        ▼
   compute (scheduled procedure) ── ctx.http.fetch POST /scenario?lite=1 ──▶ engine :8787
        │  writes result_summary + scenario.status, which every subscriber gets pushed
        ▼
   subscribers re-render (same plan, same numbers, everyone's cursors)
```

Measured locally: a fresh plan takes about **1.5 s** from `set_pedestrian` to the pushed `result_summary` (the engine takes about 1.0 s of that). A plan the engine has cached takes about 0.4 s. Edits made during a compute are not lost: when the run finishes it sees the newer `edit_version` and queues another one.

## Run it

You need the engine running (`backend/run.sh`) and the CLI at `~/.local/bin/spacetime` (v2.13).

```bash
spacetime start
```

In a second terminal, from `backend/live/`:

```bash
npm install
npm run publish:local      # spacetime publish human-live --server local --yes
npm run proxy              # leave running: exposes POST /scenario to the module, then calls set_engine_url
npm run e2e                # optional check: hero street car-free -> result_summary in < 3 s, then reset
```

Use `spacetime publish human-live --server local --delete-data=always --yes` to start from an empty plan. After a schema change, run `npm run build:client` to regenerate `client/module_bindings/` and `client/dist/live.mjs`.

### Engine URL (why the proxy exists)

SpacetimeDB refuses procedure HTTP to **private or special-purpose addresses**: `localhost`, `127.0.0.1`, `10/8`, `192.168/16`, `172.16/12` and `fd00::/8` all fail with `refusing to connect to private or special-purpose addresses`. It checks both DNS results and literal IPs, and no config option turns it off. So the module can't call `http://localhost:8787` directly. It POSTs to whatever URL is in its private `config` table instead:

- **Local (default): `npm run proxy`** (`scripts/engine-proxy.mjs`) listens on this machine's **global IPv6** address, port 8788. It forwards only `POST /scenario` and `GET /health` to `127.0.0.1:8787`; everything else (including `/narrative/*`, which spends Claude credits) gets a 403. With `--set` it calls `set_engine_url` for you. This needs a network that gives the machine a global IPv6 address; phone hotspots usually do. The address changes when you switch networks, so rerun `npm run proxy` after switching.
- **No IPv6, or Maincloud:** put the engine behind any public HTTPS URL (for example a tunnel) and run `spacetime call human-live set_engine_url '"https://<public-host>/scenario?lite=1"' --server local`. Only the identity that published the module can call `set_engine_url`.

Status and errors show up in `scenario.status` / `scenario.error` and in the `activity` feed. `spacetime call human-live recompute --server local` re-runs the engine on the current edits.

## Schema

| Table | Key | What |
|---|---|---|
| `scenario` | `id` = 1 | `plan_id` (API scenario id of the latest result), `status` (`pending`, `computing`, `ready` or `error`), `day` / `days` (k of 5; the engine reports only the final day, so it goes 0 → 5), `edit_version`, `result_version`, `error` |
| `street_edit` | `edge_id` | car-free edges in the plan: `author`, `author_name`, `at` |
| `block_edit` | `building_id` | `scale` (0.25–4), `zone` (`res`, `office`, `retail`, `mixed`, or `''` to keep the building's own use) |
| `player` | `identity` | `name`, `color`, `online`, `cursor_x` / `cursor_z` (world metres, the same frame as `world.json`), `last_seen` |
| `activity` | `id` | feed: `who`, `color`, `text`, `at` |
| `result_summary` | `id` = 1 | `scenario_id`, `edit_version`, `cached`, `settle_ms`, `value_{mobility,social,economy,health,environment,total}` ($/yr vs baseline), `metrics_json` / `delta_json` (the API's `metrics` / `delta`, verbatim), `car_day` / `ped_day` (per edge id) |
| `config` (private) | `id` = 1 | `owner`, `engine_url` |

Reducers: `set_pedestrian(edge_ids: u32[], on: bool)`, `set_block(building_ids: u32[], scale: f32, zone: string)` (scale 1 with zone `''` clears the edit), `reset()`, `set_name(name)`, `set_cursor(x: f32, z: f32)`, `recompute()`, `set_engine_url(url)` (owner only).

The module doesn't know the street network and stores any id it gets. The engine silently ignores unknown edge ids (`[99999]` returns the baseline), so the UI should only send ids from `world.editable_edges` and real building ids.

## Frontend: JS client

`client/dist/live.mjs` is a single ES module: the SpacetimeDB SDK, the generated bindings, and a small `connectLive` helper. It needs no bundler. Copy it next to the page (or serve `backend/live/client/dist/`) and import it:

```html
<script type="module">
import { connectLive } from './live.mjs';

// uri defaults to ws://<page host>:3000, so a phone that opened http://<laptop-ip>:8765/ connects to the laptop.
const live = connectLive({
  name: localStorage.getItem('planner-name') || undefined,   // optional, calls set_name
  onChange(state, table) {
    // state.scenario: { status, day, days, planId, editVersion, resultVersion, error }
    // state.result:   { scenarioId, value: { total, mobility, ... }, metrics, delta, carDay, pedDay, cached, settleMs }
    // state.streets:  Set of car-free edge ids     state.blocks: Map buildingId -> { scale, zone, authorName }
    // state.players:  [{ id, name, color, online, x, z, me }]     state.activity: [{ who, color, text, at }]
    if (table === 'street_edit' || table === '*') paintCarFree(state.streets);
    if ((table === 'result_summary' || table === '*') && state.result) renderFlows(state.result.carDay, state.result.pedDay, state.result.value.total);
    if (table === 'scenario') showChip(state.scenario.status === 'ready' ? 'Settled' : 'Replanning…');
    if (table === 'player') drawCursors(state.players.filter(p => p.online && !p.me));
  },
  onError: err => console.warn('live layer', err),
});

// From the UI:
live.setPedestrian([1070, 832, 1423], true);   // or false to reopen
live.setBlock([512, 513], 1.5, 'res');
live.reset();
live.setName('Judge 3');
canvas.addEventListener('pointermove', e => { const p = screenToWorld(e); live.setCursor(p.x, p.z); });  // throttled to 10/s
</script>
```

`live.state()` returns the same snapshot at any time. `live.conn` is the raw `DbConnection` if you need row-level `onInsert` / `onUpdate` / `onDelete`. The browser keeps its identity token in `localStorage`, so a reload keeps the same player (name and color).

For the full result (hourly arrays, trips, POIs), fetch `GET :8787/scenario/{state.result.scenarioId}` as usual. The live layer carries only the summary.

## Files

- `src/schema.ts`: tables
- `src/index.ts`: reducers, lifecycle and the `compute` procedure
- `client/live.ts` → `client/dist/live.mjs`: the browser client (`npm run build:client`)
- `client/module_bindings/`: generated (`npm run generate`)
- `scripts/engine-proxy.mjs`: IPv6 forwarder for local publishing
- `scripts/e2e.mjs`: end-to-end check

`server/spacetimedb/` is an earlier prototype that ran the whole sim inside the module. It is kept as a reference and is not used here.
