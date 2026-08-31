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
- [x] T9 — backend runnability: `src/api/main.py` loads the repo-root `.env` at import/startup (same file `tests/conftest.py` uses) so `uvicorn src.api.main:app` picks up `ANTHROPIC_API_KEY` without a manual export. Promote `python-dotenv` from the `dev` extra to a runtime dependency in `pyproject.toml`. Must NOT override an env var that is already set. Ships with a pytest test.
- [x] T10 — backend: add `body_excerpt: str` to `TicketSummary` (`GET /tickets`) — first ~140 chars of the ticket body, cut at a word boundary, `…` suffix if truncated, `""` for an empty body. Update `src/api/routes.py` + `src/api/schemas.py` + pytest, and mirror the field into `frontend/src/lib/types.ts` `TicketSummary` + the `isTicketSummary` guard in `frontend/src/lib/api.ts`.
- [x] T11a — frontend redesign, shell + dashboard (static, existing palette, light theme; ref: user mockup #1). `Layout.astro`: left sidebar (brand wordmark + single active "Inicio" nav item, terracotta accent via `color-mix` on `--color-brand`, no new tokens) + centered content area. `pages/index.astro`: tickets grouped by month (`created_at`, es-ES "Noviembre 2025" headers). `TicketCard.astro` restyle: short id `#<first 8 of ticket_id>` + right-aligned date + bold subject + `body_excerpt` + status badge + action badge, cleaner padding/dividers.
- [x] T11b — frontend redesign, detail page (ref: user mockup #2). `pages/tickets/[id].astro`: two-column grid. Left: "Descripción del ticket" card (subject + body, pre-wrap), "Fuentes citadas" (`SourceCitation` as rows), "Borrador del agente" (`DecisionPanel`: reasoning + draft as a message block with an agent avatar). Right: summary card — "Generado el" (date), "Estado" badge, "Acción propuesta" badge. Breadcrumb ("Inicio › #<id corto>") + styled Back button. Restyle `SourceCitation.astro` and `DecisionPanel.astro` to match. All Spanish strings via `labels.ts`, no hardcoded hex.
- [x] Validate against acceptance criteria in spec.md
- [x] Update roadmap.md — move 002-frontend-dashboard to Done (or Backlog
      if the 90 minutes run out before this feature)

## Deferred / tech debt
- T0 — `_is_valid_source` in `src/db/repository.py` is defined after `_load_sources` uses it (works at call time, but the file's other `_`-helpers are defined before use).
- T0 — N+1 `get_decision_for_ticket` lookup in the `GET /tickets` handler; acceptable for the demo dataset, revisit if it grows (a batch `Repository.latest_decisions_for(ids)` would be cleaner).
- T0 — unused `ScriptedLlm(...)` construction in two of the new `GET /tickets` tests in `tests/test_api.py`.
- T3 — `.sr-only` was removed from `TicketCard.astro` in favour of an `aria-label` on the card link. If T4/T5/T7 need a visually-hidden label, create a shared `frontend/src/styles/global.css` `.sr-only` rule or a `VisuallyHidden.astro` helper rather than re-adding a per-component copy.
  - Update (T7): T7 folded the date-format duplication into `frontend/src/lib/date.ts` (`formatTicketDate`); the `.sr-only`/VisuallyHidden helper is still not needed (no component currently uses a visually-hidden label after T3's aria-label refactor).
- T10 — `_body_excerpt` in `src/api/routes.py` duplicates the word-boundary truncation algorithm already in `src/agent/retrieval.py` `_make_excerpt`. Extract a shared `truncate_at_word(text, limit, *, ellipsis)` util (e.g. `src/text.py`) consumed by both; not done now to avoid destabilising feature 001's retrieval.
- T11/env — on this Windows + Node setup, `npm run build` prints `Assertion failed: !(handle->flags & UV_HANDLE_CLOSING)` and exits non-zero AFTER writing a complete, valid `dist/` (verified: `index.html` + detail pages render real content, `npx astro check` is clean). It only happens when the build-time fetch hits a live backend. It's a libuv teardown crash, not a build failure. For the Astro tasks the gate is `npx astro check` (0 errors) + `dist/` HTML inspection; `npm run dev` (used for the demo) is unaffected.
- T11a — `.action` pill in `TicketCard.astro` duplicates the `.badge` base rule from `StatusBadge.astro` (padding/radius/font). Extract a shared pill (a `.pill` utility or an `ActionBadge.astro` mirroring `StatusBadge`) so the two can't drift. T11b added a third copy (`.action-pill` in `pages/tickets/[id].astro`). An `ActionBadge.astro` mirroring `StatusBadge` would DRY the dashboard card, the summary card, and the inline action label in one shot.
- T13 — `frontend/src/components/SourceCitation.astro` and `DecisionPanel.astro` are now orphaned: `pages/tickets/[id].astro` (deleted) was their only consumer, and `pages/ticket.astro` rebuilds the same markup in its client `<script>`. They still typecheck but are dead code that will drift from the page. Either delete both, or (if a future SSR/prerender path is wanted) note them as intentionally retained.

## Post-release changes
- [x] T12 — backend: add `CORSMiddleware` to `src/api/main.py` so the browser can call the API cross-origin. Least-privilege: allowed origins default to `http://localhost:4321` + `http://127.0.0.1:4321`, overridable via a `FRONTEND_ORIGINS` env var (comma-separated); `allow_methods=["GET"]` only; `allow_credentials=False`; never `allow_origins=["*"]`. Ships with pytest (allowed origin gets the ACAO header, disallowed origin does not, OPTIONS preflight works).
- [x] T13 — frontend: replace the static `pages/tickets/[id].astro` route with a client-fetched detail page. New `pages/ticket.astro` = a static shell that reads `?id=` from the URL in a `<script>`, calls `fetchTicketDetail(id)` (reuse `lib/api.ts`), and renders the two-column detail DOM in JS (loading / not-found / error states in Spanish from `lib/labels.ts`). Update `TicketCard.astro`'s link to `/ticket?id=${ticket.ticket_id}`. Delete `[id].astro` and drop the now-unused `getStaticPaths`/`fetchTicketIds`. Detail styles move to a `<style>` block scoped via a wrapper class (JS-built DOM won't get Astro's scoped-style hash). No new dependency. Gate: `npx astro check` + manual check that a ticket created after build opens without a rebuild.
