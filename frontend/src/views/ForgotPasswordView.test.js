import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ForgotPasswordView from './ForgotPasswordView.vue'

const routerPush = vi.fn()
const clerkState = vi.hoisted(() => ({
  activateSessionAndHydrateAuth: vi.fn(),
  clerk: {},
  isLoaded: { value: true, __v_isRef: true },
  setActive: { value: vi.fn(), __v_isRef: true },
  signIn: {
    value: {
      create: vi.fn(),
      attemptFirstFactor: vi.fn(),
      validatePassword: vi.fn(),
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

describe('ForgotPasswordView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clerkState.signIn.value.create.mockResolvedValue({})
    clerkState.signIn.value.attemptFirstFactor.mockResolvedValue({
      status: 'complete',
      createdSessionId: 'sess_reset',
    })
  })

  it('renders password policy on reset and submits the new password to Clerk', async () => {
    const wrapper = mount(ForgotPasswordView, {
      global: { stubs: ['RouterLink'] },
    })

    await wrapper.find('input[autocomplete="email"]').setValue('alex@example.com')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('Password requirements')

    await wrapper.find('input[autocomplete="one-time-code"]').setValue('123456')
    await wrapper.find('input[autocomplete="new-password"]').setValue('longenough')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(clerkState.signIn.value.attemptFirstFactor).toHaveBeenCalledWith({
      strategy: 'reset_password_email_code',
      code: '123456',
      password: 'longenough',
    })
    expect(clerkState.activateSessionAndHydrateAuth).toHaveBeenCalled()
  })
})
