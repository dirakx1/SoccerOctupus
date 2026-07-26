from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import requests


class ProviderDataError(ValueError):
    pass


@dataclass(frozen=True)
class ProviderStanding:
    provider_team_id: str
    team_name: str
    abbreviation: str | None
    position: int
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int


@dataclass(frozen=True)
class ProviderStandings:
    fetched_at: datetime
    entries: tuple[ProviderStanding, ...]


class EspnStandingsProvider:
    URL = "https://site.api.espn.com/apis/v2/sports/soccer/{competition}/standings"

    def fetch(self, competition_id: str, season: str) -> ProviderStandings:
        response = requests.get(
            self.URL.format(competition=competition_id),
            params={"season": season},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        try:
            raw_entries = payload["children"][0]["standings"]["entries"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderDataError("ESPN standings response is malformed") from exc
        if not isinstance(raw_entries, list):
            raise ProviderDataError("ESPN standings entries must be a list")

        entries = tuple(self._normalize_entry(entry) for entry in raw_entries)
        team_ids = [entry.provider_team_id for entry in entries]
        positions = [entry.position for entry in entries]
        if len(team_ids) != len(set(team_ids)):
            raise ProviderDataError("ESPN standings contain duplicate Teams")
        if len(positions) != len(set(positions)):
            raise ProviderDataError("ESPN standings contain duplicate positions")
        return ProviderStandings(datetime.now(timezone.utc), entries)

    @staticmethod
    def _normalize_entry(entry: dict) -> ProviderStanding:
        try:
            team = entry["team"]
            stats = {
                stat["name"]: stat["value"]
                for stat in entry["stats"]
                if "name" in stat and "value" in stat
            }
            required = (
                "rank", "gamesPlayed", "wins", "ties", "losses", "points",
                "pointsFor", "pointsAgainst", "pointDifferential",
            )
            if any(name not in stats for name in required):
                raise KeyError("required statistic")
            return ProviderStanding(
                provider_team_id=str(team["id"]),
                team_name=str(team["displayName"]),
                abbreviation=team.get("abbreviation"),
                position=int(stats["rank"]),
                played=int(stats["gamesPlayed"]),
                won=int(stats["wins"]),
                drawn=int(stats["ties"]),
                lost=int(stats["losses"]),
                goals_for=int(stats["pointsFor"]),
                goals_against=int(stats["pointsAgainst"]),
                goal_difference=int(stats["pointDifferential"]),
                points=int(stats["points"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderDataError("ESPN standing entry is malformed") from exc
