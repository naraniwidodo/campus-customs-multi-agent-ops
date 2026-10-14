"""Customer Service specialist — customer and order questions, and message drafts."""

from __future__ import annotations

from pydantic_ai import Agent

from config import (
    AGENT_RETRIES,
    SPECIALIST_CONTRACT,
    build_model,
    build_toolset,
    load_prompt,
)
from models import AgentResponse

#: Customer and order records live in `tickets`, now readable. Drafting saves to
#: the board and sends nothing — there is no send capability anywhere in the
#: server. Product and cash questions stay with Inventory and Accounting.
TOOLS = ("get_ticket_info", "draft_customer_message")

customer_service_agent = Agent(
    build_model(),
    output_type=AgentResponse,
    instructions=load_prompt("customer_service.md") + SPECIALIST_CONTRACT,
    toolsets=[build_toolset(TOOLS)],
    name="customer_service",
    retries=AGENT_RETRIES,
)
