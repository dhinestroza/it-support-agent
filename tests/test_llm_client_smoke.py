from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import Any

import pytest

from src.agent.decision import ANTHROPIC_MODEL, build_llm_client

anthropic = pytest.importorskip("anthropic")

REQUIRED_CREATE_KWARGS = (
    "model",
    "max_tokens",
    "output_config",
    "thinking",
    "system",
    "messages",
)


@pytest.fixture(autouse=True)
def _dummy_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")


def test_anthropic_exposes_the_client_class() -> None:
    assert hasattr(anthropic, "Anthropic")


def test_messages_create_accepts_the_kwargs_we_pass() -> None:
    signature = inspect.signature(anthropic.resources.messages.Messages.create)
    missing = [
        name for name in REQUIRED_CREATE_KWARGS if name not in signature.parameters
    ]
    assert not missing, (
        f"anthropic SDK {anthropic.__version__} messages.create is missing "
        f"{missing}; actual signature: {signature}"
    )


def test_client_returns_the_joined_text_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_create(self: Any, **kwargs: Any) -> SimpleNamespace:
        captured.update(kwargs)
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text='{"action":"escalate",'),
                SimpleNamespace(type="text", text='"draft":"d","reasoning":"r"}'),
            ]
        )

    monkeypatch.setattr(anthropic.resources.messages.Messages, "create", fake_create)

    call = build_llm_client()
    raw = call("system prompt", "user prompt")

    assert raw == '{"action":"escalate","draft":"d","reasoning":"r"}'
    assert captured["model"] == ANTHROPIC_MODEL
    assert captured["system"] == "system prompt"
    assert captured["messages"] == [{"role": "user", "content": "user prompt"}]
    assert isinstance(captured["max_tokens"], int)
    assert captured["output_config"] == {"effort": "low"}
    assert captured["thinking"] == {"type": "disabled"}


def test_non_text_blocks_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_create(self: Any, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="thinking", thinking="ignored"),
                SimpleNamespace(type="text", text="kept"),
            ]
        )

    monkeypatch.setattr(anthropic.resources.messages.Messages, "create", fake_create)

    assert build_llm_client()("system", "user") == "kept"
