import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import CompleteUsernameView from './CompleteUsernameView.vue'

const routerPush = vi.fn()
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
  consumePostAuthRedirect: vi.fn(() => ''),
}))

describe('CompleteUsernameView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clerkState.signUp.value.status = 'missing_requirements'
    clerkState.signUp.value.missingFields = ['username']
    clerkState.signUp.value.username = null
    clerkState.signUp.value.update.mockResolvedValue({
      status: 'complete',
      createdSessionId: 'sess_complete',
    })
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

    expect(wrapper.text()).toContain('No pending username step is available.')
  })
})
