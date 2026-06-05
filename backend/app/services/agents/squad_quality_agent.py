"""
Squad Quality Agent
===================
Uses Opta / Stats Perform player statistics to evaluate each team's
individual player quality and produce a prediction that captures
dimensions none of the other agents see:

  - Average player Opta rating        → overall squad calibre
  - Key passes per game               → chance-creation quality
  - Successful dribbles per game      → individual flair / unpredictability
  - Tackles won %                     → defensive organisation
  - Aerial duels won %                → physical dominance / set-piece danger
  - Set piece conversion rate         → dead-ball efficiency
  - Squad depth score                 → bench quality (rotation / fatigue resilience)
  - Pass accuracy %                   → technical level
  - xG overperformance               → clinical finishing above expected
  - Pressing success rate             → intensity without the ball

Weight: 1.1× — moderate; player-quality data is highly relevant but
the prediction is still at team level, and we lack real-time injury/
availability data which is the biggest Opta signal in practice.
"""

from __future__ import annotations

from typing import Any, Dict

from ...models.match import AgentPrediction
from ...utils.logger import get_logger
from ..data_collectors.opta_collector import OptaCollector
from ..zep_football_tools import ZepFootballTools
from .base_agent import BaseFootballAgent

logger = get_logger("fifaoctopus.agent.squad_quality")


class SquadQualityAgent(BaseFootballAgent):
    """Opta player-quality metrics → squad-level prediction."""

    def __init__(self, zep_tools: ZepFootballTools | None = None):
        super().__init__("Squad Quality Agent", weight=1.1)
        self.opta = OptaCollector()
        self.zep = zep_tools

    def predict(self, home_team: str, away_team: str, context: Dict[str, Any]) -> AgentPrediction:
        h = self.opta.get_team_opta_stats(home_team)
        a = self.opta.get_team_opta_stats(away_team)

        # ── 1. Overall quality differential ─────────────────────────────
        # Opta average rating (0–10) encodes squad calibre most directly
        rating_diff = h["avg_player_rating"] - a["avg_player_rating"]

        # ── 2. Chance-creation edge ──────────────────────────────────────
        # Key passes create shots; dribbles create space and numerical advantages
        creation_h = h["key_passes_per_game"] * 0.6 + h["successful_dribbles_per_game"] * 0.4
        creation_a = a["key_passes_per_game"] * 0.6 + a["successful_dribbles_per_game"] * 0.4
        creation_diff = creation_h - creation_a

        # ── 3. Defensive solidarity ──────────────────────────────────────
        # Tackles won % and aerial success proxy defensive organisation
        defence_h = h["tackles_won_pct"] * 0.6 + h["aerial_duels_won_pct"] * 0.4
        defence_a = a["tackles_won_pct"] * 0.6 + a["aerial_duels_won_pct"] * 0.4
        defence_diff = defence_h - defence_a

        # ── 4. Set piece efficiency ──────────────────────────────────────
        # Each 1% edge in conversion = small uplift in expected goals
        sp_diff = (h["set_piece_conversion_rate"] - a["set_piece_conversion_rate"]) * 100

        # ── 5. Squad depth advantage ─────────────────────────────────────
        # Better bench = less fatigue, better substitution impact in 70-90 min
        depth_diff = h["squad_depth_score"] - a["squad_depth_score"]

        # ── 6. Technical quality (passing) ───────────────────────────────
        pass_diff = h["pass_accuracy_pct"] - a["pass_accuracy_pct"]

        # ── 7. Clinical finishing ────────────────────────────────────────
        clinical_diff = h["xg_overperformance"] - a["xg_overperformance"]

        # ── 8. Pressing intensity ────────────────────────────────────────
        press_diff = h["pressing_success_rate"] - a["pressing_success_rate"]

        # ── Composite advantage score ────────────────────────────────────
        # Weighted combination of all differentials, normalised to ±1
        composite = (
            rating_diff    * 0.35 +   # most predictive
            creation_diff  * 0.20 +
            defence_diff   / 100 * 0.15 +
            sp_diff        * 0.08 +
            depth_diff     * 0.08 +
            pass_diff      / 100 * 0.06 +
            clinical_diff  * 0.05 +
            press_diff     * 0.03
        )

        # Map composite score → probability offset around 50/50
        # composite +1.0 → home ~65%, composite -1.0 → away ~65%
        hw_base = 0.375   # home advantage base (slight)
        dr_base = 0.250
        aw_base = 0.375

        sensitivity = 0.12   # per unit of composite
        hw = min(0.82, max(0.05, hw_base + composite * sensitivity))
        aw = min(0.82, max(0.05, aw_base - composite * sensitivity))
        dr = max(0.08, 1.0 - hw - aw)
        total = hw + dr + aw
        hw, dr, aw = hw / total, dr / total, aw / total

        # ── Expected goals ───────────────────────────────────────────────
        # Use xG-overperformance-adjusted scoring rate
        from ..data_collectors.sofascore_collector import TEAM_STATIC_DATA
        hd = TEAM_STATIC_DATA.get(home_team, {"gf": 1.2})
        ad = TEAM_STATIC_DATA.get(away_team, {"gf": 1.2})
        home_xg = max(0.3, hd["gf"] * (1 + h["xg_overperformance"] * 0.1) * 0.90)
        away_xg = max(0.3, ad["gf"] * (1 + a["xg_overperformance"] * 0.1) * 0.85)

        # ── Confidence ───────────────────────────────────────────────────
        # Higher confidence when using benchmark/live data vs fully derived
        sources = {h.get("source"), a.get("source")}
        if "opta_live" in sources:
            confidence = 0.78
        elif "opta_benchmark" in sources:
            confidence = 0.68
        else:
            confidence = 0.58

        # ── Reasoning ────────────────────────────────────────────────────
        better = home_team if composite > 0.02 else (away_team if composite < -0.02 else "neither side")
        reasoning = (
            f"Opta squad quality: {home_team} {h['avg_player_rating']:.2f}/10 vs "
            f"{away_team} {a['avg_player_rating']:.2f}/10 (Δ{rating_diff:+.2f}). "
            f"Key passes: {h['key_passes_per_game']:.1f} vs {a['key_passes_per_game']:.1f}/game. "
            f"Dribbles: {h['successful_dribbles_per_game']:.1f} vs {a['successful_dribbles_per_game']:.1f}/game. "
            f"Tackles won: {h['tackles_won_pct']:.0f}% vs {a['tackles_won_pct']:.0f}%. "
            f"Aerials: {h['aerial_duels_won_pct']:.0f}% vs {a['aerial_duels_won_pct']:.0f}%. "
            f"Set pieces: {h['set_piece_conversion_rate']:.1%} vs {a['set_piece_conversion_rate']:.1%}. "
            f"Pass acc: {h['pass_accuracy_pct']:.0f}% vs {a['pass_accuracy_pct']:.0f}%. "
            f"Squad depth: {h['squad_depth_score']:.2f} vs {a['squad_depth_score']:.2f}. "
            f"Composite Opta edge: {better} ({composite:+.3f}). "
            f"Data: {h.get('source','?')}/{a.get('source','?')}"
        )

        src_label = (
            "Opta Stats Perform (live API)"
            if "opta_live" in sources
            else "Opta (benchmark)" if "opta_benchmark" in sources
            else "Opta (derived model)"
        )

        return AgentPrediction(
            agent_name=self.name,
            home_win_prob=round(hw, 3),
            draw_prob=round(dr, 3),
            away_win_prob=round(aw, 3),
            predicted_home_goals=round(home_xg, 2),
            predicted_away_goals=round(away_xg, 2),
            confidence=confidence,
            reasoning=reasoning,
            data_sources=[src_label],
        )
