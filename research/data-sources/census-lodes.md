# Census LEHD LODES (LODES8) and OnTheMap

## What it is
LEHD Origin-Destination Employment Statistics: job counts by census block. Built from state UI wage records, QCEW and federal employment records. There are three file types:
- **OD**: job flows from home block to work block.
- **RAC**: jobs by where workers live (residence block).
- **WAC**: jobs by where they work (workplace block).

## Publisher & URL
| Item | Value |
|---|---|
| Publisher | U.S. Census Bureau, Center for Economic Studies, LEHD program |
| Data root | https://lehd.ces.census.gov/data/lodes/LODES8/ |
| California | https://lehd.ces.census.gov/data/lodes/LODES8/ca/{od,rac,wac}/ and `ca_xwalk.csv.gz` |
| Tech doc (v8.4, rev. 2025-12-03) | https://lehd.ces.census.gov/data/lodes/LODES8/LODESTechDoc8.4.pdf |
| Release note (2023 data, v8.4) | https://www.census.gov/programs-surveys/ces/news-and-updates/updates/12182025.html |
| OnTheMap (web UI) | https://onthemap.ces.census.gov |

## Version and years
| Item | Value | Source |
|---|---|---|
| Current version | **LODES 8.4** (2020 census blocks, 2024 TIGER/Line) | Tech doc 8.4 |
| Latest year | **2023**. Released 2025-12-18. As of 2026-10-24 the `ca/wac` and `ca/od` folders end at `*_2023.csv.gz` (checked) | release note; directory listing |
| Year range | 2002–2023 for most states | Tech doc 8.4 |
| Missing states | 2022–2023: Alaska and Michigan. California is complete. | Tech doc 8.4 table |
| Next release | "LODES 2024 coming in early Fall 2026" (a plan, not out yet as of 2026-10-24) | https://lehd.ces.census.gov/doc/workshop/2026/WhatsNewLEHD.pdf |

## License / terms
U.S. federal government work, public domain. Census asks for source attribution (e.g. "U.S. Census Bureau, LEHD Origin-Destination Employment Statistics (2002-2023), LODES 8.4"). The disclosure review number in the tech doc is CBDRB-FY21-249.

## File naming and segments (Tech doc 8.4)
- OD: `ca_od_[main|aux]_JT0x_YYYY.csv.gz`.
  - **main** = home and work both in CA.
  - **aux** = work in CA, home out of state.
- RAC/WAC: `ca_[rac|wac]_[SEG]_JT0x_YYYY.csv.gz`.
- Job types:
  - JT00 = All Jobs
  - JT01 = Primary Jobs
  - JT02 = All Private
  - JT03 = Private Primary
  - JT04 = All Federal
  - JT05 = Federal Primary

| Segment | Definition (verbatim from tech doc) |
|---|---|
| S000 | Total number of jobs |
| SA01 / SA02 / SA03 | Workers age 29 or younger / 30 to 54 / 55 or older |
| **SE01** | Jobs with earnings **$1250/month or less** |
| **SE02** | Jobs with earnings **$1251/month to $3333/month** |
| **SE03** | Jobs with earnings **greater than $3333/month** |
| SI01 / SI02 / SI03 | Goods Producing / Trade, Transportation & Utilities / All Other Services |
| WAC/RAC CNS01–CNS20 | Jobs by 2-digit NAICS sector |
| CR*, CT*, CD*, CS* | Race, ethnicity, education, sex |
| CFA*/CFS* (WAC) | Firm age and size. Only for JT02, years 2011–2023 |

Earnings thresholds are nominal and **not indexed to inflation**. SE03 (>$3,333/mo, about $40k/yr) covers most FiDi office workers, so it says little about income within that group.

## Fields we use
| File | Fields | Use |
|---|---|---|
| OD main+aux JT01 (primary jobs, so we don't double-count multiple jobholders) | `w_geocode`, `h_geocode`, `S000`, `SE01–03` | Home locations of agents working in bbox blocks |
| WAC S000 JT00 | `w_geocode`, `C000`, `CE01–03`, `CNS01–20` | Jobs per block, sector mix (office vs retail/food) |
| RAC S000 JT00 | `h_geocode`, `C000`, `CE01–03` | Resident workers in bbox |
| `ca_xwalk.csv.gz` | `tabblk2020`, `trct`, `cty`, `blklatdd`, `blklondd` | Block to tract/county lookup and block centroids |

## How the model uses it
| Module | Use |
|---|---|
| Population synthesis | Draw each worker agent's home block from OD flows into bbox work blocks. Use the SE tier to set an income band. |
| Mode choice | Home county/tract sets which modes are available: BART corridor, Caltrain, ferry, or drive-only. |
| Land use | WAC CNS sectors, cross-checked against DataSF Land Use office sq ft (`mips`). |
| Validation | Total jobs in bbox vs CoStar/Land Use sq ft × employment density. |

## Caveats
- **Privacy noise.** Workplace counts carry noise infusion, and residence-side data (RAC/OD home) is synthetic (OnTheMap Data Overview, https://lehd.ces.census.gov/doc/help/onthemap/OnTheMapDataOverview.pdf). The method was not checked in the tech doc text itself, so treat it as unverified. Block-level cells are unreliable, so aggregate to tract or bbox.
- **Jobs, not commuters.** LODES counts jobs located at a worksite. It does not count daily attendance. With hybrid work, Kastle occupancy is much lower than LODES jobs (see `kastle-back-to-work.md`).
- **HQ attribution.** Multi-site employers can be assigned to one establishment location, which inflates FiDi HQ blocks (unverified magnitude).
- **Coverage.** UI-covered and federal jobs only. Self-employed and gig workers are excluded.
- **Lag.** The latest data is 2023 (about 2–3 years old).

## Key numbers for our area
- Not computed yet. The local cache only has a partial `data/cache/lodes/ca_xwalk.csv.gz.part`. To compute: filter `ca_wac_S000_JT00_2023` to the bbox blocks (xwalk `blklatdd`/`blklondd`) and sum `C000`.
