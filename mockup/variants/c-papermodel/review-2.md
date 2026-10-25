# Review 2: Variant C · Paper Model

Reviewed at 1280x800 in my own built-in browser tab. The pane was hidden, so I drove frames with a MessageChannel pump calling `__bw.run(1)` about 30 times a second, which gives close to real-time playback. I watched the full scripted demo, then replayed step 1 to see the Traffic beat. In free play I tested the Density edit, a "why" question and a goal question to the AI, Today/Plan A, Revenue change on Today, Compare, the Top-down and FiDi presets, Zoning and the pitch card. No console errors.

**Verdict:** a big step up. The story and the numbers now agree, the stage is about 1,020 px wide during the demo, all eight info views fit, and the selection and preview colors no longer clash with the car-free yellow. What's left is mostly about **what the judge sees in the second half of the demo**. Steps 4–6 run at midday, when the model has **zero cars**. The step 6 caption covers the pitch headline. The callouts still slip under the caption. On top of that, a few numbers and labels contradict each other.

---

## Fix verification

| # | Round-1 finding | Status | Evidence |
|---|---|---|---|
| P0-1 | Numbers contradict the story | **Fixed** | 2nd St chip: car trips −258, now ride BART 240, foot traffic on 2nd St +97%. Pitch: car trips −258, all four pillars positive. Applying the AI upzone keeps car trips at 0 change, and City value rises from $4.54M to $9.57M (+$5.03M, which matches the option's +$5.04M). "Roughly double" is gone. |
| P0-2 | AI options all show red delay | **Mostly fixed** | Delay is now in min/trip (+0.0 / −0.2 / −0.2) and each option says "bridge approach unchanged". The goal appears typed in the panel header. Option 3 still shows a red **−$409K/yr** (see N-6). |
| P0-3 | "Traffic builds" shows an all-green map | **Partially fixed** | At 08:07 the I-80 ramp and a few streets are orange/red, but most SoMa arterials are still green. In Compare (08:34) both halves are still mostly green, and the spillover label carries the whole difference. |
| P0-4 | Stage too small, covered by cards | **Fixed in demo, regressed in free play** | Demo mode folds the right column into a bottom metrics strip, so the stage is about 1,020 px. The legend is stacked above the Key, the AI panel is a right drawer, and Maria gets a compact card. In free play the View bar now overlaps the legend stack whenever an inspector is open (N-4). |
| P0-5 | Info views below the fold | **Fixed** | A 2-column grid with a gradient swatch per view. All eight fit with no scroll. Keys 1–8 work. |
| P1-1 | Yellow used for 3 meanings | **Fixed** | Selection is a translucent ink-blue and the AI preview is a hatched blue. Yellow is now only used for car-free streets. |
| P1-2 | Car-free street vanishes in info views | **Fixed** | 2nd St stays yellow on top of Foot traffic, Traffic, Connections and Revenue. |
| P1-3 | Cars drive on the freshly painted street | **Fixed** | `togglePed` removes the car agents on that edge, with a puff. |
| P1-4 | Demo length, typed goal, AI pacing | **Fixed** | The button says "2-minute demo" (the run is about 110 s), the goal is typed into the AI header, and each option is held for 2.5 s. |
| P1-5 | Maria not visible | **Mostly fixed** | A dark name tag reads "Maria · at work" / "Maria · at lunch". I did not see the pulse ring or a trail while she was dwelling. The tag sits on top of the "2nd St · car-free" label (N-9). |
| P1-6 | Inlet callouts hidden or fragmented | **Partially fixed** | They are now one-line pills ("BART MONTGOMERY ▲7.6k ▼1.2k") and are culled in close views. But the Montgomery pill still pokes out from under the caption's bottom edge in steps 2, 4 and 5 (N-3). |
| P1-7 | Pitch buttons off-screen, toast hidden | **Fixed, with a new overlap** | There is a ×, "How we value this" is a `<details>`, Escape and click-outside close it, the sheet fits (613/612 px), and the toast is at z 12 over the veil at z 10. However, the step 6 caption now covers the pitch title (N-2). |
| P1-8 | Feed not reset or out of order | **Fixed** | `resetPlan()` clears FEED. The order was correct across runs. |
| P1-9 | City value counts down on restart | **Fixed** | Values snap on reset, and the note reads "no changes yet". |
| P1-10 | Density gives jarring numbers | **Partially fixed** | The chip is now block-relevant (Residents +1,660, Jobs +3,237, Car trips 0). But one 5-building block at 2.8× adds **+$7.11M/yr**, more than the whole 2nd St promenade (+$4.5M). Valuation is not dampened (N-7). |
| P1-11 | Connections nearly invisible | **Fixed, new issue** | The arcs are now bold, but they form a city-wide purple hairball that does not point at 2nd St (N-8). |
| P1-12 | Revenue change empty with no edits | **Fixed** | The empty-state copy is present (`kind === 'div'` with no edits). The legend on the Today side explains "no change by definition". |
| P2-1 | Radar unreadable | **Fixed** | The radar was removed. |
| P2-2 | Pillar sub-lines clipped | **Fixed** | Example: "cars −258/day · spillover +4.8%" fits. |
| P2-3 | Tagline truncated | **Fixed** | Not truncated at +$11.7M at 1280 px. It does still truncate in the narrow layout. |
| P2-4 | Stale hover tooltip | **Fixed (code)** | The tooltip hides on pointerleave, on control start and in `setInfo`. |
| P2-5 | Compare tags overlap the Key | **Fixed** | The TODAY / PLAN A tags now sit at the top of the stage. |
| P2-6 | Copy fixes | **Partially fixed** | Done: "each dot = 6 people", the "(simulated survey of agents)" note, and the commute minutes are dropped. Not done: **"Lunch at Sweet greens"** still appears (it comes from the OSM POI name, so rename it in the template). "after 5 sim days" is still jargon. |
| P2-7 | Pedestrian colour vs "orange" copy | **Fixed** | The copy now says "Coral walkers". |
| P2-8 | Agents tiny at Overview | **Not fixed** | Agents are still 1–3 px at the Overview, which is the first frame of the demo. |
| P2-9 | "+ Plan B" disabled button | **Fixed** | The button was removed. |
| P2-10 | FiDi preset is a wall of towers | **Fixed** | Streets and 2nd St are now visible. |

---

## New findings

### P0

**N-1 Steps 4–6 play out on a city with no cars.** At 12:13–14:08 the bottom strip and the Right now panel read **"driving 0"**. I checked `V.plan.active` and `V.base.active` at 13:20: there are only `ped` agents, and none with mode `car`. Half the demo (Maria, Connections, AI, Revenue, pitch) shows a city with no cars at all, so the blue-vs-coral story vanishes. "Driving 0" next to "people here 34,014" reads as a bug. In the afternoon free play it gets worse ("walking 18").
*Fix:* add midday car trips (deliveries, ride-hail, errands, about 15–25% of the AM peak), or run steps 4–6 at about 08:45–09:30 instead of jumping to 12:06. If lunch is essential, run Maria at lunch but return to 17:00 for the AI and pitch beats, when the PM rush puts cars back on the map. At minimum, never show a literal "0": hide the driving stat when it is zero.

**N-2 The step 6 caption covers the pitch card's headline.** During "Pitch to the Board", the caption (z above the veil) sits on top of the sheet's eyebrow, the title "2nd Street Promenade + 2 rezoned buildings", the × and "Copy summary". The money shot of the demo opens with its title hidden for 7 s.
*Fix:* hide the caption while `#pitch` is open, and put "Step 6 of 6" into the pitch eyebrow. Alternatively, dock the caption to the bottom of the stage for step 6.

### P1

**N-3 Inlet callouts still collide with the caption.** "BART MONTGOMERY ▲3.5k ▼312" pokes out from the caption's bottom border in steps 2, 4 and 5. It looks like a rendering glitch.
*Fix:* add the caption rect (plus 8 px) to the callout cull or safe area. Callouts whose anchor is inside it should fade out instead of being clamped to its edge.

**N-4 The View bar overlaps the legend stack in free play.** With an inspector open, `#presets` moves to x 390–707 px and `#legstack` sits at x 263–525 px, both on the bottom row (y 680–713). "VIEW Overview FiDi…" is drawn over "Car-free street · New tie".
*Fix:* when the drawer opens, set the presets' right edge to `drawerLeft − 12px` and clamp their left edge to at least `legstack.right + 12px`. If there is no room, collapse the presets to an icon-only row.

**N-5 The "2nd St · car-free" label shows in the Today view.** After switching to Today, the yellow street correctly disappears, but the label stays on, which tells the judge that today's 2nd St is car-free.
*Fix:* hide `streetLabel` (and the spillover label) when `ui.view === 'base'`. In Compare, show it only on the Plan A half (or at the handle, labelled "Plan A only").

**N-6 AI option 3 contradicts the goal and the facts.** "Convert Moscone Convention Center West to housing · Uses vacant office floors" shows **−$409K/yr** in red with +5,233 residents. Moscone is a convention hall, not offices, and a red negative inside a list that "helps small businesses" makes the planner look careless. The hover cards for options 2 and 3 are also below the fold of the drawer (scrollHeight 917 vs 620), so the judge never sees which card is "being previewed".
*Fix:* pick an office building for option 3 (or rename it "Convert vacant offices on Howard St"). Make sure all three options are positive, with option 1 clearly the best. During the scripted hover, `scrollIntoView({block:'nearest'})` the active card, or show the options as a compact 3-row list (title + $/yr + one tag).

**N-7 Valuation scale is still out of proportion.** One block at 2.8× adds +$7.11M/yr, and the AI upzone adds +$5.04M, while the hero promenade adds +$4.54M. Local economy (+$6.79M) dominates the pitch, and Mobility is only +$117K for −258 car trips a day. The pitch also says "Local business revenue +$77K/day", which over 250 days is $19M of revenue. Without "35% value added" spelled out, that does not reconcile with +$6.79M.
*Fix:* dampen block-edit value (for example, apply new-homes value at about 25% and count only ground-floor retail). Target an order where the promenade is the largest single item. In the key changes table, label the revenue row "Local business revenue (35% counted as value)" so the arithmetic is visible.

**N-8 Connections is a hairball that does not support its caption.** The arcs span the whole map with no concentration around 2nd St, so "car-free streets add chance encounters, so more of these arcs form" cannot be seen.
*Fix:* show only the Plan-A-minus-today new ties (or color the extra ones brighter and draw the shared ties at 20% opacity), and limit the arcs to 2nd St ±300 m for this beat. Add a count to the legend: "+474 new connections vs today".

**N-9 Maria's tag sits on the street label, and her status contradicts the card.** At 12:13 the tag says "Maria · at work" while her card reads "12:15 Lunch at Sweet greens…". At 12:19 "Maria · at lunch" covers "2nd St · car-free". In free play the feed later says she bumped into **James**, while the demo said **Omar**.
*Fix:* offset the follow tag upward (or hide the street label while following). Derive the tag from the same event as the card. Pin Maria's lunch partner to Omar (seeded) so the story is the same on every run.

**N-10 Stale chips persist.** "2nd St · Market → Folsom" stays on screen when a block inspector opens, and "Block edit" stays after the inspector closes and through preset changes, sitting on landmark labels such as Transamerica Pyramid.
*Fix:* auto-dismiss chips after about 8 s, or when another inspector, chip or AI panel opens.

### P2

1. **Speed buttons lie in beat 1.** The demo runs at 300× while "10×" is highlighted. Show the actual rate ("fast-forward") or add a 60× / 300× pill during the demo.
2. **Inconsistent "+0.0 min/trip".** This appears on AI option 1, in the AI "why" answer and in the pitch. Write "no change" when |d| < 0.05.
3. **Pitch title says "2 rezoned buildings"** while the AI copy says "Upzone the low-rise block". Use "+ 1 rezoned block".
4. **Health is drawn in coral red** in the pitch stacked bar and legend (#f0532d), which reads as a negative next to the red "Drivers 37%" bar. Use a positive hue (teal) for Health and keep red for negatives only.
5. **Purple is overloaded.** Zoning "Mixed use", Connections arcs, Street life and "New tie" all use the same violet. Shift Mixed use to a muted plum or brown.
6. **Feed template repetition.** "Stuck on Stevenson Street again. Two blocks in ten minutes." appears three times in a row from different people. Vary the templates and dedupe by street.
7. **The AI drawer is mostly empty for a "why" answer.** The panel stretches the full stage height with one paragraph in it. Size it to its content, max-height to the stage.
8. **Overview agents are still tiny** (carried over from P2-8). The first frame should show blue vs coral at a glance: use a screen-space minimum of 3 px.
9. **Exit mid-demo leaves partial state** (2nd St closed, Foot traffic on, chip open) with no prompt. That is fine, but the toast should say "Demo stopped. Plan A keeps your changes. Press Today to compare."
10. **Narrow widths.** At about 570 px wide the header stacks and "+$11.7M" overflows its card. Not a judging-laptop scenario, but you should clamp the font size.

---

## Keep
- **Demo-mode layout.** The right column folds into a bottom strip of driving / walking / pillar values. It is the right call and the stage finally breathes.
- **The 2nd St chip** (−258 car trips · 240 now ride BART · +97% foot traffic) is the clearest "what changed" artifact in any variant.
- **Info views as a gradient-swatch grid.** It is discoverable, compact and on-brand. Zoning and Revenue change are beautiful.
- **The AI header showing the typed goal** and the hatched-blue preview block.
- **The pitch card.** It fits, can be closed, and has the methods in a disclosure.

---

## Scores
- **Demo clarity: 7 / 10.** Up from about 5. The narrative and numbers agree and the steps are legible. It loses points for the car-less second half, the hidden pitch headline and the Connections hairball.
- **Visual polish: 7 / 10.** The paper aesthetic is calm and consistent, and the typography and spacing are good. It loses points for card and callout collisions, color overloading (purple, red Health) and the stale chips and labels.
