from __future__ import annotations

import copy
import json
from datetime import datetime, timezone

import pytest


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_season_store_loads_an_edition_and_rejects_incomplete_snapshots(tmp_path):
    from app.leagues.store import LeagueSeasonStore, SeasonDataError

    edition = tmp_path / "premier-league" / "2026-27"
    _write_json(edition / "edition.json", {
        "competition": "premier-league",
        "season": "2026-27",
        "provider": {"name": "espn", "competition": "eng.1", "season": 2026},
        "history": [],
    })
    _write_json(edition / "teams.json", [{"id": "1", "name": "Arsenal"}, {"id": "2", "name": "Chelsea"}])
    _write_json(edition / "fixtures.json", [{
        "id": "fixture-1", "kickoff": "2026-08-15T14:00:00+00:00", "status": "scheduled",
        "homeTeamId": "1", "awayTeamId": "2", "homeScore": None, "awayScore": None,
    }])
    _write_json(edition / "standings.json", [])

    season = LeagueSeasonStore(tmp_path).load("premier-league", "2026-27")
    assert season.team("1")["name"] == "Arsenal"
    assert season.fixtures[0]["awayTeamId"] == "2"

    _write_json(edition / "teams.json", [{"id": "1", "name": "Arsenal"}])
    with pytest.raises(SeasonDataError, match="unknown away team"):
        LeagueSeasonStore(tmp_path).load("premier-league", "2026-27")


def test_league_model_uses_completed_history_and_returns_normalized_markets():
    from app.leagues.prediction import LeaguePredictionModel

    completed = [
        {"id": "a", "kickoff": "2026-08-01T14:00:00+00:00", "status": "completed", "homeTeamId": "1", "awayTeamId": "2", "homeScore": 3, "awayScore": 0},
        {"id": "b", "kickoff": "2026-08-08T14:00:00+00:00", "status": "completed", "homeTeamId": "2", "awayTeamId": "1", "homeScore": 0, "awayScore": 2},
    ]
    model = LeaguePredictionModel(
        teams=[{"id": "1", "name": "Arsenal"}, {"id": "2", "name": "Chelsea"}],
        completed_fixtures=completed,
        promoted_team_ids=set(),
    )

    result = model.predict("1", "2", kickoff=datetime(2026, 8, 20, tzinfo=timezone.utc))
    assert sum(result["probabilities"].values()) == pytest.approx(1.0)
    assert result["expectedGoals"]["home"] > result["expectedGoals"]["away"]
    assert 0 <= result["markets"]["bothTeamsToScoreYes"] <= 1
    assert result["modelVersion"]
    assert result["outcome"] in {"home_win", "draw", "away_win"}
    assert sum(result["probabilities"].values()) == pytest.approx(1.0)
    assert len(result["scoreProbabilities"]) == 5
    assert result["scoreProbabilities"] == sorted(result["scoreProbabilities"], key=lambda row: row["probability"], reverse=True)
    assert len(result["analysis"]["signals"]) >= 3
    specialists = {item["name"]: item for item in result["analysis"]["specialists"]}
    assert specialists["Statistical"]["numericContribution"] is True
    assert specialists["Tactical"]["status"] == "unavailable"
    assert all(item["numericContribution"] is False for item in specialists.values() if item["name"] != "Statistical" and item["name"] != "Recent form")


def test_custom_premier_league_rollover_derives_promoted_ids_and_activates(tmp_path):
    from app.leagues.espn import EspnLeagueClient
    from app.leagues.season import SeasonManager, SeasonSpec

    def snapshot(team_ids):
        teams = [{"id": team_id, "displayName": f"Team {team_id}"} for team_id in team_ids]
        return {
            "fixtures": [],
            "standings": [{
                "teamId": team_id,
                "team": team,
                "position": index,
                "played": 0,
                "won": 0,
                "drawn": 0,
                "lost": 0,
                "goalsFor": 0,
                "goalsAgainst": 0,
                "goalDifference": 0,
                "points": 0,
            } for index, (team_id, team) in enumerate(zip(team_ids, teams), 1)],
            "fetchedAt": "2027-08-01T00:00:00+00:00",
            "provider": "espn",
        }

    snapshots = {
        ("eng.1", 2027): snapshot(["1", "2", "3"]),
        ("eng.1", 2026): snapshot(["1", "2"]),
        ("eng.2", 2026): snapshot(["3", "4"]),
    }

    def get(url, params=None, **_kwargs):
        competition = "eng.2" if "/eng.2/" in url else "eng.1"
        season = int((params or {}).get("season", 2027))
        if "scoreboard" in url:
            payload = {"events": []}
        else:
            payload = snapshots[(competition, season)]
            payload = {"children": [{"standings": {"entries": [
                {"team": row["team"], "stats": [
                    {"name": "rank", "value": row["position"]},
                    {"name": "gamesPlayed", "value": row["played"]},
                    {"name": "wins", "value": row["won"]},
                    {"name": "ties", "value": row["drawn"]},
                    {"name": "losses", "value": row["lost"]},
                    {"name": "pointsFor", "value": row["goalsFor"]},
                    {"name": "pointsAgainst", "value": row["goalsAgainst"]},
                    {"name": "pointDifferential", "value": row["goalDifference"]},
                    {"name": "points", "value": row["points"]},
                ]} for row in payload["standings"]
            ]}}]}
        return type("Response", (), {"raise_for_status": lambda self: None, "json": lambda self: payload})()

    spec = SeasonSpec(
        "premier-league", "2027-28", "eng.1", 2027, "2027-08-01", "2028-05-31", "Premier League 2027-28",
        history=(
            {"competition": "premier-league", "season": "2026-27", "providerCompetition": "eng.1", "providerSeason": 2026, "startsOn": "2026-08-01", "endsOn": "2027-05-31", "file": "prior.json"},
            {"competition": "championship", "season": "2026-27", "providerCompetition": "eng.2", "providerSeason": 2026, "startsOn": "2026-08-01", "endsOn": "2027-05-31", "file": "championship.json"},
        ),
    )
    manager = SeasonManager(tmp_path, client=EspnLeagueClient(get=get))
    manager.refresh(spec)
    manager.activate(spec)
    edition = json.loads((tmp_path / "premier-league" / "2027-28" / "edition.json").read_text())
    catalog = json.loads((tmp_path / "catalog.json").read_text())
    assert edition["promotedTeamIds"] == ["3"]
    assert edition["promotedTeamIdsSource"].startswith("derived:")
    assert next(item for item in catalog if item["active"])["slug"] == "premier-league-2027-28"


def test_league_projection_uses_goal_tiebreak_and_seed_is_deterministic(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from app.leagues.prediction import project_table

    season = SimpleNamespace(
        directory=tmp_path / "premier-league" / "2026-27",
        competition="premier-league",
        teams=({"id": "3", "name": "Third"}, {"id": "1", "name": "Winner"}, {"id": "2", "name": "Opponent"}),
        standings=({"teamId": "3", "points": 3, "goalsFor": 0, "goalsAgainst": 0}, {"teamId": "1", "points": 0, "goalsFor": 0, "goalsAgainst": 0}, {"teamId": "2", "points": 0, "goalsFor": 0, "goalsAgainst": 0}),
        fixtures=({"id": "future", "status": "scheduled", "kickoff": "2026-08-30T14:00:00+00:00", "homeTeamId": "1", "awayTeamId": "2"},),
        completed_fixtures=(),
        promoted_team_ids=set(),
    )
    monkeypatch.setattr("app.leagues.prediction.LeaguePredictionModel.predict", lambda *_args, **_kwargs: {"expectedGoals": {"home": 2.0, "away": 0.0}, "probabilities": {"home": 1.0, "draw": 0.0, "away": 0.0}})

    first = project_table(season, simulations=1, seed=7)
    second = project_table(season, simulations=1, seed=7)

    assert first == second
    assert first[0]["team"]["id"] == "1"
    assert first[0]["expectedPosition"] == 1.0
    assert set(first[0]["positionDistribution"]) == {"1", "2", "3"}


def test_league_market_questions_have_stable_fixture_and_season_contracts():
    from app.leagues.markets import match_questions, season_questions

    fixture = {"id": "fixture-1", "kickoff": "2026-08-30T14:00:00+00:00"}
    forecast = {
        "probabilities": {"home": 0.5, "draw": 0.25, "away": 0.25},
        "expectedGoals": {"home": 1.5, "away": 1.0},
        "scoreProbabilities": [{"home": 1, "away": 0, "probability": 0.2}],
        "markets": {"bothTeamsToScoreYes": 0.5, "homeCleanSheet": 0.35, "awayCleanSheet": 0.22},
        "confidence": 0.5,
    }
    fixture_rows = match_questions(competition="premier-league", season="2026-27", fixture=fixture, forecast=forecast, home="Arsenal", away="Chelsea", competition_name="Premier League", competition_tag="premier-league")
    season_rows = season_questions(competition="premier-league", season="2026-27", end_date="2027-05-31", projected=[{"team": {"id": "1", "name": "Arsenal"}, "championProbability": 0.4, "topFourProbability": 0.8, "relegationProbability": 0.01}], competition_name="Premier League", competition_tag="premier-league")

    assert len(fixture_rows) == 10
    assert len({row["question_id"] for row in fixture_rows}) == len(fixture_rows)
    assert {row["prop_type"] for row in fixture_rows} == {"match_winner", "draw", "btts", "over_under", "clean_sheet", "correct_score"}
    assert all(row["resolution"]["source"].startswith("ESPN official") for row in fixture_rows)
    assert len(season_rows) == 3
    assert all(row["resolution"]["date"] == "2027-05-31" for row in season_rows)


def test_forecast_ledger_captures_only_near_kickoff_and_keeps_probability_immutable(tmp_path):
    from types import SimpleNamespace
    from app.leagues.forecast import forecast_metrics, sync_forecast_ledger

    fixture = {"id": "near", "status": "scheduled", "kickoff": "2026-08-30T14:00:00+00:00", "homeTeamId": "1", "awayTeamId": "2"}
    far_fixture = {"id": "far", "status": "scheduled", "kickoff": "2026-08-30T16:00:00+00:00", "homeTeamId": "1", "awayTeamId": "2"}
    started_fixture = {"id": "started", "status": "scheduled", "kickoff": "2026-08-30T13:00:00+00:00", "homeTeamId": "1", "awayTeamId": "2"}
    season = SimpleNamespace(
        directory=tmp_path / "premier-league" / "2026-27", competition="premier-league", season="2026-27",
        teams=({"id": "1", "name": "Arsenal"}, {"id": "2", "name": "Chelsea"}),
        fixtures=[fixture, far_fixture, started_fixture], completed_fixtures=(), promoted_team_ids=set(),
    )
    before = sync_forecast_ledger(season, now=datetime(2026, 8, 30, 13, 30, tzinfo=timezone.utc))
    assert [row["fixtureId"] for row in before["forecasts"]] == ["near"]
    original = before["forecasts"][0]["probabilities"]
    fixture.update(status="completed", homeScore=2, awayScore=1)
    fixture["kickoff"] = "2026-08-30T14:00:00+00:00"
    resolved = sync_forecast_ledger(season, now=datetime(2026, 9, 1, tzinfo=timezone.utc))

    assert resolved["forecasts"][0]["probabilities"] == original
    assert resolved["forecasts"][0]["actual"]["outcome"] == "home"
    assert forecast_metrics(season)["status"] == "insufficient"

    final = sync_forecast_ledger(season, now=datetime(2026, 9, 1, tzinfo=timezone.utc))
    assert [row["fixtureId"] for row in final["forecasts"]] == ["near"]
    assert "evidence" in final["forecasts"][0]


def test_forecast_ledger_keeps_one_immutable_provider_snapshot(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from app.leagues.forecast import forecast_performance, sync_forecast_ledger

    fixture = {"id": "near", "status": "scheduled", "kickoff": "2026-08-30T14:00:00+00:00", "homeTeamId": "1", "awayTeamId": "2"}
    season = SimpleNamespace(
        directory=tmp_path / "premier-league" / "2026-27", competition="premier-league", season="2026-27",
        edition={"leagueGraph": {"graphId": "league-graph"}}, teams=({"id": "1", "name": "Arsenal"}, {"id": "2", "name": "Chelsea"}),
        fixtures=[fixture], completed_fixtures=(), promoted_team_ids=set(),
    )
    evidence = [{"provider": "365Scores", "status": "admitted", "source": "odds", "reason": "pre-kickoff odds", "evidence": {"homeImplied": 0.5, "drawImplied": 0.25, "awayImplied": 0.25}}]
    monkeypatch.setattr("app.leagues.forecast.collect_league_evidence", lambda **_kwargs: evidence)

    first = sync_forecast_ledger(season, now=datetime(2026, 8, 30, 13, 30, tzinfo=timezone.utc), settings=object())
    row = first["forecasts"][0]
    assert row["modelVersion"] == "league-swarm-2026.2"
    assert row["evidence"]["providerEvidence"] == evidence
    assert row["analysis"]["swarm"]["contributions"] == [{"name": "Statistical/form", "source": "ESPN completed results", "weight": 1.0}]
    original = copy.deepcopy(row)

    fixture.update(status="completed", homeScore=1, awayScore=0)
    resolved = sync_forecast_ledger(season, now=datetime(2026, 8, 31, tzinfo=timezone.utc), settings=object())
    assert {key: value for key, value in resolved["forecasts"][0].items() if key != "actual"} == original
    assert resolved["forecasts"][0]["actual"]["outcome"] == "home"
    report = forecast_performance(season)
    assert report["snapshots"] == report["resolvedSnapshots"] == 1
    provider = next(item for item in report["providers"] if item["provider"] == "365Scores")
    assert provider["snapshots"] == provider["resolvedSnapshots"] == 1
    assert provider["admission"] == "collecting"
