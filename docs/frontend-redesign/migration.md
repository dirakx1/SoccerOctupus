# Frontend Redesign Migration

> Status: Proposed
> Last reviewed: 2026-07-16
> Depends on: [Frontend Redesign Architecture](architecture.md)

## Migration Strategy

Build the Tournament Atlas frontend alongside the current frontend. Keep current
routes and behavior available until each replacement workflow reaches parity.
Avoid a repository-wide CSS rewrite or a single cutover release.

Parity is measured against the
[Current Frontend Baseline](current-state.md), plus the authoritative
authentication and billing workflow documents.

Each phase updates this document and the authoritative workflow documentation in
the same change. A phase is complete only when its exit criteria pass.

## Phase 0: Approve the Foundation

Deliverables:

- Approve or revise the proposed architecture choices.
- Validate the current baseline against any frontend changes made since its last
  review.
- Resolve the locale and URL open decisions.
- Confirm Competition Edition terminology and capability definitions.
- Record additional durable decisions as ADRs only when accepted.

Exit criteria:

- Architecture status is updated from `Proposed` where decisions are accepted.
- No unresolved decision blocks route or design-system implementation.
- Every production route and shared behavior has an owning migration phase.

## Phase 1: Platform Foundations

Status: In progress. The localization core is implemented, but Phase 1 is not
complete.

Implemented localization foundation:

- Vue I18n Composition API plugin with `en` and `es` support and English fallback.
- Explicit, saved, browser-preference, and fallback Locale resolution.
- Best-effort preference persistence and document-language updates.
- URL Locale application for canonical Competition Workspace routes.
- Namespaced `common` resources and automated tests for the public localization
  interface.

Remaining localization foundation:

- Localized route integration for authentication, account, legal, and other
  public workflows.
- Production `home` and `groups` message domains added alongside their first
  translated consumers; remaining domains are added with later slices.
- Translation completeness and locale-formatting tests.
- Localized page content and a Locale switcher, which belong to later migration
  work.

Implemented competition foundation:

- Framework-independent Competition Edition registry and defensive lookup
  interface.
- FIFA World Cup 2026 configuration adapter with stable identifiers,
  `group-and-knockout` format, and current-portal Competition Capabilities.

Deferred competition integration, owned by later migration phases:

- Capability-driven navigation from the active Competition Edition.
- Integration with production views and existing endpoint ownership as each
  workflow migrates.
- Additional Competition Edition adapters only when their real requirements and
  data contracts are known.

Implemented theme foundation:

- Tournament Atlas semantic tokens for typography, spacing, radii, borders,
  shadows, motion, controls, icons, layering, and semantic colors.
- Light and dark theme maps with a `system` preference and a framework-independent
  runtime that initializes before Vue mounts.
- Best-effort preference persistence and root `data-theme`/`color-scheme`
  updates, with focused tests for fallback and failure behavior.

Deferred theme integration, owned by later migration phases:

- Migrating production views and shared modules from page-local colors to
  semantic tokens.
- A visible theme control and live updates when the operating-system preference
  changes.
- Shared primitives, component states, and Storybook coverage in both themes.

Deliverables:

- Complete the remaining localization foundation listed above.
- Storybook with accessibility and interaction testing.
- First UI primitives: button, icon button, input, select, tabs, dialog, notice,
  and skeleton.

Exit criteria:

- Every primitive has English and Spanish stories in both themes.
- Keyboard, focus, disabled, loading, and error behavior is verified.
- Missing translations fail automated tests.
- No production view depends directly on Reka UI internals.

## Phase 2: Localized Application Shell

Status: In progress. The Competition Workspace URL layer and shell are
implemented; Home and Groups are the first localized production consumers.

Implemented routing foundation:

- Canonical `en` and `es` Competition Workspace routes for overview, Groups,
  Match Prediction, Knockout Bracket, and Markets using existing production
  views.
- Stable route names and a registry-derived `workspaceLocation` helper for
  redirects and future shell callers.
- Registry-backed unknown and blank Competition Edition fallback to the
  same-locale World Cup overview.
- Root and flat workflow redirects with query/hash preservation, including
  `/tournament` to canonical `/bracket`.
- URL Locale application before auth handling and full canonical post-auth
  destination preservation for protected workspace routes.

Implemented shell foundation:

- `AppShell` and `CompetitionShell` presentational patterns using Tournament
  Atlas semantic tokens and Lucide controls, with a compact inline desktop
  header and expanded mobile navigation panel.
- Capability-derived workspace navigation and visible current Competition Edition
  dropdown, with no unsupported table or fixtures links.
- English and Spanish shell navigation, account, footer, auth-recovery, theme,
  and mobile-control messages.
- Keyboard-accessible icon-only Locale and light/dark/system theme controls with
  labeled menus. Locale changes preserve the current named workspace route,
  Competition Edition, query, and hash; theme changes persist through the
  existing runtime without OS listeners.

Remaining Phase 2 work:

- Localized authentication, account, billing, admin, legal, and public routes.
- Page translations, localized metadata, and localized route aliases if later
  requirements justify aliases.
- Migrating remaining page-local styles and copy into the shell and shared
  design-system patterns.

Deliverables:

- `AppShell` and `CompetitionShell`.
- Competition, locale, theme, and account controls.
- Capability-driven Competition Workspace navigation.
- Localized canonical routes and legacy redirects.
- Locale-preserving authentication and billing redirects.

Exit criteria:

- Direct navigation and refresh work for English and Spanish routes.
- Unsupported Competition Capabilities produce a helpful localized state.
- Signed-in, signed-out, admin, billing-attention, and mobile shell states pass.
- Existing authentication and billing workflow documents are updated.

## Phase 3: First Vertical Slice

Status: In progress. Home and Groups implementation and behavior parity are
landed; visual QA across all required themes and viewport sizes remains before
this phase can be marked complete. The current live matrix is recorded as
blocked in [Visual QA](visual-qa.md).

Implemented:

- Home uses the real SoccerOctopus/FIFA World Cup 2026 scope, four current
  workflow destinations, five current Swarm Agent roles with their existing
  weights and descriptions, and the existing Video Agent modal behavior.
- Home workflow links use `workspaceLocation` with the active Locale and
  Competition Edition rather than flat legacy URLs.
- Groups keeps `GET /api/predictions/groups`, descending ELO sorting, and the
  Team/ELO/rank fields while adding dynamic group/team counts, semantic tables,
  loading skeletons, an empty state, and retryable inline errors.
- English and Spanish page message domains and focused component tests cover
  canonical Home links, localized copy, modal access, Groups success/sorting,
  loading, empty, error/retry, and localized output.
- Cookie Banner and Video Agent evidence overlays consume Atlas tokens and the
  English/Spanish `overlays` domain. Consent storage semantics, blocked-storage
  fallback, source evidence, dialog/lightbox keyboard behavior, focus lifecycle,
  and scroll lock have focused component coverage.

Remaining before completion:

- Complete light, dark, desktop, tablet, mobile, and text-expansion visual QA.
- Confirm direct navigation and refresh behavior for both migrated routes in
  the running application.
- Keep account, authentication, admin, billing-page, and other public routes
  explicitly pending their own migration slices.
- Keep authentication controls, reverification, password policy, and two-factor
  settings pending their own shared-component migrations.

Exit criteria:

- Feature parity with existing Home and Groups views.
- Loading, empty, error, and success states are present.
- English and Spanish layouts pass text-expansion checks.
- Light, dark, desktop, tablet, and mobile visual checks pass.
- Existing routes remain usable through redirects.

This phase validates the full route, locale, theme, design-system, feature-module,
and API-adapter path before migrating higher-risk workflows.

## Phase 4: Prediction Workflows

Status: In progress. Predict Match, the combined live-results / Tournament
Simulation workflow, and Prediction Markets are migrated. Phase 4 remains open
for generated-text localization and visual QA. The current live matrix is
blocked as documented in [Visual QA](visual-qa.md).

Implemented for Predict Match:

- Existing team-list and Match Prediction endpoints, request payload, result
  fields, billing codes, recovery actions, and Pricing link behavior are
  preserved.
- English/Spanish frontend copy, locale-aware numeric presentation, distinct-team
  validation, team-feed states, long-running state, run error, complete result
  rendering, and four-specialized-agent agreement have focused tests.
- `ProbMeter`, `BillingStatusNotice`, and `BillingPlansLink` use Atlas tokens and
  localized labels without changing their interfaces for other callers.

Implemented for live Tournament results and Tournament Simulation:

- The exact live-results GET and Tournament Simulation POST contracts, boolean
  swarm payload, returned podium/knockout fields, billing codes, recovery action,
  and Pricing route are preserved.
- The English/Spanish `tournament` domain, locale-aware numeric presentation,
  accessible keyboard tabs, live loading/empty/error/retry states, stable
  long-running state, run error, and pre-run state have focused coverage.
- Live standings expose ordered positions without implying qualification.
  Official knockout results take precedence, are labeled official/final, and do
  not show prediction probabilities. Predicted matches retain the returned score,
  outcome, and home/draw/away probabilities in backend stage order.
- `TournamentBracket` is a feature-local presentation module. It renders the
  response-derived champion, runner-up, and third place, with only the returned
  champion final-win probability, and contains horizontal bracket overflow on
  narrow viewports.

Implemented for Prediction Markets:

- The exact team GET, three-field Match Markets POST, and bodyless Tournament
  Markets POST contracts remain unchanged, including all three billing codes.
- Match and Tournament modes preserve their filters, counts, summary fields,
  binary questions, categorical winner outcomes, Question IDs, dates,
  probabilities, platform prices, and Resolution Criteria.
- `MarketCard` retains its public `question` prop and adds localized type labels,
  accessible probability meters, keyboard criteria disclosure, and clipboard
  success/failure feedback without rewriting source-generated fields.

Current limitation:

- The backend does not accept Locale for Match Prediction or Market generation.
  Swarm Consensus, Key Factors, Agent reasoning, Market Questions, and Resolution
  Criteria remain English/source values. The frontend does not add unsupported
  payload fields; locale-aware generation remains required before this phase can
  satisfy the generated-text exit criterion.

Migration order:

1. Predict Match. Implemented; visual QA remains.
2. Tournament live results and Simulation. Implemented; visual QA remains.
3. Prediction Markets. Implemented; visual QA remains.

Exit criteria for each workflow:

- Existing requests, billing gates, and result fields remain unchanged or use a
  documented adapter.
- Generated narrative follows the selected locale.
- Error codes map to complete English and Spanish messages.
- Loading and long-running states do not shift the Atlas layout.
- Primary interactions have integration and end-to-end coverage.

## Phase 5: Account and Public Workflows

Migrate pricing, profile, authentication, billing success, contact, about, legal,
and cookie-policy views after the Competition Workspace is stable.

Legal and billing translations require content review; they must not be treated as
literal UI-string translation tasks.

Exit criteria:

- Authentication and billing documentation matches localized behavior.
- Consent and legal copy is approved in both locales.
- Post-auth and checkout redirects preserve locale and intended destination.

## Phase 6: Cutover and Cleanup

Deliverables:

- Make localized Competition Workspace routes canonical.
- Preserve legacy redirects for the agreed compatibility period.
- Remove obsolete page-level styles and mockup-only routes.
- Update metadata, sitemap, analytics paths, and deployment routing.

Exit criteria:

- Production build, unit tests, component tests, and end-to-end tests pass.
- No untranslated user-facing strings remain in production views.
- No view duplicates a primitive or design token owned by the design system.
- Documentation describes the resulting system, not the migration history.
- Rollback steps and the legacy-route removal date are recorded.

## Documentation in Every Change

Every implementation change must update documentation when it changes:

- Domain terminology.
- An accepted architectural decision.
- A module interface or ownership seam.
- Route, locale, fallback, or redirect behavior.
- Competition Capability behavior.
- Design tokens or component states.
- Authentication, billing, legal, or deployment workflows.

Pull-request review should reject code whose authoritative documentation is stale,
and documentation that describes behavior not covered by code or tests.
