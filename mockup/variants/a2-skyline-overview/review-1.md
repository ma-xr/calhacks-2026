# Review 1: Skyline Overview (a2), first-time-user pass

Tested `index.html?snapshot` at 1280x800 in the in-app browser. I explored freely, made unaided edits (Folsom St, then 2nd St from the "What changed" suggestion), used info views, inlets, mini-map and Compare, ran the full demo once while watching, and ran it a second time pressing **Next** at every beat. The console stayed clean throughout: no errors or warnings.

## 1. First 10 seconds
- **The intro veil is excellent.** "What if 2nd Street belonged to people?", a two-sentence explanation, and two clear choices. Within about 5 seconds I knew this is a simulated SF weekday where I can change a street.
- **After "Explore on my own" the screen is busy.** I count 9 glass panels: top bar with 4 stats, City value, status strip, mini-map, 8 inlet badges, What changed, Scorecard, Radar, Feed/Inlets, time card, dock and camera chips. My eye went to the inlet badges in the middle of the map first, not the city.
- **"What changed: Nothing has changed yet · Try: make 2nd St car-free"** is the best single overview addition. It tells me what to do and where results will appear.
- **The header says Plan A** (and the status strip shows a "Plan A" pill) even though Plan A is identical to today. As a first-timer I didn't know what "Plan A" was.

## 2. First edit
- **The tool is discoverable.** The Pedestrianize dock button shows a hint toast, and hovering a street shows "Folsom Street · click or drag to make car-free". I made an edit unaided in about 20 seconds.
- **The 2nd St suggestion flies the camera to 2nd St and arms the tool, but doesn't mark the street.** I had to guess which road was 2nd St (it's partly hidden behind towers and runs under the dock). A normal drag only caught 3 of 14 segments.
- **After any edit that isn't in the snapshot (including a partial 2nd St), the whole app drops into toy mode.** P0, see below.
- **The "What changed" card itself reads well.** It shows a headline ("2nd St is car-free."), car trips, foot traffic, value, and a spillover line. Clicking a line flies to the edit and shows the "Folsom St · car-free" label. It works.

## 3. Clarity
- **Mini-map:** good orientation, with inlet counts and the camera frustum. But clicking it can push the city into a corner, where badges pile up behind the mini-map and status strip. A thin black diagonal line across its bottom-right is unexplained. The "Tie" legend label should be plural ("Ties").
- **Status strip** ("Plan A · Normal view · 08:17 Morning rush · Engine snapshot"): a useful one-glance summary. It overlaps the right column by 28 px. "Painting car-free streets" stays there after the edit is done, because the tool stays armed.
- **Info views and legends:** the Traffic legend card ("Info view · On", a gradient, and Free flow / Jammed) is clear, and the 8-tile picker is clean. Fine.
- **Inlets table:** a nice idea, but in practice it's invisible. Once "What changed" grows, the Feed/Inlets panel collapses to 3–20 px. Even in demo beat 1, which switches to the Inlets tab, only 2 of 8 rows show. The badges on the map are readable but big. They cover the "FINANCIAL DISTRICT" label (Montgomery badge, same pixel row), and toasts land on top of the I-80 and US-101 badges.
- **Faded city edge:** in Overview the context fades into a near-white haze. The simulated area reads as an island, which is good. But the dashed boundary is hard to see at the default angle, and the entry-road dashes don't visibly connect to the inlet badges, which float inside the area instead of at the edge.
- **Cars vs pedestrians vs bikes:** cyan vs amber is fine up close (SoMa cam). At Overview the dots are unreadable. Bikes (green) are never distinguishable, and the stat "walking + biking" merges them anyway.

## 4. Scripted demo, beat by beat
| Beat | What I saw | Story check |
|---|---|---|
| 1 Morning rush | "About 186K commuters (270,942 people)" + 8 inlets, then the Traffic view (red ramps) | Good. The Inlets tab is opened but the table is clipped to 2 rows. "What changed" still says "Try: make 2nd St…" during the demo |
| 2 Paint 2nd St | Brush animation, replanning progress "day 5/5", label | Good visual. Then the foot-traffic view |
| 3 Swipe | Split + "Spillover: 3rd +17%". What changed: −588 car trips/day, +24% foot traffic, **+$6.36M/yr**, avg drive +1.2% | Consistent with the scorecard (+$6.36M) |
| 4 Follow Maria | "**Maria still drives in under Plan A**… meets Dev P. … 14,140 agents." The inspector shows driving 8 → 9 min (red) | Undercuts the pitch: the hero is unaffected and slightly worse off. "14,140 agents" vs "270,942 people" vs "186K commuters" is never reconciled (the 1 agent = 21 people note only appears in the pitch footer) |
| 5 AI planner | 3 options; it applies "Clementina + Minna + Stevenson + **$5 I-80 charge**". Option 1 shows "+$22.3M/yr" next to "revenue −$19K/day" for a "boost small business" goal | The AI panel's bottom is hidden behind the time card (only 2 of 3 options visible). The applied option **replaces** 2nd St |
| 6 Pitch | "Street changes + congestion charge **+$35.1M/yr**". Mobility −$25.7M. **"Who gains": −$66 / −$70 / −$30 (everyone loses)**. Car trips −6,615 vs AI text "3,297 fewer car commuters". New connections +136 vs header +174/+140 | The story pivots from "2nd St belongs to people" to "alleys + bridge toll". 2nd St isn't in the final plan |

- **Next works at all 6 beats**, verified by clicking it every 2.5 s, and the end state commits correctly.
- **I-80 badge framing:** after the $5 charge the I-80 badge still shows only cumulative "▲ 24K ▼ 963". There's no "$5 charge" marker and no comparison against baseline. A judge can't see that the charge did anything at the bridge. Given that the AI itself says "the model does not report Bay Bridge traffic separately", the badge should not imply bridge-level precision.

## 5. Visual polish
- **The look is modern and coherent:** navy glass, crisp type, good icon dock, and the "What changed" plus status strip pattern. The sunny city with the white haze looks premium.
- **It's too dense at 1280x800.** The right column has 4 stacked cards (What changed, Scorecard with 6 tiles, Radar, Feed/Inlets) and overflows. The Scorecard and the Radar show the same five pillars twice. The top bar plus City value plus scorecard City value shows "$35.1M" three times.

## 6. Bugs
- **Right-column overflow:** the Feed/Inlets card collapses to 3–20 px and slides under the camera chips (feedbox y=745 h=20 vs cams y=744).
- **Status strip overlaps "What changed":** it spans x 298–980 while the right column starts at x 952, so the card title is clipped to "HAT CHANGED".
- **The pitch card is taller than the viewport** (scrollHeight 871 vs 766), so "Copy summary" and "Close" sit below the fold. Esc doesn't close it; only a backdrop click does.
- **The AI panel is clipped by the time card.**
- **Labels collide:** the Montgomery badge sits on "FINANCIAL DISTRICT", and toasts sit on the I-80/US-101 badges.
- **The edit label stays on the map in Baseline:** "Folsom St · car-free" is still drawn while viewing Baseline.
- **In toy mode, the "Market St (west)" inlet reads 0 / 0** on both badge and table.
- **The Pedestrianize tool stays armed after an edit,** so a second click on the map makes another edit by accident.

---

## P0
1. **Off-snapshot edits collapse the world.** Pedestrianizing Folsom, or a partial 2nd St, switches both scenarios to the toy model. "People in area today" drops from **270,942 to about 30,000**, cars moving from about 4,000 to about 100, and the status shows "Estimate (engine offline)". A judge's very first edit makes the sim look broken.
   **Fix:** in snapshot mode, keep the engine baseline and agents for the view, and only overlay the toy *delta* on the What-changed card and scorecard. Never re-seed the population. Rename the badge to "Quick estimate" and drop the word "offline". Also, snap any edit that touches ≥ 1 hero edge to the full snapshot 2nd St plan, with a toast saying "Snapped to the full 2nd St plan (engine result)".
2. **The suggested first action doesn't guarantee success.** **Fix:** make "Try: make 2nd St car-free" a one-click action that applies all 14 HERO_EDGES with the brush animation. Alternatively, pulse a dashed magenta outline along 2nd St with a "Drag along here" label until it's painted.
3. **The demo story contradicts itself.** The pitch is about the AI's alleys + toll plan; 2nd St disappears; "Who gains" is all negative; and Maria still drives.
   **Fix:** have the AI option be *added to* Plan A, keeping 2nd St and listing it first in What changed. Title the pitch "2nd St promenade + SoMa alleys". Rename "Who gains · per person" to "Cost per person / yr" or show net including health. In beat 4, pick an agent from the snapshot whose mode actually changes, or reword it to "Maria still drives, but 3rd St carries +17% and she loses 1 min, the trade-off".

## P1
4. **Right column overflow.** **Fix:** merge the Radar into the Scorecard as a toggle, or drop the Radar at heights under 900 px. Give `#right` `overflow:auto` with What changed capped at about 40% height, or make Feed/Inlets a collapsible tab in the bottom-right.
5. **The status strip overlaps the right column.** **Fix:** set `max-width: calc(100vw - 316px - 2*gutter - left column)` on `#status` and let it ellipsize the tool segment.
6. **Inlets table invisible in demo beat 1.** **Fix:** fixing #4 solves this. Otherwise, for beat 1, show the table as a floating card next to the caption.
7. **Number reconciliation.** **Fix:** add a one-line explainer under "people in area today", for example "14,140 agents × 21". Make the caption say "14,140 agents (≈ 297K people)". Use one "new ties/day" figure everywhere: header, pitch and AI.
8. **I-80 badge.** **Fix:** when a charge exists, add a "$5" chip to the I-80 badge and show "▲ in vs today" (for example "▲ 24K, −8% vs today") in Plan A. Mark it "≈ modelled" because the engine doesn't separate bridge traffic.
9. **The pitch card doesn't fit at 800 px.** **Fix:** use a two-column layout with tighter rows, or a sticky footer containing Copy and Close. Add Esc to close.
10. **The AI panel is clipped by the time card.** **Fix:** anchor `#ai` with `bottom: time-card height + 24px` and `max-height: calc(100vh - 200px); overflow:auto`.

## P2
11. **The default "Plan A" tab before any edit.** **Fix:** start on "Today" (Baseline). Auto-switch to Plan A on the first edit, with the pill animating "Plan A · 1 change".
12. **Label collisions.** **Fix:** run the same `fitInlets` collision pass on district labels, or hide district labels while badges are shown. Place toasts above the dock, offset from badges, or push badges aside while a toast is visible.
13. **Badges float inside the area.** **Fix:** pin each inlet badge on the boundary where its entry road crosses the dashed line, with a short leader to the accent dashes. That makes "traffic enters here" obvious.
14. **Weak boundary at the default camera.** **Fix:** raise the boundary glow opacity in Overview, or add a soft vignette outside the simulated area.
15. **Edit labels in Baseline.** **Fix:** hide or ghost edit labels when viewing Baseline.
16. **The tool stays armed.** **Fix:** return to Select after a click-edit (keep it armed only during a drag session), or show "Press V or Esc to stop painting" in the status strip.
17. **Agent legibility.** **Fix:** scale agent dots with camera distance. Either give bikes their own stat or drop "Bikes" from the legend.
18. **Mini-map details:** remove or explain the black diagonal line, pluralize "Ties", and clamp the camera target so the city stays centered after a mini-map click.

## Keep
- The intro veil copy and its two buttons.
- The "What changed" card: the empty state with a suggestion, the click-to-fly lines, and the spillover line.
- The status strip pattern (scenario · view · time · data source).
- The hover tooltip on streets ("Folsom Street · click or drag to make car-free").
- The replanning progress pill ("The swarm is replanning · day 5/5").
- The info-view legend card and the 8-tile Info views picker.
- Compare split with BASELINE / PLAN A tags.
- Robust demo plumbing: Next works at every beat, the end state commits, and the console stays clean.
- The AI option cards with honest caveats, and the pitch card content: value bar, approval bars, biggest value lines.

## Scores
- **First-time clarity: 6/10.** The intro and What changed are great, but the first unaided edit falls into toy mode and the population collapses.
- **Demo clarity: 6/10.** Beats 1–3 tell a clean, consistent story. Beats 4–6 contradict it (Maria still drives, 2nd St is dropped, "who gains" is negative, mismatched counts).
- **Visual polish: 7/10.** Modern and coherent, but the right column overflows and panels overlap at 1280x800.
