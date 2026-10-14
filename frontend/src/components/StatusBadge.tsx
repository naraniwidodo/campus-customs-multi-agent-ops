import type { Ticket } from "../types";

export type TicketState = "resolved" | "working" | "unresolved";

/** Green resolved, yellow while agents are working, red otherwise. */
export function ticketState(ticket: Ticket, running: boolean): TicketState {
  if (ticket.resolved) return "resolved";
  if (running) return "working";
  return "unresolved";
}

const LABEL: Record<TicketState, string> = {
  resolved: "Resolved",
  working: "Agents working",
  unresolved: "Not resolved",
};

const CLASS: Record<TicketState, string> = {
  resolved: "badge-ok",
  working: "badge-busy",
  unresolved: "badge-stop",
};

export function StatusBadge({ state }: { state: TicketState }) {
  return (
    <span className={`badge ${CLASS[state]}`}>
      <span className="dot" />
      {LABEL[state]}
    </span>
  );
}
