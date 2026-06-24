import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProfileView from './ProfileView.vue'

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

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

vi.mock('../lib/billing', () => ({
  getSubscription: vi.fn(),
  createPortalSession: vi.fn(),
}))

import { api } from '../lib/api'
import { createPortalSession, getSubscription } from '../lib/billing'

describe('ProfileView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.get.mockResolvedValue({ data: { is_admin: false } })
    getSubscription.mockResolvedValue({
      data: {
        tier: 'pro',
        status: 'active',
        is_paid_entitled: true,
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
  })

  it('opens the Stripe customer portal from profile', async () => {
    const wrapper = mount(ProfileView)
    await flushPromises()

    await wrapper.find('.billing-action').trigger('click')
    await flushPromises()

    expect(createPortalSession).toHaveBeenCalledWith({ return_path: '/profile' })
    expect(window.location.assign).toHaveBeenCalledWith('https://billing.stripe.com/session')
  })
})
