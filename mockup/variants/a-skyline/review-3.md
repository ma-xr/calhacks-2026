# Review 3: Variant A · Skyline (final round)

Reviewed at 1280x800. The built-in browser pane had no free tab slot (tab cap reached), so I didn't touch the existing tabs. Instead I drove a separate headless Chrome through CDP at a true 1280x800 viewport. I watched the full demo once (about 100 s from Play to the pitch) and stepped through all six beats with **Next ▸**. I also explored freely for about 5 minutes: Select/inspector, rezoning, Pedestrianize painting, the AI question box and the Baseline tab. Finally I checked 17:30 traffic. I changed no files except this one.

**Verdict:** this is now a demo that works. The opening frame is alive (07:27, about 1,100 cars, inlets counting). Rush hour finally shows **real red** on the ramps, Howard and Folsom. Next ▸ commits each beat's end state. The pitch numbers add up. Most of what's left is beat 4 (nothing happens while you "follow Maria") and a few copy and logic contradictions that a sharp judge could catch.

---

## Round-2 fix verification

| Item | Status |
|---|---|
| N1 Dead opening shot | **Fixed.** Starts at 07:27 with live counts on every inlet (▲930, ▲1.4K…). |
| N2 Next skips the edit | **Fixed.** Skipping beat 2 still paints and settles 2nd St. Compare, tool and AI all reset at each beat. |
| N3 / R1-3 Rush hour is green | **Fixed.** 08:05 close-up shows red Bay Bridge/Fremont ramps and orange Harrison. 17:30 SoMa is heavily red. |
| N4 Agent counts collapse after settle | **Mostly fixed** in the demo (2,322 → 2,232 walkers across the settle). |
| N5 Repeated "Stuck on Market" posts | **Fixed** in the demo; the feed is sparse but varied. The template still appears once in free mode. |
| N6 Settle chip covers its subject | **Fixed.** Now a one-row pill under the caption. One leftover in beat 5 (P2-3 below). |
| N7 Inlet overlap / anonymous pins | **Fixed.** Pins show name + ▲ count. Market St/Powell pills touch in Overview but no longer overlap. |
| N8 Rezoned colour | **Not fixed.** The rezoned block keeps the pale-lilac selection tint, with no zoning colour or height change. |
| N9 "New ties" meanings | **Fixed.** "new ties so far today" vs "+246/day" now reads correctly. |
| N10 Pills stacking | **Fixed.** The Maria pill is clear of the street pill. |
| N11 Landmark zoning | **Fixed.** YBCA, SFMOMA and Moscone are Civic. (The regex also catches "Yerba Buena Lofts" and "Museum Parc Apartments", which is harmless.) |
| N12 Inspector/AI under #time | **Fixed.** Inspector bottom 688 < 703. AI cards collapse to one line except the hovered one. |
| N14 Mobility sub-line truncated | **Not fixed.** Still "−372 car trips · +0.3…" |
| N15 Maria diary future events | **Fixed**, but see P1-1: now the diary shows nothing beyond 08:00. |
| N17 Moscone-to-housing copy | **Fixed.** It's "Convert Hobart Building to housing". |
| N19 / N21 / N23 | N19 and N21 fixed. N23 still wraps ("New Montgomery St / +20%"). |
| Pitch "2 rezoned blocks" | **Fixed.** "+ 1 rezoned block". |
| Midday cars (R1-7) | **Improved, still thin.** About 270 cars at noon vs about 2,000 at peak. Acceptable now that the beat is about walking. |

---

## P0

None. The demo plays end to end, Next ▸ is safe, and no number on screen contradicts the main story.

## P1

**P1-1. Beat 4 "Follow Maria" is a still frame for about 10 seconds.** From 12:08 to 12:15 the "● Maria" pill and camera stay fixed over her office. She never walks down 2nd St on camera, and the meeting with Marco (12:16) fires *after* the view has already switched to Connections. Meanwhile the inspector shows **"Minutes moving 22 → 22" with the Plan A value in red**, which reads as "no change, and bad". The diary has only the 08:00 line. The caption promises "walks down the car-free 2nd St, and has lunch outside", and the judge sees none of it.
*Fix:* `jumpTo` about 12:12 (just before she leaves), or run beat 4 at 60–90× until `mariaMet`. Hold Connections until the meet event has posted. Colour equal values neutral (white), and make the Plan A minutes show her walking time (or replace the row with "Driving → 0 min").

**P1-2. The AI's second option pedestrianizes the street the demo just called the spillover.** Beat 3 labels "Spillover: New Montgomery St +20% traffic", and the pitch lists it as a trade-off. Thirty seconds later the AI suggests "Extend the promenade along New Montgomery St… It mostly carries walkers already, so the car impact is small · drive time −5.3%". Closing a street that just absorbed +20% traffic *speeds up* driving? A judge will notice.
*Fix:* exclude the `spill()` street from candidate options, or make that option's copy acknowledge it ("Also absorbs the 3rd St spillover…") and give it a realistic drive-time cost.

**P1-3. Civic ("fixed") blocks can be rezoned, and the inspector pre-selects the wrong zone.** Clicking Moscone Convention Center Ballroom shows "· Civic", yet the **Mixed use** button is highlighted as active, and clicking it does nothing (dead button). Clicking Residential converts the convention ballroom to 799 residents for **+$1.43M/yr**, even though the legend says "Civic (fixed)". The footer text "Office conversions assume vacant floors…" also shows for a civic building.
*Fix:* for civic blocks, disable the zoning buttons with the note "Civic buildings are fixed in this mockup", and highlight no zone. Show the office-vacancy note only for office blocks.

**P1-4. In the beat 3 swipe, the spillover label sits on the BASELINE half.** "Spillover: New Montgomery St +20% traffic" renders left of the divider (or split by it), right where the left side shows *today's* traffic. So the label points at the wrong world, and the street underneath looks the same on both sides.
*Fix:* anchor the label on the Plan A side (clamp `x > split`), or pick a camera where the spill street falls right of the 50% split. Pulse that street's segment so the +20% is visible.

**P1-5. The scorecard tiles show $0 while the sub-lines already show results.** During each "swarm is replanning · day n/5" phase, the tiles read "$0 / revenue +$41K/day / ties +246/day". In beat 5 the old $4.99M stays next to the new "ties +702/day". It's a 3-to-4-second flash of contradictory numbers at the very moment the presenter is talking about results.
*Fix:* update the sub-lines and the dollar values together, at settle end, or dim the whole tile with "replanning…" until both are ready.

## P2 (top 5)

1. **The Revenue view (beat 5) frames Yerba Buena Gardens, not the promenade.** The caption says "gains cluster along the promenade and the new mixed-use block", but 2nd St is off-frame top-right, and the most visible red blocks are at the top edge. *Fix:* frame the hero edge plus the upzoned block (midpoint, `d` about 1300).
2. **The free-form AI answer contradicts the chip.** It says "delay fell −18% on parallel streets", while the chip says drive time −4.5%. *Fix:* template the answer from `driveDelta()`.
3. **The beat 5 "AI suggestion applied" chip covers the "2nd St · car-free" pill**, which peeks out as "t · car-free". *Fix:* add `#chips` to `hudRects()`.
4. **Free-mode painting gives implausible results.** A short diagonal drag closed 4 small segments, labelled "Folsom St · car-free" on a N–S block. That edit scored Mobility **+$2.83M** with drive time −4.5%, more than the whole 2nd St promenade, and Street life showed a stray "**−$570**". *Fix:* cap the drive-time *improvement* from closures at 0, label by the dominant street, and round tiles under $1K to "$0".
5. **Mobility tile sub-line truncated; the pitch spillover row wraps.** It's still "−348 car trips · +0.2…" and "New Montgomery St / +20%". *Fix:* split the tile sub-line onto two lines. Shorten the pitch row to "New Montgomery +20%".

---

## Keep

- The opening at 07:27 with live inlet counts, then a hard cut to a red-ramp Traffic close-up. That is the 10-second hook now.
- The beat 2 promenade (purple edit edge, red umbrellas, walkers) and the one-row result pill ("foot traffic +98% · car trips −372/day · drive time +0.3%").
- Next ▸ commit logic: every beat lands in a consistent state.
- The AI panel: collapsed one-line options that expand on hover, "drive time ±0%" matching the goal, and the camera flying to each option.
- The pitch: +$11.9M = $309K + $1.95M + $8.25M + $1.40M. "1 rezoned block", plain-English footnote, honest trade-offs (drivers 41%, middle third −$27).
- 17:30 traffic reads instantly as rush hour.

## Scores

- **Demo clarity: 8 / 10** (round 2: 6.5). Hook, payoff and pitch all land. Beat 4's static Maria and the AI-vs-spillover contradiction are the only story-level dents.
- **Visual polish: 8 / 10** (round 2: 7). The HUD is clean and nothing overlaps HUD panels anymore. What's left: the spill label on the wrong half, the beat 5 chip over the pill, truncated sub-lines, and no visible rezone feedback.
