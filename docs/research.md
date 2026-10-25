# Research reference

Collected 2026-10-24 during planning. Figures marked *(verify)* were not checked against a primary source.

## 1. Prior art

| Tool | What it models | What we borrow |
|---|---|---|
| MATSim (matsim.org) | Agents with daily plans. They simulate, score and replan until equilibrium | **Settle loop**: run 5–10 fast replanning "days" after each edit, so traffic evaporation emerges |
| SUMO (eclipse.dev/sumo) | Microscopic car-following on OSM networks | Too detailed; OSM import pipeline is a reference |
| MIT CityScope ([Volpe](https://www.media.mit.edu/projects/cityscope-volpe/overview/), [Kendall ABM](https://arxiv.org/pdf/2106.14572)) | Tangible blocks; agents choose housing and mode | **Live radar chart** that updates as blocks change |
| A/B Street ([UW](https://urban.uw.edu/news/a-b-streets-game-lets-you-create-the-seattle-street-grid-of-your-dreams), [GitHub](https://github.com/a-b-street/abstreet)) | Seattle OSM network, regional demand model, lane edits | **Side-by-side A/B** with per-trip time deltas |
| UrbanSim (urbansim.com) | Household/firm location + developer model | Zoning → density → land value |
| ActivitySim / POLARIS | Activity-based demand (pattern → tours → destination → mode) | Schedule template |
| Replica (replicahq.com) | Calibrated synthetic population, consumer spend | Revenue-by-block is a credible product category; [road closure scenarios](https://learn.replicahq.com/road-closure-scenario) |
| CityFlow | Fast RL traffic sim | Thousands of agents is feasible with simple rules |
| Cities: Skylines I/II | Game agents, info-view overlays, traffic routes tool | UX bar: overlays, route tool, Chirper |
| Smallville ([arXiv 2304.03442](https://arxiv.org/abs/2304.03442)) | LLM agents with memory | "Click a sim, read their day" |
| AgentSociety ([arXiv 2502.08691](https://arxiv.org/abs/2502.08691v1)) | 10k+ LLM agents in a city | **Hybrid**: rules for the crowd, LLM for narration |

## 2. Modeling techniques (hackathon-sized, credible)

- **Activity schedule**: home/work/departure sampled; P(extra stop) falls as commute time rises.
- **Huff store choice**: `P(j) = A_j^α · d_ij^-β / Σ_k A_k^α · d_ik^-β`. A pedestrianized street adds a pleasantness bonus to A.
- **Logit mode choice**: `U_m = ASC_m − b_t·time − b_c·cost + comfort`, `P = e^U / Σ e^U`.
- **BPR congestion**: `t = t0 · (1 + 0.15 · (V/C)^4)`. Pedestrianized road: C = 0.
- **Encounters**: pairs on the same segment/place in the same time bin, weighted by dwell; cars count 0.
- **Experienced income mixing**: [Atlas of Inequality](https://inequality.media.mit.edu), [paper](https://dspace.mit.edu/handle/1721.1/131211).
- **15-minute accessibility**: amenity types reachable within a 15-minute walk.
- **Space Syntax** ([Hillier](https://discovery.ucl.ac.uk/id/eprint/1398/)): network integration and choice predict foot traffic, and retail follows.
- **Jacobs vitality**: foot traffic across the day × land-use mix entropy × density × active frontage.

## 3. Empirical evidence (sets the direction of effects)

- **Traffic evaporation**: 51 of 63 capacity-reduction cases showed less total traffic; median −11% ([travelwest](https://travelwest.info/essential-evidence/no-5-impact-of-highway-traffic-capacity-reductions/)).
- **Car-free Market St (2020)**: Muni about 6% faster (up to 12% on some lines), worst parallel slowdown about 4% on Mission, cycling +25% ([CBS/INRIX](https://cbsnews.com/amp/sanfrancisco/news/car-free-market-street-faster-muni-traffic-impact-inrix-study)).
- **JFK Promenade**: walking +29%, biking +76% ([SFMTA](https://www.sfmta.com/project-updates/april-2022-update-new-hearing-date-and-new-robust-data)).
- **Retail**: walking and public-realm upgrades raised sales by up to 30% (TfL/UCL). Walkers make more visits, about 12/month vs. 6/month for drivers, rather than spending more per visit ([Takapuna](https://openrepository.aut.ac.nz/handle/10292/999)).
- **Barcelona Sant Antoni superblock**: card spending 16.4% above the city average ([Ajuntament](https://ajuntament.barcelona.cat/superilles/en/noticia/1100503)), but one study found square visits −17.6% after a year ([PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9793503/)), and gentrification pressure is documented.

## 4. Valuation factors (for City Value)

| Factor | Value | Source |
|---|---|---|
| Value of travel time, personal | about $19–20/hr (2023$) *(verify)*; walk/wait ×2 | [USDOT VTTS](https://www.transportation.gov/office-policy/transportation-policy/revised-departmental-guidance-valuation-travel-time-economic) |
| Value of statistical life | $13.7M (2024 base) / $14.2M (2025) | [USDOT VSL](https://www.transportation.gov/office-policy/transportation-policy/revised-departmental-guidance-on-valuation-of-a-statistical-life-in-economic-analysis) |
| Walking health benefit | RR 0.89 at 11.25 MET-h/week, linear, capped | [WHO HEAT](https://who-sandbox.squiz.cloud/__data/assets/pdf_file/0005/248900/Development-of-the-health-economic-assessment-tools-HEAT-for-walking-and-cycling.pdf) |
| Vehicle operating cost | about $0.50–0.70/mi *(verify)* | [USDOT BCA 2025](https://www.transportation.gov/sites/dot.gov/files/2024-11/Benefit%20Cost%20Analysis%20Guidance%202025%20Update%20%28Final%29.pdf) |
| Loneliness wellbeing cost | about £9,500/person/yr | [UK monetisation report](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/963077/Loneliness_monetisation_report_V2.pdf) |
| Neighbour contact (upper bound) | about £37k/yr | [Powdthavee](https://warwick.ac.uk/fac/soc/economics/staff/ajoswald/download/valuing_relationships.pdf) |
| SF sales tax | 8.625%; city share about 1% *(verify)* | CDTFA |
| Walkability → property value | about +1–2% per 10 Walk Score points *(verify)* | hedonic literature |

## 5. Data sources

| Data | Source | Notes |
|---|---|---|
| Roads, buildings (prototype) | OpenStreetMap via Overpass. Snapshot in `data/raw/` | ODbL: credit "© OpenStreetMap contributors" |
| Building footprints/heights | DataSF Building Footprints | Free |
| Zoning | DataSF zoning districts (3i4a-hu95) | Free, Socrata API |
| Businesses | Google Maps via **Apify** (ratings, price, categories, popular times) + DataSF Registered Businesses | |
| Commute flows | [Census LODES](https://lehd.ces.census.gov/data/) | Seed home→work pairs |
| Income | ACS via api.census.gov | Equity breakdown |
| Transit stations | BART/Muni GTFS via [511.org](https://511.org/open-data) | Spawn points only |
| Calibration | SFCTA SF-CHAMP, SFMTA counts, Caltrans PeMS | |

## 6. UX references

- **Overlays**: Cities: Skylines II info views, SimCity 2013 data layers.
- **Follow an agent / inspector**: SimCity 2013 GlassBox.
- **Origin–destination arcs**: Cities: Skylines II traffic routes tool.
- **A/B side by side**: A/B Street; Esri GeoPlanner [side-by-side](https://enterprise.arcgis.com/en/geoplanner/11.0/documentation/side-by-side-comparison-of-scenarios.htm).
- **Live radar feedback**: MIT CityScope.
- **Tactile editing and audio**: Townscaper, Mini Motorways.
- **Trade-off levers**: Frostpunk Book of Laws (Policy Book).
- **Trip trails + time scrubber**: [deck.gl TripsLayer](https://deck.gl/docs/api-reference/geo-layers/trips-layer).
- **Diversion view**: Replica road closures.
- **Citizen feed**: Cities: Skylines Chirper.
