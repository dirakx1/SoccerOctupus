import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import requests
import pytest

from app.leagues.evidence import (
    FotMobLeagueAdapter,
    ProviderEvidence,
    Scores365LeagueAdapter,
    YouTubeLeagueAdapter,
    collect_league_evidence,
)
from app.leagues.store import LeagueSeasonStore
from app.leagues.zep import LeagueZepGraphManager, league_graph_id
from app.config import Config
from app.runtime_settings import RuntimeSettings


def _settings():
    return RuntimeSettings(
        llm_api_key="", llm_base_url="", llm_model_name="", youtube_api_key="",
        opta_api_key="", opta_base_url="", zep_api_key="", zep_graph_id="",
        swarm_parallel_agents=1, swarm_timeout_seconds=1, mc_simulations=1,
    )


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_provider_evidence_rejects_unknown_status():
    with pytest.raises(ValueError, match="unknown provider evidence status"):
        ProviderEvidence("test", "synthetic", "test", "now", "bad", {})


def test_fotmob_adapter_uses_verified_league_and_team_routes():
    league = {
        "details": {"id": 47, "name": "Premier League", "selectedSeason": "2026/2027"},
        "table": [{"data": {"table": {"all": [
            {"id": 8455, "name": "Chelsea"},
            {"id": 10204, "name": "Brighton & Hove Albion"},
        ]}}}],
    }

    def get(url, **kwargs):
        assert kwargs["headers"]["Accept"] == "application/json"
        if url.endswith("/leagues"):
            assert kwargs["params"] == {"id": 47, "season": "2026/2027"}
            return _Response(league)
        team_id = str(kwargs["params"]["id"])
        name = "Chelsea" if team_id == "8455" else "Brighton & Hove Albion"
        return _Response({
            "details": {"id": int(team_id), "name": name, "primaryLeagueId": 47},
            "stats": {"teams": [
                {"participant": {"id": 0, "name": name, "teamId": int(team_id), "stat": {"name": "rating_team", "value": 7.2}}},
                {"participant": {"id": 0, "name": name, "teamId": int(team_id), "stat": {"name": "goals_team_match", "value": 1.4}}},
            ]},
        })

    evidence = FotMobLeagueAdapter(get=get).collect(
        "Chelsea", "Brighton & Hove Albion", datetime.now(timezone.utc) + timedelta(days=1)
    )

    assert evidence.status == "admitted"
    assert evidence.evidence["Chelsea"]["providerTeamId"] == "8455"
    assert evidence.evidence["Chelsea"]["stats"]["rating_team"] == 7.2


def test_provider_probe_never_turns_network_failure_into_synthetic_evidence():
    def unavailable(*_args, **_kwargs):
        raise requests.ConnectionError("offline")

    result = collect_league_evidence(
        home="Arsenal",
        away="Chelsea",
        kickoff=datetime.now(timezone.utc) + timedelta(days=1),
        settings=_settings(),
        get=unavailable,
    )

    assert {row["provider"] for row in result} == {"SofaScore", "FotMob", "365Scores", "YouTube", "Zep", "Opta"}
    assert all(row["status"] in {"unavailable", "excluded", "error"} for row in result)
    assert all("synthetic" not in row["reason"].lower() for row in result)
    assert all({"provider", "status", "source", "fetchedAt", "reason", "evidence"} <= row.keys() for row in result)


def test_league_overview_completed_matches_counts_current_edition_only(client):
    season = LeagueSeasonStore(Config.DATA_DIR + "/leagues").load("premier-league", "2026-27")
    current_count = sum(1 for fixture in season.fixtures if fixture.get("status") == "completed")

    response = client.get("/api/leagues/premier-league/2026-27")

    assert response.status_code == 200
    assert response.get_json()["evidence"]["completedMatches"] == current_count


def test_provider_probe_excludes_live_context_after_kickoff():
    result = collect_league_evidence(
        home="Arsenal",
        away="Chelsea",
        kickoff=datetime.now(timezone.utc) - timedelta(minutes=1),
        settings=_settings(),
        get=lambda *_args, **_kwargs: pytest.fail("past kickoffs must not call providers"),
    )

    assert {row["status"] for row in result} == {"excluded"}
    assert all("leakage-safe" in row["reason"] for row in result)


def test_youtube_uses_separate_team_queries_and_admits_only_relevant_pre_kickoff_videos():
    kickoff = datetime.now(timezone.utc) + timedelta(days=1)
    queries = []

    def get(url, **kwargs):
        queries.append(kwargs["params"])
        alias = "Brighton" if "Brighton" in kwargs["params"]["q"] else "Arsenal"
        return _Response({"items": [{
            "id": {"videoId": f"{alias.lower()}-video"},
            "snippet": {
                "title": f"{alias} Premier League tactical analysis",
                "channelTitle": f"{alias} Football Channel",
                "publishedAt": (kickoff - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
            },
        }]})

    evidence = YouTubeLeagueAdapter(api_key="test-key", get=get).collect("Arsenal", "Brighton & Hove Albion", kickoff)

    assert evidence.status == "admitted"
    assert set(evidence.evidence["teams"]) == {"Arsenal", "Brighton & Hove Albion"}
    assert len(queries) == 2
    assert all(query["publishedBefore"].endswith("Z") for query in queries)
    assert all("Arsenal" not in query["q"] or "Brighton" not in query["q"] for query in queries)


def test_youtube_excludes_blocked_or_post_kickoff_results():
    kickoff = datetime.now(timezone.utc) + timedelta(days=1)

    def get(_url, **kwargs):
        alias = "Brighton" if "Brighton" in kwargs["params"]["q"] else "Arsenal"
        title = "Arsenal national team World Cup preview" if alias == "Arsenal" else "Brighton Premier League preview"
        published = kickoff + timedelta(minutes=1) if alias == "Brighton" else kickoff - timedelta(hours=1)
        return _Response({"items": [{
            "id": {"videoId": f"{alias.lower()}-video"},
            "snippet": {"title": title, "channelTitle": "Football Channel", "publishedAt": published.isoformat().replace("+00:00", "Z")},
        }]})

    evidence = YouTubeLeagueAdapter(api_key="test-key", get=get).collect("Arsenal", "Brighton & Hove Albion", kickoff)

    assert evidence.status == "excluded"
    assert "no verified pre-kickoff EPL videos" in evidence.reason


def test_365scores_reconciles_epl_fixture_before_admitting_market_odds():
    kickoff = datetime.now(timezone.utc) + timedelta(days=1)
    calls = []

    def get(_url, **kwargs):
        calls.append(kwargs)
        return _Response({"games": [{
            "competitionId": 7,
            "startTime": kickoff.isoformat(),
            "homeCompetitor": {"name": "Arsenal"},
            "awayCompetitor": {"name": "Brighton & Hove Albion"},
            "odds": {"homeOdds": 2.0, "drawOdds": 3.5, "awayOdds": 4.0},
        }]})

    evidence = Scores365LeagueAdapter(get=get).collect("Arsenal", "Brighton & Hove Albion", kickoff)

    assert evidence.status == "admitted"
    assert evidence.evidence["kickoff"] == kickoff.isoformat()
    assert calls[0]["headers"]["Origin"] == "https://www.365scores.com"
    assert calls[0]["params"]["competitions"] == "7"


def test_365scores_excludes_fixture_outside_canonical_kickoff_tolerance():
    kickoff = datetime.now(timezone.utc) + timedelta(days=1)

    def get(_url, **_kwargs):
        return _Response({"games": [{
            "competitionId": 7,
            "startTime": (kickoff + timedelta(minutes=16)).isoformat(),
            "homeCompetitor": {"name": "Arsenal"},
            "awayCompetitor": {"name": "Brighton & Hove Albion"},
            "odds": {"homeOdds": 2.0, "drawOdds": 3.5, "awayOdds": 4.0},
        }]})

    evidence = Scores365LeagueAdapter(get=get).collect("Arsenal", "Brighton & Hove Albion", kickoff)

    assert evidence.status == "excluded"
    assert "competitionId=7" in evidence.reason


def test_league_zep_graph_is_edition_scoped_and_not_world_cup_graph():
    season = LeagueSeasonStore(Config.DATA_DIR + "/leagues").load("premier-league", "2026-27")
    graph_id = LeagueZepGraphManager.graph_id(season)

    assert graph_id == league_graph_id("premier-league", "2026-27")
    assert graph_id != "fifaoctopus_world_cup_2026"
    assert all("world cup" not in episode["data"].lower() for episode in LeagueZepGraphManager.episodes(season))


def test_league_zep_standings_use_snapshot_availability_before_future_fixture():
    season = LeagueSeasonStore(Config.DATA_DIR + "/leagues").load("premier-league", "2026-27")
    raw_episodes = LeagueZepGraphManager.episodes(season)
    episodes = [json.loads(item["data"]) for item in raw_episodes]
    standings = [item for item, raw in zip(episodes, raw_episodes) if item["entity"] == "standing" and raw["created_at"]]
    fetched_at = json.loads((season.directory / "snapshot.json").read_text())["fetchedAt"]
    future_kickoff = min(item["kickoff"] for item in season.fixtures if item["status"] == "scheduled")

    assert standings
    assert all(item["competition"] == "premier-league 2026-27" for item in standings)
    assert all(raw["created_at"] == fetched_at for item, raw in zip(episodes, raw_episodes) if item["entity"] == "standing")
    assert all(datetime.fromisoformat(fetched_at) < datetime.fromisoformat(future_kickoff) for _ in standings)


def test_league_zep_build_is_locally_idempotent_and_refuses_remote_conflict():
    season = LeagueSeasonStore(Config.DATA_DIR + "/leagues").load("premier-league", "2026-27")
    graph_id = LeagueZepGraphManager.graph_id(season)
    built = replace(season, edition={**season.edition, "leagueGraph": {"graphId": graph_id}})
    never_called = LeagueZepGraphManager(client_factory=lambda **_: pytest.fail("local graph must not rebuild"))

    assert never_called.build(built, api_key="configured") == graph_id

    class ConflictGraph:
        def create(self, **_kwargs):
            raise RuntimeError("409 already exists")

    class ConflictClient:
        graph = ConflictGraph()

    unbuilt = replace(season, edition={key: value for key, value in season.edition.items() if key != "leagueGraph"})
    conflict = LeagueZepGraphManager(client_factory=lambda **_: ConflictClient())
    with pytest.raises(ValueError, match="refusing duplicate ingestion"):
        conflict.build(unbuilt, api_key="configured")


def test_provider_probe_cli_passes_edition_graph_id(app, monkeypatch):
    captured = {}
    monkeypatch.setattr("app.leagues.cli.RuntimeSettingsService.current", lambda _db: _settings())
    monkeypatch.setattr(
        "app.leagues.cli.collect_league_evidence",
        lambda **kwargs: captured.update(kwargs) or [],
    )

    result = app.test_cli_runner().invoke(
        args=["probe-league-providers", "--competition", "premier-league", "--season", "2026-27"]
    )

    assert result.exit_code == 0, result.output
    assert captured["graph_id"] == "socceroctupus_premier_league_2026_27"


def test_league_prediction_uses_canonical_future_fixture_and_exposes_provider_shape(client, user, monkeypatch):
    monkeypatch.setattr("app.auth.verify_session_token", lambda _token: {"sub": user["clerk_user_id"], "email": user["email"]})
    captured = {}
    monkeypatch.setattr(
        "app.leagues.forecast.collect_league_evidence",
        lambda **kwargs: captured.update(kwargs) or [{"provider": "SofaScore", "status": "unavailable", "source": "test", "fetchedAt": "2026-08-29T00:00:00+00:00", "reason": "offline", "evidence": {}}],
    )
    from app.api.leagues import _load

    season = _load("premier-league", "2026-27")
    fixture = next(
        item for item in season.fixtures
        if item.get("status") == "scheduled"
        and datetime.fromisoformat(item["kickoff"].replace("Z", "+00:00")) > datetime.now(timezone.utc)
    )
    teams = {str(team["id"]): team["name"] for team in season.teams}
    response = client.post(
        "/api/leagues/premier-league/2026-27/predict",
        headers={"Authorization": f"Bearer {user['clerk_user_id']}"},
        json={"fixtureId": fixture["id"], "homeTeamId": "ignored", "awayTeamId": "ignored", "kickoff": "1900-01-01T00:00:00Z"},
    )

    assert response.status_code == 200
    prediction = response.get_json()["prediction"]
    assert prediction["homeTeam"]["name"] == teams[str(fixture["homeTeamId"])]
    assert prediction["awayTeam"]["name"] == teams[str(fixture["awayTeamId"])]
    assert captured["home"] == prediction["homeTeam"]["name"]
    assert captured["away"] == prediction["awayTeam"]["name"]
    assert captured["kickoff"].isoformat() == fixture["kickoff"]
    assert set(prediction["probabilities"]) == {"home", "draw", "away"}
    assert prediction["evidence"]["adjustmentsApplied"] is False
    assert prediction["evidence"]["adjustmentVersion"] is None
    assert prediction["evidence"]["providerEvidence"][0]["status"] == "unavailable"


def test_invalid_or_past_fixture_releases_prediction_reservation(client, user, monkeypatch):
    monkeypatch.setattr("app.auth.verify_session_token", lambda _token: {"sub": user["clerk_user_id"], "email": user["email"]})
    released = []
    from app.feature_limits import release_feature_usage as real_release

    def release(cycle_id, db_session):
        released.append(cycle_id)
        real_release(cycle_id, db_session)

    monkeypatch.setattr("app.api.leagues.release_feature_usage", release)
    headers = {"Authorization": f"Bearer {user['clerk_user_id']}"}

    unknown = client.post("/api/leagues/premier-league/2026-27/predict", headers=headers, json={"fixtureId": "unknown"})
    past = client.post("/api/leagues/premier-league/2026-27/predict", headers=headers, json={"fixtureId": "401879301"})

    assert unknown.status_code == 400
    assert "unknown fixtureId" in unknown.get_json()["error"]
    assert past.status_code == 400
    assert "not scheduled" in past.get_json()["error"]
    assert len(released) == 2


def test_specialist_reports_preserve_provider_status_and_numeric_boundary():
    from app.leagues.evidence import specialist_reports

    rows = specialist_reports([
        {"provider": "Zep", "status": "admitted", "source": "graph", "fetchedAt": "2026-08-30T10:00:00+00:00", "reason": "verified"},
        {"provider": "FotMob", "status": "admitted", "source": "fotmob", "fetchedAt": "2026-08-30T10:00:00+00:00", "reason": "verified"},
    ], fotmob_adjustment_applied=True)
    by_name = {row["name"]: row for row in rows}
    assert by_name["Tactical"]["status"] == "admitted"
    assert by_name["Live data"]["numericContribution"] is True
    assert by_name["Tactical"]["numericContribution"] is False
    assert by_name["Video intelligence"]["status"] == "unavailable"
