import type { Ticket } from "../types";
import { StatusBadge, ticketState } from "./StatusBadge";

interface Props {
  tickets: Ticket[];
  selectedId: number | null;
  runningTicketId: number | null;
  onSelect: (id: number) => void;
}

const STATE_CLASS = {
  resolved: "state-ok",
  working: "state-busy",
  unresolved: "state-stop",
} as const;

export function TicketList({ tickets, selectedId, runningTicketId, onSelect }: Props) {
  return (
    <div>
      <div className="section-title">Tickets</div>
      {tickets.map((t) => {
        const state = ticketState(t, runningTicketId === t.id);
        const detail = t.sku
          ? `${t.sku} · size ${t.size} · qty ${t.qty}`
          : t.lease
            ? `${t.lease.space_name} · $${t.lease.monthly_rent.toLocaleString()}`
            : t.type;
        return (
          <button
            key={t.id}
            className={`ticket ${STATE_CLASS[state]} ${selectedId === t.id ? "selected" : ""}`}
            onClick={() => onSelect(t.id)}
            aria-pressed={selectedId === t.id}
          >
            <div className="ticket-top">
              <span className="ticket-id">#{t.id} · {t.type}</span>
              <StatusBadge state={state} />
            </div>
            <div className="ticket-subject">{t.subject}</div>
            <div className="ticket-meta">{t.requester} — {detail}</div>
          </button>
        );
      })}
    </div>
  );
}
