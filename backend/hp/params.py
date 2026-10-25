"""Model parameters. research/parameters/parameters.json (written by the research agent, with sources)
overrides these defaults key by key, so docs and code cannot drift. Anything not overridden keeps the
status below and is reported in every result's `assumptions`."""
import json

from .config import RESEARCH_PARAMS

L, A, D, C = "literature", "assumed", "data", "calibrated"

# key: (value, status, note)
DEFAULTS = {
    # Valuation
    "vot_personal_usd_per_hr": (19.4, L, "USDOT BCA guidance, personal local travel"),
    "vot_business_usd_per_hr": (32.0, L, "USDOT BCA guidance"),
    "walk_wait_time_multiplier": (2.0, L, "USDOT: walk/wait time valued at 2x in-vehicle"),
    "vsl_usd": (13.2e6, L, "USDOT VSL 2024"),
    "heat_walk_rr": (0.89, L, "WHO HEAT walking RR at reference volume"),
    "heat_walk_ref_min_per_week": (168, L, "WHO HEAT reference walking volume"),
    "heat_walk_rr_cap": (0.30, L, "WHO HEAT max risk reduction"),
    "us_crude_mortality_20_74": (0.0045, A, "all-cause deaths per person-year, ages 20-74"),
    "crash_cost_usd_per_vmt": (0.10, A, "external crash cost, urban"),
    "co2_kg_per_vmt": (0.40, L, "EPA average passenger vehicle ~400 g/mi"),
    "scc_usd_per_tonne": (190, L, "EPA 2023 central (2% discount); slider"),
    "vehicle_operating_cost_usd_per_mile": (0.30, A, "fuel + maintenance + tires"),
    "retail_value_added_share": (0.35, A, "GDP share of food-service/retail revenue"),
    "sf_sales_tax_rate": (0.08625, D, "SF combined sales tax"),
    "city_share_of_sales_tax": (0.01, D, "Bradley-Burns local 1%"),
    "sf_property_tax_rate": (0.0118, D, "SF secured property tax rate"),
    "value_of_weak_tie_usd_per_yr": (500, A, "wellbeing value of an acquaintance"),
    "value_per_encounter_usd": (0.05, A, "small value per positive chance encounter"),
    "workdays_per_year": (250, A, "weekdays modeled per year"),
    "retail_net_new_share": (0.5, A, "share of a business's revenue gain that is new to the city rather than shifted from elsewhere"),
    "assessed_value_usd_per_m2": (5000, A, "assessed value of new floor area (~$465/sqft)"),
    # Congestion
    "bpr_alpha": (0.15, L, "BPR default"),
    "bpr_beta": (4.0, L, "BPR default"),
    "lane_capacity_vph": ({"motorway": 1900, "motorway_link": 1200, "trunk": 1500, "primary": 800, "secondary": 750,
                           "tertiary": 700, "residential": 550, "unclassified": 550, "living_street": 300}, L,
                          "HCM saturation flow ~1900 pcphpl x g/C ~0.4-0.45 on signalized grid"),
    "background_traffic_share": (0.45, A, "share of street traffic not modeled as agents (taxis/TNC, freight, buses, other through traffic); calibrated to counts when available"),
    "through_vehicles_per_day": (26000, A, "surface through-trips crossing the area between inlets"),
    "bypass_penalty_min": (6.0, A, "extra minutes for a through-trip to avoid the area entirely"),
    "region_car_access": ({"east_bay": [["key:i80", 0], ["side:east", 4], ["side:south", 3]],
                           "peninsula_south_bay": [["key:us101", 0], ["side:south", 2]],
                           "sf_west": [["key:mkt", 0], ["side:west", 1]],
                           "sf_southeast_mission": [["key:fol", 0], ["side:south", 1], ["side:west", 3]],
                           "sf_north": [["key:bwy", 0], ["side:north", 1], ["side:west", 3]],
                           "north_bay": [["key:bwy", 0], ["side:north", 2], ["side:west", 4]],
                           "sf_in_area": [["key:fol", 0], ["side:south", 1], ["side:east", 1], ["side:west", 1], ["side:north", 1]],
                           "other": [["key:i80", 0], ["side:east", 4], ["side:south", 3]]}, A,
                          "car inlets each home region may use: [selector, extra outside minutes]; drivers pick by route cost"),
    "inlet_class_penalty_min": ({"motorway": 0, "motorway_link": 0, "trunk": 0, "trunk_link": 0.5, "primary": 0, "primary_link": 0.5,
                                 "secondary": 0.5, "secondary_link": 1, "tertiary": 1, "tertiary_link": 1.5, "unclassified": 2.5, "residential": 2.5}, A,
                                "extra perceived minutes for entering/leaving on a lower-class street"),
    "through_inlet_max_penalty_min": (1.0, A, "through-traffic uses non-freeway inlets up to this class penalty"),
    "settle_days_baseline": (10, A, "replanning days for the baseline"),
    "settle_days_plan": (5, A, "replanning days for a plan (warm-started from baseline)"),
    "msa_step": (0.6, A, "congestion smoothing between replanning days"),
    # Mode choice
    "beta_time_per_min": (-0.035, L, "typical commute logit time coefficient (MTC/SFCTA range -0.02 to -0.05)"),
    "traffic_evaporation_median": (-0.11, L, "Cairns et al.: median traffic change across treated + parallel area"),
    "car_trip_time_elasticity": (-0.35, L, "short-run elasticity of car trips w.r.t. travel time"),
    "downtown_sf_worker_mode_share": ({"drive_alone": 0.20, "carpool": 0.06, "transit": 0.50, "walk": 0.12, "bike": 0.04, "other": 0.03}, L,
                                      "downtown SF workplace mode share (calibration target)"),
    "car_availability_by_income": ({"low": 0.55, "mid": 0.78, "high": 0.90}, A, "share with a car available"),
    "daily_parking_cost_fidi_usd": (32.0, A, "FiDi/SoMa daily garage rate"),
    "bart_fare_usd": ({"east_bay": 4.6, "peninsula": 6.2, "sf": 2.85, "north_bay": 8.0}, A, "one-way fares"),
    "bridge_toll_usd": (8.0, A, "Bay Bridge toll"),
    "walking_speed_m_s": (1.34, L, "average adult walking speed"),
    "bike_speed_m_s": (4.2, L, "urban cycling ~15 km/h"),
    "car_free_bike_comfort_bonus": (0.12, A, "perceived-distance discount for cycling on car-free streets; v1 used 0.25 and overshot Market St cycling (+530% vs +25%), revised to the ~10-15% detour cyclists accept for calmer routes"),
    "busy_street_bike_penalty": (1.10, A, "perceived-distance factor for cycling on primary/secondary streets with traffic"),
    "car_free_walk_comfort_bonus": (0.10, A, "perceived-distance discount for walking on car-free streets; v1 used 0.30 and overshot footfall (+91% vs +29%), revised to the ~10% detour pedestrians accept for pleasant routes"),
    "market_pre2020_cost_factor": (3.0, A, "travel-time factor on Market St for private cars before 2020: forced turns at 10th, 6th and 3rd made through-driving impractical (SFMTA 2009/2015 restrictions)"),
    "route_noise_sd": (0.25, A, "lognormal sd of perceived edge cost across cyclists (stochastic route choice, 3 draws)"),
    "bus_mixed_traffic_share": (0.25, A, "share of Muni's Market St running time exposed to car congestion (red transit-only lanes cover most of Market); v1 used 0.5"),
    # Land use and population
    "sf_office_occupancy_rate": (0.45, L, "Kastle SF weekday office occupancy"),
    "nonoffice_attendance_rate": (0.90, A, "share of non-office workers present on a weekday"),
    "fidi_office_vacancy_rate": (0.35, L, "downtown SF office vacancy"),
    "office_sqft_per_job": (250, L, "typical office density"),
    "retail_sqft_per_job": (450, L, "retail density"),
    "hotel_sqft_per_job": (900, A, "hotel density"),
    "other_sqft_per_job": (600, A, "civic/institutional/PDR density"),
    "sf_persons_per_household": (2.3, D, "ACS SF"),
    "visitors_per_day": (30000, A, "shoppers/tourists entering the area on a weekday"),
    "evening_visitors_per_day": (18000, A, "people coming into the area for dinner/drinks on a weekday evening"),
    "target_worker_agents": (9000, A, "agent budget; sets people-per-agent scale"),
    # Activities and retail
    "lunch_out_share_office_workers": (0.55, A, "share buying lunch out on an in-office day"),
    "coffee_trip_share": (0.30, A, "afternoon coffee run"),
    "morning_coffee_share": (0.25, A, "office workers who buy coffee right after arriving"),
    "avg_ticket_usd": ({"cafe": 8.5, "restaurant": 32, "fast_food": 14, "bar": 30, "shop": 42}, A, "average spend per visit"),
    "impulse_capture_per_passerby": ({"cafe": 0.010, "restaurant": 0.004, "fast_food": 0.007, "bar": 0.003, "shop": 0.006}, A,
                                     "share of passers-by who stop in (walkers only); calibrated so walkers visit ~2x as often as drivers"),
    "huff_distance_decay_per_m": (0.006, A, "Huff/MNL distance decay for walking destination choice"),
    "car_free_poi_attractiveness_bonus": (0.15, A, "utility bonus for POIs fronting a car-free street (pleasantness, outdoor seating); v1 used 0.35"),
    "walker_vs_driver_visit_ratio": (2.0, L, "walkers ~12 visits/month vs drivers ~6"),
    "ped_street_retail_uplift": (0.20, L, "retail/footfall uplift after pedestrianization, validation band 0.1-0.3"),
    "ped_footfall_uplift": (0.29, L, "JFK Promenade walking +29%"),
    # Social
    "encounter_window_min": (15, A, "co-presence time bin"),
    "tie_formation_prob_per_repeat_encounter": (0.02, A, "chance a repeated co-presence becomes an acquaintance"),
    "repeat_days_per_year": (60, A, "days a habitual lunch spot pairing repeats per year"),
    "street_dwell_share_car_free": (0.08, A, "share of passers-by who linger on a car-free street"),
    "appleyard_friends_by_traffic": ({"light": 3.0, "moderate": 1.3, "heavy": 0.9}, L, "Appleyard 1969 Livable Streets: friends per resident by street traffic"),
    "rent_walkability_elasticity": (0.04, A, "% rent change per 10% change in nearby foot traffic/amenity access"),
}


def _load_overrides():
    try:
        data = json.loads(RESEARCH_PARAMS.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


class Params:
    def __init__(self):
        self.meta = {}
        self.values = {}
        over = _load_overrides()
        for k, (v, status, note) in DEFAULTS.items():
            self.values[k] = v
            self.meta[k] = {"value": v, "status": status, "note": note, "source": None}
            o = over.get(k)
            val = o.get("value") if isinstance(o, dict) else None
            num = (int, float)
            if val is not None and ((isinstance(v, dict) and isinstance(val, dict)) or
                                    (isinstance(v, num) and isinstance(val, num) and not isinstance(val, bool))):
                if isinstance(v, dict) and isinstance(val, dict):
                    val = {**v, **val}
                self.values[k] = val
                self.meta[k] = {"value": val, "status": o.get("status", L), "note": o.get("notes") or note,
                                "source": o.get("source"), "low": o.get("low"), "high": o.get("high")}
        # Extra research keys are exposed too (read-only context for the narrative layer).
        for k, o in over.items():
            if k not in self.meta and isinstance(o, dict):
                self.meta[k] = {"value": o.get("value"), "status": o.get("status"), "note": o.get("notes"), "source": o.get("source")}

    def __getitem__(self, k):
        return self.values[k]

    def set(self, k, v, status=C, note=None):
        self.values[k] = v
        self.meta[k] = {**self.meta.get(k, {}), "value": v, "status": status, **({"note": note} if note else {})}

    def assumptions(self):
        return [{"key": k, "status": m["status"], "value": m["value"], "note": m.get("note"), "source": m.get("source")}
                for k, m in self.meta.items() if k in DEFAULTS and m["status"] in (A, C)]
