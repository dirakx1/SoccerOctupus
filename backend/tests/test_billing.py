from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.db.base import db
from app.db.models import StripeEvent, User


class StripeLike(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def get(self, key, default=None):  # noqa: A003 - intentionally reproduces StripeObject behavior
        raise AttributeError("get")


def _auth_header(clerk_user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {clerk_user_id}"}


def _auth(monkeypatch):
    monkeypatch.setattr("app.auth.verify_session_token", lambda token: {"sub": token, "email": "user@example.com"})


def _configure_stripe(monkeypatch):
    monkeypatch.setattr("app.billing.Config.STRIPE_SECRET_KEY", "sk_test_local")
    monkeypatch.setattr("app.billing.Config.STRIPE_BASIC_PRICE_ID", "price_basic")
    monkeypatch.setattr("app.billing.Config.STRIPE_PRO_PRICE_ID", "price_pro")
    monkeypatch.setattr("app.billing.Config.FRONTEND_ORIGIN", "http://localhost:3001")
    monkeypatch.setattr("app.api.webhooks.Config.STRIPE_WEBHOOK_SECRET", "whsec_test")


def _subscription(**overrides):
    payload = {
        "id": "sub_123",
        "object": "subscription",
        "customer": "cus_123",
        "status": "active",
        "current_period_end": 1_800_000_000,
        "cancel_at_period_end": False,
        "metadata": {},
        "items": {"data": [{"price": {"id": "price_basic"}}]},
    }
    payload.update(overrides)
    return payload


def _stripe_like(value):
    if isinstance(value, dict):
        return StripeLike({key: _stripe_like(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_stripe_like(item) for item in value]
    return value


def test_plans_return_free_basic_and_pro(client):
    response = client.get("/api/billing/plans")
    assert response.status_code == 200
    plans = response.get_json()["plans"]
    assert [plan["tier"] for plan in plans] == ["free", "basic", "pro"]
    assert plans[1]["display_price"] == "$5"
    assert plans[2]["display_price"] == "$10"
    assert all("price_id" not in plan for plan in plans)


def test_checkout_rejects_unauthenticated(client):
    response = client.post("/api/billing/checkout", json={"tier": "basic"})
    assert response.status_code == 401


def test_checkout_creates_basic_and_pro_sessions(client, user, monkeypatch):
    _auth(monkeypatch)
    _configure_stripe(monkeypatch)
    created = []

    class FakeCustomer:
        @staticmethod
        def create(**kwargs):
            return {"id": "cus_123"}

    class FakeSession:
        @staticmethod
        def create(**kwargs):
            created.append(kwargs)
            return {"url": f"https://checkout.stripe.com/{kwargs['line_items'][0]['price']}"}

    fake_stripe = type(
        "FakeStripe",
        (),
        {"Customer": FakeCustomer, "checkout": type("Checkout", (), {"Session": FakeSession})},
    )
    monkeypatch.setattr("app.billing._stripe", lambda: fake_stripe)

    basic = client.post("/api/billing/checkout", headers=_auth_header(user["clerk_user_id"]), json={"tier": "basic"})
    pro = client.post("/api/billing/checkout", headers=_auth_header(user["clerk_user_id"]), json={"tier": "pro"})

    assert basic.status_code == 200
    assert pro.status_code == 200
    assert basic.get_json()["url"] == "https://checkout.stripe.com/price_basic"
    assert pro.get_json()["url"] == "https://checkout.stripe.com/price_pro"
    assert created[0]["mode"] == "subscription"
    assert created[1]["line_items"] == [{"price": "price_pro", "quantity": 1}]


def test_checkout_reuses_existing_stripe_customer(client, user, monkeypatch):
    _auth(monkeypatch)
    _configure_stripe(monkeypatch)
    created_sessions = []

    with client.application.app_context():
        entry = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()
        entry.stripe_customer_id = "cus_existing"
        db.session.commit()

    class FakeCustomer:
        @staticmethod
        def create(**kwargs):
            raise AssertionError("checkout should reuse the existing customer")

    class FakeSession:
        @staticmethod
        def create(**kwargs):
            created_sessions.append(kwargs)
            return {"url": "https://checkout.stripe.com/existing"}

    fake_stripe = type(
        "FakeStripe",
        (),
        {"Customer": FakeCustomer, "checkout": type("Checkout", (), {"Session": FakeSession})},
    )
    monkeypatch.setattr("app.billing._stripe", lambda: fake_stripe)

    response = client.post("/api/billing/checkout", headers=_auth_header(user["clerk_user_id"]), json={"tier": "basic"})

    assert response.status_code == 200
    assert created_sessions[0]["customer"] == "cus_existing"


def test_checkout_rejects_free_and_missing_config(client, user, monkeypatch):
    _auth(monkeypatch)
    monkeypatch.setattr("app.billing.Config.STRIPE_SECRET_KEY", "")

    free = client.post("/api/billing/checkout", headers=_auth_header(user["clerk_user_id"]), json={"tier": "free"})
    missing_config = client.post("/api/billing/checkout", headers=_auth_header(user["clerk_user_id"]), json={"tier": "basic"})

    assert free.status_code == 400
    assert missing_config.status_code == 400
    assert "STRIPE_SECRET_KEY" in missing_config.get_json()["error"]


def test_portal_creates_customer_when_missing(client, user, monkeypatch):
    _auth(monkeypatch)
    _configure_stripe(monkeypatch)
    created_customers = []
    created_portal_sessions = []

    class FakeCustomer:
        @staticmethod
        def create(**kwargs):
            created_customers.append(kwargs)
            return {"id": "cus_created"}

    class FakePortalSession:
        @staticmethod
        def create(**kwargs):
            created_portal_sessions.append(kwargs)
            return {"url": "https://billing.stripe.com/session"}

    fake_stripe = type(
        "FakeStripe",
        (),
        {"Customer": FakeCustomer, "billing_portal": type("BillingPortal", (), {"Session": FakePortalSession})},
    )
    monkeypatch.setattr("app.billing._stripe", lambda: fake_stripe)

    response = client.post("/api/billing/portal", headers=_auth_header(user["clerk_user_id"]), json={})
    assert response.status_code == 200
    assert response.get_json()["url"] == "https://billing.stripe.com/session"
    assert created_customers[0]["email"] == user["email"]
    assert created_portal_sessions[0]["customer"] == "cus_created"
    assert created_portal_sessions[0]["return_url"] == "http://localhost:3001/profile"


def test_invoice_listing_empty_or_sanitized(client, user, monkeypatch):
    _auth(monkeypatch)
    _configure_stripe(monkeypatch)

    billing_clerk_id = "user_billing"
    with client.application.app_context():
        entry = User(
            clerk_user_id=billing_clerk_id,
            email="billing@example.com",
            stripe_customer_id="cus_123",
            last_sign_in_at=datetime.now(timezone.utc),
        )
        db.session.add(entry)
        db.session.commit()

    empty = client.get("/api/billing/invoices", headers=_auth_header(user["clerk_user_id"]))
    assert empty.status_code == 200
    assert empty.get_json()["invoices"] == []
    class FakeInvoice:
        @staticmethod
        def list(**kwargs):
            return {
                "data": [
                    {
                        "id": "in_123",
                        "number": "INV-001",
                        "status": "paid",
                        "amount_due": 500,
                        "amount_paid": 500,
                        "currency": "usd",
                        "created": 1_800_000_000,
                        "hosted_invoice_url": "https://invoice.stripe.com/i",
                        "customer": "cus_123",
                    }
                ]
            }

    fake_stripe = type("FakeStripe", (), {"Invoice": FakeInvoice})
    monkeypatch.setattr("app.billing._stripe", lambda: fake_stripe)
    with client.application.app_context():
        from app.billing import list_invoices

        invoice = list_invoices(User.query.filter_by(clerk_user_id=billing_clerk_id).one())[0]
        assert invoice["hosted_invoice_url"] == "https://invoice.stripe.com/i"
        assert "customer" not in invoice


def test_stripe_webhook_rejects_invalid_signature(client, monkeypatch):
    _configure_stripe(monkeypatch)
    monkeypatch.setattr("app.api.webhooks.stripe.Webhook.construct_event", lambda *args: (_ for _ in ()).throw(ValueError("bad sig")))
    response = client.post("/api/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "bad"})
    assert response.status_code == 400


def test_stripe_webhook_stores_events_and_duplicates(client, user, monkeypatch):
    _configure_stripe(monkeypatch)
    event = {
        "id": "evt_123",
        "type": "customer.subscription.updated",
        "data": {"object": _subscription(customer="cus_123", metadata={"user_id": str(user["id"])})},
    }
    monkeypatch.setattr("app.api.webhooks.stripe.Webhook.construct_event", lambda *args: event)

    first = client.post("/api/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "ok"})
    duplicate = client.post("/api/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "ok"})

    assert first.status_code == 200
    assert duplicate.status_code == 200
    assert duplicate.get_json()["status"] == "duplicate"
    with client.application.app_context():
        stored = StripeEvent.query.filter_by(stripe_event_id="evt_123").one()
        updated = User.query.get(user["id"])
        assert stored.processed_at is not None
        assert updated.subscription_tier == "basic"


def test_subscription_sync_maps_basic_pro_and_deleted(client, user, monkeypatch):
    _configure_stripe(monkeypatch)
    from app.billing import sync_subscription_from_stripe_subscription

    with client.application.app_context():
        basic = sync_subscription_from_stripe_subscription(
            _subscription(customer="cus_123", metadata={"user_id": str(user["id"])}),
            db,
        )
        db.session.commit()
        assert basic.subscription_tier == "basic"

        pro = sync_subscription_from_stripe_subscription(
            _subscription(customer="cus_123", items={"data": [{"price": {"id": "price_pro"}}]}),
            db,
        )
        db.session.commit()
        assert pro.subscription_tier == "pro"

        deleted = sync_subscription_from_stripe_subscription(
            _subscription(customer="cus_123", status="canceled", items={"data": []}),
            db,
        )
        db.session.commit()
        assert deleted.subscription_tier == "free"
        assert deleted.subscription_status == "canceled"
        assert deleted.stripe_price_id is None


def test_checkout_completed_webhook_syncs_expanded_subscription(client, user, monkeypatch):
    _configure_stripe(monkeypatch)
    event = {
        "id": "evt_checkout",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_123",
                "customer": "cus_checkout",
                "client_reference_id": str(user["id"]),
                "subscription": _subscription(customer="cus_checkout", items={"data": [{"price": {"id": "price_pro"}}]}),
                "metadata": {"user_id": str(user["id"])},
            }
        },
    }
    monkeypatch.setattr("app.api.webhooks.stripe.Webhook.construct_event", lambda *args: event)

    response = client.post("/api/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "ok"})

    assert response.status_code == 200
    with client.application.app_context():
        updated = User.query.get(user["id"])
        assert updated.stripe_customer_id == "cus_checkout"
        assert updated.subscription_tier == "pro"


def test_stripe_webhook_accepts_stripe_object_events(client, user, monkeypatch):
    _configure_stripe(monkeypatch)
    event = _stripe_like(
        {
            "id": "evt_object",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_object",
                    "customer": "cus_object",
                    "client_reference_id": str(user["id"]),
                    "subscription": _subscription(
                        customer="cus_object",
                        items={"data": [{"price": {"id": "price_pro"}}]},
                    ),
                    "metadata": {"user_id": str(user["id"])},
                }
            },
        }
    )
    monkeypatch.setattr("app.api.webhooks.stripe.Webhook.construct_event", lambda *args: event)

    response = client.post("/api/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "ok"})

    assert response.status_code == 200
    with client.application.app_context():
        updated = User.query.get(user["id"])
        assert updated.stripe_customer_id == "cus_object"
        assert updated.subscription_tier == "pro"


def test_checkout_session_ownership_accepts_stripe_object_metadata(user):
    from app.billing import checkout_session_belongs_to_user

    session = _stripe_like(
        {
            "id": "cs_object",
            "customer": "cus_other",
            "client_reference_id": None,
            "metadata": {"user_id": str(user["id"])},
        }
    )
    account = User(id=user["id"], clerk_user_id=user["clerk_user_id"], email=user["email"])

    assert checkout_session_belongs_to_user(session, account) is True


def test_free_user_gets_402_from_prediction_and_markets(client, user, monkeypatch):
    _auth(monkeypatch)
    prediction = client.post(
        "/api/predictions/match",
        headers=_auth_header(user["clerk_user_id"]),
        json={"home_team": "France", "away_team": "Argentina"},
    )
    market = client.post(
        "/api/markets/match",
        headers=_auth_header(user["clerk_user_id"]),
        json={"home_team": "France", "away_team": "Argentina"},
    )
    assert prediction.status_code == 402
    assert prediction.get_json()["code"] == "subscription_required"
    assert market.status_code == 402


@pytest.mark.parametrize(("tier", "expected_video"), [("basic", False), ("pro", True)])
def test_paid_prediction_passes_video_entitlement(client, user, monkeypatch, tier, expected_video):
    _auth(monkeypatch)
    seen = []

    with client.application.app_context():
        entry = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()
        entry.subscription_tier = tier
        entry.subscription_status = "active"
        db.session.commit()

    class FakeResult:
        def to_dict(self):
            return {"agent_predictions": [], "home_team": "France", "away_team": "Argentina"}

    class FakeOrchestrator:
        def __init__(self, *, include_video_analysis=True):
            seen.append(include_video_analysis)

        def predict_match(self, *args, **kwargs):
            return FakeResult()

    monkeypatch.setattr("app.api.predictions._get_orchestrator", lambda include_video_analysis=True: FakeOrchestrator(include_video_analysis=include_video_analysis))

    response = client.post(
        "/api/predictions/match",
        headers=_auth_header(user["clerk_user_id"]),
        json={"home_team": "France", "away_team": "Argentina"},
    )

    assert response.status_code == 200
    assert seen == [expected_video]


def test_swarm_orchestrator_can_exclude_video_agent(app):
    from app.runtime_settings import RuntimeSettingsService
    from app.services.swarm_orchestrator import SwarmOrchestrator

    with app.app_context():
        settings = RuntimeSettingsService.current(db)
        orchestrator = SwarmOrchestrator(settings=settings, include_video_analysis=False)

    assert all(getattr(agent, "name", "") != "Video Intelligence Agent" for agent in orchestrator.agents)
