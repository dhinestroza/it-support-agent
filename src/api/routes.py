from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from src.agent.decision import Decision, DecisionEngine, build_ticket_query
from src.agent.retrieval import Retriever, Source
from src.api.dependencies import (
    get_decision_engine,
    get_repository,
    get_retriever,
)
from src.api.schemas import SourceOut, TicketRequest, TicketResponse
from src.db.models import status_for_action
from src.db.repository import Repository
from src.errors import SupportAgentError

logger = logging.getLogger(__name__)

router = APIRouter()

RepositoryDep = Annotated[Repository, Depends(get_repository)]
RetrieverDep = Annotated[Retriever, Depends(get_retriever)]
DecisionEngineDep = Annotated[DecisionEngine, Depends(get_decision_engine)]


def _to_sources_out(decision: Decision) -> list[SourceOut]:
    return [
        SourceOut(doc_id=source.doc_id, excerpt=source.excerpt)
        for source in decision.sources
    ]


def _retrieve_or_empty(
    retriever: Retriever, query: str, ticket_id: str
) -> list[Source]:
    try:
        return retriever.retrieve(query)
    except SupportAgentError:
        raise
    except Exception:  # noqa: BLE001
        logger.warning("retrieval failed for ticket %s", ticket_id, exc_info=True)
        return []


@router.post("/tickets")
def create_ticket(
    request: TicketRequest,
    repository: RepositoryDep,
    retriever: RetrieverDep,
    engine: DecisionEngineDep,
) -> TicketResponse:
    ticket = repository.create_ticket(request.subject, request.body)

    query = build_ticket_query(request.subject, request.body)
    sources = _retrieve_or_empty(retriever, query, ticket.id)
    decision = engine.decide(request.subject, request.body, sources)

    cited = _to_sources_out(decision)
    repository.save_decision(
        ticket.id,
        decision.action,
        decision.reasoning,
        decision.draft,
        [source.model_dump() for source in cited],
    )

    status = status_for_action(decision.action)
    if status != ticket.status:
        repository.update_ticket_status(ticket.id, status)

    return TicketResponse(
        ticket_id=ticket.id,
        action=decision.action,
        draft=decision.draft,
        sources=cited,
        reasoning=decision.reasoning,
    )
