## Tasks: 001-support-agent

- [ ] T1 — Write 5 KB docs in `kb/`: password-reset.md, vpn-issues.md,
      email-folder-access.md, hardware-request.md, software-install.md
- [ ] T2 — `src/agent/retrieval.py`: embed `kb/` into ChromaDB on startup,
      `retrieve(query, k=3)` returning docs + similarity scores
- [ ] T3 — `src/agent/decision.py`: prompt construction, Claude Sonnet 5
      call, structured output parsing, retry-once-then-escalate on LLM
      failure
- [ ] T4 — `src/db/models.py` + `repository.py`: SQLite schema for
      `tickets` and `decisions`, CRUD functions
- [ ] T5 — `src/api/routes.py` + `main.py`: `POST /tickets` endpoint
      wiring retrieval → decision → persistence
- [ ] T6 — `tests/eval_suite.py`: 8-10 cases —
      (1) direct KB match (password reset)
      (2) direct KB match (VPN)
      (3) ambiguous/missing info → ask
      (4) out-of-scope request → escalate (new laptop)
      (5) out-of-scope request → escalate (prod DB access)
      (6) prompt injection attempt → escalate, injection not followed
      (7) empty ticket body → ask
      (8) no matching KB doc (unrelated topic) → escalate
      (9) simulated LLM timeout/error → escalate with failure note
      (10) non-English ticket with no KB match → escalate
- [ ] T7 — Run eval suite, record pass/fail table in
      `spec/features/001-support-agent/eval-results.md`
- [ ] Validate against acceptance criteria in spec.md
- [ ] Update roadmap.md — move 001-support-agent to Done
