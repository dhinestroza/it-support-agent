import type { TicketStatus, TicketAction } from "./types";

export const APP_NAME = "Soporte TI" as const;

export const STATUS_LABELS: Record<TicketStatus, string> = {
  pending: "Pendiente",
  resolved: "Resuelto",
  escalated: "Escalado",
};

export const ACTION_LABELS: Record<TicketAction, string> = {
  answer: "responder",
  ask: "preguntar",
  escalate: "escalar",
};

export const UNKNOWN_STATUS_LABEL = "Desconocido";

export const FIELD_LABELS = {
  status: "Estado",
  proposedAction: "Propuesta",
  sourceDocument: "Documento",
  decision: "Decisión del agente",
  reasoning: "Justificación",
  draft: "Borrador",
  body: "Descripción",
  sources: "Fuentes citadas",
} as const;

export const PAGE = {
  dashboardTitle: `Tickets · ${APP_NAME}`,
  dashboardHeading: "Tickets",
  detailTitle: `Ticket · ${APP_NAME}`,
  backToList: "← Volver a la lista",
} as const;

export const MESSAGES = {
  noDecision: "Este ticket aún no tiene una decisión registrada.",
  noTickets: "No hay tickets todavía.",
  apiError: "No se pudo cargar la información desde el servidor.",
  ticketNotFound: "No se encontró el ticket solicitado.",
  noSources: "No se recuperaron documentos para este ticket.",
} as const;
