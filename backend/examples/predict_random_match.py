#!/usr/bin/env python3
"""
predict_random_match.py
=======================
Picks a random group-stage fixture from the FIFA World Cup 2026 draw
and runs the full FifaOctopus swarm prediction pipeline on it.

Usage:
    cd /Users/mac/FifaOctopus
    python3 backend/examples/predict_random_match.py

    # Fix the random seed for a reproducible result:
    python3 backend/examples/predict_random_match.py --seed 7

    # Predict a specific match:
    python3 backend/examples/predict_random_match.py --home France --away Morocco

    # Configure optional LLM/Zep/YouTube/Opta keys in /admin/settings.
"""

import argparse
import itertools
import os
import random
import sys
from typing import List, Tuple

# ── Make sure the backend package is importable ─────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from app.db.base import db
from app.models.match import AgentPrediction, MatchOutcome, MatchPrediction, MatchStage
from app.runtime_settings import RuntimeSettings, RuntimeSettingsService
from app.services.agents.aggregator_agent import AggregatorAgent
from app.services.agents.form_agent import FormAgent
from app.services.agents.statistical_agent import StatisticalAgent
from app.services.agents.tactical_agent import TacticalAgent
from app.services.agents.video_agent import VideoAgent
from app.services.data_collectors.sofascore_collector import TEAM_STATIC_DATA
from app.services.swarm_orchestrator import SwarmOrchestrator
from app.services.tournament_simulator import WC2026_GROUPS


# ── Helpers ──────────────────────────────────────────────────────────────────

BAR = "═" * 62


def _load_runtime_settings() -> RuntimeSettings:
    app = create_app()
    with app.app_context():
        return RuntimeSettingsService.current(db)


def _resolve_team(name: str) -> str:
    """Match a CLI team name to the canonical dataset key.

    Handles missing spaces (e.g. 'SouthAfrica' → 'South Africa') and
    case differences by trying progressively looser comparisons.
    """
    stripped = name.strip()
    # Exact match wins immediately
    if stripped in TEAM_STATIC_DATA:
        return stripped
    # Case-insensitive + normalise interior spaces
    normalised = " ".join(stripped.split())
    lower = normalised.lower()
    for key in TEAM_STATIC_DATA:
        if key.lower() == lower:
            return key
    # Insert spaces before uppercase letters (CamelCase → words)
    import re
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", stripped)
    lower_spaced = spaced.lower()
    for key in TEAM_STATIC_DATA:
        if key.lower() == lower_spaced:
            return key
    # Prefix match (e.g. "South" → "South Africa") — only if unambiguous
    matches = [k for k in TEAM_STATIC_DATA if k.lower().startswith(lower)]
    if len(matches) == 1:
        return matches[0]
    # Give up — return as-is so the warning fires
    return stripped

def _all_group_fixtures() -> List[Tuple[str, str, str]]:
    """Return every unique group-stage match as (group, home, away)."""
    fixtures = []
    for group, teams in WC2026_GROUPS.items():
        for home, away in itertools.combinations(teams, 2):
            fixtures.append((group, home, away))
    return fixtures


def _bar(char: str = "─", width: int = 62) -> str:
    return char * width


def _outcome_label(
    outcome: MatchOutcome,
    home: str,
    away: str,
    stage: MatchStage,
    went_to_penalties: bool = False,
) -> str:
    if outcome == MatchOutcome.HOME_WIN:
        label = f"{home} WIN"
    elif outcome == MatchOutcome.AWAY_WIN:
        label = f"{away} WIN"
    else:
        label = "DRAW"

    if went_to_penalties:
        label += "  →  resolved via Extra Time / Penalties"
    elif outcome == MatchOutcome.DRAW and stage == MatchStage.GROUP:
        label += "  (both teams earn 1 point)"
    return label


def _prob_bar(prob: float, width: int = 20) -> str:
    filled = round(prob * width)
    return "█" * filled + "░" * (width - filled)


def _elo(team: str) -> int:
    return TEAM_STATIC_DATA.get(team, {}).get("elo", 1800)


def _rank(team: str) -> int:
    return TEAM_STATIC_DATA.get(team, {}).get("rank", 999)


def _style(team: str) -> str:
    return TEAM_STATIC_DATA.get(team, {}).get("style", "balanced")


def _conf_star(conf: float) -> str:
    stars = round(conf * 5)
    return "★" * stars + "☆" * (5 - stars)


# ── Pretty printer ────────────────────────────────────────────────────────────

def print_prediction(group: str, prediction: MatchPrediction) -> None:
    home = prediction.home_team
    away = prediction.away_team
    hw = prediction.home_win_prob
    dr = prediction.draw_prob
    aw = prediction.away_win_prob

    print()
    print(BAR)
    is_group = prediction.stage == MatchStage.GROUP
    stage_note = (
        "Draws allowed — 1pt each"
        if is_group
        else "Knockout — winner decided by 90 min, AET or PKs"
    )
    print(f"  🐙  FifaOctopus — Swarm Match Prediction")
    print(f"  FIFA World Cup 2026 · Group {group} · Group Stage · {stage_note}")
    print(BAR)
    print()

    # ── Team header ──────────────────────────────────────────────────────────
    print(f"  {'HOME':>28}        {'AWAY'}")
    print(f"  {home:>28}   vs   {away}")
    print(f"  {'ELO ' + str(_elo(home)):>28}        {'ELO ' + str(_elo(away))}")
    print(f"  {'FIFA #' + str(_rank(home)):>28}        {'FIFA #' + str(_rank(away))}")
    print(f"  {_style(home):>28}        {_style(away)}")
    print()
    print(_bar())

    # ── Probability display ──────────────────────────────────────────────────
    print()
    print("  SWARM PROBABILITIES")
    print()
    print(f"  {home} win   {_prob_bar(hw)}  {hw:>5.1%}")
    print(f"  Draw         {_prob_bar(dr)}  {dr:>5.1%}")
    print(f"  {away} win   {_prob_bar(aw)}  {aw:>5.1%}")
    print()

    # ── Prediction summary ───────────────────────────────────────────────────
    result_label = _outcome_label(
        prediction.outcome, home, away,
        prediction.stage, prediction.went_to_penalties,
    )
    print(f"  Expected goals    :  {prediction.predicted_home_goals:.2f} – {prediction.predicted_away_goals:.2f}")
    print(f"  Predicted outcome :  {result_label}")
    print()
    print("  TOP 5 LIKELY SCORES")
    print()
    for i, sp in enumerate(prediction.score_probabilities or []):
        bar = "█" * int(sp["probability"] * 200)
        marker = "  ◄ most likely" if i == 0 else ""
        print(f"    {sp['score']}   {sp['probability']*100:5.1f}%  {bar}{marker}")

    if prediction.stage == MatchStage.GROUP:
        pts = {"home_win": (3, 0), "draw": (1, 1), "away_win": (0, 3)}
        hp, ap = pts[prediction.outcome.value]
        print(f"  Points awarded    :  {home} +{hp}pt  /  {away} +{ap}pt")
    print(f"  Swarm confidence  :  {_conf_star(prediction.overall_confidence)}  "
          f"({prediction.overall_confidence:.0%})")
    print()
    print(_bar())

    # ── Per-agent breakdown ───────────────────────────────────────────────────
    print()
    print("  AGENT BREAKDOWN")
    print()
    for ap in prediction.agent_predictions:
        winner_side = (
            "← HOME" if ap.home_win_prob > ap.away_win_prob + 0.05
            else ("AWAY →" if ap.away_win_prob > ap.home_win_prob + 0.05
                  else "≈ EVEN")
        )
        print(f"  ▸ {ap.agent_name}")
        print(f"    H {ap.home_win_prob:.1%}  D {ap.draw_prob:.1%}  A {ap.away_win_prob:.1%}"
              f"  │  xG {ap.predicted_home_goals:.1f}–{ap.predicted_away_goals:.1f}"
              f"  │  conf {ap.confidence:.0%}  {winner_side}")
        # Wrap reasoning at ~60 chars
        words, line = ap.reasoning.split(), ""
        wrapped = []
        for w in words:
            if len(line) + len(w) + 1 > 56:
                wrapped.append(line)
                line = w
            else:
                line = (line + " " + w).strip()
        if line:
            wrapped.append(line)
        for i, ln in enumerate(wrapped):
            prefix = "    " if i > 0 else "    → "
            print(f"{prefix}{ln}")
        print()

    # ── Data sources ─────────────────────────────────────────────────────────
    all_sources: List[str] = []
    for ap in prediction.agent_predictions:
        for src in ap.data_sources:
            if src not in all_sources:
                all_sources.append(src)
    print(f"  Data sources: {', '.join(all_sources)}")
    print()
    print(_bar())

    # ── Key factors ──────────────────────────────────────────────────────────
    if prediction.key_factors:
        print()
        print("  KEY FACTORS")
        print()
        for f in prediction.key_factors:
            print(f"  • {f}")
        print()

    # ── Swarm narrative ──────────────────────────────────────────────────────
    if prediction.swarm_consensus:
        print(_bar())
        print()
        print("  SWARM CONSENSUS")
        print()
        words, line = prediction.swarm_consensus.split(), ""
        for w in words:
            if len(line) + len(w) + 1 > 56:
                print(f"  {line}")
                line = w
            else:
                line = (line + " " + w).strip()
        if line:
            print(f"  {line}")
        print()

    print(BAR)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Predict a random WC2026 group-stage match")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible fixture selection")
    parser.add_argument("--home", type=str, default=None,
                        help="Home team (overrides random selection)")
    parser.add_argument("--away", type=str, default=None,
                        help="Away team (overrides random selection)")
    args = parser.parse_args()

    # ── Select fixture ────────────────────────────────────────────────────────
    if args.home and args.away:
        home, away = _resolve_team(args.home), _resolve_team(args.away)
        # Find their group
        group = "?"
        for g, teams in WC2026_GROUPS.items():
            if home in teams and away in teams:
                group = g
                break
        if home not in TEAM_STATIC_DATA:
            print(f"  Warning: '{home}' not in team dataset — using default stats.")
        if away not in TEAM_STATIC_DATA:
            print(f"  Warning: '{away}' not in team dataset — using default stats.")
    else:
        if args.seed is not None:
            random.seed(args.seed)
        fixtures = _all_group_fixtures()
        group, home, away = random.choice(fixtures)
        print(f"\n  🎲  Randomly selected: Group {group} — {home} vs {away}")

    # ── Build swarm ───────────────────────────────────────────────────────────
    settings = _load_runtime_settings()
    llm_client = None
    if settings.llm_api_key:
        try:
            from app.utils.llm_client import LLMClient
            llm_client = LLMClient(settings=settings)
            print("  🤖  LLM client active — narrative synthesis enabled.")
        except Exception as e:
            print(f"  ⚠️   LLM init failed ({e}). Running without narrative synthesis.")

    orc = SwarmOrchestrator(settings=settings, llm_client=llm_client)

    print(f"\n  Running swarm for {home} vs {away}…\n")

    def progress(stage: str, pct: int, msg: str) -> None:
        bar = "▓" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"  [{bar}] {pct:3d}%  {msg}")

    # ── Run prediction ────────────────────────────────────────────────────────
    prediction = orc.predict_match(
        home_team=home,
        away_team=away,
        stage=MatchStage.GROUP,
        group=group,
        progress_callback=progress,
    )

    # ── Display result ────────────────────────────────────────────────────────
    print_prediction(group, prediction)


if __name__ == "__main__":
    main()
