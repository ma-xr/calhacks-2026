"""Mobility, Local Economy and Equity agents. Each runs the plan on the engine and reports its part."""

from __future__ import annotations

import json

from uagents import Agent, Context, Protocol

from . import analysis, sim
from .config import FETCH_DIR, seed
from .models import AnalyzeRequest, AnalyzeResponse
from .streets import load_index

SPECS = {
    "mobility": ("Mobility", "Traffic, transit and mode shift for SF street closures, from the CommonGround sim."),
    "economy": ("Local Economy", "Foot traffic and revenue for SF businesses on a car-free street, from the CommonGround sim."),
    "equity": ("Equity", "Who gains and who pays (income tiers, health, social ties, rent) for SF street plans."),
}

def make_specialist(key: str, **agent_kwargs) -> Agent:
    live = bool(agent_kwargs.get("mailbox"))
    name, description = SPECS[key]
    agent = Agent(name=name, seed=seed(key), description=description,
                  readme_path=str(FETCH_DIR / "profiles" / f"{key}.md"), **agent_kwargs)
    proto = Protocol(name="HPStreetAnalysis", version="0.1.0")

    @proto.on_message(AnalyzeRequest, replies=AnalyzeResponse)
    async def on_request(ctx: Context, sender: str, req: AnalyzeRequest):
        ctx.logger.info(f"{name}: analysing {req.label} ({len(req.edges)} edges)")
        try:
            world = await sim.world()
            base = await sim.baseline()
            plan = await sim.pedestrianize(req.edges, req.label)
            index = load_index(frozenset(world["editable_edges"]))
            out = analysis.SPECIALISTS[key](plan, base, world, index, req.edges)
            out["facts"]["settle"] = plan.get("settle", {})
            resp = AnalyzeResponse(request_id=req.request_id, specialist=key, scenario_id=plan["id"],
                                   markdown=out["markdown"], facts_json=json.dumps(out["facts"], default=str))
        except Exception as e:  # report back instead of leaving the analyst waiting
            ctx.logger.exception(f"{name} failed")
            resp = AnalyzeResponse(request_id=req.request_id, specialist=key, error=f"{type(e).__name__}: {e}")
        await ctx.send(sender, resp)

    agent.include(proto, publish_manifest=live)
    return agent
