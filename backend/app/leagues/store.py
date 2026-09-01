from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SeasonDataError(ValueError):
    pass


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SeasonDataError(f"missing season file: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise SeasonDataError(f"invalid JSON in {path.name}: {exc}") from exc


@dataclass(frozen=True)
class LeagueSeason:
    directory: Path
    edition: dict[str, Any]
    teams: tuple[dict[str, Any], ...]
    fixtures: tuple[dict[str, Any], ...]
    standings: tuple[dict[str, Any], ...]
    history: tuple[dict[str, Any], ...]

    @property
    def competition(self) -> str:
        return self.edition["competition"]

    @property
    def season(self) -> str:
        return self.edition["season"]

    @property
    def slug(self) -> str:
        return f"{self.competition}-{self.season}"

    def team(self, team_id: str) -> dict[str, Any]:
        for team in self.teams:
            if team["id"] == str(team_id):
                return team
        raise SeasonDataError(f"unknown team: {team_id}")

    @property
    def completed_fixtures(self) -> tuple[dict[str, Any], ...]:
        historical = tuple(
            {
                **fixture,
                "_competition": snapshot.get("competition"),
                "_season": snapshot.get("season"),
            }
            for snapshot in self.history
            for fixture in snapshot.get("fixtures", ())
            if fixture.get("status") == "completed"
        )
        current = tuple(
            {**fixture, "_competition": self.competition, "_season": self.season}
            for fixture in self.fixtures
            if fixture.get("status") == "completed"
        )
        return historical + current

    @property
    def promoted_team_ids(self) -> set[str]:
        return {str(value) for value in self.edition.get("promotedTeamIds", ())}


class LeagueSeasonStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def load(self, competition: str, season: str) -> LeagueSeason:
        directory = self.root / competition / season
        edition = _read_json(directory / "edition.json")
        teams = tuple(_read_json(directory / "teams.json"))
        fixtures = tuple(_read_json(directory / "fixtures.json"))
        standings = tuple(_read_json(directory / "standings.json"))
        history = tuple(
            _read_json(directory / item["file"])
            for item in edition.get("history", ())
        )
        loaded = LeagueSeason(directory, edition, teams, fixtures, standings, history)
        self._validate(loaded, competition, season)
        return loaded

    def load_slug(self, slug: str) -> LeagueSeason:
        catalog = self.catalog()
        entry = next((item for item in catalog if item["slug"] == slug), None)
        if entry is None:
            raise SeasonDataError(f"unknown league edition: {slug}")
        return self.load(entry["competition"], entry["season"])

    def catalog(self) -> list[dict[str, Any]]:
        path = self.root / "catalog.json"
        value = _read_json(path)
        if not isinstance(value, list):
            raise SeasonDataError("catalog.json must contain a list")
        return value

    @staticmethod
    def _validate(data: LeagueSeason, competition: str, season: str) -> None:
        if data.edition.get("competition") != competition or data.edition.get("season") != season:
            raise SeasonDataError("edition identity does not match its directory")
        team_ids = {str(team.get("id", "")) for team in data.teams}
        if "" in team_ids or len(team_ids) != len(data.teams):
            raise SeasonDataError("teams contain missing or duplicate IDs")
        fixture_ids: set[str] = set()
        for fixture in data.fixtures:
            fixture_id = str(fixture.get("id", ""))
            if not fixture_id or fixture_id in fixture_ids:
                raise SeasonDataError("fixtures contain missing or duplicate IDs")
            fixture_ids.add(fixture_id)
            if str(fixture.get("homeTeamId")) not in team_ids:
                raise SeasonDataError(f"fixture {fixture_id} has unknown home team")
            if str(fixture.get("awayTeamId")) not in team_ids:
                raise SeasonDataError(f"fixture {fixture_id} has unknown away team")
