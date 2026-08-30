"""Season-scoped ESPN snapshots and season lifecycle operations."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .espn import EspnLeagueClient
from .store import SeasonDataError


@dataclass(frozen=True)
class SeasonSpec:
    competition: str
    season: str
    provider_competition: str
    provider_season: int
    starts_on: str
    ends_on: str
    display_name: str
    promoted_team_ids: tuple[str, ...] = ()
    history: tuple[dict[str, str], ...] = ()

    @property
    def directory(self) -> str:
        return f"{self.competition}/{self.season}"


SEASON_SPECS = (
    SeasonSpec(
        "premier-league", "2026-27", "eng.1", 2026, "2026-08-01", "2027-05-31",
        "Premier League 2026-27",
        promoted_team_ids=("388", "306", "373"),
        history=(
            {"competition": "premier-league", "season": "2024-25", "file": "history-premier-league-2024-25.json"},
            {"competition": "premier-league", "season": "2025-26", "file": "history-premier-league-2025-26.json"},
            {"competition": "championship", "season": "2025-26", "file": "history-championship-2025-26.json"},
        ),
    ),
    SeasonSpec("premier-league", "2025-26", "eng.1", 2025, "2025-08-01", "2026-05-31", "Premier League 2025-26"),
    SeasonSpec("premier-league", "2024-25", "eng.1", 2024, "2024-08-01", "2025-05-31", "Premier League 2024-25"),
    SeasonSpec("championship", "2025-26", "eng.2", 2025, "2025-08-01", "2026-05-31", "Championship 2025-26"),
)


def season_spec(competition: str, season: str) -> SeasonSpec:
    for spec in SEASON_SPECS:
        if spec.competition == competition and spec.season == season:
            return spec
    raise SeasonDataError(f"unknown configured season: {competition}/{season}")


class SeasonManager:
    def __init__(self, root: str | Path, *, client: EspnLeagueClient | None = None):
        self.root = Path(root)
        self.client = client or EspnLeagueClient()

    def prepare(self, spec: SeasonSpec, *, fetch: bool = False) -> Path:
        directory = self.root / spec.directory
        directory.mkdir(parents=True, exist_ok=True)
        existing_edition = self._read(directory / "edition.json") if (directory / "edition.json").exists() else {}
        edition = {
            "competition": spec.competition,
            "season": spec.season,
            "displayName": spec.display_name,
            "provider": {"name": "espn", "competition": spec.provider_competition, "season": spec.provider_season},
            "startsOn": spec.starts_on,
            "endsOn": spec.ends_on,
            "promotedTeamIds": existing_edition.get("promotedTeamIds", list(spec.promoted_team_ids)),
            "history": list(spec.history),
            "active": bool(existing_edition.get("active", False)),
        }
        if "promotedTeamIdsSource" in existing_edition:
            edition["promotedTeamIdsSource"] = existing_edition["promotedTeamIdsSource"]
        if "leagueGraph" in existing_edition:
            edition["leagueGraph"] = existing_edition["leagueGraph"]
        self._write(directory / "edition.json", edition)
        for filename, value in (("teams.json", []), ("fixtures.json", []), ("standings.json", [])):
            if not (directory / filename).exists():
                self._write(directory / filename, value)
        if fetch:
            self.refresh(spec)
        self._update_catalog(spec)
        return directory

    def refresh(self, spec: SeasonSpec, *, include_history: bool = True) -> Path:
        directory = self.root / spec.directory
        if include_history or not (directory / "edition.json").exists():
            directory = self.prepare(spec, fetch=False)
        else:
            directory.mkdir(parents=True, exist_ok=True)
        snapshot = self.client.snapshot(
            competition=spec.provider_competition,
            season=spec.provider_season,
            starts_on=spec.starts_on,
            ends_on=spec.ends_on,
        )
        teams: dict[str, dict[str, Any]] = {}
        for fixture in snapshot["fixtures"]:
            teams[fixture["homeTeam"]["id"]] = fixture["homeTeam"]
            teams[fixture["awayTeam"]["id"]] = fixture["awayTeam"]
        for row in snapshot["standings"]:
            teams[row["team"]["id"]] = row["team"]
        self._write(directory / "teams.json", sorted(teams.values(), key=lambda item: item["name"]))
        self._write(directory / "fixtures.json", snapshot["fixtures"])
        self._write(directory / "standings.json", snapshot["standings"])
        self._write(directory / "snapshot.json", snapshot)
        if include_history:
            # Keep prior Premier League and Championship results alongside the
            # active edition so promoted clubs can start with a real prior.  They
            # are fetched from the same canonical provider, never synthesized.
            history_snapshots: dict[tuple[str, str], dict[str, Any]] = {}
            for history in spec.history:
                historical = self._history_spec(history)
                historical_snapshot = self.client.snapshot(
                    competition=historical.provider_competition,
                    season=historical.provider_season,
                    starts_on=historical.starts_on,
                    ends_on=historical.ends_on,
                )
                history_snapshots[(historical.competition, historical.season)] = historical_snapshot
                self._write(
                    directory / history["file"],
                    {
                        "provider": "espn",
                        "competition": historical.competition,
                        "season": historical.season,
                        "fixtures": historical_snapshot["fixtures"],
                        "fetchedAt": historical_snapshot["fetchedAt"],
                    },
                )
            if spec.competition == "premier-league":
                edition = self._read(directory / "edition.json")
                prior_entries = [
                    (season, snapshot)
                    for (competition, season), snapshot in history_snapshots.items()
                    if competition == "premier-league" and season != spec.season
                ]
                championship_entries = [
                    (season, snapshot)
                    for (competition, season), snapshot in history_snapshots.items()
                    if competition == "championship"
                ]
                if prior_entries and championship_entries:
                    _, prior = max(prior_entries, key=lambda item: item[0])
                    _, championship = max(championship_entries, key=lambda item: item[0])
                    current_ids = set(teams)
                    prior_ids = {str(row["teamId"]) for row in prior.get("standings", ())}
                    championship_ids = {
                        str(row["team"]["id"])
                        for row in championship.get("standings", ())
                        if isinstance(row.get("team"), dict) and row["team"].get("id")
                    }
                    promoted = sorted((current_ids - prior_ids) & championship_ids)
                    if promoted:
                        edition["promotedTeamIds"] = promoted
                        edition["promotedTeamIdsSource"] = "derived: current EPL minus most recent prior EPL, verified in Championship"
                    else:
                        edition["promotedTeamIdsSource"] = "derived: no current EPL entrants verified in supplied Championship snapshot"
                else:
                    edition["promotedTeamIdsSource"] = "unavailable: requires prior Premier League and Championship history snapshots"
                self._write(directory / "edition.json", edition)
        self._update_catalog()
        return directory

    def activate(self, spec: SeasonSpec) -> Path:
        directory = self.prepare(spec, fetch=False)
        catalog = []
        for item in self._read_catalog():
            item["active"] = item["slug"] == f"{spec.competition}-{spec.season}"
            edition_path = self.root / item["competition"] / item["season"] / "edition.json"
            if edition_path.exists():
                edition = self._read(edition_path)
                edition["active"] = item["active"]
                self._write(edition_path, edition)
            catalog.append(item)
        self._write(self.root / "catalog.json", catalog)
        edition_path = directory / "edition.json"
        edition = self._read(edition_path)
        edition["active"] = True
        self._write(edition_path, edition)
        return directory

    def _update_catalog(self, prepared: SeasonSpec | None = None) -> None:
        existing = {item["slug"]: item for item in self._read_catalog()}
        specs = (*SEASON_SPECS, prepared) if prepared else SEASON_SPECS
        for spec in specs:
            if spec is None:
                continue
            directory = self.root / spec.directory
            if not (directory / "edition.json").exists():
                continue
            existing[f"{spec.competition}-{spec.season}"] = {
                "slug": f"{spec.competition}-{spec.season}",
                "competition": spec.competition,
                "season": spec.season,
                "displayName": spec.display_name,
                "active": bool(existing.get(f"{spec.competition}-{spec.season}", {}).get("active", False)),
            }
        self._write(self.root / "catalog.json", sorted(existing.values(), key=lambda item: item["slug"]))

    @staticmethod
    def _history_spec(history: dict[str, Any]) -> SeasonSpec:
        try:
            return SeasonSpec(
                competition=history["competition"],
                season=history["season"],
                provider_competition=history.get("providerCompetition", "eng.1"),
                provider_season=int(history.get("providerSeason", str(history["season"]).split("-")[0])),
                starts_on=history.get("startsOn", f"{history['season'][:4]}-08-01"),
                ends_on=history.get("endsOn", f"{int(history['season'][:4]) + 1}-05-31"),
                display_name=history.get("displayName", f"{history['competition']} {history['season']}"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SeasonDataError("history entry must include competition and season") from exc

    def _read_catalog(self) -> list[dict[str, Any]]:
        path = self.root / "catalog.json"
        if not path.exists():
            return []
        value = self._read(path)
        return value if isinstance(value, list) else []

    @staticmethod
    def _read(path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SeasonDataError(f"invalid season data: {path}") from exc

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temporary, path)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
