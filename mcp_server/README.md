# Campus Customs — Operations MCP Server

**MCP server:** FastMCP

**Database file it uses:** `data/campus_customs_new.db` — copied from the original
`campus_customs.db` file, which we have decided not to change anything to, to keep
it original for reset purposes.

**Ten tools it has** — six read, four write:

| # | Tool | Kind |
|---|---|---|
| 1 | `get_ticket_info` | read |
| 2 | `update_ticket_status` | write |
| 3 | `get_product_info` | read |
| 4 | `get_vendor_info` | read |
| 5 | `suggest_vendor_for_sku` | read |
| 6 | `draft_restock_po` | write |
| 7 | `get_financial_info` | read |
| 8 | `record_discount_decision` | write |
| 9 | `get_lease_info` | read |
| 10 | `draft_customer_message` | write |

Tools 3, 7 and 9 were the original three. The other seven were added in Problem 5B.

---

## The tools

| Tool | Reads / writes | Serves tickets | Answers |
|---|---|---|---|
| `get_ticket_info` | reads `desk`, `tickets`, `invoices`, `leases`, `proposals` | 101, 102, 103 | What is on the board, and what is attached to each ticket? |
| `update_ticket_status` | writes `tickets.status`, `tickets.notes` | 101, 102, 103 | Move a ticket — but a close is refused unless the outcome is verifiable |
| `get_product_info` | reads `desk`, `inventory`, `pricing` | 101, 103 | What is it, what is on the shelf, what does it cost? |
| `get_vendor_info` | reads `desk`, `vendors`, `invoices` | 101, 103 | Who can supply this, how fast, and may they ship at all? |
| `suggest_vendor_for_sku` | reads `desk`, `pricing`, `inventory`, `vendors`, `invoices` | 101, 103 | Which vendor *could* restock this? **A suggestion, not an approval** |
| `draft_restock_po` | writes `proposals` | 101, 103 | Draft a purchase order — **does not place one** |
| `get_financial_info` | reads `desk`, `cash_accounts`, `invoices`, `vendors`, `leases` | 102, 103 | How much cash do we have, and what do we owe — invoices **and** rent? |
| `record_discount_decision` | writes `proposals` | 103 | Record a proposed price override — **does not apply one** |
| `get_lease_info` | reads `desk`, `leases` | 102 | What is the space, the landlord, the rent, and when is it due? |
| `draft_customer_message` | writes `proposals` | 101, 103 | Save a customer draft — **never sends it** |

Every argument on every tool is optional except the few a write genuinely needs, so
an agent narrows the query to what its ticket needs rather than filtering a full
dump afterwards.

Field-by-field documentation, the safety rules, the agent team and a section per
tool are in [`../output/harness.md`](../output/harness.md).

## Three guarantees

**No agent can spend money.** There is deliberately no tool to pay an invoice, pay
rent, or place a purchase order. The four write tools only *record a
recommendation*: they return `placed: false`, `applied: false` or `sent: false`,
and write a `proposals` row whose `approved_by` is NULL. **No tool can set
`approved_by`** — only a human can.

**Reads cannot write.** Read tools open with SQLite's `mode=ro` flag, so a stray
write raises `attempt to write a readonly database` rather than silently
succeeding. Writes go through a separate `connect_rw()` helper, keeping the narrow
write surface visibly distinct from ordinary reads.

**It never reads the system clock.** "Today" is `desk.date_today`, read through
`db.today()` by every tool. Every response is stamped `as_of`, and overdue and
days-until-due figures are computed server-side against the shop's date. An agent
cannot get dates wrong by reasoning about them itself.

## The close guard

`update_ticket_status` refuses to close a ticket whose outcome is not verifiable in
the database:

| Ticket type | Close requires |
|---|---|
| `customer_order` | stock covers the request **and** no linked invoice is still open |
| `rent_notice` | a rent payment recorded in `payments` — which no tool can make |
| `price_override` | a price-override proposal carrying a human approver |

A refused close leaves the ticket untouched and returns the reason, so the caller
can set `pending` or `blocked` instead. Because nothing can pay, **ticket 102
cannot be closed by any agent** — that is the designed outcome, not a defect.

## The `proposals` table

Four tools record a recommendation, and the seeded schema had nowhere to put one.
A single table is added **to the working copy only**:

```
proposals(id, ticket_id, kind, status, summary, details, amount,
          vendor_id, sku, size, qty, created_by, created_on, approved_by)
```

`kind` is one of `vendor_suggestion`, `restock_po`, `price_override`,
`customer_draft`. It is created idempotently at server start, so it survives a
reset: resetting drops it along with everything else the seed lacks, and the next
start recreates it empty. **The seed is never touched.**

## Running it

The server is wired to the agent team and registered as `campus-customs-ops` in
`.mcp.json`.

Install once:

```bash
cd "/Users/nurazizahmaharani/Desktop/AI Foundations/Homework 5" && python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
```

Run over stdio, which is how an MCP client launches it:

```bash
cd "/Users/nurazizahmaharani/Desktop/AI Foundations/Homework 5/mcp_server" && ../.venv/bin/python server.py
```

Or over HTTP at `http://127.0.0.1:8003/mcp`:

```bash
cd "/Users/nurazizahmaharani/Desktop/AI Foundations/Homework 5/mcp_server" && ../.venv/bin/python server.py --http
```

Port 8003 follows the course convention — Lecture 09 uses 8001, the Outlook
server 8002.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `CAMPUS_DB_PATH` | `data/campus_customs_new.db` | The working copy. Relative paths resolve from the project root. |

Every connection resolves through this one variable, so the pristine seed cannot
be opened by accident. See [`.env.example`](../.env.example).

## Resetting

Business rule 7 requires resetting before a full run. There is no reset tool, by
design — it is an operator action:

```bash
cd "/Users/nurazizahmaharani/Desktop/AI Foundations/Homework 5" && cp -p campus_customs.db data/campus_customs_new.db
```

**Verify a reset by row counts, not by hash.** The working copy carries the
`proposals` table, which the seed does not, so their SHA-256 values no longer
match — that is expected, not corruption. A correct reset gives:

| Check | Expected |
|---|---|
| tickets | 101, 102, 103 all `open` |
| `cash_accounts.checking` | $3,400.00 |
| `payments` | empty |
| `proposals` | empty (recreated on next server start) |
| `desk.date_today` | `2026-08-31` |

The seed itself still hashes to `23686a90…f360a` and should never change.

## Files

| File | Purpose |
|---|---|
| `server.py` | FastMCP app and the ten tools |
| `db.py` | Path resolution, read-only and read-write connections, the `proposals` schema, date helpers |

## Not provided, deliberately

- **No payment tools.** No `pay_invoice`, no `pay_rent`, no "place purchase
  order". Agents inspect the finances and recommend; a human verifies and
  executes. This is safety rule 1 — see
  [`../output/harness.md`](../output/harness.md).
- **No send capability.** Drafts stay on the board.
- **No `reset_database` tool** — resetting is the operator's action, above.

## Obligations in one call

`get_financial_info` returns **both** things that draw cash down — unpaid invoices
and rent falling due — so affordability is answerable in a single call:
`total_obligations`, `cash_after_obligations` and `can_meet_all_obligations`.

It originally read invoices but not leases, and in a live run that cost a full
round: Accounting could see the cash but not the rent, and the Boss had to pass it
a figure Facilities already held. The same rent question now resolves in **2 rounds
instead of 3**.
