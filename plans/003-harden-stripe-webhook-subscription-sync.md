# Plan 003: Harden Stripe webhook subscription sync

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report; do not improvise. When done, update the status row for this plan in
> `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat c6a14a9..HEAD -- backend/app/api/webhooks.py backend/app/billing.py backend/app/db/models.py backend/tests/test_billing.py backend/migrations/versions/20260619_0004_stripe_subscriptions.py plans/003-harden-stripe-webhook-subscription-sync.md`
>
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding. If the
> webhook event routing, Stripe event model, or billing tests no longer match,
> treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: `plans/001-implement-stripe-subscriptions.md`, `plans/002-implement-cycle-based-feature-usage-limits.md`
- **Category**: bug
- **Planned at**: commit `c6a14a9`, 2026-06-25

## Why this matters

Stripe does not guarantee that webhook events arrive in business-order, and
the embedded event object can be older than the current Stripe resource state.
The app currently trusts subscription and checkout payloads in several webhook
paths, so an older delivery can overwrite a newer subscription tier, period,
or cancellation state. This plan makes the webhook use the event only as a
pointer to the changed resource, then fetches the latest Checkout Session,
Invoice, or Subscription from Stripe before syncing local entitlement state.

The plan also adds `invoice.paid` handling and locks down event deduplication.
Do not expand this into a broader subscription lifecycle rewrite; the user
explicitly asked to handle invoice paid and leave the rest.

## Current state

Relevant files:

- `backend/app/api/webhooks.py` - Clerk and Stripe webhook endpoints.
- `backend/app/billing.py` - Stripe helpers and subscription sync logic.
- `backend/app/db/models.py` - contains the `StripeEvent` dedupe table.
- `backend/tests/test_billing.py` - existing billing and webhook tests.
- `backend/migrations/versions/20260619_0004_stripe_subscriptions.py` - migration that created `stripe_events`.

The Stripe webhook verifies the signature, inserts a `StripeEvent`, flushes to
detect duplicates, then processes the event. This is the right dedupe shape and
must be preserved, but the event id/type access should support StripeObject-like
events too:

```python
# backend/app/api/webhooks.py:49-74
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
```

The webhook currently routes subscription events by passing the payload object
directly into `sync_subscription_from_stripe_subscription`. That is the main
behavior to change:

```python
# backend/app/api/webhooks.py:77-95
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
```

Checkout handling also accepts an expanded subscription from the webhook
payload. After this plan, checkout processing should fetch the current session
by id and then fetch the current subscription if needed:

```python
# backend/app/api/webhooks.py:97-116
def _handle_checkout_completed(session: dict) -> None:
    customer_id = _get_value(session, "customer")
    user = None
    client_reference_id = _get_value(session, "client_reference_id")
    if client_reference_id:
        user = User.query.get(client_reference_id)
    metadata = _metadata_dict(_get_value(session, "metadata"))
    ...
    subscription = _get_value(session, "subscription")
    if isinstance(subscription, str):
        subscription = stripe.Subscription.retrieve(subscription, expand=["items.data.price"])
    if subscription:
        sync_subscription_from_stripe_subscription(subscription, db)
```

Subscription sync is centralized and should continue to be the only place that
maps Stripe subscription data onto local user fields:

```python
# backend/app/billing.py:325-363
def sync_subscription_from_stripe_subscription(subscription: dict[str, Any], db_session) -> User | None:
    metadata = _metadata_dict(_get_value(subscription, "metadata"))
    customer_id = _get_value(subscription, "customer")
    subscription_id = _get_value(subscription, "id")
    ...
    user.subscription_status = "canceled" if deleted else status
    user.subscription_current_period_start = _ts(_get_value(subscription, "current_period_start"))
    user.subscription_current_period_end = _ts(_get_value(subscription, "current_period_end"))
    user.subscription_cancel_at_period_end = False if deleted else bool(_get_value(subscription, "cancel_at_period_end"))
    user.subscription_synced_at = utcnow()
    user.stripe_price_id = price_id
    user.subscription_tier = "free" if deleted else tier_for_price_id(price_id)
```

The database already has the dedupe primitive. Do not add a second dedupe table
or a migration unless this table is missing in the live branch:

```python
# backend/app/db/models.py:49-55
class StripeEvent(db.Model, TimestampMixin):
    __tablename__ = "stripe_events"

    id = db.Column(db.Integer, primary_key=True)
    stripe_event_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    event_type = db.Column(db.String(255), nullable=False)
    processed_at = db.Column(db.DateTime(timezone=True), nullable=True)
```

The migration backs that model with a unique index:

```python
# backend/migrations/versions/20260619_0004_stripe_subscriptions.py:40-50
op.create_table(
    "stripe_events",
    sa.Column("id", sa.Integer(), nullable=False),
    sa.Column("stripe_event_id", sa.String(length=255), nullable=False),
    sa.Column("event_type", sa.String(length=255), nullable=False),
    sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    ...
)
op.create_index(op.f("ix_stripe_events_stripe_event_id"), "stripe_events", ["stripe_event_id"], unique=True)
```

Existing tests already cover invalid signatures, duplicate event rows, checkout
sync, and StripeObject-like event payloads. They currently assume payload data
is enough and must be updated:

```python
# backend/tests/test_billing.py:287-306
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
```

```python
# backend/tests/test_billing.py:340-364
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
```

Repo conventions to match:

- Keep webhook resource routing in `backend/app/api/webhooks.py`.
- Keep user subscription field mapping in `backend/app/billing.py`.
- Use `_get_value(...)` and `_metadata_dict(...)` for dict and StripeObject
  compatibility instead of direct attribute-only or key-only access.
- Tests monkeypatch Stripe SDK calls directly in `backend/tests/test_billing.py`;
  follow that style rather than introducing a new test fixture framework.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Focused backend tests | `cd backend && venv/bin/python -m pytest tests/test_billing.py` | exit 0, all tests pass |
| Full backend tests | `cd backend && venv/bin/python -m pytest` | exit 0, all tests pass |
| Whitespace/check diff | `git diff --check` | exit 0, no whitespace errors |

If `venv/bin/python` does not exist, use the repo's active Python interpreter
with the same module form: `python -m pytest ...`. Do not install dependencies
as part of this plan unless the operator explicitly permits it.

## Scope

**In scope**:

- `backend/app/api/webhooks.py`
- `backend/app/billing.py` only if a small shared Stripe retrieval helper belongs there
- `backend/tests/test_billing.py`
- `plans/README.md` status row update after implementation

**Out of scope**:

- Frontend billing or pricing UI.
- New database migrations; the current `stripe_events` unique index is enough
  for event dedupe.
- New Stripe event families beyond `invoice.paid` and the already handled
  checkout, subscription, `invoice.payment_succeeded`, and
  `invoice.payment_failed` paths.
- Free tier Stripe subscriptions.
- Changing feature usage limit behavior.
- Reworking Clerk webhooks.

## Git workflow

- Stay on the current branch unless the operator tells you otherwise.
- Do not push or open a PR unless explicitly asked.
- Do not revert unrelated modified files in the working tree.

## Steps

### Step 1: Strengthen event id/type extraction and preserve dedupe

In `backend/app/api/webhooks.py`, update `stripe_webhook()` to read the event id
and event type via `_get_value(event, "id")` and `_get_value(event, "type")`
instead of `event["id"]` and `event["type"]`. Return a 400 if either value is
missing after signature verification.

Keep the existing dedupe order:

1. create `StripeEvent(stripe_event_id=event_id, event_type=event_type)`;
2. `db.session.flush()`;
3. on `IntegrityError`, `rollback()` and return `{"status": "duplicate"}` with
   HTTP 200;
4. only set `processed_at` after `_process_stripe_event(event)` succeeds;
5. on any processing exception, roll back and let Flask return an error so
   Stripe retries the event.

Do not commit the `StripeEvent` row before processing succeeds. The current
rollback-on-exception behavior is intentional because a transient Stripe API
failure should not permanently dedupe an unprocessed event.

**Verify**: `cd backend && venv/bin/python -m pytest tests/test_billing.py -k "invalid_signature or duplicates or object_events"` -> selected tests pass.

### Step 2: Add latest-resource retrieval helpers

In `backend/app/api/webhooks.py`, add small private helpers near
`_process_stripe_event`:

- `_retrieve_subscription(subscription_id: str)` returns
  `stripe.Subscription.retrieve(subscription_id, expand=["items.data.price"])`.
- `_retrieve_checkout_session(session_id: str)` returns
  `stripe.checkout.Session.retrieve(session_id, expand=["subscription"])`.
- `_retrieve_invoice(invoice_id: str)` returns
  `stripe.Invoice.retrieve(invoice_id, expand=["subscription"])`.
- `_sync_subscription_reference(subscription_ref)` accepts either a subscription
  id string or an expanded subscription object. If it is a string, retrieve the
  subscription first. If it is an object, use `_get_value(subscription_ref, "id")`
  to fetch the latest subscription by id before syncing. Then call
  `sync_subscription_from_stripe_subscription(fetched_subscription, db)`.

Important: even when Stripe gives an expanded subscription object in a fetched
checkout session or invoice, fetch the subscription by id before syncing. This
keeps the rule simple: local subscription state is synced from the latest
Subscription API response, not from webhook payloads or nested resource
snapshots.

If the Stripe Python SDK in this project does not support the `stripe.checkout`
namespace in tests or runtime, STOP and report the SDK/API mismatch instead of
rewriting checkout handling around a guessed API.

**Verify**: `cd backend && venv/bin/python -m pytest tests/test_billing.py -k "checkout"` -> checkout tests pass after they are updated in later steps.

### Step 3: Refetch resources for every handled webhook path

Update `_process_stripe_event(event)` in `backend/app/api/webhooks.py` so the
event payload is used only to identify which Stripe resource to fetch.

Target routing:

```python
if event_type == "checkout.session.completed":
    session_id = _get_value(obj, "id")
    if session_id:
        _handle_checkout_completed(_retrieve_checkout_session(session_id))
elif event_type in {
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
}:
    subscription_id = _get_value(obj, "id")
    if subscription_id:
        _sync_subscription_reference(subscription_id)
elif event_type in {"invoice.paid", "invoice.payment_succeeded", "invoice.payment_failed"}:
    invoice_id = _get_value(obj, "id")
    if invoice_id:
        invoice = _retrieve_invoice(invoice_id)
        _sync_subscription_reference(_get_value(invoice, "subscription"))
```

If a handled event lacks the relevant resource id, return without changing
local subscription fields. Keep this behavior quiet and idempotent; malformed
Stripe events should be rare and the signature-verified event has already been
recorded.

Do not add fallback sync from the event payload if a Stripe retrieve call fails.
Let the exception roll back the database transaction so Stripe retries. For
`customer.subscription.deleted`, assume Stripe can still retrieve the
subscription as canceled. If manual testing proves deleted subscriptions cannot
be retrieved in this Stripe API version, STOP and report that finding; do not
silently rely on the deleted event payload.

**Verify**: `cd backend && venv/bin/python -m pytest tests/test_billing.py -k "stripe_webhook"` -> selected tests pass after the test updates below.

### Step 4: Keep checkout user linking, but use fetched data

Update `_handle_checkout_completed(session)` so it expects a fetched Checkout
Session, not the raw webhook session object. Keep the current user-linking
order:

1. `client_reference_id`;
2. `metadata["user_id"]`;
3. `metadata["clerk_user_id"]`.

Continue setting `user.stripe_customer_id` when the user is found and the local
customer id is missing. For the session subscription, call
`_sync_subscription_reference(_get_value(session, "subscription"))` instead of
syncing an expanded object directly.

Do not move user-linking logic into `billing.py`; this is webhook-specific
glue.

**Verify**: `cd backend && venv/bin/python -m pytest tests/test_billing.py -k "checkout_completed"` -> selected checkout webhook tests pass.

### Step 5: Update tests to prove stale payloads cannot win

In `backend/tests/test_billing.py`, update existing Stripe webhook tests and add
new focused cases. Reuse `_configure_stripe`, `_subscription`, `_stripe_like`,
and Flask client patterns already in the file.

Required test coverage:

1. `customer.subscription.updated` event contains a stale payload price, while
   mocked `stripe.Subscription.retrieve` returns a different current price.
   Assert the user tier matches the retrieved subscription, not the payload.
2. Duplicate event posts return `{"status": "duplicate"}` and do not call
   `stripe.Subscription.retrieve` a second time. A simple list counter or
   integer closure is enough.
3. `checkout.session.completed` event payload contains only `id` or stale
   nested subscription data. Mock `stripe.checkout.Session.retrieve` to return
   the current session, mock `stripe.Subscription.retrieve` to return the
   current subscription, and assert the user customer id/tier come from fetched
   resources.
4. `invoice.paid` fetches the invoice with `stripe.Invoice.retrieve`, then
   fetches/syncs the current subscription. Assert paid tier and period fields
   update.
5. Keep or update the StripeObject-like event test so event id/type extraction,
   checkout session retrieval, and metadata access all work with StripeObject
   style wrappers.

The old test named
`test_checkout_completed_webhook_syncs_expanded_subscription` should be renamed
or rewritten because syncing directly from an expanded webhook subscription is
no longer the expected behavior.

**Verify**: `cd backend && venv/bin/python -m pytest tests/test_billing.py` -> all tests in the file pass.

### Step 6: Run final verification and update the plan index

Run the full backend test suite and diff check:

```bash
cd backend && venv/bin/python -m pytest
git diff --check
```

Then update this plan's row in `plans/README.md` from `TODO` to `DONE` only if
all done criteria below are satisfied.

## Test plan

Model new tests after the existing webhook tests in
`backend/tests/test_billing.py`.

Add or update tests for:

- subscription webhook refetches latest subscription and ignores stale payload;
- event dedupe prevents a second Stripe API retrieval;
- checkout completion refetches latest session and subscription;
- `invoice.paid` fetches invoice and subscription before syncing;
- StripeObject-like event id/type access still works.

Verification:

- `cd backend && venv/bin/python -m pytest tests/test_billing.py` -> all pass.
- `cd backend && venv/bin/python -m pytest` -> all pass.
- `git diff --check` -> exit 0.

## Done criteria

All must hold:

- [ ] `stripe_webhook()` extracts event id/type with `_get_value(...)` and
      returns 400 for missing id/type.
- [ ] `StripeEvent` unique-row dedupe remains the only event dedupe mechanism.
- [ ] Duplicate Stripe events return HTTP 200 with `{"status": "duplicate"}` and
      do not make downstream Stripe retrieval calls.
- [ ] Subscription created/updated/deleted webhooks fetch the latest
      subscription from Stripe before local sync.
- [ ] Checkout completion fetches the latest Checkout Session and then the
      latest Subscription before local sync.
- [ ] `invoice.paid`, `invoice.payment_succeeded`, and `invoice.payment_failed`
      fetch the latest Invoice and latest Subscription before local sync.
- [ ] No handled webhook path syncs subscription fields directly from the raw
      webhook payload or a nested expanded object without refetching by id.
- [ ] `cd backend && venv/bin/python -m pytest tests/test_billing.py` exits 0.
- [ ] `cd backend && venv/bin/python -m pytest` exits 0.
- [ ] `git diff --check` exits 0.
- [ ] No files outside the in-scope list are modified, except
      `plans/README.md` status update.

## STOP conditions

Stop and report back if:

- The current webhook code no longer has the routing and dedupe shape shown in
  this plan.
- The live branch lacks the `stripe_events.stripe_event_id` unique constraint.
- Stripe deleted subscriptions cannot be retrieved by id in the Stripe API
  version used by this project.
- The Stripe SDK does not support the retrieval calls named in this plan.
- Passing tests requires broad changes outside `backend/app/api/webhooks.py`,
  `backend/app/billing.py`, or `backend/tests/test_billing.py`.
- A verification command fails twice after a reasonable fix attempt.

## Maintenance notes

Reviewers should scrutinize idempotency and rollback behavior. A processing
failure must not commit `processed_at`, because Stripe should retry events that
failed due to a transient API or database issue.

Future webhook additions should follow the same rule: use the webhook payload
to identify the resource, fetch the current Stripe resource, then sync local
state from the fetched object. Do not add raw payload sync paths for convenience
unless the event type is explicitly documented by Stripe as unretrievable and a
reviewer accepts the resulting ordering tradeoff.
