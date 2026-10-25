#!/bin/sh
# Start the sim API on :8787 (baseline calibrates in ~10 s; /health shows when it is ready).
cd "$(dirname "$0")"
exec .venv/bin/uvicorn hp.api:app --host 0.0.0.0 --port "${HP_PORT:-8787}"
