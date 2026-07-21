<template>
  <AtlasAuthLayout><template #intro><h1 id="username-title">{{ t('usernameContinuation.title') }}</h1><p>{{ t('usernameContinuation.subtitle') }}</p></template>

      <form v-if="canCompleteUsername" class="auth-form" :aria-busy="loading" @submit.prevent="completeUsername">
        <label class="field">
          <span>{{ t('usernameContinuation.username') }}</span>
          <input
            v-model.trim="form.username"
            type="text"
            autocomplete="username"
            required
            :placeholder="t('usernameContinuation.placeholder')"
          />
        </label>

        <p v-if="error" class="error-box" role="alert">{{ error }}</p>

        <button class="btn-primary" :disabled="loading || !form.username">
          {{ loading ? t('usernameContinuation.saving') : t('usernameContinuation.continue') }}
        </button>
      </form>

      <div v-else class="auth-form">
        <p class="verification-copy">{{ fallbackCopy }}</p>
        <p v-if="error" class="error-box" role="alert">{{ error }}</p>
        <router-link class="btn-primary link-button" to="/sign-up">{{ t('usernameContinuation.return') }}</router-link>
      </div>
  </AtlasAuthLayout>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useClerk, useSignUp } from '@clerk/vue'

import { activateSessionAndHydrateAuth } from '../lib/clerkSession'
import { consumePostAuthRedirect } from '../lib/postAuthRedirect'
import { userFacingError } from '../lib/userFacingError'
import AtlasAuthLayout from '../ui/patterns/AtlasAuthLayout.vue'

const router = useRouter()
const { t } = useI18n()
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
  if (!isLoaded.value) return t('usernameContinuation.loading')
  return t('usernameContinuation.fallback')
})

watch(
  () => signUp.value?.username,
  (username) => {
    form.username = username || ''
  },
  { immediate: true }
)

function authError(err) {
  return userFacingError(err, t('usernameContinuation.errors.fallback'))
}

async function completeSession(result) {
  if (!setActive.value || !result.createdSessionId) {
    error.value = t('usernameContinuation.errors.session')
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
    error.value = t('usernameContinuation.errors.required')
    return
  }

  if (result.unverifiedFields?.includes('email_address')) {
    router.push('/sign-up')
    return
  }

  error.value = t('usernameContinuation.errors.complete')
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
.verification-copy{background:var(--color-surface-inset);border-left:var(--border-width-strong) solid var(--color-accent);color:var(--color-text-muted);font-size:var(--font-size-sm);line-height:var(--line-height-relaxed);padding:var(--space-4)}

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
  color: var(--color-text-muted);
  font-size: 13px;
}

input {
  background: var(--color-surface-raised); border: var(--border-width-thin) solid var(--color-border); border-radius: var(--radius-md); color: var(--color-text);
  font-size: 15px;
  min-height:var(--control-height-lg);padding:0 var(--space-3);
}

.btn-primary {
  background: var(--color-accent);
  border: none;
  border-radius: var(--radius-md); color: var(--color-accent-contrast);
  cursor: pointer;
  font-weight: 700;
  min-height:var(--control-height-lg);padding:0 var(--space-4);
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
  background: var(--color-danger-surface);border:var(--border-width-thin) solid var(--color-danger);color:var(--color-danger);
  font-size: 14px;
  padding: 12px;
}
.btn-primary:focus-visible,input:focus-visible{outline:var(--border-width-strong) solid var(--color-focus);outline-offset:3px}
</style>
