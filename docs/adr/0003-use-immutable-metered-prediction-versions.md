---
status: accepted
date: 2026-07-26
---

# Use immutable metered prediction versions

Premier League Match Predictions and League Simulations will be generated on
demand, cached by a fingerprint of their source data and configuration, and
stored as immutable versions. A user spends the relevant allowance once to
reveal a version and retains access to it across later versions and Competition
Editions. The account history exposes all personally revealed versions, while
the Projected Table also provides an edition-local version selector.

League Simulations preserve completed results and use cached Fixture scoreline
distributions for 10,000 Monte Carlo completions. Aggregate probabilities come
from all runs and one seeded representative run supplies a coherent projected
table and remaining-fixture results. During live play, the current score is
explicitly treated as final for that Projection Version; score or status
changes create a new source version, while clock changes alone do not.

Match markets and Competition futures consume their own market allowances and
may reuse cached prediction inputs, but they do not unlock detailed Match
Predictions or Projected Tables. Reopening the same generated market version is
free. Generation first attempts to refresh stale ESPN data, consumes no
allowance on failure, and is blocked only when the refresh fails and the prior
snapshot exceeds its configured stale limit.
