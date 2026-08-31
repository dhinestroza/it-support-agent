from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest

from src.db.models import (
    VALID_ACTIONS,
    VALID_TICKET_STATUSES,
    DecisionRecord,
    Ticket,
)
from src.db.repository import Repository, connect, create_schema
from src.errors import NotFoundError, ValidationError

SQL_INJECTION_PAYLOAD = "'; DROP TABLE tickets;--"
UNICODE_PAYLOAD = "contraseña 密码"


class FakeClock:
    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 1, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        now = self._now
        self._now += timedelta(seconds=1)
        return now


class FrozenClock:
    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 1, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self._now


@pytest.fixture
def connection() -> Iterator[sqlite3.Connection]:
    conn = connect(":memory:")
    create_schema(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def repository(connection: sqlite3.Connection) -> Repository:
    return Repository(connection, clock=FakeClock())


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = ?", ("table",)
    ).fetchall()
    return {row[0] for row in rows}


def test_create_schema_creates_both_tables(
    connection: sqlite3.Connection,
) -> None:
    assert {"tickets", "decisions"} <= _table_names(connection)


def test_create_schema_is_idempotent(connection: sqlite3.Connection) -> None:
    create_schema(connection)

    assert {"tickets", "decisions"} <= _table_names(connection)


def test_connect_enables_foreign_keys() -> None:
    conn = connect(":memory:")
    try:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conn.close()


def test_repository_rejects_a_connection_without_foreign_keys() -> None:
    conn = connect(":memory:")
    create_schema(conn)
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        clock = FakeClock()

        with pytest.raises(ValidationError):
            Repository(conn, clock=clock)
    finally:
        conn.close()


def test_repository_accepts_a_connection_built_by_connect() -> None:
    conn = connect(":memory:")
    create_schema(conn)
    try:
        repository = Repository(conn, clock=FakeClock())

        ticket = repository.create_ticket("Subject", "Body long enough")

        assert repository.get_ticket(ticket.id) == ticket
    finally:
        conn.close()


def test_schema_defaults_the_ticket_status_to_pending(
    connection: sqlite3.Connection, repository: Repository
) -> None:
    connection.execute(
        "INSERT INTO tickets (id, subject, body, created_at) VALUES (?, ?, ?, ?)",
        ("no-status", "Subject", "Body long enough", "2026-01-01T00:00:00+00:00"),
    )

    assert repository.get_ticket("no-status").status == "pending"


def test_schema_accepts_every_valid_ticket_status(
    connection: sqlite3.Connection, repository: Repository
) -> None:
    ticket = repository.create_ticket("Subject", "Body long enough")

    for status in VALID_TICKET_STATUSES:
        connection.execute(
            "UPDATE tickets SET status = ? WHERE id = ?", (status, ticket.id)
        )
        assert repository.get_ticket(ticket.id).status == status


def test_schema_rejects_an_unknown_ticket_status(
    connection: sqlite3.Connection, repository: Repository
) -> None:
    ticket = repository.create_ticket("Subject", "Body long enough")

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "UPDATE tickets SET status = ? WHERE id = ?", ("deleted", ticket.id)
        )


def test_schema_accepts_every_valid_decision_action(
    connection: sqlite3.Connection, repository: Repository
) -> None:
    ticket = repository.create_ticket("Subject", "Body long enough")

    for action in VALID_ACTIONS:
        connection.execute("DELETE FROM decisions WHERE ticket_id = ?", (ticket.id,))
        connection.execute(
            "INSERT INTO decisions "
            "(ticket_id, action, reasoning, drafted_response, sources_used, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (ticket.id, action, "why", "draft", "[]", "2026-01-01T00:00:00"),
        )
        stored = repository.get_decision_for_ticket(ticket.id)
        assert stored is not None
        assert stored.action == action


def test_schema_rejects_an_unknown_decision_action(
    connection: sqlite3.Connection, repository: Repository
) -> None:
    ticket = repository.create_ticket("Subject", "Body long enough")

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO decisions "
            "(ticket_id, action, reasoning, drafted_response, sources_used, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (ticket.id, "send", "why", "draft", "[]", "2026-01-01T00:00:00"),
        )


def test_create_ticket_returns_a_pending_ticket_with_an_id(
    repository: Repository,
) -> None:
    ticket = repository.create_ticket("VPN down", "I cannot connect to the VPN")

    assert isinstance(ticket, Ticket)
    assert ticket.id
    assert ticket.status == "pending"
    assert ticket.created_at


def test_create_ticket_generates_distinct_ids(repository: Repository) -> None:
    first = repository.create_ticket("One", "Body one")
    second = repository.create_ticket("Two", "Body two")

    assert first.id != second.id


def test_get_ticket_round_trips_subject_and_body(
    repository: Repository,
) -> None:
    created = repository.create_ticket("Password reset", "I forgot my password")

    stored = repository.get_ticket(created.id)

    assert stored == created
    assert stored.subject == "Password reset"
    assert stored.body == "I forgot my password"


def test_get_ticket_raises_not_found_for_an_unknown_id(
    repository: Repository,
) -> None:
    with pytest.raises(NotFoundError):
        repository.get_ticket("does-not-exist")


def test_list_tickets_returns_newest_first(repository: Repository) -> None:
    first = repository.create_ticket("Oldest", "Body one")
    second = repository.create_ticket("Middle", "Body two")
    third = repository.create_ticket("Newest", "Body three")

    listed = repository.list_tickets()

    assert [ticket.id for ticket in listed] == [third.id, second.id, first.id]


def test_list_tickets_is_empty_on_a_fresh_database(
    repository: Repository,
) -> None:
    assert repository.list_tickets() == []


def test_update_ticket_status_persists(repository: Repository) -> None:
    ticket = repository.create_ticket("Laptop request", "I need a new laptop")

    repository.update_ticket_status(ticket.id, "escalated")

    assert repository.get_ticket(ticket.id).status == "escalated"


def test_update_ticket_status_rejects_an_invalid_status(
    repository: Repository,
) -> None:
    ticket = repository.create_ticket("Laptop request", "I need a new laptop")

    with pytest.raises(ValidationError):
        repository.update_ticket_status(ticket.id, "deleted")  # type: ignore[arg-type]

    assert repository.get_ticket(ticket.id).status == "pending"


def test_update_ticket_status_raises_not_found_for_an_unknown_ticket(
    repository: Repository,
) -> None:
    with pytest.raises(NotFoundError):
        repository.update_ticket_status("does-not-exist", "resolved")


def test_save_decision_round_trips_sources_as_a_python_list(
    repository: Repository,
) -> None:
    ticket = repository.create_ticket("Password reset", "I forgot my password")
    sources = [
        {"doc_id": "password-reset", "excerpt": "Use the self-service portal."},
        {"doc_id": "vpn-issues", "excerpt": "Reconnect the VPN client."},
    ]

    saved = repository.save_decision(
        ticket_id=ticket.id,
        action="answer",
        reasoning="The KB covers password resets.",
        drafted_response="Reset it from the self-service portal.",
        sources_used=sources,
    )

    stored = repository.get_decision_for_ticket(ticket.id)
    assert isinstance(saved, DecisionRecord)
    assert stored == saved
    assert stored is not None
    assert stored.action == "answer"
    assert stored.reasoning == "The KB covers password resets."
    assert stored.drafted_response == "Reset it from the self-service portal."
    assert stored.sources_used == sources
    assert isinstance(stored.sources_used, list)


def test_save_decision_stores_sources_used_as_json(
    connection: sqlite3.Connection, repository: Repository
) -> None:
    ticket = repository.create_ticket("Password reset", "I forgot my password")
    sources = [{"doc_id": "password-reset", "excerpt": "Use the portal."}]

    repository.save_decision(
        ticket_id=ticket.id,
        action="answer",
        reasoning="Covered by the KB.",
        drafted_response="Use the portal.",
        sources_used=sources,
    )

    raw = connection.execute(
        "SELECT sources_used FROM decisions WHERE ticket_id = ?", (ticket.id,)
    ).fetchone()[0]
    assert isinstance(raw, str)
    assert json.loads(raw) == sources


def test_save_decision_accepts_an_empty_source_list(
    repository: Repository,
) -> None:
    ticket = repository.create_ticket("New laptop", "Please buy me a laptop")

    saved = repository.save_decision(
        ticket_id=ticket.id,
        action="escalate",
        reasoning="Purchases are out of scope.",
        drafted_response="Escalating to a human agent.",
        sources_used=[],
    )

    assert saved.sources_used == []


def test_save_decision_rejects_an_action_outside_the_domain_values(
    repository: Repository,
) -> None:
    ticket = repository.create_ticket("Password reset", "I forgot my password")

    with pytest.raises(ValidationError):
        repository.save_decision(
            ticket_id=ticket.id,
            action="send",  # type: ignore[arg-type]
            reasoning="Should never be stored.",
            drafted_response="Should never be stored.",
            sources_used=[],
        )

    assert repository.get_decision_for_ticket(ticket.id) is None


def test_save_decision_fails_for_an_unknown_ticket(
    repository: Repository,
) -> None:
    with pytest.raises(NotFoundError):
        repository.save_decision(
            ticket_id="does-not-exist",
            action="answer",
            reasoning="Orphan decision.",
            drafted_response="Orphan decision.",
            sources_used=[],
        )


def test_save_decision_does_not_relabel_a_genuine_integrity_error(
    repository: Repository,
) -> None:
    ticket = repository.create_ticket("VPN down", "I cannot connect")

    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        repository.save_decision(
            ticket_id=ticket.id,
            action="answer",
            reasoning=None,
            drafted_response="x",
            sources_used=[],
        )

    assert not isinstance(exc_info.value, NotFoundError)
    assert repository.get_decision_for_ticket(ticket.id) is None


def test_save_decision_rejects_sources_that_are_not_json_serializable(
    repository: Repository,
) -> None:
    ticket = repository.create_ticket("VPN down", "I cannot connect")
    unserializable_sources = [{"excerpt": object()}]

    with pytest.raises(ValidationError):
        repository.save_decision(
            ticket_id=ticket.id,
            action="answer",
            reasoning="Should never be stored.",
            drafted_response="Should never be stored.",
            sources_used=unserializable_sources,
        )

    assert repository.get_decision_for_ticket(ticket.id) is None


@pytest.mark.parametrize(
    "raw_sources",
    [
        "not json",
        '{"a": 1}',
        "[1, 2]",
        '[{"doc_id": "x"}]',
        '[{"excerpt": "x"}]',
        '[{"doc_id": 1, "excerpt": "x"}]',
        '[{"doc_id": "x", "excerpt": null}]',
    ],
    ids=[
        "invalid-json",
        "json-object-not-list",
        "list-of-non-objects",
        "source-missing-excerpt",
        "source-missing-doc-id",
        "source-with-non-str-doc-id",
        "source-with-non-str-excerpt",
    ],
)
def test_get_decision_for_ticket_rejects_a_corrupt_sources_blob(
    connection: sqlite3.Connection, repository: Repository, raw_sources: str
) -> None:
    ticket = repository.create_ticket("VPN down", "I cannot connect")
    connection.execute(
        "INSERT INTO decisions "
        "(ticket_id, action, reasoning, drafted_response, sources_used, "
        "created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            ticket.id,
            "answer",
            "why",
            "draft",
            raw_sources,
            "2026-01-01T00:00:00+00:00",
        ),
    )

    with pytest.raises(ValidationError):
        repository.get_decision_for_ticket(ticket.id)


def test_get_decision_for_ticket_returns_none_when_absent(
    repository: Repository,
) -> None:
    ticket = repository.create_ticket("VPN down", "I cannot connect")

    assert repository.get_decision_for_ticket(ticket.id) is None


def test_get_decision_for_ticket_returns_the_latest_decision(
    repository: Repository,
) -> None:
    ticket = repository.create_ticket("VPN down", "I cannot connect")
    repository.save_decision(
        ticket_id=ticket.id,
        action="ask",
        reasoning="Missing the OS and the error message.",
        drafted_response="Which OS and error do you see?",
        sources_used=[],
    )
    repository.save_decision(
        ticket_id=ticket.id,
        action="escalate",
        reasoning="Still unresolved after the follow-up.",
        drafted_response="Escalating to a human agent.",
        sources_used=[],
    )

    stored = repository.get_decision_for_ticket(ticket.id)

    assert stored is not None
    assert stored.action == "escalate"


def test_list_tickets_breaks_equal_timestamps_by_insertion_order(
    connection: sqlite3.Connection,
) -> None:
    repository = Repository(connection, clock=FrozenClock())

    first = repository.create_ticket("Oldest", "Body one")
    second = repository.create_ticket("Newest", "Body two")

    listed = repository.list_tickets()

    assert first.created_at == second.created_at
    assert [ticket.id for ticket in listed] == [second.id, first.id]


def test_get_decision_for_ticket_breaks_equal_timestamps_by_insertion_order(
    connection: sqlite3.Connection,
) -> None:
    repository = Repository(connection, clock=FrozenClock())
    ticket = repository.create_ticket("VPN down", "I cannot connect")
    earlier = repository.save_decision(
        ticket_id=ticket.id,
        action="ask",
        reasoning="Missing the OS and the error message.",
        drafted_response="Which OS and error do you see?",
        sources_used=[],
    )
    later = repository.save_decision(
        ticket_id=ticket.id,
        action="escalate",
        reasoning="Still unresolved after the follow-up.",
        drafted_response="Escalating to a human agent.",
        sources_used=[],
    )

    stored = repository.get_decision_for_ticket(ticket.id)

    assert earlier.created_at == later.created_at
    assert stored == later
    assert stored is not None
    assert stored.action == "escalate"


def test_unicode_text_round_trips_unchanged(repository: Repository) -> None:
    ticket = repository.create_ticket(UNICODE_PAYLOAD, f"body {UNICODE_PAYLOAD}")
    repository.save_decision(
        ticket_id=ticket.id,
        action="answer",
        reasoning=UNICODE_PAYLOAD,
        drafted_response=UNICODE_PAYLOAD,
        sources_used=[{"doc_id": "password-reset", "excerpt": UNICODE_PAYLOAD}],
    )

    stored_ticket = repository.get_ticket(ticket.id)
    stored_decision = repository.get_decision_for_ticket(ticket.id)

    assert stored_ticket.subject == UNICODE_PAYLOAD
    assert stored_ticket.body == f"body {UNICODE_PAYLOAD}"
    assert stored_decision is not None
    assert stored_decision.reasoning == UNICODE_PAYLOAD
    assert stored_decision.sources_used[0]["excerpt"] == UNICODE_PAYLOAD


def test_sql_metacharacters_are_stored_verbatim(
    connection: sqlite3.Connection, repository: Repository
) -> None:
    ticket = repository.create_ticket(
        SQL_INJECTION_PAYLOAD, f"body {SQL_INJECTION_PAYLOAD}"
    )

    stored = repository.get_ticket(ticket.id)

    assert stored.subject == SQL_INJECTION_PAYLOAD
    assert stored.body == f"body {SQL_INJECTION_PAYLOAD}"
    assert {"tickets", "decisions"} <= _table_names(connection)
    assert len(repository.list_tickets()) == 1


def test_sql_metacharacters_in_a_decision_are_stored_verbatim(
    connection: sqlite3.Connection, repository: Repository
) -> None:
    ticket = repository.create_ticket("Subject", "Body long enough")

    repository.save_decision(
        ticket_id=ticket.id,
        action="ask",
        reasoning=SQL_INJECTION_PAYLOAD,
        drafted_response=SQL_INJECTION_PAYLOAD,
        sources_used=[{"doc_id": "kb", "excerpt": SQL_INJECTION_PAYLOAD}],
    )

    stored = repository.get_decision_for_ticket(ticket.id)

    assert stored is not None
    assert stored.reasoning == SQL_INJECTION_PAYLOAD
    assert stored.drafted_response == SQL_INJECTION_PAYLOAD
    assert stored.sources_used[0]["excerpt"] == SQL_INJECTION_PAYLOAD
    assert {"tickets", "decisions"} <= _table_names(connection)
