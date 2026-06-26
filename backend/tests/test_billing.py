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
        "current_period_start": 1_700_000_000,
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

    class FakePrice:
        @staticmethod
        def retrieve(price_id):
            return {"id": price_id, "currency": "usd"}

    class FakeSession:
        @staticmethod
        def create(**kwargs):
            created.append(kwargs)
            return {"url": f"https://checkout.stripe.com/{kwargs['line_items'][0]['price']}"}

    class FakeSubscription:
        @staticmethod
        def list(**kwargs):
            return {"data": []}

    fake_stripe = type(
        "FakeStripe",
        (),
        {
            "Customer": FakeCustomer,
            "Price": FakePrice,
            "Subscription": FakeSubscription,
            "checkout": type("Checkout", (), {"Session": FakeSession}),
        },
    )
    monkeypatch.setattr("app.billing._stripe", lambda: fake_stripe)

    basic = client.post("/api/billing/checkout", headers=_auth_header(user["clerk_user_id"]), json={"tier": "basic"})
    pro = client.post("/api/billing/checkout", headers=_auth_header(user["clerk_user_id"]), json={"tier": "pro"})

    assert basic.status_code == 200
    assert pro.status_code == 200
    assert basic.get_json()["action"] == "checkout"
    assert pro.get_json()["action"] == "checkout"
    assert basic.get_json()["url"] == "https://checkout.stripe.com/price_basic"
    assert pro.get_json()["url"] == "https://checkout.stripe.com/price_pro"
    assert created[0]["mode"] == "subscription"
    assert created[0]["payment_method_types"] == ["card", "cashapp"]
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

    class FakePrice:
        @staticmethod
        def retrieve(price_id):
            return {"id": price_id, "currency": "usd"}

    class FakeSession:
        @staticmethod
        def create(**kwargs):
            created_sessions.append(kwargs)
            return {"url": "https://checkout.stripe.com/existing"}

    class FakeSubscription:
        @staticmethod
        def list(**kwargs):
            return {"data": []}

    fake_stripe = type(
        "FakeStripe",
        (),
        {
            "Customer": FakeCustomer,
            "Price": FakePrice,
            "Subscription": FakeSubscription,
            "checkout": type("Checkout", (), {"Session": FakeSession}),
        },
    )
    monkeypatch.setattr("app.billing._stripe", lambda: fake_stripe)

    response = client.post("/api/billing/checkout", headers=_auth_header(user["clerk_user_id"]), json={"tier": "basic"})

    assert response.status_code == 200
    assert response.get_json()["action"] == "checkout"
    assert created_sessions[0]["customer"] == "cus_existing"


def test_checkout_updates_existing_paid_subscription_from_stripe_state(client, user, monkeypatch):
    _auth(monkeypatch)
    _configure_stripe(monkeypatch)
    calls = {"checkout": 0, "portal": []}

    with client.application.app_context():
        entry = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()
        entry.stripe_customer_id = "cus_existing"
        entry.subscription_tier = "free"
        entry.subscription_status = None
        db.session.commit()

    def basic_subscription():
        return _subscription(
            id="sub_existing",
            customer="cus_existing",
            metadata={"user_id": str(user["id"])},
            items={"data": [{"id": "si_basic", "price": {"id": "price_basic"}}]},
        )

    class FakeCustomer:
        @staticmethod
        def create(**kwargs):
            raise AssertionError("plan change should not create a new customer")

    class FakePrice:
        @staticmethod
        def retrieve(price_id):
            return {"id": price_id, "currency": "usd"}

    class FakeSession:
        @staticmethod
        def create(**kwargs):
            calls["checkout"] += 1
            raise AssertionError("paid-to-paid changes should not create checkout")

    class FakePortalSession:
        @staticmethod
        def create(**kwargs):
            calls["portal"].append(kwargs)
            return {"url": "https://billing.stripe.com/update"}

    class FakeSubscription:
        @staticmethod
        def list(**kwargs):
            return {"data": [basic_subscription()]}

    fake_stripe = type(
        "FakeStripe",
        (),
        {
            "Customer": FakeCustomer,
            "Price": FakePrice,
            "Subscription": FakeSubscription,
            "billing_portal": type("BillingPortal", (), {"Session": FakePortalSession}),
            "checkout": type("Checkout", (), {"Session": FakeSession}),
        },
    )
    monkeypatch.setattr("app.billing._stripe", lambda: fake_stripe)

    response = client.post("/api/billing/checkout", headers=_auth_header(user["clerk_user_id"]), json={"tier": "pro"})

    assert response.status_code == 200
    assert response.get_json()["action"] == "subscription_update"
    assert response.get_json()["url"] == "https://billing.stripe.com/update"
    assert calls["checkout"] == 0
    assert calls["portal"] == [
        {
            "customer": "cus_existing",
            "return_url": "http://localhost:3001/profile",
            "flow_data": {
                "type": "subscription_update_confirm",
                "subscription_update_confirm": {
                    "subscription": "sub_existing",
                    "items": [{"id": "si_basic", "price": "price_pro"}],
                },
                "after_completion": {
                    "type": "redirect",
                    "redirect": {"return_url": "http://localhost:3001/profile"},
                },
            },
        }
    ]
    with client.application.app_context():
        updated = User.query.get(user["id"])
        assert updated.stripe_subscription_id == "sub_existing"
        assert updated.subscription_tier == "basic"


def test_change_plan_to_free_creates_cancel_portal_flow(client, user, monkeypatch):
    _auth(monkeypatch)
    _configure_stripe(monkeypatch)
    portal_calls = []

    with client.application.app_context():
        entry = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()
        entry.stripe_customer_id = "cus_existing"
        entry.stripe_subscription_id = "sub_existing"
        entry.subscription_tier = "pro"
        entry.subscription_status = "active"
        db.session.commit()

    def subscription(cancel_at_period_end=False):
        return _subscription(
            id="sub_existing",
            customer="cus_existing",
            metadata={"user_id": str(user["id"])},
            cancel_at_period_end=cancel_at_period_end,
            items={"data": [{"id": "si_pro", "price": {"id": "price_pro"}}]},
        )

    class FakeSubscription:
        @staticmethod
        def retrieve(subscription_id, **kwargs):
            assert subscription_id == "sub_existing"
            return subscription()

    class FakePortalSession:
        @staticmethod
        def create(**kwargs):
            portal_calls.append(kwargs)
            return {"url": "https://billing.stripe.com/cancel"}

    fake_stripe = type(
        "FakeStripe",
        (),
        {
            "Subscription": FakeSubscription,
            "billing_portal": type("BillingPortal", (), {"Session": FakePortalSession}),
        },
    )
    monkeypatch.setattr("app.billing._stripe", lambda: fake_stripe)

    response = client.post("/api/billing/change-plan", headers=_auth_header(user["clerk_user_id"]), json={"tier": "free"})

    assert response.status_code == 200
    assert response.get_json()["action"] == "subscription_cancel"
    assert response.get_json()["url"] == "https://billing.stripe.com/cancel"
    assert portal_calls == [
        {
            "customer": "cus_existing",
            "return_url": "http://localhost:3001/profile",
            "flow_data": {
                "type": "subscription_cancel",
                "subscription_cancel": {"subscription": "sub_existing"},
                "after_completion": {
                    "type": "redirect",
                    "redirect": {"return_url": "http://localhost:3001/profile"},
                },
            },
        }
    ]


def test_change_plan_same_tier_resumes_pending_cancellation(client, user, monkeypatch):
    _auth(monkeypatch)
    _configure_stripe(monkeypatch)
    modify_calls = []

    with client.application.app_context():
        entry = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()
        entry.stripe_customer_id = "cus_existing"
        entry.stripe_subscription_id = "sub_existing"
        entry.subscription_tier = "basic"
        entry.subscription_status = "active"
        entry.subscription_cancel_at_period_end = True
        db.session.commit()

    def subscription(cancel_at_period_end=True):
        return _subscription(
            id="sub_existing",
            customer="cus_existing",
            metadata={"user_id": str(user["id"])},
            cancel_at_period_end=cancel_at_period_end,
            items={"data": [{"id": "si_basic", "price": {"id": "price_basic"}}]},
        )

    class FakePrice:
        @staticmethod
        def retrieve(price_id):
            return {"id": price_id, "currency": "usd"}

    class FakeSubscription:
        @staticmethod
        def retrieve(subscription_id, **kwargs):
            assert subscription_id == "sub_existing"
            return subscription(cancel_at_period_end=not bool(modify_calls))

        @staticmethod
        def modify(subscription_id, **kwargs):
            modify_calls.append((subscription_id, kwargs))
            assert subscription_id == "sub_existing"
            return subscription(cancel_at_period_end=False)

    class FakeSubscriptionItem:
        @staticmethod
        def modify(item_id, **kwargs):
            raise AssertionError("resuming the same tier should not change the subscription item")

    fake_stripe = type(
        "FakeStripe",
        (),
        {"Price": FakePrice, "Subscription": FakeSubscription, "SubscriptionItem": FakeSubscriptionItem},
    )
    monkeypatch.setattr("app.billing._stripe", lambda: fake_stripe)

    response = client.post("/api/billing/change-plan", headers=_auth_header(user["clerk_user_id"]), json={"tier": "basic"})

    assert response.status_code == 200
    assert response.get_json()["action"] == "cancellation_resumed"
    assert response.get_json()["subscription"]["tier"] == "basic"
    assert response.get_json()["subscription"]["cancel_at_period_end"] is False
    assert modify_calls == [("sub_existing", {"cancel_at_period_end": False})]


def test_checkout_rejects_non_usd_price(client, user, monkeypatch):
    _auth(monkeypatch)
    _configure_stripe(monkeypatch)

    class FakeCustomer:
        @staticmethod
        def create(**kwargs):
            raise AssertionError("checkout should validate price before creating customer")

    class FakePrice:
        @staticmethod
        def retrieve(price_id):
            return {"id": price_id, "currency": "eur"}

    class FakeSession:
        @staticmethod
        def create(**kwargs):
            raise AssertionError("checkout should not create session for non-USD price")

    fake_stripe = type(
        "FakeStripe",
        (),
        {"Customer": FakeCustomer, "Price": FakePrice, "checkout": type("Checkout", (), {"Session": FakeSession})},
    )
    monkeypatch.setattr("app.billing._stripe", lambda: fake_stripe)

    response = client.post("/api/billing/checkout", headers=_auth_header(user["clerk_user_id"]), json={"tier": "basic"})

    assert response.status_code == 400
    assert "USD" in response.get_json()["error"]


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


def test_subscription_billing_health_for_past_due_and_unpaid(client, user):
    from app.billing import serialize_subscription

    with client.application.app_context():
        entry = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()
        entry.stripe_customer_id = "cus_existing"
        entry.stripe_subscription_id = "sub_existing"
        entry.subscription_tier = "pro"
        entry.subscription_status = "past_due"
        db.session.commit()

        past_due = serialize_subscription(entry)
        assert past_due["is_paid_entitled"] is True
        assert past_due["includes_video_analysis"] is True
        assert past_due["billing_health"]["state"] == "payment_failed"
        assert past_due["billing_health"]["action"] == "update_payment_method"
        assert past_due["billing_health"]["requires_attention"] is True
        assert past_due["billing_health"]["blocks_access"] is False

        entry.subscription_status = "unpaid"
        db.session.commit()
        unpaid = serialize_subscription(entry)
        assert unpaid["is_paid_entitled"] is False
        assert unpaid["includes_video_analysis"] is False
        assert unpaid["billing_health"]["state"] == "payment_required"
        assert unpaid["billing_health"]["action"] == "update_payment_method"
        assert unpaid["billing_health"]["blocks_access"] is True


def test_payment_recovery_prefers_open_invoice(client, user, monkeypatch):
    _auth(monkeypatch)
    _configure_stripe(monkeypatch)

    with client.application.app_context():
        entry = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()
        entry.stripe_customer_id = "cus_existing"
        db.session.commit()

    class FakeInvoice:
        @staticmethod
        def list(**kwargs):
            assert kwargs == {"customer": "cus_existing", "status": "open", "limit": 10}
            return {
                "data": [
                    {
                        "id": "in_open",
                        "status": "open",
                        "hosted_invoice_url": "https://invoice.stripe.com/pay/open",
                    }
                ]
            }

    fake_stripe = type(
        "FakeStripe",
        (),
        {"Invoice": FakeInvoice},
    )
    monkeypatch.setattr("app.billing._stripe", lambda: fake_stripe)

    response = client.post(
        "/api/billing/payment-method",
        headers=_auth_header(user["clerk_user_id"]),
        json={"return_path": "/profile"},
    )

    assert response.status_code == 200
    assert response.get_json()["url"] == "https://invoice.stripe.com/pay/open"


def test_payment_recovery_falls_back_to_payment_method_portal_flow(client, user, monkeypatch):
    _auth(monkeypatch)
    _configure_stripe(monkeypatch)
    portal_sessions = []

    with client.application.app_context():
        entry = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()
        entry.stripe_customer_id = "cus_existing"
        db.session.commit()

    class FakeInvoice:
        @staticmethod
        def list(**kwargs):
            return {"data": []}

    class FakePortalSession:
        @staticmethod
        def create(**kwargs):
            portal_sessions.append(kwargs)
            return {"url": "https://billing.stripe.com/payment-method"}

    fake_stripe = type(
        "FakeStripe",
        (),
        {
            "Invoice": FakeInvoice,
            "billing_portal": type("BillingPortal", (), {"Session": FakePortalSession}),
        },
    )
    monkeypatch.setattr("app.billing._stripe", lambda: fake_stripe)

    response = client.post(
        "/api/billing/payment-method",
        headers=_auth_header(user["clerk_user_id"]),
        json={"return_path": "/profile"},
    )

    assert response.status_code == 200
    assert response.get_json()["url"] == "https://billing.stripe.com/payment-method"
    assert portal_sessions == [
        {
            "customer": "cus_existing",
            "return_url": "http://localhost:3001/profile",
            "flow_data": {
                "type": "payment_method_update",
                "after_completion": {
                    "type": "redirect",
                    "redirect": {"return_url": "http://localhost:3001/profile"},
                },
            },
        }
    ]


def test_billing_required_response_includes_payment_recovery(client, user):
    from app.billing import billing_required_response

    with client.application.app_context():
        entry = User.query.filter_by(clerk_user_id=user["clerk_user_id"]).one()
        entry.stripe_customer_id = "cus_existing"
        entry.stripe_subscription_id = "sub_existing"
        entry.subscription_tier = "pro"
        entry.subscription_status = "unpaid"
        db.session.commit()

        response, status = billing_required_response(entry)
        body = response.get_json()

    assert status == 402
    assert body["code"] == "billing_payment_required"
    assert body["billing_health"]["action"] == "update_payment_method"
    assert body["subscription"]["billing_health"]["state"] == "payment_required"
    assert "Pay the invoice" in body["error"]


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


def test_stripe_webhook_rejects_missing_event_id_or_type(client, monkeypatch):
    _configure_stripe(monkeypatch)
    monkeypatch.setattr("app.api.webhooks.stripe.Webhook.construct_event", lambda *args: {"id": "evt_missing"})

    response = client.post("/api/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "ok"})

    assert response.status_code == 400
    assert "missing event id or type" in response.get_json()["error"]


def test_stripe_webhook_refetches_subscription_and_deduplicates(client, user, monkeypatch):
    _configure_stripe(monkeypatch)
    event = {
        "id": "evt_123",
        "type": "customer.subscription.updated",
        "data": {
            "object": _subscription(
                id="sub_123",
                customer="cus_123",
                metadata={"user_id": str(user["id"])},
                items={"data": [{"price": {"id": "price_basic"}}]},
            )
        },
    }
    retrieve_calls = []

    def retrieve_subscription(subscription_id, **kwargs):
        retrieve_calls.append((subscription_id, kwargs))
        return _subscription(
            id=subscription_id,
            customer="cus_123",
            metadata={"user_id": str(user["id"])},
            items={"data": [{"price": {"id": "price_pro"}}]},
        )

    monkeypatch.setattr("app.api.webhooks.stripe.Webhook.construct_event", lambda *args: event)
    monkeypatch.setattr("app.api.webhooks.stripe.Subscription.retrieve", retrieve_subscription)

    first = client.post("/api/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "ok"})
    duplicate = client.post("/api/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "ok"})

    assert first.status_code == 200
    assert duplicate.status_code == 200
    assert duplicate.get_json()["status"] == "duplicate"
    assert retrieve_calls == [("sub_123", {"expand": ["items.data.price"]})]
    with client.application.app_context():
        stored = StripeEvent.query.filter_by(stripe_event_id="evt_123").one()
        updated = User.query.get(user["id"])
        assert stored.processed_at is not None
        assert updated.subscription_tier == "pro"


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
        assert basic.subscription_current_period_start is not None

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
        assert deleted.usage_cycle_anchor_at is not None


def test_checkout_completed_webhook_refetches_session_and_subscription(client, user, monkeypatch):
    _configure_stripe(monkeypatch)
    event = {
        "id": "evt_checkout",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_123",
                "customer": "cus_stale",
                "client_reference_id": "999999",
                "subscription": _subscription(
                    id="sub_stale",
                    customer="cus_stale",
                    items={"data": [{"price": {"id": "price_basic"}}]},
                ),
            }
        },
    }
    session_calls = []
    subscription_calls = []

    def retrieve_session(session_id, **kwargs):
        session_calls.append((session_id, kwargs))
        return {
            "id": session_id,
            "customer": "cus_checkout",
            "client_reference_id": str(user["id"]),
            "subscription": "sub_checkout",
            "metadata": {"user_id": str(user["id"])},
        }

    def retrieve_subscription(subscription_id, **kwargs):
        subscription_calls.append((subscription_id, kwargs))
        return _subscription(
            id=subscription_id,
            customer="cus_checkout",
            metadata={"user_id": str(user["id"])},
            items={"data": [{"price": {"id": "price_pro"}}]},
        )

    monkeypatch.setattr("app.api.webhooks.stripe.Webhook.construct_event", lambda *args: event)
    monkeypatch.setattr("app.api.webhooks.stripe.checkout.Session.retrieve", retrieve_session)
    monkeypatch.setattr("app.api.webhooks.stripe.Subscription.retrieve", retrieve_subscription)

    response = client.post("/api/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "ok"})

    assert response.status_code == 200
    assert session_calls == [("cs_123", {"expand": ["subscription"]})]
    assert subscription_calls == [("sub_checkout", {"expand": ["items.data.price"]})]
    with client.application.app_context():
        updated = User.query.get(user["id"])
        assert updated.stripe_customer_id == "cus_checkout"
        assert updated.subscription_tier == "pro"


def test_invoice_paid_webhook_refetches_invoice_and_subscription(client, user, monkeypatch):
    _configure_stripe(monkeypatch)
    event = {
        "id": "evt_invoice_paid",
        "type": "invoice.paid",
        "data": {"object": {"id": "in_123", "subscription": "sub_stale"}},
    }
    invoice_calls = []
    subscription_calls = []

    def retrieve_invoice(invoice_id, **kwargs):
        invoice_calls.append((invoice_id, kwargs))
        return {"id": invoice_id, "subscription": "sub_current"}

    def retrieve_subscription(subscription_id, **kwargs):
        subscription_calls.append((subscription_id, kwargs))
        return _subscription(
            id=subscription_id,
            customer="cus_invoice",
            metadata={"user_id": str(user["id"])},
            items={"data": [{"price": {"id": "price_basic"}}]},
        )

    monkeypatch.setattr("app.api.webhooks.stripe.Webhook.construct_event", lambda *args: event)
    monkeypatch.setattr("app.api.webhooks.stripe.Invoice.retrieve", retrieve_invoice)
    monkeypatch.setattr("app.api.webhooks.stripe.Subscription.retrieve", retrieve_subscription)

    response = client.post("/api/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "ok"})

    assert response.status_code == 200
    assert invoice_calls == [("in_123", {"expand": ["subscription"]})]
    assert subscription_calls == [("sub_current", {"expand": ["items.data.price"]})]
    with client.application.app_context():
        updated = User.query.get(user["id"])
        assert updated.stripe_customer_id == "cus_invoice"
        assert updated.stripe_subscription_id == "sub_current"
        assert updated.subscription_tier == "basic"
        assert updated.subscription_current_period_start is not None


def test_invoice_payment_action_required_refetches_invoice_and_subscription(client, user, monkeypatch):
    _configure_stripe(monkeypatch)
    event = {
        "id": "evt_invoice_action",
        "type": "invoice.payment_action_required",
        "data": {"object": {"id": "in_action", "subscription": "sub_stale"}},
    }
    invoice_calls = []
    subscription_calls = []

    def retrieve_invoice(invoice_id, **kwargs):
        invoice_calls.append((invoice_id, kwargs))
        return {"id": invoice_id, "subscription": "sub_current_action"}

    def retrieve_subscription(subscription_id, **kwargs):
        subscription_calls.append((subscription_id, kwargs))
        return _subscription(
            id=subscription_id,
            customer="cus_action",
            status="past_due",
            metadata={"user_id": str(user["id"])},
            items={"data": [{"price": {"id": "price_pro"}}]},
        )

    monkeypatch.setattr("app.api.webhooks.stripe.Webhook.construct_event", lambda *args: event)
    monkeypatch.setattr("app.api.webhooks.stripe.Invoice.retrieve", retrieve_invoice)
    monkeypatch.setattr("app.api.webhooks.stripe.Subscription.retrieve", retrieve_subscription)

    response = client.post("/api/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "ok"})

    assert response.status_code == 200
    assert invoice_calls == [("in_action", {"expand": ["subscription"]})]
    assert subscription_calls == [("sub_current_action", {"expand": ["items.data.price"]})]
    with client.application.app_context():
        updated = User.query.get(user["id"])
        assert updated.stripe_customer_id == "cus_action"
        assert updated.stripe_subscription_id == "sub_current_action"
        assert updated.subscription_tier == "pro"
        assert updated.subscription_status == "past_due"


def test_invoice_updated_webhook_refetches_invoice_and_subscription(client, user, monkeypatch):
    _configure_stripe(monkeypatch)
    event = {
        "id": "evt_invoice_updated",
        "type": "invoice.updated",
        "data": {"object": {"id": "in_updated", "subscription": "sub_stale"}},
    }
    invoice_calls = []
    subscription_calls = []

    def retrieve_invoice(invoice_id, **kwargs):
        invoice_calls.append((invoice_id, kwargs))
        return {"id": invoice_id, "subscription": "sub_current_updated"}

    def retrieve_subscription(subscription_id, **kwargs):
        subscription_calls.append((subscription_id, kwargs))
        return _subscription(
            id=subscription_id,
            customer="cus_updated",
            status="active",
            metadata={"user_id": str(user["id"])},
            items={"data": [{"price": {"id": "price_basic"}}]},
        )

    monkeypatch.setattr("app.api.webhooks.stripe.Webhook.construct_event", lambda *args: event)
    monkeypatch.setattr("app.api.webhooks.stripe.Invoice.retrieve", retrieve_invoice)
    monkeypatch.setattr("app.api.webhooks.stripe.Subscription.retrieve", retrieve_subscription)

    response = client.post("/api/webhooks/stripe", data=b"{}", headers={"Stripe-Signature": "ok"})

    assert response.status_code == 200
    assert invoice_calls == [("in_updated", {"expand": ["subscription"]})]
    assert subscription_calls == [("sub_current_updated", {"expand": ["items.data.price"]})]
    with client.application.app_context():
        updated = User.query.get(user["id"])
        assert updated.stripe_customer_id == "cus_updated"
        assert updated.stripe_subscription_id == "sub_current_updated"
        assert updated.subscription_status == "active"


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
                        id="sub_stale",
                        customer="cus_object",
                        items={"data": [{"price": {"id": "price_basic"}}]},
                    ),
                    "metadata": {"user_id": str(user["id"])},
                }
            },
        }
    )

    def retrieve_session(session_id, **kwargs):
        assert session_id == "cs_object"
        assert kwargs == {"expand": ["subscription"]}
        return _stripe_like(
            {
                "id": "cs_object",
                "customer": "cus_object",
                "client_reference_id": str(user["id"]),
                "subscription": {"id": "sub_object"},
                "metadata": {"user_id": str(user["id"])},
            }
        )

    def retrieve_subscription(subscription_id, **kwargs):
        assert subscription_id == "sub_object"
        assert kwargs == {"expand": ["items.data.price"]}
        return _stripe_like(
            _subscription(
                id=subscription_id,
                customer="cus_object",
                metadata={"user_id": str(user["id"])},
                items={"data": [{"price": {"id": "price_pro"}}]},
            )
        )

    monkeypatch.setattr("app.api.webhooks.stripe.Webhook.construct_event", lambda *args: event)
    monkeypatch.setattr("app.api.webhooks.stripe.checkout.Session.retrieve", retrieve_session)
    monkeypatch.setattr("app.api.webhooks.stripe.Subscription.retrieve", retrieve_subscription)

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


def test_free_user_gets_cycle_limited_prediction_and_markets(client, user, monkeypatch):
    _auth(monkeypatch)

    class FakeResult:
        home_win_prob = 0.5
        draw_prob = 0.2
        away_win_prob = 0.3
        most_likely_score = "1-0"

        def to_dict(self):
            return {"home_team": "France", "away_team": "Argentina", "agent_predictions": []}

    class FakeOrchestrator:
        def predict_match(self, *args, **kwargs):
            return FakeResult()

    class FakeQuestion:
        prop_type = "match_winner"

        def to_dict(self):
            return {"question": "France to win?"}

    monkeypatch.setattr("app.api.predictions._get_orchestrator", lambda include_video_analysis=True: FakeOrchestrator())
    monkeypatch.setattr("app.api.markets._get_orc", lambda include_video_analysis=True: FakeOrchestrator())
    monkeypatch.setattr("app.api.markets._gen.from_match", lambda pred: [FakeQuestion()])

    first_prediction = client.post(
        "/api/predictions/match",
        headers=_auth_header(user["clerk_user_id"]),
        json={"home_team": "France", "away_team": "Argentina"},
    )
    second_prediction = client.post(
        "/api/predictions/match",
        headers=_auth_header(user["clerk_user_id"]),
        json={"home_team": "France", "away_team": "Argentina"},
    )
    markets = [
        client.post(
            "/api/markets/match",
            headers=_auth_header(user["clerk_user_id"]),
            json={"home_team": "France", "away_team": "Argentina"},
        )
        for _ in range(4)
    ]

    assert first_prediction.status_code == 200
    assert second_prediction.status_code == 402
    assert second_prediction.get_json()["code"] == "feature_limit_reached"
    assert [response.status_code for response in markets] == [200, 200, 200, 402]


def test_failed_prediction_releases_free_usage(client, user, monkeypatch):
    _auth(monkeypatch)

    class FailingOrchestrator:
        def predict_match(self, *args, **kwargs):
            raise RuntimeError("boom")

    class PassingResult:
        def to_dict(self):
            return {"home_team": "France", "away_team": "Argentina", "agent_predictions": []}

    class PassingOrchestrator:
        def predict_match(self, *args, **kwargs):
            return PassingResult()

    monkeypatch.setattr("app.api.predictions._get_orchestrator", lambda include_video_analysis=True: FailingOrchestrator())
    failed = client.post(
        "/api/predictions/match",
        headers=_auth_header(user["clerk_user_id"]),
        json={"home_team": "France", "away_team": "Argentina"},
    )
    monkeypatch.setattr("app.api.predictions._get_orchestrator", lambda include_video_analysis=True: PassingOrchestrator())
    retry = client.post(
        "/api/predictions/match",
        headers=_auth_header(user["clerk_user_id"]),
        json={"home_team": "France", "away_team": "Argentina"},
    )
    exhausted = client.post(
        "/api/predictions/match",
        headers=_auth_header(user["clerk_user_id"]),
        json={"home_team": "France", "away_team": "Argentina"},
    )

    assert failed.status_code == 500
    assert retry.status_code == 200
    assert exhausted.status_code == 402


def test_free_user_gets_cycle_limited_tournament_features(client, user, monkeypatch):
    _auth(monkeypatch)

    class FakeTournamentResult:
        simulation_id = "sim_123"
        champion = "France"
        runner_up = "Argentina"
        third_place = "Brazil"
        champion_probability = 0.22

        def to_dict(self):
            return {
                "simulation_id": self.simulation_id,
                "champion": self.champion,
                "runner_up": self.runner_up,
                "third_place": self.third_place,
                "champion_probability": self.champion_probability,
            }

    class FakeSimulator:
        def __init__(self, *args, **kwargs):
            pass

        def simulate(self):
            return FakeTournamentResult()

    class FakeQuestion:
        prop_type = "tournament_winner"

        def to_dict(self):
            return {"question": "Champion?"}

    monkeypatch.setattr("app.api.predictions.TournamentSimulator", FakeSimulator)
    monkeypatch.setattr("app.api.markets.TournamentSimulator", FakeSimulator)
    monkeypatch.setattr("app.api.markets._gen.from_tournament", lambda result: [FakeQuestion()])

    first_sim = client.post("/api/predictions/tournament", headers=_auth_header(user["clerk_user_id"]), json={})
    second_sim = client.post("/api/predictions/tournament", headers=_auth_header(user["clerk_user_id"]), json={})
    markets = [
        client.post(
        "/api/markets/match",
        headers=_auth_header(user["clerk_user_id"]),
            json={"home_team": "France", "away_team": "Argentina"},
        )
        for _ in range(0)
    ]
    tournament_markets = [client.post("/api/markets/tournament", headers=_auth_header(user["clerk_user_id"]), json={}) for _ in range(4)]

    assert markets == []
    assert first_sim.status_code == 200
    assert second_sim.status_code == 402
    assert [response.status_code for response in tournament_markets] == [200, 200, 200, 402]


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
