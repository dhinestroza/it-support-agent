# spec/ — Spec Driven Development

> Write the spec first, then the plan, then the tasks, and only then touch the code. `constitution/` holds the project's stable rules; `features/` holds one folder per feature.

## Structure

```
spec/
├── constitution/            <- stable project rules (change rarely)
│   ├── mission.md           <- what we're building and for whom
│   ├── tech-stack.md        <- technologies, conventions, and limits
│   └── roadmap.md           <- feature order
└── features/                <- one folder per feature
    ├── 001-support-agent/
    │   ├── spec.md          <- what it does + acceptance criteria
    │   ├── plan.md          <- how it's implemented
    │   └── tasks.md         <- task checklist
    └── 002-frontend-dashboard/
        ├── spec.md
        ├── plan.md
        └── tasks.md
```

## Flow for a new feature

1. Create `features/NNN-feature-name/` with the next free number.
2. Write `spec.md`: what it does, why, and measurable acceptance criteria. Cite the relevant skill (see `skills/`) instead of redefining domain or design rules inline.
3. Write `plan.md`: technical approach and decisions, respecting `constitution/tech-stack.md`. Record alternatives considered and why they were discarded.
4. Break it down into `tasks.md` and track progress — one task at a time, verified before moving to the next.
5. Implement and validate: `pytest`, `ruff check .`, and the acceptance criteria in `spec.md`.
6. Update `constitution/roadmap.md` (move the feature to "Done").

> The constitution rules: if a feature conflicts with `mission.md` or `tech-stack.md`, the feature gets rethought — not the constitution.

## This project's features

- **001-support-agent** — the graded deliverable for Assessment C.2 (track P3): the RAG support agent itself. Build this first.
- **002-frontend-dashboard** — the Astro dashboard. Build only after 001's eval suite passes, and only if time remains — see `constitution/roadmap.md`.

## Who does what

- `orchestrator` runs the loop: picks the next task in a feature's `tasks.md`, delegates to `implementer`, verifies with `test-runner`, reviews with `code-reviewer` (+ `security-auditor` when a task touches ticket ingestion or the LLM prompt), and reports back for human confirmation before checking anything off.
- `spec-writer` updates `spec.md`/`plan.md`/`tasks.md` if something needs to change mid-feature — flagged to the orchestrator for human sign-off, never silent.
