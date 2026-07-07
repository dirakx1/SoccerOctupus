import { createRouter, createWebHistory } from 'vue-router'
import { useAuthState } from '../lib/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('../views/Home.vue'), meta: { public: true } },
    { path: '/groups', component: () => import('../views/GroupsView.vue'), meta: { requiresAuth: true } },
    { path: '/predict', component: () => import('../views/PredictView.vue'), meta: { requiresAuth: true } },
    { path: '/tournament', component: () => import('../views/TournamentView.vue'), meta: { requiresAuth: true } },
    { path: '/markets', component: () => import('../views/MarketsView.vue'), meta: { requiresAuth: true } },
    { path: '/profile', component: () => import('../views/ProfileView.vue'), meta: { requiresAuth: true } },
    { path: '/pricing', component: () => import('../views/PricingView.vue'), meta: { public: true } },
    { path: '/billing', redirect: '/profile', meta: { requiresAuth: true } },
    { path: '/billing/success', component: () => import('../views/BillingSuccessView.vue'), meta: { requiresAuth: true } },
    { path: '/admin/settings', component: () => import('../views/AdminSettingsView.vue'), meta: { requiresAuth: true, admin: true } },
    { path: '/sign-in', component: () => import('../views/SignInView.vue'), meta: { public: true } },
    { path: '/sign-up', component: () => import('../views/SignUpView.vue'), meta: { public: true } },
    { path: '/forgot-password', component: () => import('../views/ForgotPasswordView.vue'), meta: { public: true } },
    { path: '/sso-callback', component: () => import('../views/SSOCallbackView.vue'), meta: { public: true } },
    { path: '/legal', component: () => import('../views/LegalNoticeView.vue'), meta: { public: true } },
    { path: '/cookie-policy', component: () => import('../views/CookiePolicyView.vue'), meta: { public: true } },
    { path: '/contact', component: () => import('../views/ContactView.vue'), meta: { public: true } },
    { path: '/about', component: () => import('../views/AboutView.vue'), meta: { public: true } },
  ]
})

const auth = useAuthState()

router.beforeEach((to) => {
  if (!auth.state.loaded) return true

  if (to.meta.requiresAuth && !auth.state.signedIn) {
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
