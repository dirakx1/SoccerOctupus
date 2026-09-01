# League forecast calibration

This is the operating guide for Premier League, La Liga, and Bundesliga
forecasts. It does not alter the historical World Cup pipeline.

## What runs today

The active numerical core is selected per competition from untouched later
season results:

| Competition | Active core | 2025-26 log loss | 2025-26 Brier |
| --- | --- | ---: | ---: |
| Premier League | Time-decayed Dixon-Coles | 1.0273 | 0.6162 |
| La Liga | Time-decayed Dixon-Coles | 0.9766 | 0.5792 |
| Bundesliga | Online Poisson | 0.9741 | 0.5751 |

The fitted model uses a 240-day half-life, ridge shrinkage, league-specific
home/away scoring rates, and a Dixon-Coles correction for low scores. The
Bundesliga retains the simpler online model because the fitted candidate lost
on later data. Model selection is intentionally league-specific.

Promoted teams start with a conservative penalty. For fitted leagues, their
previous lower-division goals for and against are translated into top-flight
priors with a 35% strength transfer, an attack ceiling at league average, and a
defensive floor at league average. The Bundesliga online model keeps its
validated fixed promoted prior.

Season projections simulate every remaining match. One sampled strength state
is retained for each club throughout a simulation, so uncertainty is coherent
across the season rather than independently redrawn for every match. Final
ranking uses each competition's tie-break order, including La Liga's mini
head-to-head table for clubs level on points. Premier League projections use
points, goal difference, goals scored, head-to-head points, and head-to-head
away goals. Bundesliga projections use points, goal difference, goals scored,
aggregate head-to-head result, head-to-head away goals, and total away goals.
The implementations follow the [Premier League explanation](https://www.premierleague.com/en/news/58905)
and the [DFL competition rules](https://media.dfl.de/sites/2/2026/03/Spielordnung-SpOL-2026-03-06-Stand.pdf).

## Evidence and decisions

All tuning uses only matches that occurred before the predicted kickoff.
Parameters are selected on an older season and judged on a later untouched
season. Lower-division history is labelled by source competition and is used
only for promoted priors, never as ordinary top-flight history.

Free Football-Data opening and closing prices are stored in each historical
season's `market-benchmark.json`. They are evaluation benchmarks only. Closing
prices are never model inputs. On 2025-26, the independent model trails the
market benchmark, so market evidence is the clearest remaining opportunity—but
only timestamped live snapshots from the actual runtime provider may be
admitted.

| Competition | Model LL / Brier | Opening market LL / Brier | Closing market LL / Brier |
| --- | ---: | ---: | ---: |
| Premier League | 1.0273 / 0.6162 | 1.0153 / 0.6100 | 1.0118 / 0.6077 |
| La Liga | 0.9766 / 0.5792 | 0.9641 / 0.5715 | 0.9650 / 0.5717 |
| Bundesliga | 0.9741 / 0.5751 | 0.9533 / 0.5630 | 0.9510 / 0.5618 |

These candidates were tested and remain at zero weight:

| Candidate | Decision |
| --- | --- |
| Extra five-match form term | Rejected for fitted leagues; did not improve development data. Bundesliga's admitted online model retains its existing form term. |
| Rest/congestion term | Rejected; apparent benefit had the wrong sign and was likely schedule-strength confounding. It remains explanatory context only. |
| Temperature calibration | Rejected; small development gains did not remain stable on later data. |
| FotMob rolling xG/shots | Rejected by all three persisted admission reports; paired confidence intervals included zero. Data remains available for future retesting. |
| Arbitrary provider/swarm weights | Prohibited. Availability alone never grants a numerical weight. |

## Immutable live snapshots

The systemd timer runs `league-refresh-active` for each active competition every
30 minutes. At no more than 35 minutes before kickoff it writes exactly one
record to:

```text
backend/data/leagues/<competition>/<season>/forecasts.json
```

The record keeps team identity, the untouched ESPN baseline probabilities,
provider evidence and candidate probabilities, the final swarm result, model
versions, and capture time. When ESPN reports the result, only `actual` is
added; the original forecast is never rewritten. Historical matches must never
be backfilled with post-match provider data.

Run the admission gate after enough records resolve:

```bash
cd backend
./venv/bin/flask --app run.py league-provider-admission --competition premier-league --season 2026-27
./venv/bin/flask --app run.py league-provider-admission --competition la-liga --season 2026-27
./venv/bin/flask --app run.py league-provider-admission --competition bundesliga --season 2026-27
```

Each provider needs at least 60 numeric resolved snapshots. The command selects
a blend weight on all but the final 30 records, then holds out those final 30.
It admits the provider only if both log-loss and Brier improvements have a
positive paired-bootstrap 95% lower bound. The report is written to the
edition's `provider-admission.json`; runtime reads only entries with
`passed: true`. If correlated providers independently pass, only the strongest
holdout performer is retained until a joint blend itself has enough evidence.
Until then every external agent explicitly abstains.

## Rebuilding the evidence

The checked-in datasets make the existing result reproducible:

```bash
cd backend

# Leakage-safe ESPN walk-forward evaluation
./venv/bin/flask --app run.py league-backtest --competition premier-league --season 2025-26
./venv/bin/flask --app run.py league-backtest --competition la-liga --season 2025-26
./venv/bin/flask --app run.py league-backtest --competition bundesliga --season 2025-26

# Historical FotMob candidate data and gate
./venv/bin/flask --app run.py league-fotmob-backfill --competition premier-league
./venv/bin/flask --app run.py league-fotmob-admission --competition premier-league

# Opening/closing market benchmark; repeat with la-liga and bundesliga
./venv/bin/flask --app run.py league-market-benchmark --competition premier-league
```

Do not change a model constant because one current match looks wrong. Re-run
the older-season selection and later-season holdout, compare log loss and Brier,
and preserve the report that supports the decision.

## New season checklist

1. Add one `SeasonSpec` for the new top-flight season, its two prior top-flight
   seasons, and the immediately prior promotion-league season.
2. Run `league-season --action refresh --action activate`; ESPN creates the
   season directory, JSON snapshots, and derived promoted-team IDs.
3. Run `league-backtest` before changing any competition's active core.
4. Keep the 30-minute timer enabled from the first matchday so provider
   snapshots are not lost.
5. Re-run provider admission only after the required immutable sample exists.

The deployment commands and systemd setup are in
[`deploy/README.md`](../deploy/README.md#8b-schedule-active-league-refresh).
