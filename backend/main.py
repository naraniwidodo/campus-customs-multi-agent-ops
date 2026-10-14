"""Campus Customs operations API.

Serves the dashboard: the ticket board, agent runs, the live activity feed, the
human approval queue, the cash position, and a reset.

**Where spending lives.** Agents reach the shop only through the MCP server, which
has no payment tool. Money moves in exactly one place — `approvals.py` — reachable
only through the `/approve/*` endpoints below, which a human invokes from the
dashboard. An agent has no HTTP client and no import path to that module, so the
separation is structural rather than a matter of instructions.

Run:
    cd backend && ../.venv/bin/python -m uvicorn main:app --port 8020
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import approvals
from approvals import ApprovalError
from audit import AUDIT_PATH
from config import DB_PATH, MAX_ITERATIONS, MODEL_NAME

app = FastAPI(
    title="Campus Customs — Operations API",
    description="Multi-agent shop operations with human-approved spending.",
    version="1.0.0",
)

# The dashboard is served from a different origin in development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#: In-memory record of agent runs. Runs are not persisted — the durable record is
#: the append-only audit trail, which survives a restart.
RUNS: dict[str, dict[str, Any]] = {}

#: Audit records at or below this id predate the last reset. The trail itself is
#: append-only and keeps everything, but the dashboard must not mix work from a
#: previous scenario into the current one — a stale row saying stock already
#: arrived, next to a fresh one saying it has not, is actively misleading.
RESET_BOUNDARY: int = 0

#: Written when the reconciliation pass closes a ticket the Boss did not close.
#: Surfaced to the dashboard so a green badge is never left standing beside an
#: agent conclusion that hedges — the reader can see which one closed it.
SYSTEM_CLOSE_NOTE = (
    "Closed by system verification: stock covers the order and every linked "
    "obligation is settled."
)


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _shop_date(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    return row["date_today"] if row else "unknown"


class ApprovalRequest(BaseModel):
    approved_by: str = Field(
        min_length=1,
        description="Name of the human approving. Required — the schema will not "
        "accept a payment without one.",
    )


# --- board ---------------------------------------------------------------------


@app.get("/api/tickets", summary="All tickets, and whether each is open or resolved")
def list_tickets() -> dict[str, Any]:
    """Every ticket with its linked invoice or lease and any proposals raised.

    `resolved` is true only when the ticket is closed. A ticket that is pending or
    blocked is still outstanding work, so it reports as not resolved.
    """
    with _db() as conn:
        as_of = _shop_date(conn)
        tickets = []
        for row in conn.execute("SELECT * FROM tickets ORDER BY id").fetchall():
            t = dict(row)
            t["resolved"] = row["status"].lower() == "closed"
            # Who closed it: the Boss, or the reconciliation pass that checks the
            # guard after every run.
            t["closed_by"] = (
                "system"
                if t["resolved"] and SYSTEM_CLOSE_NOTE[:28] in (row["notes"] or "")
                else ("agent" if t["resolved"] else None)
            )

            t["invoice"] = None
            if row["invoice_id"] is not None:
                inv = conn.execute(
                    "SELECT i.*, v.name AS vendor_name, v.lead_days FROM invoices i "
                    "LEFT JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                    (row["invoice_id"],),
                ).fetchone()
                t["invoice"] = dict(inv) if inv else None

            t["lease"] = None
            if row["lease_id"] is not None:
                lease = conn.execute(
                    "SELECT * FROM leases WHERE id = ?", (row["lease_id"],)
                ).fetchone()
                t["lease"] = dict(lease) if lease else None

            t["proposals"] = [
                dict(p)
                for p in conn.execute(
                    "SELECT id, kind, status, summary, amount, approved_by, created_by "
                    "FROM proposals WHERE ticket_id = ? ORDER BY id",
                    (row["id"],),
                ).fetchall()
            ]
            tickets.append(t)

    return {
        "as_of": as_of,
        "total": len(tickets),
        "open": sum(1 for t in tickets if not t["resolved"]),
        "resolved": sum(1 for t in tickets if t["resolved"]),
        "tickets": tickets,
    }


@app.get("/api/cash", summary="Current checking balance and what is owed")
def cash() -> dict[str, Any]:
    """The cash position, with obligations, so the dashboard can show the squeeze."""
    with _db() as conn:
        as_of = _shop_date(conn)
        accounts = [dict(r) for r in conn.execute("SELECT * FROM cash_accounts").fetchall()]
        total = round(sum(a["balance"] for a in accounts), 2)

        open_invoices = round(
            conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS t FROM invoices "
                "WHERE LOWER(status) = 'open'"
            ).fetchone()["t"],
            2,
        )
        rent_due = round(
            conn.execute("SELECT COALESCE(SUM(monthly_rent), 0) AS t FROM leases").fetchone()["t"],
            2,
        )
        payments = [dict(r) for r in conn.execute(
            "SELECT * FROM payments ORDER BY id DESC LIMIT 20"
        ).fetchall()]
        spent = round(
            conn.execute("SELECT COALESCE(SUM(amount), 0) AS t FROM payments").fetchone()["t"], 2
        )

    obligations = round(open_invoices + rent_due, 2)
    return {
        "as_of": as_of,
        "accounts": accounts,
        "checking": total,
        "open_invoice_total": open_invoices,
        "rent_due_total": rent_due,
        "total_obligations": obligations,
        "cash_after_obligations": round(total - obligations, 2),
        "can_meet_all_obligations": total - obligations >= 0,
        "total_spent": spent,
        "payments": payments,
        "note": "No revenue is modelled, so the balance only ever falls.",
    }


# --- running the agent team ----------------------------------------------------


def _ticket_request(conn: sqlite3.Connection, ticket_id: int) -> str:
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"No ticket {ticket_id}.")
    parts = [
        f"Ticket {row['id']} ({row['type']}) from {row['requester']}: {row['subject']}.",
        f"Notes: {row['notes']}" if row["notes"] else "",
        f"Item: {row['sku']} size {row['size']} x{row['qty']}."
        if row["sku"]
        else "",
        f"Linked invoice: {row['invoice_id']}." if row["invoice_id"] else "",
        f"Linked lease: {row['lease_id']}." if row["lease_id"] else "",
        "Work this ticket. Prepare anything that needs a human decision, but do not "
        "describe anything as paid, ordered, applied or sent.",
    ]
    return " ".join(p for p in parts if p)


async def _execute_run(run_id: str, ticket_id: int, prompt: str) -> None:
    from agents import run_boss

    RUNS[run_id]["status"] = "running"
    try:
        result = await run_boss(prompt)
        RUNS[run_id].update(
            status="finished",
            iterations=result.iterations_used,
            hit_iteration_limit=result.hit_iteration_limit,
            agents_consulted=[a.value for a in result.final.agents_consulted],
            answer=result.final.answer,
            sufficient=result.final.sufficient,
            unresolved=result.final.unresolved,
            approvals_required=[a.model_dump() for a in result.final.approvals_required],
            delegations=len(result.transcript),
        )
    except Exception as exc:  # noqa: BLE001 — reported to the dashboard, not swallowed
        RUNS[run_id].update(status="failed", error=f"{type(exc).__name__}: {exc}")

    # Reconcile the board with the facts.
    #
    # The close guard is the authority on whether a ticket is done — it checks
    # stock actually on the shelf and invoices actually settled. When it reports
    # nothing blocking, the ticket *is* finished, whether or not the Boss
    # remembered to say so. Agents are not consistent about calling
    # update_ticket_status on the pass where the last blocker clears, which left
    # finished tickets sitting at "pending" and the human wondering what was still
    # owed. This closes that gap deterministically rather than hoping the model
    # behaves.
    _reconcile_ticket(ticket_id)


def _reconcile_ticket(ticket_id: int) -> None:
    """Close a ticket whose blockers have all cleared."""
    import sys as _sys

    mcp_dir = str(BACKEND_DIR.parent / "mcp_server")
    if mcp_dir not in _sys.path:
        _sys.path.insert(0, mcp_dir)

    try:
        import db as _db  # noqa: PLC0415
        import server as _server  # noqa: PLC0415

        conn = _db.connect_ro()
        try:
            row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
            if row is None or row["status"].lower() == "closed":
                return
            if _server._close_blockers(conn, row):
                return
        finally:
            conn.close()

        _server.update_ticket_status(
            ticket_id=ticket_id,
            status="closed",
            note=SYSTEM_CLOSE_NOTE,
        )
    except Exception:  # noqa: BLE001 — reconciliation must never break a run
        pass



def _ticket_for(kind: str, ref_id: int) -> int | None:
    """Which ticket a human decision belongs to, so work can resume on it.

    A proposal names its ticket directly. An invoice or a lease is linked the
    other way round — the ticket carries the foreign key.
    """
    with _db() as conn:
        if kind == "proposal":
            row = conn.execute(
                "SELECT ticket_id FROM proposals WHERE id = ?", (ref_id,)
            ).fetchone()
            return row["ticket_id"] if row else None
        column = {"invoice": "invoice_id", "rent": "lease_id"}.get(kind)
        if column is None:
            return None
        row = conn.execute(
            f"SELECT id FROM tickets WHERE {column} = ? ORDER BY id LIMIT 1", (ref_id,)
        ).fetchone()
        return row["id"] if row else None


def _start_run(ticket_id: int, background: BackgroundTasks) -> dict[str, Any]:
    """Queue an agent run for a ticket and return its handle."""
    from uuid import uuid4

    with _db() as conn:
        prompt = _ticket_request(conn, ticket_id)

    run_id = uuid4().hex[:12]
    RUNS[run_id] = {
        "run_id": run_id,
        "ticket_id": ticket_id,
        "status": "queued",
        "model": MODEL_NAME,
        "max_iterations": MAX_ITERATIONS,
        "prompt": prompt,
    }
    # Hand Starlette the coroutine FUNCTION and its arguments so it is awaited on
    # the server's own running loop.
    #
    # Do NOT change this to `add_task(asyncio.run, _execute_run(...))`.
    # `asyncio.run` is a *sync* callable, so Starlette would run it in a worker
    # thread where it builds a throwaway event loop and closes it. The cached
    # model client binds to the first loop that uses it, so the next run would die
    # with "Client failed to connect: Event loop is closed".
    background.add_task(_execute_run, run_id, ticket_id, prompt)
    return {"run_id": run_id, "ticket_id": ticket_id, "status": "queued"}


def _resume(kind: str, ref_id: int, background: BackgroundTasks) -> dict[str, Any] | None:
    """Put the team back on the ticket a human just unblocked.

    Approving a payment or confirming a delivery changes the facts the agents
    reasoned about — a blocked vendor is now clear, stock that was zero is now on
    the shelf. Without this the human approves and nothing happens, and the ticket
    has to be re-run by hand to notice.
    """
    ticket_id = _ticket_for(kind, ref_id)
    if ticket_id is None:
        return None
    try:
        return _start_run(ticket_id, background)
    except HTTPException:
        return None


@app.post("/api/tickets/{ticket_id}/run", summary="Run the agent team on one ticket")
def run_ticket(ticket_id: int, background: BackgroundTasks) -> dict[str, Any]:
    """Start a run and return immediately.

    A run takes minutes and makes many model calls, so it is dispatched to the
    background. Poll `/api/activity` to watch the agents work, or `/api/runs/{id}`
    for the outcome.
    """
    started = _start_run(ticket_id, background)
    return {**started, "poll": "/api/activity"}


@app.get("/api/runs", summary="Runs started since the server booted")
def list_runs() -> dict[str, Any]:
    return {"runs": list(RUNS.values())}


@app.get("/api/runs/{run_id}", summary="One run's outcome")
def get_run(run_id: str) -> dict[str, Any]:
    run = RUNS.get(run_id)
    if run is None:
        raise HTTPException(404, f"No run {run_id}.")
    return run


# --- activity ------------------------------------------------------------------


@app.get("/api/activity", summary="Recent agent activity: messages and tools used")
def activity(limit: int = 60, since_id: int = 0, ticket_id: int | None = None) -> dict[str, Any]:
    """The audit trail, newest last, for the dashboard to poll.

    Pass `since_id` with the highest `record_id` already seen to fetch only what is
    new — the dashboard can refresh without re-reading the whole file.

    Tool calls here are the ones actually made, read from the model's message
    history rather than from what an agent claimed it did.
    """
    if not AUDIT_PATH.exists():
        return {"records": [], "latest_id": 0, "total": 0}

    try:
        records = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(500, f"Audit trail is not valid JSON: {exc}") from exc

    floor = max(since_id, RESET_BOUNDARY)
    if floor:
        records = [r for r in records if r.get("record_id", 0) > floor]

    if ticket_id is not None:
        wanted = {
            r["run_id"]
            for r in records
            if r.get("event") == "run_started" and f"Ticket {ticket_id}" in str(r.get("user_request", ""))
        }
        records = [r for r in records if r.get("run_id") in wanted]

    latest = records[-1]["record_id"] if records else since_id
    trimmed = records[-limit:] if limit else records

    # A compact view for a feed: who acted, what they said, which tools they ran.
    feed = []
    for r in trimmed:
        feed.append(
            {
                "record_id": r.get("record_id"),
                "run_id": r.get("run_id"),
                "recorded_at": r.get("recorded_at"),
                "shop_date": r.get("shop_date"),
                "event": r.get("event"),
                "iteration": r.get("iteration"),
                "agent": r.get("agent") or r.get("to_agent") or ("boss" if "boss" in str(r.get("event")) else None),
                "message": r.get("summary") or r.get("reasoning") or r.get("answer") or r.get("task"),
                "answered": r.get("answered"),
                "missing": r.get("missing", []),
                "tools_used": [
                    {"tool": c["tool"], "arguments": c.get("arguments"), "ok": c.get("ok")}
                    for c in (r.get("tool_calls") or [])
                    if c.get("kind") == "mcp"
                ],
                "approvals_required": r.get("approvals_required", []),
                "draft_message": r.get("draft_message"),
            }
        )

    return {"records": feed, "latest_id": latest, "total": len(feed)}


# --- human approval: the only place money moves --------------------------------


@app.get("/api/approvals", summary="Everything awaiting a human decision")
def list_approvals() -> dict[str, Any]:
    return approvals.pending_approvals()


@app.post("/api/approve/proposal/{proposal_id}", summary="Approve an agent proposal")
def approve_proposal(
    proposal_id: int, body: ApprovalRequest, background: BackgroundTasks
) -> dict[str, Any]:
    """Approve a drafted PO, price override or customer draft.

    Only a restock PO spends money. A price override authorises a price; a draft is
    released for a human to send. Nothing is sent by this endpoint.
    """
    try:
        result = approvals.approve_proposal(proposal_id, body.approved_by)
        result["follow_up_run"] = _resume("proposal", proposal_id, background)
        return result
    except ApprovalError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/approve/invoice/{invoice_id}", summary="Pay a vendor invoice")
def approve_invoice(
    invoice_id: int, body: ApprovalRequest, background: BackgroundTasks
) -> dict[str, Any]:
    """Settle an invoice. **This spends money** and unblocks the vendor."""
    try:
        result = approvals.pay_invoice(invoice_id, body.approved_by)
        result["follow_up_run"] = _resume("invoice", invoice_id, background)
        return result
    except ApprovalError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/approve/rent/{lease_id}", summary="Pay rent on a lease")
def approve_rent(
    lease_id: int, body: ApprovalRequest, background: BackgroundTasks
) -> dict[str, Any]:
    """Pay rent. **This spends money** and rolls the lease to its next due date."""
    try:
        result = approvals.pay_rent(lease_id, body.approved_by)
        result["follow_up_run"] = _resume("rent", lease_id, background)
        return result
    except ApprovalError as exc:
        raise HTTPException(409, str(exc)) from exc


class ReceiptRequest(BaseModel):
    received_by: str = Field(
        min_length=1, description="Name of the person confirming the delivery."
    )
    qty: int | None = Field(
        default=None,
        description="Units actually received, if fewer than ordered. Defaults to the "
        "quantity on the purchase order.",
    )


@app.post("/api/receive/{proposal_id}", summary="Confirm a purchase order was delivered")
def receive(
    proposal_id: int, body: ReceiptRequest, background: BackgroundTasks
) -> dict[str, Any]:
    """Record that an approved purchase order physically arrived.

    **This is the only route that increases stock**, and like payment it is a human
    action — no agent can reach it. Paying for an order and receiving it are
    separate events; a `customer_order` ticket cannot close until the goods are
    actually here.
    """
    try:
        result = approvals.receive_goods(proposal_id, body.received_by, body.qty)
        result["follow_up_run"] = _resume("proposal", proposal_id, background)
        return result
    except ApprovalError as exc:
        raise HTTPException(409, str(exc)) from exc


# --- reset ---------------------------------------------------------------------


@app.post("/api/reset", summary="Restore the database to its original state")
def reset() -> dict[str, Any]:
    """Business rule 7. Copies the pristine seed over the working copy.

    The seed is read, never written. The audit trail is **not** cleared — it is
    append-only, and wiping it would destroy the record of how the system behaved.
    """
    try:
        result = approvals.reset_database()
    except ApprovalError as exc:
        raise HTTPException(500, str(exc)) from exc

    # Everything written so far belongs to the previous scenario. The trail keeps
    # it; the dashboard stops showing it.
    global RESET_BOUNDARY
    if AUDIT_PATH.exists():
        try:
            existing = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
            RESET_BOUNDARY = max((r.get("record_id", 0) for r in existing), default=0)
        except json.JSONDecodeError:
            pass

    RUNS.clear()
    result["activity_hidden_before_record"] = RESET_BOUNDARY
    return result


@app.get("/api/health", summary="Service and configuration check")
def health() -> dict[str, Any]:
    with _db() as conn:
        shop_date = _shop_date(conn)
        tables = sorted(
            r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        )
    return {
        "ok": True,
        "model": MODEL_NAME,
        "max_iterations": MAX_ITERATIONS,
        "database": str(DB_PATH),
        "shop_date": shop_date,
        "tables": tables,
        "audit_trail": str(AUDIT_PATH),
        "spending": "Only via /api/approve/* — agents have no payment capability.",
    }
