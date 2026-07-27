from datetime import datetime, timedelta, timezone

from app.db.base import db
from app.db.models import (
    ClubMatch,
    CompetitionEdition,
    Fixture,
    MatchPredictionVersion,
    Team,
    User,
    UserFeatureCycleLimit,
    UserMatchPredictionGrant,
)


ENDPOINT = "/api/competitions/premier-league/editions/2026-27/fixtures/1/prediction"


def _auth(monkeypatch):
    monkeypatch.setattr(
        "app.auth.verify_session_token",
        lambda token: {"sub": token, "email": f"{token}@example.com"},
    )
    monkeypatch.setattr(
        "app.api.competitions.refresh_on_demand",
        lambda config, edition: {"status": "fresh"},
    )


def _seed_fixture(app, *, status="scheduled", matches_per_team=6):
    with app.app_context():
        edition = CompetitionEdition(
            competition_slug="premier-league",
            edition_slug="2026-27",
            display_name="Premier League 2026-27",
            configuration_revision="test",
        )
        home = Team(slug="arsenal", display_name="Arsenal")
        away = Team(slug="liverpool", display_name="Liverpool")
        opponents = [Team(slug=f"opponent-{index}", display_name=f"Opponent {index}") for index in range(6)]
        db.session.add_all([edition, home, away, *opponents])
        db.session.flush()
        fixture = Fixture(
            competition_edition_id=edition.id,
            home_team=home,
            away_team=away,
            matchweek=1,
            kickoff_at=datetime(2026, 8, 15, 14, tzinfo=timezone.utc),
            status=status,
            provider_status="STATUS_SCHEDULED",
            source_updated_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
        )
        db.session.add(fixture)
        for index in range(matches_per_team):
            played_at = datetime(2026, 5, 1, tzinfo=timezone.utc) - timedelta(days=index * 7)
            db.session.add(ClubMatch(
                source="ESPN",
                source_competition="eng.1",
                source_edition="2025",
                provider_match_id=f"home-{index}",
                played_at=played_at,
                home_team=home,
                away_team=opponents[index],
                home_score=2,
                away_score=index % 2,
                source_updated_at=played_at,
            ))
            db.session.add(ClubMatch(
                source="ESPN",
                source_competition="eng.1",
                source_edition="2025",
                provider_match_id=f"away-{index}",
                played_at=played_at,
                home_team=opponents[index],
                away_team=away,
                home_score=1,
                away_score=1 + index % 2,
                source_updated_at=played_at,
            ))
        db.session.commit()


def test_reveal_creates_normalized_version_and_charges_once(app, client, user, monkeypatch):
    _auth(monkeypatch)
    _seed_fixture(app)
    headers = {"Authorization": "Bearer user_123"}

    first = client.post(ENDPOINT, headers=headers)
    second = client.post(ENDPOINT, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.get_json()
    second_body = second.get_json()
    assert first_body["reveal_status"] == "charged"
    assert second_body["reveal_status"] == "reopened"
    body = first_body["prediction"]
    assert body == second_body["prediction"]
    assert body["home_team"] == "Arsenal"
    assert body["away_team"] == "Liverpool"
    assert round(sum(body["outcome_probabilities"].values()), 8) == 1
    assert round(sum(row["probability"] for row in body["scoreline_distribution"]), 8) == 1
    assert set(body["expected_goals"]) == {"home", "away"}
    assert set(body["baseline"]["home"]) >= {"attack", "defence", "form", "strength"}
    assert body["model_version"]
    assert body["source_updated_at"]
    assert body["agents"]["available"] == ["statistical", "form"]
    assert {row["agent"] for row in body["agents"]["unavailable"]} == {
        "tactical", "live_data", "market_signals", "squad_quality", "video"
    }
    assert "generic national-team evidence" not in str(body).lower()
    with app.app_context():
        assert MatchPredictionVersion.query.count() == 1
        assert UserMatchPredictionGrant.query.count() == 1
        assert UserMatchPredictionGrant.query.one().charged is True
        usage = UserFeatureCycleLimit.query.filter_by(
            user_id=user["id"], feature_key="match_prediction"
        ).one()
        assert usage.used_count == 1


def test_reveal_requires_scheduled_fixture_and_valid_baseline_before_charge(
    app, client, user, monkeypatch
):
    _auth(monkeypatch)
    _seed_fixture(app, status="completed", matches_per_team=0)
    headers = {"Authorization": "Bearer user_123"}

    response = client.post(ENDPOINT, headers=headers)

    assert response.status_code == 409
    with app.app_context():
        assert MatchPredictionVersion.query.count() == 0
        assert UserFeatureCycleLimit.query.filter_by(user_id=user["id"]).count() == 0


def test_reveal_rejects_insufficient_real_history_without_charge(app, client, user, monkeypatch):
    _auth(monkeypatch)
    _seed_fixture(app, matches_per_team=2)

    response = client.post(ENDPOINT, headers={"Authorization": "Bearer user_123"})

    assert response.status_code == 422
    assert response.get_json()["code"] == "baseline_unavailable"
    with app.app_context():
        assert UserFeatureCycleLimit.query.filter_by(user_id=user["id"]).count() == 0


def test_prediction_grants_are_isolated_between_users(app, client, user, monkeypatch):
    _auth(monkeypatch)
    _seed_fixture(app)
    first = client.post(ENDPOINT, headers={"Authorization": "Bearer user_123"})
    version_id = first.get_json()["prediction"]["version_id"]
    with app.app_context():
        other = User(clerk_user_id="user_other", email="user_other@example.com", is_active=True)
        db.session.add(other)
        db.session.commit()

    denied = client.get(
        f"/api/competitions/premier-league/editions/2026-27/match-predictions/{version_id}",
        headers={"Authorization": "Bearer user_other"},
    )

    assert denied.status_code == 404


def test_changed_source_data_creates_and_charges_a_new_version(app, client, user, monkeypatch):
    _auth(monkeypatch)
    _seed_fixture(app)
    headers = {"Authorization": "Bearer user_123"}
    first = client.post(ENDPOINT, headers=headers)
    with app.app_context():
        user_row = db.session.get(User, user["id"])
        user_row.subscription_tier = "basic"
        user_row.subscription_status = "active"
        match = ClubMatch.query.filter_by(provider_match_id="home-0").one()
        match.home_score = 4
        match.source_updated_at = datetime(2026, 7, 28, tzinfo=timezone.utc)
        db.session.commit()

    second = client.post(ENDPOINT, headers=headers)

    assert second.status_code == 200
    assert second.get_json()["prediction"]["version_id"] != first.get_json()["prediction"]["version_id"]
    with app.app_context():
        assert MatchPredictionVersion.query.count() == 2
        assert UserMatchPredictionGrant.query.count() == 2
