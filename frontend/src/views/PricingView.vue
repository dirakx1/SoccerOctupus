<template>
  <main class="pricing-page" aria-labelledby="pricing-title">
    <header class="pricing-intro">
      <div>
        <p class="atlas-kicker">{{ t('pricing.eyebrow') }}</p>
        <h1 id="pricing-title">{{ t('pricing.title') }}</h1>
        <p>{{ t('pricing.subtitle') }}</p>
      </div>
      <router-link v-if="auth.state.signedIn" class="profile-link" to="/profile">
        <span>{{ t('pricing.profile') }}</span>
        <CreditCard :size="18" aria-hidden="true" />
      </router-link>
    </header>

    <section v-if="plansLoading" class="pricing-state" aria-busy="true" aria-live="polite">
      <LoaderCircle :size="24" class="spin" aria-hidden="true" />
      <div>
        <h2>{{ t('pricing.loading') }}</h2>
        <p>{{ t('pricing.loadingCopy') }}</p>
      </div>
    </section>

    <section v-else-if="loadError" class="pricing-state pricing-state-error" role="alert">
      <div>
        <h2>{{ t('pricing.loadError') }}</h2>
        <p>{{ loadError }}</p>
      </div>
      <button class="btn-secondary" type="button" @click="loadPlans">
        <RefreshCw :size="17" aria-hidden="true" />
        {{ t('pricing.retry') }}
      </button>
    </section>

    <template v-else>
      <p v-if="error" class="error-box" role="alert">{{ error }}</p>

      <section class="plans-grid" aria-label="Subscription plans">
        <article
          v-for="plan in plans"
          :key="plan.tier"
          class="plan-card"
          :class="{ featured: plan.tier === 'pro', current: isCurrentTier(plan.tier) }"
        >
          <p v-if="plan.tier === 'pro'" class="featured-label">{{ t('pricing.featured') }}</p>
          <div class="plan-top">
            <h2>{{ plan.label }}</h2>
            <p class="plan-note">{{ planNote(plan.tier) }}</p>
            <p class="price">
              <span>{{ plan.display_price }}</span>
              <small>{{ t('pricing.perInterval', { interval: plan.interval }) }}</small>
            </p>
          </div>
          <ul>
            <li v-for="feature in plan.features" :key="feature">
              <Check :size="16" aria-hidden="true" />
              <span>{{ feature }}</span>
            </li>
          </ul>
          <button
            class="btn-primary"
            :disabled="loadingTier === plan.tier || isCurrentTier(plan.tier)"
            :aria-label="ctaText(plan.tier)"
            :title="ctaText(plan.tier)"
            @click="choosePlan(plan.tier)"
          >
            <LoaderCircle v-if="loadingTier === plan.tier" :size="18" class="spin" aria-hidden="true" />
            <template v-else>
              <span>{{ ctaText(plan.tier) }}</span>
              <Check v-if="isCurrentTier(plan.tier)" :size="18" aria-hidden="true" />
              <component v-else :is="ctaIcon(plan.tier)" :size="18" aria-hidden="true" />
            </template>
          </button>
        </article>
      </section>
    </template>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, Check, CreditCard, LoaderCircle, LogIn, RefreshCw } from '@lucide/vue'

import { changePlan, getPlans, getSubscription } from '../lib/billing'
import { useAuthState } from '../lib/auth'
import { setPostAuthRedirect } from '../lib/postAuthRedirect'

const auth = useAuthState()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const plans = ref([])
const error = ref('')
const loadError = ref('')
const plansLoading = ref(true)
const loadingTier = ref('')
const currentTier = ref('')
let checkoutStarted = false

function isCurrentTier(tier) {
  return auth.state.signedIn && currentTier.value === tier
}

function ctaText(tier) {
  if (loadingTier.value === tier) return t('pricing.actions.updating')
  if (isCurrentTier(tier)) return t('pricing.actions.current')
  if (tier === 'free') return auth.state.signedIn ? t('pricing.actions.choose') : t('pricing.actions.start')
  return auth.state.signedIn ? t('pricing.actions.choose') : t('pricing.actions.signUp')
}

function ctaIcon() {
  return auth.state.signedIn ? ArrowRight : LogIn
}

function planNote(tier) {
  return t(`pricing.notes.${tier}`)
}

async function submitPlanChange(tier) {
  loadingTier.value = tier
  error.value = ''
  try {
    const res = await changePlan(tier)
    if (res.data.url) {
      window.location.assign(res.data.url)
      return
    }
    if (res.data.subscription?.tier) {
      currentTier.value = res.data.subscription.tier
    }
  } catch (err) {
    error.value = err.response?.data?.error || err.message || t('pricing.errors.update')
  } finally {
    loadingTier.value = ''
  }
}

async function choosePlan(tier) {
  if (isCurrentTier(tier)) return

  if (tier === 'free') {
    if (!auth.state.signedIn) {
      router.push('/sign-up')
      return
    }
    if (currentTier.value === 'free') {
      router.push('/')
      return
    }
    await submitPlanChange(tier)
    return
  }

  if (!auth.state.signedIn) {
    setPostAuthRedirect(`/pricing?plan=${tier}&checkout=1`)
    router.push('/sign-up')
    return
  }

  await submitPlanChange(tier)
}

async function startCheckoutFromRoute() {
  const plan = route.query.plan
  if (auth.state.signedIn && route.query.checkout === '1' && ['basic', 'pro'].includes(plan) && !checkoutStarted) {
    checkoutStarted = true
    router.replace({ path: '/pricing', query: { plan } })
    await submitPlanChange(plan)
  }
}

async function loadPlans() {
  plansLoading.value = true
  loadError.value = ''
  try {
    const requests = [getPlans()]
    if (auth.state.signedIn) {
      requests.push(getSubscription())
    }
    const [plansRes, subscriptionRes] = await Promise.all(requests)
    plans.value = plansRes.data.plans
    currentTier.value = subscriptionRes?.data?.tier || ''
  } catch (err) {
    loadError.value = err.response?.data?.error || t('pricing.loadError')
  } finally {
    plansLoading.value = false
  }
}

onMounted(async () => {
  await loadPlans()
  await startCheckoutFromRoute()
})
</script>

<style scoped>
.pricing-page { display: flex; flex-direction: column; gap: var(--space-8); margin: 0 auto; max-width: 72rem; padding: var(--space-8) 0 var(--space-12); }
.pricing-intro { align-items: end; border-bottom: var(--border-width-strong) solid var(--color-border-strong); display: flex; gap: var(--space-6); justify-content: space-between; padding-bottom: var(--space-6); }
.atlas-kicker,.featured-label { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs)/var(--line-height-normal) var(--font-family-data); letter-spacing: 0; margin: 0 0 var(--space-2); text-transform: uppercase; }
.pricing-intro h1,.plan-card h2,.pricing-state h2 { color: var(--color-text); font-family: var(--font-family-display); margin: 0; }
.pricing-intro h1 { font-size: var(--font-size-4xl); line-height: var(--line-height-tight); }
.pricing-intro > div > p:not(.atlas-kicker) { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-relaxed); margin: var(--space-3) 0 0; max-width: 45rem; }
.profile-link,.btn-primary,.btn-secondary { align-items: center; border: var(--border-width-thin) solid transparent; border-radius: var(--radius-md); cursor: pointer; display: inline-flex; font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); gap: var(--space-2); justify-content: center; min-height: var(--control-height-lg); padding: 0 var(--space-4); text-decoration: none; }
.profile-link,.btn-secondary { background: transparent; border-color: var(--color-border-strong); color: var(--color-text); }
.profile-link:hover,.btn-secondary:hover:not(:disabled) { background: var(--color-surface-inset); }
.btn-primary { background: var(--color-accent); color: var(--color-accent-contrast); }
.btn-primary:hover:not(:disabled) { background: var(--color-accent-hover); transform: translateY(-1px); }
.btn-primary:disabled { cursor: default; opacity: .55; }
.profile-link:focus-visible,.btn-primary:focus-visible,.btn-secondary:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.plans-grid { display: grid; gap: var(--space-5); grid-template-columns: repeat(3, minmax(0, 1fr)); }
.plan-card { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); display: flex; flex-direction: column; gap: var(--space-6); min-height: 25rem; padding: var(--space-6); position: relative; }
.plan-card.featured { border-color: var(--color-accent); border-top-width: var(--border-width-strong); }
.plan-card.current { background: var(--color-surface-raised); }
.featured-label { margin: 0; position: absolute; right: var(--space-5); top: var(--space-4); }
.plan-top { display: flex; flex-direction: column; gap: var(--space-2); }
.plan-card h2 { font-size: var(--font-size-2xl); line-height: var(--line-height-tight); }
.plan-note { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-normal); margin: 0; }
.price { align-items: baseline; display: flex; gap: var(--space-1); margin: var(--space-3) 0 0; }
.price span { color: var(--color-accent); font: var(--font-weight-heavy) var(--font-size-5xl)/1 var(--font-family-data); }
.price small { color: var(--color-text-muted); font-size: var(--font-size-sm); }
ul { border-top: var(--border-width-thin) solid var(--color-border); color: var(--color-text-muted); display: flex; flex: 1; flex-direction: column; gap: var(--space-3); list-style: none; margin: 0; padding: var(--space-5) 0 0; }
li { align-items: flex-start; display: flex; font-size: var(--font-size-sm); gap: var(--space-2); line-height: var(--line-height-normal); }
li svg { color: var(--color-success); flex: 0 0 auto; margin-top: 2px; }
.pricing-state { align-items: center; background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); display: flex; gap: var(--space-4); min-height: 10rem; padding: var(--space-6); }
.pricing-state > svg { color: var(--color-accent); flex: 0 0 auto; }
.pricing-state h2 { font-size: var(--font-size-xl); }
.pricing-state p { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-relaxed); margin: var(--space-2) 0 0; }
.pricing-state-error { border-color: var(--color-danger); color: var(--color-danger); justify-content: space-between; }
.pricing-state-error h2 { color: var(--color-danger); }
.error-box { background: var(--color-danger-surface); border: var(--border-width-thin) solid var(--color-danger); color: var(--color-danger); font-size: var(--font-size-sm); margin: 0; padding: var(--space-3); }
.spin { animation: spin .9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media(prefers-reduced-motion:reduce) { .spin { animation: none; }.btn-primary { transition: none; } }
@media(max-width:820px) { .plans-grid { grid-template-columns: 1fr; }.plan-card { min-height: auto; }.pricing-intro { align-items: flex-start; flex-direction: column; }.pricing-state-error { align-items: flex-start; flex-direction: column; } }
@media(max-width:640px) { .pricing-page { padding-top: var(--space-5); }.pricing-intro h1 { font-size: var(--font-size-3xl); }.profile-link,.btn-primary,.btn-secondary { width: 100%; }.featured-label { position: static; }.plan-card { padding: var(--space-5); } }
</style>
