<template>
  <div class="auth-page">
    <section class="auth-panel">
      <div class="eyebrow">Create account</div>
      <h1>Sign up</h1>
      <p class="subtitle">Join the workspace to run predictions and receive role-based access.</p>

      <form v-if="step === 'details'" class="auth-form" @submit.prevent="createAccount">
        <div class="name-grid">
          <label class="field">
            <span>First name</span>
            <input v-model.trim="form.firstName" type="text" autocomplete="given-name" placeholder="Alex" />
          </label>

          <label class="field">
            <span>Last name</span>
            <input v-model.trim="form.lastName" type="text" autocomplete="family-name" placeholder="Morgan" />
          </label>
        </div>

        <label class="field">
          <span>Email address</span>
          <input
            v-model.trim="form.email"
            type="email"
            autocomplete="email"
            required
            placeholder="you@example.com"
          />
        </label>

        <label class="field">
          <span>Password</span>
          <input
            v-model="form.password"
            type="password"
            autocomplete="new-password"
            required
            minlength="8"
            placeholder="Create a password"
          />
        </label>

        <p v-if="error" class="error-box">{{ error }}</p>

        <div id="clerk-captcha" />

        <button class="btn-primary" :disabled="loading || !isLoaded">
          {{ loading ? 'Creating account...' : 'Create account' }}
        </button>
      </form>

      <form v-else class="auth-form" @submit.prevent="verifyEmail">
        <p class="verification-copy">
          Enter the verification code Clerk sent to {{ form.email }}.
        </p>

        <label class="field">
          <span>Verification code</span>
          <input
            v-model.trim="form.code"
            type="text"
            inputmode="numeric"
            autocomplete="one-time-code"
            required
            placeholder="123456"
          />
        </label>

        <p v-if="error" class="error-box">{{ error }}</p>

        <button class="btn-primary" :disabled="loading || !isLoaded">
          {{ loading ? 'Verifying...' : 'Verify email' }}
        </button>

        <button class="btn-link" type="button" :disabled="loading" @click="resendEmailCode">
          Resend code
        </button>
      </form>

      <p class="auth-switch">
        Already have an account?
        <router-link to="/sign-in">Sign in</router-link>
      </p>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useClerk, useSignUp } from '@clerk/vue'

import { activateSessionAndHydrateAuth } from '../lib/clerkSession'

const router = useRouter()
const clerk = useClerk()
const { isLoaded, signUp, setActive } = useSignUp()

const step = ref('details')
const loading = ref(false)
const error = ref('')
const form = reactive({
  firstName: '',
  lastName: '',
  email: '',
  password: '',
  code: '',
})

function authError(err) {
  return err?.response?.data?.error || err?.errors?.[0]?.longMessage || err?.errors?.[0]?.message || err?.message || 'Unable to create your account. Check your details and try again.'
}

async function completeSignUp(result) {
  if (!setActive.value || !result.createdSessionId) {
    error.value = 'Unable to activate your session. Please try signing in.'
    return
  }

  await activateSessionAndHydrateAuth({
    clerk,
    setActive: setActive.value,
    sessionId: result.createdSessionId,
  })
  router.push('/')
}

async function prepareEmailVerification() {
  const supportedStrategies = signUp.value?.verifications?.emailAddress?.supportedStrategies || []

  if (supportedStrategies.length && !supportedStrategies.includes('email_code')) {
    error.value = `This sign-up requires ${supportedStrategies.join(', ')}, which is not supported by this custom sign-up page yet.`
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

  error.value = 'Unable to complete sign-up. Please check your details and try again.'
}

async function createAccount() {
  if (!isLoaded.value || !signUp.value) return

  loading.value = true
  error.value = ''

  try {
    const result = await signUp.value.create({
      emailAddress: form.email,
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
.auth-page {
  display: flex;
  justify-content: center;
  padding: 48px 0;
}

.auth-panel {
  width: min(100%, 560px);
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
  color: #8888aa;
  font-size: 13px;
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

#clerk-captcha {
  display: flex;
  justify-content: center;
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

@media (max-width: 640px) {
  .name-grid {
    grid-template-columns: 1fr;
  }
}
</style>
