"""Stripe billing helpers and entitlement policy."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import stripe
from flask import jsonify
from sqlalchemy.exc import IntegrityError

from .config import Config
from .db.base import db
from .db.models import User, utcnow


PAID_STATUSES = {"active", "trialing", "past_due"}
PAID_TIERS = {"basic", "pro"}
CHECKOUT_PAYMENT_METHOD_TYPES = ["card", "cashapp"]
CHECKOUT_CURRENCY = "usd"
MANAGED_SUBSCRIPTION_STATUSES = {"active", "trialing", "past_due", "unpaid", "incomplete", "paused"}
RECOVERABLE_BILLING_STATUSES = {"past_due"}
BLOCKED_BILLING_STATUSES = {"incomplete", "incomplete_expired", "unpaid", "canceled"}
PAYMENT_RECOVERY_STATUSES = RECOVERABLE_BILLING_STATUSES | {"incomplete", "unpaid"}


class BillingConfigError(RuntimeError):
    pass


def _stripe() -> Any:
    stripe.api_key = Config.STRIPE_SECRET_KEY
    return stripe


def _price_id_for_tier(tier: str) -> str:
    return {
        "basic": Config.STRIPE_BASIC_PRICE_ID,
        "pro": Config.STRIPE_PRO_PRICE_ID,
    }.get(tier, "")


def _ensure_usd_price(stripe_client: Any, price_id: str) -> None:
    price = stripe_client.Price.retrieve(price_id)
    currency = (_get_value(price, "currency", "") or "").lower()
    if currency != CHECKOUT_CURRENCY:
        raise BillingConfigError("Stripe price must use USD currency")


def plan_catalog() -> list[dict[str, Any]]:
    return [
        {
            "tier": "free",
            "label": "Free",
            "amount": 0,
            "display_price": "$0",
            "interval": "month",
            "features": [
                "1 match prediction",
                "1 tournament simulation",
                "3 match markets",
                "3 tournament markets",
            ],
            "includes_video_analysis": False,
        },
        {
            "tier": "basic",
            "label": "Basic",
            "amount": 500,
            "display_price": "$5",
            "interval": "month",
            "features": [
                "Unlimited prediction runs",
                "Unlimited market generation",
                "No video analysis",
            ],
            "includes_video_analysis": False,
        },
        {
            "tier": "pro",
            "label": "Pro",
            "amount": 1000,
            "display_price": "$10",
            "interval": "month",
            "features": [
                "Unlimited prediction runs",
                "Unlimited market generation",
                "Includes video analysis",
            ],
            "includes_video_analysis": True,
        },
    ]


def tier_for_price_id(price_id: str | None) -> str:
    if price_id and price_id == Config.STRIPE_BASIC_PRICE_ID:
        return "basic"
    if price_id and price_id == Config.STRIPE_PRO_PRICE_ID:
        return "pro"
    return "free"


def serialize_subscription(user: User) -> dict[str, Any]:
    tier = user.subscription_tier or "free"
    return {
        "tier": tier,
        "status": user.subscription_status,
        "is_paid_entitled": is_paid_entitled(user),
        "includes_video_analysis": includes_video_analysis(user),
        "billing_health": subscription_billing_health(user),
        "current_period_start": (
            user.subscription_current_period_start.isoformat()
            if user.subscription_current_period_start
            else None
        ),
        "current_period_end": (
            user.subscription_current_period_end.isoformat()
            if user.subscription_current_period_end
            else None
        ),
        "cancel_at_period_end": bool(user.subscription_cancel_at_period_end),
        "synced_at": user.subscription_synced_at.isoformat() if user.subscription_synced_at else None,
    }


def is_paid_entitled(user: User) -> bool:
    if user.is_admin:
        return True
    return (user.subscription_tier in PAID_TIERS) and (user.subscription_status in PAID_STATUSES)


def includes_video_analysis(user: User) -> bool:
    if user.is_admin:
        return True
    return user.subscription_tier == "pro" and user.subscription_status in PAID_STATUSES


def subscription_billing_health(user: User) -> dict[str, Any]:
    tier = user.subscription_tier or "free"
    status = user.subscription_status

    def health(
        state: str,
        severity: str = "none",
        *,
        requires_attention: bool = False,
        blocks_access: bool = False,
        action: str | None = None,
        action_label: str | None = None,
        message: str = "",
    ) -> dict[str, Any]:
        return {
            "state": state,
            "severity": severity,
            "requires_attention": requires_attention,
            "blocks_access": blocks_access,
            "action": action,
            "action_label": action_label,
            "message": message,
        }

    if tier not in PAID_TIERS or not user.stripe_subscription_id:
        return health("healthy")

    if status in {"active", "trialing"}:
        if user.subscription_cancel_at_period_end:
            return health(
                "healthy",
                "info",
                action="manage_billing",
                action_label="Manage",
                message="Your plan ends at the current period end.",
            )
        return health("healthy")

    if status == "past_due":
        return health(
            "payment_failed",
            "warning",
            requires_attention=True,
            blocks_access=False,
            action="update_payment_method",
            action_label="Pay invoice",
            message="Payment failed. Pay the invoice to keep access.",
        )

    if status in {"incomplete", "unpaid"}:
        return health(
            "payment_required",
            "danger",
            requires_attention=True,
            blocks_access=True,
            action="update_payment_method",
            action_label="Pay invoice",
            message="Payment is overdue. Pay the invoice to restore access.",
        )

    if status in {"canceled", "incomplete_expired"}:
        return health(
            "canceled",
            "danger",
            requires_attention=True,
            blocks_access=True,
            action="choose_plan",
            action_label="Choose plan",
            message="Your subscription is inactive. Choose a plan to continue.",
        )

    return health("inactive")


def billing_required_response(user: User):
    if is_paid_entitled(user):
        return None
    subscription = serialize_subscription(user)
    billing_health = subscription["billing_health"]
    is_payment_recovery = billing_health.get("action") == "update_payment_method"
    return jsonify(
        {
            "error": billing_health["message"] if billing_health.get("requires_attention") else "Active subscription required",
            "code": "billing_payment_required" if is_payment_recovery else "subscription_required",
            "plans_url": "/pricing",
            "subscription": subscription,
            "billing_health": billing_health,
        }
    ), 402


def ensure_stripe_configured(*, require_prices: bool = True, require_webhook: bool = False) -> None:
    missing = []
    if not Config.STRIPE_SECRET_KEY:
        missing.append("STRIPE_SECRET_KEY")
    if require_prices:
        if not Config.STRIPE_BASIC_PRICE_ID:
            missing.append("STRIPE_BASIC_PRICE_ID")
        if not Config.STRIPE_PRO_PRICE_ID:
            missing.append("STRIPE_PRO_PRICE_ID")
    if require_webhook and not Config.STRIPE_WEBHOOK_SECRET:
        missing.append("STRIPE_WEBHOOK_SECRET")
    if missing:
        raise BillingConfigError(f"Stripe configuration missing: {', '.join(missing)}")


def _session(db_session):
    return getattr(db_session, "session", db_session)


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    try:
        return obj[key]
    except (KeyError, TypeError):
        pass
    value = getattr(obj, key, default)
    return value if value is not None else default


def _metadata_dict(metadata: Any) -> dict[str, Any]:
    if metadata is None:
        return {}
    if hasattr(metadata, "to_dict_recursive"):
        return metadata.to_dict_recursive()
    if hasattr(metadata, "to_dict"):
        return metadata.to_dict()
    if isinstance(metadata, dict):
        return {key: metadata[key] for key in metadata}
    return {}


def _customer_profile_payload(user: User) -> dict[str, Any]:
    name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
    payload: dict[str, Any] = {
        "email": user.email,
        "metadata": {
            "user_id": str(user.id),
            "clerk_user_id": user.clerk_user_id,
        },
    }
    if name:
        payload["name"] = name
    return payload


def _customer_create_payload(user: User) -> dict[str, Any]:
    payload = _customer_profile_payload(user)
    if Config.STRIPE_TEST_CLOCK_ID:
        payload["test_clock"] = Config.STRIPE_TEST_CLOCK_ID
    return payload


def sync_stripe_customer_profile(user: User, db_session) -> str:
    """Create or update the Stripe customer backing a Clerk user."""
    ensure_stripe_configured(require_prices=False)
    stripe_client = _stripe()
    payload = _customer_profile_payload(user)

    if user.stripe_customer_id:
        stripe_client.Customer.modify(user.stripe_customer_id, **payload)
        return user.stripe_customer_id

    customer = stripe_client.Customer.create(**_customer_create_payload(user))
    customer_id = _get_value(customer, "id")
    user.stripe_customer_id = customer_id
    session = _session(db_session)
    try:
        session.add(user)
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = User.query.get(user.id)
        if existing and existing.stripe_customer_id:
            stripe_client.Customer.modify(existing.stripe_customer_id, **payload)
            return existing.stripe_customer_id
        raise
    return customer_id


def ensure_customer(user: User, db_session) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id

    return sync_stripe_customer_profile(user, db_session)


def create_checkout_session(user: User, tier: str) -> str:
    if tier not in PAID_TIERS:
        raise ValueError("Unknown paid tier")
    ensure_stripe_configured()
    price_id = _price_id_for_tier(tier)
    stripe_client = _stripe()
    _ensure_usd_price(stripe_client, price_id)
    customer_id = ensure_customer(user, db)
    session = stripe_client.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        client_reference_id=str(user.id),
        payment_method_types=CHECKOUT_PAYMENT_METHOD_TYPES,
        allow_promotion_codes=True,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{Config.FRONTEND_ORIGIN}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{Config.FRONTEND_ORIGIN}/pricing?checkout=cancelled&plan={tier}",
        metadata={"user_id": str(user.id), "tier": tier},
        subscription_data={"metadata": {"user_id": str(user.id), "tier": tier}},
    )
    return session["url"] if isinstance(session, dict) else session.url


def _portal_return_url(return_path: str = "/profile") -> str:
    return f"{Config.FRONTEND_ORIGIN}{return_path}"


def _portal_session_url(user: User, return_path: str = "/profile", flow_data: dict[str, Any] | None = None) -> str:
    customer_id = ensure_customer(user, db)
    params: dict[str, Any] = {
        "customer": customer_id,
        "return_url": _portal_return_url(return_path),
    }
    if Config.STRIPE_BILLING_PORTAL_CONFIGURATION_ID:
        params["configuration"] = Config.STRIPE_BILLING_PORTAL_CONFIGURATION_ID
    if flow_data:
        params["flow_data"] = flow_data
    session = _stripe().billing_portal.Session.create(**params)
    return session["url"] if isinstance(session, dict) else session.url


def _retrieve_subscription(subscription_id: str):
    return _stripe().Subscription.retrieve(subscription_id, expand=["items.data.price"])


def _list_customer_subscriptions(customer_id: str):
    return _stripe().Subscription.list(
        customer=customer_id,
        status="all",
        limit=10,
        expand=["data.items.data.price"],
    )


def _subscription_status(subscription: dict[str, Any]) -> str | None:
    return _get_value(subscription, "status")


def _is_managed_subscription(subscription: dict[str, Any] | None) -> bool:
    if not subscription:
        return False
    status = _subscription_status(subscription)
    return status in MANAGED_SUBSCRIPTION_STATUSES


def _best_customer_subscription(customer_id: str):
    subscriptions = _list_customer_subscriptions(customer_id)
    data = _get_value(subscriptions, "data", [])
    if not data:
        return None
    active_statuses = {"active", "trialing", "past_due", "unpaid", "incomplete"}
    for subscription in data:
        if _subscription_status(subscription) in active_statuses:
            return subscription
    for subscription in data:
        if _is_managed_subscription(subscription):
            return subscription
    return data[0]


def _first_subscription_item(subscription: dict[str, Any]):
    items_obj = _get_value(subscription, "items") or {}
    items = _get_value(items_obj, "data", [])
    if not items:
        return None
    return items[0]


def _subscription_item_id(subscription: dict[str, Any]) -> str | None:
    item = _first_subscription_item(subscription)
    return _get_value(item, "id") if item else None


def _active_stripe_subscription(user: User):
    subscription = None
    if user.stripe_subscription_id:
        subscription = _retrieve_subscription(user.stripe_subscription_id)
        if not _is_managed_subscription(subscription) and user.stripe_customer_id:
            customer_subscription = _best_customer_subscription(user.stripe_customer_id)
            if _is_managed_subscription(customer_subscription):
                subscription = customer_subscription
    elif user.stripe_customer_id:
        subscription = _best_customer_subscription(user.stripe_customer_id)
    if not subscription:
        return None
    sync_subscription_from_stripe_subscription(subscription, db)
    db.session.commit()
    return subscription


def change_subscription_plan(user: User, desired_tier: str) -> dict[str, Any]:
    """Apply a server-derived subscription transition for the requested tier."""
    if desired_tier not in {"free", "basic", "pro"}:
        raise ValueError("Select Free, Basic, or Pro")
    if desired_tier in PAID_TIERS or user.stripe_subscription_id or user.stripe_customer_id:
        ensure_stripe_configured(require_prices=desired_tier in PAID_TIERS)

    subscription = _active_stripe_subscription(user)
    current_tier = tier_for_price_id(_subscription_item_price_id(subscription)) if subscription else "free"
    is_paid_subscription = _is_managed_subscription(subscription)

    if desired_tier == "free":
        if not is_paid_subscription:
            return {"action": "noop", "subscription": serialize_subscription(user)}
        subscription_id = _get_value(subscription, "id")
        if not subscription_id:
            raise BillingConfigError("Stripe subscription is missing an ID")
        flow_data = {
            "type": "subscription_cancel",
            "subscription_cancel": {"subscription": subscription_id},
            "after_completion": {
                "type": "redirect",
                "redirect": {"return_url": _portal_return_url("/profile")},
            },
        }
        return {
            "action": "subscription_cancel",
            "url": _portal_session_url(user, "/profile", flow_data),
        }

    if not is_paid_subscription:
        return {"action": "checkout", "url": create_checkout_session(user, desired_tier)}

    price_id = _price_id_for_tier(desired_tier)
    stripe_client = _stripe()
    _ensure_usd_price(stripe_client, price_id)

    current_price_id = _subscription_item_price_id(subscription)
    cancel_at_period_end = bool(_get_value(subscription, "cancel_at_period_end"))
    if current_tier == desired_tier and current_price_id == price_id and not cancel_at_period_end:
        return {"action": "noop", "subscription": serialize_subscription(user)}

    subscription_id = _get_value(subscription, "id")
    if current_tier == desired_tier and current_price_id == price_id and cancel_at_period_end:
        stripe_client.Subscription.modify(subscription_id, cancel_at_period_end=False)
        updated = _retrieve_subscription(subscription_id)
        sync_subscription_from_stripe_subscription(updated, db)
        db.session.commit()
        return {"action": "cancellation_resumed", "subscription": serialize_subscription(user)}

    item_id = _subscription_item_id(subscription)
    if not subscription_id or not item_id:
        raise BillingConfigError("Stripe subscription is missing an item to update")

    flow_data = {
        "type": "subscription_update_confirm",
        "subscription_update_confirm": {
            "subscription": subscription_id,
            "items": [{"id": item_id, "price": price_id}],
        },
        "after_completion": {
            "type": "redirect",
            "redirect": {"return_url": _portal_return_url("/profile")},
        },
    }
    return {
        "action": "subscription_update",
        "url": _portal_session_url(user, "/profile", flow_data),
    }


def create_portal_session(user: User, return_path: str = "/profile") -> str:
    ensure_stripe_configured(require_prices=False)
    return _portal_session_url(user, return_path)


def create_payment_method_update_session(user: User, return_path: str = "/profile") -> str:
    ensure_stripe_configured(require_prices=False)
    flow_data = {
        "type": "payment_method_update",
        "after_completion": {
            "type": "redirect",
            "redirect": {"return_url": _portal_return_url(return_path)},
        },
    }
    return _portal_session_url(user, return_path, flow_data)


def latest_payable_invoice_url(user: User) -> str | None:
    ensure_stripe_configured(require_prices=False)
    if not user.stripe_customer_id:
        return None
    invoices = _stripe().Invoice.list(customer=user.stripe_customer_id, status="open", limit=10)
    data = invoices.get("data", invoices) if isinstance(invoices, dict) else invoices.data
    for invoice in data:
        hosted_invoice_url = _get_value(invoice, "hosted_invoice_url")
        if hosted_invoice_url:
            return hosted_invoice_url
    return None


def create_payment_recovery_session(user: User, return_path: str = "/profile") -> str:
    invoice_url = latest_payable_invoice_url(user)
    if invoice_url:
        return invoice_url
    return create_payment_method_update_session(user, return_path)


def list_invoices(user: User, limit: int = 20) -> list[dict[str, Any]]:
    ensure_stripe_configured(require_prices=False)
    if not user.stripe_customer_id:
        return []
    invoices = _stripe().Invoice.list(customer=user.stripe_customer_id, limit=limit)
    data = invoices.get("data", invoices) if isinstance(invoices, dict) else invoices.data
    sanitized = []
    for invoice in data:
        sanitized.append(
        {
            "id": _get_value(invoice, "id"),
            "number": _get_value(invoice, "number"),
            "status": _get_value(invoice, "status"),
            "amount_due": _get_value(invoice, "amount_due"),
            "amount_paid": _get_value(invoice, "amount_paid"),
            "currency": _get_value(invoice, "currency"),
            "created": _get_value(invoice, "created"),
            "hosted_invoice_url": _get_value(invoice, "hosted_invoice_url"),
        }
        )
    return sanitized


def retrieve_checkout_session(session_id: str) -> dict[str, Any]:
    ensure_stripe_configured(require_prices=False)
    return _stripe().checkout.Session.retrieve(session_id, expand=["subscription"])


def checkout_session_belongs_to_user(session: dict[str, Any], user: User) -> bool:
    metadata = _metadata_dict(_get_value(session, "metadata"))
    return any(
        [
            _get_value(session, "customer") and _get_value(session, "customer") == user.stripe_customer_id,
            _get_value(session, "client_reference_id") == str(user.id),
            metadata.get("user_id") == str(user.id),
            metadata.get("clerk_user_id") == user.clerk_user_id,
        ]
    )


def _ts(value: int | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc)


def _subscription_item_price_id(subscription: dict[str, Any]) -> str | None:
    item = _first_subscription_item(subscription)
    if not item:
        return None
    price = _get_value(item, "price") or {}
    return _get_value(price, "id")


def _subscription_period_timestamp(subscription: dict[str, Any], key: str) -> int | None:
    value = _get_value(subscription, key)
    if value is not None:
        return value
    item = _first_subscription_item(subscription)
    return _get_value(item, key) if item else None


def sync_subscription_from_stripe_subscription(subscription: dict[str, Any], db_session) -> User | None:
    metadata = _metadata_dict(_get_value(subscription, "metadata"))
    customer_id = _get_value(subscription, "customer")
    subscription_id = _get_value(subscription, "id")
    user = None

    if customer_id:
        user = User.query.filter_by(stripe_customer_id=customer_id).one_or_none()
    if user is None and subscription_id:
        user = User.query.filter_by(stripe_subscription_id=subscription_id).one_or_none()
    if user is None and metadata.get("user_id"):
        user = User.query.get(metadata["user_id"])
    if user is None and metadata.get("clerk_user_id"):
        user = User.query.filter_by(clerk_user_id=metadata["clerk_user_id"]).one_or_none()
    if user is None:
        return None

    status = _get_value(subscription, "status")
    price_id = _subscription_item_price_id(subscription)
    deleted = status == "canceled" or (
        _get_value(subscription, "object") == "subscription" and _get_value(subscription, "deleted") is True
    )

    user.stripe_customer_id = customer_id or user.stripe_customer_id
    user.stripe_subscription_id = subscription_id or user.stripe_subscription_id
    user.subscription_status = "canceled" if deleted else status
    user.subscription_current_period_start = _ts(_subscription_period_timestamp(subscription, "current_period_start"))
    user.subscription_current_period_end = _ts(_subscription_period_timestamp(subscription, "current_period_end"))
    user.subscription_cancel_at_period_end = False if deleted else bool(_get_value(subscription, "cancel_at_period_end"))
    user.subscription_synced_at = utcnow()
    user.stripe_price_id = price_id
    user.subscription_tier = "free" if deleted else tier_for_price_id(price_id)
    if deleted:
        period_end = user.subscription_current_period_end
        now = utcnow()
        user.usage_cycle_anchor_at = period_end if period_end and period_end <= now else now
    if deleted and not price_id:
        user.stripe_price_id = None
    _session(db_session).add(user)
    return user
