# Frontend Redesign Architecture

> Status: Tournament Atlas, the localization core, and the Competition registry
> are accepted; remaining architecture is proposed
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
| Localization | Vue I18n Composition API with English fallback | Core implemented; routes and page content pending |
| Competition registry | Internal plain-JavaScript registry with a World Cup 2026 configuration adapter | Implemented; route, navigation, and view integration pending |
| Canonical routes | Locale-prefixed Competition Workspace routes | Proposed |
| Design system | Internal SoccerOctopus modules using semantic CSS tokens | Proposed |
| Accessible primitives | Reka UI wrapped behind internal interfaces | Proposed |
| Component catalogue | Storybook for Vue 3 and Vite | Proposed |
| Styling migration | Keep Vue scoped CSS; introduce global tokens and foundations | Proposed |

Vue I18n is approved and installed. Other proposed dependencies remain
unapproved and must not be installed until their architecture is accepted.

## Route Model

Canonical Competition Workspace routes use stable, untranslated path segments:

```text
/:locale(en|es)/competitions/:competitionEditionSlug
/:locale(en|es)/competitions/:competitionEditionSlug/groups
/:locale(en|es)/competitions/:competitionEditionSlug/table
/:locale(en|es)/competitions/:competitionEditionSlug/fixtures
/:locale(en|es)/competitions/:competitionEditionSlug/predict
/:locale(en|es)/competitions/:competitionEditionSlug/bracket
/:locale(en|es)/competitions/:competitionEditionSlug/markets
```

Spanish changes the navigation labels and content, not the resource identifiers.
For example, `/es/competitions/world-cup-2026/groups` displays `Grupos`. Localized
path aliases can be added later if search requirements justify their complexity.

Current flat routes redirect to their World Cup 2026 equivalents during migration:

```text
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

A locale switch preserves the named route, Competition Edition, query, and hash.
Authentication redirects must preserve the full localized destination.

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

The registry does not fetch data, build navigation, change routes, or adapt API
requests. Current views retain their existing endpoint calls. Navigation and
endpoint/view integration are later migration work; do not add a speculative
data-fetching seam before a second real adapter requires one.

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
    es/
      common.json
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
preferences and installs the plugin. URL Locale input is not connected until
localized routing is implemented. Browser-storage failures do not prevent startup
or document-language updates.

Only the `common` domain exists today because no production view has been
translated. Add another domain file in both Locales when its first real consumer
is migrated; do not create empty resource files in advance.

Pending localization rules:

- Use locale-aware date, number, percentage, and currency formatting.
- Translation keys describe meaning, not English wording.
- Missing Spanish messages fail CI once production message domains are added.
- Components receive IDs, values, and error codes rather than preformatted English.
- API errors use stable codes that map to localized frontend messages.
- Match Prediction requests include locale for Swarm Consensus and key factors.
- Cached generated narrative is keyed by locale.
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
