export type TicketStatus = "pending" | "resolved" | "escalated";

export type TicketAction = "answer" | "ask" | "escalate";

export interface Source {
  doc_id: string;
  excerpt: string;
}

export interface TicketDetail {
  ticket_id: string;
  subject: string;
  body: string;
  status: TicketStatus;
  created_at: string;
  action: TicketAction | null;
  reasoning: string | null;
  draft: string | null;
  sources: Source[];
}

export interface TicketSummary {
  ticket_id: string;
  subject: string;
  status: TicketStatus;
  created_at: string;
  action: TicketAction | null;
}
