<template>
  <div class="atlas-app-shell">
    <CompetitionShell
      :edition="edition"
      :editions="editions"
      :navigation="navigation"
      :home-location="homeLocation"
      :locale="locale"
      :theme-preference="themePreference"
      :effective-theme="effectiveTheme"
      :workspace-route="workspaceRoute"
      :signed-in="signedIn"
      :is-admin="isAdmin"
      :user-display-name="userDisplayName"
      :user-email="userEmail"
      :user-initials="userInitials"
      :user-avatar-url="userAvatarUrl"
      :mobile-menu-open="mobileMenuOpen"
      :user-menu-open="userMenuOpen"
      @close-menus="emit('close-menus')"
      @edition-change="(value) => emit('edition-change', value)"
      @locale-change="(value) => emit('locale-change', value)"
      @sign-out="emit('sign-out')"
      @theme-change="(value) => emit('theme-change', value)"
      @toggle-account="emit('toggle-account')"
      @toggle-mobile="emit('toggle-mobile')"
    />

    <slot name="billing-notice" />

    <main class="content atlas-content">
      <slot name="auth-recovery" />
      <slot />
    </main>

    <footer class="atlas-footer">
      <p>{{ t('navigation.footer.disclaimer') }}</p>
      <nav :aria-label="t('navigation.footer.label')">
        <router-link to="/legal">{{ t('navigation.footer.legal') }}</router-link>
        <router-link to="/cookie-policy">{{ t('navigation.footer.cookies') }}</router-link>
        <router-link to="/contact">{{ t('navigation.footer.contact') }}</router-link>
        <router-link to="/about">{{ t('navigation.footer.about') }}</router-link>
      </nav>
    </footer>

    <slot name="cookie" />
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

import CompetitionShell from './CompetitionShell.vue'

defineProps({
  edition: { type: Object, required: true },
  editions: { type: Array, default: () => [] },
  navigation: { type: Array, default: () => [] },
  homeLocation: { type: [String, Object], required: true },
  locale: { type: String, default: 'en' },
  themePreference: { type: String, default: 'system' },
  effectiveTheme: { type: String, default: 'light' },
  workspaceRoute: { type: Boolean, default: false },
  signedIn: { type: Boolean, default: false },
  isAdmin: { type: Boolean, default: false },
  userDisplayName: { type: String, default: '' },
  userEmail: { type: String, default: '' },
  userInitials: { type: String, default: 'A' },
  userAvatarUrl: { type: String, default: '' },
  mobileMenuOpen: { type: Boolean, default: false },
  userMenuOpen: { type: Boolean, default: false },
})

const emit = defineEmits([
  'close-menus',
  'edition-change',
  'locale-change',
  'sign-out',
  'theme-change',
  'toggle-account',
  'toggle-mobile',
])

const { t } = useI18n()
</script>

<style scoped>
.atlas-app-shell {
  background: var(--color-background);
  color: var(--color-text);
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.atlas-content {
  flex: 1;
  margin: 0 auto;
  max-width: var(--content-max-width);
  padding: var(--space-8) var(--space-6) var(--space-12);
  width: 100%;
}

.atlas-footer {
  align-items: center;
  border-top: var(--border-width-thin) solid var(--color-border);
  color: var(--color-text-muted);
  display: flex;
  flex-wrap: wrap;
  font-size: var(--font-size-xs);
  gap: var(--space-4) var(--space-6);
  justify-content: space-between;
  margin: 0 auto;
  max-width: var(--content-max-width);
  padding: var(--space-5) var(--space-6);
  width: 100%;
}

.atlas-footer p { margin: 0; }

.atlas-footer nav {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
}

.atlas-footer a {
  color: var(--color-text-muted);
  text-decoration: none;
}

.atlas-footer a:hover { color: var(--color-accent); }

.atlas-footer a:focus-visible {
  outline: var(--border-width-strong) solid var(--color-focus);
  outline-offset: 3px;
}

:deep(.auth-recovery) {
  align-items: center;
  background: var(--color-surface);
  border: var(--border-width-thin) solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin: var(--space-12) auto;
  max-width: 32rem;
  padding: var(--space-8);
  text-align: center;
}

:deep(.shell-billing-notice) {
  border-left: 0;
  border-radius: 0;
  border-right: 0;
  justify-content: center;
}

:deep(.auth-recovery h1) {
  color: var(--color-text);
  font-family: var(--font-family-display);
  font-size: var(--font-size-2xl);
  margin: 0;
}

:deep(.auth-recovery p) {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
  margin: 0;
}

:deep(.auth-retry) {
  background: var(--color-accent);
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--color-accent-contrast);
  cursor: pointer;
  font-weight: var(--font-weight-semibold);
  min-height: var(--control-height-lg);
  padding: 0 var(--space-4);
}

:deep(.auth-retry:focus-visible) {
  outline: var(--border-width-strong) solid var(--color-focus);
  outline-offset: 3px;
}

:deep(.spin) { animation: atlas-spin 0.8s linear infinite; }

@keyframes atlas-spin { to { transform: rotate(360deg); } }

@media (max-width: 640px) {
  .atlas-content { padding: var(--space-6) var(--space-4) var(--space-10); }
  .atlas-footer { align-items: flex-start; flex-direction: column; padding: var(--space-4); }
}

@media (prefers-reduced-motion: reduce) {
  :deep(.spin) { animation: none; }
}
</style>
