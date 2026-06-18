"""
Video Intelligence Agent
========================
Queries YouTube for recent match highlights and tactical analysis videos.
Extracts engagement ratios, title sentiment, and momentum signals to
produce a prediction skewed toward the "hotter" team heading into the match.
"""

from __future__ import annotations

from typing import Any, Dict

from ...models.match import AgentPrediction
from ...runtime_settings import RuntimeSettings
from ...utils.logger import get_logger
from ..data_collectors.sofascore_collector import TEAM_STATIC_DATA
from ..data_collectors.youtube_collector import YouTubeCollector
from .base_agent import BaseFootballAgent

logger = get_logger("fifaoctopus.agent.video")


class VideoAgent(BaseFootballAgent):
    """Analyses YouTube video signals to measure team momentum."""

    def __init__(self, settings: RuntimeSettings | None = None):
        super().__init__("Video Intelligence Agent", weight=1.0)
        self.yt = YouTubeCollector(api_key=settings.youtube_api_key if settings else None)

    def predict(self, home_team: str, away_team: str, context: Dict[str, Any]) -> AgentPrediction:
        # Retrieve videos for the fixture
        videos = self.yt.search_match_videos(home_team, away_team, max_results=5)

        home_titles = [v["title"] for v in videos]
        away_titles = home_titles  # same pool; sentiment extracted per team

        home_sentiment = YouTubeCollector.extract_title_sentiment(home_titles, home_team)
        away_sentiment = YouTubeCollector.extract_title_sentiment(away_titles, away_team)

        home_momentum = self.yt.get_tactical_analysis_score(home_team)["momentum_score"]
        away_momentum = self.yt.get_tactical_analysis_score(away_team)["momentum_score"]

        avg_engagement = (
            sum(v.get("engagement_ratio", 0.5) for v in videos) / len(videos)
            if videos else 0.5
        )

        # Combined video score per team
        home_score = (home_sentiment * 0.5 + home_momentum * 0.5)
        away_score = (away_sentiment * 0.5 + away_momentum * 0.5)

        total = home_score + away_score + 0.001
        hw_raw = home_score / total
        aw_raw = away_score / total

        # Compress toward 50-50 (video signals shouldn't dominate)
        hw = 0.5 + (hw_raw - 0.5) * 0.6
        aw = 0.5 + (aw_raw - 0.5) * 0.6
        dr = max(0.05, 1.0 - hw - aw)
        total2 = hw + dr + aw
        hw, dr, aw = hw / total2, dr / total2, aw / total2

        # Expected goals — inherit from static data scaled by momentum
        hd = TEAM_STATIC_DATA.get(home_team, {"gf": 1.2, "ga": 1.2})
        ad = TEAM_STATIC_DATA.get(away_team, {"gf": 1.2, "ga": 1.2})
        home_xg = hd["gf"] * (0.8 + home_momentum * 0.4)
        away_xg = ad["gf"] * (0.8 + away_momentum * 0.4)

        confidence = 0.45 + avg_engagement * 0.25   # video signals are inherently noisier
        source_tag = "YouTube (live API)" if self.yt.api_key else "YouTube (synthetic)"

        video_count = len(videos)
        reasoning = (
            f"Analysed {video_count} YouTube videos. "
            f"{home_team} sentiment={home_sentiment:.2f}, momentum={home_momentum:.2f}; "
            f"{away_team} sentiment={away_sentiment:.2f}, momentum={away_momentum:.2f}. "
            f"Avg engagement ratio: {avg_engagement:.3f}. "
            f"Video signals favour {'neither side' if abs(hw-aw)<0.05 else (home_team if hw>aw else away_team)}."
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
            data_sources=[source_tag],
        )
