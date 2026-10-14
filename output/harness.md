# Campus Customs — Data Harness

Field notes on the Campus Customs database, written so the agent team can read
the schema without guessing at what a column means.

- **Seed (never written to):** `campus_customs.db`
- **Working copy (agents read/write):** `data/campus_customs_new.db`
- **Tables:** 9 seeded — `cash_accounts`, `desk`, `inventory`, `invoices`,
  `leases`, `payments`, `pricing`, `tickets`, `vendors` — plus **`proposals`**,
  added to the working copy to hold recommendations awaiting a human. Ten in total;
  see [The `proposals` table](#the-proposals-table).

Descriptions below are the operator's own field notes. Types and keys are read
from the live schema.

**Contents:** [Safety rules](#safety-rules) · tables 1-9 · cross-table notes ·
[The agent team](#the-agent-team) · [MCP tools](#mcp-tools) ·
[Backend API](#backend-api) · [Dashboard](#dashboard)

---

# Safety rules

These bind every agent. Where a rule can be enforced in tool code rather than
asked for in a prompt, it is — an agent cannot reason its way past a guard that
lives in the tool.

## 1. No agent may make a payment

Agents must **not** pay invoices, pay rent, or actually place purchase orders.
They may inspect financial information and make recommendations; actual payment
requires human verification and approval.

**How this is enforced:** there is no payment tool. The MCP server exposes nothing
that writes to `payments`, moves cash, or places an order. The closest tools —
`draft_restock_po` and `record_discount_decision` — return `placed: false` and
`applied: false`, and write a row to `proposals` with `approved_by` **NULL**. No
tool can set `approved_by`; only a human can.

Verified across two live runs: `payments` stayed empty, cash stayed at $3,400.00,
and all three proposals came back unapproved.

## 2. The database is the only source of truth

Shop facts come only from `data/campus_customs_new.db`, through the MCP server.
Never invent or guess data. If something is unknown, confirm it or say so — be
honest rather than plausible.

**How this is enforced:** every agent's structured response carries `answered` and
`missing`. An agent that cannot find something sets `answered=false` and lists
what was missing, which the Boss must then carry into the final answer. The audit
trail records the *actual* tool calls from the model's message history, so a claim
that is not backed by a tool call is visible after the fact.

## 3. No private or external sources

Agents must not access private links or outside sources of data.

**How this is enforced:** no agent has web, file or network access. The only
toolset any agent holds is the local MCP server, which speaks stdio and reads one
SQLite file. There is no send capability either — `draft_customer_message` saves
to the board and sends nothing.

## 4. Work efficiently

Do not spend many rounds going back and forth. Cap the exchange at **2-3 rounds**.

**How this is enforced:** `MAX_ITERATIONS = 3` in `backend/config.py`, tunable to 2
via the environment. Each round is one Boss call plus the specialists it
dispatches, which run **concurrently** — so one round with three specialists costs
roughly one round of wall-clock time. `hit_iteration_limit` is reported, so a
truncated run is visible rather than silent.

**Specialist-to-specialist traffic is structurally impossible.** The team is
hub-and-spoke: specialists answer within their own domain and hand results back to
the Boss, which is the only agent that routes. Two specialists therefore cannot
loop between themselves. The Boss also cannot delegate to itself — invalid targets
are dropped before dispatch and recorded as `invalid_delegation`.

## 5. Always `gpt-6-luna`, never upgrade

Other models cost too much.

**How this is enforced:** one constant, `MODEL_NAME`, in `backend/config.py`,
imported by all six agent instances. It is read from `MODEL_NAME` and **never**
from `PORTKEY_MODEL` — the inherited parent `.env` sets that to a different model,
and reading it would silently run the whole team on the wrong one with no error.

**Note:** `gpt-6-luna` on this gateway rejects function tools unless
`openai_reasoning_effort="none"` is set. It is set. Do not remove it.

---

## 1. `cash_accounts`

The shop's money. One row per account.

| Field | Type | Key | Description |
|---|---|---|---|
| `name` | TEXT | **PK** | Account name (e.g. petty cash) |
| `balance` | REAL | not null | Amount of money in the account |
| `date` | TEXT | not null | Date the balance was recorded |

**Seeded:** one account, `checking`, balance **3400.0**, as of `2026-08-31`.

---

## 2. `desk`

The shop's operating context. Single row.

| Field | Type | Key | Description |
|---|---|---|---|
| `date_today` | TEXT | not null | Today's operational date as recognised by the system |
| `notes` | TEXT | nullable | Additional information supporting the operational process |

**Seeded:** `date_today` = **2026-08-31**, notes empty.

---

## 3. `inventory`

What is physically on the shelf. Keyed by SKU **and** size — one SKU spans
several rows.

| Field | Type | Key | Description |
|---|---|---|---|
| `sku` | TEXT | **PK (1/2)** | Identifier |
| `name` | TEXT | not null | Name of the product, also an identifier technically |
| `size` | TEXT | **PK (2/2)** | Size of the product (small, medium, etc.) |
| `qty` | INTEGER | not null | Number of products |
| `location` | TEXT | not null | Location of the products |

**Observed sizes:** `S`, `M`, `L`, `XL`, `OS` (one-size).
**Seeded:** 10 rows across 4 SKUs. Two are at zero — `CC-TEE-WHITE` size S and
`CC-MUG-CREST` size OS.

---

## 4. `invoices`

Money owed to vendors.

| Field | Type | Key | Description |
|---|---|---|---|
| `id` | INTEGER | **PK** | Identifier of transaction |
| `vendor_id` | INTEGER | not null, **FK → `vendors.id`** | Identifier of the vendor |
| `amount` | REAL | not null | Amount of money stated in the invoice |
| `due_date` | TEXT | not null | Deadline date to pay the invoice |
| `status` | TEXT | not null | Whether the invoice has been processed or not (current progress) |
| `description` | TEXT | nullable | Description of the invoice |

**Observed status:** `open`.
**Seeded:** one invoice, **501** — vendor 1, **$840.00**, due `2026-08-28`,
status `open`, "Rush reprint CC-TEE-WHITE S".

---

## 5. `leases`

The shop space and what it costs.

| Field | Type | Key | Description |
|---|---|---|---|
| `id` | INTEGER | **PK** | Identifier of the lease |
| `space_name` | TEXT | not null | Name of the place leased |
| `landlord` | TEXT | not null | Owner of the place |
| `monthly_rent` | REAL | not null | Amount of money for rent payable monthly |
| `next_due` | TEXT | not null | Next deadline to pay the rent |
| `notes` | TEXT | nullable | Additional description |

**Seeded:** lease **1** — Chapel Street shop, Elm City Properties, **$2,400.00**
monthly, next due `2026-09-02`.

---

## 6. `payments`

The cash-out ledger. **Empty at seed** — every row here is created by the system
during a run, and only after a human has approved it.

| Field | Type | Key | Description |
|---|---|---|---|
| `id` | INTEGER | **PK** | Identifier of each transaction |
| `kind` | TEXT | not null | Type of payment |
| `ref_id` | INTEGER | nullable | ID for payment reference |
| `amount` | REAL | not null | Amount of payment |
| `account` | TEXT | not null | Account used to make the payment |
| `paid_at` | TEXT | not null | Time the payment is made |
| `approved_by` | TEXT | not null | Name of the human who approves the payment |

**`approved_by` is NOT NULL and has no default.** A payment physically cannot be
written without naming its human approver — the approval rule is enforced by the
schema, not only by agent instructions.

**`ref_id`** is a soft pointer, not a foreign key: it points into `invoices.id`
when `kind` is an invoice payment, and into `leases.id` when it is rent. Whoever
writes the row must set `kind` and `ref_id` consistently.

---

## 7. `pricing`

Unit economics per SKU. One row per SKU — **price does not vary by size**.

| Field | Type | Key | Description |
|---|---|---|---|
| `sku` | TEXT | **PK** | Product identifier |
| `unit_cost` | REAL | not null | Cost to make 1 product |
| `list_price` | REAL | not null | Price of 1 unit of the product |

**Seeded:**

| sku | unit_cost | list_price | margin |
|---|---|---|---|
| CC-HOOD-NAVY | 22.00 | 58.00 | 62.1% |
| CC-TEE-WHITE | 8.00 | 28.00 | 71.4% |
| CC-HAT-BLUE | 6.00 | 22.00 | 72.7% |
| CC-MUG-CREST | 3.50 | 14.00 | 75.0% |

---

## 8. `tickets`

The work board. Everything the agent team does starts here.

| Field | Type | Key | Description |
|---|---|---|---|
| `id` | INTEGER | **PK** | Identifier of the ticket |
| `type` | TEXT | not null | Type of ticket |
| `requester` | TEXT | not null | Who requests |
| `subject` | TEXT | not null | Title of the ticket |
| `sku` | TEXT | nullable | SKU related to the ticket |
| `size` | TEXT | nullable | Product size related to the ticket |
| `qty` | INTEGER | nullable | Quantity in the ticket |
| `lease_id` | INTEGER | nullable, **FK → `leases.id`** | Lease ID in the ticket |
| `invoice_id` | INTEGER | nullable, **FK → `invoices.id`** | Invoice ID in the ticket |
| `status` | TEXT | not null | Ticket status |
| `notes` | TEXT | nullable | Additional description of the ticket |
| `created_at` | TEXT | not null | Time the ticket was created |

**Observed types:** `customer_order`, `rent_notice`, `price_override`.
**Observed status:** `open`.

**The `type` field is the routing key.** Each type populates a different foreign
key, so the Boss agent can route on structure rather than parsing free text:

| type | populates | implies |
|---|---|---|
| `customer_order` | `sku`, `size`, `qty`, **`invoice_id`** | a vendor obligation to clear first |
| `rent_notice` | **`lease_id`** | a dated obligation against a lease |
| `price_override` | `sku`, `size`, `qty`, *neither FK* | no obligation — a margin question |

`notes` is context for the working agent, not a routing signal.

---

## 9. `vendors`

Who can supply what, and how fast.

| Field | Type | Key | Description |
|---|---|---|---|
| `id` | INTEGER | **PK** | Vendor identifier |
| `name` | TEXT | not null | Name of the vendor |
| `specialty` | TEXT | not null | Vendor's service or goods |
| `lead_days` | INTEGER | not null | Days the vendor needs to produce and ship units — used to predict how long we wait |

**Seeded:**

| id | name | specialty | lead_days |
|---|---|---|---|
| 1 | Bulldog Print Co | apparel reprint | 5 |
| 2 | Elm City Gifts | mugs and small goods | 3 |
| 3 | QuickShip CT | local courier | 1 |

`specialty` is free text, not an enum — matching a SKU to a vendor is a judgement
call for the Inventory agent, not a lookup.

---

## Cross-table notes for the agents

**Dates are stored in two different formats.** Comparing them naively will
produce wrong answers:

| Column | Format | Example |
|---|---|---|
| `desk.date_today` | plain date | `2026-08-31` |
| `invoices.due_date` | plain date | `2026-08-28` |
| `leases.next_due` | plain date | `2026-09-02` |
| `cash_accounts.date` | plain date | `2026-08-31` |
| `tickets.created_at` | ISO 8601 with offset | `2026-08-31T09:15:00-04:00` |
| `payments.paid_at` | *(unset — table empty)* | — |

Overdue checks compare plain dates against `desk.date_today` and sort correctly
as strings. `tickets.created_at` must be truncated to its date part before being
compared with any of them. `payments.paid_at` has no precedent in the seed, so
the writing tool must fix a format — matching `created_at` (ISO 8601 with
offset) keeps the two timestamp columns consistent.

**There is no revenue table.** Money only leaves. `cash_accounts.balance` is
strictly decreasing over a run, which is why every spend competes with every
other spend.

**No `qty` is reserved or held.** `inventory.qty` is simply what is on the
shelf — nothing in the schema expresses "promised to a customer". If an agent
commits stock to a ticket, that commitment lives in the ticket, not the
inventory.

**The vendor-ships gate is not in the schema.** The rule that a vendor with an
open unpaid invoice cannot ship is a business rule to be enforced in tool code:
join `vendors` → `invoices` on `vendor_id` and check for `status = 'open'`.
Nothing in the database prevents it otherwise.
---

# The agent team

Five agents, **hub-and-spoke**: the Boss routes and verifies, specialists work
within their own domain and hand results back. Specialists do not decide who
handles what. Flow:

```
user -> Boss -> specialists (using tools) -> Boss (verify) -> user
```

Responsibilities below are the operator's own words. Implementation notes follow
each.

## Boss agent

Understanding the user's request, identifying which specialist agent(s) are needed
(the Boss must know each agent's tools and responsibilities), delegating the tasks
based on the specialist agent's responsibilities, combining results from multiple
specialist agents if needed (meaning if the request requires information from
multiple domains, the Boss may call multiple specialist agents), verifying and
clarifying the specialists' results if needed, and returning the final response to
the user.

**Tools:** `get_ticket_info`, `update_ticket_status`

**Implementation:** two agent instances. `boss_router` decides each round whether
to delegate and to whom (`BossDecision`); `boss_finalizer` writes and verifies the
answer once (`FinalAnswer`). The finaliser holds no tools — it writes the answer
and touches no data. Every factual claim in the final answer must trace to a
specialist's finding; anything unestablished goes to `unresolved` instead.
Approvals raised by any specialist are merged into the final answer even if the
Boss omits them, so a decision the human must make cannot be silently dropped.

## Inventory agent

Managing and informing information related to: products, SKUs, stock quantity,
sizes, colours, product availability (including low stock and out-of-stock
products), and locations. **Important:** the Inventory Agent should use
inventory/product tools or the database, never invent or guess.

**Tools:** `get_product_info`, `get_vendor_info`, `suggest_vendor_for_sku`,
`draft_restock_po`

**Implementation:** holds no financial tool, so it cannot answer affordability —
that is Accounting's. Inventory is keyed by SKU **and** size, so stock answers are
always qualified by size. A vendor suggestion is returned `approved: false`, and a
restock PO is `placed: false`.

## Accounting agent

Prices, sales, revenue, expenses, refunds, payments, financial transactions,
financial summaries, and other tasks related to the finance record (such as telling
us whether we have enough cash or not). **Important:** the Accounting Agent should
use accounting/transaction tools and the database. It must never invent or guess
financial numbers. It should be very careful when working with numbers and never
make any mistakes. It should also never make any payment without verification.

**Tools:** `get_financial_info`, `get_product_info`, `get_vendor_info`,
`record_discount_decision`

**Implementation:** it holds `get_product_info` because unit cost and list price
live in `pricing`, so a margin question is unanswerable without it. Margin
arithmetic for a discount is computed **by the tool**, not by the agent, so the
recorded numbers are the database's. Per safety rule 1 it cannot pay at all —
there is no payment tool — so its prompt says it *cannot* pay rather than that it
must seek approval first.

## Facilities agent

Tasks related to logistics, e.g. stores, warehouses, physical facilities,
equipment, maintenance, repairs, incidents, etc. (including tracking numbers and
status if any).

**Tools:** `get_lease_info`

**Implementation:** the database holds **leases only**. There are no tables for
warehouses, equipment, maintenance, repairs, incidents or shipment tracking, so
the prompt instructs the agent to say plainly that the data does not exist rather
than estimate. Rent is a payment, so Facilities reports what is due and when; it
does not pay it.

## Customer Service agent

Tasks related to customer data, order data (including details, status, etc.),
returns, complaints, exchanges, refunds, and other customer-facing support. **Note:**
this agent's responsibilities may overlap with other specialists (e.g. Accounting,
when it comes to whether a refund has been processed).

**Tools:** `get_ticket_info`, `draft_customer_message`

**Implementation:** customer and order records live in `tickets`, which is its own
domain. Product, stock, price and cash lookups were deliberately withheld so it
cannot duplicate Inventory or Accounting — on an overlapping question the Boss
delegates to both and combines the answers. **Drafts are never sent**; there is no
send capability anywhere in the server.

---

# MCP Tools

Ten tools, served by `mcp_server/server.py` over FastMCP. Six read, four write —
and **none of the four writes money, places an order, applies a price, or sends a
message.**

Every tool reads `desk.date_today` and stamps its answer `as_of`, so overdue and
days-until-due figures are computed against the shop's date rather than the system
clock (business rule 1).

| # | Tool | Reads/Writes | Serves tickets | Used by |
|---|---|---|---|---|
| 1 | `get_ticket_info` | read | 101, 102, 103 | Boss, Customer Service |
| 2 | `update_ticket_status` | **write** | 101, 102, 103 | Boss |
| 3 | `get_product_info` | read | 101, 103 | Inventory, Accounting |
| 4 | `get_vendor_info` | read | 101, 103 | Inventory, Accounting |
| 5 | `suggest_vendor_for_sku` | read | 101, 103 | Inventory |
| 6 | `draft_restock_po` | **write** | 101, 103 | Inventory |
| 7 | `get_financial_info` | read | 102, 103 | Accounting |
| 8 | `record_discount_decision` | **write** | 103 | Accounting |
| 9 | `get_lease_info` | read | 102 | Facilities |
| 10 | `draft_customer_message` | **write** | 101, 103 | Customer Service |

Tools 3, 7 and 9 were the original three. The other seven were added in Problem 5B.

---

## 1. `get_ticket_info` — read

**Reads:** `desk`, `tickets`, `invoices`, `leases`, `vendors`, `proposals`
**Unlocks tickets:** 101, 102, 103 — the board itself

Reads the work queue the team routes from. Each ticket's type implies a different
foreign key, and the linked record is resolved here so the board can be read in one
call: a `customer_order` points at an invoice, a `rent_notice` at a lease, a
`price_override` at neither. Proposals already raised against a ticket come back
with it.

**Arguments:** `ticket_id`, `status`, `ticket_type`

`tickets.created_at` is ISO-8601 with an offset, unlike every other date in the
schema; the tool truncates it before any date comparison and returns `created_on`
and `age_days`.

## 2. `update_ticket_status` — write

**Writes:** `tickets.status`, `tickets.notes`
**Unlocks tickets:** 101, 102, 103

Moves a ticket to `open`, `pending`, `blocked` or `closed`. **A ticket may only be
closed once its outcome is verifiable in the database**, checked per type:

| Ticket type | Close requires |
|---|---|
| `customer_order` | stock covers the request **and** no linked invoice is still open |
| `rent_notice` | a rent payment recorded in `payments` — which no tool can make |
| `price_override` | a price-override proposal carrying a human approver |

A refused close leaves the ticket untouched and returns the reason, so the caller
can set `pending` or `blocked` instead. Because no tool can pay, **ticket 102
cannot be closed by any agent** — that is the designed outcome, not a defect.

**Arguments:** `ticket_id`, `status`, `note`

## 3. `get_product_info` — read

**Reads:** `desk`, `inventory`, `pricing`
**Unlocks tickets:** 101, 103

*Operator's note:* With this tool, I expect the agent to get back to me with data
needed in the database — e.g. product, SKU, size, qty, and others — which is highly
tailored to 101 (a customer order ticket) and 103 (price override). Among all the
product data it can take, I hope the agent can pick data that is relevant to the
ticket only.

**Arguments:** `sku`, `name_contains`, `size`, `requested_qty`

Every argument is optional, so the agent narrows the query rather than filtering a
full dump afterwards. Passing `requested_qty` returns `available_qty`, `shortfall`
and `can_fulfil_from_stock` already computed, handing over the decision rather than
arithmetic. Inventory is keyed by SKU **and** size; pricing is per SKU and does not
vary by size.

## 4. `get_vendor_info` — read

**Reads:** `desk`, `vendors`, `invoices`
**Unlocks tickets:** 101, 103

Vendors, their `lead_days`, and whether each may currently ship. **`clear_to_ship`
is computed by the tool from open invoices** — business rule 3, straight from the
database, never an agent's judgement. Returns `blocking_invoices` and
`earliest_delivery` when the vendor is clear.

**Arguments:** `vendor_id`, `specialty_contains`

## 5. `suggest_vendor_for_sku` — read

**Reads:** `desk`, `pricing`, `inventory`, `vendors`, `invoices`
**Unlocks tickets:** 101, 103

Suggests which vendor could restock a SKU, ranked from database values: specialty
match first, then clear-to-ship, then shortest lead time. Each candidate carries a
`why` explaining its placement.

**A suggestion is not an approval.** The result always returns `approved: false`
and `requires_human_approval: true`, because vendor selection affects cash,
fulfilment and product quality. Calling it orders nothing and **records nothing**.

**Arguments:** `sku`, `requested_qty`

## 6. `draft_restock_po` — write

**Writes:** `proposals` (`kind='restock_po'`, `approved_by` NULL)
**Unlocks tickets:** 101, 103

Drafts a purchase order. **It does not place one.** Returns `placed: false`. Before
recording it checks what the database can tell us — whether the vendor may ship,
and whether the cost fits the cash on hand — and attaches any `problems` found.

A draft is still recorded when the vendor is blocked or cash is short, because a
human needs to see the blocked option rather than an empty answer.

**Arguments:** `sku`, `size`, `qty`, `vendor_id`, `ticket_id`, `created_by`,
`rationale`

## 7. `get_financial_info` — read

**Reads:** `desk`, `cash_accounts`, `invoices`, `vendors`, `leases`
**Unlocks tickets:** 102, 103

*Operator's note:* I want the agent to be able to access financial data,
especially the product's price (103) and the amount of cash we have (relevant for
102, rent) — i.e. I want the agent to know how much cash we have before we pay.

**Arguments:** `account`, `include_invoices`, `include_leases`, `invoice_status`, `vendor_id`

Returns the cash accounts with `total_cash`, and invoices with their vendor, lead
time and overdue standing (`days_until_due`, `is_overdue`, `days_overdue`), plus
`open_invoice_total` and `cash_after_open_invoices`.

**On product price:** unit cost, list price and margin come from **`get_product_info`**,
because `pricing` is keyed by SKU and belongs with the product. For ticket 103
Accounting calls both — `get_product_info` for the margin, this tool for whether a
restock is affordable.

**Rent is included as an obligation.** Both things that draw cash down — unpaid
invoices and rent falling due — come back together, so affordability is answerable
in one call. `leases` carries each lease with `monthly_rent`, `next_due`,
`days_until_due` and `is_overdue`; `rent_due_total`, `total_obligations`,
`cash_after_obligations` and `can_meet_all_obligations` summarise the position.

Set `include_leases=False` for an invoices-only answer.

*Why this was added:* the tool originally read invoices but not leases, and in a
live run that cost a full round — Accounting could see $3,400 in cash but not the
rent amount, returned `answered=false`, and the Boss had to spend a round passing
it a figure Facilities already held. With leases included, the same rent question
now resolves in **2 rounds instead of 3**, and the whole cash squeeze —
$3,400 − $840 − $2,400 = **$160** — comes from a single call.

## 8. `record_discount_decision` — write

**Writes:** `proposals` (`kind='price_override'`, `approved_by` NULL)
**Unlocks tickets:** 103

Records a **proposed** price override. **It does not apply one.** Returns
`applied: false`; the list price is unchanged and no sale happens.

The margin comparison is computed **by the tool** from `pricing` — discount
percentage, margin at list versus at the proposed price, per-unit and total margin,
revenue if approved — so the record carries the database's numbers rather than the
agent's arithmetic. Flags selling below cost, and a stock shortfall against the
requested quantity.

**Arguments:** `sku`, `qty`, `proposed_unit_price`, `ticket_id`, `size`,
`created_by`, `rationale`

## 9. `get_lease_info` — read

**Reads:** `desk`, `leases`
**Unlocks tickets:** 102

*Operator's note:* This tool can be used for 102 (rent lease), so the agent and I
can verify lease data such as space, landlord, monthly rent and due date before
doing any payment.

**Arguments:** `lease_id`

Returns each lease with `days_until_due` and `is_overdue` computed against the
shop's date, plus `total_monthly_rent`.

## 10. `draft_customer_message` — write

**Writes:** `proposals` (`kind='customer_draft'`, `approved_by` NULL)
**Unlocks tickets:** 101, 103

Saves a customer-facing draft to the board against its ticket. **Nothing is ever
sent** — returns `sent: false`, and there is no send capability anywhere in this
server. The recipient is resolved from the ticket's `requester` when not given.

**Arguments:** `subject`, `body`, `ticket_id`, `recipient`, `created_by`

---

## The `proposals` table

Four of the ten tools record a recommendation, and the seeded schema had nowhere
to put one — `payments.approved_by` is the only approval concept in the database,
and it requires an *executed* payment, which safety rule 1 forbids. So a single
table was added **to the working copy only**:

```
proposals(id, ticket_id, kind, status, summary, details, amount,
          vendor_id, sku, size, qty, created_by, created_on, approved_by)
```

`kind` is one of `vendor_suggestion`, `restock_po`, `price_override`,
`customer_draft`. All four are the same shape — a recommendation awaiting a human —
so they share one table.

**`approved_by` mirrors `payments.approved_by`: NULL means unapproved, and no tool
can fill it in.** Only a human can.

The table is created idempotently when the server starts, so it survives a reset:
resetting copies the seed over the working copy, which drops the table, and the
next start recreates it empty. **The seed is never touched.**

**Consequence for reset checks:** the working copy's SHA-256 no longer matches the
seed, because it carries this extra table. The seed still hashes to
`23686a90...f360a`. Verify a reset by **row counts** — 3 open tickets, $3,400.00 in
checking, `payments` empty, `proposals` empty — not by comparing hashes.

---

## Still not built — on the MCP side

- No tool reads the `payments` ledger, so an agent cannot answer "has this been
  paid?". Payments now exist once a human approves one, so this gap is real
  rather than theoretical.
- **No reset tool, by design.** Resetting is an operator action — either
  `POST /api/reset` or a manual `cp` (business rule 7). It is kept off the agents'
  toolset deliberately.

Note that `payments` is written only by `backend/approvals.py`, never by the MCP
server — see [Backend API](#backend-api).
---

# Backend API

FastAPI, served by `backend/main.py`. Twelve routes.

**Base URL:** `http://localhost:8000` — **plain HTTP, not HTTPS.** Uvicorn serves
no TLS listener, so a dashboard calling `https://localhost:8000` fails with a
connection error that looks like the backend is down.

Run it from the `backend/` folder:

```
../.venv/bin/python -m uvicorn main:app --reload --port 8000
```

`--reload` runs a supervisor **and** a worker, so stop the whole group rather than
only the listener:

```
pkill -f "uvicorn main:app"; sleep 2; pgrep -f "uvicorn main:app" || echo "stopped"
```

Interactive docs: `http://localhost:8000/docs`. CORS is allowed for
`http://localhost:5173` and `http://127.0.0.1:5173`, the Vite dev origins.

## Where spending lives

This matters more than any individual route. The agents' entire toolset is the MCP
server, which has **no payment tool**. Money moves in exactly one module —
`backend/approvals.py` — reachable only through the three `/api/approve/*` routes a
human invokes.

An agent has no HTTP client and no import path to that module, so there is no route
by which it can spend. **"Agents prepare, humans execute" is structural here, not a
policy an agent could be argued past.**

## Routes

| Method | Path | Purpose | Spends? |
|---|---|---|---|
| GET | `/api/tickets` | Lists tickets, their resolution status, and related records | — |
| GET | `/api/cash` | Current cash position, obligations, and payment history | — |
| POST | `/api/tickets/{ticket_id}/run` | Starts the agent team for a specific ticket | — |
| GET | `/api/runs` | Lists agent runs since server startup | — |
| GET | `/api/runs/{run_id}` | Outcome of a specific run | — |
| GET | `/api/activity` | Recent agent activity, messages, and MCP tool calls | — |
| GET | `/api/approvals` | Lists proposals awaiting human decisions | — |
| POST | `/api/approve/proposal/{proposal_id}` | Approves an agent proposal | **only a restock PO** |
| POST | `/api/approve/invoice/{invoice_id}` | Pays a vendor invoice after human approval | **yes** |
| POST | `/api/approve/rent/{lease_id}` | Pays rent after human approval | **yes** |
| POST | `/api/receive/{proposal_id}` | Confirms an approved purchase order was delivered | — (moves **stock**, not cash) |
| POST | `/api/reset` | Restores the database to its original state | — |
| GET | `/api/health` | Reports API health and configuration details | — |

---

## `GET /api/tickets`

Every ticket with its linked invoice or lease resolved, and any proposals raised
against it.

`resolved` is **true only when the status is `closed`**. A ticket that is `pending`
or `blocked` is still outstanding work, so it reports unresolved. Counts for
`open` and `resolved` come back alongside.

`closed_by` names **who** closed it — `agent` when the Boss did, `system` when the
post-run reconciliation pass did because the close guard found nothing blocking.
Surfaced so a green badge is never left standing beside an agent conclusion that
hedges; the reader can see which one closed it.

## `GET /api/cash`

`checking`, the account rows, `open_invoice_total`, `rent_due_total`,
`total_obligations`, `cash_after_obligations`, `can_meet_all_obligations`,
`total_spent`, and the last 20 payments.

No revenue is modelled, so the balance only ever falls (business rule 6).

## `POST /api/tickets/{ticket_id}/run`

Composes a request from the ticket and starts the agent team.

**Returns immediately** with a `run_id`. A run takes minutes and many model calls,
so it is dispatched to the background — a blocking call could not support watching
the work in progress. Poll `/api/activity` to follow it, or `/api/runs/{run_id}`
for the outcome.

404 if the ticket does not exist.

## `GET /api/runs` · `GET /api/runs/{run_id}`

Runs started since the server booted, held in memory: status (`queued`, `running`,
`finished`, `failed`), iterations used, whether the cap was hit, agents consulted,
the final answer, unresolved items, approvals raised.

Runs are **not** persisted — the durable record is the append-only audit trail,
which survives a restart. `POST /api/reset` clears this list.

## `GET /api/activity`

The audit trail, newest last, shaped as a feed: `agent`, `message`, `answered`,
`missing`, `tools_used` (tool name, arguments, outcome), `approvals_required`,
`draft_message`.

**Tool calls are the ones actually made**, read from the model's message history
rather than from what an agent claimed it did.

| Parameter | Purpose |
|---|---|
| `since_id` | Return only records after this `record_id` — poll without re-reading the whole trail |
| `limit` | Cap the number returned (default 60) |
| `ticket_id` | Restrict to runs for one ticket |

## `GET /api/approvals`

Everything awaiting a human, in three groups: unapproved `proposals`,
`payable_invoices`, and `payable_rent`. Each carries an `affordable` flag computed
against the current balance.

## `POST /api/approve/proposal/{proposal_id}`

Body: `{"approved_by": "<name>"}`.

**Not every approval spends.** A `restock_po` moves cash; a `price_override`
authorises a price; a `customer_draft` is released for a human to send. The
response carries an `effect` line saying what actually happened.

Refuses with **409** when: the proposal is already approved, the vendor still holds
an open invoice and cannot ship, or the cost exceeds available cash.

**Approving a PO does not increment inventory.** Stock arrives after the vendor's
lead time, which the schema cannot express, so claiming delivery would be false.

## `POST /api/approve/invoice/{invoice_id}`

Body: `{"approved_by": "<name>"}`. **Spends money.**

Inserts a `payments` row, decrements cash, and marks the invoice `paid` — which
**unblocks that vendor for shipping** under business rule 3.

Refuses with 409 when already paid, or when the payment would overdraw.

## `POST /api/approve/rent/{lease_id}`

Body: `{"approved_by": "<name>"}`. **Spends money.**

Inserts a `payments` row, decrements cash, and rolls `leases.next_due` forward one
month. Refuses with 409 when rent for that due date is already paid, or when it
would overdraw.

## `POST /api/receive/{proposal_id}`

Body: `{"received_by": "<name>", "qty": <optional>}`.

Records that an approved purchase order **physically arrived**. This is the only
route that **increases stock**, and like payment it is a human action — no agent can
reach it.

Paying for an order and receiving it are different events separated by the vendor's
lead time. Approving spends the money; this records the delivery turning up.
**Without it a `customer_order` ticket can never close**, because the close guard
waits for stock that nothing else produces.

`qty` records a short delivery as what actually turned up rather than what was
ordered. The vendor's expected delivery date is reported for context but **not**
enforced — the shop's date never advances, so blocking on it would recreate the
deadlock.

Refuses with **409** for a non-purchase-order proposal, an unapproved order, a
double receipt, a missing SKU or size, or an inventory line that does not exist.

**Approving a purchase order does not increment inventory** — only this route does.

## `POST /api/reset`

Copies the pristine seed over the working copy — business rule 7. The seed is read,
never written. The `proposals` table is dropped by the copy and recreated empty.
In-memory run history is cleared.

**The audit trail is deliberately not cleared** — it is append-only by instruction,
and wiping it would destroy the record of how the system behaved.

Returns the restored state so a reset can be verified by row counts.

## `GET /api/health`

Model in use, iteration cap, resolved database path, shop date, table list, audit
trail path, and a one-line statement of where spending lives.

---

## Three guards every spending route enforces

| Guard | Behaviour |
|---|---|
| **An approver is required** | `approved_by` must be non-empty — **422** otherwise, before the database is touched. `payments.approved_by` is also NOT NULL in the schema. |
| **The balance may never go negative** | Checked in code before any write — **409** with the arithmetic shown, e.g. *"holds $160.00 and this would spend $264.00, leaving $-104.00. Refused."* |
| **Nothing is applied partially** | A refusal leaves the database exactly as it was: no payment row, no balance change, no status flip. |

Verified live: an empty approver returned 422; paying invoice 501 took cash from
$3,400.00 to $2,560.00 and marked it paid; paying it again returned 409; rent took
cash to $160.00 and rolled the lease to 2026-10-02; approving a $264.00 PO against
$160.00 returned 409 with cash unchanged; reset restored all of it, with the seed
still hashing to `23686a90...f360a` and the audit trail intact.


---

# Dashboard

React + Vite + TypeScript, served at `http://localhost:5173`. It calls `/api/*`,
which Vite proxies to the backend — the browser only ever talks to one origin, so
CORS cannot bite in development.

**The backend is plain HTTP.** `https://localhost:8000` fails with a connection
error that reads as "the backend is down" rather than as a protocol mismatch.

## Layout

```
┌──────────────────────────────────────────────────────────┐
│  NAVY TITLE BAR            white text      Checking $…   │
├────────────────┬──────────────────────────┬──────────────┤
│  Tickets       │  Selected ticket + Run   │  Awaiting    │
│  (left rail)   │  What the team concluded │  approval —  │
│  status colour │  Agent activity          │  this ticket │
│  on each edge  │                          │              │
├────────────────┴──────────────────────────┴──────────────┤
│  Awaiting your approval — the shop's own obligations      │
└──────────────────────────────────────────────────────────┘
```

Two columns on desktop; the ticket's own approval panel collapses beneath the
ticket below 1100px, and the whole layout goes single-column below 900px.

## What each region does

| Region | Shows |
|---|---|
| **Title bar** | The one solid navy surface, so its text is white. Carries the **checking balance**, which flashes amber when it changes — tying an approval to the money actually leaving. |
| **Tickets rail** | All tickets with a status colour on the badge **and** the left border, so the rail can be scanned without reading. A **Reset to original data** button sits beneath. |
| **Ticket panel** | The selected ticket's facts, a **Run the agent team** button, what the team concluded, and `closed_by` when resolved. |
| **Agent activity** | Each agent that acted, in order: name, round, a one or two sentence summary, the MCP tools it actually called, anything it could not determine, and any customer draft — marked *not sent*. An "— agents resumed —" divider separates passes. |
| **Ticket approvals** *(right)* | Only what a run produced for **this** ticket: drafted purchase orders, price proposals, customer drafts, deliveries to confirm. |
| **Main approvals** *(bottom)* | Only the shop's **standing obligations** — unpaid invoices and rent — which exist whether or not an agent ever runs. |

## Design

Minimalist, white-dominant with navy as an accent. White is the surface; navy
appears only on the title bar, primary buttons, the selected ticket, and the left
edge of an approval that spends money. Title navy is **`#000080`**. Typeface is
**Arial at weight 300**, with **black on white and white on navy** as the only body
pairings. Full rationale in [`design.md`](design.md).

## Ticket status colours

| State | Colour | When |
|---|---|---|
| **Resolved** | Green `#1b7a3d` | Ticket status is `closed` |
| **Agents working** | Yellow `#8a6a00` | A run is live for that ticket |
| **Not resolved** | Red `#b3261e` | `open`, `pending` or `blocked`, no run active |

Colour is never the only signal — each badge pairs a coloured dot with a text
label, so state survives colour-blindness and greyscale. The yellow dot pulses, and
only while a run is live.

**Green means verified done**, not "the agents said they finished": it requires
`status = closed`, and the backend refuses to close a ticket whose outcome it cannot
verify. A fully worked ticket still awaiting a human stays red.

## Behaviour worth knowing

- **Runs are backgrounded.** Starting one returns immediately; the board polls
  every 2s while a run is live and 4s otherwise.
- **Approving resumes the ticket.** Every human decision — invoice, rent, proposal,
  delivery — automatically restarts the agents on the ticket it unblocked, and the
  board follows that run. Without this an approval was a dead end.
- **Activity follows the selected ticket**, across every run it has had, capped at
  the four most recent. Keying it to a single run id made each approval erase the
  work before it.
- **Reset hides earlier activity.** The audit trail stays append-only and complete;
  the dashboard stops showing runs from before the last reset, so a stale row cannot
  sit beside a fresh one contradicting it.
- **Refusals are shown verbatim** — "holds $160.00 and this would spend $264.00,
  leaving $-104.00" is more useful than a generic failure.
