# IT Support Agent · Assessment P3 (C.2)

Local RAG support agent for internal IT tickets (Data & Agentic AI Assessment, track P3). Receives a ticket, retrieves context from a knowledge base, decides answer/ask/escalate, and drafts the action. Mandatory human confirmation before anything is sent — see `spec/constitution/tech-stack.md` for the full autonomy limit. Authoritative source for domain and RAG rules: the `support-agent-domain` and `rag-chroma-python` skills — this file doesn't duplicate them.

## Stack
- Language: Python 3.11+, type hints required
- Backend: FastAPI + Uvicorn
- Data: ChromaDB (local, persisted to `./chroma_data/`) — **no cloud vector DB, no SQL server**
- AI: Claude Sonnet 5 via direct Anthropic API call — **no agent framework, no autonomous tool-calling on the critical path**
- Storage: SQLite (`tickets`, `decisions`)
- Frontend: Astro, 2 pages (`frontend/`) — only if time remains, see roadmap.md
- Tests: pytest, configured via `pyproject.toml`

## Commands
- Backend (Python): `pyproject.toml` exists at repo root — run `pytest` / `ruff check .` directly
- `uvicorn src.api.main:app --reload` — run the API locally
- Frontend (`frontend/`, Astro, separate subproject — only if built): `npm run dev` / `npm run build`

## Project structure
Monorepo: backend (Python) at the repo root, Astro frontend as a separate subproject in `frontend/` with its own `package.json` — same pattern as Dicio's `deck/`.

- `spec/` — Spec-Driven Development docs: `constitution/` (mission, tech-stack, roadmap) and `features/NNN-name/` (spec, plan, tasks)
- `skills/` — this project's skills: `clean-architecture-python`, `support-agent-domain`, `rag-chroma-python`, `astro-frontend-tokens`
- `CLAUDE.md` — this file, always loaded, English
- `src/agent/` — retrieval (`retrieval.py`) and decision engine (`decision.py`)
- `src/api/` — FastAPI routes (`routes.py`, `main.py`)
- `src/db/` — SQLite models and repository
- `kb/` — knowledge base documents (5 markdown docs)
- `tests/` — pytest suite, including `eval_suite.py`
- `pyproject.toml` — Python deps + pytest config, repo root
- `frontend/` — **separate subproject**: Astro app, its own `package.json`, no shared build tooling with the backend (feature 002, conditional)

## Conventions (Clean Code + SOLID)
- One route/handler = one responsibility; business logic lives outside the route (in `src/agent/` or `src/db/`)
- External dependencies (LLM client, ChromaDB client, DB connection) are injected, never instantiated inside business logic, so they can be mocked in tests
- Custom exceptions in `src/errors/`, never a bare `except Exception` that swallows without re-raising or logging
- Every new function/class ships with its test in the same task
- Full rules: `clean-architecture-python` skill

## Don't
- Don't call the Anthropic API with real employee data — `kb/` and test tickets are synthetic only
- Don't let the agent write to any real external system — it only proposes an action (see tech-stack.md hard limits)
- Don't skip human validation on `answer`/`escalate` in the intended production flow (not enforced in this demo, but never contradict it in code or docs)
- Don't add cloud infrastructure of any kind — this project is local/free only

## Workflow
- We work with **Spec-Driven Development**: spec.md → plan.md → tasks.md before code, for each feature in `spec/features/NNN-name/`
- One task at a time; when done, summarize what changed
- If less than 80% confident about a requirement, ask — don't guess
- Given the 90-minute time budget: feature 001 (the agent) is mandatory and graded; feature 002 (frontend) is built only if 001's eval suite passes with time remaining — see roadmap.md

## Documentation
The documentation for **Spec-Driven Development (SDD)** lives in `spec/`. Start with `spec/README.md`, which explains the full structure and flow. In short:

- `spec/constitution/` — the project's stable rules. **Read these before touching anything:**
  - `mission.md` — what we're building and for whom
  - `tech-stack.md` — stack, brand tokens, data model, hard limits
  - `roadmap.md` — feature order (done, next, backlog)
- `spec/features/NNN-name/` — one folder per feature, with `spec.md` (what the feature does + acceptance criteria) → `plan.md` (how it's implemented) → `tasks.md` (checklist)

**How to use them**
1. **Before implementing**, read `constitution/` and the affected feature's `spec.md` so you don't contradict them.
2. **When done**, check off the tasks in `tasks.md` and move the feature to "Done" in `roadmap.md`.
3. **The constitution rules**: if a feature conflicts with `mission.md` or `tech-stack.md`, the feature gets rethought — not the constitution.

- `spec/features/001-support-agent/` — the agent: spec, plan, tasks. Mandatory, graded.
- `spec/features/002-frontend-dashboard/` — the dashboard: spec, plan, tasks. Only if 001 passes with time remaining.
- Each `spec/features/NNN-name/spec.md` should cite the relevant skill instead of redefining business rules inline
- Domain rules (answer/ask/escalate, source citation): `support-agent-domain` skill
- RAG conventions (embeddings, chunking, threshold): `rag-chroma-python` skill
- Python architecture/SOLID: `clean-architecture-python` skill
- Frontend tokens: `astro-frontend-tokens` skill (only relevant if 002 is built)
- Library docs: Context7 MCP
- Code/dependency graph: Codebase Memory MCP

## Subagents (SDD + TDD loop)
- `.claude/agents/` holds the orchestrator + specialist subagents that enforce the loop above
- Default entry point: `claude --agent orchestrator` — the orchestrator never edits code itself, it only delegates and enforces gates
- The orchestrator never marks a task `[x]` without explicit human confirmation
