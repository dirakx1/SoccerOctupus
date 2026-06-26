from __future__ import annotations

from datetime import datetime, timezone

from app.db.base import db
from app.db.models import FeatureLimitPolicy, User, UserFeatureCycleLimit
from app.feature_limits import (
    FEATURE_MATCH_MARKET,
    FEATURE_MATCH_PREDICTION,
    FEATURE_TOURNAMENT_MARKET,
    FEATURE_TOURNAMENT_SIMULATION,
    current_usage_cycle,
    ensure_cycle_limits,
    ensure_default_feature_limit_policies,
    release_feature_usage,
    reserve_feature_usage,
    serialize_usage,
)


def _auth_header(clerk_user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {clerk_user_id}"}


def _auth(monkeypatch):
    def claims(token):
        email = "admin@example.com" if token == "user_admin" else "user@example.com"
        return {"sub": token, "email": email}

    monkeypatch.setattr("app.auth.verify_session_token", claims)


def test_default_policies_are_seeded_idempotently(app):
    with app.app_context():
        ensure_default_feature_limit_policies(db)
        ensure_default_feature_limit_policies(db)

        policies = FeatureLimitPolicy.query.all()
        assert len(policies) == 12
        assert FeatureLimitPolicy.query.filter_by(tier="free", feature_key=FEATURE_MATCH_PREDICTION).one().limit_count == 1
        assert FeatureLimitPolicy.query.filter_by(tier="free", feature_key=FEATURE_TOURNAMENT_SIMULATION).one().limit_count == 1
        assert FeatureLimitPolicy.query.filter_by(tier="free", feature_key=FEATURE_MATCH_MARKET).one().limit_count == 3
        assert FeatureLimitPolicy.query.filter_by(tier="free", feature_key=FEATURE_TOURNAMENT_MARKET).one().limit_count == 3
        assert FeatureLimitPolicy.query.filter_by(tier="basic", feature_key=FEATURE_MATCH_PREDICTION).one().limit_count is None


def test_free_cycle_uses_user_anchor(app, user):
    with app.app_context():
        entry = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()
        entry.usage_cycle_anchor_at = datetime(2026, 6, 12, 10, 0, tzinfo=timezone.utc)
        db.session.commit()

        start, end, tier = current_usage_cycle(entry, db, datetime(2026, 7, 13, 9, 0, tzinfo=timezone.utc))

        assert tier == "free"
        assert start == datetime(2026, 7, 12, 10, 0, tzinfo=timezone.utc)
        assert end == datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc)


def test_paid_cycle_uses_subscription_period(app, user):
    with app.app_context():
        entry = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()
        entry.subscription_tier = "basic"
        entry.subscription_status = "active"
        entry.subscription_current_period_start = datetime(2026, 6, 20, tzinfo=timezone.utc)
        entry.subscription_current_period_end = datetime(2026, 7, 20, tzinfo=timezone.utc)
        db.session.commit()

        start, end, tier = current_usage_cycle(entry, db, datetime(2026, 7, 1, tzinfo=timezone.utc))

        assert tier == "basic"
        assert start == datetime(2026, 6, 20, tzinfo=timezone.utc)
        assert end == datetime(2026, 7, 20, tzinfo=timezone.utc)


def test_materialized_cycle_limits_do_not_change_when_policy_changes(app, user):
    with app.app_context():
        entry = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()
        rows = ensure_cycle_limits(entry, db)
        match_row = next(row for row in rows if row.feature_key == FEATURE_MATCH_PREDICTION)
        assert match_row.limit_count == 1

        policy = FeatureLimitPolicy.query.filter_by(tier="free", feature_key=FEATURE_MATCH_PREDICTION).one()
        policy.limit_count = 9
        db.session.commit()

        rows = ensure_cycle_limits(entry, db)
        match_row = next(row for row in rows if row.feature_key == FEATURE_MATCH_PREDICTION)
        assert match_row.limit_count == 1


def test_reservation_blocks_and_release_restores_usage(app, user):
    with app.app_context():
        entry = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()

        first = reserve_feature_usage(entry, FEATURE_MATCH_PREDICTION, db)
        second = reserve_feature_usage(entry, FEATURE_MATCH_PREDICTION, db)
        assert first.allowed is True
        assert second.allowed is False
        assert second.response[1] == 402

        release_feature_usage(first.cycle_limit_id, db)
        third = reserve_feature_usage(entry, FEATURE_MATCH_PREDICTION, db)
        assert third.allowed is True


def test_billing_usage_endpoint_returns_feature_rows(client, user, monkeypatch):
    _auth(monkeypatch)
    response = client.get("/api/billing/usage", headers=_auth_header(user["clerk_user_id"]))

    assert response.status_code == 200
    body = response.get_json()
    assert body["tier"] == "free"
    assert [feature["feature_key"] for feature in body["features"]] == [
        FEATURE_MATCH_PREDICTION,
        FEATURE_TOURNAMENT_SIMULATION,
        FEATURE_MATCH_MARKET,
        FEATURE_TOURNAMENT_MARKET,
    ]
    assert body["features"][0]["limit_count"] == 1


def test_admin_can_update_policy_and_override_user_cycle(client, user, admin, monkeypatch):
    _auth(monkeypatch)

    update = client.put(
        "/api/admin/feature-limits",
        headers=_auth_header(admin["clerk_user_id"]),
        json={"policies": [{"tier": "free", "feature_key": FEATURE_MATCH_PREDICTION, "limit_count": 2}]},
    )
    assert update.status_code == 200
    assert update.get_json()["tiers"]["free"][FEATURE_MATCH_PREDICTION] == 2

    override = client.put(
        f"/api/admin/users/{user['id']}/feature-cycle-limits/{FEATURE_MATCH_PREDICTION}",
        headers=_auth_header(admin["clerk_user_id"]),
        json={"limit_count": 5, "note": "support credit"},
    )
    assert override.status_code == 200
    match_row = next(feature for feature in override.get_json()["features"] if feature["feature_key"] == FEATURE_MATCH_PREDICTION)
    assert match_row["limit_count"] == 5
    assert match_row["limit_source"] == "manual_cycle_override"


def test_non_admin_cannot_update_policy(client, user, monkeypatch):
    _auth(monkeypatch)
    response = client.put(
        "/api/admin/feature-limits",
        headers=_auth_header(user["clerk_user_id"]),
        json={"policies": [{"tier": "free", "feature_key": FEATURE_MATCH_PREDICTION, "limit_count": 2}]},
    )

    assert response.status_code == 403


def test_invalid_policy_payload_returns_400(client, admin, monkeypatch):
    _auth(monkeypatch)
    response = client.put(
        "/api/admin/feature-limits",
        headers=_auth_header(admin["clerk_user_id"]),
        json={"policies": [{"tier": "free", "feature_key": "bad", "limit_count": -1}]},
    )

    assert response.status_code == 400


def test_standing_override_applies_to_new_cycle(client, user, admin, monkeypatch):
    _auth(monkeypatch)
    response = client.post(
        f"/api/admin/users/{user['id']}/feature-limit-overrides",
        headers=_auth_header(admin["clerk_user_id"]),
        json={"feature_key": FEATURE_MATCH_MARKET, "limit_count": 7, "note": "custom"},
    )

    assert response.status_code == 200
    with client.application.app_context():
        entry = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()
        UserFeatureCycleLimit.query.delete()
        db.session.commit()
        usage = serialize_usage(entry, db)
        market = next(feature for feature in usage["features"] if feature["feature_key"] == FEATURE_MATCH_MARKET)
        assert market["limit_count"] == 7
        assert market["limit_source"] == "user_override"
