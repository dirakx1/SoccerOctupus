import { config, flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App.vue'
import { i18n } from './i18n/index.js'

const { clerkState, authState, routerState, refs } = await vi.hoisted(async () => {
  const { reactive, ref } = await import('vue')
  return {
    clerkState: {
      loaded: ref(true),
      signedIn: ref(true),
      clerk: ref({ signOut: vi.fn() }),
    },
    authState: reactive({ loaded: false, signedIn: false, isAdmin: false, user: null }),
    routerState: {
      currentRoute: ref({ meta: {}, path: '/', fullPath: '/', params: {}, query: {}, hash: '' }),
      push: vi.fn(),
      replace: vi.fn(),
    },
    refs: { ref },
  }
})
const refreshAuthState = vi.hoisted(() => vi.fn())
const setAuthPendingState = vi.hoisted(() => vi.fn())

vi.mock('@clerk/vue', () => ({
  useAuth: () => ({ getToken: refs.ref(vi.fn()), isLoaded: clerkState.loaded, isSignedIn: clerkState.signedIn }),
  useClerk: () => clerkState.clerk,
}))

vi.mock('vue-router', () => ({
  useRoute: () => routerState.currentRoute.value,
  useRouter: () => routerState,
  RouterView: { template: '<div />' },
}))

vi.mock('./lib/auth', () => ({
  clearAuthState: vi.fn(),
  refreshAuthState,
  setAuthPendingState,
  useAuthState: () => ({
    state: authState,
  }),
}))

vi.mock('./lib/api', () => ({ installAuthInterceptor: vi.fn() }))
vi.mock('./composables/useBillingStatus', () => ({
  useBillingStatus: () => ({ actionLoading: refs.ref(false), billingHealth: refs.ref(null), clearBillingStatus: vi.fn(), openBillingRecovery: vi.fn(), refreshBillingStatus: vi.fn(), requiresAttention: refs.ref(false) }),
}))
vi.mock('./composables/useCurrentUserProfile', () => ({
  useCurrentUserProfile: () => ({ avatarUrl: refs.ref(''), displayName: refs.ref(''), email: refs.ref(''), initials: refs.ref('') }),
}))

const shellStub = { template: '<main><slot name="auth-recovery" /><slot /><slot name="cookie" /></main>' }

describe('App auth completion recovery', () => {
  beforeEach(() => {
    config.global.plugins = [i18n]
    vi.clearAllMocks()
    window.localStorage.clear()
    authState.loaded = false
    authState.signedIn = false
    authState.isAdmin = false
    clerkState.loaded.value = true
    clerkState.signedIn.value = true
    refreshAuthState.mockReturnValue(new Promise(() => {}))
  })

  function mountApp() {
    return mount(App, {
      global: {
        stubs: { AppShell: shellStub, BillingStatusNotice: true, CookieBanner: true, 'router-view': true },
      },
    })
  }

  it('silently hydrates an established Clerk session without showing completion recovery', async () => {
    const wrapper = mountApp()
    await flushPromises()

    expect(refreshAuthState).toHaveBeenCalledWith({ force: true })
    expect(wrapper.find('.auth-recovery').exists()).toBe(false)
  })

  it('shows completion recovery only when an explicit post-auth handoff is pending', async () => {
    window.localStorage.setItem('socceroctopus.postAuthCompletion', String(Date.now()))
    const wrapper = mountApp()
    await flushPromises()

    expect(wrapper.find('.auth-recovery').exists()).toBe(true)
    expect(wrapper.text()).toContain('Finishing sign-in')
  })

  it('keeps retry available when an explicit handoff cannot hydrate', async () => {
    window.localStorage.setItem('socceroctopus.postAuthCompletion', String(Date.now()))
    refreshAuthState.mockRejectedValueOnce(new Error('backend unavailable'))
    const wrapper = mountApp()
    await flushPromises()

    expect(wrapper.text()).toContain('Try again')

    await wrapper.get('.auth-retry').trigger('click')
    expect(refreshAuthState).toHaveBeenCalledTimes(2)
  })
})
