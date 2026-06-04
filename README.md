# 🐙 FifaOctopus

**A swarm-intelligence prediction engine for the FIFA World Cup 2026.**

Five specialised AI agents — each drawing on a different data source — run in parallel to predict every match of the tournament, from the 72 group-stage fixtures all the way to the Final.

---

## Overview

FifaOctopus is architected in the same style as [MiroFish](https://github.com/666ghj/MiroFish): seed data feeds a knowledge layer, a swarm of agents processes it in parallel, and an aggregator synthesises the results into a single prediction with a human-readable narrative.

```
User request
    │
    ▼
SwarmOrchestrator  ──── spawns parallel threads ────►  StatisticalAgent  (weight 1.8×)
    │                                                   VideoAgent        (weight 1.0×)
    │                                                   FormAgent         (weight 1.3×)
    │                                                   TacticalAgent     (weight 1.2×)
    │
    └──► AggregatorAgent  ──► confidence-weighted ensemble
                          ──► LLM narrative synthesis (optional)
                          ──► MatchPrediction
```

### Match result rules

| Stage | Draws |
|---|---|
| **Group stage** | ✅ Allowed — both teams earn 1 point |
| **Round of 32 → Final** | ❌ Not allowed — draw after 90 min goes to Extra Time, then Penalties |

The swarm predicts the **90-minute result** (win / draw / loss probabilities). In the knockout simulator, any predicted draw is resolved by a probability-weighted coin flip that models the penalty shootout.

---

## Swarm Agents

| Agent | Weight | Data source | Signal |
|---|---|---|---|
| **StatisticalAgent** | 1.8× | SofaScore ELO + attack/defence ratings | Poisson goal model blended with ELO win probability |
| **VideoAgent** | 1.0× | YouTube Data API v3 | Highlight engagement ratios + title sentiment + tactical momentum |
| **FormAgent** | 1.3× | SofaScore last-10-match form points | Form trajectory → adjusted expected goals |
| **TacticalAgent** | 1.2× | Style-matchup matrix | high-press vs counter, gegenpressing vs possession, etc. |
| **AggregatorAgent** | — | All of the above | Confidence-weighted ensemble + optional LLM narrative |

All agents run **concurrently in separate threads**. The aggregator waits for all results, then produces:

- Home win / Draw / Away win probabilities
- Most likely scoreline
- Predicted outcome (with AET/PKs annotation in knockout rounds)
- Per-agent reasoning breakdown
- Key factors
- Swarm consensus narrative (requires `LLM_API_KEY`)

---

## FIFA World Cup 2026

The first 48-team World Cup, hosted across **USA 🇺🇸 · Canada 🇨🇦 · Mexico 🇲🇽**.

```
48 teams  →  12 groups of 4
Group stage: 72 matches (round-robin within each group)

Advance: top 2 per group (24 teams) + 8 best 3rd-place teams = 32 teams

Round of 32  →  16 winners
Round of 16  →  8 winners
Quarter-Finals  →  4 winners
Semi-Finals  →  2 winners
──────────────────────────────
3rd Place Play-off + Final
──────────────────────────────
Total: 104 matches
```

### Groups

| Group | Teams |
|---|---|
| A | USA · Panama · Algeria · New Zealand |
| B | Mexico · Jamaica · Venezuela · South Africa |
| C | Canada · Honduras · Czech Republic · Mali |
| D | Argentina · Chile · Ecuador · Indonesia |
| E | Brazil · Paraguay · Colombia · Ivory Coast |
| F | France · Belgium · Morocco · Tunisia |
| G | Spain · Croatia · Serbia · Egypt |
| H | England · Slovakia · Romania · Cameroon |
| I | Germany · Austria · Hungary · Ghana |
| J | Portugal · Poland · Turkey · Uruguay |
| K | Netherlands · Denmark · South Korea · Nigeria |
| L | Japan · Iran · Australia · Georgia |

---

## Quick Start

### Prerequisites

| Tool | Version |
|---|---|
| Python | ≥ 3.11, ≤ 3.12 |
| Node.js | ≥ 18 |

### 1. Configure environment

```bash
cp .env.example .env
# Open .env and fill in at minimum:
#   LLM_API_KEY  — any OpenAI-compatible key (optional but enables narrative synthesis)
#   YOUTUBE_API_KEY  — YouTube Data API v3 key (optional; synthetic data used if absent)
```

### 2. Install dependencies

```bash
npm run setup:all      # installs both Python and Node packages
```

Or step by step:

```bash
cd backend && pip install -r requirements.txt
cd frontend && npm install
```

### 3. Start services

```bash
npm run dev
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3001 |
| Backend API | http://localhost:5002 |

---

## Usage

### Command-line example script

Predict a random group-stage match — no server required:

```bash
cd /path/to/FifaOctopus

# Random match (new fixture every run)
python3 backend/examples/predict_random_match.py

# Reproducible random pick
python3 backend/examples/predict_random_match.py --seed 17

# Specific fixture
python3 backend/examples/predict_random_match.py --home France --away Morocco

# With LLM narrative synthesis
LLM_API_KEY=sk-... python3 backend/examples/predict_random_match.py --seed 7
```

#### Example output — Group L: Japan vs Iran (seed 17)

```
══════════════════════════════════════════════════════════════
  🐙  FifaOctopus — Swarm Match Prediction
  FIFA World Cup 2026 · Group L · Group Stage · Draws allowed — 1pt each
══════════════════════════════════════════════════════════════

                          HOME        AWAY
                         Japan   vs   Iran
                      ELO 1895        ELO 1835
                      FIFA #15        FIFA #24
                    high-press        defensive

  SWARM PROBABILITIES

  Japan win   ██████████░░░░░░░░░░  49.2%
  Draw         ███░░░░░░░░░░░░░░░░░  15.3%
  Iran win    ███████░░░░░░░░░░░░░  35.5%

  Predicted score   :  1-1
  Predicted outcome :  Japan WIN
  Points awarded    :  Japan +3pt  /  Iran +0pt
  Swarm confidence  :  ★★★☆☆  (65%)

  AGENT BREAKDOWN

  ▸ Statistical Analysis Agent
    H 49.9%  D 16.9%  A 33.2%  │  xG 1.3–1.0  │  conf 78%  ← HOME
    → ELO Japan=1895 vs Iran=1835 (Δ+60). Poisson model.
      H2H win-rate 0.58 for Japan.

  ▸ Tactical Analysis Agent
    H 48.0%  D 30.0%  A 22.0%  │  xG 1.0–0.8  │  conf 60%  ← HOME
    → Japan high-press has a tactical edge over Iran defensive.

  ▸ Recent Form Agent
    H 49.2%  D 7.4%  A 43.3%  │  xG 1.6–1.2  │  conf 65%  ← HOME
    → Japan 18/30 form points vs Iran 15/30 (last 10 matches).

  ▸ Video Intelligence Agent
    H 48.9%  D 4.8%  A 46.4%  │  xG 1.7–1.3  │  conf 58%  ≈ EVEN
    → 5 YouTube videos. Neither side has a clear momentum edge.
```

### Frontend

The Vue 3 frontend has three views:

| View | Path | Description |
|---|---|---|
| **Groups** | `/groups` | Browse all 12 groups with ELO and FIFA rankings |
| **Predict Match** | `/predict` | Select any two teams, run the swarm, see the full breakdown |
| **Tournament** | `/tournament` | Simulate the entire 104-match bracket — fast (Monte Carlo) or full swarm |

### REST API

```
POST /api/predictions/match
Body: { "home_team": "France", "away_team": "Morocco", "stage": "group", "group": "F" }

POST /api/predictions/tournament
Body: { "use_swarm": false }      ← true uses full swarm per match (slow)

GET  /api/predictions/tournament/<sim_id>
GET  /api/predictions/teams
GET  /api/predictions/groups
GET  /health
```

#### Single-match response shape

```json
{
  "prediction_id": "pred_a1b2c3d4e5",
  "home_team": "France",
  "away_team": "Morocco",
  "stage": "group",
  "group": "F",
  "home_win_prob": 0.601,
  "draw_prob": 0.184,
  "away_win_prob": 0.215,
  "predicted_home_goals": 1.72,
  "predicted_away_goals": 0.94,
  "most_likely_score": "2-1",
  "outcome": "home_win",
  "went_to_penalties": false,
  "overall_confidence": 0.68,
  "agent_predictions": [ ... ],
  "swarm_consensus": "France enter this fixture as clear favourites ...",
  "key_factors": [ "ELO gap of 175 points favours France", "... " ]
}
```

For knockout matches that go to penalties, `went_to_penalties` is `true` and `most_likely_score` is annotated, e.g. `"1-1 (AET/PKs)"`.

---

## Example Tournament Prediction

Running the full simulation (seed 42, Monte Carlo mode):

```
🏆  CHAMPION    Argentina
🥈  Runner-Up   Portugal
🥉  3rd Place   France
4️⃣   4th Place   Uruguay

Champion probability in Final: 51%
Total matches simulated: 104
```

**Knockout path to the title:**

```
Round of 32   Argentina 2-1 Colombia        (H 57% / D 14% / A 29%)
Round of 16   Argentina 1-2 Ecuador         → Argentina  (H 25% / D 14% / A 61%)
Quarter-Final Argentina 1-2 USA             → Argentina  (H 26% / D 14% / A 60%)
Semi-Final    Argentina 2-2 France          → Argentina  (AET/PKs, H 45%)
Final         Argentina 2-2 Portugal        → Argentina  (AET/PKs, H 51%)
```

---

## Configuration

All settings are via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `LLM_API_KEY` | — | OpenAI-compatible key. If unset, narrative synthesis is skipped. |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Any OpenAI-format endpoint (GPT-4o, Claude proxy, Qwen, etc.) |
| `LLM_MODEL_NAME` | `gpt-4o` | Model to use for AggregatorAgent narrative |
| `YOUTUBE_API_KEY` | — | YouTube Data API v3. If unset, VideoAgent uses synthetic ELO-based scores. |
| `PORT` | `5002` | Backend port |
| `SWARM_PARALLEL_AGENTS` | `5` | Max concurrent agent threads per prediction |
| `SWARM_TIMEOUT_SECONDS` | `60` | Per-match swarm timeout |

### Running without any API keys

The system is fully functional with no keys set:

- **StatisticalAgent**, **FormAgent**, **TacticalAgent** use the embedded static dataset (60 teams, ELO ratings, attack/defence stats, form points as of mid-2025).
- **VideoAgent** falls back to ELO-derived synthetic engagement scores.
- **AggregatorAgent** uses a rule-based fallback narrative instead of the LLM.

---

## Project Structure

```
FifaOctopus/
├── backend/
│   ├── run.py                          # Flask entry point (port 5002)
│   ├── requirements.txt
│   ├── app/
│   │   ├── config.py
│   │   ├── api/
│   │   │   └── predictions.py          # REST API endpoints
│   │   ├── models/
│   │   │   └── match.py                # MatchPrediction, GroupStanding, TournamentResult
│   │   ├── services/
│   │   │   ├── swarm_orchestrator.py   # Parallel agent dispatch
│   │   │   ├── tournament_simulator.py # Full 104-match WC bracket
│   │   │   ├── agents/
│   │   │   │   ├── base_agent.py
│   │   │   │   ├── statistical_agent.py
│   │   │   │   ├── video_agent.py
│   │   │   │   ├── form_agent.py
│   │   │   │   ├── tactical_agent.py
│   │   │   │   └── aggregator_agent.py
│   │   │   └── data_collectors/
│   │   │       ├── sofascore_collector.py   # SofaScore public API + static fallback
│   │   │       └── youtube_collector.py     # YouTube Data API v3 + synthetic fallback
│   │   └── utils/
│   │       ├── llm_client.py           # OpenAI-compatible LLM wrapper
│   │       └── logger.py
│   └── examples/
│       └── predict_random_match.py     # Standalone CLI demo
└── frontend/
    └── src/
        ├── views/
        │   ├── Home.vue
        │   ├── GroupsView.vue
        │   ├── PredictView.vue
        │   └── TournamentView.vue
        └── router/index.js
```

---

## Inspiration

FifaOctopus is named after **Paul the Octopus** 🐙, the common octopus who correctly predicted 8 out of 8 FIFA World Cup 2010 match outcomes, including the Final. He remains the most accurate World Cup predictor on record.

The engine's architecture is inspired by [MiroFish](https://github.com/666ghj/MiroFish) — a general-purpose swarm intelligence simulation engine — adapted here for sports prediction using live statistical and video data sources.
