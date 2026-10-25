"""Scripted ASI:One-style conversation with the SF Street Analyst, fully local.

A stand-in "user" agent speaks the Chat Protocol (and the buyer side of the Payment Protocol)
to the analyst inside one Bureau. Nothing is registered. Needs the engine on :8787.

    python test_conversation.py        # writes tests/transcript.md, exits non-zero on failure
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HP_SKIP_PAYMENT_VERIFY", "1")  # the stand-in user pays with a fake tx id

from uagents import Agent, Bureau, Context, Protocol  # noqa: E402
from uagents_core.contrib.protocols.chat import (  # noqa: E402
    ChatAcknowledgement, ChatMessage, MetadataContent, TextContent, chat_protocol_spec,
)
from uagents_core.contrib.protocols.chat.cards import create_card_response_content, extract_card  # noqa: E402
from uagents_core.contrib.protocols.payment import (  # noqa: E402
    CancelPayment, CommitPayment, CompletePayment, RequestPayment, payment_protocol_spec,
)

from hp_agents import sim  # noqa: E402
from hp_agents.streets import load_index  # noqa: E402
from run import OFFLINE_AGENTVERSE, build  # noqa: E402

OUT = Path(__file__).parent / "tests" / "transcript.md"
TARGET = "make 2nd St car-free between Market and Folsom"

analyst, specialists = build()
user = Agent(name="test-user", seed="hp-local-test-user-not-registered", agentverse=OFFLINE_AGENTVERSE)
chat = Protocol(spec=chat_protocol_spec)
buyer = Protocol(spec=payment_protocol_spec, role="buyer")
inbox: asyncio.Queue = asyncio.Queue()
log: list[str] = []
payment_requests: list[RequestPayment] = []


def render(msg: ChatMessage) -> str:
    out = []
    for c in msg.content:
        if isinstance(c, TextContent):
            out.append(c.text)
        elif isinstance(c, MetadataContent) and (card := extract_card(c)):
            out.append(f"[card: {card.payload.__class__.__name__}] "
                       + card.payload.model_dump_json(exclude_none=True)[:400])
    return "\n".join(out)


@chat.on_message(ChatMessage)
async def on_reply(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(acknowledged_msg_id=msg.msg_id))
    await inbox.put(("chat", msg))


@chat.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


@buyer.on_message(RequestPayment)
async def on_request_payment(ctx: Context, sender: str, msg: RequestPayment):
    await inbox.put(("pay", msg))


@buyer.on_message(CompletePayment)
async def on_complete(ctx: Context, sender: str, msg: CompletePayment):
    await inbox.put(("complete", msg))


@buyer.on_message(CancelPayment)
async def on_cancel(ctx: Context, sender: str, msg: CancelPayment):
    await inbox.put(("cancel", msg))


user.include(chat)
user.include(buyer)


async def say(ctx: Context, *content, label: str) -> ChatMessage:
    log.append(f"## User\n{label}\n")
    print(f"[test] user: {label}", flush=True)
    t0 = time.time()
    await ctx.send(analyst.address, ChatMessage(content=list(content)))
    while True:
        kind, msg = await asyncio.wait_for(inbox.get(), 120)
        print(f"[test] got {kind} after {time.time() - t0:.1f}s", flush=True)
        if kind == "chat":
            log.append(f"## SF Street Analyst ({time.time() - t0:.1f}s)\n{render(msg)}\n")
            return msg
        log.append(f"## SF Street Analyst → payment protocol\n`{type(msg).__name__}` {msg.model_dump_json()[:300]}\n")
        if kind == "pay":
            payment_requests.append(msg)


def check(cond: bool, what: str, failures: list[str]):
    log.append(f"- {'PASS' if cond else 'FAIL'}: {what}\n")
    if not cond:
        failures.append(what)


@user.on_event("startup")
async def script(ctx: Context):
    failures: list[str] = []
    try:
        await asyncio.sleep(1)
        log.append(f"# Test conversation with {analyst.name} (`{analyst.address}`)\n")

        m = await say(ctx, TextContent(text="hi, what can you do?"), label="hi, what can you do?")
        check("2nd St" in render(m) and "carousel" in render(m).lower(), "help text with example carousel", failures)

        m = await say(ctx, TextContent(text="What if 2nd St goes car-free?"), label="What if 2nd St goes car-free?")
        check("Form" in render(m) and "Folsom" in render(m), "asks which stretch with a form card", failures)

        m = await say(ctx, TextContent(text=TARGET), label=TARGET)
        reply = render(m)
        # Grounding: the numbers in the answer must be the engine's numbers for the same edges.
        world = await sim.world()
        edges = load_index(frozenset(world["editable_edges"])).stretch("2nd Street", "Market Street", "Folsom Street").edges
        plan = await sim.pedestrianize(edges)
        from hp_agents.analysis import usd
        check(usd(plan["value"]["total"]) in reply, f"total {usd(plan['value']['total'])} matches engine value.total", failures)
        check(plan["id"] in reply, f"cites engine scenario {plan['id']}", failures)
        check(f"car {plan['delta']['trips']['car']:+,.0f}" in reply, "car-trip delta matches engine delta.trips.car", failures)
        check(all(s in reply for s in ("**Mobility**", "**Local economy**", "**Equity")),
              "all three specialists answered", failures)
        check("low income" in reply, "equity section uses metrics.by_income", failures)

        detail = next(extract_card(c) for c in m.content if isinstance(c, MetadataContent) and extract_card(c))
        m = await say(ctx, create_card_response_content(card_id=detail.card_id, selection={"action": "brief"}),
                      label='[clicks card CTA "Hearing brief"]')
        check("payment request" in render(m), "brief is offered via the Payment Protocol", failures)

        # The RequestPayment arrived before the chat text; pay it.
        req = payment_requests[-1]
        log.append(f"## User → payment protocol\n`CommitPayment` {req.accepted_funds[0]}\n")
        await ctx.send(analyst.address, CommitPayment(
            funds=req.accepted_funds[0], recipient=req.recipient,
            transaction_id="LOCAL-TEST-TX", reference=req.reference))
        kinds = []
        while "chat" not in kinds:
            kind, msg = await asyncio.wait_for(inbox.get(), 120)
            kinds.append(kind)
            log.append(f"## SF Street Analyst ({kind})\n{render(msg) if kind == 'chat' else msg.model_dump_json()}\n")
        check("complete" in kinds, "CompletePayment sent", failures)
        check("# Hearing brief" in render(msg) and "Value lines" in render(msg), "hearing brief delivered", failures)

        text = "turn Kearny into a pedestrian street from Market up to Bush"
        m = await say(ctx, TextContent(text=text), label=text)
        check("Kearny Street between Market Street and Bush Street" in render(m), "second street works", failures)
    except Exception as e:
        failures.append(f"{type(e).__name__}: {e}")
        log.append(f"- FAIL: exception {type(e).__name__}: {e}\n")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(log))
    print("\n".join(log))
    print(f"\n{'FAILED: ' + '; '.join(failures) if failures else 'ALL CHECKS PASSED'} (transcript: {OUT})")
    sys.stdout.flush()
    os._exit(1 if failures else 0)


if __name__ == "__main__":
    Bureau(agents=[analyst, *specialists.values(), user], port=int(os.getenv("HP_TEST_PORT", "8011")),
           agentverse=OFFLINE_AGENTVERSE).run()
