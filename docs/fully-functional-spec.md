# Skyline Clean, fully functional

Skyline Clean (`mockup/variants/a1-skyline-clean/`) is the chosen frontend. "Fully functional" means **every number, flow and answer on screen comes from the engine** (`docs/contracts/sim-api.md`). It also means every engine capability a user would want has a control. The toy model survives only as a clearly labelled offline fallback.

## 1. Core: everything from the engine (Skyline Clean agent)
Fix everything in `mockup/variants/a1-skyline-clean/functional-audit.md`, sections A and B:
- **Every edit goes through `POST /scenario`:** pedestrianize (from `world.editable_edges`), density and zoning, policies, reopening Market St. Show streaming progress and a real error state with retry.
- **Engine-backed views:** info views, inspectors, live stats, inlet labels, pitch (`value.lines`, `assumptions`) and the demo all read engine results. No hard-coded copy numbers, and no `Math.random` in anything that looks like data.
- **Any clicked person** opens the `/scenario/{id}/agent/{agent_id}` view (diary, trips, ties), and Follow uses it.
- **Saved plans:** `GET /scenarios` lists cached plans in a small "Plans" menu with load and rename.
- **Provenance:** an "About the numbers" sheet built from `world.params` (counts by data / literature / assumed, with source links) and `result.assumptions`.

## 2. New panels as drop-in modules (module agent)
Built in `mockup/lib/` as classic scripts. Each is inlined at build time like the other libs, styled with Skyline Clean's tokens (navy glass, 12 px radius, Inter), and talks to the page only through a small host API:
- **`hp-ask.js`: Droid live agent** (`POST /droid/ask?stream=1`)
  - A chat drawer. Streams Droid's query steps ("Ranking businesses…") as a compact step list.
  - Renders the markdown answer and the `references` as chips; clicking a chip flies to it.
  - Applies `focus`, `highlights`, `info_view` and `time_s` through host callbacks. Keeps `conversation_id` for follow-ups.
  - Falls back to `/narrative/explain` when Droid is unavailable.
- **`hp-policy.js`: Policy Book** (`GET /policies`, `POST /policies/propose`, `/approve`, `/reject`)
  - Built-in levers with simple controls:
    - congestion charge on a chosen car inlet (inlet keys from `/world`, amount in $)
    - parking price
    - reopen Market St (`reopened` + `reopen_mode: "pre2020"`)
  - Droid proposals: type a request, see plan, steps, gate checks and metrics, then Approve or Reject. Approved kinds become available levers.
  - Applying a lever calls the host to merge it into the plan (`HPBackend.mergeEdits`) and re-settle.
- **`hp-live.js`: live multiplayer** (SpacetimeDB on `:3000`, `backend/live/client/dist/live.mjs`)
  - A "Go live" toggle. The shared plan streams in: car-free streets, block edits, other players' cursors and names on the map, and an activity feed.
  - Local edits call the reducers `set_pedestrian` / `set_block` / `reset`. When `scenario.plan_id` changes, the host loads the full result via `GET /scenario/{plan_id}`.
  - Hidden automatically when `:3000` isn't reachable, e.g. on a published artifact.

**Host API that each module receives:** `{ B /*HPBackend client*/, world, getPlanEdits(), applyEdits(edits, label), currentScenarioId(), flyTo({x,z,radius}), highlight({edges,buildings,pois,agents}), setInfoView(key), setTime(s), toast(msg), mount /*DOM node*/, theme }`.

## 3. Offline and published behaviour
- **Snapshot mode** (published artifact):
  - The demo path uses frozen engine results.
  - Ask, Policy Book proposals and Live show a short "Needs the live engine" state instead of failing.
  - Built-in levers that aren't in the snapshot fall back to the labelled estimate.
- **Live mode** (local, backend on :8787): everything works for real.

## 4. Done means
- Every control in the UI does something engine-backed in live mode.
- No console errors.
- The demo works with Next at every beat, in live and snapshot mode.
- A second browser tab in Live mode shows the first tab's edits and cursor within about 2 s.
- Droid answers move the camera and highlight what they mention.
