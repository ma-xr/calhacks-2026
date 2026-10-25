# Model parameters

`parameters.json` is the single parameter table the backend engine loads at startup (`backend/hp/params.py`). It overrides the engine's built-in defaults key by key. `parameters.csv` mirrors it, and `make_params.py` regenerates both (edit the script, never the JSON by hand).

Each entry has this shape:

```json
{ "value": 21.8, "low": 19.4, "high": 28.2, "unit": "...", "status": "data|literature|assumed",
  "source": "<url>", "source_title": "...", "notes": "..." }
```

The `status` field has three levels:
- **data**: measured for SF or our study area (ACS, LODES, BART, Kastle, SFMTA, INRIX, Caltrans).
- **literature**: a published estimate, from elsewhere or national (USDOT, WHO HEAT, Cairns et al., MTC TM1).
- **assumed**: our judgment, anchored where possible. The notes say what it is anchored on, and the engine lists every assumed key under `assumptions` in each result.

**Counts (74 keys):** 21 data · 37 literature · 16 assumed.

## Conventions the engine depends on (read before editing)

- **Sign of effects.** `traffic_evaporation_median` and `car_trip_time_elasticity` are **negative**. Uplifts (`ped_*_uplift`, `cycling_change_*`, `muni_speed_change_*`) are positive fractions. `parallel_street_max_slowdown_*` is a positive fraction of speed lost.
- **Dict keys.** Dict values are merged into the engine defaults, so keep these exact sub-keys:
  - `lane_capacity_vph` uses OSM `highway` classes.
  - `bart_fare_usd` uses `east_bay / peninsula / sf / north_bay`.
  - `downtown_sf_worker_mode_share` uses `drive_alone / carpool / transit / walk / bike / other`. `wfh` is separate and ignored by the ASC calibration.
- **Evaporation denominator.** Cairns' −10.6% is a share of the *treated street's* prior traffic that does not reappear on the wider network. It is not a share of total area VMT. A model that reports area-VMT change should expect a much smaller percentage.
- **`rent_walkability_elasticity`.** The literature unit is "fractional value change per Walk Score point" (Pivo & Fisher: +1–9% per 10 points). The engine applies it per 10% change in nearby foot traffic or access. Mapping one point to a 10% change is an assumption.
- **Current dollars.** USDOT values are in 2024$ (VOT, VOC) and 2025$ (VSL). The social cost of carbon is in 2020$. We do not inflate them further.

## Biggest uncertainties (ranked by effect on City Value)

1. **`downtown_sf_worker_mode_share` (assumed).** No FiDi-only work-trip split could be retrieved.
   - The car-heavy bound is ACS 2024 workplace = SF County: 42% drive alone, 34% transit, excluding WFH.
   - The SFCTA Downtown Travel Study gives all-purpose downtown trips (2023): 37% auto, 21% transit, 40% walk/bike.
   - Our 26/6/45/12/4/3 (drive alone/carpool/transit/walk/bike/other) assumes FiDi is far more transit-oriented than the county.
2. **`value_of_weak_tie_usd_per_yr` (assumed, derived).** Wellbeing valuations span an order of magnitude. Keep it on a slider.
3. **`tie_formation_prob_per_repeat_encounter` (assumed).** There is no measurement. Calibrate it so light and heavy traffic streets reproduce Appleyard's ~2–3× friends gap.
4. **`ped_street_retail_uplift` (literature).** Effects range from 0 (Oslo) to +30% (TfL), with outliers up to +172% (Brooklyn Pearl St). Report a band, not a point.
5. **`scc_usd_per_tonne`.** Policy-contingent: federal use was withdrawn in 2025. It is a user slider.

## Not found or not verified this session

- **Bay Bridge toll** ($8.50, 2026): from a secondary source; the BATA page was unreachable.
- **SF sales tax total** (8.625%) and the **Bradley-Burns split**: CDTFA tables were not machine-readable.
- **SF property tax rate** for FY2025-26.
- **North Bay transit fare.**
- **Car availability by income tier**: no ACS table crosses vehicles by worker earnings. Anchored on B08014 76% overall.
- **`hotel_rooms_per_job`**: only `hotel_sqft_per_job` was found.
- **`vot_business_usd_per_hr`**: the matrix row is labelled "Truck/Business"; a per-person business value was not verified.
- **Mortality age weights**: `us_crude_mortality_20_74` is derived and should be replaced with a CDC WONDER query.

The web search budget for this session ran out before these could be checked. They are marked "(unverified)" in `notes`.

## How values were computed (reproducible)

- **`bart_fare_usd`**:
  - Fares come from BART GTFS v72 (`fare_rules.txt`, valid 2026-01-12 → 2026-08-30).
  - They are weighted by 2025 weekday trips entering 05:00–09:59 and exiting at EMBR or MONT (BART hourly OD, `data/cache/bart/date-hour-soo-dest-2025.csv.gz`).
  - Region rule: SF stations = EMBR, MONT, POWL, CIVC, 16TH, 24TH, GLEN, BALB; Peninsula = DALY, COLM, SSAN, SBRN, SFIA, MLBR; everything else = East Bay.
- **ACS keys** (`sf_county_worker_mode_share_acs2024`, `departure_time_distribution_sf`, `arrival_time_distribution_sf_workplace`, `sf_persons_per_household`, `car_availability_by_income` anchor): ACS 2024 1-year tables B08601, B08302, B08602, B25010, B08014 and B08519 for SF County. Pulled via `api.censusreporter.org/1.0/data/show/latest?table_ids=...&geo_ids=05000US06075`.
- **`home_region_share_downtown_workers`, `income_tier_share_downtown_workers`**: LODES8 2023, computed by the data pipeline (`data/backend/lodes.json`). Work blocks are those whose internal point lies in the sim bbox.
- **`lane_capacity_vph`, `urban_free_flow_speed_kmh`**: MTC TM1 `SpeedCapacity_1hour.block`, area type 0 (regional core). Capclass = area type × 10 + facility type.

## Valuation (City Value)

Feeds: valuation engine.

| Key | Value | Range | Unit | Status | Source |
|---|---|---|---|---|---|
| `vot_personal_usd_per_hr` | 21.8 | 19.4 to 28.2 | USD(2024)/person-hour | literature | [Caltrans, 2026 INFRA Cal-B/C vs Federal (USDOT BCA guidance)](https://dot.ca.gov/-/media/dot-media/programs/transportation-planning/documents/division-transportation-planning/transportation-economics/cal-bc-federal-comparison-of-value-matrix-2026-a11y.pdf) |
| `vot_business_usd_per_hr` | 37.2 | - | USD(2024)/vehicle-hour | literature | [Caltrans, 2026 INFRA Cal-B/C vs Federal (USDOT BCA guidance)](https://dot.ca.gov/-/media/dot-media/programs/transportation-planning/documents/division-transportation-planning/transportation-economics/cal-bc-federal-comparison-of-value-matrix-2026-a11y.pdf) |
| `walk_wait_time_multiplier` | 2.0 | 1.5 to 2.65 | x in-vehicle VOT | literature | [Caltrans, 2026 INFRA Cal-B/C vs Federal (USDOT BCA guidance)](https://dot.ca.gov/-/media/dot-media/programs/transportation-planning/documents/division-transportation-planning/transportation-economics/cal-bc-federal-comparison-of-value-matrix-2026-a11y.pdf) |
| `vsl_usd` | 14,200,000 | 13,200,000 to 14,200,000 | USD | literature | [USDOT, Departmental Guidance on Valuation of a Statistical L](https://www.transportation.gov/office-policy/transportation-policy/revised-departmental-guidance-on-valuation-of-a-statistical-life-in-economic-analysis) |
| `heat_walk_rr` | 0.89 | 0.83 to 0.96 | relative risk | literature | [Kahlmeier et al. (2017), WHO Europe, Health economic assessm](https://www.rsu.lv/sites/default/files/book_download/heat.pdf) |
| `heat_walk_ref_min_per_week` | 168 | - | min/week | literature | [Kahlmeier et al. (2017), WHO Europe, Health economic assessm](https://www.rsu.lv/sites/default/files/book_download/heat.pdf) |
| `heat_walk_rr_cap` | 0.3 | - | max fractional risk reduction | literature | [Kahlmeier et al. (2017), WHO Europe, Health economic assessm](https://www.rsu.lv/sites/default/files/book_download/heat.pdf) |
| `us_crude_mortality_20_74` | 0.0059 | 0.005 to 0.0065 | deaths/person-year | literature | [NCHS Data Brief 521, Mortality in the United States, 2023](https://www.cdc.gov/nchs/products/databriefs/db521.htm) |
| `crash_cost_usd_per_vmt` | 0.2 | 0.17 to 0.43 | USD/vehicle-mile | literature | [USDOT KABCO crash unit values (via NCDOT BCA technical memo)](https://connect.ncdot.gov/resources/LBIP2026-I95US301/Documents/BCA%20Technical%20Memorandum.pdf) |
| `co2_kg_per_vmt` | 0.4 | - | kg CO2/vehicle-mile | literature | [US EPA, Greenhouse Gas Emissions from a Typical Passenger Ve](https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle) |
| `scc_usd_per_tonne` | 190 | 120 to 340 | USD(2020)/tCO2 | literature | [EPA 2023 SC-GHG report (via RFF primer)](https://www.rff.org/publications/reports/adopting-the-social-cost-of-carbon-for-state-benefit-cost-analysis-a-primer-for-practitioners/) |
| `vehicle_operating_cost_usd_per_mile` | 0.58 | 0.41 to 0.8 | USD(2024)/mile | literature | [Caltrans, 2026 INFRA Cal-B/C vs Federal (USDOT BCA guidance)](https://dot.ca.gov/-/media/dot-media/programs/transportation-planning/documents/division-transportation-planning/transportation-economics/cal-bc-federal-comparison-of-value-matrix-2026-a11y.pdf) |
| `retail_value_added_share` | 0.55 | 0.25 to 0.63 | fraction of revenue | literature | [BEA GDP by industry: accommodation & food services value add](https://fred.stlouisfed.org/series/USFOODDPNGSP) |
| `retail_net_new_share` | 0.5 | 0.2 to 0.8 | fraction | assumed | - |
| `sf_sales_tax_rate` | 0.08625 | - | fraction | data | [CDTFA, California City & County Sales & Use Tax Rates](https://www.cdtfa.ca.gov/taxes-and-fees/sales-use-tax-rates.htm) |
| `city_share_of_sales_tax` | 0.01 | 0.0075 to 0.01 | fraction of taxable sales | literature | [Bradley-Burns Uniform Local Sales and Use Tax](https://www.cdtfa.ca.gov/taxes-and-fees/sales-use-tax-rates.htm) |
| `sf_property_tax_rate` | 0.0118 | 0.0116 to 0.0118 | fraction of assessed value | assumed | - |
| `assessed_value_usd_per_m2` | 5000 | 3000 to 9000 | USD/m2 | assumed | - |
| `value_of_weak_tie_usd_per_yr` | 1100 | 300 to 2500 | USD/tie-year | assumed | [HACT/Fujiwara UK Social Value Bank (via SFHA toolkit guidanc](https://www.housinglin.org.uk/_assets/Resources/Housing/OtherOrganisation/Report_SFHASocialValueToolkitGuidanceNotes.pdf) |
| `value_per_encounter_usd` | 0.05 | 0.0 to 0.25 | USD/encounter | assumed | - |
| `workdays_per_year` | 250 | 230 to 260 | days/yr | assumed | - |

## Congestion and assignment

Feeds: BPR assignment + settle days.

| Key | Value | Range | Unit | Status | Source |
|---|---|---|---|---|---|
| `bpr_alpha` | 0.15 | 0.15 to 1.12 | - | literature | [Bureau of Public Roads (1964) volume-delay function; FHWA HP](https://www.fhwa.dot.gov/ohim/hpmsmanl/appn5.cfm) |
| `bpr_beta` | 4.0 | 4.0 to 6.0 | - | literature | [BPR (1964); FHWA HPMS Appendix N](https://www.fhwa.dot.gov/ohim/hpmsmanl/appn5.cfm) |
| `lane_capacity_vph` | motorway 2050; motorway_link 1450; trunk 1450; primary 900; secondary 800; tertiary 650; residential 600; unclassified 600; living_street 300 | - | veh/hour/lane | literature | [MTC Travel Model One SpeedCapacity_1hour.block (area type 0 ](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/block/SpeedCapacity_1hour.block) |
| `urban_free_flow_speed_kmh` | motorway 88; motorway_link 48; trunk 64; primary 32; secondary 32; tertiary 28; residential 24; unclassified 24; living_street 10 | - | km/h | literature | [MTC Travel Model One SpeedCapacity_1hour.block free-flow spe](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/block/SpeedCapacity_1hour.block) |
| `traffic_evaporation_median` | -0.106 | -0.22 to -0.05 | fraction of treated road's prior traffic | literature | [Cairns, Atkins & Goodwin (2002), Disappearing traffic? The s](https://nacto.org/wp-content/uploads/disappearing_traffic_cairns.pdf) |
| `cairns_central_shopping_median` | -0.137 | - | fraction | literature | [Cairns et al. (2002)](https://nacto.org/wp-content/uploads/disappearing_traffic_cairns.pdf) |
| `car_trip_time_elasticity` | -0.5 | -1.0 to -0.22 | elasticity | literature | [Litman (VTPI), Transportation Elasticities; Goodwin (1996) E](https://www.vtpi.org/elasticities.pdf) |
| `bay_bridge_aadt` | 231000 | - | vehicles/day (two-way) | data | [Caltrans Traffic Census AADT (2024), SF-Oakland Bay Bridge t](https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/Traffic_AADT/MapServer/0) |
| `downtown_arterial_speed_mph_2025` | am 12.9; pm 11.5 | - | mph | data | [SFCTA Congestion Management Program 2025, Fig 4-3](https://www.sfcta.org/sites/default/files/2025-12/SFCTA_CMP2025_Fig4-3_CMP_Arterial_Average_Speeds_Citywide_and_in_the_Downtown_Core.csv) |

## Population and mode choice

Feeds: synthetic population + logit.

| Key | Value | Range | Unit | Status | Source |
|---|---|---|---|---|---|
| `downtown_sf_worker_mode_share` | drive_alone 0.26; carpool 0.06; transit 0.45; walk 0.12; bike 0.04; other 0.03; wfh 0.2 | - | share of commuters (wfh = share of workers) | assumed | [Anchors: ACS 2024 1-yr B08601 (workplace = SF County) and SF](https://censusreporter.org/tables/B08601/?primary_geo_id=05000US06075) |
| `sf_county_worker_mode_share_acs2024` | drive_alone 0.421; carpool 0.085; transit 0.342; walk 0.086; bike 0.033; other 0.034; wfh 0.159 | - | share of commuters excl. WFH (wfh = share of all workers) | data | [ACS 2024 1-year, Table B08601 Means of Transportation to Wor](https://censusreporter.org/tables/B08601/?primary_geo_id=05000US06075) |
| `downtown_trip_mode_share_sfcta` | y2019 auto 0.245; transit 0.279; walk_bike 0.434; tnc 0.042; y2023 auto 0.369; transit 0.209; walk_bike 0.397; tnc 0.025 | - | share of trips to/from/within Downtown | data | [SFCTA, Downtown Travel Study (May 2025), Executive Summary](https://www.sfcta.org/sites/default/files/2025-05/Downtown_Travel_Study_FINAL_Report_2025-05-22_Executive_Summary.pdf) |
| `home_region_share_downtown_workers` | east_bay 0.328; peninsula_south_bay 0.214; sf_west 0.11; sf_southeast_mission 0.142; sf_north 0.048; sf_in_area 0.028; north_bay 0.063; other 0.066 | - | share of jobs in sim bbox by home region | data | [Census LEHD LODES8 OD main JT00 2023 (CA), jobs in SF blocks](https://lehd.ces.census.gov/data/lodes/LODES8/ca/od/ca_od_main_JT00_2023.csv.gz) |
| `income_tier_share_downtown_workers` | low 0.067; mid 0.08; high 0.853 | - | share of jobs | data | [Census LODES8 WAC 2023 (CE01-CE03), SF blocks in sim bbox](https://lehd.ces.census.gov/data/lodes/LODES8/ca/wac/ca_wac_S000_JT00_2023.csv.gz) |
| `car_availability_by_income` | low 0.55; mid 0.72; high 0.8 | 0.5 to 0.9 | share of workers with a vehicle available | assumed | [ACS 2024 1-year B08014 (Vehicles available, SF resident work](https://censusreporter.org/tables/B08014/?primary_geo_id=05000US06075) |
| `departure_time_distribution_sf` | 00:00-04:59 0.0209; 05:00-05:29 0.0183; 05:30-05:59 0.0216; 06:00-06:29 0.05; 06:30-06:59 0.0566; 07:00-07:29 0.1325; 07:30-07:59 0.1172; 08:00-08:29 0.1843; 08:30-08:59 0.1096; 09:00-09:59 0.1417; 10:00-10:59 0.047; 11:00-11:59 0.014; 12:00-15:59 0.0515; 16:00-23:59 0.0347 | - | share of SF-resident commuters (excl. WFH) leaving home | data | [ACS 2024 1-year B08302 Time of Departure to Go to Work, San ](https://censusreporter.org/tables/B08302/?primary_geo_id=05000US06075) |
| `arrival_time_distribution_sf_workplace` | 00:00-04:59 0.0201; 05:00-05:29 0.0097; 05:30-05:59 0.0221; 06:00-06:29 0.0408; 06:30-06:59 0.0498; 07:00-07:29 0.0856; 07:30-07:59 0.1081; 08:00-08:29 0.1456; 08:30-08:59 0.1397; 09:00-09:59 0.1907; 10:00-10:59 0.0659; 11:00-11:59 0.0258; 12:00-15:59 0.0538; 16:00-23:59 0.0421 | - | share of people working in SF (excl. WFH) arriving at work | data | [ACS 2024 1-year B08602 Time Arriving at Work, Workplace Geog](https://censusreporter.org/tables/B08602/?primary_geo_id=05000US06075) |
| `daily_parking_cost_fidi_usd` | 22.0 | 22.0 to 40.0 | USD/day | data | [SFMTA Golden Gateway Garage (250 Clay St) rates](https://www.sfmta.com/index%2Ephp/garages-lots/golden-gateway-garage) |
| `parking_price_elasticity_vehicle_trips` | -0.3 | -0.54 to -0.1 | elasticity | literature | [Litman (VTPI), Transportation Elasticities](https://www.vtpi.org/elasticities.pdf) |
| `bart_fare_usd` | east_bay 6.33; peninsula 5.07; sf 2.85; sf_bart 2.55; north_bay 8.0 | - | USD one-way (Clipper) | data | [BART GTFS feed v72 (fare_rules/fare_attributes, valid 2026-0](https://www.bart.gov/dev/schedules/google_transit.zip) |
| `bridge_toll_usd` | 8.5 | 8.0 to 8.5 | USD | literature | [Bay Bridge toll schedule 2026 (Wikipedia infobox; primary BA](https://en.wikipedia.org/wiki/San_Francisco%E2%80%93Oakland_Bay_Bridge) |
| `walking_speed_m_s` | 1.34 | 1.07 to 1.4 | m/s | literature | [SFCTA ActivitySim constants (walk 3 mph)](https://github.com/sfcta/activitysim-sfcta/blob/main/configs/common/constants.yaml) |
| `walk_detour_factor` | 1.21 | 1.14 to 1.3 | network/crow-fly distance | literature | [Boeing (2019), Urban spatial order: street network orientati](https://arxiv.org/pdf/1708.00836) |
| `bike_speed_m_s` | 4.2 | 3.5 to 5.0 | m/s | assumed | - |
| `mtc_tm1_ivt_coef_work_per_min` | -0.0134 | - | utils/min | literature | [MTC Travel Model One, ModeChoice.xls (work tours)](https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/model/ModeChoice.xls) |
| `sfcta_ivt_coef_work_per_min` | -0.016 | - | utils/min | literature | [SFCTA ActivitySim tour mode choice coefficients (work)](https://github.com/sfcta/activitysim-sfcta/blob/main/configs/resident/tour_mode_choice_coefficients.csv) |
| `bart_weekday_exits_downtown_2026_09` | embarcadero 23619; montgomery 18908; powell 13573 | - | avg weekday | data | [BART Monthly Ridership Report, September 2026](https://www.bart.gov/sites/default/files/2026-10/Ridership_202609.xlsx) |

## Land use and density

Feeds: jobs/residents per block, conversion.

| Key | Value | Range | Unit | Status | Source |
|---|---|---|---|---|---|
| `sf_office_occupancy_rate` | 0.472 | 0.44 to 0.55 | fraction of pre-pandemic badge swipes | data | [Kastle Systems Back to Work Barometer, week incl. 13 Oct 202](https://www.kastle.com/safety-wellness/getting-america-back-to-work/) |
| `fidi_office_vacancy_rate` | 0.29 | 0.248 to 0.309 | fraction of inventory | data | [Kidder Mathews, San Francisco Office Market Report Q2 2026](https://kidder.com/wp-content/uploads/market_report/office-market-research-san-francisco-2026-2q.pdf) |
| `soma_office_vacancy_rate` | 0.332 | 0.332 to 0.354 | fraction of inventory | data | [Kidder Mathews Q2 2026 (CBRE Q1 2026 high)](https://kidder.com/wp-content/uploads/market_report/office-market-research-san-francisco-2026-2q.pdf) |
| `office_sqft_per_job` | 240 | 220 to 300 | gross sqft/job | literature | [SF Planning, Jobs-Housing Fit Report 2020](https://sfplanning.org/sites/default/files/resources/2021-11/Jobs-Housing_Fit_Report_2020.pdf) |
| `retail_sqft_per_job` | 350 | 300 to 500 | gross sqft/job | literature | [SF Planning, Jobs-Housing Fit Report 2020](https://sfplanning.org/sites/default/files/resources/2021-11/Jobs-Housing_Fit_Report_2020.pdf) |
| `hotel_sqft_per_job` | 440 | 400 to 900 | gross sqft/job | literature | [SF Planning, Jobs-Housing Fit Report 2020](https://sfplanning.org/sites/default/files/resources/2021-11/Jobs-Housing_Fit_Report_2020.pdf) |
| `other_sqft_per_job` | 600 | 400 to 900 | gross sqft/job | assumed | - |
| `residential_sqft_per_unit_gross` | 950 | 900 to 1000 | gross sqft/unit | literature | [SPUR / HR&A, SF Office-to-Residential Conversion Feasibility](https://www.spur.org/sites/default/files/2023-10/HR%26A_SF_Office_to_Residential_Conversion_Feasibility_Study_Sept_2023.pdf) |
| `sf_persons_per_household` | 2.14 | 1.8 to 2.24 | persons/household | data | [ACS 2024 1-year B25010, San Francisco County](https://censusreporter.org/tables/B25010/?primary_geo_id=05000US06075) |
| `persons_per_household_downtown` | 1.8 | 1.6 to 2.0 | persons/household | data | [ACS 2019-2023 5-year, B01003/B11001 for the 15 SF tracts ins](https://api.census.gov/data/2023/acs/acs5) |
| `rent_walkability_elasticity` | 0.005 | 0.001 to 0.009 | fractional rent change per Walk Score point (engine: per 10% foot-traffic change) | literature | [Pivo & Fisher (2011), The walkability premium in commercial ](https://experts.arizona.edu/en/publications/the-walkability-premium-in-commercial-real-estate-investments/) |

## Activities and retail

Feeds: schedules, Huff store choice, revenue.

| Key | Value | Range | Unit | Status | Source |
|---|---|---|---|---|---|
| `lunch_out_share_office_workers` | 0.52 | 0.4 to 0.6 | share of in-office days | literature | [ezCater 2025 office lunch survey (via press coverage)](https://www.aol.com/articles/week-worth-lunches-now-cost-130000134.html) |
| `coffee_trip_share` | 0.3 | 0.19 to 0.45 | share of in-office days | assumed | [National Coffee Association newsroom, National Coffee Data T](https://ncausa.org/Newsroom/Grounds-for-celebration-Americans-remain-committed-to-coffee) |
| `morning_coffee_share` | 0.25 | 0.15 to 0.35 | share of in-office days | assumed | - |
| `avg_ticket_usd` | cafe 7.0; restaurant 28.0; fast_food 13.0; bar 25.0; shop 45.0 | - | USD/visit | literature | [Toast restaurant check data (2023); ezCater; SF downtown sho](https://www.retailbrew.com/stories/2023/05/30/higher-average-lunchtime-checks-post-pandemic) |
| `walker_vs_driver_visit_ratio` | 2.0 | 1.1 to 3.2 | visits/month ratio | literature | [SF downtown shopper survey (via Streetsblog 2009); Takapuna/](https://sf.streetsblog.org/2009/05/27/only-17-percent-drive-to-downtown-sf-to-shop-study-finds) |
| `ped_street_retail_uplift` | 0.15 | 0.0 to 0.3 | fractional change in sales | literature | [NYC DOT Measuring the Street (2012); Volker & Handy (2021) r](https://nacto.org/wp-content/uploads/measuring_the_street_nyc_dot.pdf) |
| `ped_footfall_uplift` | 0.29 | 0.11 to 0.65 | fractional change in pedestrian volume | data | [SFMTA JFK Promenade data update (April 2022)](https://www.sfmta.com/project-updates/april-2022-update-new-hearing-date-and-new-robust-data) |

## Social

Feeds: encounters and ties.

| Key | Value | Range | Unit | Status | Source |
|---|---|---|---|---|---|
| `encounter_window_min` | 15 | 5 to 15 | minutes | assumed | [Sapiezynski et al. (2019), Interaction data from the Copenha](https://pmc.ncbi.nlm.nih.gov/articles/PMC6906316/) |
| `tie_formation_prob_per_repeat_encounter` | 0.02 | 0.01 to 0.1 | probability per repeated co-presence | assumed | [Calibration assumption bounded by Hipp & Perrin (2009) and H](https://escholarship.org/uc/item/4tp2801z) |
| `repeat_days_per_year` | 60 | 30 to 120 | days/yr | assumed | - |
| `street_dwell_share_car_free` | 0.08 | 0.03 to 0.15 | share of passers-by | assumed | [Anchor: NYC DOT Green Light for Midtown (2010)](https://nacto.org/wp-content/uploads/greenlight_midtown_nycdot.pdf) |
| `appleyard_friends_by_traffic` | light 3.0; moderate 1.3; heavy 0.9 | - | friends per resident on the street | literature | [Appleyard (1981) Livable Streets, via Streetfilms video tran](https://amara.org/videos/WrBmfcwZMu7b/en/103981) |

## Validation targets (Market St 2020)

Feeds: validation.

| Key | Value | Range | Unit | Status | Source |
|---|---|---|---|---|---|
| `muni_speed_change_market_car_free` | 0.06 | 0.04 to 0.136 | fractional Muni speed change | data | [SFMTA Board, Better Market Street update (19 Jan 2021); SF C](https://sfmta.com/media/25169/download) |
| `parallel_street_max_slowdown_market_car_free` | 0.04 | 0.0 to 0.06 | fractional travel-speed reduction | data | [INRIX (2020), Full car ban on Market Street: little impact o](https://inrix.com/blog/full-car-ban-on-market-street-little-impact-on-surrounding-roads/) |
| `cycling_change_market_car_free` | 0.25 | 0.2 to 0.3 | fractional change in bike volume | data | [SFMTA Board Better Market Street update (Jan 2021); SFMTA bl](https://sfmta.com/media/25169/download) |
