import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import SignInView from './SignInView.vue'

const routerPush = vi.fn()
const clerkState = vi.hoisted(() => ({
  activateSessionAndHydrateAuth: vi.fn(),
  clerk: {},
  isLoaded: { value: true, __v_isRef: true },
  setActive: { value: vi.fn(), __v_isRef: true },
  signIn: {
    value: {
      create: vi.fn(),
      authenticateWithRedirect: vi.fn(),
      attemptFirstFactor: vi.fn(),
      attemptSecondFactor: vi.fn(),
      prepareFirstFactor: vi.fn(),
      prepareSecondFactor: vi.fn(),
    },
    __v_isRef: true,
  },
}))

vi.mock('@clerk/vue', () => ({
  useClerk: () => clerkState.clerk,
  useSignIn: () => ({
    isLoaded: clerkState.isLoaded,
    signIn: clerkState.signIn,
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

describe('SignInView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clerkState.signIn.value.create.mockResolvedValue({
      status: 'complete',
      createdSessionId: 'sess_123',
    })
    clerkState.signIn.value.authenticateWithRedirect.mockResolvedValue(undefined)
  })

  it('signs in with an email-or-username identifier', async () => {
    const wrapper = mount(SignInView, {
      global: { stubs: ['RouterLink'] },
    })

    expect(wrapper.text()).toContain('Email or username')

    await wrapper.find('input[autocomplete="username"]').setValue('alexmorgan')
    await wrapper.find('input[autocomplete="current-password"]').setValue('secret-pass')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(clerkState.signIn.value.create).toHaveBeenCalledWith({
      strategy: 'password',
      identifier: 'alexmorgan',
      password: 'secret-pass',
    })
  })

  it('keeps TOTP second-factor rendering', async () => {
    clerkState.signIn.value.create.mockResolvedValue({
      status: 'needs_second_factor',
      supportedSecondFactors: [{ strategy: 'totp' }],
    })
    const wrapper = mount(SignInView, {
      global: { stubs: ['RouterLink'] },
    })

    await wrapper.find('input[autocomplete="username"]').setValue('alexmorgan')
    await wrapper.find('input[autocomplete="current-password"]').setValue('secret-pass')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('Enter the code from your authenticator app.')
  })

  it('keeps backup-code second-factor rendering', async () => {
    clerkState.signIn.value.create.mockResolvedValue({
      status: 'needs_second_factor',
      supportedSecondFactors: [{ strategy: 'backup_code' }],
    })
    const wrapper = mount(SignInView, {
      global: { stubs: ['RouterLink'] },
    })

    await wrapper.find('input[autocomplete="username"]').setValue('alexmorgan')
    await wrapper.find('input[autocomplete="current-password"]').setValue('secret-pass')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('Enter one of your backup codes.')
    expect(wrapper.text()).toContain('Backup code')
  })

  it('switches between TOTP and backup code locally without preparing either factor', async () => {
    clerkState.signIn.value.create.mockResolvedValue({
      status: 'needs_second_factor',
      supportedSecondFactors: [{ strategy: 'totp' }, { strategy: 'backup_code' }],
    })
    const wrapper = mount(SignInView, {
      global: { stubs: ['RouterLink'] },
    })

    await wrapper.find('input[autocomplete="username"]').setValue('alexmorgan')
    await wrapper.find('input[autocomplete="current-password"]').setValue('secret-pass')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    const switchButton = wrapper.get('button.second-factor-switch')
    expect(switchButton.text()).toBe('Use a backup code instead')
    expect(clerkState.signIn.value.prepareFirstFactor).not.toHaveBeenCalled()
    expect(clerkState.signIn.value.prepareSecondFactor).not.toHaveBeenCalled()

    await switchButton.trigger('click')

    expect(wrapper.text()).toContain('Enter one of your backup codes.')
    expect(wrapper.get('input[autocomplete="one-time-code"]').attributes('inputmode')).toBe('text')
    expect(wrapper.get('button.second-factor-switch').text()).toBe('Use authenticator app instead')
    expect(clerkState.signIn.value.prepareFirstFactor).not.toHaveBeenCalled()
    expect(clerkState.signIn.value.prepareSecondFactor).not.toHaveBeenCalled()

    await wrapper.get('button.second-factor-switch').trigger('click')

    expect(wrapper.text()).toContain('Enter the code from your authenticator app.')
    expect(wrapper.get('input[autocomplete="one-time-code"]').attributes('inputmode')).toBe('numeric')
  })

  it('starts OAuth redirect for Google and X without exposing Facebook', async () => {
    for (const strategy of ['oauth_google', 'oauth_x']) {
      clerkState.signIn.value.authenticateWithRedirect.mockClear()
      const wrapper = mount(SignInView, {
        global: { stubs: ['RouterLink'] },
      })

      await wrapper.find(`button[data-strategy="${strategy}"]`).trigger('click')
      await flushPromises()
      expect(clerkState.signIn.value.authenticateWithRedirect).toHaveBeenLastCalledWith({
        strategy,
        redirectUrl: '/sso-callback',
        redirectUrlComplete: '/',
      })
      wrapper.unmount()
    }

    const wrapper = mount(SignInView, {
      global: { stubs: ['RouterLink'] },
    })
    expect(wrapper.find('button[data-strategy="oauth_facebook"]').exists()).toBe(false)
  })
})
