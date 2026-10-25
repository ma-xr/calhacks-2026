# The Human Project: mockup redesign brief

**Project name:** The Human Project. **Tagline:** "Modeling urban society with agent swarms."
The current mockup (`mockup/template.html`, built to `mockup/blockwise-demo.html`) is a single-page three.js simulation of SF's FiDi + upper SoMa built from real OSM data. It is still branded "Blockwise".

The user reviewed it and found it **too confusing and visually messy**. Every variant must fix all of the following:

## Required changes (all variants)
1. **Rename** everything to *The Human Project* (title, brand, intro, pitch card, AI name, copy). Remove "Blockwise".
2. **Free camera.** The user can pan, rotate, tilt and zoom (three.js `MapControls` from `three/addons/controls/MapControls.js`, damping, `zoomToCursor`, clamped polar angle and distance, target clamped to the map). Add camera presets (e.g. Overview, FiDi, SoMa, Top-down) plus a reset. The demo script uses smooth fly-to moves instead of the old fixed camera. Remove the mouse parallax. Distinguish click from drag: a click opens inspectors, a drag moves the camera. When the Pedestrianize tool starts on a road, painting must disable the controls for that stroke.
3. **Cars and pedestrians are clearly different by color**, everywhere: 3D agents, legend, inspector, feed. Suggested: cars in a cool cyan/blue, pedestrians in a warm amber. Keep the legend always visible.
4. **Cities: Skylines-inspired menus.** Big, clear icon tool buttons (inline SVG icons, no emoji). An **Info views** menu that switches the whole city into a data view, one at a time, each with a legend card (gradient or categories). Required info views:
   - **Traffic** (roads green → yellow → red by congestion; heat map)
   - **Foot traffic** (pedestrian heat map)
   - **Workplaces** (jobs per block, buildings colored)
   - **Residents** (living population per block)
   - **Visits** (business visits per block per day)
   - **Zoning** (categorical: residential / commercial / office / mixed / civic)
   - **Connections** (social ties arcs)
   - **Revenue change** (plan vs baseline, diverging)

   In an info view the city desaturates and only the data is colored. "Per block" means aggregating buildings into street blocks: union buildings whose centroids are within ~70 m and not separated by a road (`crossesRoad` already exists). The plan and baseline get separate colors so Compare still works (e.g. two per-vertex attributes mixed by `uPlan`). Hovering a building in an info view shows its block's value.
5. **A few distinct inlets/outlets only**, each with a 3D marker and a small live counter label showing people **entered ▲** and **left ▼** (scaled by SCALE), in the inlet's mode color:
   - BART stations: Embarcadero, Montgomery, Powell (pedestrians)
   - Highways: I-80 · Bay Bridge, US-101 (cars)
   - Main feeder roads: Market St (west), Folsom · 6th St (south), Broadway · Columbus (north) (cars)

   Remap regions to these inlets (each region has one car inlet and one BART inlet). Drop the other stations and transit center from spawning, and remove the clutter of station labels. Tag trips with their inlet (`gin`/`gout`) and count on spawn and finish. Recompute the counts on a time jump. Show "people in area", "cars moving" and "walking" as live stats.
6. **Less mess, more to look at.** Fewer and calmer labels, a clean hierarchy, and richer 3D: varied facade colors (glass towers, brick and sand low-rise), trees in parks and along SoMa streets (instanced), nicer water and ground. Day and night are still fine. The demo must stay legible.
7. Keep all existing functionality: baseline vs Plan A, the settle loop, Compare swipe, inspectors, the AI planner (scripted), the pitch card, the citizen feed, and the 6-beat scripted demo (update its camera moves, and show off a couple of info views during it).

## Technical constraints
- Single HTML template with `__WORLD__` placeholder. Build: `python3 scripts/build_mockup.py <template> <output.html>`.
- Libraries only from cdn.jsdelivr.net/npm/three@0.160.0 (import map already set up). No other external hosts except Google Fonts.
- Must run from a local http server: `python3 -m http.server 8765 --directory mockup`, then open `http://localhost:8765/variants/<name>/index.html`.
- Test in the built-in browser pane (`mcp__Claude_Browser__*`). The pane may be hidden, which throttles requestAnimationFrame. `window.__bw.run(n)` steps frames manually; keep an equivalent debug hook. After navigating, re-apply `resize_window` (1280x800); screenshots can glitch until you do.
- No console errors. Keep the page under ~2 MB.

## Demo context
This is for a Cal Hacks judging demo. A judge must understand within about 10 seconds what they are looking at and what changed. Clarity beats feature count.
