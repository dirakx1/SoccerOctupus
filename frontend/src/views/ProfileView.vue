<template>
  <div class="profile-page">
    <ReverificationDialog :workflow="reverification" />

    <header class="profile-header">
      <div>
        <div class="eyebrow">Account</div>
        <h1>Profile settings</h1>
        <p>Update your profile and password for SoccerOctopus.</p>
      </div>
      <img v-if="avatarUrl" class="avatar" :src="avatarUrl" alt="Profile avatar" />
    </header>

    <div class="profile-grid">
      <section class="profile-card">
        <h2>Personal details</h2>
        <p class="card-copy">Keep your account details up to date.</p>

        <form class="profile-form" @submit.prevent="updateProfile">
          <div class="name-grid">
            <label class="field">
              <span>First name</span>
              <input v-model.trim="profileForm.firstName" type="text" autocomplete="given-name" placeholder="Alex" />
            </label>

            <label class="field">
              <span>Last name</span>
              <input v-model.trim="profileForm.lastName" type="text" autocomplete="family-name" placeholder="Morgan" />
            </label>
          </div>

          <label class="field">
            <span>Email address</span>
            <input :value="emailAddress" type="email" disabled />
          </label>

          <p v-if="profileError" class="error-box">{{ profileError }}</p>
          <p v-if="profileSuccess" class="success-box">{{ profileSuccess }}</p>

          <button class="btn-primary" :disabled="profileLoading || !isLoaded || !user" :aria-label="profileLoading ? 'Saving profile' : 'Save profile'">
            <LoaderCircle v-if="profileLoading" :size="18" class="spin" aria-hidden="true" />
            <template v-else>Save profile</template>
          </button>
        </form>
      </section>

      <section class="profile-card">
        <h2>Change password</h2>
        <p class="card-copy">Enter your current password, then confirm your new password twice.</p>

        <form class="profile-form" @submit.prevent="updatePassword">
          <label class="field">
            <span>Current password</span>
            <input
              v-model="passwordForm.currentPassword"
              type="password"
              autocomplete="current-password"
              required
              placeholder="Enter current password"
            />
          </label>

          <label class="field">
            <span>New password</span>
            <input
              v-model="passwordForm.newPassword"
              type="password"
              autocomplete="new-password"
              required
              placeholder="Enter new password"
            />
          </label>
          <PasswordPolicyChecklist :policy="passwordPolicy" />

          <label class="field">
            <span>Confirm new password</span>
            <input
              v-model="passwordForm.confirmPassword"
              type="password"
              autocomplete="new-password"
              required
              placeholder="Repeat new password"
            />
          </label>

          <p v-if="passwordError" class="error-box">{{ passwordError }}</p>
          <p v-if="passwordSuccess" class="success-box">{{ passwordSuccess }}</p>

          <button class="btn-primary" :disabled="passwordLoading || !isLoaded || !user" :aria-label="passwordLoading ? 'Updating password' : 'Update password'">
            <LoaderCircle v-if="passwordLoading" :size="18" class="spin" aria-hidden="true" />
            <template v-else>Update password</template>
          </button>
        </form>
      </section>
    </div>

    <section class="profile-card security-card">
      <h2>Security</h2>
      <TwoFactorSettings :is-loaded="isLoaded" :reverification="reverification" :user="user" />
    </section>

    <section class="profile-card billing-card">
      <div class="billing-row">
        <div>
          <h2>Billing</h2>
          <p class="billing-tier">
            <span>Current tier</span>
            <LoaderCircle v-if="billingLoading" :size="18" class="spin billing-loader" aria-label="Loading billing tier" />
            <strong v-else>{{ tierLabel }}</strong>
          </p>
        </div>
        <button
          class="btn-primary billing-action"
          :disabled="billingLoading || portalLoading"
          :aria-label="portalLoading ? 'Opening billing' : billingActionLabel"
          :title="portalLoading ? 'Opening billing' : billingActionLabel"
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

const {
  avatarUrl,
  email: emailAddress,
  firstName,
  isLoaded,
  lastName,
  user,
} = useCurrentUserProfile()

const router = useRouter()
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
  return labels[subscription.value.tier] || 'Free'
})
const isFreeTier = computed(() => (subscription.value.tier || 'free') === 'free')
const billingHealth = computed(() => subscription.value.billing_health || {})
const billingActionText = computed(() => (isFreeTier.value ? 'Plans' : 'Manage'))
const billingActionLabel = computed(() => (isFreeTier.value ? 'View plans' : 'Manage billing'))

watch(
  [firstName, lastName],
  ([currentFirstName, currentLastName]) => {
    profileForm.firstName = currentFirstName
    profileForm.lastName = currentLastName
  },
  { immediate: true }
)

function clerkError(err, fallback) {
  return err?.response?.data?.error || err?.errors?.[0]?.longMessage || err?.errors?.[0]?.message || err?.message || fallback
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
    billingError.value = err.response?.data?.error || 'Could not load billing details.'
  } finally {
    billingLoading.value = false
  }
}

function usageText(feature) {
  if (feature.unlimited) return 'Unlimited'
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
    billingError.value = err.response?.data?.error || 'Could not open Stripe billing portal.'
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
    billingError.value = err.response?.data?.error || 'Could not open payment update.'
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
    profileSuccess.value = 'Profile updated.'

    try {
      await user.value.reload()
      await refreshLocalUser()
    } catch (err) {
      profileError.value = clerkError(
        err,
        'Your changes were saved, but the latest profile could not be refreshed. Reload the page to confirm them.',
      )
    }
  } catch (err) {
    profileError.value = clerkError(err, 'Unable to update your profile. Please try again.')
  } finally {
    profileLoading.value = false
  }
}

function validatePasswordForm() {
  if (!passwordForm.currentPassword) {
    return 'Enter your current password.'
  }

  if (!passwordPolicy.passesRequiredRules.value) {
    return 'New password does not meet the password requirements.'
  }

  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    return 'New passwords do not match.'
  }

  if (passwordForm.currentPassword === passwordForm.newPassword) {
    return 'New password must be different from your current password.'
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
    passwordSuccess.value = 'Password updated. Other sessions were signed out.'
  } catch (err) {
    passwordError.value = clerkError(err, 'Unable to update your password. Check your current password and try again.')
  } finally {
    passwordLoading.value = false
  }
}

onMounted(loadBilling)
</script>

<style scoped>
.profile-page {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.profile-header {
  align-items: center;
  background: linear-gradient(135deg, #16213e, #0f3460);
  border: 1px solid #1f4c7a;
  border-radius: 16px;
  display: flex;
  justify-content: space-between;
  padding: 28px;
}

.eyebrow {
  color: #e2b714;
  font-size: 12px;
  letter-spacing: 0.08em;
  margin-bottom: 10px;
  text-transform: uppercase;
}

h1,
h2 {
  color: #e0e0e0;
}

h1 {
  font-size: 34px;
  margin-bottom: 8px;
}

h2 {
  font-size: 22px;
  margin-bottom: 8px;
}

.profile-header p,
.card-copy {
  color: #a0aec0;
  font-size: 14px;
  line-height: 1.5;
}

.avatar {
  border: 2px solid #e2b714;
  border-radius: 999px;
  height: 72px;
  object-fit: cover;
  width: 72px;
}

.profile-grid {
  display: grid;
  gap: 24px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.profile-card {
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  padding: 28px;
}

.security-card {
  gap: 20px;
  overflow: hidden;
}

.billing-card {
  gap: 16px;
}

.billing-row {
  align-items: center;
  display: flex;
  gap: 20px;
  justify-content: space-between;
}

.billing-tier {
  align-items: baseline;
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.billing-tier span {
  color: #8888aa;
  font-size: 13px;
}

.billing-tier strong {
  color: #e2b714;
  font-size: 20px;
}

.billing-loader {
  color: #e2b714;
}

.billing-action {
  flex: 0 0 auto;
}

.usage-grid {
  border-top: 1px solid #0f3460;
  display: grid;
  gap: 10px;
  padding-top: 16px;
}

.usage-row {
  align-items: center;
  display: flex;
  gap: 16px;
  justify-content: space-between;
}

.usage-row span {
  color: #a0aec0;
  font-size: 13px;
}

.usage-row strong {
  color: #e0e0e0;
  font-size: 13px;
}

.profile-form {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 16px;
  margin-top: 22px;
}

.name-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  color: #8888aa;
  font-size: 13px;
}

input {
  background: #0a0a1a;
  border: 1px solid #0f3460;
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 14px;
  padding: 12px 14px;
}

input:disabled {
  color: #8888aa;
  cursor: not-allowed;
  opacity: 0.8;
}

input:focus {
  border-color: #e2b714;
  outline: none;
}

.btn-primary {
  align-items: center;
  background: linear-gradient(135deg, #e2b714, #f6d860);
  border: none;
  border-radius: 10px;
  color: #0a0a1a;
  cursor: pointer;
  display: inline-flex;
  font-size: 15px;
  font-weight: 700;
  gap: 8px;
  justify-content: center;
  min-height: 46px;
  padding: 13px 24px;
  transition: opacity 0.2s;
}

.profile-form .btn-primary {
  margin-top: auto;
}

.btn-primary:disabled {
  cursor: default;
  opacity: 0.55;
}

.spin {
  animation: spin 0.9s linear infinite;
}

.error-box,
.success-box {
  border-radius: 8px;
  font-size: 13px;
  padding: 12px 14px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-box {
  background: #3d1a1a;
  border: 1px solid #c53030;
  color: #fc8181;
}

.success-box {
  background: #123322;
  border: 1px solid #38a169;
  color: #9ae6b4;
}

@media (max-width: 860px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .profile-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 20px;
  }

  .billing-row {
    align-items: stretch;
    flex-direction: column;
  }

  .name-grid {
    grid-template-columns: 1fr;
  }
}
</style>
