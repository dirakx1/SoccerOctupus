# Frontend Redesign Documentation

> Status: Active
> Last reviewed: 2026-07-16
> Scope: Multi-competition, localized Tournament Atlas frontend

This directory is the entry point for the frontend redesign. Each document has
one job. Do not copy the same decision or requirement into several documents.

## Documents

| Document | Authority |
|---|---|
| [Current Baseline](current-state.md) | Source-derived inventory of existing routes, workflows, data dependencies, and temporary mockup routes. |
| [Architecture](architecture.md) | Intended frontend structure, module interfaces, routes, localization, design system, and data contracts. |
| [Migration](migration.md) | Delivery sequence, compatibility strategy, verification, and completion criteria. |
| [Visual QA](visual-qa.md) | Dated viewport, theme, locale, interaction, and responsive evidence for the migrated Competition Workspace. |
| [Domain Language](../../CONTEXT.md) | Canonical product terminology only. It contains no implementation details. |
| [ADR-0001](../adr/0001-tournament-atlas-design-direction.md) | Accepted decision to use Tournament Atlas as the production design direction. |

Existing [authentication](../auth-workflow.md) and
[billing](../billing-workflow.md) documents remain authoritative for those
workflows. The redesign must update them when localized routes, shell behavior,
or visible workflow states change.

## Documentation Contract

1. Update documentation in the same change as the behavior it describes.
2. Mark unapproved architecture as `Proposed`; do not present it as implemented.
3. Put durable trade-off decisions in an ADR only after they are accepted.
4. Put current intended structure in `architecture.md`, not in an ADR or plan.
5. Put execution order and temporary compatibility work in `migration.md`.
6. Use terms from `CONTEXT.md`. Resolve terminology conflicts before adding new
   synonyms to code or copy.
7. Link to source files and official external documentation where those links
   reduce ambiguity. Do not paste large implementation excerpts that will drift.
8. Remove superseded instructions or mark them explicitly. Do not append a new
   section that contradicts an older section.
9. Check migrated workflows against `current-state.md`; remove an item only after
   its replacement and compatibility behavior are verified.

## Review Checklist

Every frontend-redesign change must answer these questions:

- Did a route, module interface, locale rule, token, or data contract change?
- Which authoritative document owns that fact?
- Does English and Spanish behavior remain documented and tested?
- Are loading, empty, error, disabled, and authenticated states covered?
- Are legacy routes or temporary adapters still required?
- Does the document describe current behavior rather than the history of edits?
