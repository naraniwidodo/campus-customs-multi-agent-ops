/** Typed client for the operations API. Every call goes through the Vite proxy. */

import type {
  ActivityResponse,
  ApprovalsResponse,
  CashResponse,
  RunState,
  TicketsResponse,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    // The backend returns a readable reason in `detail` for every refusal —
    // insufficient cash, already paid, missing approver. Surface it as-is rather
    // than replacing it with a generic failure message.
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail =
          typeof body.detail === "string"
            ? body.detail
            : body.detail?.[0]?.msg ?? JSON.stringify(body.detail);
      }
    } catch {
      /* non-JSON error body; keep the status line */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

/** A human decision may kick the agents back onto the ticket it unblocked. */
export interface ApprovalResult extends Record<string, unknown> {
  follow_up_run?: { run_id: string; ticket_id: number; status: string } | null;
}

export const api = {
  tickets: () => request<TicketsResponse>("/tickets"),
  cash: () => request<CashResponse>("/cash"),
  approvals: () => request<ApprovalsResponse>("/approvals"),

  activity: (sinceId = 0, limit = 200, ticketId?: number) =>
    request<ActivityResponse>(
      `/activity?since_id=${sinceId}&limit=${limit}` +
        (ticketId != null ? `&ticket_id=${ticketId}` : ""),
    ),

  runTicket: (ticketId: number) =>
    request<{ run_id: string; ticket_id: number; status: string }>(
      `/tickets/${ticketId}/run`,
      { method: "POST" },
    ),

  run: (runId: string) => request<RunState>(`/runs/${runId}`),

  approveProposal: (id: number, approvedBy: string) =>
    request<ApprovalResult>(`/approve/proposal/${id}`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy }),
    }),

  approveInvoice: (id: number, approvedBy: string) =>
    request<ApprovalResult>(`/approve/invoice/${id}`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy }),
    }),

  approveRent: (id: number, approvedBy: string) =>
    request<ApprovalResult>(`/approve/rent/${id}`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy }),
    }),

  receiveGoods: (proposalId: number, receivedBy: string) =>
    request<ApprovalResult>(`/receive/${proposalId}`, {
      method: "POST",
      body: JSON.stringify({ received_by: receivedBy }),
    }),

  reset: () => request<Record<string, unknown>>("/reset", { method: "POST" }),
};
