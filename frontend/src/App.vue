<template>
  <AppShell
    :edition="activeEdition"
    :editions="competitionEditions"
    :navigation="competitionNavigation"
    :home-location="homeLocation"
    :locale="currentLocale"
    :theme-preference="themePreference"
    :effective-theme="effectiveTheme"
    :workspace-route="isWorkspaceRoute"
    :signed-in="auth.state.signedIn"
    :is-admin="auth.state.isAdmin"
    :user-display-name="userDisplayName"
    :user-email="userEmail"
    :user-initials="userInitials"
    :user-avatar-url="userAvatarUrl"
    :mobile-menu-open="mobileMenuOpen"
    :user-menu-open="userMenuOpen"
    @close-menus="closeMenus"
    @edition-change="changeEdition"
    @locale-change="changeLocale"
    @sign-out="signOut"
    @theme-change="changeTheme"
    @toggle-account="toggleUserMenu"
    @toggle-mobile="toggleMobileMenu"
  >
    <template #billing-notice>
      <BillingStatusNotice
        v-if="auth.state.signedIn && requiresAttention"
        class="shell-billing-notice"
        :health="billingHealth"
        :loading="billingActionLoading"
        @action="openShellBillingRecovery"
      />
    </template>

    <template #auth-recovery>
      <section v-if="showAuthRecovery" class="auth-recovery" aria-live="polite">
        <LoaderCircle v-if="authRefreshing" :size="28" class="spin" aria-hidden="true" />
        <h1>{{ t('navigation.authRecovery.title') }}</h1>
        <p v-if="authRecoveryError">{{ authRecoveryError }}</p>
        <p v-else>{{ t('navigation.authRecovery.loading') }}</p>
        <button v-if="authRecoveryError" class="auth-retry" type="button" @click="recoverAuthState">
          {{ t('navigation.authRecovery.retry') }}
        </button>
      </section>
    </template>

    <router-view v-if="canRenderRoute" />
    <template #cookie><CookieBanner /></template>
  </AppShell>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useAuth, useClerk } from '@clerk/vue'
import { LoaderCircle } from '@lucide/vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'

import AppShell from './ui/patterns/AppShell.vue'
import BillingStatusNotice from './components/BillingStatusNotice.vue'
import CookieBanner from './components/CookieBanner.vue'
import { getCompetitionEdition, listCompetitionEditions } from './competition/index.js'
import { getCompetitionNavigation } from './competition/navigation.js'
import { useBillingStatus } from './composables/useBillingStatus'
import { useCurrentUserProfile } from './composables/useCurrentUserProfile'
import {
  i18n,
  normalizeLocale,
} from './i18n/index.js'
import { installAuthInterceptor } from './lib/api'
import { clearAuthState, refreshAuthState, setAuthPendingState, useAuthState } from './lib/auth'
import {
  consumePostAuthRedirect,
  peekPostAuthRedirect,
  setPostAuthRedirect,
} from './lib/postAuthRedirect'
import { useThemePreference } from './ui/themePreference.js'
import { workspaceLocaleLocation, workspaceLocation } from './router/workspace.js'

function getBrowserStorage() {
  try {
    return window.localStorage
  } catch {
    return undefined
  }
}

function getPrefersDark() {
  try {
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  } catch {
    return false
  }
}

const auth = useAuthState()
const clerk = useClerk()
const {
  getToken,
  isLoaded: clerkLoaded,
  isSignedIn: clerkSignedIn,
} = useAuth()
const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const browserStorage = getBrowserStorage()
const competitionEditions = listCompetitionEditions()
const defaultEdition = competitionEditions[0]
const userMenuOpen = ref(false)
const mobileMenuOpen = ref(false)
const authRecoveryError = ref('')
const authRefreshing = ref(false)
const {
  effectiveTheme,
  preference: themePreference,
  setPreference: changeTheme,
} = useThemePreference({
  storage: browserStorage,
  documentElement: document.documentElement,
  prefersDark: getPrefersDark(),
})
let signingOut = false

const {
  avatarUrl: userAvatarUrl,
  displayName: userDisplayName,
  email: userEmail,
  initials: userInitials,
} = useCurrentUserProfile()
const {
  actionLoading: billingActionLoading,
  billingHealth,
  clearBillingStatus,
  openBillingRecovery,
  refreshBillingStatus,
  requiresAttention,
} = useBillingStatus()

const activeEdition = computed(() => (
  getCompetitionEdition(route.params.competitionEditionSlug) || defaultEdition
))
const currentLocale = computed(() => (
  normalizeLocale(route.params.locale) || normalizeLocale(i18n.global.locale.value) || 'en'
))
const isWorkspaceRoute = computed(() => Boolean(
  route.meta.competitionWorkspace && route.params.locale
))
const homeLocation = computed(() => workspaceLocation('overview', {
  locale: currentLocale.value,
  competitionEditionSlug: activeEdition.value.slug,
}))
const competitionNavigation = computed(() => getCompetitionNavigation(activeEdition.value, {
  locale: currentLocale.value,
}))

installAuthInterceptor(async () => {
  return await getToken.value?.()
})

const canRenderRoute = computed(() => {
  const current = router.currentRoute.value
  if (!current.meta.requiresAuth) return true
  return auth.state.loaded && auth.state.signedIn && (!current.meta.admin || auth.state.isAdmin)
})
const showAuthRecovery = computed(() => (
  clerkLoaded.value && clerkSignedIn.value && !auth.state.loaded
))

function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

function toggleUserMenu() {
  userMenuOpen.value = !userMenuOpen.value
}

function closeMenus() {
  mobileMenuOpen.value = false
  userMenuOpen.value = false
}

async function changeLocale(value) {
  const nextLocation = workspaceLocaleLocation(route, value)
  if (nextLocation) await router.push(nextLocation)
}

async function changeEdition(edition) {
  if (!isWorkspaceRoute.value || !route.name || !edition?.slug) return

  await router.push({
    name: route.name,
    params: { ...route.params, competitionEditionSlug: edition.slug },
    query: route.query,
    hash: route.hash,
  })
}

watch(() => route.fullPath, closeMenus)

function redirectAfterAuthRefresh() {
  const current = router.currentRoute.value
  const storedRedirect = peekPostAuthRedirect()
  const isWorkspaceLanding = current.meta.competitionWorkspace && !current.meta.requiresAuth

  if (storedRedirect && (
    isWorkspaceLanding
    || ['/', '/sign-in', '/sign-up', '/sso-callback'].includes(current.path)
  )) {
    router.replace(consumePostAuthRedirect())
    return
  }

  if (current.path === '/sign-in' || current.path === '/sign-up') {
    router.replace('/')
    return
  }

  if (current.meta.admin && !auth.state.isAdmin) {
    router.replace('/')
  }
}

function redirectAfterSignOut() {
  const current = router.currentRoute.value
  if (!current.meta.requiresAuth) return

  if (!signingOut && current.meta.competitionWorkspace) {
    try {
      setPostAuthRedirect(current.fullPath)
    } catch {
      // Authentication remains reachable when browser storage is blocked.
    }
  }

  router.replace('/sign-in')
}

async function recoverAuthState() {
  if (authRefreshing.value || !clerkSignedIn.value) return

  authRefreshing.value = true
  authRecoveryError.value = ''
  try {
    await refreshAuthState({ force: true })
    redirectAfterAuthRefresh()
  } catch {
    authRecoveryError.value = t('navigation.authRecovery.error')
    setAuthPendingState()
  } finally {
    authRefreshing.value = false
  }
}

async function signOut() {
  signingOut = true
  closeMenus()
  try {
    await clerk.value?.signOut()
    clearBillingStatus()
    clearAuthState()
    await router.push('/sign-in')
  } finally {
    signingOut = false
  }
}

async function openShellBillingRecovery() {
  await openBillingRecovery(router.currentRoute.value.fullPath || '/profile')
}

watch(
  () => auth.state.signedIn,
  (signedIn) => {
    if (signedIn) {
      refreshBillingStatus()
    } else {
      clearBillingStatus()
    }
  },
  { immediate: true }
)

watch(
  [clerkLoaded, clerkSignedIn, () => auth.state.loaded],
  async ([loaded, signedIn, authLoaded]) => {
    if (!loaded) return

    if (!signedIn) {
      authRecoveryError.value = ''
      clearAuthState()
      redirectAfterSignOut()
      return
    }

    if (!authLoaded) {
      if (!authRecoveryError.value) await recoverAuthState()
      return
    }

    redirectAfterAuthRefresh()
  },
  { immediate: true }
)
</script>
