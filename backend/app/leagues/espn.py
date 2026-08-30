"""Small, normalized client for ESPN's public soccer feeds.

ESPN is the canonical source for league snapshots.  The rest of the app only
sees the stable dictionaries returned here, so provider payload changes stay
isolated to this module.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

import requests


class EspnDataError(ValueError):
    """Raised when ESPN returns a payload that cannot be normalized safely."""


class EspnLeagueClient:
    SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/{competition}/scoreboard"
    STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/soccer/{competition}/standings"

    def __init__(self, get: Callable[..., Any] = requests.get, *, timeout: int = 20):
        self._get = get
        self.timeout = timeout

    def snapshot(
        self,
        *,
        competition: str,
        season: int,
        starts_on: str,
        ends_on: str,
        fetched_at: datetime | None = None,
    ) -> dict[str, Any]:
        fixtures = self.fixtures(
            competition=competition,
            starts_on=starts_on,
            ends_on=ends_on,
        )
        standings = self.standings(competition=competition, season=season)
        return {
            "fixtures": fixtures,
            "standings": standings,
            "fetchedAt": (fetched_at or datetime.now(timezone.utc)).isoformat(),
            "provider": "espn",
        }

    def fixtures(self, *, competition: str, starts_on: str, ends_on: str) -> list[dict[str, Any]]:
        response = self._get(
            self.SCOREBOARD_URL.format(competition=competition),
            params={"limit": 1000, "dates": f"{starts_on.replace('-', '')}-{ends_on.replace('-', '')}"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        events = payload.get("events") if isinstance(payload, dict) else None
        if not isinstance(events, list):
            raise EspnDataError("ESPN scoreboard response is missing events")
        result = [self._fixture(event) for event in events]
        if len({item["id"] for item in result}) != len(result):
            raise EspnDataError("ESPN scoreboard contains duplicate event IDs")
        return sorted(result, key=lambda item: item["kickoff"])

    def standings(self, *, competition: str, season: int) -> list[dict[str, Any]]:
        response = self._get(
            self.STANDINGS_URL.format(competition=competition),
            params={"season": season},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        try:
            entries = payload["children"][0]["standings"]["entries"]
        except (KeyError, IndexError, TypeError) as exc:
            raise EspnDataError("ESPN standings response is missing entries") from exc
        if not isinstance(entries, list):
            raise EspnDataError("ESPN standings entries must be a list")
        result = [self._standing(entry) for entry in entries]
        if len({item["teamId"] for item in result}) != len(result):
            raise EspnDataError("ESPN standings contain duplicate teams")
        return sorted(result, key=lambda item: item["position"])

    @classmethod
    def _team(cls, raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise EspnDataError("ESPN team is malformed")
        team_id = str(raw.get("id", "")).strip()
        name = str(raw.get("displayName", "")).strip()
        if not team_id or not name:
            raise EspnDataError("ESPN team is missing an ID or display name")
        return {
            "id": team_id,
            "name": name,
            "abbreviation": str(raw.get("abbreviation", "")).strip() or None,
            "provider": "espn",
        }

    @classmethod
    def _fixture(cls, event: Any) -> dict[str, Any]:
        try:
            competition = event["competitions"][0]
            competitors = competition["competitors"]
            home = next(item for item in competitors if item["homeAway"] == "home")
            away = next(item for item in competitors if item["homeAway"] == "away")
            status = event["status"]["type"]
            kickoff = datetime.fromisoformat(event["date"].replace("Z", "+00:00")).isoformat()
            event_id = str(event["id"]).strip()
        except (KeyError, IndexError, StopIteration, TypeError, ValueError) as exc:
            raise EspnDataError("ESPN fixture entry is malformed") from exc
        if not event_id:
            raise EspnDataError("ESPN fixture is missing an ID")
        normalized_status = cls._status(status)
        return {
            "id": event_id,
            "kickoff": kickoff,
            "matchweek": cls._number(event.get("week") or competition.get("week")),
            "status": normalized_status,
            "providerStatus": str(status.get("name", "UNKNOWN")),
            "homeTeamId": cls._team(home["team"])["id"],
            "awayTeamId": cls._team(away["team"])["id"],
            "homeTeam": cls._team(home["team"]),
            "awayTeam": cls._team(away["team"]),
            "venue": cls._venue(competition, event),
            "homeScore": cls._score(home) if normalized_status in {"completed", "in_progress"} else None,
            "awayScore": cls._score(away) if normalized_status in {"completed", "in_progress"} else None,
        }

    @classmethod
    def _standing(cls, entry: Any) -> dict[str, Any]:
        try:
            stats = {
                item["name"]: item["value"]
                for item in entry["stats"]
                if "name" in item and "value" in item
            }
            team = cls._team(entry["team"])
            return {
                "teamId": team["id"],
                "team": team,
                "position": int(stats["rank"]),
                "played": int(stats["gamesPlayed"]),
                "won": int(stats["wins"]),
                "drawn": int(stats["ties"]),
                "lost": int(stats["losses"]),
                "goalsFor": int(stats["pointsFor"]),
                "goalsAgainst": int(stats["pointsAgainst"]),
                "goalDifference": int(stats["pointDifferential"]),
                "points": int(stats["points"]),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise EspnDataError("ESPN standing entry is malformed") from exc

    @staticmethod
    def _number(value: Any) -> int | None:
        value = value.get("number") if isinstance(value, dict) else value
        try:
            value = int(value)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    @staticmethod
    def _score(competitor: dict[str, Any]) -> int | None:
        value = competitor.get("score")
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise EspnDataError("ESPN fixture score is malformed") from exc

    @staticmethod
    def _venue(competition: dict[str, Any], event: dict[str, Any]) -> str | None:
        venue = competition.get("venue") or event.get("venue") or {}
        value = venue.get("fullName") if isinstance(venue, dict) else None
        return str(value).strip() if value else None

    @staticmethod
    def _status(raw: dict[str, Any]) -> str:
        if raw.get("completed"):
            return "completed"
        state = str(raw.get("state", ""))
        name = str(raw.get("name", "")).upper()
        if state == "in":
            return "in_progress"
        if "POSTPON" in name:
            return "postponed"
        if "CANCEL" in name:
            return "cancelled"
        return "scheduled"
