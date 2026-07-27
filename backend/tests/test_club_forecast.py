from datetime import datetime, timedelta, timezone

from app.competitions.forecasting import build_club_baseline, poisson_forecast


def test_baseline_weights_recent_matches_and_adjusts_promoted_clubs():
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    matches = [
        {"played_at": now - timedelta(days=days), "goals_for": goals, "goals_against": 1}
        for days, goals in ((7, 3), (30, 2), (180, 0), (300, 0), (400, 0))
    ]

    regular = build_club_baseline(matches, promoted=False, as_of=now)
    promoted = build_club_baseline(matches, promoted=True, as_of=now)

    assert regular["attack"] > 1
    assert regular["form"] > 0.5
    assert promoted["strength"] < regular["strength"]
    assert promoted["promotion_adjustment"] == 0.88


def test_poisson_forecast_is_normalized():
    forecast = poisson_forecast(home_xg=1.7, away_xg=1.1)

    assert round(sum(forecast["outcome_probabilities"].values()), 10) == 1
    assert round(sum(row["probability"] for row in forecast["scoreline_distribution"]), 10) == 1
    assert forecast["likely_score"] in {
        f"{row['home']}-{row['away']}" for row in forecast["scoreline_distribution"]
    }
