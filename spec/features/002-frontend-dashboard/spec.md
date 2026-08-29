## Spec: 002-frontend-dashboard

_Token usage rules (which CSS variables, no hardcoded hex, status color
pairing) are defined once in the `astro-frontend-tokens` skill — this spec
states only what's specific to this feature's pages and contract._

### Problem
Once 001-support-agent can decide and draft, there's no way for an N1
agent to see the ticket queue and the agent's proposed action without
calling the API directly. This feature gives them a browsable view.

### User and context of use
The same N1 agents from 001, browsing the queue during a support shift.
Low technical level expected — needs to be readable at a glance.

### Scope
- Includes: a dashboard listing tickets with status and proposed action; a
  detail view per ticket showing the retrieved sources, decision, and
  drafted text
- NOT includes: editing/approving/sending actions (read-only demo view),
  auth, real-time updates, pagination beyond what fits on screen for the
  demo dataset

### Inputs and outputs
- Input: reads from `GET /tickets` and `GET /tickets/{id}` (001's API,
  extended with two read endpoints if not already present)
- Output: two rendered pages — dashboard, ticket detail

### Acceptance criteria
- [ ] Dashboard lists every ticket in the demo dataset with its status
      badge (resolved / pending / escalated) using the brand palette from
      tech-stack.md
- [ ] Clicking a ticket opens its detail view
- [ ] Detail view shows the ticket text, the retrieved KB sources, the
      agent's decision, and the drafted response/escalation note
- [ ] All colors come from `astro-frontend-tokens` — no hardcoded hex, no
      default blue/purple UI library look

### Edge cases and failure modes
- No tickets yet → empty state, not a blank page
- API unreachable → visible error state, not a silent blank screen

### Autonomy limits
N/A — this is a read-only UI, no autonomous action.

### Risks
Low — read-only view of already-generated, non-sensitive demo data.

### How it's evaluated
Manual check against the acceptance criteria above (visual/UI feature —
no automated test suite required for the 90-minute scope).
