"""Typed contracts exchanged between the Boss and the specialist agents.

The Boss delegates with an `AgentRequest` and receives an `AgentResponse`. Both
are structured rather than free text, so the dashboard can render a hand-off, and
so an agent that cannot answer has a field to say so in — `answered=False` plus
`missing` — instead of filling the gap with a guess.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentName(str, Enum):
    BOSS = "boss"
    INVENTORY = "inventory"
    ACCOUNTING = "accounting"
    FACILITIES = "facilities"
    CUSTOMER_SERVICE = "customer_service"


SPECIALISTS: tuple[AgentName, ...] = (
    AgentName.INVENTORY,
    AgentName.ACCOUNTING,
    AgentName.FACILITIES,
    AgentName.CUSTOMER_SERVICE,
)


class ToolCall(BaseModel):
    """One tool invocation, as the agent reports it.

    This is the agent's own account of what it looked up. The authoritative
    record is the run's message history; this exists so the dashboard can show
    which facts were read rather than reasoned.
    """

    tool: str = Field(description="Tool name, e.g. get_product_info")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Arguments passed to the tool"
    )
    note: str = Field(description="What this call established, in one sentence")


class AgentRequest(BaseModel):
    """A task the Boss sends to one specialist."""

    to_agent: AgentName
    task: str = Field(description="What the specialist is being asked to do")
    context: str = Field(
        default="", description="Facts already established, so the work is not repeated"
    )
    ticket_id: int | None = Field(
        default=None, description="Ticket this task belongs to, when there is one"
    )


class ApprovalRequest(BaseModel):
    """A money or discount decision that a human must make.

    Agents never execute these. Business rule 4 requires human approval for any
    payment, and the schema enforces it too — `payments.approved_by` is NOT NULL.
    """

    kind: Literal[
        "invoice_payment",
        "rent_payment",
        "purchase_order",
        "price_override",
        "other",
    ]
    description: str = Field(description="What is being proposed, in plain words")
    amount: float | None = Field(default=None, description="Amount in dollars")
    ref_id: int | None = Field(
        default=None, description="Invoice id for an invoice payment, lease id for rent"
    )
    account: str | None = Field(default=None, description="Account it would be paid from")
    cash_before: float | None = None
    cash_after: float | None = Field(
        default=None, description="Balance if approved; must never be negative"
    )
    rationale: str = Field(description="Why this is being recommended")
    blocks: list[str] = Field(
        default_factory=list,
        description="What stays blocked until this is approved, e.g. a vendor that cannot ship",
    )
    requires_human: Literal[True] = True


class AgentResponse(BaseModel):
    """A specialist's structured answer back to the Boss."""

    agent: AgentName
    answered: bool = Field(
        description="True only if the task was answered from tool data. False when "
        "the information was unavailable — say so rather than guessing."
    )
    summary: str = Field(description="The answer in one or two sentences")
    findings: list[str] = Field(
        default_factory=list, description="Specific facts established, each traceable to a tool call"
    )
    tool_calls: list[ToolCall] = Field(
        default_factory=list, description="Tools actually called while answering"
    )
    missing: list[str] = Field(
        default_factory=list,
        description="What could not be determined, and why. Populate this instead of inventing.",
    )
    approvals_required: list[ApprovalRequest] = Field(
        default_factory=list, description="Money or discount decisions needing a human"
    )
    draft_message: str | None = Field(
        default=None,
        description="Customer-facing draft, when one was asked for. Never sent — it stays on the board.",
    )


class BossDecision(BaseModel):
    """The Boss's choice at one turn of the orchestration loop."""

    action: Literal["delegate", "answer"] = Field(
        description="'delegate' to send work to specialists, 'answer' when enough is known"
    )
    reasoning: str = Field(description="Why this routing, in one or two sentences")
    requests: list[AgentRequest] = Field(
        default_factory=list,
        description="Tasks to dispatch. Send every specialist needed in one round — they run in parallel.",
    )


class FinalAnswer(BaseModel):
    """The Boss's verified response to the user."""

    answer: str = Field(description="The response to the user")
    sufficient: bool = Field(
        description="False if the question could not be fully answered from available data"
    )
    agents_consulted: list[AgentName] = Field(default_factory=list)
    unresolved: list[str] = Field(
        default_factory=list, description="Anything that could not be determined"
    )
    approvals_required: list[ApprovalRequest] = Field(default_factory=list)


class TranscriptEntry(BaseModel):
    """One delegation and the response it produced."""

    iteration: int
    request: AgentRequest
    response: AgentResponse


class RunResult(BaseModel):
    """Everything one user request produced — the dashboard renders this."""

    user_request: str
    final: FinalAnswer
    iterations_used: int
    hit_iteration_limit: bool = Field(
        description="True if the loop stopped on the cap rather than because the Boss was satisfied"
    )
    transcript: list[TranscriptEntry] = Field(default_factory=list)
    model: str
