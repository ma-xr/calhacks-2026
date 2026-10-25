# DataSF (San Francisco Open Data) and related SF city data

## What it is
San Francisco's Socrata open-data portal. **Domain change:** `data.sfgov.org` now returns a 301 redirect to **`data.sf.gov`** (checked 2026-10-24 with `curl -i https://data.sfgov.org/api/views/3i4a-hu95.json`). Old `/resource/<id>` links still resolve if you follow redirects (`curl -L`).

- API pattern: `https://data.sf.gov/resource/<id>.json?$where=...` (SoQL). Metadata: `https://data.sf.gov/api/views/<id>.json`. Landing page: `https://data.sf.gov/d/<id>`.
- Without an app token, requests are throttled. A free token from the portal is recommended for bulk pulls.

## Datasets: IDs checked against the live metadata API on 2026-10-24
| Dataset | ID | Publisher (attribution) | License | Rows last updated | Update frequency |
|---|---|---|---|---|---|
| Building Footprints | `ynuv-fyni` | City and County of SF | ODC PDDL | 2026-10-24 | As needed |
| Zoning Map – Zoning Districts | `3i4a-hu95` | SF Planning Dept | ODC PDDL | 2026-10-24 | Quarterly |
| Registered Business Locations – SF | `g8m3-pdis` | City and County of SF (Treasurer-Tax Collector) | ODC PDDL | 2026-10-24 | Daily |
| San Francisco Land Use (current, parcel-level LUDB) | `c5ge-t6pj` | SF Planning Dept | CC0 1.0 | 2026-08-17 | As needed |
| SF Land Use 2023 (archived) | `fdfd-xptc` (map `k8rg-ihdq`, no-geom `qbf8-heuf`) | SF Planning Dept | Public Domain | 2024-03-07 | Archived |
| Map of Land Use 2020 (archived) | `us3s-fp9q` | — | — | 2023-10-17 | Archived |
| Traffic Crashes Resulting in Injury (TransBASE replacement) | `ubvf-ztfx` | SFDPH/SFPD | ODC PDDL | 2026-10-07 | Quarterly |
| ... Parties Involved / Victims Involved | `8gtc-pjc6` / `nwes-mmgh` | SFDPH/SFPD | ODC PDDL | 2026-10-07 | Quarterly |
| Traffic Crashes Resulting in Fatality | `dau3-4s8f` | — | — | 2026-09-25 | — |
| 2024 High Injury Network | `enwt-3u8m` | — | — | 2026-03-23 | — |
| Speed Limits per Street Segment | `3t7b-gebn` | SFMTA | ODC PDDL | 2026-10-24 | As needed |
| SF Speed Limit Compliance (2016, historical speed surveys) | `wytw-dqq4` | SFMTA | — | 2016-09-14 | — |
| SFMTA Transit Vehicle Location History (Current Year) | `x344-v6h6` | SFMTA | ODC PDDL | **2021-12-31 (stale)** | "Daily" |
| Muni Stops | `i28k-bkz6` | SFMTA | ODC PDDL | 2026-04-11 | Every service change |
| Muni Simple Routes | `9exe-acju` | SFMTA | — | 2026-04-11 | — |
| Bike Volume – Manual Counts (2006–2017 PM peak) | `v4v2-5x7s` | — | ODC PDDL | 2024-01-18 | Annually (in practice stopped after 2017) |
| Travel Decision Survey 2019 (SFMTA) | `qmdj-wtj2` | SFMTA | — | 2020-01-28 | Historical only |
| BART Daily Station Exits (mirror of BART data) | `m2xz-p7ja` | BART | CC0 1.0 | 2025-11-20 (data through 2025-07-31) | Monthly |
| Taxable Commercial Spaces (commercial vacancy tax) | `rzkk-54yv` | Treasurer-Tax Collector | ODC PDDL | 2026-10-24 | Daily |
| Sales Tax by Census Block | `6k2u-yz39` | — | ODC PDDL | 2026-07-21 | Quarterly |
| SF Development Pipeline | `6jgi-cpb4` | SF Planning | — | 2026-08-28 | — |

Metadata source for every row: `https://data.sf.gov/api/views/<id>.json` (fields `attribution`, `license.name`, `rowsUpdatedAt`).

### Not on DataSF (checked with portal search, 2026-10-24)
| Want | Where it actually is |
|---|---|
| **TransBASE** | Retired. The `ubvf-ztfx` description says transbase.sfgov.org "is no longer in operation" and redirects to that dataset. |
| **SFMTA traffic (vehicle) counts** | No DataSF dataset. Historical 24-hour ADT counts for 1993–2015 are a PDF: https://www.sfmta.com/sites/default/files/reports/2016/SFMTA%20Traffic%20Count%20Data%201993-2015%20with%20cover%20sheet.pdf . SFCTA's count database code is at https://github.com/sfcta/CountDracula . Newer counts are by request (unverified whether any are public). |
| **Arterial speeds** | SFCTA CMP (INRIX-based). See `sfcta-sf-champ.md`. |
| **Muni ridership** | SFMTA "Muni Data" dashboards, https://www.sfmta.com/muni-data . Systemwide monthly CSV: https://transtat.sfmta.com/t/public/views/SystemwideRidershipRecovery/MonthlySystemwideRecoveryAccessibleTable.csv . Route-by-month boardings: https://www.sfmta.com/reports/average-daily-muni-boardings-route-and-month-pre-pandemic-present . No public stop-level APC download was found. |

## Fields we use
| Dataset | Fields |
|---|---|
| `ynuv-fyni` Footprints | `sf16_bldgid`, `mblr` (block-lot), `hgt_median_m` (height, text type, so cast it), `gnd_min_m`, `peak_1st_m`, `shape` |
| `3i4a-hu95` Zoning | `zoning` (e.g. C-3-O), `zoning_sim`, `districtna`, `gen`, `the_geom` |
| `g8m3-pdis` Businesses | `dba_name`, `self_reported_naics_code`, `location_start_date`, `location_end_date`, `dba_end_date`, `location`, `business_corridor`, `neighborhoods_analysis_boundaries` |
| `c5ge-t6pj` Land Use | `mapblklot`, `resunits`, floor area (sq ft) by use: `cie` (cultural/institutional/educational), `med` (medical), `mips` (office: management, information, professional services), `retail` (retail/entertainment), `pdr` (production/distribution/repair), `visitor` (hotel), `total_comm` |
| `ubvf-ztfx` Crashes | `collision_datetime`, `tb_latitude`/`tb_longitude`, `collision_severity`, `type_of_collision`, `party1_type`, `ped_action`, `dph_col_grp_description`, `cnn_intrsctn_fkey` |
| `3t7b-gebn` Speed limits | `cnn`, `street`, `speedlimit`, `schoolzone` |
| `m2xz-p7ja` BART exits | `date`, `day_of_week` (`w`, `sa`, `su`, `hol`), station columns `em`, `mt`, `pl`, `cc` ..., `total` |

## How the model uses it
| Module | Datasets |
|---|---|
| Land use / population of buildings | Land Use `c5ge-t6pj` (office sq ft gives jobs per building, residential units give residents), Footprints `ynuv-fyni` (heights and floors) |
| Valuation / zoning scenarios | Zoning `3i4a-hu95`, Development Pipeline `6jgi-cpb4`, Taxable Commercial Spaces `rzkk-54yv` (vacancy) |
| Retail | Registered Businesses `g8m3-pdis` (where shops are, by NAICS), Sales Tax by Census Block `6k2u-yz39` (spend calibration) |
| Mode choice / assignment | Speed limits (free-flow speed), Muni Stops, Travel Decision Survey 2019 (mode-share prior) |
| Validation | Injury crashes as a pedestrian/vehicle exposure proxy, BART exits `m2xz-p7ja`, bike counts |

## Caveats
- **Footprint heights come from a 2010 Pictometry/LiDAR model.** The tallest footprint in our bbox is 218.4 m, so towers finished after 2010 are missing or wrong. Salesforce Tower (2018) is about 326 m (unverified) and is not reflected. Override heights with OSM `height` or a manual list.
- Registered Businesses counts *registrations*, not storefronts. 18,609 active locations in our bbox include office suites, home offices and agents at shared addresses. Filter with NAICS 44-45/72 plus ground-floor checks. NAICS descriptions were deprecated on 2026-07-06 (Prop M change, per the dataset note).
- Land Use is a parcel snapshot. The 2023 release did not refresh commercial parcels (per the catalog.data.gov record https://catalog.data.gov/dataset/san-francisco-land-use-2023). Vacancy is not shown.
- The crash data covers injury crashes only (no property-damage-only crashes). The 2026 rows are year-to-date.
- The Transit Vehicle Location History has not updated since 2021. Use GTFS-RT instead (see `gtfs-511.md`).

## Key numbers for our bbox (37.7800–37.7975 N, −122.4095 to −122.3880 W)
All values computed by us with SoQL on 2026-10-24.

| Metric | Value | Query source |
|---|---|---|
| Building footprints intersecting bbox | 2,238 (median height 13.1 m, p90 39.6 m, max 218.4 m) | `ynuv-fyni` |
| Land-use parcels intersecting bbox | 2,207 | `c5ge-t6pj` |
| Office (MIPS) floor area | 88.0 M sq ft | `c5ge-t6pj` sum(`mips`) |
| Visitor/hotel floor area | 16.7 M sq ft | sum(`visitor`) |
| Retail/entertainment floor area | 11.4 M sq ft | sum(`retail`) |
| CIE / PDR / medical | 5.43 M / 3.40 M / 0.08 M sq ft | |
| Total commercial floor area | 125.1 M sq ft | sum(`total_comm`) |
| Residential units | 32,320 | sum(`resunits`) |
| Active registered business locations | 18,609 | `g8m3-pdis`, end dates null, `within_box(location, ...)` |
| Most common zoning polygons | C-3-O (67), C-3-O(SD) (46), P (36), C-3-R (29), CMUO (22) | `3i4a-hu95` |
| Injury crashes per year in bbox | 2019: 360 · 2020: 180 · 2021: 257 · 2022: 261 · 2023: 269 · 2024: 287 · 2025: 300 · 2026 YTD: 257 | `ubvf-ztfx` |
| Muni systemwide boardings, Aug 2026 | 14.84 M/month = **83.6%** of Aug 2019 (17.71 M) | SFMTA transtat CSV above |
| Travel Decision Survey 2019 sustainable mode share (all trips, SF) | 47% (down from 54% in 2017) | https://www.sfmta.com/blog/sfmta-travel-decision-survey-2019 |

Note: polygon `intersects` counts include parcels and footprints that only cross the bbox edge.
