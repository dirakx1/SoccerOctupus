# Sign-In and Sign-Up Workflow

This app uses Clerk for identity and a local `users` table for app authorization.
The frontend keeps custom Vue auth screens instead of Clerk's prebuilt sign-in
and sign-up components.

## Key Files

| Area | File | Purpose |
|---|---|---|
| Frontend auth provider | `frontend/src/main.js` | Installs Clerk Vue with `VITE_CLERK_PUBLISHABLE_KEY` and protects routes. |
| Sign in UI | `frontend/src/views/SignInView.vue` | Custom email-or-username/password sign-in, MFA, Client Trust verification, and social auth flow. |
| Sign up UI | `frontend/src/views/SignUpView.vue` | Custom account creation with email, username, password policy, CAPTCHA mount, and email-code verification flow. |
| Password reset UI | `frontend/src/views/ForgotPasswordView.vue` | Custom email-code password reset flow with password-policy guidance. |
| OAuth callback | `frontend/src/views/SSOCallbackView.vue` | Handles social OAuth redirects from Clerk and routes incomplete username sign-ups to the continuation page. |
| Username continuation | `frontend/src/views/CompleteUsernameView.vue` | Completes Clerk-owned OAuth sign-ups that are missing the required username. |
| Session hydration | `frontend/src/lib/clerkSession.js` | Activates the Clerk session, fetches a token, calls `/api/me`, and updates local auth state. |
| Profile security UI | `frontend/src/components/TwoFactorSettings.vue` | Custom authenticator-app and backup-code management backed by Clerk user APIs. |
| API token injection | `frontend/src/App.vue` | Installs the Axios bearer-token interceptor from inside Vue setup. |
| Backend auth | `backend/app/auth.py` | Verifies Clerk JWTs, syncs local users, and provides auth decorators. |
| Webhook endpoint | `backend/app/api/webhooks.py` | Receives Clerk user lifecycle events and syncs the local `users` table. |
| Account API | `backend/app/api/admin.py` | Exposes `/api/me` and admin-only settings endpoints. |

## Required Clerk Settings

Configure these in the Clerk Dashboard:

- Email sign-up enabled.
- Email sign-in enabled.
- Username enabled for sign-up and sign-in. This app requires both email and
  username on custom sign-up, but username remains Clerk-owned and is not stored
  in the local database.
- Password authentication enabled.
- Email verification code enabled for sign-up.
- Password reset enabled with email verification code.
- Password policy configured in Clerk. Current target:
  - minimum length 8;
  - reject compromised passwords;
  - enforce strong password strength;
  - avoid mandatory lowercase/uppercase/number/special-character rules unless
    product/security explicitly accepts Clerk's NIST warning for those rules.
- Google, Facebook, and X enabled as SSO/social connections for sign-up and sign-in.
- Client Trust can be enabled; the custom sign-in flow supports `needs_client_trust`.
- MFA can be enabled; the custom sign-in flow supports `email_code`, `phone_code`, `totp`, and `backup_code` as second factors.
- Authenticator app and backup codes enabled for users that manage 2FA from the
  custom profile security UI.
- Clerk webhook endpoint points to `POST /api/webhooks/clerk`.

## Required Environment Variables

Backend:

```env
VITE_CLERK_PUBLISHABLE_KEY=pk_...
CLERK_SECRET_KEY=sk_...
CLERK_JWKS_URL=https://<your-clerk-domain>/.well-known/jwks.json
CLERK_JWKS_JSON=
CLERK_JWT_PUBLIC_KEY=
CLERK_WEBHOOK_SECRET=whsec_...
DATABASE_URL=postgresql://...
FRONTEND_ORIGIN=http://localhost:3001
```

The backend verifies bearer tokens with `CLERK_JWT_PUBLIC_KEY` first,
`CLERK_JWKS_JSON` second, and `CLERK_JWKS_URL` as the fallback. Use only one
local key option unless you are rotating keys. The frontend uses the public
`VITE_CLERK_PUBLISHABLE_KEY` at build/bootstrap time.

For `CLERK_JWT_PUBLIC_KEY`, the most portable `.env` format is a single line
with escaped line breaks:

```env
CLERK_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
```

Raw multiline PEM blocks are also supported in local `.env` files:

```env
CLERK_JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----
...
-----END PUBLIC KEY-----
```

## Sign-Up Workflow

1. User opens `/sign-up`.
2. `SignUpView.vue` shows the custom account form with first name, last name,
   email, username, password, and password-policy guidance.
3. The form includes `<div id="clerk-captcha" />`, which Clerk uses for bot
   protection in custom sign-up flows.
4. On submit, the page calls `signUp.create()` with:
   - `emailAddress`
   - `username`
   - `password`
   - optional `firstName`
   - optional `lastName`
5. If Clerk returns `complete`, the frontend activates the created session.
6. If Clerk requires email verification, the frontend calls
   `prepareEmailAddressVerification({ strategy: 'email_code' })`.
7. User enters the email verification code.
8. The frontend calls `attemptEmailAddressVerification({ code })`.
9. When Clerk returns `complete`, `activateSessionAndHydrateAuth()`:
   - calls `setActive({ session })`
   - waits for a usable Clerk token
   - calls `/api/me` with `Authorization: Bearer <token>`
   - stores `signedIn`, `isAdmin`, and user details in local auth state
   - redirects to `/`

## Social OAuth Workflow

1. User selects `Continue with Google`, `Continue with Facebook`, or
   `Continue with X` on `/sign-in` or `/sign-up`.
2. The frontend calls `authenticateWithRedirect()` with:
   - `strategy: 'oauth_google'`, `oauth_facebook`, or `oauth_x`
   - `redirectUrl: '/sso-callback'`
   - `redirectUrlComplete: '/'`
3. Clerk redirects the browser through the provider's OAuth consent flow.
4. The provider returns to `/sso-callback`.
5. `SSOCallbackView.vue` renders `AuthenticateWithRedirectCallback`, which lets
   Clerk finish the OAuth flow, activate the session, and return to `/`.
6. If Clerk reports an incomplete sign-up because username is required,
   `continueSignUpUrl` sends the browser to `/complete-username`, where the
   custom UI calls `signUp.update({ username })`. Username remains Clerk-owned.
7. The existing router guard calls `/api/me`, which verifies the Clerk session
   token, syncs the local `users` row if needed, and updates local auth state.

## Sign-In Workflow

1. User opens `/sign-in`.
2. `SignInView.vue` shows the custom email-or-username/password form.
3. On submit, the page calls `signIn.create()` with:
   - `strategy: 'password'`
   - `identifier: form.identifier`
   - `password: form.password`
4. The result is passed to `handleSignInResult()`.
5. If Clerk already has a `createdSessionId` or returns `status === 'complete'`,
   the frontend activates the session through `activateSessionAndHydrateAuth()`.
6. If Clerk returns `needs_first_factor` with a password factor, the frontend
   attempts the password first factor with `attemptFirstFactor()`.
7. If Clerk returns `needs_second_factor`, the frontend selects a supported
   second factor and shows the custom verification form.
8. User enters the verification code.
9. The frontend calls `attemptSecondFactor()` or `attemptFirstFactor()` depending
   on the active stage.
10. When Clerk returns a created session, the frontend activates the session and
    redirects to `/`.

## Profile Security Workflow

1. User opens `/profile`.
2. `ProfileView.vue` renders `TwoFactorSettings.vue` in the Security section.
3. The component reads Clerk user flags:
   - `totpEnabled`
   - `backupCodeEnabled`
   - `twoFactorEnabled`
4. To enable authenticator-app 2FA, the component calls `user.createTOTP()`,
   displays the Clerk-provided secret and URI, and asks for an authenticator code.
5. On verification, it calls `user.verifyTOTP({ code })` and then
   `user.createBackupCode()` when backup codes are not returned by TOTP verify.
6. Backup codes are shown once with copy/download actions and cleared from
   component state after the user confirms they saved them.
7. Regeneration calls `user.createBackupCode()` and again shows codes once.
8. Disabling authenticator-app 2FA calls `user.disableTOTP()` and relies on
   Clerk for any reverification or security errors.

## Password Reset Workflow

1. User opens `/forgot-password` from the sign-in page.
2. `ForgotPasswordView.vue` asks for the account email address.
3. The frontend calls `signIn.create()` with:
   - `strategy: 'reset_password_email_code'`
   - `identifier: form.email`
4. Clerk sends an email verification code.
5. User enters the code and a new password.
6. The frontend calls `attemptFirstFactor()` with:
   - `strategy: 'reset_password_email_code'`
   - `code`
   - `password`
7. If Clerk returns `complete`, the frontend activates the new session through
   `activateSessionAndHydrateAuth()` and redirects to `/`.
8. If Clerk requires a second factor after reset, the frontend sends the user
   back to `/sign-in` so the existing sign-in MFA flow can complete access.

## Client Trust Workflow

Client Trust can return `needs_client_trust` when a valid password is used from
a new device. The custom sign-in page handles it as a code-based second factor.

1. Clerk returns `status === 'needs_client_trust'`.
2. The frontend looks for `email_code` or `phone_code` in
   `supportedSecondFactors`.
3. The frontend calls `prepareSecondFactor()` to send the code.
4. The UI changes to a custom verification-code form with copy explaining that
   this device needs one more verification.
5. User enters the code.
6. The frontend calls `attemptSecondFactor()`.
7. On success, the session is activated and the user is redirected to `/`.

## Supported Verification Methods

The custom sign-in flow supports:

- `email_code` as first or second factor.
- `phone_code` as first or second factor.
- `totp` as second factor.
- `backup_code` as second factor.
- `password` as first factor.
- `needs_client_trust` through email or phone code.
- Password reset through `reset_password_email_code`.

The custom sign-up flow supports:

- Email/password account creation.
- Google OAuth sign-up through Clerk's `oauth_google` strategy.
- Clerk CAPTCHA/bot protection through `#clerk-captcha`.
- Email verification through `email_code`.

Unsupported methods intentionally produce a visible error that names the Clerk
strategy returned by the API.

## Session Hydration

`activateSessionAndHydrateAuth()` exists because the app needs both Clerk session
state and local backend authorization state.

The helper:

1. Calls `setActive({ session: sessionId })`.
2. Polls Clerk client sessions until a token is available.
3. Calls `/api/me` with an explicit bearer token.
4. Updates local auth state with backend user data.

This avoids redirecting into protected app routes before the backend can verify
the new Clerk session.

## Frontend Route and Token Flow

The router guard in `frontend/src/main.js` calls `/api/me` before protected
routes. If `/api/me` succeeds:

- local auth state is set to signed in
- signed-in users are redirected away from `/sign-in` and `/sign-up`
- non-admin users are redirected away from admin routes

If `/api/me` fails:

- local auth state is cleared
- public routes are allowed
- protected routes redirect to `/sign-in`

`App.vue` installs the Axios auth interceptor from inside Vue setup, where Clerk
composables are valid. This keeps bearer-token injection in a valid Clerk/Vue
context.

## Backend User Sync

The local `users` table is used for app authorization, especially `is_admin` and
`is_active`. Clerk remains the identity source of truth. Username, password
policy, social providers, authenticator-app 2FA, and backup codes are Clerk
owned; the local app continues to use `clerk_user_id` after authentication.

There are two sync paths:

1. Clerk webhook events call `sync_user()` from `POST /api/webhooks/clerk`.
2. Authenticated API requests call `/api/me`, which verifies the session token
   and lazily calls `sync_user()`.

Both paths are intentional:

- Webhooks keep local user data in sync over time.
- Lazy sync lets first login work even if webhook delivery is delayed.

`sync_user()` is idempotent and race-safe:

- It first looks up by `clerk_user_id`.
- If no row exists, it inserts one.
- If a webhook or another request inserts first, it catches the duplicate-key
  `IntegrityError`, rolls back, reloads by `clerk_user_id`, and updates the row.
- Lazy session sync uses `overwrite_missing=False` so missing token claims do not
  erase richer webhook data.
- Webhook sync uses `overwrite_missing=True` because webhook payloads are the
  authoritative profile sync source.
- If a lazy sync has no email claim, it uses a per-user placeholder email like
  `user_xxx@pending.clerk.local` until the webhook provides the real address.

## Webhook Workflow

`POST /api/webhooks/clerk` handles:

- `user.created`: creates or updates the local user.
- `user.updated`: updates local profile fields while preserving app-owned flags
  such as `is_admin`.
- `user.deleted`: deactivates the local user instead of hard-deleting it.

Webhook requests are verified with `CLERK_WEBHOOK_SECRET` through Svix before any
database mutation occurs.

## Admin Bootstrap

New users are created with `is_admin = false`. To create the first admin:

1. Sign up and complete verification.
2. Confirm the user exists in the local `users` table.
3. Promote the user manually:

```sql
UPDATE users SET is_admin = true WHERE email = '<admin-email>';
```

After this, the admin can access `/admin/settings`.

## Runtime Settings

After first-admin bootstrap, LLM, Zep, YouTube, Opta, provider endpoint URLs, swarm, and Monte Carlo settings are managed in `/admin/settings`, not deployment env. Provider API keys are write-only in the admin API, stored encrypted in the database, and reported to the frontend only as configured/not-configured booleans.

The encryption root key is stored outside the database at `backend/instance/settings-fernet.key` for local and single-host deployments. Production must persist and back up that file, or provide an equivalent persistent secret-file/KMS-backed mount, before storing API keys. If the root key is lost, previously encrypted API keys cannot be decrypted and must be re-entered.

## Troubleshooting

### `This sign-in requires a verification method that is not enabled on this page`

This means Clerk returned a factor the custom page did not handle. The current
sign-in page supports common password, code, TOTP, backup-code, and Client Trust
paths. Check the error for the exact unsupported strategy.

### `Unable to complete sign-in from Clerk status: needs_client_trust`

The custom flow must handle Client Trust. The current implementation does this
by sending an email or phone second-factor code. If this appears again, inspect
`supportedSecondFactors` in the Clerk response.

### Duplicate `users_clerk_user_id_key`

This happens when webhook sync and lazy `/api/me` sync race to insert the same
Clerk user. `sync_user()` is now designed to catch this duplicate insert, reload
the existing row, and update it safely.

### Empty user email after sign-up

Clerk session tokens may not include email claims immediately. Lazy sync uses a
temporary `@pending.clerk.local` placeholder when no email is available. The
webhook should replace it with the real email from Clerk.

### CAPTCHA errors on sign-up

Make sure the custom sign-up form contains `<div id="clerk-captcha" />` and that
the Clerk publishable key is configured correctly in the backend environment.

### Protected API requests missing bearer token

The Axios interceptor must be installed from a valid Vue setup context. In this
app, `App.vue` owns that setup. Do not move Clerk composables into module scope
or router bootstrap code.

## Verification Checklist

Run these checks after auth changes:

```bash
cd frontend
npm run build
npm test
```

```bash
cd backend
python3 -m pytest tests/test_auth_and_settings.py
```

Manual smoke test:

1. Sign up with a new email/password.
2. Complete CAPTCHA if shown.
3. Verify email code.
4. Confirm `/api/me` returns the local user.
5. Sign out.
6. Sign in from a new browser/device.
7. Complete Client Trust verification if prompted.
8. Confirm protected routes load.
9. Promote a test user to admin and confirm `/admin/settings` loads.
