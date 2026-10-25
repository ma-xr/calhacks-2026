# Research: The Human Project

This folder holds the evidence base behind the simulation of SF FiDi and upper SoMa: what every number in the model is and where it comes from.

- **Sourcing:** every figure carries an inline link to its source, preferring primary sources (agency reports, peer-reviewed papers, official data files). Anything we could not verify is marked **(unverified)**, and figures we calculated ourselves are marked **(derived)**.
- **One parameter table:** the engine loads [`parameters/parameters.json`](parameters/parameters.json) at startup, so the docs and the code use the same numbers.

| Folder | What it holds |
|---|---|
| [`parameters/`](parameters/README.md) | 74 model parameters with value, range, unit, status, source and notes (`parameters.json`, `.csv`, generator `make_params.py`) |
| [`case-studies/`](#case-studies) | 16 real interventions, with before/after numbers and "what our model should reproduce" |
| [`literature/`](#literature-syntheses) | 8 syntheses: the key findings, how the model uses them, and their limitations |
| [`data-sources/`](#data-sources) | 10 dataset cards: licence, fields, how we use them, caveats |
| `validation/` | Model vs. reality report, written by the backend (not by research) |

## How research feeds the model

```
 data-sources ──► POPULATION ──► SCHEDULE ──► MODE CHOICE ──► ASSIGNMENT ──► STREET LIFE ──► VALUATION
 (LODES, ACS,     home region,   departure/   logit: time,    BPR + settle   Huff retail,     $/yr City
  BART, OSM,      income tier,   arrival,     cost, parking,  days, lane     encounters →     Value
  DataSF, Kastle) occupancy      lunch/coffee fares, toll     capacity       ties, health
                                                                  │
 case-studies ─────────────────────────────────────────────► VALIDATION targets (Market St, JFK, Cairns…)
```

| Model component | Parameter keys | Main research inputs |
|---|---|---|
| **Population** | `home_region_share_downtown_workers`, `income_tier_share_downtown_workers`, `sf_office_occupancy_rate`, `office_sqft_per_job`, `retail_sqft_per_job`, `hotel_sqft_per_job`, `persons_per_household_downtown` | [census-lodes](data-sources/census-lodes.md), [acs](data-sources/acs.md), [kastle](data-sources/kastle-back-to-work.md), [datasf](data-sources/datasf.md), [zoning-density-and-travel](literature/zoning-density-and-travel.md) |
| **Schedule** | `arrival_time_distribution_sf_workplace`, `departure_time_distribution_sf`, `lunch_out_share_office_workers`, `coffee_trip_share` | [acs](data-sources/acs.md), [bart-ridership](data-sources/bart-ridership.md) (hourly exits), [retail-and-walkability](literature/retail-and-walkability.md) |
| **Mode choice** | `downtown_sf_worker_mode_share`, `car_availability_by_income`, `vot_personal_usd_per_hr`, `walk_wait_time_multiplier`, `daily_parking_cost_fidi_usd`, `bart_fare_usd`, `bridge_toll_usd`, `mtc_tm1_ivt_coef_work_per_min`, `sfcta_ivt_coef_work_per_min` | [mode-choice-and-elasticities](literature/mode-choice-and-elasticities.md), [sfcta-sf-champ](data-sources/sfcta-sf-champ.md), [gtfs-511](data-sources/gtfs-511.md) |
| **Assignment / congestion** | `bpr_alpha`, `bpr_beta`, `lane_capacity_vph`, `urban_free_flow_speed_kmh`, `car_trip_time_elasticity`, `traffic_evaporation_median` | [congestion-modeling](literature/congestion-modeling.md), [traffic-evaporation](literature/traffic-evaporation-and-induced-demand.md), [openstreetmap](data-sources/openstreetmap.md), [caltrans-pems](data-sources/caltrans-pems.md) |
| **Retail** | `avg_ticket_usd`, `walker_vs_driver_visit_ratio`, `ped_street_retail_uplift`, `retail_value_added_share` | [retail-and-walkability](literature/retail-and-walkability.md), [google-maps-apify](data-sources/google-maps-apify.md) (popular times), NYC/Oslo/Barcelona case studies |
| **Social** | `encounter_window_min`, `tie_formation_prob_per_repeat_encounter`, `appleyard_friends_by_traffic`, `value_of_weak_tie_usd_per_yr` | [social-interaction-in-public-space](literature/social-interaction-in-public-space.md), [london-LTN](case-studies/london-low-traffic-neighbourhoods.md) (residents "stop and talk" RR 1.29–1.48) |
| **Land use** | `fidi_office_vacancy_rate`, `soma_office_vacancy_rate`, `residential_sqft_per_unit_gross`, `rent_walkability_elasticity` | [office-to-residential-conversion](literature/office-to-residential-conversion.md), [embarcadero](case-studies/embarcadero-freeway-removal.md) and [octavia](case-studies/central-freeway-octavia-blvd.md) property effects |
| **Valuation** | `vsl_usd`, `heat_walk_*`, `us_crude_mortality_20_74`, `crash_cost_usd_per_vmt`, `co2_kg_per_vmt`, `scc_usd_per_tonne`, `vehicle_operating_cost_usd_per_mile`, tax rates | [health-valuation](literature/health-valuation.md) |
| **Validation** | `muni_speed_change_market_car_free`, `parallel_street_max_slowdown_market_car_free`, `cycling_change_market_car_free`, `ped_footfall_uplift`, `downtown_arterial_speed_mph_2025`, `bay_bridge_aadt` | [market-street-car-free-2020](case-studies/market-street-car-free-2020.md), [jfk-promenade](case-studies/jfk-promenade.md), [sf-slow-streets](case-studies/sf-slow-streets.md), [sfcta-sf-champ](data-sources/sfcta-sf-champ.md) |

## Headline validation targets

| Target | Value | Source |
|---|---|---|
| Car-free Market St (Jan 2020): Muni speed | **+6% average** (up to −12% travel time on the best line) | [SFMTA Board 2021](https://sfmta.com/media/25169/download), [SF Chronicle](https://www.sfchronicle.com/bayarea/article/Results-of-car-free-Market-Street-so-so-for-SF-15087210.php) |
| Car-free Market St: worst parallel-street slowdown | **−4%** (Mission SB, 8 AM). Adjacent streets averaged −1%; Howard/Folsom got faster | [INRIX 2020](https://inrix.com/blog/full-car-ban-on-market-street-little-impact-on-surrounding-roads/) |
| Car-free Market St: cycling | **+25%** (650 → 800+ bikes/h) | [SFMTA Board 2021](https://sfmta.com/media/25169/download) |
| Traffic evaporation after capacity removal | **−10.6% median** of the treated road's prior traffic (62 cases, 82% showing reductions) | [Cairns et al. 2002](https://nacto.org/wp-content/uploads/disappearing_traffic_cairns.pdf) |
| Footfall after car-free conversion | **+29%** walking (JFK); +11% (Times Sq), +14% (Oslo), +65% (SF Slow Streets) | [SFMTA](https://www.sfmta.com/project-updates/april-2022-update-new-hearing-date-and-new-robust-data), [NYC DOT](https://nacto.org/wp-content/uploads/greenlight_midtown_nycdot.pdf) |
| Retail after pedestrianization | 0 to +30%; **+14%** at NYC's FiDi Pearl St plaza | [NYC DOT 2012](https://nacto.org/wp-content/uploads/measuring_the_street_nyc_dot.pdf) |
| Baseline downtown congestion | Arterials **12.9 mph AM / 11.5 mph PM** (2025) | [SFCTA CMP 2025](https://www.sfcta.org/reports/congestion-management-program-2025) |
| Social ties vs. traffic | Light-traffic street residents have **~3×** the friends of heavy-traffic street residents (3.0 vs 0.9) | Appleyard 1981, see [social synthesis](literature/social-interaction-in-public-space.md) |

## Calibrated vs. assumed

Of the 74 parameters, **21 are data** (SF-measured), **37 literature** (published estimates) and **16 assumed**.

| | Keys |
|---|---|
| **Data (SF / study area)** | Workplace mode split (ACS 2024), SFCTA downtown trip shares, departure/arrival times, LODES home regions and earnings tiers, BART fares (GTFS × OD-weighted), Kastle occupancy 47.2%, FiDi/SoMa vacancy 29% / 33%, parking $22–40/day, household size, Market St outcomes (Muni, parallel streets, cycling), JFK footfall, Bay Bridge AADT, downtown arterial speeds, BART exits |
| **Literature** | USDOT VOT ($21.80/h), VSL ($14.2M), HEAT walking (RR 0.89 @ 168 min/wk, 30% cap), CO2, SCC, VOC, crash cost, BPR, TM1 capacities and speeds, Cairns evaporation, Goodwin elasticity, SF Planning sqft/job, retail tickets, walker-vs-driver visits, retail uplift, Pivo & Fisher walkability premium, Bay Bridge toll |
| **Assumed** (anchored, adjustable) | **FiDi worker mode share** (anchored to ACS county and SFCTA), car availability by income, coffee shares, `tie_formation_prob_per_repeat_encounter`, `encounter_window_min`, `value_of_weak_tie_usd_per_yr`, `value_per_encounter_usd`, `retail_net_new_share`, `assessed_value_usd_per_m2`, `sf_property_tax_rate` (unverified), `other_sqft_per_job`, bike speed, dwell share, repeat days, workdays |

**What was not found.**
- **FiDi work trips:** no FiDi-only work-trip mode split (the full SFCTA report could not be retrieved).
- **Social-tie rates:** no measured tie-formation probability exists in the literature.
- **Line-level Muni data:** SFMTA never published Muni travel-time changes by line for Market St 2020.
- **Market St parallel streets:** INRIX reported only Mission, Howard and Folsom.
- **Car access by income:** no ACS table gives car availability by earnings tier.
- **Missing primary pages:** primary pages for the Bay Bridge toll, SF property tax rate and Takapuna visit figures could not be reached.
- **Thin European case studies:** monitoring reports for Ghent, Madrid traffic and the Paris riverbank closures are thin (the shared web-search budget ran out).

## Case studies

**San Francisco (inside or next to our area):**
- [Car-free Market Street 2020](case-studies/market-street-car-free-2020.md): the primary calibration case.
- [JFK Promenade](case-studies/jfk-promenade.md)
- [Slow Streets, Valencia St, Shared Spaces](case-studies/sf-slow-streets.md)
- [Embarcadero Freeway removal](case-studies/embarcadero-freeway-removal.md)
- [Central Freeway / Octavia Blvd](case-studies/central-freeway-octavia-blvd.md)

**International:**
- [Times Square](case-studies/times-square-nyc.md)
- [Broadway / Herald Sq](case-studies/broadway-herald-square-nyc.md)
- [Strøget, Copenhagen](case-studies/stroget-copenhagen.md)
- [Barcelona superblocks](case-studies/barcelona-superblocks.md)
- [Pontevedra](case-studies/pontevedra.md)
- [Oslo car-free centre](case-studies/oslo-car-free-city-centre.md)
- [Paris Rue de Rivoli](case-studies/paris-rue-de-rivoli.md)
- [Ghent circulation plan](case-studies/ghent-circulation-plan.md)
- [Madrid Central](case-studies/madrid-central.md)
- [London LTNs](case-studies/london-low-traffic-neighbourhoods.md)
- [Seoul Cheonggyecheon](case-studies/seoul-cheonggyecheon.md)

## Literature syntheses

- [Traffic evaporation and induced demand](literature/traffic-evaporation-and-induced-demand.md): Cairns 2002, Duranton & Turner, Thomas & Aldred, Nello-Deakin.
- [Mode choice and elasticities](literature/mode-choice-and-elasticities.md): MTC TM1 and SFCTA ActivitySim coefficients read from the model files; VTPI elasticities; parking.
- [Congestion modeling](literature/congestion-modeling.md): BPR vs TM1 curves, HCM saturation flow, MATSim replanning, and why we use settle days.
- [Zoning, density and travel](literature/zoning-density-and-travel.md): Ewing & Cervero 2010 elasticities, SF floor area per job.
- [Retail and walkability](literature/retail-and-walkability.md): Pedestrian Pound, TfL, NYC DOT, Clifton, ticket sizes.
- [Social interaction in public space](literature/social-interaction-in-public-space.md): Appleyard, Gehl, Whyte, Jacobs, Hipp & Perrin, Copenhagen Networks Study, wellbeing valuation.
- [Office-to-residential conversion](literature/office-to-residential-conversion.md): vacancy, SF programs, SPUR/HR&A feasibility.
- [Health valuation](literature/health-valuation.md): WHO HEAT, VSL, crash costs, CO2/SCC, Barcelona HIA.

## Data sources

- [OpenStreetMap](data-sources/openstreetmap.md)
- [DataSF](data-sources/datasf.md)
- [Census LODES](data-sources/census-lodes.md)
- [ACS](data-sources/acs.md)
- [BART ridership](data-sources/bart-ridership.md)
- [511 GTFS](data-sources/gtfs-511.md)
- [Caltrans PeMS / AADT](data-sources/caltrans-pems.md)
- [Google Maps via Apify](data-sources/google-maps-apify.md): ToS caveats; demo use only.
- [Kastle Back to Work](data-sources/kastle-back-to-work.md)
- [SFCTA SF-CHAMP / Downtown Travel Study / CMP](data-sources/sfcta-sf-champ.md)
