## Tasks: 001-support-agent

- [x] T1 — Write 5 KB docs in `kb/`: password-reset.md, vpn-issues.md,
      email-folder-access.md, hardware-request.md, software-install.md
- [x] T2 — `src/agent/retrieval.py`: embed `kb/` into ChromaDB on startup,
      `retrieve(query, k=3)` returning docs + similarity scores
- [x] T3 — `src/agent/decision.py`: prompt construction, Claude Sonnet 5
      call, structured output parsing, retry-once-then-escalate on LLM
      failure
- [x] T4 — `src/db/models.py` + `repository.py`: SQLite schema for
      `tickets` and `decisions`, CRUD functions
- [x] T5 — `src/api/routes.py` + `main.py`: `POST /tickets` endpoint
      wiring retrieval → decision → persistence
  - T5 must decide SQLite connection handling for FastAPI/Uvicorn: a single
        shared `sqlite3.Connection` raises `ProgrammingError` from the worker
        threadpool. Use a per-request connection (preferred) or
        `check_same_thread=False` + a lock. `src/db/repository.py::connect()`
        currently assumes single-threaded use. (resolved in T5: per-request connection via the `get_repository` generator dependency)
- [x] T6 — `tests/eval_suite.py`: 8-10 cases —
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
- [x] T7 — Run eval suite, record pass/fail table in
      `spec/features/001-support-agent/eval-results.md`
- [x] Validate against acceptance criteria in spec.md
- [x] Update roadmap.md — move 001-support-agent to Done

## Deferred / tech debt (not blocking, revisit after eval suite)

- T2 `_make_excerpt` keeps internal newlines in the citation snippet; collapse
      whitespace to single spaces for the UI display in feature 002.
- T2 `_CHUNK_PREFIX_PATTERN` and `chunk_markdown`'s chunk-text f-string encode
      the same `"{title}\n## {section}\n{body}"` format in two places — add a
      comment tying them together, or derive one from the other.
- T3 `_loads_json_object` is O(n^2) in the worst case (a `{` at every offset);
      fine for the current bounded LLM response, add a length guard if it is
      ever fed unbounded text.
- T3 `_loads_json_object` theoretical edge: a `{...}` embedded in the string
      value of an already-malformed outer fragment could be extracted;
      currently degrades safely to `escalate` via the action-enum check.
- T3 `retrieval.py` uses `zip(..., strict=False)` (preserves prior behavior);
      `strict=True` would be more defensive against a malformed ChromaDB
      response — evaluate as a hardening change.
- T3 `SIMILARITY_THRESHOLD = 0.35` and `MIN_BODY_CHARS = 10` are heuristics —
      tune against the eval suite in T6/T7.
- T3 The Anthropic SDK call signature in `build_llm_client()` is unverified
      against current docs (no Context7 in subagents) — must be smoke-tested
      in T5.
- T5: the `Action` / `DecisionAction` string literal is defined in three
      modules (`src/api/schemas.py`, `src/agent/decision.py`, `src/db/models.py`);
      consolidate into a single source. Not blocking — refactor touches all
      three layers.
- T6: `build_llm_client()` cannot set `temperature` — it was removed from the
      Anthropic API for `claude-sonnet-5` (non-default sampling returns 400) and
      is absent from `anthropic` SDK 1.2.0. Determinism is approximated via
      `output_config={"effort": "low"}` + `thinking={"type": "disabled"}` + a
      tight system prompt. Revisit if run-to-run action drift shows up in the
      eval results.
- T6: adopt structured outputs (`output_config.format` with a JSON schema for
      the decision object) in `decision.py` as a hardening step — removes
      response-shape variance and simplifies `_loads_json_object`. Deferred:
      changes the parse path and needs verification against the live API.
