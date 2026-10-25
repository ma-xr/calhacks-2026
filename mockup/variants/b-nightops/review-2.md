# Review 2: variant B · Night Ops

Second-round review. The test is still whether a Cal Hacks judge can tell within about 10 seconds what they're looking at, what they can do, and what changed. The bar for polish is higher this time.

**How I tested.** The built-in browser pane had hit its tab cap, and every open tab belonged to another session. Instead I drove a separate headless Chrome 155 over CDP at a 1280x800 viewport (SwiftShader WebGL, about 4 fps).
- I watched the full scripted demo, which ran about 144 s at that frame rate. I also walked through the beats with Next.
- I tested free exploration: camera presets, painting Howard St by hand, Compare, the street, block and person inspectors, rezoning a block, a free AI question, and the Pitch card.
- I read `template.html` to confirm the root causes.
- The console showed no errors and the built page is 814 KB.
- Screenshots are in `/private/tmp/claude-501/-Users-maximilianthiersch-Projects-Cal-Hacks-13/ac7040a9-393e-47aa-8cf2-215d9477ba2e/scratchpad/rv2/shots/`.

Sim time moves with frame rate (`dt` is capped at 0.05 s), so I reasoned about real-time beat timing from the code as well as by watching it.

**Verdict:** a big step up. The city is busy from the first frame. The info bar is labeled. Edits are magenta and stand out from pedestrians. Painting a street by hand now feels great. The pitch is readable and ends cleanly.

Five problems remain:
- A glaring bug on the Pitch button.
- A Maria beat that still mostly shows an empty office.
- Spillover numbers that contradict the story.
- Compare labels hidden under the caption.
- A rezone that makes the city richer by deleting 5,000 jobs.

---

## 1. Fix verification (round-1 findings)

| # | Round-1 finding | Status | Evidence / remaining gap |
|---|---|---|---|
| 1 | Beat 1 opens on an empty city | **Fixed** | The intro and the demo both start at 07:15 with agents pre-warmed: 372 cars and 720 walking on the first caption frame. The cars/pedestrians caption holds for 6.5 s. |
| 2 | Traffic view doesn't support its caption | **Partially fixed** | Added: a rescaled ramp (`trafT` v/c 0.55 to 1.05), dimmed agents, 3 jam callouts, and an 8 s hold. At 07:25 the map is still about 85% green. The "MARKET ST · JAMMED" callout sits on a yellow segment and is clipped at the left stage edge. The beat shows traffic before the peak (08:20). |
| 3 | "Follow Maria" never shows Maria | **Partially fixed** | Added: a green marker, a "MARIA O." label, a green trail, and a diary filtered by clock. The beat still jumps to 12:11, while Maria stays in her office until her lunch trip at 12:15. At 60 fps she appears only about 8 s into a 12 s shot. At under 20 fps she never appears (my run). Her "Bumped into Marco" payoff posts at 12:16, during beat 5. See N2. |
| 4 | Beat 6 caption hidden behind pitch; demo ends under a modal | **Fixed** | The 6/6 copy now sits in the card's demo-note banner. `endDemo()` removes the pitch, and the "Demo finished…" toast shows. |
| 5 | "Next ▸" breaks pacing | **Fixed (minor edge case)** | Each beat calls `tidy()`, `ensureTime()` and `setRate()`. Edge case: Next pressed during a fly-to isn't handled until the next `wait()`. In beat 2 that aborts the brush stroke halfway through. See P2. |
| 6 | Too many orange tones | **Fixed (with new side-effects)** | Edits are hot magenta `#ff3fa4` and the promenade is a solid glowing band. Leftovers: stale "orange = Plan A" copy, magenta reused for all UI chrome, and the amber Residential zoning color. See P2. |
| 7 | Inlet tags collide with labels/HUD | **Partially fixed** | The keep-out zones and greedy de-overlap mostly work. Still seen: the Embarcadero tag clipped under the result chip ("EMBARCADER"), leader lines running under the caption, jam labels clipped at the stage edge, and Market St W / Folsom tags stacked 2 px apart. |
| 8 | Right column covers the action | **Partially fixed** | The caption is now a bottom-center lower third (max 560 px). The 320 px result chip still covers the north-east of the map, including the Embarcadero and Ferry Building. In beat 5 the AI panel and the caption overlap (N6). |
| 9 | Info-view bar icon-only | **Fixed** | Labels are always visible (Live · Traffic · Foot · Jobs · Homes · Visits · Zoning · Ties · Revenue) and hotkeys 0–8 show in the corner. |
| 10 | Zoning 84% "Mixed use" | **Fixed** | The map is a readable mix of office, residential and commercial. |
| 11 | Connections legend useless | **Fixed** | The legend has one entry, "Arc = two people who met today", and reads "6,156 ties/day (projected) · +240 vs baseline". |
| 12 | Rezone gives no 3D feedback / stale inspector | **Fixed** | The block flashes in its zoning color and keeps a "RESIDENTIAL · 3.0×" badge. The subtitle reads "Plan A: Residential (today Office)". The chip switches to Residents / Jobs. |
| 13 | Hand-painting 2nd St is hard | **Fixed** | The P tool auto-tilts the camera and the hovered segment pulses. Five coarse drag samples painted 9 contiguous Howard St segments. |
| 14 | Compare shows no difference / clipped tag | **Partially fixed** | Fixed: Compare forces the Foot view, and `#tag-r` is clamped with `nowrap`. Still broken: the split stays at 0.95 after the demo, so tags overlap as "BASELIN PLAN A" (N7). During beat 3 both tags are hidden under the caption (N4). |
| 15 | Beat 5 doesn't land | **Mostly fixed** | Fixed: the goal is typed into the AI panel, previews hold 2.5 s, and the camera flies to the revenue box. Remaining: the result chip omits revenue, the goal metric, and the caption covers the AI panel (N6). |
| 16 | Pitch name contradicts what was applied | **Fixed** | The name reads "2nd Street Promenade + 1 upzoned block". Key-change rows are colored good or bad. The lowest approval gets a "Why low:" line. |
| 17 | "3-minute demo" copy | **Fixed** | It now says "2-minute", and the code timing is about 95–100 s. |
| 18 | Tagline truncates in the top bar | **Fixed** | The tagline is removed from the bar. |
| 19 | "+$0" pillars before any edit | **Fixed (polish gap)** | The pillars show "—" and "make an edit to see impact". The hint truncates to "make an edit to see…", and the top bar reads "— /yr". |
| 20 | Jargon | **Fixed** | The UI now says "trips no longer made", "stable after 5 simulated days", "Agents re-planning… day 2 of 5", "Balance vs baseline" and "ALL". |
| 21 | "Cars moving 0" at lunch | **Not fixed** | The stat is renamed "Commuter cars" but still reads **0** from about 12:00 until the evening rush, and it still looks broken. |
| 22 | Repetitive feed / stale posts on restart | **Fixed (new gap)** | `runDemo()` clears the feed and duplicate posts are filtered. Now the feed stays empty for beats 1–3 (N10). |
| 23 | Cars render near-white in close-ups | **Likely fixed** | Cars read cyan in the beat 2 close-up. This is hard to judge under SwiftShader. |
| 24 | Workplaces ramp ≈ car cyan | **Fixed** | The ramp runs navy → blue → white-blue. |
| 25 | Visits uses a red ramp | **Fixed** | The ramp runs purple → gold. |
| 26 | Block tooltip lacks a street | **Fixed** | The tooltip reads "Block at …" and shows the Plan A delta. |
| 27 | Inlet counters not marked cumulative | **Fixed** | The tags show "TODAY". |
| 28 | "+ Plan B" noise | **Fixed** | The tab is removed. |

**Tally:** 19 fixed or likely fixed, 8 partially fixed, 1 not fixed. All five P0s were addressed, but #3 (Maria) still fails on stage.

---

## 2. New findings

### P0: breaks the demo or the understanding

**N1. The "Pitch to the Board" button shows `[object PointerEvent]`.**
- Location: `$('#pitch-btn').onclick = openPitch` passes the click event as `demoNote`.
- Every manual open shows a magenta banner reading "[object PointerEvent]" at the top of the card.
- The banner also hides the valuation footer (`.foot` is hidden whenever `demoNote` is truthy), so the methodology a judge asks about is gone.
- This is the button judges are most likely to click on their own.
- **Fix:** `$('#pitch-btn').onclick = () => openPitch();`. Also type-check: `if (typeof demoNote === 'string')`.

**N2. The Maria beat still shows an empty office for most of its length.**
- Maria's trips are: AM walk 08:17–08:26, lunch walk starting 12:15, arrival at Sweet greens 12:16.6.
- Beat 4 `jumpTo(731*60)` lands at 12:11 and flies to her office, where she is neither active nor dwelling, so `marker` and `followLabel` stay hidden.
- At 1×, real time vs sim time is roughly:
  - At 60 fps: the marker appears about 8 s in, the meeting happens about 11 s in, and the beat cuts to Connections about 1 s later.
  - At ~20 fps (a busy laptop or a projector): neither happens.
- The caption opens with "The green marker is Maria" over an empty street. The payoff post ("Bumped into Marco…") arrives in the feed during beat 5.
- **Fix:**
  - Start the beat at 12:14:30, or wait on **sim** time, not wall time: `while (ui.time < 737*60) await wait(50)`.
  - Better, tell the story the caption actually describes. Show her 08:17 walk down car-free 2nd St from Embarcadero at 1× (about 5 s), then `jumpTo(735*60)` for the lunch meet.
  - Hold 2 s after the meeting, with the inspector's new diary line highlighted.

### P1: significant confusion or wrong numbers

**N3. Spillover numbers are inflated and contradict the narrative.**
- On screen in beat 3 and the pitch: "Spillover: Hawthorne St +700 cars/hr · delay +4.3%".
- In the same model, the busiest 2nd St segment carried only about **205** cars/hr (agent flow × SCALE / 2.2).
- After also painting Howard St, the pitch reads "Mission Street **+1,405** cars/hr".
- Root cause: `displacedBackground()` adds every closed *segment's* background volume to the nearest parallel edge. Fourteen 2nd St segments all dump onto the same Hawthorne segment, so one corridor's through traffic is counted 14 times.
- This also contradicts the caption ("a modest spillover"), the chip ("Car trips/day −222") and the +4.3% delay.
- Hawthorne St is also a one-block alley, which isn't a credible "parallel street".
- **Fix:**
  - Aggregate per closed street: take the max segment volume per (closed street → target street) pair, not the sum.
  - Report spillover per target *street*. Expect roughly 100–250 cars/hr.
  - Prefer `primary` and `secondary` targets (3rd St, New Montgomery) over a `tertiary` alley.
  - Keep "+X cars/hr" and "delay +Y%" side by side only once they agree in scale.

**N4. During the Compare beat, BASELINE and PLAN A tags are hidden under the caption.**
- `.side-tag` is `bottom:46px; z-index:4`, and `#caption` is `bottom:46px; z-index:12`, so they occupy exactly the same strip.
- In beat 3 only a sliver ("BA…") peeks out. The beat that explains "what changed" has no on-map side labels.
- **Fix:** move the side tags to the top of the stage (`top:64px`, below the info bar) or above the caption (`bottom:190px`). Or put "◀ TODAY | PLAN A ▶" on the handle knob itself.

**N5. Rezoning an office block to residential makes the city richer by deleting 5,148 jobs.**
- Test: block near 611 Folsom, Office → Residential.
- Chip: Jobs −5,148, Residents +2,629.
- Results: Local economy jumps from +$3.96M to **+$8.78M**, revenue from +$45K/day to **+$100K/day**, and City value from +$4.48M to **+$10.8M**.
- Removing 5,000 lunchtime workers should *reduce* café and shop revenue. A judge who pokes at it will stop trusting every number.
- **Fix:**
  - Subtract the lost workers' weekday spend (lunch and coffee visits) before adding resident spend.
  - Weight resident spend toward evenings and weekends.
  - Sanity-check that office → residential at 1.0× lands near neutral revenue.

**N6. Beat 5: the AI panel and the caption collide, and the result omits the goal metric.**
- The caption (`z-index:12`, x 397–922) sits on top of the lower half of the AI panel (x 603–922). Option 2's APPLY button and the scan of options sit under it.
- After applying, the chip reads "Car trips −222 · now ride BART 216 · Residents +1,195 · Jobs −335 (red) · Traffic delay +4.3%".
- The goal was "Boost small business … without slowing Bay Bridge traffic", but neither revenue nor bridge delay appears. "Jobs −335" in red reads as a failure.
- **Fix:**
  - Hide the caption while `#ai` is open and put the beat text in the AI panel header. Or dock the caption left of the panel (`right: 344px`).
  - For AI applies, render a goal-specific chip: "Local revenue **+$16K/day** · Bay Bridge delay **±0.0%** · New homes +1,195".

**N7. Compare outside the demo opens at a 95/5 split, with overlapping tags.**
- `ui.split` keeps the demo's last value (0.95). Clicking Compare after the demo puts the handle at the far right, the Plan A side is a sliver, and the tags overlap as "BASELIN PLAN A".
- **Fix:** in `setCompare(true)` set `ui.split = .5` when not in the demo. Keep a minimum gap between `#tag-l` and `#tag-r`, or flip `#tag-l` left of the handle.

**N8. Bloom blow-outs.**
- In the Connections view (beat 4) the arcs converge into a large white hotspot under the caption, with no readable structure.
- In a SoMa close-up a square white blob, about 200 px, stayed on screen with pedestrians hidden.
- The square shape suggests NaN or Inf pixels fed into `UnrealBloomPass`. I saw it under SwiftShader, so verify it on the demo GPU.
- **Fix:**
  - Clamp additive alpha per arc and lower arc opacity where many arcs overlap.
  - Reduce bloom strength while `ui.info === 'ties'`.
  - Guard shader normalizations against zero-length vectors.
  - Clamp the composer output, e.g. `min(color, 4.0)` before bloom.

**N9. The 2nd St promenade blows out in close-ups.**
- In beats 2 and 4 and in the Maria close-up, the painted band plus the green trail saturate to white-pink. The trail and Maria's ring disappear into it.
- The "2nd St · car-free" pill is also partly covered by the person inspector ("t · car-free").
- **Fix:**
  - Lower the promenade emissive by about 40% when the camera distance is under 1,200.
  - Draw Maria's trail above the band (`depthTest:false`, `renderOrder` above the overlay).
  - Add the inspector to the label keep-out zones for street pills too, not only for inlet tags.

**N10. The citizen feed is empty for the first ~50 s of the demo.**
- `runDemo()` clears the feed. Ambient posts fire at most every 30 sim-minutes, and only if conditions match.
- Beats 2–3 run at 1×, so no posts appear.
- The largest right-column panel is an empty box until about 12:11.
- **Fix:**
  - Seed 2–3 morning posts at demo start.
  - Push scripted posts on beat events, e.g. after the paint: "Took BART in instead of driving today…" from a switcher, and "Walking 2nd St with tables in the street…".

### P2: polish

- **Stale copy:**
  - The POI inspector says "Grey = baseline, **orange** = Plan A", but the bars are magenta.
  - The CSS header comment still says "orange = your edits".
- **Magenta is overloaded.** "Your edits" magenta is also the Play/CTA buttons, the City value number, the radar polygon, the caption border, the selected-block highlight, the focus ring and the AI ✦. The legend's "Your edits" swatch loses meaning. **Fix:**
  - Make primary buttons and the caption border white or neutral.
  - Keep magenta for edits and Plan A only.
  - Use a separate outline style for "selected", e.g. a white rim.
- **Zoning colors.** Residential `#f0b44c` is the pedestrian amber, and Commercial `#ff7a45` sits next to it. **Fix:** Residential → `#e6d86a` (yellow-green), Commercial → `#ff6f91`, or another pair not used by agents.
- **Pillars panel:**
  - The "Pillars · Δ vs baseline" header wraps to two lines once "stable after 5 simulated days" appears.
  - The Mobility subline always truncates ("delay +4.3% · cars …").
  - The empty-state hint truncates.
  - **Fix:** shorten the note to "settled", let the sublines wrap to 2 lines, and use the shorter hint "edit to see".
- **Top bar.** "City value vs baseline — /yr" looks odd before the first edit. Hide "/yr" until there is a value.
- **Commuter cars 0** at lunch (carry-over #21). Show "cars in area" including midday and delivery traffic, or label it "commuter cars (rush hours)".
- **Equal values shown red.** The person inspector shows "Minutes moving in area 22 → 22" in red because `row()` compares unrounded values. Compare after formatting, or use an epsilon of 0.5.
- **Every person inspector uses Maria's green dot.** Use the agent's mode color for everyone else.
- **The "Stop demo" button keeps the ▶ icon.** Swap it to ■ while the demo runs.
- **Stale tooltip.** After a paint stroke the tooltip keeps saying "click or drag to make car-free" on the now-painted street until the mouse moves. Refresh it on pointerup.
- **Pitch naming.** A fully car-free Howard St is called "shared streets". Name the edits by street: "2nd St + Howard St Promenades + 1 rezoned block".
- **Jam callouts aren't clamped** and get cut at the stage edge ("· JAMMED"). Apply the same keep-out and clamp pass used for inlet tags.
- **Next during a fly-to** sets `skip`, which is consumed by the next `wait()` (e.g. mid brush stroke). In `flyWait`, check `skip` and call `cancelFly()`, then throw `'skip'`.
- **Pitch vs top bar mismatch.** The pitch shows +$6.01M while the top bar still animates at +$6.00M. Snap `shown.val = target.val` when the pitch opens.
- **Exit demo mid-beat** leaves that beat's info view on (e.g. Ties). Call `setInfo('none')` in `endDemo()` unless the beat was the last.
- **Inlet tags crowd the overview.** Seven boxed tags with leader lines are always on. When zoomed out, collapse them to a compact "▲ 7,158" chip with no title, or hide them in building-color info views, where they compete with the data.
- **Debug hook.** `__bw.run()` sets `last` to `performance.now()`, but the next rAF timestamp is earlier, so `dt` goes negative and sim time runs backwards (I saw 12:11 → 11:47). Use `const dt = clamp((now - last) / 1000, 0, .05)`.
- **Compare handle knob** covers the "2nd St · car-free" pill when centered on it. Add `#handle` to the keep-out zones.

---

## 3. Scores

| | Score | Why |
|---|---|---|
| **Demo clarity** | **7 / 10** (round 1: about 5) | It opens busy, the info views are labeled, the paint → foot traffic → chip sequence lands, and the pitch closes cleanly. It loses points for Maria's empty beat, Compare without side labels, spillover numbers that don't add up, and the `[object PointerEvent]` banner on the most-clicked button. |
| **Visual polish** | **6.5 / 10** | The palette, typography (Barlow Condensed with JetBrains Mono) and info-view desaturation look strong. It loses points for bloom blow-outs (Connections, promenade close-ups), panel overlaps (caption over AI panel, side tags and inlet tags under chips), truncated pillar text, and magenta overused as both data and chrome. |

**What gets this to 8+/10:** fix N1–N7. They're each small, mostly one-line or one-function changes. After that, the remaining issues are taste rather than trust.
