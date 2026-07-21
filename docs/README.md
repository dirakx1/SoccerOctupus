# Documentation

## Frontend Architecture

- [`frontend-redesign/README.md`](frontend-redesign/README.md) is the maintained
  index for the multi-competition, localized Tournament Atlas redesign.
- [`frontend-redesign/current-state.md`](frontend-redesign/current-state.md)
  inventories the production routes, workflows, data dependencies, and temporary
  design-lab routes that form the migration parity baseline.
- [`frontend-redesign/architecture.md`](frontend-redesign/architecture.md)
  records the proposed frontend structure, route and locale model, design system,
  module interfaces, and data-contract requirements.
- [`frontend-redesign/migration.md`](frontend-redesign/migration.md) defines the
  incremental migration sequence and completion criteria.
- [`../CONTEXT.md`](../CONTEXT.md) defines canonical SoccerOctopus domain terms.
- [`adr/0001-tournament-atlas-design-direction.md`](adr/0001-tournament-atlas-design-direction.md)
  records the accepted client design direction.

## Authentication and Billing

- [`auth-workflow.md`](auth-workflow.md) documents the complete custom Clerk
  sign-in and sign-up workflow, including frontend states, backend user sync,
  webhooks, Client Trust, CAPTCHA, and troubleshooting.
- [`billing-workflow.md`](billing-workflow.md) documents Stripe Billing setup,
  tier behavior, webhook configuration, and local smoke testing.
