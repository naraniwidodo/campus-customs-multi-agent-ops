"""Accounting specialist — cash, invoices, margins, payments prepared for approval."""

from __future__ import annotations

from pydantic_ai import Agent

from config import AGENT_RETRIES, SPECIALIST_CONTRACT, build_model, build_toolset, load_prompt
from models import AgentResponse

#: Accounting also reads product pricing: unit cost and list price live in the
#: pricing table, which `get_product_info` returns, and margin questions on a
#: discount need them. Without this the agent could not answer a price override.
TOOLS = (
    "get_financial_info",
    "get_product_info",
    "get_vendor_info",
    "record_discount_decision",
)

accounting_agent = Agent(
    build_model(),
    output_type=AgentResponse,
    instructions=load_prompt("accounting.md") + SPECIALIST_CONTRACT,
    toolsets=[build_toolset(TOOLS)],
    name="accounting",
    retries=AGENT_RETRIES,
)
