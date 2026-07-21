# Stripe Billing Workflow

SoccerOctopus uses Stripe-hosted Checkout and Customer Portal for subscription
billing. The app does not collect card details, generate invoice PDFs, or mutate
subscriptions directly from custom UI in this release.

## Tiers

| Tier | Price | Access |
|---|---:|---|
| Free | USD 0 | Browse signed-in account pages, no paid prediction runs. |
| Basic | USD 5/month | Prediction and market-generation workflows without YouTube video analysis. |
| Pro | USD 10/month | Prediction and market-generation workflows with YouTube video analysis. |

Admins bypass subscription checks for operational testing.

## Environment Variables

```env
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_BASIC_PRICE_ID=
STRIPE_PRO_PRICE_ID=
STRIPE_BILLING_PORTAL_CONFIGURATION_ID=
```

Stripe secrets stay in deployment env, not `/admin/settings`. Stripe price IDs
are not secret, but they are account-specific and should be configured through
env for each Stripe account.

Local secret hygiene: `.env:1`, `.env:3`, and `.env:4` contain local
auth/database secret types. Rotate those credentials before production billing
setup if they were exposed outside the local machine.

## Stripe Dashboard Setup

1. Create a Basic product with a recurring USD 5 monthly price.
2. Create a Pro product with a recurring USD 10 monthly price.
3. Set `STRIPE_BASIC_PRICE_ID` and `STRIPE_PRO_PRICE_ID` from those recurring
   price IDs.
4. Enable Customer Portal plan changes and cancellation for the Basic/Pro
   products.
5. Add a webhook endpoint: `<backend-origin>/api/webhooks/stripe`.
6. Subscribe the endpoint to:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
7. Set `STRIPE_WEBHOOK_SECRET` from that endpoint.

## Local Smoke Test

1. Set test-mode Stripe env vars.
2. Start the app with `npm run dev`.
3. If Stripe CLI is available, run:

   ```bash
   stripe listen --forward-to localhost:5002/api/webhooks/stripe
   ```

4. Visit `/pricing` while signed out.
5. Choose Basic, sign up, and confirm redirect to Stripe Checkout.
6. Complete Checkout with a Stripe test card.
7. Return to `/billing/success?session_id={CHECKOUT_SESSION_ID}`, then `/profile`.
8. Run a prediction and confirm no `Video Intelligence Agent` appears in the
   agent breakdown.
9. Use the Billing section on the Profile page to change to Pro.
10. Confirm webhook sync changes the local tier and a new prediction includes
    `Video Intelligence Agent`.
11. Use the portal cancel flow and confirm local subscription becomes free after
    webhook sync.

## Pricing Surface

`/pricing` is a public Tournament Atlas page. It uses the active persisted
Locale (English or Spanish) for its frontend-owned page, plan-note, action,
loading, and error copy. Server-provided plan labels, prices, intervals, and
feature strings remain verbatim so that billing configuration stays the single
source of truth.

For a signed-out paid-plan choice, the page stores the exact local return path
`/pricing?plan={basic|pro}&checkout=1` before sending the user to sign-up. Once
signed in, it removes only `checkout=1`, then calls the existing plan-change
endpoint. A signed-in selection uses the existing `POST /api/billing/change-plan`
request and follows a returned Stripe URL unchanged. Choosing Free while paid
continues to use that same plan-change path, including a returned cancellation
portal URL. No Locale, return-path, or extra frontend field is sent to the
billing endpoint.

## Checkout Return

`/billing/success` is a signed-in route. Stripe supplies `session_id` through
the configured success URL; the frontend sends it unchanged to
`GET /api/billing/checkout-session/{session_id}`. The backend verifies that the
Stripe session belongs to the current user, synchronizes the embedded
subscription when available, and returns the current serialized subscription.

The localized Tournament Atlas return screen uses the active persisted Locale
(English or Spanish) for its frontend-owned pending, confirmed, missing-session,
and retry labels. It does not pass Locale to Stripe or add client-side billing
state. A missing or failed verification retains any backend error detail and
offers one manual recheck. The original 3.5-second return to `/profile` remains
in effect after success, failure, a missing session ID, or a manual retry; the
Stripe webhook may complete reconciliation asynchronously after a failed check.
