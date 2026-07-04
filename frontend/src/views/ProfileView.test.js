import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ProfileView from './ProfileView.vue'

const routerPush = vi.fn()
const clerkState = vi.hoisted(() => ({
  clerk: {
    __unstable__environment: {
      userSettings: {
        passwordSettings: {
          min_length: 8,
          max_length: 72,
          require_lowercase: false,
          require_uppercase: false,
          require_numbers: false,
          require_special_char: false,
          disable_hibp: true,
          show_zxcvbn: false,
          min_zxcvbn_strength: 0,
        },
      },
    },
  },
  isLoaded: { value: true, __v_isRef: true },
  signIn: {
    value: {
      validatePassword: vi.fn(),
    },
    __v_isRef: true,
  },
  user: {
    value: {
      firstName: 'Alex',
      lastName: 'Morgan',
      username: 'alex',
      imageUrl: '',
      primaryEmailAddress: { emailAddress: 'alex@example.com' },
      totpEnabled: false,
      backupCodeEnabled: false,
      twoFactorEnabled: false,
      update: vi.fn(),
      reload: vi.fn(),
      updatePassword: vi.fn(),
      createTOTP: vi.fn(),
      verifyTOTP: vi.fn(),
      disableTOTP: vi.fn(),
      createBackupCode: vi.fn(),
    },
    __v_isRef: true,
  },
}))

vi.mock('@clerk/vue', () => ({
  useClerk: () => clerkState.clerk,
  useSignIn: () => ({
    isLoaded: clerkState.isLoaded,
    signIn: clerkState.signIn,
    setActive: { value: vi.fn(), __v_isRef: true },
  }),
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
  createPaymentMethodSession: vi.fn(),
}))

import { api } from '../lib/api'
import { createPaymentMethodSession, createPortalSession, getSubscription, getUsage } from '../lib/billing'

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
    createPaymentMethodSession.mockResolvedValue({ data: { url: 'https://billing.stripe.com/payment-method' } })
    Object.defineProperty(window, 'location', {
      value: { assign: vi.fn() },
      writable: true,
    })
  })

  it('shows the current billing tier on the profile page', async () => {
    const wrapper = mount(ProfileView)
    await flushPromises()

    expect(wrapper.text()).toContain('Security')
    expect(wrapper.text()).toContain('alex')
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

  it('shows payment recovery for failed billing status', async () => {
    getSubscription.mockResolvedValue({
      data: {
        tier: 'pro',
        status: 'past_due',
        is_paid_entitled: true,
        billing_health: {
          state: 'payment_failed',
          severity: 'warning',
          requires_attention: true,
          blocks_access: false,
          action: 'update_payment_method',
          action_label: 'Pay invoice',
          message: 'Payment failed. Pay the invoice to keep access.',
        },
      },
    })
    const wrapper = mount(ProfileView)
    await flushPromises()

    expect(wrapper.text()).toContain('Payment failed. Pay the invoice to keep access.')
    expect(wrapper.text()).toContain('Pay invoice')

    const buttons = wrapper.findAll('button')
    await buttons.find((button) => button.text().includes('Pay invoice')).trigger('click')
    await flushPromises()

    expect(createPaymentMethodSession).toHaveBeenCalledWith({ return_path: '/profile' })
    expect(window.location.assign).toHaveBeenCalledWith('https://billing.stripe.com/payment-method')
  })

  it('renders the account security section with 2FA state', async () => {
    const wrapper = mount(ProfileView)
    await flushPromises()

    expect(wrapper.text()).toContain('Security')
    expect(wrapper.text()).toContain('Authenticator app')
    expect(wrapper.text()).toContain('Backup codes')
    expect(wrapper.text()).toContain('alex')
  })

  it('blocks profile password updates that fail policy', async () => {
    const wrapper = mount(ProfileView)
    await flushPromises()

    const passwordForm = wrapper.findAll('form')[1]
    await passwordForm.find('input[autocomplete="current-password"]').setValue('current-pass')
    await passwordForm.find('input[autocomplete="new-password"]').setValue('short')
    await passwordForm.findAll('input[autocomplete="new-password"]')[1].setValue('short')
    await passwordForm.trigger('submit.prevent')
    await flushPromises()

    expect(clerkState.user.value.updatePassword).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('New password does not meet the password requirements.')
  })

  it('updates password through Clerk when policy and confirmation pass', async () => {
    clerkState.user.value.updatePassword.mockResolvedValue({})
    const wrapper = mount(ProfileView)
    await flushPromises()

    const passwordForm = wrapper.findAll('form')[1]
    await passwordForm.find('input[autocomplete="current-password"]').setValue('current-pass')
    await passwordForm.find('input[autocomplete="new-password"]').setValue('longenough')
    await passwordForm.findAll('input[autocomplete="new-password"]')[1].setValue('longenough')
    await passwordForm.trigger('submit.prevent')
    await flushPromises()

    expect(clerkState.user.value.updatePassword).toHaveBeenCalledWith({
      currentPassword: 'current-pass',
      newPassword: 'longenough',
      signOutOfOtherSessions: true,
    })
  })
})
