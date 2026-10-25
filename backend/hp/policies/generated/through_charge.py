"""A flat charge for car trips crossing the area without a local destination."""
import numpy as np

KIND = "through_charge"
TITLE = "Through-traffic charge"
DESCRIPTION = (
    "Charge only through-traffic per one-way crossing, entering the engine's "
    "stay-versus-bypass choice. Workers, residents, and visitors are exempt."
)
PARAMS = {"amount": {"default": 5.0, "min": 0, "max": 50, "unit": "USD"}}
EXAMPLE = {"amount": 5.0}


def car_cost_usd(agents, params):
    # The engine charges crossings that stay in the area, not freeway bypasses.
    return np.where(agents.is_through, params["amount"], 0.0)
