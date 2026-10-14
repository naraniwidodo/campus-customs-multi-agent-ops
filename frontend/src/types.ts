/** Shapes returned by the Campus Customs operations API. */

export type TicketStatus = "open" | "pending" | "blocked" | "closed";

export interface Proposal {
  id: number;
  kind: "restock_po" | "price_override" | "customer_draft" | "vendor_suggestion";
  status: string;
  summary: string;
  amount: number | null;
  approved_by: string | null;
  created_by: string;
}

export interface Invoice {
  id: number;
  vendor_id: number;
  vendor_name: string | null;
  amount: number;
  due_date: string;
  status: string;
  description: string | null;
  lead_days: number | null;
}

export interface Lease {
  id: number;
  space_name: string;
  landlord: string;
  monthly_rent: number;
  next_due: string;
}

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  status: TicketStatus;
  notes: string | null;
  created_at: string;
  resolved: boolean;
  closed_by: "agent" | "system" | null;
  invoice: Invoice | null;
  lease: Lease | null;
  proposals: Proposal[];
}

export interface TicketsResponse {
  as_of: string;
  total: number;
  open: number;
  resolved: number;
  tickets: Ticket[];
}

export interface Payment {
  id: number;
  kind: string;
  ref_id: number | null;
  amount: number;
  account: string;
  paid_at: string;
  approved_by: string;
}

export interface CashResponse {
  as_of: string;
  checking: number;
  open_invoice_total: number;
  rent_due_total: number;
  total_obligations: number;
  cash_after_obligations: number;
  can_meet_all_obligations: boolean;
  total_spent: number;
  payments: Payment[];
}

export interface ToolUse {
  tool: string;
  arguments: Record<string, unknown> | null;
  ok: boolean | null;
}

export interface ActivityRecord {
  record_id: number;
  run_id: string;
  recorded_at: string;
  shop_date: string;
  event: string;
  iteration: number | null;
  agent: string | null;
  message: string | null;
  answered: boolean | null;
  missing: string[];
  tools_used: ToolUse[];
  draft_message: string | null;
}

export interface ActivityResponse {
  records: ActivityRecord[];
  latest_id: number;
  total: number;
}

export interface RunState {
  run_id: string;
  ticket_id: number;
  status: "queued" | "running" | "finished" | "failed";
  iterations?: number;
  delegations?: number;
  agents_consulted?: string[];
  answer?: string;
  sufficient?: boolean;
  unresolved?: string[];
  error?: string;
}

export interface PendingProposal extends Proposal {
  ticket_id: number | null;
  spends_cash: boolean;
  affordable: boolean;
  details?: Record<string, unknown>;
}

export interface PayableInvoice {
  invoice_id: number;
  vendor: string | null;
  amount: number;
  due_date: string;
  description: string | null;
  affordable: boolean;
}

export interface PayableRent {
  lease_id: number;
  space: string;
  landlord: string;
  amount: number;
  due_date: string;
  affordable: boolean;
}

export interface AwaitingReceipt {
  proposal_id: number;
  ticket_id: number | null;
  summary: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  approved_by: string;
  created_on: string;
}

export interface ApprovalsResponse {
  as_of: string;
  cash: number;
  proposals: PendingProposal[];
  payable_invoices: PayableInvoice[];
  payable_rent: PayableRent[];
  awaiting_receipt: AwaitingReceipt[];
  total_pending: number;
}
