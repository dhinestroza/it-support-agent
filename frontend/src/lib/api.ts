import type { Source, TicketDetail, TicketSummary } from "./types";
import { STATUS_LABELS, ACTION_LABELS } from "./labels";


const DEFAULT_API_BASE = "http://localhost:8000";

const configured = import.meta.env.PUBLIC_API_BASE_URL?.trim();
const RAW_API_BASE: string = configured ? configured : DEFAULT_API_BASE;

const API_BASE = RAW_API_BASE.replace(/\/+$/, "");

export type LoadResult<T> =
  | { ok: true; data: T }
  | { ok: false; reason: "not-found" | "error" };

function isTicketSummary(value: unknown): value is TicketSummary {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.ticket_id === "string" &&
    typeof candidate.subject === "string" &&
    typeof candidate.created_at === "string" &&
    typeof candidate.status === "string" &&
    candidate.status in STATUS_LABELS &&
    (candidate.action === null ||
      (typeof candidate.action === "string" && candidate.action in ACTION_LABELS))
  );
}

export async function fetchTickets(): Promise<LoadResult<TicketSummary[]>> {
  try {
    const response = await fetch(`${API_BASE}/tickets`);
    if (!response.ok) {
      console.warn(`[api] GET /tickets responded ${response.status}`);
      return { ok: false, reason: "error" };
    }
    const payload: unknown = await response.json();
    if (!Array.isArray(payload)) {
      console.warn("[api] GET /tickets payload is not an array");
      return { ok: false, reason: "error" };
    }
    return { ok: true, data: payload.filter(isTicketSummary) };
  } catch (error) {
    console.warn(`[api] GET /tickets failed: ${String(error)}`);
    return { ok: false, reason: "error" };
  }
}

export async function fetchTicketIds(): Promise<string[]> {
  const result = await fetchTickets();
  return result.ok ? result.data.map((ticket) => ticket.ticket_id) : [];
}

function isSource(value: unknown): value is Source {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.doc_id === "string" && typeof candidate.excerpt === "string"
  );
}

function isTicketDetail(value: unknown): value is TicketDetail {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.ticket_id === "string" &&
    typeof candidate.subject === "string" &&
    typeof candidate.body === "string" &&
    typeof candidate.created_at === "string" &&
    typeof candidate.status === "string" &&
    candidate.status in STATUS_LABELS &&
    (candidate.action === null ||
      (typeof candidate.action === "string" &&
        candidate.action in ACTION_LABELS)) &&
    (candidate.reasoning === null || typeof candidate.reasoning === "string") &&
    (candidate.draft === null || typeof candidate.draft === "string") &&
    Array.isArray(candidate.sources) &&
    candidate.sources.every(isSource)
  );
}

export async function fetchTicketDetail(
  id: string,
): Promise<LoadResult<TicketDetail>> {
  const path = `/tickets/${encodeURIComponent(id)}`;
  try {
    const response = await fetch(`${API_BASE}${path}`);
    if (response.status === 404) {
      console.warn(`[api] GET ${path} responded 404`);
      return { ok: false, reason: "not-found" };
    }
    if (!response.ok) {
      console.warn(`[api] GET ${path} responded ${response.status}`);
      return { ok: false, reason: "error" };
    }
    const payload: unknown = await response.json();
    if (!isTicketDetail(payload)) {
      console.warn(`[api] GET ${path} payload has an unexpected shape`);
      return { ok: false, reason: "error" };
    }
    return { ok: true, data: payload };
  } catch (error) {
    console.warn(`[api] GET ${path} failed: ${String(error)}`);
    return { ok: false, reason: "error" };
  }
}
