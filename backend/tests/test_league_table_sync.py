from datetime import datetime, timezone

from app.db.models import (
    CompetitionEdition,
    CompetitionEditionTeam,
    Standing,
    StandingsSnapshot,
    Team,
    TeamProviderMapping,
)
from app.competitions.editions import PREMIER_LEAGUE_2026_27
from app.db.base import db


def espn_payload(*, arsenal_points=6, include_unknown=False):
    entries = [
        {
            "team": {"id": "359", "displayName": "Arsenal", "abbreviation": "ARS"},
            "stats": [
                {"name": "rank", "value": 1},
                {"name": "gamesPlayed", "value": 2},
                {"name": "wins", "value": 2},
                {"name": "ties", "value": 0},
                {"name": "losses", "value": 0},
                {"name": "points", "value": arsenal_points},
                {"name": "pointsFor", "value": 5},
                {"name": "pointsAgainst", "value": 1},
                {"name": "pointDifferential", "value": 4},
            ],
        },
        {
            "team": {"id": "364", "displayName": "Liverpool", "abbreviation": "LIV"},
            "stats": [
                {"name": "rank", "value": 2},
                {"name": "gamesPlayed", "value": 2},
                {"name": "wins", "value": 1},
                {"name": "ties", "value": 1},
                {"name": "losses", "value": 0},
                {"name": "points", "value": 4},
                {"name": "pointsFor", "value": 3},
                {"name": "pointsAgainst", "value": 1},
                {"name": "pointDifferential", "value": 2},
            ],
        },
    ]
    if include_unknown:
        entries.append({
            "team": {"id": "999", "displayName": "Unknown"},
            "stats": [
                {"name": "rank", "value": 21},
                {"name": "gamesPlayed", "value": 2},
                {"name": "wins", "value": 1},
                {"name": "ties", "value": 0},
                {"name": "losses", "value": 1},
                {"name": "points", "value": 3},
                {"name": "pointsFor", "value": 2},
                {"name": "pointsAgainst", "value": 2},
                {"name": "pointDifferential", "value": 0},
            ],
        })
    present_ids = {entry["team"]["id"] for entry in entries}
    position = 3
    for slug, provider_id in PREMIER_LEAGUE_2026_27.provider_team_mappings:
        if provider_id in present_ids:
            continue
        entries.append({
            "team": {"id": provider_id, "displayName": slug.replace("-", " ").title()},
            "stats": [
                {"name": "rank", "value": position},
                {"name": "gamesPlayed", "value": 2},
                {"name": "wins", "value": 0},
                {"name": "ties", "value": 0},
                {"name": "losses", "value": 2},
                {"name": "points", "value": 0},
                {"name": "pointsFor", "value": 0},
                {"name": "pointsAgainst", "value": 2},
                {"name": "pointDifferential", "value": -2},
            ],
        })
        position += 1
    for entry in entries:
        entry["stats"].append({"name": "overall", "summary": "0-0-0"})
    return {"children": [{"standings": {"entries": entries}}]}


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def response_for(url, standings):
    return Response({"events": []} if "scoreboard" in url else standings)


def test_sync_season_normalizes_and_idempotently_updates_standings(app, monkeypatch):
    payload = espn_payload()
    monkeypatch.setattr(
        "app.competitions.providers.espn.requests.get",
        lambda url, **kwargs: response_for(url, payload),
    )
    runner = app.test_cli_runner()

    first = runner.invoke(args=["sync-season", "premier-league", "2026-27"])

    assert first.exit_code == 0, first.output
    assert "Synced 20 Teams and 20 standings" in first.output
    with app.app_context():
        assert Team.query.count() == 20
        assert CompetitionEdition.query.count() == 1
        assert CompetitionEditionTeam.query.count() == 20
        assert TeamProviderMapping.query.count() == 20
        assert StandingsSnapshot.query.count() == 1
        arsenal = Standing.query.join(Team).filter(Team.slug == "arsenal").one()
        assert arsenal.position == 1
        assert arsenal.points == 6
        assert arsenal.team.display_name == "Arsenal"

    second = runner.invoke(args=["sync-season", "premier-league", "2026-27"])
    assert second.exit_code == 0, second.output
    with app.app_context():
        assert Team.query.count() == 20
        assert CompetitionEditionTeam.query.count() == 20
        assert StandingsSnapshot.query.count() == 1

    payload.clear()
    payload.update(espn_payload(arsenal_points=7))
    third = runner.invoke(args=["sync-season", "premier-league", "2026-27"])
    assert third.exit_code == 0, third.output
    with app.app_context():
        assert StandingsSnapshot.query.count() == 2
        latest = StandingsSnapshot.query.order_by(StandingsSnapshot.id.desc()).first()
        assert latest.source == "ESPN"
        assert latest.source_updated_at <= datetime.now(timezone.utc).replace(tzinfo=None)
        assert next(row for row in latest.standings if row.team.slug == "arsenal").points == 7


def test_sync_season_rejects_missing_and_malformed_provider_data(app, monkeypatch):
    missing = espn_payload()
    missing["children"][0]["standings"]["entries"].pop()
    monkeypatch.setattr(
        "app.competitions.providers.espn.requests.get",
        lambda url, **kwargs: response_for(url, missing),
    )
    result = app.test_cli_runner().invoke(
        args=["sync-season", "premier-league", "2026-27"]
    )
    assert result.exit_code != 0
    assert "Missing ESPN standings Teams" in result.output

    monkeypatch.setattr(
        "app.competitions.providers.espn.requests.get",
        lambda url, **kwargs: response_for(url, {"children": []}),
    )
    result = app.test_cli_runner().invoke(
        args=["sync-season", "premier-league", "2026-27"]
    )
    assert result.exit_code != 0
    assert "ESPN standings response is malformed" in result.output
    with app.app_context():
        assert Team.query.count() == 0
        assert StandingsSnapshot.query.count() == 0


def test_sync_season_rejects_persisted_provider_mapping_collision(app, monkeypatch):
    with app.app_context():
        wrong_team = Team(slug="wrong-team", display_name="Wrong Team")
        db.session.add(wrong_team)
        db.session.flush()
        db.session.add(TeamProviderMapping(
            provider="espn", provider_team_id="359", team_id=wrong_team.id
        ))
        db.session.commit()
    monkeypatch.setattr(
        "app.competitions.providers.espn.requests.get",
        lambda url, **kwargs: response_for(url, espn_payload()),
    )

    result = app.test_cli_runner().invoke(
        args=["sync-season", "premier-league", "2026-27"]
    )

    assert result.exit_code != 0
    assert "ESPN Team 359 is already mapped to wrong-team" in result.output


def test_sync_season_rejects_unknown_provider_team_without_partial_writes(app, monkeypatch):
    monkeypatch.setattr(
        "app.competitions.providers.espn.requests.get",
        lambda url, **kwargs: response_for(url, espn_payload(include_unknown=True)),
    )

    result = app.test_cli_runner().invoke(
        args=["sync-season", "premier-league", "2026-27"]
    )

    assert result.exit_code != 0
    assert "Unknown ESPN Team mapping: 999 (Unknown)" in result.output
    with app.app_context():
        assert Team.query.count() == 0
        assert CompetitionEdition.query.count() == 0
        assert StandingsSnapshot.query.count() == 0


def test_table_api_exposes_public_preview_and_authenticated_complete_table(
    app, client, user, monkeypatch
):
    monkeypatch.setattr(
        "app.competitions.providers.espn.requests.get",
        lambda url, **kwargs: response_for(url, espn_payload()),
    )
    assert app.test_cli_runner().invoke(
        args=["sync-season", "premier-league", "2026-27"]
    ).exit_code == 0

    preview = client.get(
        "/api/competitions/premier-league/editions/2026-27/table/preview"
    )
    assert preview.status_code == 200
    assert preview.get_json()["standings"][:2] == [
        {"position": 1, "team": {"slug": "arsenal", "display_name": "Arsenal", "abbreviation": "ARS"}, "played": 2, "goal_difference": 4, "points": 6},
        {"position": 2, "team": {"slug": "liverpool", "display_name": "Liverpool", "abbreviation": "LIV"}, "played": 2, "goal_difference": 2, "points": 4},
    ]
    assert preview.get_json()["source"] == "ESPN"
    assert preview.get_json()["source_updated_at"].endswith("+00:00")

    assert client.get(
        "/api/competitions/premier-league/editions/2026-27/table"
    ).status_code == 401
    monkeypatch.setattr(
        "app.auth.verify_session_token",
        lambda token: {"sub": token, "email": "user@example.com"},
    )
    full = client.get(
        "/api/competitions/premier-league/editions/2026-27/table",
        headers={"Authorization": "Bearer user_123"},
    )
    assert full.status_code == 200
    assert full.get_json()["standings"][0] == {
        "position": 1,
        "team": {"slug": "arsenal", "display_name": "Arsenal", "abbreviation": "ARS"},
        "played": 2,
        "won": 2,
        "drawn": 0,
        "lost": 0,
        "goals_for": 5,
        "goals_against": 1,
        "goal_difference": 4,
        "points": 6,
    }


def test_table_api_reports_unsynchronized_and_unknown_editions(client, monkeypatch):
    monkeypatch.setattr(
        "app.auth.verify_session_token",
        lambda token: {"sub": token, "email": "new@example.com"},
    )
    headers = {"Authorization": "Bearer user_new"}

    unavailable = client.get(
        "/api/competitions/premier-league/editions/2026-27/table",
        headers=headers,
    )
    assert unavailable.status_code == 503
    assert unavailable.get_json() == {"error": "League Table data is not available"}
    assert client.get(
        "/api/competitions/premier-league/editions/not-real/table/preview"
    ).status_code == 404
