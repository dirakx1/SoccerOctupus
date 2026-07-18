import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import PricingView from './PricingView.vue'
import { clearAuthState, setAuthState } from '../lib/auth'
import { applyLocale, i18n } from '../i18n/index.js'

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
  changePlan: vi.fn(),
}))

import { changePlan, getPlans, getSubscription } from '../lib/billing'

const plans = [
  {
    tier: 'free',
    label: 'Free',
    display_price: '$0',
    interval: 'month',
    features: [
      '1 match prediction',
      '1 tournament simulation',
      '3 match markets',
      '3 tournament markets',
    ],
  },
  {
    tier: 'basic',
    label: 'Basic',
    display_price: '$5',
    interval: 'month',
    features: ['Unlimited prediction runs', 'Unlimited market generation', 'No video analysis'],
  },
  {
    tier: 'pro',
    label: 'Pro',
    display_price: '$10',
    interval: 'month',
    features: ['Unlimited prediction runs', 'Unlimited market generation', 'Includes video analysis'],
  },
]

describe('PricingView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    routeQuery = {}
    clearAuthState()
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
    getPlans.mockResolvedValue({ data: { plans } })
    getSubscription.mockResolvedValue({ data: { tier: 'free' } })
    changePlan.mockResolvedValue({ data: { action: 'checkout', url: 'https://checkout.stripe.com/session' } })
    Object.defineProperty(window, 'location', {
      value: { assign: vi.fn() },
      writable: true,
    })
  })

  function mountPricing() {
    return mount(PricingView, { global: { plugins: [i18n], stubs: ['router-link'] } })
  }

  it('stores a post-auth redirect and routes to sign-up when Basic is clicked signed out', async () => {
    const wrapper = mountPricing()
    await flushPromises()

    expect(wrapper.text()).toContain('1 match prediction')
    expect(wrapper.text()).toContain('Unlimited market generation')

    await wrapper.findAll('button')[1].trigger('click')

    expect(window.localStorage.getItem('socceroctopus.postAuthRedirect')).toBe('/pricing?plan=basic&checkout=1')
    expect(routerPush).toHaveBeenCalledWith('/sign-up')
  })

  it('starts Pro checkout when signed in', async () => {
    setAuthState({ signedIn: true, isAdmin: false, user: { email: 'user@example.com' } })
    const wrapper = mountPricing()
    await flushPromises()

    await wrapper.findAll('button')[2].trigger('click')
    await flushPromises()

    expect(changePlan).toHaveBeenCalledWith('pro')
    expect(window.location.assign).toHaveBeenCalledWith('https://checkout.stripe.com/session')
  })

  it('opens cancellation flow when a paid user chooses Free', async () => {
    setAuthState({ signedIn: true, isAdmin: false, user: { email: 'user@example.com' } })
    getSubscription.mockResolvedValue({ data: { tier: 'pro' } })
    changePlan.mockResolvedValue({
      data: {
        action: 'subscription_cancel',
        url: 'https://billing.stripe.com/cancel',
      },
    })
    const wrapper = mountPricing()
    await flushPromises()

    await wrapper.findAll('button')[0].trigger('click')
    await flushPromises()

    expect(changePlan).toHaveBeenCalledWith('free')
    expect(window.location.assign).toHaveBeenCalledWith('https://billing.stripe.com/cancel')
    expect(routerPush).not.toHaveBeenCalled()
  })

  it('disables the current signed-in tier', async () => {
    setAuthState({ signedIn: true, isAdmin: false, user: { email: 'user@example.com' } })
    getSubscription.mockResolvedValue({ data: { tier: 'pro' } })
    const wrapper = mountPricing()
    await flushPromises()

    const proButton = wrapper.findAll('button')[2]
    expect(proButton.attributes('disabled')).toBeDefined()
    expect(proButton.text()).toContain('Current plan')

    await proButton.trigger('click')
    expect(changePlan).not.toHaveBeenCalled()
  })

  it('uses Spanish frontend copy while preserving plan data from billing', async () => {
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const wrapper = mountPricing()
    await flushPromises()

    expect(wrapper.text()).toContain('Elige tu acceso a predicciones')
    expect(wrapper.text()).toContain('Cobertura completa de señales')
    expect(wrapper.text()).toContain('Unlimited prediction runs')
    expect(wrapper.text()).toContain('/month')
  })

  it('renders a retryable plan-load error while preserving the existing post-auth checkout handoff', async () => {
    getPlans.mockRejectedValue({ response: { data: { error: 'Billing service unavailable' } } })
    routeQuery = { plan: 'pro', checkout: '1' }
    setAuthState({ signedIn: true, isAdmin: false, user: { email: 'user@example.com' } })
    const wrapper = mountPricing()
    await flushPromises()

    expect(wrapper.text()).toContain('Could not load plans.')
    expect(wrapper.text()).toContain('Billing service unavailable')
    expect(changePlan).toHaveBeenCalledWith('pro')

    getPlans.mockResolvedValue({ data: { plans } })
    await wrapper.find('.btn-secondary').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Pro')
    expect(changePlan).toHaveBeenCalledTimes(1)
  })

  it('shows a plan-change error and keeps the plan actions available', async () => {
    setAuthState({ signedIn: true, isAdmin: false, user: { email: 'user@example.com' } })
    changePlan.mockRejectedValue({ response: { data: { error: 'Card update needed' } } })
    const wrapper = mountPricing()
    await flushPromises()

    await wrapper.findAll('button')[1].trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Card update needed')
    expect(wrapper.findAll('button')[1].attributes('disabled')).toBeUndefined()
  })
})
