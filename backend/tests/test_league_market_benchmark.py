from types import SimpleNamespace

from app.leagues.market_benchmark import ClosingOddsAuditor


def test_market_benchmark_reconciles_opening_and_closing_prices(tmp_path):
    csv = "Date,HomeTeam,AwayTeam,FTHG,FTAG,AvgH,AvgD,AvgA,AvgCH,AvgCD,AvgCA\n01/09/2026,Arsenal,Chelsea,2,1,2.0,3.5,4.0,1.9,3.6,4.2\n"
    response = SimpleNamespace(content=csv.encode(), raise_for_status=lambda: None)
    season = SimpleNamespace(
        competition="premier-league",
        season="2026-27",
        directory=tmp_path,
        teams=({"id": "1", "name": "Arsenal"}, {"id": "2", "name": "Chelsea"}),
        fixtures=({"id": "match", "status": "completed", "kickoff": "2026-09-01T15:00:00+00:00", "homeTeamId": "1", "awayTeamId": "2", "homeScore": 2, "awayScore": 1},),
    )
    result = ClosingOddsAuditor(get=lambda *_args, **_kwargs: response).run(season)
    assert result["reconciledCount"] == 1
    assert result["fixtures"][0]["opening"]["home"] != result["fixtures"][0]["closing"]["home"]
