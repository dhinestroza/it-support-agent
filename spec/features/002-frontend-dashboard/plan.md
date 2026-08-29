## Plan: 002-frontend-dashboard

### Approach
Static Astro pages that fetch from the FastAPI backend at request time.
No client-side framework needed for two read-only pages — plain Astro
components keep this fast to build.

### Files / modules touched (in order)
1. `frontend/src/components/StatusBadge.astro`
2. `frontend/src/components/TicketCard.astro`
3. `frontend/src/components/SourceCitation.astro`
4. `frontend/src/components/DecisionPanel.astro`
5. `frontend/src/pages/index.astro` — dashboard, lists `TicketCard`s
6. `frontend/src/pages/tickets/[id].astro` — detail view, uses
   `SourceCitation` + `DecisionPanel`
7. `frontend/src/styles/tokens.css` — brand palette as CSS variables

### Alternatives considered
- **React/Vue islands** — discarded: no interactivity needed for a
  read-only 2-page demo, plain Astro is faster to build and matches the
  "keep it organized but fast" constraint
- **Server-rendering tickets inline in FastAPI (Jinja templates)** —
  discarded: user explicitly asked for Astro; also keeps frontend/backend
  concerns separated for a cleaner demo
