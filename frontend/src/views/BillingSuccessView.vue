<template>
  <div class="success-view">
    <section class="success-panel">
      <p class="eyebrow">Checkout</p>
      <h1>Processing your subscription</h1>
      <p class="subtitle">We are updating your billing details. You will be redirected to your account shortly.</p>
      <router-link class="btn-primary" to="/profile">
        <span>Account</span>
        <UserCircle :size="18" aria-hidden="true" />
      </router-link>
    </section>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { UserCircle } from '@lucide/vue'

import { getCheckoutSession } from '../lib/billing'

const route = useRoute()
const router = useRouter()
let redirectTimer

onMounted(async () => {
  const sessionId = typeof route.query.session_id === 'string' ? route.query.session_id : ''
  if (sessionId) {
    try {
      await getCheckoutSession(sessionId)
    } catch {
      // The Stripe webhook can still reconcile this subscription asynchronously.
    }
  }
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
.success-view { display: flex; justify-content: center; padding: 48px 0; }
.success-panel { background: #16213e; border: 1px solid #0f3460; border-radius: 12px; padding: 32px; text-align: center; width: min(100%, 560px); }
.eyebrow { color: #e2b714; font-size: 12px; font-weight: 800; letter-spacing: 0.08em; margin-bottom: 8px; text-transform: uppercase; }
h1 { color: #e2b714; font-size: 30px; margin-bottom: 8px; }
.subtitle { color: #8888aa; font-size: 14px; line-height: 1.6; margin-bottom: 22px; }
.btn-primary { align-items: center; background: linear-gradient(135deg, #e2b714, #f6d860); border-radius: 10px; color: #0a0a1a; display: inline-flex; font-size: 14px; font-weight: 800; gap: 8px; min-height: 44px; justify-content: center; padding: 0 16px; text-decoration: none; }
</style>
