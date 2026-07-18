<template>
  <div class="atlas-auth-page">
    <section class="atlas-auth-intro" aria-labelledby="callback-title">
      <h1 id="callback-title">{{ copy('title') }}</h1>
      <p>{{ copy('subtitle') }}</p>
    </section>

    <section class="atlas-auth-panel" aria-labelledby="callback-status">
      <div class="callback-status" role="status" aria-live="polite">
        <div class="spinner" aria-hidden="true" />
        <p class="atlas-auth-kicker">{{ copy('status') }}</p>
        <h2 id="callback-status">{{ copy('title') }}</h2>
        <p class="callback-copy">{{ copy('waiting') }}</p>
      </div>

      <AuthenticateWithRedirectCallback
        :sign-in-force-redirect-url="redirectTarget"
        :sign-up-force-redirect-url="redirectTarget"
        :sign-in-fallback-redirect-url="redirectTarget"
        :sign-up-fallback-redirect-url="redirectTarget"
        continue-sign-up-url="/complete-username"
        first-factor-url="/sign-in?resume=oauth"
        second-factor-url="/sign-in?resume=oauth"
        sign-in-url="/sign-in"
        sign-up-url="/sign-up"
      />
      <div id="clerk-captcha" />

      <div class="callback-fallback">
        <p>{{ copy('takingLonger') }}</p>
        <div class="fallback-links">
          <router-link to="/sign-in">{{ copy('signIn') }}</router-link>
          <router-link to="/sign-up">{{ copy('signUp') }}</router-link>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { AuthenticateWithRedirectCallback } from '@clerk/vue'
import { useI18n } from 'vue-i18n'
import { peekPostAuthRedirect } from '../lib/postAuthRedirect'

const { t } = useI18n()
const redirectTarget = peekPostAuthRedirect() || '/'

const fallbackCopy = {
  title: 'Completing authentication',
  subtitle: 'We are finishing your sign-in.',
  status: 'Authentication in progress',
  waiting: 'Waiting for your provider.',
  takingLonger: 'Taking longer than expected?',
  signIn: 'Return to sign in',
  signUp: 'Return to sign up',
}

function copy(key) {
  const path = `oauthCallback.${key}`
  const translated = t(path)
  return translated === path ? fallbackCopy[key] : translated
}
</script>

<style scoped>
.atlas-auth-page { align-items: start; display: grid; gap: var(--space-12); grid-template-columns: minmax(0,.8fr) minmax(20rem,1fr); margin: 0 auto; max-width: 64rem; padding: var(--space-12) 0; }
.atlas-auth-intro { align-self: center; padding: var(--space-6) 0; }
.atlas-auth-kicker { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs)/var(--line-height-normal) var(--font-family-data); margin: 0 0 var(--space-3); text-transform: uppercase; }
.atlas-auth-intro h1 { font-family: var(--font-family-display); font-size: var(--font-size-5xl); line-height: var(--line-height-tight); margin: 0; max-width: 10ch; }
.atlas-auth-intro > p:not(.atlas-auth-kicker) { color: var(--color-text-muted); font-size: var(--font-size-lg); line-height: var(--line-height-relaxed); margin: var(--space-5) 0 0; max-width: 30ch; }
.atlas-auth-rule { background: var(--color-accent); height: var(--border-width-strong); margin-top: var(--space-8); width: 4rem; }
.atlas-auth-note { font-size: var(--font-size-sm) !important; }
.atlas-auth-panel { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); padding: var(--space-8); }
.callback-status { align-items: center; display: flex; flex-direction: column; text-align: center; }
.callback-status h2 { font-family: var(--font-family-display); font-size: var(--font-size-3xl); margin: 0; }
.callback-copy { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-relaxed); margin: var(--space-3) 0 0; max-width: 34ch; }

.spinner {
  animation: spin 0.8s linear infinite;
  border: var(--border-width-strong) solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 999px;
  height: 36px;
  margin-bottom: var(--space-5);
  width: 36px;
}
.callback-fallback { border-top: var(--border-width-thin) solid var(--color-border); color: var(--color-text-muted); font-size: var(--font-size-sm); margin-top: var(--space-8); padding-top: var(--space-5); text-align: center; }
.callback-fallback p { margin: 0; }
.fallback-links { display: flex; flex-wrap: wrap; gap: var(--space-4); justify-content: center; margin-top: var(--space-3); }
.fallback-links a { color: var(--color-link); font-weight: var(--font-weight-bold); }
.fallback-links a:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
#clerk-captcha { display: flex; justify-content: center; margin-top: var(--space-4); }

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media(max-width:640px) {
  .atlas-auth-page { display: block; padding: var(--space-6) 0; }
  .atlas-auth-intro { padding: 0 0 var(--space-6); }
  .atlas-auth-intro h1 { font-size: var(--font-size-4xl); }
  .atlas-auth-panel { padding: var(--space-5); }
}
</style>
