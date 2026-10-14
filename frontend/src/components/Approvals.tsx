import { useState } from "react";
import { api, type ApprovalResult } from "../api";
import type { ApprovalsResponse } from "../types";

interface Props {
  approvals: ApprovalsResponse | null;
  approver: string;
  onApprover: (name: string) => void;
  onDone: () => void;
  /** Called when a decision restarted the agents on a ticket. */
  onFollowUp: (runId: string, ticketId: number) => void;
  /**
   * "initial" — standing obligations that exist before any agent runs: unpaid
   * invoices and rent. These belong to the shop, not to a run.
   * "ticket"  — follow-ups an agent produced while working one ticket: drafted
   * orders, price proposals, customer drafts, deliveries to confirm.
   */
  scope?: "initial" | "ticket";
  ticketId?: number | null;
}

type Pending = { key: string; busy: boolean };

/**
 * The human approval queue. This is the only place in the whole system where
 * money moves — the agents prepare, a person clicks, and the backend executes.
 */
export function Approvals({
  approvals,
  approver,
  onApprover,
  onDone,
  onFollowUp,
  scope = "initial",
  ticketId = null,
}: Props) {
  const [pending, setPending] = useState<Pending | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  if (!approvals) return <div className="empty">Loading…</div>;

  const isInitial = scope === "initial";

  // Invoices and rent are the shop's own obligations — they exist whether or not
  // an agent ever runs, so they stay in the main queue. Proposals and deliveries
  // are produced by a run, so they belong beside the ticket that produced them.
  const invoices = isInitial ? approvals.payable_invoices : [];
  const rents = isInitial ? approvals.payable_rent : [];
  const proposals = isInitial
    ? approvals.proposals.filter((p) => p.ticket_id == null)
    : approvals.proposals.filter((p) => p.ticket_id === ticketId);
  const receipts = isInitial
    ? approvals.awaiting_receipt.filter((r) => r.ticket_id == null)
    : approvals.awaiting_receipt.filter((r) => r.ticket_id === ticketId);

  const nothing =
    proposals.length === 0 &&
    invoices.length === 0 &&
    rents.length === 0 &&
    receipts.length === 0;

  async function act(key: string, fn: () => Promise<ApprovalResult>, label: string) {
    if (!approver.trim()) {
      setError("Enter your name first — a payment cannot be recorded without an approver.");
      return;
    }
    setPending({ key, busy: true });
    setError(null);
    setDone(null);
    try {
      const result = await fn();
      setDone(label);
      onDone();
      // The backend puts the team straight back on the ticket this unblocked, so
      // the board follows that run instead of leaving the approval a dead end.
      const follow = result?.follow_up_run;
      if (follow) {
        setDone(`${label} The agents are picking up ticket ${follow.ticket_id} now.`);
        onFollowUp(follow.run_id, follow.ticket_id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPending(null);
    }
  }

  const busy = (key: string) => pending?.key === key && pending.busy;

  return (
    <div>
      <div className="section-title">
        {isInitial ? "Awaiting your approval" : `Awaiting your approval — ticket ${ticketId}`}
      </div>

      <div className="card" style={{ marginBottom: 12 }}>
        <label htmlFor="approver" style={{ fontSize: 12.5, color: "#4a4a4a" }}>
          Approving as
        </label>
        <div style={{ marginTop: 6 }}>
          <input
            id="approver"
            className="input"
            style={{ width: "100%" }}
            placeholder="Your name"
            value={approver}
            onChange={(e) => onApprover(e.target.value)}
          />
        </div>
        <div className="approval-note">
          Required. Every payment is recorded against the person who approved it.
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {done && <div className="success">{done}</div>}

      {nothing && (
        <div className="empty">
          {isInitial
            ? "Nothing is waiting on you."
            : "Nothing from the agents yet for this ticket."}
        </div>
      )}

      {invoices.map((inv) => (
        <div className="approval spends" key={`inv-${inv.invoice_id}`}>
          <div className="approval-head">
            <div>
              <strong>Pay invoice {inv.invoice_id}</strong>
              <div className="approval-note">
                {inv.vendor} · due {inv.due_date}
                {inv.description ? ` · ${inv.description}` : ""}
              </div>
            </div>
            <span className="approval-amount">${inv.amount.toLocaleString()}</span>
          </div>
          <div className="approval-note">
            Paying this unblocks {inv.vendor} for shipping.
          </div>
          <div className="approval-actions">
            <button
              className="btn btn-small"
              disabled={busy(`inv-${inv.invoice_id}`) || !inv.affordable}
              onClick={() =>
                act(
                  `inv-${inv.invoice_id}`,
                  () => api.approveInvoice(inv.invoice_id, approver),
                  `Invoice ${inv.invoice_id} paid — $${inv.amount.toLocaleString()}.`,
                )
              }
            >
              {busy(`inv-${inv.invoice_id}`) ? "Paying…" : "Approve payment"}
            </button>
            {!inv.affordable && <span className="round">Not enough cash</span>}
          </div>
        </div>
      ))}

      {rents.map((rent) => (
        <div className="approval spends" key={`rent-${rent.lease_id}`}>
          <div className="approval-head">
            <div>
              <strong>Pay rent — {rent.space}</strong>
              <div className="approval-note">
                {rent.landlord} · due {rent.due_date}
              </div>
            </div>
            <span className="approval-amount">${rent.amount.toLocaleString()}</span>
          </div>
          <div className="approval-actions">
            <button
              className="btn btn-small"
              disabled={busy(`rent-${rent.lease_id}`) || !rent.affordable}
              onClick={() =>
                act(
                  `rent-${rent.lease_id}`,
                  () => api.approveRent(rent.lease_id, approver),
                  `Rent paid — $${rent.amount.toLocaleString()}.`,
                )
              }
            >
              {busy(`rent-${rent.lease_id}`) ? "Paying…" : "Approve payment"}
            </button>
            {!rent.affordable && <span className="round">Not enough cash</span>}
          </div>
        </div>
      ))}

      {receipts.map((r) => (
        <div className="approval" key={`recv-${r.proposal_id}`}>
          <div className="approval-head">
            <div>
              <strong>Confirm delivery — {r.summary}</strong>
              <div className="approval-note">
                approved by {r.approved_by} · ordered {r.created_on}
                {r.ticket_id ? ` · ticket ${r.ticket_id}` : ""}
              </div>
            </div>
          </div>
          <div className="approval-note">
            Paid for, but not yet delivered. Confirm only once the goods have
            physically arrived — this is what adds them to stock.
          </div>
          <div className="approval-actions">
            <button
              className="btn btn-small btn-quiet"
              disabled={busy(`recv-${r.proposal_id}`)}
              onClick={() =>
                act(
                  `recv-${r.proposal_id}`,
                  () => api.receiveGoods(r.proposal_id, approver),
                  `Received ${r.qty} x ${r.sku} size ${r.size} — stock updated.`,
                )
              }
            >
              {busy(`recv-${r.proposal_id}`) ? "Recording…" : "Confirm delivery"}
            </button>
          </div>
        </div>
      ))}

      {proposals.map((p) => (
        <div className={`approval ${p.spends_cash ? "spends" : ""}`} key={`prop-${p.id}`}>
          <div className="approval-head">
            <div>
              <strong>{p.summary}</strong>
              <div className="approval-note">
                prepared by {p.created_by.replace(/_/g, " ")}
                {p.ticket_id ? ` · ticket ${p.ticket_id}` : ""}
              </div>
            </div>
            {p.spends_cash && p.amount != null && (
              <span className="approval-amount">${p.amount.toLocaleString()}</span>
            )}
          </div>
          <div className="approval-note">
            {p.kind === "restock_po" && "Approving places this order and spends the cash."}
            {p.kind === "price_override" && "Approving authorises this price. No cash moves."}
            {p.kind === "customer_draft" && "Approving releases the draft for you to send. Nothing is sent automatically."}
          </div>
          <div className="approval-actions">
            <button
              className={`btn btn-small ${p.spends_cash ? "" : "btn-quiet"}`}
              disabled={busy(`prop-${p.id}`) || (p.spends_cash && !p.affordable)}
              onClick={() =>
                act(
                  `prop-${p.id}`,
                  () => api.approveProposal(p.id, approver),
                  `Approved: ${p.summary}`,
                )
              }
            >
              {busy(`prop-${p.id}`) ? "Approving…" : "Approve"}
            </button>
            {p.spends_cash && !p.affordable && (
              <span className="round">Not enough cash</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
