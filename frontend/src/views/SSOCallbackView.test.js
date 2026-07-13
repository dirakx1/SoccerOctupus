import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import SSOCallbackView from './SSOCallbackView.vue'

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
  peekPostAuthRedirect: vi.fn(() => '/groups'),
}))

describe('SSOCallbackView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('routes OAuth sign-in factor requirements to the custom sign-in view', () => {
    const wrapper = mount(SSOCallbackView)
    const callback = wrapper.findComponent(callbackComponent)

    expect(callback.props()).toMatchObject({
      firstFactorUrl: '/sign-in?resume=oauth',
      secondFactorUrl: '/sign-in?resume=oauth',
      signInUrl: '/sign-in',
      signInForceRedirectUrl: '/groups',
      signInFallbackRedirectUrl: '/groups',
      signUpUrl: '/sign-up',
      continueSignUpUrl: '/complete-username',
    })
  })
})
