#!/usr/bin/env bash
# The Human Project: one command to set up and run everything locally.
#
#   ./run.sh            set up on first run, start the engine (:8787) and the web app (:8765), open the browser
#   ./run.sh --live     also start the shared session (SpacetimeDB :3000) so collaborators on your network
#                       can edit one plan together; prints the link to share
#   ./run.sh --no-open  don't open a browser (combine freely with --live)
#
# Ports: HP_PORT (engine, default 8787), WEB_PORT (web app, default 8765).
# Stop with Ctrl-C; both servers shut down together.
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
HP_PORT="${HP_PORT:-8787}"
WEB_PORT="${WEB_PORT:-8765}"
OPEN=1; LIVE=0
for a in "$@"; do case "$a" in --no-open) OPEN=0 ;; --live) LIVE=1 ;; *) echo "unknown option: $a" >&2; exit 2 ;; esac; done
mkdir -p .run

say() { printf '\033[1;36m▸\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m✗\033[0m %s\n' "$*" >&2; exit 1; }

# 1 · Python
PY="${PYTHON:-}"
if [[ -z "$PY" ]]; then
  for c in python3.12 python3.11 python3.10 python3.9 python3; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
fi
[[ -n "$PY" ]] || die "Python 3.9+ is required (python3 not found)."
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || die "Python 3.9+ is required (found $("$PY" -V))."

# 2 · Engine environment (first run only)
if [[ ! -x backend/.venv/bin/uvicorn ]]; then
  say "First run: creating backend/.venv and installing dependencies (about a minute)…"
  "$PY" -m venv backend/.venv
  backend/.venv/bin/pip install --quiet --upgrade pip
  backend/.venv/bin/pip install --quiet -r backend/requirements.txt
fi
[[ -f .env ]] || say "No .env found: the engine runs fully; AI features (planner text, Ask the city) stay off. See .env.example."

# 3 · Build the web app (inlines the world, the engine connector and the offline snapshot)
say "Building the web app…"
"$PY" scripts/build_mockup.py mockup/variants/a1-skyline-clean/template.html mockup/variants/a1-skyline-clean/index.html >/dev/null

# 4 · Start the engine
PIDS=()
cleanup() { for p in "${PIDS[@]:-}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM

if curl -fs "http://localhost:$HP_PORT/health" >/dev/null 2>&1; then
  say "Engine already running on :$HP_PORT"
else
  say "Starting the simulation engine on :$HP_PORT…"
  (cd backend && HP_PORT="$HP_PORT" exec .venv/bin/uvicorn hp.api:app --host 0.0.0.0 --port "$HP_PORT") >.run/engine.log 2>&1 &
  PIDS+=($!)
fi

# 5 · Start the web app
if curl -fs "http://localhost:$WEB_PORT/" >/dev/null 2>&1; then
  say "Web server already running on :$WEB_PORT"
else
  "$PY" -m http.server "$WEB_PORT" --directory mockup >.run/web.log 2>&1 &
  PIDS+=($!)
fi

# 6 · Wait for the engine to calibrate its baseline
say "Calibrating the baseline weekday…"
for i in $(seq 1 180); do
  if curl -fs "http://localhost:$HP_PORT/health" 2>/dev/null | grep -q '"baseline_ready":true'; then break; fi
  if [[ ${#PIDS[@]} -gt 0 ]] && ! kill -0 "${PIDS[0]}" 2>/dev/null; then die "The engine stopped. See .run/engine.log"; fi
  sleep 1
  [[ $i -eq 180 ]] && die "The engine didn't become ready in 3 minutes. See .run/engine.log"
done

# 7 · Shared session (optional): SpacetimeDB holds one plan for everyone; the engine computes it.
if [[ $LIVE -eq 1 ]]; then
  SPACETIME="$(command -v spacetime || echo "$HOME/.local/bin/spacetime")"
  [[ -x "$SPACETIME" ]] || die "--live needs the SpacetimeDB CLI (https://spacetimedb.com/install), then re-run."
  command -v node >/dev/null || die "--live needs Node 18+."
  if ! curl -s -o /dev/null "http://localhost:3000" 2>/dev/null; then
    say "Starting SpacetimeDB on :3000…"
    "$SPACETIME" start >.run/spacetime.log 2>&1 &
    PIDS+=($!)
    for i in $(seq 1 30); do curl -s -o /dev/null "http://localhost:3000" 2>/dev/null && break; sleep 1; done
  fi
  [[ -d backend/live/node_modules ]] || { say "Installing the live module's packages…"; (cd backend/live && npm install --silent); }
  say "Publishing the shared-plan module…"
  (cd backend/live && "$SPACETIME" publish human-live --server local --yes) >.run/spacetime-publish.log 2>&1 \
    || die "Publishing the live module failed. See .run/spacetime-publish.log"
  # SpacetimeDB refuses to call private addresses, so a small proxy exposes the engine on this machine's global IPv6.
  if ! lsof -iTCP:8788 -sTCP:LISTEN >/dev/null 2>&1; then
    (cd backend/live && ENGINE_PORT="$HP_PORT" SPACETIME="$SPACETIME" exec node scripts/engine-proxy.mjs --set) >.run/engine-proxy.log 2>&1 &
    PIDS+=($!)
    sleep 2
    kill -0 "${PIDS[${#PIDS[@]}-1]}" 2>/dev/null || say "Engine proxy didn't start (no global IPv6?). Edits will sync, but plans won't recompute. See backend/live/README.md (Engine URL)."
  fi
  LAN_IP="$( (ipconfig getifaddr en0 || ipconfig getifaddr en1 || hostname -I 2>/dev/null | awk '{print $1}') 2>/dev/null | head -1)"
fi

URL="http://localhost:$WEB_PORT/home/"
[[ "$HP_PORT" != "8787" ]] && URL="$URL?api=http://localhost:$HP_PORT"
say "Ready → $URL"
say "Engine API → http://localhost:$HP_PORT  (logs in .run/)   ·   Ctrl-C to stop"
if [[ $LIVE -eq 1 ]]; then
  say "Shared session on. Collaborators on the same network open:"
  say "    http://${LAN_IP:-<your-ip>}:$WEB_PORT/variants/a1-skyline-clean/index.html   then press Go live in the dock"
fi
if [[ $OPEN -eq 1 ]]; then (command -v open >/dev/null && open "$URL") || (command -v xdg-open >/dev/null && xdg-open "$URL") || true; fi
wait
