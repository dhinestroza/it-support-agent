---
name: astro-frontend-tokens
description: How to apply the project's brand design tokens (from constitution/tech-stack.md) inside Astro components. Only relevant if feature 002 gets built.
---

- All colors come from `frontend/src/styles/tokens.css` as CSS custom properties matching the hex values in `tech-stack.md`'s "Brand / design tokens" table — never a hardcoded hex inside a component.
- Status badges always use the paired bg/text tokens (resolved / pending / escalated) — never mix a status color with a different status's text color.
- No default UI-kit blue/purple — if a component needs a neutral accent outside the three statuses, use the brand terracotta (`--color-brand`) at reduced opacity, not a new color.
