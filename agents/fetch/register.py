"""Create Agentverse mailboxes for the four agents and publish their profiles.

This makes the agents PUBLIC on Agentverse (and discoverable from ASI:One). Run it once, on purpose:

    python register.py            # dry run: prints what would be registered
    python register.py --yes      # registers, using AGENTVERSE_API_KEY from the project-root .env

Then start them with `python run.py --live`. Same as clicking Connect → Mailbox in each agent's inspector.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from uagents.mailbox import AgentverseConnectRequest, register_in_agentverse
from uagents_core.registration import RegistrationRequest

from hp_agents.config import AGENTVERSE_API_KEY
from run import build


async def main(yes: bool):
    analyst, specialists = build(live=True)
    agents = [analyst, *specialists.values()]
    for a in agents:
        print(f"{a.name:20s} {a.address}  protocols={len(a.protocols)}")
    if not yes:
        print("\nDry run. Re-run with --yes to register these on Agentverse (public).")
        return
    if not AGENTVERSE_API_KEY:
        sys.exit("AGENTVERSE_API_KEY is not set in the project-root .env")
    for a in agents:
        # Mirrors the agent inspector's /connect handler (uagents.agent.Agent._handle_connect).
        details = RegistrationRequest(
            address=a.address, name=a.name, handle=a._handle, url=None,
            profile=a._build_registration_profile(), endpoints=a._endpoints,
            protocols=list(a.protocols.keys()), metadata=a.metadata,
        )
        res = await register_in_agentverse(
            request=AgentverseConnectRequest(user_token=AGENTVERSE_API_KEY, agent_type="mailbox"),
            identity=a._identity, prefix=a._prefix, agentverse=a._agentverse, agent_details=details,
        )
        print(f"{a.name:20s} {'registered' if res.success else 'FAILED: ' + str(res.detail)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true")
    asyncio.run(main(ap.parse_args().yes))
