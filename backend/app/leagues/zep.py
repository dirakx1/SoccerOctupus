"""Edition-scoped Zep graph preparation for league evidence.

This module intentionally does not import or reuse the World Cup graph
builder.  A graph ID is deterministic per competition/season and is only
stored in that edition's metadata after an explicit remote build.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def league_graph_id(competition: str, season: str) -> str:
    safe_competition = "_".join(part for part in competition.lower().replace("/", "-").split("-") if part)
    safe_season = season.replace("/", "-")
    return f"socceroctupus_{safe_competition}_{safe_season.replace('-', '_')}"


def _timestamp(value: Any) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat()


class LeagueZepGraphManager:
    """Build a small graph from committed ESPN edition data."""

    def __init__(self, *, client_factory=None):
        self.client_factory = client_factory

    @staticmethod
    def graph_id(season) -> str:
        return league_graph_id(season.competition, season.season)

    @staticmethod
    def _standings_available_at(season) -> str | None:
        """Return when the committed standings snapshot became available."""
        try:
            snapshot = json.loads((season.directory / "snapshot.json").read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        value = snapshot.get("fetchedAt") if isinstance(snapshot, dict) else None
        return str(value) if value else None

    @staticmethod
    def episodes(season) -> list[dict[str, Any]]:
        episodes: list[dict[str, Any]] = []
        identity = f"{season.competition} {season.season}"
        promoted = season.promoted_team_ids
        teams = {str(team["id"]): team for team in season.teams}
        standings_available_at = LeagueZepGraphManager._standings_available_at(season)
        for team in season.teams:
            episodes.append({
                "data": json.dumps({
                    "competition": identity,
                    "entity": "club",
                    "clubId": str(team["id"]),
                    "club": team["name"],
                    "promoted": str(team["id"]) in promoted,
                }),
                "created_at": _timestamp(season.edition.get("startsOn")),
                "source_description": "Committed ESPN league season club metadata",
            })
        for row in season.standings:
            team = teams.get(str(row.get("teamId")))
            if not team:
                continue
            episodes.append({
                "data": json.dumps({
                    "competition": identity,
                    "entity": "standing",
                    "clubId": str(row["teamId"]),
                    "club": team["name"],
                    "position": row.get("position"),
                    "points": row.get("points"),
                    "played": row.get("played"),
                }),
                "created_at": _timestamp(standings_available_at),
                "source_description": "Committed ESPN league standings",
            })
        for fixture in season.completed_fixtures:
            home = teams.get(str(fixture.get("homeTeamId")))
            away = teams.get(str(fixture.get("awayTeamId")))
            if not home or not away:
                continue
            episodes.append({
                "data": json.dumps({
                    "competition": identity,
                    "entity": "completed_fixture",
                    "fixtureId": str(fixture["id"]),
                    "homeClub": home["name"],
                    "awayClub": away["name"],
                    "homeScore": fixture.get("homeScore"),
                    "awayScore": fixture.get("awayScore"),
                }),
                "created_at": _timestamp(fixture.get("kickoff")),
                "source_description": "Committed ESPN completed result",
            })
        return episodes

    def build(self, season, *, api_key: str) -> str:
        if not api_key.strip():
            raise ValueError("Zep API key is not configured")
        graph_id = league_graph_id(season.competition, season.season)
        existing_id = str(season.edition.get("leagueGraph", {}).get("graphId", ""))
        if existing_id == graph_id:
            return graph_id
        try:
            from zep_cloud import EpisodeData
            from zep_cloud.client import Zep
        except ImportError as exc:
            raise ValueError("zep-cloud dependency is not installed") from exc
        client = self.client_factory(api_key=api_key) if self.client_factory else Zep(api_key=api_key)
        try:
            client.graph.create(
                graph_id=graph_id,
                name=f"SoccerOctupus {season.competition} {season.season}",
                description="Edition-scoped league graph built only from committed ESPN data",
            )
        except Exception as exc:
            message = str(exc).lower()
            if "already exists" in message or "conflict" in message or "409" in message:
                raise ValueError(
                    f"remote edition graph {graph_id} already exists but local metadata is absent; refusing duplicate ingestion"
                ) from exc
            raise ValueError(f"could not create edition graph {graph_id}: {exc.__class__.__name__}") from exc
        raw_episodes = self.episodes(season)
        self._add_episodes(client, graph_id, raw_episodes, EpisodeData)
        return graph_id

    @staticmethod
    def _add_episodes(client, graph_id: str, raw_episodes: list[dict[str, Any]], episode_type) -> None:
        for offset in range(0, len(raw_episodes), 20):
            batch = raw_episodes[offset:offset + 20]
            client.graph.add_batch(
                graph_id=graph_id,
                episodes=[
                    episode_type(
                        data=item["data"],
                        type="json",
                        created_at=item.get("created_at"),
                        source_description=item.get("source_description"),
                    )
                    for item in batch
                ],
            )

    def resume_existing(self, season, *, api_key: str) -> str:
        """Populate an already-created graph only after confirming it is empty."""
        if not api_key.strip():
            raise ValueError("Zep API key is not configured")
        graph_id = league_graph_id(season.competition, season.season)
        if str(season.edition.get("leagueGraph", {}).get("graphId", "")) == graph_id:
            return graph_id
        try:
            from zep_cloud import EpisodeData
            from zep_cloud.client import Zep
        except ImportError as exc:
            raise ValueError("zep-cloud dependency is not installed") from exc
        client = self.client_factory(api_key=api_key) if self.client_factory else Zep(api_key=api_key)
        try:
            results = client.graph.search(
                query=f"{season.competition} {season.season}",
                graph_id=graph_id,
                scope="episodes",
                limit=1,
            )
        except Exception as exc:
            raise ValueError(f"could not verify existing edition graph {graph_id}: {exc.__class__.__name__}") from exc
        if getattr(results, "episodes", None):
            raise ValueError(f"edition graph {graph_id} already contains episodes; refusing duplicate ingestion")
        self._add_episodes(client, graph_id, self.episodes(season), EpisodeData)
        return graph_id

    @staticmethod
    def metadata(graph_id: str) -> dict[str, str]:
        return {"graphId": graph_id, "builtAt": datetime.now(timezone.utc).isoformat(), "source": "ESPN committed league JSON"}


def graph_view(season) -> dict[str, Any]:
    """Return a local, edition-scoped graph view without requiring a Zep key."""
    competition_id = f"competition:{season.competition}:{season.season}"
    nodes = [{"id": competition_id, "label": season.edition.get("displayName", season.season), "type": "competition"}]
    links = []
    teams = {str(team["id"]): team for team in season.teams}
    for team_id, team in teams.items():
        node_id = f"club:{team_id}"
        nodes.append({"id": node_id, "label": team["name"], "type": "club", "promoted": team_id in season.promoted_team_ids})
        links.append({"source": competition_id, "target": node_id, "type": "member"})
    for fixture in season.completed_fixtures:
        fixture_id = f"fixture:{fixture['id']}"
        home, away = str(fixture["homeTeamId"]), str(fixture["awayTeamId"])
        nodes.append({"id": fixture_id, "label": f"{teams[home]['name']} {fixture['homeScore']}–{fixture['awayScore']} {teams[away]['name']}", "type": "result"})
        links.extend(({"source": fixture_id, "target": f"club:{home}", "type": "home"}, {"source": fixture_id, "target": f"club:{away}", "type": "away"}))
    return {"graphId": LeagueZepGraphManager.graph_id(season), "mode": "zep" if season.edition.get("leagueGraph", {}).get("graphId") else "edition", "nodes": nodes, "links": links}
