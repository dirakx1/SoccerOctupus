from __future__ import annotations

from datetime import datetime, timezone

from app.db.base import db
from app.db.models import User
from app.runtime_settings import RuntimeSettingsService


def _auth_header(clerk_user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {clerk_user_id}"}


def test_protected_route_requires_auth(client):
    response = client.get("/api/me")
    assert response.status_code == 401


def test_signed_in_user_can_access_me(client, user, monkeypatch):
    monkeypatch.setattr("app.auth.verify_session_token", lambda token: {"sub": token, "email": "user@example.com"})
    response = client.get("/api/me", headers=_auth_header(user["clerk_user_id"]))
    assert response.status_code == 200
    assert response.get_json()["email"] == "user@example.com"


def test_non_admin_cannot_access_admin_settings(client, user, monkeypatch):
    monkeypatch.setattr("app.auth.verify_session_token", lambda token: {"sub": token, "email": "user@example.com"})
    response = client.get("/api/admin/settings", headers=_auth_header(user["clerk_user_id"]))
    assert response.status_code == 403


def test_admin_can_update_settings(client, admin, monkeypatch):
    monkeypatch.setattr("app.auth.verify_session_token", lambda token: {"sub": token, "email": "admin@example.com"})
    response = client.put(
        "/api/admin/settings",
        headers=_auth_header(admin["clerk_user_id"]),
        json={
            "llm_base_url": "https://api.openai.com/v1",
            "llm_model_name": "gpt-4.1",
            "zep_graph_id": "graph_123",
            "swarm_parallel_agents": 6,
            "swarm_timeout_seconds": 90,
            "mc_simulations": 15000,
        },
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["llm_model_name"] == "gpt-4.1"
    assert body["updated_by"]["email"] == "admin@example.com"


def test_validation_rejects_invalid_base_url():
    try:
        RuntimeSettingsService.validate_payload(
            {
                "llm_base_url": "https://api.openai.com",
                "llm_model_name": "gpt-4o",
                "zep_graph_id": "",
                "swarm_parallel_agents": 5,
                "swarm_timeout_seconds": 60,
                "mc_simulations": 10000,
            }
        )
    except ValueError as exc:
        assert "ending in /v1" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid llm_base_url")


def test_webhook_update_preserves_admin_flag(client, admin, monkeypatch):
    monkeypatch.setattr(
        "app.api.webhooks.verify_webhook",
        lambda payload, headers: {
            "type": "user.updated",
            "data": {
                "id": admin["clerk_user_id"],
                "first_name": "Updated",
                "last_name": "Admin",
                "email_addresses": [{"email_address": "admin@example.com"}],
                "primary_email_address_id": None,
                "image_url": "https://example.com/avatar.png",
            },
        },
    )
    response = client.post("/api/webhooks/clerk", data=b"{}")
    assert response.status_code == 200
    with client.application.app_context():
        updated = User.query.filter_by(clerk_user_id=admin["clerk_user_id"]).one()
        assert updated.is_admin is True
        assert updated.first_name == "Updated"


def test_user_deleted_deactivates_local_user(client, user, monkeypatch):
    monkeypatch.setattr(
        "app.api.webhooks.verify_webhook",
        lambda payload, headers: {"type": "user.deleted", "data": {"id": user["clerk_user_id"]}},
    )
    response = client.post("/api/webhooks/clerk", data=b"{}")
    assert response.status_code == 200
    with client.application.app_context():
        updated = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()
        assert updated.is_active is False
        assert updated.deleted_at is not None


def test_runtime_settings_update_changes_current_snapshot(app, admin):
    with app.app_context():
        settings = RuntimeSettingsService.ensure_defaults(db)
        settings.llm_model_name = "gpt-4.1-mini"
        settings.mc_simulations = 20000
        settings.updated_by_user_id = admin["id"]
        db.session.commit()

        current = RuntimeSettingsService.current(db)
        assert current.llm_model_name == "gpt-4.1-mini"
        assert current.mc_simulations == 20000


def test_lazy_upsert_creates_local_user(client, monkeypatch):
    monkeypatch.setattr(
        "app.auth.verify_session_token",
        lambda token: {
            "sub": token,
            "email_addresses": [{"email_address": "new@example.com"}],
            "primary_email_address_id": None,
            "first_name": "New",
            "last_name": "User",
            "iat": int(datetime.now(timezone.utc).timestamp()),
        },
    )
    response = client.get("/api/me", headers=_auth_header("user_new"))
    assert response.status_code == 200
    with client.application.app_context():
        created = User.query.filter_by(clerk_user_id="user_new").one()
        assert created.email == "new@example.com"
