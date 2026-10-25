"""SF Street Analyst: the ASI:One-facing orchestrator.

Chat Protocol in, three specialists out (Mobility, Local Economy, Equity), one grounded answer
back, with Interactive Cards for picking a stretch and a Payment Protocol tier for the brief.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone

import httpx
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    MetadataContent,
    TextContent,
    chat_protocol_spec,
)
from uagents_core.contrib.protocols.chat.cards import (
    CarouselCardPayload,
    CarouselItem,
    CtaAction,
    DetailCardPayload,
    DetailSummaryRow,
    FormCardPayload,
    FormField,
    FormFieldOption,
    create_card_content,
    extract_card_response,
)
from uagents_core.contrib.protocols.payment import (
    CancelPayment,
    CommitPayment,
    CompletePayment,
    Funds,
    RejectPayment,
    RequestPayment,
    payment_protocol_spec,
)

from . import llm, sim
from .analysis import PILLARS, usd
from .config import BRIEF_CURRENCY, BRIEF_PRICE_FET, FETCH_DIR, REPLAY_URL, SIM_API, seed
from .models import AnalyzeRequest, AnalyzeResponse
from .parse import parse_stretch, wants_brief
from .streets import Stretch, load_index

NAME = "SF Street Analyst"
DESCRIPTION = ("Ask what happens if a San Francisco street in FiDi or SoMa goes car-free. Runs an agent-based "
               "city sim and returns $/yr by pillar, traffic diversion, business revenue and who wins or loses.")
EXAMPLES = [("2nd Street", "Market Street", "Folsom Street"),
            ("Howard Street", "2nd Street", "4th Street"),
            ("Kearny Street", "Market Street", "Bush Street"),
            ("Folsom Street", "2nd Street", "5th Street")]
SPECIALIST_TIMEOUT_S = 90
PLAN_WORDS = re.compile(r"car.?free|pedestrian|close|closure|ban cars|plaza|street|\bst\b|avenue", re.I)
HELP = ("I'm the **SF Street Analyst**. I run CommonGround's agent-based sim of SF's Financial District "
        "and SoMa (≈220k people a day) and tell you what a car-free street does to traffic, local business, "
        "health and equity, in dollars per year.\n\nTry: *make 2nd St car-free between Market and Folsom*.")


def _text(*parts: str) -> TextContent:
    return TextContent(text="\n\n".join(p for p in parts if p))


def _short(name: str) -> str:
    return name.replace(" Street", " St").replace(" Avenue", " Ave")


def _card_selection(msg: ChatMessage) -> dict | None:
    for c in msg.content:
        if isinstance(c, MetadataContent):
            r = extract_card_response(c)
            if r is not None:
                return {"action": "cancel"} if r.cancelled else dict(r.selection or {})
    raw = msg.text().strip()
    if raw.startswith("{"):  # older clients send the CTA selection as JSON text
        try:
            d = json.loads(raw)
            return d if isinstance(d, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def make_analyst(specialists: dict[str, str], **agent_kwargs) -> Agent:
    """`specialists` maps mobility|economy|equity to agent addresses."""
    readme = FETCH_DIR / "profiles" / "analyst.md"
    agent = Agent(name=NAME, seed=seed("analyst"), description=DESCRIPTION,
                  readme_path=str(readme) if readme.exists() else None,
                  handle_messages_concurrently=True, **agent_kwargs)
    chat = Protocol(spec=chat_protocol_spec)
    pay = Protocol(spec=payment_protocol_spec, role="seller")
    street = Protocol(name="HPStreetAnalysis", version="0.1.0")
    pending: dict[str, dict] = {}

    # ---- specialists -----------------------------------------------------
    @street.on_message(AnalyzeResponse)
    async def on_part(ctx: Context, sender: str, resp: AnalyzeResponse):
        job = pending.get(resp.request_id)
        ctx.logger.info(f"{resp.specialist} answered{' with error ' + resp.error if resp.error else ''}")
        if job is None:
            return
        job["parts"][resp.specialist] = resp
        if len(job["parts"]) == len(specialists):
            job["done"].set()

    async def run_plan(ctx: Context, stretch: Stretch) -> dict:
        rid = uuid.uuid4().hex
        pending[rid] = job = {"parts": {}, "done": asyncio.Event()}
        req = AnalyzeRequest(request_id=rid, label=stretch.label, edges=stretch.edges)
        for addr in specialists.values():
            await ctx.send(addr, req)
        try:
            await asyncio.wait_for(job["done"].wait(), SPECIALIST_TIMEOUT_S)
        except asyncio.TimeoutError:
            ctx.logger.warning(f"specialists missing: {set(specialists) - set(job['parts'])}")
        pending.pop(rid, None)
        parts = job["parts"]
        facts = {k: json.loads(p.facts_json) for k, p in parts.items() if not p.error}
        value = {}
        for k, f in facts.items():
            value |= {key.split(".", 1)[1]: v for key, v in f.items() if key.startswith("value.")}
        scenario_id = next((p.scenario_id for p in parts.values() if p.scenario_id), "")
        settle = next((f["settle"] for f in facts.values() if "settle" in f), {})
        return {"label": stretch.label, "street": stretch.street, "edges": stretch.edges,
                "length_m": stretch.length_m, "scenario_id": scenario_id, "settle": settle,
                "value": value, "total": sum(value.get(p, 0) for p in PILLARS),
                "sections": {k: (p.markdown if not p.error else f"_{k} agent failed: {p.error}_")
                             for k, p in parts.items()},
                "missing": sorted(set(specialists) - set(parts)), "facts": facts}

    def result_contents(r: dict) -> list:
        v = r["value"]
        conv = ("converged" if r["settle"].get("converged")
                else f"settled to a {r['settle'].get('gap', 0):.0%} gap") if r["settle"] else ""
        head = (f"### Car-free {r['label']}\n"
                f"**Net value to the city: {usd(r['total'])}** vs today. "
                + " · ".join(f"{p} {usd(v.get(p, 0), '')}" for p in PILLARS)
                + f"\n_Engine scenario `{r['scenario_id']}` over {r['length_m']:.0f} m, "
                  f"{r['settle'].get('days', '?')} simulated days, {conv}._")
        order = [k for k in ("mobility", "economy", "equity") if k in r["sections"]]
        missing = f"_No answer from: {', '.join(r['missing'])}._" if r["missing"] else ""
        replay = f"[Replay it in 3D]({REPLAY_URL.format(id=r['scenario_id'])})" if REPLAY_URL else ""
        more = (f"Want the **full hearing brief** (every value line, sources, assumptions, and an executive "
                f"summary)? Say *hearing brief*: it costs {BRIEF_PRICE_FET} {BRIEF_CURRENCY}.")
        card = create_card_content(DetailCardPayload(
            title=f"Car-free {_short(r['street'])}: {usd(r['total'])}",
            summary_rows=[DetailSummaryRow(label=p.title(), value=usd(v.get(p, 0))) for p in PILLARS]
                         + [DetailSummaryRow(label="Total", value=usd(r["total"]))],
            ctas=[CtaAction(label=f"Hearing brief ({BRIEF_PRICE_FET} {BRIEF_CURRENCY})",
                            selection={"action": "brief"}, primary=True),
                  CtaAction(label="Try another stretch", selection={"action": "pick", "street": r["street"]})],
        ), card_id=uuid.uuid4())
        return [_text(head, *(r["sections"][k] for k in order), missing, replay, more), card]

    # ---- cards -------------------------------------------------------------
    def pick_contents(index, street_name: str, note: str = "") -> list:
        crosses = index.cross_streets(street_name)
        opts = [FormFieldOption(value=c, label=_short(c)) for c in crosses]
        card = create_card_content(FormCardPayload(
            title=f"Which stretch of {_short(street_name)}?",
            fields=[FormField(name="from_cross", kind="select", label="From", required=True, options=opts),
                    FormField(name="to_cross", kind="select", label="To", required=True, options=opts)],
            submit_cta=CtaAction(label="Run the sim", selection={"action": "run", "street": street_name},
                                 primary=True),
        ), card_id=uuid.uuid4())
        listed = ", ".join(_short(c) for c in crosses)
        return [_text(note, f"Which stretch of **{street_name}**? It crosses (in order): {listed}.",
                      f"Reply like *{_short(street_name)} between {_short(crosses[0])} and "
                      f"{_short(crosses[min(3, len(crosses) - 1)])}*, or pick in the card."), card]

    def examples_contents(index, note: str = HELP) -> list:
        items = []
        for s, a, b in EXAMPLES:
            try:
                st = index.stretch(s, a, b)
            except ValueError:
                continue
            items.append(CarouselItem(
                id=f"{s}|{a}|{b}", title=f"{_short(s)}", subtitle=f"{_short(a)} → {_short(b)}",
                secondary_text=f"{st.length_m:.0f} m, {len(st.edges)} road segments",
                primary_cta=CtaAction(label="Make it car-free",
                                      selection={"action": "run", "street": s, "from_cross": a, "to_cross": b})))
        card = create_card_content(CarouselCardPayload(title="Try a street", items=items), card_id=uuid.uuid4())
        return [_text(note), card]

    # ---- chat ------------------------------------------------------------
    async def answer(ctx: Context, sender: str, msg: ChatMessage) -> list:
        world = await sim.world()
        index = load_index(frozenset(world["editable_edges"]))
        sel = _card_selection(msg) or {}
        text = "" if sel else msg.text().strip()
        action = sel.get("action")
        if action == "cancel":
            return [_text("No problem. Ask about any FiDi or SoMa street whenever you like.")]
        if action == "brief" or (text and wants_brief(text) and not index.mentions(text)):
            return await offer_brief(ctx, sender)
        if action == "pick":
            return pick_contents(index, sel["street"])
        if action == "run":
            want = {k: index.canonical(sel.get(k)) for k in ("street", "from_cross", "to_cross")}
        elif text:
            want = await parse_stretch(text, index, use_llm=bool(PLAN_WORDS.search(text)))
        else:
            return examples_contents(index)
        if not want["street"]:
            if not PLAN_WORDS.search(text):
                return examples_contents(index)
            return examples_contents(index, "I couldn't find a street in the model area (FiDi + SoMa) in that. "
                                            "Here are a few to try, or name one.")
        if not (want["from_cross"] and want["to_cross"]):
            return pick_contents(index, want["street"])
        if want["from_cross"] == want["to_cross"]:
            return pick_contents(index, want["street"], "Pick two different cross streets.")
        try:
            stretch = index.stretch(want["street"], want["from_cross"], want["to_cross"])
        except ValueError as e:
            return pick_contents(index, want["street"], str(e))
        r = await run_plan(ctx, stretch)
        if not r["sections"]:
            return [_text(f"The sim didn't answer in time for {stretch.label}. Is the engine up at {SIM_API}?")]
        ctx.storage.set(f"last:{sender}", {k: r[k] for k in ("label", "street", "edges", "scenario_id",
                                                              "sections", "facts", "value", "total")})
        return result_contents(r)

    @chat.on_message(ChatMessage)
    async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
        await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(timezone.utc),
                                                   acknowledged_msg_id=msg.msg_id))
        kinds = ",".join(c.type for c in msg.content)
        ctx.logger.info(f"Received chat from {sender[:16]}… [{kinds}] {msg.text()[:160]!r}")
        if not msg.text().strip() and not any(isinstance(c, MetadataContent) for c in msg.content):
            return  # start-session / end-session only
        try:
            contents = await answer(ctx, sender, msg)
        except httpx.HTTPError as e:
            contents = [_text(f"The city sim at {SIM_API} isn't reachable right now ({type(e).__name__}). "
                              "Start it with `backend/run.sh` and ask again.")]
        except Exception as e:
            ctx.logger.exception("answer failed")
            contents = [_text(f"Something went wrong on my side ({type(e).__name__}). Please try again.")]
        status = await ctx.send(sender, ChatMessage(content=contents))
        ctx.logger.info(f"Replied to {sender[:16]}… [{','.join(c.type for c in contents)}] -> {status.status}")

    @chat.on_message(ChatAcknowledgement)
    async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        pass

    # ---- payment tier: the hearing brief -----------------------------------
    async def offer_brief(ctx: Context, sender: str) -> list:
        last = ctx.storage.get(f"last:{sender}")
        if not last:
            return [_text("Run a plan first (e.g. *2nd St car-free between Market and Folsom*), "
                          "then I can write its hearing brief.")]
        ref = f"brief-{last['scenario_id']}-{uuid.uuid4().hex[:8]}"
        ctx.storage.set(f"pay:{sender}", ref)
        await ctx.send(sender, RequestPayment(
            accepted_funds=[Funds(amount=BRIEF_PRICE_FET, currency=BRIEF_CURRENCY, payment_method="fet_direct")],
            recipient=str(agent.wallet.address()), deadline_seconds=600, reference=ref,
            description=f"Hearing brief: car-free {last['label']}",
            metadata={"scenario_id": last["scenario_id"]},
        ))
        return [_text(f"The hearing brief for **car-free {last['label']}** is {BRIEF_PRICE_FET} {BRIEF_CURRENCY}. "
                      "I've sent a payment request; approve it and the brief follows here.")]

    def _verify_fet(tx_id: str, amount: str) -> bool:
        if os.getenv("HP_SKIP_PAYMENT_VERIFY") == "1":
            return True
        try:
            tx = agent.ledger.query_tx(tx_id)
        except Exception:
            return False
        want = int(float(amount) * 10**18)
        transfer = tx.events.get("transfer", {})
        return (transfer.get("recipient") == str(agent.wallet.address())
                and transfer.get("amount") in {f"{want}afet", f"{want}atestfet"})

    @pay.on_message(CommitPayment)
    async def on_commit(ctx: Context, sender: str, msg: CommitPayment):
        ref = ctx.storage.get(f"pay:{sender}")
        last = ctx.storage.get(f"last:{sender}")
        if not ref or msg.reference != ref or not last:
            await ctx.send(sender, CancelPayment(transaction_id=msg.transaction_id, reason="Unknown payment reference"))
            return
        if not await asyncio.to_thread(_verify_fet, msg.transaction_id, msg.funds.amount):
            await ctx.send(sender, CancelPayment(transaction_id=msg.transaction_id,
                                                 reason="Couldn't verify the transfer on the ledger"))
            return
        ctx.storage.set(f"pay:{sender}", None)
        await ctx.send(sender, CompletePayment(transaction_id=msg.transaction_id))
        brief = await write_brief(last)
        await ctx.send(sender, ChatMessage(content=[_text(brief), EndSessionContent()]))

    @pay.on_message(RejectPayment)
    async def on_reject(ctx: Context, sender: str, msg: RejectPayment):
        ctx.storage.set(f"pay:{sender}", None)
        await ctx.send(sender, ChatMessage(content=[_text("No brief then. The summary above is free to use.")]))

    async def write_brief(last: dict) -> str:
        async with httpx.AsyncClient(timeout=60) as c:
            full = (await c.get(f"{SIM_API}/scenario/{last['scenario_id']}", params={"lite": 1})).json()
        summary = await llm.brief_summary(last["label"], {"value": last["value"], "total": last["total"],
                                                           **last["facts"]})
        lines = "\n".join(f"| {l['pillar']} | {l['label']} | {l['qty']:,.2f} {l['unit']} | {usd(l['usd_per_yr'])} |"
                          for l in full["value"]["lines"] if abs(l["usd_per_yr"]) >= 1)
        assumptions = "\n".join(f"- `{a['key']}` ({a['status']}): {a.get('note', '')[:220]}"
                                for a in full.get("assumptions", [])[:15])
        factors = ", ".join(f"{k} = {v}" for k, v in full["value"].get("factors", {}).items())
        return "\n\n".join(x for x in [
            f"# Hearing brief: car-free {last['label']}",
            f"_Prepared by {NAME} from CommonGround engine scenario `{last['scenario_id']}`. "
            f"Every figure below is an engine output._",
            f"## Executive summary\n{summary}" if summary else "",
            f"## Bottom line\n**{usd(last['total'])}** net value per year: "
            + ", ".join(f"{p} {usd(last['value'].get(p, 0))}" for p in PILLARS) + ".",
            *(last["sections"][k] for k in ("mobility", "economy", "equity") if k in last["sections"]),
            f"## Value lines\n| Pillar | Line | Quantity | $/yr |\n|---|---|---|---|\n{lines}",
            f"## Valuation factors\n{factors}",
            f"## Key assumptions (first 15 of {len(full.get('assumptions', []))})\n{assumptions}",
            "## Limits\nOne simulated weekday, settled over several days of replanning. Values are social "
            "value estimates for comparison, not a budget forecast.",
        ] if x)

    live = bool(agent_kwargs.get("mailbox"))
    agent.include(chat, publish_manifest=live)
    agent.include(pay, publish_manifest=live)
    agent.include(street, publish_manifest=False)
    return agent
