# Review 1: Variant C · Paper Model

Reviewed at 1280x800 in the built-in browser, in two passes: free exploration, and the full scripted demo plus steps 3 and 5 re-run from the story sidebar. No console errors in either pass. Screenshots were taken during the session; the ones referred to below are described inline.

**Verdict:** this is the calmest and most "explainable" variant so far. The intro, the numbered story sidebar and the step captions do exactly what a judge needs. But in its current state the demo **tells one story and shows another**: the numbers contradict the captions (the car-free plan adds car trips and delay, and the AI options all show red "delay +80–106%" for a goal of "without slowing Bay Bridge traffic"). Also, the 3D stage is only 56% of the screen and is crowded by floating cards. Fix the P0s and this is a strong demo.

---

## P0: breaks the demo or the understanding

### P0-1 The numbers contradict the story (pitch card, chips, pillars)
- Beat 3's caption says "Fewer cars come in…". Beat 6's pitch card lists **"Car trips into the area +138"** and **"Hours of traffic delay +1"**, the Mobility pillar is **"−$98K · delay +0.7% · car trips +138"**, and the chip reads **"Planner suggestion applied · Car trips per day +138 · now ride BART 0"**.
- After my own 2nd St paint the pillars read **"MOBILITY +$43K · delay +11%"** (more delay but positive value) and **"STREET LIFE −$55K · encounters −0.1%"**: closing a street to cars *lowered* street life. That contradicts beat 4's line "Car-free streets roughly double these encounters".
- **Fix:** make the scripted plan's outputs consistent with the narrative: car trips ↓ (about −150), BART ↑, delay small (+1–3%) and labelled as the trade-off. Applying the AI option (an upzone) must not cancel the car-trip reduction. Have the chip for a block edit show *its own* deltas (homes and jobs added), not the street's car-trip numbers. Clamp the "Street life" value so it is ≥ 0 when encounters rise, and drop "roughly double" unless the panel shows about +100% (it shows +19–28%).

### P0-2 The AI planner's options all show red "delay +106% / +80% / +90%"
- Goal typed in beat 5: "Boost small business in SoMa without slowing Bay Bridge traffic". Every option card shows a red delay of 80–106%, and option 3 is **"−$269K/yr"**. To a judge that reads as "the AI failed its own goal".
- **Fix:** script the three options so the recommended one (option 1) shows delay ≤ +2% in neutral grey and the others show plausible trade-offs, e.g. "+$1.2M/yr · delay +0.4% · bridge approach unchanged". Express delay as minutes per trip ("+0.3 min/trip"), not as a percentage of a tiny baseline.

### P0-3 The "Traffic builds" beat shows an all-green map
- Beat 1b, "Traffic builds on the SoMa arterials · Roads go from green to red as they jam": at 07:27–08:16 almost every road is green, with a few yellow ticks and no red. Compare in beat 3 is also all green on both halves, so the swipe shows two identical pictures and the spillover label ("Spillover: 1st Street +35 cars/hr") is the only difference.
- **Fix:** rescale the traffic ramp to the demo's actual range (normalize to the 90th-percentile road flow, so peak arterials such as Folsom, Harrison, the 1st St on-ramp and Bryant reach orange/red at 08:00), or hold beat 1b until the time when the arterials are red. In beat 3, use Foot traffic for the swipe (the visible difference is walkers on 2nd St), or make the spillover street visibly redder on the right.

### P0-4 The 3D stage is too small and is covered by floating cards
- At 1280x800 the stage is **716x648 px** (56% of the width) between a 244 px story column and a 272 px stats column. During beats, the caption (top), the chip ("2nd St · Market → Folsom", top right), the inspector/AI panel (left/right), the info legend (bottom left), the Key (bottom left) and the View bar (bottom right) all float over it. In beat 4 the Maria inspector covers about 40% of the map and the caption overlaps the inspector. In beat 5 the AI panel overlaps the caption, the View bar and the "2nd St · car-free" label.
- **Fix:** (a) during the demo, collapse the right column into a slim metrics strip (City value plus 4 pillar numbers) or put it under the story column, giving the stage about 950 px; (b) anchor only one floating card per corner: caption top-centre, info legend *above* the Key in one stacked bottom-left card, chip top right, inspector/AI as a right drawer that pushes the View bar left; (c) in beat 4, show a compact Maria card (name, mode change, one line) instead of the full inspector.

### P0-5 Five of the eight info views are below the fold
- `#story` has scrollHeight 788 vs 648 visible, so only **Traffic, Foot traffic, Workplaces** are visible. Residents is clipped, and Visits, Zoning, Connections and Revenue change are hidden. The brief's main "Cities: Skylines info views" feature is undiscoverable.
- **Fix:** move Info views to a horizontal icon bar along the bottom of the stage (Cities: Skylines style: 8 round icon buttons with a tooltip label), or a 2-column grid of compact tiles. Collapse the story list's sub-lines when no demo is running. Everything must fit in 648 px with no scroll.

---

## P1: significant confusion or ugliness

1. **Yellow means three different things.** The car-free street, the building selection highlight (the Moscone building turns flat yellow when clicked with Density) and the AI ghost preview (the 3rd St block turns yellow) all use the same yellow. A judge will think the block was made car-free. **Fix:** keep yellow only for car-free streets. Use an ink-blue outline or halo for selection and a hatched or dashed translucent white/blue for previews.
2. **The car-free street disappears in info views.** In beat 2b (Foot traffic) the yellow 2nd St is greyed out like everything else, so the edit the beat is about is invisible apart from the label. **Fix:** always draw edited streets (yellow) on top of the desaturated info view. Make it a rule: user edits are never desaturated.
3. **Cars still drive on the freshly painted street.** Right after painting, several blue cars sit on the yellow segment for the 5-day settle (seen in my free-play test). **Fix:** on `togglePed`, remove or fade out the cars on those edges immediately (puff), even before the settle finishes.
4. **The demo length is wrong.** The intro button says **"Play the 3-minute demo"**, but the run takes about **108 s**. Some beats are rushed (AI: 3 options previewed at 1.6 s each, with the typing in the tiny footer input), while beat 6 holds 9 s on a static card. **Fix:** relabel it "Play the 2-minute demo". Show the typed goal *in the caption or the AI panel header*, not only in the footer input, which sits out of the judge's eyeline. Give each AI option 2.5 s.
5. **Maria is not visible on the map.** In beat 4 the camera "follows" her, but there is no marker, so a judge can't tell which dot is Maria. **Fix:** give the followed agent a pin with a name tag ("Maria"), a 2× scale and a pulsing ring, and draw her trail in her mode color.
6. **Inlet callouts are hidden by the cards.** In the Overview, the info legend covers **US-101** and **FOLSOM · 6TH ST**. Top-down clips **BROADWAY · COLUMBUS** off the top edge and US-101 overlaps the View bar. During captions, the callouts behind the caption peek out as fragments ("▲ 572", "BART"). **Fix:** cull or fade the callouts whose screen rect intersects a floating card or the stage edge, or clamp them inside a safe area. Shrink them to a one-line pill: "BART Powell ▲2.1k ▼144".
7. **The pitch card's buttons are off-screen and it hides the step 6 caption.** `.sheet.pitch` has scrollHeight 682 vs 612 visible, so **"Close"** and **"Copy summary"** sit below the fold. The pitch veil also covers the beat 6 caption, and the "Demo finished…" toast fires behind the veil (z-index 6 vs 10), so nobody sees it. **Fix:** add a top-right × to the sheet, drop the "Valuation…" footnote into a collapsible "How we value this", and close Escape/click-outside. Fire the end toast after closing the pitch, or raise its z-index.
8. **The citizen feed is not reset between runs and goes out of time order.** At 07:04 in step 1 the feed shows "Elena H. 09:10 driving · Stuck on Market Street…". At 08:22 it shows "Planner 12:36 · Applied: Upzone…", and that Planner post appears twice. **Fix:** clear the feed in `resetPlan()`/`runDemo()`, and drop posts whose timestamp is later than `ui.time` after a jump.
9. **City value counts down when the demo restarts.** Starting the demo after edits shows "+$4.42M" and coloured pillars over the step 1 caption for about 2 s while they animate to $0, and the stale "settled · 5 days" note remains. **Fix:** snap the shown values to the target on reset (no tween) and set the note to "no changes yet".
10. **Density gives jarring numbers.** Dragging one building to 3× moves City value from +$265K to **+$7.56M**, and the chip label "Block edit" shows "Foot traffic on edited streets +508%". The big numbers dwarf the 2nd St story. **Fix:** dampen the valuation per block and show block-relevant chip rows ("+514 homes · +1,199 jobs · +$X/yr").
11. **The Connections view is nearly invisible.** At 12:17 it shows faint purple wisps around FiDi in the overview. **Fix:** draw thicker, brighter arcs (2–3 px, opacity 0.8) and zoom to 2nd St for this beat instead of the full overview.
12. **Revenue change is empty when there are no edits.** The legend reads "−$1 / no change / $1" over an all-grey city. **Fix:** in the legend body show "No changes yet. Paint a street or rezone a block to see where money moves."

---

## P2: polish

1. **The radar is unreadable.** Its labels render at about **7.7 px** (12 px × 0.64 scale), and the legend "Today / Plan A" is smaller still. Either drop the radar (the 4 pillars already say it) or render it at ≥ 11 px effective.
2. **Pillar sub-lines are clipped.** "delay +0.7% · car trips +138" truncates to "car trips…" at 10 px. Wrap to two lines or shorten to "delay +1% · cars −150".
3. **The header tagline is truncated.** When City value grows (+$265K and up), "Modeling urban society with agent swar…" clips. Reserve a fixed width for the value or drop the tagline from the header after the intro.
4. **The stale hover tooltip remains.** "+$4K/day · block of 19 buildings · Mixed use" stayed on screen after leaving the info view and switching to Top-down. Hide `#tip` on `setInfo(null)` and on camera move.
5. **Compare side tags overlap the Key.** The "TODAY" tag at bottom-left sits under the Key card. Move the tags to the top of the stage, under the caption.
6. **Copy fixes:**
   - "Lunch at Sweet greens" uses a real brand misspelled; use a fictional café such as "Lunch at Folsom Greens".
   - "Minutes moving in area · Car 21 / BART + walk 22" shows Maria's commute getting *longer*; either own it ("+1 min, but $14/day saved on parking") or fix the numbers.
   - "Upper third −$0" should read "$0".
   - "1 agent = 6 people" and "settled · 5 days" are jargon. Use "each dot = 6 people" and "results after 5 simulated days".
   - "Pitch to the Board of Supervisors" is fine. "Projected approval" needs the source "(simulated survey of agents)".
7. **Pedestrian color.** Pedestrians are coral/vermilion (#f0532d), the same as the BART callouts and the Foot traffic ramp. Distinguishable from blue cars, so it works, but the caption calls them "Orange walkers". Shift to a warmer amber (#f59e0b), or change the copy to "coral".
8. **Agents are tiny at the Overview distance.** Cars and walkers are 1–2 px at the default camera. Scale agent size with camera distance (min 3 px on screen) so the judge sees "blue vs orange" on the first frame.
9. **The "+ Plan B" disabled button** looks like a broken control. Hide it or add a tooltip that shows on hover ("coming soon").
10. **The FiDi preset** looks into a wall of grey towers with no streets visible. Raise the polar angle (more top-down) or target Market St.

---

## Keep: this works
- **Intro sheet.** "What if *2nd Street* belonged to people?" with the yellow highlight, a 3-sentence explanation, a clear primary CTA and an inline color key. Best intro of the variants.
- **Story sidebar with numbered steps** plus the in-stage caption "Step 2 of 6 · Close 2nd St to cars", with Next and Exit. The judge always knows where they are, and any step can be replayed with one click.
- **Cars vs pedestrians up close.** Blue boxes vs coral spheres are unmistakable in the SoMa preset (see the 08:16 street screenshot).
- **Inlet callouts** with mode-colored headers ("EMBARCADERO BART ▲ 2,676 ▼ 120", "I-80 · BAY BRIDGE freeway ▲ 1,644 ▼ 0"). They are readable and clearly tied to the brief.
- **Info legends in plain language.** For example, "Where people are walking right now. Darker means more walkers." Info views desaturate the city properly, and Zoning, Workplaces and Revenue change look great (the green and red revenue towers around 2nd St are the money shot).
- **Hover on a block in an info view** ("+$4K/day · block of 19 buildings · Mixed use").
- **Settle feedback.** The "Agents replanning · day 2 of 5" chip, the puff on paint and the "2nd St · car-free" label.
- **The 2nd St paint brush animation** in beat 2, and the smooth fly-to camera moves.
- **"Right now" stats** (people here / driving / walking) colored by mode.
- **Pitch card structure:** headline value, a stacked bar by pillar, key changes, who gains, approval and trade-offs. Keep it; just fix the numbers (P0-1) and the close button (P1-7).
