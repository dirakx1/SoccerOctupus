<template>
  <div class="billing-success-page">
    <section class="billing-success-intro" aria-labelledby="billing-success-title">
      <p class="atlas-kicker">{{ t('billingSuccess.eyebrow') }}</p>
      <h1 id="billing-success-title">{{ t('billingSuccess.title') }}</h1>
      <p>{{ t('billingSuccess.subtitle') }}</p>
      <div class="atlas-rule" aria-hidden="true" />
      <p class="billing-success-note">{{ t('billingSuccess.note') }}</p>
    </section>

    <section class="billing-success-panel" :aria-busy="isReconciling" aria-labelledby="billing-success-status">
      <div class="status-mark" :class="`is-${status}`" aria-hidden="true">
        <LoaderCircle v-if="isReconciling" :size="28" class="spin" />
        <Check v-else-if="status === 'complete'" :size="28" />
        <Clock3 v-else :size="28" />
      </div>

      <p class="atlas-kicker">{{ statusKicker }}</p>
      <h2 id="billing-success-status">{{ statusTitle }}</h2>
      <p class="status-copy" role="status" aria-live="polite">{{ statusCopy }}</p>
      <p v-if="reconciliationError" class="status-detail" role="alert">{{ reconciliationError }}</p>

      <div class="billing-success-actions">
        <button
          v-if="status === 'retryable-error'"
          class="btn-secondary"
          type="button"
          :disabled="isReconciling"
          @click="reconcileCheckout"
        >
          <RefreshCw :size="17" aria-hidden="true" />
          {{ t('billingSuccess.retry') }}
        </button>
        <router-link class="btn-primary" to="/profile">
          <span>{{ t('billingSuccess.profile') }}</span>
          <UserCircle :size="18" aria-hidden="true" />
        </router-link>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { Check, Clock3, LoaderCircle, RefreshCw, UserCircle } from '@lucide/vue'

import { getCheckoutSession } from '../lib/billing'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const status = ref('pending')
const reconciliationError = ref('')
let redirectTimer

const sessionId = computed(() => (
  typeof route.query.session_id === 'string' ? route.query.session_id : ''
))
const isReconciling = computed(() => status.value === 'pending')
const statusKicker = computed(() => t(`billingSuccess.states.${status.value}.eyebrow`))
const statusTitle = computed(() => t(`billingSuccess.states.${status.value}.title`))
const statusCopy = computed(() => t(`billingSuccess.states.${status.value}.copy`))

function sourceError(err) {
  return err?.response?.data?.error || ''
}

async function reconcileCheckout() {
  if (!sessionId.value) {
    status.value = 'retryable-error'
    reconciliationError.value = t('billingSuccess.missingSession')
    return
  }

  status.value = 'pending'
  reconciliationError.value = ''

  try {
    await getCheckoutSession(sessionId.value)
    status.value = 'complete'
  } catch (err) {
    // The Stripe webhook can still reconcile this subscription asynchronously.
    status.value = 'retryable-error'
    reconciliationError.value = sourceError(err)
  }
}

onMounted(async () => {
  await reconcileCheckout()
  redirectTimer = window.setTimeout(() => {
    router.replace('/profile')
  }, 3500)
})

onBeforeUnmount(() => {
  if (redirectTimer) {
    window.clearTimeout(redirectTimer)
  }
})
</script>

<style scoped>
.billing-success-page { align-items: start; display: grid; gap: var(--space-12); grid-template-columns: minmax(0, .8fr) minmax(20rem, 1fr); margin: 0 auto; max-width: 64rem; padding: var(--space-12) 0; }
.billing-success-intro { align-self: center; padding: var(--space-6) 0; }
.atlas-kicker { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); margin: 0 0 var(--space-3); text-transform: uppercase; }
.billing-success-intro h1 { font-family: var(--font-family-display); font-size: var(--font-size-5xl); line-height: var(--line-height-tight); margin: 0; max-width: 9ch; }
.billing-success-intro > p:not(.atlas-kicker) { color: var(--color-text-muted); font-size: var(--font-size-lg); line-height: var(--line-height-relaxed); margin: var(--space-5) 0 0; max-width: 31ch; }
.atlas-rule { background: var(--color-accent); height: var(--border-width-strong); margin-top: var(--space-8); width: 4rem; }
.billing-success-note { font-size: var(--font-size-sm) !important; }
.billing-success-panel { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); padding: var(--space-8); text-align: center; }
.status-mark { align-items: center; border: var(--border-width-strong) solid var(--color-information); color: var(--color-information); display: inline-flex; height: 3.5rem; justify-content: center; margin-bottom: var(--space-5); width: 3.5rem; }
.status-mark.is-complete { border-color: var(--color-success); color: var(--color-success); }
.status-mark.is-retryable-error { border-color: var(--color-warning); color: var(--color-warning); }
.billing-success-panel h2 { font-family: var(--font-family-display); font-size: var(--font-size-3xl); line-height: var(--line-height-tight); margin: 0; }
.status-copy { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-relaxed); margin: var(--space-3) auto 0; max-width: 34ch; }
.status-detail { background: var(--color-warning-surface); border: var(--border-width-thin) solid var(--color-warning); color: var(--color-warning); font-size: var(--font-size-sm); line-height: var(--line-height-normal); margin: var(--space-5) 0 0; padding: var(--space-3); text-align: left; }
.billing-success-actions { align-items: center; display: flex; flex-wrap: wrap; gap: var(--space-3); justify-content: center; margin-top: var(--space-8); }
.btn-primary,.btn-secondary { align-items: center; border: var(--border-width-thin) solid transparent; border-radius: var(--radius-md); cursor: pointer; display: inline-flex; font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); gap: var(--space-2); justify-content: center; min-height: var(--control-height-lg); padding: 0 var(--space-4); text-decoration: none; transition: background var(--duration-fast) var(--easing-standard), border-color var(--duration-fast) var(--easing-standard), transform var(--duration-fast) var(--easing-standard); }
.btn-primary { background: var(--color-accent); color: var(--color-accent-contrast); }
.btn-primary:hover { background: var(--color-accent-hover); transform: translateY(-1px); }
.btn-secondary { background: transparent; border-color: var(--color-border-strong); color: var(--color-text); }
.btn-secondary:hover:not(:disabled) { background: var(--color-surface-inset); }
.btn-secondary:disabled { cursor: not-allowed; opacity: .55; }
.btn-primary:focus-visible,.btn-secondary:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.spin { animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media(max-width:640px) { .billing-success-page { display: block; padding: var(--space-6) 0; }.billing-success-intro { padding: 0 0 var(--space-6); }.billing-success-intro h1 { font-size: var(--font-size-4xl); }.billing-success-panel { padding: var(--space-5); } }
</style>
