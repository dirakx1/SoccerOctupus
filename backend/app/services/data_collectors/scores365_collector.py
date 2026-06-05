"""
365Scores Collector
====================
Fetches betting odds, news sentiment, and match interest scores
from 365Scores' public web API.

API base: https://webws.365scores.com/web/
No authentication required for basic access.

Betting odds encode market consensus about match probability —
converting them to implied probabilities gives an independent
signal that cross-validates the statistical model.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests

from ...utils.logger import get_logger
from .sofascore_collector import TEAM_STATIC_DATA

logger = get_logger("fifaoctopus.365scores")

_BASE = "https://webws.365scores.com/web"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Origin": "https://www.365scores.com",
    "Referer": "https://www.365scores.com/",
}

# 365Scores competition IDs (football = sport 1)
_WC_COMPETITION_ID = 4  # FIFA World Cup


class Scores365Collector:
    """
    Betting odds, news sentiment, and match interest from 365Scores.

    Odds-derived probabilities serve as a market-consensus signal:
    bookmakers aggregate vast amounts of team intelligence into a
    single probability estimate.
    """

    def get_match_odds(self, home: str, away: str) -> Dict[str, Any]:
        """Return implied win/draw/loss probabilities from betting odds."""
        live = self._fetch_live_odds(home, away)
        if live:
            return live
        return self._estimate_odds(home, away)

    def get_news_sentiment(self, team: str) -> Dict[str, Any]:
        """Return aggregated news sentiment for a team (0 = negative, 1 = positive)."""
        live = self._fetch_live_news_sentiment(team)
        if live:
            return live
        return self._estimate_sentiment(team)

    def get_match_interest(self, home: str, away: str) -> float:
        """Return a 0-1 match interest/importance score."""
        hd = TEAM_STATIC_DATA.get(home, {"elo": 1800})
        ad = TEAM_STATIC_DATA.get(away, {"elo": 1800})
        avg_elo = (hd["elo"] + ad["elo"]) / 2
        elo_closeness = 1 - abs(hd["elo"] - ad["elo"]) / 400
        return round(min(1.0, max(0.1, (avg_elo - 1700) / 400 * 0.6 + elo_closeness * 0.4)), 3)

    # ------------------------------------------------------------------

    def _fetch_live_odds(self, home: str, away: str) -> Optional[Dict[str, Any]]:
        try:
            resp = requests.get(
                f"{_BASE}/games/",
                params={
                    "appTypeId": "5",
                    "langId": "1",
                    "timezoneName": "UTC",
                    "userCountryId": "6",
                    "sports": "1",
                    "competitions": str(_WC_COMPETITION_ID),
                },
                headers=_HEADERS,
                timeout=6,
            )
            if resp.status_code != 200:
                return None
            games = resp.json().get("games", [])
            for game in games:
                hn = game.get("homeCompetitor", {}).get("name", "")
                an = game.get("awayCompetitor", {}).get("name", "")
                if home.lower() in hn.lower() and away.lower() in an.lower():
                    odds_data = game.get("odds", {})
                    if odds_data:
                        return self._parse_odds(home, away, odds_data)
            return None
        except Exception as exc:
            logger.debug(f"365Scores odds fetch failed: {exc}")
            return None

    def _fetch_live_news_sentiment(self, team: str) -> Optional[Dict[str, Any]]:
        try:
            resp = requests.get(
                f"{_BASE}/news/",
                params={
                    "appTypeId": "5",
                    "langId": "1",
                    "competitors": team,
                    "sports": "1",
                },
                headers=_HEADERS,
                timeout=5,
            )
            if resp.status_code != 200 or "application/json" not in resp.headers.get("content-type", ""):
                return None
            articles = resp.json().get("articles", [])
            if not articles:
                return None
            return self._score_articles(team, articles)
        except Exception as exc:
            logger.debug(f"365Scores news fetch failed for {team}: {exc}")
            return None

    # ------------------------------------------------------------------

    @staticmethod
    def _parse_odds(home: str, away: str, odds_data: Dict) -> Dict[str, Any]:
        """Convert raw odds dict to implied probabilities with vig removal."""
        try:
            home_odd = float(odds_data.get("homeOdds", odds_data.get("1", 2.5)))
            draw_odd = float(odds_data.get("drawOdds", odds_data.get("X", 3.2)))
            away_odd = float(odds_data.get("awayOdds", odds_data.get("2", 2.8)))

            # Raw implied probabilities (sum > 1 due to bookmaker margin)
            raw_h = 1 / home_odd
            raw_d = 1 / draw_odd
            raw_a = 1 / away_odd
            total = raw_h + raw_d + raw_a

            # Remove vig (normalise)
            return {
                "home_team": home, "away_team": away,
                "home_win_implied": round(raw_h / total, 3),
                "draw_implied": round(raw_d / total, 3),
                "away_win_implied": round(raw_a / total, 3),
                "bookmaker_margin": round((total - 1) * 100, 2),
                "home_decimal_odds": home_odd,
                "draw_decimal_odds": draw_odd,
                "away_decimal_odds": away_odd,
                "source": "365scores_live",
            }
        except Exception:
            return None

    def _estimate_odds(self, home: str, away: str) -> Dict[str, Any]:
        """
        Synthesise market-style odds from ELO + slight home advantage.
        Models the bookmaker's pricing logic (fade extreme favourites slightly).
        """
        hd = TEAM_STATIC_DATA.get(home, {"elo": 1800})
        ad = TEAM_STATIC_DATA.get(away, {"elo": 1800})
        elo_diff = hd["elo"] - ad["elo"]

        hw = 1 / (1 + 10 ** (-elo_diff / 400))
        # Bookmakers shade draws down vs. pure probability
        draw_raw = 0.26 - abs(elo_diff) * 0.0002
        draw = max(0.10, min(0.28, draw_raw))
        aw = max(0.05, 1 - hw - draw)

        # Add slight home advantage to market odds
        hw = min(0.85, hw + 0.02)
        aw = max(0.05, 1 - hw - draw)

        # Convert to decimal odds with ~5% margin
        margin = 1.05
        home_odd = round(margin / hw, 2)
        draw_odd = round(margin / draw, 2)
        away_odd = round(margin / aw, 2)

        return {
            "home_team": home, "away_team": away,
            "home_win_implied": round(hw, 3),
            "draw_implied": round(draw, 3),
            "away_win_implied": round(aw, 3),
            "bookmaker_margin": 5.0,
            "home_decimal_odds": home_odd,
            "draw_decimal_odds": draw_odd,
            "away_decimal_odds": away_odd,
            "source": "365scores_estimate",
        }

    def _estimate_sentiment(self, team: str) -> Dict[str, Any]:
        """Derive sentiment from recent form and ranking."""
        d = TEAM_STATIC_DATA.get(team, {"form": 15, "elo": 1800, "rank": 50})
        form = d.get("form", 15)
        elo = d.get("elo", 1800)
        rank = d.get("rank", 50)

        # Higher-ranked, better-form teams get more positive coverage
        sentiment = 0.5 + (form - 15) / 30 * 0.25 + (elo - 1800) / 600 * 0.20
        sentiment = min(0.90, max(0.15, sentiment))

        return {
            "team": team,
            "sentiment_score": round(sentiment, 3),
            "articles_found": 0,
            "trending": elo >= 2000 or form >= 22,
            "source": "365scores_estimate",
        }

    @staticmethod
    def _score_articles(team: str, articles: List[Dict]) -> Dict[str, Any]:
        """Simple keyword sentiment scorer for live articles."""
        pos_words = {"win", "victory", "champion", "impressive", "dominant", "strong", "scored", "triumph"}
        neg_words = {"loss", "defeat", "injured", "suspended", "crash", "poor", "eliminated", "weak"}
        score = 0.5
        count = 0
        for article in articles[:10]:
            title = (article.get("title", "") + " " + article.get("body", "")[:200]).lower()
            pos = sum(1 for w in pos_words if w in title)
            neg = sum(1 for w in neg_words if w in title)
            score += (pos - neg) * 0.04
            count += 1
        score = min(0.90, max(0.10, score))
        return {
            "team": team,
            "sentiment_score": round(score, 3),
            "articles_found": count,
            "trending": count >= 5,
            "source": "365scores_live",
        }
