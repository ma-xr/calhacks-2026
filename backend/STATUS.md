# Backend status

## 2026-10-24 (night) · cars enter and leave at every street crossing the map edge

- **Gateways:** `scripts/build_world.py` now finds every car road crossing the bbox boundary ("cross" gateways, 74), plus the original road ends ("end", 20, unchanged). The rebuilt `world.json` is identical except `gateways` (verified key by key).
- **Inlets:** 65 total = 3 BART + the 5 legacy car keys (`i80`, `us101`, `mkt`, `fol`, `bwy`; same entrances, so the Market St baseline and "Mission carries Market's inflow" still hold) + 57 generated car inlets named by street and side (e.g. `howard_st_south`, "Howard St · south"). A crossing within 300 m of a legacy entrance on the same street counts as that entrance. Generated inlets keep only entries and exits connected to the main network. **Inlet ids are no longer fixed: read the list from `GET /world`** (breaking change in the contract).
- **Demand:**
  - Each home region has a set of usable inlets with extra outside-the-map minutes (`region_car_access`) and a class penalty (`inlet_class_penalty_min`), all marked assumed in `research/parameters/`. Drivers pick the cheapest by route cost (one multi-entry tree per region and hour), so closures shift entry points.
  - Through-traffic runs between map sides, weighted by the lane capacity of each side's eligible surface inlets (`through_inlet_max_penalty_min`), from the cheapest entry to the cheapest exit.
  - Visitors who drive arrive over all car inlets in proportion to capacity.
  - A congestion charge with `target` set to an inlet key is now a toll on entering there, so drivers can avoid it.
- **Calibration:** re-run. Mode split car 35.1 / transit 49.7 / walk 11.1 / bike 4.2 vs target 34.4 / 48.4 / 12.9 / 4.3.
- **Validation (Market St, pre-2020 → car-free), before → after this change:**
  - Worst parallel-street slowdown: Folsom +32.1% → Mission +4.8% (observed ≤ +4%). Folsom is now +4.5%.
  - Muni on Market: +3.5% → +0.0% (observed +6%; new open gap).
  - Cycling on Market: +104% → +98% (observed +25%).
  - Area VMT: −0.3% → −0.6%.
  - Evaporation ratio: −1.7 → −3.3 (unstable: pre-2020 Market carried few cars).
- **Hero plan (2nd St car-free), before → after:**
  - Total value: +$6.4M/yr → **+$9.85M/yr**. Health +$5.3M, economy +$1.5M, social +$1.4M, environment +$1.1M, mobility +$0.5M.
  - 378 fewer car commuters (147 trips skipped), revenue +$21k per day, delay +80 veh-h per day (diverted traffic).
  - **Maria now switches car → BART in the plan** (before she drove in both).
  - Baseline peak delay is lower overall, because cars no longer funnel through 5 gates.
- **Clients updated to read inlets from `/world`:**
  - API `/world` returns the full inlet list plus each region's `car_inlets`; congestion-charge targets are validated against car inlet keys.
  - The AI planner got a `list_inlets` tool instead of a fixed enum.
  - Diaries name the inlet a driver actually used.
  - The policy plugin view adds through-trip sides.
  - `mockup/lib/hp-backend.js` gains `mergeInlets`/`inletByKey`; the fixed `INLET_KEYS` is gone. The a1/a2/a3 templates append every engine inlet, map counts by key, and draw markers for the 8 legacy inlets plus the 12 busiest generated ones; their offline toy model is pinned to the original road-end gateways.
  - `server/spacetimedb` (archived prototype) reads only those original gateways too.
  - The live layer and the Fetch.ai agents never read inlets, so nothing needed to change there.
  - Pages rebuilt; snapshots refreshed, including the Claude narrative.
  - The narrative cache key now includes an engine fingerprint, so it can't serve text that quotes old numbers.
  - In the browser, a1/a2/a3 load in live mode with 65 inlets, 20 markers and no console errors.
- **Tests:** 14 pass. New tests cover: inlets are data-driven and the legacy keys are kept; every car inlet connects to the network; no worker is left without reachable parking; closing the busiest generated inlet's street moves its traffic to other inlets.

## 2026-10-24 (late) · research parameters live, validation fixes

- **Research inputs:** the research agent's `research/parameters/parameters.json` (74 keys: 21 data, 37 literature, 16 assumed) now overrides the engine defaults. Examples: VOT $21.80/h, VSL $14.2M, parking $22/day, BART fares from GTFS, Kastle occupancy 47.2%, FiDi vacancy 29%, MTC lane capacities, car-trip time elasticity −0.5. Case studies, literature and data cards are in `research/`.
- **Bugs that validation caught and that are now fixed** (full list in `research/validation/README.md` → findings log):
  - Closing a street left 7% of workers with no reachable parking.
  - The Market St (west) car inlet entered on Market itself, which is car-free.
  - Evaporation was measured on the wrong denominator.
- **Market St (pre-2020 → car-free):** Muni +3.5% (obs. +6%), Mission +7.6%, Folsom +32% (obs. worst ≤ +4%; open gap), cycling +104% (obs. +25%), area VMT −0.3%.
- **Hero plan (2nd St car-free):** +$6.4M/yr. Health +$3.9M, business +$1.3M, social +$0.8M, environment +$0.35M, mobility ≈ 0. Plan evaluation takes about 0.6 s.

## 2026-10-24 (evening) · all data sources live, validation extended

- **Data:** all six inputs are loaded (`/health` → data all true).
  - LODES 2023: 322k jobs in the area. The engine uses the home-region split that excludes homes more than 150 km away (HQ-reporting artifacts).
  - ACS 2019–23: 37,174 residents, 1.80 persons per household.
  - DataSF land use: 86M sqft office.
  - Google Maps via Apify: 868 places, 388 matched to POIs, 344 with popular times; $5.26 spent.
  - BART Sep 2026 exits.
  - SFMTA bike counts.
  - Caltrans freeway AADT. DataSF has no surface-street car counts, so arterial volumes are modeled only.
- **New in the model:** evening visitors (dinner and drinks) and morning coffee runs. Rezoning to retail or mixed creates shops (`virtual_pois`). Charge and parking revenue are counted as a transfer to the city. The result includes `agents_sample`.
- **Validation** (`research/validation/README.md`):
  - BART hourly arrival shape r = 0.90–0.97.
  - Café and shop timing vs Google popular times r = 0.81–0.91; restaurants 0.65, bars 0.51.
  - Gap: rail-inlet volume is 2–3× BART exits, because the inlet also carries Muni Metro, buses and ferries.
  - Gap: cycling volumes are about 10% of the SFMTA counts (2015–17); through-cyclists are not modeled.
- **Hero plan (2nd St car-free):** +$3.7M/yr in total. Health +$5.9M, business +$1.6M, environment +$0.9M, social +$0.4M, commuter cost −$5.0M. 722 fewer car commuters, revenue +$34k per day, rent pressure +0.3%.

## 2026-10-24 · Milestones 1–3 done, 4–5 working (v0.2)

**For the frontend agent:** the API is live on `http://localhost:8787` (`backend/run.sh`). The contract is `docs/contracts/sim-api.md` (v0.2, additive).
- `GET /world` returns static data for one session: POIs with Google attributes, `block_of`, inlets, regions, hero, params.
- `GET /baseline?lite=1` is about 120 KB. The full result, with hourly arrays and 4k sampled trips, is about 1.7 MB.
- `POST /scenario` takes about 1.5 s for a new plan and returns instantly from cache. `?stream=1` gives SSE "Replanning day k/5" progress.
- `GET /scenario/{id}/agent/{agent_id}` serves Follow Maria. The hero is in `world.hero`, and the 2nd St plan is precomputed (`world.hero.plan_id`).
- `POST /narrative/{explain,diary,posts,planner}` is the Claude layer. The planner takes about 15 s and evaluates real plans.
- **Note:** Market St is car-free in the baseline (2026 reality). Draw `world.base_car_free_edges` as car-free.

| Milestone | Status |
|---|---|
| 1 Contract, data pipeline with caching, research agent | ✅ contract v0.2. Pipeline: LODES ✅, ACS ✅, DataSF land use ✅; Apify businesses, traffic counts and BART in progress. The research agent is writing `research/` |
| 2 Baseline population, demand, assignment, calibrated | ✅ 175k present workers (LODES × Kastle occupancy) and 37k residents (ACS), 14k agents at 19 people/agent. Mode split calibrated (car 29 / transit 56 / walk 11 / bike 4 vs target 28/54/13/4) |
| 3 Plans, metrics, value engine | ✅ pedestrianize, density, zoning, congestion charge, parking price, reopen. All pillars itemized in `value.lines` |
| 4 Validation + hardening | 🟡 `research/validation/README.md`: Market St VMT −11.6% (lit. −11%), Muni +3% (obs. +6%), parallel streets +0.2% (obs. ≤+4%), cycling +179% (obs. +25%, still too high). 2nd St footfall +27% (lit. +29%), fronting revenue +24% (lit. +10–30%). 10 tests pass |
| 5 Narrative layer | ✅ explain, diary, citizen posts, AI planner (tool use; it only proposes edits, and the engine scores them) |

**Known gaps / next:**
- Calibrate `background_traffic_share` and lane capacities against SFMTA counts once `traffic_counts.json` lands.
- Calibrate the hourly visit profile against Google popular times once `businesses.json` lands.
- Cycling route response is still too elastic.
- Load the research agent's `parameters.json`; it overrides defaults automatically on restart.

**v1 → v2 parameter revision (disclosed):** the first validation run used assumed comfort bonuses that overshot: walk 0.30, bike 0.25, car-free POI 0.35, bus exposure 0.5. Footfall came out +91% against +29%, and cycling on Market +530% against +25%. They were revised to the ~10–15% detour tolerance found in route-choice studies (walk 0.10, bike 0.12, POI 0.15, bus 0.25). Footfall then landed at +27%. These were not fitted per case; each is a single global value.
