# Current Frontend Baseline

> Status: Current implementation
> Last reviewed: 2026-07-16
> Source of truth: `frontend/src/`

This document records the frontend behavior and migration status during the
Tournament Atlas rollout. It is a parity checklist, not a target architecture.
Update it when the current production frontend changes before its replacement is
complete.

## Application Shell

`App.vue` owns auth, billing, recovery, and menu state while composing the
presentational `AppShell` and `CompetitionShell` patterns. The compact desktop
header contains the favicon brand mark, SoccerOctopus name, registered Competition
Edition dropdown, registry-derived Overview, Groups, Predict, Bracket, and Markets
links, Pricing, admin visibility, account actions, icon-only Locale and theme
controls, and their labeled menus. On mobile the workspace links become an
expanded panel. Existing billing-attention, auth recovery, sign-out, footer, legal
links, and cookie-banner behavior remain mounted through explicit slots.

Signed-out navigation exposes the canonical Competition overview, Pricing, Sign
In, and Sign Up. Signed-in workspace navigation is derived from the registered
Competition Capabilities; unsupported `table` and `fixtures` items are not
shown. The Competition Edition button lists only registered editions and shows
the current display-name key; it does not invent a selector option. Home and
Groups now use Atlas page structure, semantic tokens, canonical workspace links,
and localized page messages; other views remain legacy until each view migrates.

## Localization Core

`frontend/src/i18n/` owns the current localization interface. Vue I18n runs in
Composition API mode with supported Locales `en` and `es` and English fallback.
At startup, the frontend resolves a saved preference, then supported browser
preferences, then English; an explicit Locale has higher priority when a caller
provides one. Applying a Locale persists it when storage is available and updates
the document `lang` attribute. Blocked browser storage does not prevent startup.

Namespaced `common`, `navigation`, `competitions`, `home`, `groups`, `overlays`,
and `predictions` messages exist. Canonical
Competition Workspace routes apply their URL Locale over saved and browser
preferences, including persistence and the document `lang` attribute. The shell
navigation, account controls, footer, recovery labels, theme preferences, and
Competition context are translated. Home, Groups, Predict frontend copy, Cookie
Banner, Video Agent overlay, Probability Meter, and billing-notice controls are
translated in production domains. Predict's backend-generated Swarm Consensus,
Key Factors, and Agent reasoning remain English because the endpoint does not
accept Locale. Authentication, account, legal, and other public routes are not
localized yet.

## Competition Registry

`frontend/src/competition/` owns a framework-independent Competition Edition
registry. It currently contains one record for FIFA World Cup 2026 with stable
Competition and Competition Edition IDs, the `world-cup-2026` slug,
`group-and-knockout` format, a display-name localization key, and the `groups`,
`predictions`, `bracket`, and `markets` Competition Capabilities.

The public interface lists Competition Editions, resolves one by slug, and checks
Competition Capability support without exposing shared registry state. The
router and shell use listing and lookup to derive the transitional default,
validate workspace route context, and derive navigation. Home uses the active
edition to build canonical workflow links; Groups uses it for localized context
while retaining its existing endpoint. The registry does not yet adapt API
requests, and only FIFA World Cup 2026 is registered.

## Theme Foundation

`frontend/src/ui/foundations/tokens.css` and `themes.css` are loaded globally,
while `frontend/src/ui/theme.js` initializes the effective theme before Vue
mounts. The runtime supports `light`, `dark`, and `system` preferences, persists
the normalized value under `socceroctopus.theme`, and sets the root `data-theme`
attribute plus `color-scheme`. Startup safely reads local storage and the current
`prefers-color-scheme` signal once; the shell exposes a compact icon menu, but
there is no live system listener yet.

The token layer defines semantic typography, spacing, radius, border, shadow,
motion, control, icon, and layering values without a global reset. Theme values
cover background, surfaces, text, borders, accent, focus, and distinct status
roles for light and dark modes. Home and Groups consume these semantic roles;
other production views still use their page-local styles, so loading the
foundation does not change their appearance until each view is migrated.

`AppShell` exposes the current theme preference through a keyboard-accessible
icon button and labeled menu and applies it through the existing runtime without
a reload. System preference changes are intentionally not observed live in this
phase.

## Production Route Inventory

| Route | Access | View or behavior | Current responsibility |
|---|---|---|---|
| `/` | Public | Redirect | Redirects to `/en/competitions/world-cup-2026`. |
| `/:locale/competitions/:competitionEditionSlug` | Public | `Home.vue` | Atlas overview with localized World Cup 2026 scope, four canonical workflow links, five current Swarm Agent roles, and the existing Video Agent evidence modal trigger. |
| `/groups` | Signed in | Redirect | Redirects to the canonical English Groups workspace. |
| `/:locale/competitions/:competitionEditionSlug/groups` | Signed in | `GroupsView.vue` | Atlas standings tables from `GET /api/predictions/groups`, with Team name, ELO, and rank sorted by descending ELO, response-derived counts, loading, empty, and retryable error states. |
| `/predict` | Signed in | Redirect | Redirects to the canonical English Match Prediction workspace. |
| `/:locale/competitions/:competitionEditionSlug/predict` | Signed in | `PredictView.vue` | Atlas Match Prediction workflow with localized team/stage controls, complete team-feed and run states, exact existing API payload/billing gates, probabilities, predicted score/xG, confidence, four-agent agreement, source narrative, key factors, and Agent detail. |
| `/tournament` | Signed in | Redirect | Redirects to the canonical English Knockout Bracket workspace. |
| `/:locale/competitions/:competitionEditionSlug/bracket` | Signed in | `TournamentView.vue` | Atlas live group standings/results plus optional-swarm Tournament Simulation, with complete feed/run states, localized controls, exact existing API and billing behavior, response-derived podium fields, and an ordered horizontally scrollable knockout bracket. |
| `/markets` | Signed in | Redirect | Redirects to the canonical English Markets workspace. |
| `/:locale/competitions/:competitionEditionSlug/markets` | Signed in | `MarketsView.vue` | Match markets and tournament futures, filters, fair-value contract prices, and generated Market Questions. |
| `/profile` | Signed in | `ProfileView.vue` | User profile, subscription, usage, billing health, portal access, payment recovery, and two-factor settings. |
| `/pricing` | Public | `PricingView.vue` | Plan comparison, checkout or plan change, cancellation, and signed-in subscription context. |
| `/billing` | Signed in | Redirect | Redirects to `/profile`. |
| `/billing/success` | Signed in | `BillingSuccessView.vue` | Verifies a checkout session before returning the user to their account. |
| `/admin/settings` | Administrator | `AdminSettingsView.vue` | Provider, model, swarm, tournament, and per-tier feature-limit settings. |
| `/sign-in` | Public | `SignInView.vue` | Localized Tournament Atlas Clerk sign-in, social sign-in, and multi-factor continuation. |
| `/sign-up` | Public | `SignUpView.vue` | Localized Tournament Atlas Clerk registration, password policy, social sign-up, and email verification. |
| `/forgot-password` | Public | `ForgotPasswordView.vue` | Localized Tournament Atlas password reset and email-code verification flow. |
| `/sso-callback` | Public | `SSOCallbackView.vue` | Clerk OAuth callback and post-authentication redirect continuation. |
| `/complete-username` | Public | `CompleteUsernameView.vue` | Collects a missing username after external authentication. |
| `/legal` | Public | `LegalNoticeView.vue` | Legal notice and prediction disclaimer. |
| `/cookie-policy` | Public | `CookiePolicyView.vue` | Cookie-policy content. |
| `/contact` | Public | `ContactView.vue` | Contact information. |
| `/about` | Public | `AboutView.vue` | Product and methodology information. |

Workspace routes accept only `en` and `es`, validate Competition Edition slugs
through the registry, and preserve query/hash across legacy and fallback
redirects. Signed-out protected workspace navigation stores the full canonical
destination before redirecting to flat `/sign-in`. The router also redirects
non-admin users away from Admin and signed-in users away from Sign In and Sign
Up. Account, billing, admin, authentication, legal, and public-information routes
remain transitional flat routes.

## Current Data Dependencies

| Workflow | Frontend request |
|---|---|
| Groups | `GET /api/predictions/groups` |
| Team selection | `GET /api/predictions/teams` |
| Match Prediction | `POST /api/predictions/match` |
| Live tournament results | `GET /api/predictions/live-results` |
| Tournament Simulation | `POST /api/predictions/tournament` |
| Match markets | `POST /api/markets/match` |
| Tournament markets | `POST /api/markets/tournament` |
| Current user | `GET /api/me` |
| Admin settings | `GET` and `PUT /api/admin/settings` |
| Feature limits | `GET` and `PUT /api/admin/feature-limits` |

Billing calls are centralized in `frontend/src/lib/billing.js`. Authentication
headers are centralized in `frontend/src/lib/api.js`. The redesign must keep
these ownership boundaries or replace them deliberately rather than adding API
calls to generic UI components.

## Shared Behavior That Must Survive

- Shell-level and workflow-level billing-attention recovery.
- Subscription-required, payment-required, and feature-limit error handling.
- Post-authentication destination recovery for email, MFA, and social flows.
- Administrator-only navigation and route access.
- Official results taking precedence over predicted tournament results.
- Official Tournament results are labeled final and never display predicted
  probabilities; live standings do not infer qualification state.
- Full-swarm opt-in for Tournament Simulation.
- Match and tournament Market Question modes and filters.
- Responsive navigation, footer links, cookie consent, and legal disclaimer.

The complete authentication and billing behavior is owned by
[Authentication Workflow](../auth-workflow.md) and
[Billing Workflow](../billing-workflow.md). Those documents, not this summary,
are authoritative for their workflows.

## Existing Shared Components

`CookieBanner.vue`, `VideoAgentModal.vue`, `ProbMeter.vue`,
`BillingStatusNotice.vue`, and `BillingPlansLink.vue` now consume Atlas tokens
and localized message domains. The latter three preserve their public props,
events, and routes for Tournament, Markets, Profile, and shell callers.

Cookie Banner and Video Agent detail retain their existing behavior. Cookie
Banner preserves the `so_cookie_consent` key, `all`/`necessary` values,
in-session dismissal when storage is unavailable, and the existing Cookie Policy
route. Video Agent detail retains every evidence source while adding semantic
modal/lightbox roles, native screenshot buttons, localized controls and captions,
layered Escape handling, focus capture/restoration, and background scroll lock.

`MarketCard.vue` now uses Atlas tokens and localized frontend labels while
preserving every returned contract value and its public `question` prop. The
current frontend also shares authentication controls, reverification, password
policy, and two-factor settings. Those components remain pending Atlas
migration. The redesign should adapt or wrap working domain
behavior before replacing it;
visual similarity alone is not a reason to discard tested workflow components.

## Design-Lab Routes

The following public routes are temporary design review tools and are not part of
the production feature inventory:

| Route | Purpose |
|---|---|
| `/design-lab` | Comparison page for the explored visual directions. |
| `/design-lab/atlas` | Multi-page Tournament Atlas portal mockup. |
| `/design-lab/orbit` | Multi-page Swarm Orbit portal mockup retained for comparison. |

They use representative mock data and must not become application data sources.
Remove them during the final cutover after the production Tournament Atlas views
cover the required review surface.

### Tournament Atlas parity

The `/design-lab/atlas` screens use static examples, but their visible data fields
and actions map to current production workflows:

| Atlas screen | Production source | Parity boundary |
|---|---|---|
| Home | `/` | Competition summary, four workflow entry points, and the five current swarm roles. |
| Groups | `/groups` and `GET /api/predictions/groups` | Four representative groups from the current roster, ordered by ELO with Team name, ELO, and FIFA rank. The mockup does not infer qualification. |
| Predict | `/predict` and `POST /api/predictions/match` | Team and stage selectors, most-likely score, outcome probabilities, overall confidence, predicted goals, score probability, consensus, and a summary derived from Agent predictions. |
| Tournament | `/tournament` and `POST /api/predictions/tournament` | Simulation action, official-versus-predicted behavior, champion, runner-up, third place, champion final-win probability, and representative knockout results. |
| Markets | `/markets`, `POST /api/markets/match`, and `POST /api/markets/tournament` | Match and tournament modes, generated Market Questions, fair-value prices, and the current Kalshi and Polymarket formats. |

The Atlas preview deliberately shows a curated subset of Groups, knockout
matches, Market Questions, and result detail. Its controls switch mockup screens
but do not call the API. Loading, empty, error, authentication, billing, and live
result states remain production migration requirements; their absence from the
preview is not an accepted omission from the final frontend.
