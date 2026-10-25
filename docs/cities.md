# City environments

The homepage lets the user pick a city. Each city is the same kind of 3D environment: a ~1.9 × 1.9 km simulated box of real OSM buildings (with building parts and roofs), streets, transit stations and entry roads, plus the faded surrounding city, water and a dashed boundary.

| id | City | Area | Page (served from `mockup/`) | Simulation |
|---|---|---|---|---|
| `sf` | San Francisco | Financial District + SoMa | `/cities/sf/` | **Full engine** (live API or snapshot), demo, AI planner, policies, Go live |
| `chicago` | Chicago | The Loop: Chicago River / Marina City to Van Buren, Canal St to Millennium Park | `/cities/chicago/` | **Explore mode**: 3D city with placeholder traffic; engine data comes later |
| `nyc` | New York | Midtown Manhattan: 34th St to ~55th St, 8th Ave to Lexington | `/cities/nyc/` | **Explore mode** |

**For the homepage:** link to `cities/<id>/index.html` relative to the `mockup/` root, e.g. `http://localhost:8765/cities/chicago/index.html`. The SF page is the full product. It's the same build as `variants/a1-skyline-clean/`, which keeps working.

## Data
- **Config:** `scripts/cities.py` holds each city's center (frame origin), simulation bbox, district labels and wanted landmarks.
- **Download:** `scripts/fetch_city.py <id>` caches four Overpass queries in `data/raw/<id>/`: core, context, coast + water, building parts.
- **Build:** `scripts/build_city.py <id>` writes `data/processed/<id>/`:
  - `world.json`: same schema as SF's (buildings, road graph, POIs, stations, gateways)
  - `context.json`: surrounding buildings, roads, parks, real coastline land, rivers and lakes
  - `buildings_detail.json`: building parts, roof shapes, colours
  - `city.json`: name, area, box in meters, district labels, landmark positions, stations ranked by entrances, and `engine: true|false`
- **SF exception:** SF keeps its original files in `data/processed/`, which the engine reads. `build_city.py sf` only writes `city.json`.
- **Page build:** `scripts/build_mockup.py <template> <out> --city <id>` inlines that city's world, context and building detail, and replaces `__CITY__` with its `city.json`.

## Frontend contract (Skyline Clean template)
- **Config:** `<script id="city" type="application/json">__CITY__</script>` gives the page its city config.
- **SF** (`engine: true`): unchanged behaviour.
- **Other cities** (`engine: false`), explore mode:
  - No engine connection. Show an honest status: "Explore mode · simulation data for <City> coming soon".
  - Placeholder agents from the in-browser model, entering at the city's own gateways (highway ends and boundary crossings) and stations.
  - Hidden or disabled with a clear note: scripted SF demo, AI planner, Ask, Policies, Go live, pitch, engine-only info views (revenue change, visits). Workplaces, Residents and Zoning can use building types locally.
  - Land and water: `HPContext.add(..., { inside: true })` draws the real coastline, rivers and parks inside the box too, instead of SF's Embarcadero shoreline.
  - Labels from `city.json`: districts, landmarks (name + height), the top stations. Highway badges at the city's freeway gateways, plus the per-side entry labels.
  - Camera presets derived from the box (Overview, plus two zooms around the densest landmarks), and the brand line "CommonGround · <City> · <Area>".
  - City switcher in the top bar (SF / Chicago / New York) linking to the sibling pages.
