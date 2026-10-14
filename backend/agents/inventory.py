"""Inventory specialist — products, SKUs, stock, sizes, availability, locations."""

from __future__ import annotations

from pydantic_ai import Agent

from config import AGENT_RETRIES, SPECIALIST_CONTRACT, build_model, build_toolset, load_prompt
from models import AgentResponse

#: Stock, plus the vendor side of restocking. Inventory has no reason to read
#: cash or leases. `suggest_vendor_for_sku` returns a suggestion the human must
#: approve, and `draft_restock_po` drafts an order without placing it.
TOOLS = (
    "get_product_info",
    "get_vendor_info",
    "suggest_vendor_for_sku",
    "draft_restock_po",
)

inventory_agent = Agent(
    build_model(),
    output_type=AgentResponse,
    instructions=load_prompt("inventory.md") + SPECIALIST_CONTRACT,
    toolsets=[build_toolset(TOOLS)],
    name="inventory",
    retries=AGENT_RETRIES,
)
