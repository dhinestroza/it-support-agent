# Roadmap

## Done
- 001-support-agent — core agent: KB ingestion, RAG retrieval, decision
  engine (answer/ask/escalate), response drafting, SQLite persistence,
  FastAPI endpoints, eval suite (8-10 cases incl. adversarial). This is
  what's graded. Done 2026-08-30 — eval suite 11/11 pass against the real
  stack (see `spec/features/001-support-agent/eval-results.md`).

## Next
- 002-frontend-dashboard — Astro dashboard + ticket detail. Build only
  after 001 passes its eval suite, and only if time remains.

## Backlog (out of scope for the 90-minute assessment)
- Real ticketing system integration
- Multi-department support (beyond IT)
- Autonomy matrix / configurable per-category escalation rules
- Human-in-the-loop approval step before sending any answer
