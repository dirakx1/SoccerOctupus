import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import SignInView from './SignInView.vue'

const routerPush = vi.fn()
const routeQuery = vi.hoisted(() => ({}))
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
  useRoute: () => ({ query: routeQuery }),
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
    Object.keys(routeQuery).forEach((key) => delete routeQuery[key])
    delete clerkState.signIn.value.status
    delete clerkState.signIn.value.supportedFirstFactors
    delete clerkState.signIn.value.supportedSecondFactors
    clerkState.signIn.value.create.mockResolvedValue({
      status: 'complete',
      createdSessionId: 'sess_123',
    })
    clerkState.signIn.value.authenticateWithRedirect.mockResolvedValue(undefined)
    clerkState.activateSessionAndHydrateAuth.mockResolvedValue(undefined)
  })

  it('does not repeat sign-in when Clerk activated the session before hydration finished', async () => {
    clerkState.activateSessionAndHydrateAuth.mockResolvedValue({ hydrated: false })
    const wrapper = mount(SignInView, {
      global: { stubs: ['RouterLink'] },
    })

    await wrapper.find('input[autocomplete="username"]').setValue('alexmorgan')
    await wrapper.find('input[autocomplete="current-password"]').setValue('secret-pass')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(clerkState.signIn.value.create).toHaveBeenCalledTimes(1)
    expect(routerPush).toHaveBeenCalledWith('/')
    expect(wrapper.text()).not.toContain('Unable to sign in')
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

  it('resumes an OAuth sign-in that needs TOTP on mount', async () => {
    routeQuery.resume = 'oauth'
    clerkState.signIn.value.status = 'needs_second_factor'
    clerkState.signIn.value.supportedSecondFactors = [{ strategy: 'totp' }]

    const wrapper = mount(SignInView, {
      global: { stubs: ['RouterLink'] },
    })
    await flushPromises()

    expect(clerkState.signIn.value.create).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Enter the code from your authenticator app.')
  })

  it('does not auto-resume a pending resource outside the OAuth callback path', async () => {
    clerkState.signIn.value.status = 'needs_second_factor'
    clerkState.signIn.value.supportedSecondFactors = [{
      strategy: 'email_code',
      emailAddressId: 'idn_email',
    }]

    const wrapper = mount(SignInView, {
      global: { stubs: ['RouterLink'] },
    })
    await flushPromises()

    expect(clerkState.signIn.value.prepareSecondFactor).not.toHaveBeenCalled()
    expect(wrapper.find('input[autocomplete="username"]').exists()).toBe(true)
  })

  it('resumes an OAuth sign-in that needs a password without restarting OAuth', async () => {
    routeQuery.resume = 'oauth'
    clerkState.signIn.value.status = 'needs_first_factor'
    clerkState.signIn.value.supportedFirstFactors = [{ strategy: 'password' }]
    clerkState.signIn.value.attemptFirstFactor.mockResolvedValue({
      status: 'complete',
      createdSessionId: 'sess_oauth',
    })

    const wrapper = mount(SignInView, {
      global: { stubs: ['RouterLink'] },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Enter your password to continue signing in.')
    expect(wrapper.find('input[autocomplete="username"]').exists()).toBe(false)
    await wrapper.find('input[autocomplete="current-password"]').setValue('secret-pass')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(clerkState.signIn.value.create).not.toHaveBeenCalled()
    expect(clerkState.signIn.value.attemptFirstFactor).toHaveBeenCalledWith({
      strategy: 'password',
      password: 'secret-pass',
    })
  })

  it('keeps OAuth password continuation active after an incorrect password', async () => {
    routeQuery.resume = 'oauth'
    clerkState.signIn.value.status = 'needs_first_factor'
    clerkState.signIn.value.supportedFirstFactors = [{ strategy: 'password' }]
    clerkState.signIn.value.attemptFirstFactor
      .mockRejectedValueOnce(new Error('Incorrect password'))
      .mockResolvedValueOnce({ status: 'complete', createdSessionId: 'sess_oauth' })

    const wrapper = mount(SignInView, {
      global: { stubs: ['RouterLink'] },
    })
    await flushPromises()

    const passwordInput = wrapper.find('input[autocomplete="current-password"]')
    await passwordInput.setValue('wrong-pass')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('Incorrect password')
    expect(wrapper.find('input[autocomplete="username"]').exists()).toBe(false)

    await passwordInput.setValue('correct-pass')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(clerkState.signIn.value.attemptFirstFactor).toHaveBeenCalledTimes(2)
    expect(clerkState.signIn.value.create).not.toHaveBeenCalled()
  })

  it('resumes an OAuth sign-in that needs client trust code verification', async () => {
    routeQuery.resume = 'oauth'
    clerkState.signIn.value.status = 'needs_client_trust'
    clerkState.signIn.value.supportedSecondFactors = [{
      strategy: 'email_code',
      emailAddressId: 'idn_email',
      safeIdentifier: 'a***@example.com',
    }]

    const wrapper = mount(SignInView, {
      global: { stubs: ['RouterLink'] },
    })
    await flushPromises()

    expect(clerkState.signIn.value.create).not.toHaveBeenCalled()
    expect(clerkState.signIn.value.prepareSecondFactor).toHaveBeenCalledWith({
      strategy: 'email_code',
      emailAddressId: 'idn_email',
    })
    expect(wrapper.text()).toContain('This device needs one more verification.')
    expect(wrapper.text()).toContain('a***@example.com')
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
