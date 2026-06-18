<template>
  <div class="auth-page">
    <section class="auth-panel">
      <div class="eyebrow">Account recovery</div>
      <h1>Reset password</h1>
      <p class="subtitle">We will send a verification code so you can set a new password.</p>

      <form v-if="step === 'request'" class="auth-form" @submit.prevent="sendResetCode">
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

        <p v-if="error" class="error-box">{{ error }}</p>

        <button class="btn-primary" :disabled="loading || !isLoaded">
          {{ loading ? 'Sending code...' : 'Send reset code' }}
        </button>
      </form>

      <form v-else class="auth-form" @submit.prevent="resetPassword">
        <p class="verification-copy">
          Enter the verification code Clerk sent to {{ form.email }} and choose a new password.
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

        <label class="field">
          <span>New password</span>
          <input
            v-model="form.password"
            type="password"
            autocomplete="new-password"
            required
            minlength="8"
            placeholder="Create a new password"
          />
        </label>

        <p v-if="error" class="error-box">{{ error }}</p>

        <button class="btn-primary" :disabled="loading || !isLoaded">
          {{ loading ? 'Resetting password...' : 'Reset password' }}
        </button>

        <button class="btn-link" type="button" :disabled="loading" @click="sendResetCode">
          Resend code
        </button>

        <button class="btn-link" type="button" :disabled="loading" @click="backToRequest">
          Use a different email
        </button>
      </form>

      <p class="auth-switch">
        Remembered it?
        <router-link to="/sign-in">Sign in</router-link>
      </p>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useClerk, useSignIn } from '@clerk/vue'

import { activateSessionAndHydrateAuth } from '../lib/clerkSession'

const router = useRouter()
const clerk = useClerk()
const { isLoaded, signIn, setActive } = useSignIn()

const step = ref('request')
const loading = ref(false)
const error = ref('')
const form = reactive({
  email: '',
  code: '',
  password: '',
})

function authError(err) {
  return err?.response?.data?.error || err?.errors?.[0]?.longMessage || err?.errors?.[0]?.message || err?.message || 'Unable to reset your password. Please try again.'
}

async function sendResetCode() {
  if (!isLoaded.value || !signIn.value) return

  loading.value = true
  error.value = ''

  try {
    await signIn.value.create({
      strategy: 'reset_password_email_code',
      identifier: form.email,
    })
    form.code = ''
    form.password = ''
    step.value = 'reset'
  } catch (err) {
    error.value = authError(err)
  } finally {
    loading.value = false
  }
}

async function resetPassword() {
  if (!isLoaded.value || !signIn.value || !setActive.value) return

  loading.value = true
  error.value = ''

  try {
    const result = await signIn.value.attemptFirstFactor({
      strategy: 'reset_password_email_code',
      code: form.code,
      password: form.password,
    })

    if (result.status === 'needs_second_factor') {
      error.value = 'Password reset succeeded, but this account requires an additional verification step. Please sign in to continue.'
      router.push('/sign-in')
      return
    }

    if (result.status !== 'complete' || !result.createdSessionId) {
      error.value = result.status
        ? `Unable to complete password reset from Clerk status: ${result.status}.`
        : 'Unable to complete password reset. Clerk did not return a session.'
      return
    }

    await activateSessionAndHydrateAuth({
      clerk,
      setActive: setActive.value,
      sessionId: result.createdSessionId,
    })
    router.push('/')
  } catch (err) {
    error.value = authError(err)
  } finally {
    loading.value = false
  }
}

function backToRequest() {
  step.value = 'request'
  form.code = ''
  form.password = ''
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
