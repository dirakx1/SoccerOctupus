"""
Tactical Agent
==============
Evaluates style matchups (e.g. high-press vs. defensive block) and produces
a prediction based on stylistic advantages.  Uses LLM if available, otherwise
falls back to a heuristic style-compatibility matrix.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ...models.match import AgentPrediction
from ...utils.logger import get_logger
from ..data_collectors.sofascore_collector import TEAM_STATIC_DATA
from ..zep_football_tools import ZepFootballTools
from .base_agent import BaseFootballAgent

logger = get_logger("fifaoctopus.agent.tactical")

# Advantage matrix: (attacker_style, defender_style) → home_edge (-1 to +1)
# Positive = home team has stylistic edge, Negative = away team has edge
STYLE_MATRIX: Dict[Tuple[str, str], float] = {
    ("high-press", "counter-attack"):  0.15,
    ("high-press", "defensive"):       0.10,
    ("high-press", "tiki-taka"):      -0.05,
    ("high-press", "possession"):      0.05,
    ("high-press", "balanced"):        0.05,
    ("high-press", "high-press"):      0.00,
    ("high-press", "gegenpressing"):   0.00,
    ("counter-attack", "high-press"): -0.10,
    ("counter-attack", "tiki-taka"):   0.10,
    ("counter-attack", "possession"):  0.10,
    ("counter-attack", "balanced"):    0.00,
    ("counter-attack", "defensive"):   0.00,
    ("counter-attack", "counter-attack"): 0.00,
    ("tiki-taka", "high-press"):       0.05,
    ("tiki-taka", "defensive"):        0.00,
    ("tiki-taka", "counter-attack"):  -0.10,
    ("tiki-taka", "tiki-taka"):        0.00,
    ("tiki-taka", "possession"):       0.05,
    ("tiki-taka", "balanced"):         0.05,
    ("tiki-taka", "gegenpressing"):   -0.05,
    ("defensive", "high-press"):       0.05,
    ("defensive", "tiki-taka"):        0.00,
    ("defensive", "counter-attack"):   0.00,
    ("defensive", "balanced"):         0.00,
    ("defensive", "defensive"):        0.05,   # home advantage
    ("defensive", "possession"):       0.00,
    ("possession", "counter-attack"): -0.10,
    ("possession", "high-press"):     -0.05,
    ("possession", "defensive"):       0.00,
    ("possession", "balanced"):        0.05,
    ("possession", "tiki-taka"):       0.05,
    ("gegenpressing", "counter-attack"): 0.10,
    ("gegenpressing", "possession"):   0.10,
    ("gegenpressing", "defensive"):    0.05,
    ("gegenpressing", "high-press"):   0.00,
    ("gegenpressing", "balanced"):     0.05,
    ("balanced", "balanced"):          0.05,   # slight home advantage
    ("balanced", "high-press"):        0.00,
    ("balanced", "defensive"):         0.00,
    ("balanced", "counter-attack"):    0.05,
    ("balanced", "tiki-taka"):        -0.05,
    ("balanced", "possession"):       -0.05,
}


class TacticalAgent(BaseFootballAgent):
    """Evaluates style matchups and expected-goals delta from tactical fit."""

    def __init__(self, llm_client=None, zep_tools: ZepFootballTools | None = None):
        super().__init__("Tactical Analysis Agent", weight=1.2)
        self._llm = llm_client   # optional; injected by orchestrator
        self.zep = zep_tools

    def predict(self, home_team: str, away_team: str, context: Dict[str, Any]) -> AgentPrediction:
        # Query Zep for tactical profile facts when available
        zep_tactical = ""
        if self.zep:
            try:
                facts = self.zep.search_facts(f"{home_team} vs {away_team} tactical style", limit=4)
                if facts:
                    zep_tactical = " | Graph tactical context: " + "; ".join(f.fact[:80] for f in facts[:2])
            except Exception:
                pass

        hd = TEAM_STATIC_DATA.get(home_team, {"style": "balanced", "att": 65, "def": 65, "gf": 1.2, "ga": 1.2})
        ad = TEAM_STATIC_DATA.get(away_team, {"style": "balanced", "att": 65, "def": 65, "gf": 1.2, "ga": 1.2})

        h_style = hd.get("style", "balanced")
        a_style = ad.get("style", "balanced")

        # Lookup stylistic edge
        edge = STYLE_MATRIX.get((h_style, a_style), 0.0)

        # Base probs: slight home advantage
        hw_base = 0.38 + edge
        aw_base = 0.32 - edge
        dr_base = max(0.08, 1.0 - hw_base - aw_base)
        t = hw_base + dr_base + aw_base
        hw, dr, aw = hw_base / t, dr_base / t, aw_base / t

        # Tactical xG: better attack against weaker defence
        home_xg = (hd["att"] / 100) * (1 - ad["def"] / 150) * 2.5
        away_xg = (ad["att"] / 100) * (1 - hd["def"] / 150) * 2.5

        # LLM-enhanced reasoning (if key provided)
        reasoning = self._build_reasoning(home_team, away_team, h_style, a_style, edge, hw, aw)

        source = (
            "Zep graph + Tactical style matrix"
            if zep_tactical else
            "Tactical style matrix"
        )
        return AgentPrediction(
            agent_name=self.name,
            home_win_prob=round(hw, 3),
            draw_prob=round(dr, 3),
            away_win_prob=round(aw, 3),
            predicted_home_goals=round(home_xg, 2),
            predicted_away_goals=round(away_xg, 2),
            confidence=0.60,
            reasoning=reasoning + zep_tactical,
            data_sources=[source, "Attack/defence ratings (SofaScore)"],
        )

    def _build_reasoning(
        self,
        home_team: str,
        away_team: str,
        h_style: str,
        a_style: str,
        edge: float,
        hw: float,
        aw: float,
    ) -> str:
        direction = (
            "neutral tactical matchup"
            if abs(edge) < 0.03
            else (
                f"{home_team}'s {h_style} has a tactical advantage over {away_team}'s {a_style}"
                if edge > 0
                else f"{away_team}'s {a_style} counter-plays {home_team}'s {h_style} effectively"
            )
        )
        return (
            f"Tactical profile — {home_team}: {h_style} vs {away_team}: {a_style}. "
            f"Edge={edge:+.2f}. {direction.capitalize()}. "
            f"Tactical win probabilities: {home_team} {hw:.1%} / Draw {1-hw-aw:.1%} / {away_team} {aw:.1%}."
        )
