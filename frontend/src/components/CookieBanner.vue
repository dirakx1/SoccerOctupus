<template>
  <Transition name="cookie-reveal">
    <aside
      v-if="visible"
      class="cookie-banner"
      role="dialog"
      :aria-label="t('overlays.cookie.dialogLabel')"
    >
      <div class="cookie-content">
        <div class="cookie-message">
          <Cookie :size="22" aria-hidden="true" />
          <p>
            {{ t('overlays.cookie.description') }}
            {{ t('overlays.cookie.policyLead') }}
            <router-link to="/cookie-policy">{{ t('overlays.cookie.policyLink') }}</router-link>.
          </p>
        </div>
        <div class="cookie-actions">
          <button class="cookie-button cookie-button-secondary" type="button" @click="acceptNecessary">
            {{ t('overlays.cookie.necessary') }}
          </button>
          <button class="cookie-button cookie-button-primary" type="button" @click="acceptAll">
            {{ t('overlays.cookie.acceptAll') }}
          </button>
        </div>
      </div>
    </aside>
  </Transition>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Cookie } from '@lucide/vue'

const STORAGE_KEY = 'so_cookie_consent'
const visible = ref(false)
const { t } = useI18n()

function getStorage() {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

function readConsent() {
  try {
    return getStorage()?.getItem(STORAGE_KEY) || null
  } catch {
    return null
  }
}

function saveConsent(value) {
  try {
    getStorage()?.setItem(STORAGE_KEY, value)
  } catch {
    // Consent still applies for the current page session when storage is blocked.
  }
  visible.value = false
}

function acceptAll() {
  saveConsent('all')
}

function acceptNecessary() {
  saveConsent('necessary')
}

onMounted(() => {
  visible.value = !readConsent()
})
</script>

<style scoped>
.cookie-banner {
  background: var(--color-surface-raised);
  border: var(--border-width-thin) solid var(--color-border-strong);
  bottom: var(--space-4);
  box-shadow: var(--shadow-lg);
  color: var(--color-text);
  left: var(--space-4);
  padding: var(--space-4);
  position: fixed;
  right: var(--space-4);
  z-index: var(--z-overlay);
}

.cookie-content {
  align-items: center;
  display: flex;
  gap: var(--space-6);
  justify-content: space-between;
  margin: 0 auto;
  max-width: var(--content-max-width);
}

.cookie-message {
  align-items: flex-start;
  display: flex;
  flex: 1;
  gap: var(--space-3);
  min-width: 0;
}

.cookie-message > svg { color: var(--color-accent); flex: 0 0 auto; margin-top: var(--space-1); }

.cookie-message p {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
  margin: 0;
  max-width: 72ch;
}

.cookie-message a { color: var(--color-accent); font-weight: var(--font-weight-semibold); }
.cookie-message a:hover { color: var(--color-accent-hover); }

.cookie-actions { display: flex; flex: 0 0 auto; gap: var(--space-2); }

.cookie-button {
  border: var(--border-width-thin) solid transparent;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family-body);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  min-height: var(--control-height-lg);
  padding: 0 var(--space-4);
  transition: background-color var(--duration-fast) var(--easing-standard), border-color var(--duration-fast) var(--easing-standard), color var(--duration-fast) var(--easing-standard);
}

.cookie-button-secondary { background: transparent; border-color: var(--color-border); color: var(--color-text-muted); }
.cookie-button-secondary:hover { border-color: var(--color-border-strong); color: var(--color-text); }
.cookie-button-primary { background: var(--color-accent); color: var(--color-accent-contrast); }
.cookie-button-primary:hover { background: var(--color-accent-hover); }

.cookie-button:focus-visible,
.cookie-message a:focus-visible {
  outline: var(--border-width-strong) solid var(--color-focus);
  outline-offset: 3px;
}

.cookie-reveal-enter-active,
.cookie-reveal-leave-active {
  transition: opacity var(--duration-normal) var(--easing-standard), transform var(--duration-normal) var(--easing-standard);
}
.cookie-reveal-enter-from,
.cookie-reveal-leave-to { opacity: 0; transform: translateY(var(--space-4)); }

@media (max-width: 720px) {
  .cookie-content { align-items: stretch; flex-direction: column; gap: var(--space-4); }
  .cookie-actions { width: 100%; }
  .cookie-button { flex: 1; }
}

@media (max-width: 440px) {
  .cookie-banner { bottom: var(--space-2); left: var(--space-2); right: var(--space-2); }
  .cookie-message > svg { display: none; }
  .cookie-actions { flex-direction: column-reverse; }
  .cookie-button { width: 100%; }
}

@media (prefers-reduced-motion: reduce) {
  .cookie-reveal-enter-active,
  .cookie-reveal-leave-active { transition: none; }
}
</style>
