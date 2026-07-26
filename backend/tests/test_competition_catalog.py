def test_premier_league_catalog_resolves_current_and_immutable_editions(client):
    catalog = client.get("/api/competitions")

    assert catalog.status_code == 200
    assert catalog.get_json() == {
        "competitions": [
            {
                "slug": "premier-league",
                "display_name": "Premier League",
                "current_edition": {
                    "slug": "2026-27",
                    "display_name": "Premier League 2026-27",
                    "format": "league",
                    "capabilities": [
                        "table",
                        "fixtures",
                        "predictions",
                        "markets",
                    ],
                    "current_from": "2026-07-01",
                    "current_until": "2027-06-30",
                },
            }
        ]
    }

    current = client.get("/api/competitions/premier-league")
    immutable = client.get("/api/competitions/premier-league/editions/2026-27")

    assert current.status_code == 200
    assert current.get_json() == immutable.get_json()
    assert "provider" not in str(current.get_json()).lower()

    assert client.get("/api/competitions/not-real").status_code == 404
    assert client.get(
        "/api/competitions/premier-league/editions/not-real"
    ).status_code == 404
    assert client.get(
        "/api/competitions/not-real/editions/2026-27"
    ).status_code == 404


def test_current_edition_resolution_uses_configured_window_and_falls_back():
    from datetime import date

    from app.competitions.registry import get_competition

    assert get_competition("premier-league", date(2026, 6, 30)) is None
    assert get_competition("premier-league", date(2026, 7, 1)).edition_slug == "2026-27"
    assert get_competition("premier-league", date(2027, 6, 30)).edition_slug == "2026-27"
    assert get_competition("premier-league", date(2027, 7, 1)).edition_slug == "2026-27"
