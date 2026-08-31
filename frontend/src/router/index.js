import { createRouter, createWebHistory } from 'vue-router'
import { getCompetitionEdition } from '../competition/index.js'
import { applyLocale } from '../i18n/index.js'
import { useAuthState } from '../lib/auth'
import { setPostAuthRedirect } from '../lib/postAuthRedirect.js'
import { HISTORIC_WORKSPACE_ROUTE_NAMES, LEAGUE_ROUTE_NAMES, workspaceLocation } from './workspace.js'

function workspaceRedirect(area) {
  return (to) => {
    try {
      return workspaceLocation(area, { query: to.query, hash: to.hash })
    } catch {
      return workspaceLocation('overview', { query: to.query, hash: to.hash })
    }
  }
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
      path: '/:locale(en|es)/competitions/:competitionEditionSlug(premier-league|la-liga|bundesliga|premier-league-[0-9]{4}-[0-9]{2}|la-liga-[0-9]{4}-[0-9]{2}|bundesliga-[0-9]{4}-[0-9]{2})',
      name: LEAGUE_ROUTE_NAMES.overview,
      component: () => import('../views/LeagueOverviewView.vue'),
      meta: { public: true, competitionWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionEditionSlug(premier-league|la-liga|bundesliga|premier-league-[0-9]{4}-[0-9]{2}|la-liga-[0-9]{4}-[0-9]{2}|bundesliga-[0-9]{4}-[0-9]{2})/table',
      name: LEAGUE_ROUTE_NAMES.table,
      component: () => import('../views/LeagueTableView.vue'),
      meta: { public: true, competitionWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionEditionSlug(premier-league|la-liga|bundesliga|premier-league-[0-9]{4}-[0-9]{2}|la-liga-[0-9]{4}-[0-9]{2}|bundesliga-[0-9]{4}-[0-9]{2})/fixtures',
      name: LEAGUE_ROUTE_NAMES.fixtures,
      component: () => import('../views/LeagueFixturesView.vue'),
      meta: { public: true, competitionWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionEditionSlug(premier-league|la-liga|bundesliga|premier-league-[0-9]{4}-[0-9]{2}|la-liga-[0-9]{4}-[0-9]{2}|bundesliga-[0-9]{4}-[0-9]{2})/predict',
      name: LEAGUE_ROUTE_NAMES.predict,
      component: () => import('../views/LeaguePredictView.vue'),
      meta: { requiresAuth: true, competitionWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionEditionSlug(premier-league|la-liga|bundesliga|premier-league-[0-9]{4}-[0-9]{2}|la-liga-[0-9]{4}-[0-9]{2}|bundesliga-[0-9]{4}-[0-9]{2})/markets',
      name: LEAGUE_ROUTE_NAMES.markets,
      component: () => import('../views/LeagueMarketsView.vue'),
      meta: { requiresAuth: true, competitionWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionEditionSlug(premier-league|la-liga|bundesliga|premier-league-[0-9]{4}-[0-9]{2}|la-liga-[0-9]{4}-[0-9]{2}|bundesliga-[0-9]{4}-[0-9]{2})/performance',
      name: LEAGUE_ROUTE_NAMES.performance,
      component: () => import('../views/LeaguePerformanceView.vue'),
      meta: { requiresAuth: true, admin: true, competitionWorkspace: true },
    },
    {
      path: '/:locale(en|es)/competitions/:competitionEditionSlug(premier-league|la-liga|bundesliga|premier-league-[0-9]{4}-[0-9]{2}|la-liga-[0-9]{4}-[0-9]{2}|bundesliga-[0-9]{4}-[0-9]{2})/swarm',
      name: LEAGUE_ROUTE_NAMES.swarm,
      component: () => import('../views/LeagueSwarmView.vue'),
      meta: { requiresAuth: true, admin: true, competitionWorkspace: true },
    },
    {
      path: '/:locale(en|es)/historic/competitions/:competitionEditionSlug(world-cup-2026)',
      name: HISTORIC_WORKSPACE_ROUTE_NAMES.overview,
      component: () => import('../views/Home.vue'),
      meta: { public: true, competitionWorkspace: true, historicWorkspace: true },
    },
    {
      path: '/:locale(en|es)/historic/competitions/:competitionEditionSlug(world-cup-2026)/groups',
      name: HISTORIC_WORKSPACE_ROUTE_NAMES.groups,
      component: () => import('../views/GroupsView.vue'),
      meta: { requiresAuth: true, competitionWorkspace: true, historicWorkspace: true },
    },
    {
      path: '/:locale(en|es)/historic/competitions/:competitionEditionSlug(world-cup-2026)/predict',
      name: HISTORIC_WORKSPACE_ROUTE_NAMES.predict,
      component: () => import('../views/PredictView.vue'),
      meta: { requiresAuth: true, competitionWorkspace: true, historicWorkspace: true },
    },
    {
      path: '/:locale(en|es)/historic/competitions/:competitionEditionSlug(world-cup-2026)/bracket',
      name: HISTORIC_WORKSPACE_ROUTE_NAMES.bracket,
      component: () => import('../views/TournamentView.vue'),
      meta: { requiresAuth: true, competitionWorkspace: true, historicWorkspace: true },
    },
    {
      path: '/:locale(en|es)/historic/competitions/:competitionEditionSlug(world-cup-2026)/markets',
      name: HISTORIC_WORKSPACE_ROUTE_NAMES.markets,
      component: () => import('../views/MarketsView.vue'),
      meta: { requiresAuth: true, competitionWorkspace: true, historicWorkspace: true },
    },
    {
      path: '/:locale(en|es)/historic/competitions/:competitionEditionSlug(world-cup-2026)/swarm',
      name: HISTORIC_WORKSPACE_ROUTE_NAMES.swarm,
      component: () => import('../views/SwarmLabView.vue'),
      meta: { requiresAuth: true, competitionWorkspace: true, historicWorkspace: true },
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
    if (!getCompetitionEdition(to.params.competitionEditionSlug)) {
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
