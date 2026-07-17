import { config, flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ForgotPasswordView from './ForgotPasswordView.vue'
import { applyLocale, i18n } from '../i18n/index.js'
const RouterLinkStub = { props: ['to'], template: '<a :data-to="to"><slot /></a>' }

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
    config.global.plugins = [i18n]
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
    vi.clearAllMocks()
    clerkState.signIn.value.create.mockResolvedValue({})
    clerkState.signIn.value.attemptFirstFactor.mockResolvedValue({
      status: 'complete',
      createdSessionId: 'sess_reset',
    })
    clerkState.activateSessionAndHydrateAuth.mockResolvedValue(undefined)
  })

  it('does not reuse a reset code when Clerk activated the session before hydration finished', async () => {
    clerkState.activateSessionAndHydrateAuth.mockResolvedValue({ hydrated: false })
    const wrapper = mount(ForgotPasswordView, {
      global: { stubs: ['RouterLink'] },
    })

    await wrapper.find('input[autocomplete="email"]').setValue('alex@example.com')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    await wrapper.find('input[autocomplete="one-time-code"]').setValue('123456')
    await wrapper.find('input[autocomplete="new-password"]').setValue('longenough')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(clerkState.signIn.value.attemptFirstFactor).toHaveBeenCalledTimes(1)
    expect(routerPush).toHaveBeenCalledWith('/')
    expect(wrapper.text()).not.toContain('Unable to reset')
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

  it('renders the complete recovery flow in Spanish with the sign-in link', async () => {
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const wrapper = mount(ForgotPasswordView, { global: { stubs: { RouterLink: RouterLinkStub } } })
    expect(wrapper.text()).toContain('Restablecer contraseña')
    expect(wrapper.text()).toContain('Correo electrónico')
    expect(wrapper.find('[data-to]').attributes('data-to')).toBe('/sign-in')
    await wrapper.find('input[autocomplete="email"]').setValue('alex@example.com')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(wrapper.text()).toContain('Código de verificación')
    expect(wrapper.text()).toContain('Contraseña nueva')
    expect(wrapper.text()).toContain('Reenviar código')
  })

  it('preserves request, resend, back, loading, and error lifecycle', async () => {
    let rejectRequest
    clerkState.signIn.value.create.mockImplementationOnce(() => new Promise((resolve, reject) => { rejectRequest = reject }))
    const wrapper = mount(ForgotPasswordView, { global: { stubs: ['RouterLink'] } })
    await wrapper.find('input[autocomplete="email"]').setValue('alex@example.com')
    await wrapper.find('form').trigger('submit.prevent')
    expect(wrapper.text()).toContain('Sending code...')
    rejectRequest(new Error('Unknown account'))
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Unknown account')

    clerkState.signIn.value.create.mockResolvedValue({})
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    await wrapper.findAll('.btn-link')[0].trigger('click')
    await flushPromises()
    expect(clerkState.signIn.value.create).toHaveBeenCalledTimes(3)
    await wrapper.findAll('.btn-link')[1].trigger('click')
    expect(wrapper.find('input[autocomplete="email"]').exists()).toBe(true)
  })
})
