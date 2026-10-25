# Review 1: Variant A1 · Skyline Clean

Reviewed at 1280x800 in my own built-in browser tab, at `index.html?snapshot`. I tried it as a first-time user: the intro, then "Explore on my own", painting 3rd St car-free, the info views, Baseline, the edge and inlets, Compare and the AI planner. I watched the scripted demo once in real time, from Play to the pitch, then stepped through all six beats with **Next ▸**. The console stayed empty the whole time, with no errors or warnings. The only file I changed is this one.

**Verdict:** the first 10 seconds and the HUD are now very good. The intro card answers *what is this* and *what can I do* in one glance, and the HUD is calm and consistent. Two problems hurt the story, though. (1) The first edit you make yourself turns the whole city into an "engine offline" estimate, and the city shrinks to about 1/8 of its people. (2) The demo opens with "What if 2nd Street belonged to people?" but ends with a pitch for a *different* plan, which also has a hidden $5 Bay Bridge toll. Several numbers in that pitch contradict each other.

---

## 1. First 10 seconds
- **Intro card (blurred city behind):** "What if 2nd Street belonged to people? A simulated weekday in San Francisco, where every dot is a person…", then two clear CTAs. Excellent. I knew right away what this is and what I could do.
- **After "Explore on my own":** a sunny 3D overview with 8 inlet pins, a top bar and a right-hand Impact panel that says "No changes yet. Make a street car-free…". It's obvious where to look: the Impact panel.
- **Confusing:**
  - The top-bar counters (`● 271K ● 4.0K ● 9.5K ● 0`) have no labels until you hover. The hover card is good, but **Cycling (650) is missing from the strip**.
  - **Plan A** is the active tab even though you haven't changed anything.
  - Inlet pins show only `▲ 5.4K`, with no name, unit or time window until you hover.
  - The clock moves fast: about 50 sim-minutes in roughly 30 s at 3×.

## 2. First edit, unaided
- **Yes, I managed it.** The dock icon expands to "Car-free street". A hint says "Drag along a street…", and hovering shows "3rd Street · click or drag to make car-free". The drag worked on the first try, and a purple "3rd St · car-free" pill appears.
- **The result reads badly** (see P0-1):
  - A "Estimating in the browser (engine offline) · day 5/5" chip appears, and the badge switches to an orange **Estimate**.
  - People drop from 271K to 33K, cars from 1,000 to 168, and walkers from 5.9K to 534. **This happens in Baseline too.**
  - The tiles say **Street life −$27K, "ties −12/day"** for a new pedestrian street, while foot traffic is +10%.
  - Back in Baseline, the big number shows $0, but the category tiles still show the Plan A values (−$96K, +$294K…). The "3rd St · car-free" pill also stays on the Baseline map.

## 3. Clarity
- **Info views and legends.** The 8-tile popover with "keys 1–8" is clean. Each legend card (top-left) has an icon, a one-line meaning and a gradient. Connections even shows Baseline vs Plan A per day. This is good.
- **Inlets and the faded city edge.**
  - The cyan dashed boundary reads well over the water.
  - On land, the faded context washes out into a white haze. In Overview it looks more like fog or unloaded tiles than "the city continues but isn't simulated". The entry-road dashes are thin and pale, and almost invisible next to the pins.
  - Nothing in the legend explains the boundary, the inlets, or the difference between the blue car pins and the amber BART pins.
  - ▲/▼ is explained only in the beat 1 caption.
- **Cars vs pedestrians vs bikes.**
  - Cyan vs amber works in close-ups of SoMa.
  - In FiDi, the towers hide most streets.
  - **Bikes use green (#29db85), the same hue as "Free flow" in the Traffic view and close to the trees and parks.** In Traffic view the bikes disappear.
  - At midday there are only about 100–300 cars on screen, so the streets look empty.

## 4. Scripted demo, beat by beat

| Beat | What you see | Numbers | Consistent? |
|---|---|---|---|
| 1 Morning rush | 07:34, inlets counting, then an 08:00 Traffic close-up with red Bay Bridge ramps | 271K people | Yes. Strong hook. |
| 2 Paint 2nd St | Foot-traffic view, red umbrellas, result pill | foot +24%, car trips −588/day, drive +0.3%, **+$6.36M/yr** | Mostly. Health (+$3.91M) is bigger than Economy (+$1.29M) for a "business" street. |
| 3 Swipe | BASELINE / PLAN A split, "Spillover: 3rd St +17% traffic" on the Plan A side | — | Yes. The old spill-label bug is fixed. |
| 4 Follow Maria | Maria card: Car→Car, driving 8→**9 (red)**, "10:22 Drove in", then Connections 12,427 → 12,664 (+1.9%) | — | Honest ("one street doesn't flip every commute"), but the hero's only visible change is a minute *worse*. "Drove in at 10:22" is odd for a commuter. |
| 5 AI planner | 3 options. ★ "Clementina + Minna + Stevenson with $5 …" (truncated). Applied: "Minna St + 2 more · car-free" | **+$35.1M**, Mobility **−$25.7M** with delay **−774 veh-h**, Economy **+$19.2M** from revenue **+$10K/day**, car trips **−6,615** | **No** (see P0-2 and P1-1) |
| 6 Pitch | "Minna + Stevenson + Clementina car-free + $5 I-80 charge, +$35.1M/yr" | see P1-1 | **No.** 2nd St is gone. |

Next ▸ works at every beat and lands each beat in a consistent state (I checked beats 1→6 in sequence).

---

## P0

**P0-1. Any edit you make yourself switches the whole world to the toy model and shrinks the city by about 8×, in both Baseline and Plan A.**
- In snapshot mode, an edit that isn't in the snapshot runs `useWorld(false)`, which swaps `S.base` *and* `S.plan` to `TOY`.
- On screen: people 271K → 33K, cars 1,000 → 168, walkers 5.9K → 534, and the inlet counts drop too. The UI says "engine offline", which sounds broken to a judge.
- This is the first thing a curious judge will try.

*Fix:*
- Keep `S.base` on `ENG.base` in estimate mode, and only estimate the *delta* for the plan. Scale `TOY.plan` to the engine's base totals (multiply by `ENG.base.m.people / TOY.base.m.people`) so the counters stay near 271K.
- Rename the chip to "Quick estimate · this street isn't pre-computed in the demo snapshot" and drop "offline".
- Optionally pre-compute 3rd, 4th, Howard and Folsom in the snapshot.

**P0-2. The demo pitches a different plan than the one it promised, and hides a toll.**
- The intro, beats 2–4 and the hero pill are all about 2nd Street. Beat 5's "Apply" **replaces** Plan A: `S.plan.ped` becomes only Stevenson, Minna and Clementina, and 2nd St is removed.
- The pitch title is "Minna + Stevenson + Clementina car-free + $5 I-80 charge". The map pill says only "Minna St + 2 more · car-free", and the AI option title is truncated at "$5 …". So the $18.4M congestion-charge line, which carries the score, is never shown on the map.

*Fix (pick one):*
- (a) Apply the AI option **on top of** 2nd St, and title the pitch "2nd St promenade + SoMa alleys + $5 I-80 charge".
- (b) Have the demo AI pick an option without a toll, and keep the pitch about 2nd St.

Either way, label the toll in the edit pill ("+ $5 Bay Bridge charge"), and never truncate it in the option title. Wrap it onto 2 lines instead.

## P1

**P1-1. The pitch numbers contradict each other.** A sharp judge will spot each of these:
- **Economy +$19.2M from "revenue +$10K/day".** $10K × 250 days is about $2.5M. In beat 2, +$18K/day gave $1.29M. *Fix:* show the components that make up Economy (revenue plus rent and land value, or whatever goes into it) in the tile sub-line and in "Biggest value lines". Or derive the sub-line from the same total.
- **Mobility −$25.7M while "Total traffic delay −774 veh-h" and drive time −0.6%.** The cost is the toll and the logit surplus, not delay. *Fix:* use the sub-line "toll −$74K/day · delay −774 veh-h", so the sign makes sense.
- **"Crash costs +107,735 VMT/day → +$5.39M"** and **"Delay to other traffic +348 veh-h/day → +$2.28M"** are positive values next to "up" quantities. *Fix:* sign the quantities as changes (−107,735 VMT, −348 veh-h) or label them "avoided".
- **"Who gains": every income third is negative (−$72/−$77/−$33),** yet Health is +$32.6M and the plan is "+$35.1M". *Fix:* add a line saying the net is driven by the toll transfer and health at city level. Or include the health value per person, so the rows aren't all red.
- **"Deaths averted per year +2.30" is listed under "Trade-offs".** *Fix:* move it to the benefits.
- **Spillover changes between beats:** "3rd St +17%" in beat 3 and "3rd +25%" in the pitch. *Fix:* use one source.

**P1-2. Free-mode result for a new pedestrian street: Street life −$27K, "ties −12/day".**
- This contradicts foot traffic +10% and the product's thesis.
- *Fix:* in the estimate model, don't let a closure cut ties below zero on the edited edge. Show "≈0" instead of a negative under $50K.

**P1-3. The Baseline view still shows Plan A values.**
- The big number reads $0, but the five tiles keep their Plan A values. The "3rd St · car-free" and "Minna St + 2 more" pills stay on the Baseline map.
- *Fix:* in Baseline, dim the tiles or show "—", and hide the edit pills (or show them as "planned" with a dashed outline).

**P1-4. Maria (beat 4) shows no visible benefit.**
- Car → Car, driving 8 → 9 in red, and nothing is drawn walking.
- *Fix:* replace the "Minutes driving" row with "Lunch walk on 2nd St: 11 min, car-free". Colour +1 minute neutral grey, not red. Start the beat at about 12:10, so her walk to Grace happens on camera.

**P1-5. The faded edge doesn't say "not simulated".**
- On land the context dissolves into a white haze, and the entry-road dashes are too faint to show where traffic enters.
- *Fix:*
  - Raise the context buildings' opacity or saturation a little for the first 200 m.
  - Thicken the accent dashes on the 8 inlet roads, and animate them toward each pin.
  - Add a legend entry "┅ Simulated area · ▲ in / ▼ out at entry points".
  - Show the inlet name next to the count by default in Overview (they're names only on hover today).

## P2
1. **Dock expansion overlaps the bottom-left legend.** With "Car-free street" open, "Your edits" is cut off ("Your ed"). *Fix:* include `#legends` in the dock's collision check, or move the legend above the dock row.
2. **The Info views popover covers the tool hint** ("Drag along a street to make it…" is clipped). *Fix:* hide `#toolhint` while `#infopop` is open.
3. **In Compare at Overview, the BASELINE tag sits on top of the bottom inlet pin (▲18K)**, and both halves look identical at that zoom. *Fix:* nudge the tags up 40 px. When Compare is turned on, fly to the edited street automatically.
4. **The edit pill clamps onto the legend** (FiDi camera: "Minna St + 2 more" sits on top of "Cars · Pedestrians"). *Fix:* add the legend to `hudRects()`.
5. **The AI panel covers inlet pins** (▲26K, ▲4.0K peek out from under it). *Fix:* hide pins under the HUD rects, or fade them.
6. **The AI input keeps a truncated demo prompt** ("…without slowing Bay"), and the bubble posts it truncated. *Fix:* clear `#ask-in` when the demo ends.
7. **Option copy is long and over-precise:** "delay rises 193.59 hours", plus a multi-sentence paragraph saying the plan "fails both the small-business goal and the no-slowdown goal". *Fix:* round to whole hours. Cap each option at 2 lines, plus a ✓/✗ for each goal.
8. **Bikes share the "free flow" green.** *Fix:* make bikes violet-blue or white with a dark ring, and keep green only for the traffic gradient.
9. **The counter strip has no Cycling entry, and Plan A is preselected with no edits.** *Fix:* add a green bike dot to the strip. Start on **Baseline**, and auto-switch to Plan A on the first edit.
10. **The hover tooltip on an already car-free street still says "click or drag to make car-free".** *Fix:* change it to "click to reopen to cars".
11. **The pitch card is taller than the 800 px viewport.** Close, Copy and the footnote are below the fold (scrollHeight 922 vs 768). *Fix:* use a two-column footer, or put Close in the header.
12. **The feed is sparse:** 2–3 posts after a full demo. *Fix:* seed 1–2 posts per beat.

---

## Keep
- The intro card: the headline question, a one-line explainer, and "Play the 2-minute demo" / "Explore on my own".
- The calm navy-glass HUD, with one top bar, one right panel and one dock, and consistent radii and type.
- The hover "Right now" card with labelled counts, and the street-name hover tooltip in the paint tool.
- The one-row result pill ("foot traffic +24% · car trips −588/day · drive time +0.3%").
- Info-view legend cards, especially Connections with its Baseline/Plan A per-day box.
- Beat 1: an 08:00 Traffic close-up with real red on the Bay Bridge ramps.
- The beat 3 swipe with BASELINE/PLAN A tags, and the spill label now on the Plan A side.
- Next ▸ at every beat. The civic-block zoning fix (buttons disabled for Civic). A clean console.

## Scores
- **First-time clarity: 7 / 10.** The intro and the paint tool are excellent. The first result is undermined by the "engine offline" estimate, the city shrinking, and negative Street life.
- **Demo clarity: 5.5 / 10.** Beats 1–3 are strong. Beat 5 swaps out the hero plan for a toll plan, and the pitch has several sign and scale contradictions.
- **Visual polish: 8 / 10.** Modern and calm. The leftovers are small collisions (dock/legend, pins under panels, Compare tag), a washed-out faded edge, and bike colour.
