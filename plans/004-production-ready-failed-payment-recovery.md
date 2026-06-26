# Plan 004: Add production-ready failed-payment recovery

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report; do not improvise. When done, update the status row for this plan in
> `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat 28a5f55..HEAD -- backend/app/billing.py backend/app/api/billing.py backend/app/api/webhooks.py backend/tests/test_billing.py frontend/src/App.vue frontend/src/lib/billing.js frontend/src/views/ProfileView.vue frontend/src/views/ProfileView.test.js frontend/src/views/PredictView.vue frontend/src/views/TournamentView.vue frontend/src/views/MarketsView.vue frontend/src/components/BillingPlansLink.vue README.md plans/004-production-ready-failed-payment-recovery.md`
>
> Also run:
> `git diff --stat -- backend/app/billing.py backend/app/api/billing.py backend/app/api/webhooks.py backend/tests/test_billing.py frontend/src/App.vue frontend/src/lib/billing.js frontend/src/views/ProfileView.vue frontend/src/views/ProfileView.test.js frontend/src/views/PredictView.vue frontend/src/views/TournamentView.vue frontend/src/views/MarketsView.vue frontend/src/components/BillingPlansLink.vue README.md`
>
> This plan was written against the live working tree on 2026-06-26, with
> local billing changes present on top of commit `28a5f55`. If any excerpt in
> "Current state" does not match the live code, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: `plans/001-implement-stripe-subscriptions.md`, `plans/003-harden-stripe-webhook-subscription-sync.md`
- **Category**: bug
- **Planned at**: commit `28a5f55`, 2026-06-26

## Why this matters

Stripe payment failures currently sync into local subscription status, but the
app gives users only generic "Active subscription required" and "Pricing"
messaging. In production, failed payments need a clear recovery path: tell the
customer what happened, send them directly to Stripe's payment-method update
flow, and avoid pretending a billing issue is the same thing as choosing a new
plan. This plan adds backend billing-health semantics and frontend notices
without adding a new database table.

The policy for this first production-ready version is:

- `active` and `trialing` subscriptions remain healthy and entitled.
- `past_due` is recoverable. Show urgent notices and recovery CTAs; do not
  downgrade the tier label. Whether access is retained should follow the
  entitlement helper below.
- `incomplete`, `unpaid`, `canceled`, and `incomplete_expired` are blocked or
  inactive. Show recovery or plan-selection messaging and keep paid-only
  operations blocked.
- Stripe Customer Portal owns card collection and payment-method updates.
  The app should deep-link to `payment_method_update`; do not collect card
  details directly.

Stripe references used for this plan:

- Customer Portal session creation and `flow_data`: https://docs.stripe.com/api/customer_portal/sessions/create
- Subscription webhook behavior and customer notification guidance: https://docs.stripe.com/billing/subscriptions/webhooks

## Current state

Relevant files:

- `backend/app/billing.py` - Stripe helpers, subscription serialization, entitlement policy, portal session creation.
- `backend/app/api/billing.py` - billing API routes consumed by the frontend.
- `backend/app/api/webhooks.py` - Stripe webhook event routing and subscription sync.
- `backend/tests/test_billing.py` - backend billing and Stripe webhook tests.
- `frontend/src/lib/billing.js` - frontend billing API wrappers.
- `frontend/src/App.vue` - app shell; currently no billing-health banner.
- `frontend/src/views/ProfileView.vue` - profile and billing section; currently shows tier and manage/plans button.
- `frontend/src/views/ProfileView.test.js` - profile billing tests.
- `frontend/src/views/PredictView.vue`, `frontend/src/views/TournamentView.vue`, `frontend/src/views/MarketsView.vue` - paid/limited feature pages.
- `frontend/src/components/BillingPlansLink.vue` - small pricing CTA used in feature error boxes.
- `README.md` - Stripe setup docs.

Backend subscription serialization currently exposes raw status and entitlement
booleans, but no user-facing health/recovery metadata:

```python
# backend/app/billing.py:100-119
def serialize_subscription(user: User) -> dict[str, Any]:
    tier = user.subscription_tier or "free"
    return {
        "tier": tier,
        "status": user.subscription_status,
        "is_paid_entitled": is_paid_entitled(user),
        "includes_video_analysis": includes_video_analysis(user),
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
```

Paid entitlement currently accepts only `active` and `trialing`:

```python
# backend/app/billing.py:17-21,122-131
PAID_STATUSES = {"active", "trialing"}
PAID_TIERS = {"basic", "pro"}
CHECKOUT_PAYMENT_METHOD_TYPES = ["card", "cashapp"]
CHECKOUT_CURRENCY = "usd"
MANAGED_SUBSCRIPTION_STATUSES = {"active", "trialing", "past_due", "unpaid", "incomplete", "paused"}

def is_paid_entitled(user: User) -> bool:
    if user.is_admin:
        return True
    return (user.subscription_tier in PAID_TIERS) and (user.subscription_status in PAID_STATUSES)

def includes_video_analysis(user: User) -> bool:
    if user.is_admin:
        return True
    return user.subscription_tier == "pro" and user.subscription_status in PAID_STATUSES
```

Billing-required responses currently do not tell the frontend whether the
problem is a failed payment, a free-tier limit, or an inactive subscription:

```python
# backend/app/billing.py:134-143
def billing_required_response(user: User):
    if is_paid_entitled(user):
        return None
    return jsonify(
        {
            "error": "Active subscription required",
            "code": "subscription_required",
            "plans_url": "/pricing",
        }
    ), 402
```

Portal sessions already have an internal helper that can send `flow_data`, but
only `create_portal_session()` is exposed through the API:

```python
# backend/app/billing.py:258-273,411-413
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

def create_portal_session(user: User, return_path: str = "/profile") -> str:
    ensure_stripe_configured(require_prices=False)
    return _portal_session_url(user, return_path)
```

Stripe webhook routing handles `invoice.payment_failed` by refetching the
invoice, then refetching the subscription:

```python
# backend/app/api/webhooks.py:82-103
def _process_stripe_event(event: dict) -> None:
    event_type = _get_value(event, "type")
    data = _get_value(event, "data") or {}
    obj = _get_value(data, "object") or {}

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

Subscription sync writes the raw Stripe subscription status into `users`:

```python
# backend/app/billing.py:488-502
status = _get_value(subscription, "status")
price_id = _subscription_item_price_id(subscription)
deleted = status == "canceled" or (
    _get_value(subscription, "object") == "subscription" and _get_value(subscription, "deleted") is True
)

user.stripe_customer_id = customer_id or user.stripe_customer_id
user.stripe_subscription_id = subscription_id or user.stripe_subscription_id
user.subscription_status = "canceled" if deleted else status
user.subscription_current_period_start = _ts(_get_value(subscription, "current_period_start"))
user.subscription_current_period_end = _ts(_get_value(subscription, "current_period_end"))
user.subscription_cancel_at_period_end = False if deleted else bool(_get_value(subscription, "cancel_at_period_end"))
user.subscription_synced_at = utcnow()
user.stripe_price_id = price_id
user.subscription_tier = "free" if deleted else tier_for_price_id(price_id)
```

Profile shows a billing section but no payment-failure notice:

```vue
<!-- frontend/src/views/ProfileView.vue:96-127 -->
<section class="profile-card billing-card">
  <div class="billing-row">
    <div>
      <h2>Billing</h2>
      <p class="billing-tier">
        <span>Current tier</span>
        <LoaderCircle v-if="billingLoading" :size="18" class="spin billing-loader" aria-label="Loading billing tier" />
        <strong v-else>{{ tierLabel }}</strong>
      </p>
    </div>
    <button
      class="btn-primary billing-action"
      :disabled="billingLoading || portalLoading"
      :aria-label="portalLoading ? 'Opening billing' : billingActionLabel"
      :title="portalLoading ? 'Opening billing' : billingActionLabel"
      @click="openBillingPortal"
    >
      <LoaderCircle v-if="portalLoading" :size="18" class="spin" aria-hidden="true" />
      <template v-else>
        <span>{{ billingActionText }}</span>
        <CreditCard :size="18" aria-hidden="true" />
      </template>
    </button>
  </div>
  <div v-if="usage.features?.length" class="usage-grid">
    <div v-for="feature in usage.features" :key="feature.feature_key" class="usage-row">
      <span>{{ feature.label }}</span>
      <strong>{{ usageText(feature) }}</strong>
    </div>
  </div>
  <p v-if="billingError" class="error-box">{{ billingError }}</p>
</section>
```

Feature pages currently treat every subscription/limit error as a generic
pricing prompt:

```vue
<!-- frontend/src/views/PredictView.vue:46-50 -->
<div v-if="error" class="error-box">
  {{ error }}
  <BillingPlansLink v-if="subscriptionRequired" />
</div>
```

```js
// frontend/src/views/PredictView.vue:181-183
} catch (e) {
  error.value = e.response?.data?.error || e.message
  subscriptionRequired.value = ['subscription_required', 'feature_limit_reached'].includes(e.response?.data?.code)
}
```

The same error-code pattern exists in `TournamentView.vue` and
`MarketsView.vue`.

The app shell has no billing status call or banner:

```vue
<!-- frontend/src/App.vue:47-49 -->
<main class="content">
  <router-view />
</main>
```

Frontend billing API wrappers currently expose generic portal sessions only:

```js
// frontend/src/lib/billing.js:1-13
import { api } from './api'

export const getPlans = () => api.get('/api/billing/plans')
export const createCheckout = (tier) => api.post('/api/billing/checkout', { tier })
export const changePlan = (tier) => api.post('/api/billing/change-plan', { tier })
export const getSubscription = () => api.get('/api/billing/subscription')
export const getUsage = () => api.get('/api/billing/usage')
export const createPortalSession = (payload = {}) => api.post('/api/billing/portal', payload)
```

Repo conventions to match:

- Backend helpers live in `backend/app/billing.py`; API routes stay thin in
  `backend/app/api/billing.py`.
- Stripe object access must use `_get_value(...)` and `_metadata_dict(...)`
  for dict and StripeObject compatibility.
- Backend tests monkeypatch Stripe SDK methods directly in
  `backend/tests/test_billing.py`.
- Vue views use Composition API with `ref`, `computed`, and direct API wrapper
  imports.
- Loading buttons use lucide `LoaderCircle`; normal buttons should have short
  text plus an icon.
- Existing frontend tests use Vitest and `@vue/test-utils` with module mocks.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Focused backend billing tests | `backend/venv/bin/python -m pytest backend/tests/test_billing.py` | exit 0, all tests pass |
| Full backend tests | `backend/venv/bin/python -m pytest backend/tests` | exit 0, all tests pass |
| Focused profile frontend test | `cd frontend && npm test -- ProfileView.test.js` | exit 0, all tests pass |
| Full frontend tests | `cd frontend && npm test` | exit 0, all tests pass |
| Frontend production build | `cd frontend && npm run build` | exit 0, Vite build completes |
| Whitespace/diff check | `git diff --check` | exit 0, no whitespace errors |

If `backend/venv/bin/python` does not exist, use the active backend Python
interpreter with the same module form. Do not install dependencies unless the
operator explicitly approves it.

## Scope

**In scope**:

- `backend/app/billing.py`
- `backend/app/api/billing.py`
- `backend/app/api/webhooks.py`
- `backend/tests/test_billing.py`
- `frontend/src/lib/billing.js`
- `frontend/src/App.vue`
- `frontend/src/components/BillingStatusNotice.vue` (create)
- `frontend/src/composables/useBillingStatus.js` (create if needed)
- `frontend/src/views/ProfileView.vue`
- `frontend/src/views/ProfileView.test.js`
- `frontend/src/views/PredictView.vue`
- `frontend/src/views/TournamentView.vue`
- `frontend/src/views/MarketsView.vue`
- `frontend/src/components/BillingPlansLink.vue` only if it remains the shared
  feature-page CTA; otherwise leave it and introduce `BillingStatusNotice`.
- `README.md`
- `plans/README.md` status update after implementation

**Out of scope**:

- Collecting payment details in the app. Use Stripe Portal only.
- Sending custom emails from this app. Use Stripe dunning/customer emails for
  this plan.
- Adding a new payment-failure database table. Existing subscription fields
  are sufficient for the first production-ready pass.
- Changing Stripe free-tier policy.
- Changing paid plan prices, plan cards, feature limits, or usage-cycle schema.
- Reworking Clerk sync or customer email creation behavior.

## Git workflow

- Stay on the current branch unless the operator says otherwise.
- Do not push or open a PR unless explicitly asked.
- Do not revert unrelated modified files in the working tree.
- Keep commits, if requested later, scoped to this failed-payment recovery
  slice.

## Steps

### Step 1: Define billing-health semantics in the backend

In `backend/app/billing.py`, add a small policy layer near the existing status
constants. The exact names can vary, but the serialized contract must be
stable:

```python
RECOVERABLE_BILLING_STATUSES = {"past_due"}
BLOCKED_BILLING_STATUSES = {"incomplete", "incomplete_expired", "unpaid", "canceled"}
PAYMENT_RECOVERY_STATUSES = RECOVERABLE_BILLING_STATUSES | {"incomplete", "unpaid"}
```

Add a helper such as:

```python
def subscription_billing_health(user: User) -> dict[str, Any]:
    ...
```

Return a dict with these keys:

- `state`: one of `"healthy"`, `"payment_failed"`, `"payment_required"`,
  `"canceled"`, `"inactive"`.
- `severity`: one of `"none"`, `"warning"`, `"danger"`, `"info"`.
- `requires_attention`: boolean.
- `blocks_access`: boolean.
- `action`: one of `None`, `"update_payment_method"`, `"manage_billing"`,
  `"choose_plan"`.
- `action_label`: short button text, for example `"Update payment"`,
  `"Manage"`, `"Choose plan"`.
- `message`: short user-facing message. Keep it professional and concrete.

Recommended mapping:

- `tier` is free or no `stripe_subscription_id`: healthy/inactive with no
  attention.
- `active` or `trialing` with `cancel_at_period_end=False`: healthy.
- `active` or `trialing` with `cancel_at_period_end=True`: info notice,
  `requires_attention=False`, action `"manage_billing"`.
- `past_due`: warning, `requires_attention=True`, `blocks_access=False`,
  action `"update_payment_method"`.
- `incomplete`: danger, `requires_attention=True`, `blocks_access=True`,
  action `"update_payment_method"`.
- `unpaid`: danger, `requires_attention=True`, `blocks_access=True`,
  action `"update_payment_method"`.
- `canceled` or `incomplete_expired`: danger/inactive, `blocks_access=True`,
  action `"choose_plan"`.

Update `serialize_subscription(user)` to include:

```python
"billing_health": subscription_billing_health(user),
```

Do not remove the existing `status`, `is_paid_entitled`, or
`includes_video_analysis` fields; existing frontend code and tests rely on
them.

Decide the entitlement policy explicitly:

- Keep `active` and `trialing` entitled.
- For `past_due`, choose one behavior and test it:
  - Recommended production behavior: include `past_due` in paid entitlement
    only while Stripe is still retrying collection, because Stripe will move to
    `unpaid` or `canceled` when dunning is exhausted.
  - If the product owner wants strict lockout, keep `past_due` blocked. The
    rest of this plan still works, but update messages to say access is paused.

For the recommended behavior, update `PAID_STATUSES` to include `past_due` and
add comments explaining that `unpaid` remains blocked. Keep video analysis
aligned with paid entitlement by reusing the same status policy in
`includes_video_analysis`.

**Verify**:
`backend/venv/bin/python -m pytest backend/tests/test_billing.py -q`
Expected at this point: tests may fail until Step 5 adds/updates assertions,
but there should be no import or syntax errors. If there are syntax/import
errors, fix them before continuing.

### Step 2: Add a payment-method update portal flow

In `backend/app/billing.py`, add:

```python
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
```

If Stripe's current SDK/API shape in the installed version requires
`flow_data["payment_method_update"] = {}`, include that empty object. Verify
against https://docs.stripe.com/api/customer_portal/sessions/create before
finalizing the payload.

In `backend/app/api/billing.py`, expose this without overloading plan-change:

- Import `create_payment_method_update_session`.
- Add `POST /api/billing/payment-method`.
- Use `_safe_return_path(payload.get("return_path"))`.
- Return `{"url": url}`.
- Catch `BillingConfigError` and `ValueError` the same way `/portal` does.

Do not remove `/api/billing/portal`; Profile still needs generic management
for healthy paid subscriptions.

In `frontend/src/lib/billing.js`, add:

```js
export const createPaymentMethodSession = (payload = {}) => api.post('/api/billing/payment-method', payload)
```

**Verify**:
`backend/venv/bin/python -m pytest backend/tests/test_billing.py -q`
Expected at this point: backend syntax/imports are clean; route tests may still
need to be added in Step 5.

### Step 3: Expand webhook event coverage for payment-action cases

In `backend/app/api/webhooks.py`, update the invoice event set to include
Stripe's payment-action event:

```python
elif event_type in {
    "invoice.paid",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
    "invoice.payment_action_required",
}:
```

Keep the current pattern: use the event only as a pointer, refetch the invoice,
then sync the latest subscription reference. Do not trust the embedded invoice
payload for subscription state.

If the live Stripe docs or installed SDK make `invoice.payment_action_required`
unavailable for the account's API version, STOP and report that the app should
handle it as a future webhook once the API version supports it. Do not invent
an alternate event name.

**Verify**:
`backend/venv/bin/python -m pytest backend/tests/test_billing.py -q`
Expected: no syntax/import errors.

### Step 4: Add reusable frontend billing notice and recovery action

Create `frontend/src/components/BillingStatusNotice.vue`.

Component contract:

- Props:
  - `health`: object, default `{}`.
  - `compact`: boolean, default `false`.
  - `loading`: boolean, default `false`.
- Emits:
  - `action`
- Rendering:
  - Return no visible markup when `!health?.requires_attention` and
    `health?.severity !== 'info'`.
  - Use lucide icons: `AlertTriangle` for warning, `CircleAlert` for danger,
    `Info` for info, `LoaderCircle` when loading.
  - Show `health.message`.
  - Show a button only when `health.action` exists. Button text should be
    `health.action_label`.
  - On click, emit `action`.

Keep text short. Example visible messages:

- Past due: `Payment failed. Update your payment method to keep access.`
- Unpaid: `Payment is overdue. Update payment to restore access.`
- Cancel scheduled: `Your plan ends at the current period end.`

Style it as a compact inline notice/band, not a nested card. Match the app's
existing dark background, gold accent, and error-box pattern, but do not place
cards inside cards.

In `frontend/src/views/ProfileView.vue`:

- Import `BillingStatusNotice` and `createPaymentMethodSession`.
- Add a computed `billingHealth = computed(() => subscription.value.billing_health || {})`.
- Render `BillingStatusNotice` inside the billing card, below the top row and
  above usage.
- Add `paymentLoading = ref(false)`.
- Add `openPaymentRecovery()`:
  - If `billingHealth.value.action === 'choose_plan'`, route to `/pricing`.
  - If `billingHealth.value.action === 'manage_billing'`, call the existing
    `openBillingPortal()`.
  - Otherwise call `createPaymentMethodSession({ return_path: '/profile' })`
    and `window.location.assign(res.data.url)`.
  - Use `paymentLoading` for the notice button loader.
- Keep the existing `Manage` / `Plans` button behavior unchanged.

In `frontend/src/App.vue`:

- Add a top-level signed-in billing banner so users do not need to visit
  Profile to learn payment failed.
- Use a small composable or local state to call `getSubscription()` after
  sign-in. Prefer a new singleton composable
  `frontend/src/composables/useBillingStatus.js` if this avoids duplicating
  logic with Profile.
- Do not block route rendering while loading.
- Show `BillingStatusNotice` between `<nav>` and `<main>` when the signed-in
  subscription has `billing_health.requires_attention`.
- The action should use `createPaymentMethodSession({ return_path: router.currentRoute.value.fullPath || '/profile' })`
  for `update_payment_method`, `/pricing` for `choose_plan`, and generic portal
  for `manage_billing`.

Avoid polling in this plan. A single fetch on sign-in/app mount plus refreshes
after recovery navigation are enough for the first production-ready slice.

**Verify**:
`cd frontend && npm test -- ProfileView.test.js`
Expected at this point: existing tests may fail until Step 6 updates mocks, but
there should be no component import or syntax errors.

### Step 5: Show payment-specific recovery messaging on feature errors

Backend:

Update `billing_required_response(user)` in `backend/app/billing.py` to include
serialized subscription/billing health:

```python
subscription = serialize_subscription(user)
health = subscription["billing_health"]
return jsonify({
    "error": health["message"] if health.get("requires_attention") else "Active subscription required",
    "code": "billing_payment_required" if health.get("action") == "update_payment_method" else "subscription_required",
    "plans_url": "/pricing",
    "subscription": subscription,
    "billing_health": health,
}), 402
```

Keep `feature_limit_reached` behavior in `backend/app/feature_limits.py`
unchanged.

Frontend:

In `PredictView.vue`, `TournamentView.vue`, and `MarketsView.vue`, stop
treating every billing failure as "go to pricing". Store the returned
`billing_health` in a new ref where the API error provides it.

For each view:

- Import `BillingStatusNotice`.
- Add `const billingHealth = ref(null)` or one ref per tab in `MarketsView`.
- In catch blocks:
  - `billingHealth.value = e.response?.data?.billing_health || null`
  - Set the existing `subscriptionRequired` boolean for
    `subscription_required`, `billing_payment_required`, and
    `feature_limit_reached`.
- In the error box:
  - If `billingHealth?.requires_attention`, render `BillingStatusNotice` with
    the same recovery action behavior used in Profile/App.
  - Else keep the existing `BillingPlansLink` for pricing/limit prompts.

If this duplicates too much action code across three views, extract a tiny
helper/composable. Keep it scoped; do not introduce a global state management
library.

**Verify**:
`cd frontend && npm test -- ProfileView.test.js`
Expected: Profile tests pass once Step 6 is complete. If feature pages have no
tests, build verification in Step 7 must catch syntax/template errors.

### Step 6: Add backend and frontend tests

Backend tests in `backend/tests/test_billing.py`:

Add tests near the existing billing tests.

Required cases:

1. `serialize_subscription()` includes billing health for `past_due`:
   - User has `subscription_tier = "pro"`, `subscription_status = "past_due"`,
     `stripe_subscription_id`, and `stripe_customer_id`.
   - Assert `billing_health.state == "payment_failed"`.
   - Assert `billing_health.action == "update_payment_method"`.
   - Assert `billing_health.requires_attention is True`.
   - Assert entitlement behavior matches Step 1's explicit policy.

2. `serialize_subscription()` includes blocked health for `unpaid`:
   - Assert `billing_health.blocks_access is True`.
   - Assert `is_paid_entitled` is false.

3. `POST /api/billing/payment-method` creates the expected portal flow:
   - Follow the fake Stripe style from `test_portal_creates_customer_when_missing`.
   - Use a user with `stripe_customer_id = "cus_existing"`.
   - Fake `billing_portal.Session.create`.
   - Assert `flow_data.type == "payment_method_update"`.
   - Assert `after_completion.redirect.return_url == "http://localhost:3001/profile"`.

4. `billing_required_response()` includes `billing_health` for a payment
   failure:
   - Either call a paid endpoint that uses the helper or import and call the
     helper inside an app context.
   - Assert response code is 402.
   - Assert `code == "billing_payment_required"` for the update-payment path.

5. `invoice.payment_action_required` refetches invoice and subscription:
   - Model after `test_invoice_paid_webhook_refetches_invoice_and_subscription`
     at `backend/tests/test_billing.py:663-700`.
   - Assert invoice retrieve and subscription retrieve are called with the
     current resource IDs, not stale payload data.

Frontend tests:

Update `frontend/src/views/ProfileView.test.js`:

- Extend the billing mock import to include `createPaymentMethodSession`.
- Add a test where `getSubscription` resolves:

```js
{
  data: {
    tier: 'pro',
    status: 'past_due',
    is_paid_entitled: true or false, // match backend policy
    billing_health: {
      state: 'payment_failed',
      severity: 'warning',
      requires_attention: true,
      blocks_access: false,
      action: 'update_payment_method',
      action_label: 'Update payment',
      message: 'Payment failed. Update your payment method to keep access.',
    },
  },
}
```

- Assert the notice text appears.
- Click the notice CTA.
- Assert `createPaymentMethodSession` is called with `{ return_path: '/profile' }`.
- Assert `window.location.assign` receives the fake portal URL.

Add a small component test for `BillingStatusNotice.vue` if Profile assertions
do not cover warning/danger rendering and disabled loading state.

Do not add brittle tests that assert every CSS class. Test behavior and visible
copy only.

**Verify**:

- `backend/venv/bin/python -m pytest backend/tests/test_billing.py`
  Expected: all tests pass.
- `cd frontend && npm test -- ProfileView.test.js`
  Expected: all tests pass.

### Step 7: Update README and Stripe dashboard checklist

Update the `README.md` Stripe billing setup section.

Add to webhook subscribed events:

- `invoice.payment_action_required`

Add a production checklist under Stripe setup:

- Enable Stripe customer emails for failed payments.
- Configure retry/dunning policy in Stripe Billing settings.
- Confirm Customer Portal allows payment method updates.
- Confirm Customer Portal allows subscription cancellation and plan updates.
- Test a failed payment in Stripe test mode and confirm:
  - webhook receives the event,
  - `/profile` shows a payment notice,
  - the top app banner shows a payment notice,
  - clicking `Update payment` opens Stripe Portal's payment-method update flow,
  - once Stripe marks the subscription active again, the notice disappears.

Do not document secret values. Keep environment-variable names only.

**Verify**:
`git diff --check`
Expected: exit 0.

### Step 8: Run full verification

Run:

```bash
backend/venv/bin/python -m pytest backend/tests
cd frontend && npm test
cd frontend && npm run build
git diff --check
```

Expected:

- Backend: all tests pass.
- Frontend: all tests pass.
- Build: Vite completes successfully.
- Diff check: no whitespace errors.

If the frontend build writes ignored `frontend/dist` files, do not commit them
unless the repo already tracks them. Check `git status --short` before final
handoff.

## Test plan

Backend:

- Unit/route tests in `backend/tests/test_billing.py`.
- Cover health serialization for `past_due` and `unpaid`.
- Cover `billing_required_response` response shape for payment recovery.
- Cover `POST /api/billing/payment-method` Stripe portal flow payload.
- Cover `invoice.payment_action_required` webhook refetch path.

Frontend:

- Update `frontend/src/views/ProfileView.test.js` for payment notice and
  payment-method recovery action.
- Add `BillingStatusNotice` component tests only if Profile coverage does not
  assert warning/danger/loader behavior.
- Use full `npm test` and `npm run build` to catch feature-page template errors,
  since `PredictView`, `TournamentView`, and `MarketsView` currently do not
  have focused tests.

Manual Stripe smoke test after deployment/test-mode setup:

1. Create or use a paid test subscription.
2. Trigger a failed payment scenario in Stripe test mode.
3. Confirm Stripe webhook syncs the subscription to the expected failed status.
4. Open the app while signed in.
5. Confirm the global banner and Profile notice appear.
6. Click `Update payment`.
7. Confirm Stripe Portal opens directly to payment-method update.
8. Complete recovery in Stripe.
9. Confirm webhook sync returns the subscription to healthy state and notices
   disappear.

## Done criteria

All must hold:

- [ ] `serialize_subscription()` returns `billing_health` with stable keys:
  `state`, `severity`, `requires_attention`, `blocks_access`, `action`,
  `action_label`, `message`.
- [ ] `POST /api/billing/payment-method` returns a Stripe Portal URL using
  `flow_data.type == "payment_method_update"`.
- [ ] `invoice.payment_action_required` is handled by refetching invoice and
  subscription from Stripe.
- [ ] Profile billing section shows a payment-failure notice with an
  `Update payment` action for `past_due`/`unpaid` style statuses.
- [ ] Signed-in app shell shows a billing-health banner when
  `billing_health.requires_attention` is true.
- [ ] Feature pages show payment-specific recovery messaging when a 402
  response includes `billing_health.action == "update_payment_method"`.
- [ ] Generic free-tier/limit prompts still go to pricing.
- [ ] README documents the new webhook event and production Stripe dunning /
  Customer Portal checklist.
- [ ] `backend/venv/bin/python -m pytest backend/tests` exits 0.
- [ ] `cd frontend && npm test` exits 0.
- [ ] `cd frontend && npm run build` exits 0.
- [ ] `git diff --check` exits 0.
- [ ] `plans/README.md` status row for Plan 004 is updated.

## STOP conditions

Stop and report back if:

- The live code no longer has `_portal_session_url(...)`, `serialize_subscription(...)`,
  or `billing_required_response(...)` in `backend/app/billing.py`.
- Stripe's current API docs or installed SDK reject the `payment_method_update`
  portal flow shape, and a simple documented adjustment is not obvious.
- The product owner rejects the chosen `past_due` entitlement policy. Do not
  guess; ask whether `past_due` should keep access during Stripe retries or
  immediately block paid features.
- Implementing the app-shell banner requires a new global state library.
- A database migration appears necessary for this first recovery UX. Stop and
  explain why existing subscription fields are insufficient.
- Any verification command fails twice after a reasonable fix attempt.

## Maintenance notes

- Stripe dunning policy controls when subscriptions move from `past_due` to
  `unpaid` or `canceled`; keep backend entitlement policy aligned with that
  dashboard setting.
- If the app later sends its own failed-payment emails, reuse
  `billing_health` messaging and do not duplicate a separate status mapping.
- If multiple subscriptions per customer are introduced, revisit
  `_best_customer_subscription(...)` before relying on one billing health value.
- If the product adds annual plans or trials, update the `past_due` and
  `incomplete` copy so users understand whether access is retained.
