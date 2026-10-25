# Factory Droid in the running product

Droid works inside the sim in two modes. The **policy compiler** writes new city levers. The **live agent** is read-only and answers questions about the scenario on screen while pointing the map.

# 1. Policy compiler

Planners keep asking for levers the engine doesn't have yet, like "a 10-minute loading zone on Howard", "free parking for EVs" or "a $5 charge only for through-traffic". Instead of us hand-coding each one, **Factory Droid writes the lever into the running product**. It plans a policy module, writes it with a test, runs our gate, and shows its plan, steps, diff and test output for a human to approve. On approval the module is hot-loaded, and `POST /scenario` can use it at once.

## Where and how Droid runs

| | |
|---|---|
| **Trigger** | `POST /policies/propose {"request": "a $5 charge only for through-traffic"}` from the UI's Droid panel (or the planner). Proposals run one at a time on a worker thread in the sim API. |
| **Runtime** | `backend/droid/service.py` starts `node backend/droid/runner.mjs`, which uses **`@factory/droid-sdk`** (`createSession`, `session.stream`) to drive the pinned `droid` CLI in `backend/droid/node_modules`. One proposal is one Droid session with `cwd = backend/hp/policies/generated`. |
| **Turns** | 1. **Plan**: Droid reads `hp/policies/__init__.py` (the plugin interface) and returns a JSON plan (kind, hooks, params, assumptions, steps). 2. **Implement**: it writes the module and its test, then runs the gate until it passes. 3. **Fix** (at most 2): the host re-runs the gate itself, and on a failure sends Droid the output. |
| **Tools** | An allowlist set with `updateSettings({ restrictToolIds })`: `Read Grep Glob LS Execute ApplyPatch TodoWrite Script WaitForScript`. Web Search, Web Fetch, MCP/app connectors, sub-agents, automations, skills and settings are not available. In droid 0.249 the tools are called from inside the `Script` tool (`tools.Read(...)`). |
| **Write scope** | Only `backend/hp/policies/generated/<kind>.py` and `backend/hp/policies/generated/test_<kind>.py`. Both paths are fixed after the plan turn. The SDK `permissionHandler` runs with `autonomyLevel: Off` and judges every call in a script (apply_patch/create/edit by target path, with no deletes). Anything else is cancelled. Every decision is logged in `permissions`. |
| **Exec scope** | One command: `<venv python> -m droid.gate <kind>`, optionally prefixed with `cd <backend or generated> &&`. Any other command that asks for confirmation is cancelled. Droid auto-runs commands it classifies as read-only (e.g. `ls`) without asking, so the sandbox below is what really enforces the limits. |
| **Sandbox** | This is Droid's own command sandbox, enabled through a runtime settings file (`--settings droid/runtime/compiler-settings.json`). Every command, including auto-run ones, runs under `sandbox-exec` with three limits:<br>• writes only in the cwd (`hp/policies/generated/`) and Droid's state dirs<br>• no network (`allowedDomains: []`)<br>• the project `.env` is unreadable<br>Don't wrap the CLI in your own `sandbox-exec`: macOS refuses nested sandboxes, and every command dies with SIGKILL. |
| **No network** | No web tools (above), and the sandbox denies network for every command (curl gets `403`). The runner gets a minimal env (`PATH`, `HOME`, `FACTORY_API_KEY`, `PYTHONPATH`) and no other project keys. In the gate, `socket` connect/resolve raise. The module may import only `numpy` and `math`. The droid process itself can still reach Factory's API (it has to). |
| **Time limit** | `DROID_TIMEOUT_S` (default 600 s) via an `AbortController` in the runner, plus a hard kill from the service 30 s later. Each gate run is capped at 240 s. |
| **Test gate** (`droid/gate.py`) | 1. Both files exist. 2. Static AST scan: allowed imports only; no `open`/`eval`/`exec`/`getattr`, no dunders, no `np.random`, no file I/O. 3. The module loads and matches the interface. 4. `pytest` runs on Droid's test **and** the engine suite `backend/tests`. 5. **Determinism**: the same edits evaluated twice give identical metrics. 6. **Sanity**: metrics are finite, VMT/revenue/visits are within ±50% of baseline and people within ±20%, and the policy must change something at its `EXAMPLE` params. |
| **Human gate** | `POST /policies/{id}/approve` works only when the proposal is `ready`, meaning the gate passed and the file hashes still match what the gate tested. It writes `hp/policies/generated/approved.json` and hot-loads the module (no restart). Only approved files are ever imported by the engine. `POST /policies/{id}/reject` deletes the two files. |
| **Visibility** | `GET /policies` returns the Policy Book (built-ins + approved plugins) and every proposal with `plan`, `todos` (Droid's own TodoWrite plan), `steps` (each tool call with input and output), `permissions`, `messages`, `gates` (each check and the pytest output), `diff` (unified), `metrics` (baseline vs policy) and `example_edit`. `GET /policies/{id}` returns one proposal. Run records live in `backend/droid/runs/<id>.json`. |
| **Key** | `FACTORY_API_KEY` is read from the project-root `.env` by `hp.config.secret`. It is passed only in the runner's env, never logged, and scrubbed from runner stderr. |

## Plugin interface (`backend/hp/policies/__init__.py`)

A policy module defines `KIND`, `TITLE`, `DESCRIPTION`, `PARAMS` (default/min/max/unit), `EXAMPLE`, and either `apply(ctx_view, params) -> dict` or any of these hooks. Each hook returns a numpy array:

- `car_cost_usd(agents, params)` → extra $ per one-way car trip. It enters the commuter logit, the through-traffic stay-or-bypass choice, and the city's charge revenue.
- `edge_cost_factor(edges, params)` → a multiplier on car travel time per edge.
- `poi_attractiveness(pois, params)` → a multiplier on destination attractiveness (Huff choice).

The views are read-only: `agents` (kind, arrival hour, income tier, inlets, …), `edges` (name, class, `stretch(street, from, to)`, …) and `pois` (category, `fronting(edge_mask)`, …). The engine hook is in `Ctx.__init__`/`choose`/`choose_poi` in `hp/engine.py`. With no plugin policies the effects are the identity, so the baseline is unchanged (tested).

## Try it

```bash
curl -s localhost:8787/policies/propose -H 'content-type: application/json' -d '{"request":"a $5 charge only for through-traffic"}'
curl -s localhost:8787/policies?full=false            # poll until status = ready
curl -s -X POST localhost:8787/policies/<id>/approve  # returns try_it.POST /scenario
curl -s localhost:8787/scenario?lite=1 -H 'content-type: application/json' -d '{"edits":{"policies":[{"kind":"<kind>","params":{"amount":5}}]}}'
```

**Measured** on 2026-10-24 (droid 0.249, default model) for "a $5 charge only for through-traffic":
- Droid's run: plan → `through_charge.py` (one `car_cost_usd` hook) plus 21 tests, gate passed on the first attempt, about 2.5 min end to end. Record: `runs/1024-163322-8a6e.json`.
- After approval, `POST /scenario` with `{"policies":[{"kind":"through_charge","params":{"amount":5}}]}` gives:
  - in-area VMT −2.2%
  - delay −3.6% (3,749 → 3,614 veh-h/day)
  - $57.9k/day paid by through-traffic
  - +105 car commuters (freed-up roads)
  - value +$1.35M/yr

Charges paid by through drivers are reported as `through_charges_paid_usd` but not counted as city revenue. Through drivers are valued on time alone, so counting the charge would book a transfer as a gain.

Setup is a single `cd backend/droid && npm install`, which pins `@factory/droid-sdk` 0.10.0 and `@factory/cli` 0.249.0.

# 2. Live agent (read-only Q&A that points the map)

Ask "Where is traffic worst at 8am?", "Why did revenue on 2nd St go up?" or "What happened to Maria today?". Droid queries the scenario with `simq` and answers in at most 120 words, using only simq numbers. It returns references (ids from world.json), a camera `focus`, `highlights` and a suggested map layer. The contract is in `docs/contracts/sim-api.md` → "Droid live agent".

| | |
|---|---|
| **Trigger** | `POST /droid/ask[?stream=1] {conversation_id?, scenario, question, view?}` from the UI's ask box. Follow-ups reuse `conversation_id`. |
| **Runtime** | `droid/live.py` keeps one `node droid/live.mjs` daemon. The daemon holds one warm Droid session per conversation (`@factory/droid-sdk` `createSession`, 20 min idle) plus one pre-warmed spare, so a new conversation skips startup. Model: `DROID_LIVE_MODEL` (default `claude-sonnet-5-5`) at `DROID_LIVE_EFFORT` (default `low`). |
| **Data** | Before each question the API exports a snapshot for the scenario to `droid/workspace/<sid>/` (gitignored), via `droid/live_export.py`. The snapshot holds the full `S.result_json`, the baseline, a world index (edges with midpoints and bboxes, buildings, POIs, blocks, inlets), validation, and agent views (hero pair, sample, changed agents). Droid never touches the engine and needs no network. |
| **Tools** | `restrictToolIds = Execute, Script, WaitForScript`. There is no Read, no ApplyPatch and no other write tool, and no web, MCP, sub-agents or skills. |
| **Exec scope** | Only simq. A command may be compound (split on `;`, `&&`, newlines) if every segment is `cd <backend>`, `P=<venv python>` or `<venv python \| $P> -m droid.simq <plain args>`. Pipes, redirects, `$(…)`, backticks and other binaries are cancelled and shown as a `denied` step. After a denial, or a reply without answer JSON, the service sends one repair turn to the same session ("retry with plain single simq commands") before falling back. |
| **Sandbox** | Droid's command sandbox (`droid/runtime/live-settings.json`): no writes anywhere under the project root, no network, `.env` unreadable. Verified by probes: `simq` runs; `wc .env`, `touch workspace/x` and `curl example.com` all fail. |
| **Answer gate** | Droid's last message must contain one JSON block (answer, references, focus, highlights, info_view, time_s, grounding). The service:<br>• drops reference ids that don't exist in world/scenario<br>• recomputes `focus` from the leading references' geometry<br>• unions `highlights`<br>• caps `time_s`/`info_view`<br>If Droid fails, times out (40 s) or returns no JSON, it falls back to the Claude `/narrative/explain` text with `references: []` (`source: "narrative_fallback"`). |
| **Visibility** | The SSE `step` events show every simq call (label, command, first 1,200 chars of output, or `denied`). The answer's `grounding` lists the simq commands behind it, and `source` and `latency_s` say how it was produced. |

**simq** (`python -m droid.simq --scenario <sid> <cmd>`) is stdlib only and runs in about 0.1 s. Commands: `summary`, `streets`, `edges`, `street`, `stretch`, `pois`, `poi`, `agent`, `agents`, `block`, `blocks`, `inlets`, `hour`, `value`, `assumptions`, `validation`, `find`. Every row carries ids and x/z, so Droid can cite places. Run `python -m droid.simq --help` for the full list.

**Measured** on 2026-10-24, after the inlet change (65 inlets) and the compound-command fix. In-process TestClient, `claude-sonnet-5-5` low, warm daemon. Each cell is latency / references kept; every answer had `source: "droid"`.

| Question | baseline | 2nd St car-free plan |
|---|---|---|
| Where is traffic worst at 8am? | 9.1 s / 4 | 8.0 s / 4 |
| Why did revenue on 2nd St go up? | 9.0 s / 2 (no change on baseline; cites 2nd St) | 8.7 s / 5 |
| ↳ follow-up "And what about Howard?" | — | 7.7 s / 3 |
| What happened to Maria today? | 6.6 s / 4 | 6.5 s / 3 (car → transit) |
| Which businesses lose out? | 8.2 s / 3 | 8.1 s / 5 |
| How many people arrive at Embarcadero BART? | 6.6 s / 3 | 9.2 s / 2 |

Earlier runs took 8–19.6 s, with one 44.6 s fallback while a policy-compiler run shared the Factory API at the same time.

`simq inlets` lists the 3 rail stations plus the top 15 car gateways (of about 62) with totals by mode. `simq inlet <key|name>` gives one inlet's hourly arrivals.
