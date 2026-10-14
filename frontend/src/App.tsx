import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { AgentActivity } from "./components/AgentActivity";
import { Approvals } from "./components/Approvals";
import { StatusBadge, ticketState } from "./components/StatusBadge";
import { TicketList } from "./components/TicketList";
import type {
  ActivityRecord,
  ApprovalsResponse,
  CashResponse,
  RunState,
  Ticket,
} from "./types";

const POLL_IDLE = 4000;
const POLL_RUNNING = 2000;

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [asOf, setAsOf] = useState<string>("");
  const [cash, setCash] = useState<CashResponse | null>(null);
  const [approvals, setApprovals] = useState<ApprovalsResponse | null>(null);
  const [activity, setActivity] = useState<ActivityRecord[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [run, setRun] = useState<RunState | null>(null);
  const [approver, setApprover] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [balanceChanged, setBalanceChanged] = useState(false);

  // Activity follows the selected ticket across every run it has had, not a
  // single run id. An approval starts a fresh run, so keying on one id made each
  // approval erase the agent work that came before it.
  const runIdRef = useRef<string | null>(null);
  const selectedRef = useRef<number | null>(null);
  const lastCash = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [t, c, a] = await Promise.all([api.tickets(), api.cash(), api.approvals()]);
      setTickets(t.tickets);
      setAsOf(t.as_of);
      setApprovals(a);

      // Flash the balance when it actually moves, so an approval is visibly
      // connected to the money leaving.
      if (lastCash.current !== null && lastCash.current !== c.checking) {
        setBalanceChanged(true);
        setTimeout(() => setBalanceChanged(false), 1500);
      }
      lastCash.current = c.checking;
      setCash(c);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // One poll loop. It runs faster while the team is working.
  useEffect(() => {
    const working = run?.status === "queued" || run?.status === "running";

    const tick = async () => {
      try {
        const ticket = selectedRef.current;
        if (ticket != null) {
          const feed = await api.activity(0, 300, ticket);
          // Keep the few most recent passes over this ticket. Older runs are in
          // the audit trail; the panel is for what is happening now.
          const order: string[] = [];
          for (const r of feed.records) if (!order.includes(r.run_id)) order.push(r.run_id);
          const recent = new Set(order.slice(-4));
          setActivity(feed.records.filter((r) => recent.has(r.run_id)));
        }
        if (run && working) {
          const latest = await api.run(run.run_id);
          setRun(latest);
          if (latest.status === "finished" || latest.status === "failed") {
            await refresh();
          }
        }
      } catch {
        /* a transient poll failure is not worth surfacing; the next tick retries */
      }
    };

    void tick();
    const id = setInterval(tick, working ? POLL_RUNNING : POLL_IDLE);
    return () => clearInterval(id);
  }, [run, refresh]);

  const selectTicket = (id: number) => {
    setSelected(id);
    selectedRef.current = id;
    setRun(null);
    setActivity([]);
    runIdRef.current = null;
  };

  const startRun = async () => {
    if (selected == null) return;
    setError(null);
    setActivity([]);
    try {
      const started = await api.runTicket(selected);
      runIdRef.current = started.run_id;
      setRun({ run_id: started.run_id, ticket_id: selected, status: "queued" });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  /** A human decision restarted the agents — follow that run on the board. */
  const adoptRun = (runId: string, ticketId: number) => {
    setSelected(ticketId);
    selectedRef.current = ticketId;
    runIdRef.current = runId;
    setRun({ run_id: runId, ticket_id: ticketId, status: "queued" });
  };

  const doReset = async () => {
    try {
      await api.reset();
      setRun(null);
      setActivity([]);
      runIdRef.current = null;
      selectedRef.current = selected;
      lastCash.current = null;
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const ticket = tickets.find((t) => t.id === selected) ?? null;
  const working = run?.status === "queued" || run?.status === "running";
  const runningTicketId = working ? (run?.ticket_id ?? null) : null;

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Campus Customs — Operations</h1>
          <div className="sub">
            Multi-agent shop desk{asOf ? ` · shop date ${asOf}` : ""}
          </div>
        </div>
        <div className="balance">
          <div className="label">Checking</div>
          <div className={`value ${balanceChanged ? "changed" : ""}`}>
            {cash ? `$${cash.checking.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : "—"}
          </div>
          {cash && (
            <div className="meta">
              ${cash.total_obligations.toLocaleString()} owed · $
              {cash.total_spent.toLocaleString()} spent
            </div>
          )}
        </div>
      </header>

      <div className="page">
        {error && <div className="error" style={{ marginBottom: 16 }}>{error}</div>}

        <div className="cols">
          <aside>
            <TicketList
              tickets={tickets}
              selectedId={selected}
              runningTicketId={runningTicketId}
              onSelect={selectTicket}
            />
            <button className="btn btn-quiet btn-small" style={{ width: "100%", marginTop: 4 }} onClick={doReset}>
              Reset to original data
            </button>
          </aside>

          <main>
            {!ticket && (
              <div className="card">
                <div className="empty">Select a ticket to begin.</div>
              </div>
            )}

            {ticket && (
              <div className="ticket-grid">
                <div>
                <div className="card">
                  <div className="ticket-top">
                    <div>
                      <div className="ticket-id">#{ticket.id} · {ticket.type}</div>
                      <h2 style={{ fontSize: 18, marginTop: 2 }}>{ticket.subject}</h2>
                      <div className="ticket-meta">{ticket.requester}</div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <StatusBadge state={ticketState(ticket, working && run?.ticket_id === ticket.id)} />
                      {ticket.resolved && (
                        <div className="closed-by">
                          {ticket.closed_by === "system"
                            ? "closed by system verification"
                            : "closed by the agent team"}
                        </div>
                      )}
                    </div>
                  </div>

                  {ticket.notes && <div className="approval-note" style={{ marginTop: 10 }}>{ticket.notes}</div>}

                  <div className="kv">
                    {ticket.sku && <span>{ticket.sku} · size {ticket.size} · qty {ticket.qty}</span>}
                    {ticket.invoice && (
                      <span>
                        invoice {ticket.invoice.id} · ${ticket.invoice.amount.toLocaleString()} · {ticket.invoice.status}
                      </span>
                    )}
                    {ticket.lease && (
                      <span>
                        {ticket.lease.space_name} · ${ticket.lease.monthly_rent.toLocaleString()} due {ticket.lease.next_due}
                      </span>
                    )}
                    <span>status: {ticket.status}</span>
                  </div>

                  <div className="approval-actions">
                    <button className="btn" onClick={startRun} disabled={working}>
                      {working ? "Agents working…" : "Run the agent team"}
                    </button>
                    {run?.status === "finished" && (
                      <span className="round">
                        {run.iterations} rounds · {run.delegations} delegations ·{" "}
                        {run.agents_consulted?.join(", ")}
                      </span>
                    )}
                    {run?.status === "failed" && <span className="round">Run failed: {run.error}</span>}
                  </div>
                </div>

                {run?.status === "finished" && run.answer && (
                  <div className="card">
                    <div className="section-title">What the team concluded</div>
                    {ticket.closed_by === "system" && (
                      <div className="reconciled">
                        This ticket was closed by system verification after the run —
                        stock covers the order and every linked obligation is settled.
                        The team's own wording below may predate that check.
                      </div>
                    )}
                    <div className="answer">{run.answer}</div>
                    {run.unresolved && run.unresolved.length > 0 && (
                      <div className="missing">Unresolved: {run.unresolved.join("; ")}</div>
                    )}
                  </div>
                )}

                <div className="card">
                  <div className="section-title">Agent activity</div>
                  <AgentActivity records={activity} running={!!working} />
                </div>
                </div>

                <aside className="ticket-side">
                  <div className="card">
                    <Approvals
                      approvals={approvals}
                      approver={approver}
                      onApprover={setApprover}
                      onDone={refresh}
                      onFollowUp={adoptRun}
                      scope="ticket"
                      ticketId={ticket.id}
                    />
                  </div>
                </aside>
              </div>
            )}

            <div className="card">
              <Approvals
                approvals={approvals}
                approver={approver}
                onApprover={setApprover}
                onDone={refresh}
                onFollowUp={adoptRun}
              />
            </div>
          </main>
        </div>
      </div>
    </>
  );
}
