"""Admin and account API."""

from __future__ import annotations

from flask import Blueprint, jsonify, g, request

from ..auth import require_admin, require_user
from ..db.base import db
from ..db.models import AppSettings
from ..runtime_settings import RuntimeSettingsService

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
    data = RuntimeSettingsService.validate_payload(payload)
    settings = RuntimeSettingsService.ensure_defaults(db)
    settings.llm_base_url = data["llm_base_url"]
    settings.llm_model_name = data["llm_model_name"]
    settings.zep_graph_id = data["zep_graph_id"]
    settings.swarm_parallel_agents = data["swarm_parallel_agents"]
    settings.swarm_timeout_seconds = data["swarm_timeout_seconds"]
    settings.mc_simulations = data["mc_simulations"]
    settings.updated_by_user_id = g.current_user.id
    db.session.commit()
    return jsonify(_serialize_settings(settings))


def _serialize_settings(settings: AppSettings) -> dict:
    return {
        "scope": settings.scope,
        "llm_base_url": settings.llm_base_url,
        "llm_model_name": settings.llm_model_name,
        "zep_graph_id": settings.zep_graph_id,
        "swarm_parallel_agents": settings.swarm_parallel_agents,
        "swarm_timeout_seconds": settings.swarm_timeout_seconds,
        "mc_simulations": settings.mc_simulations,
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
