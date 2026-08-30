from __future__ import annotations

import pytest

from src.db.models import (
    DEFAULT_TICKET_STATUS,
    VALID_ACTIONS,
    DecisionAction,
    status_for_action,
)


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        ("answer", DEFAULT_TICKET_STATUS),
        ("ask", DEFAULT_TICKET_STATUS),
        ("escalate", "escalated"),
    ],
)
def test_status_for_action_maps_every_action(
    action: DecisionAction, expected: str
) -> None:
    assert status_for_action(action) == expected


def test_every_valid_action_is_covered() -> None:
    assert set(VALID_ACTIONS) == {"answer", "ask", "escalate"}
