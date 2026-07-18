<template>
  <AtlasAuthLayout>
    <template #intro>
      <h1 id="sign-up-title">{{ t('signUp.title') }}</h1><p>{{ t('signUp.subtitle') }}</p>
    </template>
      <form v-if="step === 'details'" class="auth-form" :aria-busy="loading || Boolean(loadingStrategy)" @submit.prevent="createAccount">
        <SocialAuthButtons
          :disabled="loading || !isLoaded"
          :loading-provider="loadingStrategy"
          appearance="atlas"
          :labels="providerLabels"
          @select="signUpWithProvider"
        />

        <div class="auth-divider"><span>{{ t('signUp.divider') }}</span></div>

        <div class="name-grid">
          <label class="field">
            <span>{{ t('signUp.firstName') }}</span>
            <input v-model.trim="form.firstName" type="text" autocomplete="given-name" placeholder="Alex" />
          </label>

          <label class="field">
            <span>{{ t('signUp.lastName') }}</span>
            <input v-model.trim="form.lastName" type="text" autocomplete="family-name" placeholder="Morgan" />
          </label>
        </div>

        <label class="field">
          <span>{{ t('signUp.email') }}</span>
          <input
            v-model.trim="form.email"
            type="email"
            autocomplete="email"
            required
            :placeholder="t('signUp.emailPlaceholder')"
          />
        </label>

        <label class="field">
          <span>{{ t('signUp.username') }}</span>
          <input
            v-model.trim="form.username"
            type="text"
            autocomplete="username"
            required
            :placeholder="t('signUp.usernamePlaceholder')"
          />
        </label>

        <label class="field">
          <span>{{ t('signUp.password') }}</span>
          <input
            v-model="form.password"
            type="password"
            autocomplete="new-password"
            required
            :placeholder="t('signUp.passwordPlaceholder')"
          />
        </label>
        <PasswordPolicyChecklist :policy="passwordPolicy" />

        <p v-if="error" class="error-box" role="alert">{{ error }}</p>

        <div id="clerk-captcha" />

        <button class="btn-primary" :disabled="!canSubmit">
          {{ loading ? t('signUp.submitting') : t('signUp.submit') }}
        </button>
      </form>

      <form v-else class="auth-form" :aria-busy="loading" @submit.prevent="verifyEmail">
        <p class="verification-copy">
          {{ t('signUp.verificationCopy', { email: form.email }) }}
        </p>

        <label class="field">
          <span>{{ t('signUp.verificationCode') }}</span>
          <input
            v-model.trim="form.code"
            type="text"
            inputmode="numeric"
            autocomplete="one-time-code"
            required
            :placeholder="t('signUp.codePlaceholder')"
          />
        </label>

        <p v-if="error" class="error-box" role="alert">{{ error }}</p>

        <button class="btn-primary" :disabled="loading || !isLoaded">
          {{ loading ? t('signUp.verifying') : t('signUp.verify') }}
        </button>

        <button class="btn-link" type="button" :disabled="loading" @click="resendEmailCode">
          {{ t('signUp.resend') }}
        </button>
      </form>

      <p class="auth-switch">
        {{ t('signUp.signInPrompt') }}
        <router-link to="/sign-in">{{ t('signUp.signIn') }}</router-link>
      </p>
  </AtlasAuthLayout>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useClerk, useSignUp } from '@clerk/vue'

import PasswordPolicyChecklist from '../components/PasswordPolicyChecklist.vue'
import SocialAuthButtons from '../components/SocialAuthButtons.vue'
import AtlasAuthLayout from '../ui/patterns/AtlasAuthLayout.vue'
import { usePasswordPolicy } from '../composables/usePasswordPolicy'
import { activateSessionAndHydrateAuth } from '../lib/clerkSession'
import { consumePostAuthRedirect, peekPostAuthRedirect } from '../lib/postAuthRedirect'
import { userFacingError } from '../lib/userFacingError'

const router = useRouter()
const { t } = useI18n()
const clerk = useClerk()
const { isLoaded, signUp, setActive } = useSignUp()

const step = ref('details')
const loading = ref(false)
const loadingStrategy = ref('')
const error = ref('')
const form = reactive({
  firstName: '',
  lastName: '',
  email: '',
  username: '',
  password: '',
  code: '',
})
const passwordPolicy = usePasswordPolicy({
  password: computed(() => form.password),
  validator: computed(() => signUp.value?.validatePassword),
  clerk,
})
const emailLooksValid = computed(() => /\S+@\S+\.\S+/.test(form.email))
const canSubmit = computed(() => {
  return isLoaded.value &&
    !loading.value &&
    !loadingStrategy.value &&
    emailLooksValid.value &&
    Boolean(form.username && form.password) &&
    passwordPolicy.passesRequiredRules.value
})
const providerLabels = { continueWith: (name) => t('signUp.provider.continueWith', { name }), opening: (name) => t('signUp.provider.opening', { name }) }

function authError(err) {
  return userFacingError(err, t('signUp.errors.fallback'))
}

async function completeSignUp(result) {
  if (!setActive.value || !result.createdSessionId) {
    error.value = t('signUp.errors.activate')
    return
  }

  await activateSessionAndHydrateAuth({
    clerk,
    setActive: setActive.value,
    sessionId: result.createdSessionId,
  })
  router.push(consumePostAuthRedirect() || '/')
}

async function prepareEmailVerification() {
  const supportedStrategies = signUp.value?.verifications?.emailAddress?.supportedStrategies || []

  if (supportedStrategies.length && !supportedStrategies.includes('email_code')) {
    error.value = t('signUp.errors.unsupported', { methods: supportedStrategies.join(', ') })
    return false
  }

  await signUp.value.prepareEmailAddressVerification({ strategy: 'email_code' })
  form.code = ''
  step.value = 'verify'
  return true
}

async function handleSignUpResult(result) {
  if (result.status === 'complete') {
    await completeSignUp(result)
    return
  }

  if (result.unverifiedFields?.includes('email_address')) {
    await prepareEmailVerification()
    return
  }

  error.value = t('signUp.errors.complete')
}

async function createAccount() {
  if (!isLoaded.value || !signUp.value) return
  if (!canSubmit.value) return

  loading.value = true
  error.value = ''

  try {
    const result = await signUp.value.create({
      emailAddress: form.email,
      username: form.username,
      password: form.password,
      firstName: form.firstName || undefined,
      lastName: form.lastName || undefined,
    })

    await handleSignUpResult(result)
  } catch (err) {
    error.value = authError(err)
  } finally {
    loading.value = false
  }
}

async function signUpWithProvider(strategy) {
  if (!isLoaded.value || !signUp.value) return

  loadingStrategy.value = strategy
  error.value = ''

  try {
    await signUp.value.authenticateWithRedirect({
      strategy,
      redirectUrl: '/sso-callback',
      redirectUrlComplete: peekPostAuthRedirect() || '/',
    })
  } catch (err) {
    loadingStrategy.value = ''
    error.value = authError(err)
  }
}

async function verifyEmail() {
  if (!isLoaded.value || !signUp.value) return

  loading.value = true
  error.value = ''

  try {
    const result = await signUp.value.attemptEmailAddressVerification({ code: form.code })
    await handleSignUpResult(result)
  } catch (err) {
    error.value = authError(err)
  } finally {
    loading.value = false
  }
}

async function resendEmailCode() {
  if (!isLoaded.value || !signUp.value) return

  loading.value = true
  error.value = ''

  try {
    await signUp.value.prepareEmailAddressVerification({ strategy: 'email_code' })
  } catch (err) {
    error.value = authError(err)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.auth-divider {
  align-items: center;
  color: var(--color-text-muted);
  display: flex;
  font-size: 11px;
  gap: 12px;
  letter-spacing: 0;
  text-transform: uppercase;
}

.auth-divider::before,
.auth-divider::after {
  background: var(--color-border);
  content: '';
  flex: 1;
  height: 1px;
}

.name-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  color: var(--color-text-muted);
  font-size: 13px;
}

input {
  background: var(--color-surface-raised); color: var(--color-text); border: var(--border-width-thin) solid var(--color-border); border-radius: var(--radius-md); min-height: var(--control-height-lg); padding: 0 var(--space-3); font-size: var(--font-size-sm);
}

input:focus {
  border-color: var(--color-accent); outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 1px;
}

.verification-copy {
  background: var(--color-surface-inset); border-left: var(--border-width-strong) solid var(--color-accent); color: var(--color-text-muted);
  font-size: 14px;
  line-height: 1.5;
  padding: 12px 14px;
}

.btn-primary {
  background: var(--color-accent); color: var(--color-accent-contrast);
  font-weight: 700;
  font-size: 15px;
  border: none;
  border-radius: var(--radius-md); min-height: var(--control-height-lg); padding: 0 var(--space-5);
  cursor: pointer;
  transition: opacity 0.2s;
  width: 100%;
}
.btn-primary:hover:not(:disabled) { background: var(--color-accent-hover); }
.btn-primary:focus-visible, .btn-link:focus-visible, .auth-switch a:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }

.btn-primary:disabled {
  cursor: default;
  opacity: 0.55;
}

.btn-link {
  align-self: center;
  background: transparent;
  border: none;
  color: var(--color-accent);
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  min-height: var(--control-height-lg); padding: 0 var(--space-3);
}

.btn-link:disabled {
  cursor: default;
  opacity: 0.55;
}

.error-box {
  background: var(--color-danger-surface); border: var(--border-width-thin) solid var(--color-danger); color: var(--color-danger);
  font-size: 13px;
  padding: 12px 14px;
}

#clerk-captcha {
  display: flex;
  justify-content: center;
}

.auth-switch {
  color: var(--color-text-muted);
  font-size: 13px;
  margin-top: 20px;
  text-align: center;
}

.auth-switch a {
  color: var(--color-accent);
  font-weight: 700;
  text-decoration: none;
}

@media (max-width: 640px) {
  .name-grid {
    grid-template-columns: 1fr;
  }
}
</style>
