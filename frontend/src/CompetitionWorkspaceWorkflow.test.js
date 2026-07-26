import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.hoisted(() => vi.fn())
const authState = vi.hoisted(() => ({
  state: { loaded: true, signedIn: false, isAdmin: false, user: null },
}))

vi.mock('@clerk/vue', async () => {
  const { ref } = await import('vue')
  return {
    useAuth: () => ({ getToken: ref(vi.fn()), isLoaded: ref(true), isSignedIn: ref(false) }),
    useClerk: () => ref(null),
  }
})
vi.mock('./lib/api', () => ({ api: { get: apiGet }, installAuthInterceptor: vi.fn() }))
vi.mock('./lib/auth', () => ({
  clearAuthState: vi.fn(),
  refreshAuthState: vi.fn(),
  setAuthPendingState: vi.fn(),
  useAuthState: () => authState,
}))
vi.mock('./composables/useBillingStatus', async () => {
  const { ref } = await import('vue')
  return { useBillingStatus: () => ({ actionLoading: ref(false), billingHealth: ref(null), clearBillingStatus: vi.fn(), openBillingRecovery: vi.fn(), refreshBillingStatus: vi.fn(), requiresAttention: ref(false) }) }
})
vi.mock('./composables/useCurrentUserProfile', async () => {
  const { ref } = await import('vue')
  return { useCurrentUserProfile: () => ({ avatarUrl: ref(''), displayName: ref(''), email: ref(''), initials: ref('') }) }
})

import App from './App.vue'
import { i18n } from './i18n/index.js'
import router from './router/index.js'

describe('Competition selection workflow', () => {
  beforeEach(async () => {
    vi.stubGlobal('history', window.history)
    apiGet.mockImplementation((url) => Promise.resolve({ data: url === '/api/competitions'
      ? { competitions: [{
          slug: 'premier-league',
          current_edition: { slug: '2026-27', display_name: 'Premier League 2026-27', format: 'league', capabilities: ['table', 'fixtures', 'predictions', 'markets'] },
        }] }
      : {
          competition: { slug: 'premier-league', display_name: 'Premier League' },
          edition: { slug: '2026-27', display_name: 'Premier League 2026-27', format: 'league', capabilities: ['table', 'fixtures', 'predictions', 'markets'] },
        },
    }))
    await router.push('/es/competitions/world-cup-2026')
  })

  it('opens the localized Premier League overview from the existing switcher', async () => {
    const wrapper = mount(App, {
      global: { plugins: [i18n, router], stubs: { BillingStatusNotice: true, CookieBanner: true } },
    })
    await flushPromises()

    await wrapper.get('[data-testid="competition-toggle"]').trigger('click')
    await wrapper.get('[data-testid="competition-option-premier-league"]').trigger('click')

    await vi.waitFor(() => {
      expect(router.currentRoute.value.fullPath).toBe('/es/competitions/premier-league')
    })
    await flushPromises()
    expect(wrapper.get('h1').text()).toBe('Premier League 2026-27')
  })
})
