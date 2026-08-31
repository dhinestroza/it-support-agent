# IT Support Agent · Assessment P3 (C.2)

Local RAG support agent for internal IT tickets. A ticket (subject + body) comes in → context is retrieved from a 5-doc markdown knowledge base (ChromaDB) → Claude Sonnet decides `answer` / `ask` / `escalate` and drafts the reply, the clarifying question, or the escalation note. **The agent only proposes**: a human confirms before anything is sent, and that confirmation step is deliberately out of scope for this demo.

## Stack

- **Python 3.11+**, FastAPI + Uvicorn, type hints required
- **SQLite** (`tickets`, `decisions`) — file at `./support_agent.db`
- **ChromaDB** (persisted to `./chroma_data/`) + `sentence-transformers` (`all-MiniLM-L6-v2`)
- **Anthropic API**, model `claude-sonnet-5` — direct call, no agent framework, no autonomous tool-calling
- **Frontend**: Astro (static output) — dashboard prerendered at build time, ticket detail fetched client-side
- **Tests**: pytest + ruff, configured in `pyproject.toml`

No cloud, no managed vector DB, no CI/CD — everything runs locally.

## Prerequisites

- Python 3.11 or newer
- Node >= 22.12 (only if you run the frontend)
- An Anthropic API key

## 1. Backend — setup & run

```powershell
cd C:\Users\dhine\Downloads\it-support-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # PowerShell  (cmd: .venv\Scripts\activate.bat)
pip install -e .
```

Put the key in a `.env` file at the repo root (git-ignored, auto-loaded at startup via `python-dotenv`):

```
ANTHROPIC_API_KEY=sk-ant-...
```

Run the API:

```powershell
uvicorn src.api.main:app            # http://127.0.0.1:8000
```

- Startup creates `./support_agent.db` with the `tickets` and `decisions` tables.
- Interactive docs: <http://127.0.0.1:8000/docs>
- Use `--reload` only while editing backend code — see the next section for why.

## 2. Why the first `POST /tickets` is slow (and later ones aren't)

`POST /tickets` builds its dependencies lazily. On the **first** call it:

1. downloads `all-MiniLM-L6-v2` (~90 MB, one-time, cached under `~/.cache`),
2. creates `./chroma_data/` and indexes the 5 `kb/*.md` docs (one chunk per `##` section),
3. calls Claude Sonnet.

First call: **~30-60 s**. The retriever and decision engine are then cached singletons, so subsequent calls are **~3-8 s** (just the Claude round-trip).

Gotchas:

- `uvicorn --reload` restarts the worker on every file save, which drops the cached model → it reloads on the next request. Run **without** `--reload` for a smooth demo.
- The `Warning: ... HF_TOKEN` line is `huggingface_hub` querying the Hub unauthenticated (rate-limited). Once the model is cached you can skip that check: set `$env:HF_HUB_OFFLINE = "1"` before starting `uvicorn`.
- On the LLM path each call has a 30 s timeout and is retried once; if both attempts fail the agent falls back to `escalate` with an automated-triage-failed note. It never guesses.

## 3. API endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | `{"status":"ok"}` |
| `POST` | `/tickets` | body `{subject, body}` → `{ticket_id, action, draft, sources[], reasoning}` (triggers retrieval + LLM) |
| `GET` | `/tickets` | list, newest first — `{ticket_id, subject, body_excerpt, status, created_at, action}` |
| `GET` | `/tickets/{id}` | full detail incl. `body`, `reasoning`, `draft`, `sources[]`; `404` if unknown |

Request limits: `subject` 1-300 chars (trimmed), `body` <= 20 000 chars, any unknown JSON field → `422`, request body over 64 KB → `413`.

Quick check:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe -X POST http://127.0.0.1:8000/tickets -H "Content-Type: application/json" -d "{\"subject\":\"VPN keeps disconnecting\",\"body\":\"My VPN drops every few minutes when I work from home.\"}"
```

An importable Postman collection covering these endpoints can be shared separately (the maintainer has it).

## 4. Ticket status vs. agent action

The agent drafts, it never sends — so a drafted answer leaves the ticket waiting for a human:

| Agent `action` | Ticket `status` |
|---|---|
| `answer` / `ask` | `pending` (a draft is waiting for review) |
| `escalate` | `escalated` |

`resolved` exists in the data model but nothing in the pipeline sets it. It would be written by the human confirmation step, which is documented as mandatory but not built in this scope.

## 5. Frontend (optional)

```powershell
cd frontend
npm install
npm run dev            # http://localhost:4321
# or a production build:
npm run build
npm run preview        # http://localhost:4321
```

- The **dashboard** (`/`) is prerendered at build time — to see tickets created after the last build, restart `npm run dev` (or rebuild).
- The **detail page** (`/ticket?id=<id>`) fetches live in the browser, so any ticket opens without a rebuild.
- The browser calls the API directly, so the backend enables **CORS** for `http://localhost:4321` and `http://127.0.0.1:4321` by default. Override with the `FRONTEND_ORIGINS` env var (comma-separated). If the backend is not on `http://localhost:8000`, set `PUBLIC_API_BASE_URL` in `frontend/.env`.
- Known issue: on some Windows + Node setups `npm run build` prints a libuv assertion and exits non-zero **after** writing a valid `dist/`. The output is fine; `npm run dev` is unaffected.

## 6. Tests

```powershell
pip install -e ".[dev]"      # pytest, ruff, httpx
pytest                       # unit + API suite
ruff check .                 # lint
pytest tests/eval_suite.py   # real-stack eval (needs ANTHROPIC_API_KEY + chromadb + sentence-transformers)
cd frontend; npx astro check # frontend typecheck
```

Plain `pytest` does **not** pick up `tests/eval_suite.py` (the filename is outside pytest's default discovery pattern), because it makes real, billed API calls. Run it explicitly by name.

## 7. Layout & docs

```
src/         backend — agent/ (retrieval, decision), api/ (routes, main), db/, errors/
kb/          knowledge base, 5 markdown docs (synthetic)
tests/       pytest suite + eval_suite.py
frontend/    Astro subproject, own package.json (dashboard + ticket detail)
spec/        Spec-Driven Development docs
```

- `spec/constitution/` — the stable rules: `mission.md`, `tech-stack.md`, `roadmap.md`
- `spec/features/NNN-name/` — per feature: `spec.md` → `plan.md` → `tasks.md` (`001-support-agent` also has `eval-results.md`); `spec/features/README.md` explains the flow
- `CLAUDE.md` and `.claude/skills/` — the working conventions (clean architecture, domain rules, RAG conventions, frontend tokens)

## 8. Constraints

- Synthetic/demo data only — never real employee PII in `kb/` or test tickets.
- Local and free: no cloud infrastructure, no managed vector DB, no agent framework.
- The agent proposes an action; it never writes to a real system and never sends anything.
- If no KB document clears the similarity threshold, the action is `escalate` — never an answer from the model's general knowledge.
