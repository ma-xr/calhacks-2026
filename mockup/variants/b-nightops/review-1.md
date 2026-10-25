# Review 1: variant B · Night Ops

Reviewed against one question: can a Cal Hacks judge tell within about 10 seconds what they're looking at, what they can do, and what changed?
Tested at 1280x800 in the built-in browser. I watched the full scripted demo (about 120 s), opened all eight info views, painted 2nd St by hand, rezoned a block and raised its density, and turned on Compare. The console showed no errors. The built page is 793 KB.

Screenshots are in `~/.claude/projects/-Users-maximilianthiersch-Projects-Cal-Hacks-13/ac7040a9-.../tool-results/` (`mcp-Claude_Browser-blob-*.jpg`).

**Verdict:** this is the most "cinematic" of the variants. The dark city with glowing data reads well in the info views, and the inlet tags look great. The demo itself undersells the product, though. Beat 1 talks about agents while the city is still empty. Traffic stays mostly green while the caption promises jams. Maria is never visible. The pitch card hides the last caption. Orange (your edits), amber (pedestrians) and Maria's trail all blur into one color family.

---

## P0: breaks the demo or the understanding

1. **Beat 1 opens on an empty city while the caption describes traffic.**
   - The caption "Cyan streaks are cars … Amber sparks are people" shows from 05:45 to 06:19, which is 7 s of real time. Live stats read `Cars moving 0 · Walking 0` and every inlet reads `▲ 0 ▼ 0` (first-frame screenshot).
   - The intro's first frame has the same problem: a dark, static city with zeros everywhere.
   - **Fix:**
     - Start the demo at about 07:15 (`jumpTo(435*60)`) and pre-warm the agents so the city is already busy on frame 1.
     - Do the same for "Explore on my own". Today it starts at 05:45 with nothing moving.
     - Keep the cars/pedestrians caption up for at least 6 s while rush traffic is visible. Only then switch to the Traffic view.

2. **The Traffic info view doesn't support its caption.**
   - The caption says "Harrison, Bryant and the Bay Bridge ramps back up first". On screen almost every road is green at 07:00 and at 08:07 (screenshots). Only the Bay Bridge approach and a little of Folsom turn orange or red.
   - Amber pedestrian agents on Market St also look like yellow congestion in this view.
   - Beat 1 then holds this mostly green map for 24 s, the longest single shot in the demo.
   - **Fix:**
     - Rescale the congestion ramp to the visible distribution, for example map the p50 to p98 of v/c to green → red, so peak hour actually shows yellow and red.
     - Hide or dim the agents while Traffic is on, keeping cars only as faint cyan.
     - Add 3D callout labels on the 2–3 worst links ("Bay Bridge ramp · jammed").
     - Shorten the Traffic hold to about 8 s.

3. **"Follow Maria" (beat 4, 22 s) never shows Maria.**
   - Nothing marks her agent and nothing labels her.
   - Her trail is drawn in amber (`new THREE.Color(2.6,1.6,.45)`). That is the same hue as pedestrians and as the painted 2nd St promenade, so the trail reads as part of the street.
   - The diary also already lists future entries ("17:29 Walked back to the station" at 12:07). The meeting is "12:23" in the diary but "12:16" in the feed.
   - **Fix:**
     - Add a large pulsing marker plus a floating label "Maria" above her agent. Use a unique color, such as white or `--social`.
     - Draw her trail in white or magenta.
     - Show only diary entries with time ≤ the current clock. Log the meeting with the same timestamp as the feed post.
     - Cut the wait loop to 10 s or less.

4. **The beat 6 caption is hidden behind the pitch card, and the demo ends under a modal.**
   - `.veil` is `z-index:10` and covers `#rcol`, so the 6/6 caption "Pitch to the Board …" is never seen.
   - When the demo ends, the pitch card stays open. The toast "Demo finished. Everything is live now: try painting a street." sits at `z-index:8` underneath it, so it is invisible.
   - **Fix:**
     - Raise `#caption` above the veil while the demo runs, or move the beat-6 copy into the pitch card's header.
     - Close the pitch card in `endDemo()`, or show the toast above the veil.

5. **"Next ▸" breaks pacing.**
   - Skipping beat 1 leaves the sim at about 06:40 and at 10×.
   - Beat 2's "Walkers pour into the new promenade" then plays over an empty 06:47 city (screenshot).
   - **Fix:** each beat sets its own state on entry. Beat 2 should `jumpTo(475*60)` and `setRate(30)` when it starts. Every beat should be self-contained so skipping is safe live on stage.

## P1: significant confusion or ugliness

6. **Too many orange tones.**
   - The edits accent `#ff6a1f`, the pedestrians `#ffb43f`, the Foot traffic ramp, Maria's trail, the "Visits" ramp and the selected-block highlight are all orange or amber.
   - A painted street (hand-painted test) looks like a row of pedestrian dots.
   - **Fix:** move "Your edits" to a color no agent uses, for example hot magenta `#ff3fa4` or white with a hatched pattern. Draw the promenade as a solid filled band with a white outline, not dots.

7. **Inlet tags collide with labels and HUD panels.**
   - The tag positioning in `updateLabels()` doesn't avoid other elements:
     - `Embarcadero BART` overlaps the "FINANCIAL DISTRICT" and "FERRY BUILDING" labels (DOM rect check).
     - The demo caption card covers the Embarcadero tag in beats 1–3.
     - "Replanning day 1/5" covers it in beat 2.
     - `Montgomery BART` slides under the legend card and the rail ("ONTGOMERY BART", beat 2 and beat 5).
     - `Market St W` and `Folsom · 6th St S` stack almost on top of each other.
   - **Fix:**
     - Treat the HUD rects (`#rail`, `#views`, `#rcol`, `#inspector`) as keep-out zones. Clamp or flip tags out of them.
     - Run a simple greedy de-overlap pass, moving tags vertically.
     - Hide district and landmark labels when an inlet tag overlaps them.

8. **The right column covers the action.** `#rcol` is 344 px wide and floats over the stage, which is only about 918 px wide. Caption plus chips plus the AI panel hide the whole north-east of the map, including Embarcadero and the Ferry Building. **Fix:** move the demo caption to a bottom-center lower-third (max 560 px) above the timeline. Keep only the result chip top-right.

9. **The info-view bar is icon-only.** Eight unlabeled glyphs sit at the top left, and only the active one shows a word. A judge can't tell which icon is "Visits" or "Revenue change" without hovering. The 0–8 hotkeys aren't shown anywhere. **Fix:** do it the Cities: Skylines way, with labels always visible under the icons ("Traffic · Foot · Jobs · Homes · Visits · Zoning · Ties · Revenue") or a flyout menu with labeled rows and the hotkey.

10. **The Zoning view is 84% "Mixed use".** 1,744 of 2,173 buildings are `k:'mixed'`, so the map is a sea of purple and the categorical view tells the judge nothing. **Fix:** infer use from the data that already exists (jobs vs residents per building, the height threshold) and fall back to office or residential. Alternatively, rename the category "Unclassified" and show it in grey.

11. **The Connections legend is useless.**
    - "Social tie" and "Walking to lunch" use the same `#c48cff` swatch.
    - The legend shows "Plan A 5,916/day · baseline 5,916/day" (identical before any edit) while the header says "ties formed today".
    - **Fix:**
      - Use one entry, "Arc = two people who met today". Or give lunch walks a second color.
      - Show "+X vs baseline" instead of two identical numbers.
      - Label the unit as "per day (projected)".

12. **Rezone gives no 3D feedback and the inspector goes stale.**
    - After switching a block to Residential, the buildings keep the same orange selection tint. Nothing in the live view says "this is now housing".
    - The subtitle still says "19 buildings · tallest 44 m · now Commercial" after rezoning to Residential and raising density to 3×.
    - The result chip is titled "BLOCK EDIT" but still shows "Foot traffic on edited streets +73%".
    - **Fix:**
      - On rezone, flash the block in its zoning-category color for 1.5 s, then keep a small zoning badge.
      - Re-render the subtitle from the current plan state.
      - For block edits, swap the last chip row to "Residents +1,811 · Jobs −2,977".

13. **Hand-painting 2nd St is hard.**
    - From the SoMa preset, 2nd St is hidden behind towers. Hover returned no tooltip at the projected street midpoint.
    - A drag along the street painted only 3 of 14 segments, leaving gaps, because pointermove events are sparse at speed.
    - **Fix:**
      - Interpolate between consecutive pointer samples and paint every edge crossed.
      - When the Pedestrianize tool is picked, auto-tilt the camera to near top-down.
      - Highlight the hovered road segment in the edit color before the click.

14. **Compare at default zoom shows no visible difference.** In the live view at Overview, both halves look identical, because a 3-block promenade is a few pixels wide. In beat 3, the "PLAN A" side tag is clipped against the right edge and wraps to "PLAN / A" (`placeHandle` doesn't clamp `tag-r`). **Fix:** force a data view (Traffic or Foot) whenever Compare turns on outside the demo. Clamp `#tag-r` to `stage.width - tagWidth - 12` and give it `white-space:nowrap`.

15. **Beat 5 doesn't land.**
    - The goal is typed into the bottom bar, far from the eye. Each option preview lasts 1.6 s.
    - The camera frames 2nd St, while the Revenue view's colored blocks sit at the left edge behind the legend card.
    - **Fix:**
      - Echo the typed goal in the AI panel as it's typed. The AI panel already shows the question; start it there.
      - Hold each option for 2.5 s.
      - After apply, fly to the bounding box of the blocks with |Δrevenue| > 0.

16. **The pitch name contradicts what was applied.** It says "2nd Street Promenade + 1 rezoned building", but the AI upzoned a whole block. "Drivers 8%" appears without explanation. "Hours of traffic delay +74" is not colored red. **Fix:** count edited blocks ("+1 upzoned block"). Color every Key-changes row by good or bad. Add a one-line "why" under the lowest approval ("Drivers: 5th St +712 cars/hr").

## P2: polish

17. The intro says "Play the 3-minute demo", but it runs about 120 s. Change it to "Play the 2-minute demo".
18. The tagline in the top bar truncates to "Modeling urban society …" as soon as City Value grows. Either drop the tagline from the bar (it's on the intro) or let the brand shrink.
19. "City value vs baseline +$0 /yr" and four green "+$0" pillars before any edit look like a broken state. Show "—" and "Make an edit to see impact" until the first settle.
20. Jargon:
    - "trips evaporated" (chip) → "trips no longer made".
    - "settled · 5 days" → "stable after 5 simulated days".
    - "Replanning day 1/5" → "Agents re-planning… day 1 of 5".
    - "City shape" → "Balance vs baseline".
    - "OVR" (camera) → "ALL".
21. "Cars moving 0" during lunch (12:07–14:30) looks broken. Either add midday deliveries and errand traffic, or label the stat "cars moving now".
22. Repetitive feed: two different people posted "Stuck on Market Street again. Two blocks in ten minutes." back to back. Restarting the demo also leaves the previous run's 12:xx posts in the feed while the clock reads 06:47. De-duplicate the templates and clear the feed in `runDemo()`.
23. Cars render as near-white blobs in close-ups (beat 2) instead of distinctly cyan. Lower bloom or exposure on car instances so the hue survives.
24. The Workplaces ramp tops out at `#6fe3ff`, nearly the car cyan. End the ramp at a white-blue that differs from the car color, or use teal → white.
25. "Visits" uses a red ramp, and red already means "worse" in Revenue change. Switch it to a purple → pink → gold ramp.
26. The block hover tooltip says only "Block · 3,282 jobs". Add the nearest street ("Block at 2nd & Howard · 3,282 jobs").
27. The inlet counters don't say that they are cumulative since 05:45 or since the last time jump. Add "today" to the tag header or the legend.
28. "+ Plan B" is a disabled tab that only adds noise. Hide it.

---

## Keep, this works
- Inlet tags: the mode-colored box, leader line to a pulsing 3D ring, and "▲ entered ▼ left" in mono read like a real ops board.
- Info-view transitions: the city desaturates and only the data glows. Workplaces, Foot traffic and Revenue change look striking and are instantly readable.
- Legend cards with a gradient and plain end labels ("free flow / jammed", "quiet / busy", "−$17K · no change · +$17K").
- The always-on bottom-left key "Cars · Pedestrians · Your edits", plus a "1 agent = 6 people" credit.
- The beat progress bar with numbered caption ("2/6"), with Next and Exit controls.
- The result chip after an edit ("Car trips / day −186 · now ride BART 180 · Foot traffic on 2nd St +97%") is the clearest "what changed" moment in the demo.
- The "2nd St · car-free" pill label in 3D, and the animated brush during the paint beat.
- Block-level selection highlight, and the inspector's Baseline vs Plan A table.
- The Pitch card layout: a big net number, a stacked value bar, approval bars, and trade-offs.
- Tool rail with SVG icons and keyboard hints (V/P/D/Z). The camera preset group with a reset button.
