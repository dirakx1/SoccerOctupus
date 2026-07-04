<template>
  <div class="auth-page">
    <section class="auth-panel">
      <div class="eyebrow">Secure access</div>
      <h1>Sign in</h1>
      <p class="subtitle">Access the prediction workspace and admin settings.</p>

      <form v-if="step === 'credentials'" class="auth-form" @submit.prevent="submit">
        <SocialAuthButtons
          :disabled="loading || !isLoaded"
          :loading-provider="loadingStrategy"
          @select="signInWithProvider"
        />

        <div class="auth-divider"><span>or use password</span></div>

        <label class="field">
          <span>Email or username</span>
          <input
            v-model.trim="form.identifier"
            type="text"
            autocomplete="username"
            required
            placeholder="you@example.com or username"
          />
        </label>

        <label class="field">
          <span>Password</span>
          <input
            v-model="form.password"
            type="password"
            autocomplete="current-password"
            required
            placeholder="Enter your password"
          />
        </label>

        <router-link class="forgot-link" to="/forgot-password">Forgot password?</router-link>

        <p v-if="error" class="error-box">{{ error }}</p>

        <button class="btn-primary" :disabled="!canSubmit">
          {{ loading ? 'Signing in...' : 'Sign in' }}
        </button>
      </form>

      <form v-else class="auth-form" @submit.prevent="verifyCode">
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

        <p v-if="error" class="error-box">{{ error }}</p>

        <button class="btn-primary" :disabled="loading || !isLoaded">
          {{ loading ? 'Verifying...' : 'Verify' }}
        </button>

        <button
          v-if="canResendCode"
          class="btn-link"
          type="button"
          :disabled="loading"
          @click="resendCode"
        >
          Resend code
        </button>

        <button class="btn-link" type="button" :disabled="loading" @click="backToCredentials">
          Use a different account
        </button>
      </form>

      <p class="auth-switch">
        Need access?
        <router-link to="/sign-up">Create an account</router-link>
      </p>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useClerk, useSignIn } from '@clerk/vue'

import SocialAuthButtons from '../components/SocialAuthButtons.vue'
import { activateSessionAndHydrateAuth } from '../lib/clerkSession'
import { consumePostAuthRedirect, peekPostAuthRedirect } from '../lib/postAuthRedirect'

const router = useRouter()
const clerk = useClerk()
const { isLoaded, signIn, setActive } = useSignIn()

const loading = ref(false)
const loadingStrategy = ref('')
const error = ref('')
const step = ref('credentials')
const verificationReason = ref('')
const verificationStage = ref('')
const verificationStrategy = ref('')
const verificationTarget = ref('')
const form = reactive({
  identifier: '',
  password: '',
  code: '',
})

const codeStrategies = ['email_code', 'phone_code']
const supportedSecondFactorStrategies = ['totp', 'email_code', 'phone_code', 'backup_code']

const canResendCode = computed(() => codeStrategies.includes(verificationStrategy.value))
const canSubmit = computed(() => isLoaded.value && !loading.value && !loadingStrategy.value && Boolean(form.identifier && form.password))
const codeInputMode = computed(() => verificationStrategy.value === 'backup_code' ? 'text' : 'numeric')
const verificationLabel = computed(() => verificationStrategy.value === 'backup_code' ? 'Backup code' : 'Verification code')
const verificationPlaceholder = computed(() => verificationStrategy.value === 'backup_code' ? 'abcd-1234' : '123456')
const verificationCopy = computed(() => {
  if (verificationReason.value === 'client_trust') {
    if (verificationStrategy.value === 'phone_code') {
      return `This device needs one more verification. Enter the code Clerk sent to ${verificationTarget.value || 'your phone'}.`
    }

    return `This device needs one more verification. Enter the code Clerk sent to ${verificationTarget.value || form.identifier}.`
  }

  if (verificationStrategy.value === 'totp') {
    return 'Enter the code from your authenticator app.'
  }

  if (verificationStrategy.value === 'backup_code') {
    return 'Enter one of your backup codes.'
  }

  if (verificationStrategy.value === 'phone_code') {
    return `Enter the verification code Clerk sent to ${verificationTarget.value || 'your phone'}.`
  }

  return `Enter the verification code Clerk sent to ${verificationTarget.value || form.identifier}.`
})

function authError(err) {
  return err?.response?.data?.error || err?.errors?.[0]?.longMessage || err?.errors?.[0]?.message || err?.message || 'Unable to sign in. Check your details and try again.'
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
    ? `This sign-in requires ${methods}, which is not supported by this custom sign-in page yet.`
    : 'This sign-in requires a verification method that is not available for this account.'
}

function getCreatedSessionId(result) {
  return result?.createdSessionId || signIn.value?.createdSessionId
}

async function completeSignIn(result) {
  const sessionId = getCreatedSessionId(result)

  if (!sessionId) {
    error.value = 'Unable to activate your session. Please try signing in again.'
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

async function handleSignInResult(result, attemptedPasswordFactor = false) {
  const currentSignIn = result || signIn.value

  if (getCreatedSessionId(currentSignIn) || currentSignIn?.status === 'complete') {
    await completeSignIn(result)
    return true
  }

  if (currentSignIn?.status === 'needs_identifier') {
    error.value = 'Unable to find this account. Check your email or username and try again.'
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

    if (codeStrategies.includes(secondFactor.strategy)) {
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
    error.value = 'This account requires a password reset before signing in.'
    return false
  }

  error.value = currentSignIn?.status
    ? `Unable to complete sign-in from Clerk status: ${currentSignIn.status}.`
    : 'Unable to complete sign-in. Clerk did not return a sign-in status.'
  return false
}

async function submit() {
  if (!isLoaded.value || !signIn.value || !setActive.value) return
  if (!canSubmit.value) return

  loading.value = true
  error.value = ''
  form.code = ''

  try {
    const result = await signIn.value.create({
      strategy: 'password',
      identifier: form.identifier,
      password: form.password,
    })

    await handleSignInResult(result)
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

  try {
    await signIn.value.authenticateWithRedirect({
      strategy,
      redirectUrl: '/sso-callback',
      redirectUrlComplete: peekPostAuthRedirect() || '/',
    })
  } catch (err) {
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
      error.value = 'Unable to resend this verification code. Please start sign-in again.'
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
  form.code = ''
  error.value = ''
}
</script>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  padding: 48px 0;
}

.auth-panel {
  width: min(100%, 520px);
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 12px;
  padding: 32px;
}

.eyebrow {
  color: #e2b714;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 10px;
}

h1 {
  color: #e0e0e0;
  font-size: 30px;
  margin-bottom: 8px;
}

.subtitle {
  color: #8888aa;
  font-size: 14px;
  margin-bottom: 24px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.auth-divider {
  align-items: center;
  color: #8888aa;
  display: flex;
  font-size: 11px;
  gap: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.auth-divider::before,
.auth-divider::after {
  background: #0f3460;
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
  color: #8888aa;
  font-size: 13px;
}

.forgot-link {
  align-self: flex-end;
  color: #e2b714;
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
}

.forgot-link:hover {
  text-decoration: underline;
}

input {
  background: #0a0a1a;
  color: #e0e0e0;
  border: 1px solid #0f3460;
  border-radius: 8px;
  padding: 12px 14px;
  font-size: 14px;
}

input:focus {
  border-color: #e2b714;
  outline: none;
}

.verification-copy {
  background: #0f3460;
  border-radius: 8px;
  color: #c0c0d0;
  font-size: 14px;
  line-height: 1.5;
  padding: 12px 14px;
}

.btn-primary {
  background: linear-gradient(135deg, #e2b714, #f6d860);
  color: #0a0a1a;
  font-weight: 700;
  font-size: 15px;
  border: none;
  border-radius: 10px;
  padding: 13px 24px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-primary:disabled {
  cursor: default;
  opacity: 0.55;
}

.btn-link {
  align-self: center;
  background: transparent;
  border: none;
  color: #e2b714;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  padding: 4px 8px;
}

.btn-link:disabled {
  cursor: default;
  opacity: 0.55;
}

.error-box {
  background: #3d1a1a;
  border: 1px solid #c53030;
  border-radius: 8px;
  color: #fc8181;
  font-size: 13px;
  padding: 12px 14px;
}

.auth-switch {
  color: #8888aa;
  font-size: 13px;
  margin-top: 20px;
  text-align: center;
}

.auth-switch a {
  color: #e2b714;
  font-weight: 700;
  text-decoration: none;
}
</style>
