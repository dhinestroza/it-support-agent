## Plan: 002-frontend-dashboard

### Approach
Static Astro pages that fetch from the FastAPI backend **at build time** (in
the component frontmatter), wrapped in try/catch. `output: "static"` per
tech-stack.md — no SSR, no client-side framework.
No client-side framework needed for two read-only pages — plain Astro
components keep this fast to build. The two GET endpoints are added to
001's FastAPI app (they were deferred from 001's scope); everything else
is static Astro.

### Files / modules touched (in order)
0. `src/api/routes.py` + `src/api/schemas.py` — two read-only endpoints
   (`GET /tickets`, `GET /tickets/{id}`) the dashboard consumes; reuse
   existing `Repository` methods, add `TicketSummary` / `TicketDetail`
   response schemas.
0b. `frontend/src/layouts/Layout.astro` — shared page shell: `<html lang="es">`,
   `<head>` (charset, viewport, title), brand header, `<slot />`, imports
   `../styles/tokens.css`.
1. `frontend/src/components/StatusBadge.astro`
2. `frontend/src/components/TicketCard.astro`
3. `frontend/src/components/SourceCitation.astro`
4. `frontend/src/components/DecisionPanel.astro`
5. `frontend/src/pages/index.astro` — dashboard, lists `TicketCard`s
6. `frontend/src/pages/tickets/[id].astro` — detail view, uses
   `SourceCitation` + `DecisionPanel`
7. `frontend/src/styles/tokens.css` — brand palette as CSS variables
   7b. `frontend/src/lib/types.ts` + `frontend/src/lib/labels.ts` — shared TS types (`TicketStatus`, `TicketAction`, `TicketSummary`) mirroring the API contract, and the Spanish display-label maps (see spec.md "UI language").
8. `frontend/` scaffold — `npm create astro@latest`, minimal template,
   TypeScript, own `package.json`.

### Testing strategy
Backend read endpoints (item 0): strict pytest TDD, same as feature 001.
Astro components/pages: no JS test runner in the 90-minute scope (spec.md
"How it's evaluated"); the per-task gate is `npm run build` + `npx astro
check` passing, plus a manual check against the acceptance criteria.
Rationale: two read-only pages don't justify standing up vitest + Astro
Container API within the time budget.

### Data fetching & failure modes
`GET /tickets` (index) and `GET /tickets/{id}` (detail) are fetched **at
build time** in the Astro frontmatter, wrapped in try/catch. The API base
URL comes from `import.meta.env.PUBLIC_API_BASE_URL`, defaulting to
`http://localhost:8000`. Fetch failure, non-2xx response, or a non-array /
malformed payload → the page renders `MESSAGES.apiError` (visible Spanish
error state, never a blank page). An empty array → the empty state. The
response is treated as untrusted: each item is shape-checked before render.
Because the fetch runs at build time, the "API unreachable → visible error
state" acceptance criterion is verified at build time — build the site with
the API down and confirm the error state renders with no blank page.
The backend loads the repo-root `.env` at startup (`src/api/main.py`), so the
demo flow is `uvicorn src.api.main:app` → `POST /tickets` (seeds data) →
`npm run build` in `frontend/`.

### Alternatives considered
- **React/Vue islands** — discarded: no interactivity needed for a
  read-only 2-page demo, plain Astro is faster to build and matches the
  "keep it organized but fast" constraint
- **Server-rendering tickets inline in FastAPI (Jinja templates)** —
  discarded: user explicitly asked for Astro; also keeps frontend/backend
  concerns separated for a cleaner demo
