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
- Namespaced `common` resources and automated tests for the public localization
  interface.

Remaining localization foundation:

- URL Locale parsing and localized route integration.
- Production message domains added alongside their first translated consumers.
- Translation completeness and locale-formatting tests.
- Localized page content and a Locale switcher, which belong to later migration
  work.

Implemented competition foundation:

- Framework-independent Competition Edition registry and defensive lookup
  interface.
- FIFA World Cup 2026 configuration adapter with stable identifiers,
  `group-and-knockout` format, and current-portal Competition Capabilities.

Deferred competition integration, owned by later migration phases:

- Competition-aware route context and capability-driven navigation.
- Integration with production views and existing endpoint ownership as each
  workflow migrates.
- Additional Competition Edition adapters only when their real requirements and
  data contracts are known.

Deliverables:

- Complete the remaining localization foundation listed above.
- Tournament Atlas semantic tokens for light and dark themes.
- Storybook with accessibility and interaction testing.
- First UI primitives: button, icon button, input, select, tabs, dialog, notice,
  and skeleton.

Exit criteria:

- Every primitive has English and Spanish stories in both themes.
- Keyboard, focus, disabled, loading, and error behavior is verified.
- Missing translations fail automated tests.
- No production view depends directly on Reka UI internals.

## Phase 2: Localized Application Shell

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

Migrate Home and Groups together using real World Cup 2026 data.

Exit criteria:

- Feature parity with existing Home and Groups views.
- Loading, empty, error, and success states are present.
- English and Spanish layouts pass text-expansion checks.
- Light, dark, desktop, tablet, and mobile visual checks pass.
- Existing routes remain usable through redirects.

This phase validates the full route, locale, theme, design-system, feature-module,
and API-adapter path before migrating higher-risk workflows.

## Phase 4: Prediction Workflows

Migration order:

1. Predict Match.
2. Tournament Simulation.
3. Prediction Markets.

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
