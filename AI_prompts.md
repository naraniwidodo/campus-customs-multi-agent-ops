# AI Homework 5 Prompt Log

Project: Campus Customs Multi-Agent Operations — an agentic team that runs the shop
Date started: 2026-10-06
Working directory: `AI Foundations/Homework 5`

This file is the running record for Homework 5. It logs every user prompt, the
actions taken in response, the decisions made, and the reasoning behind them.
It is updated continuously as the project progresses.

---

## Session start

### Project goal

Build a multi-agent operations system for Campus Customs. Open tickets land on a
board — customer orders, rent notices, unpaid bills, discount requests — and an
agentic team works them while a human supervises and approves.

Three connected pieces:

1. **MCP server** — exposes the shop database as tools (read stock, cash,
   pricing, vendors, leases; write payments; update tickets). The agents' hands.
2. **FastAPI backend** — hosts the multi-agent team, orchestrates work on each
   ticket, and surfaces approval requests.
3. **React dashboard** — the human's window: ticket board, live agent activity,
   and approve/reject controls.

### The agent team

Full connectivity — any agent may delegate to any other. Boss routes, but the
topology is a mesh, not a star.

| Agent | Responsibility |
|---|---|
| **Boss** | Reads each ticket, decides which agent works it, makes final calls |
| **Inventory** | Stock by SKU and size, shortfall detection, vendor restock routing |
| **Accounting** | Cash and invoices, margin checks, prepares payments and POs for human approval |
| **Facilities** | Shop space — leases and rent |
| **Customer Service** | Drafts customer messages |

### Planned stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + TypeScript |
| Backend | Python FastAPI |
| Agents | Multi-agent team, full mesh delegation |
| Tools | MCP server over SQLite |
| Model | `gpt-6-luna` via Portkey (OpenAI-compatible) |
| Data | SQLite (`data/campus_customs_new.db`) |

### Relationship to Homework 4

Homework 4 built the Campus Customs *customer-facing* site — product browsing,
accounts, and a single shopping-assistant chatbot. Homework 5 is the *back
office*: a team of agents running shop operations behind the counter. Different
database, different system; HW4 is reference only, nothing copied.

---

## Prompt 1 — Start Homework 5

**User prompt:** "Hey, I want to do my HW 5 for AI Foundations for Manager course"

**Action taken:**
- Listed `Homework 5` — empty, no assignment file and no starter code.
- Surveyed the course folder for the working pattern of prior assignments.
- Read `Homework 4/README.md` to recover the established stack and conventions.
- Checked `~/Downloads` for an assignment brief.

**Findings recorded:**
- `Homework 5/` was empty.
- The HW5 PDFs in Downloads (`HW_5_revised.pdf`, `HW 5 Probability & Statistics
  …`) belong to **MGT 403 Probability Modeling and Statistics** — a different
  course, already submitted Oct 5. Not this assignment.
- HW4 established the house stack: React + Vite + TypeScript front end, FastAPI
  backend, Pydantic AI agent, SQLite.
- `Lecture 10` contains `mult_agent_hp`, a multi-agent example — the likely
  foundation for HW5.

**Outcome:** Could not proceed without the assignment. Asked the user to supply
the HW5 prompt rather than guessing at requirements.

---

## Prompt 2 — Unzip and move the database

**User prompt:** "First of all, I just downloaded the data right just now
(campus_customs.db). Can you access that? Unzip and move it to this Homework 5
folder"

**Action taken:**
- Located the file at `~/Downloads/data-4/campus_customs.db` — already
  decompressed, so no unzip step was needed.
- Moved it to `Homework 5/campus_customs.db` and removed the empty
  `data-4` directory.
- Dumped the full schema and every table's contents to understand the scenario.

**Findings recorded — the shop's opening state:**

Nine tables. `desk.date_today` = **2026-08-31**. `cash_accounts.checking` =
**$3,400**. The `payments` table is **empty** but carries a required
`approved_by` column — the structural hint that human approval is central.

Three open tickets, each engineered to require more than one agent:

| # | Type | Request | Complication |
|---|---|---|---|
| 101 | `customer_order` | Tauhid Zaman wants a Bulldog Tee, size S | **0 in stock**; linked to invoice 501 — $840 rush reprint from Bulldog Print Co, due 8/28, already overdue |
| 102 | `rent_notice` | Chapel Street rent, **$2,400**, due **9/02** | Two days out |
| 103 | `price_override` | Yale AI Club wants **20 navy hoodies, size M**, bulk discount | Only **8 M** in stock; cost $22, list $58 |

Supporting data: 3 vendors with lead times (Bulldog Print Co — apparel reprint,
5 days; Elm City Gifts — mugs and small goods, 3 days; QuickShip CT — local
courier, 1 day), 4 SKUs priced, 10 inventory rows with two SKUs at zero.

**The designed tension:** $2,400 rent + $840 invoice = **$3,240** against
**$3,400** cash. Everything fits, but with no margin for anything else.

**Outcome:** Database in place and understood. Assignment brief still needed.

---

## Prompt 3 — System context: Multi-Agent Operations

**User prompt:** Explained that the project is a Multi-Agent Operations system
for Campus Customs — tickets land on a board, and three pieces must be built
(MCP server, FastAPI backend with a multi-agent team, React dashboard so a human
can watch and approve). Defined five agents with full connectivity, any agent
able to delegate to any other: Boss, Inventory, Accounting, Facilities, Customer
Service. Instructed: *"Do nothing yet, just try to understand the context first."*

**Action taken:** No files created or modified, as instructed. Read the context
back to confirm alignment.

**Understanding recorded:**
- The topology is a **mesh**, not a star. Boss routes and arbitrates, but
  delegation is peer-to-peer.
- The seeded tickets each force cross-agent collaboration:
  - **#101** — Customer Service cannot answer until Inventory confirms the
    shortfall; Inventory routes to Bulldog Print Co; Accounting must clear the
    overdue invoice first. Three agents, chained.
  - **#102** — Facilities owns the lease, Accounting confirms the cash.
  - **#103** — Inventory finds the shortfall, Accounting checks margin on a
    discount off $58 against $22 cost, Customer Service drafts the reply.
- The cash constraint is what makes the approval queue substantive rather than
  ceremonial: the agents cannot satisfy everything, so a human must choose.

**Questions deferred to implementation:** which actions are hard-gated versus
auto-executed; whether delegation is modeled as agent-as-tool or a shared message
bus; whether the dashboard streams reasoning live or after the fact.

**Outcome:** Context confirmed. No work performed.

---

## Prompt 4 — Preserve the seed, work on a copy

**User prompt:** "Remember, this data is our initial database. However, we will
need to keep it (campus_customs.db) untouched, just in case we need to reset when
we restart resolving our tickets in the future. Make a copy of the database file
called data/campus_customs_new.db and point our MCP server and backend at that
working copy."

**Action taken:**
- Created `data/` and copied the database to `data/campus_customs_new.db`
  (`cp -p`, preserving timestamps).
- Verified the copy: both files hash to SHA-256 `23686a90…f360a`,
  `PRAGMA integrity_check` returns `ok`, and all 9 tables carry identical row
  counts (3 tickets, 10 inventory rows, 0 payments).

**Layout established:**

```
Homework 5/
├── campus_customs.db          ← pristine seed, never written to
└── data/
    └── campus_customs_new.db  ← working copy, agents read/write this
```

**Build contract recorded** (the MCP server and backend do not exist yet, so
there was nothing to repoint today):

- Single source of truth: env var **`CAMPUS_DB_PATH`**, defaulting to
  `data/campus_customs_new.db`, resolved from the project root.
- Both the MCP server and the FastAPI backend read that one variable. No
  hardcoded paths in either, so the seed cannot be opened by accident.
- `campus_customs.db` is referenced in exactly one place — a `reset` routine that
  copies seed → working copy, and only ever *reads* the seed.

**Outcome:** Working copy created and verified. Reset path defined: wipe the
working copy, re-copy from seed, and the board returns to three open tickets and
$3,400 in checking.

**Offered, awaiting user decision:** `chmod 444` on the seed so stray writes fail
loudly; and whether to move the seed into `data/` for symmetry.

---

## Prompt 5 — Campus Customs business rules

**User prompt:** Supplied eight operating rules for the shop, and asked for
confirmation of understanding.

**Rules recorded:**

1. **`desk.date_today` is "today"** (currently **2026-08-31**) — never the system
   clock. All overdue math benchmarks against it.
2. **Vendor lead times come from the `vendors` table** — never assumed.
3. **A vendor with an open unpaid invoice cannot ship.** Blocking precondition.
4. **Human approval is required for any payment.** Once approved and paid, write
   back: insert into `payments`, decrement `cash_accounts.balance`, flip
   `invoices.status`, roll `leases.next_due`.
5. **Check cash first.** If funds are insufficient the pay tool must *refuse* —
   no negative balances.
6. **Cash-out only.** No revenue is modeled, so the balance is strictly decreasing.
7. **Reset the database to original values before any full run.**
8. **Never send anything** to customers or vendors. Drafts stay on the board. If
   sending ever seems warranted, ask for confirmation first.

**Design decision:** Rule 5 is implemented as a **hard guard inside the tool**,
not as a prompt instruction — an agent must not be able to argue its way past the
cash check.

**Consequences derived from the rules:**

Rules 1 and 3 interact to create the critical path. Invoice 501 is **overdue by
3 days** (due 8/28, today 8/31) and belongs to **Bulldog Print Co**, whose
specialty is `apparel reprint`. By rule 3 Bulldog is **frozen**, which blocks
*both* apparel tickets:

- **#101** (tee, size S, 0 stock) — needs a Bulldog reprint → blocked until 501 is paid
- **#103** (20 navy hoodies, 8 in stock) — also apparel → also blocked behind 501

Invoice 501 is therefore not merely a bill; it is the gate on two of three
tickets. Paying it unfreezes Bulldog, and the 5-day lead time lands stock around
**9/05**.

Rules 5 and 6 then create the squeeze:

| | |
|---|---|
| Starting cash | **$3,400** |
| − Rent (#102, due 9/02) | −$2,400 |
| − Invoice 501 (#101 gate) | −$840 |
| **Remaining** | **$160** |

Both obligations fit, in either payment order. But the 12-hoodie shortfall on
**#103** costs **12 × $22 = $264** at cost, against **$160** remaining. By rule 5
that purchase order **must be refused** regardless of sequencing.

**#103 therefore cannot be fulfilled as asked.** It resolves as a human decision —
partial fill from the 8 in stock, defer, or human override — with Customer
Service drafting the reply and, per rule 8, **not sending it**.

**Outcome:** Rules confirmed and their implications mapped before any code.

---

## Prompt 6 — Pin the model

**User prompt:** "Only use gpt-6-luna until the end of the problem, don't
switch/change"

**Action taken:**
- Verified `gpt-6-luna` is a real model string rather than a slip. Confirmed: it
  is the default in `Lecture 10/mult_agent_hp/backend/agents/config.py:21`, the
  multi-agent example this homework builds on.
- Inspected the root `.env` for the inherited model configuration.

**Issue caught:** The root `.env` sets `PORTKEY_MODEL=gpt-5.6-luna`, and
`AGENTS.md` also names 5.6-luna as the project default. Wiring the backend to
read `PORTKEY_MODEL` — the obvious approach — would have silently run every agent
on **the wrong model**, with no error to reveal it.

**Design decision:**
- Pin `MODEL_NAME=gpt-6-luna` in this project's own config, taking precedence over
  the inherited `PORTKEY_MODEL`.
- Expose it as **one constant imported by all five agents**, so no agent can drift
  onto a different model.
- The API key continues to load from the root `.env` via `PORTKEY_API_KEY` and is
  never hardcoded.

`AGENTS.md` states its default applies "unless the task explicitly specifies
another model," so this instruction overrides it cleanly — no conflict.

**Outcome:** Model pinned to `gpt-6-luna` for the duration of the assignment.

---

## Prompt 7 — Problem 1A: create the prompt log

**User prompt:** "Problem 1A: Create AI_prompts.md to record our prompt log, keep
it updated as we work on our problem step by step"

**Action taken:**
- Reviewed `Homework 4/AI_prompts.md` to match the established format and
  conventions.
- Created this file, back-filled with all prior prompts in the session.

**Convention adopted:** one `## Prompt N` section per user turn, each recording
the prompt, the action taken, findings or decisions with their reasoning, and the
outcome. Updated continuously as work proceeds, not reconstructed at the end.

**Outcome:** `AI_prompts.md` created and current through prompt 7.

---

## Problem 1B — Prompt convention

**User prompt:** "Nothing to do on your end, I guess. I will just need to start
all prompts with the problem's number & title, a prompt that I typed by myself,
and follow up prompt if needed."

**Action taken:** No build work, as stated. Adjusted this log's structure to
match the user's prompting convention.

**Convention revised:**

- Sections are now keyed to **problem number and title** (`## Problem 1B — …`)
  rather than a running prompt counter, mirroring how prompts arrive.
- **Follow-up prompts attach to the problem they belong to**, as
  `**Follow-up N:**` entries inside that problem's section, so one problem reads
  as one continuous record even when it takes several turns.
- Prompts 1–7 above predate this convention and keep their original numbering.
  Problem 1A corresponds to prompt 7; everything from here is problem-keyed.
- All prompts are the user's own words, logged as received.

**Outcome:** Logging convention aligned with the user's prompting convention.
No code changes.

---

## Problem 2A — Read the three tickets, refresh the working copy

**User prompt:** Asked to open `campus_customs.db` and look at the 3 tickets
inside it, supplying them as:

1. ID 101 — `customer_order` — Bulldog tee — SKU CC-TEE-WHITE, size S, qty 1 → invoice 501
2. ID 102 — `rent_notice` — Rent due — lease 1
3. ID 103 — `price_override` — Bulk hoodie discount — SKU CC-HOOD-NAVY, size M, qty 20

Instructed to save the information for the agents' later use, noting the pattern
"order, rent, price override", and to copy the original `campus_customs.db` to
`data/campus_customs_new.db` for later updating.

**Action taken:**
- Checked the working copy for divergence **before** overwriting it: hashes were
  identical to the seed, all three tickets still `open`, cash untouched at
  $3,400, `payments` empty. Nothing would be lost.
- Re-copied seed → `data/campus_customs_new.db` with `cp -p`.
- Verified after: SHA-256 matches (`23686a90…f360a`), `PRAGMA integrity_check`
  returns `ok`.
- Read the tickets back from the working copy and confirmed they match the
  user's listing exactly.

**The three tickets, as stored:**

| id | type | subject | sku | size | qty | lease_id | invoice_id | status |
|---|---|---|---|---|---|---|---|---|
| 101 | `customer_order` | Bulldog tee | CC-TEE-WHITE | S | 1 | — | **501** | open |
| 102 | `rent_notice` | Rent due | — | — | — | **1** | — | open |
| 103 | `price_override` | Bulk hoodie discount | CC-HOOD-NAVY | M | 20 | — | — | open |

**Why this matters for the agents — the `type` field is the routing key.**

The three tickets are not three instances of one problem; they are three
*distinct shapes* of work, and the foreign-key columns say which agents each one
pulls in:

| type | carries | first owner | likely collaborators |
|---|---|---|---|
| `customer_order` | `sku`, `size`, `qty`, **`invoice_id`** | Inventory | Accounting (the invoice gate), Customer Service (the reply) |
| `rent_notice` | **`lease_id`** | Facilities | Accounting (cash check, payment prep) |
| `price_override` | `sku`, `size`, `qty`, *neither FK* | Accounting (margin) | Inventory (shortfall), Customer Service (the reply) |

Each ticket type populates a different foreign key — `invoice_id` for the order,
`lease_id` for the rent, neither for the discount request. That is the structural
signal the **Boss** agent routes on, rather than parsing free text: an order with
an attached invoice implies a vendor obligation to clear, a rent notice points at
a lease with a due date, and a price override carries no obligation at all — only
a margin question.

**Outcome:** Ticket information recorded for agent design. Working copy refreshed
from seed and verified; seed untouched.

---

## Problem 2B — Start `output/harness.md` with field notes

**User prompt:** Asked to start `output/harness.md` and record the operator's own
notes on the fields of each of the 9 tables in the Campus Customs database
(`cash_accounts`, `desk`, `inventory`, `invoices`, `leases`, `payments`,
`pricing`, `tickets`, `vendors`), with a short description per field so the
agents understand each field's function in later assignments. The full field
descriptions were supplied in the prompt.

**Action taken:**
- Created `output/` and wrote `output/harness.md`.
- Recorded the operator's field descriptions as the primary content, one section
  per table.
- Read the live schema (`PRAGMA table_info`) and added the **actual SQL type and
  key constraints** beside each description, so the agents get the declared
  contract rather than only prose.
- Added the seeded values per table, and observed value sets for the enum-like
  columns, since these are not discoverable from the schema alone.

**Schema details surfaced that the prose did not capture:**

- **`inventory` has a composite primary key** — `(sku, size)`. One SKU spans
  several rows, so stock questions must always be qualified by size.
- **`pricing` is keyed by SKU alone** — price does not vary by size. A size-M
  hoodie and a size-XL hoodie cost and list identically.
- **`payments.approved_by` is NOT NULL with no default.** The human-approval rule
  is therefore enforced by the schema itself, not merely by agent instructions —
  a payment row cannot physically be written without naming its approver.
- **`payments.ref_id` is a soft pointer, not a foreign key.** It points into
  `invoices.id` when `kind` is an invoice payment and into `leases.id` when it is
  rent, so `kind` and `ref_id` must be written consistently by the tool.
- **`vendors.specialty` is free text, not an enum.** Matching a SKU to a vendor is
  a judgement call for the Inventory agent, not a lookup.

**Cross-table hazards recorded for the agents:**

- **Two date formats coexist.** `desk.date_today`, `invoices.due_date`,
  `leases.next_due` and `cash_accounts.date` are plain dates (`2026-08-31`), but
  `tickets.created_at` is ISO 8601 with offset
  (`2026-08-31T09:15:00-04:00`). Plain dates sort correctly as strings;
  `created_at` must be truncated to its date part before comparison. `payments.paid_at`
  has no precedent in the seed, so the writing tool must fix a format — matching
  `created_at` keeps the two timestamp columns consistent.
- **No revenue table exists.** Cash is strictly decreasing, which is why every
  spend competes with every other spend.
- **No stock is reserved.** `inventory.qty` is what sits on the shelf; nothing in
  the schema expresses "promised to a customer". A commitment lives in the ticket.
- **The vendor-ships gate is not in the schema.** Rule 3 must be enforced in tool
  code by joining `vendors` → `invoices` on `vendor_id` and checking for
  `status = 'open'`. Nothing in the database enforces it.

Margins were computed from the seeded `pricing` rows and included for the
Accounting agent: CC-MUG-CREST 75.0%, CC-HAT-BLUE 72.7%, CC-TEE-WHITE 71.4%,
CC-HOOD-NAVY 62.1%.

**Outcome:** `output/harness.md` created — 9 table sections with the operator's
field descriptions, live types and keys, seeded values, and a cross-table hazards
section. No database changes.

---

## Session note — Save and pause

**User prompt:** "Save everything, I need to be away"

**Action taken:**
- Verified every file was already written to disk — nothing had been held in a
  buffer at any point.
- Confirmed database state: seed and working copy both hash to SHA-256
  `23686a90…f360a`, `PRAGMA integrity_check` returns `ok`.
- Confirmed the board is at clean seed state: tickets 101/102/103 all `open`,
  `checking` = $3,400.00, `payments` empty — so a full run can begin on return
  without needing a reset.
- Wrote continuity notes to the project's persistent memory, covering the
  decisions that exist only as agreements so far because no code has been written
  yet: project scope and architecture, the eight business rules, the `gpt-6-luna`
  pin and the `PORTKEY_MODEL` trap, the seed/working-copy convention with
  `CAMPUS_DB_PATH`, and this log's own convention.

**State at pause:**

```
Homework 5/
├── AI_prompts.md              log current through Problem 2B
├── campus_customs.db          pristine seed
├── data/
│   └── campus_customs_new.db  working copy
└── output/
    └── harness.md             field notes, all 9 tables
```

**Outcome:** Work saved and verified. Problems 1A, 1B, 2A and 2B complete; 2C is
next. Two items remain open and non-blocking: whether to `chmod 444` the seed,
and whether to move the seed into `data/` for symmetry.

---

## Session note — Logging convention extended to every turn

**User prompt:** "I think you should log every updates in that md file"

**Context:** At the end of the previous turn it was flagged that the save-and-pause
turn had *not* been logged, on the judgement that housekeeping was not a numbered
problem. The user corrected this.

**Action taken:**
- Back-filled the skipped save-and-pause turn as the preceding section.
- Logged this turn.
- Updated the stored convention note so the rule survives into future sessions.

**Convention revised:** **every turn is logged**, not only numbered problems.
Turns that belong to a numbered problem keep the `## Problem <N><letter> — <title>`
heading; turns that do not — saves, pauses, corrections, convention changes,
clarifying questions — are logged as `## Session note — <title>` in sequence. The
log is therefore a complete record of the session, not a record of its
deliverables only.

**Outcome:** Convention extended and the gap back-filled. The log now covers every
turn from the start of the session.

---

## Problem 3A — MCP server with three read tools

**User prompt:** Asked to write an MCP server in `mcp_server/` using FastMCP,
connecting the multi-agent team to the database file — without connecting or
running it yet, which comes in a later step. Specified three starting tools,
acknowledged as a set that will need extending:

1. `get_product_info` — for tickets 101 and 103; returns product, SKU, size, qty
   and related data, with the agent able to pick only what the ticket needs.
2. `get_financial_info` — for tickets 102 and 103; must let the agent see how
   much cash is available before paying.
3. `get_lease_info` — for ticket 102; returns space, landlord, monthly rent and
   due date, following the field names recorded in Problem 2B.

**Action taken:**
- Inspected the existing course MCP servers (`Lecture 09/.../mcp_server.py`,
  `mcp_servers/mcp_outlook_server.py`) to match the house convention:
  `from fastmcp import FastMCP`, `@mcp.tool` decorators, stdio by default with an
  `--http` flag and a dedicated port.
- Created a project venv and installed `fastmcp` (4.0.11); wrote
  `requirements.txt`.
- Wrote `mcp_server/db.py` — path resolution and connection handling.
- Wrote `mcp_server/server.py` — the three tools.
- Wrote `.env.example` and `.gitignore`.

**Files created:**

```
mcp_server/
├── db.py       path resolution, read-only connections, date helpers
└── server.py   FastMCP app + the three tools
.env.example
.gitignore
requirements.txt
```

**Design decisions and their reasoning:**

- **Read-only connections.** All three tools are reads, so `db.py` opens the
  database with SQLite's `mode=ro` URI flag. A write raises
  `OperationalError: attempt to write a readonly database` rather than silently
  succeeding. Verified by attempting an `UPDATE` — it was blocked. Write tools
  will need their own read-write connection helper, which keeps the
  approval-gated writes visibly separate from ordinary reads.
- **Single path resolution.** Every connection goes through `db.db_path()`,
  honouring `CAMPUS_DB_PATH` and defaulting to `data/campus_customs_new.db`
  resolved from the project root. This is the contract set in Problem 2A; the
  seed cannot be opened through it. Verified the resolved path is the working
  copy.
- **Business rule 1 is enforced in the data layer, not left to the agents.**
  `db.today()` reads `desk.date_today`, and every tool returns its answer stamped
  with `as_of`. No tool calls the system clock. All overdue and days-until-due
  figures are computed server-side against the shop's date, so an agent cannot
  get this wrong by reasoning about dates itself.
- **`db.days_between()` takes plain ISO dates only**, with a docstring noting
  that `tickets.created_at` must be truncated first — the two-date-format hazard
  recorded in Problem 2B.
- **Every filter argument is optional.** The user's requirement that the agent
  "pick data that is relevant to the ticket only" is met by letting the caller
  narrow — by SKU, size, account, vendor, invoice status, lease id — rather than
  by returning everything and expecting the agent to filter after the fact.
- **`get_product_info` takes an optional `requested_qty`.** When supplied it
  returns a `request` block with `available_qty`, `shortfall` and
  `can_fulfil_from_stock` already computed. The shortfall is the actual decision
  the Inventory agent needs for tickets 101 and 103, and computing it in the tool
  removes an arithmetic step from the model.
- **`get_financial_info` accepts `vendor_id` and `invoice_status`.** This is the
  query shape business rule 3 requires — "does this vendor hold an open unpaid
  invoice?" — so the vendor-ships gate can be answered with one call. Invoices
  are joined to `vendors` so the vendor's name, specialty and `lead_days` come
  back alongside, which is what the restock decision needs next.
- **Margins are returned with the product, not the finances.** `unit_margin` and
  `margin_pct` are derived from `pricing`, which is keyed by SKU, so they belong
  with the product. Pricing does not vary by size.
- **Port 8003** for HTTP mode, following Lecture 09 (8001) and the Outlook
  server (8002).

**Verification — all three tools called in-process against the working copy:**

| Call | Result |
|---|---|
| tools registered | `get_product_info`, `get_financial_info`, `get_lease_info` |
| T101 `get_product_info(sku=CC-TEE-WHITE, size=S, requested_qty=1)` | qty 0, **shortfall 1**, cannot fulfil; margin 71.4% |
| T103 `get_product_info(sku=CC-HOOD-NAVY, size=M, requested_qty=20)` | qty 8, **shortfall 12**, cannot fulfil; margin 62.1% |
| T102 `get_lease_info(lease_id=1)` | Chapel Street shop, Elm City Properties, $2,400.00, due 2026-09-02, **2 days out** |
| T102/T103 `get_financial_info()` | checking **$3,400.00**; invoice 501 **overdue by 3 days**; `cash_after_open_invoices` $2,560.00 |
| Rule 3 `get_financial_info(vendor_id=1, invoice_status='open')` | returns invoice 501 — Bulldog Print Co is **not clear to ship** |
| read-only guard | `UPDATE` blocked: "attempt to write a readonly database" |
| database integrity | seed and working copy both still SHA-256 `23686a90…f360a` |

Shortfalls of 1 and 12 match the figures derived by hand in Problem 2A, and the
3-day overdue figure matches the Bulldog-gate deduction from Prompt 5.

**Gaps identified — tools still needed**, consistent with the user's note that
the set will be extended:

- `get_ticket_info` / `list_tickets` — the Boss agent currently has no tool to
  read the board it routes from.
- `get_vendor_info` with a clear-to-ship flag — rule 3 is answerable today only
  indirectly, via an invoice query. The Inventory agent would be better served by
  a direct "can this vendor ship, and how many days?" call.
- **Write tools, all approval-gated:** `pay_invoice`, `pay_rent`, `update_ticket`,
  and a restock purchase order. These need the read-write connection helper and
  the hard cash guard required by rule 5, plus the `approved_by` value the schema
  demands.
- A `reset_database` tool or script for rule 7.

**Outcome:** `mcp_server/` written and verified against all three tickets. Not
connected to any agent and not run as a server — that is the next step, as the
user specified. Database unchanged.

---

## Problem 3B — Document the three MCP tools in `harness.md`

**User prompt:** Noted that part of this was already covered while answering 3A.
Asked to list the three MCP tools — `get_product_info`, `get_financial_info`,
`get_lease_info` — in `output/harness.md`, recording for each: which tables it
reads, which tickets it unlocks, and one sentence on why the tool is right. The
operator's own paragraphs for all three tools were supplied in the prompt, with a
note that changes may follow later.

**Action taken:**
- Appended an **MCP Tools** section to `output/harness.md`, one entry per tool.
- Recorded the operator's scoped table lists and reasoning paragraphs as written.
- Extracted the tables each tool *actually* queries from `mcp_server/server.py`
  and recorded those alongside, since the two differ.
- Added each tool's return fields, filter arguments, and the verified results
  against its tickets.

**Tables actually read, per the implementation:**

| Tool | Reads today |
|---|---|
| `get_product_info` | `desk`, `inventory`, `pricing` |
| `get_financial_info` | `desk`, `cash_accounts`, `invoices`, `vendors` |
| `get_lease_info` | `desk`, `leases` |

**Discrepancy identified and recorded rather than silently reconciled.** The
scoped table lists are broader than what the read-only implementation touches. The
difference was written up as a "Scope vs. implementation" table, framed as a
to-do list rather than an error, because the scoped lists describe the decisions
each tool is *meant* to support:

- **`tickets` is scoped for all three tools but read by none.** No ticket tool
  exists yet, so the Boss agent has no way to read the board it routes from. This
  is the largest gap, and it matches the one flagged in Problem 3A.
- **`payments` is scoped for tools 2 and 3 but read by neither** — the table is
  empty at seed, and rows appear only after human approval, which requires write
  tools that do not exist yet.
- **`vendors` is scoped for tools 1 and 3 but read only by tool 2**, and only via
  an invoice join. Rule 3 is therefore answerable today only by inference.
- **`leases` is scoped for tool 2 but read only by tool 3**, so rent is not yet
  visible as a financial obligation alongside invoices.
- **`desk` is scoped only for tool 2 but is read by all three**, via
  `db.today()` — which is how business rule 1 is made to hold everywhere.

**Second discrepancy flagged — where product price lives.** The operator's
reasoning for tool 2 includes "the product's price (103)", but `pricing` is keyed
by SKU and is returned by **tool 1**, not tool 2. This was recorded as a note
rather than changed: for ticket 103 the Accounting agent calls **both** tools —
tool 1 for the margin on the discount, tool 2 for whether a restock is
affordable. Moving pricing into tool 2 would duplicate it across two tools; the
alternative is left open for the operator to decide.

**Outcome:** `output/harness.md` now carries an MCP Tools section documenting all
three tools with the operator's reasoning, the tickets each unlocks, the tables
each is scoped for *and* actually reads, verified results, and an explicit list of
the tools still needed. No code or database changes.

**Follow-up 1 — add `mcp_server/README.md`.**

*User prompt:* Noted a forgotten part of 3B — asked to create
`mcp_server/README.md` containing a short explanation, supplied in the prompt:
the MCP server is FastMCP; the database file it uses is
`data/campus_customs_new.db`, copied from the original `campus_customs.db` which
was deliberately left unchanged for reset purposes; and it has three tools —
`get_product_info`, `get_financial_info`, `get_lease_info`.

*Action taken:* Created `mcp_server/README.md` with the operator's explanation as
the opening section, then added what a reader needs in order to actually use the
server:

- A tool table — what each reads, which tickets it serves, and the question it
  answers — with a pointer to `output/harness.md` for field-level detail, so the
  two documents do not duplicate each other.
- **Two guarantees stated explicitly:** the server cannot write (`mode=ro`), and
  it never reads the system clock (`desk.date_today` via `db.today()`, every
  response stamped `as_of`).
- Install and run commands for both stdio and HTTP, noting that port 8003 follows
  the course convention (Lecture 09 on 8001, the Outlook server on 8002), and
  stating plainly that the server is not yet wired to the agent team.
- The `CAMPUS_DB_PATH` configuration contract.
- **A reset procedure for business rule 7**, with the seed's SHA-256
  (`23686a90…f360a`) and the expected restored state — 3 open tickets, $3,400.00
  in checking, `payments` empty — so a reset can be *verified* rather than
  assumed.
- The list of tools still to add, kept consistent with `harness.md` and
  Problem 3A.

*Outcome:* `mcp_server/README.md` created. No code or database changes.

---

## Problem 4A — Register the MCP server so Claude can call its tools

**User prompt:** Asked to add the MCP server to the project so Claude can call the
tools, which will later help when working with the multi-agent team, and to save
the connection JSON in a `.mcp.json` placed where a local MCP server ideally
belongs.

**Action taken:**
- Created `Homework 5/.mcp.json` — project scope, beside the server it registers.
- Registered one server, `campus-customs-ops`, using absolute paths to the
  project venv's Python and to `mcp_server/server.py`, matching the style of the
  existing course `.mcp.json`.
- Pinned `CAMPUS_DB_PATH` to the working copy in the server's `env` block, so the
  database target does not depend on the directory the client happens to launch
  from.
- Smoke-tested the registration end to end.

**Connection JSON:**

```json
{
  "mcpServers": {
    "campus-customs-ops": {
      "command": ".../Homework 5/.venv/bin/python",
      "args": [".../Homework 5/mcp_server/server.py"],
      "env": { "CAMPUS_DB_PATH": ".../Homework 5/data/campus_customs_new.db" }
    }
  }
}
```

**Why project scope rather than the course-wide file:** the server is specific to
this homework, and `.mcp.json` sitting beside `mcp_server/` keeps the registration
and the thing it registers together. The course-wide
`AI Foundations/.mcp.json` was deliberately left untouched, since editing it would
affect other coursework.

**Verification — launched over stdio from `/tmp`,** deliberately an unrelated
working directory, so any hidden dependency on the launch directory would surface:

| Check | Result |
|---|---|
| handshake | OK |
| tools listed | `get_product_info`, `get_financial_info`, `get_lease_info` |
| `get_lease_info(lease_id=1)` | Chapel Street shop, Elm City Properties, $2,400.00, due 2026-09-02, 2 days out |
| `get_financial_info(include_invoices=False)` | `total_cash` 3400.0, `as_of` 2026-08-31 |

The `from db import ...` statement in `server.py` resolves correctly regardless of
launch directory, because Python places the script's own directory on `sys.path`.

**Open risk flagged, not yet resolvable.** The two servers already connected in
this session — `yale-som-courses` and `outlook-send` — are registered in the
*parent* `AI Foundations/.mcp.json`, and neither is registered at user scope
(`~/.claude.json` has an empty `mcpServers` list). The session's working directory
is `Homework 5`, so the client is evidently resolving a `.mcp.json` above the
working directory. Whether adding a nearer `.mcp.json` causes the client to read
**both** files or only the nearest one cannot be determined without restarting the
session. If only the nearest is read, the two existing servers would stop loading
while this project is open.

Two remedies are available if that happens: merge the two existing entries into
`Homework 5/.mcp.json`, or move the `campus-customs-ops` entry up into the
course-wide file. Neither was applied pre-emptively, since the first duplicates
configuration and the second touches shared coursework config.

**Outcome:** `.mcp.json` created and the server verified working over stdio. The
tools are **not yet callable in this session** — `.mcp.json` is read at session
start, so the session must be restarted and the new server approved before Claude
can call it. No code or database changes.

---

## Session note — Verify whether the MCP server is actually connected

**User prompt:** "Wait. Can you check if the MCP server is actually configured &
connected & you Claude can see all tools?"

**Action taken:** Searched the session's available tools for the new server three
separate ways — by keyword (`campus customs product financial lease`), by name
prefix (`+campus_customs`), and by exact tool name
(`mcp__campus-customs-ops__get_product_info` and the other two). All three
searches returned nothing.

**Finding:**

| Status | Result |
|---|---|
| `.mcp.json` written and valid | yes |
| server runs and serves all three tools | yes — verified over stdio from `/tmp` in Problem 4A |
| connected to this session | **no** |
| Claude can call the tools | **no** |

The servers currently connected — `yale-som-courses` and `outlook-send` — come
from the parent `AI Foundations/.mcp.json` and were loaded when this session
started. `Homework 5/.mcp.json` was written afterwards, and `.mcp.json` is read
only at session start, so the new server was never picked up.

**Correction to the previous turn.** Problem 4A reported the server as registered
and verified, with the restart mentioned as a closing caveat. That understated
it: the restart is the actual remaining blocker for 4A, not a formality. The
server is proven to work; the connection does not exist yet.

**Outcome:** Configuration is correct, the server is proven working in isolation,
but it is **not connected**. The session must be restarted and
`campus-customs-ops` approved. That restart will also answer the open question
from 4A — whether the client reads both `.mcp.json` files or only the nearest
one. If `yale-som-courses` and `outlook-send` disappear after the restart, they
will be merged into `Homework 5/.mcp.json`.

---

## Session note — Attempt to restart; register the server in both config files

**User prompt:** "Restart it for me"

**Action taken — tried to restart, could not:**
- Queried the session's connector status. `campus-customs-ops` was **not listed at
  all**. Connected servers were `yale-som-courses` (3 tools) and `outlook-send`
  (2 tools), both `kind: "project"`, plus two unrelated connectors.
- Searched for a restart capability. None exists:
  `reconnect_session_connector` only re-dials an already-registered connector
  whose status is `failed`, and this server is not registered; `clear_session`
  wipes the transcript without reloading MCP configuration. **Restarting the
  session is the user's action, not something Claude can perform.**

**Key finding from the status output.** The two working servers are reported as
`kind: "project"` and are defined in the **parent** `AI Foundations/.mcp.json`.
The MCP project root for this session is therefore the parent folder, not
`Homework 5` — which means `Homework 5/.mcp.json`, created in Problem 4A, may
never be read at all. The assumption in 4A that project scope meant the homework
folder was wrong.

**Action taken — removed the ambiguity rather than guessing:**
- Backed up the parent config to `.mcp.json.bak-<timestamp>` before editing it.
- Added `campus-customs-ops` to `AI Foundations/.mcp.json` — demonstrably the file
  this session reads. The two existing entries were left untouched.
- Mirrored the **full three-server set** into `Homework 5/.mcp.json`, so the two
  files are now identical.

**Why mirror rather than pick one.** Which file the client resolves after a
restart is still unknown — it may read the nearest, the parent, or both. With
identical definitions in both files, every outcome yields the same three servers:

| If the client reads… | Result |
|---|---|
| the parent only (current behaviour) | all three servers |
| the nearest only (`Homework 5`) | all three servers |
| both, merged | identical definitions, so no conflict |

Had `Homework 5/.mcp.json` been left holding only the new server, a
nearest-wins rule would have silently dropped `yale-som-courses` and
`outlook-send`. Mirroring makes that regression impossible.

**Verification:** launched `campus-customs-ops` over stdio from `/tmp` using the
command, args and env taken from **each** config file in turn. Both returned all
three tools.

**Outcome:** The server is registered in both config files and proven launchable
from each. It remains **not connected** to this session — the user must restart
it, and approve `campus-customs-ops` when prompted. Session context survives the
restart via `AI_prompts.md` and the stored memory notes.

---

## Session note — Save before restart

**User prompt:** "Okay save all these outputs & files, I'll be away to restart"

**Action taken:** Verified every file was already on disk, confirmed database
state, and recorded the MCP registration finding to persistent memory so it
survives the restart.

**Files on disk:**

```
Homework 5/
├── .env.example           CAMPUS_DB_PATH, MODEL_NAME=gpt-6-luna
├── .gitignore
├── .mcp.json              3 servers (mirrors the parent config)
├── AI_prompts.md          this log
├── campus_customs.db      pristine seed
├── data/
│   └── campus_customs_new.db
├── mcp_server/
│   ├── README.md
│   ├── db.py
│   └── server.py
├── output/
│   └── harness.md
└── requirements.txt
```

**Database verified:** seed and working copy both SHA-256 `23686a90…f360a`,
`PRAGMA integrity_check` returns `ok`. Board at clean seed state — tickets
101/102/103 all `open`, `checking` $3,400.00, `payments` empty. No reset needed
before the first full run.

**MCP configs verified:** both `AI Foundations/.mcp.json` and
`Homework 5/.mcp.json` list `yale-som-courses`, `outlook-send` and
`campus-customs-ops`. Backup of the original parent config preserved at
`.mcp.json.bak-20261006-175439`.

**Memory updated:** added a note recording that the session's MCP project root is
the parent folder rather than the homework folder, that both config files are
mirrored to make the resolution order irrelevant, and what to verify after the
restart — `campus-customs-ops` connected with 3 tools, `yale-som-courses` with 3,
`outlook-send` with 2.

**State at pause:** Problems 1A, 1B, 2A, 2B, 3A, 3B and 4A complete. 4A is
functionally finished but **unconfirmed** — the server is registered and proven
launchable, yet has never been connected to a live session. First task on return
is to confirm the connection.

**Still open, non-blocking:** whether to `chmod 444` the seed; whether to move the
seed into `data/`; whether to duplicate pricing into `get_financial_info` so
Accounting is self-sufficient for ticket 103; and whether the mirrored
`Homework 5/.mcp.json` can be pruned once the client's resolution behaviour is
observed.

**Outcome:** Everything saved and verified. Safe to restart.

---

## Session note — MCP connection confirmed after restart

**User prompt:** "Hey I am back. Can you check if the MCP server is actually
configured & connected & you Claude can see all tools?"

**Action taken:** Queried connector status, then called **all three tools live**
rather than relying on the tool listing alone.

**Connector status — all connected:**

| Server | Kind | Status | Tools |
|---|---|---|---|
| `campus-customs-ops` | project | **connected** | **3** |
| `yale-som-courses` | project | connected | 3 |
| `outlook-send` | project | connected | 2 |

The two pre-existing servers survived the change, so mirroring the config into
both files caused no regression — the risk identified before the restart did not
materialise.

**Live tool calls against the working copy:**

| Tool | Call | Result |
|---|---|---|
| `get_product_info` | T101 — `sku=CC-TEE-WHITE, size=S, requested_qty=1` | qty 0 → **shortfall 1**, cannot fulfil; margin 71.4% |
| `get_financial_info` | rule 3 — `vendor_id=1, invoice_status=open` | invoice 501, $840.00, **overdue by 3 days** → Bulldog Print Co **not clear to ship** |
| `get_lease_info` | T102 — `lease_id=1` | Chapel Street shop, Elm City Properties, $2,400.00, due 2026-09-02, **2 days out** |

Every response carried `as_of: 2026-08-31`, confirming business rule 1 holds
through the MCP layer — the tools read `desk.date_today`, not the system clock.
The figures match those derived by hand in Problems 2A and 3A.

**Question left unresolved, deliberately.** Both `.mcp.json` files are identical,
so which one the client actually read cannot be determined from the result. What
matters is that no duplicate registration appeared and nothing was dropped. The
mirrored config is being kept: the redundancy costs nothing and protects against
the resolution rule differing on another machine or in a future session.

**Outcome:** **Problem 4A is now confirmed complete.** The MCP server is
configured, connected, and callable by Claude. No code or database changes; the
board remains at seed state.

---

## Problem 4B — Test each MCP tool individually

**User prompt:** Asked to test the three MCP tools individually — calling the
actual MCP tool, using valid test input based on the Campus Customs database,
and showing the exact input and response in detail with a clear success or
failure verdict. A JSON file `mcp_tool_tests.json` is to follow, holding the test
evidence — tool name, output matching `data/campus_customs_new.db`, and the
result plus proof — but the user asked to defer that and call the tools first.
Instructed not to invent or guess, to ask when unsure, and to report plainly if a
tool does not work.

**Action taken:** Called all three tools live over MCP, then queried the database
directly with `sqlite3` and recomputed every derived field independently, so that
"success" means *the output matched the data*, not merely that the call returned
without error.

**Test inputs chosen** — each drawn from a real ticket rather than invented:

| Tool | Input | Why this input |
|---|---|---|
| `get_product_info` | `sku=CC-HOOD-NAVY, size=M, requested_qty=20` | Ticket 103's exact ask |
| `get_financial_info` | `account=checking, include_invoices=true` | Ticket 102's cash question, and the rule 3 invoice check |
| `get_lease_info` | `lease_id=1` | Ticket 102's lease |

**Results — all three passed.**

*Test 1, `get_product_info`:* returned `Basic Hoodie Big Yale`, unit_cost 22,
list_price 58, size M qty 8 at Aisle A — all matching the `inventory`/`pricing`
join. Derived fields checked by hand: `unit_margin` 36 = 58 − 22;
`margin_pct` 62.1 = (58−22)/58; `shortfall` 12 = 20 − 8;
`can_fulfil_from_stock` false.

*Test 2, `get_financial_info`:* returned `checking` 3400.0 and invoice 501 —
$840.00, due 2026-08-28, status open, vendor Bulldog Print Co, specialty apparel
reprint, lead_days 5 — all matching the `invoices`/`vendors` join. Derived:
`days_until_due` −3, `days_overdue` 3, `open_invoice_total` 840,
`cash_after_open_invoices` 2560 = 3400 − 840. This call is also the business
rule 3 query, and it confirms **Bulldog Print Co is not clear to ship**.

*Test 3, `get_lease_info`:* returned lease 1 — Chapel Street shop, Elm City
Properties, $2,400.00, next due 2026-09-02, notes NULL — all matching `leases`.
Derived: `days_until_due` 2, `is_overdue` false.

**Cross-cutting check:** every response carried `as_of: 2026-08-31`, matching
`desk.date_today`. Business rule 1 therefore holds end to end through the MCP
layer — no tool consulted the system clock.

**Nothing failed**, so there is no malfunction to report.

**Question raised before building `mcp_tool_tests.json`**, because it changes the
file's structure: should the evidence cover only these three positive cases, or
also include **negative tests** — a nonexistent SKU and a nonexistent lease id —
to demonstrate that the tools fail cleanly rather than fabricating data? Negative
cases are stronger evidence but make it four to six cases rather than three.
Awaiting the user's decision rather than assuming.

**Outcome:** All three MCP tools tested live and verified against the database.
No code or database changes; the board remains at seed state.

**Follow-up 1 — build `mcp_tool_tests.json` with screenshot proof.**

*User prompt:* Confirmed having checked "returned" against "database" and found
them matching. Asked to build the JSON file now, attaching three screenshots as
proof, and to include the tool's name, success status (SUCCESS for all three),
and the user's own two prompts in the file.

*Action taken:*
- Copied the three attached screenshots out of the session's temporary image
  directory — which is not durable — into `output/evidence/`, renamed by the tool
  each one shows.
- Wrote `mcp_tool_tests.json` at the project root.

*Design decision — the database values were not transcribed.* The build script
re-opened `data/campus_customs_new.db` read-only and re-ran every verification
query at write time, so each `database` value in the file was read from the
database as the file was written, and every `derivation` was recomputed in code.
The `match` booleans are computed, not asserted. This matters because the user's
instruction was not to invent or guess anything: had any value been typed by
hand, the file would be a claim about the data rather than evidence drawn from it.

*Structure:*

| Key | Contents |
|---|---|
| `environment` | server name, FastMCP, stdio, connection status, tool count, database under test with its SHA-256, and `shop_operating_date` with its source |
| `prompts` | the user's two prompts, verbatim as supplied |
| `method` | how verification was performed |
| `tests` | three entries — tool, tickets served, input used and why, full output, per-field verification, proof, result |
| `summary` | 3 tested, 3 passed, 0 failed, **28 fields verified, 0 mismatches** |

*Proof recorded per test:* the screenshot path **with its SHA-256**, the exact SQL
used for ground truth, and the rows that query returned. The hash means a
screenshot cannot be swapped later without the evidence file disagreeing.

*Verification of the artefact itself:* re-parsed the JSON, confirmed all three
tests report SUCCESS with zero mismatches across 28 fields, and confirmed all
three referenced screenshot files exist at the recorded paths and sizes.

*Note on scope:* the earlier question about adding negative tests was answered
implicitly — the user asked for SUCCESS on all three tools, so the file contains
the three positive cases only. Negative cases remain available if wanted later.

*Outcome:* `mcp_tool_tests.json` (392 lines) and `output/evidence/` created. No
code or database changes; the board remains at seed state.

---

## Problem 5A — Build the PydanticAI agent team (setup and confirmation)

**User prompt:** Restated that the agentic team for Campus Customs is to be built
with PydanticAI, with five agents — Boss, Inventory, Accounting, Facilities,
Customer Service — able to connect, collaborate and delegate to each other. The
user will write the per-agent prompts personally; those go in `backend/prompts/`,
one file per agent. Data types go in `backend/models.py`, and the agent files
under `backend/`. Instructed to use **only `gpt-6-luna`** for every agent on cost
grounds, and to find and use the Portkey API key stored in a `.env` file on the
desktop — using it but **never exposing it, including in chat**. Asked for
confirmation of understanding before the details arrive.

**Action taken — verification before confirming:**
- Located the key at `AI Foundations/.env`. Confirmed `PORTKEY_API_KEY` is present
  and non-empty by reading it programmatically and printing **only its length**.
  The value has not been displayed in chat, written to any file, or recorded in
  this log, and will be loaded at runtime via `python-dotenv`.
- Inspected `Lecture 10/mult_agent_hp/backend/agents/config.py` for the course's
  Portkey wiring convention.
- Installed `pydantic-ai` 2.54.0 and `openai` 3.26.0 into the project venv, which
  previously held only `fastmcp`.

**Key finding — the model pin resolves cleanly.** Lecture 10's `config.py` reads
**`MODEL_NAME`**, which already defaults to `gpt-6-luna`, and does *not* read
`PORTKEY_MODEL`. Since the root `.env` sets `PORTKEY_MODEL=gpt-5.6-luna`, using
`MODEL_NAME` exclusively sidesteps the trap recorded in Prompt 6 entirely, rather
than having to override it. `PORTKEY_MODEL` will never be read by this project.

**Planned layout, pending the user's prompts:**

```
backend/
├── config.py          Portkey wiring, MODEL_NAME pinned to gpt-6-luna, prompt loader
├── models.py          Pydantic data types
├── prompts/           boss.md, inventory.md, accounting.md,
│                      facilities.md, customer_service.md
└── agents/            boss.py, inventory.py, accounting.py,
                       facilities.py, customer_service.py
```

Prompts are kept as separate files loaded at runtime, so an agent's instructions
can be edited without touching Python.

**Three decisions raised, with recommendations, to be proceeded on unless the
user objects:**

1. **Agent file location.** The instruction said "under `backend/`", which is
   ambiguous between flat files and a subpackage. Recommended `backend/agents/`,
   matching Lecture 10 and keeping five agent files from crowding `config.py` and
   `models.py`.
2. **How the mesh is implemented.** Recommended **agent-as-tool** — each agent
   exposed to the others as a callable tool — so delegation is an ordinary tool
   call, every hand-off is a recorded event the dashboard can render, and loops
   are easier to bound. The alternative, a shared message bus, is more flexible
   but much harder to display and to stop looping.
3. **How agents reach the data.** Recommended connecting as an **MCP client**
   rather than importing the tool functions directly, because the assignment
   specifies the MCP server as one of the three pieces, and keeping that boundary
   real means the agents use exactly the tools verified in Problem 4B — avoiding
   a second code path that could drift from the tested one.

**Gap flagged ahead of time:** the three existing tools are read-only and there is
still **no ticket tool**, so the Boss agent has nothing to read the board it is
meant to route from. The agents will be able to reason but not act or see their
work queue. Not a blocker for 5A, since prompts and models come first, but it must
be closed before any full run.

**Outcome:** Understanding confirmed, dependencies installed, key located and
kept confidential, model-pin approach settled. Awaiting the user's per-agent
prompts. No agent files written yet.

**Follow-up 1 — save before stepping away.**

*User prompt:* "Okay I will continue my 5A problem, but I need to be away. Save
all outputs & prompts"

*Action taken:* Verified every file on disk, confirmed database and MCP state,
added the newly installed packages to `requirements.txt`, and recorded the 5A
build plan to persistent memory so the in-progress problem survives a session
break.

*Files on disk:*

```
Homework 5/
├── .env.example  .gitignore  .mcp.json  requirements.txt
├── AI_prompts.md
├── campus_customs.db              pristine seed
├── data/campus_customs_new.db     working copy
├── mcp_server/   README.md, db.py, server.py
├── mcp_tool_tests.json            3 passed, 0 mismatches
└── output/
    ├── harness.md
    └── evidence/                  3 screenshots
```

*Verified:* seed and working copy both SHA-256 `23686a90…f360a`,
`PRAGMA integrity_check` `ok`, board at clean seed state — tickets 101/102/103
`open`, `checking` $3,400.00, `payments` empty. `mcp_tool_tests.json` re-parsed
and still reports 3 passed, 0 mismatches. All three MCP servers registered.

*`requirements.txt` updated* to `fastmcp>=4.0.10`, `pydantic-ai>=2.54.0`,
`python-dotenv>=1.2.4`, so the environment is reproducible rather than depending
on what happens to be installed in the venv.

*Memory updated* with the 5A build plan: the planned `backend/` layout, the
`MODEL_NAME`-not-`PORTKEY_MODEL` approach to the model pin, the key's location
with the instruction never to expose it, the three open decisions, and the
missing-ticket-tool gap.

*State at pause:* Problems 1A, 1B, 2A, 2B, 3A, 3B, 4A and 4B complete.
**5A is in progress** — dependencies installed and the plan settled, but nothing
in `backend/` written, because the user is supplying the five per-agent prompts
themselves.

*Still open, non-blocking:* `chmod 444` on the seed; moving the seed into
`data/`; duplicating pricing into `get_financial_info` for ticket 103; pruning
the mirrored `.mcp.json`; and the three 5A decisions, which will proceed as
recommended unless the user objects.

*Outcome:* Everything saved and verified. No code or database changes.

**Follow-up 2 — the agent team, built.**

*User prompt:* Supplied the full specification: the flow
`user -> Boss -> specialists (using tools) -> Boss (verify) -> user`, the
seven-step specialist loop, the nine-step Boss loop, per-agent responsibilities
and tools for all five agents, and an efficiency constraint — no infinite loops,
a maximum of roughly 3-5 iterations, and honest reporting instead of guessing or
looping when an agent cannot answer.

*Architecture change recorded.* The earliest context said the team had "full
connectivity, and any agent may delegate tasks to any other agent." This prompt
supersedes that: "The specialist agents should not independently decide which
specialist should handle a task, they should focus on their own domain, and let
the Boss do the job." The topology is therefore **hub-and-spoke with the Boss as
sole orchestrator**, not a mesh. Built to the new instruction. The practical
gain is that there is exactly one decision-maker, so two specialists cannot
delegate to each other in a circle - which is also what makes the iteration cap
sufficient to guarantee termination.

*Files written:*

```
backend/
  config.py                     model pin, prompt loader, per-agent tool scoping
  models.py                     10 typed contracts
  prompts/   boss.md inventory.md accounting.md facilities.md customer_service.md
  agents/    boss.py inventory.py accounting.py facilities.py customer_service.py
```

*Design decisions:*

- **Tools are scoped per agent**, not shared. `config.build_toolset()` returns a
  `FilteredToolset` so Inventory sees only `get_product_info`, Facilities only
  `get_lease_info`, Accounting `get_financial_info` **and** `get_product_info` -
  the latter because unit cost and list price live in the `pricing` table, so a
  margin question on a discount is unanswerable without it. An agent cannot stray
  outside its remit by reaching for another's tool.
- **Customer Service has no tools at all.** The tickets table, which holds
  customers and orders, is not exposed by any MCP tool. Rather than hand it
  `get_product_info` and blur the domain boundary with Inventory, the agent works
  from facts the Boss supplies and its prompt tells it to report missing facts
  rather than invent them.
- **Two Boss agents, not one.** `boss_router` decides each round whether to
  delegate and to whom; `boss_finalizer` writes and verifies the answer once.
  Their output types differ (`BossDecision` vs `FinalAnswer`), and the router
  re-runs per round while the finaliser runs once.
- **Specialists in a round run concurrently** via `asyncio.gather`, so one round
  with three delegations costs roughly one round of wall-clock time. The Boss
  prompt pushes it to dispatch everything it needs in a single round.
- **Termination is structural, not hoped for.** `MAX_ITERATIONS=3` (env-tunable
  within the 3-5 range the user asked for) bounds the loop; `hit_iteration_limit`
  is reported in the result so a truncated run is visible rather than silent.
- **A failing specialist cannot take down the run.** `_run_specialist` catches
  exceptions and returns `answered=False` with the reason - the same shape the
  Boss already handles for "I could not find this".
- **Approvals cannot be lost.** After the finaliser runs, every `ApprovalRequest`
  any specialist raised is merged into the final answer if the Boss omitted it.
  Dropping one would silently hide a decision the human has to make.

*Bug found and fixed during live testing.* The first real run failed with a
provider 400:

> `Function tools with reasoning_effort are not supported for gpt-6-luna-global
> in /v1/chat/completions. To use function tools, use /v1/responses or set
> reasoning_effort to 'none'.`

Every agent here uses function tools - for MCP tools and for structured output -
so this broke the very first call. `Lecture 10/mult_agent_hp` had hit the same
wall and solved it; applied the same fix,
`OpenAIChatModelSettings(openai_reasoning_effort="none")`. This is a property of
`gpt-6-luna` on this gateway, not of the code.

*Live end-to-end verification - ticket 102, a real run against the model:*

| | |
|---|---|
| model | `gpt-6-luna` (all six agent instances verified) |
| rounds used | 3 of 3, cap **not** hit - the Boss chose to answer |
| specialists consulted | Facilities, Accounting |
| result | `sufficient=True` |
| database after | unchanged - SHA-256 `23686a90...f360a`, `payments` still empty |

Round 1 dispatched Facilities and Accounting **in parallel**. Facilities returned
lease 1 correctly and raised a `rent_payment` approval. Accounting returned
`answered=False` - honest reporting, exactly as instructed - because it could see
$3,400 cash but not the rent amount. Round 2, the Boss passed the rent figure as
context and Accounting completed the arithmetic: $3,400 - $2,400 = $1,000, and
after reserving the $840 open invoice, $2,560 - $2,400 = $160 remaining. Round 3
the router chose to answer. The final response described the payment as
**awaiting human approval**, never as made.

*Efficiency finding, traceable to a known gap.* The extra round was caused
entirely by `get_financial_info` not reading the `leases` table - the scope gap
recorded in Problem 3B. Accounting could not see rent as a financial obligation,
so the Boss had to spend a round feeding it a figure Facilities already had.
Adding leases to that tool would remove one full round from every rent question.

*Outcome:* The five-agent team is built and verified working end to end on
`gpt-6-luna`. `.env.example` now documents `MAX_ITERATIONS` and `AGENT_RETRIES`.
The API key was loaded from the parent `.env` at runtime and never printed,
written to a file, or recorded here. Database unchanged.

---
## Problem 5B — Extend the system so the agents can work the three tickets

**User prompt:** Asked to extend the multi-agent system across four sub-tasks:
(1) add whatever MCP tools the agents need for the three open tickets, with shop
facts always coming from the MCP server over `data/campus_customs_new.db` and no
invented database; (2) wire the agents to **append** to `output/audit_trail.json`
as they run, recording enough per agent-loop step to audit later, never wiping the
file; (3) extend `output/harness.md` with a safety section plus entries for each
agent and each MCP tool; (4) update `mcp_server/README.md` to match the final tool
list. Sub-tasks 1 and 2 first, 3 and 4 later. Before building, the user asked for
confirmation of which MCP tools already exist, which capabilities are still
missing for the three tickets, and which agent needs each capability.

**Action taken:** Audited the server source rather than answering from memory —
listed the `@mcp.tool` definitions, searched for write statements, and compared
the tables the tools read against the tables that exist.

**Two structural findings:**

- **There is no write capability anywhere in `mcp_server/`.** No `INSERT`,
  `UPDATE` or `DELETE` statements, and `db.py` exposes only `connect_ro`. Every
  write tool is net-new, including the read-write connection helper itself.
- **Two of nine tables are unreachable by any agent**: `tickets` and `payments`.

**Existing tools confirmed:** `get_product_info` (desk, inventory, pricing),
`get_financial_info` (desk, cash_accounts, invoices, vendors), `get_lease_info`
(desk, leases) — all read-only.

**Capability coverage per ticket:** ticket 101 has 1 of 8 needs met, ticket 102
has 2 of 6, ticket 103 has 3 of 9.

**Missing read capabilities, mapped to agents:** read the ticket board (Boss —
the largest gap, since the Boss cannot see the board it routes from; also
Customer Service); vendor lookup with a clear-to-ship flag (Inventory, Accounting
— rule 3 is answerable today only indirectly, and `lead_days` is unreachable);
rent as a financial obligation (Accounting — `get_financial_info` does not read
`leases`, which cost a full round in the 5A live test); payments ledger
(Accounting, Customer Service).

**Missing write capabilities, all approval-gated:** pay an invoice (Accounting —
cash check, insert payment, decrement cash, flip invoice status; unblocks
Bulldog); pay rent (Accounting, with Facilities reporting — plus rolling
`leases.next_due`); raise a purchase order (Inventory with Accounting); update a
ticket (Boss); reset the database (operator, rule 7).

**Four schema holes raised as decisions for the user rather than resolved
unilaterally**, since inventing a store was explicitly ruled out:

1. **No `purchase_orders` table** — a restock PO for ticket 101 or 103 has
   nowhere to live. Options offered: a `payments` row with
   `kind='purchase_order'`, a new table, or ticket notes plus the audit trail.
2. **No place for a price-override decision** — ticket 103's entire outcome has
   nowhere to be recorded.
3. **No place for Customer Service drafts** — tickets 101 and 103 both end in a
   draft.
4. **`payments.paid_at` has no precedent**, the table being empty, so the write
   tool must fix a format. Recommended matching `tickets.created_at` (ISO-8601
   with offset).

Also flagged that `payments.ref_id` is a soft pointer rather than a foreign key,
so the write tool must keep `kind` and `ref_id` consistent — nothing in the
database will catch a mismatch.

**Cost note raised:** every tool added to an agent's toolset is schema sent on
every call that agent makes, so per-agent tool scoping matters more as the list
grows.

**On sub-task 2:** confirmed the audit trail will be append-only and never wiped,
one record per agent-loop step, with writes serialised — specialists within a
round run concurrently, so unserialised appends could interleave and corrupt the
file.

**Outcome:** Gap analysis delivered; no code written, as the user is deciding the
tool list. Database unchanged.

**Follow-up 1 — save before stepping away.**

*User prompt:* "Save everything, I'll be away for a moment"

*Action taken:* Verified every file on disk, confirmed database integrity and
board state, re-checked that the backend still imports cleanly, and recorded the
5B status to persistent memory.

*Verified:*

- Seed and working copy both SHA-256 `23686a90...f360a`, `PRAGMA integrity_check`
  `ok`. Board at clean seed state — tickets 101/102/103 `open`, `checking`
  $3,400.00, `payments` empty.
- `backend` imports cleanly: model `gpt-6-luna`, `MAX_ITERATIONS` 3, all six agent
  instances present (inventory, accounting, facilities, customer_service,
  boss_router, boss_finalizer).
- `mcp_tool_tests.json` re-parsed — still 3 passed, 0 mismatches.

*Memory updated* with the 5B status: the four sub-tasks and their ordering, the
two structural findings (no write layer anywhere; `tickets` and `payments`
unreachable), the missing-capability-to-agent mapping, and the four schema holes
awaiting the user's decision.

*State at pause:* Problems 1A through 5A complete. **5B is in progress** — the gap
analysis is delivered and nothing has been built, because the user is deciding the
tool list. Sub-tasks 1 and 2 are next; 3 and 4 follow.

*Open and awaiting the user:* where a purchase order should live; where a
price-override decision should be recorded; where Customer Service drafts should
persist; and the `payments.paid_at` format. Still open from earlier and
non-blocking: `chmod 444` on the seed, moving the seed into `data/`, pruning the
mirrored `.mcp.json`, and whether to commit a repeatable agent smoke test.

*Outcome:* Everything saved and verified. No code or database changes.

**Follow-up 2 — sub-task 1: seven new MCP tools, no payment capability.**

*User prompt:* Approved adding tools for: read the ticket, suggest apparel vendor,
vendor clear-to-ship, restock PO, close ticket, draft reply, vendor lead time, and
record discount decision. With conditions: a vendor suggestion must come from the
database but **must not be treated as approved**; clear-to-ship must always come
from the business rules/database rather than the agent; a restock PO may be
**drafted but not placed**; a discount may be **analysed and recorded but not
applied**; a ticket may only be closed **after its outcome is actually verified**,
otherwise kept open or pending. And explicitly: **no tools that let agents pay
invoices, pay rent, or place purchase orders.**

*Consequence noted:* banning payment execution removes the need to write to
`payments` at all, which dissolves the open question about the `paid_at` format.

*Blocking gap resolved.* Three of the approved tools record something — a PO draft,
a discount decision, a customer draft — and the schema had nowhere to put any of
them. `payments.approved_by` is the only approval concept in the database and it
requires an *executed* payment, which is now ruled out. Rather than invent a
separate store, one table was added to the **working copy only**:

```
proposals(id, ticket_id, kind, status, summary, details, amount,
          vendor_id, sku, size, qty, created_by, created_on, approved_by)
```

All four recordable things are the same shape — *a recommendation awaiting a
human* — so they share one table, keyed by `kind`. `approved_by` deliberately
mirrors `payments.approved_by`: NULL means unapproved, and **no tool can fill it
in**. Created idempotently at server start, so it survives a reset (which drops it
along with everything else the seed lacks) and comes back empty.

*Seven tools added, for ten in total:*

| Tool | Kind | Guard enforced in code |
|---|---|---|
| `get_ticket_info` | read | Resolves each ticket's linked invoice or lease and attached proposals; truncates `created_at` before date maths |
| `get_vendor_info` | read | `clear_to_ship` computed from open invoices — rule 3, from the database |
| `suggest_vendor_for_sku` | read | Always returns `approved: false`, `requires_human_approval: true`; records nothing |
| `draft_restock_po` | write | `placed: false`; attaches vendor-blocked and cash-short problems rather than refusing |
| `record_discount_decision` | write | `applied: false`; margin maths computed by the tool from `pricing`, not by the agent |
| `draft_customer_message` | write | `sent: false`; there is no send capability anywhere in the server |
| `update_ticket_status` | write | **Refuses to close** a ticket whose outcome is not verifiable |

*The close guard, enforced per ticket type rather than left to the agent:*
`customer_order` needs stock to cover the request **and** no open linked invoice;
`rent_notice` needs a recorded rent payment — which no tool can make, so it stays
open until a human pays; `price_override` needs an approved price-override
proposal. A refused close leaves the ticket untouched and returns the reason.

*Verified live — every new tool called against the real database:*

| Check | Result |
|---|---|
| `get_ticket_info(101)` | resolved invoice 501, overdue 3 days, proposals empty |
| `get_vendor_info("apparel")` | Bulldog **not** clear to ship, blocked by invoice 501, `earliest_delivery` null |
| `suggest_vendor_for_sku(CC-HOOD-NAVY, 12)` | `approved: false`; ranked Bulldog first on specialty but flagged BLOCKED; cost $264.00 |
| `draft_restock_po(12 hoodies)` | `placed: false`, cost $264.00, problem: vendor blocked by invoice 501 |
| `record_discount_decision(20 @ $46)` | `applied: false`, 20.7% off, margin 62.1% -> 52.2%, problem: only 8 in stock |
| `draft_customer_message(101)` | `sent: false`, recipient resolved to Tauhid Zaman from the ticket |
| close 101 | **refused** — stock 0 of 1 needed; invoice 501 still open |
| close 102 | **refused** — no rent payment recorded; requires a human |
| close 103 | **refused** — no approved price-override proposal |
| set 101 pending | accepted |
| invalid status | rejected with the allowed values |
| all 10 tools over live MCP stdio | registered and callable |

*Test rows were cleaned up by exercising the reset path* — seed copied over the
working copy, then `ensure_schema()` — returning the board to three `open`
tickets, $3,400.00, zero payments, zero proposals.

*Agent tool scoping updated:*

| Agent | Tools |
|---|---|
| `boss_router` | `get_ticket_info`, `update_ticket_status` |
| `boss_finalizer` | none — writes the answer, touches no data |
| Inventory | `get_product_info`, `get_vendor_info`, `suggest_vendor_for_sku`, `draft_restock_po` |
| Accounting | `get_financial_info`, `get_product_info`, `get_vendor_info`, `record_discount_decision` |
| Facilities | `get_lease_info` |
| Customer Service | `get_ticket_info`, `draft_customer_message` |

Customer Service is no longer toolless — `tickets` is its own domain. Product and
cash lookups were deliberately withheld so it cannot duplicate Inventory or
Accounting.

*Prompts updated* for Boss, Inventory, Accounting and Customer Service to describe
the new tools and the user's constraints in the agents' own instructions: a
suggested vendor is not a chosen vendor, a drafted PO is not a placed order, a
recorded discount is not an applied discount, a saved draft is not a sent message.
Accounting's prompt now states plainly that it **cannot** pay at all, rather than
that it must seek approval first.

*Important consequence recorded:* the working copy's SHA-256 no longer matches the
seed, because it now carries the `proposals` table — seed `23686a90...f360a`,
working copy `df422a5d...1a744e8`. The seed itself is unchanged and still hashes
to `23686a90...f360a`. Earlier "both hashes match" checks are therefore no longer
the right test of an untouched board; row counts are.

*Outcome:* Sub-task 1 complete — 10 MCP tools, no payment capability anywhere,
every approval gate enforced in tool code rather than in prompts. Sub-task 2
(append-only audit trail) is next. Board at seed state.

**Follow-up 3 — sub-task 2: append-only audit trail.**

*User prompt:* Wire the agents to append to `output/audit_trail.json` as they run,
recording enough per agent-loop step to audit later, and **never wiping the file**.

*Files:* `backend/audit.py` (new), `backend/agents/boss.py` (wired).

*Design decisions:*

- **Tool calls are read from the model's message history, not from the agent's
  self-report.** `extract_tool_calls()` walks `result.all_messages()` for
  `ToolCallPart` / `ToolReturnPart` / `RetryPromptPart`, so a recorded tool call
  is *evidence* rather than testimony. The agent's own claimed `tool_calls` is
  still stored alongside, as `self_reported_tool_calls`, so the two can be
  compared — a divergence between them is itself an audit finding. Structured
  output also travels as a tool call in PydanticAI, so calls are tagged `mcp` or
  `output` to keep real tool use distinguishable.
- **Two clocks per record.** `shop_date` is `desk.date_today` (business rule 1,
  authoritative for anything due or overdue); `recorded_at` is the real wall
  clock, because an audit trail that cannot say *when* it was written is not
  auditable. Reading `desk.date_today` is the one direct database read outside
  the MCP server — it is log metadata and never reaches an agent, and this is
  documented in the module.
- **Appends are serialised and atomic.** Specialists in a round run concurrently,
  so an `asyncio.Lock` guards a read-modify-write that lands via a temp file and
  `os.replace`. Verified with 20 concurrent appends: no records lost, ids
  contiguous.
- **A corrupt or non-array file is never overwritten** — the module raises and
  tells the operator to move it aside, rather than silently destroying history.
- `record_id` is monotonic **across runs**, not per run, so records have a stable
  global order.

*Seven record types:* `run_started`, `boss_decision`, `delegation`,
`agent_response`, `agent_failed`, `invalid_delegation`, `final_answer`,
`run_finished`.

*Bug found by the audit trail itself.* The first live run's trail showed records 9
and 10: `boss_decision -> ['boss']` followed by a `delegation` to `boss` with no
response. **The Boss had delegated to itself**, burning a whole round — a router
call plus a dead dispatch — and polluting `agents_consulted` with `boss`. Fixed in
two places: the router contract now names the four valid targets and states that
delegating to itself does nothing but burn a round; and `run_boss` filters
non-specialist targets **before** dispatch, logging an `invalid_delegation` record
and breaking early if nothing dispatchable remains. Re-ran: `consulted` came back
`['accounting', 'inventory']` with no `boss`.

*A second slip worth recording:* one patch anchor did not match the file (the
comment read "in one round", not "in a round") and `str.replace` failed silently,
producing a `NameError` on the next run. The remaining patches in that script had
assertions; that one did not. Subsequent patches assert their anchors.

*Verified across two live runs plus one crashed run:*

| Check | Result |
|---|---|
| total records | **29**, ids contiguous 1-29 |
| distinct runs in one file | **3** — the file accumulated rather than being wiped |
| crashed run visible | yes — `run_started` 3 vs `run_finished` 2, so an unfinished run is evident |
| real tool calls captured | yes, with arguments and `ok` status |
| ticket 101 run | Inventory, Accounting and Customer Service dispatched **in parallel** in round 1 |
| ticket 103 run | round 1 margin and stock, round 2 vendor suggestion and PO draft |

*Database after both runs — every guard held:*

| | |
|---|---|
| `payments` | **0** — no agent can pay, and none did |
| `cash_accounts` | **$3,400.00**, unchanged |
| tickets | all three still `open` — nothing was closed |
| `proposals` | 3 rows, **every one `approved_by` NULL** |

The three proposals: a customer draft to Tauhid Zaman (ticket 101), a price
override on ticket 103, and a $264.00 restock PO for 12 hoodies from a vendor the
tool itself flagged as blocked. All `awaiting_approval`, none executed.

*Observation for the user, not corrected unilaterally:* on ticket 103 Accounting
recorded a price override at **$58.00 — list price, 0% off** — because the user's
request named no target price. The tool recorded faithfully what it was asked to
record, and the final answer said plainly that no discount amount was provided. It
is arguably a wasted proposal row, and whether the agent should instead have
reported the missing input and recorded nothing is a prompt question for the user.

*Outcome:* Sub-task 2 complete. Sub-tasks 3 and 4 remain.

**Follow-up 4 — sub-task 3: safety, agents and all ten tools in `harness.md`.**

*User prompt:* Supplied five safety rules, the five agents' responsibilities, and a
list of the MCP tools, to be recorded in `output/harness.md`.

*Cross-check performed before recording.* The supplied tool list had **13 entries
but 10 unique names** — `get_product_info`, `get_vendor_info` and `get_ticket_info`
each appeared twice, because the list was written per-agent and those tools are
shared. Compared the unique set against the `@mcp.tool` definitions in
`server.py`: **exact match, nothing missing, nothing listed that does not exist.**

*Written to `output/harness.md`:*

- **Safety rules** section, placed near the top. Each rule is recorded in the
  operator's words, followed by **how it is actually enforced** — because a rule
  that only lives in a prompt is a request, not a guarantee:
  - *No payments* — there is no payment tool at all; the write tools return
    `placed: false` / `applied: false` and write `approved_by` NULL, which no tool
    can set.
  - *Database is the only truth* — `answered`/`missing` on every response, and the
    audit trail records real tool calls from message history, so an unbacked claim
    is visible after the fact.
  - *No private or external sources* — no agent has web, file or network access;
    the only toolset is a local stdio MCP server over one SQLite file, with no
    send capability.
  - *Work efficiently* — `MAX_ITERATIONS = 3`, within the 2-3 the user asked for
    and tunable to 2. Recorded that **specialist-to-specialist traffic is
    structurally impossible** under hub-and-spoke, so that half of the rule needs
    no enforcement, and that Boss self-delegation is dropped before dispatch.
  - *Always gpt-6-luna* — one constant read from `MODEL_NAME`, never
    `PORTKEY_MODEL`, with the `openai_reasoning_effort="none"` requirement noted so
    nobody removes it.
- **The agent team** section — each agent's responsibilities in the operator's own
  words, followed by its tools and implementation notes: why Accounting holds
  `get_product_info`, why Customer Service was denied product and cash lookups,
  why Facilities can only see leases, and why the Boss is two agent instances.
- **MCP Tools** section rewritten from three tools to **ten**, with a summary table
  marking read versus write, tickets served and owning agent, then one section per
  tool. The operator's original reasoning paragraphs for the three earlier tools
  were carried over verbatim.
- **The `proposals` table** documented — why it exists, that `approved_by` mirrors
  `payments.approved_by`, and that it is recreated empty after a reset.
- **Still not built** — no payments-ledger read, no `reset_database` tool, and
  `get_financial_info` still does not read `leases`.

*Stale content replaced.* The old "Scope vs. implementation — the gap" section
listed `tickets` as unreachable and the write tools as missing. Those gaps are now
closed, so leaving it would have actively misled a reader.

*Reset-check correction recorded prominently.* Verifying a reset by comparing the
working copy's hash to the seed **no longer works**, because the working copy
carries the `proposals` table. The harness now says to verify by row counts — 3
open tickets, $3,400.00, `payments` empty, `proposals` empty.

*Consistency verified against the code,* rather than asserted: the documented
tool-to-agent mapping was compared programmatically against the `TOOLS` tuples in
all five agent modules. All five match, and no tool is documented without an owning
agent.

*Outcome:* `output/harness.md` is now 642 lines covering safety, the data schema,
the agent team and all ten tools. Sub-task 4 — updating `mcp_server/README.md` —
remains. No code or database changes.

**Follow-up 5 — sub-task 4: `mcp_server/README.md` brought up to date.**

*User prompt:* "Update mcp_server/README.md so the tool list matches what we have
now."

*Six things in the file were wrong, not just the tool list:*

1. **"Three tools it has"** — now ten.
2. **The tool table** listed three.
3. **"Two guarantees — it cannot write."** No longer true: the server has a narrow
   write surface. Leaving this would have been the most misleading line in the
   file, since a reader would assume writes were impossible.
4. **"Not yet wired to the agent team"** — it is wired and registered.
5. **The reset check** told the reader to verify by SHA-256 against the seed, which
   now always fails because the working copy carries the `proposals` table.
6. **"Still to add"** proposed `pay_invoice`, `pay_rent` and a purchase-order tool
   — all of which the user has since explicitly forbidden. This was the worst of
   the six: a stale to-do list that reads as a plan to build the exact capability
   the safety rules prohibit.

*Rewritten:*

- Opening blurb keeps the operator's wording about the database file, with the
  count corrected and a read/write table of all ten tools.
- Full tool table — reads/writes, tickets served, and what each answers, with the
  three "does not" guarantees stated inline: does not place, does not apply, never
  sends.
- **"Two guarantees" became three**, led by the one that matters most: *no agent
  can spend money*. Then reads-cannot-write (`mode=ro` versus the separate
  `connect_rw`), then never-reads-the-system-clock.
- New sections for **the close guard** (with the per-ticket-type table, and the
  note that ticket 102 cannot be closed by any agent) and **the `proposals`
  table**.
- Reset section now says **verify by row counts, not by hash**, with an expected-state
  table, and explains that the hash mismatch is expected rather than corruption.
- "Still to add" replaced by **"Not provided, deliberately"** — no payment tools,
  no send capability, no reset tool — so the absences read as decisions rather than
  as unfinished work.
- **Known gap** retained: `get_financial_info` still does not read `leases`.

*Verified against the code rather than asserted:*

| Check | Result |
|---|---|
| tools in `server.py` | 10 |
| all ten documented in the README | yes, none undocumented |
| no `pay_*` tool exists | confirmed |
| `connect_rw` exists, `connect_ro` uses `mode=ro` | confirmed |
| `proposals` DDL present | confirmed |
| **no tool writes `approved_by`** | confirmed — it appears only in a read, a read-check and a comment |
| HTTP port 8003 | confirmed |
| board matches the documented reset state | tickets 101/102/103 `open`, $3,400.00, `payments` empty, `desk.date_today` 2026-08-31 |

*Outcome:* **Problem 5B is complete** — all four sub-tasks done. The working copy
currently holds 3 unapproved proposals from the live test runs; a reset before the
full run will clear them, per business rule 7. No code or database changes in this
sub-task.

**Follow-up 6 — clarify business rule 7, and reset the working copy.**

*User prompt:* Confirmed the tool-list typo — there are indeed 10 tools, 3 added
at the start and 7 during the build. Asked what "business rule 7 wants a reset
first" meant, and authorised the reset, with the instruction to make sure it is
performed on the **correct** database: the working copy is reset, the original is
kept.

*Clarification given:* rule 7 is the user's own, from the eight supplied earlier —
"Before a full run to resolve the tickets, make sure to reset the database to the
original values." It applied because the live test runs in sub-tasks 1 and 2 left
state behind, so a full run starting from there would not be a clean run.

*State before the reset:* three tickets `open`, cash $3,400.00, `payments` empty —
but **3 proposals** written by the agents during live runs (a customer draft from
Customer Service, a price override from Accounting, a restock PO from Inventory).
The seed was confirmed untouched first: hash `23686a90...f360a`, and no
`proposals` table.

*Reset performed in the correct direction:* `campus_customs.db` (seed) copied
**onto** `data/campus_customs_new.db` (working copy). The seed was read, never
written. A disposable snapshot of the pre-reset working copy was taken to the
session scratchpad first, outside the project. `ensure_schema()` then recreated
the `proposals` table empty, since copying the seed drops it.

*Verified by row counts, not by hash* — the method the harness and README now
specify, because the working copy carries the `proposals` table the seed lacks:

| Check | Result | Expected |
|---|---|---|
| tickets open / total | 3 / 3 | 3 / 3 |
| `checking` balance | $3,400.00 | $3,400.00 |
| `payments` | 0 | 0 |
| `proposals` | 0 | 0 |
| invoices open | 1 | 1 |
| inventory rows | 10 | 10 |
| vendors | 3 | 3 |
| `desk.date_today` | 2026-08-31 | 2026-08-31 |

All nine checks passed. Ticket notes were restored to their seeded text, with no
annotations left from the close-guard tests. The seed still hashes to
`23686a90...f360a`.

*The audit trail was deliberately NOT reset.* All 29 records across 3 runs are
intact. Rule 7 concerns the database; the audit trail is append-only by
instruction and wiping it would destroy the evidence of how the system was
tested — including the Boss self-delegation bug it caught.

*Outcome:* Working copy reset and verified clean; seed untouched; audit trail
preserved. The board is ready for a full run.

**Follow-up 7 — fix: `get_financial_info` now reads `leases`.**

*User prompt:* Asked what the second open item meant, and said it should be fixed.

*What the problem was.* `get_financial_info` returned only `as_of`, `accounts`,
`total_cash`, `invoices`, `open_invoice_total` and `cash_after_open_invoices` —
nothing about rent. Rent is money that must leave the account, so Accounting, the
agent that owns affordability, could not see one of the two obligations it was
being asked about. In the Problem 5A live run this produced:

> Accounting: *"I found checking cash of $3,400.00, but the returned financial
> information does not include the amount due on lease 1, so I cannot determine
> whether funds cover that rent."* — `answered=false`

The Boss then had to spend an entire round passing Accounting a figure Facilities
had already retrieved. The agent behaved correctly — it reported the gap honestly
rather than guessing — but the round was pure waste, which matters directly
against the user's cost constraint.

*The fix.* Added an `include_leases` argument (default `True`) and a
`_lease_obligations()` helper. The tool now returns `leases` — each with
`monthly_rent`, `next_due`, `days_until_due` and `is_overdue` — plus
`rent_due_total`, `total_obligations` (open invoices **plus** rent due),
`cash_after_obligations`, and `can_meet_all_obligations`.

**Backwards compatible:** every pre-existing key is unchanged, so the additions
cannot break an existing caller. `include_leases=False` restores the old shape,
verified.

*The whole cash squeeze now comes from a single call:*

```
total_cash 3400.00 - open_invoice_total 840.00 - rent_due_total 2400.00
  = cash_after_obligations 160.00   (can_meet_all_obligations: true)
```

That $160 is the same figure derived by hand in Problem 2A; it previously took two
agents and two rounds to assemble.

*Verified by re-running the same rent question live:*

| | Before | After |
|---|---|---|
| rounds | **3** | **2** |
| Accounting, round 1 | `answered=false` | `answered=true` |
| delegations | 3 | 2 |

Both specialists answered on the first round. One third of the rounds removed from
every rent question, and the final answer was still correct and still described the
payment as awaiting human approval.

*Board unaffected:* the run wrote nothing — 3 tickets `open`, $3,400.00, `payments`
0, `proposals` 0. The reset performed earlier still holds, so a full run can begin
from clean state.

*Documentation updated so nothing still describes this as a gap:*

- `output/harness.md` — tool 7's "Known limitation" replaced with the new
  behaviour and a note on why it was added; `leases` added to the reads column in
  both the summary table and the tool section; the stale entry removed from "Still
  not built".
- `mcp_server/README.md` — "Known gap" replaced with "Obligations in one call";
  reads column updated.
- `backend/prompts/accounting.md` — documents `include_leases` and the new summary
  fields, and tells Accounting plainly that it no longer needs another agent to
  tell it what rent costs.

*Test evidence annotated rather than regenerated.* `mcp_tool_tests.json` records a
`get_financial_info` call from 2026-10-06, whose captured output predates this
change. Regenerating it would invalidate the screenshot taken at the time, so a
`superseded_note` was added to that one test record explaining that the tool was
later extended, that every field verified in the test is unchanged, and that the
additions are purely additive. The run remains an accurate record of what happened
that day.

*Outcome:* Fixed, verified live, and documented. One of the three open items from
the previous status check is closed.

---
## Problem 6A — `output/desk_tickets.html`

**User prompt:** Create `output/desk_tickets.html` as a standalone page openable by
double-clicking, with a tab per ticket (101, 102, 103) plus **Cash** and
**Reflections** tabs marked "coming later". Each ticket tab needs an **Expected**
section describing what the multi-agent team should do given the ticket details and
system rules, and an **Actual** section left blank. The user supplied the expected
flow for each ticket and asked that it refer to the tools, agent job descriptions
and safety rules recorded earlier.

**Action taken:**
- Pulled live ticket and vendor data from the MCP server rather than writing the
  figures from memory, so every number on the page traces to
  `data/campus_customs_new.db`.
- Wrote `output/desk_tickets.html` — 5 tabs, 3 Expected sections, 3 Actual
  placeholders, 2 "coming later" panels.

**Standalone, as required:** everything inline — no stylesheet, no script file, no
font or CDN reference. Verified: zero external `src`/`href` references. It opens
from the filesystem with no server and no network.

**Design:** minimal and professional per the project defaults — restrained neutral
palette with one accent, generous whitespace, a numbered timeline for each step,
and coloured callouts only where a rule bites. Tabs are keyboard-navigable with
arrow keys and carry proper `role="tab"`/`aria-selected` semantics.

**Each Expected step records who acts and with which tool**, so the page is
checkable against the system rather than being a narrative: Boss ·
`get_ticket_info`, Inventory · `get_product_info`, and so on.

**Three places where the user's expectation and the implemented rules diverge were
flagged on the page rather than quietly smoothed over:**

1. **Ticket 102 — "close ticket" cannot happen.** The user expected the ticket to
   close. Closing a `rent_notice` requires a rent payment recorded in `payments`,
   and no tool can create one, so only a human can close it. Noted on the page,
   with the observation that allowing a close once the *recommendation* is on the
   board would be a rule change and is the user's call.
2. **Ticket 103 — "work with vendor on the communication" is not possible.** There
   is no email or messaging tool anywhere in the system. What the team can do is
   read `lead_days` and blocked status from the database; any message to a vendor
   would be a draft a human sends.
3. **Ticket 103 — no target price was given.** The ticket asks for "a bulk
   discount" without naming a figure, which is what produced the 0%-off proposal
   row in the earlier live run. The page states the expectation that Accounting
   reports the missing figure rather than inventing one.

**The ticket 103 cash arithmetic was made explicit** because it is the sharpest
constraint on the board: the 12-unit restock costs $264.00, while only $160.00
remains after rent and invoice 501 — so the PO draft should come back flagged on
*both* counts, vendor blocked and cash short.

**Outcome:** `output/desk_tickets.html` created and delivered. Actual sections
left blank for the user. No code or database changes; board still at seed state.

---
**Follow-up 1 — 6A correction: empty the Expected sections.**

*User prompt:* Realised after reading the 6B instructions that the Expected
sections were not supposed to be filled in during 6A. Asked to remove the ticket
details typed in the previous prompt while keeping the tabs and three sections —
and to prove the ticket details were still remembered.

*Action taken:* Snapshotted the filled version to the session scratchpad first, so
the drafted content was not lost, then replaced all three Expected cards with
placeholders reading "To be completed in 6B." Page dropped from 21 KB to 11 KB.
Structure untouched: 5 tabs, 3 sections per ticket, still zero external references.

*Judgement call stated, not assumed:* the per-ticket **facts card** was kept, since
those are database facts rather than the expectations the user typed, and they are
what makes a tab identifiable. Offered to remove them too.

*Recall given* for all three tickets from memory — ids, types, requesters, SKUs,
sizes, quantities, stock levels, the invoice 501 gate with its overdue standing and
5-day lead, the lease with its due date, margins, and the
$3,400 / $3,240 / $160 / $264 arithmetic.

---

## Problem 6B — Fill the Expected sections

**User prompt:** For each ticket's Expected section, supplied: who the Boss should
call first and why, all the agent delegations expected, and which MCP tools are
expected to run. Full details given for all three tickets.

**Action taken:** Added two small styles (sub-headings, tool chips) and wrote all
three Expected sections, recording the user's expectations as given — the first
call with its reasoning, the delegation sequence as a numbered flow including the
conditional branches, and the expected tool list as chips.

**The conditional structure was preserved rather than flattened.** Tickets 101 and
103 both branch on what Inventory finds — "if stock exists … however, if stock is
0/not enough …" — and that branch is the substance of the expectation, so it is
written as explicit steps rather than collapsed into the path we already know will
be taken.

**Divergences from the implemented system flagged on the page**, as notes beneath
each expectation rather than by silently rewriting what the user wrote:

*Ticket 101*
- **Closing is the Boss's tool, not Customer Service's.** `update_ticket_status`
  is scoped to the Boss; Customer Service holds `get_ticket_info` and
  `draft_customer_message` only.
- **The PO is Inventory's to draft**, not Customer Service's — so "confirm the
  order and prepare the PO" is two agents.
- **Cannot be closed on this run**: stock 0 against 1 needed, and invoice 501
  open. Expect refusal and `pending`.
- **Bulldog cannot ship** while invoice 501 is open; the 5-day lead starts only
  after a human pays.

*Ticket 102*
- **The landlord is not a vendor.** Elm City Properties lives in `leases`, not
  `vendors` — which holds Bulldog Print Co, Elm City Gifts and QuickShip CT.
  `get_vendor_info` will return nothing useful here, and **Elm City Gifts is a
  different company** despite the similar name. This was the most substantive
  catch in the prompt: the expected tool list includes a tool that cannot serve
  this ticket.
- **Drafting is Customer Service's tool**, not Facilities'.
- **Nothing is ever sent** — "draft an email to the vendor" produces a board draft.
- **Cannot be closed**: closing a `rent_notice` needs a recorded rent payment, and
  no tool can create one. Noted that the user's own "only after resolution is
  confirmed" is exactly the rule the tool already enforces.

*Ticket 103*
- **The restock cannot be funded**: $264.00 needed against $160.00 remaining.
  Expect the PO draft flagged on both counts — vendor blocked *and* cash short —
  and still recorded, because a human needs to see the blocked option.
- **No target price was given**, so `record_discount_decision` has no figure to
  evaluate; noted that an earlier trial run recorded a 0%-off proposal, which is a
  wasted row.
- Same closing-tool and cannot-close notes as 101.

**Verified:** 5 tabs, 3 Expected sections filled, 3 Actual sections still blank, 2
"coming later" panels, zero external references, balanced markup.

**Outcome:** `output/desk_tickets.html` now carries the full Expected
specification. Actual sections remain for later. No code or database changes.

---
**Follow-up 1 — corrections accepted; ticket 102 switched to lease language.**

*User prompt:* Responded to all three flags — asked for the vendor/lease confusion
to be corrected ("change 'vendor' to 'lease' if it is not a vendor case"), and
acknowledged the two other flags (closing is the Boss's tool; none of the three
tickets can close as things stand).

*Action taken on ticket 102:*

- **`get_vendor_info` removed from the expected tool list.** It cannot serve a
  lease ticket — the landlord is not in `vendors`. The expected tools are now
  `get_ticket_info`, `get_lease_info`, `get_financial_info`,
  `draft_customer_message`, `update_ticket_status`.
- The opening line now reads "validate the rent details **from the lease** — the
  landlord, the amount, and when payment is due", rather than framing it as vendor
  details.
- "Draft an email to the vendor" became "a message to the landlord".
- The red warning became a **green resolved note**, kept rather than deleted so
  the reasoning survives: Elm City Properties is a landlord in `leases`, the
  `vendors` table holds suppliers, *Elm City Gifts is a different company* despite
  the similar name, and `get_lease_info` is the lease equivalent that was already
  present. A new `.note-ok` style was added for resolved notes.

*Deliberately left alone:* "vendor" in tickets 101 and 103 is **correct** — Bulldog
Print Co genuinely is a vendor in the `vendors` table, with an open invoice and a
5-day lead time. The correction was scoped to the lease case only, as the user's
instruction specified.

*Verified:* `get_vendor_info` now appears exactly once in the 102 panel — inside
the explanatory note saying why it was removed — and not in the tool chips. Page
still has 5 tabs, 3 Expected sections filled, 3 Actual sections blank, zero
external references, balanced markup.

*Outcome:* Corrections applied. No code or database changes; board still at seed
state.

---
## Problem 7A — FastAPI backend

**User prompt:** Build `backend/main.py` with FastAPI, with routes to: display all
three tickets with open/resolved status; accept a ticket ID and run the agent team
on it; show recent agent activity including each agent's messages and the tools
they used, so the dashboard can refresh; approve a payment or purchase only after a
human clicks the approval button — this action being what actually updates the cash
balance; display the current checking balance; and restore the database to its
original state for a fresh run.

**The central design decision.** The user's fourth route introduces a capability
the system has deliberately never had: something that actually spends money. It was
placed in `backend/approvals.py` — a **plain Python module, not an MCP tool**.
Agents reach the shop only through the MCP server, have no HTTP client, and have no
import path to that module, so no agent can reach spending by any route. The
separation is structural rather than a matter of instructions, which is what makes
"agents prepare, humans execute" a guarantee instead of a policy.

**Files written:** `backend/approvals.py` (execution layer), `backend/main.py`
(API). FastAPI 0.143.0 installed; `requirements.txt` updated.

**Routes:**

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/tickets` | All tickets with `resolved`, linked invoice/lease, proposals |
| GET | `/api/cash` | Checking balance, obligations, payment history |
| POST | `/api/tickets/{id}/run` | Start an agent run (background) |
| GET | `/api/runs`, `/api/runs/{id}` | Run status and outcome |
| GET | `/api/activity` | Audit feed — agent messages and tools actually used |
| GET | `/api/approvals` | Everything awaiting a human |
| POST | `/api/approve/invoice/{id}` | **Spends money** — settles an invoice |
| POST | `/api/approve/rent/{lease_id}` | **Spends money** — pays rent |
| POST | `/api/approve/proposal/{id}` | Approves a PO (spends), discount or draft (do not) |
| POST | `/api/reset` | Restores from seed |
| GET | `/api/health` | Config check |

**Design decisions:**

- **Runs are backgrounded.** A run takes minutes and many model calls, so
  `POST /tickets/{id}/run` returns a `run_id` immediately and the dashboard polls.
  The user's activity requirement implies watching work in progress, which a
  blocking call cannot support.
- **`/api/activity` supports `since_id`**, so the dashboard fetches only new
  records rather than re-reading the whole trail on every poll.
- **`resolved` is true only for `closed`.** Pending and blocked tickets are still
  outstanding work, so they report unresolved.
- **Not every approval spends.** A restock PO moves cash; a price override
  authorises a price; a customer draft is released for a human to send. Each
  returns an `effect` line saying what actually happened.
- **`payments.paid_at` holds the shop's operating date**, consistent with every
  other business date under rule 1. The real wall-clock moment is in the audit
  trail's `recorded_at`, so business dates stay authoritative and real time stays
  auditable.
- **Approving a PO does not increment inventory.** Stock arrives after the vendor's
  lead time, which the schema cannot express, so claiming delivery would be false.
- **Reset does not clear the audit trail**, which is append-only by instruction.

**Guards verified live against a running server:**

| Check | Result |
|---|---|
| empty `approved_by` | **HTTP 422** — refused before touching the database |
| pay invoice 501 | cash **$3,400 → $2,560**, payment row with approver, invoice `paid` |
| pay it twice | **HTTP 409** "already paid. Nothing was changed." |
| pay rent | cash **$2,560 → $160**, `next_due` rolled 2026-09-02 → 2026-10-02 |
| approve $264 PO on $160 | **HTTP 409** insufficient cash — *"leaving $-104.00. Refused"* |
| cash after refusal | **unchanged at $160** — nothing partially applied |
| reset | restored to 3 open tickets, $3,400, 0 payments, 0 proposals, invoice 501 back to `open`, lease back to 2026-09-02 |
| seed after all of it | still `23686a90...f360a` |
| audit trail after reset | **48 records across 5 runs, preserved** |

**The rule 3 chain verified end to end.** Before paying invoice 501, Bulldog Print
Co reported `clear_to_ship: false` and `earliest_delivery: null`. After a human
paid it through the API, the same tool reported `clear_to_ship: true` and
`earliest_delivery: 2026-09-05` — the 5-day lead running from the shop's date. The
human unblocking a vendor propagates correctly into what the agents can see.

**Live agent run through the API:** ticket 102 dispatched in the background,
finished in roughly 40 seconds, 3 rounds, 2 delegations, Facilities and Accounting
consulted, 48 audit records accumulated and served through `/api/activity` with
tool names and arguments attached.

**Bug found during that run, and fixed.** The audit feed showed Accounting
reporting it could not see rent. Inspecting the recorded tool call showed it had
called `get_financial_info(include_invoices=False, include_leases=True)` and
received no leases: `include_invoices=False` returned early, **before** the lease
block, so one flag silently suppressed the other. Restructured so the two flags are
independent section selectors, and so `open_invoice_total` is always computed —
`total_obligations` must stay truthful regardless of which sections the caller asked
to see. All four flag combinations verified.

This was caught only because the agent reported its gap honestly and the audit
trail recorded the *actual* arguments rather than the agent's description of them.

**Outcome:** Backend complete and verified. Database reset to seed; server stopped
cleanly. The React dashboard remains.

---
## Problem 7B — Run the backend, and document its routes

**User prompt:** Start the server with `uvicorn main:app --reload --port 8000` from
the `backend/` folder, so the frontend dashboard can call the routes at
`https://localhost:8000`, reporting back if it does not work. A later prompt would
supply the route list for `output/harness.md`.

**Correction reported immediately:** the address is **`http://localhost:8000`, not
`https`**. Uvicorn serves no TLS listener, so `https://localhost:8000` fails with a
connection error that reads as "the backend is down" rather than as a protocol
mismatch — a frontend pointed at it would be debugged in the wrong place. Verified
both: HTTP returned 200, HTTPS returned nothing.

**Server started and verified:** all six read routes returned 200, and a CORS
preflight from `http://localhost:5173` returned 200, so the Vite dev origin can
call it directly.

**Background time limits hit twice, and reported both times.** The first instance
was stopped at the 30-minute default; it was restarted with the 2-hour maximum and
stopped again at that limit. Rather than restart it a third time into the same
cycle, the server was moved into the **user's Terminal panel** (tab `backend
:8000`), where it runs in their own shell, outside the harness's timer, visible and
stoppable by them. Verified again there: all routes 200, CORS 200, board reading 3
open tickets.

**Logged for the user's workflow:** a dev server that must stay up while the
frontend is built does not belong on a harness background timer. Long-running
processes go in the terminal from here on.

---

**Follow-up 1 — document the routes in `harness.md`.**

*User prompt:* Supplied the list of 12 routes with one-line purposes, referencing
`backend/main.py`, to be recorded in `output/harness.md`.

*Cross-checked before recording:* compared the supplied list against the routes
actually registered on the FastAPI app. **Exact match — 12 in code, 12 listed,
nothing in the code that was unlisted and nothing listed that does not exist.**

*Written to `output/harness.md`* as a **Backend API** section:

- **Base URL stated as plain HTTP**, with the HTTPS failure mode called out, since
  that is the error most likely to cost time when the dashboard is wired up.
- Run and stop commands, with the note that `--reload` runs a supervisor **and** a
  worker so the whole group must be killed.
- **"Where spending lives"** placed before the route table, because it matters more
  than any individual route: the agents' toolset is the MCP server, which has no
  payment tool; money moves only in `backend/approvals.py`, reachable only through
  the three `/api/approve/*` routes a human invokes. An agent has no HTTP client
  and no import path there, so the separation is structural.
- A route table carrying the user's purposes plus a **"Spends?"** column — the
  three routes that move money are marked, and `approve/proposal` is marked "only a
  restock PO", since a price override and a customer draft do not.
- A detail section per route: parameters, what comes back, and which refusals apply.
  Eleven sections for twelve routes, as `/api/runs` and `/api/runs/{run_id}` share
  one.
- **"Three guards every spending route enforces"** — an approver is required (422),
  the balance may never go negative (409 with the arithmetic shown), and nothing is
  applied partially — each with the live verification result from Problem 7A.

*Two stale passages fixed while there:*

- The contents pointer did not mention the new section.
- **"Still not built" claimed there was no reset**, which `POST /api/reset` now
  provides. Rewritten as "Still not built — on the MCP side", recording that the
  absence of a reset *tool* is deliberate (it is an operator action, kept off the
  agents' toolset) and that the payments-ledger gap is now real rather than
  theoretical, since payments can exist once a human approves one.

*Consistency verified programmatically:* every route registered on the app appears
in the harness table — 12 of 12, none missing.

*Outcome:* `output/harness.md` is now 826 lines covering safety, schema, agents,
MCP tools and the backend API. Server running in the user's terminal. No code or
database changes.

---
## Problem 8A — React + Vite + TypeScript dashboard

**User prompt:** Build the frontend dashboard in `frontend/` with React + Vite +
TypeScript against the existing routes, doing six things: list the tickets; let a
user pick one and have the agents work it; show each agent and what it did with a
short summary; mark a ticket resolved once finished; let a human approve a
payment or purchase after the agents finish preparing; and show the checking
balance, reflecting payments. Design: minimalist, white dominant (~80%) with blue
as an accent only, navy `#000080` for the title, Arial-light typography, black on
white and white on navy for legibility, and clear resolution marks — green
resolved, red not, yellow in progress.

**Files written:**

```
frontend/
  vite.config.ts            dev proxy /api -> http://localhost:8000
  src/types.ts              typed API shapes
  src/api.ts                fetch client; surfaces backend refusal text
  src/index.css             190 lines; white/navy, Arial 300, status colours
  src/App.tsx               layout, polling, run lifecycle
  src/components/  StatusBadge · TicketList · AgentActivity · Approvals
```

**Design decisions:**

- **A Vite proxy rather than cross-origin calls.** The browser only ever talks to
  one origin, so CORS cannot bite during development, and the backend's
  plain-HTTP-only constraint is handled in one place.
- **White is the surface, navy is the accent.** The only solid navy is the title
  bar, where text is white; everywhere else is black on white. Navy is otherwise
  reserved for primary buttons, the selected ticket, and the left edge of
  spending approvals.
- **Three states, not two.** Green resolved, **yellow while the agents are
  working**, red unresolved — carried on both a badge and the ticket's left border,
  so state is legible without reading the label. The yellow dot pulses only while a
  run is live.
- **The balance flashes when it changes.** An approval and the money leaving are
  otherwise two unconnected events on screen; the flash ties them together.
- **Backend refusal text is shown verbatim.** The API returns readable reasons —
  insufficient cash with the arithmetic, already paid, missing approver — and
  replacing those with a generic failure would discard the most useful information
  the system produces.
- **Approvals state what each one does before it is clicked:** a restock PO spends
  cash, a price override authorises a price, a customer draft is released for a
  human to send and is *not* sent automatically.
- **One poll loop**, 2s while a run is live and 4s otherwise, rather than a timer
  per panel.

**Bug found during verification, and fixed.** A run started through the proxy
reported `run_id 97e9ae0e83c6`, while the audit trail recorded the same run as
`eebad9fbd393`. `run_boss` minted its own id and `main.py` minted a different one,
so **the dashboard filtered activity by an id that never appears in the trail** —
the agent feed would have been permanently empty while every run worked
perfectly. This is precisely the failure that looks like "the agents did nothing".

Fixed by letting `run_boss` accept a caller-supplied `run_id`, which `main.py` now
passes. Re-verified: 7 records matched the API's run id, 4 rendered as agent rows.

**Verified end to end, through the dashboard's own proxy:**

| Requirement | Result |
|---|---|
| 1. List tickets | 3 tickets, `open` 3 / `resolved` 0, shop date 2026-08-31 |
| 2. Pick a ticket and run the team | run started via proxy, finished, 2 rounds |
| 3. Show each agent and what it did | 4 agent rows — boss routing, facilities with `get_lease_info`, boss verifying, final answer |
| 4. Mark resolved when finished | `resolved` derives from `status == closed`; the guard keeps 102 unresolved, correctly |
| 5. Human approves a payment | rent approved as "Rani Maharani" — *"Rent paid for Chapel Street shop. Next due 2026-10-02."* |
| 6. Balance reflects payments | **$3,400.00 → $1,000.00**, `total_spent` $2,400.00 |
| guard | empty approver → **HTTP 422**, rejected |

**Design tokens checked in the stylesheet**: `#000080` present, Arial first in the
stack, `font-weight: 300`, white body background, white-on-navy title bar, and all
three status colours defined.

`npm run build` succeeds and `tsc --noEmit` is clean. Scaffold leftovers
(`App.css`, `react.svg`, `assets/`) were removed.

**Not visually verified.** The in-app browser preview is not enabled on this
install, so no screenshot was taken — the data contract behind every panel was
verified instead, but the rendered appearance has not been seen and is the user's
to confirm.

**Both servers run in the user's Terminal panel** — backend on 8000, frontend on
5173 — rather than on a harness background timer.

**Database reset** after verification: 3 open tickets, $3,400.00, 0 payments, 0
proposals.

---
## Problem 8B — Connect the board, and record the design

**User prompt:** Connect the frontend to the backend at `https://localhost:8000`,
allow the Vite origin on the backend so the browser may call the routes, and start
the board with `npm run dev` so it can be opened, tickets picked, and the agents
observed. Then record the dashboard layout decisions in `output/design.md`, with
two decisions supplied — the minimalist blue/white palette with Arial and the
contrast rule, and the red/yellow/green ticket resolution colours — noting more
may be added later.

**Connection verified — already in place from 7A and 8A:**

| Check | Result |
|---|---|
| backend `http://localhost:8000/api/health` | **200** |
| board `http://localhost:5173` | **200** |
| CORS preflight from the Vite origin | `access-control-allow-origin: http://localhost:5173` |
| configured origins | `http://localhost:5173`, `http://127.0.0.1:5173` |

Both servers were already running in the user's Terminal panel, so `npm run dev`
did not need re-issuing.

**Protocol correction restated:** the backend is **`http://localhost:8000`**, not
`https` — uvicorn serves no TLS listener. In practice the browser never calls port
8000 directly: the dashboard requests `/api/*` and Vite proxies to the backend, so
everything is same-origin from the browser's point of view. The CORS allowance is
a fallback for calling the backend directly, and both are now in place.

**`output/design.md` created** — 127 lines. Each decision is recorded in the user's
own words, followed by **how it is implemented**, so the file can be checked against
the code rather than read as intent:

- **Decision 1** — a table mapping each part of the instruction to its
  implementation: white body, cards bordered rather than filled, navy confined to
  the title bar plus primary buttons and selection, `#000080` exactly, Arial at
  weight 300, and black-on-white / white-on-navy as the only body pairings. Noted
  that secondary greys still read dark-on-light, so the contrast rule holds.
- **Decision 2** — a state table for the three colours, plus three points that
  were implementation choices rather than instructions: the state is carried on
  **both** a badge and the ticket's left border so the rail can be scanned without
  reading; **colour is never the only signal**, since each badge pairs a dot with a
  text label and so survives colour-blindness and greyscale; and the yellow dot
  **pulses only while a run is live**, reserving motion for the one state that is
  actually changing.

**One point recorded because it affects how the colours should be read:** green
requires `status == closed`, and the backend refuses to close a ticket whose
outcome it cannot verify. So **green means verified done, not "the agents said they
finished"** — a fully worked ticket still awaiting a human stays red, which is the
honest signal rather than a flattering one.

**Supporting choices recorded as changeable**, since they were not specified: the
balance flash, showing backend refusal text verbatim, stating on each approval card
what it will do before it is clicked, and treating the agent panel as an auditable
record rather than a chat.

A layout sketch and a **"Still to decide"** section were included, since the user
said more would be added.

**Every design claim verified against the stylesheet** rather than asserted — 13
checks covering the navy value, white body, black ink, Arial, weight 300, all three
status colours, the navy title bar, pulse scoped to the busy dot, the balance
flash, the 900px breakpoint and the 330px rail. All passed.

**Outcome:** board connected and running, design recorded. No code or database
changes; board still at seed state.

---
**Follow-up 1 — bug report from the user: "Event loop is closed".**

*User prompt:* Reported that running ticket 102 from the dashboard failed with
`RuntimeError: Client failed to connect: Event loop is closed`, and asked for all
three tickets to run without error.

*Cause — a defect in `backend/main.py`.* The run was dispatched as:

```python
background.add_task(asyncio.run, _execute_run(run_id, ticket_id, prompt))
```

Starlette inspects the callable it is given. `asyncio.run` is a **synchronous**
function, so Starlette ran it in a worker thread, where `asyncio.run` built a
brand-new event loop and closed it on completion. Meanwhile `config.build_model()`
is `@lru_cache`'d: the `AsyncOpenAI` client and the MCP stdio toolset bind to
whichever loop first touches them. The first run therefore appeared to work and
every later run failed, because the loop those cached objects were bound to no
longer existed.

This is why it survived earlier testing — each of my own API tests happened to be
the first run after a `--reload` restart, so the failure only showed up on a second
run in the same worker. The user hit it immediately by using the dashboard
normally.

*Fix:* hand Starlette the coroutine **function** and its arguments, so it is
awaited on the server's own running loop:

```python
background.add_task(_execute_run, run_id, ticket_id, prompt)
```

The now-unused `asyncio` import was removed, and the reasoning recorded in a
comment so the line is not "simplified" back into the broken form.

*Verified by running all three tickets consecutively* — runs 2 and 3 are precisely
where the old code failed:

| Ticket | Status | Rounds | Delegations | Agents |
|---|---|---|---|---|
| 101 | **finished** | 2 | 3 | inventory, accounting, customer_service |
| 102 | **finished** | 2 | 1 | facilities |
| 103 | **finished** | 3 | 3 | accounting, inventory, customer_service |

No run failed, and **no tool call failed in any run**. Activity feeds populated
correctly: 7 agent rows for 101, 4 for 102, 7 for 103, with the tools each agent
actually used.

*Safety held throughout:* cash unchanged at $3,400.00, `payments` empty, and both
proposals raised — a customer draft on 101 and a price override on 103 — left with
`approved_by` NULL. Ticket 103 was moved to **pending** by the Boss after the close
guard refused a close, which is the designed behaviour.

*Also observed:* on this run Accounting proposed $52.00 per hoodie (10% off list)
rather than the 0%-off row recorded in an earlier trial — better behaviour, though
the ticket still names no target price, so the open prompt question from Problem 5B
stands.

*Database reset* afterwards so the user starts clean: 3 open tickets, $3,400.00, 0
payments, 0 proposals.

*Outcome:* Bug fixed and all three tickets verified to run without error.

---
## Problem 9A — Prepare for the full run

**User prompt:** Starting 9A, intending to run all tickets. Reported resetting the
working database from the dashboard and then seeing a **$2,400** balance. Asked to
keep the Expected sections in `output/desk_tickets.html` intact so Actual could be
compared against them, with Actual to be filled in later.

**The reported balance did not match a clean reset, so it was checked before
anything else.** A correct reset gives $3,400.00. The database actually showed:

| | |
|---|---|
| checking | **$2,560.00** |
| payments | **1** — invoice 501, $840.00, approved by "Rani" |
| proposals | 2 |
| invoice 501 | **paid** |

So the state was not clean: after resetting, a ticket had been run and the $840
invoice payment approved. $3,400 − $840 = $2,560.

**Why this mattered enough to stop and flag:** paying invoice 501 **unblocks
Bulldog Print Co**. Ticket 101's Expected section describes a vendor blocked by an
open invoice — with 501 already paid, that gate is gone and the agents would
behave differently, so Expected and Actual would not have been comparing like with
like.

**The $2,400 was also not the balance.** The dashboard header stacks two figures —
the balance in large type, and a smaller line reading "$2,400 owed · $840 spent".
$2,400 is the rent still owed. This was recorded as **a design flaw of mine**, not
a user error: two money figures adjacent with the secondary one weakly labelled.
A relabel was offered; the user chose to reset only.

---

**Follow-up 1 — "Event loop is closed" returned.**

*User prompt:* After resetting, the first ticket run failed again with
`RuntimeError: Client failed to connect: Event loop is closed`.

*First finding — the earlier fix was no longer in the file.* `backend/main.py` had
**reverted** to the pre-fix version: line 234 held
`background.add_task(asyncio.run, _execute_run(...))` again, and the `import
asyncio` that the fix had removed was back. The whole patch was gone, not a single
line, and the file's mtime was later than the fix. Most likely an editor saved a
stale buffer over it. Reproduced the failure twice to confirm before changing
anything.

*Re-applied the fix, with a warning comment* telling a future reader not to change
it back and explaining why, so the line is not "tidied" into the broken form again.

*Second finding — the deeper cause was never addressed.* The `asyncio.run` mistake
was only how a second event loop got created; the reason that *kills a run* is that
the MCP stdio session outlives it. `StdioTransport` keeps the subprocess and its
anyio streams alive across client context exits, bound to the loop that created
them, so any later run on a different loop finds a dead session.

Set **`keep_alive=False`** on the transport in `backend/config.py`, so each run
opens a fresh stdio session. Reconnecting costs a few milliseconds; reusing a dead
session costs the whole run. With both fixes the system no longer depends on every
run happening to land on the same loop.

*Verified with four consecutive runs*, including a repeat of the same ticket —
repetition being exactly what broke before:

| # | Ticket | Result | Rounds | Agents |
|---|---|---|---|---|
| 1 | 102 | **finished** | 2 | facilities |
| 2 | 101 | **finished** | 2 | inventory, accounting, customer_service |
| 3 | 103 | **finished** | 2 | accounting, inventory |
| 4 | 102 | **finished** | 2 | facilities |

No failures.

*Reset to a genuinely clean state* for the 9A run: **$3,400.00**, 0 payments, 0
proposals, all three tickets `open`, invoice 501 back to `open`, lease due
2026-09-02.

*Confirmed to the user:* the Expected sections in `output/desk_tickets.html` are
intact — 3 of 3 filled, 3 Actual sections still blank.

---
**Follow-up 2 — diagnose why ticket 101 stayed open, then fix it (Option A).**

*User prompt:* Asked for a step-by-step, read-only diagnosis of why ticket 101
remained open after the agent run despite payment having been made, wondering
whether lead time was the cause — explicitly forbidding any database modification,
purchase order, payment, message or close during the diagnosis. Then, after the
diagnosis, asked to implement **Option A**: a human-confirmed receive-goods tool.

**Diagnosis — nothing was modified.**

*State found:* ticket 101 `open`; invoice 501 **paid**; restock PO (proposal 2)
**approved by Rani** and paid for at $8.00; cash $2,552.00; and
**`CC-TEE-WHITE` size S stock = 0**. The user had done everything correctly — the
money had left the account twice. The goods simply never arrived.

*Audit trail:* the latest run routed Boss → Inventory + Customer Service →
Accounting, no tool failed, nothing was skipped. The Inventory agent had already
named the gap exactly:

> *"Whether the existing PO proposal was actually placed or whether stock was
> subsequently received; current inventory lookup shows none in size S"*

*Root cause — a missing business rule, not a bug.* A grep confirmed **no code path
anywhere writes to the `inventory` table**. Approving a restock PO spent money and
recorded the order but never increased stock — deliberate, since stock should not
appear instantly given a 5-day lead time, but the other half was never built: the
event where goods actually arrive. The close guard for a `customer_order` requires
stock ≥ qty, so **ticket 101 was in a deadlock**, waiting for stock that nothing
could produce. Ruled out: iteration limits, agent instructions, missing approvals,
broken tools.

Also observed: 16 runs had accumulated against ticket 101, and duplicate customer
drafts from repeated attempts.

**Fix implemented — Option A, in three parts.**

1. **`proposals` gains `received_by` and `received_on`.** `ensure_schema()` now
   also ALTERs an existing table to add them, since SQLite has no
   `ADD COLUMN IF NOT EXISTS` and a working copy created earlier would lack them.
2. **`approvals.receive_goods()`** — placed alongside payment, in the module no
   agent can reach. **This is the only code that increases stock.** That placement
   is the point: an agent able to conjure inventory could satisfy a customer order
   nothing was ever delivered for. It refuses a non-PO proposal, an unapproved PO,
   a double receipt, a missing SKU/size, a non-positive quantity, and an inventory
   line that does not exist. It accepts a `qty` argument so a **short delivery is
   recorded as what turned up**, not as what was hoped for. The vendor's expected
   delivery date is reported for context but **not enforced** — the shop's date
   never advances, so blocking on it would merely recreate the deadlock.
3. **`POST /api/receive/{proposal_id}`** plus a dashboard card. Approved-but-
   undelivered POs now appear in the approval queue as outstanding work rather than
   history.

**Second problem found while verifying — the Boss never attempted to close.** With
stock at 1 and invoice 501 paid, the guard reported `blockers: NONE`, yet the
ticket stayed open. The audit trail showed `update_ticket_status` was **never
called**. The Boss's prompt described closing defensively — "a ticket may only be
closed once its outcome is verifiable" — so the model judged for itself that it
could not verify, and never asked.

Rewritten to be positive: always set a status before answering, **attempt the
close and let the tool decide**, and use the tool's refusal reason to choose
`pending` or `blocked`. The tool holds the rules and checks them against the
database; the agent's job is to ask, not to pre-judge. The same instruction was
added to the router contract.

**Result — ticket 101 now closes.**

| Step | Result |
|---|---|
| guards: non-PO proposal | refused, 409 — *"is a customer_draft, not a purchase order"* |
| guards: empty receiver | refused, 422 |
| confirm delivery of PO 2 | stock **0 → 1**, expected delivery 2026-09-05 reported |
| re-run ticket 101 | finished in 2 rounds |
| **ticket 101** | **`closed`, resolved = true** |

**The guard was not weakened** — verified read-only immediately afterwards:
101 would close, **102 refused** ("No rent payment is recorded… requires a human"),
**103 refused** ("No price-override proposal… approved by a human"). Board: 1
resolved, 2 open.

*Outcome:* the structural deadlock is gone and the first ticket resolves end to
end — agents prepare, a human pays, a human confirms delivery, and only then does
the ticket close.

---
**Follow-up 3 — approving should put the agents straight back on the ticket.**

*User prompt:* After resetting and redoing the process, approving the drafted
purchase order left the ticket stuck — the agents did not pick it up again and the
run had to be started by hand. Argued that approving should immediately resume work
on ticket 101, as that is the only way the ticket resolves.

*Assessment:* a missing capability rather than a defect. Every human decision was a
dead end: the backend recorded it and stopped. Nothing told the team that the facts
had changed — that a blocked vendor was now clear, or that stock which had been
zero was now on the shelf. The user was right that this makes the workflow
unusable, since resolving ticket 101 needs three separate human decisions and each
one previously required noticing and re-running by hand.

*Implemented — a human decision now resumes the ticket it unblocked:*

- **`_ticket_for(kind, ref_id)`** resolves which ticket a decision belongs to. A
  proposal names its ticket directly; an invoice and a lease are linked the other
  way round, with the ticket holding the foreign key.
- **`_start_run()`** was factored out so the manual endpoint and the automatic
  resume queue runs identically — one dispatch site rather than two that could
  drift. The "do not change this back to `asyncio.run`" warning was carried onto
  it, since the earlier revert showed that comment earns its place.
- **`_resume()`** queues a run for that ticket and returns its handle, and is
  called by **all four** decision endpoints: approve invoice, approve rent, approve
  proposal, confirm delivery.
- Each response now carries **`follow_up_run`**, so the decision and the work it
  triggered are connected rather than being two unrelated events.

*Dashboard:* `Approvals` reports the follow-up upward and `App` adopts it as the
active run — selecting that ticket, clearing the feed and following the new run —
so approving visibly starts the agents instead of appearing to do nothing. The
confirmation text names the ticket being picked up.

*Verified end to end from a clean reset — one manual run, three approvals, no
re-runs by hand:*

| Step | Effect | Auto-resumed | Ticket 101 |
|---|---|---|---|
| manual run | — | — | `pending` |
| approve invoice 501 | "Bulldog Print Co is now clear to ship" | **yes** | `pending` |
| approve restock PO | "approved and paid… inventory is not incremented until it does" | **yes** | `pending` |
| confirm delivery | "1 x CC-TEE-WHITE size S received. Stock 0 → 1" | **yes** | **`closed`** |

Cash tracked correctly throughout: $3,400.00 → $2,560.00 → $2,552.00.

*The guard was not weakened* — checked read-only straight afterwards: ticket 102
still refused ("No rent payment is recorded"), ticket 103 still refused ("No
price-override proposal… approved by a human").

*Outcome:* ticket 101 now resolves through the intended path — agents prepare, the
human decides, the agents immediately continue — with the human starting exactly
one run.

---
**Follow-up 4 — third failure: no purchase order was ever drafted.**

*User prompt:* Reported that the run still failed, and worse than before — the
agents said "a human must approve a purchase order to restock one unit", but **no
approval appeared in the queue**. Noted this was the third attempt.

*Diagnosis:* `proposals` was **empty**. The audit trail showed Inventory had called
only `get_product_info`, reported the shortfall, and never called
`suggest_vendor_for_sku` or `draft_restock_po`. So the agent's own answer named an
approval that did not exist, and the workflow dead-ended with nothing for the human
to act on.

*Root cause — the same failure mode as the Boss not attempting to close.* A tool
described as *available* gets **reported about** rather than **used**: the model
concludes "a human would need to approve a restock" and stops, which is defensible
prose and useless work. Prompt wording alone had already proven unreliable once, so
fixing it in the prompt only would have been the third guess at the same class of
problem.

*Fixed in three layers, so correctness does not depend on the model choosing well:*

1. **The tool now states the required next step.** `get_product_info` checks
   `proposals` for an unreceived restock order covering the same SKU and size, and
   returns `restock_in_flight` plus an explicit `next_step`. With a shortfall and
   no order it reads: *"ACTION REQUIRED: 1 unit(s) short and no restock order
   exists. Call suggest_vendor_for_sku, then draft_restock_po… Reporting the
   shortfall without drafting the order leaves the human nothing to approve."*
   This is data in the tool result, not instruction in a prompt — much harder for a
   model to reason past. It also prevents double-ordering, since an order already
   in flight is reported instead.
2. **Inventory's prompt makes drafting mandatory** — reporting a shortfall without
   drafting is defined as an *incomplete answer*, with the reasoning spelled out:
   "a human would need to approve a restock" is not a result; drafting the order
   they approve is the result.
3. **The Boss may not answer past an un-ordered shortfall** — if a specialist
   reports stock short and no order has been drafted, it must delegate to Inventory
   to draft one first.

*Verified for reliability rather than once*, given three prior failures — three
independent trials, each from a clean reset:

| Trial | Run | Restock PO drafted |
|---|---|---|
| 1 | finished | **YES** — proposal 1, $8.00 |
| 2 | finished | **YES** — proposal 1, $8.00 |
| 3 | finished | **YES** — proposal 1, $8.00 |

**3/3.** Then the full chain end to end from a clean reset: manual run → approve
invoice (auto-resumed) → approve PO (auto-resumed) → confirm delivery
(auto-resumed) → **ticket 101 `closed`, resolved**, cash $3,400.00 → $2,560.00 →
$2,552.00.

*Board reset afterwards* so the user's own run starts clean.

---
**Follow-up 5 — all three tickets run, plus two layout improvements.**

*User prompt:* Confirmed **101 resolved**, **103 works**, and **102 works** — with
102 correctly not resolving, since the rent is not overdue and payment needs a
human. Noted that 101 and 103 only resolved after follow-up approvals made while
the agents worked, and that 101 closed with a customer draft and a PO still
pending. Then asked for two improvements: (1) split the approval queue so the
bottom panel holds **only initial approvals** — pay invoice 501, pay rent — while
follow-up approvals produced during a run appear **beside the ticket**; and (2)
restore the per-agent descriptions, which had stopped appearing, in one or two
sentences each.

**Diagnosis of the missing agent descriptions.** The activity panel filtered on a
**single `run_id`**. Auto-resume starts a *new* run for each approval, so every
approval replaced the previous run and erased the agent work before it — and
selecting a ticket without running showed nothing at all. The audit trail had the
data all along; the panel was asking the wrong question.

**Implemented:**

1. **Approvals split by origin.** Invoices and rent are the *shop's* obligations —
   they exist whether or not an agent ever runs — so they stay in the main queue.
   Proposals and deliveries are *produced by a run*, so they belong beside the
   ticket that produced them. The component took a `scope` prop rather than being
   duplicated, so both panels share one approval path and cannot drift.
2. **Layout:** the ticket area became a two-column grid — the ticket, its agent
   activity and the team's conclusion on the left; that ticket's approvals in a
   sticky panel on the right, collapsing to one column below 1100px.
3. **Activity now follows the selected ticket**, across every run it has had, so
   approving no longer erases what came before. Capped at the four most recent
   runs, with an "— agents resumed —" divider between them so the sequence stays
   readable.
4. **Summaries clamped to one or two sentences**, as asked, with an ellipsis when
   truncated. The panel is for scanning, not reading.

**A third problem found while verifying, and fixed.** With activity keyed to the
ticket, the feed began showing runs from **before the last reset** — 22 rows across
4 runs, including a row claiming stock had already arrived next to a fresh one
saying it had not. Actively misleading. Added a **`RESET_BOUNDARY`**: `/api/reset`
records the highest audit record id at that moment, and `/api/activity` serves only
records after it. The audit trail itself stays append-only and complete — it is the
*dashboard* that stops showing the previous scenario, which keeps the evidence
intact while making the board truthful.

**Verified after a reset:**

| | |
|---|---|
| bottom panel | Pay invoice 501 $840.00 · Pay rent $2,400.00 — **initial only** |
| ticket 101 panel | restock PO $8.00 — **the agents' follow-up** |
| activity | **7 rows, 1 run**, no stale history |
| per-agent detail | boss / accounting / inventory each with tools and a 1–2 sentence summary |

**Noted for the user, not acted on:** ticket 101 closing while a customer draft and
a purchase order remain unapproved is current behaviour, not a bug — the close
guard checks stock and the linked invoice, not whether every draft has been
actioned. Whether a ticket should be closable with outstanding drafts is a rule
question for the user.

*Board reset afterwards.*

---
**Follow-up 6 — customer drafts: rarer, and free of internal detail.**

*User prompt:* Two refinements — do not write to Tauhid every time the Boss comes
back, only when it is important and final; and never expose internal process to the
customer, who needs only a yes or no about their order, never the reason or the
technical background.

*Enforced in the tool, not only the prompt*, since prompt wording had already proven
unreliable twice:

- **An internal-terms guard.** `draft_customer_message` refuses copy containing
  *invoice, vendor, supplier, purchase order, approval, payment, cash, budget,
  overdue, restock, proposal, lead time, finance, awaiting* and similar, returning
  the offending words plus a rewrite example. Verified: a draft reading "The
  purchase order is awaiting approval and the invoice to our vendor has been paid"
  was **refused with 7 terms flagged**, while "Your size S tee is not available yet.
  We expect it within about a week" was accepted.
- **One open draft per ticket.** A second draft is refused while one is still
  awaiting a human, so a ticket cannot produce a string of messages.
- Prompts updated to match: Customer Service writes rarely and must give a plain
  **yes / no / not yet**; the Boss asks for a draft sparingly and must hand over the
  outcome, since Customer Service holds no stock tool and a draft can only be as
  accurate as the facts it is given.

*Two reliability defects surfaced during verification and were fixed
deterministically:*

1. **A duplicate purchase order** was drafted for a line already covered.
   `draft_restock_po` now refuses when an unreceived order exists for the same SKU
   and size.
2. **Finished tickets sat at `pending`.** The close guard reported `WOULD CLOSE`,
   but the Boss had not called `update_ticket_status` on the pass where the last
   blocker cleared. Two changes: the tool now **refuses to park** a ticket with
   nothing blocking it, and `_reconcile_ticket()` runs after every agent run —
   if the guard reports no blockers, the ticket is closed with a note. **The guard
   is the authority on "done", so the board now reflects that whether or not the
   model remembers.** This was made deterministic rather than prompt-dependent
   because the user had already absorbed several rounds of the same flakiness.

*Verified end to end:* one purchase order, **one** customer draft, no internal
terms in it, ticket closed, stock 1, cash $2,552.00.

---

**Follow-up 7 — fill the Actual sections.**

*User prompt:* Supplied, from the dashboard, which agents worked each ticket and
which MCP tools they called, to be written into the **Actual** sections of
`output/desk_tickets.html` with the Expected sections preserved for comparison.

*Cross-checked against the audit trail before recording.* Ticket 101's list matched
the recorded tool calls **exactly**. For 102 and 103 the trail held a few extra
calls, but those span several runs including test runs, whereas the user reported
the run they watched — so the user's observation was recorded as the Actual, and
the discrepancy noted rather than silently reconciled.

*Each Actual section carries:* an agent-to-tools table, and a **Compared with
Expected** block listing what ran as predicted and what was expected but not
observed — with the reason, since an unexplained absence reads as a failure:

- **101** — 6 of 8 expected tools. `get_vendor_info` was unnecessary because
  `suggest_vendor_for_sku` already returns lead time and ship status;
  `get_financial_info` was unnecessary because the invoice status arrives with the
  ticket. Accounting therefore never appeared. The Expected note that closing is the
  Boss's tool, not Customer Service's, held exactly.
- **102** — the shortest run, correctly: rent is not overdue, so nothing escalated,
  and the ticket stayed open because paying requires a human, as predicted. The
  earlier `get_vendor_info` correction held — it did not appear.
- **103** — 7 of 9, including both tools that matter for this ticket. Accounting
  calling `get_product_info` is expected behaviour, not a stray call: unit cost and
  list price live in `pricing`, so the discount margin cannot be computed without
  it. No customer draft was written because the discount was undecided — there was
  nothing final to tell the Yale AI Club, which is the revised rule working.

*Verified:* 3 Expected sections preserved, 3 Actual sections filled, no placeholders
left, Cash and Reflections still "coming later", zero external references, balanced
markup, 31 KB.

---
## Problem 9B — Cash tab in `desk_tickets.html`

**User prompt:** Asked to fill the **Cash** tab with every cash movement — the
starting balance of $3,400.00 after reset, the ending balance of $2,288.00, and a
per-ticket account of how resolving each one affected cash, with the payment type,
dollar amount and reason. Supplied the figures: ticket 101 paid $840.00 then $8.00;
ticket 103 paid $264.00; ticket 102 paid nothing, both because rent was not overdue
and because it was worked *after* 101 and 103, by which point paying $2,400.00
would have overdrawn the account.

**Every figure verified against the `payments` table before being written**, rather
than transcribed:

| # | Kind | Ref | Amount | Balance after |
|---|---|---|---|---|
| — | starting balance | — | — | $3,400.00 |
| 1 | invoice | 501 | $840.00 | $2,560.00 |
| 2 | purchase_order | 1 | $8.00 | $2,552.00 |
| 3 | purchase_order | 3 | $264.00 | $2,288.00 |

The running total reconciles exactly with `cash_accounts.balance` = $2,288.00. The
overdraft claim checks out too: $2,288.00 − $2,400.00 = **−$112.00**, which the cash
guard refuses. All three payments carry an approver.

**Written into the Cash tab:**

- A summary — starting balance, total paid out, ending balance, payment count.
- **A ledger of every movement in order**, with a running balance column, including
  a zero row for ticket 102 so the absence of a payment is visible rather than
  implied by omission.
- **Ticket-by-ticket detail.** For 101, the point that $840 of its $848 was an
  *existing debt* rather than the cost of the order — the tee itself cost $8.00 —
  and that the invoice was the gate on the whole ticket, not optional housekeeping.
  For 103, that the approved discount **moved no cash**: a price override authorises
  what may be charged, and since no revenue is modelled the sale never appears.
- **For 102, both reasons recorded as independent** — either alone would have
  prevented payment. Not overdue *and* unaffordable by the time it was worked.

**One point added that the user's figures imply but did not state.** Sequence
decided this outcome. Had 102 been worked first the rent *was* affordable —
$3,400.00 − $2,400.00 = $1,000.00 — but paying it would then have left too little
for ticket 101's $840.00 invoice, blocking Bulldog and stalling both apparel
tickets. **The three tickets compete for one pot of money, so the order they are
worked in changes which of them can be resolved at all.** This is the sharpest
finding in the cash record and would have been lost if the tab only listed amounts.

- A closing table of **what never moved cash** — the price override, the customer
  draft, and the unpaid rent — each with the reason, so a reader does not assume
  they were missed.

**Verified:** Cash tab filled, Reflections still "coming later", 3 Expected and 3
Actual sections preserved, zero external references, balanced markup, 38 KB.

---
**Follow-up 1 — `output/resolved_tickets.json`.**

*User prompt:* Supplied, per ticket, the id, final status, short outcome, what each
agent contributed, and the human approvals, to be written into
`output/resolved_tickets.json`.

*Discrepancy found and surfaced before writing.* The **live database no longer
matched the account being documented**: it showed tickets 101 and 103 as `pending`
with one payment and $2,560.00 cash, against the 9A run's `closed`/`closed` with
three payments and $2,288.00. The database had been reset and partially re-run
since. **All three 9A run ids were still present in the audit trail**, so the record
was sound — but the file would have read as a false claim about current state had
that gone unsaid.

Resolved by making the file's scope explicit rather than by changing the content:
a `what_this_records` field stating it documents the 9A run, and a
`note_on_live_database` explaining the divergence and why it is expected — the
database is working state, the audit trail is append-only.

*Written as supplied, with three additions:*

- **`run_evidence` per ticket**, read from the audit trail rather than retyped:
  record count, rounds, delegations, elapsed seconds, agents that responded, and
  every MCP tool called with the agent that called it. The operator's account and
  the machine record now sit side by side in one file.
- **`cash_effect` per ticket**, carrying the figures verified for the Cash tab — and
  the distinctions that matter: that $840 of ticket 101's $848 settled a
  pre-existing debt rather than the order, that only the restock moved cash on 103
  since a price override authorises a price rather than paying one, and that for 102
  the working order was what made the rent unaffordable.
- **`moved_cash` on every approval**, since 2 of the 5 approvals moved no money at
  all — the customer draft and the price override. A reader counting approvals as
  spending would otherwise overstate it.

*Corrected silently:* the prompt's "Ticket 1" was recorded as ticket **101**.

*Summary block:* 3 tickets, 2 resolved, 1 unresolved, 5 human approvals of which 3
moved cash, and **0 agent-initiated payments** — no agent paid, ordered, applied a
price or sent a message.

*Verified:* valid JSON, 7.9 KB, all three run ids resolve against the audit trail.

---
**Follow-up 2 — fix the contradicting ticket, then build `resolved_board.html`.**

*User prompt:* Supplied screenshots of the resolved tickets and asked for them to be
saved into a `resolved_board.html`.

*A defect was visible in the first screenshot and was raised before building around
it.* Ticket 101 showed a green **Resolved** badge directly above a conclusion
reading *"Ticket 101 has conflicting availability information… I can't confirm
fulfillment"*. Two separate causes:

1. **`update_ticket_status` appended a note on every call**, and `get_ticket_info`
   feeds those notes back to the agents. Ticket 101's notes had become a stack of
   contradicting statements — *"0 available (short by 1)"* sitting above *"1 unit
   available"* — and the agents, reading both, correctly reported a conflict. **The
   accumulated history was degrading their reasoning.** Fixed: only the ticket's own
   note plus the *latest* status note are kept. The full history remains in the
   audit trail, which is the right place for it.
2. **Closure was unattributed.** When the reconciliation pass closed a ticket the
   Boss had not closed, nothing said so — leaving a green badge beside hedging prose.
   Fixed: tickets now carry `closed_by` (`agent` or `system`), shown under the badge
   and, when the system closed it, as a note above the conclusion explaining the
   team's wording may predate that check.

*Verified by a clean run:* ticket 101's notes collapsed from four contradicting
lines to two, and it closed with `closed_by: agent` — the Boss closed it unaided, so
reconciliation was not needed at all.

*Screenshots saved* to `output/evidence/` with SHA-256 hashes — four for ticket 101,
four for ticket 103.

*`output/resolved_board.html` built* — 13 KB, referencing 2.1 MB of images from
`evidence/` rather than embedding them, which keeps the file light and the
screenshots separately inspectable. Each caption carries the image's SHA-256 prefix,
so a screenshot cannot be swapped without the record disagreeing.

*Structure:* a result summary; ticket 101 and 103 each with outcome prose, a table of
human approvals marking which moved cash, and the four screenshots captioned by what
they show; then **ticket 102 documented as correctly unresolved** — with both
independent reasons, the sequencing consequence, and an explicit note that a red
badge here is the system working rather than a failure.

*State at capture matched the documented 9A run exactly:* 101 and 103 closed, 102
open, cash $2,288.00, three payments all carrying a named approver.

---
**Follow-up 3 — ticket 102 resolved, and the $112 finding.**

*User prompt:* Supplied screenshots of ticket 102, noting they had reset 101 and 103
to work 102 first so there would be enough cash.

*Checked the database before saving, because the screenshot looked impossible* —
a green **Resolved** badge beside a conclusion reading *"no payment has been made or
initiated"*.

**The badge was right.** Rent of $2,400.00 was paid and recorded against Rani, cash
went $3,400.00 → $1,000.00, the lease rolled to 2026-10-02, and the close guard
reports no blockers. **The conclusion text was wrong**, and for a reason already on
record: **no agent can read the `payments` ledger.** Facilities holds only
`get_lease_info`, which carries no payment status, so the team genuinely could not
see the payment that had just been made.

**The finding that matters for the deliverable.** The screenshots now come from two
different runs, and they cannot both be one board — placing 102's green badge beside
the existing 101/103 screenshots would claim all three resolved, which never
happened and is not possible:

| | Run A — 101, 103, then 102 | Run B — 102 first |
|---|---|---|
| | invoice $840 → $2,560 | rent $2,400 → $1,000 |
| | restock $8 → $2,552 | invoice $840 → $160 |
| | restock $264 → $2,288 | restock $8 → $152 |
| | rent $2,400 → **REFUSED, −$112** | restock $264 → **REFUSED, −$112** |

**All four payments total $3,512 against $3,400 — the shop is $112 short, whichever
order the tickets are worked in.** Both orderings resolve exactly two of three, and
the shortfall is identical because it does not depend on sequence. Raised with the
user rather than overwriting the board; restructuring it to show both runs was
offered, with Run B's remaining tickets marked *not captured* rather than predicted.

---

**Follow-up 4 — audit trail, and a harness accuracy pass.**

*User prompt:* Append real runs to `output/audit_trail.json`, and update
`output/harness.md` so it covers tables, MCP tools, the five agents, API routes, the
dashboard and safety rules — supplying the MCP tool table, the API route table and a
description of the dashboard, and asking for the accuracy to be checked against the
latest re-run.

**On the audit trail: nothing to append by hand.** It is written by
`backend/audit.py` on every run and already holds **1,047 records across 119 runs**
(2.9 MB), including every run from 9A and 9B. Appending manually would corrupt the
distinction that makes it evidence — the file records what the system did, not what
anyone said it did.

**Harness accuracy pass — three gaps found and fixed:**

1. **A missing API route.** The code has **13** routes; the harness documented 12.
   `POST /api/receive/{proposal_id}` — added in Problem 9A to break the ticket 101
   deadlock — was never written up. Added to the route table and given a detail
   section: the only route that increases stock, a human action, with its refusals
   and the note that approving a purchase order does *not* increment inventory.
2. **The tables list said nine.** There are now **ten** — `proposals` was added to
   the working copy. The intro corrected, with a cross-reference.
3. **No Dashboard section at all**, despite the user asking for one.

**Dashboard section written**, covering: the layout with a diagram; what each region
does; the design rules (white-dominant, `#000080` navy, Arial 300, black-on-white
and white-on-navy only); the three status colours with the note that **green means
verified done** rather than "the agents said so"; and the behaviour worth knowing —
backgrounded runs, approvals auto-resuming the ticket, activity following the ticket
rather than a single run, reset hiding earlier activity, and refusals shown verbatim.

Also documented **`closed_by`** on `/api/tickets`, which was added in 9B and
distinguishes a ticket the Boss closed from one the reconciliation pass closed.

**Everything verified against the code rather than asserted:**

| Check | Result |
|---|---|
| MCP tools | 10 in code, **10 documented** |
| agent tool scoping | matches all five agents |
| DB tables | 10 in database, **10 documented** |
| API routes | 13 in code, **13 documented** |
| model pin | `gpt-6-luna` |
| iteration cap | `MAX_ITERATIONS = 3` |
| no payment tool exists | confirmed |

`output/harness.md` is now **945 lines** across six sections: Safety rules, the
schema, The agent team, MCP Tools, Backend API, Dashboard.

---
## Problems 10A and 10B — the Reflections tab

**User prompt:** Combined 10A and 10B, since 10B ties the Part A essays to Campus
Customs. Supplied written answers to all five reflection parts, to be placed in the
**Reflections** tab of `output/desk_tickets.html`.

**Written as supplied**, structured one section per part. Part 1's four distinct
episodes were given their own sub-headings — the post-approval stall on 101, the
over-technical customer email on 101, 102 refusing to overspend, and 103 benefiting
from the 101 fix — because they are separate findings rather than one narrative.

**Three gaps and corrections surfaced on the page, marked as supplementary rather
than edited into the user's own words:**

1. **Part 2's entry for ticket 103 was blank** — the prompt gave only a dash. Left
   marked *"Not yet written"* with the facts from the Actual tab beside it: 7 of 9
   expected tools ran, `get_vendor_info` was unnecessary because
   `suggest_vendor_for_sku` already returns lead time and ship status, and no
   customer draft was written because the discount was undecided.
2. **Part 2's reason for ticket 102 does not match the audit trail.** The essay says
   only Boss and Facilities were needed *because the rent was not overdue*; the
   Boss's own recorded reason was that **"rent cannot be marked paid by this team"**
   — Accounting was skipped because affordability was moot, no agent being able to
   pay. The run also took **three rounds, not one**: Facilities first looked up lease
   **102** instead of lease **1**, returned `answered=false` with three missing
   entries, and the Boss caught it and re-delegated. Recorded as an audit-trail note
   so the user can decide whether to revise the essay.
3. **Part 5's third item cannot be solved by adding a tool alone.** Detecting hidden
   fees needs line items to compare against contract terms, and the `invoices` table
   holds a single `amount` and a free-text `description` — there are no line items
   and no contract terms stored anywhere. **It needs new tables before it needs a new
   tool.** Noted on the page.

**One observation added to Part 5's second item:** external data sources such as
Yahoo Finance would be the **first break from safety rule 3**. No agent currently has
network access of any kind — the only toolset is a local server over one database —
so that boundary would have to be rewritten deliberately rather than incidentally.

**One point reinforced in Part 1:** the user's note that Customer Service *drafted*
the over-technical email rather than sending it is exactly the "nothing is ever sent"
rule paying off — it turned a bad message into a reviewable draft rather than
something a customer received.

**Verified:** all 5 parts present, **no placeholders left anywhere in the file**, 3
Expected sections and 3 Actual sections preserved, the Cash tab intact, zero external
references, balanced markup, 50 KB.

`output/desk_tickets.html` is now complete across all five tabs — 101, 102, 103,
Cash and Reflections.

---
## Session note — Save before stepping away

**User prompt:** "Save everything for me, I want to be away"

**Everything was already on disk**; this was a verification pass rather than a
flush. State confirmed:

**Deliverables**

| File | Size | State |
|---|---|---|
| `output/desk_tickets.html` | 51 K | **complete** — 5 tabs, 3 Expected, 3 Actual, Cash, 5 Reflection parts, **0 placeholders** |
| `output/resolved_tickets.json` | 8 K | valid |
| `output/resolved_board.html` | 13 K | documents Run A |
| `output/harness.md` | 40 K | 945 lines, 6 sections |
| `output/design.md` | 6 K | — |
| `output/audit_trail.json` | 3.0 M | **1,047 records / 119 runs**, append-only, intact |
| `output/evidence/` | — | 13 screenshots |
| `mcp_tool_tests.json` | 12 K | — |
| `AI_prompts.md` | 159 K | every turn logged |

**Code health:** all backend and MCP modules import cleanly; model `gpt-6-luna`;
`MAX_ITERATIONS` 3; **10 MCP tools**; **13 API routes**; frontend `tsc --noEmit`
clean. Both servers up — backend 8000, board 5173.

**Database:** 101 `open`, 102 `closed`, 103 `open`, cash $1,000.00, 1 payment
(rent), 0 proposals — mid Run B, since the user worked 102 first. Seed still hashes
to `23686a90…`, untouched throughout.

**Memory updated** with a status note: what is built, which problems are complete,
the deliverable list, the **$112 scarcity finding**, the one open decision, and the
three known gaps.

**One decision left open, deliberately:** `resolved_board.html` documents Run A
(101 and 103 resolved) while the ticket 102 screenshots come from Run B. The board
cannot honestly show all three green, because all four payments total $3,512
against $3,400 — the shop is **$112 short in either ordering**, so exactly two of
three resolve whichever way the tickets are worked. Restructuring the board to
present both runs was offered and is awaiting the user's answer; it was not done
unilaterally because it changes what the deliverable claims.

**Known gaps, all documented rather than hidden:** no agent can read the `payments`
ledger — which is why Facilities reported "no payment has been made" after rent had
in fact been paid; Accounting cannot read `proposals`, so it cannot verify its own
discount approvals; and hidden-fee detection would need new tables, not just a new
tool.

---
## Problem 11 — Publish to a public GitHub repository

**User prompt:** Push the code to a public GitHub repository and record the URL in
`output/github_url.txt`. Do not include the real `.env` with the API key — use
`.env.example` — and do not leak anything confidential. Include **both** databases.

**Published:** <https://github.com/naraniwidodo/campus-customs-multi-agent-ops>

**Secret scanning before anything irreversible happened.** Publishing is outward
facing and cannot be undone, so the tree was scanned *before* any repository
existed:

- The real credential values were loaded from the parent `.env` **without printing
  them**, then searched for across every file that would be committed. The search
  covered `PORTKEY_API_KEY`, `OUTLOOK_CLIENT_ID` and `OUTLOOK_TENANT_ID`.
- Pattern scan for OpenAI-style keys, GitHub tokens, AWS keys, bearer tokens,
  private key blocks and email addresses: **all none**.
- Re-run against the *staged* tree immediately before committing: **clean**.

**A false positive worth recording.** The first staged-tree scan reported four
"leaks" — but the matched values were `https://api.portkey.ai/v1`, a public URL, and
`gpt-5.6-luna`, a model name. The check had treated any value of twelve characters
or more as a secret. Narrowed to credential-bearing keys only and re-run; the actual
API key appeared nowhere. Recorded because a scan that cries wolf is worse than none
— the next person reading these results needs to know which hits were real.

**There is no local `.env` to leak.** The key is read from a `.env` one directory
above the project, which is outside the repository entirely.

**`.gitignore` rewritten** to exclude `.env`, `*.key`, `*.pem`, `token_cache.json`,
`.venv/`, `node_modules/`, `frontend/dist/` and `__pycache__/` — and to **stop
excluding the working-copy database**, since the user asked for both. The reason both
are tracked is written into the file itself so it does not read as an oversight.

**A root `README.md` was added** — the repository had none, only a Vite default and
the MCP server's. It covers the structural agents-prepare/humans-execute separation,
the five agents, the five safety rules, how to run it, why both databases are
tracked, and the $112 scarcity finding.

**Verified against GitHub after pushing, not merely asserted:**

| Check | Result |
|---|---|
| visibility | **PUBLIC** |
| `.env` | **NOT on GitHub** |
| `.env.example` | present |
| `campus_customs.db` (seed) | present |
| `data/campus_customs_new.db` (working copy) | present |
| files committed | 69, then 70 with the URL file |
| working tree | clean |

**Flagged to the user, not a credential:** the macOS username `nurazizahmaharani`
appears in absolute paths inside `.mcp.json`, `output/audit_trail.json` and
`mcp_server/README.md`, and is now publicly visible. Their GitHub account is a
different name. Raised before publishing with an offer to genericize the paths
afterwards; not changed unilaterally, since `.mcp.json`'s absolute paths are what
make the local setup work.

**`output/github_url.txt`** written with the repository URL, then committed and
pushed in a second commit.

---
**Follow-up 1 — check the file structure against the assignment layout.**

*User prompt:* Shared the assignment's expected file layout and asked for the
structure to be checked before submission.

*Compared path by path. Two mismatches found:*

| Expected | Where it actually was |
|---|---|
| `data/campus_customs.db` | at the project **root**, not in `data/` |
| `output/mcp_smoke.json` | `mcp_tool_tests.json`, at the **root** |

Everything else matched, including all five agent prompts and every `output/`
deliverable.

*Both moved with `git mv`* so history follows the files, then **every reference
updated** — found by grep first rather than fixed reactively:

- `backend/approvals.py` — `SEED_PATH`, the one place in code that resolves the
  seed.
- `mcp_server/db.py` — the module docstring and the not-found error message, which
  tells the operator where to copy from.
- `README.md`, `mcp_server/README.md`, `output/harness.md` — the seed path and the
  `cp` reset commands.

*Verified after moving, not assumed:* the backend and MCP modules still import,
`SEED_PATH` resolves to the new location and exists, and **a real reset through
`approvals.reset_database()` succeeded** — 3 open tickets, $3,400.00, 0 payments,
0 proposals. The seed still hashes to `23686a90…f360a`, unchanged by the move.

*The assignment also specifies what the README must explain*, and the existing one
covered only part of it — **starting the MCP server was missing entirely**. The
running section was rewritten as a numbered sequence covering all five required
points:

0. install
1. **copy the original database to the working copy** for a clean run
2. **start the MCP server** (stdio, with the note that the backend launches it
   automatically, plus the HTTP option for inspection)
3. **start the FastAPI backend** — with the plain-HTTP warning and the
   kill-the-whole-group stop command, since `--reload` runs a supervisor and a worker
4. **start the React board**
5. **reset before a full three-ticket run**, with the expected row counts and the
   reminder that a reset is verified by row counts rather than by hash

*Final check:* **all 26 expected paths present**, nothing left at the old locations.

---
