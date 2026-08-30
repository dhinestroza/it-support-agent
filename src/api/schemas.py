from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MAX_SUBJECT_CHARS = 300
MAX_BODY_CHARS = 20_000

Action = Literal["answer", "ask", "escalate"]

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
