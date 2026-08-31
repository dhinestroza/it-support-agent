import type { TicketStatus, TicketAction } from "./types";

export const APP_NAME = "Soporte TI" as const;

/** Display name of the agent that authors the drafted reply. */
export const AGENT_NAME = "Asistente de soporte" as const;

/** Role line shown under the agent name in the decision message. */
export const AGENT_ROLE = "Respuesta propuesta" as const;

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
  agentDraft: "Borrador del agente",
  proposedActionLong: "Acción propuesta",
  notProvided: "Sin definir",
  reasoning: "Justificación",
  draft: "Borrador",
  body: "Descripción",
  sources: "Fuentes citadas",
  generatedOn: "Generado el",
} as const;

export const PAGE = {
  dashboardTitle: `Tickets · ${APP_NAME}`,
  dashboardHeading: "Tickets",
  navHome: "Inicio",
  navLabel: "Navegación principal",
  detailTitle: `Ticket · ${APP_NAME}`,
  backToList: "← Volver a la lista",
  breadcrumbSeparator: "›",
  breadcrumbLabel: "Ruta de navegación",
  summaryLabel: "Resumen del ticket",
} as const;

export const MESSAGES = {
  loading: "Cargando…",
  noDecision: "Este ticket aún no tiene una decisión registrada.",
  noTickets: "No hay tickets todavía.",
  apiError: "No se pudo cargar la información desde el servidor.",
  ticketNotFound: "No se encontró el ticket solicitado.",
  noSources: "No se recuperaron documentos para este ticket.",
} as const;
