# Project Spec: **CommonGround**: modeling urban society with agent swarms

## Context
Cal Hacks project. An interactive 3D view of **FiDi + upper SoMa** where thousands of simple agents ("sims") live, commute, shop and meet. The user paints changes onto the city (pedestrianize a street, densify or rezone a block) and watches the city re-settle. They see, against a live baseline, what happened to traffic, street life, social ties, local business, health and the city's bottom line, and *who* won or lost.

Positioning: **"Cities: Skylines meets a real planning model."** It has the feel of a game and uses methods from MATSim, MIT CityScope and A/B Street, grounded in real SF data and USDOT valuation standards.

---

## 1. The demo (3 min). This drives every build decision
Anything that doesn't serve this script is secondary.

1. **Morning time-lapse**: from one cinematic fixed view, dawn turns to 8am. Cars pour off the **Bay Bridge / I-80 ramps**, and commuters stream up out of the **BART/Muni stations on Market**. Traffic builds on Mission and Howard.
2. **Paint a street car-free** (e.g. Montgomery or 2nd St): cars dissolve, people and café tables pop in, the soundscape shifts from traffic to chatter, the **evaporation counter** turns car trips into walkers, and City Value counts up.
3. **Swipe reveal**: drag a divider across the live city to show baseline vs. plan side by side. A congestion hotspot shifts slightly onto a parallel street, which is the honest trade-off.
4. **Follow Maria**: highlight one sim. Her trail lights up as she walks from Montgomery station instead of driving, meets a coworker at a plaza (a spark), and buys coffee. Then fade out to the citywide web of social ties.
5. **AI planner**: a judge types a goal ("boost small business in SoMa without slowing the Bay Bridge traffic"). The AI proposes three edits as ghost previews, and we apply one.
6. **Pitch card**: +$X M/yr, broken down by pillar, with winners and losers and stakeholder approval bars.

---

## 2. Core loop: what makes it cohesive
**Edit → Settle → Compare → Explain → Pitch**

1. **Edit:** paint a road or block. Changes snap in with sound and animation.
2. **Settle:** the city runs a few fast "replanning days" (MATSim-style). Sims reroute, switch to walking, or drop car trips entirely ("traffic evaporation").
3. **Compare:** baseline and plan run side by side, using a swipe divider. The radar chart shows the baseline as a ghost outline and the plan as a filled shape.
4. **Explain:** click a sim, shop or street to see *why* it changed. Ask the AI "why did revenue on 2nd St go up?"
5. **Pitch:** a scorecard with $ value, trade-offs, winners and losers, and approval by stakeholder group.

---

## 3. World and sims (modeling, high level)

### World
- **Area:** FiDi + the upper half of SoMa (roughly Market → Folsom, Embarcadero → about 5th St).
- **Look:** clearly recognizable SF. Real building footprints and heights (Salesforce Tower, Transamerica, the Market St canyon), real street grid, district identity. Stylized, not photoreal.
- **Single fixed camera angle** (oblique, cinematic) that looks very advanced: dynamic lighting, shadows, a day/night cycle, bloom on overlays, glowing trails.
- **Gateways that spawn and absorb sims:**
  - 1–2 highway entrances (I-80/Bay Bridge ramps around Fremont/1st/Harrison/Essex) spawn **cars**.
  - Existing **BART/Muni Metro stations** (Embarcadero, Montgomery, Powell) spawn **pedestrian commuters**. No new transit lines.
- **Blocks:** zoning (Residential / Office / Commercial / Mixed-use), density (height, which sets residents and jobs), businesses.
- **Roads:** car or pedestrian-only.
- **Places:** homes, workplaces, businesses, public spaces (plazas, POPOS, Rincon Park).

### Sims, each with a tiny brain
| Decision | Technique | Behavior that emerges |
|---|---|---|
| Daily schedule | Activity template (arrive → work → lunch → optional stops → leave/home), sampled times | Rush hours, lunch peaks (FiDi is office-heavy, so lunch matters a lot) |
| Mode / arrival | Logit model: car vs. transit-station vs. walk, based on time, parking cost and car ownership | Edits shift people from car to transit/walking |
| Route choice | Fastest path with a congestion curve (BPR) | Rerouting and spillover |
| Store choice | Huff/gravity model: attractiveness × distance, **plus walk-by exposure** | Foot traffic drives revenue. Walkers visit *more often* |
| Socializing | Co-presence at the same place and time, weighted by dwell time. Repeats strengthen ties | Plazas and pedestrian streets build social ties |

- Sim attributes: home (in area, or "commuter" from a gateway), job, income bracket, car ownership, preferences, social openness.
- **Scaled**: 1 sim = N people (shown in the UI).
- **Hybrid AI**: rules drive the crowd. An LLM only narrates (diaries, citizen posts, explanations, AI planner).
- **Calibrated to evidence:**
  - Traffic evaporation: about 10–15% of displaced car trips vanish or switch mode.
  - Car-free Market St: small spillover, about 4% on parallel streets.
  - Retail: walkers shop more often; cafés and restaurants gain most.
  - Rent pressure: shown as a real trade-off.

---

## 4. Interventions
| Tier | Edit | Effect |
|---|---|---|
| MVP | Pedestrianize road segment | Cars reroute or evaporate; walk-by exposure and encounters rise |
| MVP | Block density slider | More or fewer residents/jobs, so more trips and demand; building height animates |
| MVP | Block zoning | Changes which places exist, so trip origins and destinations shift (e.g. office → residential conversion, a hot real-world FiDi topic) |
| Strong | **Policy Book** (city-wide levers): congestion pricing, parking removal, corridor upzoning | Each lever shows ± chips for what it helps and hurts |

---

## 5. Metrics: 4 pillars (radar axes and City Value components)
Every metric is shown as **baseline → plan (Δ)** and can be broken down **by income tier** (equity).

| Pillar | Metrics | How it's valued in $ |
|---|---|---|
| **Mobility** | Person-hours of delay, VMT, mode share (car / transit / walk), evaporated trips, gateway throughput | USDOT value of travel time (about $19–20/hr; walk and wait time ×2); vehicle operating cost |
| **Street life & social** | Pedestrian flow per street, dwell time in public space, encounters/capita, new connections, strong ties, income-mixing index, Jane Jacobs vitality score | Wellbeing value of social ties (adjustable) |
| **Local economy** | Visits and revenue per business, Δ revenue by category, boom/bust hotspots, sales tax, land-value uplift, jobs-housing balance | Revenue + city sales-tax share + property-tax proxy |
| **Health** | Active minutes walked/person | WHO HEAT method × value of statistical life |
| *Access (cross-cutting)* | 15-minute-city score for residents | Shown, not monetized |

**City Value** = Σ pillar $ per year. Shown as a stacked bar with adjustable weights and visible assumptions.
**Honest trade-offs:** rent pressure and spillover congestion.

---

## 6. Function sheet

### User functions
| # | Function | Tier |
|---|---|---|
| U1 | **Fixed cinematic view** of FiDi + SoMa with hover/click selection; high-end rendering (lighting, shadows, day/night, glow) | MVP |
| U2 | Time controls: play/pause/speed, 24h scrubber with fading trip trails | MVP |
| U3 | Pedestrianize road (paint along a street) | MVP |
| U4 | Set block density (building grows/shrinks) | MVP |
| U5 | Set block zoning | MVP |
| U6 | Undo / reset | MVP |
| U7 | **Overlay layers**: traffic, foot traffic, social sparks, business Δ. City greys out and the chosen metric glows | MVP (traffic, foot traffic, business), Strong (social) |
| U8 | Metrics dashboard + radar chart (ghost baseline vs. plan, animates live) | MVP |
| U9 | City Value panel with stacked breakdown and weight sliders | MVP |
| U10 | **Compare swipe**: baseline vs. plan split across the live view | Strong |
| U11 | Scenario tabs: Baseline / Plan A / Plan B | Strong |
| U12 | Inspect sim: profile, trips, friends, **highlight + trail** ("Follow"), AI diary | Strong |
| U13 | Inspect business: visits, revenue Δ, hourly busy bars (baseline vs. plan), customer-origin arcs | Strong |
| U14 | Inspect street/block: flows, "where did the traffic go" diversion view | Strong |
| U15 | Citizen feed: posts from sims reacting to changes; click to highlight that sim | Strong |
| U16 | Equity view: winners/losers by income tier | Strong |
| U17 | **Pitch to the Board** scorecard with stakeholder approval bars | Strong (demo-critical) |
| U18 | **AI planner**: type a goal, get ghost-preview edits with trade-offs | Stretch (demo-critical wow) |
| U19 | Policy Book, guided challenges, soundscape | Stretch |

### System functions
| # | Function |
|---|---|
| S1 | Load city: roads (OSM), building footprints and heights + zoning (DataSF), businesses (Google Maps data via Apify) |
| S2 | Generate population: residents from block density; commuters from LODES flows, split across highway gateways and transit stations |
| S3 | Plan day per sim |
| S4 | Mode + route choice (logit, congestion-aware) |
| S5 | Move agents; congestion per road; spawn/absorb at gateways |
| S6 | Store choice (Huff + walk-by exposure) and revenue |
| S7 | Encounter detection + tie strengthening |
| S8 | Apply edit, then run N fast replanning days until things settle |
| S9 | Baseline runs in parallel (same seed) for deltas |
| S10 | Metrics aggregation per tick / day, by place and income tier |
| S11 | Value engine: metrics → $ via a configurable factor table |
| S12 | Narrative layer (LLM): diaries, citizen posts, explanations, AI planner |

---

## 7. User experience

### Layout
```
┌───────────────────────────────────────────────────────────────┐
│ [Baseline | Plan A | Plan B +]            CITY VALUE $4.2M/yr ▲ │
├────────┬────────────────────────────────────────┬─────────────┤
│ TOOLS  │                                        │ Radar chart │
│ select │   Fixed cinematic view: FiDi + SoMa    │ Δ metric    │
│ ped.   │   sims + trails + overlay glow         │   cards     │
│ density│                                        │ Citizen     │
│ zoning │   (click anything → inspector card)    │   feed      │
│ LAYERS │                                        │             │
├────────┴────────────────────────────────────────┴─────────────┤
│ ⏯ 06:00 ━━━━━●━━━━━━ 24:00   1× 10× 60×   [Compare ⇆]   💬 Ask AI │
└───────────────────────────────────────────────────────────────┘
```

### Principles
- **Glanceable**: one number (City Value) plus one shape (radar).
- **Tactile and forgiving**: paint to edit, satisfying pops, undo.
- **Recognizably SF**: real skyline, real streets, real businesses.
- **Explain everything**: every number links to the sims, shops and streets behind it.
- **Honest**: visible assumptions, shown downsides.

---

## 8. Data and platform
| Data | Source | Notes |
|---|---|---|
| Roads | OpenStreetMap | Attribution required |
| Building footprints/heights | DataSF Building Footprints | Real heights give a recognizable skyline |
| Zoning / land use | DataSF | Free |
| Businesses | **Google Maps data via Apify** | Includes popular times, ratings, price level and categories, which feed attractiveness and calibrate visit timing |
| Commuter flows | Census LODES | Split arrivals across highway and station gateways |
| Income | ACS | Equity breakdown |
| Transit stations | BART/Muni station locations (GTFS) | Spawn points only |

**Platform (if convenient): SpacetimeDB.** Use it as the live, authoritative world state (sims, edits, metrics) that streams to the viewer in real time. It also makes shared scenarios and a multi-viewer demo (judges editing together) almost free. Decide during technical planning.

---

## 9. Scope tiers
- **MVP:** FiDi + SoMa view; cars from highways, pedestrians from stations; 3 edits; settle loop; traffic, foot-traffic and business layers; radar + City Value vs. baseline.
- **Strong:** compare swipe, pitch card, inspectors (sim/business/street), social layer, citizen feed, equity view, scenario tabs.
- **Stretch:** AI planner, Policy Book, soundscape, guided challenges.

## 10. Open questions for the team
- Which street is the demo's hero edit (Montgomery, 2nd, Kearny, or a block of Market)?
- Team split (renderer · sim engine · data/metrics · AI/narrative)?
- Is SpacetimeDB the sim host, or only the sync and state layer? (Technical phase.)
