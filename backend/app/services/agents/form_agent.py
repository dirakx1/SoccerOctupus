"""
Form Agent
==========
Analyses the last 10 official matches (form points out of 30) to produce
a prediction that captures recent team momentum and injury impact.
"""

from __future__ import annotations

from typing import Any, Dict

from ...models.match import AgentPrediction
from ...utils.logger import get_logger
from ..data_collectors.sofascore_collector import TEAM_STATIC_DATA
from ..zep_football_tools import ZepFootballTools
from .base_agent import BaseFootballAgent

logger = get_logger("fifaoctopus.agent.form")


class FormAgent(BaseFootballAgent):
    """Converts recent form points to win/draw/loss probabilities."""

    def __init__(self, zep_tools: ZepFootballTools | None = None):
        super().__init__("Recent Form Agent", weight=1.3)
        self.zep = zep_tools

    def predict(self, home_team: str, away_team: str, context: Dict[str, Any]) -> AgentPrediction:
        # Pull richer form context from Zep graph when available
        zep_notes = ""
        if self.zep:
            try:
                h_ctx = self.zep.get_team_context(home_team)
                a_ctx = self.zep.get_team_context(away_team)
                zep_notes = f" | Graph: {h_ctx.summary[:60]}… vs {a_ctx.summary[:60]}…"
            except Exception:
                pass

        hd = TEAM_STATIC_DATA.get(home_team, {"form": 15, "gf": 1.2, "ga": 1.2, "att": 65, "def": 65})
        ad = TEAM_STATIC_DATA.get(away_team, {"form": 15, "gf": 1.2, "ga": 1.2, "att": 65, "def": 65})

        h_form = hd["form"]   # 0–30
        a_form = ad["form"]

        # Normalise to 0–1
        h_norm = h_form / 30.0
        a_norm = a_form / 30.0

        # Compute raw share
        total = h_norm + a_norm + 0.001
        hw_raw = h_norm / total
        aw_raw = a_norm / total

        # Compress toward parity (form alone is insufficient)
        hw = 0.5 + (hw_raw - 0.5) * 0.7
        aw = 0.5 + (aw_raw - 0.5) * 0.7
        dr = max(0.08, 1.0 - hw - aw)
        t = hw + dr + aw
        hw, dr, aw = hw / t, dr / t, aw / t

        # Expected goals from form-adjusted scoring/conceding rates
        home_xg = hd["gf"] * (0.5 + h_norm * 0.8)
        away_xg = ad["gf"] * (0.5 + a_norm * 0.8)

        form_diff = h_form - a_form
        form_label = "equal" if abs(form_diff) < 3 else (
            f"{home_team} in better form (+{form_diff} pts)" if form_diff > 0
            else f"{away_team} in better form ({form_diff} pts)"
        )

        reasoning = (
            f"Form points (last 10): {home_team}={h_form}/30, {away_team}={a_form}/30. "
            f"{form_label}. "
            f"Adjusted xG: {home_team} {home_xg:.2f}, {away_team} {away_xg:.2f}."
            + zep_notes
        )

        confidence = 0.55 + min(0.20, abs(form_diff) / 30)
        source = "Zep graph + SofaScore form data" if zep_notes else "SofaScore form data (last 10 official matches)"

        return AgentPrediction(
            agent_name=self.name,
            home_win_prob=round(hw, 3),
            draw_prob=round(dr, 3),
            away_win_prob=round(aw, 3),
            predicted_home_goals=round(home_xg, 2),
            predicted_away_goals=round(away_xg, 2),
            confidence=round(confidence, 3),
            reasoning=reasoning,
            data_sources=[source],
        )
