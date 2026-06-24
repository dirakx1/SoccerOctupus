import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import GroupsView from '../views/GroupsView.vue'
import PredictView from '../views/PredictView.vue'
import TournamentView from '../views/TournamentView.vue'
import MarketsView from '../views/MarketsView.vue'
import LegalNoticeView from '../views/LegalNoticeView.vue'
import AdminSettingsView from '../views/AdminSettingsView.vue'
import ProfileView from '../views/ProfileView.vue'
import SignInView from '../views/SignInView.vue'
import SignUpView from '../views/SignUpView.vue'
import SSOCallbackView from '../views/SSOCallbackView.vue'
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import PricingView from '../views/PricingView.vue'
import BillingSuccessView from '../views/BillingSuccessView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Home, meta: { public: true } },
    { path: '/groups', component: GroupsView, meta: { requiresAuth: true } },
    { path: '/predict', component: PredictView, meta: { requiresAuth: true } },
    { path: '/tournament', component: TournamentView, meta: { requiresAuth: true } },
    { path: '/markets', component: MarketsView, meta: { requiresAuth: true } },
    { path: '/profile', component: ProfileView, meta: { requiresAuth: true } },
    { path: '/pricing', component: PricingView, meta: { public: true } },
    { path: '/billing', redirect: '/profile', meta: { requiresAuth: true } },
    { path: '/billing/success', component: BillingSuccessView, meta: { requiresAuth: true } },
    { path: '/admin/settings', component: AdminSettingsView, meta: { requiresAuth: true, admin: true } },
    { path: '/sign-in', component: SignInView, meta: { public: true } },
    { path: '/sign-up', component: SignUpView, meta: { public: true } },
    { path: '/forgot-password', component: ForgotPasswordView, meta: { public: true } },
    { path: '/sso-callback', component: SSOCallbackView, meta: { public: true } },
    { path: '/legal', component: LegalNoticeView, meta: { public: true } },
  ]
})
