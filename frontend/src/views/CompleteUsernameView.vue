<template>
  <div class="atlas-auth-page"><section class="atlas-auth-intro" aria-labelledby="username-title"><h1 id="username-title">{{ t('usernameContinuation.title') }}</h1><p>{{ t('usernameContinuation.subtitle') }}</p></section><section class="atlas-auth-panel">

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
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useClerk, useSignUp } from '@clerk/vue'

import { activateSessionAndHydrateAuth } from '../lib/clerkSession'
import { consumePostAuthRedirect } from '../lib/postAuthRedirect'
import { userFacingError } from '../lib/userFacingError'

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
.atlas-auth-page{align-items:start;display:grid;gap:var(--space-12);grid-template-columns:minmax(0,.8fr) minmax(20rem,1fr);margin:0 auto;max-width:64rem;padding:var(--space-12) 0}.atlas-auth-intro{align-self:center;padding:var(--space-6) 0}.atlas-auth-kicker{color:var(--color-accent);font:var(--font-weight-bold) var(--font-size-xs)/var(--line-height-normal) var(--font-family-data);margin:0 0 var(--space-3);text-transform:uppercase}.atlas-auth-intro h1{font-family:var(--font-family-display);font-size:var(--font-size-5xl);line-height:var(--line-height-tight);margin:0;max-width:8ch}.atlas-auth-intro>p:not(.atlas-auth-kicker){color:var(--color-text-muted);font-size:var(--font-size-lg);line-height:var(--line-height-relaxed);margin:var(--space-5) 0 0;max-width:30ch}.atlas-auth-rule{background:var(--color-accent);height:var(--border-width-strong);margin-top:var(--space-8);width:4rem}.atlas-auth-note{font-size:var(--font-size-sm)!important}.atlas-auth-panel{background:var(--color-surface);border:var(--border-width-thin) solid var(--color-border);padding:var(--space-8)}.auth-panel-heading{border-bottom:var(--border-width-thin) solid var(--color-border);margin-bottom:var(--space-6);padding-bottom:var(--space-5)}.auth-panel-heading h2{font-family:var(--font-family-display);font-size:var(--font-size-3xl);margin:0}.verification-copy{background:var(--color-surface-inset);border-left:var(--border-width-strong) solid var(--color-accent);color:var(--color-text-muted);font-size:var(--font-size-sm);line-height:var(--line-height-relaxed);padding:var(--space-4)}

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
.btn-primary:focus-visible,input:focus-visible{outline:var(--border-width-strong) solid var(--color-focus);outline-offset:3px}@media(max-width:640px){.atlas-auth-page{display:block;padding:var(--space-6) 0}.atlas-auth-intro{padding:0 0 var(--space-6)}.atlas-auth-intro h1{font-size:var(--font-size-4xl)}.atlas-auth-panel{padding:var(--space-5)}.auth-panel-heading{display:none}}
</style>
