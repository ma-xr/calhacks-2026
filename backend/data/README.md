# Data pipelines (backend/data)

These scripts build clean JSON inputs for the simulation in `data/backend/`. Each output has a top-level `meta` object with sources, fetched_at, notes and caveats.
Raw responses are cached in `data/cache/<service>/`, each with a sidecar `.params.json` (the key/token values are never written).
Every external call is logged in `data/cache/USAGE.md`.

```
backend/.venv/bin/python backend/data/run_all.py            # rebuild all outputs from cache (no network)
backend/.venv/bin/python backend/data/run_all.py --online   # also fetch missing free sources (never starts Apify)
backend/.venv/bin/python backend/data/<script>.py           # one source (uses cache first; fetches if missing)
```

`common.py` holds the world.json projection (x = (lon+122.3987)*KX, z = -(lat-37.7887)*KZ), the bbox, the cache, usage-log and geometry helpers. Keys are read from `.env` (CENSUS_API_KEY, SODA_APP_TOKEN, APIFY_TOKEN).

| script | output | source |
|---|---|---|
| `lodes.py` | `lodes.json` | LEHD LODES8 CA 2023: xwalk, WAC S000 JT00, OD main JT00 |
| `acs.py` | `acs.json` | ACS 5-yr 2019-2023 (api.census.gov), Census Gazetteer 2023 tracts |
| `landuse.py` | `landuse.json` | DataSF land use `c5ge-t6pj` (current), `fdfd-xptc` (2023, archived), zoning `3i4a-hu95` |
| `businesses.py` | `businesses.json` | Apify `compass/crawler-google-places` (Google Maps) |
| `transit.py` | `transit.json` | BART monthly ridership report (Sep 2026) + hourly OD 2025 |
| `traffic_counts.py` | `traffic_counts.json` | Caltrans AADT FeatureServer + DataSF bike manual counts `v4v2-5x7s` |

## Rules and definitions
- **LODES home regions**: east_bay = Alameda+Contra Costa+Solano; peninsula_south_bay = San Mateo+Santa Clara; north_bay = Marin+Sonoma+Napa. For SF homes: `sf_in_area` if the home block is inside the sim bbox, else `sf_west` if lon < -122.44, else `sf_north` if lat > 37.79, else `sf_southeast_mission`. Any other CA county is `other`. `home_region_share_excl_far` drops homes more than 150 km away (LA, San Diego and so on, mostly HQ-reporting artifacts). This is the recommended share for generating agents.
- **Work blocks** are 2020 blocks whose internal point is inside the bbox. Jobs come from WAC (CE01-03 are reported as SE01-03).
- **ACS workplace geography** (B08406 mode, B08602 arrival time, B08534 travel time) is published at county level only, so SF County stands in for FiDi. There is no "time leaving home" table for workplace geography, so B08602 (time arriving at work) is the workplace equivalent.
- **Land-use matching**:
  1. A building's centroid inside a parcel claims that parcel (the smallest containing parcel wins). If several buildings sit in one parcel, its floor area is split by footprint area × height.
  2. A parcel with no building centroid is assigned whole to the building whose footprint contains the parcel centroid. Failing that, it goes to the nearest building within 40 m, but only if it has floor area.
  3. A building that is still unmatched gets landuse and zoning from the nearest parcel within 40 m, with zero floor area.
- **Businesses**: one search over the bbox polygon with the terms restaurant, coffee shop, fast food, bar, store and grocery store. The run used `maxCrawledPlacesPerSearch` = 150 and `scrapePlaceDetailPage` = true, which is needed for popular times. Each place's category comes from its primary Google category.

## Apify usage
- Test run `t842O99WQClgBGUJs` (8 places): $0.05. Full run `vbfPXBeCW7izCHgG1` (868 places, dataset `gG8r6GzU7zcZHtRdK`): $5.21. Total about $5.26.
- Price checked via the API: $0.004 per place plus $0.002 per place for detail pages (FREE tier).
- `businesses.py` reuses the cached run record and items, and never starts a second run while `data/cache/apify/full_items.json` exists. It never deletes or modifies Apify resources.

## Gaps / blocked sources
- **SF motor-vehicle traffic counts**: there is no SFMTA vehicle count dataset on DataSF (`data.sfgov.org` now redirects to `data.sf.gov`). Searched on 2026-10-24 for: traffic count, traffic volume, vehicle counts, ADT, volume. The catalog also returns other cities' "Traffic Counts" datasets, which are not SF.
  - Used instead: Caltrans AADT points on I-80 and the Bay Bridge ramps (5 points), plus SFMTA bike PM-peak counts (11 points, from 2017 or earlier).
  - Caltrans PeMS needs an account login, so it was skipped.
- **BART hourly OD**: published only as whole-year files, and the 2026 file was empty at fetch time. The hourly shape uses Sep 2025 weekdays; daily volumes come from the Sep 2026 report.
- **Land use 2026 dataset** (`c5ge-t6pj`) has no landuse category or residential sqft. Residential sqft comes from the 2023 dataset, joined on mapblklot, and is incomplete.
- **Popular times** exist for about 40% of places, because Google shows them mainly to logged-in users.
