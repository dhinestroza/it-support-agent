from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, cast

from src.db.models import (
    DEFAULT_TICKET_STATUS,
    SCHEMA_STATEMENTS,
    VALID_ACTIONS,
    VALID_TICKET_STATUSES,
    DecisionAction,
    DecisionRecord,
    Ticket,
    TicketStatus,
)
from src.errors import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def enable_foreign_keys(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")


def connect(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    enable_foreign_keys(connection)
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    enable_foreign_keys(connection)
    with connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)


def _new_ticket_id() -> str:
    return uuid.uuid4().hex


def _dump_sources(sources_used: Sequence[Mapping[str, Any]]) -> str:
    try:
        return json.dumps(list(sources_used))
    except (TypeError, ValueError) as error:
        logger.warning("Rejected a non-JSON-serializable sources_used value")
        raise ValidationError("sources_used is not JSON-serializable") from error


def _load_sources(raw: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        logger.exception("Stored sources_used is not valid JSON", exc_info=True)
        raise ValidationError("Stored sources_used is not valid JSON") from error
    if not isinstance(payload, list):
        raise ValidationError("Stored sources_used is not a JSON list")
    if not all(isinstance(element, Mapping) for element in payload):
        raise ValidationError("Stored sources_used has a non-object element")
    if not all(_is_valid_source(element) for element in payload):
        raise ValidationError("Stored sources_used has a malformed source object")
    return cast(list[dict[str, Any]], payload)


def _is_valid_source(source: Mapping[str, Any]) -> bool:
    return all(isinstance(source.get(key), str) for key in ("doc_id", "excerpt"))


def _to_ticket(row: sqlite3.Row) -> Ticket:
    return Ticket(
        id=str(row["id"]),
        subject=str(row["subject"]),
        body=str(row["body"]),
        status=cast(TicketStatus, row["status"]),
        created_at=str(row["created_at"]),
    )


def _to_decision(row: sqlite3.Row) -> DecisionRecord:
    return DecisionRecord(
        ticket_id=str(row["ticket_id"]),
        action=cast(DecisionAction, row["action"]),
        reasoning=str(row["reasoning"]),
        drafted_response=str(row["drafted_response"]),
        sources_used=_load_sources(str(row["sources_used"])),
        created_at=str(row["created_at"]),
    )


class Repository:
    def __init__(
        self, connection: sqlite3.Connection, *, clock: Clock = utc_now
    ) -> None:
        pragma_row = connection.execute("PRAGMA foreign_keys").fetchone()
        if pragma_row is None or pragma_row[0] != 1:
            raise ValidationError("Connection must have foreign_keys enabled")
        self._connection = connection
        self._clock = clock

    def create_ticket(self, subject: str, body: str) -> Ticket:
        ticket = Ticket(
            id=_new_ticket_id(),
            subject=subject,
            body=body,
            status=DEFAULT_TICKET_STATUS,
            created_at=self._now(),
        )
        with self._connection:
            self._connection.execute(
                "INSERT INTO tickets "
                "(id, subject, body, status, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    ticket.id,
                    ticket.subject,
                    ticket.body,
                    ticket.status,
                    ticket.created_at,
                ),
            )
        return ticket

    def get_ticket(self, ticket_id: str) -> Ticket:
        row = self._connection.execute(
            "SELECT id, subject, body, status, created_at FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError(f"No ticket with id {ticket_id!r}")
        return _to_ticket(row)

    def list_tickets(self) -> list[Ticket]:
        rows = self._connection.execute(
            "SELECT id, subject, body, status, created_at FROM tickets "
            "ORDER BY created_at DESC, rowid DESC"
        ).fetchall()
        return [_to_ticket(row) for row in rows]

    def update_ticket_status(self, ticket_id: str, status: TicketStatus) -> None:
        if status not in VALID_TICKET_STATUSES:
            raise ValidationError(f"Unsupported ticket status: {status!r}")
        with self._connection:
            cursor = self._connection.execute(
                "UPDATE tickets SET status = ? WHERE id = ?",
                (status, ticket_id),
            )
        if cursor.rowcount == 0:
            raise NotFoundError(f"No ticket with id {ticket_id!r}")

    def save_decision(
        self,
        ticket_id: str,
        action: DecisionAction,
        reasoning: str,
        drafted_response: str,
        sources_used: Sequence[Mapping[str, Any]],
    ) -> DecisionRecord:
        if action not in VALID_ACTIONS:
            raise ValidationError(f"Unsupported decision action: {action!r}")
        if not self._ticket_exists(ticket_id):
            logger.warning("Rejected decision for unknown ticket %r", ticket_id)
            raise NotFoundError(f"No ticket with id {ticket_id!r}")

        record = DecisionRecord(
            ticket_id=ticket_id,
            action=action,
            reasoning=reasoning,
            drafted_response=drafted_response,
            sources_used=[dict(source) for source in sources_used],
            created_at=self._now(),
        )
        encoded_sources = _dump_sources(record.sources_used)
        with self._connection:
            self._connection.execute(
                "INSERT INTO decisions "
                "(ticket_id, action, reasoning, drafted_response, "
                "sources_used, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record.ticket_id,
                    record.action,
                    record.reasoning,
                    record.drafted_response,
                    encoded_sources,
                    record.created_at,
                ),
            )
        return record

    def get_decision_for_ticket(self, ticket_id: str) -> DecisionRecord | None:
        row = self._connection.execute(
            "SELECT ticket_id, action, reasoning, drafted_response, "
            "sources_used, created_at FROM decisions WHERE ticket_id = ? "
            "ORDER BY created_at DESC, rowid DESC LIMIT 1",
            (ticket_id,),
        ).fetchone()
        return None if row is None else _to_decision(row)

    def _ticket_exists(self, ticket_id: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        return row is not None

    def _now(self) -> str:
        return self._clock().isoformat()
