# Plan 006: Deliver the full Premier League intelligence experience

> **Executor instructions**: Follow this plan step by step in the current shared
> working tree. Run every verification command and confirm the expected result
> before moving on. If a STOP condition occurs, stop and report; do not
> improvise. The reviewer maintains `plans/README.md`. Do not commit.
>
> **Drift check (run first)**: `git status --short && git diff --check`
> This plan is intentionally written against the current uncommitted EPL
> implementation layered on commit `23f6049`. Confirm the named current-state
> symbols and files exist before editing.

## Status

- **Priority**: P1
- **Effort**: L
- **Risk**: MED
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `23f6049`, 2026-08-30, plus the current uncommitted EPL layer

## Why this matters

The current Premier League workspace proves the competition/data abstraction,
scheduled ESPN refresh, baseline Poisson prediction, and season simulation, but
its user experience is a thin diagnostic surface. The client wants the same
depth experienced on the World Cup prediction and markets pages: likely score,
expected goals, probability visualization, scoreline distribution, key factors,
source-backed reasoning, full match contracts, season futures, and a meaningful
projected table. This milestone delivers that depth without allowing unproven
FotMob, YouTube, Zep, 365Scores, SofaScore, or Opta signals to silently change
the admitted ESPN-based probabilities.

## Product decisions and vocabulary

- Use the `CONTEXT.md` terms Competition Edition, Competition Workspace, Match
  Prediction, League Table, Market Question, and supporting evidence.
- Match the accepted Tournament Atlas direction in
  `docs/adr/0001-tournament-atlas-design-direction.md`: competition-first shell,
  editorial hierarchy, dense scannable data, semantic tokens, light/dark themes,
  localization, real data, and complete states.
- World Cup behavior and source files are reference implementations, not edit
  targets. Do not change World Cup API response shapes, simulations, agents, or
  views.
- EPL external providers remain evidence-only. Call their UI entries “analysis
  signals” or “provider evidence”, not numerical swarm agents. No provider may
  alter probabilities unless the persisted admission report passes.
- A forecast must be fixture-bound and created before kickoff. Never reconstruct
  historical forecasts using data fetched after kickoff.
- “Confidence” means the model's dominant outcome probability, not empirical
  calibration. Display it as model confidence and show the model version.

## Current state

- `backend/app/leagues/prediction.py:41-62,112-177` computes outcome
  probabilities, likely score, expected goals, confidence, BTTS, over/under 2.5,
  clean sheets, and evidence inputs. It does not return top scoreline
  probabilities or structured analysis signals.
- `backend/app/leagues/prediction.py:180-225` samples only W/D/L for the remaining
  season. Simulated goals are not added to GF/GA, so future goal difference never
  participates correctly in tied-table ordering.
- `backend/app/api/leagues.py:170-207` binds predictions to canonical scheduled
  fixtures and adds provider evidence without changing probabilities.
- `backend/app/api/leagues.py:228-262` computes fixture markets and season
  probabilities, but fixture rows are compact probability dictionaries rather
  than Market Questions.
- `frontend/src/views/LeaguePredictView.vue` renders only H/D/A plus compact
  provider rows, although the response already contains more fields.
- `frontend/src/views/LeagueMarketsView.vue` discards `fixtureMarkets` and renders
  only champion/top-four/relegation columns.
- `frontend/src/views/LeagueTableView.vue` renders only current position, club,
  points, and goal difference.
- `frontend/src/views/PredictView.vue:138-224`, `frontend/src/views/MarketsView.vue`,
  `frontend/src/components/ProbMeter.vue`, `frontend/src/components/MarketCard.vue`,
  and `frontend/src/ui/patterns/AtlasPageHeader.vue` demonstrate the required
  hierarchy, robust states, data formatting, and reusable presentation patterns.
- `backend/app/leagues/evidence.py:52-72,430-457` already normalizes provider,
  status, source, fetched time, reason, and evidence with a pre-kickoff cutoff.
- `backend/app/leagues/fotmob.py:232-378` demonstrates the existing log-loss,
  Brier, calibration, coverage, and paired-bootstrap vocabulary.
- `backend/app/leagues/cli.py:83-170` and the systemd timer refresh the active
  edition every five minutes around match windows.

## Commands

| Purpose | Command | Expected |
|---|---|---|
| Backend focused | `backend/venv/bin/python -m pytest backend/tests/test_league_seasons.py backend/tests/test_league_evidence.py backend/tests/test_league_fotmob.py backend/tests/test_league_refresh.py -q` | all pass |
| Backend full | `backend/venv/bin/python -m pytest backend/tests -q` | all pass |
| Frontend focused | `cd frontend && npm test -- --run src/views/LeaguePredictView.test.js src/views/LeagueTableView.test.js src/views/LeagueMarketsView.test.js` | all pass |
| Frontend full | `cd frontend && npm test` | all pass |
| Frontend build | `cd frontend && npm run build` | exit 0 |
| Diff hygiene | `git diff --check` | no output |

## Scope

**In scope**:

- `backend/app/leagues/prediction.py`
- New small league-only modules under `backend/app/leagues/` when needed for
  analysis, Market Questions, or forecast history
- `backend/app/api/leagues.py`
- `backend/app/leagues/cli.py`
- Existing league tests and at most three focused new league test files
- `frontend/src/views/LeagueOverviewView.vue`
- `frontend/src/views/LeaguePredictView.vue`
- `frontend/src/views/LeagueTableView.vue`
- `frontend/src/views/LeagueFixturesView.vue` only if fixture filtering/grouping
  is required by the final experience
- `frontend/src/views/LeagueMarketsView.vue`
- Focused tests for those league views
- `frontend/src/i18n/locales/en/competitions.json`
- `frontend/src/i18n/locales/es/competitions.json`
- `frontend/src/components/MarketCard.vue` only to add generic league prop labels
  without changing existing World Cup rendering
- `deploy/README.md` only if the forecast-recording behavior changes timer
  operations

**Out of scope**:

- All World Cup views, APIs, agents, tournament simulator, static datasets, and
  graph builder behavior
- Billing limits, subscription tiers, Clerk/authentication, admin settings
- New providers, paid data subscriptions, or changes to provider credentials
- Numerical admission of FotMob or any other evidence source
- A new frontend framework, design system, state library, task queue, cache,
  scheduler, or database migration
- La Liga/Bundesliga instances in this milestone

## Steps

### Step 1: Enrich the fixture-bound league prediction contract

Extend the league-only model/API response with:

- normalized `outcome` (`home_win`, `draw`, `away_win`)
- top five `scoreProbabilities` derived from the same Poisson grid
- existing likely score, xG, confidence, and markets retained
- structured `analysis` containing a concise deterministic summary, 3-6 key
  factors, and model signals for statistical strength, recent-five form, home
  advantage, and promoted-team prior
- each signal must include a name, direction (`home`, `away`, `neutral`), short
  reasoning, and explicit sources; it must not invent independent probabilities
- provider evidence remains separately identified with status/source/fetchedAt/
  reason and is summarized into the narrative without numerical adjustment

Keep the response backward compatible for the already implemented league UI
fields. Do not call the World Cup `SwarmOrchestrator`.

**Verify**: focused backend tests prove probabilities sum to one, scoreline rows
are ordered and derived from returned xG, fixture identity cannot be overridden,
provider evidence does not change probabilities, and past fixtures remain
rejected.

### Step 2: Make season projection simulate goals and expose uncertainty

Change `project_table` to sample home and away goals from the returned expected
goals for every remaining fixture, then update points, GF, and GA. Rank by
points, goal difference, then goals for. Preserve deterministic seeds.

Add per-team position counts and return:

- expected points and expected position
- most likely position
- a central finishing range (document the percentile definition)
- position distribution for 1..number of clubs
- champion, top-four, and relegation probabilities

Do not add UEFA coefficient or cup-dependent European qualification rules; use
the explicitly named top-four band for this edition.

**Verify**: one focused test proves sampled goals change GF/GA tie-breaking and
another proves identical seed/input returns identical projection output. Avoid
a large statistical matrix.

### Step 3: Generate league-safe Market Questions

Add a league-only generator that emits the existing `MarketCard`-compatible
contract shape without changing the World Cup generator. For a selected
scheduled fixture generate home win, away win, draw, BTTS, over 1.5/2.5/3.5,
both clean sheets, and most-likely correct score. Use the canonical kickoff as
resolution date/time and ESPN results as the resolution source. IDs must include
competition, edition, fixture ID, and prop so they are stable and unique.

For season futures generate champion, top-four, and relegation questions from
the goal-level projection. Label Kalshi/Polymarket values as model-implied fair
prices, not live exchange prices and not bookmaker odds.

Expose a fixture-bound match-market endpoint and keep the season-market endpoint
backward compatible. Reuse existing feature-limit categories and release a
reservation on invalid fixture/provider errors.

**Verify**: focused API tests cover one match question set, one season question,
canonical resolution metadata, and invalid/past fixture rejection.

### Step 4: Record and reconcile an honest forecast history

Create an edition-scoped JSON forecast ledger written atomically by the existing
scheduled refresh command. During the pre-match timer window, store at most one
immutable forecast per fixture/model version when kickoff is still in the
future. After ESPN marks a fixture completed, append actual score/outcome fields
without rewriting the original forecast probabilities or generated timestamp.

Compute resolved-sample log loss, multiclass Brier score, top-label calibration
error, correct-outcome rate, sample size, and status (`insufficient` below 30
resolved forecasts; `available` otherwise). Add a read-only accuracy endpoint.
Do not backfill forecasts for already-played fixtures and do not use current
evidence to fabricate past predictions.

**Verify**: one main-path test snapshots a future fixture, reconciles it after a
completed refresh, and confirms immutable original probabilities; one failure
path proves a past fixture with no stored forecast is never backfilled.

### Step 5: Deliver World Cup-level league screens

Rebuild the league views with existing Tournament Atlas tokens/components and
complete loading, empty, error, retry, and billing-limit states.

Prediction screen:

- fixture selector grouped/scannable by matchweek/date
- match scoreboard and likely score
- H/D/A probability meter without fake agent-convergence data
- model confidence/version and expected goals
- top-five scoreline probabilities
- BTTS, totals, and clean-sheet markets
- deterministic summary, key factors, model-signal cards
- provider evidence drawer/timeline with admitted/unavailable/excluded/error,
  source and freshness; clear note that external context is evidence-only

Table screen:

- full current table columns (P/W/D/L/GF/GA/GD/Pts)
- current/projected presentation
- expected position/points, finishing range, and title/top-four/relegation
  probabilities
- a selected-team position-distribution detail
- current standings remain usable publicly; authenticated projection failure
  gets an explicit sign-in/plan/error state rather than hiding current data

Markets screen:

- upcoming fixture selector and generated match Market Questions rendered with
  `MarketCard`
- filters for winner/draw/BTTS/totals/clean-sheet/correct-score
- season futures section for champion/top four/relegation
- model-implied price and ESPN resolution disclosure

Overview screen:

- current snapshot summary, top-five table, next fixtures, model version/data
  freshness, and forecast-record sample/status
- clear routes to Table, Fixtures, Prediction, and Markets

All new user-facing copy must use English and Spanish locale files. Do not add
hardcoded English strings to the league views. Match the World Cup page's
information hierarchy, but do not copy tournament-only stage/bracket concepts.

**Verify**: focused Vue tests assert substantive rendered output and error/
loading behavior, route compatibility remains green, then full Vitest and the
production build pass.

### Step 6: End-to-end acceptance

Use the Flask test client with a test user to verify active and dated EPL routes,
one scheduled-fixture prediction, match Market Questions, projection, season
futures, and accuracy response. Confirm `adjustmentsApplied=false` remains true
for the current admission report.

Run all commands in the Commands table. Review `git diff --check`, confirm no
World Cup source file changed, and remove debug artifacts.

## Test plan

- Follow `backend/tests/test_league_evidence.py` for authenticated league API
  tests and provider isolation.
- Follow `backend/tests/test_league_refresh.py` for temporary edition JSON and
  scheduler tests.
- Follow `frontend/src/views/PredictView.test.js` and
  `frontend/src/views/MarketsView.test.js` for meaningful rich-result and billing
  states, adapted to league endpoints and vocabulary.
- Add only tests that prove the accepted behavior above; do not build a broad
  new test framework or snapshot suite.

## Done criteria

- [ ] EPL prediction screen has comparable information depth to the World Cup
  prediction screen without presenting evidence providers as calibrated agents.
- [ ] Projection samples goals and updates GF/GA before tie-breaking.
- [ ] Match and season Market Questions have stable IDs, fair prices, and ESPN
  resolution metadata.
- [ ] Pre-kickoff forecasts are immutable and completed results reconcile into
  honest accuracy metrics; no historical forecast fabrication exists.
- [ ] EPL overview/table/predict/markets have localized complete states in EN/ES.
- [ ] Current and dated EPL editions continue to work.
- [ ] FotMob numerical adjustment remains disabled unless the existing persisted
  gate passes.
- [ ] Focused and full backend/frontend tests pass; frontend production build
  passes; `git diff --check` is clean.
- [ ] No World Cup behavior/source files, billing/auth rules, or unrelated files
  are changed.

## STOP conditions

Stop and report instead of improvising if:

- Existing EPL files or API shapes materially differ from the Current state.
- Completion appears to require changing World Cup behavior, billing policy,
  authentication, or provider credentials.
- Any external evidence must be allowed to alter probabilities to satisfy a UI
  requirement.
- Forecast history cannot be made immutable and pre-kickoff with the existing
  single-host scheduled refresher.
- An in-scope verification fails twice after a focused correction.

## Maintenance notes

- New leagues should reuse the league prediction/analysis/markets/forecast
  contracts with edition metadata; avoid adding Premier League names inside the
  generic backend modules.
- If a numerical provider candidate is proposed later, evaluate it against the
  immutable forecast ledger and historical holdout before changing the admitted
  model.
- If production moves from one EC2 host to multiple writers, replace the JSON
  forecast ledger with database-backed idempotent storage before enabling more
  than one scheduler.
