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
const apiGet = vi.hoisted(() => vi.fn())

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

vi.mock('./lib/api', () => ({ api: { get: apiGet }, installAuthInterceptor: vi.fn() }))
vi.mock('./composables/useBillingStatus', () => ({
  useBillingStatus: () => ({ actionLoading: refs.ref(false), billingHealth: refs.ref(null), clearBillingStatus: vi.fn(), openBillingRecovery: vi.fn(), refreshBillingStatus: vi.fn(), requiresAttention: refs.ref(false) }),
}))
vi.mock('./composables/useCurrentUserProfile', () => ({
  useCurrentUserProfile: () => ({ avatarUrl: refs.ref(''), displayName: refs.ref(''), email: refs.ref(''), initials: refs.ref('') }),
}))

const shellStub = {
  props: ['edition', 'editions', 'navigation'],
  emits: ['edition-change'],
  template: '<main><span data-testid="active-edition">{{ edition.displayName }}</span><span v-if="navigation[0]" data-testid="active-navigation-edition">{{ navigation[0].route.params.editionSlug }}</span><button v-if="editions[1]" data-testid="select-league" @click="$emit(\'edition-change\', editions[1])">Select league</button><slot name="auth-recovery" /><slot /><slot name="cookie" /></main>',
}

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
    routerState.currentRoute.value = { meta: {}, path: '/', fullPath: '/', params: {}, query: {}, hash: '' }
    refreshAuthState.mockReturnValue(new Promise(() => {}))
    apiGet.mockResolvedValue({ data: { competitions: [] } })
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

  it('loads the catalog and opens a selected Competition overview in the current locale', async () => {
    routerState.currentRoute.value = {
      meta: { public: true, competitionWorkspace: true },
      name: 'competition-workspace-overview',
      path: '/es/competitions/world-cup-2026',
      fullPath: '/es/competitions/world-cup-2026',
      params: { locale: 'es', competitionEditionSlug: 'world-cup-2026' },
      query: {},
      hash: '',
    }
    apiGet.mockResolvedValueOnce({ data: { competitions: [{
      slug: 'premier-league',
      current_edition: {
        slug: '2026-27',
        display_name: 'Premier League 2026-27',
        format: 'league',
        capabilities: ['table', 'fixtures', 'predictions', 'markets'],
      },
    }] } })
    const wrapper = mountApp()
    await flushPromises()

    await wrapper.get('[data-testid="select-league"]').trigger('click')

    expect(routerState.push).toHaveBeenCalledWith({
      name: 'league-competition-workspace-overview',
      params: { locale: 'es', competitionSlug: 'premier-league' },
    })
  })

  it('keeps shell identity and navigation scoped to an immutable Competition Edition', async () => {
    routerState.currentRoute.value = {
      meta: { public: true, competitionWorkspace: true, leagueWorkspace: true },
      name: 'league-edition-workspace-overview',
      path: '/en/competitions/premier-league/editions/2026-27',
      fullPath: '/en/competitions/premier-league/editions/2026-27',
      params: { locale: 'en', competitionSlug: 'premier-league', editionSlug: '2026-27' },
      query: {},
      hash: '',
    }
    apiGet.mockImplementation((url) => Promise.resolve({ data: url.includes('/editions/')
      ? {
          competition: { slug: 'premier-league' },
          edition: { slug: '2026-27', display_name: 'Premier League 2026-27', format: 'league', capabilities: ['table'] },
        }
      : { competitions: [{
          slug: 'premier-league',
          current_edition: { slug: '2027-28', display_name: 'Premier League 2027-28', format: 'league', capabilities: ['table'] },
        }] },
    }))

    const wrapper = mountApp()
    await flushPromises()

    expect(wrapper.get('[data-testid="active-edition"]').text()).toBe('Premier League 2026-27')
    expect(wrapper.get('[data-testid="active-navigation-edition"]').text()).toBe('2026-27')
  })
})
