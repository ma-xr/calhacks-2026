# Review 3 (final round): variant B · Night Ops

**Setup**
- Own tab in the built-in pane, 1280x800, running at about 120 fps.
- Watched the full demo once (94 s by `__demoLog`).
- Stepped through it with Next, including several restarts.
- About 6 minutes of free exploration: Pitch, rezone, Compare, a free AI question, hand-painting, Baseline, and the Zoning view.
- Root causes confirmed in `template.html`.

**Verdict:** this is now a solid stage demo.
- Every beat shows what its caption promises:
  - Traffic turns yellow and red, with jam callouts.
  - Maria is visible with a label and a trail in both shots.
  - The Connections arcs are readable, with no white blow-out.
  - The AI panel no longer collides with the caption.
- The pitch closes cleanly.

What's left is mostly trust in the numbers when a judge pokes at things, plus one stage-risk race.

## Round-2 fix check

| # | Status |
|---|---|
| N1 Pitch button showed `[object PointerEvent]` | **Fixed.** Clean card, and the valuation footer is back. |
| N2 Maria beat showed an empty office | **Fixed.** The 8:17 walk (8 s) and the 12:15 lunch meeting are both on screen, and the diary line appears. |
| N3 Spillover inflated | **Fixed.** Now "New Montgomery St +322 cars/hr" (aggregated per street, on a secondary street). |
| N4 Compare tags hidden under the caption | **Fixed.** The tags sit mid-stage beside the handle. |
| N5 Rezone deletes jobs yet adds money | **Partially fixed.** See P1-2. |
| N6 AI panel / caption collision; chip off-goal | **Fixed.** The panel is docked right and the caption is hidden. The chip reads "Local revenue +$10K/day · Bay Bridge delay ±0.0% · New homes +1,195". |
| N7 Compare opens at a 95/5 split | **Fixed** for the normal path (50/50). It can still happen through the race in P1-1. |
| N8 Bloom blow-outs | **Fixed** in Connections. |
| N9 Promenade blows out in close-ups | **Still blows out**, but it's livable. |
| N10 Feed empty for the first ~50 s | **Fixed.** Three seeded posts plus beat-triggered posts. |
| Commuter cars showed 0 at lunch | **Fixed.** The stat is now "Cars in area", showing 233 at lunch. |

## P0
None.

## P1

**1. Exiting the demo during a camera fly leaves stray state.**
- `endDemo()` calls `cancelFly()`, which ends the `while (fly)` loop in `flyWait` without checking the token. The rest of the beat then keeps running after the demo has stopped.
- Seen: clicking Exit as beat 3 started left Compare **on at a 95/5 split**, with tags overlapping as "BASELIN PLAN A", and the Foot view stuck on.
- The same race in beat 2 would leave the brush and the P tool active.
- It also adds about 1.3 s of lag to Next during flights.
- **Fix:** add `if (tok !== demoToken) throw 'stop';` after the loop in `flyWait`.

**2. The block inspector contradicts itself, and rezoning still mints money.**
- Yerba Buena Center for the Arts shows:
  - The subtitle reads "**today Residential**" (`zcat(b.use)`).
  - The zoning buttons highlight **Mixed use** (`b.k`).
  - The block has 3,337 jobs.
- Clicking "Residential" sets Jobs to **0** (an arts center loses all its jobs). Local economy still *rises* from +$3.09M to +$3.80M, and City value rises from +$4.04M to +$5.37M.
- **Fix:**
  - Use one source for "today" in both the subtitle and the highlighted button.
  - Make a same-category click a no-op.
  - Net lost worker spend against new resident spend, so that office → residential lands near neutral.

**3. Under "Who gains", everyone loses.**
- With only the promenade applied (manual Pitch), the card shows **+$4.04M/yr**, while "Who gains · per person per year" shows −$5 / −$5 / −$9 for all three income thirds.
- In the demo the AI upzone hides this, but a judge who paints a street and opens Pitch sees a plan worth $4M that harms everyone.
- **Fix:** include the street-life and health benefits in the per-person split. Or retitle the section "Change per person" and explain the sign.

**4. The spillover label never appears during the Compare beat.**
- The text exists ("Spillover: New Montgomery St +322 cars/hr · delay +2.5%"), but sampled every 250 ms it was hidden for 100% of beat 3.
- The cause: it sits around x≈478, inside the sweeping `#handle` keep-out zone, so `updateLabels()` hides it.
- The caption promises "a modest spillover" with nothing on the map to back it up.
- **Fix:** exempt `spill` from the handle zone, or anchor the label on the Plan A side, offset from the handle.

## P2 (top 5)

1. **The Pitch card overflows when the name wraps** ("2nd St + Kearny St + 5 more streets car-free + 1 rezoned block"). Copy and Close end up below the fold (card scrollHeight 665 vs 620), and **Esc doesn't close it**. Add an Esc handler and a sticky footer.
2. **Revenue beat:**
   - About half the blocks around the promenade are red, while the caption says "The gains follow the walkers". Add one clause such as "…and pull spending from nearby blocks".
   - The upzoned block's "RESIDENTIAL · 3.0×" badge sits clipped at the bottom edge, under the timeline.
   - The chip says "Local revenue +$10K/day", and 5 s later the pitch says "+$46K/day" with no hint that one is incremental. Label it "+$10K/day from this change".
3. **The Maria AM shot doesn't reach 2nd St.** In 8 s she covers about 4 sim minutes along Market/Mission, so the line "walks down car-free 2nd St" isn't shown. The diary also says "08:00" while the caption says "8:17". Start at `amT.t0 + 240` or run at 60×.
4. **After exiting mid-demo, the "2nd St · car-free" pill never comes back** (`streetLabel.hide` stays true). The Plan A "RESIDENTIAL" badge also shows in the Baseline world.
5. **A free AI question gets an off-topic answer.** Asking "Where should we add housing without more traffic?" returns the same Bay Bridge / small-business reasoning. At least echo the user's goal in the first line, e.g. "For your goal (housing, no more traffic)…".

## Scores

| | Score | Why |
|---|---|---|
| **Demo clarity** | **8 / 10** (r2: 7) | Every beat now shows its claim, and Maria finally lands. The AI and pitch beats make sense at a glance. It loses points for the invisible spillover, the "who gains" negatives and the inspector contradiction when a judge pokes. |
| **Visual polish** | **7.5 / 10** (r2: 6.5) | The overlaps are gone, Connections is readable, and the AI panel is docked. It loses points for the promenade white-out in close-ups, the clipped pitch footer, edge-clipped tags and badges, and the race-induced 95/5 Compare. |
