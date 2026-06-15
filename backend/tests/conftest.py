from __future__ import annotations

from datetime import datetime, timezone

import pytest
from cryptography.fernet import Fernet

from app import create_app
from app.db.base import db
from app.db.models import AppSettings, User


@pytest.fixture()
def app(tmp_path, monkeypatch):
    key_path = tmp_path / "settings-fernet.key"
    key_path.write_bytes(Fernet.generate_key())
    monkeypatch.setattr("app.secret_store.DEFAULT_KEY_PATH", key_path)

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.add(
            AppSettings(
                scope="global",
                llm_base_url="https://api.openai.com/v1",
                llm_model_name="gpt-4o",
                zep_graph_id=None,
                opta_base_url="https://api.performfeeds.com/soccerdata",
                swarm_parallel_agents=7,
                swarm_timeout_seconds=60,
                mc_simulations=10000,
            )
        )
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user(app):
    with app.app_context():
        entry = User(
            clerk_user_id="user_123",
            email="user@example.com",
            first_name="User",
            last_name="One",
            is_admin=False,
            is_active=True,
            last_sign_in_at=datetime.now(timezone.utc),
        )
        db.session.add(entry)
        db.session.commit()
        return {
            "id": entry.id,
            "clerk_user_id": entry.clerk_user_id,
            "email": entry.email,
        }


@pytest.fixture()
def admin(app):
    with app.app_context():
        entry = User(
            clerk_user_id="user_admin",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            is_admin=True,
            is_active=True,
            last_sign_in_at=datetime.now(timezone.utc),
        )
        db.session.add(entry)
        db.session.commit()
        return {
            "id": entry.id,
            "clerk_user_id": entry.clerk_user_id,
            "email": entry.email,
        }
