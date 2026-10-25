# Caltrans PeMS and Caltrans Traffic Census (AADT)

## What it is
- **PeMS** (Performance Measurement System) archives 30-second loop-detector data, rolled up to 5-minute, hourly and daily flow, occupancy and speed for California freeways. The site says it covers "over 39,000 individual detectors".
- **Traffic Census** is Caltrans' annual AADT for the State Highway System, with back and ahead legs at each count location.

## Publisher & URL
| Product | URL |
|---|---|
| PeMS | https://pems.dot.ca.gov/ (free account. Caltrans says approval "typically" takes 1–2 business days) |
| PeMS Data Clearinghouse (bulk station_5min, station_hour, metadata) | Inside PeMS after login (Tools → Data Clearinghouse). Not checked without an account. |
| Traffic Census Program | https://dot.ca.gov/programs/traffic-operations/census |
| 2024 AADT XLSX | https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/documents/census/2024/2024-traffic-volumes-ca-a11y.xlsx |
| 2024 Peak Hour XLSX | https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/documents/census/2024/2024-ca-peak-hours-a11y.xlsx |
| AADT GIS service (2024) | https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/Traffic_AADT/MapServer/0 |
| Back/Ahead leg explanation | https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/documents/back-and-ahead-leg-traffic-count-diagram-a11y.pdf |

## License / terms
- PeMS has a "Conditions of Use" page behind the site link. Exact redistribution terms were not checked (unverified).
- Caltrans census data is public state data (CA Open Data). No explicit license was found on the census page (unverified).

## Fields we use
| Product | Fields |
|---|---|
| PeMS station_5min | `timestamp`, `station`, `district` (4), `freeway` (80), `direction`, `lane_type` (ML/OR/FR/HV), `samples`, `pct_observed`, `total_flow`, `avg_occupancy`, `avg_speed` |
| PeMS station metadata | `ID`, `Fwy`, `Dir`, `Abs_PM`, `Latitude`, `Longitude`, `Type` |
| AADT | `RTE`, `CNTY`, `PM`, `DESCRIPTION`, `BACK_AADT`, `AHEAD_AADT`, `BACK_PEAK_HOUR`, `AHEAD_PEAK_HOUR`, `*_PEAK_MADT` |

## How the model uses it
| Module | Use |
|---|---|
| Assignment (boundary conditions) | Hourly vehicle inflow at bbox gateways: Bay Bridge ramps at Fremont, Harrison, Main/Beale, and 1st/Essex; I-80 at 4th/5th |
| Validation | Simulated ramp volumes vs PeMS on-ramp/off-ramp detectors and Caltrans ramp volumes (District 4 XLSX) |
| Congestion | PeMS speeds on the I-80 approach show queue spillback onto SoMa streets |

## Caveats
- Detector health varies. Filter on `pct_observed` (for example ≥ 70%). Imputed values are flagged.
- The Bay Bridge westbound toll plaza is metered. Mainline counts measure metered throughput, not demand.
- AADT is a two-way annual average over a fiscal count year (Oct 1–Sep 30). Most sites are not counted continuously, so values are adjusted estimates (from the GIS service description).
- **Specific PeMS station IDs on the Bay Bridge were not checked** because we have no account (unverified). Look them up with PeMS station search: District 4, I-80, around Abs PM 4–9 in SF.
- The often-quoted "~260,000 vehicles/day" Bay Bridge figure is old. NPR used it in 2009 (https://www.npr.org/2009/09/07/112627591/bay-bridge-closure-threatens-nightmare-commute) and Wikipedia's infobox repeats it. **Caltrans 2024 AADT is 231,000** (below).

## Key numbers: Caltrans 2024 AADT (two-way), I-80 / US-101 / I-280 near the bbox
Queried from the Caltrans AADT GIS service on 2026-10-24.

| Location | Postmile | Back AADT | Ahead AADT | Peak hour |
|---|---|---|---|---|
| **SF–Oakland Bay Bridge Toll Plaza** (ALA 80) | 1.989 | **231,000** | 231,000 | 15,400 |
| SF/Alameda county line (on the bridge) | SF R8.866 | 231,000 | — | 15,400 |
| Treasure Island / Yerba Buena Island (each deck shown separately) | SF 7.719 | 118,000 / 115,000 | 117,000 / 114,000 | 7,900 / 7,700 |
| First/Harrison, Bay Bridge connections | SF 5.588 | 92,000 / 104,000 | 118,000 / 115,000 | 6,100–7,900 |
| Fourth/Fifth Streets, Bay Bridge connections | SF 5.454 | 93,000 | 113,000 | 6,200 / 7,500 |
| 7th/8th Streets | SF 4.4 | 178,000 | 200,000 | 11,900 / 13,300 |
| I-80 / US-101 junction | SF 3.951 | 141,000 | 178,000 | 12,200 / 11,900 |
| US-101 at Market St (Central Fwy) | SF 101 PM 4.86 | 43,500 | 41,000 | — |
| I-280 at Brannan St (King St terminus) | SF 280 PM 7.543 | 49,500 | — | — |

Notes:
- The two-deck rows at SF 7.719 add up to about 231–235k, which matches the toll plaza figure.
- Peak hour / AADT ≈ 6.7% at the bridge.
- SFCTA's Downtown Travel Study (2025) reports Bay Bridge volumes **9% below pre-pandemic** (https://www.sfcta.org/sites/default/files/2025-05/Downtown_Travel_Study_FINAL_Report_2025-05-22_Executive_Summary.pdf).
- The same study gives Downtown I-80 car trips by origin and destination. Pass-through trips (not starting or ending in SF) rose from 7% to 15% between 2019 and 2023. To/from-SF trips fell from 82% to 72%, and intra-SF trips went from 11% to 13%.
