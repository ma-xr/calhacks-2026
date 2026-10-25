# Sim API contract (backend → frontend)

**Status:** draft v0.1, 2026-10-24. The backend agent owns this file; the frontend reads it. Breaking changes are listed here at the top with a date.

| Date | Change |
|---|---|
| 2026-10-25 | **Valuation (product decision):** health (WHO HEAT × VSL) and crash costs are no longer monetized. `value.health` is always 0, has no line, and is excluded from `value.total`. Environment is CO₂ only, at $120/t (low bound of the EPA 2023 range). `metrics.deaths_averted_per_yr` and walking minutes are still reported as plain metrics. `value.total` = mobility + social + economy + environment. |
| 2026-10-24 | **BREAKING (v0.4): inlets are a variable-length list.** Cars now enter and leave at every road that crosses the map edge, not 5 fixed gates. `GET /world → inlets` has 3 rail inlets plus ~60 car inlets (5 legacy keys `i80`, `us101`, `mkt`, `fol`, `bwy` and generated ones such as `howard_st_south`). **Stop assuming ids 0–7 or any order**: look inlets up by `key` and `mode`, and size per-inlet arrays (`result.inlets`) from the list. Car inlets gain `side`, `cls`, `lanes`, `at` (point on the map edge), `has_entry`, `has_exit`, `edges` (crossing edge ids) and `legacy`. `regions[].car_inlets` maps each usable inlet key to its extra outside minutes. Trip `inlet_in`/`inlet_out` are the inlets each driver actually chose. A `congestion_charge` with a `target` is a toll on entering at that inlet key (unknown keys → 400). |
| 2026-10-24 | v0.1 draft |
| 2026-10-24 | v0.3 (additive). **`max_trips`** query parameter on `GET /baseline`, `GET /scenario/{id}` and `POST /scenario` (default 4000, max 100000). The full day is ~52k trips; `trips.sample_share` says what share came back. Responses are gzip-compressed when the client sends `Accept-Encoding: gzip`, which browsers do automatically. |
| 2026-10-24 | v0.2 (additive, nothing removed). **Market St is car-free in the baseline** (2026 reality), listed in `world.base_car_free_edges`. New edit fields `reopened` and `reopen_mode`. New fields: `edges.bike_day`, `edges.congestion_pm`, `edges.car_free`, `metrics.trips.bike`, `metrics.market_bus_time_index`, `metrics.neighbor_ties`, `metrics.deaths_averted_per_yr`, `metrics.vmt_total`, `metrics.delay_hours_total`. Trip `mode` can be `bike`. `?lite=1` on any result drops the hourly arrays and trips (about 120 KB vs 1.7 MB). `GET /scenarios` lists cached plans. |

Base URL: `http://localhost:8787`. JSON everywhere and CORS open. Run it with `backend/run.sh` (see `backend/README.md`).

## IDs (compatible with `data/processed/world.json`)
| Thing | Id |
|---|---|
| Edge | index into `world.edges` |
| Building | index into `world.buildings` |
| POI | index into the **filtered** POI list: `world.pois` where `c ∈ {cafe, restaurant, fast_food, bar, shop}` and the point is inside `world.bbox` with a 40 m margin. This is the same list the mockup builds as `BASE_POIS`. `GET /world` returns it, so you don't need to rebuild it. POIs created by plan edits (new shops after rezoning) have ids ≥ 5000 and are listed per scenario in `virtual_pois`. |
| Block | `GET /world` returns `block_of[buildingId]`: buildings unioned within 70 m with no road between them, the same rule as the variant A mockup |
| Inlet | `GET /world → inlets[].i` (= position in that list). The list length and order can change when the world is rebuilt, so match on `key`. Rail: `emb`, `mont`, `pow`. Car: legacy `i80`, `us101`, `mkt`, `fol`, `bwy`, plus one generated inlet per street and map side that crosses the edge (`<street>_<side>`, e.g. `howard_st_south`) |
| Agent | stable integer, the same in every scenario. Agents added by a density edit get new ids ≥ 100000 |

Times are **seconds since midnight** of one simulated weekday. Money is **USD**. Every count is already scaled to **real people** unless the field name ends in `_agents`. `world.scale` = people per agent.

## Endpoints

### `GET /health`
`{ "ok": true, "baseline_ready": true, "version": "0.1" }`

### `GET /world`
Static data for one session; fetch it once.
```jsonc
{
  "scale": 12,                       // people per agent
  "inlets": [                        // variable length: read it, don't hard-code ids or order
    { "i": 0, "key": "emb", "name": "Embarcadero", "mode": "ped", "x": 157.9, "z": -459.8, "side": null, "legacy": true },
    { "i": 3, "key": "i80", "name": "I-80 · Bay Bridge", "mode": "car", "x": 2763.1, "z": -2142.1, "side": "east", "legacy": true,
      "cls": "motorway", "lanes": 4, "at": [941.3, -972.8], "has_entry": true, "has_exit": true, "edges": [] },
    { "i": 32, "key": "howard_st_south", "name": "Howard St · south", "mode": "car", "x": -715.1, "z": 961.7, "side": "south", "legacy": false,
      "cls": "secondary", "lanes": 4, "at": [-715.1, 961.7], "has_entry": false, "has_exit": true, "edges": [771] }, ...],
                                     // x,z: marker position (legacy car inlets: their road end, which may lie outside the box);
                                     // at: the same point clamped onto the map edge. edges: road edges crossing the edge.
  "regions": [{ "key": "east_bay", "name": "East Bay", "share": 0.31, "car_inlet": 3, "bart_inlet": 0,
                "car_inlets": { "i80": 0, "us101": 3.0, "king_st_south": 3.0, "bryant_st_south": 3.5, "the_embarcadero_east": 4.0, ... } }, ...],
                                     // car_inlet: the region's main inlet (walkers/cyclists from that side come in here).
                                     // car_inlets: every inlet its drivers may use → extra minutes; drivers pick by route cost.
  "pois": [{ "id": 0, "name": "Comstock Saloon", "category": "bar", "x": -610.8, "z": -913.5,
             "rating": 4.5, "reviews": 1200, "price_level": 2, "has_popular_times": true }, ...],
  "block_of": [0, 0, 1, ...],        // per building id
  "n_blocks": 412,
  "editable_edges": [12, 13, ...],   // edges that can be pedestrianized (no highways)
  "zones": ["res", "office", "retail", "mixed"],
  "params": { "<key>": { "value": ..., "status": "data|literature|assumed", "source": "url" } },
  "hero": { "agent_id": 913, "friend_id": 448, "street_edges": [1070, 832, ...], "street": "2nd Street" }
}
```

### `GET /baseline`
Same as `GET /scenario/baseline`.

### `POST /scenario`
Runs a plan against the cached baseline and returns the result (target ≤ 2 s).
```jsonc
// request
{
  "name": "Plan A",                                   // optional
  "edits": {
    "pedestrianized": [1070, 832, 1423],              // edge ids
    "blocks": { "512": { "scale": 1.5, "zone": "res" } },   // building id → edit; zone optional
    "policies": [{ "kind": "congestion_charge", "target": "i80", "amount": 5 }],  // optional; also "parking_price"
    "reopened": [],                  // optional: base car-free edges (Market St) to reopen to cars
    "reopen_mode": ""                // optional: "pre2020" = reopened with the old forced-turn restrictions
  }
}
```
Response: a **ScenarioResult** (below) with `id` set. Query parameters on every result endpoint: `lite=1` drops the hourly arrays and trips, and `max_trips=N` sets the trip sample size (default 4000; 20000 ≈ 37% of trips, ≈ 5 MB raw, much less gzipped; 100000 = every trip). The same edits return the cached result immediately (`"cached": true`).

**Streaming progress:** `POST /scenario?stream=1` returns Server-Sent Events. You get `event: progress` with `{ "day": k, "days": 5, "label": "Replanning day k/5" }`, then `event: result` with the full ScenarioResult.

### `GET /scenario/{id}`
Returns the stored ScenarioResult. `id` is `baseline` or the id from `POST`.

### `GET /scenario/{id}/agent/{agent_id}`
Data for the Follow view.
```jsonc
{ "agent_id": 913, "name": "Maria O.", "kind": "worker", "income_tier": 1, "region": "East Bay",
  "home": { "building": -1, "region": "East Bay" }, "work_building": 1532, "car_available": true,
  "baseline": { "mode": "car", "trips": [Trip...], "diary": [DiaryEvent...] },
  "plan":     { "mode": "transit", "trips": [Trip...], "diary": [DiaryEvent...] },
  "ties": [{ "agent_id": 448, "name": "Dev P.", "where_poi": 87, "strength": 0.4, "new_in_plan": true }] }
```
`DiaryEvent` = `{ "t": 30300, "kind": "arrive|depart|visit|meet|leave", "text": "Walked up from Montgomery BART", "poi": 87?, "with": 448? }`

### `POST /narrative/*` (Claude)
These endpoints only narrate numbers the engine already produced. Every response carries `"grounding"`: the metric keys and ids it used.
- `POST /narrative/explain` `{ "scenario": "<id>", "question": "why did revenue on 2nd St go up?" }` → `{ "answer": "...", "grounding": {...} }`
- `POST /narrative/diary` `{ "scenario": "<id>", "agent_id": 913 }` → `{ "text": "..." }`
- `POST /narrative/posts` `{ "scenario": "<id>", "n": 6 }` → `{ "posts": [{ "agent_id", "name", "text", "tag" }] }`
- `POST /narrative/planner` `{ "goal": "boost small business in SoMa without slowing the Bay Bridge" }` → `{ "options": [{ "title", "edits", "rationale", "result_id", "value_total", "deltas" }] }`. The planner proposes edits, the engine evaluates each one, and Claude explains the trade-offs.

## ScenarioResult
```jsonc
{
  "id": "baseline" | "<hash>",
  "name": "Plan A",
  "edits": { ... },                       // echo of the request
  "settle": { "days": 5, "ms": 840, "converged": true, "gap": 0.012 },
  "cached": false,

  "metrics": {
    "people": 61234,                      // people present in the area that day
    "trips": { "car": 18000, "transit": 32000, "walk": 6000, "bike": 900, "gone": 0 },   // person-trips/day by main mode
    "commuters": { "car": 9100, "transit": 21000, "walk": 2400, "bike": 450, "gone": 0 },
    "vmt": 41000, "veh_hours": 2900, "delay_hours": 880,
    "walk_minutes": 950000, "active_minutes_per_person": 21.4,
    "ped_trips": 140000,
    "visits": 98000, "revenue": 1840000,
    "encounters": 220000, "new_ties": 1300, "ties": 5900,
    "jobs": 168000, "residents": 21000, "jobs_housing_ratio": 8.0,
    "access_15min": 0.82,                 // share of residents with all 5 amenity types within 15 min walk
    "co2_tonnes": 17.1,
    "rent_pressure_index": 0.0,           // % change in rent pressure vs baseline (0 for baseline)
    "by_income": { "low": { "people": 0, "travel_min": 0, "walk_min": 0, "car_share": 0 }, "mid": {...}, "high": {...} }
  },
  "delta": { ...same keys as metrics, plan minus baseline (zero for the baseline)... },
  "value": {                              // $/yr vs baseline (all zero for the baseline)
    "mobility": 0, "social": 0, "economy": 0, "health": 0, "environment": 0, "total": 0,
    "factors": { "vot_personal_usd_per_hr": 19.6, ... },   // every factor used, with source keys
    "lines": [{ "pillar": "mobility", "label": "Delay saved", "qty": 120.5, "unit": "veh-h/day", "usd_per_yr": 590000 }]
  },
  "edges": {                              // arrays indexed by edge id
    "car_day": [..], "ped_day": [..],     // people per day on the edge (scaled)
    "congestion_am": [..], "congestion_pm": [..],   // travel-time factor (1 = free flow) at 8–9 and 17–18
    "bike_day": [..],                     // cyclists per day
    "car_free": [..],                     // edge ids closed to cars in this scenario (base + plan)
    "car_hour": [[24]..], "ped_hour": [[24]..]   // people per hour, edge-major
  },
  "pois": {                               // arrays indexed by POI id (filtered list)
    "visits_day": [..], "revenue_day": [..], "visits_hour": [[24]..],
    "walkby_day": [..]                    // passers-by per day: the walk-by exposure
  },
  "virtual_pois": [{ "id": 5000, "name": "New café", "category": "cafe", "x": 0, "z": 0, "visits_day": 0, "revenue_day": 0 }],
  "blocks": { "jobs": [..], "residents": [..], "visits": [..], "revenue": [..] },   // indexed by block id
  "inlets": [{ "i": 0, "entered_hour": [24], "left_hour": [24], "entered": 0, "left": 0 }],   // one row per GET /world inlet, same order
  "ties_sample": [{ "a": 913, "b": 448, "poi": 87, "t": 44100 }],                    // up to 900
  "trips": {
    "sample_share": 0.25,                 // share of all agent trips included
    "items": [{
      "agent_id": 913, "mode": "car|ped", "purpose": "commute_in|commute_out|lunch|coffee|errand|evening|return",
      "t_start": 30000, "t_end": 30900,
      "steps": [2140, 1665],              // edgeId*2 + (1 if travelled b→a, else 0)
      "trim_head": 0, "trim_tail": 0,     // car trips: polyline points dropped at the far ends of highway ramps
      "poi": 87,                          // destination POI or -1
      "dwell": 1800,                      // seconds spent at the destination
      "inlet_in": 3, "inlet_out": -1
    }]
  },
  "assumptions": [{ "key": "tie_formation_prob_per_repeat_encounter", "status": "assumed", "note": "..." }]
}
```

### Rebuilding a trip polyline
For each step `s`: `edge = world.edges[s >> 1]`, and the points are `edge.p` reversed if `s & 1`. Join the edges, dropping the duplicate joint point. For car trips, then drop `trim_head` points from the start and `trim_tail` from the end. Interpolate position linearly between `t_start` and `t_end`.

## Example client
```js
const API = 'http://localhost:8787';
const world = await (await fetch(`${API}/world`)).json();
const base = await (await fetch(`${API}/baseline`)).json();
const plan = await (await fetch(`${API}/scenario`, {
  method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ edits: { pedestrianized: world.hero.street_edges } }),
})).json();
console.log(plan.value.total, plan.delta.trips.car, plan.metrics.revenue);
```

With progress:
```js
const res = await fetch(`${API}/scenario?stream=1`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ edits }) });
const reader = res.body.getReader(); const dec = new TextDecoder(); let buf = '';
for (;;) { const { value, done } = await reader.read(); if (done) break; buf += dec.decode(value, { stream: true });
  let i; while ((i = buf.indexOf('\n\n')) >= 0) { const msg = buf.slice(0, i); buf = buf.slice(i + 2);
    const ev = /event: (\w+)/.exec(msg)?.[1], data = JSON.parse(/data: (.*)/s.exec(msg)[1]);
    if (ev === 'progress') showChip(data.label); else if (ev === 'result') render(data); } }
```

## Ports
- `8787`: this API.
- `8765`: frontend static server (not ours).
- `3000`: SpacetimeDB, if the live layer is enabled (see `backend/README.md`).

## Live layer (SpacetimeDB)

Optional. It lets several clients edit **one shared plan** in real time. The code and run steps are in `backend/live/README.md`. SpacetimeDB on `:3000` (database `human-live`) holds the plan, presence and the latest result summary. This API stays the compute layer: a scheduled SpacetimeDB procedure POSTs the merged edits to `POST /scenario?lite=1` about 400 ms after the last edit and writes the result back to every subscriber. Measured: about 1.5 s from an edit to the pushed result for a fresh plan, about 0.4 s for a cached one.

- **Reducers (client → live layer):** `set_pedestrian(edge_ids, on)`, `set_block(building_ids, scale, zone)`, `reset()`, `set_name(name)`, `set_cursor(x, z)`. Ids are the same as in this contract (edge = index into `world.edges`, building = index into `world.buildings`). Cursor x/z are world metres.
- **Tables (live layer → client, by subscription):**
  - `scenario` (one row): `plan_id`, which is the `id` of the latest ScenarioResult here, so `GET /scenario/{plan_id}` returns the full result. Also `status` (`pending`, `computing`, `ready` or `error`), `day` / `days`, `edit_version`, `result_version` and `error`.
  - `street_edit`, `block_edit`: the merged edits, which map 1:1 to `edits.pedestrianized` / `edits.blocks`.
  - `player`: name, color, online, cursor.
  - `activity`: the feed.
  - `result_summary` (one row): `scenario_id`, `value_*` totals, `metrics_json` / `delta_json` (this API's `metrics` / `delta`, verbatim) and `car_day` / `ped_day` (per edge, the same as `edges.car_day` / `edges.ped_day`).
- **Client:** `backend/live/client/dist/live.mjs` exports `connectLive({ onChange })`, a single ES module with no bundler needed. See the README for the snippet.
- **Not in the live layer:** policies, `reopened` and `reopen_mode` aren't editable through it yet, and hourly arrays, trips and POIs aren't mirrored. Fetch those from this API with `plan_id`.
- **Network note:** SpacetimeDB blocks module HTTP to private addresses, including localhost. Locally, `backend/live/scripts/engine-proxy.mjs` forwards `POST /scenario` and `GET /health` from the machine's global IPv6 address to this API; other paths get a 403. For Maincloud this API needs a public URL.

## Droid live agent (Factory)

Ask Droid anything about the scenario on screen. It answers only from the `simq` query tool's output and returns map directions: references, a camera focus, highlights and a layer. The model's normal endpoints don't change. Internals and permissions are in `backend/droid/README.md`.

### `POST /droid/ask[?stream=1]`

```json
{ "conversation_id": "optional; send back the one you got to ask follow-ups",
  "scenario": "baseline | <scenario id>",
  "question": "Why did revenue on 2nd St go up?",
  "view": { "time_s": 28800, "selected": { "type": "edge|building|poi|agent|block|inlet", "id": 268 } } }
```

- **`conversation_id`:** keeps a warm Droid session (20 min idle). Follow-ups like "and what about Howard?" are answered in context.
- **Unknown scenario:** 404. Re-POST `/scenario` if it was evicted.
- **Without `stream=1`:** the response is the answer JSON (below).
- **With `stream=1`:** server-sent events:
  - **`event: step`:** sent once when a query starts (`status: "running"`) and again when it finishes (`"done"`, `"error"` or `"denied"`). Example: `{"id", "label": "Ranking businesses: --sort revenue_delta --asc", "command": "…python -m droid.simq --scenario … pois …", "simq": "pois --sort revenue_delta --asc", "status": "done", "output": "<first 1200 chars>"}`. Show these in a "Droid is working" list.
  - **`event: answer`:** the final event, carrying the answer JSON.

`DELETE /droid/conversations/{id}` closes a conversation's session early.

### Answer JSON

```json
{ "conversation_id": "a1b2c3d4e5f6",
  "answer": "markdown, ≤120 words; every number comes from simq output",
  "references": [{ "type": "street|edge|building|block|poi|agent|inlet", "ids": [268, 291], "label": "2nd St (Market–Folsom)",
                   "why": "car-free stretch; foot traffic up", "value": "+4,787 people/day" }],
  "focus": { "x": -38.7, "z": 135.7, "radius_m": 320 },
  "highlights": { "edges": [268, 291], "buildings": [], "pois": [199], "agents": [2429] },
  "info_view": "traffic|foot|workplaces|residents|visits|zoning|connections|revenue",
  "time_s": 28800,
  "grounding": ["summary", "stretch \"2nd Street\" \"Market Street\" \"Folsom Street\""],
  "source": "droid | narrative_fallback",
  "latency_s": 12.4 }
```

- **IDs** are `world.json` indices: `edge` = `world.edges` index, `building` = `world.buildings` index, `poi` = `GET /world → pois` index (ids ≥ 5000 are `virtual_pois` from rezoning), `agent` = stable agent id, `block` = `world.block_of` value, `inlet` = `GET /world → inlets[].i`. A `street` reference lists its edge ids.
- **Validation:** the server drops reference ids that don't exist and computes `focus` from the geometry of the leading references. `highlights` is the union of all references.
- **Optional fields:** `info_view` and `time_s` are present only when Droid suggests them.
- **Fallback:** if Droid fails or times out (40 s), `source` is `"narrative_fallback"`, `answer` is the Claude `/narrative/explain` text, and `references` is `[]`.

### Client snippet

```js
async function askDroid({ scenario, question, conversationId, view, onStep }) {
  const r = await fetch(`${API}/droid/ask?stream=1`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ scenario, question, conversation_id: conversationId, view }),
  });
  const reader = r.body.pipeThrough(new TextDecoderStream()).getReader();
  let buf = '', answer = null;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += value;
    let i;
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
      const ev = /^event: (.*)$/m.exec(chunk)?.[1], data = JSON.parse(/^data: (.*)$/m.exec(chunk)[1]);
      if (ev === 'step') onStep?.(data); else if (ev === 'answer') answer = data;
    }
  }
  return answer;
}

// Fly the camera and light up what Droid talked about (three.js + OrbitControls; y-up, map in x/z).
function applyDroidAnswer(a, { camera, controls, setLayer, setClock, highlight }) {
  if (a.focus) {
    const target = new THREE.Vector3(a.focus.x, 0, a.focus.z);
    const dist = a.focus.radius_m * 2.2;                       // fits radius_m in a ~50° FOV
    const to = target.clone().add(new THREE.Vector3(0, dist * 0.8, dist * 0.6));
    const from = camera.position.clone(), fromT = controls.target.clone(), t0 = performance.now();
    (function step(now) {
      const k = Math.min(1, (now - t0) / 900), e = k * k * (3 - 2 * k);
      camera.position.lerpVectors(from, to, e); controls.target.lerpVectors(fromT, target, e); controls.update();
      if (k < 1) requestAnimationFrame(step);
    })(t0);
  }
  highlight({ edges: a.highlights.edges, buildings: a.highlights.buildings, pois: a.highlights.pois, agents: a.highlights.agents });
  if (a.info_view) setLayer(a.info_view);
  if (a.time_s != null) setClock(a.time_s);
  // Render a.references as chips: click → fly to that one (focus from its ids) and show `why` / `value`.
}
```

## Droid policy compiler (Factory)

New city levers can be written by Droid and approved by a person:
- **Propose:** `POST /policies/propose {"request": "a $5 charge only for through-traffic"}`.
- **Panel data:** `GET /policies` returns the Policy Book plus every proposal's plan, steps, permissions, gate checks, diff and metrics.
- **Decide:** `POST /policies/{id}/approve` hot-loads the module. `/reject` discards it.
- **Use it:** an approved kind works in `POST /scenario` as `{"policies": [{"kind": "<kind>", "params": {…}}]}`.
- **Details:** `backend/droid/README.md`.
