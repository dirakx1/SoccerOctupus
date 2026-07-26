## Agent skills

### Issue tracker

GitHub Issues for `dirakx1/SoccerOctupus`; external PRs are also a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the canonical `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix` labels. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: root `CONTEXT.md` and `docs/adr/`. See `docs/agents/domain.md`.

### Frontend loading states

Use structural skeletons for page-level loading states. Match the final heading,
controls, table, or list geometry so content does not jump after loading. Follow
the League Overview and League Table skeleton tokens and pulse behavior, include
a reduced-motion fallback, and reserve spinners for compact in-control actions.
