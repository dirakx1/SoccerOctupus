# Plan 002: Implement cycle-based feature usage limits

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report; do not improvise. When done, update the status row for this plan in
> `plans/README.md`.
>
> **Drift check (run first)**:
> `git diff --stat c6a14a9..HEAD -- backend/app/db/models.py backend/app/billing.py backend/app/api/predictions.py backend/app/api/markets.py backend/app/api/admin.py backend/app/api/billing.py backend/app/runtime_settings.py backend/tests frontend/src/views frontend/src/lib plans/002-implement-cycle-based-feature-usage-limits.md`
>
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding. If the
> endpoint names, subscription fields, or test structure no longer match,
> treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: L
- **Risk**: MED
- **Depends on**: `plans/001-implement-stripe-subscriptions.md`
- **Category**: direction
- **Planned at**: commit `c6a14a9`, 2026-06-24

## Why this matters

Free users currently get hard-blocked from prediction and market generation
with `subscription_required`, even though the product requirement is to allow a
small number of free runs per user cycle. The new system must also support
future Basic/Pro limits without redesigning the data model. Keep Free off
Stripe: Stripe remains the source of paid subscription state and paid billing
period dates, while this app owns all feature quotas, usage counters, and
manual overrides.

The implementation should support these four feature keys:

| Feature key | Endpoint | Free default per cycle |
|-------------|----------|------------------------|
| `match_prediction` | `POST /api/predictions/match` | 1 |
| `tournament_simulation` | `POST /api/predictions/tournament` | 1 |
| `match_market` | `POST /api/markets/match` | 3 |
| `tournament_market` | `POST /api/markets/tournament` | 3 |

Basic and Pro should default to unlimited now, but the database model must let
admins add finite limits for those tiers later. Limits reset on the user's own
cycle, not on calendar month boundaries.

## Current state

Relevant backend files:

- `backend/app/db/models.py` - SQLAlchemy models for users, Stripe events, and app settings.
- `backend/app/billing.py` - Stripe sync and current paid entitlement helpers.
- `backend/app/api/predictions.py` - prediction generation endpoints.
- `backend/app/api/markets.py` - market generation endpoints.
- `backend/app/api/admin.py` - admin settings and `/api/me`.
- `backend/app/api/billing.py` - billing subscription/portal endpoints.
- `backend/migrations/versions/` - Alembic migrations.

Relevant frontend files:

- `frontend/src/views/PredictView.vue` - calls `POST /api/predictions/match`.
- `frontend/src/views/TournamentView.vue` - calls `POST /api/predictions/tournament`.
- `frontend/src/views/MarketsView.vue` - calls both market generation endpoints.
- `frontend/src/views/ProfileView.vue` - profile and billing summary.
- `frontend/src/views/AdminSettingsView.vue` - admin runtime settings UI.
- `frontend/src/lib/billing.js` - current billing API wrapper.

Current backend subscription model has `subscription_current_period_end` but no
paid-period start and no free-cycle anchor:

```python
# backend/app/db/models.py:37-44
stripe_customer_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
stripe_subscription_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
stripe_price_id = db.Column(db.String(255), nullable=True, index=True)
subscription_tier = db.Column(db.String(32), nullable=False, default="free", index=True)
subscription_status = db.Column(db.String(64), nullable=True, index=True)
subscription_current_period_end = db.Column(db.DateTime(timezone=True), nullable=True)
subscription_cancel_at_period_end = db.Column(db.Boolean, nullable=False, default=False)
subscription_synced_at = db.Column(db.DateTime(timezone=True), nullable=True)
```

Current billing serialization exposes only the subscription, not usage:

```python
# backend/app/billing.py:77-91
def serialize_subscription(user: User) -> dict[str, Any]:
    tier = user.subscription_tier or "free"
    return {
        "tier": tier,
        "status": user.subscription_status,
        "is_paid_entitled": is_paid_entitled(user),
        "includes_video_analysis": includes_video_analysis(user),
        "current_period_end": (
            user.subscription_current_period_end.isoformat()
            if user.subscription_current_period_end
            else None
        ),
        "cancel_at_period_end": bool(user.subscription_cancel_at_period_end),
        "synced_at": user.subscription_synced_at.isoformat() if user.subscription_synced_at else None,
    }
```

Current free-user behavior hard-blocks generation:

```python
# backend/app/billing.py:106-115
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

The four target endpoints currently call that hard-block before running:

```python
# backend/app/api/predictions.py:53-57
if not home or not away:
    return jsonify({"error": "home_team and away_team are required"}), 400
required = billing_required_response(g.current_user)
if required:
    return required
```

```python
# backend/app/api/predictions.py:85-89
data = request.get_json(force=True) or {}
use_swarm = data.get("use_swarm", False)
required = billing_required_response(g.current_user)
if required:
    return required
```

```python
# backend/app/api/markets.py:50-54
if not home or not away:
    return jsonify({"error": "home_team and away_team are required"}), 400
required = billing_required_response(g.current_user)
if required:
    return required
```

```python
# backend/app/api/markets.py:99-103
data = request.get_json(silent=True) or {}
platform = data.get("platform", "both").lower()
required = billing_required_response(g.current_user)
if required:
    return required
```

Current Stripe subscription sync stores period end only:

```python
# backend/app/billing.py:318-325
user.stripe_customer_id = customer_id or user.stripe_customer_id
user.stripe_subscription_id = subscription_id or user.stripe_subscription_id
user.subscription_status = "canceled" if deleted else status
user.subscription_current_period_end = _ts(_get_value(subscription, "current_period_end"))
user.subscription_cancel_at_period_end = False if deleted else bool(_get_value(subscription, "cancel_at_period_end"))
user.subscription_synced_at = utcnow()
user.stripe_price_id = price_id
user.subscription_tier = "free" if deleted else tier_for_price_id(price_id)
```

Current tests assert the old hard-block behavior:

```python
# backend/tests/test_billing.py:362-379
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
```

Frontend generation views currently only recognize `subscription_required`:

```js
// frontend/src/views/PredictView.vue:181-184
} catch (e) {
  error.value = e.response?.data?.error || e.message
  subscriptionRequired.value = e.response?.data?.code === 'subscription_required'
}
```

```js
// frontend/src/views/TournamentView.vue:107-110
} catch (e) {
  error.value = e.response?.data?.error || e.message
  subscriptionRequired.value = e.response?.data?.code === 'subscription_required'
}
```

```js
// frontend/src/views/MarketsView.vue:321-324
} catch (e) {
  matchError.value = e.response?.data?.error ?? e.message
  matchSubscriptionRequired.value = e.response?.data?.code === 'subscription_required'
}
```

```js
// frontend/src/views/MarketsView.vue:338-341
} catch (e) {
  tourneyError.value = e.response?.data?.error ?? e.message
  tourneySubscriptionRequired.value = e.response?.data?.code === 'subscription_required'
}
```

Repository conventions to follow:

- Backend is Flask blueprints plus SQLAlchemy models, with Alembic migrations
  under `backend/migrations/versions`.
- Tests use pytest fixtures from `backend/tests/conftest.py`, in-memory SQLite,
  and monkeypatching for external services.
- Frontend is Vue 3 with script setup, axios through `frontend/src/lib/api.js`,
  and Vitest tests next to views.
- Existing branch/commit style is short imperative sentence, e.g.
  `Add Stripe billing and subscription support`.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Backend tests | `cd backend && venv/bin/python -m pytest` | exit 0; all tests pass |
| Focused backend tests | `cd backend && venv/bin/python -m pytest tests/test_feature_limits.py tests/test_billing.py` | exit 0; all tests pass |
| Frontend tests | `cd frontend && npm test` | exit 0; all Vitest tests pass |
| Frontend build | `cd frontend && npm run build` | exit 0; Vite build completes |
| Diff check | `git diff --check` | exit 0; no whitespace errors |

If `venv/bin/python` does not exist in a fresh checkout, use the repo's backend
setup command first: `cd backend && pip install -r requirements.txt`.

## Scope

**In scope**:

- `backend/app/db/models.py`
- `backend/migrations/versions/20260624_0005_feature_usage_limits.py` (create)
- `backend/app/feature_limits.py` (create)
- `backend/app/billing.py`
- `backend/app/api/predictions.py`
- `backend/app/api/markets.py`
- `backend/app/api/admin.py`
- `backend/app/api/billing.py`
- `backend/tests/test_feature_limits.py` (create)
- `backend/tests/test_billing.py`
- `backend/tests/test_auth_and_settings.py` only if admin settings response tests need updating
- `frontend/src/lib/billing.js`
- `frontend/src/views/ProfileView.vue`
- `frontend/src/views/PredictView.vue`
- `frontend/src/views/TournamentView.vue`
- `frontend/src/views/MarketsView.vue`
- `frontend/src/views/AdminSettingsView.vue`
- `frontend/src/views/ProfileView.test.js`
- `frontend/src/views/AdminSettingsView.test.js`
- `frontend/src/views/PricingView.test.js` only if plan catalog copy changes
- `README.md` only if the implementation adds user-visible setup/admin notes

**Out of scope**:

- Do not create a Free product or Free price in Stripe.
- Do not subscribe Free users in Stripe.
- Do not change Basic/Pro checkout prices or Stripe portal configuration.
- Do not add a full admin user-search page unless the operator explicitly asks.
  User-specific override endpoints and service support are enough for this plan.
- Do not change prediction algorithms, agent weights, or market question logic.
- Do not alter Clerk auth flows except where tests require authenticated calls.

## Git workflow

- Branch: keep the current branch unless the operator asks for a new one. If
  creating a branch, use `codex/002-cycle-based-feature-usage-limits`.
- Commit message style: short imperative sentence, e.g. `Add cycle-based feature usage limits`.
- Do not push or open a PR unless instructed.

## Data model target

Add these concepts.

### User cycle fields

Add to `User`:

- `subscription_current_period_start`: nullable timezone-aware datetime. Set
  from Stripe for paid subscriptions.
- `usage_cycle_anchor_at`: nullable or non-null timezone-aware datetime. For
  Free users, this anchors their cycle. Default to user creation time for
  existing and new users.

For Free users, cycle windows are monthly intervals anchored to
`usage_cycle_anchor_at`. Example: signup/anchor `2026-06-12T10:00:00Z` yields
`2026-06-12 -> 2026-07-12`, then `2026-07-12 -> 2026-08-12`.

For paid users, cycle windows come from Stripe:
`subscription_current_period_start -> subscription_current_period_end`.

### Tier policy table

Create `feature_limit_policies`:

- `id`
- `tier`: string, indexed
- `feature_key`: string, indexed
- `limit_count`: integer nullable; `NULL` means unlimited
- `created_at`, `updated_at`
- unique constraint on `(tier, feature_key)`

Seed these defaults in the migration and ensure the service can lazily create
them in tests that use `db.create_all()` instead of Alembic:

| tier | feature_key | limit_count |
|------|-------------|-------------|
| free | match_prediction | 1 |
| free | tournament_simulation | 1 |
| free | match_market | 3 |
| free | tournament_market | 3 |
| basic | match_prediction | NULL |
| basic | tournament_simulation | NULL |
| basic | match_market | NULL |
| basic | tournament_market | NULL |
| pro | match_prediction | NULL |
| pro | tournament_simulation | NULL |
| pro | match_market | NULL |
| pro | tournament_market | NULL |

### Standing per-user overrides

Create `user_feature_limit_overrides`:

- `id`
- `user_id` FK to users, indexed
- `feature_key`, indexed
- `limit_count` nullable; `NULL` means unlimited
- `starts_at`
- `ends_at` nullable
- `is_active`
- `created_by_user_id` nullable FK to users
- `note` nullable text
- `created_at`, `updated_at`

Use the latest active override for `(user_id, feature_key)` when materializing
a new cycle row. Overrides apply only to cycles created while the override is
active; they do not mutate already-materialized cycle rows.

### Materialized per-user cycle rows

Create `user_feature_cycle_limits`:

- `id`
- `user_id` FK to users, indexed
- `tier`: tier used when the row was created
- `feature_key`, indexed
- `cycle_start`, indexed
- `cycle_end`, indexed
- `limit_count` nullable; `NULL` means unlimited
- `used_count` integer, default `0`
- `limit_source`: `policy`, `user_override`, or `manual_cycle_override`
- `override_note` nullable text
- `overridden_by_user_id` nullable FK to users
- `created_at`, `updated_at`
- unique constraint on `(user_id, feature_key, cycle_start, cycle_end)`

This table is the enforcement table. Changing a global policy should affect
future cycles only. Current-cycle manual overrides should update the
materialized row.

## API behavior target

### Usage response

Add `GET /api/billing/usage` behind `@require_user(db)`. It should ensure the
current cycle rows exist for the requesting user and return:

```json
{
  "tier": "free",
  "cycle_start": "2026-06-12T10:00:00+00:00",
  "cycle_end": "2026-07-12T10:00:00+00:00",
  "features": [
    {
      "feature_key": "match_prediction",
      "label": "Match predictions",
      "limit_count": 1,
      "used_count": 0,
      "remaining_count": 1,
      "unlimited": false,
      "limit_source": "policy"
    }
  ]
}
```

Also add the same usage summary to `serialize_subscription(user)` or to
`/api/me` only if it does not create circular imports. The simplest safe route
is to keep usage at `/api/billing/usage` and have Profile call it separately.

### Limit-reached response

When a user exhausts a finite limit, return HTTP `402`:

```json
{
  "error": "Free limit reached for match predictions",
  "code": "feature_limit_reached",
  "feature_key": "match_prediction",
  "limit_count": 1,
  "used_count": 1,
  "remaining_count": 0,
  "cycle_start": "2026-06-12T10:00:00+00:00",
  "cycle_end": "2026-07-12T10:00:00+00:00",
  "plans_url": "/pricing"
}
```

For compatibility during rollout, frontend views should treat both
`subscription_required` and `feature_limit_reached` as an upsell condition.

### Admin policy endpoints

Add admin endpoints in `backend/app/api/admin.py`:

- `GET /api/admin/feature-limits`
  - Returns all `feature_limit_policies` grouped by tier, plus feature labels.
- `PUT /api/admin/feature-limits`
  - Accepts a list of policy records: `{ tier, feature_key, limit_count }`.
  - Validate tier in `free/basic/pro`, feature key in the four allowed keys,
    and `limit_count` is `null` or integer `>= 0`.
  - Do not accept negative limits.

Add admin endpoints for per-user overrides:

- `GET /api/admin/users/<user_id>/feature-limits`
  - Returns current cycle rows plus active standing overrides for that user.
- `POST /api/admin/users/<user_id>/feature-limit-overrides`
  - Creates or updates a standing override for future cycles.
- `PUT /api/admin/users/<user_id>/feature-cycle-limits/<feature_key>`
  - Ensures the current cycle row exists, then updates that row's `limit_count`,
    `limit_source="manual_cycle_override"`, `override_note`, and
    `overridden_by_user_id`.

No frontend user-management screen is required in this plan unless the operator
asks. These endpoints and tests are enough to make per-user overrides available.

## Steps

### Step 1: Add schema and migration

1. Update `backend/app/db/models.py`:
   - Add `subscription_current_period_start` and `usage_cycle_anchor_at` to
     `User`.
   - Add model classes `FeatureLimitPolicy`, `UserFeatureLimitOverride`, and
     `UserFeatureCycleLimit`.
   - Use the existing `TimestampMixin`.
   - Add relationships only where needed for serialization; avoid large
     eager-loaded relationships on hot auth paths.

2. Create `backend/migrations/versions/20260624_0005_feature_usage_limits.py`:
   - `down_revision = "20260619_0004"`.
   - Add the two new user columns.
   - Backfill `users.usage_cycle_anchor_at` from `users.created_at`.
   - Create the three new feature-limit tables and indexes/unique constraints.
   - Seed the default policy rows listed above.
   - Downgrade must drop the new tables and columns.

3. SQLite test compatibility:
   - Tests use `db.create_all()`, so model definitions must be complete without
     relying on Alembic.
   - Avoid migration operations that are unsupported by SQLite in normal test
     setup. Alembic migration can target Postgres/Supabase, but model tests must
     not require migration execution.

**Verify**:

`cd backend && venv/bin/python -m pytest tests/test_billing.py::test_plans_return_free_basic_and_pro`

Expected: exit 0, the test passes. This verifies the app imports and existing
models still create cleanly.

### Step 2: Add the feature limit service

Create `backend/app/feature_limits.py`. It should own all feature key constants,
cycle calculations, policy materialization, usage serialization, and
reservation/release behavior.

Required constants:

```python
FEATURE_MATCH_PREDICTION = "match_prediction"
FEATURE_TOURNAMENT_SIMULATION = "tournament_simulation"
FEATURE_MATCH_MARKET = "match_market"
FEATURE_TOURNAMENT_MARKET = "tournament_market"
FEATURE_KEYS = {...}
FEATURE_LABELS = {...}
TIERS = {"free", "basic", "pro"}
DEFAULT_POLICIES = {...}
```

Required service behavior:

- `ensure_default_feature_limit_policies(db_session)` inserts missing default
  policies idempotently. This is needed because tests call `db.create_all()`
  instead of Alembic migrations.
- `effective_usage_tier(user, now)` returns:
  - `pro` or `basic` when the user has that tier, status is active/trialing,
    and the period has not expired.
  - `free` otherwise.
  - Admin users can be treated as `pro` with unlimited limits, or bypass checks
    explicitly. Keep behavior consistent in tests.
- `current_usage_cycle(user, now)` returns `(cycle_start, cycle_end, tier)`.
  - For paid active users with Stripe period start/end, use those dates.
  - For paid active users missing period dates, fall back to
    `usage_cycle_anchor_at` monthly cycles. This avoids breaking existing paid
    users before their next Stripe webhook.
  - For free users, use `usage_cycle_anchor_at` monthly cycles.
- Monthly cycle addition must use calendar months, not fixed 30-day windows.
  Implement with Python standard library (`calendar.monthrange`) to avoid
  adding a dependency.
- `ensure_cycle_limits(user, db_session, now=None)` creates one
  `UserFeatureCycleLimit` row per feature for the active cycle.
  - Standing override wins over tier policy.
  - If neither exists, create default policies first and retry.
  - Existing current-cycle rows must not be overwritten by policy changes.
- `serialize_usage(user, db_session, now=None)` returns the usage response shape.
- `reserve_feature_usage(user, feature_key, db_session, now=None)`:
  - Validate feature key.
  - Ensure current cycle row exists.
  - Lock the cycle row where the database supports it. Use SQLAlchemy
    `with_for_update()` for Postgres; SQLite tests will ignore/approximate it.
  - If `limit_count is None`, allow without incrementing.
  - If `used_count >= limit_count`, return a structured blocked result.
  - Otherwise increment `used_count` and commit before the expensive job starts.
- `release_feature_usage(cycle_limit_id, db_session)`:
  - Decrement `used_count` by one, not below zero, and commit.
  - Use only when the expensive job fails after reservation.

Important: reserve only after request validation succeeds. Invalid requests
must not consume usage.

Add `backend/tests/test_feature_limits.py` with service-level tests:

- Default policies are created idempotently.
- Free user gets exactly the configured defaults.
- Basic/Pro policies default to unlimited.
- Current-cycle rows are materialized and retain old limits after policy change.
- Standing user override applies to newly materialized cycles.
- Manual current-cycle override changes only the current cycle row.
- Free cycle resets based on `usage_cycle_anchor_at`, not calendar month end.
- Paid cycle uses `subscription_current_period_start/end`.
- A released failed reservation lets the user retry.

**Verify**:

`cd backend && venv/bin/python -m pytest tests/test_feature_limits.py`

Expected: exit 0, all new service tests pass.

### Step 3: Sync paid period start from Stripe

Update Stripe subscription sync in `backend/app/billing.py`:

- Add `subscription_current_period_start` to `serialize_subscription`.
- In `sync_subscription_from_stripe_subscription`, set:
  - `user.subscription_current_period_start = _ts(_get_value(subscription, "current_period_start"))`
  - `user.subscription_current_period_end = _ts(_get_value(subscription, "current_period_end"))`
- When a subscription is deleted/canceled and the user becomes free:
  - keep Stripe identifiers consistent with current behavior.
  - set `usage_cycle_anchor_at` to the previous paid period end when available
    and not in the future, otherwise `utcnow()`. This makes the next free cycle
    start at the paid access end.
  - Do not create or subscribe to a Free Stripe plan.

Update tests in `backend/tests/test_billing.py`:

- Update `_subscription()` helper to include `current_period_start`.
- Assert sync stores both start and end.
- Add a canceled/deleted subscription case that confirms the user falls back to
  `subscription_tier == "free"` and has a non-null `usage_cycle_anchor_at`.

**Verify**:

`cd backend && venv/bin/python -m pytest tests/test_billing.py::test_subscription_sync_maps_basic_pro_and_deleted`

Expected: exit 0, the updated test passes.

### Step 4: Enforce limits in the four generation endpoints

Replace the `billing_required_response(g.current_user)` hard-block in these
four endpoints:

- `backend/app/api/predictions.py::predict_match`
- `backend/app/api/predictions.py::simulate_tournament`
- `backend/app/api/markets.py::match_markets`
- `backend/app/api/markets.py::tournament_markets`

Use the feature limit service:

- `predict_match` uses `FEATURE_MATCH_PREDICTION`.
- `simulate_tournament` uses `FEATURE_TOURNAMENT_SIMULATION`.
- `match_markets` uses `FEATURE_MATCH_MARKET`.
- `tournament_markets` uses `FEATURE_TOURNAMENT_MARKET`.

Target endpoint pattern:

1. Parse and validate request body.
2. Reserve usage for the feature.
3. If blocked, return its `402` response.
4. Run the expensive prediction/simulation/market generation.
5. On success, return existing response shape.
6. On exception, release the reservation and return the existing `500` shape.

Do not change read-only endpoints:

- `GET /api/predictions/teams`
- `GET /api/predictions/groups`
- `GET /api/predictions/tournament/<sim_id>`
- `GET /api/markets/types`

Update/replace `test_free_user_gets_402_from_prediction_and_markets`:

- Free user gets first `POST /api/predictions/match` success, second gets
  `402` with `code == "feature_limit_reached"`.
- Free user gets three `POST /api/markets/match` successes, fourth gets 402.
- Free user gets one tournament simulation success, second gets 402.
- Free user gets three tournament market successes, fourth gets 402.
- Paid Basic/Pro user can exceed free limits and still preserves video
  entitlement behavior (`basic` excludes video, `pro` includes video).
- Failed generation releases the reserved usage.

Use monkeypatch fakes for expensive services, matching current test style.

**Verify**:

`cd backend && venv/bin/python -m pytest tests/test_feature_limits.py tests/test_billing.py`

Expected: exit 0, all feature-limit and billing tests pass.

### Step 5: Add usage and admin APIs

Update `backend/app/api/billing.py`:

- Add `GET /api/billing/usage` using `serialize_usage(g.current_user, db)`.
- Keep `GET /api/billing/subscription` working as-is.

Update `backend/app/api/admin.py`:

- Add `GET /api/admin/feature-limits`.
- Add `PUT /api/admin/feature-limits`.
- Add `GET /api/admin/users/<int:user_id>/feature-limits`.
- Add `POST /api/admin/users/<int:user_id>/feature-limit-overrides`.
- Add `PUT /api/admin/users/<int:user_id>/feature-cycle-limits/<feature_key>`.

Validation rules:

- Only admins can use admin endpoints.
- `tier` must be `free`, `basic`, or `pro`.
- `feature_key` must be one of the four feature keys.
- `limit_count` can be `null` for unlimited, or integer `>= 0`.
- Reject malformed payloads with 400 and a short error message.
- Do not allow non-admins to read or mutate limit policies.

Tests to add in `backend/tests/test_feature_limits.py` or
`backend/tests/test_auth_and_settings.py`:

- Admin can read and update global policies.
- Non-admin gets 403 for policy updates.
- Invalid feature key or negative limit returns 400.
- Admin can create a standing user override.
- Admin can override the current cycle for a specific user/feature.
- Current-cycle override is reflected in `/api/billing/usage` for that user.

**Verify**:

`cd backend && venv/bin/python -m pytest tests/test_feature_limits.py tests/test_auth_and_settings.py`

Expected: exit 0, all tests pass.

### Step 6: Update frontend billing and limit UX

Update `frontend/src/lib/billing.js`:

- Add `getUsage = () => api.get('/api/billing/usage')`.

Update `frontend/src/views/ProfileView.vue`:

- Load subscription and usage in the billing section.
- Show current tier plus concise usage rows for the four features.
- Use existing loader style (`LoaderCircle`) for loading states.
- Keep button copy short.
- Do not add a separate Billing page.

Update generation views:

- `PredictView.vue`
- `TournamentView.vue`
- `MarketsView.vue`

Treat `feature_limit_reached` as an upsell state like `subscription_required`,
but preserve the specific error text from the backend. Existing
`BillingPlansLink` should remain usable for upgrade prompts.

Update `frontend/src/views/AdminSettingsView.vue`:

- Add a "Feature limits" section.
- Fetch `GET /api/admin/feature-limits` on mount.
- Render numeric inputs for Free limits:
  - Match predictions: default 1
  - Tournament simulations: default 1
  - Match markets: default 3
  - Tournament markets: default 3
- Also render Basic/Pro inputs where blank means unlimited, so future paid
  limits can be configured without another schema change.
- Save feature limits through `PUT /api/admin/feature-limits`.
- Keep existing runtime settings save behavior working. Either save feature
  limits through a separate button/section or include it in the same save flow
  with clear error handling. Prefer a separate section if it keeps the code
  simpler.

Frontend tests:

- Update `ProfileView.test.js` to mock `getUsage` and assert usage rows render.
- Update `AdminSettingsView.test.js` to mock admin feature-limit endpoints and
  assert Free defaults can be edited/saved.
- Update relevant view tests or add new tests for `feature_limit_reached`
  handling if the generation views already have test coverage. If they do not,
  add focused tests only if practical; do not build a broad E2E suite in this
  plan.

**Verify**:

`cd frontend && npm test`

Expected: exit 0, all Vitest tests pass.

`cd frontend && npm run build`

Expected: exit 0, Vite build completes.

### Step 7: Run full verification and update docs/index

Run:

```bash
cd backend && venv/bin/python -m pytest
cd frontend && npm test
cd frontend && npm run build
git diff --check
```

Expected:

- Backend: all tests pass.
- Frontend: all tests pass.
- Build: succeeds.
- Diff check: exits 0.

If the implementation changes user-visible setup or admin behavior, update
`README.md` with a short "Feature usage limits" section:

- Free tier is enforced by app DB, not Stripe.
- Paid tiers are billed by Stripe.
- Admins can configure per-tier limits in the app DB/admin settings.
- Per-user and current-cycle overrides are supported through admin endpoints.

Finally, update `plans/README.md` status for Plan 002 to `DONE` only after all
verification commands pass.

## Test plan

Backend tests:

- New `backend/tests/test_feature_limits.py`:
  - Default policy seeding.
  - Cycle calculation for free anchored cycles.
  - Cycle calculation for paid Stripe periods.
  - Materialized cycle rows freeze current-cycle limits.
  - Policy changes apply only to future cycles.
  - Standing user overrides apply when creating a new cycle.
  - Manual cycle override applies immediately to current cycle.
  - Reservation blocks at limit, releases on failure, and resets next cycle.
  - `/api/billing/usage` returns expected shape.
  - Admin policy and override endpoints validate auth and payloads.

- Update `backend/tests/test_billing.py`:
  - Existing free-user 402 test becomes quota behavior tests.
  - Paid video entitlement test still passes.
  - Stripe subscription sync stores current period start/end.

Frontend tests:

- Update `frontend/src/views/ProfileView.test.js`:
  - Mock `getUsage`.
  - Assert current tier and usage rows render.
  - Existing portal button test still passes.

- Update `frontend/src/views/AdminSettingsView.test.js`:
  - Mock feature limit load/save.
  - Assert a Free feature limit can be changed and saved.
  - Existing runtime settings tests still pass.

Verification commands:

- `cd backend && venv/bin/python -m pytest`
- `cd frontend && npm test`
- `cd frontend && npm run build`
- `git diff --check`

## Done criteria

All must be true:

- [ ] `feature_limit_policies`, `user_feature_limit_overrides`, and
      `user_feature_cycle_limits` exist in SQLAlchemy models and Alembic.
- [ ] `users.subscription_current_period_start` and
      `users.usage_cycle_anchor_at` exist in SQLAlchemy models and Alembic.
- [ ] Free defaults are exactly 1, 1, 3, 3 for the four feature keys.
- [ ] Basic/Pro default policies are unlimited (`NULL`) but configurable.
- [ ] Free users can use each of the four generation features up to their
      configured cycle limit.
- [ ] The next request after limit exhaustion returns HTTP 402 with
      `code == "feature_limit_reached"`.
- [ ] Paid Basic/Pro users continue to pass generation endpoints and preserve
      video entitlement behavior.
- [ ] Failed generation releases quota.
- [ ] Free cycles reset from the user's anchor date, not month end.
- [ ] Paid cycles use Stripe `current_period_start/end` when present.
- [ ] Admins can update tier policies.
- [ ] Admins can create per-user standing overrides.
- [ ] Admins can override a user's current cycle limit.
- [ ] Profile page shows usage for the four feature keys.
- [ ] Admin settings can edit tier policy limits.
- [ ] `cd backend && venv/bin/python -m pytest` exits 0.
- [ ] `cd frontend && npm test` exits 0.
- [ ] `cd frontend && npm run build` exits 0.
- [ ] `git diff --check` exits 0.
- [ ] `plans/README.md` row for Plan 002 is updated.

## STOP conditions

Stop and report back if:

- The four generation endpoints have been renamed or split, so the feature key
  mapping in this plan is no longer exact.
- The project now has a Free Stripe price/subscription implementation. This
  plan assumes Free remains off Stripe.
- Stripe subscription sync no longer has access to `current_period_start` and
  `current_period_end` in webhook/session payloads.
- Implementing safe quota reservation requires a background job, queue, Redis,
  or another dependency not already in the repo.
- The admin settings frontend has been replaced, making the UI instructions
  stale.
- A verification command fails twice after a reasonable fix attempt.
- The implementation needs files outside the in-scope list, except for
  narrowly required test fixture updates. Ask before expanding scope.

## Maintenance notes

- The app now owns quota state. Stripe should remain the source of paid billing
  state only.
- If Basic/Pro become finite later, update `feature_limit_policies`; do not add
  new hard-coded checks in endpoint files.
- If a process crashes after reserving usage but before releasing on failure,
  that attempt can consume quota. The current-cycle override endpoint is the
  operational correction path. If this becomes frequent, add an event-based
  reservation ledger in a separate plan.
- Reviewers should scrutinize transaction boundaries in
  `reserve_feature_usage`, especially concurrent requests against the same
  user/feature row.
- Reviewers should also verify policy changes do not mutate already-created
  cycle rows unless using the explicit current-cycle override endpoint.
