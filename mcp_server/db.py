"""Database access for the Campus Customs MCP server.

Every connection resolves through CAMPUS_DB_PATH so the pristine seed can never
be opened by accident:

    campus_customs.db          seed, never written to
    data/campus_customs_new.db working copy, this is what we open

The read tools open the file in SQLite read-only mode (``mode=ro``), so a write
raises rather than silently succeeding.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = PROJECT_ROOT / "data" / "campus_customs_new.db"


def db_path() -> Path:
    """The working-copy database. Override with CAMPUS_DB_PATH."""
    configured = os.getenv("CAMPUS_DB_PATH")
    if not configured:
        return DEFAULT_DB
    path = Path(configured).expanduser()
    return path if path.is_absolute() else (PROJECT_ROOT / path)


def connect_ro() -> sqlite3.Connection:
    """Open the working copy read-only. Rows come back as mappings."""
    path = db_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Campus Customs database not found at {path}. "
            "Copy campus_customs.db to data/campus_customs_new.db, "
            "or set CAMPUS_DB_PATH."
        )
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def today(conn: sqlite3.Connection) -> str:
    """The shop's operating date from desk.date_today.

    Business rule 1: this is "today", never the system clock. Overdue maths
    benchmarks against this value.
    """
    row = conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    if row is None:
        raise RuntimeError("desk table is empty — no operating date is set.")
    return row["date_today"]


def days_between(from_date: str, to_date: str) -> int:
    """Whole days from `from_date` to `to_date`; negative if `to_date` is earlier.

    Both arguments are plain ISO dates (YYYY-MM-DD). Timestamps carrying a time
    component, such as tickets.created_at, must be truncated by the caller.
    """
    return (date.fromisoformat(to_date) - date.fromisoformat(from_date)).days


# --- write side ---------------------------------------------------------------
# Read tools use connect_ro() above. Everything below is the narrow write surface
# the agents are allowed: recording proposals and moving a ticket's status. There
# is deliberately no way to pay an invoice, pay rent, or place a purchase order —
# those require a human, and no tool exposes them.

PROPOSAL_KINDS = (
    "vendor_suggestion",
    "restock_po",
    "price_override",
    "customer_draft",
)

TICKET_STATUSES = ("open", "pending", "blocked", "closed")

#: Added to the working copy, not to the seed. `approved_by` mirrors the
#: semantics of `payments.approved_by`: NULL means no human has approved this, and
#: nothing the agents can do will fill it in.
_PROPOSALS_DDL = """
CREATE TABLE IF NOT EXISTS proposals (
    id INTEGER PRIMARY KEY,
    ticket_id INTEGER,
    kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'awaiting_approval',
    summary TEXT NOT NULL,
    details TEXT,
    amount REAL,
    vendor_id INTEGER,
    sku TEXT,
    size TEXT,
    qty INTEGER,
    created_by TEXT NOT NULL,
    created_on TEXT NOT NULL,
    approved_by TEXT,
    received_by TEXT,
    received_on TEXT,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id),
    FOREIGN KEY (vendor_id) REFERENCES vendors(id)
)
"""


def connect_rw() -> sqlite3.Connection:
    """Open the working copy read-write, with foreign keys enforced."""
    path = db_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Campus Customs database not found at {path}. "
            "Copy campus_customs.db to data/campus_customs_new.db, "
            "or set CAMPUS_DB_PATH."
        )
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema() -> None:
    """Create the proposals table if it is absent.

    Idempotent, and safe to call after a reset: resetting copies the seed over the
    working copy, which drops this table, and the next server start recreates it
    empty. The seed itself is never touched.
    """
    with connect_rw() as conn:
        conn.execute(_PROPOSALS_DDL)

        # A working copy created before goods-receipt existed has the table but
        # not these columns. SQLite cannot ADD COLUMN IF NOT EXISTS, so check.
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(proposals)")}
        for column in ("received_by", "received_on"):
            if column not in existing:
                conn.execute(f"ALTER TABLE proposals ADD COLUMN {column} TEXT")

        conn.commit()


def add_days(start: str, days: int) -> str:
    """`start` (plain ISO date) shifted forward by `days`."""
    return (date.fromisoformat(start) + timedelta(days=days)).isoformat()
