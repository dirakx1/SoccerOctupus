"""
SofaScore data collector.

Uses the SofaScore public (unofficial) REST API.
Falls back to embedded static data when the network is unavailable or rate-limited,
so predictions still work without a live connection.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests

from ...config import Config
from ...utils.logger import get_logger

logger = get_logger("fifaoctopus.sofascore")


# ---------------------------------------------------------------------------
# Static fallback dataset  (FIFA rankings + key metrics, as of mid-2025)
# ---------------------------------------------------------------------------
TEAM_STATIC_DATA: Dict[str, Dict[str, Any]] = {
    # -- CONMEBOL --
    "Argentina":   {"elo": 2085, "rank": 1,  "att": 88, "def": 82, "gf": 2.1, "ga": 0.7, "form": 22, "style": "counter-press"},
    "Brazil":      {"elo": 2050, "rank": 4,  "att": 85, "def": 79, "gf": 1.9, "ga": 0.9, "form": 18, "style": "high-press"},
    "Uruguay":     {"elo": 1925, "rank": 19, "att": 72, "def": 78, "gf": 1.5, "ga": 0.9, "form": 16, "style": "defensive"},
    "Colombia":    {"elo": 1920, "rank": 20, "att": 74, "def": 72, "gf": 1.7, "ga": 1.0, "form": 17, "style": "counter-attack"},
    "Ecuador":     {"elo": 1860, "rank": 30, "att": 66, "def": 68, "gf": 1.4, "ga": 1.1, "form": 14, "style": "balanced"},
    "Paraguay":    {"elo": 1820, "rank": 41, "att": 60, "def": 65, "gf": 1.2, "ga": 1.2, "form": 13, "style": "defensive"},
    "Chile":       {"elo": 1810, "rank": 44, "att": 62, "def": 63, "gf": 1.3, "ga": 1.2, "form": 12, "style": "high-press"},
    "Peru":        {"elo": 1800, "rank": 46, "att": 58, "def": 62, "gf": 1.1, "ga": 1.3, "form": 11, "style": "balanced"},
    "Bolivia":     {"elo": 1740, "rank": 65, "att": 50, "def": 55, "gf": 0.9, "ga": 1.6, "form":  9, "style": "defensive"},
    "Venezuela":   {"elo": 1780, "rank": 52, "att": 56, "def": 60, "gf": 1.1, "ga": 1.3, "form": 12, "style": "counter-attack"},
    # -- UEFA --
    "France":      {"elo": 2065, "rank": 2,  "att": 90, "def": 83, "gf": 2.2, "ga": 0.8, "form": 21, "style": "counter-press"},
    "Spain":       {"elo": 2045, "rank": 3,  "att": 86, "def": 82, "gf": 2.0, "ga": 0.7, "form": 22, "style": "tiki-taka"},
    "England":     {"elo": 2030, "rank": 5,  "att": 84, "def": 80, "gf": 1.9, "ga": 0.9, "form": 20, "style": "high-press"},
    "Germany":     {"elo": 2000, "rank": 12, "att": 80, "def": 75, "gf": 1.8, "ga": 1.0, "form": 17, "style": "gegenpressing"},
    "Portugal":    {"elo": 2010, "rank": 7,  "att": 82, "def": 77, "gf": 1.9, "ga": 0.9, "form": 19, "style": "counter-attack"},
    "Netherlands": {"elo": 2005, "rank": 8,  "att": 81, "def": 76, "gf": 1.8, "ga": 1.0, "form": 18, "style": "high-press"},
    "Italy":       {"elo": 1970, "rank": 9,  "att": 76, "def": 80, "gf": 1.6, "ga": 0.9, "form": 16, "style": "defensive"},
    "Belgium":     {"elo": 1965, "rank": 10, "att": 78, "def": 74, "gf": 1.7, "ga": 1.0, "form": 16, "style": "counter-attack"},
    "Croatia":     {"elo": 1940, "rank": 11, "att": 74, "def": 76, "gf": 1.5, "ga": 0.9, "form": 16, "style": "balanced"},
    "Austria":     {"elo": 1900, "rank": 23, "att": 72, "def": 70, "gf": 1.5, "ga": 1.1, "form": 15, "style": "high-press"},
    "Switzerland": {"elo": 1895, "rank": 21, "att": 70, "def": 72, "gf": 1.4, "ga": 1.0, "form": 15, "style": "balanced"},
    "Denmark":     {"elo": 1890, "rank": 22, "att": 70, "def": 73, "gf": 1.4, "ga": 0.9, "form": 15, "style": "balanced"},
    "Poland":      {"elo": 1870, "rank": 28, "att": 68, "def": 68, "gf": 1.4, "ga": 1.1, "form": 14, "style": "counter-attack"},
    "Serbia":      {"elo": 1865, "rank": 29, "att": 70, "def": 65, "gf": 1.5, "ga": 1.2, "form": 14, "style": "balanced"},
    "Turkey":      {"elo": 1855, "rank": 31, "att": 68, "def": 64, "gf": 1.4, "ga": 1.2, "form": 13, "style": "counter-attack"},
    "Hungary":     {"elo": 1840, "rank": 35, "att": 62, "def": 65, "gf": 1.2, "ga": 1.1, "form": 13, "style": "defensive"},
    "Czech Republic": {"elo": 1835, "rank": 36, "att": 64, "def": 65, "gf": 1.3, "ga": 1.1, "form": 12, "style": "balanced"},
    "Romania":     {"elo": 1825, "rank": 40, "att": 60, "def": 63, "gf": 1.2, "ga": 1.2, "form": 12, "style": "defensive"},
    "Scotland":    {"elo": 1820, "rank": 43, "att": 62, "def": 62, "gf": 1.3, "ga": 1.2, "form": 12, "style": "high-press"},
    "Ukraine":     {"elo": 1830, "rank": 38, "att": 65, "def": 63, "gf": 1.3, "ga": 1.2, "form": 13, "style": "balanced"},
    "Slovakia":    {"elo": 1810, "rank": 47, "att": 60, "def": 62, "gf": 1.1, "ga": 1.2, "form": 11, "style": "defensive"},
    "Albania":     {"elo": 1790, "rank": 55, "att": 56, "def": 60, "gf": 1.0, "ga": 1.3, "form": 11, "style": "counter-attack"},
    "Slovenia":    {"elo": 1785, "rank": 57, "att": 58, "def": 62, "gf": 1.1, "ga": 1.2, "form": 11, "style": "balanced"},
    "Georgia":     {"elo": 1770, "rank": 63, "att": 54, "def": 60, "gf": 1.0, "ga": 1.3, "form": 11, "style": "counter-attack"},
    # -- CAF --
    "Morocco":     {"elo": 1890, "rank": 14, "att": 72, "def": 76, "gf": 1.5, "ga": 0.8, "form": 18, "style": "defensive"},
    "Senegal":     {"elo": 1850, "rank": 17, "att": 68, "def": 70, "gf": 1.4, "ga": 0.9, "form": 16, "style": "counter-attack"},
    "Nigeria":     {"elo": 1830, "rank": 26, "att": 70, "def": 65, "gf": 1.5, "ga": 1.1, "form": 14, "style": "counter-attack"},
    "Egypt":       {"elo": 1815, "rank": 34, "att": 65, "def": 67, "gf": 1.3, "ga": 1.0, "form": 14, "style": "defensive"},
    "Cameroon":    {"elo": 1800, "rank": 42, "att": 64, "def": 63, "gf": 1.3, "ga": 1.2, "form": 13, "style": "counter-attack"},
    "Ivory Coast": {"elo": 1810, "rank": 39, "att": 66, "def": 63, "gf": 1.4, "ga": 1.2, "form": 13, "style": "high-press"},
    "Tunisia":     {"elo": 1800, "rank": 45, "att": 60, "def": 65, "gf": 1.1, "ga": 1.0, "form": 13, "style": "defensive"},
    "Ghana":       {"elo": 1795, "rank": 48, "att": 62, "def": 60, "gf": 1.2, "ga": 1.2, "form": 12, "style": "counter-attack"},
    "South Africa":{"elo": 1775, "rank": 60, "att": 58, "def": 60, "gf": 1.1, "ga": 1.2, "form": 12, "style": "balanced"},
    "Mali":        {"elo": 1780, "rank": 56, "att": 58, "def": 60, "gf": 1.1, "ga": 1.2, "form": 11, "style": "counter-attack"},
    "Algeria":     {"elo": 1790, "rank": 50, "att": 62, "def": 63, "gf": 1.2, "ga": 1.1, "form": 12, "style": "counter-attack"},
    # -- AFC --
    "Japan":       {"elo": 1895, "rank": 15, "att": 74, "def": 74, "gf": 1.6, "ga": 0.9, "form": 18, "style": "high-press"},
    "South Korea": {"elo": 1850, "rank": 22, "att": 70, "def": 69, "gf": 1.5, "ga": 1.0, "form": 16, "style": "high-press"},
    "Iran":        {"elo": 1835, "rank": 24, "att": 65, "def": 70, "gf": 1.3, "ga": 0.9, "form": 15, "style": "defensive"},
    "Saudi Arabia":{"elo": 1805, "rank": 56, "att": 62, "def": 64, "gf": 1.2, "ga": 1.1, "form": 13, "style": "counter-attack"},
    "Australia":   {"elo": 1800, "rank": 54, "att": 62, "def": 63, "gf": 1.2, "ga": 1.2, "form": 13, "style": "balanced"},
    "Qatar":       {"elo": 1780, "rank": 68, "att": 56, "def": 58, "gf": 1.0, "ga": 1.4, "form": 10, "style": "balanced"},
    "Uzbekistan":  {"elo": 1765, "rank": 74, "att": 54, "def": 58, "gf": 1.0, "ga": 1.3, "form": 10, "style": "balanced"},
    "Iraq":        {"elo": 1770, "rank": 70, "att": 56, "def": 59, "gf": 1.0, "ga": 1.3, "form": 10, "style": "counter-attack"},
    # -- CONCACAF --
    "USA":         {"elo": 1870, "rank": 16, "att": 70, "def": 70, "gf": 1.5, "ga": 1.0, "form": 16, "style": "high-press"},
    "Mexico":      {"elo": 1855, "rank": 18, "att": 68, "def": 67, "gf": 1.4, "ga": 1.1, "form": 15, "style": "possession"},
    "Canada":      {"elo": 1835, "rank": 41, "att": 66, "def": 65, "gf": 1.3, "ga": 1.1, "form": 14, "style": "high-press"},
    "Jamaica":     {"elo": 1750, "rank": 84, "att": 50, "def": 55, "gf": 0.9, "ga": 1.5, "form":  9, "style": "counter-attack"},
    "Honduras":    {"elo": 1745, "rank": 88, "att": 48, "def": 54, "gf": 0.9, "ga": 1.5, "form":  8, "style": "defensive"},
    "Costa Rica":  {"elo": 1760, "rank": 77, "att": 52, "def": 60, "gf": 1.0, "ga": 1.3, "form": 10, "style": "defensive"},
    "Panama":      {"elo": 1750, "rank": 83, "att": 48, "def": 58, "gf": 0.9, "ga": 1.3, "form": 10, "style": "defensive"},
}


class SofaScoreCollector:
    """Fetches team data from SofaScore public API with static fallback."""

    BASE_URL = Config.SOFASCORE_BASE_URL
    HEADERS = Config.SOFASCORE_HEADERS

    def get_team_stats(self, team_name: str) -> Dict[str, Any]:
        """Return team stats, trying SofaScore live then falling back to static data."""
        live = self._fetch_live(team_name)
        if live:
            return live
        return self._static(team_name)

    def _fetch_live(self, team_name: str) -> Optional[Dict[str, Any]]:
        """Attempt to pull live stats from SofaScore search endpoint."""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/search/multi/",
                params={"q": team_name},
                headers=self.HEADERS,
                timeout=5,
            )
            if resp.status_code != 200:
                return None
            results = resp.json().get("teams", [])
            if not results:
                return None
            team = results[0]
            tid = team.get("id")
            # Fetch recent events
            events_resp = requests.get(
                f"{self.BASE_URL}/team/{tid}/events/last/0",
                headers=self.HEADERS,
                timeout=5,
            )
            time.sleep(0.5)
            static = self._static(team_name)
            if events_resp.status_code == 200:
                events = events_resp.json().get("events", [])
                goals_scored = []
                goals_conceded = []
                for ev in events[-10:]:
                    ht = ev.get("homeTeam", {}).get("name", "")
                    hs = ev.get("homeScore", {}).get("current", 0)
                    as_ = ev.get("awayScore", {}).get("current", 0)
                    if ht == team_name:
                        goals_scored.append(hs)
                        goals_conceded.append(as_)
                    else:
                        goals_scored.append(as_)
                        goals_conceded.append(hs)
                if goals_scored:
                    static["gf"] = sum(goals_scored) / len(goals_scored)
                    static["ga"] = sum(goals_conceded) / len(goals_conceded)
            return static
        except Exception as exc:
            logger.debug(f"SofaScore live fetch failed for {team_name}: {exc}")
            return None

    def _static(self, team_name: str) -> Dict[str, Any]:
        """Return embedded static data, with defaults for unknown teams."""
        d = TEAM_STATIC_DATA.get(team_name, {
            "elo": 1750, "rank": 100, "att": 55, "def": 55,
            "gf": 1.0, "ga": 1.4, "form": 10, "style": "balanced",
        })
        return dict(d)  # copy so callers can mutate safely

    def get_head_to_head(self, team_a: str, team_b: str) -> Dict[str, Any]:
        """Approximate H2H record from static data (live H2H would need SofaScore event IDs)."""
        a = self._static(team_a)
        b = self._static(team_b)
        elo_diff = a["elo"] - b["elo"]
        # Rough win-rate estimate from ELO
        a_win_rate = 1 / (1 + 10 ** (-elo_diff / 400))
        return {
            "team_a": team_a,
            "team_b": team_b,
            "elo_diff": round(elo_diff, 1),
            "a_historical_win_rate": round(a_win_rate, 3),
            "b_historical_win_rate": round(1 - a_win_rate, 3),
        }
