"""External webhooks."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..auth import build_identity_from_webhook, deactivate_user, sync_user, verify_webhook
from ..db.base import db

bp = Blueprint("webhooks", __name__, url_prefix="/api/webhooks")


@bp.route("/clerk", methods=["POST"])
def clerk_webhook():
    payload = request.get_data()
    try:
        event = verify_webhook(payload, dict(request.headers))
    except Exception as exc:
        return jsonify({"error": f"Invalid webhook: {exc}"}), 400

    event_type = event.get("type")
    if event_type in {"user.created", "user.updated"}:
        identity = build_identity_from_webhook(event)
        sync_user(identity, db, reactivate=True)
    elif event_type == "user.deleted":
        data = event.get("data", {})
        clerk_user_id = data.get("id")
        if clerk_user_id:
            deactivate_user(clerk_user_id, db)

    return jsonify({"status": "ok"}), 200
