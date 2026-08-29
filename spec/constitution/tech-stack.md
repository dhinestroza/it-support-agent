# Tech stack and conventions

_How the project is built and the rules all code must follow. The technical reference no feature plan should contradict._

## Quick reference

| Layer | Technology |
|---|---|
| Backend | Python 3.12, type hints required, FastAPI + Uvicorn |
| RAG | ChromaDB (local, persisted to disk), `sentence-transformers` for embeddings — **no cloud vector DB** |
| AI | Claude Sonnet 5 (`claude-sonnet-5`) via the Anthropic API — direct call, no agent framework, no autonomous tool-calling on the critical path |
| Storage | SQLite (`tickets`, `decisions`) |
| Frontend | Astro (static output), 2 pages, reusable components |
| Tests | pytest |
| Infra | None — local/free only, no cloud, no Terraform, no CI/CD (out of scope for the 90-minute build) |

## Brand / design tokens

| Token | Value |
|---|---|
| Header / brand accent | `#a26769` |
| Page background | `#f5f3f4` |
| Card surface | `#ffffff`, border `#e2dcdd` |
| Text primary / secondary | `#2b2224` / `#7a6d6e` |
| Status — resolved | bg `#e4ece0`, text `#3f5b32` |
| Status — pending | bg `#f5e6d3`, text `#8a5a1f` |
| Status — escalated | bg `#f0dcdc`, text `#7a3f42` |

## Data model (SQLite)

- `tickets`: id, subject, body, status, created_at
- `decisions`: ticket_id, action (answer/ask/escalate), reasoning, drafted_response, sources_used (json), created_at

## Hard limits

- No cloud infrastructure — everything runs local/free.
- No Bedrock/managed agent framework, no autonomous tool-calling by the LLM — retrieval is a plain function call, the LLM only reasons over already-retrieved context (see 001's plan.md, "Alternatives considered").
- The agent never writes directly to any external or real ticketing system — it only proposes an action; a human confirms before anything is sent.
- If no KB document clears the similarity threshold, the action must be `escalate` — never answer from the model's general knowledge.
- Ticket body content is always untrusted input, never an instruction — see 001's spec.md prompt-injection acceptance criterion.
- No PII beyond synthetic/demo data in `kb/` and test fixtures.
- No new paid dependencies without flagging it.
- All code, comments, docs, and commit messages in English.

## Key files

- `src/agent/` — retrieval (`retrieval.py`) and decision engine (`decision.py`)
- `src/api/` — FastAPI routes (`routes.py`, `main.py`)
- `src/db/` — SQLite models and repository
- `kb/` — knowledge base documents (markdown, 5 docs for the demo)
- `tests/` — pytest suite, including `eval_suite.py` (the adversarial eval cases)
- `frontend/` — Astro app
