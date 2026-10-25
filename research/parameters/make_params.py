"""Generate research/parameters/parameters.json and parameters.csv (source of truth = this list)."""
import csv, json, sys
from collections import OrderedDict

OUT = sys.argv[1]

CALBC = "https://dot.ca.gov/-/media/dot-media/programs/transportation-planning/documents/division-transportation-planning/transportation-economics/cal-bc-federal-comparison-of-value-matrix-2026-a11y.pdf"
CALBC_T = "Caltrans, 2026 INFRA Cal-B/C vs Federal (USDOT BCA guidance) comparison of values matrix (2024$)"
VSL = "https://www.transportation.gov/office-policy/transportation-policy/revised-departmental-guidance-on-valuation-of-a-statistical-life-in-economic-analysis"
HEAT = "https://www.rsu.lv/sites/default/files/book_download/heat.pdf"
HEAT_T = "Kahlmeier et al. (2017), WHO Europe, Health economic assessment tool (HEAT) for walking and cycling: methods and user guide, 2017 update"
CAIRNS = "https://nacto.org/wp-content/uploads/disappearing_traffic_cairns.pdf"
TM1_CAP = "https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/block/SpeedCapacity_1hour.block"
TM1_VDF = "https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/scripts/block/SpeedFlowCurve.block"
CR = "https://censusreporter.org/profiles/05000US06075-san-francisco-county-ca/"
CR_T = "U.S. Census Bureau ACS 2024 1-year, San Francisco County (via Census Reporter API)"
ACS5 = "https://api.census.gov/data/2023/acs/acs5"
LODES = "https://lehd.ces.census.gov/data/lodes/LODES8/ca/od/ca_od_main_JT00_2023.csv.gz"
LODES_WAC = "https://lehd.ces.census.gov/data/lodes/LODES8/ca/wac/ca_wac_S000_JT00_2023.csv.gz"
SFP_JH = "https://sfplanning.org/sites/default/files/resources/2021-11/Jobs-Housing_Fit_Report_2020.pdf"
INRIX = "https://inrix.com/blog/full-car-ban-on-market-street-little-impact-on-surrounding-roads/"
SFMTA_BMS = "https://sfmta.com/media/25169/download"
BART_GTFS = "https://www.bart.gov/dev/schedules/google_transit.zip"
DTS = "https://www.sfcta.org/sites/default/files/2025-05/Downtown_Travel_Study_FINAL_Report_2025-05-22_Executive_Summary.pdf"

P = OrderedDict()


def add(key, value, low, high, unit, status, source, source_title, notes):
    P[key] = OrderedDict(value=value, low=low, high=high, unit=unit, status=status,
                         source=source, source_title=source_title, notes=notes)


# ---------------------------------------------------------------- valuation
add("vot_personal_usd_per_hr", 21.80, 19.40, 28.20, "USD(2024)/person-hour", "literature", CALBC, CALBC_T,
    "USDOT BCA guidance value for local personal travel, escalated to 2024$ (Fed. column of the Caltrans matrix). Intercity personal = $28.20 (used as high). Low = previous default (unverified older guidance year). See literature/health-valuation.md and mode-choice-and-elasticities.md.")
add("vot_business_usd_per_hr", 37.20, None, None, "USD(2024)/vehicle-hour", "literature", CALBC, CALBC_T,
    "Matrix row 'Truck/Business ($/hr./veh.)', USDOT value. Row label mixes truck and business travel; a pure business-traveler-per-person value was not separately verified.")
add("walk_wait_time_multiplier", 2.0, 1.5, 2.65, "x in-vehicle VOT", "literature", CALBC, CALBC_T,
    "USDOT: walk/wait time valued at 2x (matrix: 'for wait times, the value should be doubled'). MTC TM1 uses 2x walk (<1.5 mi) and 2x initial wait (https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/model/ModeChoice.xls); SFCTA ActivitySim work-tour walk coefficient is 2.65x IVT (https://github.com/sfcta/activitysim-sfcta/blob/main/configs/resident/tour_mode_choice_coefficients.csv).")
add("vsl_usd", 14.2e6, 13.2e6, 14.2e6, "USD", "literature", VSL, "USDOT, Departmental Guidance on Valuation of a Statistical Life (2025 update)",
    "$14.2M for a 2025 base year; $13.7M (2024), $13.2M (2023). USDOT sensitivity range is wider (unverified for 2025).")
add("heat_walk_rr", 0.89, 0.83, 0.96, "relative risk", "literature", HEAT, HEAT_T,
    "All-cause mortality RR for regular walking at the reference volume (95% CI 0.83-0.96). Linear dose-response from 1.0 at 0 min.")
add("heat_walk_ref_min_per_week", 168, None, None, "min/week", "literature", HEAT, HEAT_T,
    "Reference walking volume for RR 0.89 (= 11.25 MET-h/week). Applies to ages 20-74.")
add("heat_walk_rr_cap", 0.30, None, None, "max fractional risk reduction", "literature", HEAT, HEAT_T,
    "Benefit capped at 30% risk reduction (reached at ~460 min/week). HEAT also phases benefits in over 5 years (20%/yr); we report steady state.")
add("us_crude_mortality_20_74", 0.0059, 0.0050, 0.0065, "deaths/person-year", "literature", "https://www.cdc.gov/nchs/products/databriefs/db521.htm",
    "NCHS Data Brief 521, Mortality in the United States, 2023",
    "Derived from NCHS 2023 age-specific death rates weighted by population age 20-74; population weights not verified against CDC WONDER (replace with a WONDER query). California is lower than the US average.")
add("crash_cost_usd_per_vmt", 0.20, 0.17, 0.43, "USD/vehicle-mile", "literature", "https://connect.ncdot.gov/resources/LBIP2026-I95US301/Documents/BCA%20Technical%20Memorandum.pdf",
    "USDOT KABCO crash unit values (via NCDOT BCA technical memo); NHTSA fatality rate",
    "Derived. Low = fatalities only (1.26 deaths/100M VMT x $13.2M). High = NHTSA ~$1.4T total societal crash cost / US VMT (unverified). Not all of this is external to the driver. See literature/health-valuation.md.")
add("co2_kg_per_vmt", 0.400, None, None, "kg CO2/vehicle-mile", "literature", "https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle",
    "US EPA, Greenhouse Gas Emissions from a Typical Passenger Vehicle", "Typical passenger vehicle ~400 g CO2/mile. Congested low-speed SF driving emits more per mile (not modeled).")
add("scc_usd_per_tonne", 190, 120, 340, "USD(2020)/tCO2", "literature", "https://www.rff.org/publications/reports/adopting-the-social-cost-of-carbon-for-state-benefit-cost-analysis-a-primer-for-practitioners/",
    "EPA 2023 SC-GHG report (via RFF primer)", "Central 2% discount, 2020 emissions year; range 2.5%-1.5% discount. Federal use withdrawn by Executive Order 14154 (Jan 2025); USDOT matrix shows CO2 $0 federally. Keep as a user slider.")
add("vehicle_operating_cost_usd_per_mile", 0.58, 0.41, 0.80, "USD(2024)/mile", "literature", CALBC, CALBC_T,
    "Derived: non-fuel auto cost $0.408/mi (matrix) + fuel at $4.37/gal (matrix, CA 2024$) / ~25 mpg (assumed) = ~$0.175/mi. Low = non-fuel only. High ~ AAA full ownership cost per mile (unverified). Marginal cost of a trip is closer to the low end.")
add("retail_value_added_share", 0.55, 0.25, 0.63, "fraction of revenue", "literature", "https://fred.stlouisfed.org/series/USFOODDPNGSP",
    "BEA GDP by industry: accommodation & food services value added (FRED) vs Census food-service sales",
    "Food service VA/sales ~0.63 (derived: $703B / $1.12T). General retail is much lower (~0.25, unverified) because sales include goods cost. 0.55 is our blend for a cafe/restaurant-heavy FiDi mix (assumed weights).")
add("retail_net_new_share", 0.5, 0.2, 0.8, "fraction", "assumed", None, None,
    "Share of a business's revenue gain that is new to the city rather than shifted from elsewhere. Literature (Volker & Handy 2021) notes most local gains are partly redistribution; no measured value.")
add("sf_sales_tax_rate", 0.08625, None, None, "fraction", "data", "https://www.cdtfa.ca.gov/taxes-and-fees/sales-use-tax-rates.htm",
    "CDTFA, California City & County Sales & Use Tax Rates", "Statewide base 7.25% (verified on CDTFA page) + SF district taxes; the 8.625% SF total is from CDTFA rate tables (unverified this session; page tables not machine-readable).")
add("city_share_of_sales_tax", 0.01, 0.0075, 0.01, "fraction of taxable sales", "literature", "https://www.cdtfa.ca.gov/taxes-and-fees/sales-use-tax-rates.htm",
    "Bradley-Burns Uniform Local Sales and Use Tax", "Bradley-Burns local 1%: 0.75% to the city/county general fund + 0.25% county transportation (split unverified this session). SF is a consolidated city-county. Low = general-fund only.")
add("sf_property_tax_rate", 0.0118, 0.0116, 0.0118, "fraction of assessed value", "assumed", None,
    None, "1% Prop 13 base + voter-approved debt ~0.16-0.18% (unverified: no SF Treasurer page could be retrieved this session; replace with the FY2025-26 secured rate).")
add("assessed_value_usd_per_m2", 5000, 3000, 9000, "USD/m2", "assumed", None, None,
    "Assessed value of new floor area (~$465/sqft). Downtown office values have collapsed (e.g. 350 California sold ~-75%, see literature/office-to-residential-conversion.md); keep as slider.")
add("value_of_weak_tie_usd_per_yr", 1100, 300, 2500, "USD/tie-year", "assumed",
    "https://www.housinglin.org.uk/_assets/Resources/Housing/OtherOrganisation/Report_SFHASocialValueToolkitGuidanceNotes.pdf",
    "HACT/Fujiwara UK Social Value Bank (via SFHA toolkit guidance notes)",
    "Derived: Social Value Bank 'talks to neighbours regularly' ~GBP 4,511/person-yr divided by an assumed ~5 local weak ties, converted to USD. Upper anchor: UK DCMS severe loneliness GBP 9,537/yr (https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/963077/Loneliness_monetisation_report_V2.pdf). Wellbeing valuations are not market values; show as adjustable.")
add("value_per_encounter_usd", 0.05, 0.0, 0.25, "USD/encounter", "assumed", None, None, "Small value per positive chance encounter; no literature value. Sandstrom & Dunn 2014 show weak-tie interactions raise same-day wellbeing but not in $.")
add("workdays_per_year", 250, 230, 260, "days/yr", "assumed", None, None, "Weekdays modeled per year (52x5 minus holidays).")

# ---------------------------------------------------------------- congestion
add("bpr_alpha", 0.15, 0.15, 1.12, "-", "literature", "https://www.fhwa.dot.gov/ohim/hpmsmanl/appn5.cfm",
    "Bureau of Public Roads (1964) volume-delay function; FHWA HPMS Appendix N",
    "BPR default. MTC Travel Model One does NOT use BPR 0.15/4: freeways use 0.20*((V/C)/0.75)^6 (~alpha 1.12, beta 6) and arterials an Akcelik curve (" + TM1_VDF + "). Default BPR is gentle below V/C=1; use high values as sensitivity.")
add("bpr_beta", 4.0, 4.0, 6.0, "-", "literature", "https://www.fhwa.dot.gov/ohim/hpmsmanl/appn5.cfm", "BPR (1964); FHWA HPMS Appendix N", "See bpr_alpha. TM1 freeway curve ~beta 6.")
add("lane_capacity_vph", OrderedDict(motorway=2050, motorway_link=1450, trunk=1450, primary=900, secondary=800,
                                     tertiary=650, residential=600, unclassified=600, living_street=300),
    None, None, "veh/hour/lane", "literature", TM1_CAP, "MTC Travel Model One SpeedCapacity_1hour.block (area type 0 = regional core)",
    "TM1 regional core: freeway 2,050, expressway/ramp 1,450, major arterial 900, collector 600 (650 in CBD area type 1). Cross-check: HCM base saturation flow 1,900 pc/h/ln x g/C 0.45 = 855. secondary (800) and living_street (300) are our interpolations (assumed). See literature/congestion-modeling.md.")
add("urban_free_flow_speed_kmh", OrderedDict(motorway=88, motorway_link=48, trunk=64, primary=32, secondary=32,
                                             tertiary=28, residential=24, unclassified=24, living_street=10),
    None, None, "km/h", "literature", TM1_CAP, "MTC Travel Model One SpeedCapacity_1hour.block free-flow speeds, regional core",
    "TM1 core: freeway 55 mph (88), expressway 40 mph (64), ramp 30 mph (48), major arterial 20 mph (32), collector 10 mph (16). SF default street limit 25 mph (40 km/h). tertiary/residential/living_street are our choices (assumed). Observed congested downtown arterial speed 2025: 12.9 mph AM / 11.5 mph PM (SFCTA CMP 2025, https://www.sfcta.org/reports/congestion-management-program-2025) - use as a validation target, not free flow.")
add("traffic_evaporation_median", -0.106, -0.22, -0.05, "fraction of treated road's prior traffic", "literature", CAIRNS,
    "Cairns, Atkins & Goodwin (2002), Disappearing traffic? The story so far, Proc. ICE Municipal Engineer 151(1)",
    "62 results, 51 (82%) showed reductions. Median -10.6%, mean -21.9%, central shopping schemes median -13.7%. DENOMINATOR: % of the traffic that previously used the treated road, measured across the wider area - NOT % of total area traffic/VMT. Cairns et al. 1998 report median ~-14%. Validation target, should emerge from behavior.")
add("car_trip_time_elasticity", -0.5, -1.0, -0.22, "elasticity", "literature", "https://www.vtpi.org/elasticities.pdf",
    "Litman (VTPI), Transportation Elasticities; Goodwin (1996) Empirical evidence on induced traffic, Transportation 23",
    "Goodwin 1996: traffic volume w.r.t. travel time ~-0.5 short run, ~-1.0 long run (https://trid.trb.org/View/458127). VTPI lists US urban auto -0.22 (high end of range here).")

# ---------------------------------------------------------------- mode choice / population
add("downtown_sf_worker_mode_share",
    OrderedDict(drive_alone=0.26, carpool=0.06, transit=0.45, walk=0.12, bike=0.04, other=0.03, wfh=0.20),
    None, None, "share of commuters (wfh = share of workers)", "assumed",
    "https://censusreporter.org/tables/B08601/?primary_geo_id=05000US06075",
    "Anchors: ACS 2024 1-yr B08601 (workplace = SF County) and SFCTA Downtown Travel Study 2025",
    "No published work-trip mode split for FiDi-only workplaces was retrievable. Anchors: (1) ACS 2024 B08601, people WORKING in SF County, commuters excl. WFH: drive alone 42.1%, carpool 8.5%, transit 34.2%, walk 8.6%, bike 3.3%, other 3.4%; WFH 15.9% of workers. (2) SFCTA Downtown Travel Study (2023, all trip purposes, downtown): auto 36.9%, transit 20.9%, walk/bike 39.7%, TNC 2.5% (" + DTS + "). FiDi is far more transit-oriented than the county (BART/Muni Metro trunk, $22-40/day parking), so we shift ~16 pts from car to transit/walk. Commute-share values exclude WFH and sum to 1.0; wfh is separate. Sensitivity: use the ACS county split as the car-heavy bound.")
add("sf_county_worker_mode_share_acs2024",
    OrderedDict(drive_alone=0.421, carpool=0.085, transit=0.342, walk=0.086, bike=0.033, other=0.034, wfh=0.159),
    None, None, "share of commuters excl. WFH (wfh = share of all workers)", "data", "https://censusreporter.org/tables/B08601/?primary_geo_id=05000US06075",
    "ACS 2024 1-year, Table B08601 Means of Transportation to Work for Workplace Geography, San Francisco County",
    "Total workers 632,129; WFH 100,347. Computed from table counts (drove alone 224,109; carpool 45,066; transit 181,920; walked 45,522; bike 17,403; taxi+moto+other 17,762).")
add("downtown_trip_mode_share_sfcta",
    OrderedDict(y2019=OrderedDict(auto=0.245, transit=0.279, walk_bike=0.434, tnc=0.042),
                y2023=OrderedDict(auto=0.369, transit=0.209, walk_bike=0.397, tnc=0.025)),
    None, None, "share of trips to/from/within Downtown", "data", DTS,
    "SFCTA, Downtown Travel Study (May 2025), Executive Summary",
    "All trip purposes, from household travel diaries. Downtown trips -46% within the core 2019-2023; work trips -66%. Downtown workers teleworking 2+ days/week: 14% -> 63%.")
add("car_availability_by_income", OrderedDict(low=0.55, mid=0.72, high=0.80), 0.5, 0.9, "share of workers with a vehicle available", "assumed",
    "https://censusreporter.org/tables/B08014/?primary_geo_id=05000US06075", "ACS 2024 1-year B08014 (Vehicles available, SF resident workers)",
    "Anchor: 76.3% of SF-resident workers have >=1 vehicle (B08014: 109,361 of 460,929 have none). No ACS table crosses vehicles by worker earnings; gradient by tier is assumed. Note ACS B08519 (SF workplace) shows auto commute share is nearly flat by earnings (~49% <$15k, ~52% $15-50k, ~50% >=$50k of non-WFH commuters), so income mainly matters through VOT, not car access.")
add("daily_parking_cost_fidi_usd", 22.0, 22.0, 40.0, "USD/day", "data", "https://www.sfmta.com/index%2Ephp/garages-lots/golden-gateway-garage",
    "SFMTA Golden Gateway Garage (250 Clay St) rates", "Early bird $22, 12-hr max $40, 24-hr max $46, $8/hr daytime. City garage; private FiDi garages are typically pricier (unverified). Many commuters have employer-paid parking (share unverified).")
add("bart_fare_usd", OrderedDict(east_bay=6.33, peninsula=5.07, sf=2.85, sf_bart=2.55, north_bay=8.0), None, None, "USD one-way (Clipper)", "data", BART_GTFS,
    "BART GTFS feed v72 (fare_rules/fare_attributes, valid 2026-01-12..2026-08-30), weighted by BART 2025 weekday 05-10h hourly OD to EMBR+MONT",
    "Our computation: ridership-weighted AM fare to Embarcadero/Montgomery: East Bay $6.33 (range $4.20 W. Oakland - $9.95 Berryessa), Peninsula $5.07 (Daly City $4.30 - Millbrae $6.15; SFO $11.80), SF BART $2.55. sf = Muni adult fare $2.85 Clipper/MuniMobile (https://www.sfmta.com/fares). north_bay has no BART: Golden Gate Transit/Ferry fare assumed ~$8 (unverified).")
add("bridge_toll_usd", 8.50, 8.0, 8.50, "USD", "literature", "https://en.wikipedia.org/wiki/San_Francisco%E2%80%93Oakland_Bay_Bridge",
    "Bay Bridge toll schedule 2026 (Wikipedia infobox; primary BATA page not reachable)",
    "2026: $8.50 standard, $4.25 carpool weekday peak (FasTrak), westbound only. Primary BATA/MTC source not verified this session (unverified).")
add("sf_persons_per_household", 2.14, 1.80, 2.24, "persons/household", "data", "https://censusreporter.org/tables/B25010/?primary_geo_id=05000US06075",
    "ACS 2024 1-year B25010, San Francisco County", "Owners 2.51, renters 1.93. Low = 15 tracts in our sim bbox (ACS 2019-23 5-yr, " + ACS5 + ", computed by data agent in data/backend/acs.json). High = Census QuickFacts 2019-23 (2.24).")
add("persons_per_household_downtown", 1.80, 1.6, 2.0, "persons/household", "data", ACS5,
    "ACS 2019-2023 5-year, B01003/B11001 for the 15 SF tracts inside the sim bbox", "37,174 residents / 20,604 households. Use for residents of FiDi/SoMa blocks.")
add("sf_office_occupancy_rate", 0.472, 0.44, 0.55, "fraction of pre-pandemic badge swipes", "data", "https://www.kastle.com/safety-wellness/getting-america-back-to-work/",
    "Kastle Systems Back to Work Barometer, week incl. 13 Oct 2026", "SF 47.2% vs 10-city average 55.1%. Measured relative to pre-pandemic swipes in Kastle buildings, not share of all workers. Tue-Thu peaks are higher (unverified daily breakdown).")
add("fidi_office_vacancy_rate", 0.29, 0.248, 0.309, "fraction of inventory", "data", "https://kidder.com/wp-content/uploads/market_report/office-market-research-san-francisco-2026-2q.pdf",
    "Kidder Mathews, San Francisco Office Market Report Q2 2026", "FiDi 29.0%, South FiDi 24.8%, SoMa 33.2%, citywide 27.2%. CBRE Q1 2026: North FiDi 30.9%, South FiDi 26.1%, SoMa 35.4%, city 30.4% (peak 36.9% Q3 2024) (https://mktgdocs.cbre.com/2299/4b628c03-e0be-422a-af2b-5bd047bb9a65-960261425/San_Francisco_Office_Figures_Q.pdf).")
add("soma_office_vacancy_rate", 0.332, 0.332, 0.354, "fraction of inventory", "data", "https://kidder.com/wp-content/uploads/market_report/office-market-research-san-francisco-2026-2q.pdf",
    "Kidder Mathews Q2 2026 (CBRE Q1 2026 high)", "Use for SoMa blocks south of Mission.")
add("office_sqft_per_job", 240, 220, 300, "gross sqft/job", "literature", SFP_JH, "SF Planning, Jobs-Housing Fit Report 2020",
    "SF Planning employment density factors (office 240). Central SoMa blended ~220. National CBECS median ~600 sqft/worker is not representative of downtown SF (https://www.eia.gov/consumption/commercial/data/2018/bc/pdf/b16.pdf). Multiply by occupancy for on-site workers.")
add("retail_sqft_per_job", 350, 300, 500, "gross sqft/job", "literature", SFP_JH, "SF Planning, Jobs-Housing Fit Report 2020", "Retail/restaurant density factor.")
add("hotel_sqft_per_job", 440, 400, 900, "gross sqft/job", "literature", SFP_JH, "SF Planning, Jobs-Housing Fit Report 2020", "'Visitor' (hotel) density factor. hotel_rooms_per_job not found.")
add("other_sqft_per_job", 600, 400, 900, "gross sqft/job", "assumed", None, None, "Civic/institutional/PDR density; no SF-specific value retrieved.")
add("residential_sqft_per_unit_gross", 950, 900, 1000, "gross sqft/unit", "literature",
    "https://www.spur.org/sites/default/files/2023-10/HR%26A_SF_Office_to_Residential_Conversion_Feasibility_Study_Sept_2023.pdf",
    "SPUR / HR&A, SF Office-to-Residential Conversion Feasibility Study (Sept 2023)", "650 net sqft/unit at 75-80% efficiency => ~850-900 gross; SF '30 by 30' maps 5M sqft -> ~5,000 units (~1,000 gross) (https://sf.gov/reports/july-2024/30-x-30).")
add("walking_speed_m_s", 1.34, 1.07, 1.40, "m/s", "literature", "https://github.com/sfcta/activitysim-sfcta/blob/main/configs/common/constants.yaml",
    "SFCTA ActivitySim constants (walk 3 mph)", "3 mph = 1.34 m/s. MUTCD signal timing uses 3.5 ft/s (1.07 m/s) as a slow-walker design value (https://mutcd.fhwa.dot.gov/htm/2009/part4/part4e.htm).")
add("walk_detour_factor", 1.21, 1.14, 1.30, "network/crow-fly distance", "literature", "https://arxiv.org/pdf/1708.00836",
    "Boeing (2019), Urban spatial order: street network orientation, configuration, and entropy (SF circuity)", "SF walk network circuity ~1.21 (drive network ~1.31). MATSim default beeline factor 1.3. Only for off-network trips (we route on the graph otherwise).")
add("bike_speed_m_s", 4.2, 3.5, 5.0, "m/s", "assumed", None, None, "Urban cycling ~15 km/h incl. signals (common planning assumption; no SF measurement retrieved).")
add("departure_time_distribution_sf",
    OrderedDict([("00:00-04:59", 0.0209), ("05:00-05:29", 0.0183), ("05:30-05:59", 0.0216), ("06:00-06:29", 0.0500), ("06:30-06:59", 0.0566),
                 ("07:00-07:29", 0.1325), ("07:30-07:59", 0.1172), ("08:00-08:29", 0.1843), ("08:30-08:59", 0.1096), ("09:00-09:59", 0.1417),
                 ("10:00-10:59", 0.0470), ("11:00-11:59", 0.0140), ("12:00-15:59", 0.0515), ("16:00-23:59", 0.0347)]),
    None, None, "share of SF-resident commuters (excl. WFH) leaving home", "data", "https://censusreporter.org/tables/B08302/?primary_geo_id=05000US06075",
    "ACS 2024 1-year B08302 Time of Departure to Go to Work, San Francisco County (residence geography)", "n = 368,083. Residence geography (SF residents).")
add("arrival_time_distribution_sf_workplace",
    OrderedDict([("00:00-04:59", 0.0201), ("05:00-05:29", 0.0097), ("05:30-05:59", 0.0221), ("06:00-06:29", 0.0408), ("06:30-06:59", 0.0498),
                 ("07:00-07:29", 0.0856), ("07:30-07:59", 0.1081), ("08:00-08:29", 0.1456), ("08:30-08:59", 0.1397), ("09:00-09:59", 0.1907),
                 ("10:00-10:59", 0.0659), ("11:00-11:59", 0.0258), ("12:00-15:59", 0.0538), ("16:00-23:59", 0.0421)]),
    None, None, "share of people working in SF (excl. WFH) arriving at work", "data", "https://censusreporter.org/tables/B08602/?primary_geo_id=05000US06075",
    "ACS 2024 1-year B08602 Time Arriving at Work, Workplace Geography, San Francisco County",
    "n = 531,782. Better than B08302 for downtown inflow timing (includes in-commuters). BART EMBR/MONT exits peak 08:00-08:59 (22-25% of daily exits; data/backend/transit.json).")
add("home_region_share_downtown_workers",
    OrderedDict(east_bay=0.328, peninsula_south_bay=0.214, sf_west=0.110, sf_southeast_mission=0.142, sf_north=0.048, sf_in_area=0.028, north_bay=0.063, other=0.066),
    None, None, "share of jobs in sim bbox by home region", "data", LODES,
    "Census LEHD LODES8 OD main JT00 2023 (CA), jobs in SF blocks inside the sim bbox; computed in data/backend/lodes.json",
    "Excludes home blocks >150 km from FiDi (HQ-reporting artifacts). Unfiltered: east_bay 0.275, peninsula_south_bay 0.179, sf_west 0.092, sf_se_mission 0.119, sf_north 0.040, sf_in_area 0.023, north_bay 0.053, other 0.218. LODES counts jobs at reported worksite (not attendance).")
add("income_tier_share_downtown_workers", OrderedDict(low=0.067, mid=0.080, high=0.853), None, None, "share of jobs", "data", LODES_WAC,
    "Census LODES8 WAC 2023 (CE01-CE03), SF blocks in sim bbox", "322,449 jobs: <= $1,250/mo 21,535; $1,251-3,333/mo 25,892; > $3,333/mo 275,022. Tier 'high' starts at only ~$40k/yr, so split it further with ACS earnings if needed.")
add("lunch_out_share_office_workers", 0.52, 0.40, 0.60, "share of in-office days", "literature", "https://www.aol.com/articles/week-worth-lunches-now-cost-130000134.html",
    "ezCater 2025 office lunch survey (via press coverage)", "2.6 purchased lunches per in-office week of ~5 days. US national, not SF-specific. Secondary source.")
add("coffee_trip_share", 0.30, 0.19, 0.45, "share of in-office days", "assumed", "https://ncausa.org/Newsroom/Grounds-for-celebration-Americans-remain-committed-to-coffee",
    "National Coffee Association newsroom, National Coffee Data Trends summary", "66% daily coffee drinkers x ~29% buying away from home => ~19% of adults/day (derived); bumped for downtown office commuters (assumed).")
add("morning_coffee_share", 0.25, 0.15, 0.35, "share of in-office days", "assumed", None, None, "Office workers buying coffee right after arriving; no SF measurement.")
add("avg_ticket_usd", OrderedDict(cafe=7.0, restaurant=28.0, fast_food=13.0, bar=25.0, shop=45.0), None, None, "USD/visit", "literature",
    "https://www.retailbrew.com/stories/2023/05/30/higher-average-lunchtime-checks-post-pandemic",
    "Toast restaurant check data (2023); ezCater; SF downtown shopper survey 2007-08",
    "cafe $7 ($5-8; SF lattes $6.25-8 unverified), restaurant $28 (Toast full-service lunch check ~$31 per check), fast_food $13 (derived from ezCater $34.82/week over 2.6 lunches), bar $25 (Portland 2012 $17-22/trip inflated, assumed), shop $45 (downtown SF $40-88/visit, 2007-08 survey via Streetsblog). See literature/retail-and-walkability.md.")
add("walker_vs_driver_visit_ratio", 2.0, 1.1, 3.2, "visits/month ratio", "literature", "https://sf.streetsblog.org/2009/05/27/only-17-percent-drive-to-downtown-sf-to-shop-study-finds",
    "SF downtown shopper survey (via Streetsblog 2009); Takapuna/Auckland (Fleming et al.); Clifton et al. 2012 Portland",
    "Downtown SF: walkers ~8 visits/month vs drivers ~4. Takapuna ~12 vs ~6 is widely cited (https://openrepository.aut.ac.nz/handle/10292/999) but its figures could not be retrieved (unverified). Clifton (https://trec.pdx.edu/research/project/411): drivers spend more per trip, walkers/cyclists more per month.")
add("ped_street_retail_uplift", 0.15, 0.0, 0.30, "fractional change in sales", "literature", "https://nacto.org/wp-content/uploads/measuring_the_street_nyc_dot.pdf",
    "NYC DOT Measuring the Street (2012); Volker & Handy (2021) review; TfL/UCL",
    "Central +15%. NYC Pearl St (FiDi) plaza +14% vs borough; Brooklyn Pearl St +172% (outlier); TfL public-realm upgrades up to +30%; Oslo car-free core ~0 (no harm); Valencia St SF tracked comparison zip; SF parklet businesses +29% vs +10% (Controller 2021, secondary). Volker & Handy (https://ideas.repec.org/a/taf/transr/v41y2021i4p401-431.html): effects positive or non-significant.")
add("ped_footfall_uplift", 0.29, 0.11, 0.65, "fractional change in pedestrian volume", "data", "https://www.sfmta.com/project-updates/april-2022-update-new-hearing-date-and-new-robust-data",
    "SFMTA JFK Promenade data update (April 2022)", "JFK Drive walking +29%, biking +76% (2019-2021). Low = Times Square ped volume +11% (NYC DOT 2010). High = SF Slow Streets walking +65% (SFMTA 2021). Oslo +14% people on street, +43% people staying; Copenhagen car-free area x4 => staying x4.")
add("rent_walkability_elasticity", 0.005, 0.001, 0.009, "fractional rent change per Walk Score point (engine: per 10% foot-traffic change)", "literature",
    "https://experts.arizona.edu/en/publications/the-walkability-premium-in-commercial-real-estate-investments/",
    "Pivo & Fisher (2011), The walkability premium in commercial real estate investments, Real Estate Economics 39(2)",
    "Pivo & Fisher: +1% to +9% value per 10 Walk Score points (property type dependent). The engine applies this per 10% change in nearby foot traffic/access - mapping 1 Walk Score point to a 10% foot-traffic change is our assumption. Barcelona green axes: rents +15% within 50 m, +8.5% within 100 m (thesis DiD, case-studies/barcelona-superblocks.md); Seoul Cheonggyecheon land +30-50% within 50 m.")
add("encounter_window_min", 15, 5, 15, "minutes", "assumed", "https://pmc.ncbi.nlm.nih.gov/articles/PMC6906316/",
    "Sapiezynski et al. (2019), Interaction data from the Copenhagen Networks Study, Scientific Data", "CNS Bluetooth scans every 5 min. We use 15-min co-presence bins at places/segments for compute reasons (assumed).")
add("tie_formation_prob_per_repeat_encounter", 0.02, 0.01, 0.10, "probability per repeated co-presence", "assumed", "https://escholarship.org/uc/item/4tp2801z",
    "Calibration assumption bounded by Hipp & Perrin (2009) and Hall (2019, ~50 h to casual friend)",
    "No direct measurement exists. Calibrate so that light-traffic vs heavy-traffic streets reproduce Appleyard's ~2-3x gap in local acquaintances (literature/social-interaction-in-public-space.md). Hall 2019 (https://greatergood.berkeley.edu/article/item/how_long_does_it_take_to_make_a_friend).")
add("appleyard_friends_by_traffic", OrderedDict(light=3.0, moderate=1.3, heavy=0.9), None, None, "friends per resident on the street", "literature",
    "https://amara.org/videos/WrBmfcwZMu7b/en/103981", "Appleyard (1981) Livable Streets, via Streetfilms video transcript; see also https://pps.org/article/dappleyard",
    "3.0 vs 0.9 friends confirmed only via Streetfilms transcript; 1.3 moderate (unverified). Acquaintances 'about twice as many' on light streets. Validation target for the social model.")
add("repeat_days_per_year", 60, 30, 120, "days/yr", "assumed", None, None, "Days a habitual lunch-spot pairing repeats per year (hybrid work ~2-3 office days/week).")
add("street_dwell_share_car_free", 0.08, 0.03, 0.15, "share of passers-by", "assumed", "https://nacto.org/wp-content/uploads/greenlight_midtown_nycdot.pdf",
    "Anchor: NYC DOT Green Light for Midtown (2010)", "Times/Herald Sq: +84% people staying; Oslo +43% staying. Absolute share lingering is assumed.")

# ---------------------------------------------------------------- Market St validation targets
add("muni_speed_change_market_car_free", 0.06, 0.04, 0.136, "fractional Muni speed change", "data", SFMTA_BMS,
    "SFMTA Board, Better Market Street update (19 Jan 2021); SF Chronicle 26 Feb 2020 quoting SFMTA",
    "~6% faster on average; 'up to 12% reduction in Muni travel time' (= +13.6% speed, best line, 9R best). No line-by-line table published. Clean after-window only ~7 weeks before COVID shelter-in-place (Mar 2020). Chronicle: https://www.sfchronicle.com/bayarea/article/Results-of-car-free-Market-Street-so-so-for-SF-15087210.php")
add("parallel_street_max_slowdown_market_car_free", 0.04, 0.0, 0.06, "fractional travel-speed reduction", "data", INRIX,
    "INRIX (2020), Full car ban on Market Street: little impact on surrounding roads",
    "Worst: Mission St SB 8 AM 10.3 -> 9.9 mph (-4%); worst single hour -6% (Mission SB 9 AM, 5 PM). Adjacent streets average -1% AM / 0% PM; Howard and Folsom got 1-10% faster. INRIX did not report Bush/Pine/Golden Gate/Turk. Only ~200-400 private cars/h used Market peak direction before the ban.")
add("cycling_change_market_car_free", 0.25, 0.20, 0.30, "fractional change in bike volume", "data", SFMTA_BMS,
    "SFMTA Board Better Market Street update (Jan 2021); SFMTA blog 'Moving Better Market Street forward'",
    "Peak-hour bikes ~650 -> >800/h (+25%) 'until Shelter in Place ordered'. https://www.sfmta.com/blog/moving-better-market-street-forward")

# ---------------------------------------------------------------- extra context / validation
add("bay_bridge_aadt", 231000, None, None, "vehicles/day (two-way)", "data", "https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/Traffic_AADT/MapServer/0",
    "Caltrans Traffic Census AADT (2024), SF-Oakland Bay Bridge toll plaza", "Peak hour 15,400. I-80 near 4th/5th St connections 93,000-113,000 AADT. Bay Bridge volume ~9% below pre-pandemic (SFCTA DTS 2025).")
add("downtown_arterial_speed_mph_2025", OrderedDict(am=12.9, pm=11.5), None, None, "mph", "data",
    "https://www.sfcta.org/sites/default/files/2025-12/SFCTA_CMP2025_Fig4-3_CMP_Arterial_Average_Speeds_Citywide_and_in_the_Downtown_Core.csv",
    "SFCTA Congestion Management Program 2025, Fig 4-3", "2019: 10.4 AM / 9.1 PM. Citywide 2025 16.1 / 14.7. Downtown Muni bus 7.1 AM / 6.1 PM. Validation target for baseline congestion.")
add("bart_weekday_exits_downtown_2026_09", OrderedDict(embarcadero=23619, montgomery=18908, powell=13573), None, None, "avg weekday", "data",
    "https://www.bart.gov/sites/default/files/2026-10/Ridership_202609.xlsx", "BART Monthly Ridership Report, September 2026",
    "Values as reported by data-sources agent; data/backend/transit.json gives EMBR exits 20,648 / entries 23,619 from the OD matrix (row/col convention). Sep 2019: EMBR 50,787, MONT 46,263, POWL 25,288 (~41-54% recovery).")
add("cairns_central_shopping_median", -0.137, None, None, "fraction", "literature", CAIRNS, "Cairns et al. (2002)", "Median for town-centre / central shopping area schemes (closest analogue to FiDi street pedestrianization).")
add("parking_price_elasticity_vehicle_trips", -0.3, -0.54, -0.1, "elasticity", "literature", "https://www.vtpi.org/elasticities.pdf",
    "Litman (VTPI), Transportation Elasticities", "General range -0.1 to -0.3; CBD preferred-parking -0.54 (Hensher & King 2001). SFpark -0.4 is an on-street occupancy elasticity, not mode choice.")
add("mtc_tm1_ivt_coef_work_per_min", -0.0134, None, None, "utils/min", "literature", "https://github.com/BayAreaMetro/travel-model-one/blob/master/model-files/model/ModeChoice.xls",
    "MTC Travel Model One, ModeChoice.xls (work tours)", "Non-work -0.0175. Walk <=1.5 mi 2x IVT; transfer = 30 IVT-min; BART IVT weighted 0.8x. Cost coef = 0.6*IVT/VOT.")
add("sfcta_ivt_coef_work_per_min", -0.016, None, None, "utils/min", "literature", "https://github.com/sfcta/activitysim-sfcta/blob/main/configs/resident/tour_mode_choice_coefficients.csv",
    "SFCTA ActivitySim tour mode choice coefficients (work)", "Walk -0.0424, initial wait -0.024. Repo forked from SANDAG ABM3 example; coefficients may not be SF-estimated.")

# ---------------------------------------------------------------- car inlets (added by the backend, 2026-10-24)
add("region_car_access", {
        "east_bay": [["key:i80", 0], ["side:east", 4], ["side:south", 3]],
        "peninsula_south_bay": [["key:us101", 0], ["side:south", 2]],
        "sf_west": [["key:mkt", 0], ["side:west", 1]],
        "sf_southeast_mission": [["key:fol", 0], ["side:south", 1], ["side:west", 3]],
        "sf_north": [["key:bwy", 0], ["side:north", 1], ["side:west", 3]],
        "north_bay": [["key:bwy", 0], ["side:north", 2], ["side:west", 4]],
        "sf_in_area": [["key:fol", 0], ["side:south", 1], ["side:east", 1], ["side:west", 1], ["side:north", 1]],
        "other": [["key:i80", 0], ["side:east", 4], ["side:south", 3]]},
    None, None, "[selector, extra minutes outside the map]", "assumed", None, None,
    "Which car inlets drivers from each home region can use, and the extra outside-the-map minutes of each option versus the region's main route (the legacy inlet, 0). Drivers pick the cheapest inlet by route cost, so closures shift entry points. Directions follow the regional freeway network (Bay Bridge -> I-80 ramps and the Embarcadero/SoMa grid; US-101/I-280 -> the south edge; western SF -> Market/Mission and the west edge; North Beach/Marin -> Broadway/Columbus and the north edge). Minutes are judgment, not measured.")
add("inlet_class_penalty_min", {"motorway": 0, "motorway_link": 0, "trunk": 0, "trunk_link": 0.5, "primary": 0, "primary_link": 0.5,
                                "secondary": 0.5, "secondary_link": 1, "tertiary": 1, "tertiary_link": 1.5, "unclassified": 2.5, "residential": 2.5},
    None, None, "minutes", "assumed", None, None,
    "Extra perceived minutes for entering or leaving the map on a lower-class street (slower approach outside the map, more signals). Keeps drivers on arterials unless a closure makes a side street clearly shorter.")
add("through_inlet_max_penalty_min", 1.0, None, None, "minutes", "assumed", None, None,
    "Through-traffic only uses non-freeway inlets whose class penalty is at most this (primary/secondary/tertiary). Freeway-to-freeway traffic stays on the freeway and never enters the street grid. Through volume between map sides is weighted by the lane capacity of each side's eligible inlets.")


def flat(v):
    return json.dumps(v) if isinstance(v, dict) else v


if __name__ == "__main__":
    with open(OUT + "/parameters.json", "w") as f:
        json.dump(P, f, indent=2)
        f.write("\n")
    with open(OUT + "/parameters.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "value", "low", "high", "unit", "status", "source", "notes"])
        for k, o in P.items():
            w.writerow([k, flat(o["value"]), o["low"], o["high"], o["unit"], o["status"], o["source"], o["notes"]])
    from collections import Counter
    print(len(P), Counter(o["status"] for o in P.values()))
