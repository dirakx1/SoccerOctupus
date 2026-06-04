"""
YouTube Data API v3 collector for match highlight and tactical analysis videos.

When no API key is set the collector returns synthetic metadata so the
VideoAgent can still produce a signal (based on team ELO-derived sentiment).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import requests

from ...config import Config
from ...utils.logger import get_logger

logger = get_logger("fifaoctopus.youtube")

_YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"


class YouTubeCollector:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.YOUTUBE_API_KEY

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search_match_videos(
        self,
        team_a: str,
        team_b: str,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """Return list of video metadata for a fixture."""
        query = f"{team_a} vs {team_b} highlights 2025 FIFA"
        if self.api_key:
            return self._live_search(query, max_results)
        logger.info(f"No YouTube API key — using synthetic metadata for {team_a} vs {team_b}")
        return self._synthetic_metadata(team_a, team_b, max_results)

    def get_tactical_analysis_score(
        self,
        team: str,
    ) -> Dict[str, Any]:
        """
        Aggregate like/view ratio and comment sentiment from tactical videos.
        Returns a 0–1 momentum score.
        """
        query = f"{team} tactical analysis 2025 formation"
        if self.api_key:
            videos = self._live_search(query, max_results=3)
            if videos:
                avg_ratio = sum(v.get("engagement_ratio", 0.5) for v in videos) / len(videos)
                return {"team": team, "momentum_score": round(avg_ratio, 3), "source": "youtube_live"}
        # Synthetic fallback: use embedded ELO table
        from .sofascore_collector import TEAM_STATIC_DATA
        d = TEAM_STATIC_DATA.get(team, {"elo": 1800})
        # Normalise ELO 1700–2100 → momentum 0.3–0.9
        score = 0.3 + (d["elo"] - 1700) / 400 * 0.6
        score = min(0.9, max(0.3, score))
        return {"team": team, "momentum_score": round(score, 3), "source": "synthetic_elo"}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _live_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(
                _YOUTUBE_SEARCH_URL,
                params={
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": max_results,
                    "key": self.api_key,
                    "relevanceLanguage": "en",
                    "order": "relevance",
                },
                timeout=8,
            )
            if resp.status_code != 200:
                logger.warning(f"YouTube search failed: {resp.status_code}")
                return []
            items = resp.json().get("items", [])
            video_ids = [i["id"]["videoId"] for i in items if "videoId" in i.get("id", {})]
            if not video_ids:
                return []
            return self._enrich_with_stats(items, video_ids)
        except Exception as exc:
            logger.warning(f"YouTube live search error: {exc}")
            return []

    def _enrich_with_stats(
        self, items: List[Dict], video_ids: List[str]
    ) -> List[Dict[str, Any]]:
        try:
            stats_resp = requests.get(
                _YOUTUBE_VIDEO_URL,
                params={
                    "part": "statistics,snippet",
                    "id": ",".join(video_ids),
                    "key": self.api_key,
                },
                timeout=8,
            )
            stats_map: Dict[str, Dict] = {}
            if stats_resp.status_code == 200:
                for item in stats_resp.json().get("items", []):
                    vid = item["id"]
                    s = item.get("statistics", {})
                    views = int(s.get("viewCount", 0))
                    likes = int(s.get("likeCount", 0))
                    ratio = likes / views if views > 0 else 0.5
                    stats_map[vid] = {
                        "views": views,
                        "likes": likes,
                        "engagement_ratio": round(ratio, 4),
                    }
        except Exception:
            stats_map = {}

        results = []
        for item in items:
            vid_id = item.get("id", {}).get("videoId", "")
            snippet = item.get("snippet", {})
            stats = stats_map.get(vid_id, {"views": 0, "likes": 0, "engagement_ratio": 0.5})
            results.append({
                "video_id": vid_id,
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                **stats,
            })
        return results

    def _synthetic_metadata(
        self, team_a: str, team_b: str, n: int
    ) -> List[Dict[str, Any]]:
        from .sofascore_collector import TEAM_STATIC_DATA
        da = TEAM_STATIC_DATA.get(team_a, {"elo": 1800})
        db = TEAM_STATIC_DATA.get(team_b, {"elo": 1800})
        results = []
        for i in range(n):
            ratio = 0.5 + (da["elo"] - db["elo"]) / 4000 + (i % 2) * 0.02
            results.append({
                "video_id": f"synthetic_{team_a[:3]}_{team_b[:3]}_{i}",
                "title": f"{team_a} vs {team_b} — Extended Highlights (Match {i+1})",
                "channel": "FIFAWorldCupOfficial",
                "published_at": "2025-09-01T00:00:00Z",
                "views": 500_000 + i * 100_000,
                "likes": 25_000 + i * 2_000,
                "engagement_ratio": round(min(0.9, max(0.1, ratio)), 3),
            })
        return results

    # ------------------------------------------------------------------
    # Sentiment extraction from video titles
    # ------------------------------------------------------------------

    @staticmethod
    def extract_title_sentiment(titles: List[str], team: str) -> float:
        """
        Simple keyword-based sentiment scorer (0=negative, 1=positive).
        Returns a float representing positive mentions of `team`.
        """
        positive_kw = ["win", "winner", "victory", "champion", "stunning", "brilliant", "dominant"]
        negative_kw = ["loss", "defeat", "crash", "eliminated", "shock", "dismal"]
        score = 0.5
        count = 0
        for title in titles:
            tl = title.lower()
            if team.lower() in tl:
                pos = sum(1 for k in positive_kw if k in tl)
                neg = sum(1 for k in negative_kw if k in tl)
                score += (pos - neg) * 0.05
                count += 1
        if count:
            score = min(0.9, max(0.1, score))
        return round(score, 3)
