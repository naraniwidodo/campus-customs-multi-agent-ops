"""Append-only audit trail for agent runs.

Every step of every run is appended to `output/audit_trail.json`. The file is
**never wiped** — runs accumulate, so a later reader can reconstruct what the team
did, when, on what evidence, and what it refused to do.

Two deliberate choices:

**Tool calls are read from the model's message history, not from what the agent
says it did.** An agent's self-reported `tool_calls` is a claim; `ToolCallPart`
and `ToolReturnPart` in the run's messages are what actually happened. The audit
records the latter, so a record of a tool call is evidence rather than testimony.

**Two clocks are recorded.** `shop_date` is `desk.date_today` — the shop's
operating date, which business rule 1 makes authoritative for anything due or
overdue. `recorded_at` is the real wall clock, because an audit trail that cannot
say *when* it was written is not auditable. They differ, and both matter.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
AUDIT_PATH = PROJECT_ROOT / "output" / "audit_trail.json"

#: Serialises appends. Specialists within a round run concurrently, so two
#: unsynchronised read-modify-writes could interleave and lose a record.
_lock = asyncio.Lock()


def _now() -> str:
    """Real local time, ISO-8601 with offset. Not the shop's date."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _read(path: Path) -> list[dict[str, Any]]:
    """Existing records, or an empty list. A corrupt file is never overwritten."""
    if not path.exists() or path.stat().st_size == 0:
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{path} is not valid JSON ({exc}). Refusing to overwrite it — move it "
            "aside if you want a fresh trail."
        ) from exc
    if not isinstance(data, list):
        raise RuntimeError(f"{path} should hold a JSON array of records.")
    return data


def _write_atomic(path: Path, records: list[dict[str, Any]]) -> None:
    """Write via a temp file and rename, so an interrupted run cannot truncate it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _append_sync(path: Path, record: dict[str, Any]) -> int:
    records = _read(path)
    record["record_id"] = len(records) + 1
    records.append(record)
    _write_atomic(path, records)
    return record["record_id"]


class AuditTrail:
    """One run's view of the shared, append-only trail."""

    def __init__(self, run_id: str, shop_date: str, path: Path | None = None) -> None:
        self.run_id = run_id
        self.shop_date = shop_date
        self.path = path or AUDIT_PATH

    async def append(self, event: str, **payload: Any) -> int:
        """Append one record. Returns its id, which is unique across all runs."""
        record = {
            "run_id": self.run_id,
            "recorded_at": _now(),
            "shop_date": self.shop_date,
            "event": event,
            **payload,
        }
        async with _lock:
            return await asyncio.to_thread(_append_sync, self.path, record)


def extract_tool_calls(messages: list[Any]) -> list[dict[str, Any]]:
    """Actual tool calls and their results, taken from a run's message history.

    PydanticAI also routes structured output through a tool call; those are
    tagged `output` so they can be told apart from real MCP tool use. Failed
    calls appear as retries and are recorded too — a tool that refused is often
    the most interesting line in an audit.
    """
    from pydantic_ai.messages import (
        ModelRequest,
        ModelResponse,
        RetryPromptPart,
        ToolCallPart,
        ToolReturnPart,
    )

    calls: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for message in messages:
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, ToolCallPart):
                    key = part.tool_call_id or f"{part.tool_name}:{len(order)}"
                    args = part.args
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            pass
                    calls[key] = {
                        "tool": part.tool_name,
                        "kind": "output" if part.tool_name.startswith("final_result") else "mcp",
                        "arguments": args,
                        "result": None,
                        "ok": None,
                    }
                    order.append(key)
        elif isinstance(message, ModelRequest):
            for part in message.parts:
                key = getattr(part, "tool_call_id", None)
                if key is None or key not in calls:
                    continue
                if isinstance(part, ToolReturnPart):
                    content = part.content
                    if not isinstance(content, (dict, list, str, int, float, bool, type(None))):
                        content = str(content)
                    calls[key]["result"] = content
                    calls[key]["ok"] = True
                elif isinstance(part, RetryPromptPart):
                    calls[key]["result"] = str(part.content)
                    calls[key]["ok"] = False

    return [calls[k] for k in order]


def read_shop_date() -> str:
    """`desk.date_today`, read read-only, purely to stamp audit records.

    Business facts the agents reason about always come through the MCP server.
    This one read is log metadata — it exists so every record carries the shop's
    operating date alongside the wall clock — and it never reaches an agent.
    """
    import sqlite3

    from config import DB_PATH

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
        return row[0] if row else "unknown"
    finally:
        conn.close()
