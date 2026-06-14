# 🐙 FifaOctopus

**A swarm-intelligence prediction engine for the FIFA World Cup 2026.**

Seven specialised AI agents — each drawing on a different data source — run in parallel to predict every match of the tournament, from the 72 group-stage fixtures all the way to the Final. A Zep knowledge graph provides shared memory across all agents. An LLM synthesises their outputs into a human-readable match preview.

---

## Overview

FifaOctopus is architected in the same style as [MiroFish](https://github.com/666ghj/MiroFish): seed data is ingested into a **Zep knowledge graph**, a swarm of specialised agents query that graph and their own data sources in parallel, and an aggregator synthesises the results into a single prediction with an LLM-generated narrative.

```
                        ┌─────────────────────────────────┐
                        │     Zep Knowledge Graph         │
                        │  (team profiles · H2H · groups) │
                        └────────────┬────────────────────┘
                                     │ shared read access
                                     ▼
User request ──► SwarmOrchestrator ──┬──► 📊 StatisticalAgent  (weight 1.8×)
                                     ├──► 🎥 VideoAgent         (weight 1.0×)
                                     ├──► 🔥 FormAgent           (weight 1.3×)
                                     ├──► 🧠 TacticalAgent       (weight 1.2×)
                                     ├──► 📡 LiveDataAgent       (weight 1.4×)  FotMob · FlashScore
                                     ├──► 💹 MarketSignalsAgent  (weight 0.8×)  365Scores · Tiki-Taka
                                     └──► ⚽ SquadQualityAgent   (weight 1.1×)  Opta Stats Perform
                                               │
                                               ▼
                                     AggregatorAgent
                                     ├─ confidence-weighted ensemble  (7 agents)
                                     ├─ LLM narrative synthesis       (Claude / GPT-4o)
                                     └─ MatchPrediction
```

### Match result rules

| Stage | Draws |
|---|---|
| **Group stage** | ✅ Allowed — both teams earn 1 point each |
| **Round of 32 → Final** | ❌ Not allowed — draw after 90 min → Extra Time → Penalty shootout |

The swarm predicts the **90-minute result**. In knockout rounds, any predicted draw is resolved by a probability-weighted coin flip that models the penalty shootout.

---

## Swarm Agents

### 📊 StatisticalAgent — weight 1.8×

The highest-weighted agent. Uses ELO ratings and attack/defence metrics from SofaScore to compute win probabilities via a Poisson goal model blended with the ELO formula.

| Statistic | Source | Used for |
|---|---|---|
| World Football **ELO rating** | SofaScore (static dataset) | ELO win probability formula; H2H historical win-rate |
| **Attack rating** (0–100) | SofaScore | Home/away expected-goals lambda |
| **Defence rating** (0–100) | SofaScore | Opponent's expected-goals suppression |
| **Avg goals scored** per match | SofaScore | Poisson lambda calibration |
| **Avg goals conceded** per match | SofaScore | Opponent lambda calibration |
| **FIFA ranking** | SofaScore | Tiebreaker signal |
| **Zep graph context** | Zep Cloud | Richer H2H and team-profile facts at query time |

Model: Poisson probability matrix (goals 0–6) × ELO blend (60/40). H2H nudges the final probability ±5%.

---

### 🎥 VideoAgent — weight 1.0×

Analyses YouTube match highlight videos to measure each team's current public momentum and engagement.

| Statistic | Source | Used for |
|---|---|---|
| **Engagement ratio** (likes ÷ views) | YouTube Data API v3 | Momentum score per team |
| **Title sentiment** (keyword scan) | YouTube video titles | Positive/negative frame around each team |
| **Tactical momentum score** | YouTube search + ELO fallback | Final team momentum signal (0–1) |

Falls back to ELO-derived synthetic engagement scores when no YouTube API key is set.

---

### 🔥 FormAgent — weight 1.3×

Captures recent team momentum from the last 10 official matches.

| Statistic | Source | Used for |
|---|---|---|
| **Form points** (0–30) over last 10 matches | SofaScore | Win/draw/loss probability distribution |
| **Goals scored per match** (form period) | SofaScore | Form-adjusted expected goals |
| **Goals conceded per match** (form period) | SofaScore | Opponent xG suppression |
| **Zep graph context** | Zep Cloud | Enriched form narrative from graph facts |

Converts form points to win/draw/loss rates; adjusts expected goals by form trajectory (±5% per 5 points above/below average).

---

### 🧠 TacticalAgent — weight 1.2×

Evaluates tactical style matchups using a pre-built compatibility matrix.

| Statistic | Source | Used for |
|---|---|---|
| **Playing style** | SofaScore / Zep graph | Style-matchup lookup (high-press, tiki-taka, gegenpressing, counter-attack, defensive, possession, balanced) |
| **Attack rating** (0–100) | SofaScore | xG from attack vs defence strength ratio |
| **Defence rating** (0–100) | SofaScore | xG conceded estimate |
| **Tactical facts** | Zep graph semantic search | Context-aware edge boosts when graph is active |

The style matrix covers 49 style-vs-style combinations. Each pair produces an edge value (−0.15 to +0.15) that shifts win/draw/loss probabilities from the 38/28/34 baseline.

---

### 📡 LiveDataAgent — weight 1.4× *(new)*

The second-highest-weighted agent. Combines **FotMob** deep match statistics with **FlashScore** live/recent form data to capture current team state more accurately than static ELO alone.

#### FotMob statistics

| Statistic | Used for |
|---|---|
| **xG per game** (expected goals) | Primary xG lambda for Poisson model |
| **xG against per game** | Defensive xG suppression |
| **Possession %** | Style confirmation, tempo signal |
| **Shots per game** | Attack volume |
| **Shots on target %** | Finishing quality |
| **PPDA** (passes allowed per defensive action) | Pressing intensity — lower = more aggressive press |
| **Heatmap zones** — attacking third %, middle third %, defensive third %, left wing %, right wing % | Spatial attack profile; high attacking-third % boosts home xG by up to 12% |
| **Average player rating** | Squad quality proxy |

#### FlashScore statistics

| Statistic | Used for |
|---|---|
| **W/D/L form string** (last 6 matches) | Form modifier ±5% on xG |
| **Goals scored** (last 6) | Cross-check on xG calibration |
| **Goals conceded** (last 6) | Defensive form check |
| **H2H record** (last 5 meetings) | 10% blend into final probabilities |
| **H2H recent scores** | Narrative context |

**How the model combines them:**

```
home_xg = fotmob_xg × (1 + form_mod) × (1 + press_boost) × (0.85 + att_zone × 0.35)
Blend: 85% Poisson(home_xg, away_xg) + 10% H2H rate + 5% form differential
```

---

### 💹 MarketSignalsAgent — weight 0.8× *(new)*

The lowest-weighted agent — market signals are valuable but can be biased toward famous teams. Combines **365Scores** bookmaker odds with **Tiki-Taka AI** predictions.

#### 365Scores statistics

| Statistic | Used for |
|---|---|
| **Home decimal odds** | Implied home win probability (1/odds, vig-removed) |
| **Draw decimal odds** | Implied draw probability |
| **Away decimal odds** | Implied away win probability |
| **Bookmaker margin** | Vig normalisation factor |
| **News sentiment score** per team | ±2% probability nudge based on media momentum |
| **Match interest score** | Context signal (big games → more public money influence) |

Vig removal: `implied_prob = raw_prob / (sum_of_raw_probs)`.

#### Tiki-Taka AI statistics

When the Tiki-Taka API is unavailable, falls back to a **Dixon-Coles corrected bivariate Poisson** — a mathematically different approach from StatisticalAgent's plain Poisson that adds genuine signal diversity:

| Parameter | Value | Purpose |
|---|---|---|
| **Alpha** (attack strength) | `team_att / 67` | Attack parameter, normalised to league average |
| **Beta** (defence weakness) | `67 / team_def` | Inverse defence, so weaker defence = higher opponent xG |
| **Home advantage gamma** | `1.08` | 8% expected-goals boost for home side |
| **Rho correction** | `−0.10` | Dixon-Coles adjustment for under-represented low-scoring cells: adjusts P(0-0), P(1-0), P(0-1), P(1-1) |
| **Momentum weight** | `(form_pts − 15) / 30 × 0.06` | ±6% probability shift based on form trajectory |

**Final blend:**

```
hw = 365scores_implied_hw × 0.60 + tikitaka_hw × 0.40  (+ news sentiment nudge ±2%)
```

---

### ⚽ SquadQualityAgent — weight 1.1× *(new — Opta)*

Uses Opta / Stats Perform player statistics to evaluate individual player quality across the starting XI and bench — a dimension none of the other agents see directly.

**API:** Stats Perform REST API (`https://api.performfeeds.com/soccerdata/`) — commercial license required ([developer.statsperform.com](https://developer.statsperform.com/)).  
**Without key:** falls back to a derived model calibrated against published Opta national-team benchmarks for 18 WC-tier teams; interpolates the remaining teams using regression coefficients from those benchmarks.

| Statistic | Source | Used for |
|---|---|---|
| **Avg player Opta rating** (0–10) | Opta Stats Perform | Primary quality signal; drives 35% of composite score |
| **Key passes per game** | Opta | Chance-creation quality (passes that directly create a shot) |
| **Successful dribbles per game** | Opta | Individual flair and ability to beat defenders |
| **Tackles won %** | Opta | Defensive organisation and aggression |
| **Aerial duels won %** | Opta | Physical dominance; set-piece defending/attacking |
| **Set piece conversion rate** | Opta | Goals from corners + direct free kicks per set piece taken |
| **Squad depth score** (0–1) | Opta | Bench quality vs starting XI — fatigue resilience |
| **Pass accuracy %** | Opta | Technical quality under pressure |
| **xG overperformance** | Opta | Goals minus expected goals — clinical finishing above model |
| **Pressing success rate** | Opta | % of pressing actions that recover possession |

**Composite scoring model:**

```
composite = rating_diff × 0.35
          + creation_diff × 0.20          (key passes + dribbles)
          + defence_diff / 100 × 0.15     (tackles + aerials)
          + set_piece_diff × 0.08
          + depth_diff × 0.08
          + pass_acc_diff / 100 × 0.06
          + clinical_diff × 0.05
          + pressing_diff × 0.03

hw = 0.375 + composite × 0.12
aw = 0.375 − composite × 0.12
```

Confidence: `0.78` (live API) · `0.68` (benchmark) · `0.58` (derived interpolation)

---

### AggregatorAgent

Combines all six agents using **confidence-weighted averaging** where each agent's vote is weighted by `agent_weight × agent_confidence`. Calls the LLM to synthesise a 3-sentence match preview from all agent reasonings and extract 3 key factors.

| Agent | Base weight | Typical confidence | Effective weight |
|---|---|---|---|
| StatisticalAgent | 1.8× | 70–82% | ~1.3 |
| LiveDataAgent | 1.4× | 60–65% | ~0.9 |
| FormAgent | 1.3× | 55–72% | ~0.8 |
| TacticalAgent | 1.2× | 60% | ~0.7 |
| SquadQualityAgent | 1.1× | 58–78% | ~0.8 |
| VideoAgent | 1.0× | 55–60% | ~0.6 |
| MarketSignalsAgent | 0.8× | 65–75% | ~0.6 |

---

## Knowledge Layer — Zep Graph

All agents share a **Zep Cloud knowledge graph** (`ZEP_GRAPH_ID`) built once from football seed data. Mirrors MiroFish's GraphRAG pattern exactly.

### Graph content (144 episodes → nodes + edges)

| Episode type | Count | Content |
|---|---|---|
| Team profiles | 60 | ELO, ranking, style, attack/defence, form, confederation |
| Tactical analyses | 60 | Pressing behaviour, zone tendencies, strength description |
| Group contexts | 12 | Group composition, advancement rules, group favourite |
| H2H fixtures | 72 | All group-stage matchup comparisons with ELO context |

### Graph schema

```
Nodes:  NationalTeam · Group
Edges:  beat · plays_in_group · ranked_above
```

### Build the graph (once)

```bash
python3 backend/setup_zep.py
# → prints: graph_id: fifaoctopus_xxxxxxxxxxxx
# Add to .env: ZEP_GRAPH_ID=fifaoctopus_xxxxxxxxxxxx
```

---

## Data Sources — Summary

| Source | Agent | Type | API | Fallback |
|---|---|---|---|---|
| **SofaScore** | Statistical, Form, Tactical | Stats DB | Unofficial public REST | 60-team static dataset |
| **YouTube Data API v3** | Video | Video platform | Official (key required) | ELO-derived synthetic scores |
| **FotMob** | LiveData | Deep match stats | Unofficial public REST | Style + rating estimates |
| **FlashScore** | LiveData | Live scores | Mobile web API | ELO-derived form strings |
| **365Scores** | MarketSignals | Odds + news | Unofficial public REST | ELO → implied odds conversion |
| **Tiki-Taka AI** | MarketSignals | AI predictions | Private (key optional) | Dixon-Coles Poisson model |
| **Opta / Stats Perform** | SquadQuality | Player stats | Commercial (key required) | Calibrated benchmark + derived model |
| **Zep Cloud** | All agents | Knowledge graph | Official (key required) | Static dict lookup |

---

## FIFA World Cup 2026

The first 48-team World Cup, hosted across **USA 🇺🇸 · Canada 🇨🇦 · Mexico 🇲🇽**.

```
48 teams  →  12 groups of 4
Group stage: 72 matches (round-robin within each group)
                                              ↓
Top 2 per group (24) + 8 best 3rd-place teams = 32 teams
                                              ↓
Round of 32  →  16 winners
Round of 16  →  8 winners
Quarter-Finals  →  4 winners
Semi-Finals  →  2 winners
──────────────────────────────────────────────
3rd Place Play-off + Final
──────────────────────────────────────────────
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
```

**Required:**

```env
ZEP_API_KEY=zep-...        # free at https://app.getzep.com/
ZEP_GRAPH_ID=              # filled after step 2
```

**Optional (enable additional data sources):**

```env
LLM_API_KEY=sk-...         # any OpenAI-compatible key; enables LLM narrative
LLM_BASE_URL=https://api.anthropic.com/v1   # or https://api.openai.com/v1
LLM_MODEL_NAME=claude-opus-4-8             # or gpt-4o, qwen-plus, etc.
YOUTUBE_API_KEY=...        # YouTube Data API v3; 10k units/day free
```

### 2. Install dependencies

```bash
npm run setup:all      # Python + Node packages in one command
```

### 3. Build the Zep knowledge graph (once)

```bash
python3 backend/setup_zep.py
# Ingests 144 football knowledge episodes. Takes ~2 min.
# Copy the printed graph_id into .env as ZEP_GRAPH_ID.
```

### 4. Start services

```bash
npm run dev
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3001 |
| Backend API | http://localhost:5002 |

---

## Usage

### Full prediction script (recommended)

```bash
cd /path/to/FifaOctopus

# Random group-stage fixture
python3 backend/examples/predict_full.py

# Specific fixture + stage
python3 backend/examples/predict_full.py --home Brazil --away Spain --stage semi_final
python3 backend/examples/predict_full.py --home Argentina --away France --stage final
python3 backend/examples/predict_full.py --home Germany --away Japan --stage group

# Save result as JSON
python3 backend/examples/predict_full.py --home England --away Portugal \
  --stage quarter_final --out /tmp/result.json

# Skip env check (after first run)
python3 backend/examples/predict_full.py --home Morocco --away USA --no-check
```

Valid `--stage` values: `group` · `round_of_32` · `round_of_16` · `quarter_final` · `semi_final` · `final`

### Example output — Brazil vs Spain, Semi-Final

```
══════════════════════════════════════════════════════════════════
  🐙  FifaOctopus — Full Swarm Match Prediction
  FIFA World Cup 2026  ·  Semi Final
  Knockout — winner by 90 min, AET or PKs
══════════════════════════════════════════════════════════════════

                            HOME         AWAY
                          Brazil   vs   Spain
                        ELO 2050         ELO 2045
                         FIFA #4         FIFA #3
                      high-press         tiki-taka

  SWARM PROBABILITIES

  Brazil win  █████████░░░░░░░░░░░░░  42.2%
  Draw        ████░░░░░░░░░░░░░░░░░░  17.0%
  Spain win   █████████░░░░░░░░░░░░░  40.8%

  Predicted score   :  2-2
  Predicted outcome :  Brazil WIN
  Swarm confidence  :  ★★★☆☆  (65%)
  Swarm time        :  11.5s

  AGENT BREAKDOWN  (6 agents · parallel execution)

  📊  Statistical Analysis Agent  (weight 1.8×)
     H 42.4%  D 16.2%  A 41.4%  │  xG 1.3–1.2  │  conf 71%  ≈ EVEN
     → ELO Brazil=2050 vs Spain=2045 (Δ+5). Poisson λ: 1.26–1.25.
       H2H historical win-rate 0.51 for Brazil.  [Zep graph active]

  🔥  Recent Form Agent  (weight 1.3×)
     H 43.1%  D 7.4%  A 49.5%  │  xG 1.9–2.2  │  conf 68%  AWAY →
     → Form: Brazil 18/30 vs Spain 22/30. Spain in better form (-4 pts).

  🧠  Tactical Analysis Agent  (weight 1.2×)
     H 33.0%  D 30.0%  A 37.0%  │  xG 1.0–1.0  │  conf 60%  ≈ EVEN
     → Spain tiki-taka counter-plays Brazil high-press. Edge: −0.05.

  📡  Live Data Agent  (weight 1.4×)
     H 42.0%  D 18.4%  A 39.6%  │  xG 1.9–2.0  │  conf 60%  ≈ EVEN
     → FotMob xG: Brazil 1.81/game, Spain 1.91/game. Possession: 56%/64%.
       FlashScore form: Brazil WWDWLW (13pt) / Spain WWWWWW (18pt). H2H: 2W-1D-2L.

  💹  Market Signals Agent  (weight 0.8×)
     H 46.5%  D 27.3%  A 26.2%  │  xG 1.3–1.2  │  conf 72%  ← HOME
     → 365Scores odds: Brazil 52.7% / Draw 25.9% / Spain 21.4% (margin 5.0%).
       Tiki-Taka DC model: Brazil 37.4% / Spain 33.2%. Sentiment: Brazil 0.61 / Spain 0.64.

  🎥  Video Intelligence Agent  (weight 1.0×)
     H 47.7%  D 4.8%  A 47.5%  │  xG 2.1–2.2  │  conf 58%  ≈ EVEN
     → Synthetic momentum: Brazil 0.82, Spain 0.82. Neither side has edge.

  ⚽  Squad Quality Agent  (weight 1.1×)
     H 44.2%  D 25.0%  A 30.8%  │  xG 2.0–1.8  │  conf 68%  ← HOME
     → Opta: Brazil 7.20/10 vs Spain 7.31/10 (Δ−0.11). Key passes: 2.8 vs 3.2/game.
       Dribbles: 4.8 vs 4.1/game. Tackles won: 60% vs 61%. Aerials: 55% vs 54%.
       Set pieces: 4.3% vs 4.2%. Pass acc: 77% vs 82%. Depth: 0.89 vs 0.93.
       Composite Opta edge: Spain (−0.042). Data: opta_benchmark/opta_benchmark.

  KEY FACTORS
  •  Spain's tiki-taka dominates possession (64%) and neutralises Brazil's high press
  •  Spain's superior recent form (WWWWWW, 22/30) and higher Opta rating (7.31 vs 7.20) vs Brazil's home advantage
  •  Both sides project >1.9 xG — open, high-scoring contest expected

  SWARM CONSENSUS  (Claude Opus 4.8)
  This is a razor-thin clash between two heavyweights, with Brazil's home
  advantage and dominant H2H record almost perfectly offset by Spain's
  superior current form, higher Opta squad rating (7.31 vs 7.20), and
  greater pass accuracy (82% vs 77%). Spain's tiki-taka and 64% projected
  possession threaten to neutralise Brazil's high press.
```

### Simple match prediction script

```bash
# Random group-stage match with minimal output
python3 backend/examples/predict_random_match.py
python3 backend/examples/predict_random_match.py --seed 17
python3 backend/examples/predict_random_match.py --home France --away Morocco
```

### Frontend

| View | Path | Description |
|---|---|---|
| **Groups** | `/groups` | Browse all 12 groups with ELO and FIFA rankings |
| **Predict Match** | `/predict` | Select any two teams, run the swarm, see full per-agent breakdown |
| **Tournament** | `/tournament` | Simulate the entire 104-match bracket — Monte Carlo or full swarm |
| **📈 Markets** | `/markets` | Generate Kalshi & Polymarket contracts from swarm probabilities |

#### Markets view

Two tabs — **Match Markets** and **Tournament Futures** — each backed by a dedicated REST endpoint.

**Match Markets tab**

1. Select home team, away team, stage
2. Click **Generate Market Questions** → swarm runs → 10 contracts appear
3. Filter cards by prop type: Match Winner · Draw · BTTS · Over/Under · Clean Sheet · Penalties · Exact Score
4. Each card shows:
   - YES / NO probability bars
   - **Kalshi price**: `53.0¢ YES / 47.0¢ NO` (0–100 cents per $1 contract)
   - **Polymarket price**: `$0.5300 YES / $0.4700 NO` (USDC)
   - ▼ Resolution criteria (expandable)
   - Unique ticker ID with one-click copy (e.g. `FIFA26-FRANCE-BEAT-MOROCCO-GROUP`)

**Tournament Futures tab**

1. Click **Generate Futures Markets** → Monte Carlo simulation → 40 contracts appear
2. **Champion odds table** (categorical): all contenders with probability bars and prices
3. Filter by type: Champion · Advancement · Group Winners · Confederation · Host Nation · Penalties
4. Binary cards for every team reaching the Final / Semi-Finals, all group winners, confederation wins, host nation to win, and whether the Final goes to penalties

**Market card — colour coding**

| Prop type | Accent colour |
|---|---|
| Match Winner / Champion | 🟡 Gold |
| Draw / Advancement | 🔵 Blue |
| BTTS / Group Winner | 🟢 Green |
| Over/Under / Host Nation | 🟠 Orange |
| Clean Sheet / Confederation | 🩵 Teal |
| Penalties | 🔴 Red |
| Exact Score | 🟣 Purple |

### REST API

```
POST /api/predictions/match
Body: { "home_team": "France", "away_team": "Morocco", "stage": "group", "group": "F" }

POST /api/predictions/tournament
Body: { "use_swarm": false }       ← true uses full swarm per match (slow)

GET  /api/predictions/tournament/<sim_id>
GET  /api/predictions/graph/status
POST /api/predictions/graph/build  ← rebuilds Zep graph (requires ZEP_API_KEY)
GET  /api/predictions/teams
GET  /api/predictions/groups
GET  /health

# ── Market endpoints ────────────────────────────────────────────────────
POST /api/markets/match
Body: { "home_team": "France", "away_team": "Morocco", "stage": "group",
        "platform": "both" }     ← both | kalshi | polymarket

POST /api/markets/tournament
Body: { "platform": "both" }

GET  /api/markets/types
```

#### Single-match response shape

```json
{
  "prediction_id": "pred_a1b2c3d4e5",
  "home_team": "Brazil",
  "away_team": "Spain",
  "stage": "semi_final",
  "group": null,
  "home_win_prob": 0.422,
  "draw_prob": 0.170,
  "away_win_prob": 0.408,
  "predicted_home_goals": 1.87,
  "predicted_away_goals": 1.94,
  "most_likely_score": "2-2",
  "outcome": "home_win",
  "went_to_penalties": false,
  "overall_confidence": 0.65,
  "agent_predictions": [
    {
      "agent": "Statistical Analysis Agent",
      "home_win_prob": 0.424,
      "draw_prob": 0.162,
      "away_win_prob": 0.414,
      "predicted_score": "1.3-1.2",
      "confidence": 0.71,
      "reasoning": "ELO Brazil=2050 vs Spain=2045 ...",
      "data_sources": ["Zep knowledge graph + SofaScore", "H2H historical"]
    },
    { "agent": "Live Data Agent", "..." },
    { "agent": "Market Signals Agent", "..." }
  ],
  "swarm_consensus": "This is a razor-thin clash ...",
  "key_factors": ["Spain's tiki-taka dominates possession ...", "..."]
}
```

For knockout matches that go to extra time/penalties: `"went_to_penalties": true` and `"most_likely_score": "2-2 (AET/PKs)"`.

#### Market question response shape (`/api/markets/match`)

```json
{
  "match": "France vs Morocco",
  "stage": "group",
  "prediction_summary": {
    "home_win_prob": 0.530,
    "draw_prob": 0.174,
    "away_win_prob": 0.296,
    "most_likely_score": "2-1"
  },
  "total_questions": 10,
  "questions": [
    {
      "question_id": "FIFA26-FRANCE-BEAT-MOROCCO-GROUP",
      "market_type": "binary",
      "question": "Will France beat Morocco in the 2026 FIFA World Cup Group?",
      "short_title": "France beats Morocco – WC26 Group",
      "yes_probability": 0.530,
      "no_probability": 0.470,
      "pricing": {
        "kalshi_yes_cents": 53.0,
        "kalshi_no_cents": 47.0,
        "polymarket_yes_usdc": 0.5300,
        "polymarket_no_usdc": 0.4700
      },
      "resolution": {
        "criteria": "Resolves YES if France has more goals than Morocco after 90 minutes...",
        "source": "FIFA official match results (fifa.com)",
        "date": "2026-07-02"
      },
      "platforms": ["Kalshi", "Polymarket"],
      "prop_type": "match_winner",
      "confidence": 0.650,
      "tags": ["WC2026", "Soccer", "France", "Morocco", "Group", "Match Winner"]
    }
  ]
}
```

**Kalshi-specific format** (`?platform=kalshi`):

```json
{
  "ticker": "FIFA26-FRANCE-BEAT-MOROCCO-GROUP",
  "title": "France beats Morocco – WC26 Group",
  "yes_price_cents": 53.0,
  "no_price_cents": 47.0,
  "close_time": "2026-07-02T23:59:00Z",
  "resolution_rules": "Resolves YES if France has more goals...",
  "resolution_sources": ["FIFA official match results (fifa.com)"],
  "tags": ["WC2026", "Soccer", "France", "Morocco"]
}
```

**Tournament futures response** (`/api/markets/tournament`):

```json
{
  "simulation": {
    "champion": "Argentina",
    "runner_up": "Portugal",
    "third_place": "France",
    "champion_probability": 0.508
  },
  "total_questions": 40,
  "by_type": {
    "tournament_winner": [ ... ],   ← 9 questions (1 categorical + 8 binary)
    "reach_stage":       [ ... ],   ← 12 questions
    "group_winner":      [ ... ],   ← 12 questions (one per group)
    "confederation_win": [ ... ],   ← 3 questions
    "host_nation":       [ ... ],   ← 3 questions
    "penalties":         [ ... ]    ← 1 question (Final to penalties)
  }
}
```

---

## Example Tournament Prediction

Full simulation (seed 42, Monte Carlo mode):

```
🏆  CHAMPION    Argentina
🥈  Runner-Up   Portugal
🥉  3rd Place   France
4️⃣   4th Place   Uruguay

Champion probability in Final: 51%
Total matches simulated: 104
```

**Argentina's knockout path:**

```
Round of 32   Argentina 2-1 Colombia        H 57% / D 14% / A 29%
Round of 16   Ecuador   1-2 Argentina       H 25% / D 14% / A 61%
Quarter-Final USA       1-2 Argentina       H 26% / D 14% / A 60%
Semi-Final    Argentina 2-2 France          → Argentina (AET/PKs, H 45%)
Final         Argentina 2-2 Portugal        → Argentina (AET/PKs, H 51%)
```

---

## Configuration

All settings are read from `.env` (see `.env.example`):

| Variable | Default | Required | Description |
|---|---|---|---|
| `ZEP_API_KEY` | — | For graph mode | Zep Cloud key. Free tier sufficient. |
| `ZEP_GRAPH_ID` | — | For graph mode | Set after running `setup_zep.py` |
| `LLM_API_KEY` | — | Optional | Any OpenAI-compatible key. Enables LLM narrative. |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Optional | Must end with `/v1` (e.g. `https://api.anthropic.com/v1`) |
| `LLM_MODEL_NAME` | `gpt-4o` | Optional | `claude-opus-4-8`, `gpt-4o`, `qwen-plus`, etc. |
| `OPTA_API_KEY` | — | Optional | Stats Perform commercial key. SquadQualityAgent uses benchmark fallback if absent. |
| `YOUTUBE_API_KEY` | — | Optional | YouTube Data API v3. 10k units/day free. |
| `DATABASE_URL` | `sqlite:///backend/app.db` | For auth/settings persistence | Use Postgres in production. |
| `CLERK_PUBLISHABLE_KEY` | — | For frontend auth | Clerk frontend publishable key. |
| `CLERK_SECRET_KEY` | — | For backend auth | Backend-only Clerk secret. |
| `CLERK_JWKS_URL` | `https://api.clerk.com/v1/jwks` | For backend auth | Used to verify Clerk bearer tokens. |
| `CLERK_WEBHOOK_SECRET` | — | For Clerk user sync | Svix webhook signing secret. |
| `FRONTEND_ORIGIN` | `http://localhost:3001` | For local CORS | Set to your deployed frontend origin in production. |
| `PORT` | `5002` | — | Backend port |
| `SWARM_PARALLEL_AGENTS` | `7` | — | Concurrent agent threads. Match number of agents (7). |
| `SWARM_TIMEOUT_SECONDS` | `60` | — | Per-match swarm deadline |

### Auth and admin settings bootstrap

User auth is now Clerk-backed and app authorization is stored locally. After
installing backend dependencies, create the database schema before first run:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
venv/bin/python -m alembic upgrade head
```

Then configure Clerk:

- set `CLERK_PUBLISHABLE_KEY` in the frontend environment
- set `CLERK_SECRET_KEY`, `CLERK_JWKS_URL`, and `CLERK_WEBHOOK_SECRET` for the backend
- point a Clerk webhook at `POST /api/webhooks/clerk`

The first admin is still a manual bootstrap: sign in once so the user is synced
into the local `users` table, then promote that row in the database:

```sql
UPDATE users SET is_admin = true WHERE email = '<admin-email>';
```

After that, the admin can manage non-secret runtime settings from the app’s
admin settings page.

### Running without any API keys

The system is fully functional with zero keys set:

| Component | Without key |
|---|---|
| StatisticalAgent | Uses 60-team static ELO dataset |
| FormAgent | Uses static form points |
| TacticalAgent | Uses embedded style matrix |
| LiveDataAgent | FotMob → style-derived estimates; FlashScore → ELO-derived form strings |
| MarketSignalsAgent | 365Scores → ELO-implied odds; Tiki-Taka → Dixon-Coles Poisson model |
| SquadQualityAgent | Opta benchmark table (18 elite teams) + interpolated model for the rest |
| VideoAgent | ELO-derived synthetic engagement scores |
| AggregatorAgent | Rule-based fallback narrative (no LLM call) |
| Knowledge layer | Static Python dict instead of Zep graph |

---

## Project Structure

```
FifaOctopus/
├── .env.example
├── package.json
├── backend/
│   ├── run.py                              # Flask entry point (port 5002)
│   ├── setup_zep.py                        # One-shot Zep graph builder
│   ├── requirements.txt
│   ├── app/
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── predictions.py             # Swarm + tournament endpoints
│   │   │   └── markets.py                 # /api/markets/* endpoints           ★
│   │   ├── models/
│   │   │   ├── match.py                   # MatchPrediction, TournamentResult, etc.
│   │   │   └── market.py                  # MarketQuestion, Platform, MarketType ★
│   │   ├── services/
│   │   │   ├── swarm_orchestrator.py      # Parallel agent dispatch + Zep injection
│   │   │   ├── tournament_simulator.py    # Full 104-match WC bracket
│   │   │   ├── market_question_generator.py # Converts predictions → market contracts ★
│   │   │   ├── zep_football_graph.py      # Zep graph builder (144 episodes)
│   │   │   ├── zep_football_tools.py      # Graph search tools for agents
│   │   │   ├── agents/
│   │   │   │   ├── base_agent.py
│   │   │   │   ├── statistical_agent.py   # SofaScore ELO + Poisson
│   │   │   │   ├── video_agent.py         # YouTube engagement
│   │   │   │   ├── form_agent.py          # Last-10 form points
│   │   │   │   ├── tactical_agent.py      # Style matchup matrix
│   │   │   │   ├── live_data_agent.py     # FotMob xG + FlashScore H2H
│   │   │   │   ├── market_signals_agent.py # 365Scores odds + Tiki-Taka
│   │   │   │   ├── squad_quality_agent.py  # Opta player ratings + squad depth
│   │   │   │   └── aggregator_agent.py    # Weighted ensemble + LLM (7 agents)
│   │   │   └── data_collectors/
│   │   │       ├── sofascore_collector.py
│   │   │       ├── youtube_collector.py
│   │   │       ├── fotmob_collector.py     # xG, possession, PPDA, heatmaps
│   │   │       ├── flashscore_collector.py # W/D/L form strings, H2H scores
│   │   │       ├── scores365_collector.py  # Odds, news sentiment
│   │   │       ├── tikitaka_collector.py   # Dixon-Coles AI model
│   │   │       └── opta_collector.py       # Opta Stats Perform player data
│   │   └── utils/
│   │       ├── llm_client.py              # OpenAI-compatible LLM wrapper
│   │       ├── zep_paging.py              # Paginated Zep graph reads
│   │       └── logger.py
│   └── examples/
│       ├── predict_full.py                # Full 7-agent prediction + market Qs
│       └── predict_random_match.py        # Simple random fixture demo
└── frontend/
    └── src/
        ├── views/
        │   ├── Home.vue
        │   ├── GroupsView.vue
        │   ├── PredictView.vue
        │   ├── TournamentView.vue
        │   └── MarketsView.vue            # Match Markets + Tournament Futures  ★
        ├── components/
        │   └── MarketCard.vue             # Reusable contract card component    ★
        └── router/index.js               # /markets route added                ★
```

---

## Inspiration

FifaOctopus is named after **Paul the Octopus** 🐙, the common octopus who correctly predicted 8 out of 8 FIFA World Cup 2010 match outcomes, including the Final. He remains the most accurate World Cup predictor on record.

The engine's architecture is inspired by [MiroFish](https://github.com/666ghj/MiroFish) — a general-purpose swarm intelligence simulation engine — adapted here for sports prediction using a Zep knowledge graph, live statistical feeds, video intelligence, market signals, and AI predictions.
