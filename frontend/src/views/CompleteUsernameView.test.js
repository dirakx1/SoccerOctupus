import { config, flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import CompleteUsernameView from './CompleteUsernameView.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const routerPush = vi.fn()
const postAuthState = vi.hoisted(() => ({ consume: '' }))
const clerkState = vi.hoisted(() => ({
  activateSessionAndHydrateAuth: vi.fn(),
  clerk: {},
  isLoaded: { value: true, __v_isRef: true },
  setActive: { value: vi.fn(), __v_isRef: true },
  signUp: {
    value: {
      status: 'missing_requirements',
      missingFields: ['username'],
      username: null,
      createdSessionId: 'sess_pending',
      update: vi.fn(),
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
  consumePostAuthRedirect: vi.fn(() => postAuthState.consume),
}))

describe('CompleteUsernameView', () => {
  beforeEach(() => {
    config.global.plugins = [i18n]
    applyLocale('en',{storage:window.localStorage,documentElement:document.documentElement})
    vi.clearAllMocks()
    postAuthState.consume = ''
    clerkState.signUp.value.status = 'missing_requirements'
    clerkState.signUp.value.missingFields = ['username']
    clerkState.signUp.value.username = null
    clerkState.signUp.value.update.mockResolvedValue({
      status: 'complete',
      createdSessionId: 'sess_complete',
    })
    clerkState.activateSessionAndHydrateAuth.mockResolvedValue(undefined)
  })

  it('does not repeat the username mutation when Clerk activated the session before hydration finished', async () => {
    clerkState.activateSessionAndHydrateAuth.mockResolvedValue({ hydrated: false })
    const wrapper = mount(CompleteUsernameView, {
      global: { stubs: ['RouterLink'] },
    })

    await wrapper.find('input[autocomplete="username"]').setValue('alexmorgan')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(clerkState.signUp.value.update).toHaveBeenCalledTimes(1)
    expect(routerPush).toHaveBeenCalledWith('/')
    expect(wrapper.text()).not.toContain('Unable to save username')
  })

  it('updates the pending Clerk sign-up username and activates the session', async () => {
    const wrapper = mount(CompleteUsernameView, {
      global: { stubs: ['RouterLink'] },
    })

    await wrapper.find('input[autocomplete="username"]').setValue('alexmorgan')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(clerkState.signUp.value.update).toHaveBeenCalledWith({ username: 'alexmorgan' })
    expect(clerkState.activateSessionAndHydrateAuth).toHaveBeenCalledWith({
      clerk: clerkState.clerk,
      setActive: clerkState.setActive.value,
      sessionId: 'sess_complete',
    })
    expect(routerPush).toHaveBeenCalledWith('/')
  })

  it('shows a safe fallback when there is no pending username step', () => {
    clerkState.signUp.value.status = 'complete'
    clerkState.signUp.value.missingFields = []
    const wrapper = mount(CompleteUsernameView, {
      global: { stubs: ['RouterLink'] },
    })

    expect(wrapper.text()).toContain('There is no username step to finish.')
  })

  it('localizes the form and fallback in Spanish', () => {
    applyLocale('es',{storage:window.localStorage,documentElement:document.documentElement})
    const wrapper=mount(CompleteUsernameView,{global:{stubs:['RouterLink']}})
    expect(wrapper.text()).toContain('Elige un nombre de usuario')
    expect(wrapper.text()).toContain('Nombre de usuario')
    wrapper.unmount()
    clerkState.signUp.value.status='complete';clerkState.signUp.value.missingFields=[]
    expect(mount(CompleteUsernameView,{global:{stubs:['RouterLink']}}).text()).toContain('No hay un paso de nombre de usuario que completar.')
  })

  it('preserves loading, errors, and the exact stored return destination', async () => {
    postAuthState.consume='/es/competitions/world-cup-2026/markets?from=oauth#questions'
    let rejectUpdate
    clerkState.signUp.value.update.mockImplementationOnce(()=>new Promise((resolve,reject)=>{rejectUpdate=reject}))
    const wrapper=mount(CompleteUsernameView,{global:{stubs:['RouterLink']}})
    await wrapper.find('input').setValue('alexmorgan');await wrapper.find('form').trigger('submit.prevent')
    expect(wrapper.text()).toContain('Saving...')
    rejectUpdate(new Error('Username taken'));await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Username taken')
    clerkState.signUp.value.update.mockResolvedValue({status:'complete',createdSessionId:'sess_complete'})
    await wrapper.find('form').trigger('submit.prevent');await flushPromises()
    expect(routerPush).toHaveBeenLastCalledWith(postAuthState.consume)
  })
})
