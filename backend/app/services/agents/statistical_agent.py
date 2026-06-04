"""
Statistical Agent
=================
Uses SofaScore data + ELO formula to compute win/draw/loss probabilities
and Poisson-based expected goals.
"""

from __future__ import annotations

import math
from typing import Any, Dict

from ...models.match import AgentPrediction
from ...utils.logger import get_logger
from ..data_collectors.sofascore_collector import SofaScoreCollector
from ..zep_football_tools import ZepFootballTools
from .base_agent import BaseFootballAgent

logger = get_logger("fifaoctopus.agent.statistical")

LAMBDA_BASE = 1.35   # average goals per team per WC match (historical)


class StatisticalAgent(BaseFootballAgent):
    """Derives predictions from ELO ratings, FIFA rankings, and SofaScore stats."""

    def __init__(self, zep_tools: ZepFootballTools | None = None):
        super().__init__("Statistical Analysis Agent", weight=1.8)
        self.collector = SofaScoreCollector()
        self.zep = zep_tools

    # ------------------------------------------------------------------

    def predict(self, home_team: str, away_team: str, context: Dict[str, Any]) -> AgentPrediction:
        # Enrich reasoning with Zep graph knowledge when available
        zep_context = ""
        if self.zep:
            try:
                mc = self.zep.get_match_context(home_team, away_team)
                zep_context = mc.to_text()
            except Exception as exc:
                logger.debug(f"Zep context fetch failed: {exc}")

        h = self.collector.get_team_stats(home_team)
        a = self.collector.get_team_stats(away_team)
        h2h = self.collector.get_head_to_head(home_team, away_team)

        elo_diff = h["elo"] - a["elo"]

        # ELO win probability (home team)
        home_elo_prob = 1 / (1 + 10 ** (-elo_diff / 400))

        # Attack/defence strength ratio for expected goals
        att_ratio_home = h["att"] / 65.0   # normalise against average WC qualifier
        def_ratio_away = a["def"] / 65.0
        home_lambda = LAMBDA_BASE * att_ratio_home / def_ratio_away * 0.9  # slight home boost

        att_ratio_away = a["att"] / 65.0
        def_ratio_home = h["def"] / 65.0
        away_lambda = LAMBDA_BASE * att_ratio_away / def_ratio_home * 0.85

        # Poisson probability matrix (goals 0–5)
        home_win, draw, away_win = self._poisson_probs(home_lambda, away_lambda)

        # Blend with ELO signal (60% Poisson, 40% ELO)
        hw = 0.6 * home_win + 0.4 * home_elo_prob
        aw = 0.6 * away_win + 0.4 * (1 - home_elo_prob)
        dr = max(0.0, 1.0 - hw - aw)
        total = hw + dr + aw
        hw, dr, aw = hw / total, dr / total, aw / total

        # H2H historical nudge (5%)
        h2h_boost = (h2h["a_historical_win_rate"] - 0.5) * 0.10
        hw = min(0.95, max(0.02, hw + h2h_boost))
        aw = min(0.95, max(0.02, aw - h2h_boost))
        dr = max(0.03, 1.0 - hw - aw)
        total = hw + dr + aw
        hw, dr, aw = hw / total, dr / total, aw / total

        confidence = 0.70 + min(0.20, abs(elo_diff) / 800)

        source_tag = "Zep knowledge graph + SofaScore" if zep_context else "SofaScore (ELO, att/def ratings)"
        reasoning = (
            f"ELO {home_team}={h['elo']} vs {away_team}={a['elo']} (Δ{elo_diff:+.0f}). "
            f"Expected goals: {home_team} λ={home_lambda:.2f}, {away_team} λ={away_lambda:.2f}. "
            f"Attack/defence ratios drive Poisson distribution; H2H historical win-rate {h2h['a_historical_win_rate']:.2f} for {home_team}."
            + (f" [Graph context available]" if zep_context else "")
        )

        return AgentPrediction(
            agent_name=self.name,
            home_win_prob=round(hw, 3),
            draw_prob=round(dr, 3),
            away_win_prob=round(aw, 3),
            predicted_home_goals=round(home_lambda, 2),
            predicted_away_goals=round(away_lambda, 2),
            confidence=round(confidence, 3),
            reasoning=reasoning,
            data_sources=[source_tag, "H2H historical"],
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _poisson_probs(lambda_h: float, lambda_a: float, max_goals: int = 6):
        """Compute home-win, draw, away-win probabilities via Poisson matrix."""
        home_win = draw = away_win = 0.0
        for g_h in range(max_goals + 1):
            p_h = StatisticalAgent._poisson_pmf(lambda_h, g_h)
            for g_a in range(max_goals + 1):
                p_a = StatisticalAgent._poisson_pmf(lambda_a, g_a)
                p = p_h * p_a
                if g_h > g_a:
                    home_win += p
                elif g_h == g_a:
                    draw += p
                else:
                    away_win += p
        return home_win, draw, away_win

    @staticmethod
    def _poisson_pmf(lam: float, k: int) -> float:
        return (lam ** k) * math.exp(-lam) / math.factorial(k)
