from __future__ import annotations

import pytest

from app.leagues.espn import EspnDataError, EspnLeagueClient


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_espn_adapter_normalizes_fixture_and_ignores_standing_metadata():
    fixture = {
        "id": "fixture-1",
        "date": "2026-08-21T19:00:00Z",
        "status": {"type": {"name": "STATUS_SCHEDULED", "state": "pre", "completed": False}},
        "competitions": [{"competitors": [
            {"homeAway": "home", "team": {"id": "1", "displayName": "Arsenal"}},
            {"homeAway": "away", "team": {"id": "2", "displayName": "Chelsea"}},
        ]}],
    }
    standings = {"children": [{"standings": {"entries": [{
        "team": {"id": "1", "displayName": "Arsenal"},
        "stats": [
            {"name": "rank", "value": 1}, {"name": "gamesPlayed", "value": 0},
            {"name": "wins", "value": 0}, {"name": "ties", "value": 0},
            {"name": "losses", "value": 0}, {"name": "pointsFor", "value": 0},
            {"name": "pointsAgainst", "value": 0}, {"name": "pointDifferential", "value": 0},
            {"name": "points", "value": 0}, {"name": "overall", "displayValue": "0-0-0"},
        ],
    }]}}]}

    def get(url, **_kwargs):
        return _Response({"events": [fixture]} if "scoreboard" in url else standings)

    snapshot = EspnLeagueClient(get=get).snapshot(
        competition="eng.1", season=2026, starts_on="2026-08-01", ends_on="2027-05-31"
    )
    assert snapshot["fixtures"][0]["status"] == "scheduled"
    assert snapshot["fixtures"][0]["homeTeamId"] == "1"
    assert snapshot["standings"][0]["position"] == 1


def test_espn_adapter_rejects_malformed_scoreboard():
    client = EspnLeagueClient(get=lambda *_args, **_kwargs: _Response({"events": {}}))
    with pytest.raises(EspnDataError, match="missing events"):
        client.fixtures(competition="eng.1", starts_on="2026-08-01", ends_on="2027-05-31")
