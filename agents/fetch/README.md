# CommonGround on ASI:One: Fetch.ai agents

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

Ask, in an ASI:One chat, *"make 2nd St car-free between Market and Folsom"*. Four uAgents run the plan on CommonGround's agent-based simulation of San Francisco's Financial District and SoMa, then answer in the chat with grounded numbers: the net $/yr by pillar, where the cars go, which businesses win or lose, and who pays by income tier. No custom frontend is involved.

## Agents

| Agent | Role | Address |
|---|---|---|
| **SF Street Analyst** | Orchestrator. Chat Protocol + Interactive Cards, Payment Protocol (seller) | `agent1q0df0hxkdg79syl8jeu79eqz99z0ul7td752xm3qwgqkkxdjvd4tkanh9xw` |
| **Mobility** | Trips by mode, VMT, delay, diversion, PM-peak bottleneck | `agent1qvf6rauyx3u90gumvwe889yhxy57ra99xv2lm9cxkrllqudcupu552l947a` |
| **Local Economy** | Visits, revenue, businesses on the stretch, winners and losers | `agent1qdhuluv3aem55pacllcvs4dqcqf5uk357nqwea55ylz940msr8mg2hjtyvj` |
| **Equity** | Income tiers, health (WHO HEAT), social ties, rent pressure, CO₂ | `agent1qdj58mg46l8hfayz0naxwhs4pgajkv2cr53k95w38sttwavvy8dt58k9pqk` |

The addresses come from seeds in `agents/fetch/.seeds/` (gitignored, created on first run). If you delete that folder the addresses change. Back it up, or pin the seeds with `HP_SEED_ANALYST`, `HP_SEED_MOBILITY`, `HP_SEED_ECONOMY` and `HP_SEED_EQUITY` in `.env`. Run `python run.py --addresses` to print the current ones.

Registered on Agentverse as mailbox agents on 2026-10-24 (status active):
[SF Street Analyst](https://agentverse.ai/agents/details/agent1q0df0hxkdg79syl8jeu79eqz99z0ul7td752xm3qwgqkkxdjvd4tkanh9xw/profile) ·
[Mobility](https://agentverse.ai/agents/details/agent1qvf6rauyx3u90gumvwe889yhxy57ra99xv2lm9cxkrllqudcupu552l947a/profile) ·
[Local Economy](https://agentverse.ai/agents/details/agent1qdhuluv3aem55pacllcvs4dqcqf5uk357nqwea55ylz940msr8mg2hjtyvj/profile) ·
[Equity](https://agentverse.ai/agents/details/agent1qdj58mg46l8hfayz0naxwhs4pgajkv2cr53k95w38sttwavvy8dt58k9pqk/profile).
They answer only while `run.py --live` and the engine are running on this laptop.

## How it works

```
ASI:One chat ──Chat Protocol──▶ SF Street Analyst ──HPStreetAnalysis──▶ Mobility ─────┐
   ▲   (text + Interactive Cards)      │  parse street + cross streets   Local Economy ─┼─▶ engine API :8787
   │                                   │  (regex, ASI:One LLM fallback)  Equity ────────┘   POST /scenario?lite=1
   └──── answer + result card ◀────────┘  merge the three answers                          GET /scenario/baseline
         hearing brief ◀── Payment Protocol (RequestPayment → CommitPayment → CompletePayment)
```

1. **Parse.** `hp_agents/streets.py` maps names to engine edge ids. Street names and geometry come from `data/processed/world.json` (the same edge ids as the engine). `GET /world` supplies `editable_edges` and the POI list. "2nd St between Market and Folsom" resolves to the 14 edges the engine itself uses as its hero street (`world.hero.street_edges`). If only a street is named, the analyst replies with a **form card** listing that street's cross streets in order. If no street is found, it shows a **carousel card** of examples. Free-form phrasing ("ban cars on second between market and folsom") falls back to ASI:One's `asi1-mini` model, which may only pick names from the model's street list.
2. **Delegate.** The analyst sends `AnalyzeRequest{edges}` to the three specialists. Each one calls `POST /scenario?lite=1` with `{"edits":{"pedestrianized":[...]}}` (the engine caches identical edits) and compares the result against the baseline.
3. **Answer.** Each specialist turns `delta`, `value`, `value.lines`, `metrics.by_income`, `edges.*` and `pois.*` into markdown plus a `facts` dict of the exact fields it quoted (`hp_agents/analysis.py`). The analyst adds a headline (net $/yr by pillar, scenario id, settle gap) and a **detail card** whose CTAs are *Hearing brief* and *Try another stretch*.
4. **Hearing brief (paid tier).** Saying *hearing brief*, or clicking the CTA, sends `RequestPayment` (default 2 FET, `fet_direct`, to the analyst's wallet). On `CommitPayment` the analyst checks the transfer on the ledger, replies `CompletePayment`, and delivers the brief: an ASI:One-written executive summary restricted to the engine's facts, every value line, valuation factors, key assumptions and limits.

Every number in an answer is an engine output. The LLM only extracts street names and rewrites given facts in the brief summary.

## Setup

Needs Python ≥ 3.10 (uAgents). The engine must be running on `:8787` (`backend/run.sh`).

```bash
cd agents/fetch
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Keys are read from the **project-root** `.env` and never logged:
- `ASI_ONE_API_KEY`: optional. It enables free-form parsing and the brief's summary. Without it, regex parsing still covers "X between A and B".
- `AGENTVERSE_API_KEY`: only for `register.py`.

Optional settings: `HP_SIM_API` (default `http://localhost:8787`), `HP_WORLD_JSON`, `HP_BRIEF_PRICE_FET` (default `2`), `HP_BRIEF_CURRENCY` (`FET`), `HP_REPLAY_URL` (a public link to the 3D replay; `{id}` is replaced with the scenario id), `HP_BUREAU_PORT` (default `8010`).

## Run and test locally (nothing is registered)

```bash
.venv/bin/python test_conversation.py
```

This runs all four agents plus a stand-in "user" agent in one Bureau. The user speaks the Chat Protocol and the buyer side of the Payment Protocol. In local mode every Agentverse/Almanac URL points at a dead local port, so no manifest, status or registration leaves the machine. The script runs this conversation and checks that the answer matches the engine:

1. "hi, what can you do?" → help text and an example carousel
2. "What if 2nd St goes car-free?" → a form card to choose the stretch
3. **"make 2nd St car-free between Market and Folsom"** → the grounded answer. The test checks that `value.total`, the scenario id and `delta.trips.car` equal a direct engine call on the same edges, and that all three specialists answered.
4. Click *Hearing brief* → `RequestPayment` → `CommitPayment` (fake tx, verification skipped in the test) → `CompletePayment` → the brief
5. "turn Kearny into a pedestrian street from Market up to Bush" → a second stretch

The last run is in [`tests/transcript.md`](tests/transcript.md) (all 11 checks pass). To run the agents locally without the test, use `.venv/bin/python run.py`.

## Register on Agentverse and use from ASI:One

> Registration makes the four agents **public** on Agentverse and discoverable from ASI:One. Do it deliberately.

1. Start the engine: `backend/run.sh`. Check `curl localhost:8787/health`.
2. Dry run, which prints what would be registered: `.venv/bin/python register.py`
3. Register mailboxes and profiles (uses `AGENTVERSE_API_KEY`): `.venv/bin/python register.py --yes`. This is the same as opening each agent's inspector link and clicking **Connect → Mailbox**. Each profile's README comes from `profiles/*.md`.
4. Run the agents connected to their mailboxes and keep the process up during judging: `.venv/bin/python run.py --live`
5. On agentverse.ai → *Agents*, check that the four agents are listed, active, and show **AgentChatProtocol** on the SF Street Analyst. Optionally add an avatar and keywords (urban planning, San Francisco, traffic, city simulation).
6. In **ASI:One** (asi1.ai), turn on *Agents* and ask "Ask the SF Street Analyst: what happens if 2nd St goes car-free between Market and Folsom?", or open the analyst's Agentverse profile and click **Chat with Agent**.
7. Paste the addresses and profile links into the table above and into the repo README. Register the project with the **ASI:One Submission Agent** as the hackpack describes.

Payments: the analyst's wallet address is printed in each `RequestPayment` (`recipient`). Verification checks a `transfer` of the exact amount in `afet` or `atestfet` to that address on the agent's ledger. Set `HP_SKIP_PAYMENT_VERIFY=1` only for demos with fake transactions.

## Files

| Path | What |
|---|---|
| `hp_agents/analyst.py` | SF Street Analyst: chat, cards, delegation, payment tier, brief |
| `hp_agents/specialists.py` | Mobility, Local Economy and Equity agents |
| `hp_agents/analysis.py` | What each specialist says (pure functions over engine results) |
| `hp_agents/streets.py` | Street-name index, cross streets, stretch → edge ids, POIs on a stretch |
| `hp_agents/parse.py`, `llm.py` | Request parsing (regex, ASI:One fallback); brief summary |
| `hp_agents/sim.py` | Engine API client |
| `run.py`, `register.py`, `test_conversation.py` | Run (local or `--live`), register, scripted test |
| `profiles/*.md` | Agentverse profile READMEs (ASI:One discovery reads these) |

## Limits

- Car-free plans only (`pedestrianized`). The engine also supports density, rezoning and pricing edits, which the agents don't expose yet.
- The model covers FiDi and SoMa only. A street outside it gets the example carousel.
- One simulated weekday, settled over five replanning days. The answer shows the settle gap (about 5% for 2nd St).
- Hours can't be set: a closure lasts all day.
- The 3D replay link needs a public URL in `HP_REPLAY_URL`. The frontend on `:8765` is local only.

## Demo video script (3–5 min)

**0:00–0:20 Hook.** Screen: the 3D city (optional), then ASI:One.
> "Every street closure in San Francisco goes through a hearing where people argue from gut feel. We built a simulated city of 220,000 people, and made it usable from a chat with ASI:One."

**0:20–0:50 Discovery.** ASI:One with Agents on. Type: *"What happens if 2nd St goes car-free?"*
> "ASI:One finds our SF Street Analyst on Agentverse. It only named a street, so the agent asks which stretch, with an interactive card listing the real cross streets in order."

Show the form card and pick Market → Folsom. If cards don't render, type *"make 2nd St car-free between Market and Folsom"*.

**0:50–1:50 The answer.** Scroll slowly.
> "The analyst hands the plan to three specialist agents: Mobility, Local Economy and Equity. Each one runs the scenario on our simulation engine. The headline is $6.4 million a year in net value, mostly health from extra walking and local business."

Point at Mobility:
> "About 9,500 cars a day used each block. Car trips drop by about 590 a day, some people switch to transit, and the cars that remain divert to Howard and the Bay Bridge ramps. Delay to other traffic costs $351k a year, and the agent says so."

Point at Local Economy:
> "The 25 businesses on the stretch gain about 20% in revenue. It names the winners and also the losers."

Point at Equity:
> "Low-income people barely drive here, so the added travel time falls mostly on higher incomes. The agent also flags a cost: neighbour ties drop on the streets that take the diverted traffic."

**1:50–2:30 Grounding.**
> "None of these numbers come from the LLM. Each answer cites the engine scenario id, and our test checks that the chat answer matches a direct engine call field by field." (Optional cut: `test_conversation.py` printing ALL CHECKS PASSED.)

**2:30–3:20 Paid tier.** Click *Hearing brief (2 FET)*.
> "Consultants and merchant associations need something to bring to a hearing. The analyst sends a payment request over the Agent Payment Protocol. Once paid, it delivers a full hearing brief: an executive summary written only from the engine's facts, every value line, the valuation factors, and the assumptions it rests on."

Show the payment approval, then the brief.

**3:20–4:00 Compare.** Type *"turn Kearny into a pedestrian street from Market up to Bush"*.
> "Same question, another street, a different answer: Kearny nets only about $0.6 million, because the mobility costs are much larger. That's the point: compare before you fight about it."

**4:00–4:20 Close.** Show the Agentverse profiles of the four agents.
> "Four agents on Agentverse, the Chat Protocol, Interactive Cards and the Payment Protocol, all used inside ASI:One with no custom frontend. CommonGround."
