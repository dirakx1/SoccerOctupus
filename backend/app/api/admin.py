"""Admin and account API."""

from __future__ import annotations

from flask import Blueprint, jsonify, g, request

from ..auth import require_admin, require_user
from ..billing import serialize_subscription
from ..db.base import db
from ..db.models import AppSettings
from ..runtime_settings import RuntimeSettingsService
from ..secret_store import SecretStore, SecretStoreError

bp = Blueprint("admin", __name__, url_prefix="/api")


@bp.route("/me", methods=["GET"])
@require_user(db)
def me():
    user = g.current_user
    return jsonify(
        {
            "id": user.id,
            "clerk_user_id": user.clerk_user_id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar_url": user.avatar_url,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "subscription": serialize_subscription(user),
        }
    )


@bp.route("/admin/settings", methods=["GET"])
@require_admin(db)
def get_settings():
    settings = RuntimeSettingsService.ensure_defaults(db)
    return jsonify(_serialize_settings(settings))


@bp.route("/admin/settings", methods=["PUT"])
@require_admin(db)
def update_settings():
    payload = request.get_json(force=True) or {}
    try:
        data = RuntimeSettingsService.validate_payload(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except SecretStoreError as exc:
        return jsonify({"error": str(exc)}), 500
    settings = RuntimeSettingsService.ensure_defaults(db)
    settings.llm_base_url = data["llm_base_url"]
    settings.llm_model_name = data["llm_model_name"]
    settings.zep_graph_id = data["zep_graph_id"]
    settings.opta_base_url = data["opta_base_url"]
    settings.swarm_parallel_agents = data["swarm_parallel_agents"]
    settings.swarm_timeout_seconds = data["swarm_timeout_seconds"]
    settings.mc_simulations = data["mc_simulations"]
    try:
        _apply_secret_updates(settings, payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except SecretStoreError as exc:
        return jsonify({"error": str(exc)}), 500
    settings.updated_by_user_id = g.current_user.id
    db.session.commit()
    return jsonify(_serialize_settings(settings))


def _serialize_settings(settings: AppSettings) -> dict:
    return {
        "scope": settings.scope,
        "llm_base_url": settings.llm_base_url,
        "llm_model_name": settings.llm_model_name,
        "zep_graph_id": settings.zep_graph_id,
        "opta_base_url": settings.opta_base_url,
        "swarm_parallel_agents": settings.swarm_parallel_agents,
        "swarm_timeout_seconds": settings.swarm_timeout_seconds,
        "mc_simulations": settings.mc_simulations,
        "llm_api_key_configured": bool(settings.llm_api_key_encrypted),
        "zep_api_key_configured": bool(settings.zep_api_key_encrypted),
        "youtube_api_key_configured": bool(settings.youtube_api_key_encrypted),
        "opta_api_key_configured": bool(settings.opta_api_key_encrypted),
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
        "updated_by": (
            {
                "id": settings.updated_by.id,
                "email": settings.updated_by.email,
            }
            if settings.updated_by
            else None
        ),
    }


def _apply_secret_updates(settings: AppSettings, payload: dict) -> None:
    secret_store = SecretStore()
    for name in ("llm_api_key", "zep_api_key", "youtube_api_key", "opta_api_key"):
        value = payload.get(name)
        clear = payload.get(f"clear_{name}") is True
        if clear and isinstance(value, str) and value.strip():
            raise ValueError(f"{name} cannot be set and cleared in the same request")
        if clear:
            setattr(settings, f"{name}_encrypted", None)
        elif isinstance(value, str) and value.strip():
            _verify_existing_root_key(settings, secret_store)
            setattr(settings, f"{name}_encrypted", secret_store.encrypt(value.strip()))


def _verify_existing_root_key(settings: AppSettings, secret_store: SecretStore) -> None:
    existing_ciphertexts = [
        settings.llm_api_key_encrypted,
        settings.zep_api_key_encrypted,
        settings.youtube_api_key_encrypted,
        settings.opta_api_key_encrypted,
    ]
    existing_ciphertext = next((ciphertext for ciphertext in existing_ciphertexts if ciphertext), None)
    if existing_ciphertext:
        secret_store.decrypt(existing_ciphertext)
