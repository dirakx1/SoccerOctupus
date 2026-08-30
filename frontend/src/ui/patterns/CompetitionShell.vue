<template>
  <header ref="shellRef" class="competition-shell" :data-effective-theme="effectiveTheme">
    <div class="shell-bar">
      <div class="shell-identity">
        <router-link :to="homeLocation" class="shell-brand" @click="emit('close-menus')">
          <img data-testid="brand-mark" class="shell-mark" src="/favicon.svg" alt="" />
          <span class="shell-brand-copy">
            <strong>{{ t('navigation.brand.name') }}</strong>
          </span>
        </router-link>

        <div class="competition-context">
          <button
            data-testid="competition-toggle"
            class="competition-toggle"
            type="button"
            aria-haspopup="menu"
            :aria-expanded="competitionMenuOpen"
            :aria-label="t('navigation.controls.competitionMenu')"
            :title="t('navigation.controls.competitionMenu')"
            @click="toggleMenu('competition')"
          >
            <strong>{{ edition.displayName || t(edition.displayNameKey) }}</strong>
            <ChevronDown :size="15" aria-hidden="true" />
          </button>
          <div v-if="competitionMenuOpen" data-testid="competition-menu" class="header-menu competition-menu" role="menu">
            <button
              v-for="registeredEdition in editions"
              :key="registeredEdition.id"
              :data-testid="`competition-option-${registeredEdition.slug}`"
              type="button"
              role="menuitemradio"
              :aria-checked="registeredEdition.slug === edition.slug"
              @click="selectEdition(registeredEdition)"
            >
              <Trophy :size="15" aria-hidden="true" />
              <span>{{ t(registeredEdition.displayNameKey) }}</span>
              <Check v-if="registeredEdition.slug === edition.slug" :size="15" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>

      <nav
        id="competition-navigation"
        data-testid="workspace-navigation"
        class="workspace-navigation"
        :class="{ 'is-open': mobileMenuOpen }"
      >
        <template v-if="signedIn">
          <router-link
            v-for="item in navigation"
            :key="item.key"
            :to="item.route"
            class="workspace-link"
            @click="emit('close-menus')"
          >
            <span>{{ t(item.labelKey) }}</span>
          </router-link>
          <router-link to="/pricing" class="workspace-link workspace-link-secondary" @click="emit('close-menus')">
            <span>{{ t('navigation.public.pricing') }}</span>
          </router-link>
          <router-link v-if="isAdmin" to="/admin/settings" class="workspace-link workspace-link-secondary" @click="emit('close-menus')">
            <span>{{ t('navigation.account.admin') }}</span>
          </router-link>
        </template>
        <template v-else>
          <router-link :to="homeLocation" class="workspace-link" @click="emit('close-menus')">
            <span>{{ t('navigation.workspace.overview') }}</span>
          </router-link>
          <router-link to="/pricing" class="workspace-link" @click="emit('close-menus')">
            <span>{{ t('navigation.public.pricing') }}</span>
          </router-link>
          <router-link to="/sign-in" class="workspace-link" @click="emit('close-menus')">
            <span>{{ t('navigation.public.signIn') }}</span>
          </router-link>
          <router-link to="/sign-up" class="workspace-link workspace-link-primary" @click="emit('close-menus')">
            <span>{{ t('navigation.public.signUp') }}</span>
          </router-link>
        </template>
      </nav>

      <div class="shell-controls">
        <div class="header-menu-control">
          <button
            data-testid="locale-toggle"
            class="icon-menu-toggle"
            type="button"
            aria-haspopup="menu"
            :aria-expanded="localeMenuOpen"
            :aria-label="t('navigation.controls.languageMenu')"
            :title="t('navigation.controls.languageMenu')"
            @click="toggleMenu('locale')"
          >
            <Globe2 :size="17" aria-hidden="true" />
            <span>{{ locale.toUpperCase() }}</span>
          </button>
          <div v-if="localeMenuOpen" data-testid="locale-menu" class="header-menu control-menu" role="menu">
            <button
              data-testid="locale-option-en"
              type="button"
              role="menuitemradio"
              :aria-checked="locale === 'en'"
              @click="selectLocale('en')"
            >
              <Globe2 :size="15" aria-hidden="true" />
              <span>{{ t('navigation.controls.localeEnglish') }}</span>
              <Check v-if="locale === 'en'" :size="15" aria-hidden="true" />
            </button>
            <button
              data-testid="locale-option-es"
              type="button"
              role="menuitemradio"
              :aria-checked="locale === 'es'"
              @click="selectLocale('es')"
            >
              <Globe2 :size="15" aria-hidden="true" />
              <span>{{ t('navigation.controls.localeSpanish') }}</span>
              <Check v-if="locale === 'es'" :size="15" aria-hidden="true" />
            </button>
          </div>
        </div>

        <div class="header-menu-control">
          <button
            data-testid="theme-toggle"
            class="icon-menu-toggle"
            type="button"
            aria-haspopup="menu"
            :aria-expanded="themeMenuOpen"
            :aria-label="themeButtonLabel"
            :title="themeButtonLabel"
            @click="toggleMenu('theme')"
          >
            <component :is="themeIcon(effectiveTheme)" :size="17" aria-hidden="true" />
          </button>
          <div v-if="themeMenuOpen" data-testid="theme-menu" class="header-menu control-menu" role="menu">
            <button
              v-for="option in themeOptions"
              :key="option.value"
              :data-testid="`theme-option-${option.value}`"
              type="button"
              role="menuitemradio"
              :aria-checked="themePreference === option.value"
              @click="selectTheme(option.value)"
            >
              <component :is="option.icon" :size="15" aria-hidden="true" />
              <span>{{ t(option.labelKey) }}</span>
              <Check v-if="themePreference === option.value" :size="15" aria-hidden="true" />
            </button>
          </div>
        </div>

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
  </header>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Check,
  ChevronDown,
  Globe2,
  LogOut,
  Menu,
  Moon,
  Monitor,
  Sun,
  Trophy,
  UserRound,
  X,
} from '@lucide/vue'

const props = defineProps({
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
const shellRef = ref(null)
const localeMenuOpen = ref(false)
const themeMenuOpen = ref(false)
const competitionMenuOpen = ref(false)
const themeOptions = [
  { value: 'light', labelKey: 'navigation.controls.themeLight', icon: Sun },
  { value: 'dark', labelKey: 'navigation.controls.themeDark', icon: Moon },
  { value: 'system', labelKey: 'navigation.controls.themeSystem', icon: Monitor },
]

const themeButtonLabel = computed(() => (
  `${t('navigation.controls.themeMenu')}: ${t(`navigation.controls.theme${props.effectiveTheme.charAt(0).toUpperCase()}${props.effectiveTheme.slice(1)}`)}`
))

function themeIcon(value) {
  if (value === 'dark') return Moon
  if (value === 'system') return Monitor
  return Sun
}

function closeHeaderMenus() {
  localeMenuOpen.value = false
  themeMenuOpen.value = false
  competitionMenuOpen.value = false
}

function toggleMenu(menu) {
  const nextValue = menu === 'locale'
    ? !localeMenuOpen.value
    : menu === 'theme'
      ? !themeMenuOpen.value
      : !competitionMenuOpen.value

  closeHeaderMenus()
  if (menu === 'locale') localeMenuOpen.value = nextValue
  if (menu === 'theme') themeMenuOpen.value = nextValue
  if (menu === 'competition') competitionMenuOpen.value = nextValue
}

function selectLocale(value) {
  closeHeaderMenus()
  emit('locale-change', value)
}

function selectTheme(value) {
  closeHeaderMenus()
  emit('theme-change', value)
}

function selectEdition(value) {
  closeHeaderMenus()
  emit('edition-change', value)
}

function handleDocumentClick(event) {
  if (!shellRef.value?.contains(event.target)) {
    closeHeaderMenus()
    emit('close-menus')
  }
}

onMounted(() => document.addEventListener('click', handleDocumentClick))
onBeforeUnmount(() => document.removeEventListener('click', handleDocumentClick))
</script>

<style scoped>
.competition-shell {
  background: var(--color-surface-raised);
  border-bottom: var(--border-width-thin) solid var(--color-border);
  color: var(--color-text);
  position: relative;
  z-index: var(--z-sticky);
}

.shell-bar {
  align-items: center;
  display: grid;
  gap: var(--space-4);
  grid-template-columns: minmax(13rem, auto) minmax(0, 1fr) auto;
  margin: 0 auto;
  max-width: var(--content-max-width);
  min-height: 4.5rem;
  padding: var(--space-3) var(--space-6);
  width: 100%;
}

.shell-identity {
  align-items: center;
  display: flex;
  gap: var(--space-4);
  min-width: 0;
}

.shell-brand {
  align-items: center;
  color: var(--color-text);
  display: inline-flex;
  flex-shrink: 0;
  gap: var(--space-3);
  min-height: var(--control-height-lg);
  min-width: var(--control-height-lg);
  text-decoration: none;
}

.shell-brand:focus-visible,
.workspace-link:focus-visible,
.icon-menu-toggle:focus-visible,
.competition-toggle:focus-visible,
.account-toggle:focus-visible,
.mobile-menu-toggle:focus-visible,
.header-menu button:focus-visible,
.account-menu a:focus-visible,
.account-menu button:focus-visible {
  outline: var(--border-width-strong) solid var(--color-focus);
  outline-offset: 3px;
}

.shell-mark {
  display: block;
  height: 2rem;
  object-fit: contain;
  width: 2rem;
}

.shell-brand-copy strong {
  font-family: var(--font-family-display);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-heavy);
  letter-spacing: 0;
  line-height: var(--line-height-tight);
}

.competition-context,
.header-menu-control,
.account-control {
  position: relative;
}

.competition-context { min-width: 0; }

.competition-toggle {
  align-items: center;
  background: transparent;
  border: 0;
  color: var(--color-text);
  cursor: pointer;
  display: inline-flex;
  gap: var(--space-2);
  max-width: 15rem;
  min-height: var(--control-height-lg);
  padding: 0 var(--space-2);
  text-align: left;
}

.competition-toggle strong {
  font-family: var(--font-family-display);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shell-controls {
  align-items: center;
  display: flex;
  gap: var(--space-2);
  justify-content: flex-end;
}

.icon-menu-toggle,
.account-toggle,
.mobile-menu-toggle {
  align-items: center;
  background: transparent;
  border: var(--border-width-thin) solid var(--color-border);
  color: var(--color-text);
  cursor: pointer;
  display: inline-flex;
  justify-content: center;
  min-height: var(--control-height-lg);
}

.icon-menu-toggle {
  gap: var(--space-1);
  min-width: var(--control-height-lg);
  padding: 0 var(--space-2);
}

.icon-menu-toggle span {
  font: var(--font-weight-semibold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data);
}

.account-toggle { gap: var(--space-2); padding: 0 var(--space-2); }

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

.header-menu {
  background: var(--color-surface-raised);
  border: var(--border-width-thin) solid var(--color-border);
  box-shadow: var(--shadow-md);
  display: flex;
  flex-direction: column;
  min-width: 12rem;
  padding: var(--space-2);
  position: absolute;
  right: 0;
  top: calc(100% + var(--space-2));
  z-index: var(--z-dropdown);
}

.competition-menu { left: 0; right: auto; }

.header-menu button {
  align-items: center;
  background: transparent;
  border: 0;
  color: var(--color-text);
  cursor: pointer;
  display: flex;
  font: var(--font-weight-medium) var(--font-size-sm) / var(--line-height-normal) var(--font-family-body);
  gap: var(--space-2);
  min-height: var(--control-height-lg);
  padding: 0 var(--space-2);
  text-align: left;
  white-space: nowrap;
  width: 100%;
}

.header-menu button span { flex: 1; }
.header-menu button:hover { background: var(--color-surface-inset); }

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
  min-height: var(--control-height-lg);
  padding: 0 var(--space-2);
  text-align: left;
  text-decoration: none;
  width: 100%;
}

.account-menu a:hover,
.account-menu button:hover { background: var(--color-surface-inset); }

.mobile-menu-toggle { display: none; min-width: var(--control-height-lg); padding: 0 var(--space-2); }

.workspace-navigation {
  align-items: center;
  display: flex;
  gap: var(--space-1);
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: thin;
}

.workspace-link {
  align-items: center;
  border-bottom: var(--border-width-strong) solid transparent;
  color: var(--color-text-muted);
  display: inline-flex;
  flex: 0 0 auto;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  min-height: 3.25rem;
  padding: 0 var(--space-2);
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

@media (max-width: 1080px) {
  .shell-bar { gap: var(--space-2); padding-left: var(--space-4); padding-right: var(--space-4); }
  .shell-identity { gap: var(--space-2); }
  .competition-toggle { max-width: 12rem; }
  .workspace-link { padding-left: var(--space-1); padding-right: var(--space-1); }
}

@media (max-width: 820px) {
  .shell-bar { grid-template-columns: minmax(0, 1fr) auto; }
  .shell-identity { min-width: 0; }
  .competition-toggle { max-width: 12rem; }
  .workspace-navigation {
    align-items: stretch;
    background: var(--color-surface-raised);
    border-top: var(--border-width-thin) solid var(--color-border);
    display: none;
    flex-direction: column;
    gap: 0;
    grid-column: 1 / -1;
    padding: var(--space-2) 0 var(--space-3);
  }
  .workspace-navigation.is-open { display: flex; }
  .workspace-link { min-height: var(--control-height-lg); padding: 0 var(--space-2); }
  .workspace-link:hover,
  .workspace-link.router-link-active { border-left: var(--border-width-strong) solid var(--color-accent); border-bottom-color: transparent; }
  .mobile-menu-toggle { display: inline-flex; }
}

@media (max-width: 560px) {
  .shell-bar { gap: var(--space-2); padding: var(--space-3) var(--space-4); }
  .shell-brand-copy { display: none; }
  .competition-toggle { max-width: 10rem; padding-left: 0; }
  .icon-menu-toggle span { display: none; }
  .shell-controls { gap: var(--space-1); }
}

@media (prefers-reduced-motion: reduce) {
  .workspace-link { transition: none; }
}
</style>
