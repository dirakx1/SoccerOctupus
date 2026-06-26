import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { createPaymentMethodSession, createPortalSession, getSubscription } from '../lib/billing'

const subscription = ref(null)
const loading = ref(false)
const actionLoading = ref(false)
const error = ref('')

export function useBillingStatus() {
  const router = useRouter()
  const billingHealth = computed(() => subscription.value?.billing_health || {})
  const requiresAttention = computed(() => Boolean(billingHealth.value.requires_attention))

  async function refreshBillingStatus() {
    loading.value = true
    error.value = ''
    try {
      const res = await getSubscription()
      subscription.value = res.data
    } catch (err) {
      error.value = err.response?.data?.error || 'Could not load billing status.'
      subscription.value = null
    } finally {
      loading.value = false
    }
  }

  async function openBillingRecovery(returnPath = '/profile', healthOverride = null) {
    const action = (healthOverride || billingHealth.value).action
    if (action === 'choose_plan') {
      router.push('/pricing')
      return
    }

    actionLoading.value = true
    error.value = ''
    try {
      const payload = { return_path: returnPath || '/profile' }
      const res = action === 'manage_billing'
        ? await createPortalSession(payload)
        : await createPaymentMethodSession(payload)
      window.location.assign(res.data.url)
    } catch (err) {
      error.value = err.response?.data?.error || 'Could not open billing.'
    } finally {
      actionLoading.value = false
    }
  }

  function clearBillingStatus() {
    subscription.value = null
    error.value = ''
  }

  return {
    actionLoading,
    billingHealth,
    clearBillingStatus,
    error,
    loading,
    openBillingRecovery,
    refreshBillingStatus,
    requiresAttention,
    subscription,
  }
}
