## Tasks: 002-frontend-dashboard

### Verification gate (per task)
- **T0 (backend):** strict TDD — failing pytest first, then code. Gate = `pytest` exit 0 + `ruff check .` clean.
- **T1–T7 (Astro):** this is a visual/UI feature (see spec.md "How it's evaluated"), no JS test runner in scope. Gate per task = `npm run build` succeeds AND `npx astro check` (typecheck) exit 0, run from `frontend/`, plus manual check of the relevant acceptance criterion. code-reviewer still reviews every diff.

- [x] T0 — backend: add read-only `GET /tickets` (list, newest first) and `GET /tickets/{id}` (ticket text + its latest decision + sources; 404 if unknown) to `src/api/routes.py` + response schemas in `src/api/schemas.py`. Reuses existing `Repository.list_tickets` / `get_ticket` / `get_decision_for_ticket`. Ships with pytest tests in `tests/test_api.py` (list returns created tickets; detail returns decision + sources; unknown id -> 404). No new dependencies.
- [x] T1 — scaffold the Astro project in `frontend/` (`npm create astro@latest`, minimal/empty template, its own `package.json`, `astro.config.mjs`, TypeScript) — separate subproject, no shared tooling with the backend. Then `frontend/src/styles/tokens.css`: brand palette as CSS custom properties matching the hex values in tech-stack.md's "Brand / design tokens" table (--color-brand #a26769, --color-bg #f5f3f4, card surface, text primary/secondary, and the three paired status bg/text tokens).
- [x] T2 — `StatusBadge.astro`: renders resolved/pending/escalated with
      the correct token colors
- [x] T3 — `TicketCard.astro`: subject, timestamp, status badge, links to
      detail page
- [x] T4 — `SourceCitation.astro`: doc id + excerpt from retrieval
- [x] T5 — `DecisionPanel.astro`: action, reasoning, drafted text
- [x] T6 — `layouts/Layout.astro` (shared shell, `<html lang="es">`, brand
      header) + `pages/index.astro`: dashboard — build-time fetch of
      `GET /tickets` (try/catch), renders `TicketCard` list; empty state if
      `[]`; visible Spanish error state if the fetch fails or the payload is
      not a valid ticket array
- [x] T7 — `pages/tickets/[id].astro`: reuses `Layout.astro` and the same
      build-time-fetch + error-state pattern for `GET /tickets/{id}` (404 or
      fetch failure → error state); renders ticket + `SourceCitation`s +
      `DecisionPanel`
- [ ] T8 — minimal smoke test: page loads,
      header renders. Not required per spec.md's "How it's evaluated".
- [x] T9 — backend runnability: `src/api/main.py` loads the repo-root `.env` at import/startup (same file `tests/conftest.py` uses) so `uvicorn src.api.main:app` picks up `ANTHROPIC_API_KEY` without a manual export. Promote `python-dotenv` from the `dev` extra to a runtime dependency in `pyproject.toml`. Must NOT override an env var that is already set. Ships with a pytest test.
- [ ] Validate against acceptance criteria in spec.md
- [ ] Update roadmap.md — move 002-frontend-dashboard to Done (or Backlog
      if the 90 minutes run out before this feature)

## Deferred / tech debt
- T0 — `_is_valid_source` in `src/db/repository.py` is defined after `_load_sources` uses it (works at call time, but the file's other `_`-helpers are defined before use).
- T0 — N+1 `get_decision_for_ticket` lookup in the `GET /tickets` handler; acceptable for the demo dataset, revisit if it grows (a batch `Repository.latest_decisions_for(ids)` would be cleaner).
- T0 — unused `ScriptedLlm(...)` construction in two of the new `GET /tickets` tests in `tests/test_api.py`.
- T3 — `.sr-only` was removed from `TicketCard.astro` in favour of an `aria-label` on the card link. If T4/T5/T7 need a visually-hidden label, create a shared `frontend/src/styles/global.css` `.sr-only` rule or a `VisuallyHidden.astro` helper rather than re-adding a per-component copy.
  - Update (T7): T7 folded the date-format duplication into `frontend/src/lib/date.ts` (`formatTicketDate`); the `.sr-only`/VisuallyHidden helper is still not needed (no component currently uses a visually-hidden label after T3's aria-label refactor).
