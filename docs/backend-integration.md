# Wiring a mockup variant to the real simulation backend

The backend engine (`backend/`, contract `docs/contracts/sim-api.md` v0.2) is live at `http://localhost:8787`. It computes everything with calibrated models on real data: population from LODES and ACS, Google popular times via Apify, BART exits, the research parameter table. **The page must show the engine's numbers and flows, not the in-browser toy simulation.** Keep the toy only as a fallback (see Offline below).

## What you get
- **`mockup/lib/hp-backend.js`**: the connector. To use it, put `<script>/*__HP_BACKEND__*/</script>` before your main module script. `scripts/build_mockup.py` inlines the connector there and copies `mockup/backend-snapshot/` next to your `index.html`. That defines `window.HPBackend`:
  - `const B = await HPBackend.connect()` returns `{ mode: 'live'|'snapshot'|'offline', world, baseline, hero, scenario(edits, {onProgress}), getScenario(id), agent(sid, aid), narrative: {explain, diary, posts, planner} }`.
  - `HPBackend.editsFrom({ ped: Set<edgeId>, blocks: Map<bid,{s|scale, z|zone}> })` builds the request.
  - `HPBackend.expandTrips(result, W.edges, {copies:3})` turns trips into animatable objects `{t0, t1, dur, v, pts, segE, cum, len, mode:'car'|'ped'|'bike', purpose, poi, dwell, inlet_in, inlet_out, agent_id, side}`. Live mode requests `max_trips=100000` (contract v0.3), which returns every real trip of the day (~52k, `sample_share` 1.0), so no replay happens: `copies` defaults to 1. The snapshot holds a 15k-trip sample and is replayed 2× automatically. Don't add your own multipliers.
  - `HPBackend.inletCountsAt(result, tSeconds)` gives cumulative entered/left per inlet. `HPBackend.edgeHour(result.edges.car_hour, e, t)` gives people per hour on an edge.
- **`mockup/backend-snapshot/`**: frozen real results: world, baseline, hero plan (2nd St car-free, id in `world.hero.plan_id`), Maria's agent view, one AI planner response with 3 evaluated options (their results are included), citizen posts, and an explanation. In `snapshot` mode `scenario(edits)` returns these when the edits match, and `null` otherwise.

## Map every view to engine data
| UI | Source |
|---|---|
| Agents (animation) | `expandTrips(result)`. Car = cyan, pedestrian = amber, **bike = a third distinct color** (add it to the legend). Car trips that start or end at an inlet animate from or to it. |
| Edge IDs, building IDs | Identical to `world.json` (`W.edges`, `W.buildings`). POI ids = the backend's `world.pois` list, the same filter as `BASE_POIS`. Use the backend's `world.pois`, which adds Google rating, reviews and price level. |
| Baseline car-free streets | `world.base_car_free_edges` (Market St is car-free in 2026). Draw them as pedestrian in **both** scenarios. Users can't "pedestrianize" them again; `editable_edges` lists what's editable. |
| Traffic view | `edges.car_hour[e][h]` at the current hour, normalized by lane capacity, and/or `edges.congestion_am` / `congestion_pm` (travel-time factor). Color roads green → yellow → red from these, not from on-screen car counts. |
| Foot traffic view | `edges.ped_hour[e][h]` along sidewalks (heat on edges), plus the live pedestrian agents. |
| Workplaces / Residents / Visits / Revenue per block | `result.blocks.jobs` / `residents` / `visits` / `revenue`, indexed by block id. Use `world.block_of[buildingId]` for blocks (227 blocks) instead of your own union-find. Revenue change = plan minus baseline per block. |
| Connections view | `result.ties_sample` (`a`, `b`, `poi`, `t`). Draw arcs between the agents' work and home buildings, or between POIs, and highlight ties new in the plan. |
| Inlets ▲/▼ | `inletCountsAt(result, ui.time)`. The inlet order is `emb, mont, pow, i80, us101, mkt, fol, bwy`, with positions in `world.inlets[i].x/z`. |
| Top stats | `metrics.people`, plus live counts of cars and walkers derived from the expanded trips active at time t, multiplied by `world.scale / (copies × trips.sample_share)`. Label clearly: "people in area today". |
| City Value + pillars | `result.value.total` and the pillars `mobility`, `social`, `economy`, `health`, `environment` ($/yr vs baseline). **Environment is a fifth pillar now.** Add it to the radar and the pitch card. Use `value.lines` for itemized tooltips and the pitch card ("Delay saved 120 veh-h/day → $590K/yr"). |
| Radar | Derive the axes from `delta` relative to `metrics`, plus the value pillars. Keep the baseline shape as a ghost. |
| Key deltas | `delta.trips.car`, `delta.delay_hours`, `delta.revenue`, `delta.encounters`, `delta.new_ties`, `delta.residents`, `delta.co2_tonnes`, `delta.deaths_averted_per_yr`, `delta.rent_pressure_index`. |
| Street inspector | `edges.car_day[e]`, `ped_day[e]`, `bike_day[e]`, `congestion_am[e]`, and the hourly arrays, baseline vs plan. "Where traffic went" = `car_day` plan minus baseline. |
| Business inspector | `pois.visits_day` / `revenue_day` / `walkby_day` / `visits_hour[poi]` baseline vs plan, plus Google rating, reviews and price level from `world.pois`. |
| Settle animation | `B.scenario(edits, { onProgress: d => chip(d.label) })` streams "Replanning day k/5". The result takes about 1.5 s, or comes back instantly from cache. |
| Follow Maria | `world.hero.agent_id` (Maria O.) and `friend_id` (Dev P.). `B.agent(planId, heroId)` returns her trips (contract polyline steps) and diary in both scenarios, plus her ties. Draw her trail from `plan.trips`. The meeting is the diary event `kind:'meet'`. |
| AI planner | `B.narrative.planner(goal)` returns `options[{title, edits, rationale, result_id, value_total, deltas}]`. Preview by highlighting `edits`; Apply loads `B.getScenario(result_id)` and sets the page's plan edits to `option.edits`. It takes about 15 s live, so show a "thinking" state. The snapshot has one cached response for the demo goal "Boost small business in SoMa without slowing Bay Bridge traffic". |
| Citizen feed | `B.narrative.posts(planId, 6)` after each settle (live), or the snapshot posts. Keep a few templated ambient posts only as filler. |
| "Ask AI" why-questions | `B.narrative.explain(planId, question)`. |
| Credibility | Show a small status badge, e.g. "Live engine · calibrated to LODES, ACS, BART, Google popular times", or "Snapshot of engine results". In the pitch footnote, show the counts from `world.params` by status (data / literature / assumed) and link to `research/`. |

## Offline / unknown edits
- `mode === 'snapshot'` (published artifact) or `'offline'`: the demo path (baseline, 2nd St, AI options) uses real engine results. A free edit that isn't in the snapshot falls back to the toy engine. Mark it with a visible "Estimate (engine offline)" chip, and never mix toy and engine numbers in one view.
- Published artifacts can't reach localhost (CSP). That's expected, and snapshot mode covers it.

## Scale and copy
- Engine scale: `world.scale` people per agent (currently 21). About 271k people are present per day, 322k jobs and 37k residents. Update every hard-coded copy, e.g. "31,000 commuters" or "1 sim = 6 people", to use the engine's numbers.
- The engine's hero plan is about +$3.7M to +$6.4M/yr depending on version. Read the value; never hard-code it.

## Ownership
- Don't edit `backend/**`, `research/**`, `docs/contracts/**`, `mockup/lib/**` or `mockup/backend-snapshot/**`. Ask the main agent if the connector needs a change.
- The API runs at `localhost:8787`. Don't restart it. Calls are cheap locally, except the `/narrative/*` endpoints, which call Claude. Use them sparingly while testing, and prefer snapshot mode for repeated demo runs: open the page with `?snapshot` to replay frozen results with no API or Claude calls.
