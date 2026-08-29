## Tasks: 002-frontend-dashboard

- [ ] T1 — `frontend/src/styles/tokens.css`: brand palette as CSS
      variables (header/accent #a26769, bg #f5f3f4, status colors)
- [ ] T2 — `StatusBadge.astro`: renders resolved/pending/escalated with
      the correct token colors
- [ ] T3 — `TicketCard.astro`: subject, timestamp, status badge, links to
      detail page
- [ ] T4 — `SourceCitation.astro`: doc id + excerpt from retrieval
- [ ] T5 — `DecisionPanel.astro`: action, reasoning, drafted text
- [ ] T6 — `pages/index.astro`: dashboard, fetches `GET /tickets`, renders
      `TicketCard` list, empty state if none
- [ ] T7 — `pages/tickets/[id].astro`: fetches `GET /tickets/{id}`,
      renders ticket + `SourceCitation`s + `DecisionPanel`
- [ ] Validate against acceptance criteria in spec.md
- [ ] Update roadmap.md — move 002-frontend-dashboard to Done (or Backlog
      if the 90 minutes run out before this feature)
