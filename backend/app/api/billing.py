"""Billing account API."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ..auth import require_user
from ..billing import (
    BillingConfigError,
    change_subscription_plan,
    checkout_session_belongs_to_user,
    create_portal_session,
    list_invoices,
    plan_catalog,
    retrieve_checkout_session,
    serialize_subscription,
    sync_subscription_from_stripe_subscription,
)
from ..db.base import db
from ..db.models import User
from ..feature_limits import serialize_usage

bp = Blueprint("billing", __name__, url_prefix="/api/billing")


def _safe_return_path(value: str | None) -> str:
    if not value or not value.startswith("/") or value.startswith("//"):
        return "/profile"
    return value


def _get_value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


@bp.route("/plans", methods=["GET"])
def plans():
    return jsonify({"plans": plan_catalog()})


@bp.route("/checkout", methods=["POST"])
@require_user(db)
def checkout():
    payload = request.get_json(silent=True) or {}
    tier = payload.get("tier")
    if tier not in {"basic", "pro"}:
        return jsonify({"error": "Select Basic or Pro to start checkout"}), 400
    try:
        return jsonify(change_subscription_plan(g.current_user, tier))
    except BillingConfigError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/change-plan", methods=["POST"])
@require_user(db)
def change_plan():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(change_subscription_plan(g.current_user, payload.get("tier")))
    except BillingConfigError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/subscription", methods=["GET"])
@require_user(db)
def subscription():
    return jsonify(serialize_subscription(g.current_user))


@bp.route("/usage", methods=["GET"])
@require_user(db)
def usage():
    return jsonify(serialize_usage(g.current_user, db))


@bp.route("/invoices", methods=["GET"])
@require_user(db)
def invoices():
    user = db.session.get(User, g.current_user.id) or g.current_user
    if not user.stripe_customer_id:
        return jsonify({"invoices": []})
    try:
        return jsonify({"invoices": list_invoices(user)})
    except BillingConfigError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/portal", methods=["POST"])
@require_user(db)
def portal():
    payload = request.get_json(silent=True) or {}
    try:
        url = create_portal_session(g.current_user, _safe_return_path(payload.get("return_path")))
    except BillingConfigError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"url": url})


@bp.route("/checkout-session/<session_id>", methods=["GET"])
@require_user(db)
def checkout_session(session_id: str):
    try:
        session = retrieve_checkout_session(session_id)
    except BillingConfigError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Checkout session not found"}), 404

    if not checkout_session_belongs_to_user(session, g.current_user):
        return jsonify({"error": "Checkout session not found"}), 404

    subscription_obj = _get_value(session, "subscription")
    if isinstance(subscription_obj, dict):
        sync_subscription_from_stripe_subscription(subscription_obj, db)
        db.session.commit()

    return jsonify(
        {
            "id": _get_value(session, "id"),
            "status": _get_value(session, "status"),
            "payment_status": _get_value(session, "payment_status"),
            "subscription": serialize_subscription(g.current_user),
        }
    )
