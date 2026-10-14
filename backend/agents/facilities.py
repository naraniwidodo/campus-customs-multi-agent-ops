"""Facilities specialist — the shop space, leases and rent."""

from __future__ import annotations

from pydantic_ai import Agent

from config import AGENT_RETRIES, SPECIALIST_CONTRACT, build_model, build_toolset, load_prompt
from models import AgentResponse

#: Leases are the only facilities data that exists. There are no tables for
#: warehouses, equipment, maintenance or shipment tracking, and the prompt tells
#: the agent to say so rather than estimate.
TOOLS = ("get_lease_info",)

facilities_agent = Agent(
    build_model(),
    output_type=AgentResponse,
    instructions=load_prompt("facilities.md") + SPECIALIST_CONTRACT,
    toolsets=[build_toolset(TOOLS)],
    name="facilities",
    retries=AGENT_RETRIES,
)
