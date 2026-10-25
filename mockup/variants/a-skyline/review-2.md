# Review 2: Variant A · Skyline

Reviewed at 1280x800 in my own built-in browser tab (the pane was hidden, so I stepped frames with `window.__bw.run()` in step with real time). I ran the scripted demo end to end three times: once straight through, once pressing **Next ▸** three times, and once to check peak traffic. I also explored freely: camera presets, all 8 info views, hover tips, Zoning tool and rezoning, the block and person inspectors, the AI panel and the pitch card. I changed no files. The console stayed clean throughout.

**Verdict:** a big step up from round 1. Most of the narrative contradictions are gone: Mobility is now positive, the AI option shows "drive time ±0%", car trips are green and scaled, and the spill shows as a %. Stale state is fixed, and the colour system finally separates agents from data. The demo still fails the 10-second test in two places. The **opening 6.5 seconds show an empty city** (0 cars, 0 walkers, every inlet at ▲0 ▼0). And **"Next ▸" skips the edit itself**, so a presenter who clicks it destroys the rest of the story. Peak-hour congestion is also still about 95% green.

---

## Fix verification (round-1 items)

| # | Round-1 finding | Status | Notes |
|---|---|---|---|
| 1 | Demo starts with stale feed/chips/metrics | **Fixed** | Feed cleared, metrics snapped, chips cleared. Minor: the scorecard prompt still says "…or press Play demo" while the demo plays (see N12). |
| 2 | Spillover label clipped off-screen | **Fixed** | "Spillover: 3rd Street +14% traffic" is inside the safe area. New overlap: the "2nd St · car-free" pill sits under the PLAN A tag (N10). |
| 3 | Beat 1 congestion not visible | **Not fixed** | At 07:46 in the demo (1,968 cars moving) the Traffic view is still about 95% green, the ramp is only yellow, and there is no red anywhere. Meanwhile the feed posts "Stuck on Market Street again", and Market is green. |
| 4 | Numbers contradict the narrative | **Fixed** (mostly) | Mobility +$98K (drive +0.5%, car trips −186). AI option 1 shows drive time ±0%. Pitch shows car trips −150 in green. Units are now consistent (% and ×SCALE). Remaining number problems are listed as N3 and N9. |
| 5 | "3-minute demo" / eight inlets | **Partially fixed** | The button says "1½ min" (it measured about 100–110 s here, so "2-min" is more honest). In free Overview all 8 inlets are on screen. In the demo's opening shot, Broadway · Columbus is edge-pinned under the caption, and **all counters read ▲0 ▼0** (N1). Two pairs of inlet pills overlap (N7). |
| 6 | Mode colours collide with data colours | **Fixed** | Zoning is now green/coral/slate/gold/lilac, umbrellas are red, Workplaces is slate blue, and Foot traffic runs white → amber → orange. The one leftover: a rezoned block renders pale pink, which matches no legend entry (N8). |
| 7 | No cars at midday | **Not fixed** | At 12:08–12:56 "cars moving" reads 30–78, against about 2,000 at peak (about 3%). Beats 4 and 5 still play out on empty streets. |
| 8 | Edits give little 3D feedback | **Partially fixed** | Painted roads get a purple outline, and the Zoning/Density tools auto-switch the info view. Rezoning to Mixed use turns the block pale salmon-pink, not gold (Mixed) and not purple (Your edits). I saw no height animation. |
| 9 | Settle chip never goes away | **Fixed** | It auto-dismisses after about 6 s and has a ×. New problem: its placement covers the map centre (N6). |
| 10 | Can't find Maria in beat 4 | **Partially fixed** | The "● Maria" pill exists, but it only appears once she starts walking (about 12:15+). For the first several seconds of beat 4 there is nothing in 3D, and the pill then lands on top of the "2nd St · car-free" pill. |
| 11 | Connections hairball, contradictory counts | **Partially fixed** | It now shows only new ties, plus a good legend (Baseline 5,916 · Plan A 6,162 +4.2%). At the demo's district camera it is still a dense pink tangle. The top bar says "0 new ties vs today" at 08:15 while the scorecard says "ties +246/day" (N9). |
| 12 | AI panel covers the scorecard, options cut off | **Partially fixed** | Docked left, and the scorecard stays visible. The demo flies to each option. The cards are not collapsed, so the third card ("Convert Moscone…") is clipped at the panel bottom, just above `#time`. Hovering an option outside the demo does not fly the camera. |
| 13 | Labels overlap the HUD | **Fixed** | Off-screen and under-HUD labels are edge-pinned. However, the pinned pills are an icon and an arrow only, with no name or count (N7). |
| 14 | Pitch hides the loss, jargon, wording | **Partially fixed** | The footnote is plain English. There are no negative pillars now. The title still says "+ 2 rezoned blocks" after the AI applied "Upzone **the** low-rise block" (2 buildings in blocks 206 and 208). "Hatched red = a cost" is explained but never shown. |
| 15 | Daypart truncated | **Fixed** | "Rush hour" fits. |
| 16 | "−$0" | **Fixed** | |
| 17 | Empty scorecard on first frame | **Fixed** | Shows the "No changes yet…" prompt. |
| 18 | "settled · 5 sim days" jargon | **Fixed** | "Plan A vs today · stable". |
| 19 | Overview button stays highlighted | **Fixed** | `.on` clears on custom fly-to. |
| 20 | No camera-control hint | **Fixed** | "Drag to pan · Right-drag to rotate · Scroll to zoom" shows for 12 s. |
| 21 | Shortcuts only in tooltips | **Fixed** | `<kbd>` V P D Z I C A on the dock. |
| 22 | Legend subtitles wrap | **Fixed** | |
| 23 | Revenue ramp lacks "per day" | **Fixed** | "−$6K/day … +$6K/day". |
| 24 | End toast hidden behind the pitch | **Fixed** | It shows after the pitch closes. It now sits on top of the US-101 and I-80 pills (N13). |
| 25 | Civic missing from the inspector | **Fixed** | Legend reads "Civic (fixed)". |

**Tally:** 15 fixed, 1 mostly fixed (4), 7 partially fixed, 2 not fixed (3, 7). All P2 items are fixed. Of the five P0s, 2 and 4 are fixed, 1 is fixed but still carries a stale copy line, 5 is partial, and 3 is not fixed.

---

## New findings

### P0: breaks the demo or the understanding

**N1. The opening shot is a dead city.** The demo calls `jumpTo(6:00)` and holds the Overview for 6.5 s at 300×, so the sim only reaches about 06:32. Throughout that hold, the top bar reads "0 cars moving · 0 walking" and **every inlet pill reads ▲ 0 ▼ 0**. Meanwhile the caption says "About 31,000 commuters arrive through eight inlets… Each inlet counts people in ▲ and out ▼". It is dawn, dim, and nothing moves. This is the judge's first impression.
*Fix:* start the demo at `jumpTo(7*60*60)` (07:00) and fly into Traffic at about 07:20, with the peak at 07:45–08:05. Or pre-warm the counters by starting at 06:50 at 600×. The inlet pills need visible four-digit counts before the caption mentions them.

**N2. "Next ▸" skips the edit and breaks every later beat.** Pressing Next during beat 2 or 3 throws `'skip'` out of the beat *before* `togglePed`/`settle` run. In my test, beat 4 then showed: 0 car-free edges, "No changes yet" on the scorecard, City value $0, **compare still on** (split handle visible), the **Pedestrianize tool still selected**, and Maria's inspector showing **Car → Car**. All of that sat under a caption saying she now takes BART down the car-free 2nd St. Presenters press Next under time pressure, so this will happen on stage.
*Fix:* give each beat a `finally`/"commit" step that applies its end state when skipped. For beat 2 that means painting all `HERO_EDGES`, calling `settle()` and setting the street pill. For beat 3 it means `setCompare(false)`. For beat 5 it means applying option 1. Also run `setTool('select'); setCompare(false); showChips('')` at the start of every beat.

**N3. Peak traffic is still green, so beat 1 has no payoff.** This is round-1 #3 again, re-measured during the live demo at 07:46. The ramp `clamp(d / 1.8)` still keeps nearly every link green, so "the bridge and freeway ramps fill up" shows as one yellow ramp.
*Fix:* compute colour from the per-edge *percentile* of `liveCong` at the current time (top 10% → red, next 15% → orange), or clamp at `d / 1.0`. Then frame the I-80 ramp and Harrison/Bryant at the centre of the shot. If neither is done, rewrite the caption to "…roads turn yellow as the bridge ramps fill up".

### P1: significant confusion or ugliness

**N4. "Cars moving" and "walking" collapse after every settle or time jump.** Just before the beat 2 settle the top bar reads 2,076 cars and 5,856 walkers. Right after it reads **408 cars and 2,040 walkers**, and stays there. That is the moment the caption says "walkers flood the new promenade". The same drop happens after `jumpTo`: 07:51 shows 300 cars versus 2,292 at 07:53 in a continuous run. The cause: `resetAgents()` keeps only trips with `time < t0 + dur*1.35`, but stepped agents slow to `v*0.3` in congestion and pile up, so the two counts differ by about 5×.
*Fix:* derive both top-bar stats from the trip schedule, not from the active-agent list. Count trips with `t0 ≤ now < t0 + expected congested duration`. Alternatively, have `resetAgents()` use the congested duration so the reset population matches the stepped population.

**N5. The citizen feed repeats one line.** During the morning, three to four consecutive posts read "Stuck on Market Street again. Two blocks in ten minutes." (Mei, Hana, Marco, Wei, Lena; only the street name changes). It looks canned, and it contradicts the green map.
*Fix:* rotate 5–6 templates per category. Allow one "stuck" post per street per hour, and only when that edge is actually orange or red.

**N6. The settle chip covers the subject of its own beat.** In beat 2, the "2ND ST · MARKET → FOLSOM / +97%" chip sits at top-centre right on top of the promenade while Foot traffic is shown. In free mode the "BLOCK EDIT" chip covers the edited block's surroundings in the same way.
*Fix:* dock chips directly under `#ctop` but to the *right* of the caption (or stacked into the left column under the legend card). Or shrink them to a single-row pill, "2nd St foot traffic **+97%** · car trips −186/day", and show the detail table on hover.

**N7. Inlet labels overlap each other, and pinned labels say nothing.** In Overview, Embarcadero/Montgomery and Powell/Market St overlap (measured rects intersect). Edge-pinned inlets collapse to an icon plus an arrow with no name and no count. In close-up beats there are four or five of these anonymous blue blobs down the left edge, which reads as clutter.
*Fix:* run a simple label-repulsion pass, or offset Montgomery up and Market St down by about 16 px with a leader line. For pinned pills show the short name and the ▲ count ("◂ Powell ▲3.5K"), or hide pinned inlets entirely during demo close-ups.

**N8. The rezoned block colour matches no legend entry.** After setting a block to Mixed use with the Zoning view on, it renders pale salmon-pink. Mixed is gold and "Your edits" is purple. The hover tip on the same building in Traffic view still says "Office · 70 m" (it reads `BLD[b].zone`, not the plan zone).
*Fix:* in the Zoning view paint edited blocks in their new zoning colour, with the purple edit outline the roads already use. Outside info views use the purple edit tint. Make the hover tip use `zoneOf(b, S[activeWorld()])`.

**N9. "New ties" means three different things.** The top bar shows a running count since midnight ("0" at 08:15, "+708" at 13:00). The scorecard shows "+246/day", then "+702/day". The pitch shows "New connections +702" next to "Chance encounters +14,831", which is unscaled (raw agent count) while ties are also unscaled but car trips are ×6.
*Fix:* rename the top-bar stat to "new ties so far today". Apply SCALE to encounters and ties consistently, or drop "Chance encounters" from the pitch, since it is a large unexplained number.

**N10. The pills stack on top of each other in beat 3 and beat 4.** "2nd St · car-free" is hidden behind the PLAN A compare tag. In beat 4 the "● Maria" pill sits on the street pill ("2nd St · ca[Maria]").
*Fix:* include `#tag-l/#tag-r` in `hudRects()`. Give the follow label priority and hide the street label while following.

**N11. Landmark zoning is wrong.** Hover tips read "Yerba Buena Center for the Arts · Residential" and "San Francisco Museum of Modern Art · Residential". SF judges will notice.
*Fix:* when the OSM `tourism`/`amenity`/`building` tags indicate museum, arts centre, convention centre, school or government, force zone = civic. At minimum, hard-map the named landmarks.

**N12. The block inspector and the AI panel run under the time panel.** After rezoning, the block inspector grows, and its zoning buttons and Density slider disappear behind `#time` (inspector bottom is about 700 px or more, and `#time` starts at 703 px). The AI panel ends at 700 px, so its third option needs scrolling.
*Fix:* give the left column `max-height: calc(100vh - 80px - 110px)` with internal scroll, or move `#time` above the dock row on the right. Collapse AI option cards to a single row (title plus three numbers).

### P2: polish

- **N13.** The end toast "Demo finished…" sits on top of the US-101 and I-80 pills. *Fix:* raise the toast above the dock (`bottom: 120px`) or add it to `hudRects()`.
- **N14.** The Mobility tile sub-line is truncated: "drive time +0.4% · ca…". The hidden half ("car trips −150") is exactly why Mobility is positive. *Fix:* split it into two lines, or shorten it to "−150 car trips · +0.4% drive".
- **N15.** Maria's diary lists future events (it shows "17:29 Walked back to the station" at 12:08), and her meeting time disagrees with the feed: the feed says "12:16 Bumped into Omar", the diary says "12:23 Ran into Omar". *Fix:* filter diary lines to `≤ ui.time`, and use the actual meet time (`mariaMet.t`) in both places.
- **N16.** "Lunch at Sweet greens" should be the real name, "Sweetgreen". Clean the POI names, or pick a cleaner hero café.
- **N17.** In the AI option copy, "Convert Moscone Convention Center West to housing · Uses vacant office floors" is wrong: Moscone West is a convention hall. *Fix:* pick a real office building, or reword to "Uses the underused upper halls".
- **N18.** AI option drive-time deltas show green for "+0.4%" (worse). *Fix:* colour any increase in drive time amber, and decreases green.
- **N19.** After one option is applied, the AI copy still says "three options" while only two are listed. *Fix:* generate the count from `opts.length`.
- **N20.** The scorecard prompt "…or press **Play demo**" shows during beat 1 while the demo plays. *Fix:* during the demo, show "Waiting for the first change…".
- **N21.** The Pitch footnote explains "Hatched red = a cost", but no hatched segment exists. *Fix:* show the sentence only when a negative pillar exists.
- **N22.** The Overview preset leaves about 25% of the frame as empty beige ground on the left and top. *Fix:* tighten `d` by about 10% and shift the target slightly NW, now that the inlets are edge-pinned anyway.
- **N23.** The "Spillover onto parallel streets: 3rd Street +14% traffic" row in the pitch wraps to two lines. *Fix:* widen the value column or shorten it to "3rd St +14%".

---

## Keep, this works

- Clean reset, feed ordering and chip auto-dismiss: the beat-1 → beat-2 handoff is now tidy.
- The colour system: cyan cars, amber walkers, purple edits, and data ramps that no longer collide.
- The beat-2 promenade close-up with red umbrellas, trees and walkers is the money shot.
- The Connections legend ("Bright arc = new tie only in Plan A / Faint = happens today too") and the Workplaces/Visits "Plan A vs baseline, whole area" footer are excellent explanatory patterns.
- The pitch numbers now add up: +$4.39M before the AI, plus +$6.91M from the AI option, equals +$11.3M. Approval bars and "Who gains" are readable.
- The AI panel docked left with the scorecard still visible, and option 1 at "drive time ±0%" matching the stated goal.
- The console is clean, and the page is 818 KB.

---

## Scores

- **Demo clarity: 6.5 / 10** (round 1 was about 4.5). The story is now coherent when it plays untouched. The dead opening (N1), the green "rush hour" (N3) and the fragile Next button (N2) keep it from being judge-proof.
- **Visual polish: 7 / 10.** The HUD and colour system are strong. The remaining roughness is overlapping pills, anonymous edge pins, the inspector running under the time panel, and repetitive feed copy.
