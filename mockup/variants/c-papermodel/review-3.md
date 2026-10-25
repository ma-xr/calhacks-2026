# Review 3 (final round): Variant C · Paper Model

**Method.** The built-in browser had reached its tab limit, and the existing tabs belong to other reviewers. So I ran my own headless Chrome (1280x800, SwiftShader) and drove it over CDP. I watched one full scripted demo with screenshots every 3–4 s, replayed steps 2 and 3, then explored freely: Today/Plan A, select and rezone a block, Density to 3×, Compare, an AI "why" question, and the pitch from the header.

**Timing caveat.** Headless frame rate is low, so the clock ran slower than it will on a laptop. I don't judge pacing in this review.

**Verdict.** The round-2 P0s are fixed. Midday now has cars (about 250–330 driving). The step 6 caption no longer covers the pitch. The AI options are all positive and plausible. Valuation is proportionate: the AI upzone adds +$0.80M and a 3× block adds +$0.64M, against +$4.57M for the promenade. What's left is mostly **numbers that contradict each other** across panels, plus a few leftover label glitches. **No P0s remain.**

---

## Round-2 fix verification

| # | Item | Status |
|---|---|---|
| N-1 | No cars at midday | **Fixed.** Steps 4–6 show "driving 250–340". Blue cars are visible in Maria, AI and revenue shots. |
| N-2 | Caption covers pitch headline | **Fixed.** The caption hides, and the eyebrow reads "Step 6 of 6 · Pitch to the Board…". |
| N-3 | Callouts poke out under the caption | **Fixed** in every demo frame I captured. |
| N-4 | View bar overlaps the legend when the inspector is open | **Fixed.** The bar moves to the top-left of the stage. See P2-4 for the placement. |
| N-5 | "2nd St · car-free" label in Today | **Fixed for Today, not for Compare.** See P1-3. |
| N-6 | AI option 3 negative / "Moscone" | **Fixed.** The options are +$801K, +$709K and +$79K ("Convert Hobart Building"). The active card scrolls into view. |
| N-7 | Valuation out of proportion | **Fixed.** The pitch arithmetic now reconciles: $44K/day × 250 days × 35% ≈ $3.85M against Economy +$3.88M. |
| N-8 | Connections hairball | **Partial.** The legend now says "+882 vs today" and explains bold vs faint. On screen it is still a city-wide purple tangle, and the bold arcs don't stand out. The count contradicts the pitch (P1-1). |
| N-9 | Maria tag and partner | **Fixed** (her lunch partner is pinned to Dev, and "Folsom Greens" replaces the real brand). A new timing issue remains (P2-2). |
| N-10 | Stale chips | **Fixed.** I saw no lingering chips in free play. |
| P2s | Speed pill, "no change", "+1 rezoned block", AI drawer size, overview agent size | **Fixed.** 300× is highlighted during step 1, "Delay per car trip: no change" appears, the title reads "+ 1 rezoned block", the drawer fits its content, and cars are readable at Overview. |
| P0-3 (r1) | "Traffic builds" is mostly green | **Still partial.** At 08:02 a few segments (the I-80 ramp and a couple of streets) are red, but most arterials are green. |

---

## P1

**P1-1 The "new connections" count disagrees between two screens.**
- The Connections legend (step 4) says **"+882 vs today"**.
- The pitch, about 10 s later, says **"New connections +258"**.
- The legend multiplies by SCALE (6 people per dot): `V.plan.newTies * SCALE`. The pitch uses raw `p.ties - b.ties`.
- +258 also equals the "Car trips −258" figure two rows above it, which looks fabricated to anyone who reads both.
- **Fix:** use one source and one unit for both. If the unit is people, scale the pitch row as well.

**P1-2 The live counters crash mid-demo.**
- In step 1 the bottom strip climbs to **driving 3,930 / walking 6,462** (08:02). One beat later, at 08:08 in Compare, it reads **852 / 2,346**. That is −78% cars and **−64% walkers**, right as the captions say "Walkers fill the new street".
- Cause: during step 1 at 300×, agents move at `AGENT_CAP` and pile up. The step 2 settle/jump then re-seeds the population at its "true" level of about 680 driving at 08:05.
- A judge watching the strip sees walking collapse after the car-free paint.
- **Fix option A:** run step 1 at a rate ≤ AGENT_CAP.
- **Fix option B:** re-seed (`jumpTo`) at the end of step 1, before the paint, so the drop happens off-camera.
- **Fix option C:** have the counters show `V.plan.active` × SCALE consistently with the jump state.

**P1-3 The Compare label sits on the Today side.**
- In demo step 3 the yellow **"2nd St · car-free"** pill renders entirely on the **TODAY** half (the split is at about 0.6–0.65 while the street is to its left). That repeats the N-5 contradiction at the exact moment the judge compares.
- In free play at split 0.5, the handle covers the pill ("2[⇆] car-free").
- **Fix:** in Compare, project the label and show it only if its screen x is greater than the split x, or pin it to the Plan A half (for example "Plan A: 2nd St car-free" under the PLAN A tag). Also offset it so it never sits under the handle.

---

## P2 (top 5)

1. **"What changed · no changes yet" next to +$4.6M.** After the demo is stopped in step 3, or a step is started from the sidebar, the note stays "no changes yet" while the four pillars show +$117K / +$968K / +$3.25M / +$235K. Call the settle-note update from `closeHeroNow()`/`afterSettle`.
2. **Maria's card and feed run ahead of the clock.** At 12:07 her card reads "12:15 Lunch at Folsom Greens". At 12:14 the feed shows "Maria O. 12:16 · Bumped into Dev". The timestamps are in the future. Show only events with t ≤ `ui.time`, or label them "later today".
3. **The pitch shows different totals from the header and strip.** The pitch opens at **+$5.38M** while the header still tweens at **+$5.31M** and the strip shows Health $375K vs the pitch's $388K. Snap `shown` to `target` before `openPitch()`. In free play the sheet also overflows (652/612 px), pushing "How we value this" below the fold.
4. **The View bar jumps to the top-left under the caption** whenever the AI drawer or Maria's card opens (demo steps 4–5). It no longer overlaps anything, but it floats mid-map and splits attention away from the caption. During the demo, hide the View bar entirely (the judge doesn't need presets), or dock it to the bottom-left of the drawer.
5. **AI copy bug.** "...so the average car trip changed by **no change**." Use "...so the average car trip was unchanged."
   - "Who gains" values of **+$10 / +$6 / −$4 per person per year** (demo run) undercut a +$5.38M headline, and the red −$4 for the upper third draws the eye.
   - Show per-tier totals ($/yr for each group), or drop the row from the pitch.

---

## Keep
- The demo layout with the bottom metrics strip.
- The 2nd St paint brush and yellow street.
- The 300× pill that tells the truth.
- Maria's dark name tag over the yellow street, and her compact card ("Car → BART + walk").
- AI drawer cards with "delay no change · bridge approach unchanged" and a clear first-choice outline.
- The pitch card: it can be closed, the eyebrow shows the step, and the numbers reconcile.
- The free-play inspector (Today vs Plan A jobs and residents, zoning chips, density slider) is clean and immediately understandable.

## Scores
- **Demo clarity: 8 / 10.** The story, the car/walker visuals and the money now line up across steps 1–6, and a judge gets it within one caption. It loses points for the counter crash between steps 2 and 3, the +882 vs +258 connections, and the Compare label on the wrong side.
- **Visual polish: 8 / 10.** The paper aesthetic is calm and consistent, with no card collisions in the demo frames. It loses points for the purple Connections tangle, the floating View bar, and the small tween and timestamp mismatches.
