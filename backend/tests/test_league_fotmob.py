import json
from datetime import datetime, timezone
from types import SimpleNamespace

from app.leagues.fotmob import FotMobHistoricalAuditor, _candidate_prediction
from app.leagues.prediction import LeaguePredictionModel


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_fotmob_reconciliation_quarantines_score_conflict(tmp_path):
    kickoff = "2024-08-16T19:00:00+00:00"
    season = SimpleNamespace(
        season="2024-25",
        directory=tmp_path,
        teams=({"id": "1", "name": "Arsenal"}, {"id": "2", "name": "Chelsea"}),
        fixtures=({
            "id": "espn-1", "status": "completed", "kickoff": kickoff,
            "homeTeamId": "1", "awayTeamId": "2", "homeScore": 1, "awayScore": 0,
            "homeTeam": {"name": "Arsenal"}, "awayTeam": {"name": "Chelsea"},
        },),
    )
    payload = {
        "details": {"id": 47, "name": "Premier League", "selectedSeason": "2024/2025"},
        "fixtures": {"allMatches": [{
            "id": "fotmob-1", "home": {"id": "a", "name": "Arsenal"}, "away": {"id": "c", "name": "Chelsea"},
            "status": {"utcTime": kickoff, "finished": True, "cancelled": False, "scoreStr": "2 - 0"},
        }]},
    }
    auditor = FotMobHistoricalAuditor(get=lambda _url, **_kwargs: _Response(payload), workers=1, delay=0)

    result = auditor.run(season)

    assert result["reconciledCount"] == 0
    assert result["quarantinedCount"] == 1
    assert result["quarantine"][0]["reason"] == "FotMob score conflicts with ESPN canonical score"
    assert json.loads((tmp_path / "fotmob.json").read_text())["fixtures"] == []


def test_fotmob_candidate_excludes_same_kickoff_stats():
    prior = [
        {"id": str(index), "kickoff": f"2025-08-{10 + index:02d}T15:00:00+00:00", "status": "completed", "homeTeamId": "1", "awayTeamId": "2", "homeScore": 1, "awayScore": 0}
        for index in range(1, 4)
    ]
    target = {"id": "target", "kickoff": "2025-08-20T15:00:00+00:00", "status": "completed", "homeTeamId": "1", "awayTeamId": "2", "homeScore": 1, "awayScore": 0}
    model = LeaguePredictionModel(teams=[{"id": "1", "name": "Arsenal"}, {"id": "2", "name": "Chelsea"}], completed_fixtures=prior)
    records = {
        str(index): {"espnFixtureId": str(index), "kickoff": item["kickoff"], "availableAfter": f"2025-08-{13 + index:02d}T18:00:00+00:00", "homeTeamId": "1", "awayTeamId": "2", "stats": {"xgHome": 1.0, "xgAway": 1.0, "shotsHome": 10, "shotsAway": 10}}
        for index, item in enumerate(prior, 1)
    }
    records["same-kickoff"] = {"espnFixtureId": "same-kickoff", "kickoff": target["kickoff"], "availableAfter": "2025-08-20T18:00:00+00:00", "homeTeamId": "1", "awayTeamId": "2", "stats": {"xgHome": 9.0, "xgAway": 0.1, "shotsHome": 40, "shotsAway": 1}}

    with_same, eligible = _candidate_prediction(model, target, records)
    without_same, _ = _candidate_prediction(model, target, {key: value for key, value in records.items() if key != "same-kickoff"})

    assert eligible is True
    assert with_same == without_same
