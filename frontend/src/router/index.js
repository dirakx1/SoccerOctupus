import { createRouter, createWebHistory } from 'vue-router'
import { getCompetitionEdition } from '../competition/index.js'
import { applyLocale } from '../i18n/index.js'
import { useAuthState } from '../lib/auth'
import { setPostAuthRedirect } from '../lib/postAuthRedirect.js'
import { WORKSPACE_ROUTE_NAMES, workspaceLocation } from './workspace.js'

function workspaceRedirect(area) {
  return (to) => workspaceLocation(area, { query: to.query, hash: to.hash })
}

function localizedWorkspaceFallback(to) {
  return workspaceLocation('overview', {
    locale: to.params.locale,
    query: to.query,
    hash: to.hash,
  })
}

function getBrowserStorage() {
  try {
    return window.localStorage
  } catch {
    return undefined
  }
}

function applyWorkspaceLocale(locale) {
  return applyLocale(locale, {
    storage: getBrowserStorage(),
    documentElement: typeof document === 'undefined' ? undefined : document.documentElement,
  })
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: workspaceRedirect('overview'), meta: { public: true } },
    {
      path: '/:locale(en|es)/competitions',
      redirect: localizedWorkspaceFallback,
      meta: { public: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionEditionSlug(world-cup-2026)',
      name: WORKSPACE_ROUTE_NAMES.overview,
      component: () => import('../views/Home.vue'),
      meta: { public: true, competitionWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionSlug',
      name: WORKSPACE_ROUTE_NAMES.leagueOverview,
      component: () => import('../views/LeagueOverviewView.vue'),
      props: true,
      meta: { public: true, competitionWorkspace: true, leagueWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionSlug/editions/:editionSlug',
      name: WORKSPACE_ROUTE_NAMES.leagueEditionOverview,
      component: () => import('../views/LeagueOverviewView.vue'),
      props: true,
      meta: { public: true, competitionWorkspace: true, leagueWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionSlug/editions/:editionSlug/table',
      name: WORKSPACE_ROUTE_NAMES.leagueTable,
      component: () => import('../views/LeagueCapabilityView.vue'),
      props: { capability: 'table' },
      meta: { requiresAuth: true, competitionWorkspace: true, leagueWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionSlug/editions/:editionSlug/fixtures',
      name: WORKSPACE_ROUTE_NAMES.leagueFixtures,
      component: () => import('../views/LeagueCapabilityView.vue'),
      props: { capability: 'fixtures' },
      meta: { requiresAuth: true, competitionWorkspace: true, leagueWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionSlug/editions/:editionSlug/predict',
      name: WORKSPACE_ROUTE_NAMES.leaguePredict,
      component: () => import('../views/LeagueCapabilityView.vue'),
      props: { capability: 'predict' },
      meta: { requiresAuth: true, competitionWorkspace: true, leagueWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionSlug/editions/:editionSlug/markets',
      name: WORKSPACE_ROUTE_NAMES.leagueMarkets,
      component: () => import('../views/LeagueCapabilityView.vue'),
      props: { capability: 'markets' },
      meta: { requiresAuth: true, competitionWorkspace: true, leagueWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionEditionSlug/groups',
      name: WORKSPACE_ROUTE_NAMES.groups,
      component: () => import('../views/GroupsView.vue'),
      meta: { requiresAuth: true, competitionWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionEditionSlug/predict',
      name: WORKSPACE_ROUTE_NAMES.predict,
      component: () => import('../views/PredictView.vue'),
      meta: { requiresAuth: true, competitionWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionEditionSlug/bracket',
      name: WORKSPACE_ROUTE_NAMES.bracket,
      component: () => import('../views/TournamentView.vue'),
      meta: { requiresAuth: true, competitionWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionEditionSlug/markets',
      name: WORKSPACE_ROUTE_NAMES.markets,
      component: () => import('../views/MarketsView.vue'),
      meta: { requiresAuth: true, competitionWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:pathMatch(.*)*',
      redirect: localizedWorkspaceFallback,
      meta: { public: true },
    },
    { path: '/design-lab', component: () => import('../views/DesignLabView.vue'), meta: { public: true } },
    { path: '/design-lab/atlas', component: () => import('../views/AtlasPortalPreviewView.vue'), meta: { public: true } },
    { path: '/design-lab/orbit', component: () => import('../views/OrbitPortalPreviewView.vue'), meta: { public: true } },
    { path: '/groups', redirect: workspaceRedirect('groups') },
    { path: '/predict', redirect: workspaceRedirect('predict') },
    { path: '/tournament', redirect: workspaceRedirect('bracket') },
    { path: '/markets', redirect: workspaceRedirect('markets') },
    { path: '/profile', component: () => import('../views/ProfileView.vue'), meta: { requiresAuth: true } },
    { path: '/pricing', component: () => import('../views/PricingView.vue'), meta: { public: true } },
    { path: '/billing', redirect: '/profile', meta: { requiresAuth: true } },
    { path: '/billing/success', component: () => import('../views/BillingSuccessView.vue'), meta: { requiresAuth: true } },
    { path: '/admin/settings', component: () => import('../views/AdminSettingsView.vue'), meta: { requiresAuth: true, admin: true } },
    { path: '/sign-in', component: () => import('../views/SignInView.vue'), meta: { public: true } },
    { path: '/sign-up', component: () => import('../views/SignUpView.vue'), meta: { public: true } },
    { path: '/forgot-password', component: () => import('../views/ForgotPasswordView.vue'), meta: { public: true } },
    { path: '/sso-callback', component: () => import('../views/SSOCallbackView.vue'), meta: { public: true } },
    { path: '/complete-username', component: () => import('../views/CompleteUsernameView.vue'), meta: { public: true } },
    { path: '/legal', component: () => import('../views/LegalNoticeView.vue'), meta: { public: true } },
    { path: '/cookie-policy', component: () => import('../views/CookiePolicyView.vue'), meta: { public: true } },
    { path: '/contact', component: () => import('../views/ContactView.vue'), meta: { public: true } },
    { path: '/about', component: () => import('../views/AboutView.vue'), meta: { public: true } },
  ]
})

const auth = useAuthState()

router.beforeEach((to) => {
  if (to.meta.competitionWorkspace) {
    if (!to.meta.leagueWorkspace && !getCompetitionEdition(to.params.competitionEditionSlug)) {
      return localizedWorkspaceFallback(to)
    }

    applyWorkspaceLocale(to.params.locale)
  }

  if (!auth.state.loaded) return true

  if (to.meta.requiresAuth && !auth.state.signedIn) {
    if (to.meta.competitionWorkspace) {
      try {
        setPostAuthRedirect(to.fullPath)
      } catch {
        // Authentication remains reachable when browser storage is blocked.
      }
    }

    return { path: '/sign-in' }
  }

  if (to.meta.admin && !auth.state.isAdmin) {
    return { path: '/' }
  }

  if (auth.state.signedIn && (to.path === '/sign-in' || to.path === '/sign-up')) {
    return { path: '/' }
  }

  return true
})

export default router
