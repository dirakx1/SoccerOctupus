from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.auth import ClerkIdentity, sync_user
from app.db.base import db
from app.db.models import AppSettings, User
from app.runtime_settings import RuntimeSettingsService
from app.secret_store import SecretStore, SecretStoreError


def _auth_header(clerk_user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {clerk_user_id}"}


def _settings_payload(**overrides) -> dict:
    payload = {
        "llm_base_url": "https://api.openai.com/v1",
        "llm_model_name": "gpt-4.1",
        "zep_graph_id": "graph_123",
        "opta_base_url": "https://api.performfeeds.com/soccerdata",
        "swarm_parallel_agents": 6,
        "swarm_timeout_seconds": 90,
        "mc_simulations": 15000,
    }
    payload.update(overrides)
    return payload


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

    response = client.put(
        "/api/admin/settings",
        headers=_auth_header(user["clerk_user_id"]),
        json=_settings_payload(),
    )
    assert response.status_code == 403


def test_admin_can_update_settings(client, admin, monkeypatch):
    monkeypatch.setattr("app.auth.verify_session_token", lambda token: {"sub": token, "email": "admin@example.com"})
    response = client.put(
        "/api/admin/settings",
        headers=_auth_header(admin["clerk_user_id"]),
        json=_settings_payload(),
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


def test_runtime_settings_ignore_disallowed_env(app, admin, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "env-llm")
    monkeypatch.setenv("ZEP_API_KEY", "env-zep")
    monkeypatch.setenv("YOUTUBE_API_KEY", "env-youtube")
    monkeypatch.setenv("OPTA_API_KEY", "env-opta")
    monkeypatch.setenv("LLM_MODEL_NAME", "env-model")
    monkeypatch.setenv("MC_SIMULATIONS", "1")

    with app.app_context():
        secret_store = SecretStore()
        settings = RuntimeSettingsService.ensure_defaults(db)
        settings.llm_model_name = "db-model"
        settings.opta_base_url = "https://db-opta.example/soccerdata"
        settings.mc_simulations = 22222
        settings.llm_api_key_encrypted = secret_store.encrypt("db-llm")
        settings.zep_api_key_encrypted = secret_store.encrypt("db-zep")
        settings.youtube_api_key_encrypted = secret_store.encrypt("db-youtube")
        settings.opta_api_key_encrypted = secret_store.encrypt("db-opta")
        settings.updated_by_user_id = admin["id"]
        db.session.commit()

        current = RuntimeSettingsService.current(db)
        assert current.llm_model_name == "db-model"
        assert current.opta_base_url == "https://db-opta.example/soccerdata"
        assert current.mc_simulations == 22222
        assert current.llm_api_key == "db-llm"
        assert current.zep_api_key == "db-zep"
        assert current.youtube_api_key == "db-youtube"
        assert current.opta_api_key == "db-opta"


def test_admin_can_store_redacted_api_keys(client, app, admin, monkeypatch):
    monkeypatch.setattr("app.auth.verify_session_token", lambda token: {"sub": token, "email": "admin@example.com"})
    response = client.put(
        "/api/admin/settings",
        headers=_auth_header(admin["clerk_user_id"]),
        json=_settings_payload(
            llm_api_key="llm-secret",
            zep_api_key="zep-secret",
            youtube_api_key="youtube-secret",
            opta_api_key="opta-secret",
        ),
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["llm_api_key_configured"] is True
    assert body["zep_api_key_configured"] is True
    assert body["youtube_api_key_configured"] is True
    assert body["opta_api_key_configured"] is True
    assert "llm_api_key" not in body
    assert "llm_api_key_encrypted" not in body

    with app.app_context():
        settings = db.session.get(AppSettings, "global")
        assert settings.llm_api_key_encrypted.startswith("gAAAA")
        current = RuntimeSettingsService.current(db)
        assert current.llm_api_key == "llm-secret"
        assert current.zep_api_key == "zep-secret"
        assert current.youtube_api_key == "youtube-secret"
        assert current.opta_api_key == "opta-secret"


def test_blank_secret_input_leaves_existing_ciphertext(client, app, admin, monkeypatch):
    monkeypatch.setattr("app.auth.verify_session_token", lambda token: {"sub": token, "email": "admin@example.com"})
    with app.app_context():
        settings = RuntimeSettingsService.ensure_defaults(db)
        settings.llm_api_key_encrypted = SecretStore().encrypt("existing-secret")
        db.session.commit()
        original_ciphertext = settings.llm_api_key_encrypted

    response = client.put(
        "/api/admin/settings",
        headers=_auth_header(admin["clerk_user_id"]),
        json=_settings_payload(llm_api_key=""),
    )
    assert response.status_code == 200

    with app.app_context():
        settings = db.session.get(AppSettings, "global")
        assert settings.llm_api_key_encrypted == original_ciphertext
        assert RuntimeSettingsService.current(db).llm_api_key == "existing-secret"


def test_clear_secret_removes_ciphertext(client, app, admin, monkeypatch):
    monkeypatch.setattr("app.auth.verify_session_token", lambda token: {"sub": token, "email": "admin@example.com"})
    with app.app_context():
        settings = RuntimeSettingsService.ensure_defaults(db)
        settings.zep_api_key_encrypted = SecretStore().encrypt("existing-zep")
        db.session.commit()

    response = client.put(
        "/api/admin/settings",
        headers=_auth_header(admin["clerk_user_id"]),
        json=_settings_payload(clear_zep_api_key=True),
    )
    assert response.status_code == 200
    assert response.get_json()["zep_api_key_configured"] is False

    with app.app_context():
        settings = db.session.get(AppSettings, "global")
        assert settings.zep_api_key_encrypted is None
        assert RuntimeSettingsService.current(db).zep_api_key == ""


def test_conflicting_secret_update_returns_400(client, admin, monkeypatch):
    monkeypatch.setattr("app.auth.verify_session_token", lambda token: {"sub": token, "email": "admin@example.com"})
    response = client.put(
        "/api/admin/settings",
        headers=_auth_header(admin["clerk_user_id"]),
        json=_settings_payload(llm_api_key="new-secret", clear_llm_api_key=True),
    )
    assert response.status_code == 400


def test_secret_store_error_returns_json(client, admin, monkeypatch):
    monkeypatch.setattr("app.auth.verify_session_token", lambda token: {"sub": token, "email": "admin@example.com"})

    def fail_encrypt(self, value):
        raise SecretStoreError("root key problem")

    monkeypatch.setattr("app.secret_store.SecretStore.encrypt", fail_encrypt)
    response = client.put(
        "/api/admin/settings",
        headers=_auth_header(admin["clerk_user_id"]),
        json=_settings_payload(llm_api_key="new-secret"),
    )
    assert response.status_code == 500
    assert response.get_json() == {"error": "root key problem"}


def test_graph_status_uses_db_backed_zep_key(client, app, admin, monkeypatch):
    monkeypatch.setattr("app.auth.verify_session_token", lambda token: {"sub": token, "email": "admin@example.com"})
    with app.app_context():
        settings = RuntimeSettingsService.ensure_defaults(db)
        settings.zep_api_key_encrypted = None
        db.session.commit()

    response = client.get("/api/predictions/graph/status", headers=_auth_header(admin["clerk_user_id"]))
    assert response.status_code == 200
    assert response.get_json()["zep_configured"] is False

    with app.app_context():
        settings = RuntimeSettingsService.ensure_defaults(db)
        settings.zep_api_key_encrypted = SecretStore().encrypt("db-zep")
        db.session.commit()

    response = client.get("/api/predictions/graph/status", headers=_auth_header(admin["clerk_user_id"]))
    assert response.status_code == 200
    assert response.get_json()["zep_configured"] is True


def test_market_orchestrator_uses_request_time_db_llm_key(app, monkeypatch):
    captured = {}

    class FakeLLMClient:
        def __init__(self, settings):
            captured["llm_api_key"] = settings.llm_api_key

    class FakeOrchestrator:
        def __init__(self, settings, llm_client=None):
            captured["settings"] = settings
            captured["llm_client"] = llm_client

    monkeypatch.setattr("app.api.markets.LLMClient", FakeLLMClient, raising=False)
    monkeypatch.setattr("app.api.markets.SwarmOrchestrator", FakeOrchestrator)

    with app.app_context():
        from app.api.markets import _get_orc

        settings = RuntimeSettingsService.ensure_defaults(db)
        settings.llm_api_key_encrypted = SecretStore().encrypt("db-llm")
        db.session.commit()

        _get_orc()
        assert captured["llm_api_key"] == "db-llm"
        assert captured["settings"].llm_api_key == "db-llm"


def test_market_tournament_uses_request_time_mc_simulations(client, app, monkeypatch):
    captured = {}

    class FakeResult:
        champion = "France"
        runner_up = "Brazil"
        third_place = "Argentina"
        champion_probability = 0.6

    class FakeTournamentSimulator:
        def __init__(self, orchestrator=None, use_swarm=False, mc_simulations=10000):
            captured["mc_simulations"] = mc_simulations

        def simulate(self):
            return FakeResult()

    monkeypatch.setattr("app.api.markets.TournamentSimulator", FakeTournamentSimulator)
    monkeypatch.setattr("app.api.markets._gen.from_tournament", lambda _result: [])
    with app.app_context():
        settings = RuntimeSettingsService.ensure_defaults(db)
        settings.mc_simulations = 33333
        db.session.commit()

    response = client.post("/api/markets/tournament", json={})
    assert response.status_code == 200
    assert captured["mc_simulations"] == 33333


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


def test_lazy_sync_preserves_existing_email(client, user, monkeypatch):
    monkeypatch.setattr(
        "app.auth.verify_session_token",
        lambda token: {
            "sub": token,
            "first_name": "Updated",
            "last_name": None,
            "iat": int(datetime.now(timezone.utc).timestamp()),
        },
    )
    response = client.get("/api/me", headers=_auth_header(user["clerk_user_id"]))
    assert response.status_code == 200
    assert response.get_json()["email"] == "user@example.com"
    with client.application.app_context():
        updated = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()
        assert updated.email == "user@example.com"
        assert updated.first_name == "Updated"


def test_lazy_sync_without_email_uses_unique_placeholder(client, monkeypatch):
    monkeypatch.setattr(
        "app.auth.verify_session_token",
        lambda token: {
            "sub": token,
            "first_name": "Pending",
            "iat": int(datetime.now(timezone.utc).timestamp()),
        },
    )
    response = client.get("/api/me", headers=_auth_header("user_pending"))
    assert response.status_code == 200
    with client.application.app_context():
        created = User.query.filter_by(clerk_user_id="user_pending").one()
        assert created.email == "user_pending@pending.clerk.local"


def test_sync_user_recovers_from_duplicate_insert_race(app, monkeypatch):
    with app.app_context():
        existing = User(
            clerk_user_id="user_race",
            email="existing@example.com",
            first_name="Existing",
            last_name="User",
            is_admin=False,
            is_active=True,
            last_sign_in_at=datetime.now(timezone.utc),
        )
        db.session.add(existing)
        db.session.commit()

        real_query = User.query.filter_by(clerk_user_id="user_race").one()

        class FakeQuery:
            def __init__(self):
                self.calls = 0

            def filter_by(self, **kwargs):
                return self

            def one_or_none(self):
                self.calls += 1
                if self.calls == 1:
                    return None
                return real_query

        monkeypatch.setattr("app.auth.User.query", FakeQuery(), raising=False)

        original_commit = db.session.commit
        commit_calls = {"count": 0}

        def flaky_commit():
            commit_calls["count"] += 1
            if commit_calls["count"] == 1:
                raise IntegrityError("insert", {}, Exception("duplicate key"))
            return original_commit()

        monkeypatch.setattr(db.session, "commit", flaky_commit)

        identity = ClerkIdentity(
            clerk_user_id="user_race",
            email="",
            first_name="Synced",
            last_name="User",
            avatar_url="https://example.com/avatar.png",
            last_sign_in_at=datetime.now(timezone.utc),
        )

        user = sync_user(identity, db, overwrite_missing=False)

        assert user.id == real_query.id
        assert user.email == "existing@example.com"
        assert user.first_name == "Synced"
        assert user.avatar_url == "https://example.com/avatar.png"
        assert commit_calls["count"] == 2
