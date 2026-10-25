# Review 1: Variant A · Skyline

Reviewed at 1280x800 in the built-in browser. I explored the variant freely, then ran the full scripted demo end to end (the background-pane throttling was worked around in the page's runtime only; no files were changed). The console stayed clean the whole time: no errors and no warnings.

**Verdict:** the look is the strongest part. The navy glass HUD, the bottom dock and the info-view desaturation read straight away as "Cities: Skylines". Three things hurt the 10-second test, though. (1) The scripted demo starts with stale state from the previous session. (2) The key "what changed" evidence (spillover label, congestion, inlets) falls off-screen or under panels. (3) The numbers contradict the story: City value goes up, but Mobility shows in red, car trips go *up*, and the AI options show "delay +36%".

Measured demo timeline (seconds from Play): beat 1 at 0, Traffic view at 6, beat 2 at 16, Foot view at 25, beat 3 (Compare) at 32, beat 4 at 42, Connections at 56, beat 5 at 62, Revenue at 75, beat 6 (Pitch) at 81, end at 90. **The whole demo runs about 90 seconds, but the intro button says "Play the 3-minute demo".**

---

## P0: breaks the demo or the understanding

1. **The demo does not reset the feed, chips or metrics, so the opening frame shows stale data.** After I had explored, I pressed Play demo. At "06:00 Dawn" the first frame showed "City value +$868K", "Street life −$603K", "connections 5,334", and a feed full of lunch posts. One of them was "Maria O. 12:32 · new connection · Bumped into Omar at lunch…", which spoils beat 4 before it happens. The metrics then animate down to $0 over several seconds, while the judge is reading beat 1. By beat 5, the Maria post appears twice (12:16 and 12:32), and the feed is not sorted by time (12:16, then 13:00, then 12:32).
   *Fix:* in `runDemo()`'s reset block, clear `FEED` and re-render `#feed`, call `showChips('')`, and snap the displayed metrics to their targets with no lerp (set `shown = structuredClone(target)` or similar). Insert feed posts sorted by sim time, and drop any post whose time is later than `ui.time` after `jumpTo`.

2. **The spillover label is clipped off-screen in beat 3, which is the beat's main point.** It renders as "…over: 5th Street +712 cars/hr", cut off at the left screen edge. The compare camera `{x: hm.mx-80, z: hm.mz+60, d: 2000}` frames 2nd St, not the spill street.
   *Fix:* compute `spill()` before the fly, then fly to the midpoint of the hero edge and `s.e`. Also clamp `.lbl.spill` (and all `.lbl`) to the safe area inside the HUD: `left ∈ [300, vw-310]`, `top ∈ [80, vh-100]`.

3. **Beat 1's congestion story is not visible.** The caption says "Harrison, Bryant and the bridge ramps back up first", but at 07:27 to 08:08 the Traffic view is about 95% green. The only red is one ramp at the right edge, *underneath the City scorecard panel*. A judge sees "green roads", not "rush hour".
   *Fix:* frame the ramps in the left two-thirds of the viewport, for example by moving the target about 250 m east of the current `{x:60, z:280}` with a tighter `d` of about 1300. Also tune the colour ramp so that `liveCong` around 1.5 already reads orange (the scale is currently too forgiving). Alternatively, reword the caption to describe only what is actually red.

4. **The numbers contradict the narrative on screen.**
   - After 2nd St is pedestrianized, the scorecard shows **"Mobility −$291K, delay +82%"** in red. After the AI step it shows **"−$470K, delay +85%"**. The caption never explains this.
   - The AI goal is "…without slowing Bay Bridge traffic", but option 1 shows **"delay +36%"** and option 2 shows **"delay +34%"** in red, and option 1 is applied anyway.
   - The "AI SUGGESTION APPLIED" chip and the pitch card show **"Car trips into the area +102"** right after a car-free street, with "now ride BART + walk 0".
   - The settle chip says "Car trips / day −186" while the spill label says "+712 cars/hr". These are different units and an order of magnitude apart.

   *Fix:* make delay "bridge-approach delay" and keep the scripted AI option's delay at or below +5%, so it matches the goal. In the 2/6 Foot-traffic caption, add one line: "Driving gets slower nearby (Mobility −$291K), but street life and local business more than make up for it." Show scaled trips consistently (×SCALE) in every chip. Colour "+102 car trips" red, or don't show the row at all when it goes the wrong way.

5. **The intro promises a "3-minute demo" and "eight inlets", but neither holds.** The demo takes about 90 seconds. In the default Overview only 5 inlet labels are on screen, and of those, I-80 is half under the right panel and US-101 is under the time panel. "Market St (west)", "Folsom · 6th" and "Broadway · Columbus" are off-screen, and even the Top preset doesn't show all eight. Beat 1's caption names all eight while the camera is on SoMa.
   *Fix:* rename the button to "Play the 90-second demo". Make the Overview preset (and beat 1's opening shot) fit all 8 inlet positions inside the safe rectangle (compute `d` from the inlet bounding box, with roughly 300 px reserved on the left and right). Hold that shot for the full 6 seconds of beat 1 before flying into Traffic.

## P1: significant confusion or ugliness

6. **The mode colours collide with data colours.** Cyan (#27c4ff) means *car*, yet it is also used for Zoning "Commercial", the café umbrellas on the car-free 2nd St (cyan umbrellas on a car-free street read as cars), and the pitch "Mobility" swatch. Purple (#b46cff) means *Your edits*, yet it is also Zoning "Office", the Workplaces ramp, and the selected-block tint. Red means "Jammed", and it is also Zoning "Civic", Foot traffic "Busy" and Revenue "loss".
   *Fix:* reserve cyan and amber for agents only. Recolour Zoning to Residential green, Commercial coral (#ff8a5c), Office slate blue (#6f86b8), Mixed gold, Civic grey-lilac. Make the umbrellas red, white and green. Use an orange-to-white (or blue-violet) ramp for Workplaces instead of purple. Make Foot traffic a white → amber → deep orange ramp so it stays "pedestrian" coloured.

7. **The midday city has no cars at all.** From about 10:30 to 13:30 the top bar shows "cars moving 0", and the active car agents really are zero (only peds remain). Beats 4 and 5 happen at noon on empty streets, and "0" in the top bar looks like a bug. Car agents also look sparse even at peak: 215 drawn while the counter says 1,314.
   *Fix:* add a midday car baseline (deliveries, taxis, through-traffic: roughly 25% of peak) to the trip generator. Draw cars at a lower agent-to-person ratio than peds, or render a car as a short 2-to-3-car platoon so roads look busy at Overview distance.

8. **Edits give little feedback in 3D.**
   - When you paint 2nd St, the road turns *beige*, almost the same as the sidewalks. Nothing turns purple, even though the legend says "Your edits" is purple. The "2nd St · car-free" pill only appears after settling.
   - When you rezone a block to Mixed use, the block keeps the same pale selection tint. Nothing changes height or colour, and the only feedback is in the panels.
   - The Zoning tool does not switch to the Zoning info view.

   *Fix:* draw edited roads with a purple edge outline plus a soft purple glow. Show the street pill immediately when the stroke starts. On rezone, animate `aScale` and briefly flash the block in its new zoning colour. Make the Zoning and Density tools auto-enable the Zoning or Workplaces info view (as C:S does) and restore the previous view when the tool is left.

9. **The settle chip never goes away.** "AI SUGGESTION APPLIED · Foot traffic on edited streets +112%" stays at the top centre after the demo has ended, covering "FINANCIAL DISTRICT". The beat 2 chip also carries over into beat 3 over the compare view, and in beat 5 it covers the Revenue map.
   *Fix:* auto-dismiss chips after 6 seconds (or on the next caption), and give them a close button.

10. **You can't find Maria in beat 4.** The inspector opens with her diary, but nothing in the 3D view marks her among the amber dots.
    *Fix:* give the followed agent a white ring plus a floating "Maria" name pill with a stem, and a short trail. The follow camera already exists.

11. **The Connections view is a pink hairball,** and the top bar contradicts it. The legend says "Baseline / day 5,916 · Plan A / day 5,916", while the top bar says "0 connections" and the scorecard says "ties 0/day".
    *Fix:* in the info view, draw only the *new* ties versus baseline (plan minus base), or fade baseline arcs to 15%. Label the top-bar stat "new ties vs today", so it means the same as the scorecard.

12. **The AI panel covers the whole right column,** including the scorecard, while it previews options. The ghost preview of option 1 (the pale purple block) sits at the far left, where the eye isn't. The third option, "Convert Moscone Convention Center West to housing", is cut off below the fold.
    *Fix:* fly the camera to each option's `at` as it is hovered, not only for the applied one. Collapse the option cards to one line, with the numbers only, so all three fit. Shift the AI panel up so the scorecard's City-value pill stays visible, or dock the AI panel on the left during beat 5.

13. **Labels overlap the HUD.** The I-80 label (x 803–994) and the "Ferry Building" landmark sit under `#right` (x ≥ 976). US-101 and Market St sit under `#time`. "Transamerica Pyramid" renders at y = −37 (off-screen). Embarcadero is clipped by the scorecard in beats 1 to 3.
    *Fix:* in `updateLabels()`, hide or edge-pin any label whose rect intersects a HUD panel rect. For inlets, pin them to the safe-area edge with an arrow pointing to the off-screen location, as C:S does.

14. **The pitch card's stacked bar hides the loss.** `.stack` only renders positive parts, so the −$470K Mobility loss is invisible in the bar even though it appears in the legend. The footnote "WHO HEAT walking benefit with VSL $13.7M" is jargon. The title says "+ 2 rezoned buildings" while the UI elsewhere says "block".
    *Fix:* render negatives as a hatched red segment to the left of a zero line, or put a "−$470K" chip beside the bar. Rewrite the footnote in plain words ("Time valued at $19.60/h (US DOT); health benefit of walking per WHO"). Count blocks and say "1 rezoned block".

## P2: polish

15. The daypart is truncated: "Morning ru…" (scrollWidth 73 > clientWidth 70 in `#daypart`). *Fix:* widen `#time` to 372 px, or shorten the text to "Rush hour".
16. The scorecard shows "−$0" (negative zero) for Street life right after a reset. *Fix:* `money()` should print `$0` when `Math.abs(x) < 500`.
17. Before any edit, the scorecard is four "+$0" tiles plus an empty radar, and "City value +$0". That gives the first frame nothing to look at. *Fix:* when there are no edits, replace the pillars with a one-line prompt: "No changes yet. Paint a street with Pedestrianize, or press Play demo."
18. "settled · 5 sim days" is jargon. *Fix:* "Plan A vs today · stable".
19. The "Overview" camera button stays highlighted after the demo flies elsewhere (custom `flyTo` objects don't clear `.on`). *Fix:* clear `.on` whenever `flyTo` receives an object.
20. There is no hint for camera controls. *Fix:* add a tiny line in `#cams`: "Drag pan · Right-drag rotate · Scroll zoom" (shown for 10 s on first load). The reset button is the same as Overview, so make it reset north-up as well, or remove it.
21. The keyboard shortcuts only appear in `title` tooltips. The CSS for `.dk kbd` exists, but there are no `<kbd>` elements. *Fix:* add `<kbd>P</kbd>` and the others.
22. The legend subtitles wrap to 2 lines ("Where people are walking right now", "Business revenue per block, Plan A vs baseline"). *Fix:* shorten them to 1 line each ("Walkers right now", "Revenue vs today, per block").
23. The Revenue-change ramp ends ("−$6K / +$6K") don't say "per day". *Fix:* "−$6K/day … +$6K/day".
24. The "Demo finished. Everything is live now…" toast fires while the pitch veil (z-index 20) is open, so it is never seen. *Fix:* show it when the pitch is closed, or put it inside the pitch card.
25. The Zoning legend lists "Civic", but the inspector's zoning buttons have no Civic option. That's fine, but add "(fixed)" next to Civic in the legend.

---

## Keep, this works

- **The HUD layout and style:** the top bar with live stats, the centred icon dock with labels, time at bottom-left and camera at bottom-right. It is uncluttered and clearly C:S-like.
- **Info-view desaturation:** the city goes grey-white and only the data is coloured. Traffic, Workplaces and Zoning each read in under 2 seconds. The legend card (icon, title, one-line subtitle, gradient, ends) is a good pattern.
- **The info-views popup:** a 4x4 round-icon grid labelled "keys 1–8 · 0 off", with the active state shown on the dock button.
- **Inlet pills:** a mode-coloured icon disc, the name, and "▲ 6.8K ▼ 726". Compact and readable, and the right idea.
- **Close-up agents:** cyan car blocks versus amber pedestrian discs are clearly different at SoMa or closer zoom. The top-bar stat icons use the same colours.
- **The car-free 2nd St promenade:** café tables, trees and walkers make a lovely payoff shot in beat 4.
- **The settle chip "Foot traffic on 2nd St +97%":** one big number, the right idea. Just give it consistent units and auto-dismiss.
- **The Maria inspector:** the Baseline vs Plan A table with "● Car → ● BART + walk" in mode colours, plus the timestamped diary.
- **The compare swipe:** the BASELINE / PLAN A pills and the round handle are clear.
- **Pitch card structure:** a big net number, approval bars, and a "Who gains" table. The content is right; it only needs the fixes above.
- **The free camera:** MapControls with damping and clamping, smooth fly-to with lift, and a true top-down Top preset.
- **A clean console** throughout exploration and the full demo.
