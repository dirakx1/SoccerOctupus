import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import PricingView from './PricingView.vue'
import { clearAuthState, setAuthState } from '../lib/auth'

const routerPush = vi.fn()
const routerReplace = vi.fn()
let routeQuery = {}

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: routeQuery }),
  useRouter: () => ({ push: routerPush, replace: routerReplace }),
}))

vi.mock('../lib/billing', () => ({
  getPlans: vi.fn(),
  getSubscription: vi.fn(),
  createCheckout: vi.fn(),
}))

import { createCheckout, getPlans, getSubscription } from '../lib/billing'

const plans = [
  { tier: 'free', label: 'Free', display_price: '$0', interval: 'month', features: ['No paid prediction runs'] },
  { tier: 'basic', label: 'Basic', display_price: '$5', interval: 'month', features: ['Predictions without YouTube video analysis'] },
  { tier: 'pro', label: 'Pro', display_price: '$10', interval: 'month', features: ['Predictions with YouTube video analysis'] },
]

describe('PricingView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    routeQuery = {}
    clearAuthState()
    getPlans.mockResolvedValue({ data: { plans } })
    getSubscription.mockResolvedValue({ data: { tier: 'free' } })
    createCheckout.mockResolvedValue({ data: { url: 'https://checkout.stripe.com/session' } })
    Object.defineProperty(window, 'location', {
      value: { assign: vi.fn() },
      writable: true,
    })
  })

  it('stores a post-auth redirect and routes to sign-up when Basic is clicked signed out', async () => {
    const wrapper = mount(PricingView, { global: { stubs: ['router-link'] } })
    await flushPromises()

    await wrapper.findAll('button')[1].trigger('click')

    expect(window.localStorage.getItem('socceroctopus.postAuthRedirect')).toBe('/pricing?plan=basic&checkout=1')
    expect(routerPush).toHaveBeenCalledWith('/sign-up')
  })

  it('starts Pro checkout when signed in', async () => {
    setAuthState({ signedIn: true, isAdmin: false, user: { email: 'user@example.com' } })
    const wrapper = mount(PricingView, { global: { stubs: ['router-link'] } })
    await flushPromises()

    await wrapper.findAll('button')[2].trigger('click')
    await flushPromises()

    expect(createCheckout).toHaveBeenCalledWith('pro')
    expect(window.location.assign).toHaveBeenCalledWith('https://checkout.stripe.com/session')
  })

  it('disables the current signed-in tier', async () => {
    setAuthState({ signedIn: true, isAdmin: false, user: { email: 'user@example.com' } })
    getSubscription.mockResolvedValue({ data: { tier: 'pro' } })
    const wrapper = mount(PricingView, { global: { stubs: ['router-link'] } })
    await flushPromises()

    const proButton = wrapper.findAll('button')[2]
    expect(proButton.attributes('disabled')).toBeDefined()
    expect(proButton.text()).toContain('Choose')

    await proButton.trigger('click')
    expect(createCheckout).not.toHaveBeenCalled()
  })
})
