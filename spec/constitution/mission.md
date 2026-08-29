# Mission

_Defines the project's reason for existing. It's the reference that decides whether a feature "fits" or not._

## What we're building

A local, RAG-based support agent for internal IT tickets, built for the Data & Agentic AI Assessment (track P3, challenge C.2), delivered in a single 90-minute session.

1. **One channel, one contract** — a ticket (subject + body) comes in through a single API endpoint; no multi-channel normalization needed at this scale.
2. **Grounded decisions, not autonomous ones** — ChromaDB retrieval + Claude Sonnet 5 produce an `answer`, `ask`, or `escalate` decision; the agent only proposes, a human confirms before anything is sent.
3. **The 5-doc knowledge base in `kb/` is the system of record for what the agent is allowed to know** — no answering from the model's general knowledge.
4. **Demonstrability over completeness** — the eval suite (8-10 cases, including adversarial ones) is the actual proof of "it works," not the demo itself.

## For whom

- Internal IT support N1 agents — the intended end users of the dashboard, reviewing the queue and the agent's proposed action.
- The assessment evaluator — reviews the spec, the implementation, the eval results, and (if selected) the Part D defense of this same work.
- The author (Daniel) — builds and demonstrates this within the assessment's fixed 90-minute Part C window.

## Principles

- **Human control, no exceptions in this scope** — every `answer` still requires human approval before it's sent; this is stated even though the confirmation UI itself isn't built in the 90-minute scope.
- **Escalate is the fail-safe** — no matching KB doc, an LLM failure, or a detected prompt-injection attempt all resolve to `escalate`, never to a guess.
- **Local and free, no exceptions** — ChromaDB, SQLite, sentence-transformers: no cloud infrastructure, no cost beyond the LLM calls themselves.
- **Spec before code, every time** — `spec.md` → `plan.md` → `tasks.md` before any implementation, enforced by the orchestrator loop.
- **001 before 002, always** — the agent (graded) is never sacrificed for the dashboard (not graded); see `roadmap.md`.

## What it's NOT

- Not production, not multi-department, not a real ticketing system integration.
- No authentication, no multi-user support, no real employee data — `kb/` and test tickets are synthetic only.
- No autonomous tool-calling by the LLM — retrieval is a plain function call, not a tool the model invokes on its own.
- No cloud infrastructure of any kind — no AWS, no managed vector DB, no managed LLM agent framework.
- No fine-tuning, no learning from past decisions, no feedback loop.
- No mandatory frontend — `002-frontend-dashboard` is built only if time remains after `001` passes its eval suite.