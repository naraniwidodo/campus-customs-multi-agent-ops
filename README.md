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

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env          # add your own PORTKEY_API_KEY
```

Backend — **plain HTTP, not HTTPS**:

```bash
cd backend && ../.venv/bin/python -m uvicorn main:app --reload --port 8000
```

Dashboard:

```bash
cd frontend && npm install && npm run dev     # http://localhost:5173
```

## The databases

Both are tracked deliberately:

- **`campus_customs.db`** — the pristine seed, never written to
- **`data/campus_customs_new.db`** — the working copy the agents read and write

Reset with `POST /api/reset`, or `cp campus_customs.db data/campus_customs_new.db`.
Verify a reset by **row counts**, not by hash: the working copy carries an extra
`proposals` table the seed lacks.

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
