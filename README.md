# CommonGround

**Modeling urban society with agent swarms.** A 3D simulation of a weekday in San Francisco's Financial District and SoMa. About 270,000 people commute, shop, walk and meet, built from real data: OpenStreetMap, Census LODES/ACS, DataSF, BART ridership and Google Maps via Apify.

Make a street car-free, rezone a block or add a congestion charge. The engine replans the city over five simulated days and shows the effect on traffic, foot traffic, social connections, local business, health and a combined City Value. Everything is compared against today.

Cal Hacks 2026 · Aziz Derbel, Maximilian Thiersch and Phi Linh Phan

## Quickstart

Requires **Python 3.9+** and `curl`. No API keys are needed to run the simulation.

```bash
git clone https://github.com/ma-xr/calhacks-2026.git
cd calhacks-2026
./run.sh
```

On the first run, `run.sh` creates `backend/.venv` and installs the engine's dependencies (about a minute). It then starts:
- the **simulation engine** on http://localhost:8787, which calibrates the baseline in about 10 s
- the **web app** on http://localhost:8765, opened automatically at the projects homepage `home/`. Click the San Francisco card (or **Play demo** on it) to open the 3D app at `variants/a1-skyline-clean/`

Stop both with **Ctrl-C**. Logs are in `.run/`. Change the ports with `HP_PORT=… WEB_PORT=… ./run.sh`.

### The CommonGround website (workspaces)
`mockup/site/` is the team website: a home page, workspaces, invite links with admin, editor and viewer roles, and plans that move through a Draft → In review → Approved → Archived board. It runs on its own SpacetimeDB module (`backend/workspaces/`, database `commonground`), separate from the 3D app and its Go live. On Windows, `.un.ps1` starts everything and opens http://localhost:8765/site/. Elsewhere: run `./run.sh`, then `spacetime start` and `cd backend/workspaces && npm install && npm run publish:local`. To demo collaboration on one computer, use **Add another person** in the account menu.

### Optional: AI features
Copy `.env.example` to `.env` and add:
- `ANTHROPIC_API_KEY` for the AI planner's explanations, citizen posts and "why" answers
- `FACTORY_API_KEY` for **Ask the city** (Droid live agent) and the Droid policy compiler. This also needs `cd backend/droid && npm install` (Node 18+).

Without keys, those panels say so, and everything else works.

### Collaborate: one shared plan
```bash
./run.sh --live
```
This also starts the shared session: SpacetimeDB on `:3000`, which needs the [SpacetimeDB CLI](https://spacetimedb.com/install) and Node 18+. It then prints a link like `http://192.168.x.x:8765/variants/a1-skyline-clean/index.html`.

Collaborators on the same network open that link and press **Go live** in the dock. Everyone then edits the same plan:
- car-free streets and block edits sync in about 3 s, together with the engine's result
- each person's name and cursor appear on the map
- an activity feed shows who changed what
- Reset clears the plan for everyone

If macOS asks whether Python, spacetime or node may accept incoming connections, allow it. The engine call from SpacetimeDB goes through a small proxy on the host's global IPv6 address. If the host has no IPv6, edits still sync but plans won't recompute; see `backend/live/README.md`.

### Offline / static
`mockup/variants/a1-skyline-clean/index.html?snapshot` replays frozen engine results with no engine running. Serve `mockup/` with any static server. Published demo: https://claude.ai/artifact/PH5gp1pVKFvpRW7kvmvfm1

## Using it
- **Projects home** (`/home/`): the San Francisco project shows live numbers from the engine (people, agents, inlets, POIs), its recent scenarios run against the engine, and the engine's calibration against ACS. Other cities are shown in setup, without results. `/home/?reel=1` clicks into San Francisco by itself and starts the guided demo.
- **Play demo** walks through a 2-minute story: the morning rush, making 2nd St car-free, comparing to today, following one commuter, the AI planner, and the pitch.
- **Edit tools:** make a street car-free (drag along it), change density, rezone a block. Every edit runs the real engine.
- **Info views:** traffic, foot traffic, workplaces, residents, visits, zoning, connections, revenue change.
- **Compare:** swipe between today and your plan.
- **Policies:** congestion charge on any entry road, parking price, reopening Market St (pre-2020).
- **Ask the city:** questions answered from the simulation, with the map flying to what's mentioned.
- **Go live:** edit one plan together with others on your network (`./run.sh --live`).
- **About the numbers:** every parameter with its source, marked as data, literature or assumed.

## How it works

| Part | Where | Notes |
|---|---|---|
| Simulation engine + API | `backend/` | Python, numpy/scipy, FastAPI. Activity-based demand, logit mode choice, BPR assignment with 5 replanning days, Huff destination choice, co-presence social ties, valuation (USDOT, WHO HEAT). See `backend/README.md` and `backend/STATUS.md` |
| API contract | `docs/contracts/sim-api.md` | Every endpoint and field |
| Research and validation | `research/` | Literature, case studies (Market St, JFK Promenade, superblocks…), the parameter table with sources, and the model-vs-reality validation |
| Web app | `mockup/variants/a1-skyline-clean/` | three.js. `template.html` is the source; `scripts/build_mockup.py` builds `index.html` |
| Shared frontend libraries | `mockup/lib/` | `hp-backend.js` (engine connector), `hp-context.js` (faded city around the map), `hp-buildings.js` (recognizable SF buildings), `hp-ask.js` / `hp-policy.js` (panels), `hp-live.js` (Go live: shared plan via SpacetimeDB) |
| World data | `data/processed/` | `world.json` (roads, buildings, POIs, gateways), `context.json` (surrounding city), `buildings_detail.json` (building parts and landmarks). All built from OSM by `scripts/build_*.py` |
| Engine inputs | `data/backend/` | Cleaned LODES, ACS, land use, businesses, traffic counts, BART |
| Offline snapshot | `mockup/backend-snapshot/` | Frozen engine results. Refresh with `scripts/snapshot_backend.py` while the engine runs |

Rebuild the web app after editing a template:
```bash
python3 scripts/build_mockup.py mockup/variants/a1-skyline-clean/template.html mockup/variants/a1-skyline-clean/index.html
```

Run the engine's tests:
```bash
backend/.venv/bin/python -m pytest backend/tests -q
```

## Design history
`mockup/variants/` keeps the explored design directions with their UX reviews: Skyline, Night Ops, Paper Model, and the Skyline Clean / Overview / Guided refinements. Skyline Clean is the product. Planning docs are in `docs/`: `spec.md`, `research.md`, the design briefs, and `backend-integration.md` / `context-layer.md` for the shared libraries.

## Data and licenses
Map data © OpenStreetMap contributors (ODbL). Census LODES/ACS, DataSF and BART data are public. Google Maps place data was collected via Apify for research use. The large raw downloads (`data/cache/lodes`, `data/cache/bart`) aren't in the repo; `backend/data/` re-fetches them, using the keys listed in `.env.example`.
