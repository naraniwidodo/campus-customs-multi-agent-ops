"""Human-approved execution. **This is the only code in the project that spends money.**

It is deliberately a plain Python module, not an MCP tool. The agents' entire
toolset is the MCP server; they have no HTTP client and no import path to this
file, so there is no route by which an agent can call anything here. Spending is
reachable only through a FastAPI endpoint a human invokes.

Every function here demands an `approved_by` name and refuses to overdraw the
account. Those two checks are the last line of defence and are enforced in code,
not in a prompt.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from config import DB_PATH, PROJECT_ROOT

SEED_PATH = PROJECT_ROOT / "campus_customs.db"


class ApprovalError(Exception):
    """A refusal a human should see: insufficient cash, already paid, unknown id."""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _shop_date(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    return row["date_today"] if row else "unknown"


def _require_approver(approved_by: str) -> str:
    name = (approved_by or "").strip()
    if not name:
        raise ApprovalError("An approver's name is required. Nothing was changed.")
    return name


def _checking(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute(
        "SELECT name, balance FROM cash_accounts ORDER BY name LIMIT 1"
    ).fetchone()
    if row is None:
        raise ApprovalError("No cash account exists.")
    return row


def _spend(
    conn: sqlite3.Connection, kind: str, ref_id: int | None, amount: float, approved_by: str
) -> dict[str, Any]:
    """Move money. Refuses rather than letting the balance go negative.

    Business rule 5: the guard lives here, in code. `payments.approved_by` is NOT
    NULL in the schema too, so a payment cannot physically be written without a
    named human.
    """
    account = _checking(conn)
    before = round(account["balance"], 2)
    after = round(before - amount, 2)

    if amount <= 0:
        raise ApprovalError(f"Amount must be positive, got {amount}.")
    if after < 0:
        raise ApprovalError(
            f"Insufficient cash: {account['name']} holds ${before:,.2f} and this "
            f"would spend ${amount:,.2f}, leaving ${after:,.2f}. Refused — the "
            "balance may never go negative."
        )

    # paid_at carries the shop's operating date (business rule 1), consistent with
    # every other business date in the schema. The real wall-clock moment is
    # recorded separately in the audit trail.
    paid_at = _shop_date(conn)

    cur = conn.execute(
        "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (kind, ref_id, amount, account["name"], paid_at, approved_by),
    )
    conn.execute(
        "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
        (after, paid_at, account["name"]),
    )
    return {
        "payment_id": cur.lastrowid,
        "account": account["name"],
        "amount": amount,
        "cash_before": before,
        "cash_after": after,
        "paid_at": paid_at,
    }


# --- the four things a human can approve ---------------------------------------


def pay_invoice(invoice_id: int, approved_by: str) -> dict[str, Any]:
    """Settle a vendor invoice. Unblocks that vendor for shipping."""
    approver = _require_approver(approved_by)
    with _connect() as conn:
        inv = conn.execute(
            "SELECT i.*, v.name AS vendor_name FROM invoices i "
            "LEFT JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (invoice_id,),
        ).fetchone()
        if inv is None:
            raise ApprovalError(f"No invoice {invoice_id}.")
        if inv["status"].lower() != "open":
            raise ApprovalError(
                f"Invoice {invoice_id} is already {inv['status']}. Nothing was changed."
            )

        result = _spend(conn, "invoice", invoice_id, round(inv["amount"], 2), approver)
        conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (invoice_id,))
        conn.commit()

    result.update(
        kind="invoice",
        invoice_id=invoice_id,
        vendor=inv["vendor_name"],
        approved_by=approver,
        effect=f"Invoice {invoice_id} marked paid. {inv['vendor_name']} is now clear to ship.",
    )
    return result


def pay_rent(lease_id: int, approved_by: str) -> dict[str, Any]:
    """Pay a month's rent and roll the lease to its next due date."""
    approver = _require_approver(approved_by)
    with _connect() as conn:
        lease = conn.execute("SELECT * FROM leases WHERE id = ?", (lease_id,)).fetchone()
        if lease is None:
            raise ApprovalError(f"No lease {lease_id}.")

        already = conn.execute(
            "SELECT COUNT(*) AS n FROM payments WHERE kind = 'rent' AND ref_id = ? "
            "AND paid_at >= ?",
            (lease_id, lease["next_due"]),
        ).fetchone()
        if already and already["n"]:
            raise ApprovalError(
                f"Rent for lease {lease_id} due {lease['next_due']} is already paid."
            )

        amount = round(lease["monthly_rent"], 2)
        result = _spend(conn, "rent", lease_id, amount, approver)

        # Roll to the same day next month.
        year, month, day = (int(p) for p in lease["next_due"].split("-"))
        month += 1
        if month > 12:
            month, year = 1, year + 1
        next_due = f"{year:04d}-{month:02d}-{day:02d}"
        conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (next_due, lease_id))
        conn.commit()

    result.update(
        kind="rent",
        lease_id=lease_id,
        space=lease["space_name"],
        landlord=lease["landlord"],
        approved_by=approver,
        next_due_was=lease["next_due"],
        next_due_now=next_due,
        effect=f"Rent paid for {lease['space_name']}. Next due {next_due}.",
    )
    return result


def approve_proposal(proposal_id: int, approved_by: str) -> dict[str, Any]:
    """Approve an agent's proposal.

    A restock PO spends money; a price override and a customer draft do not. The
    distinction matters: approving a discount changes what we may charge, and
    approving a draft releases it for a human to send — neither moves cash.
    """
    approver = _require_approver(approved_by)
    with _connect() as conn:
        row = conn.execute("SELECT * FROM proposals WHERE id = ?", (proposal_id,)).fetchone()
        if row is None:
            raise ApprovalError(f"No proposal {proposal_id}.")
        if row["approved_by"]:
            raise ApprovalError(
                f"Proposal {proposal_id} was already approved by {row['approved_by']}."
            )

        payment = None
        if row["kind"] == "restock_po":
            if row["amount"] is None:
                raise ApprovalError(f"Proposal {proposal_id} has no amount to spend.")

            vendor_blocked = conn.execute(
                "SELECT COUNT(*) AS n FROM invoices "
                "WHERE vendor_id = ? AND LOWER(status) = 'open'",
                (row["vendor_id"],),
            ).fetchone()
            if vendor_blocked and vendor_blocked["n"]:
                raise ApprovalError(
                    f"Vendor {row['vendor_id']} still holds an open invoice and cannot "
                    "ship. Settle that invoice first, then approve this order."
                )

            payment = _spend(
                conn, "purchase_order", proposal_id, round(row["amount"], 2), approver
            )

        conn.execute(
            "UPDATE proposals SET approved_by = ?, status = 'approved' WHERE id = ?",
            (approver, proposal_id),
        )
        conn.commit()

    effect = {
        "restock_po": "Purchase order approved and paid. Stock arrives after the "
        "vendor's lead time; inventory is not incremented until it does.",
        "price_override": "Price override approved. The list price is unchanged — "
        "this authorises the quoted price for this request.",
        "customer_draft": "Draft approved for a human to send. Nothing was sent.",
        "vendor_suggestion": "Vendor selection approved.",
    }.get(row["kind"], "Proposal approved.")

    return {
        "proposal_id": proposal_id,
        "kind": row["kind"],
        "summary": row["summary"],
        "approved_by": approver,
        "payment": payment,
        "spent": payment is not None,
        "effect": effect,
    }


def receive_goods(proposal_id: int, received_by: str, qty: int | None = None) -> dict[str, Any]:
    """Confirm that an approved purchase order has physically arrived.

    **This is the only code that increases stock**, and like payment it is a human
    action — no agent can reach it. That separation matters: an agent able to
    conjure inventory could satisfy a customer order that nothing was ever
    delivered for.

    Paying for a purchase order and receiving the goods are different events
    separated by the vendor's lead time. Approving the order spends the money;
    this records the delivery actually turning up. Without it a `customer_order`
    ticket can never close, because the close guard waits for stock that nothing
    produces.

    The vendor's expected delivery date is reported for context but is **not**
    enforced: the shop's operating date never advances, so blocking on it would
    only recreate the deadlock. A human confirms what actually arrived.

    Args:
        proposal_id: An approved `restock_po` proposal.
        received_by: Name of the person confirming the delivery. Required.
        qty: Units actually received, if it differs from the quantity ordered —
            a short delivery is recorded as what turned up, not as what was hoped.
    """
    receiver = _require_approver(received_by)

    with _connect() as conn:
        row = conn.execute("SELECT * FROM proposals WHERE id = ?", (proposal_id,)).fetchone()
        if row is None:
            raise ApprovalError(f"No proposal {proposal_id}.")
        if row["kind"] != "restock_po":
            raise ApprovalError(
                f"Proposal {proposal_id} is a {row['kind']}, not a purchase order. "
                "Only a purchase order can be received."
            )
        if not row["approved_by"]:
            raise ApprovalError(
                f"Purchase order {proposal_id} has not been approved yet. Approve and "
                "pay for it before recording a delivery."
            )
        if row["received_by"]:
            raise ApprovalError(
                f"Purchase order {proposal_id} was already received by "
                f"{row['received_by']} on {row['received_on']}."
            )
        if not row["sku"] or not row["size"]:
            raise ApprovalError(
                f"Purchase order {proposal_id} has no SKU and size, so there is "
                "nothing to add to inventory."
            )

        received_qty = qty if qty is not None else (row["qty"] or 0)
        if received_qty <= 0:
            raise ApprovalError(f"Received quantity must be positive, got {received_qty}.")

        stock = conn.execute(
            "SELECT qty FROM inventory WHERE sku = ? AND size = ?",
            (row["sku"], row["size"]),
        ).fetchone()
        if stock is None:
            raise ApprovalError(
                f"No inventory row for {row['sku']} size {row['size']}. This tool "
                "restocks existing lines; it does not create new ones."
            )

        before = stock["qty"]
        after = before + received_qty
        as_of = _shop_date(conn)

        conn.execute(
            "UPDATE inventory SET qty = ? WHERE sku = ? AND size = ?",
            (after, row["sku"], row["size"]),
        )
        conn.execute(
            "UPDATE proposals SET status = 'received', received_by = ?, received_on = ? "
            "WHERE id = ?",
            (receiver, as_of, proposal_id),
        )
        conn.commit()

        expected = None
        if row["vendor_id"] is not None:
            vendor = conn.execute(
                "SELECT lead_days FROM vendors WHERE id = ?", (row["vendor_id"],)
            ).fetchone()
            if vendor is not None:
                from datetime import date, timedelta

                expected = (
                    date.fromisoformat(row["created_on"])
                    + timedelta(days=vendor["lead_days"])
                ).isoformat()

    return {
        "ok": True,
        "proposal_id": proposal_id,
        "sku": row["sku"],
        "size": row["size"],
        "qty_received": received_qty,
        "qty_ordered": row["qty"],
        "short_delivery": row["qty"] is not None and received_qty < row["qty"],
        "stock_before": before,
        "stock_after": after,
        "received_by": receiver,
        "received_on": as_of,
        "expected_delivery": expected,
        "effect": (
            f"{received_qty} x {row['sku']} size {row['size']} received. "
            f"Stock {before} -> {after}."
        ),
    }

def pending_approvals() -> dict[str, Any]:
    """Everything awaiting a human: unapproved proposals, and payable obligations."""
    with _connect() as conn:
        as_of = _shop_date(conn)
        account = _checking(conn)
        cash = round(account["balance"], 2)

        proposals = []
        for r in conn.execute(
            "SELECT * FROM proposals WHERE approved_by IS NULL ORDER BY id"
        ).fetchall():
            item = dict(r)
            if item.get("details"):
                try:
                    item["details"] = json.loads(item["details"])
                except (TypeError, json.JSONDecodeError):
                    pass
            item["spends_cash"] = r["kind"] == "restock_po"
            item["affordable"] = (
                r["amount"] is None or r["amount"] <= cash if item["spends_cash"] else True
            )
            proposals.append(item)

        invoices = [
            {
                "invoice_id": r["id"],
                "vendor": r["vendor_name"],
                "amount": r["amount"],
                "due_date": r["due_date"],
                "description": r["description"],
                "affordable": r["amount"] <= cash,
            }
            for r in conn.execute(
                "SELECT i.*, v.name AS vendor_name FROM invoices i "
                "LEFT JOIN vendors v ON v.id = i.vendor_id "
                "WHERE LOWER(i.status) = 'open' ORDER BY i.due_date"
            ).fetchall()
        ]

        rents = []
        for r in conn.execute("SELECT * FROM leases ORDER BY next_due").fetchall():
            paid = conn.execute(
                "SELECT COUNT(*) AS n FROM payments WHERE kind = 'rent' AND ref_id = ? "
                "AND paid_at >= ?",
                (r["id"], r["next_due"]),
            ).fetchone()
            if paid and paid["n"]:
                continue
            rents.append(
                {
                    "lease_id": r["id"],
                    "space": r["space_name"],
                    "landlord": r["landlord"],
                    "amount": r["monthly_rent"],
                    "due_date": r["next_due"],
                    "affordable": r["monthly_rent"] <= cash,
                }
            )

        # Approved and paid for, but not yet delivered. A customer_order ticket
        # cannot close until the goods actually arrive, so these are real
        # outstanding work rather than history.
        awaiting_receipt = [
            {
                "proposal_id": r["id"],
                "ticket_id": r["ticket_id"],
                "summary": r["summary"],
                "sku": r["sku"],
                "size": r["size"],
                "qty": r["qty"],
                "approved_by": r["approved_by"],
                "created_on": r["created_on"],
            }
            for r in conn.execute(
                "SELECT * FROM proposals WHERE kind = 'restock_po' "
                "AND approved_by IS NOT NULL AND received_by IS NULL ORDER BY id"
            ).fetchall()
        ]

    return {
        "as_of": as_of,
        "cash": cash,
        "proposals": proposals,
        "payable_invoices": invoices,
        "payable_rent": rents,
        "awaiting_receipt": awaiting_receipt,
        "total_pending": len(proposals) + len(invoices) + len(rents) + len(awaiting_receipt),
    }


def reset_database() -> dict[str, Any]:
    """Restore the working copy from the pristine seed. Business rule 7.

    The seed is read, never written. The `proposals` table is dropped by the copy
    and recreated empty on the next connection. The audit trail is **not** touched
    — it is append-only by instruction, and wiping it would destroy the record of
    how the system behaved.
    """
    import shutil

    if not SEED_PATH.exists():
        raise ApprovalError(f"Seed database not found at {SEED_PATH}.")

    shutil.copyfile(SEED_PATH, DB_PATH)

    import sys

    sys.path.insert(0, str(PROJECT_ROOT / "mcp_server"))
    from db import ensure_schema  # noqa: PLC0415 — recreates `proposals` post-copy

    ensure_schema()

    with _connect() as conn:
        state = {
            "tickets_open": conn.execute(
                "SELECT COUNT(*) AS n FROM tickets WHERE status = 'open'"
            ).fetchone()["n"],
            "cash": round(_checking(conn)["balance"], 2),
            "payments": conn.execute("SELECT COUNT(*) AS n FROM payments").fetchone()["n"],
            "proposals": conn.execute("SELECT COUNT(*) AS n FROM proposals").fetchone()["n"],
            "shop_date": _shop_date(conn),
        }

    return {
        "ok": True,
        "restored_from": SEED_PATH.name,
        "restored_to": Path(DB_PATH).name,
        "state": state,
        "note": "Audit trail deliberately preserved — it is append-only.",
    }
