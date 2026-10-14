"""Boss agent — leader and orchestrator of the Campus Customs team.

The flow is:

    user -> Boss -> specialists (which use tools) -> Boss (verify) -> user

The Boss is the only agent that routes. Specialists answer within their own
domain and hand the result back; they never choose who works next. That keeps one
decision-maker, makes every hand-off a recorded event, and stops two agents from
delegating to each other in a circle.

Two Boss calls do distinct jobs. `boss_router` decides, each round, whether to
delegate and to whom. `boss_finalizer` writes and verifies the answer once. They
are separate agents because their output types differ, and because the router is
re-run per round while the finaliser runs once.
"""

from __future__ import annotations

import asyncio
import time
from uuid import uuid4

from pydantic_ai import Agent

from audit import AuditTrail, extract_tool_calls, read_shop_date

from config import AGENT_RETRIES, MAX_ITERATIONS, build_model, build_toolset, load_prompt
from models import (
    AgentName,
    AgentRequest,
    AgentResponse,
    BossDecision,
    FinalAnswer,
    RunResult,
    TranscriptEntry,
)

from .accounting import accounting_agent
from .customer_service import customer_service_agent
from .facilities import facilities_agent
from .inventory import inventory_agent

_BOSS_PROMPT = load_prompt("boss.md")

SPECIALIST_AGENTS: dict[AgentName, Agent] = {
    AgentName.INVENTORY: inventory_agent,
    AgentName.ACCOUNTING: accounting_agent,
    AgentName.FACILITIES: facilities_agent,
    AgentName.CUSTOMER_SERVICE: customer_service_agent,
}

_ROUTER_CONTRACT = f"""

---

## This turn

Decide whether to delegate or to answer.

- `action="delegate"` — put every specialist you need into `requests` **in this
  one round**. They run in parallel, so one round with three requests costs far
  less time than three rounds with one each.
- `action="answer"` — you have enough to respond. Leave `requests` empty.

Delegate only to **inventory**, **accounting**, **facilities** or
**customer_service**. Never delegate to yourself — you are the Boss, and a request
addressed to "boss" does nothing but burn a round. When the remaining work is
yours, choose `action="answer"`.

You have at most {MAX_ITERATIONS} rounds. If a specialist has already reported it
cannot answer something, do not ask again — accept it and answer with what you
have, noting the gap.

Give each specialist the facts already established in `context`, so it does not
repeat a lookup another specialist has already done.

**Never answer while a shortfall has no restock order against it.** If a
specialist reports stock short of what a ticket needs and no order has been
drafted, delegate to **inventory** to draft one before you answer. A reply that
says "a human must approve a purchase order" when no purchase order exists leaves
the human nothing to approve, and the ticket cannot progress.

**Before you choose `action="answer"`, set the ticket's status.** Call
`update_ticket_status` — with `closed` if the work looks finished, and the tool
will refuse and explain if it is not; with `pending` or `blocked` otherwise. A
ticket the team has worked should never be left at `open`.
"""

_FINALIZER_CONTRACT = """

---

## This turn

Write the final response to the user, and verify it before returning.

Every factual claim must trace to a specialist's finding. If no specialist
established something, it does not go in the answer — put it in `unresolved`
instead.

Set `sufficient=False` if the request could not be fully answered, and say so in
the answer itself rather than implying success.

Carry every approval a specialist raised into `approvals_required`. Describe
payments as *awaiting approval*, never as made.
"""

#: The Boss reads the board it routes from, and records where each ticket stands.
#: `update_ticket_status` refuses to close a ticket whose outcome is not verifiable
#: in the database, so "mark it done" is not something the Boss can talk its way
#: into. It owns no financial or product tool -- those belong to the specialists.
BOSS_TOOLS = ("get_ticket_info", "update_ticket_status")

boss_router = Agent(
    build_model(),
    output_type=BossDecision,
    instructions=_BOSS_PROMPT + _ROUTER_CONTRACT,
    toolsets=[build_toolset(BOSS_TOOLS)],
    name="boss_router",
    retries=AGENT_RETRIES,
)

boss_finalizer = Agent(
    build_model(),
    output_type=FinalAnswer,
    instructions=_BOSS_PROMPT + _FINALIZER_CONTRACT,
    name="boss_finalizer",
    retries=AGENT_RETRIES,
)


def _render_transcript(entries: list[TranscriptEntry]) -> str:
    """The work so far, as the Boss sees it between rounds."""
    if not entries:
        return "No specialist has reported yet."

    lines: list[str] = []
    for entry in entries:
        r = entry.response
        lines.append(f"--- round {entry.iteration}: {r.agent.value} ---")
        lines.append(f"task: {entry.request.task}")
        lines.append(f"answered: {r.answered}")
        lines.append(f"summary: {r.summary}")
        for finding in r.findings:
            lines.append(f"  finding: {finding}")
        for call in r.tool_calls:
            lines.append(f"  tool: {call.tool}({call.arguments}) -> {call.note}")
        for gap in r.missing:
            lines.append(f"  MISSING: {gap}")
        for approval in r.approvals_required:
            lines.append(
                f"  APPROVAL NEEDED: {approval.kind} {approval.amount} — {approval.description}"
            )
        if r.draft_message:
            lines.append(f"  draft: {r.draft_message}")
    return "\n".join(lines)


async def _run_specialist(
    request: AgentRequest, trail: AuditTrail, iteration: int
) -> AgentResponse:
    """Dispatch one task, and turn a failure into an honest response.

    A specialist that raises — a tool error, a validation failure — must not take
    the whole run down. It comes back as `answered=False` with the reason, which
    is the same shape the Boss handles for "I could not find this".
    """
    await trail.append(
        "delegation",
        iteration=iteration,
        from_agent="boss",
        to_agent=request.to_agent.value,
        task=request.task,
        context=request.context,
        ticket_id=request.ticket_id,
    )

    agent = SPECIALIST_AGENTS.get(request.to_agent)
    if agent is None:
        return AgentResponse(
            agent=request.to_agent,
            answered=False,
            summary=f"No such specialist: {request.to_agent}",
            missing=[f"Unknown agent {request.to_agent}"],
        )

    prompt = f"Task: {request.task}"
    if request.context:
        prompt += f"\n\nFacts already established:\n{request.context}"
    if request.ticket_id is not None:
        prompt += f"\n\nThis task belongs to ticket {request.ticket_id}."

    started = time.monotonic()
    try:
        result = await agent.run(prompt)
        response = result.output
        tool_calls = extract_tool_calls(result.all_messages())
    except Exception as exc:  # noqa: BLE001 — surfaced to the Boss, not swallowed
        response = AgentResponse(
            agent=request.to_agent,
            answered=False,
            summary=f"{request.to_agent.value} could not complete the task.",
            missing=[f"{type(exc).__name__}: {exc}"],
        )
        await trail.append(
            "agent_failed",
            iteration=iteration,
            agent=request.to_agent.value,
            task=request.task,
            error=f"{type(exc).__name__}: {exc}",
            elapsed_seconds=round(time.monotonic() - started, 2),
        )
        return response

    # The model fills `agent` from the schema; set it from the routing decision so
    # it is always the agent that actually ran.
    response.agent = request.to_agent

    await trail.append(
        "agent_response",
        iteration=iteration,
        agent=request.to_agent.value,
        task=request.task,
        answered=response.answered,
        summary=response.summary,
        findings=response.findings,
        missing=response.missing,
        # Taken from the message history: what the agent actually called, not
        # what it reported calling.
        tool_calls=tool_calls,
        self_reported_tool_calls=[c.model_dump() for c in response.tool_calls],
        approvals_required=[a.model_dump() for a in response.approvals_required],
        draft_message=response.draft_message,
        elapsed_seconds=round(time.monotonic() - started, 2),
    )
    return response


async def run_boss(
    user_request: str,
    max_iterations: int | None = None,
    run_id: str | None = None,
) -> RunResult:
    """Run one user request through the team and return the whole run.

    Each round is a single router call plus however many specialists it dispatches,
    run concurrently. The loop stops when the Boss says it has enough, when no
    specialist is needed, or at the iteration cap — whichever comes first.
    """
    from config import DB_PATH, MODEL_NAME

    limit = max_iterations or MAX_ITERATIONS
    transcript: list[TranscriptEntry] = []
    consulted: list[AgentName] = []
    iterations = 0
    hit_limit = False

    # The caller may supply the id so its own record and the audit trail agree.
    # Without this the API would hand the dashboard an id that never appears in
    # the trail, and the activity feed would silently stay empty.
    run_id = run_id or uuid4().hex[:12]
    trail = AuditTrail(run_id=run_id, shop_date=read_shop_date())
    started = time.monotonic()

    await trail.append(
        "run_started",
        user_request=user_request,
        model=MODEL_NAME,
        max_iterations=limit,
        database=str(DB_PATH),
        agents_available=[a.value for a in SPECIALIST_AGENTS],
    )

    for iteration in range(1, limit + 1):
        iterations = iteration

        decision_prompt = (
            f"User request:\n{user_request}\n\n"
            f"Work so far:\n{_render_transcript(transcript)}\n\n"
            f"This is round {iteration} of at most {limit}."
        )
        router_result = await boss_router.run(decision_prompt)
        decision = router_result.output

        await trail.append(
            "boss_decision",
            iteration=iteration,
            action=decision.action,
            reasoning=decision.reasoning,
            delegating_to=[r.to_agent.value for r in decision.requests],
            requests=[r.model_dump(mode="json") for r in decision.requests],
            tool_calls=extract_tool_calls(router_result.all_messages()),
        )

        if decision.action == "answer" or not decision.requests:
            break

        # A request addressed to the Boss (or to an unknown name) cannot be served
        # and would otherwise cost a full round. Drop it here, before it is
        # dispatched, and record why.
        dispatchable = [r for r in decision.requests if r.to_agent in SPECIALIST_AGENTS]
        for bad in (r for r in decision.requests if r.to_agent not in SPECIALIST_AGENTS):
            await trail.append(
                "invalid_delegation",
                iteration=iteration,
                to_agent=bad.to_agent.value,
                task=bad.task,
                reason="Not a specialist — the Boss cannot delegate to itself or to "
                "an unknown agent. Request dropped.",
            )
        if not dispatchable:
            # Nothing left to dispatch; answering beats spending another round.
            break

        # Specialists in one round are independent: run them concurrently.
        responses = await asyncio.gather(
            *(
                _run_specialist(request, trail, iteration)
                for request in dispatchable
            )
        )
        for request, response in zip(dispatchable, responses):
            transcript.append(
                TranscriptEntry(iteration=iteration, request=request, response=response)
            )
            if response.agent not in consulted:
                consulted.append(response.agent)
    else:
        # The loop ran to the cap without the Boss choosing to answer.
        hit_limit = True

    final_prompt = (
        f"User request:\n{user_request}\n\n"
        f"Everything the specialists reported:\n{_render_transcript(transcript)}\n\n"
        "Write the final response to the user."
    )
    if hit_limit:
        final_prompt += (
            f"\n\nNote: the {limit}-round limit was reached. Answer with what is "
            "known and state plainly what remains unresolved."
        )

    final_result = await boss_finalizer.run(final_prompt)
    final = final_result.output

    # The Boss reports who it consulted; correct it from what actually ran.
    final.agents_consulted = consulted

    # Carry forward every approval a specialist raised, in case the Boss dropped
    # one. Human approval is required for all payments, so losing one here would
    # silently hide a decision the user has to make.
    seen = {(a.kind, a.ref_id, a.amount) for a in final.approvals_required}
    for entry in transcript:
        for approval in entry.response.approvals_required:
            key = (approval.kind, approval.ref_id, approval.amount)
            if key not in seen:
                final.approvals_required.append(approval)
                seen.add(key)

    await trail.append(
        "final_answer",
        answer=final.answer,
        sufficient=final.sufficient,
        agents_consulted=[a.value for a in final.agents_consulted],
        unresolved=final.unresolved,
        approvals_required=[a.model_dump() for a in final.approvals_required],
        tool_calls=extract_tool_calls(final_result.all_messages()),
    )
    await trail.append(
        "run_finished",
        iterations_used=iterations,
        hit_iteration_limit=hit_limit,
        delegations=len(transcript),
        agents_consulted=[a.value for a in consulted],
        approvals_pending=len(final.approvals_required),
        elapsed_seconds=round(time.monotonic() - started, 2),
    )

    return RunResult(
        user_request=user_request,
        final=final,
        iterations_used=iterations,
        hit_iteration_limit=hit_limit,
        transcript=transcript,
        model=MODEL_NAME,
    )
