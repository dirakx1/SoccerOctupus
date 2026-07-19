<template>
  <AtlasAuthLayout>
    <template #intro>
      <h1 id="sign-in-title">{{ t('signIn.title') }}</h1>
      <p>{{ t('signIn.subtitle') }}</p>
    </template>
      <form v-if="step === 'credentials'" class="auth-form" :aria-busy="loading || Boolean(loadingStrategy)" @submit.prevent="submit">
        <template v-if="!resumingPasswordFirstFactor">
          <SocialAuthButtons
            :disabled="loading || !isLoaded"
            :loading-provider="loadingStrategy"
            appearance="atlas"
            :labels="providerLabels"
            @select="signInWithProvider"
          />

          <div class="auth-divider"><span>{{ t('signIn.divider') }}</span></div>

          <label class="field">
            <span>{{ t('signIn.identifier') }}</span>
            <input
              v-model.trim="form.identifier"
              type="text"
              autocomplete="username"
              required
              :placeholder="t('signIn.identifierPlaceholder')"
            />
          </label>
        </template>

        <p v-else class="verification-copy">{{ t('signIn.verification.passwordResume') }}</p>

        <label class="field">
          <span>{{ t('signIn.password') }}</span>
          <input
            v-model="form.password"
            type="password"
            autocomplete="current-password"
            required
            :placeholder="t('signIn.passwordPlaceholder')"
          />
        </label>

        <router-link v-if="!resumingPasswordFirstFactor" class="forgot-link" to="/forgot-password">{{ t('signIn.forgot') }}</router-link>

        <p v-if="error" class="error-box" role="alert">{{ error }}</p>

        <button class="btn-primary" :disabled="!canSubmit">
          {{ loading ? t('signIn.submitting') : (resumingPasswordFirstFactor ? t('signIn.continue') : t('signIn.submit')) }}
        </button>
      </form>

      <form v-else class="auth-form" :aria-busy="loading" @submit.prevent="verifyCode">
        <p class="verification-copy">{{ verificationCopy }}</p>

        <label class="field">
          <span>{{ verificationLabel }}</span>
          <input
            v-model.trim="form.code"
            type="text"
            :inputmode="codeInputMode"
            autocomplete="one-time-code"
            required
            :placeholder="verificationPlaceholder"
          />
        </label>

        <p v-if="error" class="error-box" role="alert">{{ error }}</p>

        <button class="btn-primary" :disabled="loading || !isLoaded">
          {{ loading ? t('signIn.verifying') : t('signIn.verify') }}
        </button>

        <button
          v-if="canSwitchSecondFactor"
          class="btn-link second-factor-switch"
          type="button"
          :disabled="loading"
          @click="switchSecondFactor"
        >
          {{ secondFactorSwitchLabel }}
        </button>

        <button
          v-if="canResendCode"
          class="btn-link"
          type="button"
          :disabled="loading"
          @click="resendCode"
        >
          {{ t('signIn.resend') }}
        </button>

        <button class="btn-link" type="button" :disabled="loading" @click="backToCredentials">
          {{ t('signIn.differentAccount') }}
        </button>
      </form>

      <p class="auth-switch">
        {{ t('signIn.createPrompt') }}
        <router-link to="/sign-up">{{ t('signIn.createAccount') }}</router-link>
      </p>
  </AtlasAuthLayout>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useClerk, useSignIn } from '@clerk/vue'

import SocialAuthButtons from '../components/SocialAuthButtons.vue'
import AtlasAuthLayout from '../ui/patterns/AtlasAuthLayout.vue'
import { activateSessionAndHydrateAuth } from '../lib/clerkSession'
import { clearPostAuthCompletion, startPostAuthCompletion } from '../lib/postAuthCompletion'
import { consumePostAuthRedirect, peekPostAuthRedirect } from '../lib/postAuthRedirect'
import { userFacingError } from '../lib/userFacingError'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const clerk = useClerk()
const { isLoaded, signIn, setActive } = useSignIn()

const loading = ref(false)
const loadingStrategy = ref('')
const error = ref('')
const step = ref('credentials')
const resumingPasswordFirstFactor = ref(false)
const verificationReason = ref('')
const verificationStage = ref('')
const verificationStrategy = ref('')
const verificationTarget = ref('')
const availableSecondFactorStrategies = ref([])
const form = reactive({
  identifier: '',
  password: '',
  code: '',
})
let resumedSignIn = null

const codeStrategies = ['email_code', 'phone_code']
const supportedSecondFactorStrategies = ['totp', 'email_code', 'phone_code', 'backup_code']

const canResendCode = computed(() => codeStrategies.includes(verificationStrategy.value))
const canSubmit = computed(() => (
  isLoaded.value
  && !loading.value
  && !loadingStrategy.value
  && Boolean(form.password)
  && (resumingPasswordFirstFactor.value || Boolean(form.identifier))
))
const codeInputMode = computed(() => verificationStrategy.value === 'backup_code' ? 'text' : 'numeric')
const verificationLabel = computed(() => t(verificationStrategy.value === 'backup_code' ? 'signIn.verification.backupCode' : 'signIn.verification.code'))
const verificationPlaceholder = computed(() => t(verificationStrategy.value === 'backup_code' ? 'signIn.verification.backupPlaceholder' : 'signIn.verification.codePlaceholder'))
const providerLabels = {
  continueWith: (name) => t('signIn.provider.continueWith', { name }),
  opening: (name) => t('signIn.provider.opening', { name }),
}
const canSwitchSecondFactor = computed(() => (
  verificationStage.value === 'second'
  && availableSecondFactorStrategies.value.includes('totp')
  && availableSecondFactorStrategies.value.includes('backup_code')
  && ['totp', 'backup_code'].includes(verificationStrategy.value)
))
const secondFactorSwitchLabel = computed(() => verificationStrategy.value === 'totp'
  ? t('signIn.switchBackup')
  : t('signIn.switchAuthenticator'))
const verificationCopy = computed(() => {
  if (verificationReason.value === 'client_trust') {
    if (verificationStrategy.value === 'phone_code') {
      return t('signIn.verification.clientTrustPhone', { target: verificationTarget.value || t('signIn.verification.yourPhone') })
    }

    return t('signIn.verification.clientTrustEmail', { target: verificationTarget.value || form.identifier })
  }

  if (verificationStrategy.value === 'totp') {
    return t('signIn.verification.authenticator')
  }

  if (verificationStrategy.value === 'backup_code') {
    return t('signIn.verification.backupCopy')
  }

  if (verificationStrategy.value === 'phone_code') {
    return t('signIn.verification.phone', { target: verificationTarget.value || t('signIn.verification.yourPhone') })
  }

  return t('signIn.verification.email', { target: verificationTarget.value || form.identifier })
})

function authError(err) {
  return userFacingError(err, t('signIn.errors.fallback'))
}

function findFactor(factors = [], strategies = []) {
  return strategies.map((strategy) => factors.find((factor) => factor.strategy === strategy)).find(Boolean)
}

function codeFactorParams(factor, stage) {
  if (factor.strategy === 'email_code') {
    return { strategy: 'email_code', emailAddressId: factor.emailAddressId }
  }

  const params = { strategy: 'phone_code', phoneNumberId: factor.phoneNumberId }
  if (stage === 'first' && factor.channel) {
    params.channel = factor.channel
  }
  return params
}

function unsupportedFactorMessage(factors = []) {
  const methods = factors.map((factor) => factor.strategy).filter(Boolean).join(', ')
  return methods
    ? t('signIn.errors.unsupported', { methods })
    : t('signIn.errors.unsupportedGeneric')
}

function getCreatedSessionId(result) {
  return result?.createdSessionId || signIn.value?.createdSessionId
}

async function completeSignIn(result) {
  const sessionId = getCreatedSessionId(result)

  if (!sessionId) {
    error.value = t('signIn.errors.activate')
    return
  }

  await activateSessionAndHydrateAuth({
    clerk,
    setActive: setActive.value,
    sessionId,
  })
  router.push(consumePostAuthRedirect() || '/')
}

async function prepareCodeVerification(stage, factor) {
  if (verificationReason.value !== 'client_trust') {
    verificationReason.value = ''
  }
  verificationStage.value = stage
  verificationStrategy.value = factor.strategy
  verificationTarget.value = factor.safeIdentifier || ''
  form.code = ''

  if (stage === 'first') {
    await signIn.value.prepareFirstFactor(codeFactorParams(factor, stage))
  } else {
    await signIn.value.prepareSecondFactor(codeFactorParams(factor, stage))
  }

  step.value = 'verify'
}

function prepareLocalVerification(stage, factor) {
  verificationReason.value = ''
  verificationStage.value = stage
  verificationStrategy.value = factor.strategy
  verificationTarget.value = ''
  form.code = ''
  step.value = 'verify'
}

function switchSecondFactor() {
  if (!canSwitchSecondFactor.value) return

  verificationStrategy.value = verificationStrategy.value === 'totp' ? 'backup_code' : 'totp'
  form.code = ''
  error.value = ''
}

async function handleSignInResult(result, attemptedPasswordFactor = false) {
  const currentSignIn = result || signIn.value

  if (getCreatedSessionId(currentSignIn) || currentSignIn?.status === 'complete') {
    await completeSignIn(result)
    return true
  }

  if (currentSignIn?.status === 'needs_identifier') {
    error.value = t('signIn.errors.identifier')
    return false
  }

  if (currentSignIn?.status === 'needs_first_factor') {
    const firstFactors = currentSignIn.supportedFirstFactors || []
    const passwordFactor = findFactor(firstFactors, ['password'])

    if (passwordFactor && !attemptedPasswordFactor) {
      const passwordResult = await signIn.value.attemptFirstFactor({
        strategy: 'password',
        password: form.password,
      })
      return await handleSignInResult(passwordResult, true)
    }

    const codeFactor = findFactor(firstFactors, codeStrategies)
    if (codeFactor) {
      await prepareCodeVerification('first', codeFactor)
      return true
    }

    error.value = unsupportedFactorMessage(firstFactors)
    return false
  }

  if (currentSignIn?.status === 'needs_second_factor') {
    const secondFactors = currentSignIn.supportedSecondFactors || []
    const secondFactor = findFactor(secondFactors, supportedSecondFactorStrategies)

    if (!secondFactor) {
      error.value = unsupportedFactorMessage(secondFactors)
      return false
    }

    availableSecondFactorStrategies.value = secondFactors
      .map((factor) => factor.strategy)
      .filter((strategy) => ['totp', 'backup_code'].includes(strategy))

    if (codeStrategies.includes(secondFactor.strategy)) {
      availableSecondFactorStrategies.value = []
      await prepareCodeVerification('second', secondFactor)
    } else {
      prepareLocalVerification('second', secondFactor)
    }

    return true
  }

  if (currentSignIn?.status === 'needs_client_trust') {
    const secondFactors = currentSignIn.supportedSecondFactors || []
    const secondFactor = findFactor(secondFactors, codeStrategies)

    if (!secondFactor) {
      error.value = unsupportedFactorMessage(secondFactors)
      return false
    }

    verificationReason.value = 'client_trust'
    await prepareCodeVerification('second', secondFactor)
    return true
  }

  if (currentSignIn?.status === 'needs_new_password') {
    error.value = t('signIn.errors.newPassword')
    return false
  }

  error.value = t('signIn.errors.complete')
  return false
}

async function resumePendingSignIn() {
  if (route.query.resume !== 'oauth') return
  if (!isLoaded.value || !signIn.value || resumedSignIn === signIn.value) return

  if (!['needs_first_factor', 'needs_second_factor', 'needs_client_trust'].includes(signIn.value.status)) return

  resumedSignIn = signIn.value
  loading.value = true
  error.value = ''

  try {
    if (signIn.value.status === 'needs_first_factor') {
      const firstFactors = signIn.value.supportedFirstFactors || []
      const passwordFactor = findFactor(firstFactors, ['password'])
      const codeFactor = findFactor(firstFactors, codeStrategies)

      if (codeFactor) {
        await handleSignInResult(signIn.value, true)
      } else if (passwordFactor) {
        resumingPasswordFirstFactor.value = true
        step.value = 'credentials'
      } else {
        error.value = unsupportedFactorMessage(firstFactors)
      }
    } else {
      await handleSignInResult(signIn.value)
    }
  } catch (err) {
    error.value = authError(err)
  } finally {
    loading.value = false
  }
}

watch([isLoaded, () => signIn.value?.status], resumePendingSignIn, { immediate: true })

async function submit() {
  if (!isLoaded.value || !signIn.value || !setActive.value) return
  if (!canSubmit.value) return

  loading.value = true
  error.value = ''
  form.code = ''

  try {
    const wasResumingPasswordFirstFactor = resumingPasswordFirstFactor.value
    const result = wasResumingPasswordFirstFactor
      ? await signIn.value.attemptFirstFactor({
        strategy: 'password',
        password: form.password,
      })
      : await signIn.value.create({
        strategy: 'password',
        identifier: form.identifier,
        password: form.password,
      })

    if (wasResumingPasswordFirstFactor) resumingPasswordFirstFactor.value = false
    await handleSignInResult(result, wasResumingPasswordFirstFactor)
  } catch (err) {
    error.value = authError(err)
  } finally {
    loading.value = false
  }
}

async function signInWithProvider(strategy) {
  if (!isLoaded.value || !signIn.value) return

  loadingStrategy.value = strategy
  error.value = ''
  startPostAuthCompletion()

  try {
    await signIn.value.authenticateWithRedirect({
      strategy,
      redirectUrl: '/sso-callback',
      redirectUrlComplete: peekPostAuthRedirect() || '/',
    })
  } catch (err) {
    clearPostAuthCompletion()
    loadingStrategy.value = ''
    error.value = authError(err)
  }
}

async function verifyCode() {
  if (!isLoaded.value || !signIn.value || !setActive.value) return

  loading.value = true
  error.value = ''

  try {
    const result = verificationStage.value === 'second'
      ? await signIn.value.attemptSecondFactor({ strategy: verificationStrategy.value, code: form.code })
      : await signIn.value.attemptFirstFactor({ strategy: verificationStrategy.value, code: form.code })

    await handleSignInResult(result)
  } catch (err) {
    error.value = authError(err)
  } finally {
    loading.value = false
  }
}

async function resendCode() {
  if (!isLoaded.value || !signIn.value || !canResendCode.value) return

  loading.value = true
  error.value = ''

  try {
    const factors = verificationStage.value === 'second'
      ? signIn.value.supportedSecondFactors || []
      : signIn.value.supportedFirstFactors || []
    const factor = findFactor(factors, [verificationStrategy.value])

    if (!factor) {
      error.value = t('signIn.errors.resend')
      return
    }

    if (verificationStage.value === 'second') {
      await signIn.value.prepareSecondFactor(codeFactorParams(factor, verificationStage.value))
    } else {
      await signIn.value.prepareFirstFactor(codeFactorParams(factor, verificationStage.value))
    }
  } catch (err) {
    error.value = authError(err)
  } finally {
    loading.value = false
  }
}

function backToCredentials() {
  step.value = 'credentials'
  verificationReason.value = ''
  verificationStage.value = ''
  verificationStrategy.value = ''
  verificationTarget.value = ''
  availableSecondFactorStrategies.value = []
  form.code = ''
  error.value = ''
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

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  color: var(--color-text-muted);
  font-size: 13px;
}

.forgot-link {
  align-self: flex-end;
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
}

.forgot-link:hover {
  text-decoration: underline;
}

input {
  background: var(--color-surface-raised);
  border: var(--border-width-thin) solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  font: var(--font-weight-medium) var(--font-size-sm) / var(--line-height-normal) var(--font-family-body);
  min-height: var(--control-height-lg);
  padding: 0 var(--space-3);
  width: 100%;
}

input:focus { border-color: var(--color-accent); outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 1px; }

.verification-copy {
  background: var(--color-surface-inset);
  border-left: var(--border-width-strong) solid var(--color-accent);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
  margin: 0;
  padding: var(--space-3) var(--space-4);
}

.btn-primary {
  align-items: center;
  background: var(--color-accent);
  border: 0;
  border-radius: var(--radius-md);
  color: var(--color-accent-contrast);
  cursor: pointer;
  display: inline-flex;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  justify-content: center;
  min-height: var(--control-height-lg);
  padding: 0 var(--space-5);
  width: 100%;
}
.btn-primary:hover:not(:disabled) { background: var(--color-accent-hover); }
.btn-primary:focus-visible, .btn-link:focus-visible, .forgot-link:focus-visible, .auth-switch a:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.btn-primary:disabled { cursor: not-allowed; opacity: 0.55; }

.btn-link {
  align-self: center;
  background: transparent;
  border: none;
  color: var(--color-accent);
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  min-height: var(--control-height-lg);
  padding: 0 var(--space-3);
}

.btn-link:disabled {
  cursor: default;
  opacity: 0.55;
}

.error-box {
  background: var(--color-danger-surface);
  border: var(--border-width-thin) solid var(--color-danger);
  color: var(--color-danger);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
  padding: var(--space-3) var(--space-4);
}

.auth-switch {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin: var(--space-6) 0 0;
  text-align: center;
}

.auth-switch a {
  color: var(--color-accent);
  font-weight: 700;
  text-decoration: none;
}

</style>
