# Plan 001: Implement Stripe subscriptions and billing self-service

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 941b807..HEAD -- backend/requirements.txt backend/pyproject.toml backend/app/config.py backend/app/__init__.py backend/app/db/models.py backend/app/api/admin.py backend/app/api/predictions.py backend/app/api/markets.py backend/app/api/webhooks.py backend/app/services/swarm_orchestrator.py backend/migrations/versions backend/tests frontend/src/App.vue frontend/src/main.js frontend/src/lib frontend/src/router/index.js frontend/src/views .env.example README.md docs deploy/README.md`
>
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: L
- **Risk**: HIGH
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `941b807`, 2026-06-19
- **Execution status**: DONE on 2026-06-23. The Stripe migration `20260619_0004` was applied with `cd backend && venv/bin/python -m alembic upgrade head` against the configured test Supabase database after owner confirmation. Verification also passed with `cd backend && venv/bin/python -m pytest`, `cd frontend && npm test`, `cd frontend && npm run build`, docs/env grep, and `git diff --check`.

## Why this matters

SoccerOctopus currently protects app screens with Clerk sign-in, but it has no paid entitlement layer. Any signed-in user can run the expensive prediction pipeline, and the public markets API can run prediction-backed market generation without authentication. This plan adds a first Stripe Billing release with a public pricing page, authenticated Checkout subscription creation, verified webhook syncing, invoice/account self-service, and server-side access control for the two paid prediction tiers.

The intended product shape is three displayed tiers: Free, Basic at USD 5/month, and Pro at USD 10/month. Basic can run predictions without YouTube video analysis; Pro can run predictions with YouTube video analysis.

## Current state

- Root scripts live in `package.json`; there is no root test script.

```json
package.json:4-10
"scripts": {
  "setup": "cd frontend && npm install",
  "setup:backend": "cd backend && pip install -r requirements.txt",
  "setup:all": "npm run setup && npm run setup:backend",
  "frontend": "cd frontend && npm run dev",
  "backend": "cd backend && python run.py",
  "dev": "concurrently \"npm run backend\" \"npm run frontend\""
}
```

- Frontend scripts are Vite/Vitest only; there is no frontend typecheck or lint script.

```json
frontend/package.json:5-9
"scripts": {
  "dev": "vite",
  "build": "vite build",
  "preview": "vite preview",
  "test": "vitest run"
}
```

- Backend dependencies do not include Stripe yet.

```text
backend/requirements.txt:1-14
flask>=3.0
flask-cors>=4.0
flask-sqlalchemy>=3.1
sqlalchemy>=2.0
psycopg[binary]>=3.1
alembic>=1.13
openai>=1.30
requests>=2.31
python-dotenv>=1.0
svix>=1.29.0
pyjwt>=2.8
cryptography>=42.0
pytest>=8.2
zep-cloud==3.13.0
```

- Backend dependency metadata is duplicated in `backend/pyproject.toml`. Add Stripe there too, but do not reconcile unrelated existing differences between `requirements.txt` and `pyproject.toml` in this plan.

```toml
backend/pyproject.toml:6-21
dependencies = [
    "flask>=3.0",
    "flask-cors>=4.0",
    "flask-sqlalchemy>=3.1",
    "sqlalchemy>=2.0",
    "psycopg[binary]>=3.1",
    "alembic>=1.13",
    "openai>=1.30",
    "requests>=2.31",
    "python-dotenv>=1.0",
    "svix>=1.29.0",
    "pyjwt>=2.8",
    "cryptography>=42.0",
    "pytest>=8.2",
]
```

- Environment config currently contains Clerk and app runtime settings only. Add Stripe deployment secrets here, not in admin-managed `AppSettings`, because billing credentials should be deploy-time secrets.

```python
backend/app/config.py:80-95
DATABASE_URL: str = normalize_database_url(
    os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/socceroctupus",
    )
)
CLERK_SECRET_KEY: str = os.getenv("CLERK_SECRET_KEY", "")
CLERK_PUBLISHABLE_KEY: str = os.getenv("CLERK_PUBLISHABLE_KEY", "")
CLERK_JWKS_URL: str = os.getenv(
    "CLERK_JWKS_URL",
    "https://api.clerk.com/v1/jwks",
)
CLERK_JWKS_JSON: str = os.getenv("CLERK_JWKS_JSON", "")
CLERK_JWT_PUBLIC_KEY: str = _load_clerk_jwt_public_key()
CLERK_WEBHOOK_SECRET: str = os.getenv("CLERK_WEBHOOK_SECRET", "")
FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3001")
```

- `.env` is ignored by `.gitignore`, but the local `.env` contains live-looking `CLERK_SECRET_KEY`, `CLERK_WEBHOOK_SECRET`, and `DATABASE_URL` values at `.env:1`, `.env:3`, and `.env:4`. Do not print or copy those values. Rotate them before production billing setup if they were ever exposed outside the local machine.

```text
.gitignore:1-9
.env
__pycache__/
*.pyc
*.pyo
.venv/
node_modules/
backend/uploads/
backend/instance/
dist/
```

- The `User` model has auth/profile/admin fields only. There is no subscription state or Stripe customer/subscription identifier.

```python
backend/app/db/models.py:24-36
class User(db.Model, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    clerk_user_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(255), nullable=True)
    last_name = db.Column(db.String(255), nullable=True)
    avatar_url = db.Column(db.Text, nullable=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_sign_in_at = db.Column(db.DateTime(timezone=True), nullable=True)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
```

- `/api/me` is in `backend/app/api/admin.py` and returns user/admin state only. Extend this response with a nested `subscription` object instead of flattening billing fields into the top-level user payload.

```python
backend/app/api/admin.py:16-31
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
```

- Webhooks currently handle only Clerk lifecycle events under `/api/webhooks/clerk`. There is no Stripe signature verification, no event idempotency table, and an unused `import os` should be removed if the file is touched.

```python
backend/app/api/webhooks.py:12-33
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
        sync_user(identity, db, reactivate=True, overwrite_missing=True)
    elif event_type == "user.deleted":
        data = event.get("data", {})
        clerk_user_id = data.get("id")
        if clerk_user_id:
            deactivate_user(clerk_user_id, db)

    return jsonify({"status": "ok"}), 200
```

- Prediction routes require a signed-in user but do not require a paid subscription.

```python
backend/app/api/predictions.py:39-66
@bp.route("/match", methods=["POST"])
@require_user(db)
def predict_match():
    ...
    try:
        orc = _get_orchestrator()
        result = orc.predict_match(home, away, stage=stage, group=group)
        return jsonify(result.to_dict()), 200
    except Exception as exc:
        logger.error(f"Match prediction failed: {exc}")
        return jsonify({"error": str(exc)}), 500
```

- `SwarmOrchestrator` always includes `VideoAgent`, so there is no way to run the Basic tier without YouTube analysis.

```python
backend/app/services/swarm_orchestrator.py:63-72
self.agents = [
    StatisticalAgent(zep_tools=self.zep),          # ELO + Poisson (SofaScore)
    VideoAgent(settings=settings),                  # YouTube engagement
    FormAgent(zep_tools=self.zep),                 # last-10 form points
    TacticalAgent(llm_client=llm_client, zep_tools=self.zep),  # style matchup
    LiveDataAgent(zep_tools=self.zep),             # FotMob xG + FlashScore form
    MarketSignalsAgent(zep_tools=self.zep),        # 365Scores odds + Tiki-Taka AI
    SquadQualityAgent(settings=settings, zep_tools=self.zep),  # Opta player ratings + squad depth
]
```

- Markets routes are backend-public even though frontend `/markets` is protected. `match_markets()` and `tournament_markets()` both perform prediction/simulation work and must not remain a billing bypass.

```python
backend/app/api/markets.py:32-39
@bp.route("/match", methods=["POST"])
def match_markets():
    """
    POST /api/markets/match
    Body: { "home_team": "France", "away_team": "Argentina", "stage": "final" }
    Returns all prediction market questions for a single match.
    """
```

- Frontend route table has no pricing, billing, or checkout success routes.

```js
frontend/src/router/index.js:17-30
routes: [
  { path: '/', component: Home, meta: { public: true } },
  { path: '/groups', component: GroupsView, meta: { requiresAuth: true } },
  { path: '/predict', component: PredictView, meta: { requiresAuth: true } },
  { path: '/tournament', component: TournamentView, meta: { requiresAuth: true } },
  { path: '/markets', component: MarketsView, meta: { requiresAuth: true } },
  { path: '/profile', component: ProfileView, meta: { requiresAuth: true } },
  { path: '/admin/settings', component: AdminSettingsView, meta: { requiresAuth: true, admin: true } },
  { path: '/sign-in', component: SignInView, meta: { public: true } },
  { path: '/sign-up', component: SignUpView, meta: { public: true } },
  { path: '/forgot-password', component: ForgotPasswordView, meta: { public: true } },
  { path: '/sso-callback', component: SSOCallbackView, meta: { public: true } },
  { path: '/legal', component: LegalNoticeView, meta: { public: true } },
]
```

- Frontend auth guard hydrates auth state from `/api/me`; it can carry the new nested `subscription` object through `auth.state.user`.

```js
frontend/src/main.js:9-27
router.beforeEach(async (to) => {
  try {
    const res = await api.get('/api/me')
    setAuthState({ signedIn: true, isAdmin: res.data.is_admin, user: res.data })
    ...
    return true
  } catch {
    clearAuthState()
    if (to.meta.public) return true
    return { path: '/sign-in' }
  }
})
```

- Signed-in navbar has profile/admin links but no billing link. Signed-out navbar has no pricing link.

```vue
frontend/src/App.vue:28-41
<div v-if="userMenuOpen" class="user-dropdown" role="menu">
  <div class="user-summary">
    <strong>{{ userDisplayName }}</strong>
    <small>{{ auth.state.user?.email }}</small>
  </div>
  <router-link to="/profile" role="menuitem" @click="closeUserMenu">Profile</router-link>
  <button type="button" role="menuitem" @click="signOut">Sign Out</button>
</div>
...
<template v-else>
  <router-link to="/">Home</router-link>
  <router-link to="/sign-in">Sign In</router-link>
  <router-link to="/sign-up">Sign Up</router-link>
</template>
```

- Sign-in and sign-up always redirect to `/` after session activation. Add a safe post-auth redirect helper so an unauthenticated user can start on `/pricing`, create/sign into an account, and then be sent to Checkout.

```js
frontend/src/views/SignInView.vue:183-197
async function completeSignIn(result) {
  ...
  await activateSessionAndHydrateAuth({
    clerk,
    setActive: setActive.value,
    sessionId,
  })
  router.push('/')
}
```

```js
frontend/src/views/SignUpView.vue:128-140
async function completeSignUp(result) {
  ...
  await activateSessionAndHydrateAuth({
    clerk,
    setActive: setActive.value,
    sessionId: result.createdSessionId,
  })
  router.push('/')
}
```

- OAuth callback also forces `/`, so the post-auth redirect helper must account for OAuth.

```vue
frontend/src/views/SSOCallbackView.vue:8-15
<AuthenticateWithRedirectCallback
  sign-in-force-redirect-url="/"
  sign-up-force-redirect-url="/"
  sign-in-fallback-redirect-url="/"
  sign-up-fallback-redirect-url="/"
  sign-in-url="/sign-in"
  sign-up-url="/sign-up"
/>
```

- Backend tests use an in-memory SQLite database and monkeypatch auth. Add billing tests following this style.

```python
backend/tests/conftest.py:19-44
app = create_app(
    {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    }
)

with app.app_context():
    db.drop_all()
    db.create_all()
    db.session.add(
        AppSettings(
            scope="global",
            llm_base_url="https://api.openai.com/v1",
            llm_model_name="gpt-4o",
            zep_graph_id=None,
            opta_base_url="https://api.performfeeds.com/soccerdata",
            swarm_parallel_agents=7,
            swarm_timeout_seconds=60,
            mc_simulations=10000,
        )
    )
    db.session.commit()
    yield app
    db.session.remove()
    db.drop_all()
```

```python
backend/tests/test_auth_and_settings.py:145-149
def test_signed_in_user_can_access_me(client, user, monkeypatch):
    monkeypatch.setattr("app.auth.verify_session_token", lambda token: {"sub": token, "email": "user@example.com"})
    response = client.get("/api/me", headers=_auth_header(user["clerk_user_id"]))
    assert response.status_code == 200
    assert response.get_json()["email"] == "user@example.com"
```

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Install backend deps | `cd backend && pip install -r requirements.txt` | exit 0; `stripe` installed after this plan adds it |
| Install frontend deps | `cd frontend && npm install` | exit 0; lockfile updated only if package metadata changes |
| Run migrations | `cd backend && python3 -m alembic upgrade head` | exit 0; local configured database has new billing columns/tables |
| Backend tests | `cd backend && python3 -m pytest` | exit 0; all backend tests pass |
| Focused backend tests | `cd backend && python3 -m pytest tests/test_billing.py tests/test_auth_and_settings.py` | exit 0; billing/auth tests pass |
| Frontend tests | `cd frontend && npm test` | exit 0; Vitest suite passes |
| Frontend build | `cd frontend && npm run build` | exit 0; Vite build succeeds |
| Local app | `npm run dev` | frontend and backend dev servers start |

There is no dedicated backend lint/typecheck script and no frontend typecheck script in this repo at the time of planning.

## Suggested executor toolkit

- Stripe official docs:
  - Checkout subscription flow: `https://docs.stripe.com/billing/subscriptions/build-subscriptions`
  - Checkout Session create API: `https://docs.stripe.com/api/checkout/sessions/create`
  - Webhook signature verification: `https://docs.stripe.com/webhooks/signature`
  - Subscription webhook events: `https://docs.stripe.com/billing/subscriptions/webhooks`
  - Customer Portal: `https://docs.stripe.com/customer-management`
  - Invoice list API: `https://docs.stripe.com/api/invoices/list`
- Use the Stripe CLI manually for webhook smoke testing if it is available: `stripe listen --forward-to localhost:5002/api/webhooks/stripe`. Do not add the Stripe CLI as a project dependency.

## Scope

**In scope** (the only files you should modify):

- `backend/requirements.txt`
- `backend/pyproject.toml`
- `backend/app/config.py`
- `backend/app/__init__.py`
- `backend/app/db/models.py`
- `backend/app/api/admin.py`
- `backend/app/api/predictions.py`
- `backend/app/api/markets.py`
- `backend/app/api/webhooks.py`
- `backend/app/api/billing.py` (create)
- `backend/app/billing.py` (create)
- `backend/app/services/swarm_orchestrator.py`
- `backend/migrations/versions/20260619_0004_stripe_subscriptions.py` (create; keep next revision number if another migration already exists)
- `backend/tests/conftest.py`
- `backend/tests/test_billing.py` (create)
- `backend/tests/test_auth_and_settings.py`
- `.env.example`
- `README.md`
- `docs/auth-workflow.md` or a new `docs/billing-workflow.md` if that is cleaner
- `deploy/README.md`
- `frontend/src/lib/auth.js`
- `frontend/src/lib/api.js` only if a response helper is needed
- `frontend/src/lib/billing.js` (create)
- `frontend/src/lib/postAuthRedirect.js` (create)
- `frontend/src/main.js`
- `frontend/src/router/index.js`
- `frontend/src/router/index.test.js`
- `frontend/src/App.vue`
- `frontend/src/views/PricingView.vue` (create)
- `frontend/src/views/BillingView.vue` (create)
- `frontend/src/views/BillingSuccessView.vue` (create)
- `frontend/src/views/PricingView.test.js` (create)
- `frontend/src/views/BillingView.test.js` (create)
- `frontend/src/views/PredictView.vue`
- `frontend/src/views/MarketsView.vue` only to handle 402 subscription errors if needed
- `frontend/src/views/TournamentView.vue` only to handle 402 subscription errors if needed
- `frontend/src/views/SignInView.vue`
- `frontend/src/views/SignUpView.vue`
- `frontend/src/views/SSOCallbackView.vue`

**Out of scope** (do NOT touch, even though they look related):

- Do not commit or modify `.env`, `frontend/.env`, `backend/instance/settings-fernet.key`, or any live secret file.
- Do not commit changes to `backend/app.db`; schema changes must be represented by Alembic migrations and model changes.
- Do not replace Clerk auth or add a second auth provider.
- Do not move existing provider API keys from admin settings into environment variables.
- Do not implement direct card collection, direct invoice PDF generation, or direct payment-method update UI. Use Stripe-hosted Checkout and Customer Portal.
- Do not implement annual plans, coupons, trials, usage metering, team seats, tax calculation, or multi-currency pricing in this plan.
- Do not redesign the entire frontend. Match the existing dark card-based Vue style unless the owner starts a separate design task.

## Git workflow

- Branch: `codex/001-stripe-subscriptions`
- Commit style observed in recent history is short imperative sentence case, for example `Use silent JSON parsing; add empty-body test`.
- Commit per logical unit if you are committing: backend schema/service, backend gating/webhooks, frontend pricing/billing, docs/tests.
- Do not push or open a PR unless the operator explicitly instructs it.

## Implementation assumptions

- The third pricing tier is a Free tier with no Stripe checkout. Free users can sign in and browse non-execution account pages, but they cannot run prediction or market-generation endpoints.
- The two paid tiers are:
  - `basic`: USD 5/month, active subscription required, predictions run without YouTube `VideoAgent`.
  - `pro`: USD 10/month, active subscription required, predictions include YouTube `VideoAgent`.
- Admin users may bypass the paid prediction gate for operational testing, and admin predictions should include video analysis unless the request explicitly selects otherwise. If this is not acceptable to the product owner, stop before implementing Step 5.
- Upgrade, downgrade, and cancellation are handled through Stripe Customer Portal in this first release. The app owns Checkout creation, webhook syncing, invoice listing, and portal session creation. It does not directly call Stripe subscription update/cancel APIs from custom app UI.
- A user is entitled when `subscription_tier` is `basic` or `pro` and `subscription_status` is `active` or `trialing`. Do not grant paid access for `incomplete`, `incomplete_expired`, `canceled`, `unpaid`, or missing status. Treat `past_due` as not entitled for v1 unless the owner explicitly approves a grace policy.

## Steps

### Step 1: Add Stripe configuration, dependency, and secret documentation

1. Add `stripe>=10.0.0` to `backend/requirements.txt`.
2. Add the same `stripe>=10.0.0` dependency to `backend/pyproject.toml`. Keep the existing ordering style and do not make unrelated dependency cleanup.
3. Add these `Config` fields in `backend/app/config.py` near the existing Clerk/`FRONTEND_ORIGIN` fields:
   - `STRIPE_SECRET_KEY`
   - `STRIPE_WEBHOOK_SECRET`
   - `STRIPE_BASIC_PRICE_ID`
   - `STRIPE_PRO_PRICE_ID`
   - `STRIPE_BILLING_PORTAL_CONFIGURATION_ID` as optional; leave empty by default
4. Add placeholder-only entries to `.env.example`. Use empty values only:
   - `STRIPE_SECRET_KEY=`
   - `STRIPE_WEBHOOK_SECRET=`
   - `STRIPE_BASIC_PRICE_ID=`
   - `STRIPE_PRO_PRICE_ID=`
   - `STRIPE_BILLING_PORTAL_CONFIGURATION_ID=`
5. Update `README.md` and `deploy/README.md` environment sections with those Stripe variables and a note that:
   - Stripe secrets stay in deployment env, not `/admin/settings`.
   - Price IDs are not secret but should still be configured through env for each Stripe account.
   - The Stripe webhook endpoint will be `/api/webhooks/stripe`.
6. Add a short secret hygiene note to docs: `.env:1`, `.env:3`, and `.env:4` contain local auth/database secret types and should be rotated if exposed. Do not include values.

**Verify**: `cd backend && python3 -c "from app.config import Config; [getattr(Config, name) for name in ('STRIPE_SECRET_KEY','STRIPE_WEBHOOK_SECRET','STRIPE_BASIC_PRICE_ID','STRIPE_PRO_PRICE_ID','STRIPE_BILLING_PORTAL_CONFIGURATION_ID')]; print('stripe config ok')"` -> prints `stripe config ok`.

**Verify**: after installing backend dependencies, `cd backend && python3 -c "import stripe; print('stripe import ok')"` -> prints `stripe import ok`.

### Step 2: Add billing persistence and migration

1. Extend `User` in `backend/app/db/models.py` with nullable Stripe identifiers and local subscription state:
   - `stripe_customer_id = db.Column(db.String(255), unique=True, nullable=True, index=True)`
   - `stripe_subscription_id = db.Column(db.String(255), unique=True, nullable=True, index=True)`
   - `stripe_price_id = db.Column(db.String(255), nullable=True, index=True)`
   - `subscription_tier = db.Column(db.String(32), nullable=False, default="free", index=True)`
   - `subscription_status = db.Column(db.String(64), nullable=True, index=True)`
   - `subscription_current_period_end = db.Column(db.DateTime(timezone=True), nullable=True)`
   - `subscription_cancel_at_period_end = db.Column(db.Boolean, nullable=False, default=False)`
   - `subscription_synced_at = db.Column(db.DateTime(timezone=True), nullable=True)`
2. Add a new `StripeEvent` model for idempotency:
   - table name `stripe_events`
   - `id` integer primary key
   - `stripe_event_id` string, unique, indexed, not nullable
   - `event_type` string, not nullable
   - `processed_at` timezone datetime, nullable
   - inherit `TimestampMixin`
3. Create Alembic migration `backend/migrations/versions/20260619_0004_stripe_subscriptions.py`, with `down_revision` set to the current head `20260615_0003`.
4. Migration upgrade must add the user columns, indexes, and `stripe_events`. Server defaults should backfill existing rows:
   - `subscription_tier` server default `'free'`, then leave default in place or remove it after backfill; match the repo's migration style.
   - `subscription_cancel_at_period_end` server default false.
5. Migration downgrade must drop indexes/columns/table in reverse order.
6. Update `backend/tests/conftest.py` fixtures only if model construction requires new non-null values. Prefer model defaults so existing fixtures remain short.

**Verify**: `cd backend && python3 -m pytest tests/test_auth_and_settings.py` -> existing auth/settings tests pass against in-memory SQLite.

**Verify**: `cd backend && python3 -m alembic upgrade head` -> exits 0 against the configured local development database. If this points at a shared/staging/production database, STOP before running it.

### Step 3: Add billing service and account API

1. Create `backend/app/billing.py` with all subscription constants and Stripe-facing helpers. Keep Stripe calls isolated here so routes are thin and tests can monkeypatch a single module.
2. Define tier metadata in code:
   - `free`: label `Free`, amount `0`, interval `month`, features include `No paid prediction runs`, no price id.
   - `basic`: label `Basic`, amount `500`, display price `$5`, interval `month`, feature `Predictions without YouTube video analysis`, `includes_video_analysis=False`, price id from `Config.STRIPE_BASIC_PRICE_ID`.
   - `pro`: label `Pro`, amount `1000`, display price `$10`, interval `month`, feature `Predictions with YouTube video analysis`, `includes_video_analysis=True`, price id from `Config.STRIPE_PRO_PRICE_ID`.
3. In `backend/app/billing.py`, implement helpers:
   - `tier_for_price_id(price_id: str | None) -> str`, returning `basic`, `pro`, or `free`.
   - `serialize_subscription(user: User) -> dict`.
   - `is_paid_entitled(user: User) -> bool`.
   - `includes_video_analysis(user: User) -> bool`, true for Pro and admin bypass.
   - `ensure_stripe_configured()` that returns a JSON-safe error or raises a small custom exception when secret key or price ids are missing.
   - `ensure_customer(user: User, db_session) -> str`, creating a Stripe customer with `email`, `metadata.user_id`, and `metadata.clerk_user_id` when missing, then committing `stripe_customer_id`.
   - `create_checkout_session(user: User, tier: str) -> str`, returning the Stripe Checkout URL.
   - `create_portal_session(user: User, return_path: str = "/billing") -> str`, returning a Customer Portal URL.
   - `list_invoices(user: User, limit: int = 20) -> list[dict]`, returning only JSON-safe invoice fields.
   - `retrieve_checkout_session(session_id: str) -> dict`, expanding subscription enough to report status and sync if possible.
4. In `ensure_customer`, if the user already has `stripe_customer_id`, reuse it. If committing a newly created customer id hits an `IntegrityError`, roll back, reload the user, and reuse the existing local customer id instead of creating another local row or overwriting another user's customer id.
5. Use Stripe Checkout Session in subscription mode. Required fields:
   - `mode="subscription"`
   - `customer=<stripe_customer_id>`
   - `client_reference_id=str(user.id)`
   - `line_items=[{"price": price_id, "quantity": 1}]`
   - `success_url=f"{Config.FRONTEND_ORIGIN}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"`
   - `cancel_url=f"{Config.FRONTEND_ORIGIN}/pricing?checkout=cancelled&plan={tier}"`
   - `metadata={"user_id": str(user.id), "tier": tier}`
   - `subscription_data={"metadata": {"user_id": str(user.id), "tier": tier}}`
6. Create `backend/app/api/billing.py` with blueprint `bp = Blueprint("billing", __name__, url_prefix="/api/billing")`.
7. Add routes:
   - `GET /api/billing/plans`: public; returns all three tier objects. Do not return Stripe price ids because the frontend does not need them.
   - `POST /api/billing/checkout`: `@require_user(db)`; body `{ "tier": "basic" | "pro" }`; returns `{ "url": "https://checkout.stripe.com/..." }`; reject `free`, unknown tier, and missing config with 400.
   - `GET /api/billing/subscription`: `@require_user(db)`; returns `serialize_subscription(g.current_user)`.
   - `GET /api/billing/invoices`: `@require_user(db)`; returns `{ "invoices": [] }` when the user has no `stripe_customer_id`, otherwise returns a sanitized invoice list.
   - `POST /api/billing/portal`: `@require_user(db)`; returns `{ "url": "https://billing.stripe.com/..." }`. Accept optional `{ "return_path": "/billing" }` and sanitize it to local paths only.
   - `GET /api/billing/checkout-session/<session_id>`: `@require_user(db)`; retrieve the session and confirm it belongs to the current user by customer id, `client_reference_id`, or metadata before returning status. Return 403 or 404 without session details if it belongs to someone else. Do not return raw Stripe customer ids, subscription ids, or price ids.
8. Register the billing blueprint in `backend/app/__init__.py` next to admin/markets/predictions/webhooks.
9. Extend `backend/app/api/admin.py` `/api/me` to include:

```python
"subscription": serialize_subscription(user)
```

Do not include raw Stripe customer ids or subscription ids in `/api/me`.

**Verify**: `cd backend && python3 -m pytest tests/test_auth_and_settings.py` -> existing auth/settings tests pass, including updated `/api/me` expectations.

### Step 4: Add Stripe webhook verification and subscription sync

1. In `backend/app/billing.py`, implement `sync_subscription_from_stripe_subscription(subscription: dict, db_session) -> User | None`.
2. Sync logic:
   - Find the user by `stripe_customer_id`, `stripe_subscription_id`, `metadata.user_id`, or `metadata.clerk_user_id`, in that order.
   - Set `stripe_customer_id`, `stripe_subscription_id`, `stripe_price_id`, `subscription_tier`, `subscription_status`, `subscription_current_period_end`, `subscription_cancel_at_period_end`, and `subscription_synced_at`.
   - For canceled/deleted subscriptions, keep Stripe ids for audit but set `subscription_tier="free"`, `subscription_status="canceled"`, `subscription_cancel_at_period_end=False`, and clear `stripe_price_id` unless Stripe still provides a current price.
   - Convert Stripe Unix timestamps to timezone-aware UTC datetimes.
3. In `backend/app/api/webhooks.py`, add `POST /api/webhooks/stripe`:
   - Use `payload = request.get_data()` exactly once.
   - Read `Stripe-Signature` header.
   - Verify with `stripe.Webhook.construct_event(payload, sig_header, Config.STRIPE_WEBHOOK_SECRET)`.
   - Return 400 for bad signatures/payloads.
4. Add event idempotency:
   - Before processing, insert a `StripeEvent(stripe_event_id=event["id"], event_type=event["type"])`.
   - On unique constraint violation, roll back and return `{"status": "duplicate"}`, 200.
   - After successful processing, set `processed_at=utcnow()` and commit.
   - Keep event insertion, subscription sync, `processed_at`, and the final commit in one transaction. If processing raises, roll back so Stripe can retry the same event later.
   - Do not create app-visible side effects before the idempotency insert succeeds.
5. Handle these event types:
   - `checkout.session.completed`: retrieve expanded subscription if necessary, associate the user/customer, and sync.
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`: no invoice table required; if the invoice has a subscription id, retrieve and sync subscription.
   - `invoice.payment_failed`: retrieve and sync subscription when possible so status changes are reflected.
6. Unknown events should be stored as processed and return 200.
7. Do not trust plan/tier values from request bodies or the frontend. The canonical paid tier comes from the Stripe subscription price id mapped to env price ids.

**Verify**: Add backend tests in `backend/tests/test_billing.py` and run `cd backend && python3 -m pytest tests/test_billing.py` -> tests pass for valid signature handling via monkeypatch, duplicate event handling, checkout completion sync, subscription updated sync, and subscription deleted downgrade-to-free behavior.

### Step 5: Enforce paid entitlements and disable YouTube for Basic

1. Add an entitlement helper/decorator in `backend/app/billing.py`, for example `require_paid_subscription(db_session)`, or a simple route helper `billing_required_response(user)`. It must:
   - Assume `@require_user(db)` already loaded `g.current_user`.
   - Allow admins.
   - Allow paid users with `active` or `trialing` Basic/Pro subscriptions.
   - Return 402 with JSON:

```json
{
  "error": "Active subscription required",
  "code": "subscription_required",
  "plans_url": "/pricing"
}
```

2. Update `backend/app/services/swarm_orchestrator.py` constructor to accept `include_video_analysis: bool = True`.
3. Build `self.agents` so `VideoAgent(settings=settings)` is appended only when `include_video_analysis` is true. Keep the relative order of all other agents.
4. Update `backend/app/api/predictions.py`:
   - `_get_orchestrator(include_video_analysis: bool = True)`.
   - In `predict_match()`, after auth and validation, enforce billing before creating the orchestrator.
   - Pass `include_video_analysis=includes_video_analysis(g.current_user)`.
   - In `simulate_tournament()`, enforce billing for all tournament simulations. If `use_swarm` is true, pass the same video entitlement to the orchestrator. If `use_swarm` is false, still require a paid tier because it is a prediction product workflow.
   - Leave `/teams`, `/groups`, and admin graph endpoints as they are unless product owner explicitly wants them paid.
5. Update `backend/app/api/markets.py`:
   - Import `g`, `require_user`, and billing helpers.
   - Add `@require_user(db)` and billing enforcement to `match_markets()` and `tournament_markets()` because they generate prediction/market outputs.
   - Leave `GET /api/markets/types` public.
   - Make `_get_orc(include_video_analysis=True)` mirror predictions.
6. Add tests in `backend/tests/test_billing.py`:
   - Signed-in free user receives 402 from `/api/predictions/match`.
   - Active Basic user can call the route and the orchestrator receives `include_video_analysis=False`.
   - Active Pro user can call the route and the orchestrator receives `include_video_analysis=True`.
   - Free user receives 402 from `/api/markets/match`.
   - `SwarmOrchestrator(settings, include_video_analysis=False)` has no agent named `Video Intelligence Agent`.

**Verify**: `cd backend && python3 -m pytest tests/test_billing.py tests/test_auth_and_settings.py` -> billing and existing auth tests pass.

### Step 6: Add public pricing and authenticated Checkout flow

1. Create `frontend/src/lib/billing.js` with small API helpers:
   - `getPlans()`
   - `createCheckout(tier)`
   - `getSubscription()`
   - `getInvoices()`
   - `createPortalSession(payload)`
   - `getCheckoutSession(sessionId)`
2. Create `frontend/src/lib/postAuthRedirect.js`:
   - Store only local paths beginning with `/`.
   - Reject absolute URLs and protocol-relative URLs.
   - Provide `setPostAuthRedirect(path)`, `peekPostAuthRedirect()`, and `consumePostAuthRedirect()`.
3. Update `frontend/src/router/index.js`:
   - Import `PricingView`, `BillingView`, and `BillingSuccessView`.
   - Add `/pricing` as public.
   - Add `/billing` and `/billing/success` as authenticated.
4. Update `frontend/src/main.js`:
   - After successful `/api/me`, if current route is `/`, `/sign-in`, `/sign-up`, or `/sso-callback` and `peekPostAuthRedirect()` exists, return `consumePostAuthRedirect()`.
   - Keep admin route behavior unchanged.
5. Update `frontend/src/views/SignInView.vue` and `SignUpView.vue`:
   - After `activateSessionAndHydrateAuth`, route to `consumePostAuthRedirect() || '/'`.
   - For links between sign-in and sign-up, preserve relevant `plan` or `redirect` query if implemented.
6. Update Google OAuth flow:
   - Before calling Clerk Google auth from pricing-driven sign-in/sign-up, make sure the pending redirect is in local storage.
   - In both Google handlers, pass `redirectUrlComplete: peekPostAuthRedirect() || '/'` after importing the helper. Because `postAuthRedirect` stores only local paths, this remains a safe Clerk redirect target.
   - In `SSOCallbackView.vue`, replace the hardcoded force/fallback URLs with bound local values derived from `peekPostAuthRedirect() || '/'`, or keep `/` only if a new test proves the router guard reliably consumes the stored redirect after OAuth completion.
7. Create `frontend/src/views/PricingView.vue`:
   - Public page with three tier cards: Free, Basic `$5/month`, Pro `$10/month`.
   - Basic CTA:
     - if signed in, `createCheckout('basic')` then `window.location.assign(url)`;
     - if signed out, `setPostAuthRedirect('/pricing?plan=basic&checkout=1')` then route to `/sign-up`.
   - Pro CTA mirrors Basic with `pro`.
   - Free CTA signs up or returns to app; no checkout.
   - On mount, if signed in and route query has `checkout=1&plan=basic|pro`, call Checkout once and clear the query or guard against duplicate calls.
   - Handle backend 400 config errors and show concise error text.
   - Do not import Stripe.js or add frontend Stripe dependencies for this first release; the backend returns hosted Checkout/Portal URLs and the browser redirects to them.
8. Update `frontend/src/App.vue`:
   - Add Pricing link in signed-out nav.
   - Add Pricing link in signed-in nav or user dropdown.
   - Add Billing link in user dropdown for signed-in users.
9. Update `frontend/src/router/index.test.js` to assert:
   - `/pricing` is public.
   - `/billing` requires auth.
   - `/billing/success` requires auth.

**Verify**: `cd frontend && npm test` -> router tests and any new pricing tests pass.

### Step 7: Add billing account page, invoice view, portal flows, and success return

1. Create `frontend/src/views/BillingView.vue`:
   - Fetch `/api/billing/subscription` and `/api/billing/invoices`.
   - Show current tier, status, current period end, and cancel-at-period-end when present.
   - If no active paid subscription, show CTA to `/pricing`.
   - If active Basic, show buttons:
     - "Manage billing" -> `POST /api/billing/portal`
     - "Change plan" or "Upgrade to Pro" -> same portal endpoint for v1
     - "Cancel subscription" -> same portal endpoint for v1
   - If active Pro, show buttons:
     - "Manage billing"
     - "Change plan" or "Downgrade to Basic"
     - "Cancel subscription"
   - Render invoice rows with amount, status, date, and hosted invoice link when present. Do not embed invoice PDFs.
2. Create `frontend/src/views/BillingSuccessView.vue`:
   - Read `session_id` query param.
   - Call `GET /api/billing/checkout-session/<session_id>`.
   - Display processing state if webhook has not synced yet.
   - Include a link to `/billing`.
   - Refresh local auth state from `/api/me` after success so `auth.state.user.subscription` is current.
3. Update `frontend/src/views/PredictView.vue`, `MarketsView.vue`, and `TournamentView.vue` only as needed to handle 402 responses:
   - If response `code === 'subscription_required'`, show a short message and link to `/pricing`.
   - Preserve the existing generic error behavior for other errors.
4. Ensure account/billing flows use Stripe-hosted Portal for upgrade/downgrade/cancel. Do not implement custom subscription mutation in Vue.

**Verify**: `cd frontend && npm test` -> all frontend tests pass.

**Verify**: `cd frontend && npm run build` -> Vite build exits 0.

### Step 8: Add focused backend and frontend tests

Backend tests in `backend/tests/test_billing.py` should monkeypatch Stripe instead of making network calls:

- `GET /api/billing/plans` returns exactly `free`, `basic`, `pro`, and the paid tiers display `$5` and `$10`.
- `POST /api/billing/checkout` rejects unauthenticated requests with 401.
- Signed-in users can create Basic/Pro checkout when config is present; response includes a Stripe Checkout URL from the monkeypatch.
- Checkout creation rejects `free`.
- Checkout creation returns 400 when required Stripe config is missing.
- Portal creation rejects users without `stripe_customer_id`.
- Invoice listing returns an empty array for users without a Stripe customer id or a sanitized list for monkeypatched Stripe invoices.
- Stripe webhook rejects invalid signature with 400.
- Stripe webhook stores `stripe_events` and treats duplicates as 200 duplicate responses.
- Stripe subscription update maps `STRIPE_BASIC_PRICE_ID` to `basic` and `STRIPE_PRO_PRICE_ID` to `pro`.
- Deleted subscriptions downgrade to free.
- Prediction and markets entitlement tests listed in Step 5.

Frontend tests should follow existing Vitest style:

- Router metadata tests in `frontend/src/router/index.test.js`.
- Create `frontend/src/views/PricingView.test.js` with tests that clicking Basic while signed out stores a local post-auth redirect and routes to sign-up, and clicking Pro while signed in calls `api.post('/api/billing/checkout', { tier: 'pro' })`.
- Create `frontend/src/views/BillingView.test.js` with a test that invoice links render when returned by API, using `target="_blank"` and `rel="noopener"` or `rel="noreferrer"` on hosted invoice links.
- If the new tests require mocking `vue-router`, copy the project’s existing simple test style rather than introducing a new testing framework.

**Verify**: `cd backend && python3 -m pytest` -> all backend tests pass.

**Verify**: `cd frontend && npm test` -> all frontend tests pass.

### Step 9: Document Stripe setup and manual smoke test

1. Add or update docs with:
   - Stripe Dashboard setup: create products/prices for Basic USD 5 monthly and Pro USD 10 monthly.
   - Set `STRIPE_BASIC_PRICE_ID` and `STRIPE_PRO_PRICE_ID` from those recurring prices.
   - Enable Customer Portal plan changes and cancellation for the Basic/Pro products.
   - Add webhook endpoint: `<backend-origin>/api/webhooks/stripe`.
   - Subscribe webhook endpoint to: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, and `invoice.payment_failed`.
   - Set `STRIPE_WEBHOOK_SECRET` from that endpoint.
2. Add a local smoke test section:
   - Start app with `npm run dev`.
   - Start Stripe CLI forwarding if available: `stripe listen --forward-to localhost:5002/api/webhooks/stripe`.
   - Set test-mode Stripe env vars.
   - Visit `/pricing` signed out.
   - Choose Basic; sign up; confirm redirect to Stripe Checkout.
   - Complete Checkout with a Stripe test card.
   - Return to `/billing/success`, then `/billing`.
   - Run a prediction and confirm no `Video Intelligence Agent` appears in the agent breakdown.
   - Use Billing page portal to change to Pro.
   - Confirm webhook sync changes tier and a new prediction includes `Video Intelligence Agent`.
   - Use portal cancel flow and confirm local subscription becomes free after webhook.

**Verify**: `rg -n "STRIPE_SECRET_KEY|STRIPE_WEBHOOK_SECRET|STRIPE_BASIC_PRICE_ID|STRIPE_PRO_PRICE_ID" README.md deploy/README.md docs .env.example` -> placeholders/docs exist and no secret values are printed.

## Test plan

- Backend:
  - Add `backend/tests/test_billing.py` for Stripe config, checkout, portal, invoices, webhook verification/idempotency/sync, entitlement gating, and Basic-vs-Pro video agent behavior.
  - Update `backend/tests/test_auth_and_settings.py` for the new `/api/me.subscription` object while preserving existing auth/admin tests.
  - Run `cd backend && python3 -m pytest`.
- Frontend:
  - Update `frontend/src/router/index.test.js` for `/pricing`, `/billing`, and `/billing/success`.
  - Add focused tests for Pricing and Billing views using the `AdminSettingsView.test.js` mocking pattern.
  - Run `cd frontend && npm test`.
- Build:
  - Run `cd frontend && npm run build`.
- Manual Stripe smoke:
  - Use Stripe test mode and Stripe CLI forwarding. Never use live mode for initial verification.

## Done criteria

All must hold:

- [ ] `backend/requirements.txt` and `backend/pyproject.toml` include Stripe's Python SDK.
- [ ] `Config` exposes Stripe secret, webhook secret, and Basic/Pro price id env vars.
- [ ] `.env.example`, `README.md`, and deployment docs include placeholder Stripe env setup without secret values.
- [ ] Alembic migration adds user billing fields and `stripe_events`; `cd backend && python3 -m alembic upgrade head` succeeds against a local/dev database.
- [ ] `/api/billing/plans` returns Free, Basic `$5/month`, and Pro `$10/month`.
- [ ] Signed-in users can create Basic and Pro Checkout sessions; signed-out users cannot.
- [ ] `/api/webhooks/stripe` verifies Stripe signatures and is idempotent by Stripe event id.
- [ ] Webhooks sync checkout completion, subscription create/update/delete, payment success, and payment failure.
- [ ] `/api/me` returns a nested `subscription` object without raw Stripe ids.
- [ ] Free users receive 402 from endpoints that execute prediction or market-generation work.
- [ ] Basic users can run predictions and no `Video Intelligence Agent` runs or appears in results.
- [ ] Pro users can run predictions with `Video Intelligence Agent`.
- [ ] Markets endpoints that generate predictions are authenticated and subscription-gated; `/api/markets/types` can remain public.
- [ ] Public `/pricing` page displays three tiers and supports signed-out-to-sign-up-to-Checkout flow.
- [ ] `/billing` shows subscription status, invoice links, and opens Stripe Customer Portal for manage/change/cancel.
- [ ] `/billing/success` handles Stripe Checkout return and refreshes local subscription state.
- [ ] `cd backend && python3 -m pytest` exits 0.
- [ ] `cd frontend && npm test` exits 0.
- [ ] `cd frontend && npm run build` exits 0.
- [ ] No live secret file, `backend/app.db`, or file outside the in-scope list is modified.
- [ ] `plans/README.md` status row for this plan is updated.

## STOP conditions

Stop and report back instead of improvising if:

- The product owner intended three paid tiers, not Free + Basic + Pro.
- The product owner wants custom in-app upgrade/downgrade/cancel mutations instead of Stripe Customer Portal for v1.
- The owner does not want admins to bypass subscription checks.
- Existing `markets` backend routes are intentionally public despite performing prediction work.
- Stripe products/prices do not exist and the operator expects you to create them in Stripe Dashboard from this code task.
- The configured database for `alembic upgrade head` is not local/dev.
- Current code differs materially from the excerpts above.
- Implementing this requires changing Clerk auth architecture or storing Stripe secrets in admin-managed encrypted settings.
- A verification command fails twice after a reasonable fix attempt.

## Maintenance notes

- Stripe webhook delivery is at-least-once; keep the `stripe_events` idempotency table and avoid side effects before event insertion commits.
- Stripe price ids are the source of truth for tier mapping. If prices are replaced in Stripe, update env vars before users subscribe to the new prices.
- Customer Portal capabilities are configured in Stripe Dashboard. If plan change or cancellation buttons open a portal that does not allow those actions, fix the Portal configuration before changing app code.
- If the business later wants grace periods for `past_due`, change entitlement policy in one helper and add tests before enabling it.
- If new agents are added to `SwarmOrchestrator`, review Basic-tier exclusion rules so YouTube/video-derived analysis stays Pro-only.
- Rotate local credentials referenced by type at `.env:1`, `.env:3`, and `.env:4` if they were exposed during development or support.
