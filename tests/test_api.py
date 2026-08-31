from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from src.agent.decision import (
    MAX_BODY_CHARS as DECISION_MAX_BODY_CHARS,
)
from src.agent.decision import (
    MAX_SUBJECT_CHARS as DECISION_MAX_SUBJECT_CHARS,
)
from src.agent.decision import (
    TRUNCATION_MARKER,
    DecisionEngine,
)
from src.agent.retrieval import Source
from src.api.dependencies import (
    get_decision_engine,
    get_repository,
    get_retriever,
)
from src.api.main import (
    DEFAULT_FRONTEND_ORIGINS,
    MAX_REQUEST_BYTES,
    _frontend_origins,
    _replay,
    app,
)
from src.db.repository import Repository, connect
from src.errors import (
    EmptyKnowledgeBaseError,
    LlmError,
    NotFoundError,
    ValidationError,
)

RESPONSE_KEYS = {"ticket_id", "action", "draft", "sources", "reasoning"}
SUMMARY_KEYS = {
    "ticket_id",
    "subject",
    "body_excerpt",
    "status",
    "created_at",
    "action",
}
# The detail payload carries the full body, never the list-only excerpt.
DETAIL_KEYS = (SUMMARY_KEYS - {"body_excerpt"}) | {
    "body",
    "reasoning",
    "draft",
    "sources",
}
EXCERPT_LIMIT = 140

PASSWORD_SOURCE = Source(
    doc_id="password-reset",
    section="Resetting your password",
    text="Password reset\n## Resetting your password\nOpen the self-service portal.",
    excerpt="Open the self-service portal.",
    score=0.82,
)
WEAK_SOURCE = Source(
    doc_id="hardware-request",
    section="Requesting hardware",
    text="Hardware request\n## Requesting hardware\nManagers approve purchases.",
    excerpt="Managers approve purchases.",
    score=0.10,
)


class FakeRetriever:
    def __init__(self, sources: list[Source]) -> None:
        self._sources = sources
        self.queries: list[str] = []

    def retrieve(self, query: str, k: int = 3) -> list[Source]:
        self.queries.append(query)
        return list(self._sources)


class ExplodingRetriever:
    def __init__(self, error: Exception) -> None:
        self._error = error
        self.calls = 0

    def retrieve(self, query: str, k: int = 3) -> list[Source]:
        self.calls += 1
        raise self._error


class BrokenRepository:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def create_ticket(self, subject: str, body: str) -> None:
        raise self._error


class ScriptedLlm:
    def __init__(self, *responses: str | Exception) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def __call__(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        index = min(len(self.calls) - 1, len(self._responses) - 1)
        response = self._responses[index]
        if isinstance(response, Exception):
            raise response
        return response


def llm_json(
    action: str,
    draft: str = "Here is what to do.",
    reasoning: str = "Covered by the knowledge base.",
    sources: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "action": action,
            "draft": draft,
            "reasoning": reasoning,
            "sources": sources or [],
        }
    )


@pytest.fixture
def db_path(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> str:
    """Point the app at a throwaway database file."""
    path = str(tmp_path / "test.db")
    monkeypatch.setenv("APP_DB_PATH", path)
    return path


@pytest.fixture
def repository(db_path: str) -> Iterator[Repository]:
    connection = connect(db_path)
    try:
        yield Repository(connection)
    finally:
        connection.close()


def build_client(retriever: Any, llm: Any) -> TestClient:
    app.dependency_overrides[get_retriever] = lambda: retriever
    app.dependency_overrides[get_decision_engine] = lambda: DecisionEngine(llm)
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def test_kb_matched_ticket_returns_answer_with_citation(db_path: str) -> None:
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(
        llm_json("answer", draft="Use the portal.", sources=["password-reset"])
    )
    with build_client(retriever, llm) as client:
        response = client.post(
            "/tickets",
            json={"subject": "Password reset", "body": "How do I reset my password?"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "answer"
    assert payload["draft"] == "Use the portal."
    assert payload["sources"][0]["doc_id"] == "password-reset"
    assert payload["sources"][0]["excerpt"] == "Open the self-service portal."
    assert set(payload["sources"][0]) == {"doc_id", "excerpt"}


def test_response_body_matches_the_contract_exactly(db_path: str) -> None:
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(llm_json("answer", sources=["password-reset"]))
    with build_client(retriever, llm) as client:
        payload = client.post(
            "/tickets",
            json={"subject": "Password reset", "body": "How do I reset my password?"},
        ).json()

    assert set(payload) == RESPONSE_KEYS
    assert isinstance(payload["ticket_id"], str)
    assert payload["ticket_id"]
    assert isinstance(payload["reasoning"], str)


def test_retriever_is_queried_with_subject_and_body(db_path: str) -> None:
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(llm_json("answer", sources=["password-reset"]))
    with build_client(retriever, llm) as client:
        client.post(
            "/tickets",
            json={"subject": "VPN down", "body": "It fails on my laptop every time."},
        )

    assert len(retriever.queries) == 1
    assert "VPN down" in retriever.queries[0]
    assert "It fails on my laptop every time." in retriever.queries[0]


def test_retrieval_query_is_capped_by_the_prompt_limits(db_path: str) -> None:
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(llm_json("answer", sources=["password-reset"]))
    with build_client(retriever, llm) as client:
        client.post(
            "/tickets",
            json={"subject": "s" * 300, "body": "b" * 19_000},
        )

    marker = len(TRUNCATION_MARKER)
    assert len(retriever.queries[0]) <= (
        DECISION_MAX_SUBJECT_CHARS + DECISION_MAX_BODY_CHARS + 2 * marker + 1
    )


def test_ticket_and_decision_are_persisted(
    db_path: str, repository: Repository
) -> None:
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(
        llm_json("answer", draft="Use the portal.", sources=["password-reset"])
    )
    with build_client(retriever, llm) as client:
        payload = client.post(
            "/tickets",
            json={"subject": "Password reset", "body": "How do I reset my password?"},
        ).json()

    ticket = repository.get_ticket(payload["ticket_id"])
    assert ticket.subject == "Password reset"
    assert ticket.body == "How do I reset my password?"

    decision = repository.get_decision_for_ticket(payload["ticket_id"])
    assert decision is not None
    assert decision.action == "answer"
    assert decision.drafted_response == "Use the portal."
    assert decision.sources_used == [
        {"doc_id": "password-reset", "excerpt": "Open the self-service portal."}
    ]


def test_empty_body_returns_ask_without_calling_the_llm(db_path: str) -> None:
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(llm_json("answer", sources=["password-reset"]))
    with build_client(retriever, llm) as client:
        response = client.post("/tickets", json={"subject": "Help", "body": ""})

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "ask"
    assert payload["draft"]
    assert llm.calls == []


def test_no_eligible_source_returns_escalate_with_empty_sources(
    db_path: str, repository: Repository
) -> None:
    retriever = FakeRetriever([WEAK_SOURCE])
    llm = ScriptedLlm(llm_json("escalate", draft="Routing to a human."))
    with build_client(retriever, llm) as client:
        response = client.post(
            "/tickets",
            json={
                "subject": "New laptop",
                "body": "Please buy me a new laptop for the design team.",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "escalate"
    assert payload["sources"] == []
    assert repository.get_ticket(payload["ticket_id"]).status == "escalated"


def test_repeated_llm_failure_returns_escalate_not_a_server_error(
    db_path: str, repository: Repository
) -> None:
    llm = ScriptedLlm(RuntimeError("boom"), RuntimeError("boom again"))
    with build_client(FakeRetriever([PASSWORD_SOURCE]), llm) as client:
        response = client.post(
            "/tickets",
            json={"subject": "Password reset", "body": "How do I reset my password?"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "escalate"
    assert len(llm.calls) == 2
    decision = repository.get_decision_for_ticket(payload["ticket_id"])
    assert decision is not None
    assert decision.action == "escalate"


def test_missing_subject_is_rejected(db_path: str) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        response = client.post("/tickets", json={"body": "My VPN is down."})

    assert response.status_code == 422


def test_oversized_body_is_rejected(db_path: str) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        response = client.post("/tickets", json={"subject": "Hi", "body": "x" * 20_001})

    assert response.status_code == 422


def test_whitespace_only_subject_is_rejected(db_path: str) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        response = client.post(
            "/tickets", json={"subject": "   ", "body": "My VPN is down."}
        )

    assert response.status_code == 422


def test_unknown_field_is_rejected(db_path: str) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        response = client.post(
            "/tickets",
            json={
                "subject": "VPN",
                "body": "My VPN is down.",
                "status": "resolved",
            },
        )

    assert response.status_code == 422


def test_subject_whitespace_is_stripped_before_persisting(
    db_path: str, repository: Repository
) -> None:
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(llm_json("answer", sources=["password-reset"]))
    with build_client(retriever, llm) as client:
        payload = client.post(
            "/tickets",
            json={
                "subject": "  Password reset  ",
                "body": "How do I reset my password?",
            },
        ).json()

    assert repository.get_ticket(payload["ticket_id"]).subject == "Password reset"


def test_domain_errors_are_mapped_to_http_status_codes(db_path: str) -> None:
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(llm_json("answer", sources=["password-reset"]))
    body = {"subject": "Password reset", "body": "How do I reset my password?"}

    for error, expected in (
        (NotFoundError("nope"), 404),
        (ValidationError("bad"), 422),
    ):
        app.dependency_overrides[get_repository] = lambda error=error: BrokenRepository(
            error
        )
        with build_client(retriever, llm) as client:
            response = client.post("/tickets", json=body)
        assert response.status_code == expected
        assert str(error) not in response.text


def test_retrieval_failure_escalates_instead_of_returning_500(
    db_path: str, repository: Repository
) -> None:
    retriever = ExplodingRetriever(RuntimeError("chroma is down"))
    llm = ScriptedLlm(llm_json("escalate", draft="Routing to a human."))
    with build_client(retriever, llm) as client:
        response = client.post(
            "/tickets",
            json={
                "subject": "VPN down",
                "body": "The VPN client fails to connect from home.",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "escalate"
    assert payload["sources"] == []
    assert retriever.calls == 1

    decision = repository.get_decision_for_ticket(payload["ticket_id"])
    assert decision is not None
    assert decision.action == "escalate"
    assert repository.get_ticket(payload["ticket_id"]).status == "escalated"


def test_retrieval_domain_error_still_propagates_to_the_handler(db_path: str) -> None:
    retriever = ExplodingRetriever(EmptyKnowledgeBaseError("kb is empty"))
    llm = ScriptedLlm(llm_json("escalate"))
    with build_client(retriever, llm) as client:
        response = client.post(
            "/tickets",
            json={
                "subject": "VPN down",
                "body": "The VPN client fails to connect from home.",
            },
        )

    assert response.status_code == 500
    assert "kb is empty" not in response.text


def test_oversized_request_is_rejected_before_reaching_the_agent(db_path: str) -> None:
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(llm_json("answer", sources=["password-reset"]))
    with build_client(retriever, llm) as client:
        response = client.post(
            "/tickets",
            json={"subject": "Password reset", "body": "How do I reset my password?"},
            headers={"Content-Length": str(MAX_REQUEST_BYTES + 1)},
        )

    assert response.status_code == 413
    assert response.json() == {"detail": "Request too large"}
    assert retriever.queries == []
    assert llm.calls == []


def test_buffered_body_is_replayed_once_then_the_channel_disconnects() -> None:
    receive = _replay(b'{"subject": "VPN"}')

    async def drain() -> list[dict[str, object]]:
        return [await receive(), await receive(), await receive()]

    messages = asyncio.run(drain())

    assert messages[0] == {
        "type": "http.request",
        "body": b'{"subject": "VPN"}',
        "more_body": False,
    }
    assert messages[1] == {"type": "http.disconnect"}
    assert messages[2] == {"type": "http.disconnect"}


def test_request_without_content_length_is_replayed_to_the_agent(db_path: str) -> None:
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(llm_json("answer", sources=["password-reset"]))
    body = json.dumps(
        {"subject": "Password reset", "body": "How do I reset my password?"}
    ).encode()
    with build_client(retriever, llm) as client:
        response = client.post(
            "/tickets",
            content=iter([body]),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 200
    assert response.json()["action"] == "answer"
    assert retriever.queries == ["Password reset\nHow do I reset my password?"]


def test_oversized_request_without_content_length_is_rejected(db_path: str) -> None:
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(llm_json("answer", sources=["password-reset"]))
    body = b"x" * (MAX_REQUEST_BYTES + 1)
    with build_client(retriever, llm) as client:
        response = client.post(
            "/tickets",
            content=iter([body]),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 413
    assert response.json() == {"detail": "Request too large"}
    assert retriever.queries == []
    assert llm.calls == []


def test_mapped_errors_are_logged_as_warnings(
    db_path: str, caplog: pytest.LogCaptureFixture
) -> None:
    app.dependency_overrides[get_repository] = lambda: BrokenRepository(
        ValidationError("bad")
    )
    with caplog.at_level(logging.DEBUG, logger="src.api.main"):
        with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
            response = client.post(
                "/tickets", json={"subject": "VPN", "body": "My VPN is down."}
            )

    assert response.status_code == 422
    records = [record for record in caplog.records if record.name == "src.api.main"]
    assert [record for record in records if record.levelno >= logging.ERROR] == []
    assert [record for record in records if record.levelno == logging.WARNING]


def test_unmapped_errors_are_logged_at_error_level(
    db_path: str, caplog: pytest.LogCaptureFixture
) -> None:
    app.dependency_overrides[get_repository] = lambda: BrokenRepository(
        LlmError("boom")
    )
    with caplog.at_level(logging.DEBUG, logger="src.api.main"):
        with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
            response = client.post(
                "/tickets", json={"subject": "VPN", "body": "My VPN is down."}
            )

    assert response.status_code == 500
    errors = [
        record
        for record in caplog.records
        if record.name == "src.api.main" and record.levelno >= logging.ERROR
    ]
    assert len(errors) == 1
    assert errors[0].exc_info is not None
    # The handler runs in a threadpool, where sys.exc_info() is empty, so the
    # exception must be passed explicitly or the traceback is silently lost.
    assert errors[0].exc_info[0] is LlmError
    assert errors[0].exc_info[2] is not None


def test_schema_validation_errors_do_not_echo_the_input(db_path: str) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        response = client.post(
            "/tickets",
            json={
                "subject": "VPN",
                "body": "My VPN is down.",
                "status": "leaked-value",
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request"}
    assert "leaked-value" not in response.text


def test_health_endpoint(db_path: str) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_tickets_is_empty_when_no_ticket_exists(db_path: str) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        response = client.get("/tickets")

    assert response.status_code == 200
    assert response.json() == []


def test_list_tickets_returns_newest_first_with_the_decided_action(
    db_path: str,
) -> None:
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(llm_json("answer", sources=["password-reset"]))
    with build_client(retriever, llm) as client:
        first = client.post(
            "/tickets",
            json={"subject": "Password reset", "body": "How do I reset my password?"},
        ).json()
        second = client.post(
            "/tickets",
            json={"subject": "VPN down", "body": "The VPN client fails to connect."},
        ).json()
        response = client.get("/tickets")

    assert response.status_code == 200
    payload = response.json()
    assert [item["ticket_id"] for item in payload] == [
        second["ticket_id"],
        first["ticket_id"],
    ]
    assert set(payload[0]) == SUMMARY_KEYS
    assert payload[0]["subject"] == "VPN down"
    assert payload[0]["status"] == "pending"
    assert payload[0]["created_at"]
    assert [item["action"] for item in payload] == ["answer", "answer"]


def test_list_tickets_exposes_a_null_action_without_a_decision(
    db_path: str, repository: Repository
) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        ticket = repository.create_ticket("Undecided", "Nothing has run yet.")
        response = client.get("/tickets")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert set(payload[0]) == SUMMARY_KEYS
    assert payload[0]["ticket_id"] == ticket.id
    assert payload[0]["subject"] == "Undecided"
    assert payload[0]["status"] == "pending"
    assert payload[0]["action"] is None


def test_list_tickets_exposes_an_escalated_ticket_and_its_action(
    db_path: str, repository: Repository
) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        ticket = repository.create_ticket("Laptop on fire", "Smoke is coming out.")
        repository.save_decision(
            ticket_id=ticket.id,
            action="escalate",
            reasoning="No KB coverage for hardware incidents.",
            drafted_response="Escalating to the hardware team.",
            sources_used=[],
        )
        repository.update_ticket_status(ticket.id, "escalated")
        response = client.get("/tickets")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["ticket_id"] == ticket.id
    assert payload[0]["status"] == "escalated"
    assert payload[0]["action"] == "escalate"


def test_list_tickets_includes_a_body_excerpt_for_every_item(db_path: str) -> None:
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(llm_json("answer", sources=["password-reset"]))
    with build_client(retriever, llm) as client:
        client.post(
            "/tickets",
            json={"subject": "Password reset", "body": "How do I reset my password?"},
        )
        response = client.get("/tickets")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload[0]) == SUMMARY_KEYS
    assert payload[0]["body_excerpt"] == "How do I reset my password?"


def test_list_tickets_truncates_a_long_body_excerpt_on_a_word_boundary(
    db_path: str,
) -> None:
    body = "The VPN client keeps dropping the connection from home every hour. " * 4
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(llm_json("answer", sources=["password-reset"]))
    with build_client(retriever, llm) as client:
        client.post("/tickets", json={"subject": "VPN down", "body": body})
        response = client.get("/tickets")

    assert response.status_code == 200
    excerpt = response.json()[0]["body_excerpt"]
    assert len(body) > EXCERPT_LIMIT
    assert excerpt.endswith("…")
    assert len(excerpt) <= EXCERPT_LIMIT + 1
    assert excerpt.split()[0] == body.split()[0]
    stem = excerpt.removesuffix("…")
    assert body.startswith(stem)
    # The cut lands on a word boundary, so the last kept word stays intact.
    assert body[len(stem)].isspace()


def test_list_tickets_excerpt_keeps_the_last_word_when_the_cut_lands_on_a_space(
    db_path: str, repository: Repository
) -> None:
    # The character at the limit is already a space, so no word is split and
    # the naive rfind(" ") backtrack would drop "final" for nothing.
    body = "word " * 27 + "final extra"
    assert body[EXCERPT_LIMIT] == " "
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        ticket = repository.create_ticket("Cut on a space", body)
        repository.save_decision(
            ticket_id=ticket.id,
            action="ask",
            reasoning="The cut lands on a space.",
            drafted_response="Could you add more detail?",
            sources_used=[],
        )
        response = client.get("/tickets")

    assert response.status_code == 200
    excerpt = response.json()[0]["body_excerpt"]
    assert excerpt == "word " * 27 + "final" + "…"


def test_list_tickets_excerpt_breaks_on_a_newline_boundary(
    db_path: str, repository: Repository
) -> None:
    body = "alpha\n" * 30
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        ticket = repository.create_ticket("Newline separated", body)
        repository.save_decision(
            ticket_id=ticket.id,
            action="ask",
            reasoning="The body has no spaces, only newlines.",
            drafted_response="Could you add more detail?",
            sources_used=[],
        )
        response = client.get("/tickets")

    assert response.status_code == 200
    excerpt = response.json()[0]["body_excerpt"]
    assert excerpt == "alpha\n" * 22 + "alpha" + "…"


def test_list_tickets_excerpt_hard_cuts_a_long_unbroken_word(
    db_path: str, repository: Repository
) -> None:
    body = "x" * 200
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        ticket = repository.create_ticket("No spaces", body)
        repository.save_decision(
            ticket_id=ticket.id,
            action="ask",
            reasoning="The body is one long token.",
            drafted_response="Could you rephrase the issue?",
            sources_used=[],
        )
        response = client.get("/tickets")

    assert response.status_code == 200
    excerpt = response.json()[0]["body_excerpt"]
    assert excerpt == "x" * EXCERPT_LIMIT + "…"
    assert len(excerpt) == EXCERPT_LIMIT + 1


def test_list_tickets_excerpt_keeps_a_body_of_exactly_the_limit_verbatim(
    db_path: str, repository: Repository
) -> None:
    body = "word " * 27 + "final"
    assert len(body) == EXCERPT_LIMIT
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        ticket = repository.create_ticket("Exactly at the limit", body)
        repository.save_decision(
            ticket_id=ticket.id,
            action="ask",
            reasoning="The body is exactly at the limit.",
            drafted_response="Could you add more detail?",
            sources_used=[],
        )
        response = client.get("/tickets")

    assert response.status_code == 200
    excerpt = response.json()[0]["body_excerpt"]
    assert excerpt == body
    assert "…" not in excerpt


def test_list_tickets_keeps_a_short_body_excerpt_verbatim(db_path: str) -> None:
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(llm_json("answer", sources=["password-reset"]))
    with build_client(retriever, llm) as client:
        client.post(
            "/tickets",
            json={"subject": "VPN down", "body": "  The VPN client fails.  "},
        )
        response = client.get("/tickets")

    assert response.status_code == 200
    excerpt = response.json()[0]["body_excerpt"]
    assert excerpt == "The VPN client fails."
    assert "…" not in excerpt


def test_list_tickets_returns_an_empty_body_excerpt_for_an_empty_body(
    db_path: str, repository: Repository
) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        ticket = repository.create_ticket("Undecided", "")
        repository.save_decision(
            ticket_id=ticket.id,
            action="ask",
            reasoning="The body is empty.",
            drafted_response="Could you describe the issue?",
            sources_used=[],
        )
        response = client.get("/tickets")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["ticket_id"] == ticket.id
    assert payload[0]["body_excerpt"] == ""


def test_get_ticket_returns_the_body_and_its_latest_decision(db_path: str) -> None:
    retriever = FakeRetriever([PASSWORD_SOURCE])
    llm = ScriptedLlm(
        llm_json(
            "answer",
            draft="Use the portal.",
            reasoning="The KB covers this.",
            sources=["password-reset"],
        )
    )
    with build_client(retriever, llm) as client:
        created = client.post(
            "/tickets",
            json={"subject": "Password reset", "body": "How do I reset my password?"},
        ).json()
        response = client.get(f"/tickets/{created['ticket_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == DETAIL_KEYS
    assert payload["ticket_id"] == created["ticket_id"]
    assert payload["subject"] == "Password reset"
    assert payload["body"] == "How do I reset my password?"
    assert payload["status"] == "pending"
    assert payload["created_at"]
    assert payload["action"] == "answer"
    assert payload["reasoning"] == "The KB covers this."
    assert payload["draft"] == "Use the portal."
    assert payload["sources"] == [
        {"doc_id": "password-reset", "excerpt": "Open the self-service portal."}
    ]


def test_get_ticket_without_a_decision_returns_nulls_and_no_sources(
    db_path: str, repository: Repository
) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        ticket = repository.create_ticket("Undecided", "Nothing has run yet.")
        response = client.get(f"/tickets/{ticket.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticket_id"] == ticket.id
    assert payload["body"] == "Nothing has run yet."
    assert payload["action"] is None
    assert payload["reasoning"] is None
    assert payload["draft"] is None
    assert payload["sources"] == []


def test_get_ticket_with_an_unknown_id_returns_404(db_path: str) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        response = client.get("/tickets/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found"}


def test_allowed_origin_gets_the_cors_header(db_path: str) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        response = client.get("/tickets", headers={"Origin": "http://localhost:4321"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4321"


def test_disallowed_origin_does_not_get_the_cors_header(db_path: str) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        response = client.get("/tickets", headers={"Origin": "http://evil.example"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_preflight_for_the_allowed_origin_permits_get(db_path: str) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        response = client.options(
            "/tickets",
            headers={
                "Origin": "http://localhost:4321",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4321"
    assert "GET" in response.headers["access-control-allow-methods"]


def test_preflight_does_not_advertise_write_methods(db_path: str) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        response = client.options(
            "/tickets",
            headers={
                "Origin": "http://localhost:4321",
                "Access-Control-Request-Method": "GET",
            },
        )

    allowed = response.headers["access-control-allow-methods"]
    assert "*" not in allowed
    assert "POST" not in allowed
    assert response.headers.get("access-control-allow-credentials") is None


def test_cors_is_the_outermost_middleware() -> None:
    # Starlette wraps the LAST added middleware outermost, so CORS must be able
    # to answer a preflight before the body-size guard consumes the request.
    assert app.user_middleware[0].cls is CORSMiddleware


def test_preflight_is_answered_before_the_request_size_guard(db_path: str) -> None:
    with build_client(FakeRetriever([]), ScriptedLlm(llm_json("ask"))) as client:
        response = client.options(
            "/tickets",
            headers={
                "Origin": "http://localhost:4321",
                "Access-Control-Request-Method": "GET",
                "Content-Length": str(MAX_REQUEST_BYTES + 1),
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4321"


def test_frontend_origins_defaults_to_the_local_astro_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FRONTEND_ORIGINS", raising=False)

    assert _frontend_origins() == list(DEFAULT_FRONTEND_ORIGINS)
    assert "*" not in DEFAULT_FRONTEND_ORIGINS


def test_frontend_origins_reads_the_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "FRONTEND_ORIGINS", " https://tickets.example , ,https://ops.example "
    )

    assert _frontend_origins() == ["https://tickets.example", "https://ops.example"]


def test_frontend_origins_falls_back_when_the_override_is_blank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FRONTEND_ORIGINS", "  , ")

    assert _frontend_origins() == list(DEFAULT_FRONTEND_ORIGINS)


def test_get_repository_yields_a_fresh_connection_and_closes_it(
    db_path: str,
) -> None:
    first_generator = get_repository()
    first = next(first_generator)
    second_generator = get_repository()
    second = next(second_generator)

    assert first is not second
    assert first._connection is not second._connection  # noqa: SLF001

    connection = first._connection  # noqa: SLF001
    with pytest.raises(StopIteration):
        next(first_generator)
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")

    with pytest.raises(StopIteration):
        next(second_generator)
