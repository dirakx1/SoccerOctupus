from __future__ import annotations

import json


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _seed_active_league(root, *, kickoff: str, fetched_at: str, season: str = "2026-27"):
    league = root / "leagues" / "premier-league" / season
    teams = [
        {"id": "1", "name": "Alpha FC", "abbreviation": "ALP", "provider": "espn"},
        {"id": "2", "name": "Beta FC", "abbreviation": "BET", "provider": "espn"},
    ]
    fixture = {
        "id": "fixture-1",
        "kickoff": kickoff,
        "status": "scheduled",
        "homeTeamId": "1",
        "awayTeamId": "2",
        "homeTeam": teams[0],
        "awayTeam": teams[1],
        "homeScore": None,
        "awayScore": None,
    }
    standings = [
        {"teamId": team["id"], "team": team, "position": index, "played": 0, "won": 0, "drawn": 0, "lost": 0, "goalsFor": 0, "goalsAgainst": 0, "goalDifference": 0, "points": 0}
        for index, team in enumerate(teams, 1)
    ]
    _write(root / "leagues" / "catalog.json", [{"slug": f"premier-league-{season}", "competition": "premier-league", "season": season, "displayName": f"Premier League {season}", "active": True}])
    _write(league / "edition.json", {
        "competition": "premier-league",
        "season": season,
        "displayName": f"Premier League {season}",
        "provider": {"name": "espn", "competition": "eng.1", "season": int(season[:4])},
        "startsOn": "2026-08-01",
        "endsOn": "2027-05-31",
        "promotedTeamIds": ["1"],
        "history": [{"competition": "premier-league", "season": "2025-26", "file": "history.json"}],
        "active": True,
    })
    _write(league / "history.json", {"marker": "preserve"})
    _write(league / "teams.json", teams)
    _write(league / "fixtures.json", [fixture])
    _write(league / "standings.json", standings)
    _write(league / "snapshot.json", {"provider": "espn", "fetchedAt": fetched_at, "fixtures": [fixture], "standings": standings})
    return fixture, standings


def test_active_refresh_uses_current_snapshot_only_during_match_window(app, tmp_path, monkeypatch):
    fixture, standings = _seed_active_league(tmp_path, season="2027-28", kickoff="2027-08-30T12:00:00+00:00", fetched_at="2027-08-30T00:00:00+00:00")
    calls = []

    class FakeClient:
        def snapshot(self, **kwargs):
            calls.append(kwargs)
            return {"provider": "espn", "fetchedAt": "2027-08-30T11:45:00+00:00", "fixtures": [fixture], "standings": standings}

    monkeypatch.setattr("app.config.Config.DATA_DIR", str(tmp_path))
    monkeypatch.setattr("app.leagues.season.EspnLeagueClient", lambda: FakeClient())
    monkeypatch.setattr("app.leagues.forecast.collect_league_evidence", lambda **_kwargs: [])
    result = app.test_cli_runner().invoke(args=["league-refresh-active", "--now", "2027-08-30T11:45:00Z"])

    assert result.exit_code == 0, result.output
    assert "reason=match-window,snapshot-stale" in result.output
    assert len(calls) == 1
    assert calls[0]["competition"] == "eng.1"
    assert calls[0]["season"] == 2027
    assert json.loads((tmp_path / "leagues/premier-league/2027-28/history.json").read_text()) == {"marker": "preserve"}

    forced = app.test_cli_runner().invoke(args=["league-refresh-active", "--now", "2027-08-30T11:45:00Z", "--force"])
    assert forced.exit_code == 0, forced.output
    assert "reason=forced" in forced.output
    assert len(calls) == 2


def test_active_refresh_skips_fresh_snapshot_outside_match_window(app, tmp_path, monkeypatch):
    _seed_active_league(tmp_path, kickoff="2026-09-30T12:00:00+00:00", fetched_at="2026-08-30T11:00:00+00:00")
    calls = []

    class FakeClient:
        def snapshot(self, **kwargs):
            calls.append(kwargs)
            raise AssertionError("fresh snapshots outside a match window must not refresh")

    monkeypatch.setattr("app.config.Config.DATA_DIR", str(tmp_path))
    monkeypatch.setattr("app.leagues.season.EspnLeagueClient", lambda: FakeClient())
    result = app.test_cli_runner().invoke(args=["league-refresh-active", "--now", "2026-08-30T12:00:00Z"])

    assert result.exit_code == 0, result.output
    assert "Skipped premier-league/2026-27" in result.output
    assert "outside-match-window-and-snapshot-fresh" in result.output
    assert calls == []
