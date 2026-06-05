"""
Live Data Agent
===============
Combines FotMob (deep match stats, xG, heatmaps) and
FlashScore (recent W/D/L form strings, live scores, H2H)
into a single prediction that captures current team state
more accurately than static ELO alone.

Weight: 1.4× — live data is more current than static ratings.
"""

from __future__ import annotations

from typing import Any, Dict

from ...models.match import AgentPrediction
from ...utils.logger import get_logger
from ..data_collectors.flashscore_collector import FlashScoreCollector
from ..data_collectors.fotmob_collector import FotMobCollector
from ..zep_football_tools import ZepFootballTools
from .base_agent import BaseFootballAgent

logger = get_logger("fifaoctopus.agent.live_data")


class LiveDataAgent(BaseFootballAgent):
    """FotMob deep stats + FlashScore live form and H2H."""

    def __init__(self, zep_tools: ZepFootballTools | None = None):
        super().__init__("Live Data Agent", weight=1.4)
        self.fotmob = FotMobCollector()
        self.flashscore = FlashScoreCollector()
        self.zep = zep_tools

    def predict(self, home_team: str, away_team: str, context: Dict[str, Any]) -> AgentPrediction:
        # ── FotMob data ───────────────────────────────────────────────────
        match_stats = self.fotmob.get_match_stats(home_team, away_team)
        h_fm = match_stats["home"]
        a_fm = match_stats["away"]

        # ── FlashScore form + H2H ─────────────────────────────────────────
        h_form = self.flashscore.get_team_form(home_team, last_n=6)
        a_form = self.flashscore.get_team_form(away_team, last_n=6)
        h2h = self.flashscore.get_head_to_head(home_team, away_team, last_n=5)

        # ── Probability model ─────────────────────────────────────────────
        # xG-based expected goals
        home_xg = h_fm["xg_per_game"]
        away_xg = a_fm["xg_per_game"]

        # Form adjustment: points from last 6 (max 18) → ±5% modifier
        h_form_mod = (h_form["points"] - 9) / 18 * 0.05
        a_form_mod = (a_form["points"] - 9) / 18 * 0.05
        home_xg = max(0.3, home_xg * (1 + h_form_mod))
        away_xg = max(0.3, away_xg * (1 + a_form_mod))

        # Pressing edge: lower PPDA = more pressing = better chance creation
        # Teams that press more generate ~3% more xG
        press_diff = a_fm["pressing_intensity"] - h_fm["pressing_intensity"]
        press_boost = press_diff * 0.003   # positive = home pressing more
        home_xg = max(0.3, home_xg * (1 + press_boost))

        # Heatmap attacking zone boost: teams spending >45% in attacking third
        home_att_zone = h_fm.get("heatmap_zones", {}).get("attacking_third", 0.38)
        away_att_zone = a_fm.get("heatmap_zones", {}).get("attacking_third", 0.38)
        home_xg = max(0.3, home_xg * (0.85 + home_att_zone * 0.35))
        away_xg = max(0.3, away_xg * (0.85 + away_att_zone * 0.35))

        # H2H history nudge (10% weight)
        h2h_total = h2h["home_wins"] + h2h["draws"] + h2h["away_wins"]
        if h2h_total > 0:
            h2h_home_rate = h2h["home_wins"] / h2h_total
        else:
            h2h_home_rate = 0.5

        # Poisson win/draw/loss from xG
        hw, dr, aw = _poisson_probs(home_xg, away_xg)

        # Blend with H2H (10%) and form (5%) signals
        hw = hw * 0.85 + h2h_home_rate * 0.10 + (0.5 + h_form_mod - a_form_mod) * 0.05
        aw = aw * 0.85 + (1 - h2h_home_rate) * 0.10 + (0.5 + a_form_mod - h_form_mod) * 0.05
        dr = max(0.06, 1.0 - hw - aw)
        t = hw + dr + aw
        hw, dr, aw = hw/t, dr/t, aw/t

        # Confidence: higher when live data is available
        live_sources = sum(1 for s in [
            h_fm.get("source"), a_fm.get("source"),
            h_form.get("source"), a_form.get("source"),
        ] if s and "live" in s)
        confidence = 0.60 + live_sources * 0.05

        # Sources list
        sources = list({
            "FotMob" + (" (live)" if "live" in h_fm.get("source","") else " (estimated)"),
            "FlashScore" + (" (live)" if "live" in h_form.get("source","") else " (estimated)"),
        })

        reasoning = (
            f"FotMob xG: {home_team} {h_fm['xg_per_game']:.2f}/game, "
            f"{away_team} {a_fm['xg_per_game']:.2f}/game. "
            f"Adjusted xG (form+press+heatmap): {home_team} {home_xg:.2f} vs {away_team} {away_xg:.2f}. "
            f"Possession: {home_team} {h_fm['possession_pct']:.0f}% / {away_team} {a_fm['possession_pct']:.0f}%. "
            f"FlashScore form (last 6): {home_team} {h_form['form_string']} ({h_form['points']}pt) / "
            f"{away_team} {a_form['form_string']} ({a_form['points']}pt). "
            f"H2H: {home_team} {h2h['home_wins']}W-{h2h['draws']}D-{h2h['away_wins']}L."
        )

        return AgentPrediction(
            agent_name=self.name,
            home_win_prob=round(hw, 3),
            draw_prob=round(dr, 3),
            away_win_prob=round(aw, 3),
            predicted_home_goals=round(home_xg, 2),
            predicted_away_goals=round(away_xg, 2),
            confidence=round(confidence, 3),
            reasoning=reasoning,
            data_sources=sources,
        )


# ---------------------------------------------------------------------------

def _poisson_probs(lam_h: float, lam_a: float, max_g: int = 6) -> tuple[float, float, float]:
    import math
    hw = dr = aw = 0.0
    for i in range(max_g + 1):
        ph = (lam_h**i) * math.exp(-lam_h) / math.factorial(i)
        for j in range(max_g + 1):
            pa = (lam_a**j) * math.exp(-lam_a) / math.factorial(j)
            p = ph * pa
            if i > j:    hw += p
            elif i == j: dr += p
            else:        aw += p
    return hw, dr, aw
