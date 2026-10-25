# Backend agent briefing: The Human Project

You are the **backend + simulation agent** for *The Human Project* ("modeling urban society with agent swarms"), a Cal Hacks project. Another agent (the "frontend agent") is building the 3D web UI at the same time, in the same folder. Read this whole brief before touching anything.

Project root: `/Users/maximilianthiersch/Projects/Cal Hacks 13` (not a git repo; don't `git init` or reorganize existing files).

---

## 1. What the product is

An interactive 3D San Francisco (FiDi + upper SoMa) where thousands of agents ("sims") commute, shop and meet. A user edits the city in three ways:
- pedestrianize a street
- change a block's density
- change a block's zoning

The city then re-settles, and every metric is shown as **Plan vs Baseline (Δ)**:
- traffic
- foot traffic
- social connections
- local business revenue
- health
- housing and access
- a combined dollar "City Value"

Read these first; they are the source of truth for product intent:
- `docs/spec.md`: product spec, function sheet, 3-minute demo script, metric pillars.
- `docs/research.md`: first-pass prior art (MATSim, CityScope, A/B Street…), techniques (logit mode choice, Huff, BPR, activity schedules), empirical evidence, valuation factors, data sources.
- `docs/redesign-brief.md`: what the frontend is building now (inlets, info views, etc.).
- `data/processed/world.json`: the shared world: real OSM buildings, road graph, POIs, stations, gateways. Its schema is built by `scripts/build_world.py`.
- `mockup/template.html`: a working **in-browser toy simulation** (search `class Scenario`, `modeOf`, `iterate`, `buildTrips`, `project`, `valueOf`). It is your reference for what the frontend currently expects. **Your job is to replace that toy with a real, research-grounded engine.**

## 2. Your mission

Build the real simulation backend: models, calibration and an API that computes everything the frontend displays. It should reproduce **real-world magnitudes and before/after effects** as closely as the literature and data allow. We want to understand how cities function, and to *prove* our realism to judges.

Concretely:
1. **Synthetic population** from real data:
   - Census LODES home→work flows for jobs located in our blocks.
   - ACS income and mode share.
   - Residents from block density.
   Calibrate the overall mode split to SF data (ACS commute shares, SFCTA SF-CHAMP if obtainable).
2. **Activity-based demand.** Each agent gets a daily schedule (arrive, lunch, errands, leave; residents: commute and evening outings). Use time-of-day distributions from data (ACS departure times, NHTS trip-purpose shares).
3. **Mode choice.** Calibrated logit (car / BART-Muni / walk) using travel time, parking cost, transit access and income. Use published SF/Bay Area coefficients where possible.
4. **Route choice + congestion.**
   - Network assignment on the real road graph (BPR or better) with iterative replanning (MATSim-style "settle days").
   - Calibrate link volumes against SFMTA / Caltrans PeMS counts where available.
   - Traffic evaporation should come out of the model: mode shift plus trip suppression, with an elasticity grounded in the evaporation literature (Cairns et al.: median about −11% of traffic on the treated area).
5. **Pedestrian flows and exposure.**
   - Sidewalk flows, and walk-by exposure per storefront.
   - Optional: Space Syntax-style integration as a prior.
6. **Business model.**
   - Visits per POI come from exposure, Huff/gravity and category, calibrated with **Google Maps popular-times data via Apify**.
   - Revenue = visits × ticket by category.
   - Reproduce the pedestrianization retail literature: walkers visit more often rather than spending more per visit; cafés and restaurants gain most.
7. **Social model.** Co-presence encounters (same place and time window, weighted by dwell). Ties form from repeated encounters and strengthen over time. Ground this in the literature on public space and weak ties (Jacobs, Gehl, Hipp & Perrin, etc.).
8. **Land use / zoning / density.**
   - Jobs and residents per block from floor area and use.
   - Office→residential conversion with FiDi vacancy.
   - Jobs-housing balance, 15-minute access, and rent/land-value pressure as an honest trade-off.
9. **Valuation engine.** Metrics → $/yr using USDOT value of travel time, VSL, WHO HEAT (walking health), crash costs (optional), social cost of carbon (as a slider) and value added on retail. Make the factors configurable and documented.
10. **Validation.** Build a scenario that mirrors **Market Street going car-free (Jan 2020)** and compare our outputs with the reported outcomes: about 6% faster Muni, about 4% worst parallel slowdown, cycling +25%. Add other before/after cases where data allows. Write the results to `research/validation/`.

## 3. Research agent (spin up a separate agent)

Spin up a **separate research agent** whose only output goes in `research/`. That folder is for hackathon judges and reviewers to see how much realism and detail went into the simulation. Have it do extensive literature and data research:
- before/after pedestrianization case studies with numbers (Market St SF, JFK Promenade, Times Square, Strøget Copenhagen, Barcelona superblocks, Pontevedra, Oslo car-free centre, Paris Rue de Rivoli, and more)
- traffic evaporation and induced demand
- retail impacts of walkability
- mode-choice elasticities
- zoning and density effects on travel
- office-to-residential conversion
- social interaction in public space
- health valuation
- SF-specific data sources

Suggested structure:
```
research/
  README.md                 # index: what's here, how it feeds the model
  case-studies/             # one .md per case: context, intervention, measured before/after, source links
  literature/               # topic syntheses (traffic evaporation, retail & walkability, mode choice, social ties, zoning/density, valuation)
  parameters/               # parameters.csv/json: every model parameter → value, range, source, notes
  data-sources/             # what each dataset is, license, how we use it
  validation/               # model-vs-reality comparisons (written by you, the backend agent)
```
Every number gets a citation link. The parameter table is the bridge: the backend loads model parameters from `research/parameters/` (or a copy of it), so the documentation and the code can't drift apart.

## 4. Boundaries: who owns what (prevents overwriting)

| Path | Owner | Rule |
|---|---|---|
| `backend/**` (new) | **You** | All engine, API and calibration code |
| `research/**` (new) | **Your research agent** (you write `research/validation/`) | Docs, case studies, parameters |
| `data/raw/**`, `data/cache/**` (new), `data/backend/**` (new) | **You** | Add files; never delete or modify `data/raw/osm_fidi_soma_2026-10-24.json` |
| `data/processed/world.json`, `scripts/build_world.py` | Shared, read-only for both | If you need schema changes, write a **new** file (e.g. `data/backend/world_v2.json`) and document it in the contract; don't modify these in place |
| `docs/contracts/sim-api.md` (new) | **You** author it | The interface spec the frontend will consume (see §5). The frontend agent only reads it |
| `mockup/**`, `scripts/build_mockup.py`, `docs/redesign-brief.md`, `.claude/launch.json` | **Frontend agent** | Do not edit |
| `docs/spec.md`, `docs/research.md`, `README.md` | Shared | Append only, in your own clearly titled sections; never rewrite others' text |

Don't run anything on port **8765** (the frontend's static server). Use **8787** for your API server. If SpacetimeDB is used, run it on its own default port and note it in the contract.

## 5. The contract with the frontend

Write `docs/contracts/sim-api.md` early, even as a draft, so the frontend can integrate. Keep IDs compatible with `world.json`:
- **edge id** = index into `world.edges`
- **building id** = index into `world.buildings`
- **POI id** = index into the filtered POI list (or define a stable `poi_id`)

**Input: scenario edits**
```json
{ "pedestrianized": [edgeId, ...], "blocks": { "<buildingId>": { "scale": 1.5, "zone": "res|office|retail|mixed" } } }
```

**Outputs per scenario**: baseline and each plan, for one simulated weekday:
- `metrics`: everything in the toy's `S.m`. That covers car/transit/walk trip counts, VMT, vehicle-hours, delay hours, walking minutes, revenue, encounters, ties, jobs, residents, and per-income-tier time and walk figures. Add anything new, documented.
- `value`: the $/yr by pillar (mobility, street life and social, local economy, health) plus the total, with factors used.
- `edges`: per-edge car flow by hour, ped flow by hour, congestion factor.
- `pois`: visits per day and per hour, revenue.
- `blocks`: block id per building; jobs, residents and visits per block.
- `inlets`: entered/left counts by hour for the 8 inlets. These are BART Embarcadero, Montgomery and Powell, I-80 Bay Bridge, US-101, Market St west, Folsom·6th, and Broadway·Columbus.
- `trips`: a sample of agent trips for animation, `{agent_id, mode, t_start, t_end, path:[edgeIds] or polyline, purpose, inlet_in, inlet_out}`. A few thousand max, and say what share of the full population they represent.
- `agents` (sample): profile, mode baseline vs plan, diary events (for "Follow Maria"), ties.

The frontend needs **interactive latency**. Re-settling after an edit should return in about 2 s or less, or stream progress such as "replanning day k/5". Precompute the baseline and cache everything.

Transport: an HTTP JSON API (`POST /scenario`, `GET /scenario/{id}`, `GET /baseline`), and/or SpacetimeDB tables (the spec lists SpacetimeDB as the preferred live state layer if convenient). Write a small example client call into the contract.

## 6. APIs and data access

The user has API access for this project; the keys are in the environment or in `.env` at the project root. **Never print, log or commit key values.** Check which ones are actually present before planning around them. Expected or relevant:
- **Apify**: Google Maps scrapers for businesses in our area: ratings, price level, categories, **popular times**, reviews count.
- **Google Maps Platform**: Places and Routes, if a key is present. Use it to validate travel times.
- **Anthropic API**: only for the narrative layer (sim diaries, citizen posts, AI planner explanations), never for the core math. Use `claude-haiku-5-5` for tests and `claude-sonnet-5-5` / `claude-opus-5-5` only where quality matters.
- **SpacetimeDB**, if available.
- **Census API key**: ACS income, mode share and household data. LODES needs no key.
- **DataSF app token**: land use, zoning and bike counts.
- **Factory Droid**: part of the product. It runs the policy builder, and a live in-sim agent is in progress.
- **Fetch.ai Agentverse / ASI:One**: the four analyst agents in `agents/fetch/`, which call this API.
- **Present in `.env` but not used yet**: Google Maps Platform (Google data comes through Apify instead), Elastic, Moss.
- **Free public data**, no key needed or a free key: DataSF/Socrata (zoning, land use, building footprints, registered businesses, SFMTA counts, TransBASE crashes), Census LODES and ACS, 511.org GTFS (BART/Muni), Caltrans PeMS, OpenStreetMap/Overpass.

Another user may be running a similar project on the same API accounts. Ignore that, and don't delete or modify any resources (Apify datasets, actors, tasks) you didn't create.

**Be frugal with API usage:**
- Cache every API response to `data/cache/<service>/…` (raw JSON plus request params), and always check the cache before calling. Never re-fetch what is cached.
- Develop and test against tiny samples first: e.g. 10 POIs, one street, one hour. Run a full pull exactly once, after the pipeline works.
- For Apify: set `maxItems` / result limits, reuse existing datasets you created, and keep one consolidated run for the whole area rather than many small runs. Estimate cost before running.
- For Overpass and public APIs: one bulk query, cached, with a polite User-Agent.
- Keep a running log of calls and approximate cost in `data/cache/USAGE.md`.

## 7. How to work

- **Language:** your choice. Python (numpy/scipy, networkx or igraph, FastAPI) is the natural fit. Put dependencies in `backend/requirements.txt` (or equivalent) and a `backend/README.md` with run instructions.
- **Determinism:** fixed seeds, so baseline vs plan differences are real effects and not noise. Use the same population for both scenarios.
- **Performance:** vectorize; precompute shortest-path trees per origin; cache baseline assignments; settle a plan incrementally from the baseline.
- **Tests:** unit tests for each model component, plus a regression test: the Market St car-free scenario stays within the validated bands.
- **Honesty:** where a quantity is extrapolated or assumed, mark it in the parameter table and expose it in the API (e.g. `assumptions[]`). The judges should see calibrated vs assumed at a glance.
- **Milestones:**
  1. Contract draft, data pipeline with caching, and the research agent kicked off.
  2. Baseline population, demand and assignment, calibrated.
  3. Plan scenarios with edits, plus the metrics and value engine.
  4. Validation report and API hardening.
  5. Narrative layer.

  After each milestone, append a short status note to `backend/STATUS.md` so the frontend agent and the user can follow along.

## 8. Current frontend status (for context)

The frontend is iterating on three design-language variants of the 3D UI in `mockup/variants/{a-skyline,b-nightops,c-papermodel}/`; the user will pick one. They all still run the toy in-browser sim. Once your API contract and baseline exist, the frontend will switch to calling your backend. So keep the outputs above stable and documented, and flag any breaking change at the top of `docs/contracts/sim-api.md` with a date.
