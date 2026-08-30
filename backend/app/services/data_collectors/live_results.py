"""
WC 2026 live match results — auto-fetched from ESPN public API.

Exports:
  WC2026_RESULTS  — list of finished matches (auto-populated on import)
  apply_results   — adjusts TEAM_STATIC_DATA in-place (ELO + form + goals)

The ESPN scoreboard endpoint is queried for every date from the tournament
start through today. Results are cached in memory for the process lifetime.
Falls back to a hardcoded seed list if the network is unavailable.
"""

from __future__ import annotations

import datetime
import time
from typing import Any, Dict, List, Optional

import requests

from ...utils.logger import get_logger

logger = get_logger("fifaoctopus.live_results")

# ---------------------------------------------------------------------------
# Tournament date range
# ---------------------------------------------------------------------------
_TOURNAMENT_START = datetime.date(2026, 6, 11)
# Last day of the group stage. Matches after this date are knockout matches,
# even when both teams share a group (same-group rematches are possible from
# the quarter-finals onward and must not be counted in group standings).
GROUP_STAGE_END = datetime.date(2026, 6, 27)
_ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
_FETCH_TIMEOUT = 6  # seconds per request

# ---------------------------------------------------------------------------
# ESPN team name → canonical name used in TEAM_STATIC_DATA
# ---------------------------------------------------------------------------
_NAME_MAP: Dict[str, str] = {
    "Bosnia-Herzegovina":          "Bosnia and Herzegovina",
    "United States":               "USA",
    "Korea Republic":              "South Korea",
    "Turkiye":                     "Turkey",
    "Türkiye":                     "Turkey",
    "Turkey":                      "Turkey",
    "Côte d'Ivoire":               "Ivory Coast",
    "Cote d'Ivoire":               "Ivory Coast",
    "DR Congo":                    "DR Congo",
    "Congo DR":                    "DR Congo",
    "Democratic Republic of Congo": "DR Congo",
    "Curacao":                     "Curacao",
    "Curaçao":                     "Curacao",
    "Czechia":                     "Czechia",
    "Czech Republic":              "Czechia",
    "Cape Verde":                  "Cape Verde",
    "New Zealand":                 "New Zealand",
    "South Africa":                "South Africa",
}


def _canonical(name: str) -> str:
    return _NAME_MAP.get(name, name)


# ---------------------------------------------------------------------------
# Hardcoded seed — used as fallback when ESPN is unreachable
# ---------------------------------------------------------------------------
_SEED_RESULTS: List[Dict[str, Any]] = [
    {"date": "2026-06-11", "group": "A", "home": "Mexico",      "away": "South Africa", "home_goals": 2, "away_goals": 0},
    {"date": "2026-06-12", "group": "A", "home": "South Korea", "away": "Czechia",      "home_goals": 2, "away_goals": 1},
]

# ---------------------------------------------------------------------------
# ESPN fetcher
# ---------------------------------------------------------------------------

_WC2026_GROUPS: Dict[str, List[str]] = {
    "A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["USA", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}
_TEAM_TO_GROUP: Dict[str, str] = {
    team: letter
    for letter, teams in _WC2026_GROUPS.items()
    for team in teams
}


def _group_for(home: str, away: str) -> str:
    g = _TEAM_TO_GROUP.get(home)
    return g if g and _TEAM_TO_GROUP.get(away) == g else "?"


def _fetch_date(date: datetime.date) -> List[Dict[str, Any]]:
    """Return finished WC matches for *date* via ESPN API."""
    date_str = date.strftime("%Y%m%d")
    try:
        resp = requests.get(
            _ESPN_URL,
            params={"dates": date_str},
            headers={"Accept": "application/json"},
            timeout=_FETCH_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        events = resp.json().get("events", [])
    except Exception as exc:
        logger.debug(f"ESPN fetch failed for {date_str}: {exc}")
        return []

    # Knockout matches decided in extra time / on penalties get their own
    # final statuses — they are finished results and must not be dropped.
    finished_statuses = {"STATUS_FULL_TIME", "STATUS_FINAL_AET", "STATUS_FINAL_PEN", "STATUS_FINAL"}

    results = []
    for event in events:
        comp = event.get("competitions", [{}])[0]
        status = comp.get("status", {}).get("type", {}).get("name", "")
        if status not in finished_statuses:
            continue

        competitors = comp.get("competitors", [])
        home_data = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away_data = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if not home_data or not away_data:
            continue

        home = _canonical(home_data["team"]["displayName"])
        away = _canonical(away_data["team"]["displayName"])
        try:
            hg = int(home_data.get("score", 0))
            ag = int(away_data.get("score", 0))
        except (TypeError, ValueError):
            continue

        # Winner: needed for knockout matches decided on penalties, where the
        # full-time score is level. ESPN flags the shootout winner.
        if hg != ag:
            winner = home if hg > ag else away
        elif home_data.get("winner"):
            winner = home
        elif away_data.get("winner"):
            winner = away
        else:
            winner = None

        results.append({
            "date": date.isoformat(),
            "group": _group_for(home, away) if date <= GROUP_STAGE_END else "?",
            "home": home,
            "away": away,
            "home_goals": hg,
            "away_goals": ag,
            "winner": winner,
        })

    return results


def _fetch_all_results() -> List[Dict[str, Any]]:
    """Fetch every finished WC match from tournament start through today."""
    today = datetime.date.today()
    if today < _TOURNAMENT_START:
        return []

    results: List[Dict[str, Any]] = []
    date = _TOURNAMENT_START
    while date <= today:
        daily = _fetch_date(date)
        results.extend(daily)
        date += datetime.timedelta(days=1)
        if daily:
            time.sleep(0.15)   # be polite to ESPN

    if results:
        logger.info(f"Live results: fetched {len(results)} finished WC matches from ESPN")
    else:
        logger.warning("Live results: ESPN fetch returned nothing — using seed fallback")
        results = _SEED_RESULTS

    return results


# ---------------------------------------------------------------------------
# Keep application startup network-free. Load current results only when the
# live-results or tournament-simulation functionality is actually requested.
# ---------------------------------------------------------------------------
WC2026_RESULTS: List[Dict[str, Any]] = list(_SEED_RESULTS)
_RESULTS_LOADED = False
_LAST_FETCH: float = time.time()
_REFRESH_TTL = 3600  # seconds


def load_results() -> None:
    """Load current ESPN results once, preserving the shared list object."""
    global _RESULTS_LOADED, _LAST_FETCH
    if _RESULTS_LOADED:
        return
    WC2026_RESULTS[:] = _fetch_all_results()
    # Apply the complete official result set only after the first real load.
    # Importing the collector itself must remain network-free and must not
    # apply the seed and live results twice.
    from .sofascore_collector import TEAM_STATIC_DATA
    apply_results(TEAM_STATIC_DATA)
    _RESULTS_LOADED = True
    _LAST_FETCH = time.time()


def refresh_results() -> None:
    """
    Re-fetch the last few tournament days if the cache is older than the TTL.
    Mutates WC2026_RESULTS in place so existing imports stay valid.
    """
    global _LAST_FETCH
    load_results()
    if time.time() - _LAST_FETCH < _REFRESH_TTL:
        return

    today = datetime.date.today()
    if today < _TOURNAMENT_START:
        return

    # Matches finish at most ~2 days before they appear missing; re-fetch a
    # 3-day window ending today and replace those dates in the cache.
    window_start = max(_TOURNAMENT_START, today - datetime.timedelta(days=2))
    fresh: List[Dict[str, Any]] = []
    date = window_start
    while date <= today:
        fresh.extend(_fetch_date(date))
        date += datetime.timedelta(days=1)

    _LAST_FETCH = time.time()
    if not fresh:
        return

    window_dates = {d["date"] for d in fresh}
    kept = [m for m in WC2026_RESULTS if m["date"] not in window_dates]
    WC2026_RESULTS[:] = kept + fresh
    logger.info(f"Live results refreshed: {len(fresh)} matches in window, {len(WC2026_RESULTS)} total")

# ---------------------------------------------------------------------------
# ELO helpers
# ---------------------------------------------------------------------------
_K = 40


def _expected(elo_a: float, elo_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400.0))


def _result_score(goals_for: int, goals_against: int) -> float:
    if goals_for > goals_against:
        return 1.0
    if goals_for == goals_against:
        return 0.5
    return 0.0


def _margin_multiplier(goal_diff: int) -> float:
    gd = abs(goal_diff)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11 + gd) / 8.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_results(data: Dict[str, Dict[str, Any]]) -> None:
    """
    Mutate *data* (TEAM_STATIC_DATA) to reflect all played WC matches.

    Per match:
      - ELO updated with K=40 + goal-difference multiplier
      - form nudged by W=3 / D=1 / L=0 (capped at 30)
      - gf/ga blended 80% historical / 20% actual
    """
    for match in WC2026_RESULTS:
        home, away = match["home"], match["away"]
        hg, ag = match["home_goals"], match["away_goals"]

        if home not in data or away not in data:
            logger.debug(f"Skipping result {home} vs {away} — team(s) not in static data")
            continue

        h, a = data[home], data[away]

        exp_h = _expected(h["elo"], a["elo"])
        exp_a = 1.0 - exp_h
        score_h = _result_score(hg, ag)
        score_a = 1.0 - score_h
        mult = _margin_multiplier(hg - ag)

        h["elo"] = round(h["elo"] + _K * mult * (score_h - exp_h))
        a["elo"] = round(a["elo"] + _K * mult * (score_a - exp_a))

        h_pts = 3 if hg > ag else (1 if hg == ag else 0)
        a_pts = 3 if ag > hg else (1 if hg == ag else 0)
        h["form"] = min(30, h["form"] + h_pts)
        a["form"] = min(30, a["form"] + a_pts)

        h["gf"] = round(0.8 * h["gf"] + 0.2 * hg, 2)
        h["ga"] = round(0.8 * h["ga"] + 0.2 * ag, 2)
        a["gf"] = round(0.8 * a["gf"] + 0.2 * ag, 2)
        a["ga"] = round(0.8 * a["ga"] + 0.2 * hg, 2)
