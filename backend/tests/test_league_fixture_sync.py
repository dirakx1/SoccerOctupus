from datetime import datetime, timezone

from app.competitions.editions import PREMIER_LEAGUE_2026_27
from app.db.models import Fixture, FixtureProviderMapping

from test_league_table_sync import Response, espn_payload


def fixture_payload(*, kickoff="2026-08-15T14:00:00Z", status="STATUS_SCHEDULED", matchweek=1):
    return {
        "events": [
            {
                "id": "401810001",
                "date": kickoff,
                "season": {"slug": "2026-27"},
                "week": {"number": matchweek},
                "status": {
                    "type": {
                        "name": status,
                        "state": "pre",
                        "completed": False,
                        "description": status.removeprefix("STATUS_").replace("_", " ").title(),
                    }
                },
                "competitions": [
                    {
                        "venue": {"fullName": "Emirates Stadium"},
                        "competitors": [
                            {"homeAway": "home", "team": {"id": "359"}, "score": "2"},
                            {"homeAway": "away", "team": {"id": "364"}, "score": "1"},
                        ],
                    }
                ],
            }
        ]
    }


def mock_espn(monkeypatch, fixtures):
    standings = espn_payload()
    monkeypatch.setattr(
        "app.competitions.providers.espn.requests.get",
        lambda url, **kwargs: Response(fixtures if "scoreboard" in url else standings),
    )


def test_fixture_provider_requests_the_complete_configured_date_range(monkeypatch):
    requests = []
    monkeypatch.setattr(
        "app.competitions.providers.espn.requests.get",
        lambda url, **kwargs: (
            requests.append((url, kwargs["params"]))
            or Response({"events": []})
        ),
    )

    from app.competitions.providers.espn import EspnFixturesProvider

    EspnFixturesProvider().fetch("eng.1", "2026", "20260801", "20270531")

    fixture_request = requests[0][1]
    assert fixture_request == {"dates": "20260801-20270531", "limit": 500}


def test_sync_season_persists_fixture_identity_and_rescheduling(app, monkeypatch):
    payload = fixture_payload()
    mock_espn(monkeypatch, payload)
    runner = app.test_cli_runner()

    first = runner.invoke(args=["sync-season", "premier-league", "2026-27"])

    assert first.exit_code == 0, first.output
    assert "1 Fixture" in first.output
    with app.app_context():
        fixture = Fixture.query.one()
        original_id = fixture.id
        assert fixture.matchweek == 1
        assert fixture.status == "scheduled"
        assert fixture.home_team.slug == "arsenal"
        assert fixture.away_team.slug == "liverpool"
        assert FixtureProviderMapping.query.one().provider_fixture_id == "401810001"

    payload["events"][0]["date"] = "2026-08-17T19:00:00Z"
    payload["events"][0]["week"]["number"] = 2
    payload["events"][0]["id"] = "401819999"
    second = runner.invoke(args=["sync-season", "premier-league", "2026-27"])

    assert second.exit_code == 0, second.output
    with app.app_context():
        fixture = Fixture.query.one()
        assert fixture.id == original_id
        assert fixture.kickoff_at == datetime(2026, 8, 17, 19, tzinfo=timezone.utc).replace(tzinfo=None)
        assert fixture.matchweek == 1
        assert FixtureProviderMapping.query.one().provider_fixture_id == "401819999"


def test_sync_season_normalizes_exceptional_and_unknown_fixture_statuses(app, monkeypatch):
    statuses = {
        "STATUS_IN_PROGRESS": "in_progress",
        "STATUS_POSTPONED": "postponed",
        "STATUS_CANCELED": "cancelled",
        "STATUS_SUSPENDED": "suspended",
        "STATUS_ABANDONED": "abandoned",
        "STATUS_FULL_TIME": "completed",
        "STATUS_MYSTERY": "unknown",
    }
    payload = fixture_payload()
    payload["events"] = []
    away_team_ids = ["364", "360", "363", "368", "370", "382", "361"]
    for index, (provider_status, away_team_id) in enumerate(zip(statuses, away_team_ids)):
        event = fixture_payload(status=provider_status)["events"][0]
        event["id"] = f"40181000{index}"
        event["date"] = f"2026-08-{15 + index:02d}T14:00:00Z"
        event["competitions"][0]["competitors"][1]["team"]["id"] = away_team_id
        payload["events"].append(event)
    mock_espn(monkeypatch, payload)

    result = app.test_cli_runner().invoke(args=["sync-season", "premier-league", "2026-27"])

    assert result.exit_code == 0, result.output
    with app.app_context():
        persisted = {fixture.provider_status: fixture for fixture in Fixture.query.all()}
        assert {key: fixture.status for key, fixture in persisted.items()} == statuses
        assert persisted["STATUS_MYSTERY"].status != "completed"


def test_sync_season_rolls_back_conflicting_fixture_identity(app, monkeypatch):
    payload = fixture_payload()
    duplicate = fixture_payload()["events"][0]
    duplicate["competitions"][0]["competitors"][1]["team"]["id"] = "360"
    payload["events"].append(duplicate)
    mock_espn(monkeypatch, payload)

    result = app.test_cli_runner().invoke(args=["sync-season", "premier-league", "2026-27"])

    assert result.exit_code != 0
    assert "conflicting identity" in result.output
    with app.app_context():
        assert Fixture.query.count() == 0
        assert FixtureProviderMapping.query.count() == 0


def test_sync_season_accepts_fixture_before_espn_assigns_matchweek(app, monkeypatch):
    payload = fixture_payload()
    payload["events"][0].pop("week")
    mock_espn(monkeypatch, payload)

    result = app.test_cli_runner().invoke(args=["sync-season", "premier-league", "2026-27"])

    assert result.exit_code == 0, result.output
    with app.app_context():
        assert Fixture.query.one().matchweek is None


def test_fixture_api_exposes_public_previews_and_authenticated_filters(
    app, client, user, monkeypatch
):
    payload = fixture_payload()
    scheduled = payload["events"][0]
    completed = fixture_payload(
        kickoff="2026-08-08T14:00:00Z", status="STATUS_FULL_TIME", matchweek=1
    )["events"][0]
    completed["id"] = "401810000"
    completed["competitions"][0]["competitors"][1]["team"]["id"] = "368"
    next_matchweek = fixture_payload(
        kickoff="2026-08-22T14:00:00Z", matchweek=2
    )["events"][0]
    next_matchweek["id"] = "401810002"
    next_matchweek["competitions"][0]["competitors"][0]["team"]["id"] = "360"
    cancelled = fixture_payload(
        kickoff="2026-08-29T14:00:00Z", status="STATUS_CANCELED", matchweek=3
    )["events"][0]
    cancelled["id"] = "401810003"
    cancelled["competitions"][0]["competitors"][1]["team"]["id"] = "363"
    payload["events"] = [completed, scheduled, next_matchweek, cancelled]
    mock_espn(monkeypatch, payload)
    assert app.test_cli_runner().invoke(
        args=["sync-season", "premier-league", "2026-27"]
    ).exit_code == 0

    preview = client.get(
        "/api/competitions/premier-league/editions/2026-27/fixtures/preview"
    )
    assert preview.status_code == 200
    assert [row["id"] for row in preview.get_json()["upcoming"]] == [2, 3]
    assert [row["id"] for row in preview.get_json()["results"]] == [1]
    assert "provider_fixture_id" not in preview.get_json()["upcoming"][0]

    endpoint = "/api/competitions/premier-league/editions/2026-27/fixtures"
    assert client.get(endpoint).status_code == 401
    monkeypatch.setattr(
        "app.auth.verify_session_token",
        lambda token: {"sub": token, "email": "user@example.com"},
    )
    headers = {"Authorization": "Bearer user_123"}

    default = client.get(endpoint, headers=headers)
    assert default.status_code == 200
    assert default.get_json()["selected_matchweek"] == 1
    assert [row["status"] for row in default.get_json()["fixtures"]] == ["scheduled"]
    assert default.get_json()["matchweeks"] == [1, 2, 3]

    filtered = client.get(
        f"{endpoint}?mode=upcoming&matchweek=2&team=manchester-united",
        headers=headers,
    )
    assert [row["matchweek"] for row in filtered.get_json()["fixtures"]] == [2]
    assert filtered.get_json()["filters"] == {
        "mode": "upcoming", "matchweek": 2, "team": "manchester-united"
    }

    results = client.get(f"{endpoint}?mode=results&matchweek=1", headers=headers)
    assert [row["status"] for row in results.get_json()["fixtures"]] == ["completed"]
    assert results.get_json()["selected_matchweek"] == 1
    cancelled_results = client.get(f"{endpoint}?mode=results&matchweek=3", headers=headers)
    assert [row["status"] for row in cancelled_results.get_json()["fixtures"]] == ["cancelled"]


def test_fixture_api_rejects_invalid_filters_and_reports_unavailable_data(client, monkeypatch):
    monkeypatch.setattr(
        "app.auth.verify_session_token",
        lambda token: {"sub": token, "email": "new@example.com"},
    )
    endpoint = "/api/competitions/premier-league/editions/2026-27/fixtures"
    headers = {"Authorization": "Bearer user_new"}

    assert client.get(endpoint, headers=headers).status_code == 503
    assert client.get(f"{endpoint}?mode=invalid", headers=headers).status_code == 400
    assert client.get(f"{endpoint}?matchweek=abc", headers=headers).status_code == 400
    assert client.get(
        "/api/competitions/premier-league/editions/not-real/fixtures/preview"
    ).status_code == 404
