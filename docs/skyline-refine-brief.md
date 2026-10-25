# Skyline refinement brief

The user picked **variant A · Skyline** (`mockup/variants/a-skyline/`, published at https://claude.ai/artifact/VPWacDTAF4M65YF5WWMNRT) as the nicest of three design languages. Three refinements are now built on top of it, each changing Skyline **slightly**. The aims:

- **more modern**
- **a better overview**
- **less confusing to a first-time user**

**Keep Skyline's identity:** sunny daytime 3D city, navy-glass HUD, Cities: Skylines-style icon dock, info views with legends, inlets with ▲/▼ counters, cyan cars / amber pedestrians, the 6-beat demo, compare, AI planner and pitch card. Everything that works today must still work. Read `mockup/variants/a-skyline/review-3.md` for the last known state and remaining issues.

## Shared goals for all three
- **The first 10 seconds:** a first-time user immediately understands *what this is* (a simulated weekday in SF), *what they can do* (change a street or block), and *where to look for the result*.
- **Modern and calmer:** less visual noise, more consistent spacing, fewer competing panels, crisp type, subtle motion, and fewer simultaneous numbers.
- **A clear overview:** the user always knows the current mode, scenario (Baseline vs Plan A) and time, and what changed.
- **Fix any leftover issues** from `a-skyline/review-3.md`.
- **No regressions.** Keep the scripted demo working, including "Next" at every beat, and keep the console free of errors.

## Technical
- **Work only in your own folder:** `mockup/variants/<your-folder>/` (`template.html` → `index.html`).
- **Build:** `python3 scripts/build_mockup.py mockup/variants/<f>/template.html mockup/variants/<f>/index.html`
- **Serve:** a server already runs on port 8765, serving `mockup/`. Your page is at `http://localhost:8765/variants/<f>/index.html`.
- **Browser:** use your OWN browser tab and close it when done; the pane has a tab limit. If no tab is free, use your own headless Chrome. Re-apply `resize_window` 1280x800 after each navigation. `window.__bw.run(n)` steps frames while the pane is hidden.
- **Title:** set `<title>` to `Human Project · <Variant name>`.
