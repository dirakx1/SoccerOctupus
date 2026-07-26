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
import { computed, onMounted, ref, watch } from 'vue'
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
  applyLocale,
  i18n,
  normalizeLocale,
} from './i18n/index.js'
import { api, installAuthInterceptor } from './lib/api'
import { clearAuthState, refreshAuthState, setAuthPendingState, useAuthState } from './lib/auth'
import {
  consumePostAuthRedirect,
  peekPostAuthRedirect,
  setPostAuthRedirect,
} from './lib/postAuthRedirect'
import {
  clearPostAuthCompletion,
  hasPostAuthCompletion,
} from './lib/postAuthCompletion'
import { useThemePreference } from './ui/themePreference.js'
import { leagueWorkspaceLocation, workspaceLocaleLocation, workspaceLocation } from './router/workspace.js'

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
const defaultEdition = listCompetitionEditions()[0]
const competitionEditions = ref(listCompetitionEditions())
const routeEdition = ref(null)
const userMenuOpen = ref(false)
const mobileMenuOpen = ref(false)
const authRecoveryError = ref('')
const authRefreshing = ref(false)
const authCompletionPending = ref(hasPostAuthCompletion())
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
  route.meta.leagueWorkspace
    ? routeEdition.value
      || competitionEditions.value.find((entry) => entry.competitionSlug === route.params.competitionSlug)
      || defaultEdition
    : getCompetitionEdition(route.params.competitionEditionSlug) || defaultEdition
))
const currentLocale = computed(() => (
  normalizeLocale(route.params.locale) || normalizeLocale(i18n.global.locale.value) || 'en'
))
const isWorkspaceRoute = computed(() => Boolean(
  route.meta.competitionWorkspace && route.params.locale
))
const homeLocation = computed(() => activeEdition.value.competitionSlug
  ? leagueWorkspaceLocation('overview', {
      locale: currentLocale.value,
      competitionSlug: activeEdition.value.competitionSlug,
    })
  : workspaceLocation('overview', {
      locale: currentLocale.value,
      competitionEditionSlug: activeEdition.value.slug,
    }))
const competitionNavigation = computed(() => {
  if (!activeEdition.value.competitionSlug) {
    return getCompetitionNavigation(activeEdition.value, { locale: currentLocale.value })
  }

  return activeEdition.value.capabilities.map((capability) => ({
    key: capability,
    labelKey: `league.capabilities.${capability}`,
    route: leagueWorkspaceLocation(capability === 'predictions' ? 'predict' : capability, {
      locale: currentLocale.value,
      competitionSlug: activeEdition.value.competitionSlug,
      editionSlug: activeEdition.value.editionSlug,
    }),
  }))
})

installAuthInterceptor(async () => {
  return await getToken.value?.()
})

const canRenderRoute = computed(() => {
  const current = router.currentRoute.value
  if (!current.meta.requiresAuth) return true
  return auth.state.loaded && auth.state.signedIn && (!current.meta.admin || auth.state.isAdmin)
})
const showAuthRecovery = computed(() => (
  authCompletionPending.value && clerkLoaded.value && clerkSignedIn.value && !auth.state.loaded
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
  if (nextLocation) {
    await router.push(nextLocation)
    return
  }

  applyLocale(value, {
    storage: browserStorage,
    documentElement: document.documentElement,
  })
}

async function changeEdition(edition) {
  if (!edition?.slug) return

  const location = edition.competitionSlug
    ? leagueWorkspaceLocation('overview', {
        locale: currentLocale.value,
        competitionSlug: edition.competitionSlug,
      })
    : workspaceLocation('overview', {
        locale: currentLocale.value,
        competitionEditionSlug: edition.slug,
      })
  await router.push(location)
}

async function loadCompetitionCatalog() {
  try {
    const { data } = await api.get('/api/competitions')
    const leagues = data.competitions.map((competition) => ({
      id: `${competition.slug}-${competition.current_edition.slug}`,
      competitionSlug: competition.slug,
      editionSlug: competition.current_edition.slug,
      slug: competition.slug,
      displayName: competition.current_edition.display_name,
      format: competition.current_edition.format,
      capabilities: competition.current_edition.capabilities,
    }))
    competitionEditions.value = [...listCompetitionEditions(), ...leagues]
  } catch {
    // The shipped World Cup workspace remains available if the catalog is offline.
  }
}

async function loadRouteEdition() {
  if (!route.meta.leagueWorkspace || !route.params.editionSlug) {
    routeEdition.value = null
    return
  }

  try {
    const { data } = await api.get(
      `/api/competitions/${route.params.competitionSlug}/editions/${route.params.editionSlug}`
    )
    routeEdition.value = {
      id: `${data.competition.slug}-${data.edition.slug}`,
      competitionSlug: data.competition.slug,
      editionSlug: data.edition.slug,
      slug: data.competition.slug,
      displayName: data.edition.display_name,
      format: data.edition.format,
      capabilities: data.edition.capabilities,
    }
  } catch {
    routeEdition.value = null
  }
}

watch(
  () => [route.params.competitionSlug, route.params.editionSlug],
  loadRouteEdition,
  { immediate: true }
)
onMounted(loadCompetitionCatalog)

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
    clearPostAuthCompletion()
    authCompletionPending.value = false
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
    clearPostAuthCompletion()
    authCompletionPending.value = false
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
      authCompletionPending.value = hasPostAuthCompletion()
      if (authCompletionPending.value) {
        if (!authRecoveryError.value) await recoverAuthState()
      } else {
        try {
          await refreshAuthState({ force: true })
          redirectAfterAuthRefresh()
        } catch {
          // Existing-session hydration is intentionally silent. Route guards own protected-route fallback.
        }
      }
      return
    }

    if (authCompletionPending.value) {
      clearPostAuthCompletion()
      authCompletionPending.value = false
    }

    redirectAfterAuthRefresh()
  },
  { immediate: true }
)
</script>
