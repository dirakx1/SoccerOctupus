# Frontend Redesign Architecture

> Status: Tournament Atlas foundations and localized Competition Workspace
> routing are implemented; remaining architecture is proposed
> Last reviewed: 2026-07-16
> Applies to: `frontend/` and frontend-facing competition data contracts

## Purpose

The redesign must support more than FIFA World Cup 2026, add Spanish without
duplicating application logic, and replace repeated page-level styling with a
small internal design system. Existing authentication, billing, prediction,
simulation, and market behavior must remain intact during migration.

The client-approved visual direction is recorded in
[ADR-0001](../adr/0001-tournament-atlas-design-direction.md).

## Architectural Principles

- Locale and Competition Edition are route context, not page-local state.
- Navigation is derived from Competition Capabilities.
- Views compose feature modules; they do not redefine common controls and states.
- Accessible interaction behavior lives behind internal UI interfaces.
- Domain data uses stable identifiers and codes. Display text is localized at
  the presentation seam.
- Legacy routes remain available until replacement routes have behavioral parity.

## Decision Status

| Concern | Direction | Status |
|---|---|---|
| Visual language | Tournament Atlas | Accepted |
| Localization | Vue I18n Composition API with English fallback | Core, shell, Home, Groups, Predict, and migrated shared-component messages implemented; remaining routes pending |
| Competition registry | Internal plain-JavaScript registry with a World Cup 2026 configuration adapter | Implemented for route validation, shell navigation, Home links, and Groups context; endpoint adapters remain pending |
| Theme foundation | Semantic Atlas tokens with light/dark runtime preference | Implemented and consumed by the shell, Home, Groups, Predict, and migrated shared components |
| Canonical routes | Locale-prefixed Competition Workspace routes | Implemented for current World Cup workflows; shell and non-workspace routes pending |
| Application shell | Internal `AppShell` and `CompetitionShell` patterns using semantic tokens | Implemented; Home, Groups, and Predict are migrated production pages |
| Workspace navigation | Registry-derived navigation mapped through `workspaceLocation` | Implemented for current Competition Capabilities; future editions pending real adapters |
| Design system | Internal SoccerOctopus modules using semantic CSS tokens | Proposed |
| Accessible primitives | Reka UI wrapped behind internal interfaces | Proposed |
| Component catalogue | Storybook for Vue 3 and Vite | Proposed |
| Styling migration | Keep Vue scoped CSS; introduce global tokens and foundations | Proposed |

Vue I18n is approved and installed. Other proposed dependencies remain
unapproved and must not be installed until their architecture is accepted.

## Route Model

Implemented Competition Workspace routes use stable, untranslated path segments:

```text
/:locale(en|es)/competitions/:competitionEditionSlug
/:locale(en|es)/competitions/:competitionEditionSlug/groups
/:locale(en|es)/competitions/:competitionEditionSlug/predict
/:locale(en|es)/competitions/:competitionEditionSlug/bracket
/:locale(en|es)/competitions/:competitionEditionSlug/markets
```

`table` and `fixtures` paths remain reserved for Competition Editions that expose
those capabilities; no route is registered before a real view exists. A Spanish
workspace URL applies `es` to Vue I18n, persisted preference, and the document
language before auth handling. Page copy and navigation labels remain English
until their owning views and shell migrate. Localized path aliases can be added
later if search requirements justify their complexity.

`frontend/src/router/workspace.js` is the route-construction interface:

| Export | Behavior |
|---|---|
| `WORKSPACE_ROUTE_NAMES` | Stable names for overview, groups, predict, bracket, and markets. |
| `DEFAULT_COMPETITION_EDITION_SLUG` | Default slug derived from the Competition registry rather than duplicated in the router. |
| `workspaceLocation(area, options)` | Builds a named route location with Locale, Competition Edition slug, query, and hash. |

The router validates every canonical Competition Edition slug through
`getCompetitionEdition`. Unknown or blank edition paths redirect to the
same-locale World Cup overview while preserving query and hash.

Current flat routes redirect to their World Cup 2026 equivalents during migration:

```text
/             -> /en/competitions/world-cup-2026
/groups       -> /en/competitions/world-cup-2026/groups
/predict      -> /en/competitions/world-cup-2026/predict
/tournament   -> /en/competitions/world-cup-2026/bracket
/markets      -> /en/competitions/world-cup-2026/markets
```

Locale resolution order is:

1. Locale in the current URL.
2. Saved user or device preference.
3. Supported browser preference.
4. English fallback.

Legacy redirects preserve query and hash. A future locale switch uses the named
route helper to preserve the Competition Edition, query, and hash. Signed-out
protected workspace navigation stores the full canonical destination through the
existing post-auth redirect seam before using flat `/sign-in`; existing sign-in,
sign-up, OAuth callback, and username-completion flows consume that destination.

`AppShell` owns the page frame, footer, route-content slots, billing and recovery
slots, while `CompetitionShell` owns the compact Atlas header, favicon brand mark,
registered Competition Edition menu, capability-derived inline navigation,
account menu, mobile menu, icon-only Locale and theme controls, and their labeled
menus. App state remains the owner of auth, billing, and menu state; the patterns
are presentational and emit intent events.

Authentication, account, billing, admin, public-information, and legal routes
remain flat and unlocalized until their owning migration phases. The three
`/design-lab` routes remain unchanged and public. Home and Groups now consume the
shell's Atlas context, semantic tokens, canonical workspace links, and English /
Spanish page messages. Other production views keep their page-local copy and
styling while they migrate into the shell incrementally.

## Production Page Slices

The first vertical slice migrates the public Competition overview and the
protected Groups workflow while preserving their existing route and data seams:

- `Home.vue` keeps SoccerOctopus identity, FIFA World Cup 2026 scope, four
  workflow destinations, five current Swarm Agent roles, weights, descriptions,
  and the existing `VideoAgentModal` behavior. Workflow targets are built with
  `workspaceLocation` from the active Locale and Competition Edition.
- `GroupsView.vue` keeps `GET /api/predictions/groups`, Team/ELO/rank fields,
  descending ELO sorting, and World Cup 2026 scope. It adds response-derived
  group/team counts, semantic standings tables, loading skeleton, empty state,
  and retryable inline error state.
- `AtlasPageHeader.vue` is the small shared presentation pattern used by both
  pages. It owns no domain state or data fetching.

Home and Groups load `home` and `groups` message domains for English and Spanish.
Markets, auth, billing, admin, and other public routes remain pending migration.

The Match Prediction slice preserves the current backend and billing contracts:

- `PredictView.vue` keeps `GET /api/predictions/teams` and
  `POST /api/predictions/match` with only `home_team`, `away_team`, and `stage`.
  It renders the existing probability, score, predicted-goals, confidence,
  consensus, factor, and Agent Prediction fields without adapting generated
  evidence.
- Frontend-owned Predict copy and number/percentage formatting use the English /
  Spanish `predictions` domain. Team names, Agent names/reasoning, Swarm
  Consensus, and Key Factors remain backend/source values.
- `ProbMeter.vue`, `BillingStatusNotice.vue`, and `BillingPlansLink.vue` retain
  their public props, events, and `/pricing` route while consuming semantic Atlas
  tokens and localized frontend labels.

The backend Match Prediction request does not accept or apply Locale. Generated
narrative, Key Factors, and Agent reasoning therefore remain English until a
backend contract explicitly adds locale-aware generation and caching. The
frontend must not add a speculative `locale` payload field.

The Tournament slice preserves the live-results, simulation, and billing
contracts while separating feature presentation from workflow state:

- `TournamentView.vue` keeps `GET /api/predictions/live-results` and
  `POST /api/predictions/tournament` with only `{ use_swarm: boolean }`. It owns
  the accessible live/simulation tabs, live-feed and run states, API calls, and
  billing recovery through the canonical localized route.
- Live standings preserve the backend's ranked team order, present groups in
  canonical label order, and render all played, won, drawn, lost, goals-for,
  goals-against, goal-difference, and points values. Positions are ordinal only;
  the frontend does not infer qualification from a team's row.
- `TournamentBracket.vue` owns the returned podium and knockout presentation.
  It orders the known backend stages, exposes the champion final-win probability
  without inventing runner-up or third-place probabilities, and suppresses
  prediction probabilities for `is_actual` official results.
- Frontend-owned Tournament copy and number/percentage formatting use the English
  / Spanish `tournament` domain. Team names, `ESPN`, backend dates, scores, and
  other returned values remain source data.

The first shared-overlay slice completes the migrated Home presentation without
introducing a generic dialog framework:

- `CookieBanner.vue` preserves `so_cookie_consent` with the `all` and
  `necessary` values, keeps the `/cookie-policy` route, and treats browser
  storage as best effort so a blocked store cannot prevent an in-session choice.
- `VideoAgentModal.vue` preserves the current screenshots, source videos, URLs,
  titles, durations, and `close` event. It owns its focused dialog/lightbox
  behavior, layered Escape handling, scroll lock, and focus restoration locally.
- The `overlays` English/Spanish message domain owns Cookie Banner and Video
  Agent UI labels plus the explanatory screenshot captions. External video
  titles remain source content rather than translations.

Other shared and feature components remain pending Atlas migration.

## Competition Module

The Competition registry core is implemented as a framework-independent module:

```text
src/competition/
  index.js
  editions/
    worldCup2026.js
```

`index.js` is the public interface:

```text
listCompetitionEditions() -> CompetitionEdition[]
getCompetitionEdition(slug) -> CompetitionEdition | null
supportsCapability(edition, capability) -> boolean
```

Listing and lookup return defensive copies, so callers cannot mutate shared
registry state. Lookup returns `null` for blank or unknown slugs. Capability
checks return `false` for invalid Competition Editions and capabilities and use
the registered record rather than trusting caller-mutated capability lists.

`worldCup2026.js` is the first Competition Edition configuration adapter:

| Field | Value |
|---|---|
| Competition Edition ID | `fifa-world-cup-2026` |
| Competition ID | `fifa-world-cup` |
| Slug | `world-cup-2026` |
| Competition Format | `group-and-knockout` |
| Display-name key | `competitions.editions.worldCup2026.name` |
| Competition Capabilities | `groups`, `predictions`, `bracket`, `markets` |

The capabilities match current production workflows. `groups` maps to the group
roster, `predictions` to Match Prediction, `bracket` to the existing combined
Tournament view and Tournament Simulation, and `markets` to Market Questions.
`table` is excluded because the glossary reserves League Table for league-format
Competition Editions. `fixtures` is excluded because the current portal has no
fixtures workflow. A Competition overview is common workspace context rather
than an optional capability.

No exact date range is stored yet. Add verified dates only when a schedule-aware
consumer requires them. The display-name key also remains unconsumed until the
competition UI introduces the `competitions` localization domain.

The registry does not fetch data, build navigation, or adapt API requests. The
router consumes its listing and lookup interfaces to derive the default edition
and validate route context; current views retain their existing endpoint calls.
Capability-driven navigation and endpoint/view integration are later migration
work; do not add a speculative data-fetching seam before a second real adapter
requires one.

## Theme Foundation

The Tournament Atlas theme foundation is implemented behind a small
framework-independent module at `frontend/src/ui/theme.js` and loaded globally
from `main.js`. The shell exposes compact Locale and theme menus, while live
system-preference updates remain deferred in this phase.

| Export | Behavior |
|---|---|
| `normalizeThemePreference(value)` | Accepts `light`, `dark`, or `system` and returns `null` for unsupported input. |
| `resolveThemePreference(options)` | Uses an explicit preference, then a saved preference, then `system`. |
| `getEffectiveTheme(preference, options)` | Converts `system` to `light` or `dark` using the current `prefers-color-scheme` signal. |
| `applyTheme(preference, dependencies)` | Sets the root `data-theme` attribute and `color-scheme`, persists the normalized preference, and returns both preference values. |
| `initializeTheme(options)` | Reads saved preference safely, resolves it, and applies it before Vue mounts. |

The runtime uses `socceroctopus.theme` as its storage key. DOM and storage writes
are best effort: blocked storage, unavailable style access, or a missing document
must not prevent application startup. The entry point reads `localStorage` and
`matchMedia('(prefers-color-scheme: dark)')` once before mounting; the current
shell control calls `applyTheme` for explicit preference changes.

The current shell uses `frontend/src/ui/themePreference.js` as a small reactive
adapter over that runtime. It exposes the saved preference, effective theme, and
`setPreference` action to `App.vue`; it does not add an operating-system listener.

Theme CSS is split into stable, non-visual foundations:

```text
src/ui/foundations/
  tokens.css
  themes.css
```

`tokens.css` owns typography stacks, type scale, spacing, radii, borders,
shadows, motion, control sizes, icon sizes, and layering. It deliberately has no
global reset or element styling. `themes.css` maps semantic roles to concrete
light and dark values. The current anchor palette is warm off-white surfaces and
charcoal text in light mode (`#eee9df`, `#f8f4eb`, `#24201c`, `#1f7771`) and
deep green-black surfaces with pale text in dark mode (`#111514`, `#1b211f`,
`#edf1e9`, `#72b6a5`). Success, warning, danger, information, and focus use
distinct semantic hues in both modes. Font stacks use system and locally
available fallbacks; no remote font dependency is introduced.

Home and Groups now consume these semantic tokens through their Atlas page
styles. Other production views still own their existing styles; live system
preference updates, component primitives, and Storybook remain later work.

## Localization Module

The localization core is implemented with Vue I18n 11.4.6 in Composition API
mode (`legacy: false`). The frontend declares Node.js 22 or newer because that is
the installed release's runtime requirement.

Current structure:

```text
src/i18n/
  index.js
  locale.js
  locales/
    en/
      common.json
      competitions.json
      groups.json
      home.json
      navigation.json
      overlays.json
      predictions.json
    es/
      common.json
      competitions.json
      groups.json
      home.json
      navigation.json
      overlays.json
      predictions.json
```

`index.js` is the public interface:

| Export | Behavior |
|---|---|
| `normalizeLocale(value)` | Converts supported regional forms such as `es-MX` to `es`; returns `null` for unsupported input. |
| `resolveLocale(options)` | Resolves explicit input, saved preference, supported browser preferences, then English. |
| `applyLocale(locale, dependencies)` | Applies a normalized Locale, persists it when storage is available, and updates the injected document element. |
| `initializeLocale(options)` | Reads the saved preference safely, resolves the startup Locale, and applies it. |
| `i18n` | Vue I18n plugin configured with `en` and `es`, English fallback, and namespaced messages. |

The application entry point initializes the Locale from saved and browser
preferences and installs the plugin. Each matched Competition Workspace route
then applies its URL Locale, so route context wins over startup preference before
auth handling. `AppShell` switches Locale by preserving the current named route,
Competition Edition, query, and hash through `workspaceLocaleLocation`. Browser-
storage failures do not prevent startup, route navigation, or document-language
updates. Flat non-workspace routes retain the current Locale until their
localized route migration is implemented.

The `common`, `navigation`, `competitions`, `home`, `groups`, `overlays`, and
`predictions` domains exist today. They are consumed by the shell, migrated
production pages, and migrated shared components. Remaining feature-view domains
are added in the same change as their first real consumer. Do not create empty
resource files in advance.

Pending localization rules:

- Use locale-aware date, number, percentage, and currency formatting.
- Translation keys describe meaning, not English wording.
- Missing Spanish messages fail CI once production message domains are added.
- Components receive IDs, values, and error codes rather than preformatted English.
- API errors use stable codes that map to localized frontend messages.
- When the backend supports Locale, Match Prediction requests include it for
  Swarm Consensus and Key Factors, and generated narrative caches are keyed by
  Locale. Neither behavior exists in the current backend contract.
- Team and Competition display names are resolved from stable IDs or codes.
- Localized metadata changes with the route Locale.

The implementation should follow the official Vue I18n
[Composition API](https://vue-i18n.intlify.dev/guide/advanced/composition) and
[lazy-loading](https://vue-i18n.intlify.dev/guide/advanced/lazy) guidance.

## Design System

The SoccerOctopus design system is an internal frontend module, not a separately
published package in the first release.

```text
src/ui/
  foundations/
    tokens.css
    themes.css
  themePreference.js
    typography.css
    base.css
  primitives/
    UiButton.vue
    UiIconButton.vue
    UiInput.vue
    UiSelect.vue
    UiTabs.vue
    UiDialog.vue
    UiPopover.vue
    UiTooltip.vue
    UiSkeleton.vue
    UiNotice.vue
  patterns/
    AppShell.vue
    CompetitionShell.vue
    AtlasPageHeader.vue
    MetricStrip.vue
    DataList.vue
    EmptyState.vue
  index.js
```

Semantic tokens include background, surface, text, muted text, border, accent,
success, warning, danger, typography, spacing, radius, and motion. Components
consume semantic tokens and do not embed raw theme colors.

Native HTML remains the default for simple behavior. Reka UI is used behind the
internal `Ui*` seam for behavior that is difficult to implement accessibly, such
as selects, dialogs, popovers, menus, and tabs. Callers depend on the SoccerOctopus
interface rather than Reka UI anatomy. Reka UI documents its components as
unstyled, accessible primitives with managed focus and keyboard behavior:
[Reka UI getting started](https://reka-ui.com/docs/overview/getting-started).

Do not migrate to Tailwind during the redesign. A styling-framework migration and
visual redesign in the same change would produce a hybrid codebase and obscure
behavioral regressions. Existing scoped CSS can consume the new token layer and
be removed incrementally as views move to shared modules.

## Feature Modules

Feature modules own domain presentation and expose small interfaces to views:

```text
src/features/
  competition-overview/
  groups/
  table/
  predictions/
  tournament/
  markets/
  account/
  billing/
```

Expected domain components include `CompetitionSwitcher`, `GroupStandings`,
`LeagueTable`, `MatchSelector`, `PredictionSummary`, `ProbabilityMeter`,
`AgentBreakdown`, `TournamentBracket`, and `MarketQuestion`.

Views own routing and feature composition. Data access, formatting, capability
checks, and repeated interaction behavior stay behind module interfaces.

## Component Catalogue and Verification

Use Storybook with the Vue 3 Vite framework. Required stories cover:

- Light and dark themes.
- English, Spanish, and a development-only text-expansion locale.
- Default, hover, focus, disabled, loading, empty, and error states.
- Mobile and desktop constraints for layout patterns.

Use the Storybook accessibility and Vitest addons so accessibility violations and
interaction tests can run with the component suite. See the official
[accessibility testing](https://storybook.js.org/docs/writing-tests/accessibility-testing)
documentation.

Application verification includes route tests, locale fallback and completeness
tests, feature-module tests, and end-to-end coverage for the primary prediction,
simulation, market, authentication, and billing workflows.

## Data Contract Requirements

Frontend-facing responses should expose:

- Stable Competition Edition, Team, Match, prediction, and market identifiers.
- Machine-readable outcome, stage, capability, and error codes.
- Raw numeric values for probabilities, money, dates, and rankings.
- Localized generated narrative or enough structured evidence to localize it.

The frontend must not parse English display strings to recover domain state.

## Open Decisions

- Approve Reka UI and Storybook as foundation dependencies.
- Confirm whether English receives an explicit `/en` prefix at cutover.
- Decide whether Team names are localized by the backend or frontend catalogue.
- Decide whether public competition pages require translated path aliases for SEO.
