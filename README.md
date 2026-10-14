# Campus Customs — Multi-Agent Operations

A back-office agent team that runs a merchandise shop's ticket desk: customer
orders, rent notices and discount requests land on a board, five agents work them,
and **a human approves anything that spends money**.

Built for AI Foundations for Managers, Homework 5.

## The idea

Agents prepare; humans execute. That separation is **structural, not a policy**:
the agents' entire toolset is an MCP server with no payment tool, and the only code
that moves money lives in `backend/approvals.py`, reachable solely through endpoints
a person invokes. No agent has an HTTP client or an import path to it.

## The pieces

| Part | What it is |
|---|---|
| `mcp_server/` | FastMCP server over SQLite — **10 tools**, 6 read, 4 write |
| `backend/` | FastAPI — **13 routes** — plus the five-agent PydanticAI team |
| `frontend/` | React + Vite + TypeScript dashboard |
| `output/` | Deliverables, evidence and the append-only audit trail |

## The agents

Hub-and-spoke: the Boss routes and verifies, specialists work their own domain and
hand results back.

**Boss** · **Inventory** · **Accounting** · **Facilities** · **Customer Service**

Each holds only the tools its domain needs, so an agent cannot stray by reaching for
another's.

## Safety rules

1. **No agent may make a payment** — there is no payment tool at all
2. **The database is the only source of truth** — never invent, say what is missing
3. **No private or external sources** — no network access of any kind
4. **Work efficiently** — hard cap of 3 orchestration rounds
5. **Always `gpt-6-luna`** — one constant, imported by all five agents

Nothing is ever sent to a customer or vendor. Drafts stay on the board.

## Running it

### 0 · Install

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then add your own PORTKEY_API_KEY
```

The real `.env` is never committed. The model is pinned to `gpt-6-luna`.

### 1 · Copy the original database to the working copy

Do this whenever you want a clean run. The seed is **read, never written** — the
agents only ever touch the working copy.

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

### 2 · Start the MCP server

The agents' only access to the shop. It speaks stdio, which is how an MCP client
launches it — the backend starts it automatically, so you normally do **not** need
to run it by hand:

```bash
cd mcp_server && ../.venv/bin/python server.py
```

To inspect it directly over HTTP at `http://127.0.0.1:8003/mcp`:

```bash
cd mcp_server && ../.venv/bin/python server.py --http
```

### 3 · Start the FastAPI backend

**Plain HTTP, not HTTPS** — there is no TLS listener, and `https://localhost:8000`
fails with an error that reads like the backend is down.

```bash
cd backend && ../.venv/bin/python -m uvicorn main:app --reload --port 8000
```

`--reload` runs a supervisor *and* a worker, so stop the whole group:

```bash
pkill -f "uvicorn main:app"; sleep 2; pgrep -f "uvicorn main:app" || echo stopped
```

### 4 · Start the React board

```bash
cd frontend && npm install && npm run dev     # http://localhost:5173
```

The board calls `/api/*`, which Vite proxies to the backend, so the browser only
ever talks to one origin.

### 5 · Reset before a full three-ticket run

Always reset first, so the run starts from the seeded scenario:

```bash
curl -X POST http://localhost:8000/api/reset
```

or press **Reset to original data** on the board, or copy the file as in step 1.

**Verify a reset by row counts, not by hash** — the working copy carries an extra
`proposals` table the seed lacks, so the two files will never hash alike:

| Check | Expected |
|---|---|
| tickets | 101, 102, 103 all `open` |
| `cash_accounts.checking` | $3,400.00 |
| `payments` | empty |
| `proposals` | empty |
| `desk.date_today` | `2026-08-31` |

Then pick a ticket on the board and press **Run the agent team**. Approving anything
restarts the agents on that ticket automatically — you do not re-run by hand.

## The databases

Both are tracked deliberately:

- **`data/campus_customs.db`** — the pristine seed, never written to
- **`data/campus_customs_new.db`** — the working copy the agents read and write

## The scenario, and its sharpest finding

Three tickets compete for **$3,400** of cash. The payments they require total
**$3,512**.

**The shop is $112 short — whichever order the tickets are worked in.** Exactly two
of three resolve either way, and the shortfall is identical because it does not
depend on sequence. Which two you get is the only thing the ordering decides.

## Deliverables

| File | |
|---|---|
| `output/desk_tickets.html` | Expected vs Actual per ticket, cash ledger, reflections |
| `output/resolved_board.html` | Screenshot evidence of the resolutions |
| `output/resolved_tickets.json` | Per-ticket outcomes, agents, approvals |
| `output/harness.md` | Schema, agents, tools, API, dashboard, safety rules |
| `output/design.md` | Dashboard design decisions |
| `output/audit_trail.json` | Append-only record of every run |
| `AI_prompts.md` | Full prompt log |

## A note on the audit trail

Tool calls in `output/audit_trail.json` are read from the model's own message
history, not from what an agent *claimed* it did. That distinction found two real
bugs during development — a Boss delegating to itself, and a tool argument silently
suppressing another.
