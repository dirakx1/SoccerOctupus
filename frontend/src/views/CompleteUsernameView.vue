<template>
  <div class="auth-page">
    <section class="auth-panel">
      <div class="eyebrow">Finish setup</div>
      <h1>Choose username</h1>
      <p class="subtitle">Add the username required for this account.</p>

      <form v-if="canCompleteUsername" class="auth-form" @submit.prevent="completeUsername">
        <label class="field">
          <span>Username</span>
          <input
            v-model.trim="form.username"
            type="text"
            autocomplete="username"
            required
            placeholder="alexmorgan"
          />
        </label>

        <p v-if="error" class="error-box">{{ error }}</p>

        <button class="btn-primary" :disabled="loading || !form.username">
          {{ loading ? 'Saving...' : 'Continue' }}
        </button>
      </form>

      <div v-else class="auth-form">
        <p class="verification-copy">{{ fallbackCopy }}</p>
        <p v-if="error" class="error-box">{{ error }}</p>
        <router-link class="btn-primary link-button" to="/sign-up">Return to sign up</router-link>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useClerk, useSignUp } from '@clerk/vue'

import { activateSessionAndHydrateAuth } from '../lib/clerkSession'
import { consumePostAuthRedirect } from '../lib/postAuthRedirect'
import { userFacingError } from '../lib/userFacingError'

const router = useRouter()
const clerk = useClerk()
const { isLoaded, signUp, setActive } = useSignUp()

const loading = ref(false)
const error = ref('')
const form = reactive({
  username: '',
})

const missingFields = computed(() => signUp.value?.missingFields || [])
const canCompleteUsername = computed(() => {
  return isLoaded.value && signUp.value?.status === 'missing_requirements' && missingFields.value.includes('username')
})
const fallbackCopy = computed(() => {
  if (!isLoaded.value) return 'Loading your sign-up.'
  return 'No pending username step is available. Start sign-up again to continue.'
})

watch(
  () => signUp.value?.username,
  (username) => {
    form.username = username || ''
  },
  { immediate: true }
)

function authError(err) {
  return userFacingError(err, 'Unable to save username. Please try again.')
}

async function completeSession(result) {
  if (!setActive.value || !result.createdSessionId) {
    error.value = 'Username saved, but your session could not be started. Please sign in.'
    return
  }

  await activateSessionAndHydrateAuth({
    clerk,
    setActive: setActive.value,
    sessionId: result.createdSessionId,
  })
  router.push(consumePostAuthRedirect() || '/')
}

async function handleSignUpResult(result) {
  if (result.status === 'complete') {
    await completeSession(result)
    return
  }

  if (result.missingFields?.includes('username')) {
    error.value = 'Choose a username to continue.'
    return
  }

  if (result.unverifiedFields?.includes('email_address')) {
    router.push('/sign-up')
    return
  }

  error.value = 'Unable to complete sign-up. Please try again.'
}

async function completeUsername() {
  if (!canCompleteUsername.value || !form.username) return

  loading.value = true
  error.value = ''

  try {
    const result = await signUp.value.update({ username: form.username })
    await handleSignUpResult(result)
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
  width: min(100%, 520px);
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 12px;
  padding: 32px;
}

.eyebrow {
  color: #e2b714;
  font-size: 12px;
  letter-spacing: 0.08em;
  margin-bottom: 10px;
  text-transform: uppercase;
}

h1 {
  color: #e0e0e0;
  font-size: 30px;
  margin-bottom: 8px;
}

.subtitle,
.verification-copy {
  color: #8888aa;
  font-size: 14px;
}

.subtitle {
  margin-bottom: 24px;
}

.auth-form,
.field {
  display: flex;
  flex-direction: column;
}

.auth-form {
  gap: 16px;
}

.field {
  gap: 6px;
}

.field span {
  color: #8888aa;
  font-size: 13px;
}

input {
  background: #0f3460;
  border: 1px solid #1f4c7a;
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 15px;
  padding: 12px;
}

.btn-primary {
  background: #e2b714;
  border: none;
  border-radius: 8px;
  color: #16213e;
  cursor: pointer;
  font-weight: 700;
  padding: 12px 18px;
  text-align: center;
  text-decoration: none;
}

.btn-primary:disabled {
  cursor: default;
  opacity: 0.55;
}

.link-button {
  display: inline-flex;
  justify-content: center;
}

.error-box {
  background: rgba(220, 38, 38, 0.16);
  border-radius: 8px;
  color: #fecaca;
  font-size: 14px;
  padding: 12px;
}
</style>
