# Tournament Atlas Visual QA

> Status: Partial; protected routes and remaining matrix cells blocked
> QA date: 2026-07-16
> Fixed point: `35adbbec7d9ec6e1f2a6cae026aa3f0b74de4c74`
> Target: `http://localhost:3001`

This document is the authoritative visual QA record for the migrated Competition
Workspace. A blocked cell is not a pass. Phase 3 and Phase 4 visual gates remain
open until the incomplete cells are rerun in the in-app browser.

## Environment

The required in-app browser runtime was initialized through the bundled Browser
plugin. Browser selection failed because `iab` was unavailable, and the required
one-time browser discovery returned an empty list. No alternate browser backend
was used because that would not preserve the required in-app session or evidence
surface.

The development target was already listening on port 3001. The execution agent's
browser remained unavailable, but the root session later recovered the in-app
browser and supplied the limited live evidence recorded below.

## Live Matrix

Every cell below requires a screenshot or direct DOM observation, including the
page-level `scrollWidth <= clientWidth` assertion. All cells are blocked by the
same unavailable in-app browser, not by an application failure.

| Surface | Viewport | Locale / theme | Status | Evidence still required |
|---|---:|---|---|---|
| Shell, Home, Cookie Banner, footer | 1440 x 900 | EN / light | Blocked | Required viewport/theme cell was not captured. |
| Shell, Home, Video Agent modal/lightbox | 1440 x 900 | ES / dark | Blocked | Spanish expansion, modal focus/layers, screenshots, lightbox controls, and contrast. |
| Shell and Home | 905 x 863 | EN / light | Blocked | Feedback-width header composition, menu placement, workflow layout, and page overflow. |
| Shell, Home, Banner, modal/lightbox | 390 x 844 | EN / light | Partial | Home has no page overflow; remaining interactions and post-fix modal recheck are incomplete. |
| Shell, Home, Banner, modal/lightbox | 390 x 844 | ES / dark | Partial | Home has no page overflow; dark modal layering/DOM and settled Cookie Banner are readable. Remaining interaction sequence is incomplete. |
| Shell, Home, Banner, modal/lightbox | 390 x 844 | ES / light | Partial | Post-fix browser recheck passed: dialog and headings compute to `rgb(36, 32, 28)` on `rgb(255, 253, 248)`, and the screenshot confirms readable modal headings/layout. Remaining interaction sequence is incomplete. |
| Shell and Home static minimum | 320 x 700 | EN / light | Partial | Page-level overflow passes with `scrollWidth = clientWidth = 320`; remaining controls were not exercised. |
| Groups tables and states | 1440 x 900, 905 x 863, 390 x 844 | EN light / ES dark | Auth blocked | `/es/competitions/world-cup-2026/groups` redirected to flat `/sign-in`; no credentials were invented. |
| Predict form, billing, and result states | 1440 x 900, 390 x 844 | EN light / ES dark | Auth blocked | Protected Competition Workspace route; no sign-in credentials were available and no prediction run was made. |
| Tournament tabs, tables, bracket, billing | 1440 x 900, 905 x 863, 390 x 844 | EN light / ES dark | Auth blocked | Protected Competition Workspace route; no sign-in credentials were available and no simulation was run. |
| Markets modes, filters, table, cards, billing | 1440 x 900, 905 x 863, 390 x 844 | EN light / ES dark | Auth blocked | Protected Competition Workspace route; no sign-in credentials were available and no market run was made. |
| Locale and theme persistence | 1440 x 900, 390 x 844 | EN/ES and light/dark/system | Blocked | Switch controls must preserve route, query, hash, and stable header dimensions. |
| Keyboard sequence | Desktop and mobile emulation | EN / light | Blocked | Visible focus, menu/tab selection, modal/lightbox focus lifecycle, and Escape behavior. |

No credentials were invented, authentication was not bypassed, and no paid,
prediction, simulation, or market-generation request was made for QA.

Supplemental live checks at 1280px desktop and 390px mobile found no Home page
horizontal overflow in English dark mode. Spanish Home also passed page overflow
in dark and light mobile modes. The settled Cookie Banner was opaque and readable,
and modal layering/DOM structure was verified. These supplemental observations do
not replace missing required viewport/theme/interaction cells. The unauthenticated
redirect target `/sign-in` remains English and uses the legacy presentation; it is
outside this Competition Workspace QA scope.

## Static Audit

Static inspection is supporting evidence only; it does not convert a live cell
to a pass.

| Check | Result | Evidence |
|---|---|---|
| Legacy colors, gradients, decorative emoji/glyph controls | Pass | No hard-coded color values, gradients, or emoji controls were found in the scoped migrated files. |
| Shadows | Pass | Scoped shadows use `--shadow-md` or `--shadow-lg`. |
| Negative letter spacing and viewport-scaled type | Pass | Neither pattern appears in the scoped migrated files. |
| Page and data-surface containment | Pass by source inspection | Groups, Tournament standings, Tournament Bracket, and Markets winner tables contain wide content in explicit internal horizontal scrollers. Live page-width assertions remain blocked. |
| Responsive structure | Pass by source inspection | Shell, pages, modal/lightbox, banner, cards, tables, and bracket define scoped tablet/mobile breakpoints. Live Spanish expansion remains blocked. |
| Layer ownership | Pass by source inspection | Shell, dropdown, overlay, modal, and lightbox use semantic z-index tokens; the lightbox is above the modal. Live stacking remains blocked. |
| Touch target minimum | Fixed | Migrated 40px or unconstrained interactive targets now use the existing 48px `--control-height-lg` token. |

## Fixes Applied

- Increased the brand target, Competition selector, locale/theme/account/mobile
  controls, and dropdown/account-menu items to a 48px minimum touch dimension.
- Increased shell authentication retry, Groups retry, Tournament retry, Markets
  platform links and filter controls to 48px minimum height.
- Added a 48px minimum height to MarketCard Resolution Criteria and Copy ID
  controls.
- Set the teleported Video Agent dialog's text color explicitly to
  `--color-text`, preventing legacy body color inheritance in light mode.

These are presentation-only changes. They do not alter routes, API payloads,
authentication, billing, source data, or component events.

## Residual Risks

- Live evidence covers only the Home overflow, settled Cookie Banner, and partial
  modal cells described above; the required matrix is incomplete.
- The corrected ES light mobile modal color and layout passed browser recheck;
  other required modal viewport/theme combinations remain incomplete.
- Required desktop/tablet combinations, menu placement, focus visibility, and
  complete Spanish expansion remain unverified at runtime.
- Protected-route matrix cells remain blocked by the unauthenticated redirect.
- Loading, empty, error, billing, and result states are behavior-tested but not
  visually observed in the required browser matrix.
- Backend-generated Match Prediction and Market Question text remains source
  English, as documented in the architecture.

## Gate Decision

Phase 3 and Phase 4 visual criteria do not close. Rerun this matrix when the
in-app browser is available, replace each blocked status with pass or fail based
on direct evidence, attach observations, and fix verified failures before closing
either gate.
