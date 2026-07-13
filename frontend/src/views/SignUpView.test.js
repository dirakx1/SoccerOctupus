import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import SignUpView from './SignUpView.vue'

const routerPush = vi.fn()
const clerkState = vi.hoisted(() => ({
  activateSessionAndHydrateAuth: vi.fn(),
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
  setActive: { value: vi.fn(), __v_isRef: true },
  signUp: {
    value: {
      create: vi.fn(),
      authenticateWithRedirect: vi.fn(),
      prepareEmailAddressVerification: vi.fn(),
      attemptEmailAddressVerification: vi.fn(),
      validatePassword: vi.fn(),
      verifications: {
        emailAddress: { supportedStrategies: ['email_code'] },
      },
    },
    __v_isRef: true,
  },
}))

vi.mock('@clerk/vue', () => ({
  useClerk: () => clerkState.clerk,
  useSignUp: () => ({
    isLoaded: clerkState.isLoaded,
    signUp: clerkState.signUp,
    setActive: clerkState.setActive,
  }),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
}))

vi.mock('../lib/clerkSession', () => ({
  activateSessionAndHydrateAuth: clerkState.activateSessionAndHydrateAuth,
}))

vi.mock('../lib/postAuthRedirect', () => ({
  consumePostAuthRedirect: vi.fn(() => ''),
  peekPostAuthRedirect: vi.fn(() => ''),
}))

describe('SignUpView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clerkState.signUp.value.create.mockResolvedValue({
      status: 'complete',
      createdSessionId: 'sess_123',
    })
    clerkState.signUp.value.authenticateWithRedirect.mockResolvedValue(undefined)
    clerkState.signUp.value.prepareEmailAddressVerification.mockResolvedValue(undefined)
    clerkState.signUp.value.attemptEmailAddressVerification.mockResolvedValue({
      status: 'complete',
      createdSessionId: 'sess_123',
    })
    clerkState.activateSessionAndHydrateAuth.mockResolvedValue(undefined)
  })

  it('does not repeat account creation when Clerk activated the session before hydration finished', async () => {
    clerkState.activateSessionAndHydrateAuth.mockResolvedValue({ hydrated: false })
    const wrapper = mount(SignUpView, {
      global: { stubs: ['RouterLink'] },
    })

    await wrapper.find('input[autocomplete="email"]').setValue('alex@example.com')
    await wrapper.find('input[autocomplete="username"]').setValue('alexmorgan')
    await wrapper.find('input[autocomplete="new-password"]').setValue('longenough')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(clerkState.signUp.value.create).toHaveBeenCalledTimes(1)
    expect(routerPush).toHaveBeenCalledWith('/')
    expect(wrapper.text()).not.toContain('Unable to create your account')
  })

  it('requires username and sends it to Clerk on sign-up', async () => {
    const wrapper = mount(SignUpView, {
      global: { stubs: ['RouterLink'] },
    })

    expect(wrapper.text()).toContain('Username')
    expect(wrapper.find('input[autocomplete="username"]').attributes('required')).toBeDefined()

    await wrapper.find('input[autocomplete="email"]').setValue('alex@example.com')
    await wrapper.find('input[autocomplete="username"]').setValue('alexmorgan')
    await wrapper.find('input[autocomplete="new-password"]').setValue('longenough')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(clerkState.signUp.value.create).toHaveBeenCalledWith({
      emailAddress: 'alex@example.com',
      username: 'alexmorgan',
      password: 'longenough',
      firstName: undefined,
      lastName: undefined,
    })
    expect(clerkState.activateSessionAndHydrateAuth).toHaveBeenCalled()
  })

  it('blocks sign-up when username is empty', async () => {
    const wrapper = mount(SignUpView, {
      global: { stubs: ['RouterLink'] },
    })

    await wrapper.find('input[autocomplete="email"]').setValue('alex@example.com')
    await wrapper.find('input[autocomplete="new-password"]').setValue('longenough')
    await wrapper.find('form').trigger('submit.prevent')

    expect(clerkState.signUp.value.create).not.toHaveBeenCalled()
  })

  it('starts OAuth redirect for Google and X without exposing Facebook', async () => {
    for (const strategy of ['oauth_google', 'oauth_x']) {
      clerkState.signUp.value.authenticateWithRedirect.mockClear()
      const wrapper = mount(SignUpView, {
        global: { stubs: ['RouterLink'] },
      })

      await wrapper.find(`button[data-strategy="${strategy}"]`).trigger('click')
      await flushPromises()
      expect(clerkState.signUp.value.authenticateWithRedirect).toHaveBeenLastCalledWith({
        strategy,
        redirectUrl: '/sso-callback',
        redirectUrlComplete: '/',
      })
      wrapper.unmount()
    }

    const wrapper = mount(SignUpView, {
      global: { stubs: ['RouterLink'] },
    })
    expect(wrapper.find('button[data-strategy="oauth_facebook"]').exists()).toBe(false)
  })

  it('keeps email-code verification for unverified email sign-ups', async () => {
    clerkState.signUp.value.create.mockResolvedValue({
      status: 'missing_requirements',
      unverifiedFields: ['email_address'],
    })
    const wrapper = mount(SignUpView, {
      global: { stubs: ['RouterLink'] },
    })

    await wrapper.find('input[autocomplete="email"]').setValue('alex@example.com')
    await wrapper.find('input[autocomplete="username"]').setValue('alexmorgan')
    await wrapper.find('input[autocomplete="new-password"]').setValue('longenough')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(clerkState.signUp.value.prepareEmailAddressVerification).toHaveBeenCalledWith({ strategy: 'email_code' })
  })
})
