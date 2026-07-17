import { config, flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import SignInView from './SignInView.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const routerPush = vi.fn()
const routeQuery = vi.hoisted(() => ({}))
const postAuthState = vi.hoisted(() => ({ consume: '', peek: '' }))
const RouterLinkStub = { props: ['to'], template: '<a :data-to="to"><slot /></a>' }
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
  consumePostAuthRedirect: vi.fn(() => postAuthState.consume),
  peekPostAuthRedirect: vi.fn(() => postAuthState.peek),
}))

describe('SignInView', () => {
  beforeEach(() => {
    config.global.plugins = [i18n]
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
    vi.clearAllMocks()
    Object.keys(routeQuery).forEach((key) => delete routeQuery[key])
    postAuthState.consume = ''
    postAuthState.peek = ''
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

  it('renders localized Atlas copy, providers, fields, and account links in Spanish', () => {
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const wrapper = mount(SignInView, { global: { stubs: { RouterLink: RouterLinkStub } } })

    expect(wrapper.text()).toContain('Acceso seguro')
    expect(wrapper.text()).toContain('Iniciar sesión')
    expect(wrapper.text()).toContain('Continuar con Google')
    expect(wrapper.text()).toContain('Continuar con X')
    expect(wrapper.text()).toContain('Correo o nombre de usuario')
    expect(wrapper.text()).toContain('¿Has olvidado tu contraseña?')
    expect(wrapper.text()).toContain('Crear una cuenta')
    expect(wrapper.find('input[autocomplete="username"]').attributes('placeholder')).toBe('Correo electrónico o usuario')
    expect(wrapper.findAll('[data-to]').map((link) => link.attributes('data-to'))).toEqual(['/forgot-password', '/sign-up'])
  })

  it('keeps stable loading and error feedback for credential sign-in', async () => {
    let rejectSignIn
    clerkState.signIn.value.create.mockImplementation(() => new Promise((resolve, reject) => { rejectSignIn = reject }))
    const wrapper = mount(SignInView, { global: { stubs: ['RouterLink'] } })
    await wrapper.find('input[autocomplete="username"]').setValue('alexmorgan')
    await wrapper.find('input[autocomplete="current-password"]').setValue('secret-pass')
    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.text()).toContain('Signing in...')
    expect(wrapper.find('form').attributes('aria-busy')).toBe('true')
    expect(wrapper.find('.btn-primary').attributes('disabled')).toBeDefined()
    rejectSignIn(new Error('Incorrect password'))
    await flushPromises()
    expect(wrapper.find('.error-box').text()).toContain('Incorrect password')
    expect(wrapper.find('.error-box').attributes('role')).toBe('alert')
    expect(wrapper.find('.btn-primary').attributes('disabled')).toBeUndefined()
  })

  it('preserves the canonical localized return path for password and OAuth sign-in', async () => {
    const destination = '/es/competitions/world-cup-2026/markets?source=nav#questions'
    postAuthState.consume = destination
    postAuthState.peek = destination
    const wrapper = mount(SignInView, { global: { stubs: ['RouterLink'] } })
    await wrapper.find('input[autocomplete="username"]').setValue('alexmorgan')
    await wrapper.find('input[autocomplete="current-password"]').setValue('secret-pass')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(routerPush).toHaveBeenLastCalledWith(destination)

    await wrapper.find('button[data-strategy="oauth_google"]').trigger('click')
    await flushPromises()
    expect(clerkState.signIn.value.authenticateWithRedirect).toHaveBeenLastCalledWith({
      strategy: 'oauth_google',
      redirectUrl: '/sso-callback',
      redirectUrlComplete: destination,
    })
  })
})
