"""Run the four agents in one Bureau.

    python run.py            # local only: no endpoints, nothing registered anywhere
    python run.py --live     # Agentverse mailboxes, so ASI:One can reach the analyst
    python run.py --addresses
"""

from __future__ import annotations

import argparse
import os

from uagents import Bureau

from hp_agents.analyst import make_analyst
from hp_agents.specialists import SPECS, make_specialist


OFFLINE_AGENTVERSE = "http://127.0.0.1:9"


def build(live: bool = False, extra_kwargs: dict | None = None):
    # Local mode points every Agentverse/Almanac call at a dead local port, so nothing is published.
    kw = {"mailbox": True, "publish_agent_details": True} if live else {"agentverse": OFFLINE_AGENTVERSE}
    kw |= extra_kwargs or {}
    specialists = {k: make_specialist(k, **kw) for k in SPECS}
    analyst = make_analyst({k: a.address for k, a in specialists.items()}, **kw)
    return analyst, specialists


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="connect to Agentverse mailboxes")
    ap.add_argument("--addresses", action="store_true", help="print agent names and addresses, then exit")
    ap.add_argument("--port", type=int, default=int(os.getenv("HP_BUREAU_PORT", "8010")))
    args = ap.parse_args()
    analyst, specialists = build(args.live)
    agents = [analyst, *specialists.values()]
    if args.addresses:
        for a in agents:
            print(f"{a.name:20s} {a.address}")
        return
    Bureau(agents=agents, port=args.port, agentverse=None if args.live else OFFLINE_AGENTVERSE).run()


if __name__ == "__main__":
    main()
