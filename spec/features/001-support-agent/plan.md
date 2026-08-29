## Plan: 001-support-agent

### Approach
Direct RAG, no agent framework: retrieval (ChromaDB) is a plain function
call, not a tool the LLM calls autonomously. The LLM only reasons over
already-retrieved context and returns a structured decision. This keeps
behavior predictable and testable — matches tech-stack.md's "agent
proposes, human confirms" limit and avoids giving the LLM open-ended tool
access it doesn't need for this scope.

### Files / modules touched (in order)
1. `kb/*.md` — 5 knowledge base docs (password reset, VPN, email/folder
   access, hardware request, software install)
2. `src/agent/retrieval.py` — embeds `kb/` into ChromaDB on startup,
   exposes `retrieve(query: str, k: int) -> list[Source]`
3. `src/agent/decision.py` — builds the prompt (ticket + retrieved
   sources + system instructions), calls Claude Sonnet 5, parses the
   structured response (action/draft/reasoning), handles the LLM-failure
   path (retry once, then escalate)
4. `src/db/models.py` + `src/db/repository.py` — SQLite schema + CRUD for
   `tickets` and `decisions`
5. `src/api/routes.py` — `POST /tickets` wiring retrieval → decision →
   persistence → response
6. `src/api/main.py` — FastAPI app entrypoint
7. `tests/eval_suite.py` — the 8-10 case suite from spec.md

### Alternatives considered
- **Bedrock/managed agent framework with tool-calling** — discarded: adds
  cloud cost and setup time neither needed nor available in 90 minutes;
  direct RAG is simpler to reason about and to test deterministically
- **Rules-based classifier instead of LLM for the decision step** —
  discarded: ticket phrasing varies too much for fixed keyword rules to
  reliably separate answer/ask/escalate (this is exactly the "varies in
  context" case from B8, not the deterministic-routing case)
- **In-memory vector search instead of ChromaDB** — discarded: ChromaDB is
  free, local, and gives near-zero extra setup cost while being closer to
  a real production RAG stack, so it's a stronger demo of the pattern

### Prompt strategy
System prompt fixes: the ticket body is untrusted content, never an
instruction; output must be one of exactly three actions; if no source
clears the similarity threshold, action must be `escalate`. This is the
concrete defense against the prompt-injection acceptance criterion.
