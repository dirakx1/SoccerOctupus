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


@dataclass(frozen=True)
class ProviderFixture:
    provider_fixture_id: str
    home_provider_team_id: str
    away_provider_team_id: str
    kickoff_at: datetime
    matchweek: int | None
    venue: str | None
    status: str
    provider_status: str
    home_score: int | None
    away_score: int | None


@dataclass(frozen=True)
class ProviderFixtures:
    fetched_at: datetime
    entries: tuple[ProviderFixture, ...]


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


class EspnFixturesProvider:
    URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/{competition}/scoreboard"
    STATUS_MAP = {
        "STATUS_SCHEDULED": "scheduled",
        "STATUS_IN_PROGRESS": "in_progress",
        "STATUS_HALFTIME": "in_progress",
        "STATUS_POSTPONED": "postponed",
        "STATUS_CANCELED": "cancelled",
        "STATUS_CANCELLED": "cancelled",
        "STATUS_SUSPENDED": "suspended",
        "STATUS_ABANDONED": "abandoned",
        "STATUS_FULL_TIME": "completed",
        "STATUS_FINAL": "completed",
    }

    def fetch(
        self,
        competition_id: str,
        season: str,
        date_from: str,
        date_until: str,
    ) -> ProviderFixtures:
        response = requests.get(
            self.URL.format(competition=competition_id),
            params={"dates": f"{date_from}-{date_until}", "limit": 500},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        events = payload.get("events") if isinstance(payload, dict) else None
        if not isinstance(events, list):
            raise ProviderDataError("ESPN Fixtures response is malformed")
        entries = tuple(self._normalize_event(event) for event in events)
        identities = {}
        for entry in entries:
            identity = (entry.home_provider_team_id, entry.away_provider_team_id)
            previous = identities.setdefault(entry.provider_fixture_id, identity)
            if previous != identity:
                raise ProviderDataError(
                    f"ESPN Fixture {entry.provider_fixture_id} has conflicting identity"
                )
        return ProviderFixtures(datetime.now(timezone.utc), entries)

    @classmethod
    def _normalize_event(cls, event: dict) -> ProviderFixture:
        try:
            competition = event["competitions"][0]
            competitors = {item["homeAway"]: item for item in competition["competitors"]}
            status_type = event["status"]["type"]
            provider_status = str(status_type["name"])
            kickoff_at = datetime.fromisoformat(str(event["date"]).replace("Z", "+00:00"))
            if kickoff_at.tzinfo is None:
                kickoff_at = kickoff_at.replace(tzinfo=timezone.utc)

            def score(side: str) -> int | None:
                value = competitors[side].get("score")
                return int(value) if value not in (None, "") else None

            return ProviderFixture(
                provider_fixture_id=str(event["id"]),
                home_provider_team_id=str(competitors["home"]["team"]["id"]),
                away_provider_team_id=str(competitors["away"]["team"]["id"]),
                kickoff_at=kickoff_at,
                matchweek=(
                    int(event["week"]["number"])
                    if event.get("week", {}).get("number") is not None
                    else None
                ),
                venue=competition.get("venue", {}).get("fullName"),
                status=cls.STATUS_MAP.get(provider_status, "unknown"),
                provider_status=provider_status,
                home_score=score("home"),
                away_score=score("away"),
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderDataError("ESPN Fixture entry is malformed") from exc
