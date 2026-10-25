# Track strategy: CommonGround at Cal Hacks

Written Saturday 2026-10-24, early afternoon. Devpost closes **Sunday 9:00 AM**, which leaves about 19 hours. Everything below is sized to that.

## 1. The idea in one line

**One product, one architecture. Each sponsor owns a real layer of it, and each judge gets a pitch cut for their criteria.**

You can't build eight products in 19 hours. But a city sim has natural slots for several sponsors: a live world state, AI agents that plan and explain, real-world data, a way to add new policies, and other ways in (chat, voice). If every integration does real work, you can enter many tracks honestly. A sponsor integration that sits on the side scores poorly with that sponsor's judges, so don't add one just to qualify.

## 2. Track fit and priority

| Priority | Track | Fit | Effort on top of the core | Prize |
|---|---|---|---|---|
| **Core** | SpacetimeDB | ★★★ The sponsor's own wishlist includes "shared simulations", "AI agents coordinating in a persistent world state" and live dashboards. That is this project. | Core work | $2,048 / 1,024 / 512 |
| **Core** | Anthropic | ★★★ If we name a community (see §4) and Claude is the planner and explainer | Core work + pitch | $5k credits + Max |
| **Core** | Microsoft: Built for the Real World + Customer Impact | ★★★ Production-minded agent in a high-impact domain (civic planning) | Pitch, responsible-design features | Surface laptops + FDE mentorship |
| **Core** | Apify (Top 5 + Best Actor) | ★★★ Spec S1 already uses Google Maps data via Apify. Publishing our own actor makes us eligible for a second award | 2–3 h | up to $2,000 + $400 |
| **High** | Meta: Bringing People Closer Together | ★★☆ The social-ties pillar (encounters, new ties, income mixing) becomes the headline. Live multiplayer co-design adds to it | Social layer + 2–3 min video | Round 2 at Menlo Park |
| **High** | Factory Droid SDK | ★★☆ Droid as a **policy compiler** that writes new intervention modules into the running product (§3.4) | 4–5 h, one person | $2,000 |
| **High** | Fetch.ai | ★★☆ An "SF Street Analyst" multi-agent system on ASI:One that calls the headless sim | 4–5 h, one person | $1,250 / 750 / 500 + $250 ×2 |
| **Medium** | Moss | ★☆☆ Voice: interview a sim ("Maria, how was your commute?"). Moss does fast retrieval over each sim's memory | 3 h | AirPods |
| **Skip unless swapped in** | Convex | Only wins if Convex is *the* backend. A second database next to Spacetime looks bolted on to both sponsors | n/a | $5,000 |
| **Skip / watch** | Creao (×3), Elastic, Bright Data | Their requirements weren't published or I couldn't verify them. Creao probably wants you to build on its own platform. Elastic is "coming soon". Apify already covers scraping | n/a | |

**Recommended entry set: SpacetimeDB, Anthropic, Microsoft (both), Apify (both), Meta, Factory, Fetch.ai.** Add Moss if someone frees up by Saturday midnight.

> **Spacetime or Convex?** Convex pays more ($5k), but for one winner across a crowded general track. Spacetime is a better technical fit (live shared sim state that many viewers subscribe to), it's already in the spec, and the competition is thinner. Pick one as the core. Splitting the backend loses both.

> **Check first:** confirm on Devpost or with organizers whether Cal Hacks caps how many sponsor prizes one submission can opt into. If it does, use the priority order above.

## 3. Architecture: who owns which layer

```
      Apify actor ──► world.json + businesses (popular times, ratings, categories) + Reddit voices
                         │
                         ▼
 ┌──────────────── SpacetimeDB module (authoritative world) ────────────────┐
 │ tables: road, block, business, sim, trip_plan, edit, scenario, metric,  │
 │         tie, citizen_post, policy_module                                │
 │ reducers: apply_edit, settle(n_days), set_density, set_zoning, vote     │
 └──────▲───────────────▲───────────────────▲──────────────────▲──────────┘
        │ subscribe     │ subscribe         │ call reducers    │ call reducers
  three.js viewer   phones (QR):        Claude planner     Fetch.ai agents
  (main screen)     judges paint/vote   + narrator          (ASI:One, headless)
                                           │
                                           └─► Factory Droid: writes new policy modules
                                               (sandboxed, tested, diff shown in UI)
  Moss: index of sim memories/diaries + evidence library ◄── voice interview
```

### 3.1 SpacetimeDB: the living city (core)
- **Don't stream every agent position.** Store each sim's **trip plan** (departure time, path, mode). Clients interpolate movement locally from the shared clock. The server only writes on replanning. That keeps thousands of agents cheap and still exact across viewers.
- `settle` runs the MATSim-style replanning days server-side, next to the data (route choice with BPR, logit mode choice, Huff store choice), then writes trips and metrics in one transaction.
- **Multiplayer is the Spacetime hero moment:** a QR code on the screen lets judges join from their phones, paint a street, and see the edit land on the big screen and on each other's phones instantly. This is also the Meta story (§4).
- Baseline and plan are two `scenario` rows with the same seed. Compare reads both.

### 3.2 Claude: planner, explainer, citizen voices
- The **AI planner** is a tool-use loop with `get_metrics`, `list_streets`, `propose_edit` (ghost preview), `run_scenario`, and `explain_delta`. It never makes up numbers. Every figure it quotes comes from a tool result, and the UI shows which tool call produced it.
- **Explain:** "Why did revenue on 2nd St go up?" Claude reads the business's visit deltas and customer origins and answers with links that highlight the sims involved.
- **Citizen feed and diaries** are generated from the sims' actual trip logs, so each post is grounded in what that sim did.
- **Where it can go wrong** (Anthropic wants us to know): a persuasive narrative on top of a toy model, bias in synthetic personas, and planners trusting $ figures too much. Mitigations: an assumptions panel, uncertainty bands, a "losers" section that is always shown, and visible tool provenance.

### 3.3 Apify: real-city data, and our own actor
- Use the Google Maps scraper for FiDi and SoMa businesses. Popular times calibrate visit timing; rating and price feed Huff attractiveness.
- **Best Actor entry:** publish a `city-pulse` actor. Input: a bounding box. Output: sim-ready JSON (businesses with hourly demand curves and categories, plus geotagged Reddit r/sanfrancisco posts about streets in the box). Any city then gets a "street life seed". Put it on the Apify Store and link it in the README.
- The Reddit posts seed citizen personas and the "lived problem" evidence for Anthropic.

### 3.4 Factory Droid: the city sim extends itself
This fits Factory's criteria exactly: a trigger we designed, scoped permissions, and visible work.
- **Trigger:** the planner (or a user) asks for a lever that doesn't exist yet, for example "a $5 congestion charge on cars entering from I-80 at peak hours" or "a 10-minute loading zone on Howard".
- **Droid's job:** write a new policy module against a small `Policy` interface (`modifyUtility`, `modifyCapacity`, `onTick`) in `policies/`, add a unit test, and run the sim's validation suite (determinism, no NaNs, metrics in a sane range).
- **Safety:** write access only to `policies/<new-file>`, no network, a time limit, and a test gate. A human clicks **Apply** in the UI before the module is hot-loaded into the Policy Book.
- **Visible:** an in-app "Droid panel" shows the plan, the steps, the diff, test results and the before/after metrics. The README section says exactly where and how Droid runs.

### 3.5 Fetch.ai: the city on ASI:One
Hard requirements: register agents on Agentverse, implement the Chat Protocol, run the whole workflow inside ASI:One with no custom frontend, use tools or multi-agent orchestration, and publish a public repo.
- **Agents:** `SF Street Analyst` (orchestrator) delegates to `Mobility`, `Local Economy` and `Equity` agents. Each one calls the headless sim API (Spacetime reducers) and returns its part.
- **Flow in ASI:One:** "What happens if 2nd St between Market and Folsom goes car-free?" The analyst replies with an Interactive Card (pick the segment, pick hours), runs the scenario, and returns result cards with $ by pillar, winners and losers, and a link to replay it in 3D.
- **Bonus:** a Payment Protocol "full report" tier (e.g. $2 for a PDF hearing brief). That is a believable model for consultants and merchant associations.
- Deliverables: a 3–5 min video, the agent names and addresses plus the Innovation Lab badges in the README, and registration with the ASI:One Submission Agent.

### 3.6 Moss (optional): talk to the city
- Each sim's day log and diary go into a Moss index with metadata filters. Push-to-talk: "Maria, why did you stop driving?" Moss returns her relevant memories in under 10 ms, Claude answers in her voice, and TTS speaks it.
- Fits Moss's "voice agent" and "agent that remembers you" categories. Build it only if the core is done.

## 4. Positioning per track

**Named community (Anthropic's "right register"):**
> *Small-business owners and merchant groups in downtown SF (FiDi and SoMa) who must take a position on street changes, such as car-free blocks or plaza activations, before SFMTA hearings. Today they rely on gut feeling and on traffic studies that take months.*

This community is concrete, it's live (downtown recovery, the car-free Market St precedent), and it's the person the demo's "local economy" pillar speaks to. **Action today:** talk to 2–3 people who fit, by phone, DM or a café visit. Get one quote and one number ("we lost X% when...") for the pitch. Reddit posts from the Apify actor back it up.

| Track | Pitch line | What the judge must see |
|---|---|---|
| **Anthropic** | "Before the hearing, a café owner on 2nd St can see what a car-free block does to their foot traffic, and who it hurts." | Named community, a real quote, one flow that works end to end, Claude's tool-grounded planning, and the failure modes we designed around |
| **Microsoft** | "A planning agent for city staff and merchant groups: proposal → simulation → hearing brief, in minutes instead of months." | Customer understanding (the quote), a measurable output ($/yr, delay hours, visits), responsible design (assumptions, uncertainty, equity, losers), and a path to production (any city via the Apify actor and OSM; SFMTA pilot) |
| **SpacetimeDB** | "Thousands of agents and many humans editing one shared city in real time." | Judges' phones editing live, the reducers doing the replanning, subscriptions keeping viewers in sync |
| **Meta** | "Streets built for cars kill chance encounters. We let neighbors design streets for connection together, and AI shows how many new ties each design creates." | The Connections info view, encounter sparks, the multiplayer co-design session, the AI planner optimizing for "new ties without hurting Bay Bridge traffic" |
| **Factory** | "When a planner asks for a policy that doesn't exist, Droid builds it, tests it and hands it over for approval." | The trigger, the scoped sandbox, the diff and tests in the UI, the human Apply step |
| **Fetch.ai** | "Ask ASI:One about any SF street change and a team of analyst agents simulates it." | The whole flow in ASI:One, multi-agent delegation, cards, payment |
| **Apify** | "Real businesses, real rhythms: our actor turns any bounding box into a living city seed." | The actor on the Store, the data visibly driving the sim (popular-times curves in the business inspector) |
| **Moss** | "Interview any citizen of the simulated city by voice." | Voice round trip and latency |

## 5. The demo (2 min live, at the table)

One main script, with a 20–30 s "sponsor beat" you swap in depending on who is judging:

1. **(15 s) Problem and community:** the merchant quote and "hearings decide this on gut feeling".
2. **(30 s) Living city:** the morning rush. Cars from I-80, walkers from BART, live counters.
3. **(30 s) The edit:** paint 2nd St car-free. The settle loop runs, the Compare swipe shows baseline vs plan, the spillover onto 3rd is shown honestly.
4. **(20 s) Why:** click the café. Visits are up, and here are the sims who now walk past it. Claude explains, citing its tool calls.
5. **(25 s) Sponsor beat:** judges' phones join (Spacetime/Meta) · Droid builds the congestion charge (Factory) · ASI:One chat (Fetch) · voice interview (Moss).
6. **(10 s) Hearing brief:** $/yr by pillar, winners and losers, stakeholder approval.

Keep a **recorded fallback** of every sponsor beat on a laptop tab in case the venue Wi-Fi fails.

## 6. Scope cuts (to protect the 19 hours)

From `spec.md`, **keep**: the free camera and one design variant (pick A, B or C now and stop iterating), pedestrianize, density, Compare, the traffic, foot-traffic, connections and revenue-change views, the business and sim inspectors, the AI planner, and the pitch card.
**Cut:** zoning edits, scenario tabs beyond Baseline/Plan A, guided challenges, soundscape, most of the Policy Book (Droid fills it instead).

## 7. Team split and timeline

| Role | Owns | Tracks it serves |
|---|---|---|
| **A · World/backend** | Spacetime module, settle loop port, phone client | Spacetime, Meta, all |
| **B · Viewer** | three.js client on Spacetime subscriptions, info views, Compare, inspectors | All demos |
| **C · AI** | Claude planner and explainer, citizen feed, Droid policy compiler | Anthropic, Microsoft, Factory |
| **D · Data and agents** | Apify actor, business calibration, Fetch.ai agents, (Moss) | Apify, Fetch, Moss |

| When (Sat → Sun) | Milestone |
|---|---|
| now → 18:00 | Spacetime schema and `apply_edit`/`settle` working headless. Apify run done, businesses in `world.json`. Viewer reads from Spacetime. Community interviews. |
| 18:00 → 24:00 | Claude planner on real tools. Phone multiplayer. Droid policy compiler end to end. Fetch agents registered, ASI:One flow working. |
| **by 23:00** | **Draft Devpost submission** (organizers recommend it) |
| 00:00 → 04:00 | Polish the hero flow, honesty features (assumptions, losers), fallback recordings |
| 04:00 → 07:00 | Videos: Meta (2–3 min, follow their 4-part outline, including "tools, harnesses and models used"), Fetch (3–5 min). READMEs: Droid section, agent addresses and badges, Apify actor link |
| 07:00 → 09:00 | Final submit, opt into every track in §2, rehearse the 2-min pitch and sponsor beats |
| 10:30 → 12:30 | Whole team at the table for the full window |

## 8. Submission checklist per track
- [ ] **All:** Devpost by 9:00, a live demo at the table, the whole team present
- [ ] **Meta:** a 2–3 min video (problem and connection · demo · AI role · tools, harnesses and models)
- [ ] **Factory:** a README section on where Droid runs, its trigger, its permissions, and how its work is shown
- [ ] **Fetch.ai:** a public repo, the agents on Agentverse with the Chat Protocol, the full flow in ASI:One, agent names and addresses plus the Innovation Lab and hackathon badges in the README, a 3–5 min video, registration with the ASI:One Submission Agent
- [ ] **Apify:** the actor published to the Store, its link in the README, the data used in the product
- [ ] **Anthropic:** the named community and a real quote in the Devpost text, Claude's role and failure modes written down
- [ ] **Microsoft:** a "path to production" and "responsible design" section in the Devpost text
- [ ] **Spacetime:** a README diagram of tables and reducers, and how many clients stay in sync
