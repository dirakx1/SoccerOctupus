# League forecast calibration

This process applies to the Premier League edition only. It does not alter the
World Cup prediction pipeline.

## What is captured

The active-league systemd timer runs `league-refresh-active` every five
minutes. When it observes a scheduled fixture no more than 35 minutes before
kickoff (normally inside the 30-minute match window), it saves exactly one
record in:

```text
backend/data/leagues/premier-league/<season>/forecasts.json
```

Each record contains the pre-kickoff ESPN baseline, all provider evidence and
availability states, the league swarm result, model versions, and the capture
time. Once ESPN reports a completed result, the same record receives the final
score and outcome. Forecast fields are not rewritten.

## Operating it

1. Install and enable `socceroctupus-league-refresh.timer` as described in
   [the deployment guide](../deploy/README.md#8a-schedule-active-league-refresh).
2. Confirm it runs before a match with `journalctl -u
   socceroctupus-league-refresh.service -f`.
3. After fixtures finish, use the resolved ledger records to compare every
   provider candidate against the ESPN baseline.
4. Select a provider weight on older resolved records, freeze it, and verify it
   on a later untouched set of resolved records.
5. Apply a non-zero weight only when it improves log loss and Brier score with
   a positive 95% paired-bootstrap confidence interval. Otherwise leave it at
   zero.

## Important limits

- Never fetch provider evidence after a match to fill an old ledger entry; that
  would introduce hindsight.
- A provider being available does not mean it influences the prediction. It
  must pass the admission test first.
- The first 14 EPL matches of 2026-27 have no pre-kickoff provider snapshots,
  so they remain useful only for the ESPN baseline backtest.
