import { config, mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import SSOCallbackView from './SSOCallbackView.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const postAuthState = vi.hoisted(() => ({ peek: '/groups' }))
const routerLinkStub = {
  name: 'RouterLink',
  props: ['to'],
  template: '<a><slot /></a>',
}

const callbackComponent = vi.hoisted(() => ({
  name: 'AuthenticateWithRedirectCallback',
  props: [
    'continueSignUpUrl',
    'firstFactorUrl',
    'secondFactorUrl',
    'signInFallbackRedirectUrl',
    'signInForceRedirectUrl',
    'signInUrl',
    'signUpFallbackRedirectUrl',
    'signUpForceRedirectUrl',
    'signUpUrl',
  ],
  template: '<div data-testid="oauth-callback" />',
}))

vi.mock('@clerk/vue', () => ({
  AuthenticateWithRedirectCallback: callbackComponent,
}))

vi.mock('../lib/postAuthRedirect', () => ({
  peekPostAuthRedirect: vi.fn(() => postAuthState.peek),
}))

describe('SSOCallbackView', () => {
  beforeEach(() => {
    config.global.plugins = [i18n]
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
    vi.clearAllMocks()
    postAuthState.peek = '/groups'
  })

  it('preserves every Clerk callback handoff and the exact stored destination', () => {
    postAuthState.peek = '/es/competitions/world-cup-2026/markets?from=oauth#questions'
    const wrapper = mount(SSOCallbackView, { global: { stubs: { RouterLink: routerLinkStub } } })
    const callback = wrapper.findComponent(callbackComponent)

    expect(callback.props()).toMatchObject({
      firstFactorUrl: '/sign-in?resume=oauth',
      secondFactorUrl: '/sign-in?resume=oauth',
      signInUrl: '/sign-in',
      signInForceRedirectUrl: postAuthState.peek,
      signInFallbackRedirectUrl: postAuthState.peek,
      signUpUrl: '/sign-up',
      signUpForceRedirectUrl: postAuthState.peek,
      signUpFallbackRedirectUrl: postAuthState.peek,
      continueSignUpUrl: '/complete-username',
    })
  })

  it('renders the English pending and recovery states', () => {
    const wrapper = mount(SSOCallbackView, { global: { stubs: { RouterLink: routerLinkStub } } })

    expect(wrapper.get('[role="status"]').text()).toContain('Completing sign-in')
    expect(wrapper.text()).toContain('Taking longer than expected?')
    expect(wrapper.findAllComponents({ name: 'RouterLink' }).map((link) => link.props('to'))).toEqual(['/sign-in', '/sign-up'])
  })

  it('renders the Spanish pending and recovery states without changing callback URLs', () => {
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const wrapper = mount(SSOCallbackView, { global: { stubs: { RouterLink: routerLinkStub } } })

    expect(wrapper.get('[role="status"]').text()).toContain('Completando el inicio de sesión')
    expect(wrapper.text()).toContain('¿Está tardando más de lo esperado?')
    expect(wrapper.findComponent(callbackComponent).props('firstFactorUrl')).toBe('/sign-in?resume=oauth')
  })

  it('falls back to root when no stored destination exists', () => {
    postAuthState.peek = null
    const callback = mount(SSOCallbackView, { global: { stubs: { RouterLink: routerLinkStub } } }).findComponent(callbackComponent)

    expect(callback.props()).toMatchObject({
      signInForceRedirectUrl: '/',
      signInFallbackRedirectUrl: '/',
      signUpForceRedirectUrl: '/',
      signUpFallbackRedirectUrl: '/',
    })
  })

  it('mounts Clerk immediately with readable fallback copy when locale messages are unavailable', () => {
    config.global.plugins = []
    const emptyI18n = createI18n({ legacy: false, locale: 'es', fallbackLocale: false, missingWarn: false, messages: { es: {} } })
    const wrapper = mount(SSOCallbackView, {
      global: { plugins: [emptyI18n], stubs: { RouterLink: routerLinkStub } },
    })

    expect(wrapper.findComponent(callbackComponent).exists()).toBe(true)
    expect(wrapper.get('[role="status"]').text()).toContain('Completing authentication')
  })
})
