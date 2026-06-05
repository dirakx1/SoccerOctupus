"""
Market Signals Agent
====================
Combines two external consensus signals:
  365Scores  — bookmaker odds → implied win/draw/loss probabilities
  Tiki-Taka  — external AI prediction (Dixon-Coles corrected Poisson
                when their API is unavailable)

Rationale: bookmakers aggregate enormous amounts of information
(team news, injury reports, market sentiment) into a single probability
estimate. Using their implied probability as a cross-validation signal
often catches things the pure-stats model misses (key player absence,
motivation, travel fatigue).

Weight: 0.8× — market signals are valuable but can be reputation-biased
toward big-name teams; we keep them as a minority voice in the swarm.
"""

from __future__ import annotations

from typing import Any, Dict

from ...models.match import AgentPrediction
from ...utils.logger import get_logger
from ..data_collectors.scores365_collector import Scores365Collector
from ..data_collectors.tikitaka_collector import TikiTakaCollector
from ..zep_football_tools import ZepFootballTools
from .base_agent import BaseFootballAgent

logger = get_logger("fifaoctopus.agent.market_signals")


class MarketSignalsAgent(BaseFootballAgent):
    """Odds-implied probability (365Scores) + external AI signal (Tiki-Taka)."""

    def __init__(self, zep_tools: ZepFootballTools | None = None):
        super().__init__("Market Signals Agent", weight=0.8)
        self.scores365 = Scores365Collector()
        self.tikitaka = TikiTakaCollector()
        self.zep = zep_tools

    def predict(self, home_team: str, away_team: str, context: Dict[str, Any]) -> AgentPrediction:
        # ── 365Scores odds ────────────────────────────────────────────────
        odds = self.scores365.get_match_odds(home_team, away_team)
        home_sentiment = self.scores365.get_news_sentiment(home_team)
        away_sentiment = self.scores365.get_news_sentiment(away_team)
        match_interest = self.scores365.get_match_interest(home_team, away_team)

        # ── Tiki-Taka AI prediction ───────────────────────────────────────
        tt = self.tikitaka.predict(home_team, away_team)

        # ── Blend odds + AI prediction ────────────────────────────────────
        # 60% weight to market odds, 40% to Tiki-Taka AI signal
        hw = odds["home_win_implied"] * 0.60 + tt["home_win_prob"] * 0.40
        dr = odds["draw_implied"] * 0.60 + tt["draw_prob"] * 0.40
        aw = odds["away_win_implied"] * 0.60 + tt["away_win_prob"] * 0.40

        # News sentiment nudge: ±2% for each team's media momentum
        h_sent = home_sentiment["sentiment_score"]
        a_sent = away_sentiment["sentiment_score"]
        sent_diff = (h_sent - a_sent) * 0.04
        hw = min(0.88, max(0.04, hw + sent_diff))
        aw = min(0.88, max(0.04, aw - sent_diff))
        dr = max(0.05, 1.0 - hw - aw)
        t = hw + dr + aw
        hw, dr, aw = hw/t, dr/t, aw/t

        # Expected goals: use Tiki-Taka's model (Dixon-Coles has its own xG)
        home_xg = tt.get("expected_home_goals", 1.2)
        away_xg = tt.get("expected_away_goals", 1.1)

        # Confidence: higher when both signals agree
        agreement = 1 - abs(odds["home_win_implied"] - tt["home_win_prob"])
        confidence = 0.55 + agreement * 0.20

        # Sources
        odds_source = "365Scores" + (" (live odds)" if odds.get("source") == "365scores_live" else " (estimated odds)")
        tt_source = "Tiki-Taka" + (" (live AI)" if tt.get("source") == "tikitaka_live" else " (Dixon-Coles AI)")

        reasoning = (
            f"365Scores implied odds: {home_team} {odds['home_win_implied']:.1%} / "
            f"Draw {odds['draw_implied']:.1%} / {away_team} {odds['away_win_implied']:.1%} "
            f"(margin {odds['bookmaker_margin']:.1f}%). "
            f"Tiki-Taka AI: {home_team} {tt['home_win_prob']:.1%} / "
            f"Draw {tt['draw_prob']:.1%} / {away_team} {tt['away_win_prob']:.1%}. "
            f"News sentiment: {home_team} {h_sent:.2f} vs {away_team} {a_sent:.2f}. "
            f"Match interest score: {match_interest:.2f}. "
            f"Signal agreement: {agreement:.0%}."
        )
        if tt.get("key_insight"):
            reasoning += f" [{tt['key_insight'][:100]}]"

        return AgentPrediction(
            agent_name=self.name,
            home_win_prob=round(hw, 3),
            draw_prob=round(dr, 3),
            away_win_prob=round(aw, 3),
            predicted_home_goals=round(home_xg, 2),
            predicted_away_goals=round(away_xg, 2),
            confidence=round(confidence, 3),
            reasoning=reasoning,
            data_sources=[odds_source, tt_source],
        )
