---
status: accepted
date: 2026-07-26
---

# Use a generic league competition foundation

Premier League support will be the first use of a shared league-format
foundation rather than a Premier League-specific copy of the World Cup code.
Competition Edition configuration selects shared table, fixture, forecast, and
simulation behavior; a provider adapter normalizes ESPN data so consumers do
not depend on ESPN payloads or identifiers. SoccerOctopus owns stable Team and
Fixture identities, while ESPN is authoritative for official Premier League
standings and supplies fixtures, results, and live states.

The public current workspace is
`/:locale/competitions/:competition`, while immutable edition workspaces and
new APIs use the nested
`/:competition/editions/:edition` hierarchy. Premier League editions are
current from July 1 through June 30, become read-only for new predictive output
when all fixtures are terminal, and retain official data and history afterward.
The existing World Cup routes and implicit APIs remain unchanged in this phase.

Each edition is version-controlled configuration. A developer adds the next
edition, then an idempotent `sync-season` command fetches and stores its ESPN
teams, fixtures, standings, and provider mappings in the target database. This
keeps deployment and annual preparation explicit while allowing Bundesliga,
La Liga, and other league competitions to reuse the foundation later.
