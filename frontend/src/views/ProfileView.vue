<template>
  <div class="profile-page">
    <ReverificationDialog :workflow="reverification" />

    <header class="profile-header">
      <div>
        <div class="eyebrow">{{ t('profile.eyebrow') }}</div>
        <h1>{{ t('profile.title') }}</h1>
        <p>{{ t('profile.subtitle') }}</p>
      </div>
      <img v-if="avatarUrl" class="avatar" :src="avatarUrl" alt="Profile avatar" />
    </header>

    <div class="profile-grid">
      <section class="profile-card">
        <h2>{{ t('profile.personal') }}</h2>
        <p class="card-copy">{{ t('profile.personalCopy') }}</p>

        <form class="profile-form" @submit.prevent="updateProfile">
          <div class="name-grid">
            <label class="field">
              <span>{{ t('profile.firstName') }}</span>
              <input v-model.trim="profileForm.firstName" type="text" autocomplete="given-name" :placeholder="t('profile.firstPlaceholder')" />
            </label>

            <label class="field">
              <span>{{ t('profile.lastName') }}</span>
              <input v-model.trim="profileForm.lastName" type="text" autocomplete="family-name" :placeholder="t('profile.lastPlaceholder')" />
            </label>
          </div>

          <label class="field">
            <span>{{ t('profile.email') }}</span>
            <input :value="emailAddress" type="email" disabled />
          </label>

          <p v-if="profileError" class="error-box">{{ profileError }}</p>
          <p v-if="profileSuccess" class="success-box">{{ profileSuccess }}</p>

          <button class="btn-primary" :disabled="profileLoading || !isLoaded || !user" :aria-label="profileLoading ? t('profile.saving') : t('profile.save')">
            <LoaderCircle v-if="profileLoading" :size="18" class="spin" aria-hidden="true" />
            <template v-else>{{ t('profile.save') }}</template>
          </button>
        </form>
      </section>

      <section class="profile-card">
        <h2>{{ t('profile.password') }}</h2>
        <p class="card-copy">{{ t('profile.passwordCopy') }}</p>

        <form class="profile-form" @submit.prevent="updatePassword">
          <label class="field">
            <span>{{ t('profile.currentPassword') }}</span>
            <input
              v-model="passwordForm.currentPassword"
              type="password"
              autocomplete="current-password"
              required
              :placeholder="t('profile.currentPlaceholder')"
            />
          </label>

          <label class="field">
            <span>{{ t('profile.newPassword') }}</span>
            <input
              v-model="passwordForm.newPassword"
              type="password"
              autocomplete="new-password"
              required
              :placeholder="t('profile.newPlaceholder')"
            />
          </label>
          <PasswordPolicyChecklist :policy="passwordPolicy" />

          <label class="field">
            <span>{{ t('profile.confirmPassword') }}</span>
            <input
              v-model="passwordForm.confirmPassword"
              type="password"
              autocomplete="new-password"
              required
              :placeholder="t('profile.confirmPlaceholder')"
            />
          </label>

          <p v-if="passwordError" class="error-box">{{ passwordError }}</p>
          <p v-if="passwordSuccess" class="success-box">{{ passwordSuccess }}</p>

          <button class="btn-primary" :disabled="passwordLoading || !isLoaded || !user" :aria-label="passwordLoading ? t('profile.updatingPassword') : t('profile.updatePassword')">
            <LoaderCircle v-if="passwordLoading" :size="18" class="spin" aria-hidden="true" />
            <template v-else>{{ t('profile.updatePassword') }}</template>
          </button>
        </form>
      </section>
    </div>

    <section class="profile-card security-card">
      <h2>{{ t('profile.security') }}</h2>
      <TwoFactorSettings :is-loaded="isLoaded" :reverification="reverification" :user="user" />
    </section>

    <section class="profile-card billing-card">
      <div class="billing-row">
        <div>
          <h2>{{ t('profile.billing') }}</h2>
          <p class="billing-tier">
            <span>{{ t('profile.currentTier') }}</span>
            <LoaderCircle v-if="billingLoading" :size="18" class="spin billing-loader" :aria-label="t('profile.loadingTier')" />
            <strong v-else>{{ tierLabel }}</strong>
          </p>
        </div>
        <button
          class="btn-primary billing-action"
          :disabled="billingLoading || portalLoading"
          :aria-label="portalLoading ? t('profile.openingBilling') : billingActionLabel"
          :title="portalLoading ? t('profile.openingBilling') : billingActionLabel"
          @click="openBillingPortal"
        >
          <LoaderCircle v-if="portalLoading" :size="18" class="spin" aria-hidden="true" />
          <template v-else>
            <span>{{ billingActionText }}</span>
            <CreditCard :size="18" aria-hidden="true" />
          </template>
        </button>
      </div>
      <BillingStatusNotice
        :health="billingHealth"
        :loading="paymentLoading"
        @action="openPaymentRecovery"
      />
      <div v-if="usage.features?.length" class="usage-grid">
        <div v-for="feature in usage.features" :key="feature.feature_key" class="usage-row">
          <span>{{ feature.label }}</span>
          <strong>{{ usageText(feature) }}</strong>
        </div>
      </div>
      <p v-if="billingError" class="error-box">{{ billingError }}</p>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { CreditCard, LoaderCircle } from '@lucide/vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useClerk, useSession, useSignIn } from '@clerk/vue'

import BillingStatusNotice from '../components/BillingStatusNotice.vue'
import PasswordPolicyChecklist from '../components/PasswordPolicyChecklist.vue'
import ReverificationDialog from '../components/ReverificationDialog.vue'
import TwoFactorSettings from '../components/TwoFactorSettings.vue'
import { useCurrentUserProfile } from '../composables/useCurrentUserProfile'
import { usePasswordPolicy } from '../composables/usePasswordPolicy'
import { useReverification } from '../composables/useReverification'
import { api } from '../lib/api'
import { setAuthState } from '../lib/auth'
import { createPaymentMethodSession, createPortalSession, getSubscription, getUsage } from '../lib/billing'
import { userFacingError } from '../lib/userFacingError'

const {
  avatarUrl,
  email: emailAddress,
  firstName,
  isLoaded,
  lastName,
  user,
} = useCurrentUserProfile()

const router = useRouter()
const { t } = useI18n()
const clerk = useClerk()
const { session } = useSession()
const { signIn } = useSignIn()
const reverification = useReverification({ session })
const profileLoading = ref(false)
const passwordLoading = ref(false)
const profileError = ref('')
const passwordError = ref('')
const profileSuccess = ref('')
const passwordSuccess = ref('')
const subscription = ref({})
const usage = ref({})
const billingLoading = ref(true)
const portalLoading = ref(false)
const paymentLoading = ref(false)
const billingError = ref('')

const profileForm = reactive({
  firstName: '',
  lastName: '',
})

const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})
const passwordPolicy = usePasswordPolicy({
  password: computed(() => passwordForm.newPassword),
  validator: computed(() => signIn.value?.validatePassword),
  clerk,
})

const tierLabel = computed(() => {
  const labels = {
    free: 'Free',
    basic: 'Basic',
    pro: 'Pro',
  }
  return labels[subscription.value.tier] || labels.free
})
const isFreeTier = computed(() => (subscription.value.tier || 'free') === 'free')
const billingHealth = computed(() => subscription.value.billing_health || {})
const billingActionText = computed(() => (isFreeTier.value ? t('profile.plans') : t('profile.manage')))
const billingActionLabel = computed(() => (isFreeTier.value ? t('profile.viewPlans') : t('profile.manageBilling')))

watch(
  [firstName, lastName],
  ([currentFirstName, currentLastName]) => {
    profileForm.firstName = currentFirstName
    profileForm.lastName = currentLastName
  },
  { immediate: true }
)

function clerkError(err, fallback) {
  return userFacingError(err, fallback)
}

async function refreshLocalUser() {
  const res = await api.get('/api/me')
  setAuthState({ signedIn: true, isAdmin: res.data.is_admin, user: res.data })
}

async function loadBilling() {
  billingLoading.value = true
  billingError.value = ''
  try {
    const [subscriptionRes, usageRes] = await Promise.all([getSubscription(), getUsage()])
    subscription.value = subscriptionRes.data
    usage.value = usageRes.data
  } catch (err) {
    billingError.value = err.response?.data?.error || t('profile.errors.billing')
  } finally {
    billingLoading.value = false
  }
}

function usageText(feature) {
  if (feature.unlimited) return t('profile.unlimited')
  return `${feature.used_count} / ${feature.limit_count}`
}

async function openBillingPortal() {
  if (isFreeTier.value) {
    router.push('/pricing')
    return
  }

  portalLoading.value = true
  billingError.value = ''
  try {
    const res = await createPortalSession({ return_path: '/profile' })
    window.location.assign(res.data.url)
  } catch (err) {
    billingError.value = err.response?.data?.error || t('profile.errors.portal')
  } finally {
    portalLoading.value = false
  }
}

async function openPaymentRecovery() {
  if (billingHealth.value.action === 'choose_plan') {
    router.push('/pricing')
    return
  }

  if (billingHealth.value.action === 'manage_billing') {
    await openBillingPortal()
    return
  }

  paymentLoading.value = true
  billingError.value = ''
  try {
    const res = await createPaymentMethodSession({ return_path: '/profile' })
    window.location.assign(res.data.url)
  } catch (err) {
    billingError.value = err.response?.data?.error || t('profile.errors.payment')
  } finally {
    paymentLoading.value = false
  }
}

async function updateProfile() {
  if (!isLoaded.value || !user.value) return

  profileLoading.value = true
  profileError.value = ''
  profileSuccess.value = ''

  try {
    await user.value.update({
      firstName: profileForm.firstName,
      lastName: profileForm.lastName,
    })
    profileSuccess.value = t('profile.profileUpdated')

    try {
      await user.value.reload()
      await refreshLocalUser()
    } catch (err) {
      profileError.value = clerkError(
        err,
        t('profile.errors.refreshProfile'),
      )
    }
  } catch (err) {
    profileError.value = clerkError(err, t('profile.errors.profile'))
  } finally {
    profileLoading.value = false
  }
}

function validatePasswordForm() {
  if (!passwordForm.currentPassword) {
    return t('profile.errors.currentPassword')
  }

  if (!passwordPolicy.passesRequiredRules.value) {
    return t('profile.errors.requirements')
  }

  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    return t('profile.errors.mismatch')
  }

  if (passwordForm.currentPassword === passwordForm.newPassword) {
    return t('profile.errors.same')
  }

  return ''
}

async function updatePassword() {
  if (!isLoaded.value || !user.value) return

  passwordError.value = validatePasswordForm()
  passwordSuccess.value = ''
  if (passwordError.value) return

  passwordLoading.value = true

  try {
    await user.value.updatePassword({
      currentPassword: passwordForm.currentPassword,
      newPassword: passwordForm.newPassword,
      signOutOfOtherSessions: true,
    })
    passwordForm.currentPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
    passwordSuccess.value = t('profile.passwordUpdated')
  } catch (err) {
    passwordError.value = clerkError(err, t('profile.errors.password'))
  } finally {
    passwordLoading.value = false
  }
}

onMounted(loadBilling)
</script>

<style scoped>
.profile-page { display: flex; flex-direction: column; gap: var(--space-6); margin: 0 auto; max-width: 72rem; padding: var(--space-8) 0 var(--space-12); }
.profile-header { align-items: center; border-bottom: var(--border-width-strong) solid var(--color-border-strong); display: flex; justify-content: space-between; padding: var(--space-4) 0 var(--space-6); }
.eyebrow { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs)/var(--line-height-normal) var(--font-family-data); margin-bottom: var(--space-2); text-transform: uppercase; }
h1,h2 { color: var(--color-text); font-family: var(--font-family-display); margin: 0; }
h1 { font-size: var(--font-size-4xl); line-height: var(--line-height-tight); }
h2 { font-size: var(--font-size-2xl); }
.profile-header p,.card-copy { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-relaxed); margin: var(--space-2) 0 0; }
.avatar { border: var(--border-width-strong) solid var(--color-accent); border-radius: 999px; height: 72px; object-fit: cover; width: 72px; }
.profile-grid { display: grid; gap: var(--space-6); grid-template-columns: repeat(2,minmax(0,1fr)); }
.profile-card { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); display: flex; flex-direction: column; padding: var(--space-6); }
.security-card,.billing-card { gap: var(--space-5); overflow: hidden; }
.billing-row { align-items: center; display: flex; gap: var(--space-5); justify-content: space-between; }
.billing-tier { align-items: baseline; display: flex; gap: var(--space-3); margin: var(--space-3) 0 0; }
.billing-tier span,.usage-row span,.field span { color: var(--color-text-muted); font-size: var(--font-size-sm); }
.billing-tier strong,.billing-loader { color: var(--color-accent); }
.billing-tier strong { font: var(--font-weight-bold) var(--font-size-xl)/1 var(--font-family-display); }
.billing-action { flex: 0 0 auto; }
.usage-grid { border-top: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-3); padding-top: var(--space-4); }
.usage-row { align-items: center; display: flex; gap: var(--space-4); justify-content: space-between; }
.usage-row strong { color: var(--color-text); font-size: var(--font-size-sm); }
.profile-form { display: flex; flex: 1; flex-direction: column; gap: var(--space-4); margin-top: var(--space-5); }
.name-grid { display: grid; gap: var(--space-4); grid-template-columns: repeat(2,minmax(0,1fr)); }
.field { display: flex; flex-direction: column; gap: var(--space-2); }
input { background: var(--color-surface-raised); border: var(--border-width-thin) solid var(--color-border); border-radius: var(--radius-md); color: var(--color-text); font-size: var(--font-size-sm); min-height: var(--control-height-lg); padding: 0 var(--space-3); }
input:disabled { color: var(--color-text-muted); cursor: not-allowed; opacity: .8; }
input:focus-visible,.btn-primary:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.btn-primary { align-items: center; background: var(--color-accent); border: 0; border-radius: var(--radius-md); color: var(--color-accent-contrast); cursor: pointer; display: inline-flex; font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); gap: var(--space-2); justify-content: center; min-height: var(--control-height-lg); padding: 0 var(--space-4); }
.profile-form .btn-primary { margin-top: auto; }
.btn-primary:disabled { cursor: default; opacity: .55; }
.spin { animation: spin .9s linear infinite; }
.error-box,.success-box { font-size: var(--font-size-sm); padding: var(--space-3); }
.error-box { background: var(--color-danger-surface); border: var(--border-width-thin) solid var(--color-danger); color: var(--color-danger); }
.success-box { background: var(--color-success-surface); border: var(--border-width-thin) solid var(--color-success); color: var(--color-success); }
@keyframes spin { to { transform: rotate(360deg); } }
@media(prefers-reduced-motion:reduce) { .spin { animation: none; } }
@media(max-width:760px) { .profile-grid { grid-template-columns: 1fr; } }
@media(max-width:640px) { .profile-page { padding-top: var(--space-5); }.profile-header { align-items: flex-start; flex-direction: column; gap: var(--space-5); }.billing-row { align-items: stretch; flex-direction: column; }.name-grid { grid-template-columns: 1fr; }.profile-card { padding: var(--space-5); } }
</style>
