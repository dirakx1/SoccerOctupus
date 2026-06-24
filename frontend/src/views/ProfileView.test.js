import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProfileView from './ProfileView.vue'

const routerPush = vi.fn()
const clerkState = vi.hoisted(() => ({
  isLoaded: { value: true, __v_isRef: true },
  user: {
    value: {
      firstName: 'Alex',
      lastName: 'Morgan',
      imageUrl: '',
      primaryEmailAddress: { emailAddress: 'alex@example.com' },
      update: vi.fn(),
      reload: vi.fn(),
      updatePassword: vi.fn(),
    },
    __v_isRef: true,
  },
}))

vi.mock('@clerk/vue', () => ({
  useUser: () => ({
    isLoaded: clerkState.isLoaded,
    user: clerkState.user,
  }),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
}))

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

vi.mock('../lib/billing', () => ({
  getSubscription: vi.fn(),
  getUsage: vi.fn(),
  createPortalSession: vi.fn(),
}))

import { api } from '../lib/api'
import { createPortalSession, getSubscription, getUsage } from '../lib/billing'

describe('ProfileView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routerPush.mockClear()
    api.get.mockResolvedValue({ data: { is_admin: false } })
    getSubscription.mockResolvedValue({
      data: {
        tier: 'pro',
        status: 'active',
        is_paid_entitled: true,
      },
    })
    getUsage.mockResolvedValue({
      data: {
        tier: 'pro',
        cycle_start: '2026-06-01T00:00:00+00:00',
        cycle_end: '2026-07-01T00:00:00+00:00',
        features: [
          {
            feature_key: 'match_prediction',
            label: 'Match predictions',
            limit_count: null,
            used_count: 2,
            remaining_count: null,
            unlimited: true,
            limit_source: 'policy',
          },
        ],
      },
    })
    createPortalSession.mockResolvedValue({ data: { url: 'https://billing.stripe.com/session' } })
    Object.defineProperty(window, 'location', {
      value: { assign: vi.fn() },
      writable: true,
    })
  })

  it('shows the current billing tier on the profile page', async () => {
    const wrapper = mount(ProfileView)
    await flushPromises()

    expect(wrapper.text()).toContain('Billing')
    expect(wrapper.text()).toContain('Current tier')
    expect(wrapper.text()).toContain('Pro')
    expect(wrapper.text()).toContain('Match predictions')
    expect(wrapper.text()).toContain('Unlimited')
  })

  it('opens the Stripe customer portal from profile', async () => {
    const wrapper = mount(ProfileView)
    await flushPromises()

    await wrapper.find('.billing-action').trigger('click')
    await flushPromises()

    expect(createPortalSession).toHaveBeenCalledWith({ return_path: '/profile' })
    expect(window.location.assign).toHaveBeenCalledWith('https://billing.stripe.com/session')
  })

  it('routes free users to pricing from profile billing', async () => {
    getSubscription.mockResolvedValue({
      data: {
        tier: 'free',
        status: null,
        is_paid_entitled: false,
      },
    })
    const wrapper = mount(ProfileView)
    await flushPromises()

    expect(wrapper.text()).toContain('Plans')
    await wrapper.find('.billing-action').trigger('click')
    await flushPromises()

    expect(routerPush).toHaveBeenCalledWith('/pricing')
    expect(createPortalSession).not.toHaveBeenCalled()
  })
})
