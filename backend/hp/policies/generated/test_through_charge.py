import numpy as np
import pytest

from hp.policies import testing


@pytest.fixture(scope="module")
def mod():
    return testing.load_policy("through_charge")


def test_default_targets_only_through_traffic(mod):
    v = testing.view()
    out = testing.run(mod, v, {})
    assert set(out) == {"car_cost_usd"}
    cost = out["car_cost_usd"]
    assert cost.shape == (v.agents.n,)
    assert np.issubdtype(cost.dtype, np.floating)
    assert np.isfinite(cost).all()
    assert v.agents.is_through.any()
    assert (~v.agents.is_through).any()
    np.testing.assert_array_equal(
        cost, np.where(v.agents.kind == "through", 5.0, 0.0)
    )
    for kind in ("worker", "resident", "visitor"):
        assert (cost[v.agents.kind == kind] == 0.0).all()
    assert mod.KIND == "through_charge"
    assert mod.EXAMPLE == {"amount": 5.0}
    np.testing.assert_array_equal(
        testing.run(mod, v, mod.EXAMPLE)["car_cost_usd"], cost
    )


@pytest.mark.parametrize(
    "amount, expected", [(-1.0, 0.0), (0.0, 0.0), (2.5, 2.5), (50.0, 50.0), (51.0, 50.0)]
)
def test_amount_and_host_clipping(mod, amount, expected):
    v = testing.view()
    cost = testing.run(mod, v, {"amount": amount})["car_cost_usd"]
    assert cost.shape == (v.agents.n,)
    assert np.isfinite(cost).all()
    np.testing.assert_array_equal(
        cost, np.where(v.agents.is_through, expected, 0.0)
    )


def test_deterministic_and_does_not_mutate_inputs(mod):
    v = testing.view()
    before = v.agents.is_through.copy()
    params = {"amount": 7.5}
    first = testing.run(mod, v, params)["car_cost_usd"]
    second = testing.run(mod, v, params)["car_cost_usd"]
    np.testing.assert_array_equal(first, second)
    np.testing.assert_array_equal(v.agents.is_through, before)
    assert not v.agents.is_through.flags.writeable
    assert not np.shares_memory(first, v.agents.is_through)
    assert params == {"amount": 7.5}


@pytest.mark.parametrize("mask", [[], [False, False], [True, True]])
def test_empty_and_uniform_agent_views(mod, mask):
    class Agents:
        pass

    agents = Agents()
    agents.n = len(mask)
    agents.is_through = np.array(mask, dtype=bool)
    agents.is_through.setflags(write=False)
    cost = mod.car_cost_usd(agents, {"amount": 5.0})
    assert cost.shape == (agents.n,)
    assert np.issubdtype(cost.dtype, np.floating)
    assert np.isfinite(cost).all()
    np.testing.assert_array_equal(cost, np.array(mask, dtype=float) * 5.0)
