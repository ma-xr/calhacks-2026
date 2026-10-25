# Review 1: Variant A3 · Skyline Guided (first-time user)

**Setup.** I used my own browser tab at a 1280x800 viewport, emulated and rendered scaled at 800x500, with `?snapshot`. Here is what I did:

1. Went through the welcome card, then did the 3-step tour, dragging 2nd St myself.
2. Opened the result card and tried Compare.
3. Explored freely with Overview / Top / SoMa, zooming out to the edge, the Traffic info view, and a free edit on Clementina St.
4. Switched to Baseline.
5. Watched the full scripted demo (about 107 s).
6. Stepped all 6 beats again with **Next ▸**.

The console was clean throughout: no errors or warnings, and no `window.error` events. I changed no files except this one.

**Verdict.** The onboarding is the best of any Skyline variant so far. The welcome card answers "what is this / what can I do / where do I look" in one glance. The tour is short, it lets you do the edit, and it hands you a plain-language result card. After the tour, the product becomes much less coherent. Unlocking crowds the HUD. The demo's opening shows zeros. The numbers across the card, scorecard, AI panel and pitch don't agree with each other, and units drift (/day vs /yr, 6 vs 21 people per agent). The pitch ends on a $5 Bay Bridge toll rather than the 2nd St story the whole onboarding built.

---

## 1. First 10 seconds

- **Welcome card (screenshot 1):** "What if 2nd Street belonged to people?", with three steps: Watch, Change, See the result. Below them are three buttons: tour, demo, explore. I knew immediately what this is (a simulated weekday downtown) and what I can do (make a street car-free). I didn't yet know *where to look* for results, but step 3 of the tour fixes that.
- **The footer contradicts the product:** "The agents follow simple rules and the numbers are illustrative." Yet the header chip says "Engine snapshot — calibrated to LODES, ACS, BART…", and the pitch says "Computed by the simulation engine".
- **Behind the card**, the HUD already shows **Plan A** highlighted even though there is no plan yet. The I-80 inlet pin is clipped under the "Try it" panel, and the Powell pin sits under the legend.

## 2. The tour

- **Step 1** rings the stats and explains the colours. It's good, but it mentions "the dashed line" and "glowing roads", and neither is visible at the tour's camera distance.
- **Step 2** is excellent. The camera flies to 2nd St, the street glows yellow, and a "Drag along 2nd St" pill appears, plus a "Do it for me" escape. My drag worked first time.
- **Step 3** shows a result card: "Nice! 2nd St is now car-free", with **588** fewer car trips a day, **24%** more people walking on 2nd St, **+$18K** a day for local shops, and City Value **+$6.36M/yr**. The tooltips on every number are clear plain English. **But the step-3 bubble covers the purple street it is describing**, and the card covers the top-centre of the map.
- **Overall it is helpful, not annoying.** It's 3 steps, skippable, and the user acts in step 2. Keep it.
- **Making an edit on my own afterwards was hard.** At the Overview/SoMa zoom, two drags on visible streets just panned the camera, with no feedback. The hit radius is 14 m and the start point must land on an edge. Only a click placed exactly on an alley (Clementina, found via projection) worked. A first-timer would conclude "painting is broken".
- **The free-edit result card is clear in form but deflating in content.** Clementina gives "0 change in car trips / 0% / +$152 a day", yet still opens with "Nice!" and a green check. Worse, the whole HUD silently rescales: walkers drop from about 12,000 to 312, and people in area from 271K to 32K. That's because the free edit falls back to "Estimate (engine offline)" with a different agent scale.

## 3. Clarity

- **Info views and legends.** Choosing an info view swaps the colour legend for a gradient legend ("Free flow → Jammed"). That's clean, and the best part of the HUD. The Connections legend (Baseline 12,427 / Plan A 12,664 per day) is a good touch. Problem: **Pedestrianize stays highlighted** in the dock while an info view is active, so the current mode is ambiguous.
- **Inlets.** Pills show a name and ▲ count, and the train icon vs car icon differs. **The legend never explains the icons** (train = BART exit, car = road entry). Only some pills show ▼. The counts are cumulative ("▲59K"), but nothing says "today". Several pills are clipped by side panels (I-80 and Embarcadero under the scorecard / Try-it, Powell under the legend), and they stack at the left edge (Powell / Folsom / Market).
- **Faded city edge.** It's only visible if you zoom out by hand past every preset. There, the faint dashed boundary, the paler context and the cyan entry-road dashes read well (screenshot "Top + zoom out"). **No camera preset shows it, and nothing in the tour points at it,** even though step 1 talks about it. BART inlets (Montgomery, Embarcadero, Powell) sit deep inside the box, so "where traffic enters" and "the edge" are two different ideas that the UI never reconciles.
- **Cars vs pedestrians vs bikes.** At the default and SoMa zoom the dots are tiny. Amber is readable, cyan cars are sparse, and I never visually picked out a green cyclist. The cycling stat jumps between 0, 75, 150 and 375 depending on the view. The stats say "cars moving / walking", but the tooltip says "in this view", which explains why 25 cars at noon in SoMa looks wrong. The tooltip says "1 dot ≈ 6 people", but the pitch footnote says "1 agent = 21 people".
- **Unlocking advanced tools.** It triggers automatically after the tour's first edit, with a toast ("New: Density & Zoning, plus the AI planner and the full scorecard") and NEW badges. The idea is great, but all of it lands at once: the scorecard with a radar, the "What people are saying" feed, a 6-stat top bar, Pitch, and 3 new dock buttons. The calm 3-panel screen becomes the busiest screen in the app in one frame. The demo also unlocks everything at second 0.

## 4. The scripted demo, beat by beat

Next ▸ works at every beat (1/6 → 6/6 → pitch), and City Value commits correctly ($0 → $6.36M at beat 3 → $35.1M at the pitch).

| Beat | What I saw | Consistent? |
|---|---|---|
| 1 Morning rush (07:15) | **0 cars, 0 walkers, every inlet ▲0 for about 9 s** while the caption says commuters "pour in through eight ways… each one counts people in ▲ and out ▼". Red appears on the ramps by 07:42. The caption says "186,000 commuters", but the top bar says "271K people in area today". | ✗ dead opening (a regression of a-skyline N1) |
| 2 Paint 2nd St | Foot-traffic view, pill "foot traffic +24% · car trips −588/day · drive time +1.2%". Same numbers as the tour. Good. The scorecard says Mobility **+$25K** next to "drive time +1.2%", with no explanation. | ~ |
| 3 Swipe | The spillover label "3rd St +17% traffic" now sits on the Plan A side (a-skyline P1-4 fixed). The right-side inlet pills pile up behind the scorecard. | ✓ / visual ✗ |
| 4 Follow Maria | The inspector shows Car → Car, driving 8 → **9 (red)**, walking 11 → 11, **"New connections today 0 → 0"** throughout. The caption says she "walks to **Grace**… runs into a coworker". The feed says "Bumped into **Dev** at lunch". The Connections legend says +237 **per day**, but the scorecard and top bar say "+237 new ties **/yr**". | ✗ names, ✗ units |
| 5 AI planner | The answer is engine-speak: "total delay falls 773.53 hours… rent pressure index… +0.03… the model does not report Bay Bridge traffic on its own." It proposes a **$5 Bay Bridge toll** for a goal of "without slowing Bay Bridge traffic". The card says "delay −11%", while the applied pill says "drive time −3.5%". After applying, Mobility **−$25.7M** sits next to faster driving. Economy jumps $1.29M → **$19.2M** while "shop sales" *fall* from +$18K to **+$10K/day**. New ties *drop* 237 → 136 while Street life $ *doubles*. | ✗✗ |
| 6 Pitch | The title is the AI toll option, not 2nd St. +$35.1M adds up (−25.7 + 1.63 + 19.2 + 32.6 + 7.43). But "Who gains" is **negative for every income third** (−$52 / −$56 / −$16). Spillover "3rd +25%" doesn't match beat 3's +17%. "+1,610 friendships" doesn't match "New connections +136". Local economy $19.2M is really the $18.4M toll revenue (a transfer). "Crash costs · +107,735 VMT/day" and "Delay… +348 veh-h/day" show positive $ for positive bad quantities. There's jargon (WHO HEAT × VSL, logit consumer surplus, VMT). Copy/Close sit below the fold (the card scrolls: 985/766 px). | ✗ |

**Story verdict.** The numbers are internally summed correctly, but they don't tell one story. A judge sees a 2nd St promenade sold as the hero, then a toll plan that makes every income group poorer, presented as +$35M.

## 5. Visual polish and modernity

- The welcome card, tour bubbles, result card and info-view legends look modern: crisp type, consistent radius, calm navy glass.
- **Clutter after unlock:** a 6-stat top bar with clipped labels ("people in area to…", "cars movi…", "new ties / yr" cut by the City Value chip), a scorecard and feed stacked on the right, the legend on the left, and a 9-button dock. The map is about 45% of the screen.
- **The dock overlaps the clock panel:** the 10× button (x 314–352) sits under the dock (x 339+), and the "18:00 / 24:00" ticks are hidden.
- Stale content: the "Try it: Make a street car-free" panel stays after you've done it. The feed shows "Stuck on Mission Street… 08:15" at 12:40. The "Clementina St · car-free" pill shows in **Baseline**.
- Compare from the result card doesn't frame the edit: the divider lands right on 2nd St, the purple street isn't visible, and the card keeps covering the top.

## 6. Bugs

- The dock overlaps the clock (10× button, timeline ticks).
- Top-bar stat labels are clipped after unlock.
- Plan A is highlighted before any edit exists.
- Inlet pills are hidden under the legend, Try-it and scorecard panels.
- The edit pill is visible in the Baseline view.
- Pedestrianize stays active-highlighted alongside the Info views.
- A missed paint drag gives no feedback.
- Population scale jumps (≈12K → 312 walkers) when a free edit falls back to the estimate.
- Pitch action buttons are below the fold.
- Console: clean.

---

## P0

**P0-1. The demo's numbers contradict each other from beat 4 to the pitch.** These are the issues a judge will catch: ties per day vs per year; Grace vs Dev; Maria's connections 0 → 0; shop sales falling while Economy rises 15×; ties falling while Street life doubles; spillover 17% vs 25%; 136 vs 1,610 friendships; delay −11% vs drive time −3.5%; "who gains" all negative under +$35M.
*Fix:*
- Use **one unit per metric everywhere**: ties/day in the legend, the tile and the top bar, with the label "new ties / day".
- Make the caption name and the feed name come from the same meet event, and update Maria's "New connections" row when that event fires.
- Split the toll revenue out of "Local economy" into its own "City revenue (toll)" segment, so Economy tracks shop sales.
- Source the spillover % for both beat 3 and the pitch from the same scenario, or label them "2nd St only" vs "2nd St + AI plan".
- Show the AI card's "delay" and the pill's "drive time" as the same metric.
- Add one line in the pitch explaining the negative per-person values ("toll cost to commuters; offset by health benefits not counted per person").

**P0-2. The demo pitches a $5 Bay Bridge toll, not the 2nd St promenade.** It undercuts the onboarding's whole message ("What if 2nd Street belonged to people?"), and the AI answers "without slowing Bay Bridge traffic" with a bridge toll while admitting the model can't measure the bridge.
*Fix:* in snapshot mode, choose the pedestrian-only option (or 2nd St + alleys, no toll) as the AI's top pick. Title the pitch "2nd St promenade + SoMa alleys". Rewrite the AI answer in 2–3 plain sentences with rounded numbers (no "773.53 hours", no "rent pressure index +0.03").

## P1

**P1-1. Beat 1 opens on zeros.** 0 cars, 0 walkers and ▲0 at every inlet last about 9 s, under a caption about traffic "pouring in".
*Fix:* pre-roll the sim to about 07:30 before the first frame (as a-skyline did), or hide the stats until they're non-zero.

**P1-2. Unlocking dumps everything at once.** A clean 3-panel screen becomes a 6-stat bar, scorecard, feed, Pitch and 3 new tools in one frame. The demo unlocks everything at t = 0.
*Fix:* unlock in two steps. After the first edit, show the scorecard (collapsed to City Value plus the 5 tiles, no radar) and Compare. Unlock Density/Zoning/AI after the second edit or on "All tools". Keep the feed hidden until requested. Keep the top bar at 3 stats (cars, walking, City Value) and move "people in area", "cycling" and "ties" into the scorecard.

**P1-3. Free painting is too hard to hit at normal zoom, and a miss is silent.**
*Fix:*
- Raise the `edgeAt` start radius when the tool is `ped` (for example 14 → 30 m, scaled with camera distance).
- Show a hover highlight on the street under the cursor while Pedestrianize is active.
- When a drag starts off-street, show a toast: "Start your drag on a street; it will light up when you're on one".
- Keep the "Drag along 2nd St" glow pattern for any hovered street.

**P1-4. The free-edit fallback silently changes the world's scale.** Walkers ≈12K → 312, and people in area 271K → 32K. A "Nice!" card then reports 0 / 0% / +$152.
*Fix:* keep `DISPLAY_SCALE` constant between the engine snapshot and the estimate. When the estimate shows no meaningful effect, change the header to "Small change: Clementina St is a quiet alley", with a suggestion ("Try a busier street such as 2nd or Howard"). Make the "Estimate · engine offline" state visible in the result card itself, not only under the logo.

**P1-5. Nobody sees the faded edge or understands the inlets.**
*Fix:*
- Add an "Area" camera preset (or make Overview pull back) that frames the whole dashed boundary with the faded city around it, and use it in tour step 1 and demo beat 1.
- Brighten the boundary dash.
- Add to the legend: "🚆 BART exit · 🚗 road entry. Counts = people in ▲ / out ▼ so far today".
- Show ▼ on every inlet, or on none.
- Add every inlet pill's rect, and every side panel, to the label-avoidance list so no pill hides under the legend, Try-it or scorecard.

**P1-6. "1 dot = 6 people" (tooltip) vs "1 agent = 21 people" (pitch).** Also 186K commuters (caption) vs 271K people (top bar).
*Fix:* derive the tooltip text from `DISPLAY_SCALE`. Have the caption reuse the top-bar figure, or label the two distinctly ("186K commuters + 85K visitors").

**P1-7. The welcome footer says the numbers are "illustrative" while the header says "calibrated engine".**
*Fix:* in snapshot/engine mode, use "Results replayed from the calibrated simulation engine. Edits outside the demo use a quick estimate".

## P2

1. **The dock overlaps the clock panel** (10× button and 18:00/24:00 ticks hidden). *Fix:* shift the dock's left edge to ≥ the clock's right edge + 12 px, or shorten the clock card's speed group.
2. **Top-bar labels are clipped after unlock.** *Fix:* addressed by P1-2 (fewer stats), or give the stats `min-width: max-content`.
3. **Plan A is highlighted with no plan.** *Fix:* default to Baseline (or a neutral "Today") until the first edit, then auto-switch to Plan A with a short pulse.
4. **The step-3 tour bubble covers the 2nd St edit.** *Fix:* anchor the bubble below the result card and to its side, or pan the camera so the street sits in the lower third.
5. **Compare from the result card doesn't frame the change.** *Fix:* on `Compare before / after`, collapse the card and fly to the edit's midpoint, offsetting the camera so the edit sits right of the divider.
6. **Stale UI.** *Fix:* hide the "Try it" card after the first edit (or switch it to "Try another street / Ask the AI"). Hide the edit pill in Baseline. Drop feed posts older than about 2 simulated hours. Un-highlight Pedestrianize when an info view is active, or show both states in different styles.
7. **Pitch jargon and signs.** *Fix:* "Premature deaths avoided (walking & cycling)", "Commuters' time & money", "Fewer crashes (−107,735 vehicle-miles/day)", "Delay to buses & freight (+348 h/day)" in red as a cost. Pin Copy/Close in a sticky footer.
8. **Mobility +$25K with "drive time +1.2%"** reads as a mistake. *Fix:* add a sub-line ("fewer trips outweigh slower drives") or show its components on hover.
9. **Green cyclists are effectively invisible.** *Fix:* make bikes larger and a saturated green with a white outline, or drop "Green = cycling" from the first-run legend until cyclists can be seen.

---

## Keep

- The welcome card: the headline question, Watch / Change / See the result, and three clear choices.
- Tour step 2: the camera flies to 2nd St, the street glows, there's a "Drag along 2nd St" pill and a "Do it for me" escape, and the user does the edit themselves.
- The result card format: three big plain-language numbers, City Value, "Compare before / after" and "Try another change", with a tooltip on every number.
- Info-view legends that replace the colour legend, plus the Connections Baseline vs Plan A box.
- The "Engine snapshot" / "Estimate (engine offline)" honesty chip.
- The idea of progressive unlocking, with the toast and NEW badges (just stage it).
- Beat 3: the spillover label now sits on the Plan A side.
- Next ▸ commits every beat correctly, and the console is clean.
- The faded context city and entry-road dashes, once you can see them.

## Scores

- **First-time clarity: 7 / 10.** The welcome card and tour are excellent (9 on their own). Points come off for silent paint misses, the unlock dump, inlet/edge confusion and the scale jump on free edits.
- **Demo clarity: 5 / 10.** It plays smoothly and Next works, but it opens on zeros, beat 4 contradicts itself, and the AI/pitch story pivots to a toll that leaves every income group worse off. The figures don't agree across panels.
- **Visual polish: 7 / 10.** The onboarding surfaces are modern and calm. The post-unlock HUD is crowded: clipped stats, dock/clock overlap, pills under panels, stale cards.
