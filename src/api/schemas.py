from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MAX_SUBJECT_CHARS = 300
MAX_BODY_CHARS = 20_000

Action = Literal["answer", "ask", "escalate"]
TicketStatus = Literal["pending", "resolved", "escalated"]

Subject = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=MAX_SUBJECT_CHARS
    ),
]


class TicketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: Subject
    body: str = Field(max_length=MAX_BODY_CHARS)


class SourceOut(BaseModel):
    doc_id: str
    excerpt: str


class TicketResponse(BaseModel):
    ticket_id: str
    action: Action
    draft: str
    sources: list[SourceOut] = Field(default_factory=list)
    reasoning: str


class TicketSummary(BaseModel):
    ticket_id: str
    subject: str
    body_excerpt: str
    status: TicketStatus
    created_at: str
    action: Action | None = None


class TicketDetail(BaseModel):
    ticket_id: str
    subject: str
    body: str
    status: TicketStatus
    created_at: str
    action: Action | None = None
    reasoning: str | None = None
    draft: str | None = None
    sources: list[SourceOut] = Field(default_factory=list)
