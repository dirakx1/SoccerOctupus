"""Read-only league workspace endpoints backed by season JSON snapshots."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, g, request

from ..auth import require_user
from ..config import Config
from ..db.base import db
from ..feature_limits import (
    FEATURE_MATCH_MARKET,
    FEATURE_MATCH_PREDICTION,
    FEATURE_TOURNAMENT_SIMULATION,
    release_feature_usage,
    reserve_feature_usage,
)
from ..leagues.prediction import LeaguePredictionModel, admitted_fotmob_records, project_table
from ..leagues.forecast import fixture_forecast, forecast_metrics, forecast_performance
from ..leagues.markets import match_questions, season_questions
from ..leagues.season import season_spec
from ..leagues.store import LeagueSeasonStore, SeasonDataError
from ..leagues.zep import graph_view
from ..runtime_settings import RuntimeSettingsService


bp = Blueprint("leagues", __name__, url_prefix="/api/leagues")


def _store() -> LeagueSeasonStore:
    return LeagueSeasonStore(Config.DATA_DIR + "/leagues")


def _load(competition: str, season: str):
    return _store().load(competition, season)


def _team(team: dict) -> dict:
    return {"id": str(team["id"]), "name": team["name"], "abbreviation": team.get("abbreviation")}


def _fixture(fixture: dict, teams: dict[str, dict]) -> dict:
    return {
        "id": str(fixture["id"]),
        "kickoff": fixture["kickoff"],
        "matchweek": fixture.get("matchweek"),
        "status": fixture.get("status", "scheduled"),
        "venue": fixture.get("venue"),
        "homeTeam": _team(teams[str(fixture["homeTeamId"])]),
        "awayTeam": _team(teams[str(fixture["awayTeamId"])]),
        "homeScore": fixture.get("homeScore"),
        "awayScore": fixture.get("awayScore"),
    }


def _market_metadata(data, competition: str, season: str) -> tuple[str, str]:
    edition = data.edition
    display_name = str(edition.get("competitionName") or edition.get("displayName") or competition)
    suffix = f" {season}"
    competition_name = display_name[:-len(suffix)] if display_name.endswith(suffix) else display_name
    return competition_name.strip() or competition.replace("-", " ").title(), str(edition.get("competitionTag") or competition)


def _error(error: Exception):
    return {"error": str(error)}, 404


def _upcoming_fixture(data, fixture_id: str):
    if not fixture_id:
        raise ValueError("fixtureId is required")
    fixture = next((item for item in data.fixtures if str(item.get("id")) == str(fixture_id)), None)
    if fixture is None:
        raise ValueError("unknown fixtureId")
    if fixture.get("status") != "scheduled":
        raise ValueError("fixture is not scheduled")
    try:
        kickoff = datetime.fromisoformat(str(fixture["kickoff"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("fixture kickoff is malformed") from exc
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)
    if kickoff <= datetime.now(timezone.utc):
        raise ValueError("fixture has already kicked off")
    return fixture, kickoff


@bp.get("")
def catalog():
    try:
        return {"leagues": _store().catalog()}
    except SeasonDataError as exc:
        return _error(exc)


@bp.get("/active")
def active_season():
    try:
        active = next((item for item in _store().catalog() if item.get("active")), None)
        if not active:
            return {"error": "No active league season"}, 404
        return season_overview(active["competition"], active["season"])
    except (SeasonDataError, KeyError) as exc:
        return _error(exc)


def _active_identity():
    active = next((item for item in _store().catalog() if item.get("active")), None)
    if not active:
        raise SeasonDataError("No active league season")
    return active["competition"], active["season"]


@bp.get("/active/<area>")
def active_area(area: str):
    try:
        competition, season = _active_identity()
        if area == "table":
            return table(competition, season)
        if area == "fixtures":
            return fixtures(competition, season)
        if area == "markets":
            return markets(competition, season)
        if area == "projection":
            return projection(competition, season)
        if area == "accuracy":
            return accuracy(competition, season)
        if area == "performance":
            return performance(competition, season)
        if area == "graph":
            return graph(competition, season)
        return {"error": "Unknown active league area"}, 404
    except SeasonDataError as exc:
        return _error(exc)


@bp.post("/active/predict")
def active_predict():
    try:
        competition, season = _active_identity()
        return predict(competition, season)
    except SeasonDataError as exc:
        return _error(exc)


@bp.post("/active/markets/match")
def active_match_markets():
    try:
        competition, season = _active_identity()
        return match_markets(competition, season)
    except SeasonDataError as exc:
        return _error(exc)


@bp.get("/<competition>/<season>")
def season_overview(competition: str, season: str):
    try:
        data = _load(competition, season)
    except SeasonDataError as exc:
        return _error(exc)
    teams = {str(team["id"]): team for team in data.teams}
    snapshot_fetched_at = None
    try:
        import json
        snapshot = json.loads((data.directory / "snapshot.json").read_text(encoding="utf-8"))
        snapshot_fetched_at = snapshot.get("fetchedAt") if isinstance(snapshot, dict) else None
    except (OSError, ValueError, TypeError):
        pass
    return {
        "edition": data.edition,
        "teams": [_team(team) for team in data.teams],
        "fixtures": [_fixture(item, teams) for item in data.fixtures],
        "standings": list(data.standings),
        "evidence": {
            "provider": "ESPN",
            "completedMatches": sum(1 for fixture in data.fixtures if fixture.get("status") == "completed"),
            "history": list(data.edition.get("history", ())),
            "snapshotFetchedAt": snapshot_fetched_at,
            "forecast": forecast_metrics(data),
        },
    }


@bp.get("/<competition>/<season>/fixtures")
def fixtures(competition: str, season: str):
    try:
        data = _load(competition, season)
    except SeasonDataError as exc:
        return _error(exc)
    status = request.args.get("status")
    teams = {str(team["id"]): team for team in data.teams}
    rows = data.fixtures
    if status:
        rows = tuple(item for item in rows if item.get("status") == status)
    return {"fixtures": [_fixture(item, teams) for item in rows], "provider": "ESPN"}


@bp.get("/<competition>/<season>/table")
def table(competition: str, season: str):
    try:
        data = _load(competition, season)
    except SeasonDataError as exc:
        return _error(exc)
    return {"standings": list(data.standings), "provider": "ESPN"}


@bp.post("/<competition>/<season>/predict")
@require_user(db)
def predict(competition: str, season: str):
    reservation = reserve_feature_usage(g.current_user, FEATURE_MATCH_PREDICTION, db)
    if not reservation.allowed:
        return reservation.response
    try:
        data = _load(competition, season)
        body = request.get_json(silent=True) or {}
        fixture, kickoff = _upcoming_fixture(data, str(body.get("fixtureId", "")))
        result = fixture_forecast(
            data,
            fixture,
            kickoff,
            settings=RuntimeSettingsService.current(db) if competition == "premier-league" else None,
        )
        return {"prediction": result, "provider": "ESPN"}
    except (SeasonDataError, KeyError, TypeError, ValueError) as exc:
        release_feature_usage(reservation.cycle_limit_id, db)
        return {"error": str(exc)}, 400


@bp.get("/<competition>/<season>/projection")
@require_user(db)
def projection(competition: str, season: str):
    reservation = reserve_feature_usage(g.current_user, FEATURE_TOURNAMENT_SIMULATION, db)
    if not reservation.allowed:
        return reservation.response
    try:
        data = _load(competition, season)
        count = min(max(int(request.args.get("simulations", 500)), 1), 10000)
        return {"projection": project_table(data, simulations=count), "provider": "ESPN"}
    except (SeasonDataError, ValueError) as exc:
        release_feature_usage(reservation.cycle_limit_id, db)
        return {"error": str(exc)}, 400


@bp.post("/<competition>/<season>/markets/match")
@require_user(db)
def match_markets(competition: str, season: str):
    reservation = reserve_feature_usage(g.current_user, FEATURE_MATCH_MARKET, db)
    if not reservation.allowed:
        return reservation.response
    try:
        data = _load(competition, season)
        fixture, kickoff = _upcoming_fixture(data, str((request.get_json(silent=True) or {}).get("fixtureId", "")))
        home = data.team(str(fixture["homeTeamId"]))
        away = data.team(str(fixture["awayTeamId"]))
        forecast = fixture_forecast(
            data,
            fixture,
            kickoff,
            settings=RuntimeSettingsService.current(db) if competition == "premier-league" else None,
        )
        competition_name, competition_tag = _market_metadata(data, competition, season)
        return {
            "fixture": _fixture(fixture, {str(team["id"]): team for team in data.teams}),
            "questions": match_questions(competition=competition, season=season, fixture=fixture, forecast=forecast, home=home["name"], away=away["name"], competition_name=competition_name, competition_tag=competition_tag),
            "evidence": {"provider": "ESPN", "model": forecast["modelVersion"], "pricing": "model-implied fair value", "forecastEvidence": forecast.get("evidence", {})},
        }
    except (SeasonDataError, KeyError, TypeError, ValueError) as exc:
        release_feature_usage(reservation.cycle_limit_id, db)
        return {"error": str(exc)}, 400


@bp.get("/<competition>/<season>/markets")
@require_user(db)
def markets(competition: str, season: str):
    reservation = reserve_feature_usage(g.current_user, FEATURE_TOURNAMENT_SIMULATION, db)
    if not reservation.allowed:
        return reservation.response
    try:
        data = _load(competition, season)
        upcoming = []
        teams = {str(team["id"]): team for team in data.teams}
        competition_name, competition_tag = _market_metadata(data, competition, season)
        for fixture in data.fixtures:
            if fixture.get("status") != "scheduled":
                continue
            kickoff = datetime.fromisoformat(fixture["kickoff"].replace("Z", "+00:00"))
            if kickoff <= datetime.now(timezone.utc):
                continue
            upcoming.append({
                "fixture": fixture["id"],
                "kickoff": fixture["kickoff"],
                "homeTeam": _team(teams[str(fixture["homeTeamId"])]),
                "awayTeam": _team(teams[str(fixture["awayTeamId"])]),
            })
        projected = project_table(data, simulations=500)
        season_markets = [
            {
                "team": row["team"],
                "championProbability": row["championProbability"],
                "topFourProbability": row["topFourProbability"],
                "relegationProbability": row["relegationProbability"],
            }
            for row in projected
        ]
        return {
            "fixtureMarkets": upcoming,
            "seasonMarkets": season_markets,
            "seasonQuestions": season_questions(competition=competition, season=season, end_date=data.edition.get("endsOn", ""), projected=projected, competition_name=competition_name, competition_tag=competition_tag),
            "evidence": {"provider": "ESPN", "model": "league-poisson-2026.1", "simulationCount": 500},
        }
    except (SeasonDataError, ValueError) as exc:
        release_feature_usage(reservation.cycle_limit_id, db)
        return {"error": str(exc)}, 400


@bp.get("/<competition>/<season>/accuracy")
@require_user(db)
def accuracy(competition: str, season: str):
    try:
        data = _load(competition, season)
        return {"accuracy": forecast_metrics(data), "provider": "ESPN", "model": "league-poisson-2026.1"}
    except SeasonDataError as exc:
        return _error(exc)


@bp.get("/<competition>/<season>/performance")
@require_user(db)
def performance(competition: str, season: str):
    try:
        return {"performance": forecast_performance(_load(competition, season)), "provider": "ESPN"}
    except SeasonDataError as exc:
        return _error(exc)


@bp.get("/<competition>/<season>/graph")
@require_user(db)
def graph(competition: str, season: str):
    try:
        return graph_view(_load(competition, season))
    except SeasonDataError as exc:
        return _error(exc)
