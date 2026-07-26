# SoccerOctopus Domain Language

SoccerOctopus provides football predictions, competition simulations, and
prediction-market questions across multiple football competitions. This
glossary defines the language used in product, design, code, and documentation.

## Competitions

**Competition**:
A named football competition whose rules and identity persist across editions,
such as the FIFA World Cup or the English Premier League.
_Avoid_: Tournament when referring to leagues, event, product

**Competition Edition**:
One scheduled occurrence of a Competition, such as FIFA World Cup 2026 or
Premier League 2026-27.
_Avoid_: Season when referring to every format, competition instance

**Current Competition Edition**:
The Competition Edition designated as the present edition of a Competition.
It changes as that Competition progresses from one edition to the next.
_Avoid_: Current season, latest competition

**Prediction Window**:
The part of a Competition Edition during which new Match Predictions,
Competition Simulations, and Market Questions may be generated.
_Avoid_: Active season, betting window

**Competition Format**:
The structure used by a Competition Edition, such as a league, group-and-knockout
tournament, or knockout tournament.
_Avoid_: Competition type, mode

**Competition Capability**:
A user-visible area supported by a Competition Edition, such as groups, table,
fixtures, bracket, predictions, or markets.
_Avoid_: Feature flag, tab

**Competition Workspace**:
The part of the product scoped to one Competition Edition and its available
Competition Capabilities.
_Avoid_: Dashboard, tournament page

**Team**:
A football club or national side with an identity that persists across
Competition Editions and data providers.
_Avoid_: Squad, provider team, display name

**Fixture**:
A scheduled pairing of two Teams within a Competition Edition whose identity
persists through postponement, rescheduling, and data-provider changes.
_Avoid_: Provider event, prediction, kickoff

**Matchweek**:
The official round of league Fixtures to which a Fixture remains assigned even
if its kickoff is postponed or rescheduled.
_Avoid_: Calendar week, date range

**Group Stage**:
A tournament phase that divides Teams into groups before qualification to a
later phase.
_Avoid_: League table

**League Table**:
The ordered standings for a league-format Competition Edition.
_Avoid_: Groups, bracket

**Knockout Bracket**:
The ordered knockout rounds and Matches that lead to a champion.
_Avoid_: Tournament when referring specifically to knockout progression

## Predictions

**Match Prediction**:
The model output for one Match, including outcome probabilities, a likely
score, confidence, and supporting evidence.
_Avoid_: Bet, pick, tip

**Match Prediction Version**:
An immutable, timestamped Match Prediction for a Fixture associated with the
evidence and prediction model available when it was generated.
_Avoid_: Cache entry, latest prediction

**Tournament Simulation**:
A predicted progression through the remaining Knockout Bracket of a Competition
Edition, while preserving official results already played.
_Avoid_: Match Prediction, bracket prediction

**Competition Simulation**:
A format-specific prediction of the remaining course of a Competition Edition,
realized as either a Tournament Simulation or a League Simulation.
_Avoid_: Match Prediction, generic prediction

**League Simulation**:
A probabilistic completion of the remaining fixtures in a league-format
Competition Edition, preserving completed results and producing a projected
final League Table and outcome probabilities.
_Avoid_: Tournament Simulation, season prediction

**Projection Version**:
An immutable, timestamped result of a Competition Simulation associated with
the official results and fixture forecasts available when it was generated.
_Avoid_: Cache entry, generation, latest prediction

**Live Score Assumption**:
The current score of an in-progress Fixture when a League Simulation treats
that score as final for one Projection Version.
_Avoid_: Live result, official result

**Competition Simulation Reveal**:
An allowance-backed authorization that grants a user durable access to a
Projection Version, regardless of the Competition Format that produced it.
_Avoid_: Tournament simulation credit, league simulation credit

**Swarm Agent**:
A specialised predictor that evaluates a defined evidence source or analytical
perspective.
_Avoid_: Bot, model when referring to one specialist role

**Swarm Consensus**:
The combined prediction and explanation produced from the weighted outputs of
the Swarm Agents.
_Avoid_: Average, final agent

**Market Question**:
A contract-shaped question derived from a Match Prediction, Tournament
Simulation, or League Simulation for use with a prediction-market platform.
_Avoid_: Bet, wager, bookmaker line

## Presentation

**Locale**:
The user's language and cultural formatting context for interface text, dates,
numbers, and generated narrative.
_Avoid_: Language when formatting behaviour is also meant
