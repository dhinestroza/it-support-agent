from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

TicketStatus = Literal["pending", "resolved", "escalated"]
DecisionAction = Literal["answer", "ask", "escalate"]

VALID_TICKET_STATUSES: tuple[TicketStatus, ...] = (
    "pending",
    "resolved",
    "escalated",
)
VALID_ACTIONS: tuple[DecisionAction, ...] = ("answer", "ask", "escalate")

DEFAULT_TICKET_STATUS: TicketStatus = "pending"


def status_for_action(action: DecisionAction) -> TicketStatus:
    return "escalated" if action == "escalate" else DEFAULT_TICKET_STATUS


@dataclass(frozen=True)
class Ticket:
    id: str
    subject: str
    body: str
    status: TicketStatus
    created_at: str


@dataclass(frozen=True)
class DecisionRecord:
    ticket_id: str
    action: DecisionAction
    reasoning: str
    drafted_response: str
    sources_used: list[dict[str, Any]]
    created_at: str


SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS tickets (
        id TEXT PRIMARY KEY,
        subject TEXT NOT NULL,
        body TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'resolved', 'escalated')),
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS decisions (
        ticket_id TEXT NOT NULL,
        action TEXT NOT NULL
            CHECK (action IN ('answer', 'ask', 'escalate')),
        reasoning TEXT NOT NULL,
        drafted_response TEXT NOT NULL,
        sources_used TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (ticket_id) REFERENCES tickets(id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_decisions_ticket_id
        ON decisions (ticket_id)
    """,
)

__all__ = [
    "DEFAULT_TICKET_STATUS",
    "SCHEMA_STATEMENTS",
    "VALID_ACTIONS",
    "VALID_TICKET_STATUSES",
    "DecisionAction",
    "DecisionRecord",
    "Ticket",
    "TicketStatus",
    "status_for_action",
]
