<template>
  <div class="atlas-auth-page">
    <section class="atlas-auth-intro" aria-labelledby="sign-up-title">
      <p class="atlas-auth-kicker">{{ t('signUp.eyebrow') }}</p><h1 id="sign-up-title">{{ t('signUp.title') }}</h1><p>{{ t('signUp.subtitle') }}</p><div class="atlas-auth-rule" aria-hidden="true" /><p class="atlas-auth-note">{{ t('signUp.redirectNote') }}</p>
    </section>
    <section class="atlas-auth-panel">
      <header class="auth-panel-heading"><p class="atlas-auth-kicker">{{ t('signUp.eyebrow') }}</p><h2>{{ t('signUp.title') }}</h2></header>

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
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useClerk, useSignUp } from '@clerk/vue'

import PasswordPolicyChecklist from '../components/PasswordPolicyChecklist.vue'
import SocialAuthButtons from '../components/SocialAuthButtons.vue'
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
.atlas-auth-page { align-items: start; display: grid; gap: var(--space-12); grid-template-columns: minmax(0, .8fr) minmax(22rem, 1fr); margin: 0 auto; max-width: 68rem; padding: var(--space-12) 0; }
.atlas-auth-intro { align-self: center; padding: var(--space-6) 0; }
.atlas-auth-kicker { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs)/var(--line-height-normal) var(--font-family-data); margin: 0 0 var(--space-3); text-transform: uppercase; }
.atlas-auth-intro h1 { font-family: var(--font-family-display); font-size: var(--font-size-5xl); line-height: var(--line-height-tight); margin: 0; max-width: 8ch; }
.atlas-auth-intro>p:not(.atlas-auth-kicker) { color: var(--color-text-muted); font-size: var(--font-size-lg); line-height: var(--line-height-relaxed); margin: var(--space-5) 0 0; max-width: 30ch; }
.atlas-auth-rule { background: var(--color-accent); height: var(--border-width-strong); margin-top: var(--space-8); width: 4rem; }
.atlas-auth-note { font-size: var(--font-size-sm) !important; }
.atlas-auth-panel { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); padding: var(--space-8); }
.auth-panel-heading { border-bottom: var(--border-width-thin) solid var(--color-border); margin-bottom: var(--space-6); padding-bottom: var(--space-5); }
.auth-panel-heading h2 { font-family: var(--font-family-display); font-size: var(--font-size-3xl); margin: 0; }

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
  .atlas-auth-page { display: block; padding: var(--space-6) 0; }
  .atlas-auth-intro { padding: 0 0 var(--space-6); }
  .atlas-auth-intro h1 { font-size: var(--font-size-4xl); }
  .atlas-auth-panel { padding: var(--space-5); }
  .auth-panel-heading { display: none; }
  .name-grid {
    grid-template-columns: 1fr;
  }
}
</style>
