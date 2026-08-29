## Spec: 001-support-agent

_Domain rules (answer/ask/escalate policy, source-citation policy) and RAG
conventions (embedding model, chunking, similarity threshold) are defined
once in the `support-agent-domain` and `rag-chroma-python` skills — this
spec states only what's specific to this feature's contract and test cases._

### Problem
IT support tickets are triaged manually today: an N1 agent reads every
ticket, decides what to do, and drafts the response — even for repetitive,
well-documented issues (password resets, VPN errors, access requests).
This wastes N1 time and delays simple resolutions. If unaddressed, ticket
volume keeps consuming human time that could go to harder cases.

### User and context of use
Internal N1 support agents, during their normal ticket queue review.
Tickets arrive as short text (subject + body), similar to an email or a
web form submission. Used continuously during business hours, one ticket
at a time. Users are non-technical about AI internals — they just need a
clear decision and a draft they can approve or edit.

### Scope
- Includes: receiving one ticket (subject + body), retrieving relevant KB
  documents, deciding answer / ask / escalate, drafting the corresponding
  text (response or escalation note), persisting the ticket + decision,
  exposing this via a FastAPI endpoint
- Includes: an evaluation suite with 8-10 cases incl. adversarial ones
- NOT includes: real ticketing system integration, multi-department
  support, auto-sending anything without human confirmation, learning
  from past decisions (no fine-tuning / feedback loop), authentication

### Inputs and outputs
**Input** (`POST /tickets`): JSON `{ "subject": str, "body": str }`

**Output**: JSON
```
{
  "ticket_id": str,
  "action": "answer" | "ask" | "escalate",
  "draft": str,
  "sources": [ { "doc_id": str, "excerpt": str } ],
  "reasoning": str
}
```
- `action=answer` → `draft` is the response to send to the user
- `action=ask` → `draft` is the clarifying question
- `action=escalate` → `draft` is the escalation note for the human agent,
  `sources` may be empty

### Acceptance criteria
- [ ] Given a ticket clearly covered by one KB doc (e.g. "how do I reset my
      password"), the agent returns `action=answer` with a draft that
      references the correct doc
- [ ] Given a ticket with missing information needed to help (e.g. "my VPN
      doesn't work" with no OS/error given), the agent returns `action=ask`
- [ ] Given a ticket requesting something outside agent authority (e.g. new
      laptop purchase, access to a production database), the agent returns
      `action=escalate`
- [ ] Given a ticket containing an instruction trying to override the
      agent's behavior (prompt injection), the agent ignores the injected
      instruction and treats it as ticket content, not as a command
- [ ] Given an empty or near-empty ticket body, the agent returns
      `action=ask` rather than guessing or erroring
- [ ] Given the LLM call fails (timeout/error), the agent returns
      `action=escalate` with a note that automated triage failed — never
      silently drops the ticket
- [ ] Every `answer` and `ask` response cites at least one retrieved
      source when one was used; no fabricated doc references

### Edge cases and failure modes
General answer/ask/escalate policy (missing threshold, LLM failure, prompt
injection) is defined in `support-agent-domain` — see that skill. Specific
to this feature:
- Ticket in a language other than English → still processed as normal
  input; the domain policy's "no match → escalate" rule applies the same
  way regardless of language
- Retry policy on LLM failure: exactly one retry before escalating (not
  defined in the skill, since it's an implementation/reliability choice
  specific to this feature)

### Autonomy limits
The can/cannot boundary is the skill's escalate policy plus: the agent
never writes to a real ticketing system and never accesses KB content
outside `kb/` (see tech-stack.md hard limits). Every `answer` still
requires human approval before send in the intended production flow —
this demo logs the decision only; a human-in-the-loop confirmation step
is documented as a roadmap backlog item, not built in the 90-minute scope.

### Risks
- Data: only synthetic/demo ticket data, no real employee PII
- Impact of a wrong `answer`: low (draft still needs human approval in the
  intended production flow) but a wrong `escalate` (under-escalating) is
  the higher-risk failure mode — the eval suite weights escalation
  recall accordingly
- Human enters: reviewing every drafted answer before it's sent (out of
  scope for this demo but stated as the production requirement)

### How it's evaluated
`tests/eval_suite.py` — 8-10 fixed cases (see tasks.md) covering: direct
KB match, ambiguous/missing info, out-of-scope request, prompt injection,
empty input, and a simulated LLM failure. Each case asserts the expected
`action` and checks the draft references a real source when applicable.
