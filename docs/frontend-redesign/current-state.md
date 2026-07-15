# Current Frontend Baseline

> Status: Current implementation
> Last reviewed: 2026-07-16
> Source of truth: `frontend/src/`

This document records the frontend behavior that exists before the Tournament
Atlas migration. It is a parity checklist, not a target architecture. Update it
when the current production frontend changes before its replacement is complete.

## Application Shell

`App.vue` currently owns the global navigation, responsive menu, account menu,
billing-attention notice, authentication recovery state, footer, and cookie
banner. Navigation is a fixed World Cup-oriented list rather than being derived
from the active Competition Edition.

Signed-in navigation exposes Home, Groups, Predict Match, Tournament, Markets,
Pricing, Profile through the account menu, and Admin for administrators. Public
navigation exposes Home, Pricing, Sign In, and Sign Up.

## Localization Core

`frontend/src/i18n/` owns the current localization interface. Vue I18n runs in
Composition API mode with supported Locales `en` and `es` and English fallback.
At startup, the frontend resolves a saved preference, then supported browser
preferences, then English; an explicit Locale has higher priority when a caller
provides one. Applying a Locale persists it when storage is available and updates
the document `lang` attribute. Blocked browser storage does not prevent startup.

Only namespaced `common.localeName` messages exist. Production routes, navigation,
views, authentication redirects, and API-generated narrative are not localized
yet, and there is no Locale switcher. The current flat routes remain canonical.

## Competition Registry

`frontend/src/competition/` owns a framework-independent Competition Edition
registry. It currently contains one record for FIFA World Cup 2026 with stable
Competition and Competition Edition IDs, the `world-cup-2026` slug,
`group-and-knockout` format, a display-name localization key, and the `groups`,
`predictions`, `bracket`, and `markets` Competition Capabilities.

The public interface lists Competition Editions, resolves one by slug, and checks
Competition Capability support without exposing shared registry state. It does
not yet drive routes, navigation, views, or API requests. Existing World Cup
views and endpoints remain the production behavior.

## Theme Foundation

`frontend/src/ui/foundations/tokens.css` and `themes.css` are loaded globally,
while `frontend/src/ui/theme.js` initializes the effective theme before Vue
mounts. The runtime supports `light`, `dark`, and `system` preferences, persists
the normalized value under `socceroctopus.theme`, and sets the root `data-theme`
attribute plus `color-scheme`. Startup safely reads local storage and the current
`prefers-color-scheme` signal once; there is no visible selector or live system
listener yet.

The token layer defines semantic typography, spacing, radius, border, shadow,
motion, control, icon, and layering values without a global reset. Theme values
cover background, surfaces, text, borders, accent, focus, and distinct status
roles for light and dark modes. Existing production views still use their
page-local styles, so loading the foundation does not change their appearance
until each view is migrated.

## Production Route Inventory

| Route | Access | View or behavior | Current responsibility |
|---|---|---|---|
| `/` | Public | `Home.vue` | World Cup 2026 product overview and links to the four prediction areas. |
| `/groups` | Signed in | `GroupsView.vue` | Twelve groups with Team name, ELO, and rank, sorted by ELO. |
| `/predict` | Signed in | `PredictView.vue` | Team and stage selection, Match Prediction, probabilities, predicted score, xG, narrative, key factors, and Swarm Agent detail. |
| `/tournament` | Signed in | `TournamentView.vue` | Live group results and standings plus optional-swarm Tournament Simulation and knockout results. |
| `/markets` | Signed in | `MarketsView.vue` | Match markets and tournament futures, filters, fair-value contract prices, and generated Market Questions. |
| `/profile` | Signed in | `ProfileView.vue` | User profile, subscription, usage, billing health, portal access, payment recovery, and two-factor settings. |
| `/pricing` | Public | `PricingView.vue` | Plan comparison, checkout or plan change, cancellation, and signed-in subscription context. |
| `/billing` | Signed in | Redirect | Redirects to `/profile`. |
| `/billing/success` | Signed in | `BillingSuccessView.vue` | Verifies a checkout session before returning the user to their account. |
| `/admin/settings` | Administrator | `AdminSettingsView.vue` | Provider, model, swarm, tournament, and per-tier feature-limit settings. |
| `/sign-in` | Public | `SignInView.vue` | Custom Clerk sign-in, social sign-in, and multi-factor continuation. |
| `/sign-up` | Public | `SignUpView.vue` | Custom Clerk registration, password policy, social sign-up, and verification. |
| `/forgot-password` | Public | `ForgotPasswordView.vue` | Password reset and verification flow. |
| `/sso-callback` | Public | `SSOCallbackView.vue` | Clerk OAuth callback and post-authentication redirect continuation. |
| `/complete-username` | Public | `CompleteUsernameView.vue` | Collects a missing username after external authentication. |
| `/legal` | Public | `LegalNoticeView.vue` | Legal notice and prediction disclaimer. |
| `/cookie-policy` | Public | `CookiePolicyView.vue` | Cookie-policy content. |
| `/contact` | Public | `ContactView.vue` | Contact information. |
| `/about` | Public | `AboutView.vue` | Product and methodology information. |

The router redirects signed-out users away from protected routes, redirects
non-admin users away from Admin, and redirects signed-in users away from Sign In
and Sign Up. The current redirect helpers use flat, non-localized paths.

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
- Full-swarm opt-in for Tournament Simulation.
- Match and tournament Market Question modes and filters.
- Responsive navigation, footer links, cookie consent, and legal disclaimer.

The complete authentication and billing behavior is owned by
[Authentication Workflow](../auth-workflow.md) and
[Billing Workflow](../billing-workflow.md). Those documents, not this summary,
are authoritative for their workflows.

## Existing Shared Components

The current frontend already shares billing notices and plan links, probability
meters, market cards, video-agent detail, authentication controls, reverification,
password policy, and two-factor settings. The redesign should adapt or wrap
working domain behavior before replacing it. Visual similarity alone is not a
reason to discard tested workflow components.

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
