<template>
  <div class="atlas-auth-page">
    <section class="atlas-auth-intro" aria-labelledby="recovery-title"><p class="atlas-auth-kicker">{{ t('passwordRecovery.eyebrow') }}</p><h1 id="recovery-title">{{ t('passwordRecovery.title') }}</h1><p>{{ t('passwordRecovery.subtitle') }}</p><div class="atlas-auth-rule" aria-hidden="true" /><p class="atlas-auth-note">{{ t('passwordRecovery.note') }}</p></section>
    <section class="atlas-auth-panel"><header class="auth-panel-heading"><p class="atlas-auth-kicker">{{ t('passwordRecovery.eyebrow') }}</p><h2>{{ t('passwordRecovery.title') }}</h2></header>

      <form v-if="step === 'request'" class="auth-form" :aria-busy="loading" @submit.prevent="sendResetCode">
        <label class="field">
          <span>{{ t('passwordRecovery.email') }}</span>
          <input
            v-model.trim="form.email"
            type="email"
            autocomplete="email"
            required
            :placeholder="t('passwordRecovery.emailPlaceholder')"
          />
        </label>

        <p v-if="error" class="error-box" role="alert">{{ error }}</p>

        <button class="btn-primary" :disabled="loading || !isLoaded">
          {{ loading ? t('passwordRecovery.sending') : t('passwordRecovery.send') }}
        </button>
      </form>

      <form v-else class="auth-form" :aria-busy="loading" @submit.prevent="resetPassword">
        <p class="verification-copy">
          {{ t('passwordRecovery.verificationCopy', { email: form.email }) }}
        </p>

        <label class="field">
          <span>{{ t('passwordRecovery.code') }}</span>
          <input
            v-model.trim="form.code"
            type="text"
            inputmode="numeric"
            autocomplete="one-time-code"
            required
            :placeholder="t('passwordRecovery.codePlaceholder')"
          />
        </label>

        <label class="field">
          <span>{{ t('passwordRecovery.password') }}</span>
          <input
            v-model="form.password"
            type="password"
            autocomplete="new-password"
            required
            :placeholder="t('passwordRecovery.passwordPlaceholder')"
          />
        </label>
        <PasswordPolicyChecklist :policy="passwordPolicy" />

        <p v-if="error" class="error-box" role="alert">{{ error }}</p>

        <button class="btn-primary" :disabled="loading || !isLoaded || !passwordPolicy.passesRequiredRules.value">
          {{ loading ? t('passwordRecovery.resetting') : t('passwordRecovery.reset') }}
        </button>

        <button class="btn-link" type="button" :disabled="loading" @click="sendResetCode">
          {{ t('passwordRecovery.resend') }}
        </button>

        <button class="btn-link" type="button" :disabled="loading" @click="backToRequest">
          {{ t('passwordRecovery.differentEmail') }}
        </button>
      </form>

      <p class="auth-switch">
        {{ t('passwordRecovery.remembered') }}
        <router-link to="/sign-in">{{ t('passwordRecovery.signIn') }}</router-link>
      </p>
    </section>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useClerk, useSignIn } from '@clerk/vue'

import PasswordPolicyChecklist from '../components/PasswordPolicyChecklist.vue'
import { usePasswordPolicy } from '../composables/usePasswordPolicy'
import { activateSessionAndHydrateAuth } from '../lib/clerkSession'
import { userFacingError } from '../lib/userFacingError'

const router = useRouter()
const { t } = useI18n()
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
const passwordPolicy = usePasswordPolicy({
  password: computed(() => form.password),
  validator: computed(() => signIn.value?.validatePassword),
  clerk,
})

function authError(err) {
  return userFacingError(err, t('passwordRecovery.errors.fallback'))
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

  if (!passwordPolicy.passesRequiredRules.value) {
    error.value = t('passwordRecovery.errors.requirements')
    return
  }

  loading.value = true
  error.value = ''

  try {
    const result = await signIn.value.attemptFirstFactor({
      strategy: 'reset_password_email_code',
      code: form.code,
      password: form.password,
    })

    if (result.status === 'needs_second_factor') {
      error.value = t('passwordRecovery.errors.secondFactor')
      router.push('/sign-in')
      return
    }

    if (result.status !== 'complete' || !result.createdSessionId) {
      error.value = t('passwordRecovery.errors.complete')
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
.atlas-auth-page { align-items: start; display: grid; gap: var(--space-12); grid-template-columns: minmax(0,.8fr) minmax(20rem,1fr); margin: 0 auto; max-width: 64rem; padding: var(--space-12) 0; }
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
  border-radius: var(--radius-md); min-height: var(--control-height-lg); padding: 0 var(--space-5); width: 100%;
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
.btn-primary:hover:not(:disabled) { background: var(--color-accent-hover); }
.btn-primary:focus-visible,.btn-link:focus-visible,.auth-switch a:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
@media(max-width:640px){.atlas-auth-page{display:block;padding:var(--space-6) 0}.atlas-auth-intro{padding:0 0 var(--space-6)}.atlas-auth-intro h1{font-size:var(--font-size-4xl)}.atlas-auth-panel{padding:var(--space-5)}.auth-panel-heading{display:none}}
</style>
