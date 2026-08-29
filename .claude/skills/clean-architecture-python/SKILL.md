---
name: clean-architecture-python
description: SOLID and clean architecture conventions for Python services in this project — layering, dependency injection, testing boundaries.
---

- One route/handler = one responsibility. Business logic lives in `src/agent/` or `src/db/`, never inline in `src/api/routes.py`.
- External dependencies (LLM client, ChromaDB client, DB connection) are injected as constructor/function params — never instantiated inside business logic — so they can be mocked in tests.
- Custom exceptions live under `src/errors/`. Never a bare `except Exception` that swallows without re-raising or logging.
- Every new function/class ships with its test in the same task.
- Type hints on every function signature (params + return).
