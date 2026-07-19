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

**Tournament Simulation**:
A predicted progression through the remaining Knockout Bracket of a Competition
Edition, while preserving official results already played.
_Avoid_: Match Prediction, bracket prediction

**Swarm Agent**:
A specialised predictor that evaluates a defined evidence source or analytical
perspective.
_Avoid_: Bot, model when referring to one specialist role

**Swarm Consensus**:
The combined prediction and explanation produced from the weighted outputs of
the Swarm Agents.
_Avoid_: Average, final agent

**Market Question**:
A contract-shaped question derived from a Match Prediction or Tournament
Simulation for use with a prediction-market platform.
_Avoid_: Bet, wager, bookmaker line

## Presentation

**Locale**:
The user's language and cultural formatting context for interface text, dates,
numbers, and generated narrative.
_Avoid_: Language when formatting behaviour is also meant
