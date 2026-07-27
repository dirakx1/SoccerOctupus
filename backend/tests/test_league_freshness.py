from datetime import datetime, timedelta, timezone

from app.competitions.editions import PREMIER_LEAGUE_2026_27
from app.competitions.freshness import freshness_limits, serialize_freshness
from app.db.models import CompetitionEditionRefresh, Fixture

from test_league_fixture_sync import fixture_payload, mock_espn


NOW = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)


def fixture(*, status="scheduled", kickoff_at=None):
    return Fixture(status=status, kickoff_at=kickoff_at or NOW + timedelta(days=1))


def state(age_seconds, *, error=None, lease_until=None):
    return CompetitionEditionRefresh(
        source_updated_at=NOW - timedelta(seconds=age_seconds),
        last_attempt_at=NOW,
        last_error=error,
        refresh_lease_until=lease_until,
    )


def test_adaptive_refresh_limits_follow_live_kickoff_season_and_offseason_windows():
    config = PREMIER_LEAGUE_2026_27
    assert freshness_limits(config, [fixture(status="in_progress")], NOW) == ("live", 30, 300)
    assert freshness_limits(config, [fixture(kickoff_at=NOW + timedelta(hours=2))], NOW) == (
        "kickoff_window", 120, 900
    )
    assert freshness_limits(config, [fixture()], NOW) == ("in_season", 900, 86400)
    assert freshness_limits(config, [], datetime(2028, 1, 1, tzinfo=timezone.utc)) == (
        "off_season", 86400, 86400
    )


def test_freshness_discloses_refresh_failure_hard_stale_and_active_refresh():
    config = PREMIER_LEAGUE_2026_27
    live = [fixture(status="in_progress")]
    assert serialize_freshness(state(30), config, live, NOW)["status"] == "fresh"
    stale = serialize_freshness(state(31, error="ESPN unavailable"), config, live, NOW)
    assert stale["status"] == "stale"
    assert stale["refresh_failed"] is True
    assert stale["retryable"] is True
    assert serialize_freshness(state(300, error="ESPN unavailable"), config, live, NOW)["status"] == "hard_stale"
    refreshing = serialize_freshness(
        state(301, lease_until=NOW + timedelta(seconds=10)), config, live, NOW
    )
    assert refreshing["status"] == "hard_stale"


def test_active_refresh_lease_reuses_persisted_data_without_another_provider_call(
    app, client, monkeypatch
):
    mock_espn(monkeypatch, fixture_payload(status="STATUS_IN_PROGRESS"))
    assert app.test_cli_runner().invoke(args=["sync-season", "premier-league", "2026-27"]).exit_code == 0
    with app.app_context():
        refresh = CompetitionEditionRefresh.query.one()
        refresh.source_updated_at = datetime.now(timezone.utc) - timedelta(seconds=31)
        refresh.refresh_lease_until = datetime.now(timezone.utc) + timedelta(seconds=30)
        app.extensions["sqlalchemy"].session.commit()
    monkeypatch.setattr(
        "app.competitions.providers.espn.requests.get",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("duplicate refresh")),
    )

    response = client.get("/api/competitions/premier-league/editions/2026-27/table/preview")

    assert response.status_code == 200
    assert response.get_json()["freshness"]["status"] == "refreshing"


def test_expired_api_data_refreshes_once_and_reuses_the_new_snapshot(app, client, monkeypatch):
    mock_espn(monkeypatch, fixture_payload(status="STATUS_IN_PROGRESS"))
    assert app.test_cli_runner().invoke(args=["sync-season", "premier-league", "2026-27"]).exit_code == 0
    with app.app_context():
        refresh = CompetitionEditionRefresh.query.one()
        refresh.source_updated_at = datetime.now(timezone.utc) - timedelta(seconds=31)
        app.extensions["sqlalchemy"].session.commit()

    calls = 0
    original_get = __import__("app.competitions.providers.espn", fromlist=["requests"]).requests.get

    def counting_get(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original_get(*args, **kwargs)

    monkeypatch.setattr("app.competitions.providers.espn.requests.get", counting_get)
    endpoint = "/api/competitions/premier-league/editions/2026-27/table/preview"
    first = client.get(endpoint)
    second = client.get(endpoint)

    assert first.status_code == second.status_code == 200
    assert first.get_json()["freshness"]["status"] == "fresh"
    assert calls == 2


def test_failed_refresh_retains_last_good_snapshot_and_recovers(app, client, monkeypatch):
    mock_espn(monkeypatch, fixture_payload(status="STATUS_IN_PROGRESS"))
    assert app.test_cli_runner().invoke(args=["sync-season", "premier-league", "2026-27"]).exit_code == 0
    with app.app_context():
        refresh = CompetitionEditionRefresh.query.one()
        refresh.source_updated_at = datetime.now(timezone.utc) - timedelta(seconds=301)
        app.extensions["sqlalchemy"].session.commit()

    monkeypatch.setattr(
        "app.competitions.providers.espn.requests.get",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("ESPN unavailable")),
    )
    endpoint = "/api/competitions/premier-league/editions/2026-27/table/preview"
    failed = client.get(endpoint)
    assert failed.status_code == 200
    assert failed.get_json()["standings"][0]["team"]["slug"] == "arsenal"
    assert failed.get_json()["freshness"]["status"] == "hard_stale"
    assert failed.get_json()["freshness"]["refresh_failed"] is True

    mock_espn(monkeypatch, fixture_payload(status="STATUS_IN_PROGRESS"))
    recovered = client.get(endpoint)
    assert recovered.status_code == 200
    assert recovered.get_json()["freshness"]["status"] == "fresh"
    assert recovered.get_json()["freshness"]["refresh_failed"] is False
