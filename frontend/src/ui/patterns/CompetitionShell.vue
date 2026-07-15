<template>
  <header class="competition-shell" :data-effective-theme="effectiveTheme">
    <div class="shell-bar">
      <router-link :to="homeLocation" class="shell-brand" @click="emit('close-menus')">
        <span class="shell-mark" aria-hidden="true">SO</span>
        <span class="shell-brand-copy">
          <strong>{{ t('navigation.brand.name') }}</strong>
          <small>{{ t('navigation.brand.strapline') }}</small>
        </span>
      </router-link>

      <div class="competition-context" data-testid="competition-context">
        <span>{{ t('navigation.competition.label') }}</span>
        <strong>{{ t(edition.displayNameKey) }}</strong>
      </div>

      <div class="shell-controls">
        <label v-if="workspaceRoute" class="shell-select">
          <Globe2 :size="15" aria-hidden="true" />
          <span class="sr-only">{{ t('navigation.controls.language') }}</span>
          <select
            data-testid="locale-control"
            :aria-label="t('navigation.controls.language')"
            :value="locale"
            @change="emit('locale-change', $event.target.value)"
          >
            <option value="en">EN</option>
            <option value="es">ES</option>
          </select>
        </label>

        <label class="shell-select">
          <Sun v-if="themePreference === 'light'" :size="15" aria-hidden="true" />
          <Moon v-else-if="themePreference === 'dark'" :size="15" aria-hidden="true" />
          <Monitor v-else :size="15" aria-hidden="true" />
          <span class="sr-only">{{ t('navigation.controls.theme') }}</span>
          <select
            data-testid="theme-control"
            :aria-label="t('navigation.controls.theme')"
            :value="themePreference"
            @change="emit('theme-change', $event.target.value)"
          >
            <option value="light">{{ t('navigation.controls.themeLight') }}</option>
            <option value="dark">{{ t('navigation.controls.themeDark') }}</option>
            <option value="system">{{ t('navigation.controls.themeSystem') }}</option>
          </select>
        </label>

        <div v-if="signedIn" class="account-control">
          <button
            data-testid="account-menu-toggle"
            class="account-toggle"
            type="button"
            aria-haspopup="menu"
            :aria-expanded="userMenuOpen"
            :aria-label="userMenuOpen ? t('navigation.controls.closeAccount') : t('navigation.controls.openAccount')"
            @click="emit('toggle-account')"
          >
            <img v-if="userAvatarUrl" :src="userAvatarUrl" alt="" />
            <span v-else>{{ userInitials }}</span>
            <ChevronDown :size="14" aria-hidden="true" />
          </button>
          <div v-if="userMenuOpen" data-testid="account-menu" class="account-menu" role="menu">
            <div class="account-summary">
              <strong>{{ userDisplayName }}</strong>
              <small>{{ userEmail }}</small>
            </div>
            <router-link to="/profile" role="menuitem" @click="emit('close-menus')">
              <UserRound :size="15" aria-hidden="true" />
              <span>{{ t('navigation.account.profile') }}</span>
            </router-link>
            <button type="button" role="menuitem" @click="emit('sign-out')">
              <LogOut :size="15" aria-hidden="true" />
              <span>{{ t('navigation.account.signOut') }}</span>
            </button>
          </div>
        </div>

        <button
          data-testid="mobile-menu-toggle"
          class="mobile-menu-toggle"
          type="button"
          :aria-expanded="mobileMenuOpen"
          aria-controls="competition-navigation"
          :aria-label="mobileMenuOpen ? t('navigation.controls.closeMenu') : t('navigation.controls.openMenu')"
          @click="emit('toggle-mobile')"
        >
          <X v-if="mobileMenuOpen" :size="20" aria-hidden="true" />
          <Menu v-else :size="20" aria-hidden="true" />
        </button>
      </div>
    </div>

    <div class="shell-subbar">
      <span class="shell-rule" aria-hidden="true"></span>
      <nav
        id="competition-navigation"
        data-testid="workspace-navigation"
        class="workspace-navigation"
        :class="{ 'is-open': mobileMenuOpen }"
        :aria-label="t('navigation.competition.label')"
      >
        <template v-if="signedIn">
          <router-link
            v-for="item in navigation"
            :key="item.key"
            :to="item.route"
            class="workspace-link"
            @click="emit('close-menus')"
          >
            <component :is="iconFor(item.key)" :size="15" aria-hidden="true" />
            <span>{{ t(item.labelKey) }}</span>
          </router-link>
          <router-link to="/pricing" class="workspace-link workspace-link-secondary" @click="emit('close-menus')">
            <CreditCard :size="15" aria-hidden="true" />
            <span>{{ t('navigation.public.pricing') }}</span>
          </router-link>
          <router-link v-if="isAdmin" to="/admin/settings" class="workspace-link workspace-link-secondary" @click="emit('close-menus')">
            <ShieldCheck :size="15" aria-hidden="true" />
            <span>{{ t('navigation.account.admin') }}</span>
          </router-link>
        </template>
        <template v-else>
          <router-link :to="homeLocation" class="workspace-link" @click="emit('close-menus')">
            <Compass :size="15" aria-hidden="true" />
            <span>{{ t('navigation.workspace.overview') }}</span>
          </router-link>
          <router-link to="/pricing" class="workspace-link" @click="emit('close-menus')">
            <CreditCard :size="15" aria-hidden="true" />
            <span>{{ t('navigation.public.pricing') }}</span>
          </router-link>
          <router-link to="/sign-in" class="workspace-link" @click="emit('close-menus')">
            <LogIn :size="15" aria-hidden="true" />
            <span>{{ t('navigation.public.signIn') }}</span>
          </router-link>
          <router-link to="/sign-up" class="workspace-link workspace-link-primary" @click="emit('close-menus')">
            <UserPlus :size="15" aria-hidden="true" />
            <span>{{ t('navigation.public.signUp') }}</span>
          </router-link>
        </template>
      </nav>
    </div>
  </header>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import {
  Activity,
  BarChart3,
  ChevronDown,
  Compass,
  CreditCard,
  Globe2,
  LayoutGrid,
  LogIn,
  LogOut,
  Menu,
  Monitor,
  Moon,
  ShieldCheck,
  Sun,
  UserPlus,
  UserRound,
  X,
} from '@lucide/vue'

defineProps({
  edition: { type: Object, required: true },
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
  'locale-change',
  'sign-out',
  'theme-change',
  'toggle-account',
  'toggle-mobile',
])

const { t } = useI18n()
const iconByKey = {
  overview: Compass,
  groups: LayoutGrid,
  predict: Activity,
  bracket: BarChart3,
  markets: BarChart3,
}

function iconFor(key) {
  return iconByKey[key] || Compass
}

</script>

<style scoped>
.competition-shell {
  background: var(--color-surface-raised);
  border-bottom: var(--border-width-thin) solid var(--color-border);
  color: var(--color-text);
  position: relative;
  z-index: var(--z-sticky);
}

.shell-bar,
.shell-subbar {
  margin: 0 auto;
  max-width: var(--content-max-width);
  width: 100%;
}

.shell-bar {
  align-items: center;
  display: flex;
  gap: var(--space-6);
  min-height: 4.5rem;
  padding: var(--space-3) var(--space-6);
}

.shell-brand {
  align-items: center;
  color: var(--color-text);
  display: inline-flex;
  flex-shrink: 0;
  gap: var(--space-3);
  min-height: var(--control-height-lg);
  text-decoration: none;
}

.shell-brand:focus-visible,
.workspace-link:focus-visible,
.account-toggle:focus-visible,
.mobile-menu-toggle:focus-visible,
.shell-select:focus-within,
.account-menu a:focus-visible,
.account-menu button:focus-visible {
  outline: var(--border-width-strong) solid var(--color-focus);
  outline-offset: 3px;
}

.shell-mark {
  align-items: center;
  background: var(--color-accent);
  color: var(--color-accent-contrast);
  display: inline-flex;
  font-family: var(--font-family-data);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  height: 2rem;
  justify-content: center;
  letter-spacing: 0;
  width: 2rem;
}

.shell-brand-copy {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.shell-brand-copy strong {
  font-family: var(--font-family-display);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-heavy);
  letter-spacing: 0;
  line-height: var(--line-height-tight);
}

.shell-brand-copy small,
.competition-context span {
  color: var(--color-text-muted);
  font-family: var(--font-family-data);
  font-size: var(--font-size-xs);
  letter-spacing: 0;
  text-transform: uppercase;
}

.competition-context {
  border-left: var(--border-width-thin) solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
  padding-left: var(--space-5);
}

.competition-context strong {
  font-family: var(--font-family-display);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shell-controls {
  align-items: center;
  display: flex;
  gap: var(--space-2);
  margin-left: auto;
}

.shell-select {
  align-items: center;
  color: var(--color-text-muted);
  display: inline-flex;
  gap: var(--space-1);
  min-height: var(--control-height-md);
}

.shell-select select {
  appearance: none;
  background: var(--color-surface-raised);
  border: var(--border-width-thin) solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text);
  cursor: pointer;
  font: var(--font-weight-semibold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data);
  min-height: var(--control-height-md);
  min-width: 3.5rem;
  padding: 0 var(--space-2);
}

.shell-select select:hover { border-color: var(--color-border-strong); }

.account-control { position: relative; }

.account-toggle,
.mobile-menu-toggle {
  align-items: center;
  background: transparent;
  border: var(--border-width-thin) solid var(--color-border);
  color: var(--color-text);
  cursor: pointer;
  display: inline-flex;
  justify-content: center;
  min-height: var(--control-height-md);
}

.account-toggle {
  gap: var(--space-2);
  padding: 0 var(--space-2);
}

.account-toggle img,
.account-toggle > span {
  align-items: center;
  background: var(--color-accent);
  color: var(--color-accent-contrast);
  display: inline-flex;
  font-family: var(--font-family-data);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  height: 1.5rem;
  justify-content: center;
  object-fit: cover;
  width: 1.5rem;
}

.account-menu {
  background: var(--color-surface-raised);
  border: var(--border-width-thin) solid var(--color-border);
  box-shadow: var(--shadow-md);
  display: flex;
  flex-direction: column;
  min-width: 14rem;
  padding: var(--space-2);
  position: absolute;
  right: 0;
  top: calc(100% + var(--space-2));
  z-index: var(--z-dropdown);
}

.account-summary {
  border-bottom: var(--border-width-thin) solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin-bottom: var(--space-1);
  padding: var(--space-2) var(--space-2) var(--space-3);
}

.account-summary strong { font-size: var(--font-size-sm); }
.account-summary small { color: var(--color-text-muted); overflow-wrap: anywhere; }

.account-menu a,
.account-menu button {
  align-items: center;
  background: transparent;
  border: 0;
  color: var(--color-text);
  cursor: pointer;
  display: flex;
  font: var(--font-weight-medium) var(--font-size-sm) / var(--line-height-normal) var(--font-family-body);
  gap: var(--space-2);
  min-height: var(--control-height-md);
  padding: 0 var(--space-2);
  text-align: left;
  text-decoration: none;
  width: 100%;
}

.account-menu a:hover,
.account-menu button:hover { background: var(--color-surface-inset); }

.mobile-menu-toggle { display: none; padding: 0 var(--space-2); }

.shell-subbar { padding: 0 var(--space-6); }
.shell-rule { border-top: var(--border-width-thin) solid var(--color-border); display: block; }

.workspace-navigation {
  align-items: center;
  display: flex;
  gap: var(--space-1);
  min-height: 3.25rem;
  overflow-x: auto;
}

.workspace-link {
  align-items: center;
  border-bottom: var(--border-width-strong) solid transparent;
  color: var(--color-text-muted);
  display: inline-flex;
  flex: 0 0 auto;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  gap: var(--space-2);
  min-height: 3.25rem;
  padding: 0 var(--space-3);
  text-decoration: none;
  transition: background-color var(--duration-fast) var(--easing-standard), color var(--duration-fast) var(--easing-standard), border-color var(--duration-fast) var(--easing-standard);
}

.workspace-link:hover,
.workspace-link.router-link-active {
  background: var(--color-surface-inset);
  border-bottom-color: var(--color-accent);
  color: var(--color-text);
}

.workspace-link-secondary { color: var(--color-text-subtle); }
.workspace-link-primary { color: var(--color-accent); }

.sr-only {
  border: 0;
  clip: rect(0 0 0 0);
  height: 1px;
  margin: -1px;
  overflow: hidden;
  padding: 0;
  position: absolute;
  white-space: nowrap;
  width: 1px;
}

@media (max-width: 820px) {
  .shell-bar { gap: var(--space-3); padding: var(--space-3) var(--space-4); }
  .competition-context { border-left: 0; display: flex; flex: 1; min-width: 6rem; padding-left: 0; }
  .competition-context span { display: none; }
  .shell-subbar { padding: 0 var(--space-4); }
  .mobile-menu-toggle { display: inline-flex; }
  .workspace-navigation {
    align-items: stretch;
    background: var(--color-surface-raised);
    display: none;
    flex-direction: column;
    gap: 0;
    padding: var(--space-2) 0 var(--space-3);
  }
  .workspace-navigation.is-open { display: flex; }
  .workspace-link { min-height: var(--control-height-lg); padding: 0 var(--space-2); }
  .workspace-link:hover,
  .workspace-link.router-link-active { border-left: var(--border-width-strong) solid var(--color-accent); border-bottom-color: transparent; }
}

@media (max-width: 640px) {
  .shell-brand-copy { display: none; }
  .shell-bar { gap: var(--space-2); }
  .competition-context strong { font-size: var(--font-size-xs); }
}

@media (prefers-reduced-motion: reduce) {
  .workspace-link { transition: none; }
}
</style>
