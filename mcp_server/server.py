"""Campus Customs operations MCP.

Tools the agent team uses to read the shop's books. Everything here is
read-only; nothing in this file writes to the database.

Dates follow business rule 1 — "today" is desk.date_today, never the system
clock — so overdue answers stay stable however long after the fact a run happens.

Run from this folder (stdio):  python server.py
Run (HTTP):                    python server.py --http
HTTP URL:                      http://127.0.0.1:8003/mcp
"""

from __future__ import annotations

import argparse
import re

from fastmcp import FastMCP

import json as _json

from db import (
    PROPOSAL_KINDS,
    add_days,
    TICKET_STATUSES,
    connect_ro,
    connect_rw,
    days_between,
    ensure_schema,
    today,
)

mcp = FastMCP("campus-customs-ops")

# The proposals table lives in the working copy only, and a reset drops it.
# Creating it at import keeps the server usable immediately after a reset.
ensure_schema()


def _margin_pct(unit_cost: float, list_price: float) -> float | None:
    """Gross margin on one unit, as a percentage of list price."""
    if not list_price:
        return None
    return round((list_price - unit_cost) / list_price * 100, 1)


@mcp.tool
def get_product_info(
    sku: str | None = None,
    name_contains: str | None = None,
    size: str | None = None,
    requested_qty: int | None = None,
) -> dict:
    """Look up a product: what it is, what is on the shelf, and what it costs.

    Serves stock and pricing questions — ticket 101 (customer order) and ticket
    103 (price override). Pass only the filters the ticket calls for; everything
    is optional, and omitting all of them returns the whole catalogue.

    Args:
        sku: Exact SKU, e.g. "CC-TEE-WHITE". Case-insensitive.
        name_contains: Partial product name, for when the ticket names an item
            but not its SKU.
        size: Restrict the size breakdown to one size, e.g. "S", "M", "OS".
        requested_qty: How many units the ticket asks for. Supplying this adds a
            `request` block with the shortfall already worked out.

    Returns:
        `as_of` (the shop's date), `matched` (product count) and `products` —
        each with its pricing, unit margin, per-size stock with locations, and
        total units on hand. Inventory is keyed by SKU *and* size, so one product
        spans several size rows; pricing is per SKU and does not vary by size.
    """
    with connect_ro() as conn:
        as_of = today(conn)

        where, params = [], []
        if sku:
            where.append("UPPER(p.sku) = UPPER(?)")
            params.append(sku)
        if name_contains:
            where.append(
                "EXISTS (SELECT 1 FROM inventory i2 "
                "WHERE i2.sku = p.sku AND LOWER(i2.name) LIKE LOWER(?))"
            )
            params.append(f"%{name_contains}%")
        clause = f"WHERE {' AND '.join(where)}" if where else ""

        rows = conn.execute(
            f"SELECT p.sku, p.unit_cost, p.list_price FROM pricing p {clause} "
            "ORDER BY p.sku",
            params,
        ).fetchall()

        products = []
        for row in rows:
            size_params: list[object] = [row["sku"]]
            size_clause = ""
            if size:
                size_clause = "AND UPPER(size) = UPPER(?)"
                size_params.append(size)

            stock = conn.execute(
                "SELECT name, size, qty, location FROM inventory "
                f"WHERE sku = ? {size_clause} ORDER BY size",
                size_params,
            ).fetchall()

            if not stock and size:
                # Product exists but not in this size — say so rather than
                # returning an empty list that reads like "no such product".
                name_row = conn.execute(
                    "SELECT name FROM inventory WHERE sku = ? LIMIT 1", (row["sku"],)
                ).fetchone()
                product_name = name_row["name"] if name_row else None
            else:
                product_name = stock[0]["name"] if stock else None

            product = {
                "sku": row["sku"],
                "name": product_name,
                "unit_cost": row["unit_cost"],
                "list_price": row["list_price"],
                "unit_margin": round(row["list_price"] - row["unit_cost"], 2),
                "margin_pct": _margin_pct(row["unit_cost"], row["list_price"]),
                "sizes": [
                    {
                        "size": s["size"],
                        "qty": s["qty"],
                        "location": s["location"],
                        "in_stock": s["qty"] > 0,
                    }
                    for s in stock
                ],
                "total_qty": sum(s["qty"] for s in stock),
            }

            if requested_qty is not None:
                available = product["total_qty"] if size is None else (
                    stock[0]["qty"] if stock else 0
                )
                shortfall = max(0, requested_qty - available)

                # Is a restock already in flight for this line? A drafted order
                # that has not been received yet still covers the shortfall, and
                # drafting a second one would double-order.
                pending = conn.execute(
                    "SELECT id, status, approved_by, received_by, qty FROM proposals "
                    "WHERE kind = 'restock_po' AND UPPER(sku) = UPPER(?) "
                    "AND (? IS NULL OR UPPER(size) = UPPER(?)) "
                    "AND received_by IS NULL ORDER BY id DESC LIMIT 1",
                    (row["sku"], size, size),
                ).fetchone()

                request = {
                    "size": size,
                    "requested_qty": requested_qty,
                    "available_qty": available,
                    "shortfall": shortfall,
                    "can_fulfil_from_stock": available >= requested_qty,
                    "restock_in_flight": dict(pending) if pending else None,
                }

                # Say plainly what has to happen next. A shortfall with no order
                # against it is unfinished work, not a finding — without this the
                # shortfall gets reported and nothing is ever drafted, leaving the
                # human with nothing to approve.
                if shortfall and pending is None:
                    request["next_step"] = (
                        f"ACTION REQUIRED: {shortfall} unit(s) short and no restock "
                        f"order exists. Call suggest_vendor_for_sku, then "
                        f"draft_restock_po for {shortfall} unit(s) of {row['sku']} "
                        f"size {size}. Reporting the shortfall without drafting the "
                        f"order leaves the human nothing to approve."
                    )
                elif shortfall and pending is not None:
                    request["next_step"] = (
                        f"A restock order (proposal {pending['id']}, status "
                        f"{pending['status']}) already covers this shortfall. Do not "
                        f"draft another."
                    )
                else:
                    request["next_step"] = "Stock covers the request. No restock needed."

                product["request"] = request

            products.append(product)

    return {"as_of": as_of, "matched": len(products), "products": products}


@mcp.tool
def get_financial_info(
    account: str | None = None,
    include_invoices: bool = True,
    include_leases: bool = True,
    invoice_status: str | None = None,
    vendor_id: int | None = None,
) -> dict:
    """Read the cash position and what is owed to vendors.

    Serves "can we afford this?" — ticket 102 (rent) and ticket 103 (price
    override). Check this before preparing any payment: business rule 5 forbids
    letting the balance go negative, and rule 6 means no money comes in, so cash
    only ever falls.

    Rent counts as an obligation here. Both things that draw down cash — unpaid
    invoices and rent falling due — are returned together, so affordability can be
    answered in one call rather than by combining two.

    Args:
        account: Restrict to one cash account, e.g. "checking".
        include_invoices: Set False to leave out vendor invoices.
        include_leases: Set False to leave out rent obligations.
        invoice_status: Restrict invoices by status, e.g. "open".
        vendor_id: Restrict invoices to one vendor — use this to check whether a
            vendor is clear to ship (business rule 3: a vendor holding an open
            unpaid invoice cannot ship).

    Returns:
        `as_of`, the cash `accounts` with `total_cash`, `invoices` with their
        vendor, lead time and overdue standing, and `leases` with their monthly
        rent and when it next falls due. `total_obligations` is open invoices plus
        rent due, and `cash_after_obligations` is what would remain once both were
        settled — negative means they cannot both be met.
    """
    with connect_ro() as conn:
        as_of = today(conn)

        acct_rows = conn.execute(
            "SELECT name, balance, date FROM cash_accounts "
            + ("WHERE LOWER(name) = LOWER(?) " if account else "")
            + "ORDER BY name",
            (account,) if account else (),
        ).fetchall()
        accounts = [
            {"name": a["name"], "balance": a["balance"], "as_of_date": a["date"]}
            for a in acct_rows
        ]
        total_cash = round(sum(a["balance"] for a in accounts), 2)

        result = {
            "as_of": as_of,
            "accounts": accounts,
            "total_cash": total_cash,
        }

        where, params = [], []
        if invoice_status:
            where.append("LOWER(i.status) = LOWER(?)")
            params.append(invoice_status)
        if vendor_id is not None:
            where.append("i.vendor_id = ?")
            params.append(vendor_id)
        clause = f"WHERE {' AND '.join(where)}" if where else ""

        inv_rows = conn.execute(
            "SELECT i.id, i.vendor_id, i.amount, i.due_date, i.status, "
            "       i.description, v.name AS vendor_name, "
            "       v.specialty AS vendor_specialty, v.lead_days "
            "FROM invoices i LEFT JOIN vendors v ON v.id = i.vendor_id "
            f"{clause} ORDER BY i.due_date",
            params,
        ).fetchall()

        invoices = []
        for inv in inv_rows:
            days_until_due = days_between(as_of, inv["due_date"])
            is_open = inv["status"].lower() == "open"
            invoices.append(
                {
                    "id": inv["id"],
                    "vendor_id": inv["vendor_id"],
                    "vendor_name": inv["vendor_name"],
                    "vendor_specialty": inv["vendor_specialty"],
                    "vendor_lead_days": inv["lead_days"],
                    "amount": inv["amount"],
                    "due_date": inv["due_date"],
                    "status": inv["status"],
                    "description": inv["description"],
                    "days_until_due": days_until_due,
                    "is_overdue": is_open and days_until_due < 0,
                    "days_overdue": max(0, -days_until_due) if is_open else 0,
                }
            )

        # Open invoices are always totalled, even when the list itself is not
        # returned: `total_obligations` must stay truthful regardless of which
        # sections the caller asked to see.
        open_total = round(
            sum(i["amount"] for i in invoices if i["status"].lower() == "open"), 2
        )
        result["open_invoice_total"] = open_total
        result["cash_after_open_invoices"] = round(total_cash - open_total, 2)
        if include_invoices:
            result["invoices"] = invoices

        # Independent of include_invoices. These two flags select sections; one
        # must never suppress the other.
        result.update(_lease_obligations(conn, as_of, total_cash, open_total, include_leases))

    return result


def _lease_obligations(
    conn, as_of: str, total_cash: float, open_invoice_total: float, include: bool
) -> dict:
    """Rent as a financial obligation, alongside what is owed to vendors.

    Rent is money that must leave the account, so Accounting needs it in the same
    picture as the invoices. Without this it could see the cash but not the rent,
    and had to be told the figure by another agent — costing a whole round.
    """
    if not include:
        return {}

    leases = []
    for row in conn.execute(
        "SELECT id, space_name, landlord, monthly_rent, next_due FROM leases "
        "ORDER BY next_due"
    ).fetchall():
        days_until_due = days_between(as_of, row["next_due"])
        leases.append(
            {
                "id": row["id"],
                "space_name": row["space_name"],
                "landlord": row["landlord"],
                "monthly_rent": row["monthly_rent"],
                "next_due": row["next_due"],
                "days_until_due": days_until_due,
                "is_overdue": days_until_due < 0,
            }
        )

    rent_due_total = round(sum(l["monthly_rent"] for l in leases), 2)
    obligations = round(open_invoice_total + rent_due_total, 2)
    remaining = round(total_cash - obligations, 2)

    return {
        "leases": leases,
        "rent_due_total": rent_due_total,
        "total_obligations": obligations,
        "cash_after_obligations": remaining,
        "can_meet_all_obligations": remaining >= 0,
    }


@mcp.tool
def get_lease_info(lease_id: int | None = None) -> dict:
    """Read the shop's leases and when rent falls due.

    Serves ticket 102 (rent notice). Returns the space, landlord, monthly rent
    and next due date, with the due date already compared against the shop's
    operating date.

    Args:
        lease_id: One lease by id. Omit for every lease.

    Returns:
        `as_of`, the `leases` with `days_until_due` and `is_overdue`, and
        `total_monthly_rent` across the leases returned.
    """
    with connect_ro() as conn:
        as_of = today(conn)

        rows = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes "
            "FROM leases "
            + ("WHERE id = ? " if lease_id is not None else "")
            + "ORDER BY next_due",
            (lease_id,) if lease_id is not None else (),
        ).fetchall()

        leases = []
        for row in rows:
            days_until_due = days_between(as_of, row["next_due"])
            leases.append(
                {
                    "id": row["id"],
                    "space_name": row["space_name"],
                    "landlord": row["landlord"],
                    "monthly_rent": row["monthly_rent"],
                    "next_due": row["next_due"],
                    "notes": row["notes"],
                    "days_until_due": days_until_due,
                    "is_overdue": days_until_due < 0,
                }
            )

    return {
        "as_of": as_of,
        "matched": len(leases),
        "leases": leases,
        "total_monthly_rent": round(sum(l["monthly_rent"] for l in leases), 2),
    }


# --- tickets ------------------------------------------------------------------


@mcp.tool
def get_ticket_info(
    ticket_id: int | None = None,
    status: str | None = None,
    ticket_type: str | None = None,
) -> dict:
    """Read the ticket board — the work queue the team routes from.

    Each ticket carries whichever foreign key its type implies: a customer order
    points at an invoice, a rent notice at a lease, a price override at neither.
    Those linked records are resolved here so the board can be read in one call.
    Any proposals already raised against a ticket come back with it.

    Args:
        ticket_id: One ticket by id. Omit for the whole board.
        status: Restrict by status, e.g. "open", "pending", "blocked", "closed".
        ticket_type: Restrict by type, e.g. "customer_order", "rent_notice",
            "price_override".

    Returns:
        `as_of`, `matched`, and `tickets` — each with its fields, the linked
        invoice or lease where one exists, and `proposals` awaiting a human.
    """
    with connect_ro() as conn:
        as_of = today(conn)

        where, params = [], []
        if ticket_id is not None:
            where.append("t.id = ?")
            params.append(ticket_id)
        if status:
            where.append("LOWER(t.status) = LOWER(?)")
            params.append(status)
        if ticket_type:
            where.append("LOWER(t.type) = LOWER(?)")
            params.append(ticket_type)
        clause = f"WHERE {' AND '.join(where)}" if where else ""

        rows = conn.execute(
            f"SELECT * FROM tickets t {clause} ORDER BY t.id", params
        ).fetchall()

        tickets = []
        for row in rows:
            ticket = dict(row)

            # created_at is ISO-8601 with an offset, unlike every other date in
            # the schema. Truncate before comparing it with the shop's date.
            created_date = ticket["created_at"][:10]
            ticket["created_on"] = created_date
            ticket["age_days"] = days_between(created_date, as_of)

            ticket["invoice"] = None
            if row["invoice_id"] is not None:
                inv = conn.execute(
                    "SELECT i.id, i.vendor_id, i.amount, i.due_date, i.status, "
                    "       i.description, v.name AS vendor_name, v.lead_days "
                    "FROM invoices i LEFT JOIN vendors v ON v.id = i.vendor_id "
                    "WHERE i.id = ?",
                    (row["invoice_id"],),
                ).fetchone()
                if inv is not None:
                    invoice = dict(inv)
                    due = days_between(as_of, inv["due_date"])
                    invoice["days_until_due"] = due
                    invoice["is_overdue"] = inv["status"].lower() == "open" and due < 0
                    ticket["invoice"] = invoice

            ticket["lease"] = None
            if row["lease_id"] is not None:
                lease = conn.execute(
                    "SELECT id, space_name, landlord, monthly_rent, next_due "
                    "FROM leases WHERE id = ?",
                    (row["lease_id"],),
                ).fetchone()
                if lease is not None:
                    lease_d = dict(lease)
                    lease_d["days_until_due"] = days_between(as_of, lease["next_due"])
                    ticket["lease"] = lease_d

            ticket["proposals"] = [
                {
                    "id": p["id"],
                    "kind": p["kind"],
                    "status": p["status"],
                    "summary": p["summary"],
                    "amount": p["amount"],
                    "approved_by": p["approved_by"],
                    "created_by": p["created_by"],
                }
                for p in conn.execute(
                    "SELECT * FROM proposals WHERE ticket_id = ? ORDER BY id",
                    (row["id"],),
                ).fetchall()
            ]
            tickets.append(ticket)

    return {"as_of": as_of, "matched": len(tickets), "tickets": tickets}


@mcp.tool
def update_ticket_status(ticket_id: int, status: str, note: str | None = None) -> dict:
    """Move a ticket's status, and refuse to close one whose work is not done.

    A ticket may only be closed once its outcome is actually verifiable from the
    database. This is enforced here rather than left to the agent's judgement:

    - `customer_order` — stock must cover the requested quantity, and any linked
      invoice must no longer be open.
    - `rent_notice` — rent must be recorded as paid in `payments`. No tool can do
      that, so these stay open until a human pays.
    - `price_override` — a price-override proposal must carry a human approver.

    When a close is refused the ticket is left as it is and the reason is
    returned, so the caller can set "pending" or "blocked" instead.

    Args:
        ticket_id: The ticket to update.
        status: One of "open", "pending", "blocked", "closed".
        note: Appended to the ticket's notes, with the shop's date.

    Returns:
        `ok`, the ticket's `status_before` and `status_after`, and `reason` when a
        close was refused.
    """
    status = status.lower().strip()
    if status not in TICKET_STATUSES:
        return {
            "ok": False,
            "error": f"Unknown status {status!r}. Use one of: {', '.join(TICKET_STATUSES)}.",
        }

    with connect_rw() as conn:
        as_of = today(conn)
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"ok": False, "error": f"No ticket {ticket_id}."}

        before = row["status"]

        if status in ("pending", "blocked"):
            # A ticket with nothing blocking it should not be parked. Otherwise a
            # finished ticket sits open and the human is left wondering what is
            # still owed.
            blockers = _close_blockers(conn, row)
            if not blockers:
                return {
                    "ok": False,
                    "ticket_id": ticket_id,
                    "status_before": before,
                    "status_after": before,
                    "refused": status,
                    "reason": [
                        "Nothing is blocking this ticket: the stock is on the shelf "
                        "and any linked invoice is settled."
                    ],
                    "guidance": "Call this again with status 'closed'.",
                }

        if status == "closed":
            blockers = _close_blockers(conn, row)
            if blockers:
                return {
                    "ok": False,
                    "ticket_id": ticket_id,
                    "status_before": before,
                    "status_after": before,
                    "refused": "close",
                    "reason": blockers,
                    "guidance": "Set 'pending' or 'blocked' instead, and leave the "
                    "ticket for a human.",
                }

        # Keep the ticket's own note plus the *latest* status note only.
        #
        # Appending every status note turned the field into a stack of
        # contradicting statements — "0 available (short by 1)" sitting above
        # "1 unit available" — and get_ticket_info feeds that straight back to the
        # agents, which then correctly report "conflicting availability
        # information". The stale lines were actively degrading their reasoning,
        # so only the current one is kept. The full history lives in the audit
        # trail, which is the right place for it.
        base = re.split(r"\n?\[\d{4}-\d{2}-\d{2}\]", row["notes"] or "")[0].strip()
        notes = f"{base}\n[{as_of}] {note}".strip() if note else base

        conn.execute(
            "UPDATE tickets SET status = ?, notes = ? WHERE id = ?",
            (status, notes, ticket_id),
        )
        conn.commit()

    return {
        "ok": True,
        "ticket_id": ticket_id,
        "status_before": before,
        "status_after": status,
        "as_of": as_of,
    }


def _close_blockers(conn, ticket) -> list[str]:
    """Reasons this ticket cannot be closed yet. Empty means it may close."""
    reasons: list[str] = []
    kind = ticket["type"].lower()

    if kind == "customer_order":
        if ticket["sku"] and ticket["size"]:
            stock = conn.execute(
                "SELECT qty FROM inventory WHERE sku = ? AND size = ?",
                (ticket["sku"], ticket["size"]),
            ).fetchone()
            have = stock["qty"] if stock else 0
            want = ticket["qty"] or 0
            if have < want:
                reasons.append(
                    f"Stock is {have} for {ticket['sku']} size {ticket['size']}, "
                    f"but {want} is needed."
                )
        if ticket["invoice_id"] is not None:
            inv = conn.execute(
                "SELECT status FROM invoices WHERE id = ?", (ticket["invoice_id"],)
            ).fetchone()
            if inv is not None and inv["status"].lower() == "open":
                reasons.append(
                    f"Invoice {ticket['invoice_id']} is still open; it needs a human "
                    "to pay it."
                )

    elif kind == "rent_notice":
        paid = conn.execute(
            "SELECT COUNT(*) AS n FROM payments WHERE kind = 'rent' AND ref_id = ?",
            (ticket["lease_id"],),
        ).fetchone()
        if not paid or paid["n"] == 0:
            reasons.append(
                "No rent payment is recorded for this lease. Payment requires a "
                "human; no tool can make one."
            )

    elif kind == "price_override":
        approved = conn.execute(
            "SELECT COUNT(*) AS n FROM proposals "
            "WHERE ticket_id = ? AND kind = 'price_override' "
            "AND approved_by IS NOT NULL",
            (ticket["id"],),
        ).fetchone()
        if not approved or approved["n"] == 0:
            reasons.append(
                "No price-override proposal on this ticket has been approved by a "
                "human."
            )

    return reasons


# --- vendors ------------------------------------------------------------------


def _vendor_block(conn, vendor_id: int) -> dict:
    """Whether a vendor may ship, read from the database rather than judged.

    Business rule 3: a vendor holding an open unpaid invoice cannot ship. This is
    computed here so no agent has to decide it.
    """
    rows = conn.execute(
        "SELECT id, amount, due_date, status FROM invoices "
        "WHERE vendor_id = ? AND LOWER(status) = 'open'",
        (vendor_id,),
    ).fetchall()
    return {
        "clear_to_ship": not rows,
        "blocking_invoices": [
            {"id": r["id"], "amount": r["amount"], "due_date": r["due_date"]}
            for r in rows
        ],
        "blocking_total": round(sum(r["amount"] for r in rows), 2),
    }


@mcp.tool
def get_vendor_info(
    vendor_id: int | None = None,
    specialty_contains: str | None = None,
) -> dict:
    """Read vendors, their lead times, and whether each may currently ship.

    `clear_to_ship` and `lead_days` both come from the database — the first
    computed from open invoices under business rule 3, the second read from
    `vendors.lead_days`. Neither is for an agent to estimate.

    Args:
        vendor_id: One vendor by id.
        specialty_contains: Partial match on specialty, e.g. "apparel".

    Returns:
        `as_of`, `matched`, and `vendors` — each with `lead_days`,
        `clear_to_ship`, any `blocking_invoices`, and `earliest_delivery` when the
        vendor is clear.
    """
    with connect_ro() as conn:
        as_of = today(conn)

        where, params = [], []
        if vendor_id is not None:
            where.append("id = ?")
            params.append(vendor_id)
        if specialty_contains:
            where.append("LOWER(specialty) LIKE LOWER(?)")
            params.append(f"%{specialty_contains}%")
        clause = f"WHERE {' AND '.join(where)}" if where else ""

        vendors = []
        for row in conn.execute(
            f"SELECT id, name, specialty, lead_days FROM vendors {clause} ORDER BY id",
            params,
        ).fetchall():
            vendor = dict(row)
            vendor.update(_vendor_block(conn, row["id"]))
            vendor["earliest_delivery"] = (
                add_days(as_of, row["lead_days"]) if vendor["clear_to_ship"] else None
            )
            vendors.append(vendor)

    return {"as_of": as_of, "matched": len(vendors), "vendors": vendors}


@mcp.tool
def suggest_vendor_for_sku(sku: str, requested_qty: int | None = None) -> dict:
    """Suggest which vendor could restock a SKU. **A suggestion, not a decision.**

    Ranking comes from the database: vendors whose specialty matches the product,
    preferring those clear to ship, then shortest lead time. The result is always
    marked unapproved. Vendor selection affects cash, fulfilment and product
    quality, so a human verifies it before anything is ordered.

    Args:
        sku: The SKU to restock.
        requested_qty: Units wanted, used to cost the suggestion.

    Returns:
        `approved: false`, `requires_human_approval: true`, the ranked
        `candidates` with the reasoning behind each, and `estimated_cost` when a
        quantity was given. Calling this orders nothing and records nothing.
    """
    with connect_ro() as conn:
        as_of = today(conn)

        price = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE UPPER(sku) = UPPER(?)",
            (sku,),
        ).fetchone()
        if price is None:
            return {
                "as_of": as_of,
                "approved": False,
                "requires_human_approval": True,
                "error": f"No such SKU: {sku}",
                "candidates": [],
            }

        name_row = conn.execute(
            "SELECT name FROM inventory WHERE UPPER(sku) = UPPER(?) LIMIT 1", (sku,)
        ).fetchone()
        product_name = name_row["name"] if name_row else None

        # Match the product to a specialty from its own name and SKU. Specialty is
        # free text, so this is a heuristic over database values, never a guess at
        # a vendor that is not listed.
        haystack = f"{sku} {product_name or ''}".lower()
        keywords = {
            "apparel": ("tee", "hood", "shirt", "apparel", "hat", "cap"),
            "mug": ("mug", "gift", "small"),
            "courier": ("courier", "ship"),
        }
        wanted = [
            specialty
            for specialty, words in keywords.items()
            if any(word in haystack for word in words)
        ]

        candidates = []
        for row in conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors ORDER BY lead_days"
        ).fetchall():
            specialty = row["specialty"].lower()
            matches = [w for w in wanted if w in specialty]
            block = _vendor_block(conn, row["id"])
            candidates.append(
                {
                    "vendor_id": row["id"],
                    "name": row["name"],
                    "specialty": row["specialty"],
                    "lead_days": row["lead_days"],
                    "specialty_matches_product": bool(matches),
                    "clear_to_ship": block["clear_to_ship"],
                    "blocking_invoices": block["blocking_invoices"],
                    "earliest_delivery": (
                        add_days(as_of, row["lead_days"])
                        if block["clear_to_ship"]
                        else None
                    ),
                    "why": (
                        f"specialty {row['specialty']!r}"
                        + (" matches the product" if matches else " does not match the product")
                        + ("; clear to ship" if block["clear_to_ship"] else "; BLOCKED by an open invoice")
                        + f"; {row['lead_days']} day lead"
                    ),
                }
            )

        candidates.sort(
            key=lambda c: (
                not c["specialty_matches_product"],
                not c["clear_to_ship"],
                c["lead_days"],
            )
        )

        estimated_cost = (
            round(price["unit_cost"] * requested_qty, 2)
            if requested_qty is not None
            else None
        )

    return {
        "as_of": as_of,
        "sku": price["sku"],
        "product_name": product_name,
        "unit_cost": price["unit_cost"],
        "requested_qty": requested_qty,
        "estimated_cost": estimated_cost,
        "approved": False,
        "requires_human_approval": True,
        "note": "This is a suggestion only. Vendor selection affects cash, "
        "fulfilment and product quality, so a human must verify it. Nothing has "
        "been ordered or recorded.",
        "candidates": candidates,
    }


# --- proposals ----------------------------------------------------------------
# Everything below *records a recommendation*. Nothing here pays, orders, applies
# a price, or sends a message. Each row lands with approved_by NULL, and no tool
# can fill that in — only a human can.


def _record_proposal(conn, **fields) -> int:
    """Insert one proposal and return its id. Always unapproved."""
    cols = (
        "ticket_id", "kind", "status", "summary", "details", "amount",
        "vendor_id", "sku", "size", "qty", "created_by", "created_on",
    )
    values = [fields.get(c) for c in cols]
    cur = conn.execute(
        f"INSERT INTO proposals ({', '.join(cols)}) "
        f"VALUES ({', '.join('?' for _ in cols)})",
        values,
    )
    conn.commit()
    return cur.lastrowid


@mcp.tool
def draft_restock_po(
    sku: str,
    size: str,
    qty: int,
    vendor_id: int,
    ticket_id: int | None = None,
    created_by: str = "inventory",
    rationale: str = "",
) -> dict:
    """Draft a purchase order for restocking. **Drafts it — does not place it.**

    The draft is recorded awaiting human approval. No order is placed, no money
    moves, and no stock changes. Before recording, this checks what the database
    can tell us: whether the vendor may ship at all, and whether the cost fits the
    cash on hand.

    A draft is still recorded when the vendor is blocked or the cash is short —
    with those problems attached — because a human needs to see the blocked
    option, not an empty answer.

    Args:
        sku: SKU to restock.
        size: Size to restock. Inventory is keyed by SKU and size together.
        qty: Units to order.
        vendor_id: Vendor to order from. Use `suggest_vendor_for_sku` first; the
            suggestion is not an approval.
        ticket_id: Ticket this belongs to.
        created_by: Agent drafting it.
        rationale: Why this restock is proposed.

    Returns:
        `proposal_id`, `placed: false`, `requires_human_approval: true`, the
        costing, and any `problems` found.
    """
    with connect_rw() as conn:
        as_of = today(conn)

        price = conn.execute(
            "SELECT unit_cost FROM pricing WHERE UPPER(sku) = UPPER(?)", (sku,)
        ).fetchone()
        if price is None:
            return {"ok": False, "error": f"No such SKU: {sku}", "placed": False}

        vendor = conn.execute(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?",
            (vendor_id,),
        ).fetchone()
        if vendor is None:
            return {"ok": False, "error": f"No such vendor: {vendor_id}", "placed": False}

        on_hand_row = conn.execute(
            "SELECT qty FROM inventory WHERE UPPER(sku) = UPPER(?) AND UPPER(size) = UPPER(?)",
            (sku, size),
        ).fetchone()
        have = on_hand_row["qty"] if on_hand_row else 0

        # Refuse an order nothing needs. Stock that has already arrived, or an
        # order still in flight, both mean this one would double-buy.
        in_flight = conn.execute(
            "SELECT id, status FROM proposals WHERE kind = 'restock_po' "
            "AND UPPER(sku) = UPPER(?) AND UPPER(size) = UPPER(?) "
            "AND received_by IS NULL ORDER BY id DESC LIMIT 1",
            (sku, size),
        ).fetchone()
        if in_flight is not None:
            return {
                "ok": False,
                "placed": False,
                "existing_proposal_id": in_flight["id"],
                "reason": (
                    f"Purchase order {in_flight['id']} for {sku} size {size} is already "
                    f"on the board ({in_flight['status']}) and has not been received. "
                    "Drafting another would double-order."
                ),
                "guidance": "Report the existing order to the Boss instead.",
            }

        cost = round(price["unit_cost"] * qty, 2)
        cash = conn.execute("SELECT SUM(balance) AS total FROM cash_accounts").fetchone()
        cash_total = round(cash["total"] or 0.0, 2)

        block = _vendor_block(conn, vendor_id)
        problems = []
        if not block["clear_to_ship"]:
            ids = ", ".join(str(i["id"]) for i in block["blocking_invoices"])
            problems.append(
                f"{vendor['name']} is blocked by open invoice(s) {ids} "
                f"(${block['blocking_total']:.2f}) and cannot ship until a human pays."
            )
        if cost > cash_total:
            problems.append(
                f"Cost ${cost:.2f} exceeds cash on hand ${cash_total:.2f}."
            )

        summary = (
            f"Restock {qty} x {sku} size {size} from {vendor['name']} "
            f"at ${cost:.2f}"
        )
        details = _json.dumps(
            {
                "unit_cost": price["unit_cost"],
                "qty": qty,
                "cost": cost,
                "vendor": vendor["name"],
                "lead_days": vendor["lead_days"],
                "earliest_delivery": (
                    add_days(as_of, vendor["lead_days"])
                    if block["clear_to_ship"]
                    else None
                ),
                "on_hand": have,
                "cash_before": cash_total,
                "cash_after_if_approved": round(cash_total - cost, 2),
                "rationale": rationale,
                "problems": problems,
            }
        )

        proposal_id = _record_proposal(
            conn,
            ticket_id=ticket_id,
            kind="restock_po",
            status="awaiting_approval",
            summary=summary,
            details=details,
            amount=cost,
            vendor_id=vendor_id,
            sku=sku,
            size=size,
            qty=qty,
            created_by=created_by,
            created_on=as_of,
        )

    return {
        "ok": True,
        "proposal_id": proposal_id,
        "placed": False,
        "requires_human_approval": True,
        "summary": summary,
        "cost": cost,
        "cash_before": cash_total,
        "cash_after_if_approved": round(cash_total - cost, 2),
        "vendor": vendor["name"],
        "lead_days": vendor["lead_days"],
        "clear_to_ship": block["clear_to_ship"],
        "problems": problems,
        "note": "Drafted only. No order was placed and no money moved.",
    }


@mcp.tool
def record_discount_decision(
    sku: str,
    qty: int,
    proposed_unit_price: float,
    ticket_id: int | None = None,
    size: str | None = None,
    created_by: str = "accounting",
    rationale: str = "",
) -> dict:
    """Record a proposed price override. **Records it — does not apply it.**

    The margin is computed here from `pricing`, so the numbers in the record are
    the database's, not an agent's arithmetic. The proposal lands awaiting human
    approval; list price is unchanged and no sale happens.

    Args:
        sku: SKU the discount applies to.
        qty: Units in the request.
        proposed_unit_price: The per-unit price being proposed.
        ticket_id: Ticket this belongs to.
        size: Size requested, when relevant.
        created_by: Agent recording it.
        rationale: Why this is being proposed.

    Returns:
        `proposal_id`, `applied: false`, `requires_human_approval: true`, and the
        full margin comparison at list price versus the proposed price.
    """
    with connect_rw() as conn:
        as_of = today(conn)

        price = conn.execute(
            "SELECT sku, unit_cost, list_price FROM pricing WHERE UPPER(sku) = UPPER(?)",
            (sku,),
        ).fetchone()
        if price is None:
            return {"ok": False, "error": f"No such SKU: {sku}", "applied": False}

        unit_cost = price["unit_cost"]
        list_price = price["list_price"]
        discount_pct = (
            round((list_price - proposed_unit_price) / list_price * 100, 1)
            if list_price
            else None
        )
        margin_at_list = _margin_pct(unit_cost, list_price)
        margin_at_proposed = _margin_pct(unit_cost, proposed_unit_price)
        below_cost = proposed_unit_price < unit_cost

        problems = []
        if below_cost:
            problems.append(
                f"Proposed price ${proposed_unit_price:.2f} is below unit cost "
                f"${unit_cost:.2f} — every unit sold loses money."
            )

        on_hand = conn.execute(
            "SELECT SUM(qty) AS q FROM inventory WHERE UPPER(sku) = UPPER(?)"
            + (" AND UPPER(size) = UPPER(?)" if size else ""),
            (sku, size) if size else (sku,),
        ).fetchone()
        available = (on_hand["q"] or 0) if on_hand else 0
        if available < qty:
            problems.append(
                f"Only {available} units in stock against {qty} requested; the "
                "shortfall needs a restock a human has approved."
            )

        summary = (
            f"Price override: {qty} x {sku} at ${proposed_unit_price:.2f} "
            f"(list ${list_price:.2f}, {discount_pct}% off)"
        )
        details = _json.dumps(
            {
                "unit_cost": unit_cost,
                "list_price": list_price,
                "proposed_unit_price": proposed_unit_price,
                "discount_pct": discount_pct,
                "margin_pct_at_list": margin_at_list,
                "margin_pct_at_proposed": margin_at_proposed,
                "margin_per_unit_at_proposed": round(proposed_unit_price - unit_cost, 2),
                "qty": qty,
                "revenue_if_approved": round(proposed_unit_price * qty, 2),
                "margin_total_if_approved": round((proposed_unit_price - unit_cost) * qty, 2),
                "available_now": available,
                "below_cost": below_cost,
                "rationale": rationale,
                "problems": problems,
            }
        )

        proposal_id = _record_proposal(
            conn,
            ticket_id=ticket_id,
            kind="price_override",
            status="awaiting_approval",
            summary=summary,
            details=details,
            amount=round(proposed_unit_price * qty, 2),
            sku=sku,
            size=size,
            qty=qty,
            created_by=created_by,
            created_on=as_of,
        )

    return {
        "ok": True,
        "proposal_id": proposal_id,
        "applied": False,
        "requires_human_approval": True,
        "summary": summary,
        "unit_cost": unit_cost,
        "list_price": list_price,
        "proposed_unit_price": proposed_unit_price,
        "discount_pct": discount_pct,
        "margin_pct_at_list": margin_at_list,
        "margin_pct_at_proposed": margin_at_proposed,
        "available_now": available,
        "problems": problems,
        "note": "Recorded only. The list price is unchanged and no sale was made.",
    }


#: Words that reveal how the shop runs. A customer is owed an answer about their
#: order — whether we can fill it and roughly when — not an account of our
#: invoices, suppliers, cash position or internal sign-offs.
_INTERNAL_TERMS = (
    "invoice", "purchase order", " po ", "po#", "vendor", "supplier",
    "approval", "approve", "approved", "unapproved", "sign-off", "signoff",
    "payment", "paid", "unpaid", "cash", "budget", "funds", "overdue",
    "restock", "reorder", "proposal", "procurement", "internal",
    "lead time", "manager", "finance", "accounting", "awaiting",
)


def _internal_leaks(text: str) -> list[str]:
    """Internal-process terms found in customer-facing copy."""
    padded = f" {text.lower()} "
    return sorted({term.strip() for term in _INTERNAL_TERMS if term in padded})


@mcp.tool
def draft_customer_message(
    subject: str,
    body: str,
    ticket_id: int | None = None,
    recipient: str | None = None,
    created_by: str = "customer_service",
) -> dict:
    """Save a customer-facing draft to the board. **Nothing is ever sent.**

    There is no send capability anywhere in this server. The draft is stored
    against its ticket for a human to read, edit and send themselves.

    Args:
        subject: Draft subject line.
        body: Draft message body.
        ticket_id: Ticket this belongs to.
        recipient: Who it would go to, for the human's reference.
        created_by: Agent that wrote it.

    Returns:
        `proposal_id`, `sent: false`, and a reminder that the draft stays on the
        board.
    """
    with connect_rw() as conn:
        as_of = today(conn)

        # Refuse copy that exposes how the shop runs. The customer is owed an
        # answer about their order, not our invoices, suppliers or sign-offs.
        leaks = _internal_leaks(f"{subject} {body}")
        if leaks:
            return {
                "ok": False,
                "saved": False,
                "sent": False,
                "rejected_terms": leaks,
                "reason": (
                    "This draft describes internal process. A customer may be told "
                    "whether their order can be filled and roughly when — never why "
                    "not, and never how the shop operates."
                ),
                "guidance": (
                    "Rewrite without these terms: " + ", ".join(leaks) + ". "
                    "Say only what it means for their order. Good: \"Your size S tee "
                    "is not available yet; we expect it within about a week and will "
                    "confirm once it arrives.\" Bad: anything naming an invoice, a "
                    "supplier, a purchase order, a payment or an approval."
                ),
            }

        # One open draft per ticket. The customer should hear from us when there is
        # something to tell them, not after every internal step.
        if ticket_id is not None:
            existing = conn.execute(
                "SELECT id, summary FROM proposals WHERE ticket_id = ? "
                "AND kind = 'customer_draft' AND approved_by IS NULL ORDER BY id DESC "
                "LIMIT 1",
                (ticket_id,),
            ).fetchone()
            if existing is not None:
                return {
                    "ok": False,
                    "saved": False,
                    "sent": False,
                    "existing_draft_id": existing["id"],
                    "reason": (
                        f"Draft {existing['id']} for ticket {ticket_id} is already on "
                        "the board awaiting a human. Do not write another."
                    ),
                    "guidance": (
                        "Report the existing draft to the Boss instead. Write a new "
                        "one only once the outcome has materially changed for the "
                        "customer — their order is ready, or it cannot be filled."
                    ),
                }

        if ticket_id is not None and recipient is None:
            row = conn.execute(
                "SELECT requester FROM tickets WHERE id = ?", (ticket_id,)
            ).fetchone()
            if row is not None:
                recipient = row["requester"]

        details = _json.dumps(
            {"subject": subject, "body": body, "recipient": recipient}
        )
        proposal_id = _record_proposal(
            conn,
            ticket_id=ticket_id,
            kind="customer_draft",
            status="awaiting_approval",
            summary=f"Draft to {recipient or 'customer'}: {subject}",
            details=details,
            created_by=created_by,
            created_on=as_of,
        )

    return {
        "ok": True,
        "proposal_id": proposal_id,
        "sent": False,
        "recipient": recipient,
        "subject": subject,
        "note": "Draft saved to the board. It was not sent — this server has no "
        "send capability.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Campus Customs operations MCP")
    parser.add_argument("--http", action="store_true", help="serve over HTTP")
    parser.add_argument("--port", type=int, default=8003, help="HTTP port")
    args = parser.parse_args()

    if args.http:
        mcp.run(transport="http", host="127.0.0.1", port=args.port)
    else:
        mcp.run()
