# CommonGround: Devpost submission

Draft for Cal Hacks 2026. Every number comes from the repo: the engine snapshot `mockup/backend-snapshot/plan-84731cbe0c91.json` (2nd St car-free), `research/validation/README.md`, `backend/droid/README.md`, `backend/live/README.md`, `backend/workspaces/README.md` and `agents/fetch/README.md`. Fill in every `TODO` before you submit.

---

## General info

**Project name**

```
CommonGround
```

(Longer option, 55 characters: `CommonGround: test street changes in minutes, not years`)

**Elevator pitch** (178 / 200 characters)

```
A living simulation of 270,000 people in downtown San Francisco, built from real data. Close a street to cars and see traffic, foot traffic and sales shift in minutes, not years.
```

---

## About the project

Paste everything between the two lines below into Devpost.

---

## Inspiration

The cities we live in shape who we meet, where we go and how we spend our time. When New York opened Ditmars Boulevard in Astoria, Queens, to people instead of cars, restaurants on the open street saw sales rise 44%. On a stretch of the same street that kept its cars, sales fell 7% ([NYC DOT, *Streets for Recovery*, 2022](https://www.nyc.gov/html/dot/downloads/pdf/streets-for-recovery.pdf)). The street also became a place where neighbors gather.

Getting to a decision like that takes months, often years, of traffic counts and field studies. The people with the most at stake wait the longest. Before the SFMTA votes on a car-free block, the merchants and neighbors on a street like 2nd Street in SoMa have to take a side. They get a few minutes at the microphone and a traffic study that says nothing about their customers. Their questions are simple: Will more people walk past my door? Where do the cars go instead? Who gains, and who pays?

> TODO: the real quote from a merchant, neighbor or planner you talked to. Name, role, business or street.

**Who it's for:** city and transit planners who scope street projects, and the merchant groups and neighborhood associations in downtown San Francisco (the Financial District and SoMa) who must take a position before a hearing. We wanted them to get a defensible estimate of a project's effects in minutes, before anyone pours concrete.

## What it does

CommonGround is a 3D simulation of a weekday in San Francisco's Financial District and SoMa. It models 270,942 people as 14,140 agents, each with a home, a job and a schedule drawn from Census data. Each one plans their day, chooses where to go and how to get there, and crosses paths with others along the way. That adds up to about 994,000 walking trips, 197,000 transit trips and 178,000 car trips a day.

Then you change the city:

- **Streets:** drag along a street to make it car-free, a slow street, a protected bike lane or a road diet. Click a freeway ramp to close it.
- **Blocks:** change density, rezone a block, turn a building into a park or plaza, or open a café, restaurant, bar, grocery or shop in it.
- **Policies:** add a congestion charge on any entry road, set a parking price, or reopen Market Street to cars as it was before 2020.

After each edit, every agent replans over five simulated days, which takes about 1.5 seconds. CommonGround then compares the plan with today: traffic, foot traffic, visits and revenue for each business, chance encounters and new acquaintances, CO₂, and a net value in dollars per year, split by category and by income group. A swipe shows today and the plan side by side.

**Example: 2nd Street car-free from Market to Folsom**, each weekday compared with today:

- Foot traffic on 2nd Street rises 25%.
- Local businesses earn $21,000 more a day.
- 378 fewer people drive to work.
- The cars don't vanish. Mission Street carries about 17% more car traffic, and other drivers lose 80 vehicle-hours a day, about 1.8 seconds per car trip. We show this on purpose.
- People have 84,500 more chance encounters and form 241 new acquaintances.
- Net value is +$1.79M a year after the cost to drivers: mobility −$1.36M, local economy +$1.52M, street life +$1.44M, environment +$0.19M.

You can also follow one person. Maria drives in from the East Bay today. When 2nd Street goes car-free she switches to BART, and the app replays her day both ways.

**AI proposes and explains. The engine does the counting.**

- **AI planner (Claude):** type a goal such as "boost small business in SoMa without slowing Bay Bridge traffic." Claude searches streets and entry roads, runs each candidate plan through the engine and previews the best ones on the map.
- **Ask the city (Factory Droid):** ask "Where is traffic worst at 8am?" or "Why did revenue on 2nd St go up?" Droid answers from engine queries in about 8 seconds, and the camera flies to the places it mentions.
- **Policy compiler (Factory Droid):** ask for a lever the engine doesn't have, such as "a $5 charge only for through-traffic." Droid writes it as a module with tests inside a sandbox, and a person approves it before it goes live.
- **ASI:One (Fetch.ai):** ask about a street change in a chat. Four agents run it on the engine and answer with its numbers.

**Built for teams.** A planning team opens a workspace, invites colleagues as admins, editors or viewers, and moves plans across a Draft → In review → Approved board. SpacetimeDB lets everyone see each other's edits, cursors and the recomputed results live.

**About the numbers.** The app lists every parameter with its source and tags it as data, literature or assumed.

**Cities.** San Francisco runs the full engine. Chicago's Loop and Midtown Manhattan are built in 3D with the same pipeline and open in explore mode while we load their engine data.

## How we built it

### Real data, collected with Apify

- **OpenStreetMap:** streets, buildings, building parts, transit stations and every road that crosses the edge of the map.
- **US Census LODES and ACS:** 322,000 jobs in the area, where those workers live and what they earn, and 37,174 residents.
- **DataSF:** land use and zoning for every parcel (86 million square feet of office space), matched to buildings.
- **BART:** station exits by hour.
- **Google Maps businesses via Apify:** we ran the `compass/crawler-google-places` actor over the study area. It returned 868 places for $5.26. We matched 388 of them to buildings, and 344 have popular-times curves. Ratings and reviews set how attractive each business is, and popular times calibrate when people visit.
- **Caltrans freeway counts and SFMTA bike counts** for validation.

### The simulation engine (Python, numpy, scipy, FastAPI)

- **Activities:** each agent commutes, gets coffee, eats lunch, runs errands and goes out in the evening.
- **Mode choice:** a multinomial logit over car, transit, walking and cycling, with value of time by income tier. Its constants are calibrated to the Census commute split.

$$P_i(m) = \frac{e^{V_{im}}}{\sum_{k} e^{V_{ik}}}$$

- **Traffic:** hourly shortest-path trees on the real road graph from 65 entry points, with BPR congestion on every road.

$$t_e = t_e^0 \left[ 1 + \alpha \left( \frac{v_e}{c_e} \right)^{\beta} \right]$$

- **Replanning:** five MATSim-style days that average flows from day to day, so traffic settles after each change. Drivers can also skip a trip or take the freeway around the area, so traffic can "evaporate" as studies of real closures observe.
- **Destinations:** a Huff model weighs each business's Google quality against distance, with a bonus for car-free frontage. People walking past make impulse visits; drivers don't.
- **Social ties:** two people in the same café, shop or plaza within 15 minutes count as an encounter. Repeated encounters can become acquaintances. Neighbors on busy streets know fewer people, following Donald Appleyard's 1969 study of three San Francisco streets.
- **Valuation:** consumer surplus for travelers, the USDOT value of time, the social cost of carbon, crash costs, value added and taxes for local business, and a labeled assumption for social ties.
- **Fair comparison:** the baseline and every plan run the same procedure with the same people and the same random draws. A plan with no edits reproduces today exactly, and a test checks that, so every difference comes from the edit.

### Checked against the real city

Calibrated on purpose:

- Commute mode share: car 35.1% in the model vs 34.4% in the Census; transit 49.7% vs 48.4%.

Not fitted:

- Hourly arrivals at the three downtown BART stations correlate with BART's own data at r = 0.84–0.97.
- Making 2nd Street car-free raises foot traffic 24.6% in the model; SFMTA measured 29%.
- After Market Street went car-free in 2020, the model slows Mission Street by 4.8%; INRIX measured 4.0%.

Partly calibrated:

- Café visits by hour correlate with Google popular times at r = 0.82.

Where we're off, and the app says so: cycling on Market Street rises 98% in the model against 25% observed, and Muni speeds on Market don't improve in the model, while SFMTA measured +6%.

### Claude: planner, explainer and citizen voices (Anthropic API)

- **Claude Sonnet 5.5** runs the AI planner as a tool-use loop over the engine (list streets, list entry roads, evaluate a plan) and writes the "why" explanations.
- **Claude Haiku 5.5** writes citizen posts and diaries from each agent's actual trips that day.
- Every prompt carries grounding JSON from the engine, and the system prompt allows only numbers that appear in it. The planner only proposes edits; the engine scores them. We cache responses under a fingerprint of the engine, so cached text can't quote outdated numbers.

### Factory Droid SDK: the city extends itself

Droid does real work in the running product, in two modes. Our FastAPI server drives both through `@factory/droid-sdk` (`createSession`, `session.stream`).

**Policy compiler.** The trigger is a planner asking for a lever that doesn't exist, via `POST /policies/propose` from the Droid panel or the AI planner.

1. **Plan:** Droid reads our policy plugin interface and returns a JSON plan with hooks, parameters, assumptions and steps.
2. **Write:** Droid writes one module and its test. Both file paths are fixed after the plan.
3. **Gate:** a static scan of the code (allowed imports only, no file access, no `eval`), pytest on Droid's test and on the whole engine suite, a determinism check, and sanity bounds on the results. Our server re-runs the gate itself, and Droid gets at most two rounds to fix failures.
4. **Approve:** a person clicks Apply. The file hashes must still match what passed the gate. The module then loads into the Policy Book without a restart.

What Droid can touch: an allowlist of tools (`restrictToolIds`), a permission handler that checks every file write by its path, one allowed command (the gate), Droid's own sandbox with no network and an unreadable `.env`, and a 10-minute limit. The panel shows the plan, Droid's to-do list, every tool call, every permission decision, the diff, the test output and the before-and-after metrics.

In a measured run, "a $5 charge only for through-traffic" became `through_charge.py` with 21 tests and passed the gate on the first try, about 2.5 minutes end to end. It cuts driving in the area by 2.2% and delay by 3.6%, worth +$1.35M a year.

**Ask the city.** Each conversation gets a warm Droid session that answers from `simq`, a read-only query tool over a snapshot of the scenario. `simq` is the only command Droid may run; pipes, redirects and other programs are denied and shown as denied steps. An answer gate drops any place that doesn't exist and recomputes the camera target from real geometry. Answers take 6.5 to 9 seconds.

### SpacetimeDB: one shared city for the whole team

We run two SpacetimeDB modules:

- **`commonground` (the website):** workspaces, members with roles, private invite codes, plans on a workflow board, each plan's street and block edits, presence, cursors, an activity feed and each plan's latest result. Reducers check membership and role with `ctx.sender`.
- **`human-live` (Go live in the 3D app):** one shared plan. Each edit bumps a version number and starts a 400 ms debounce. A scheduled procedure then sends the plan to the engine and writes the result in one transaction. Every subscriber gets the same numbers about 1.5 seconds after an edit, or 0.4 seconds if the engine has seen the plan before. Edits made during a computation are never lost: the run sees the newer version and queues another.

### Fetch.ai: the city on ASI:One

Four uAgents on Agentverse: an **SF Street Analyst** that orchestrates, and **Mobility**, **Local Economy** and **Equity** specialists. Ask in ASI:One, "make 2nd St car-free between Market and Folsom." The analyst maps the street to the engine's road segments; if you name only a street, an Interactive Card asks which cross streets. It hands the plan to the three specialists, each runs the scenario on the engine, and the analyst merges their answers. A hearing brief costs 2 FET through the Payment Protocol. A scripted conversation checks the chat answer against a direct engine call, field by field, and all 11 checks pass.

### The 3D app

The app uses three.js, with recognizable San Francisco buildings built from OpenStreetMap building parts and a faded city around the study area. It has eight info views (traffic, foot traffic, workplaces, residents, visits, zoning, connections and revenue change) and a compare swipe. An offline mode replays saved engine results without a server.

## Challenges we ran into

- **SpacetimeDB won't call localhost.** Procedures refuse HTTP requests to private addresses, and no setting turns that off. For Go live we wrote a small proxy on the laptop's public IPv6 address. It forwards only `POST /scenario` and `/health`, so nobody can spend our Claude credits through it. In the website module, a member's browser claims the computation and reports the result instead, and a claim expires after 30 seconds.
- **Our first validation run was badly off.** Car-free 2nd Street raised foot traffic 91%, against 29% measured. Our comfort bonuses for car-free streets were too generous. We revised them to the 10–15% detour tolerance that route-choice studies report, as one global value each rather than tuned per case, and foot traffic landed at +24.6%.
- **Five entry roads were too few.** With cars entering at five hand-picked points, car-free Market Street slowed Folsom Street by 32%, while INRIX measured at most 4%. We now create an entry point at every road that crosses the map edge (65 in all), drivers pick the cheapest, and Folsom comes out at +4.5%.
- **Silent failures.** Closing a street left 7% of workers with no reachable parking, which quietly pushed them onto transit. One entry road led straight onto car-free Market Street. Validation caught both after the unit tests had passed.
- **Sandboxing an agent on macOS.** When we wrapped the Droid CLI in our own `sandbox-exec`, every command died, because macOS refuses nested sandboxes. We turned on Droid's own sandbox through a settings file instead. Droid also runs commands it considers read-only without asking our permission handler, so the operating system sandbox is what really enforces the limits.
- **A known flaw we keep visible.** Any changed plan, even one with no effect, comes out about $0.36M a year better than today because of how replanning starts. We record it as a strict expected-failure test instead of hiding it.

## Accomplishments that we're proud of

- A model of 270,942 people that replans in about 1.5 seconds, matches the Census mode split within two points, and lands near SFMTA's measurement on 2nd Street without being tuned to it.
- No AI in the product can invent a number. Claude, Droid and the Fetch.ai agents quote only engine outputs, each answer lists the tool calls behind it, and a test checks that the chat answer equals the engine's.
- Droid adds working, tested levers to the running product in about 2.5 minutes, and nothing loads until a person approves it.
- Research behind every number: 16 case studies (Market Street, Barcelona's superblocks, Pontevedra, Oslo, Seoul's Cheonggyecheon and more) and 74 sourced parameters, tagged data (21), literature (37) or assumed (16).
- The costs stay on screen: the extra delay, the streets that take diverted traffic, and who pays by income group.

## What we learned

- **Validation finds bugs that unit tests miss.** Comparing against the real Market Street closure exposed four bugs that every test had passed.
- **Agents earn trust when they can't touch the numbers.** Once AI only proposed and explained while the engine counted, we could put Claude and Droid in front of a hearing.
- **Agent safety comes in layers.** A tool allowlist, a permission handler that checks paths, an operating system sandbox, a test gate and a human approval each catch what the others miss.
- **Showing the losers builds trust.** A tool that reports only gains reads like advocacy. Planners need the delay and the diverted traffic too.

## Where it could go wrong, and what we built against it

- **A fluent story on top of a model.** Claude and Droid may only quote engine numbers, and each answer lists its tool calls.
- **Synthetic people carry bias.** Agents come from Census LODES and ACS, and results are split by income third, so the app shows who pays.
- **One dollar figure gets too much trust.** Every parameter carries its source, and the costs, the losers and the gap left by replanning stay on screen.
- **Social value is the softest number.** We value a new acquaintance at $1,100 a year, an assumption derived from the UK Social Value Bank, and we label it as one.
- **AI-written code in a running product.** Droid works in a sandbox behind a test gate, and nothing loads until a person approves it.

## What's next for CommonGround

- **More cities.** Chicago and New York already render from the same pipeline. OpenStreetMap and Census LODES and ACS cover every US city, so each new city needs local land-use data, an Apify business run and a calibration pass.
- **Changes by time of day**, such as weekend-only closures, loading zones and peak-hour charges. Droid can write many of these as new levers.
- **Uncertainty ranges** on every result, and fixes for the open gaps in cycling and Muni speeds.
- **A pilot** with a SoMa merchant association or an SFMTA project team, ending in a hearing brief they can bring to the microphone.
- **Path to production:** the engine is deterministic, caches identical plans and sits behind a documented API, so it can run as a hosted service. The SpacetimeDB modules move to Maincloud, and per-member views replace public tables before real city data goes in.

---

## Built with

25 tags, the maximum:

```
python, numpy, scipy, fastapi, pytest, javascript, typescript, node.js, three.js, html5, spacetimedb, factory-droid-sdk, claude, anthropic-api, fetch.ai, uagents, agentverse, asi-one, apify, google-maps, openstreetmap, us-census, datasf, bart, server-sent-events
```

## "Try it out" links

- Code: https://github.com/ma-xr/calhacks-2026
- Offline demo (saved engine results): https://claude.ai/artifact/PH5gp1pVKFvpRW7kvmvfm1 (TODO: confirm it opens in a private window)
- SF Street Analyst on Agentverse: https://agentverse.ai/agents/details/agent1q0df0hxkdg79syl8jeu79eqz99z0ul7td752xm3qwgqkkxdjvd4tkanh9xw/profile

---

## Project media

**Image gallery** (crop to 3:2, for example 1620 × 1080; JPG or PNG under 5 MB)

| # | Shot | Caption | Source |
|---|---|---|---|
| 1 | The 3D city in the morning rush, traffic view | A weekday in downtown San Francisco: 270,942 people, every trip | `slides/img/city.jpg` (1920 × 1080) |
| 2 | 2nd Street painted car-free | Drag along a street to make it car-free | `slides/img/car-free-2nd.jpg` |
| 3 | Foot traffic heat map, plan vs today | Foot traffic on 2nd Street rises 25% | new screenshot |
| 4 | Revenue change view | Businesses on the street earn $21,000 more a day | new screenshot |
| 5 | Traffic view showing Mission Street | The cars go somewhere: Mission Street carries about 17% more | new screenshot |
| 6 | Connections view with pink arcs | Each arc is a new acquaintance that exists only in the plan | `slides/img/ties-wide.jpg` or `slides/img/connections.jpg` |
| 7 | Following Maria | One commuter switches from driving to BART | new screenshot |
| 8 | Droid panel: plan, diff, gate results | Factory Droid writes, tests and hands over a new policy | new screenshot |
| 9 | Workspace board with two cursors | Plans move from Draft to Approved, edited live by the team | new screenshot (website at `/site/`) |
| 10 | ASI:One chat answer | Four Fetch.ai agents run the plan from a chat | new screenshot |
| 11 | About the numbers panel | Every parameter with its source: data, literature or assumed | new screenshot |

**Video demo link**

```
TODO: YouTube or Vimeo URL
```

---

## Feedback on the technology we used

**SpacetimeDB.** Reducers plus subscriptions made shared state nearly free: one transaction reaches every browser, and the generated TypeScript bindings meant we never wrote sync code. Scheduled procedures gave us a clean debounce for recomputing a plan. The biggest snag: procedure HTTP refuses private addresses, with no override for local development, so calling our engine on localhost needed an IPv6 proxy or computation in the browser. A dev-only flag would have saved hours. Most schema changes also meant republishing with `--delete-data`.

**Factory Droid SDK.** `createSession`, `session.stream`, `restrictToolIds` and the `permissionHandler` made it practical to run an agent inside a product with real limits, and the step stream made Droid's work easy to show. Rough edges: in droid 0.249 tools run inside the `Script` tool, so our permission handler had to judge scripts rather than single tool calls; commands Droid considers read-only skip the handler; and wrapping the CLI in `sandbox-exec` kills every command on macOS. Documenting these would help the next team. Answers also slowed down when two sessions shared the API at once.

**Fetch.ai (uAgents, Agentverse, ASI:One).** Running all four agents plus a scripted user in one Bureau made the multi-agent flow easy to test offline. The Chat Protocol and Interactive Cards gave us a real interface inside ASI:One with no frontend of our own, and the Payment Protocol was simple to add. Hard parts: agent addresses depend on seeds, so losing the seed folder changes them, and mailbox agents have to keep running on our laptop for judges to reach them.

**Apify.** The Google Places crawler gave us popular times, which no free API offers, and the per-place pricing was clear: 868 places cost $5.26. Only about 40% of places come back with popular times, and the actor takes one place limit for all search terms.

**Anthropic Claude API.** Tool use was dependable for the planner loop, Haiku was fast enough for bulk citizen posts, and putting engine JSON in the prompt kept answers grounded.

---

## Which of the following AI tools did you use this weekend?

Tick the boxes that apply. Based on the repo:

- **Claude / Claude Code (Claude Opus 5.5):** our pair programmer for the engine, tests, 3D app and research (the commits are co-authored by Claude).
- **Factory Droid:** inside the product (Ask the city and the policy compiler).
- **ASI:One (Fetch.ai):** inside the Fetch.ai agents.

## Did you implement a generative AI model or API in your hack this weekend?

```
Yes, in four places, all under one rule: AI proposes and explains, and the simulation engine produces every number.

1. Claude Sonnet 5.5 (Anthropic API) is the AI planner. Given a goal such as "boost small business in SoMa without slowing Bay Bridge traffic," it runs a tool-use loop: it lists streets and entry roads, sends candidate plans to the engine, and explains the results it gets back. It also answers "why" questions. Prompts carry the engine's results as JSON, and Claude may quote only numbers found there.
2. Claude Haiku 5.5 writes citizen posts and diaries from each simulated person's actual trips that day, so every post matches what that person did.
3. Factory Droid (Droid SDK) answers questions about a scenario using a read-only query tool, and writes new policy levers as code with tests, inside a sandbox, behind a test gate and a human approval.
4. ASI:One's asi1-mini model turns free-form chat requests into street names for our Fetch.ai agents, choosing only from the engine's list of streets.

We used generative AI because planners ask in plain language and need explanations, not raw tables. We kept it away from the numbers because a fluent answer built on an invented figure could mislead a public hearing.
```

---

## Sponsor tracks to opt into

| Track | Enter? | Why |
|---|---|---|
| Factory: Best Use of the Droid SDK | Yes | Two modes in the running product, a designed trigger, scoped permissions, visible plan, steps and diff |
| SpacetimeDB | Yes | Two modules: workspaces and Go live with shared plan state |
| Fetch.ai | Yes | Four agents on Agentverse, Chat Protocol, cards and payments in ASI:One |
| Apify: Best Use | Yes | Google Maps data drives destination choice and visit timing |
| Apify: Best Actor | Only if you publish an actor | The repo uses `compass/crawler-google-places` and has no actor of its own |
| Anthropic | Yes, after adding the real quote | Named community, a planner built on tool use, failure modes written down |
| Microsoft: Built for the Real World and Customer Impact | Yes | High-impact civic domain, measurable outputs, responsible design, a path to production |
| Moss, Convex, Elastic, Bright Data | No | None of them is used in the code |
