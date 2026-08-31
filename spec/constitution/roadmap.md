# Roadmap

## Done
- 001-support-agent — core agent: KB ingestion, RAG retrieval, decision
  engine (answer/ask/escalate), response drafting, SQLite persistence,
  FastAPI endpoints, eval suite (8-10 cases incl. adversarial). This is
  what's graded. Done 2026-08-30 — eval suite 11/11 pass against the real
  stack (see `spec/features/001-support-agent/eval-results.md`).
- 002-frontend-dashboard — Astro static dashboard + ticket detail (sidebar
  shell, month-grouped queue, two-column detail with KB sources and the
  agent's drafted message). Read-only, build-time fetch of GET /tickets and
  GET /tickets/{id}. Done 2026-08-30 — visually redesigned to the supplied
  mockups, validated manually against the acceptance criteria; `npx astro
  check` clean, all colour via brand tokens. Backend gained GET /tickets,
  GET /tickets/{id}, TicketSummary.body_excerpt, and repo-root .env loading
  at startup. Post-release: detail page moved to a client-side fetch
  (`/ticket?id=`) + backend CORS, so newly-created tickets open without a
  rebuild (T12–T13).

## Next
- (nothing queued — both planned features are Done)

## Backlog (out of scope for the 90-minute assessment)
- Real ticketing system integration
- Multi-department support (beyond IT)
- Autonomy matrix / configurable per-category escalation rules
- Human-in-the-loop approval step before sending any answer
