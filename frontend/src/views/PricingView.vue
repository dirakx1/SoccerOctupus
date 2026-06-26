<template>
  <div class="pricing-view">
    <section class="page-header">
      <div>
        <p class="eyebrow">Billing</p>
        <h1>Choose prediction access</h1>
        <p class="subtitle">Free includes cycle-limited access. Paid tiers remove usage caps; Pro adds video analysis.</p>
      </div>
      <router-link v-if="auth.state.signedIn" class="icon-link" to="/profile">
        <span>Billing</span>
        <CreditCard :size="18" aria-hidden="true" />
      </router-link>
    </section>

    <p v-if="error" class="error-box">{{ error }}</p>

    <section class="plans-grid">
      <article v-for="plan in plans" :key="plan.tier" class="plan-card" :class="{ featured: plan.tier === 'pro' }">
        <div class="plan-top">
          <h2>{{ plan.label }}</h2>
          <p class="plan-note">{{ planNote(plan.tier) }}</p>
          <div class="price">
            <span>{{ plan.display_price }}</span>
            <small>/{{ plan.interval }}</small>
          </div>
        </div>
        <ul>
          <li v-for="feature in plan.features" :key="feature">{{ feature }}</li>
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
            <component :is="ctaIcon(plan.tier)" :size="18" aria-hidden="true" />
          </template>
        </button>
      </article>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, CreditCard, LoaderCircle, LogIn } from '@lucide/vue'

import { changePlan, getPlans, getSubscription } from '../lib/billing'
import { useAuthState } from '../lib/auth'
import { setPostAuthRedirect } from '../lib/postAuthRedirect'

const auth = useAuthState()
const route = useRoute()
const router = useRouter()
const plans = ref([])
const error = ref('')
const loadingTier = ref('')
const currentTier = ref('')
let checkoutStarted = false

function isCurrentTier(tier) {
  return auth.state.signedIn && currentTier.value === tier
}

function ctaText(tier) {
  if (loadingTier.value === tier) return 'Updating'
  if (tier === 'free') return auth.state.signedIn ? 'Choose' : 'Start'
  return auth.state.signedIn ? 'Choose' : 'Sign up'
}

function ctaIcon(tier) {
  if (tier === 'free') return auth.state.signedIn ? ArrowRight : LogIn
  return auth.state.signedIn ? ArrowRight : LogIn
}

function planNote(tier) {
  if (tier === 'free') return 'Starter quota'
  if (tier === 'basic') return 'Unlimited core access'
  if (tier === 'pro') return 'Full signal coverage'
  return ''
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
    error.value = err.response?.data?.error || err.message || 'Unable to update billing.'
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

onMounted(async () => {
  try {
    const requests = [getPlans()]
    if (auth.state.signedIn) {
      requests.push(getSubscription())
    }
    const [plansRes, subscriptionRes] = await Promise.all(requests)
    plans.value = plansRes.data.plans
    currentTier.value = subscriptionRes?.data?.tier || ''
  } catch (err) {
    error.value = 'Could not load plans.'
  }

  const plan = route.query.plan
  if (auth.state.signedIn && route.query.checkout === '1' && ['basic', 'pro'].includes(plan) && !checkoutStarted) {
    checkoutStarted = true
    router.replace({ path: '/pricing', query: { plan } })
    await submitPlanChange(plan)
  }
})
</script>

<style scoped>
.pricing-view { display: flex; flex-direction: column; gap: 24px; }
.page-header { align-items: flex-start; display: flex; justify-content: space-between; gap: 20px; }
.eyebrow { color: #e2b714; font-size: 12px; font-weight: 800; letter-spacing: 0.08em; margin-bottom: 8px; text-transform: uppercase; }
h1 { color: #e2b714; font-size: 30px; margin-bottom: 8px; }
.subtitle { color: #8888aa; font-size: 14px; line-height: 1.6; max-width: 680px; }
.icon-link { align-items: center; background: #16213e; border: 1px solid #0f3460; border-radius: 10px; color: #a0c0ff; display: inline-flex; font-size: 14px; font-weight: 800; gap: 8px; min-height: 42px; justify-content: center; padding: 0 14px; text-decoration: none; }
.icon-link:hover { border-color: #e2b714; color: #e2b714; }
.plans-grid { display: grid; gap: 16px; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.plan-card { background: #16213e; border: 1px solid #0f3460; border-radius: 12px; display: flex; flex-direction: column; gap: 20px; min-height: 320px; padding: 24px; }
.plan-card.featured { border-color: #e2b714; box-shadow: 0 0 0 1px rgba(226, 183, 20, 0.2); }
.plan-top { display: flex; flex-direction: column; gap: 10px; }
h2 { color: #e0e0e0; font-size: 20px; }
.plan-note { color: #8888aa; font-size: 13px; margin-top: -4px; }
.price span { color: #e2b714; font-size: 34px; font-weight: 800; }
.price small { color: #8888aa; font-size: 14px; margin-left: 4px; }
ul { color: #c0c0d0; display: flex; flex: 1; flex-direction: column; gap: 10px; list-style: none; padding: 0; }
li::before { color: #e2b714; content: '•'; margin-right: 8px; }
.btn-primary { align-items: center; background: linear-gradient(135deg, #e2b714, #f6d860); border: none; border-radius: 10px; color: #0a0a1a; cursor: pointer; display: inline-flex; font-size: 15px; font-weight: 800; gap: 8px; justify-content: center; min-height: 46px; padding: 13px 20px; }
.btn-primary:disabled { cursor: default; opacity: 0.55; }
.spin { animation: spin 0.9s linear infinite; }
.error-box { background: #3d1a1a; border: 1px solid #c53030; border-radius: 8px; color: #fc8181; padding: 14px; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 820px) {
  .plans-grid { grid-template-columns: 1fr; }
  .page-header { flex-direction: column; }
}
</style>
