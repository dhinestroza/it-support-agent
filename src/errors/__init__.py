from __future__ import annotations


class SupportAgentError(Exception):
    """Base class for every error raised by this application."""


class EmptyKnowledgeBaseError(SupportAgentError):
    """The knowledge base has no indexable content to retrieve from."""


class LlmError(SupportAgentError):
    """The LLM call failed or returned an unusable response."""


class NotFoundError(SupportAgentError):
    """The requested resource does not exist."""


class ValidationError(SupportAgentError):
    """The provided or stored data failed validation."""


__all__ = [
    "EmptyKnowledgeBaseError",
    "LlmError",
    "NotFoundError",
    "SupportAgentError",
    "ValidationError",
]
