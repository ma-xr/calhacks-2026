# Backend: CommonGround simulation engine + API

Python 3.9 · numpy · scipy · FastAPI. The API contract is `docs/contracts/sim-api.md`.

```bash
python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt   # once
backend/run.sh                                   # API on :8787; the baseline calibrates in ~5 s (watch /health)
backend/.venv/bin/python -m pytest backend/tests -q
cd backend && .venv/bin/python -m hp.validation  # writes research/validation/README.md
```

Keys come from the project-root `.env`. Only the narrative layer (Anthropic) and the data pipeline (Census, DataSF, Apify) use them. The engine itself is offline and deterministic.

## How one simulated weekday works

| Step | Module | Method | Data / parameters |
|---|---|---|---|
| World | `hp/world.py` | OSM road graph (directed car arcs, undirected walk arcs), buildings, POIs, inlets (3 rail + a car inlet for every road crossing the map edge, generated from `world.json` gateways), blocks (variant A rule) | `data/processed/world.json` |
| Population | `hp/population.py` | Jobs per building from land use (DataSF sqft ÷ sqft/job, office vacancy), scaled to **LODES** jobs in the area. Present workers = office jobs × **Kastle** occupancy + other jobs × attendance. Residents = units × household size, scaled to the **ACS** tract population. Plus visitors and through-traffic. Home region and earnings tier come from **LODES OD** | `data/backend/lodes.json`, `acs.json`, `landuse.json` |
| Car inlets | `hp/world.py` `_inlets`, `Engine._inlet_sets` | Every car road crossing the map edge is a gateway; gateways are grouped by street and side into inlets (5 legacy keys kept). Drivers choose the cheapest inlet of their home region by route cost (one multi-entry tree per region and hour), and through-traffic runs side to side, so closures shift entry points | `region_car_access`, `inlet_class_penalty_min`, `through_inlet_max_penalty_min` (assumed) |
| Mode choice | `hp/engine.py` `Ctx.choose` | Multinomial logit over car / BART-Muni / walk / bike. Inputs: time inside and outside the map, walk time ×2, parking, toll, fare, vehicle operating cost and policies. VOT varies by income tier. Alternative-specific constants are **calibrated** to the downtown worker mode split | `downtown_sf_worker_mode_share`, `beta_time_per_min` |
| Assignment | `hp/network.py`, `Ctx.load_cars` | Hourly shortest-path trees per inlet on the real graph. BPR congestion (`bpr_alpha`, `bpr_beta`, lane capacities) and background traffic share. Flows are loaded by exact subtree accumulation. Replanning days use the method of successive averages on flows | MATSim-style settle loop |
| Evaporation | `Ctx.choose` | Comes out of the model: mode shift through the logit, trip suppression from a time elasticity (`car_trip_time_elasticity`), and through-traffic choosing a freeway bypass | validated vs Cairns et al. |
| Walking / cycling | `WalkNet` | All-pairs walking (perceived cost with a comfort bonus on car-free streets). Cycling uses three stochastic route draws | `car_free_*_comfort_bonus`, `route_noise_sd` |
| Destinations | `Ctx.choose_poi` | Huff/MNL: log(category weight × Google quality) − distance decay + car-free frontage bonus + Gumbel noise. The noise uses common random numbers by agent id | Apify Google Maps (rating, reviews) |
| Retail | `Ctx._outputs` | Visits = destination visits + walk-by impulse visits from **pedestrians only**, so walkers visit more often. Revenue = visits × ticket | `impulse_capture_per_passerby`, `avg_ticket_usd` |
| Social | `Ctx._outputs` | Co-presence at the same POI in 15-minute windows, capped per person, plus lingering on car-free streets. Ties form from habitual encounters. Neighbouring follows Appleyard (friends fall with street traffic) | `tie_formation_prob_*`, `appleyard_friends_by_traffic` |
| Land use | `population.py` / `_outputs` | Density and zoning edits change jobs and residents per building, adding or removing agents. Also reports jobs-housing balance, 15-minute access (food, café, shop, park, station within 1.2 km), and a rent-pressure index | |
| Valuation | `hp/results.py` | Mobility = logit consumer surplus (log-sum) for commuters + through-traffic + background delay. Health = WHO HEAT × VSL. Environment = SCC × CO₂ + crash costs. Economy = value added × net-new share + sales tax + property tax. Social = ties and encounters | every factor is in `value.factors` |

**Baseline = 2026 reality.** Market St has been closed to private cars from 10th St to Main St since Jan 29, 2020, so it is car-free in the baseline. An edit can reopen it (`"reopened": [...]`, `"reopen_mode": "pre2020"`); the validation uses this.

**Determinism and fair A/B.** Calibration settles once from cold, and the resulting flows become the shared starting state. The baseline and every plan then run the *same* procedure (5 replanning days), with the same population and the same random draws. A plan with no edits therefore reproduces the baseline exactly (tested), and every delta is an effect of the edit.

**Demo staging (disclosed).** The hero "Maria O." is chosen by rule at startup: an East Bay driver near 2nd St who switches mode when 2nd St goes car-free. Her coworker "Dev P." is given Maria's lunch time and destination noise, so their lunch encounter is scripted. Everything else emerges from the model.

## Layout
```
backend/
  hp/config.py      paths, secrets
  hp/params.py      parameter registry (defaults ← research/parameters/parameters.json)
  hp/inputs.py      loaders for data/backend/*.json (written by backend/data/)
  hp/world.py       graph, buildings, POIs, inlets, blocks
  hp/population.py  synthetic population + density/zoning edits
  hp/network.py     car trees, walking all-pairs, flow accumulation
  hp/engine.py      settle loop, choices, final-day outputs
  hp/results.py     valuation, ScenarioResult JSON, trip samples, agent diaries
  hp/narrative.py   Claude: explain, diary, citizen posts, AI planner (tool use)
  hp/api.py         FastAPI app
  hp/validation.py  model vs. reality report
  data/             data pipeline (LODES, ACS, DataSF, Apify, counts, BART)
  tests/
```
