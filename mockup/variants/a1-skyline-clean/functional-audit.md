# Skyline Clean: functional audit against the live engine

- Date: 2026-10-24
- Page: `http://localhost:8765/variants/a1-skyline-clean/index.html` (live mode, `B.mode === 'live'`, status chip "Live engine")
- Backend: `:8787`, health v0.2, `world.scale` 21, 65 inlets (3 rail, 62 car), 97 params (21 data, 38 literature, 38 assumed)
- Method: I drove the page in a separate browser tab with real mouse drags for painting and DOM clicks for the controls. Where noted, I called the page's own functions through `window.__bw`, which run the same code paths. I checked every API call with `read_network_requests`.
- Line numbers below refer to `mockup/variants/a1-skyline-clean/template.html`. `index.html` was built from the current template; both are dated 19:21.

**Narrative spend during the test:**
- 1 planner call, 1 explain call, 0 diary calls.
- 5 posts calls. The page fired these by itself, once per new plan, before I blocked them at runtime. That behaviour is finding B6.

**What works end to end (no action needed):**
- Painting one street or several streets sends `POST /scenario?stream=1&max_trips=100000`. Pillars, City Value, the chip, the street and block inspectors, and the block info views all show the engine's `delta`, `value` and `blocks` values. Examples: 2nd St 3 edges gave −378 car trips and +$671K; adding Howard gave +$2.85M.
- Erasing works. It returns the client-cached result without a new request.
- Density and zoning on a block send all 13 buildings of the block (`world.block_of`). The inspector shows engine jobs and residents: 3,531 → 479 jobs and 301 → 6,326 residents.
- Baseline/Plan A toggle, Compare swipe, scrubber, speed cycle (1×/3×/10×) all work.
- Inlet badges and the per-side sums use `result.inlets` looked up by key (`g.ei`), so they follow v0.4.
- Clicking any person calls `GET /scenario/{id}/agent/{aid}`.
- The AI planner calls `/narrative/planner`. Apply merges the option's edits on top of the plan and POSTs `/scenario`, policy included.
- Explain calls `/narrative/explain`.
- The engine pitch card shows engine pillars, deltas and the top 4 `value.lines`.
- The scripted demo runs on live results: hero agent view, one POST for 2nd St, one POST for the AI apply.

---

## A. Broken or non-functional

### A1 · P0 · An edit made during a settle is silently dropped, so the map and the numbers disagree
- **Evidence:**
  - I called `togglePed(268) → settle()`, then 100 ms later `togglePed(291) → settle()`.
  - Afterwards `S.plan.ped = [268, 291, 1399, 1423, 1424]`, but the shown result's `edits.pedestrianized = [268, 1399, 1423, 1424]`.
  - Edge 291 is drawn car-free with café tables, yet it was never simulated.
  - The same applies to brush strokes, zoning clicks and density drags that land while the engine is replanning.
- **Code:** `settle()` line 1863: `if (ui.settling) return;`. Also the demo and planner paths that set `ui.settling` (line 2170).
- **Fix:** queue a re-settle when the edits changed while a settle was running. Or compare `editsKey(currentEdits())` with `result.edits` after each settle and run again if they differ.

### A2 · P0 · No timeout on the scenario stream, so one hung request locks every edit tool
- **Evidence:** `scenario()` in `mockup/lib/hp-backend.js` lines 122–133 does `fetch(...)` and reads the stream with no timeout or abort. If the engine stalls, `ui.settling` stays `true` forever, and A1 then drops every later edit.
- **Code:** `hp-backend.js` 117–135 (the connector itself, owned by the main agent); `settle()` lines 1862–1872.
- **Fix:** an AbortController with a timeout of about 20 s, an error chip, and a Retry button.

### A3 · P1 · A failed engine call in live mode silently becomes the toy model, labelled "engine offline"
- **Evidence (400):**
  - I sent an invalid policy (`target: 'nope'`). The engine returned 400 with `unknown car inlet 'nope'`.
  - The connector does not check `res.ok`. It reads the JSON error as an empty SSE stream and returns `null`.
- **Evidence (thrown error):**
  - I made `B.scenario` throw.
  - The UI then ran `TOY.plan.settle` and showed "Estimate (engine offline)", status "Estimate", and City Value **+$5.45M**, while the engine's value for the same edits is about +$0.67M.
  - `value.lines` is empty in that state, and the error message is never shown.
- **Code:** `settle()` 1868–1870; `fillEstimate()` 1080–1110; `hp-backend.js` 122 (no `res.ok` check).
- **Fix:**
  - In live mode, show the engine error and keep the previous engine result.
  - Use the toy estimate only when `B.mode !== 'live'`.

### A4 · P1 · The person inspector throws for anyone with a lunch walk until the agent view arrives, so the trail and label are never drawn
- **Evidence:** `followPerson(342)` threw `TypeError: trip.steps is not iterable` at `tripPolyline`.
- **Cause:**
  - Before `/agent` returns, `inspectAgentEng` builds `simple()` trips without `steps`.
  - The "Lunch walk" row then calls `HPBackend.tripPolyline(lw, EDGES)`.
  - The exception aborts `followPerson` before the follow label and trail are set: the follow label stayed empty.
- **Snapshot mode:** there is no agent file for arbitrary ids, so the inspector stays broken there.
- **Code:** line 2001 (`HPBackend.tripPolyline(lw, ...)` on `simple()` trips from line 1991); `followPerson` 2020–2027.
- **Fix:** guard with `lw.steps`, or use `lw.segE` from the expanded trip.

### A5 · P1 · The Foot traffic hover tooltip is 6× too high
- **Evidence:** edge 1399 has engine `ped_day` = 26,376. The tooltip prints `pedFlow * SCALE` = 158,256 walkers/day.
- **Code:** line 2078: `num(S[activeWorld()].pedFlow[id] * SCALE, false)`. `SCALE = 6` is a toy constant (line 572). `flowScale()` exists (line 1076) but isn't used here.

### A6 · P1 · The engine's `/narrative/posts` returns empty posts, so the feed is entirely templated
- **Evidence:** all 5 responses were `{"posts":[{"agent_id":null,"name":"Citizen","text":"","tag":"social"}]}`. The UI filters out empty text (line 1877) without saying so.
- **Result:** the feed only ever shows `ambientPost()` templates and the hard-coded "Rosa S." post.
- **Responsibility:** this is a backend bug. The UI should still show "No citizen posts from the engine" or retry.
- **Code:** `fetchPosts` 1874–1878.

### A7 · P1 · Explain answers are cut off mid-sentence
- **Evidence:** the `/narrative/explain` response ends with "…**Losers:** Foot traffic drops on 5th Street and". The UI types it out as is.
- **Responsibility:** this is the backend's `max_tokens`. The UI could detect a missing final period, or render the `grounding` keys, which it currently ignores.
- **Code:** `askEngine` 2149–2151.

### A8 · P1 · Any Ask question without "why/explain/how come" runs the paid planner
- **Evidence:** `askAI` line 2127 sets `why = /why|explain|how come/i.test(q)`. Anything else, for example "what happened to traffic on Howard?", goes to `/narrative/planner` (up to 90 s, the most expensive call). Results are cached per goal string only.
- **Fix:** an explicit "Ask" vs "Plan" toggle, or route questions to `/droid/ask` or `/narrative/explain`.

### A9 · P1 · There is no Reset
- **Evidence:** no Reset control exists. The only way to clear a plan is to start the demo, which resets as a side effect (line 2269), or to erase each street by hand.
- **Policies:** policies added by the AI (`planPolicies`) cannot be removed at all. Block edits can only be undone one block at a time.
- **Code:** the dock (lines 486–497) has no reset; `planPolicies` 1019 and 2168.

### A10 · P2 · Stale street label after erasing
- **Evidence:** after erasing Howard St, the purple label still read "Howard St · car-free". `paintEdge` sets it on paint; erase never clears or updates it.
- **Code:** 2051–2053.

### A11 · P2 · "Stable" claim, but the result didn't converge
- **Evidence:** the result had `settle.converged: false, gap: 0.03`, yet the panel note says "Plan A vs today · stable".
- **Code:** line 1884.

### A12 · P2 · "Drive time %" in the chip, pitch and AI caption is not a drive time
- **Evidence:** `tripMin = (veh_hours / vmt) * 60 * 20` (line 1069) is minutes per mile × 20, i.e. inverse average speed. It is labelled "Average drive time".
- **Fix:** use `delta.delay_hours_total` per car trip, or a real per-trip time if the engine exposes one.

### A13 · P2 · Fake progress after the result is already in
- **Evidence:** after the result arrives, the chip steps through days 2–5 with `sleep(110)`, which adds about 440 ms of fake progress.
- **Code:** line 1869.

### A14 · P2 · At 3× and 10× agents lag their engine schedule
- **Evidence:** agent speed is capped at 32× (`AGENT_CAP`, line 1520), and `resetAgents` scales progress by `f` (line 1537). At 10× (rate 300) a dot covers about 9% of its route by the time the engine says it has arrived.
- **Result:** the top-bar counts come from the schedule and are correct, but the dots on the map are not.

### A15 · P2 · Inlet tooltips say "Vehicles" for counts of people
- **Evidence:** side-label tooltips say "Vehicles entering / leaving" (line 1716), but `result.inlets` counts are people (contract: "every count is already scaled to real people").

### A16 · P2 · Formatting glitches
- **Evidence:** a planner option shows "delay −0 veh-h" (`num()` of a small negative, line 2157).
- **Evidence:** the pitch title counts 13 rezoned buildings as "1 rezoned block" (grouping by 140 m, lines 2214–2216). That is acceptable, but it disagrees with the block inspector's building count.

---

## B. Mocked or local where the engine should be used

### B1 · P1 · The full toy engine still boots and settles in live mode
- **What:** `S.base.settle` runs twice and `S.plan.settle` once, with about 6,500 synthetic persons plus 5,200 through-drivers and local Dijkstra. All of this runs before the engine adapter.
- **Code:** lines 785–1013 (population, `Scenario`, `BASE_PERSONS`, `REGIONS` with hard-coded shares and travel times at 736–742, `THROUGH_OD` at 744).
- **Why it matters:** it costs boot time, and it is the source for A3 and for the AI fallbacks.
- **Fix:** run it lazily, only when `B.mode !== 'live'`.

### B2 · P1 · Projected approval percentages in the pitch are invented
- **What:** `merch = 55 + rel(revenue) * 2600`, `drv = 50 − … − 12 − 18`, and so on, with clamps of 8–96.
- **Problem:** the footer then says "Every number here comes from the simulation engine".
- **Code:** line 2221 and footer 2242.
- **Fix:** drop the section, or label it "illustrative".

### B3 · P1 · Pitch "Who gains" uses local factors
- **What:** `walk_min * .12` is a hard-coded $/min, and VOT falls back to `21.8`. The engine has `value.factors` and `by_income`.
- **Problem:** the footnote calls the city total "driven by … toll revenue" even when `charges_paid_usd` is 0. In the test, a $3 charge at `fol` produced 0 charges.
- **Code:** lines 2217–2218, 2240.

### B4 · P1 · The Zoning view and the zone labels come from a random local classification
- **What:** OSM `mixed` buildings are split by height and `hash2(b.id, 11) < .38 ? 'res'`, which is pseudo-random. The result drives the Zoning info view, the hover text, the block inspector's zone label and the "civic: fixed" rule. None of it comes from the engine's land-use data.
- **Code:** line 773, `zoneOf` 775, civic rule 1939/1945, office-vacancy copy 1948 ("about 35%", hard-coded).

### B5 · P1 · Person names are invented locally and conflict with the engine
- **What:** `engPerson()` makes names from `FIRST`/`LAST` by `hash2(id)` (line 1028).
- **Evidence:** agent 342 is "Ana C." in the follow label, feed and ties, but "Yuki M." in the engine `/agent` response, which the inspector header shows.
- **Fix:** take names from `/agent` (or a names list in `/world` / `agents_sample`), and fall back to "Commuter #342".

### B6 · P1 · Citizen feed: templates, plus a posts call after every settle
- **Ambient posts:** "Stuck on {street} again…", "Kids drawing chalk…" and similar are chosen with `Math.random`. They are triggered by local `liveCong` thresholds and by agents on painted edges (lines 1843–1858, 2359). The "switched to BART" template can never fire for engine agents, because they have no `p.reg` (line 1856).
- **Hard-coded post:** "Rosa S." at boot and in the demo (lines 2271, 2350).
- **Cost:** `fetchPosts` runs after *every* new plan id (line 1886). My 5 street, zoning and density edits produced 5 paid posts calls in a few minutes.
- **Fix:** debounce (for example, only after 10 s idle or on Feed open), and cap the number of calls per session.

### B7 · P1 · Radar ghost and axes are hard-coded shapes
- **What:**
  - `BASE_SHAPE = [62, 46, 68, 50, 55, 34]` (line 1748) is drawn as the "baseline" ghost.
  - `engShape` maps $ values through `sqrt(|v|/1e6) * 10` onto that fixed shape (line 1773).
  - The Housing axis is invented from `delta.residents`.
- **Problem:** none of this derives from baseline `metrics`, which is what the integration guide asks for.

### B8 · P1 · The Traffic view ignores the engine's congestion factors
- **What:** the colour is `car_hour / (lanes × 560 or 1900) / 1.15 × 3`, eased frame by frame (line 1548), mapped through the toy calibration `CAL.vlo/vspan` (line 1609).
- **Unused engine data:** `edges.congestion_am` and `congestion_pm`, the engine's own travel-time factors, are not used in the view.
- **Partial use:** `congPm` is stored (line 1057) but never read. The street inspector shows AM only ("Rush-hour delay ×", line 1920).
- **Local thresholds:** the hover text "congestion low/moderate/heavy" uses local thresholds (line 2078).

### B9 · P2 · "New tie" sparks are random, not engine ties
- **What:** pink sparks fire when two agents dwell at the same POI, with `Math.random() < .35` (line 1565). They look like the "New tie" legend item but are not `ties_sample` events.
- **Live stat:** the "New ties so far" stat is `delta.new_ties ×` the share of the `ties_sample` times passed (line 1812). That is an approximation.

### B10 · P2 · Spillover is a local aggregation
- **What:** spillover is computed locally from `car_day` within 700 m of the hero midpoint (lines 2248–2253). It is always relative to 2nd St, even when the edit is elsewhere.
- **Fix:** it should come from the engine, or at least be centred on the actual edits.

### B11 · P2 · Inlet marker positions come from toy gateways and a local Dijkstra
- **What:** I-80 and US-101 badges are placed by routing from toy gateway nodes (lines 1366–1372), not from the engine's `inlets[].at`/`x,z`.
- **Also hard-coded:** the marker set (`HIGHWAYS`, line 724) and the `REGIONS` → inlet mapping. Engine `regions[].car_inlets` is unused.

### B12 · P2 · Hard-coded demo copy that asserts results
- **Beat 1:** "the Fremont and Bay Bridge ramps, Howard and Folsom jam first" (line 2280).
- **Beat 2:** "street life and local business more than make up for it" (line 2291). This is shown even when the engine says otherwise.
- **Beat 3:** "Some traffic spills onto a parallel street; the rest switches to BART or skips the trip" (line 2295).
- **Beat 4:** fallback copy "takes BART to Embarcadero…" (toy path only, line 2315).
- **Toy fallback strings still present:** "About 31,000 commuters" (2278), "1 agent = 6 people … Mockup with illustrative numbers" (2204), and "AI planner (scripted for the mockup)" in a comment (2106).
- **Fix:** make the claims conditional on `delta`.

### B13 · P2 · Toy constants still in live code paths
- **`SCALE = 6`:** used in A5, in the diversion and stat fallbacks, in `recountInlets`, and in `stepAgents` inlet increments (lines 1532, 1545, 1555). These run harmlessly in engine mode because `gin`/`gout` = −1.
- **`WORKDAYS = 250`:** used in the copy "One weekday projected to 250 workdays" and in the economy-line heuristic (line 1793). The engine's `value.factors` should be the source.
- **Category table:** the `CAT` ticket sizes are used for business labels. Fine.

### B14 · P2 · Two of four ad-hoc AI fallbacks are still toy-scripted
- **What:** with no engine, `candidateOptions`/`trialScn` (lines 2109–2122) run three hard-coded proposals (upzone near 2nd St, New Montgomery, tower to housing) through the toy model.
- **Status:** labelled "scripted" only in a comment. They are fine as an offline fallback, but nothing in the UI says the options are canned.

---

## C. Engine capabilities not exposed

| # | Prio | Capability | Status in UI | Suggested minimal UI |
|---|---|---|---|---|
| C1 | P1 | **Policies**: `congestion_charge` (with an inlet `target`), `parking_price`. `GET /policies` lists the params (amount 0–50, target). | Only reachable when the AI proposes one. The user can't add, edit or remove a policy. | A "Policies" dock button with a small popover: a toggle plus a $ slider for the congestion charge, and a target dropdown (All / I-80 / US-101 / Folsom · 6th / per-side) built from `world.inlets` filtered to `mode==='car' && has_entry`. Also a parking price slider. Show active policies as removable chips under the City Value. Clicking an inlet badge could offer "Charge entry here". |
| C2 | P1 | **`reopened` / `reopen_mode`** (reopen Market St, optionally `pre2020`) | `togglePed` blocks base car-free edges with a toast (line 1895). `editsFrom` supports `reopened`, but the page never fills it. | In the street inspector for a `BASE_CF` edge: a "Reopen to cars" button, plus a "with pre-2020 turn restrictions" checkbox. Draw reopened edges with a dashed asphalt outline. |
| C3 | P1 | **`GET /scenarios`** (saved, cached plans with `value_total`) | Unused. The page always sends `name: 'Plan A'`, so every saved plan is named "Plan A" and they can't be told apart. | A "Plans" dropdown next to the Baseline/Plan A switch. It lists `/scenarios` (name, $ value) and loads one via `getScenario(id)` plus its `edits`. A "Save as…" option sets `name` on POST. |
| C4 | P2 | **`/agent` for any clicked person** | Wired (followPerson, 2021). But see A4, B5, and note that the `diary` events' `with`/`poi` and `ties[].new_in_plan` aren't highlighted on the map. | Use the engine name everywhere. Draw the plan trail from `view.plan.trips` instead of the sampled trips, and mark `meet` diary events with a pin. |
| C5 | P2 | **`/narrative/diary`** | Never called (`narrative.diary` has 0 references). | A "Read Maria's day" link in the person inspector: one call, cached per (plan, agent). |
| C6 | P1 | **`value.lines`** | Used in pillar tooltips (title attribute only) and the top 4 in the pitch. | Expand a pillar on click into its line items (`label`, `qty unit`, `usd_per_yr`). The data is already there. |
| C7 | P1 | **`assumptions`** (38 in each result) | Unused (0 references). | An "Assumptions (38)" link in the Impact srcline. It opens a list of key, status and note, with assumed items flagged amber. |
| C8 | P1 | **`world.params` provenance** (value, status, source URL) | Only the three counts appear in the pitch footnote. | The same drawer as C7, with a "Parameters" tab: a table with status pills and source links. |
| C9 | P2 | **SpacetimeDB live layer** (`connectLive`: shared plan, presence, cursors, activity feed) | Not integrated (0 references). | Behind a `?live` flag: route `togglePed`/`setBlock` to `live.setPedestrian`/`setBlock`, render `state.players` cursors, and feed `state.activity` into the Feed tab. Fetch the full result via `GET /scenario/{plan_id}`. |
| C10 | P2 | **Droid** `/droid/ask` (grounded answers with references, focus, highlights, `info_view`, `time_s`) | Unused. Ask goes to explain or the planner. | Route why-questions to `/droid/ask?stream=1`. Show the step list while it works, then `applyDroidAnswer` (fly to `focus`, highlight, switch the info view), and show references as chips. |
| C11 | P2 | **Droid policy compiler** `/policies/propose`, approve and reject | Unused. | A "Propose a new lever…" text field in the C1 popover that lists proposals with Approve/Reject buttons. |
| C12 | P2 | **Unused metrics**: `access_15min`, `market_bus_time_index`, `neighbor_ties`, `jobs_housing_ratio`, `walker_visits_per_day`/`driver_visits_per_day`, `through_charges_paid_usd`, `metrics.trips.bike`, most of `by_income` | Not shown. | A collapsible "More metrics" table in the Impact pane (baseline / plan / Δ). Show the Market St bus index when C2 is used. |
| C13 | P2 | **`edges.congestion_pm`, `edges.car_free`, `settle.converged/gap`, `regions[].car_inlets`, per-inlet `entered_hour`** | Stored or ignored. | An AM/PM toggle in the Traffic legend. Use `car_free` (base + plan) for paving instead of local sets. Show "not converged (gap 3%)" in the note. Clicking an inlet badge opens a 24-hour in/out sparkline. |
| C14 | P2 | **Rezoning creates `virtual_pois` (≥ 5000)** | Loaded into `s.pois` (1059), but they get no marker on the map. They only appear in the block inspector's "Top businesses". | Small "new shop" pins on rezoned blocks, opening the business inspector. |

---

## Priority summary
- **P0:** A1 (dropped edits during a settle), A2 (no timeout, so the UI can lock).
- **P1:**
  - Broken: A3–A9.
  - Local or mocked: B1–B8.
  - Not exposed: C1–C3, C6–C8.
- **P2:** everything else.
