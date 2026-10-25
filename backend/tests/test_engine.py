"""Unit + regression tests. Run: backend/.venv/bin/python -m pytest backend/tests -q"""
import numpy as np
import pytest

from hp.engine import Engine, edits_key, hash_uniform
from hp.inputs import Inputs
from hp.network import CarNet
from hp.params import Params
from hp.validation import market_street, pedestrianization_retail
from hp.world import World


@pytest.fixture(scope="module")
def eng():
    w, P, I = World(), Params(), Inputs()
    e = Engine(w, P, I)
    e.calibrate()
    return e


def test_world_ids_match_frontend(eng):
    w = eng.w
    assert w.E == len(w.raw["edges"]) and w.B == len(w.raw["buildings"])
    assert [g["i"] for g in w.inlets] == list(range(len(w.inlets)))  # i = position; clients read the list, not fixed ids
    assert [w.inlets[i]["key"] for i in w.rail_inlets] == ["emb", "mont", "pow"]
    assert len(w.block_of) == w.B


def test_subtree_accumulation_equals_path_walk(eng):
    w = eng.w
    car = CarNet(w, set())
    cong = np.ones((24, w.E))
    t = car.tree(w.inlets[3]["entries"], 8, cong)
    tg = w.bld_car_node[w.bld_car_node >= 0][:200]
    loads = np.zeros(w.N); np.add.at(loads, tg, 1.0)
    f = car.accumulate(t, loads)
    f2 = np.zeros(len(car.arc_edge))
    for n in tg:
        nodes = t.path_nodes(int(n))
        for u, v in zip(nodes[:-1], nodes[1:]):
            f2[car.lookup[u, v]] += 1
    assert np.allclose(f, f2)


def test_crn_hash_is_deterministic():
    a = hash_uniform(np.arange(10), 3, 7)
    assert np.allclose(a, hash_uniform(np.arange(10), 3, 7)) and (0 <= a).all() and (a < 1).all()


def test_noop_plan_equals_baseline(eng):
    r = eng.evaluate({})
    assert r["metrics"]["delay_hours"] == eng.baseline["metrics"]["delay_hours"]
    assert r["metrics"]["revenue"] == eng.baseline["metrics"]["revenue"]


def test_edits_key_is_order_independent():
    a = edits_key({"pedestrianized": [3, 1, 2]})[1]
    b = edits_key({"pedestrianized": [1, 2, 3]})[1]
    assert a == b


def test_mode_split_calibrated(eng):
    c = eng.baseline["metrics"]["commuters"]
    tot = sum(c[k] for k in ("car", "transit", "walk", "bike"))
    tgt = eng.calibration["target"]
    for k in ("car", "transit", "bike"):
        assert abs(c[k] / tot - tgt[k]) < 0.04, k


def test_pedestrianizing_moves_the_right_way(eng):
    w = eng.w
    edges = w.stretch("2nd Street", "Market Street", "Folsom Street")
    r = eng.evaluate({"pedestrianized": edges})
    b = eng.baseline
    assert r["edges"]["car_day"][edges].sum() < 0.1 * max(b["edges"]["car_day"][edges].sum(), 1)
    assert r["edges"]["ped_day"][edges].sum() > b["edges"]["ped_day"][edges].sum()
    assert r["metrics"]["commuters"]["car"] <= b["metrics"]["commuters"]["car"]


def test_density_edit_adds_people(eng):
    w = eng.w
    b = int(np.argmax(w.bld_floor_area * w.bld_inside))
    r = eng.evaluate({"blocks": {str(b): {"scale": 2.0}}})
    assert r["metrics"]["jobs"] + r["metrics"]["residents"] > eng.baseline["metrics"]["jobs"] + eng.baseline["metrics"]["residents"]


def test_market_street_regression(eng):
    """Car-free Market St: area traffic falls within the Cairns et al. range (−25% … 0%)."""
    c = market_street(eng)
    vmt = next(r for r in c["rows"] if r[0].startswith("Car traffic in the whole"))[1]
    assert -0.25 < vmt < 0.0
    evap = next(r for r in c["rows"] if r[0].startswith("Traffic evaporation"))[1]
    assert evap < 0.25  # traffic does not grow (the ratio is unstable when pre-2020 Market carried few cars)
    worst = next(r for r in c["rows"] if r[0].startswith("Worst parallel"))[1]
    assert worst < 0.10  # INRIX: worst parallel street about +4%
    muni = next(r for r in c["rows"] if r[0].startswith("Muni"))[1]
    assert 0.0 <= muni < 0.20


def test_pedestrianization_footfall_band(eng):
    c = pedestrianization_retail(eng)
    ff = c["rows"][0][1]
    assert 0.05 < ff < 0.60


# ───────────────────────── car inlets (generated from every road crossing the map edge) ─────────────────────────
from hp.network import CarNet as _CarNet  # noqa: E402


def test_inlets_are_data_driven_and_legacy_keys_kept(eng):
    w = eng.w
    keys = [g["key"] for g in w.inlets]
    assert len(keys) == len(set(keys))
    for k in ("emb", "mont", "pow", "i80", "us101", "mkt", "fol", "bwy"):
        assert k in w.inlet_by_key
    assert len(w.car_inlets) > 20
    # Legacy entrances unchanged: Mission still carries Market's inflow.
    mission_nodes = {g["node"] for g in w.raw["gateways"] if g.get("src", "end") == "end" and g["name"] == "Mission Street"}
    assert mission_nodes & set(w.inlet_by_key["mkt"]["entries"])
    assert {g["side"] for g in w.inlets if g["mode"] == "car"} == {"north", "east", "south", "west"}


def test_every_car_inlet_connects_to_the_network(eng):
    """Each car inlet has an entry or exit; every entry can drive into the map and every exit is reachable from it."""
    w = eng.w
    car = _CarNet(w, set(eng.base_closed))
    cong = np.ones((24, w.E))
    core = np.where(car.open_node)[0]
    def reach_in(n):
        return np.isfinite(car.tree([n], 8, cong).dist[core]).any()

    def reach_out(n):
        return np.isfinite(car.tree([n], 8, cong, reverse=True).dist[core]).any()
    for g in (w.inlets[i] for i in w.car_inlets):
        assert g["entries"] or g["exits"], g["key"]
        if g["legacy"]:  # legacy lists are kept as they were; at least one end of each must work
            assert any(map(reach_in, g["entries"])) and any(map(reach_out, g["exits"])), g["key"]
        else:
            assert all(map(reach_in, g["entries"])) and all(map(reach_out, g["exits"])), g["key"]
    for k in ("i80", "us101", "mkt", "fol", "bwy"):
        assert w.inlet_by_key[k]["entries"] and w.inlet_by_key[k]["exits"], k


def _car_unreachable_workers(res):
    c = res["_state"]["ctx"]
    wk = (c.pop.kind == 0) & c.pop.car
    return int((c.car_node[wk] < 0).sum()), int((~np.isfinite(c.car_in_min[wk])).sum())


def test_no_worker_without_reachable_parking(eng):
    no_parking, unreachable = _car_unreachable_workers(eng.baseline)
    assert no_parking == 0 and unreachable == 0


def test_closing_an_inlet_street_moves_traffic_to_neighbours(eng):
    """Make the crossing edges of the busiest generated inlet car-free: its traffic shifts to other inlets."""
    w, b = eng.w, eng.baseline
    gen = [w.inlets[i] for i in w.car_inlets if not w.inlets[i]["legacy"] and w.inlets[i]["edges"] and w.inlets[i]["entries"]]
    g = max(gen, key=lambda g: b["inlets"][g["i"]]["entered"])
    assert b["inlets"][g["i"]]["entered"] > 0
    r = eng.evaluate({"pedestrianized": g["edges"]})
    assert r["inlets"][g["i"]]["entered"] < 0.1 * b["inlets"][g["i"]]["entered"]
    others_b = sum(x["entered"] for x in b["inlets"] if w.inlets[x["i"]]["mode"] == "car" and x["i"] != g["i"])
    others_r = sum(x["entered"] for x in r["inlets"] if w.inlets[x["i"]]["mode"] == "car" and x["i"] != g["i"])
    assert others_r > others_b
    assert r["metrics"]["commuters"]["car"] >= 0.95 * b["metrics"]["commuters"]["car"]
    assert _car_unreachable_workers(r) == (0, 0)


# ───────────────────────── new edits: street treatments, ramp closures, parks, business types ─────────────────────────
def test_new_edit_fields_left_empty_keep_ids_and_the_baseline(eng):
    """Empty new fields change nothing: the same scenario id (narrative caches and snapshots key on it) and the baseline."""
    import hashlib, json
    old_norm = {"pedestrianized": [1, 2], "reopened": [], "reopen_mode": "", "blocks": {"5": {"scale": 2.0, "zone": ""}}, "policies": []}
    old_key = hashlib.sha1(json.dumps(old_norm, sort_keys=True).encode()).hexdigest()[:12]
    new = {"pedestrianized": [2, 1], "blocks": {"5": {"scale": 2, "shops": ""}}, "street_treatments": {}, "closed_roads": []}
    assert edits_key(new)[1] == old_key
    assert eng.evaluate({"street_treatments": {}, "closed_roads": []})["id"] == "baseline"


def test_slow_street_cuts_traffic_less_than_car_free(eng):
    """SF Slow Streets: weekday car volume −35…−61%, walking and cycling up. Car-free removes all of it."""
    w, b = eng.w, eng.baseline
    es = w.stretch("2nd Street", "Market Street", "Folsom Street")
    r = eng.evaluate({"street_treatments": {str(e): "slow" for e in es}})
    car_b, car_r = b["edges"]["car_day"][es].sum(), r["edges"]["car_day"][es].sum()
    assert 0.2 * car_b < car_r < 0.8 * car_b
    assert r["edges"]["ped_day"][es].sum() > b["edges"]["ped_day"][es].sum()
    assert r["edges"]["bike_day"][es].sum() > b["edges"]["bike_day"][es].sum()
    assert r["metrics"]["delay_hours"] != b["metrics"]["delay_hours"]


def test_bike_lane_draws_cyclists(eng):
    w, b = eng.w, eng.baseline
    es = w.stretch("Howard Street", "2nd Street", "5th Street")
    r = eng.evaluate({"street_treatments": {str(e): "bike_lane" for e in es}})
    assert r["edges"]["bike_day"][es].sum() > 1.1 * b["edges"]["bike_day"][es].sum()


def test_road_diet_raises_congestion(eng):
    w, b = eng.w, eng.baseline
    es = w.stretch("Folsom Street", "2nd Street", "5th Street")
    r = eng.evaluate({"street_treatments": {str(e): "road_diet" for e in es}})
    assert r["edges"]["congestion_am"][es].mean() > b["edges"]["congestion_am"][es].mean()
    assert r["edges"]["car_day"][es].sum() < b["edges"]["car_day"][es].sum()


def test_closing_a_freeway_ramp_moves_traffic_to_other_ramps(eng):
    """Central Freeway / Embarcadero: traffic shifts to other ramps; few trips vanish (~3%)."""
    w, b = eng.w, eng.baseline
    ramp = max((r for r in w.ramps if r["inside"]), key=lambda r: b["edges"]["car_day"][r["edges"]].sum())
    assert b["edges"]["car_day"][ramp["edges"]].sum() > 0
    r = eng.evaluate({"closed_roads": ramp["edges"]})
    assert r["edges"]["car_day"][ramp["edges"]].sum() == 0
    others = [e for g in w.ramps if g["id"] != ramp["id"] for e in g["edges"]]
    assert r["edges"]["car_day"][others].sum() > b["edges"]["car_day"][others].sum()
    assert r["metrics"]["commuters"]["car"] >= 0.95 * b["metrics"]["commuters"]["car"]
    assert not set(ramp["edges"]) & set(r["_state"]["closed_walk"])  # a closed ramp is not a walkable street
    assert _car_unreachable_workers(r) == (0, 0)


def _busiest_office(eng):
    off = eng.pb.base_cap[0] * eng.w.bld_inside
    return int(np.argmax(off))


def test_park_replaces_a_building(eng):
    """A park: the building's jobs and floor area go; people visit it and meet there; it sells nothing."""
    b0 = _busiest_office(eng)
    r = eng.evaluate({"blocks": {str(b0): {"zone": "park"}}})
    bm, rm = eng.baseline["metrics"], r["metrics"]
    assert rm["jobs"] < bm["jobs"]
    assert rm["floor_delta_m2"] < 0
    parks = [p for p in r["virtual_pois"] if p["category"] == "park"]
    assert len(parks) == 1 and parks[0]["visits_day"] > 0 and parks[0]["revenue_day"] == 0


def test_business_type_opens_the_chosen_shops(eng):
    b0 = _busiest_office(eng)
    r = eng.evaluate({"blocks": {str(b0): {"shops": "bar"}}})
    vp = r["virtual_pois"]
    assert vp and {p["category"] for p in vp} == {"bar"}
    assert r["metrics"]["jobs"] == eng.baseline["metrics"]["jobs"]  # no rezoning: the building keeps its use
    g = eng.evaluate({"blocks": {str(b0): {"shops": "grocery"}}})["virtual_pois"]
    assert len(g) == 1 and g[0]["category"] == "shop" and g[0]["name"] == "New grocery"


@pytest.mark.xfail(strict=True, reason="Known: plans replan against the baseline's final-day car times from the seed state, so trip "
                                        "suppression on early days shifts flows; a plan that changes nothing is worth ~+$0.36M/yr")
def test_plan_that_changes_nothing_equals_baseline(eng):
    r = eng.evaluate({"pedestrianized": [10 ** 6]})  # an edge id that doesn't exist: not the baseline id, but no change
    assert r["id"] != "baseline"
    assert r["metrics"]["neighbor_ties"] == eng.baseline["metrics"]["neighbor_ties"]
