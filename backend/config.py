"""Model, prompt and tool configuration shared by every agent.

Two things are deliberate here.

**The model is pinned to `gpt-6-luna`.** It is read from `MODEL_NAME`, never from
`PORTKEY_MODEL` — the inherited parent `.env` sets `PORTKEY_MODEL=gpt-5.6-luna`,
so reading that variable would silently run the whole team on the wrong model with
no error to reveal it. One constant, imported by all five agents, so none can
drift.

**The API key is never hardcoded.** It is read at runtime from `PORTKEY_API_KEY`
in the nearest `.env`, and nothing in this project writes it to a file or logs it.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
PROMPTS_DIR = BACKEND_DIR / "prompts"

# The key lives one level up, shared across the course. load_dotenv does not
# overwrite variables that are already set, so the nearest file wins.
for candidate in (PROJECT_ROOT / ".env", PROJECT_ROOT.parent / ".env"):
    load_dotenv(candidate)

#: The only model this project uses. See the module docstring.
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-6-luna")

PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")

#: Hard cap on Boss orchestration rounds, so a disagreement cannot loop forever.
#: Each round is one Boss call plus the specialists it dispatches, run in parallel.
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))

#: Per-agent cap on tool-call retries within a single run.
AGENT_RETRIES = int(os.getenv("AGENT_RETRIES", "2"))

# --- MCP server the specialists call -----------------------------------------
MCP_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
MCP_SERVER_SCRIPT = PROJECT_ROOT / "mcp_server" / "server.py"
DB_PATH = Path(
    os.getenv("CAMPUS_DB_PATH", str(PROJECT_ROOT / "data" / "campus_customs_new.db"))
)


def require_api_key() -> str:
    """Return the Portkey key, or raise with a message the UI can show.

    The value is never logged or echoed.
    """
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "PORTKEY_API_KEY is not set. Add it to the .env file in the project "
            "root or one level up."
        )
    return key


def load_prompt(name: str) -> str:
    """Read an agent's prompt from backend/prompts."""
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def build_model():
    """An OpenAI-compatible PydanticAI model pointed at the Portkey gateway.

    Cached so every agent run reuses one client and its connection pool rather
    than opening a fresh one per request.
    """
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
    from pydantic_ai.providers.openai import OpenAIProvider

    client = AsyncOpenAI(api_key=require_api_key(), base_url=PORTKEY_BASE_URL)
    return OpenAIChatModel(
        MODEL_NAME,
        provider=OpenAIProvider(openai_client=client),
        # Required. The gateway rejects function tools on /v1/chat/completions
        # unless reasoning_effort is 'none' ("Function tools with
        # reasoning_effort are not supported for gpt-6-luna"). Every agent
        # here uses function tools -- for MCP tools and for structured output
        # -- so without this the very first call 400s before any work starts.
        settings=OpenAIChatModelSettings(openai_reasoning_effort="none"),
    )


def build_toolset(allowed: tuple[str, ...]):
    """An MCP toolset exposing only `allowed` tools.

    Each specialist gets the tools for its own domain and nothing else, so an
    agent cannot stray outside its remit by reaching for another's tool. Passing
    an empty tuple yields no toolset at all.
    """
    if not allowed:
        return None

    from pydantic_ai.mcp import MCPToolset, StdioTransport

    transport = StdioTransport(
        command=str(MCP_PYTHON),
        args=[str(MCP_SERVER_SCRIPT)],
        env={"CAMPUS_DB_PATH": str(DB_PATH)},
        # Each run gets a fresh stdio session. A kept-alive session holds the
        # subprocess and its anyio streams open, bound to the event loop that
        # created them — so a later run on a different loop fails with
        # "Client failed to connect: Event loop is closed". Reconnecting costs a
        # few milliseconds; reusing a dead session costs the whole run.
        keep_alive=False,
    )
    toolset = MCPToolset(transport, id="campus-customs-ops")
    return toolset.filtered(lambda ctx, tool_def: tool_def.name in allowed)


#: Appended to every specialist prompt. Keeps the response contract and the
#: no-guessing rule identical across the team, rather than restating them in
#: five prompt files where they could drift apart.
SPECIALIST_CONTRACT = """

---

## Response contract

Return an `AgentResponse`:

- `answered` — true **only** if you answered from data a tool returned. If the
  information was not available, set it to false.
- `summary` — the answer in one or two sentences.
- `findings` — the specific facts you established. Every one must trace to a tool
  call you made or a fact the Boss supplied.
- `tool_calls` — the tools you actually called, with the arguments you used.
- `missing` — anything you could not determine, and why. Populate this instead of
  inventing a value.
- `approvals_required` — any payment or discount decision that needs a human.
- `draft_message` — only when a customer-facing draft was asked for.

Answer only what the Boss asked. Do not route work to other specialists; the Boss
decides that. Do not repeat a lookup you have already made.
"""
