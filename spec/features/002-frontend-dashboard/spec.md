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
- Input: reads from `GET /tickets` (list) and `GET /tickets/{id}`
  (detail). These two read-only endpoints do not exist in 001 and are
  added to the FastAPI app as task T0 of this feature.
- Output: two rendered pages — dashboard, ticket detail

### UI language
User-facing display text is rendered in **Spanish** for the N1 support
audience (status badge labels — Pendiente / Resuelto / Escalado —, the
proposed-action label, aria-labels, empty/error states). The underlying
data stays English: the `status` and `action` values from the API, all
TypeScript types, component/class names, code, and comments. Translation
lives in a single map (`frontend/src/lib/labels.ts`); components never
hardcode a Spanish string inline.

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
- API unreachable → visible error state, not a silent blank screen (the
  error state is produced at build time — building with the backend down
  renders the error page, never a blank one)

### Autonomy limits
N/A — this is a read-only UI, no autonomous action.

### Risks
Low — read-only view of already-generated, non-sensitive demo data.

### How it's evaluated
Manual check against the acceptance criteria above (visual/UI feature —
no automated test suite required for the 90-minute scope).
The backend endpoints added in T0 are covered by pytest
(`tests/test_api.py`). The Astro pages are verified by `npm run build` +
`npx astro check` per task plus the manual acceptance-criteria check
above.
