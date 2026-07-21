# Plan 005: Add custom Clerk username, password-policy, social-login, and 2FA security flows

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report - do not improvise. When done, update the status row for this plan
> in `plans/README.md` - unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 8af5228..HEAD -- frontend/src/views/SignInView.vue frontend/src/views/SignUpView.vue frontend/src/views/ForgotPasswordView.vue frontend/src/views/ProfileView.vue frontend/src/views/SSOCallbackView.vue frontend/src/views/CompleteUsernameView.vue frontend/src/router/index.js frontend/src/lib/clerkSession.js frontend/src/composables/useCurrentUserProfile.js frontend/src/composables/usePasswordPolicy.js frontend/src/components/PasswordPolicyChecklist.vue frontend/src/components/SocialAuthButtons.vue frontend/src/components/TwoFactorSettings.vue frontend/src/views/ProfileView.test.js frontend/src/router/index.test.js frontend/src/views/SignUpView.test.js frontend/src/views/SignInView.test.js frontend/src/views/ForgotPasswordView.test.js frontend/src/components/PasswordPolicyChecklist.test.js frontend/src/components/TwoFactorSettings.test.js docs/auth-workflow.md README.md`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: L
- **Risk**: MED
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `8af5228`, 2026-07-04

## Why this matters

The app already uses Clerk as the identity authority, but its custom Vue auth
screens only expose email/password plus Google OAuth. The product decision is
to keep the custom UI while adding username sign-up/sign-in, Facebook and X
OAuth, visible password-policy feedback, and user-managed authenticator-app 2FA
with one-time backup codes. This plan keeps Clerk as the source of truth:
username, passwords, TOTP, and backup codes must remain Clerk-owned, while the
local database continues to use `clerk_user_id` for app authorization.

## Current state

Relevant files and roles:

- `frontend/src/views/SignInView.vue` - custom sign-in page, password sign-in,
  OAuth redirect, second-factor prompts, session activation.
- `frontend/src/views/SignUpView.vue` - custom sign-up page, CAPTCHA mount,
  email verification, OAuth redirect.
- `frontend/src/views/ForgotPasswordView.vue` - custom password reset with
  email-code verification.
- `frontend/src/views/ProfileView.vue` - profile, password change, and billing
  UI. This is where the custom security section should live.
- `frontend/src/views/SSOCallbackView.vue` - current OAuth callback wrapper.
- `frontend/src/router/index.js` - lazy route table and local route guards.
- `frontend/src/composables/useCurrentUserProfile.js` - exposes Clerk-derived
  profile fields without local username storage.
- `docs/auth-workflow.md` and `README.md` - current Clerk setup docs.

Current sign-in is email-only and has a single Google OAuth button:

```vue
<!-- frontend/src/views/SignInView.vue:8-29 -->
<form v-if="step === 'credentials'" class="auth-form" @submit.prevent="submit">
  <button class="btn-google" type="button" @click="signInWithGoogle">
    <span class="google-mark" aria-hidden="true">G</span>
    {{ googleLoading ? 'Opening Google...' : 'Continue with Google' }}
  </button>

  <div class="auth-divider"><span>or use email</span></div>

  <label class="field">
    <span>Email address</span>
    <input v-model.trim="form.email" type="email" autocomplete="email" required />
  </label>
```

```js
// frontend/src/views/SignInView.vue:116-123
const form = reactive({
  email: '',
  password: '',
  code: '',
})

const codeStrategies = ['email_code', 'phone_code']
const supportedSecondFactorStrategies = ['totp', 'email_code', 'phone_code', 'backup_code']
```

```js
// frontend/src/views/SignInView.vue:313-317
const result = await signIn.value.create({
  strategy: 'password',
  identifier: form.email,
  password: form.password,
})
```

Existing sign-in already supports TOTP and backup-code prompts after Clerk
requests a second factor:

```js
// frontend/src/views/SignInView.vue:262-275
if (currentSignIn?.status === 'needs_second_factor') {
  const secondFactors = currentSignIn.supportedSecondFactors || []
  const secondFactor = findFactor(secondFactors, supportedSecondFactorStrategies)

  if (codeStrategies.includes(secondFactor.strategy)) {
    await prepareCodeVerification('second', secondFactor)
  } else {
    prepareLocalVerification('second', secondFactor)
  }
}
```

Current sign-up collects email and password, not username:

```vue
<!-- frontend/src/views/SignUpView.vue:33-54 -->
<label class="field">
  <span>Email address</span>
  <input v-model.trim="form.email" type="email" autocomplete="email" required />
</label>

<label class="field">
  <span>Password</span>
  <input
    v-model="form.password"
    type="password"
    autocomplete="new-password"
    required
    minlength="8"
  />
</label>
```

```js
// frontend/src/views/SignUpView.vue:117-123
const form = reactive({
  firstName: '',
  lastName: '',
  email: '',
  password: '',
  code: '',
})
```

```js
// frontend/src/views/SignUpView.vue:178-183
const result = await signUp.value.create({
  emailAddress: form.email,
  password: form.password,
  firstName: form.firstName || undefined,
  lastName: form.lastName || undefined,
})
```

Current reset and profile password forms only enforce a local minimum length:

```vue
<!-- frontend/src/views/ForgotPasswordView.vue:44-53 -->
<label class="field">
  <span>New password</span>
  <input v-model="form.password" type="password" autocomplete="new-password" required minlength="8" />
</label>
```

```js
// frontend/src/views/ProfileView.vue:294-312
function validatePasswordForm() {
  if (!passwordForm.currentPassword) return 'Enter your current password.'
  if (passwordForm.newPassword.length < 8) return 'New password must be at least 8 characters.'
  if (passwordForm.newPassword !== passwordForm.confirmPassword) return 'New passwords do not match.'
  if (passwordForm.currentPassword === passwordForm.newPassword) return 'New password must be different from your current password.'
  return ''
}
```

Current profile UI has personal details, password, and billing sections. There
is no security/2FA management UI:

```vue
<!-- frontend/src/views/ProfileView.vue:45-96 -->
<section class="profile-card">
  <h2>Change password</h2>
  ...
</section>
</div>

<section class="profile-card billing-card">
  <div class="billing-row">
    <h2>Billing</h2>
```

Current OAuth callback copy is Google-specific and does not route incomplete
sign-ups to a username-completion page:

```vue
<!-- frontend/src/views/SSOCallbackView.vue:5-15 -->
<h1>Completing sign-in</h1>
<p class="subtitle">Securely finishing your Google authentication.</p>

<AuthenticateWithRedirectCallback
  :sign-in-force-redirect-url="redirectTarget"
  :sign-up-force-redirect-url="redirectTarget"
  sign-in-url="/sign-in"
  sign-up-url="/sign-up"
/>
```

Current router has no username-completion route and only redirects signed-in
users away from sign-in/sign-up:

```js
// frontend/src/router/index.js:17-20
{ path: '/sign-in', component: () => import('../views/SignInView.vue'), meta: { public: true } },
{ path: '/sign-up', component: () => import('../views/SignUpView.vue'), meta: { public: true } },
{ path: '/forgot-password', component: () => import('../views/ForgotPasswordView.vue'), meta: { public: true } },
{ path: '/sso-callback', component: () => import('../views/SSOCallbackView.vue'), meta: { public: true } },
```

The local user mirror is intentionally keyed by Clerk ID and has no username
field:

```js
// frontend/src/composables/useCurrentUserProfile.js:18-24
const email = computed(() => {
  return user.value?.primaryEmailAddress?.emailAddress || auth.state.user?.email || ''
})

const avatarUrl = computed(() => {
  return user.value?.imageUrl || auth.state.user?.avatar_url || ''
})
```

```python
# backend/app/db/models.py:28-33, found by rg during recon
clerk_user_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
is_admin = db.Column(db.Boolean, nullable=False, default=False)
```

Installed Clerk SDK type facts to use:

```ts
// frontend/node_modules/@clerk/shared/dist/types/index.d.ts:2966-2977
type PasswordSettingsData = {
  allowed_special_characters: string;
  disable_hibp: boolean;
  min_length: number;
  max_length: number;
  require_special_char: boolean;
  require_numbers: boolean;
  require_uppercase: boolean;
  require_lowercase: boolean;
  show_zxcvbn: boolean;
  min_zxcvbn_strength: number;
};
```

```ts
// frontend/node_modules/@clerk/shared/dist/types/index.d.ts:3016-3031
interface UserSettingsResource extends ClerkResource {
  passwordSettings: PasswordSettingsData;
  usernameSettings: UsernameSettingsData;
  socialProviderStrategies: OAuthStrategy[];
  authenticatableSocialStrategies: OAuthStrategy[];
}
```

```ts
// frontend/node_modules/@clerk/shared/dist/types/index.d.ts:3054-3061
type PasswordValidation = {
  complexity?: ComplexityErrors;
  strength?: PasswordStrength;
};
type ValidatePasswordCallbacks = {
  onValidation?: (res: PasswordValidation) => void;
  onValidationComplexity?: (b: boolean) => void;
};
```

```ts
// frontend/node_modules/@clerk/shared/dist/types/index.d.ts:3810 and 6316
validatePassword: (password: string, callbacks?: ValidatePasswordCallbacks) => void;
```

```ts
// frontend/node_modules/@clerk/shared/dist/types/index.d.ts:2074-2133
interface UserResource extends ClerkResource {
  username: string | null;
  passwordEnabled: boolean;
  totpEnabled: boolean;
  backupCodeEnabled: boolean;
  twoFactorEnabled: boolean;
  updatePassword: (params: UpdateUserPasswordParams) => Promise<UserResource>;
  createTOTP: () => Promise<TOTPResource>;
  verifyTOTP: (params: VerifyTOTPParams) => Promise<TOTPResource>;
  disableTOTP: () => Promise<DeletedObjectResource>;
  createBackupCode: () => Promise<BackupCodeResource>;
}
```

```ts
// frontend/node_modules/@clerk/shared/dist/types/index.d.ts:1759-1764 and 1955-1963
interface BackupCodeResource extends ClerkResource {
  codes: string[];
}
interface TOTPResource extends ClerkResource {
  secret?: string;
  uri?: string;
  verified: boolean;
  backupCodes?: string[];
}
```

```ts
// frontend/node_modules/@clerk/shared/dist/types/index.d.ts:3845 and 6090-6114
type SignUpStatus = 'missing_requirements' | 'complete' | 'abandoned';
readonly missingFields: SignUpField[];
readonly username: string | null;
```

```ts
// frontend/node_modules/@clerk/shared/dist/types/index.d.ts:9000-9027
type HandleOAuthCallbackParams = ... & {
  signInUrl?: string;
  signUpUrl?: string;
  continueSignUpUrl?: string | null;
}
```

`frontend/node_modules/@clerk/shared/dist/runtime/oauth.mjs` contains
`oauth_facebook` and `oauth_x`, so the provider strategies to expose are
`oauth_google`, `oauth_facebook`, and `oauth_x`.

Repo conventions to match:

- Frontend code uses Vue 3 single-file components with `<script setup>`,
  Composition API refs/reactive state, and scoped CSS.
- Routes are lazy-loaded in `frontend/src/router/index.js`.
- Auth errors use helpers that prefer Clerk long messages:
  `err?.errors?.[0]?.longMessage || err?.errors?.[0]?.message || err?.message`.
- Tests use Vitest and Vue Test Utils. `ProfileView.test.js` uses `vi.hoisted`
  for Clerk mocks and `flushPromises()` after async UI work.

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Inspect Clerk SDK facts | `rg -n "createTOTP|createBackupCode|validatePassword|PasswordSettingsData|continueSignUpUrl|oauth_facebook|oauth_x" frontend/node_modules/@clerk/shared/dist frontend/node_modules/@clerk/vue/dist` | matching lines for the APIs in this plan |
| Frontend targeted tests | `cd frontend && npm test -- SignInView SignUpView ForgotPasswordView PasswordPolicyChecklist TwoFactorSettings ProfileView router/index` | exit 0, all matching Vitest tests pass |
| Frontend all tests | `cd frontend && npm test` | exit 0, all Vitest tests pass |
| Frontend build | `cd frontend && npm run build` | exit 0, Vite build succeeds |
| Scope check | `git diff --name-only` | only in-scope files from this plan plus `plans/README.md` |

There is no dependency install step in this plan. Do not add a QR-code package
or any other frontend dependency in this slice. Render the TOTP setup with
Clerk's `secret`/`uri`, copy controls, and an "open in authenticator app" link.

## Suggested executor toolkit

- If available, use the `clerk-custom-ui` skill for custom Clerk flow details.
- If available, use the `clerk` skill only to validate Clerk API semantics. Do
  not use it to change the live Clerk instance from this repo task.

## Scope

**In scope** - the only source/docs files you should modify:

- `frontend/src/views/SignInView.vue`
- `frontend/src/views/SignUpView.vue`
- `frontend/src/views/ForgotPasswordView.vue`
- `frontend/src/views/ProfileView.vue`
- `frontend/src/views/SSOCallbackView.vue`
- `frontend/src/views/CompleteUsernameView.vue` (create if OAuth missing-username handling requires a custom continuation page)
- `frontend/src/router/index.js`
- `frontend/src/composables/useCurrentUserProfile.js` (only if needed to expose read-only Clerk username to the profile/security UI)
- `frontend/src/composables/usePasswordPolicy.js` (create)
- `frontend/src/components/PasswordPolicyChecklist.vue` (create)
- `frontend/src/components/SocialAuthButtons.vue` (create)
- `frontend/src/components/TwoFactorSettings.vue` (create)
- `frontend/src/views/ProfileView.test.js`
- `frontend/src/router/index.test.js`
- `frontend/src/views/SignUpView.test.js` (create if absent)
- `frontend/src/views/SignInView.test.js` (create if absent)
- `frontend/src/views/ForgotPasswordView.test.js` (create if absent)
- `frontend/src/components/PasswordPolicyChecklist.test.js` (create if absent)
- `frontend/src/components/TwoFactorSettings.test.js` (create if absent)
- `docs/auth-workflow.md`
- `README.md`

**Out of scope** - do NOT touch:

- Backend models, migrations, API routes, auth decorators, or webhooks.
- Any local database username field. Username is auth-only and Clerk-owned.
- Any admin-specific 2FA enforcement. The owner explicitly rejected extra admin
  requirements for this slice.
- Phone/SMS/email 2FA enrollment management. Sign-in may continue to handle
  those if Clerk requests them, but this plan only adds authenticator-app and
  backup-code management.
- Clerk prebuilt `UserProfile` or `TaskSetupMFA` as the primary account
  security UI. The requested UI is custom.
- Dependency changes in `frontend/package.json` or `frontend/package-lock.json`.
- Billing/subscription behavior.

## Git workflow

- Branch: `codex/005-custom-clerk-auth-security`
- Commit per logical unit if the operator asks you to commit. Match the repo's
  terse history style, for example `Adding about link`.
- Do not push or open a PR unless the operator explicitly instructs it.

## Steps

### Step 1: Verify Clerk runtime shapes before editing

Confirm the installed SDK supports the APIs this plan relies on:

1. Run the SDK inspection command from "Commands you will need".
2. Inspect `frontend/node_modules/@clerk/vue/dist/index.js` around the
   `AuthenticateWithRedirectCallback` implementation. It currently calls
   `clerk.handleRedirectCallback(props)`, so `continue-sign-up-url` can be
   passed as a prop if the Vue wrapper exposes it.
3. Inspect the runtime Clerk object shape in existing app code before using
   dynamic password settings. The type only proves `EnvironmentResource` has
   `userSettings`; the executor must find the actual runtime path exposed by
   this SDK. Prefer a public path such as `clerk.value.environment.userSettings`
   if available. If only an internal path is available, isolate it in
   `usePasswordPolicy.js` and keep a fallback.

**Verify**: `rg -n "handleRedirectCallback|continueSignUpUrl|PasswordSettingsData|createTOTP|createBackupCode|oauth_facebook|oauth_x" frontend/node_modules/@clerk/shared/dist/types/index.d.ts frontend/node_modules/@clerk/vue/dist/index.js frontend/node_modules/@clerk/shared/dist/runtime/oauth.mjs` -> matching lines for each API.

### Step 2: Add reusable password-policy display and validation

Create `frontend/src/composables/usePasswordPolicy.js` and
`frontend/src/components/PasswordPolicyChecklist.vue`.

Target behavior:

- Dynamically mirror Clerk password settings when the frontend can read them:
  minimum length, maximum length, required lowercase/uppercase/number/special
  flags, allowed special characters, zxcvbn strength settings, and HIBP
  compromise rejection status.
- Use `signUp.value.validatePassword` on sign-up and `signIn.value.validatePassword`
  on reset/profile if available. The callback shape is documented in the
  installed types as `onValidation(res)` and `onValidationComplexity(b)`.
- If dynamic settings or `validatePassword` are unavailable, fall back to a
  conservative static policy: minimum 8 characters, maximum 72 characters, and
  a visible "Clerk will perform final password checks when you submit" note.
- Do not claim that a password passed HIBP locally unless Clerk exposes that
  result in the validation callback. If `disable_hibp === false`, show a
  neutral rule such as "Not found in known breaches - checked by Clerk on
  submit".
- Expose a `passesRequiredRules` boolean for submit-button disabling on
  sign-up and local validation on reset/profile. Server-side Clerk rejection
  remains authoritative.
- Keep the UI compact: a checklist and optional strength row below the password
  field, visible when the field is focused, non-empty, or the form has an error.

Implementation shape:

- `usePasswordPolicy({ password, validator, clerk })` should return:
  `settings`, `rules`, `strength`, `source`, `passesRequiredRules`,
  `validateNow`.
- `rules` should be plain objects like `{ key, label, status }`, where status
  is `pass`, `fail`, or `info`.
- `PasswordPolicyChecklist.vue` should accept the composable output or accept
  `password`, `validator`, and `clerk` props and render the rules. Keep it easy
  to test without a live Clerk instance.

Add `frontend/src/components/PasswordPolicyChecklist.test.js` covering:

- fallback rules when no dynamic settings are available;
- dynamic min/max and character-class rules from a mocked `passwordSettings`;
- zxcvbn/strength result from a mocked `validatePassword` callback;
- HIBP shown as server-checked info, not a local pass/fail.

**Verify**: `cd frontend && npm test -- PasswordPolicyChecklist` -> exit 0, new tests pass.

### Step 3: Enable username and social providers on custom sign-up

Update `frontend/src/views/SignUpView.vue`.

Required behavior:

- Add a required `username` field between email and password, with
  `autocomplete="username"`.
- Keep email required. The owner decided both email and username are required.
- Pass username to Clerk:

```js
const result = await signUp.value.create({
  emailAddress: form.email,
  username: form.username,
  password: form.password,
  firstName: form.firstName || undefined,
  lastName: form.lastName || undefined,
})
```

- Do not pre-check username uniqueness locally. Clerk owns username uniqueness
  and error messages.
- Add `PasswordPolicyChecklist` under the password input and disable submit
  when email, username, or visible password policy is clearly invalid.
- Replace the single Google button with a reusable provider list for:
  `oauth_google`, `oauth_facebook`, `oauth_x`.
- Prefer a shared `frontend/src/components/SocialAuthButtons.vue` so sign-up
  and sign-in stay consistent. The component should show provider labels and a
  per-provider loading state. Use text labels like "Continue with Google",
  "Continue with Facebook", "Continue with X".
- The OAuth redirect call should still use:
  `redirectUrl: '/sso-callback'` and
  `redirectUrlComplete: peekPostAuthRedirect() || '/'`.

Add or update `frontend/src/views/SignUpView.test.js` covering:

- username field exists and is required;
- `signUp.create()` receives `username`, `emailAddress`, and `password`;
- submit is disabled or blocked for empty username;
- social provider clicks call `authenticateWithRedirect()` with
  `oauth_google`, `oauth_facebook`, and `oauth_x`;
- existing email-code verification flow still calls
  `prepareEmailAddressVerification({ strategy: 'email_code' })`.

**Verify**: `cd frontend && npm test -- SignUpView PasswordPolicyChecklist` -> exit 0.

### Step 4: Enable email-or-username sign-in and social providers

Update `frontend/src/views/SignInView.vue`.

Required behavior:

- Rename form state from `email` to `identifier` or add an identifier field
  without leaving stale sign-in logic that still uses `form.email`.
- Change the label to "Email or username".
- Use `type="text"` and `autocomplete="username"` so usernames are accepted.
- Submit password sign-in with:

```js
const result = await signIn.value.create({
  strategy: 'password',
  identifier: form.identifier,
  password: form.password,
})
```

- Update messages that currently say "email address" to "email or username"
  where the user entered an identifier.
- Keep the existing second-factor behavior. It already supports `totp` and
  `backup_code` and should not be weakened.
- Reuse `SocialAuthButtons.vue` and expose Google, Facebook, and X.

Add or update `frontend/src/views/SignInView.test.js` covering:

- field label is "Email or username";
- password sign-in sends `identifier: form.identifier`;
- the old `form.email` path is not used in submit;
- TOTP and backup-code second-factor branches still render the correct label;
- provider clicks call `authenticateWithRedirect()` with the three strategies.

**Verify**: `cd frontend && npm test -- SignInView` -> exit 0.

### Step 5: Handle OAuth sign-up continuation when username is missing

Update `frontend/src/views/SSOCallbackView.vue`, `frontend/src/router/index.js`,
and create `frontend/src/views/CompleteUsernameView.vue` if the Step 1 runtime
check confirms this SDK can route incomplete sign-ups there.

Target behavior:

- Make the callback copy provider-neutral, for example "Completing
  authentication".
- Pass a continuation URL to Clerk's callback component:

```vue
<AuthenticateWithRedirectCallback
  :sign-in-force-redirect-url="redirectTarget"
  :sign-up-force-redirect-url="redirectTarget"
  :sign-in-fallback-redirect-url="redirectTarget"
  :sign-up-fallback-redirect-url="redirectTarget"
  continue-sign-up-url="/complete-username"
  sign-in-url="/sign-in"
  sign-up-url="/sign-up"
/>
```

- Add route:

```js
{ path: '/complete-username', component: () => import('../views/CompleteUsernameView.vue'), meta: { public: true } }
```

- `CompleteUsernameView.vue` should:
  - use `useSignUp()` and `useClerk()`;
  - read `signUp.value.status`, `signUp.value.missingFields`, and
    `signUp.value.username`;
  - show only a username field;
  - call `signUp.value.update({ username: form.username })`;
  - if the result is `complete`, activate the created session through
    `activateSessionAndHydrateAuth()` and redirect to the stored post-auth
    target or `/`;
  - if only email verification remains, route to `/sign-up` or show a clear
    "Continue sign-up from the email verification page" action. Do not invent
    local state for Clerk's pending sign-up.

Add/update tests:

- `frontend/src/router/index.test.js` checks `/complete-username` is public
  and lazy-loaded.
- `frontend/src/views/CompleteUsernameView.test.js` if the view is created:
  mocked `signUp.update({ username })` completes and activates session;
  no pending sign-up redirects away or shows the safe fallback.

**Verify**: `cd frontend && npm test -- SSOCallback CompleteUsername router/index` -> exit 0, if those tests exist. If Vitest reports no matching files for `SSOCallback`, run `cd frontend && npm test -- CompleteUsername router/index` instead.

### Step 6: Show password policy on reset and profile password change

Update `frontend/src/views/ForgotPasswordView.vue` and
`frontend/src/views/ProfileView.vue`.

Required behavior:

- Render `PasswordPolicyChecklist` below the new-password field in password
  reset.
- Render `PasswordPolicyChecklist` below the profile new-password field.
- Replace the hardcoded `newPassword.length < 8` validation in
  `ProfileView.vue` with `passesRequiredRules`, while retaining:
  - current password required;
  - confirm password must match;
  - new password must differ from current password.
- Keep Clerk as the final password authority. Submit should still surface Clerk
  errors through the existing error helper.

Add/update tests:

- `frontend/src/views/ForgotPasswordView.test.js`: policy renders on reset
  step and reset submit sends the password to Clerk.
- `frontend/src/views/ProfileView.test.js`: password update blocks policy
  failures, still blocks mismatched confirmation, and calls
  `user.updatePassword({ currentPassword, newPassword, signOutOfOtherSessions: true })`
  on success.

**Verify**: `cd frontend && npm test -- ForgotPasswordView ProfileView PasswordPolicyChecklist` -> exit 0.

### Step 7: Add custom authenticator-app and backup-code management

Create `frontend/src/components/TwoFactorSettings.vue` and embed it in
`frontend/src/views/ProfileView.vue` as a Security section. Put it near the
password card, not inside billing. A full-width `profile-card` is acceptable if
the existing grid needs room.

Required behavior:

- Show the current status from Clerk user fields:
  `user.value.totpEnabled`, `user.value.backupCodeEnabled`, and
  `user.value.twoFactorEnabled`.
- If `user.value.username` exists, show it read-only in the Security section.
  Do not provide username editing.
- Start setup:
  - call `user.value.createTOTP()`;
  - show `totp.secret` and `totp.uri` if present;
  - provide copy controls for secret/URI;
  - provide an `href` to the `otpauth://` URI when present;
  - prompt for authenticator code.
- Verify setup:
  - call `user.value.verifyTOTP({ code })`;
  - then call `user.value.createBackupCode()`;
  - if `createBackupCode()` is not available but `verifyTOTP()` returns
    `backupCodes`, use those;
  - show backup codes once in a dedicated panel.
- Backup codes panel:
  - show one code per line;
  - provide copy and download buttons;
  - require a checkbox such as "I saved these backup codes" before closing the
    panel;
  - clear codes from component state on close and `onBeforeUnmount()`;
  - never write backup codes to localStorage, sessionStorage, IndexedDB, URL
    params, the backend, or logs.
- Regenerate backup codes:
  - call `user.value.createBackupCode()`;
  - show the new codes once with the same save-confirmation flow.
- Disable authenticator app:
  - call `user.value.disableTOTP()`;
  - surface Clerk reverification/errors through the existing Clerk error helper
    style;
  - call `user.value.reload?.()` after successful setup, regeneration, or
    disable so the status flags refresh.
- Do not add an admin-specific 2FA requirement.

Add/update tests:

- `frontend/src/components/TwoFactorSettings.test.js`: setup calls
  `createTOTP()`, verify calls `verifyTOTP({ code })`, backup generation calls
  `createBackupCode()`, codes render once, close is disabled until saved is
  checked, disable calls `disableTOTP()`, and unmount clears codes.
- `frontend/src/views/ProfileView.test.js`: Profile renders the Security
  section and passes the mocked Clerk user through.

**Verify**: `cd frontend && npm test -- TwoFactorSettings ProfileView` -> exit 0.

### Step 8: Update docs with required Clerk dashboard settings

Update `docs/auth-workflow.md` and `README.md`.

Docs must say:

- Clerk is still the identity source of truth.
- The local app still authorizes by `clerk_user_id`, `is_admin`, and
  `is_active`; username is not stored locally in this plan.
- Enable password auth.
- Enable username for sign-up and sign-in, and configure it as required if the
  product requires both email and username.
- Enable email sign-up/sign-in and email-code verification.
- Enable password reset with email verification code.
- Configure password policy in Clerk Dashboard. Recommended current target from
  the planning discussion:
  - minimum length 8;
  - reject compromised passwords;
  - enforce strong minimum password strength;
  - avoid mandatory character-class rules unless the product intentionally
    accepts the NIST trade-off shown in Clerk's dashboard.
- Enable Google, Facebook, and X social connections if those buttons should be
  visible and functional.
- Enable authenticator app and backup codes in Clerk Dashboard for custom 2FA
  management.
- Admin access remains unchanged: no extra admin-only 2FA gate in this plan.

**Verify**: `rg -n "username|Facebook|oauth_x|backup codes|authenticator|password policy|clerk_user_id" docs/auth-workflow.md README.md` -> matching updated documentation lines.

### Step 9: Run full verification and scope checks

Run the complete frontend checks:

1. `cd frontend && npm test`
2. `cd frontend && npm run build`
3. `git diff --name-only`

Expected:

- all Vitest tests pass;
- Vite build exits 0;
- `git diff --name-only` lists only in-scope files plus `plans/README.md` if
  you update plan status.

**Verify**: all three commands meet the expected result.

## Test plan

Write or extend focused Vitest coverage:

- `frontend/src/components/PasswordPolicyChecklist.test.js`
  - fallback password policy;
  - dynamic Clerk password settings;
  - strength callback handling;
  - HIBP displayed as Clerk/server-checked info.
- `frontend/src/views/SignUpView.test.js`
  - username field and `signUp.create({ username })`;
  - both email and username required;
  - social provider strategies: `oauth_google`, `oauth_facebook`, `oauth_x`;
  - existing email verification still works.
- `frontend/src/views/SignInView.test.js`
  - email-or-username identifier submitted to Clerk;
  - no stale email-only sign-in path;
  - TOTP and backup-code second-factor UI remains supported;
  - social provider strategies.
- `frontend/src/views/ForgotPasswordView.test.js`
  - policy rendered on reset password step;
  - reset still uses `reset_password_email_code`.
- `frontend/src/components/TwoFactorSettings.test.js`
  - TOTP setup, verify, backup-code generation, regeneration, disable, and
    one-time code clearing.
- `frontend/src/views/ProfileView.test.js`
  - security section renders;
  - password policy gates update;
  - existing billing tests still pass.
- `frontend/src/router/index.test.js`
  - `/complete-username` route is public if that view is created;
  - no admin route behavior changes.

Verification:

- `cd frontend && npm test` -> all pass.
- `cd frontend && npm run build` -> exit 0.

## Done criteria

All must hold:

- [ ] Sign-up requires both email and username in the custom UI and sends
      `username` to Clerk.
- [ ] Sign-in accepts an email or username identifier and sends it as
      `identifier` to Clerk.
- [ ] Google, Facebook, and X OAuth buttons exist on sign-in and sign-up and
      call `oauth_google`, `oauth_facebook`, and `oauth_x`.
- [ ] OAuth callback is provider-neutral and incomplete username sign-ups route
      through a Clerk-owned custom continuation flow, not local username
      storage.
- [ ] Password-policy UI appears on sign-up, password reset, and profile
      password change, with dynamic Clerk settings when available and a static
      fallback when not.
- [ ] Profile contains a custom Security/2FA section for authenticator app and
      backup codes.
- [ ] Backup codes are displayed once, can be copied/downloaded, require a
      saved confirmation before closing, and are cleared from component state.
- [ ] No backend model, migration, webhook, or `/api/me` response change was
      made for username.
- [ ] No admin-specific 2FA enforcement was added.
- [ ] `rg -n "localStorage|sessionStorage|indexedDB|backupCodes" frontend/src/components/TwoFactorSettings.vue frontend/src/views/ProfileView.vue` shows no persistence of backup codes. Seeing reactive state variable names is acceptable; storage calls are not.
- [ ] `cd frontend && npm test` exits 0.
- [ ] `cd frontend && npm run build` exits 0.
- [ ] `git diff --name-only` contains only files listed in this plan's scope
      plus `plans/README.md`.
- [ ] `plans/README.md` row for Plan 005 is updated from TODO to DONE or
      BLOCKED with a one-line reason.

## STOP conditions

Stop and report back, do not improvise, if:

- The code at the locations in "Current state" does not match the excerpts.
- The installed Clerk SDK does not expose `validatePassword`, `createTOTP`,
  `verifyTOTP`, `disableTOTP`, or `createBackupCode` on the resources described
  above.
- Dynamic password settings cannot be read from the Clerk runtime and the
  product owner rejects the static fallback. If the owner accepts fallback,
  proceed with fallback and document it.
- OAuth incomplete sign-up cannot be routed to a custom username-completion
  flow with this Clerk Vue SDK. Do not store username locally to work around
  this; Clerk must remain the authority.
- Implementing username appears to require backend database changes.
- Implementing 2FA appears to require admin-only route/API enforcement.
- A step's verification fails twice after a reasonable fix attempt.
- You need to add a frontend dependency, touch package lockfiles, or introduce
  a QR-code package to complete the work.

## Maintenance notes

- Clerk Dashboard settings must stay aligned with the custom UI. If username,
  password policy, social providers, authenticator app, or backup codes are
  disabled in Clerk, the UI should surface Clerk errors cleanly but cannot make
  those flows work by itself.
- Reviewers should scrutinize the boundary between Clerk-owned identity data
  and local authorization data. This plan intentionally does not mirror username
  into the local database.
- Backup-code handling is sensitive. Review for accidental persistence, logs,
  snapshots, or test fixtures that contain real codes.
- A QR-code setup experience can be planned later if manual secret/URI setup is
  not enough. Keep that as a separate dependency/package decision.
