"""Regenerate every data/backend/*.json output from the cache (no network calls).

    backend/.venv/bin/python backend/data/run_all.py            # offline, cache only
    backend/.venv/bin/python backend/data/run_all.py --online   # allow fetching missing free sources
                                                                # (never starts Apify runs)
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import acs  # noqa: E402
import businesses  # noqa: E402
import landuse  # noqa: E402
import lodes  # noqa: E402
import traffic_counts  # noqa: E402
import transit  # noqa: E402


def main():
    offline = "--online" not in sys.argv
    steps = [
        ("lodes", lambda: lodes.main(offline=offline)),
        ("acs", lambda: acs.main(offline=offline)),
        ("landuse", lambda: landuse.main(offline=offline)),
        ("businesses", lambda: businesses.main("build")),  # cache only, never starts a run
        ("transit", lambda: transit.main(offline=offline)),
        ("traffic_counts", lambda: traffic_counts.main(offline=offline)),
    ]
    failed = []
    for name, fn in steps:
        print(f"== {name}")
        try:
            fn()
        except Exception:
            traceback.print_exc()
            failed.append(name)
    print("failed:", failed or "none")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
