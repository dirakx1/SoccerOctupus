"""External webhooks."""

from __future__ import annotations

import stripe
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from ..auth import build_identity_from_webhook, deactivate_user, sync_user, verify_webhook
from ..billing import (
    BillingConfigError,
    _get_value,
    _metadata_dict,
    sync_stripe_customer_profile,
    sync_subscription_from_stripe_subscription,
)
from ..config import Config
from ..db.base import db
from ..db.models import StripeEvent, User, utcnow

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
        user = sync_user(identity, db, reactivate=True, overwrite_missing=True)
        try:
            sync_stripe_customer_profile(user, db)
        except BillingConfigError:
            pass
    elif event_type == "user.deleted":
        data = event.get("data", {})
        clerk_user_id = data.get("id")
        if clerk_user_id:
            deactivate_user(clerk_user_id, db)

    return jsonify({"status": "ok"}), 200


@bp.route("/stripe", methods=["POST"])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, Config.STRIPE_WEBHOOK_SECRET)
    except Exception as exc:
        return jsonify({"error": f"Invalid webhook: {exc}"}), 400

    event_row = StripeEvent(stripe_event_id=event["id"], event_type=event["type"])
    db.session.add(event_row)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"status": "duplicate"}), 200

    try:
        _process_stripe_event(event)
        event_row.processed_at = utcnow()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({"status": "ok"}), 200


def _process_stripe_event(event: dict) -> None:
    event_type = _get_value(event, "type")
    data = _get_value(event, "data") or {}
    obj = _get_value(data, "object") or {}

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(obj)
    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        sync_subscription_from_stripe_subscription(obj, db)
    elif event_type in {"invoice.payment_succeeded", "invoice.payment_failed"}:
        subscription_id = _get_value(obj, "subscription")
        if subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id, expand=["items.data.price"])
            sync_subscription_from_stripe_subscription(subscription, db)


def _handle_checkout_completed(session: dict) -> None:
    customer_id = _get_value(session, "customer")
    user = None
    client_reference_id = _get_value(session, "client_reference_id")
    if client_reference_id:
        user = User.query.get(client_reference_id)
    metadata = _metadata_dict(_get_value(session, "metadata"))
    if user is None and metadata.get("user_id"):
        user = User.query.get(metadata["user_id"])
    if user is None and metadata.get("clerk_user_id"):
        user = User.query.filter_by(clerk_user_id=metadata["clerk_user_id"]).one_or_none()
    if user and customer_id and not user.stripe_customer_id:
        user.stripe_customer_id = customer_id
        db.session.add(user)

    subscription = _get_value(session, "subscription")
    if isinstance(subscription, str):
        subscription = stripe.Subscription.retrieve(subscription, expand=["items.data.price"])
    if subscription:
        sync_subscription_from_stripe_subscription(subscription, db)
