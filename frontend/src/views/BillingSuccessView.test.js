import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import BillingSuccessView from './BillingSuccessView.vue'
import { i18n } from '../i18n'

const routerReplace = vi.fn()
const routeQuery = vi.hoisted(() => ({ value: { session_id: 'cs_123' } }))

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: routeQuery.value }),
  useRouter: () => ({ replace: routerReplace }),
}))

vi.mock('../lib/billing', () => ({
  getCheckoutSession: vi.fn(),
}))

import { getCheckoutSession } from '../lib/billing'

function mountView() {
  return mount(BillingSuccessView, {
    global: {
      plugins: [i18n],
      stubs: {
        RouterLink: true,
      },
    },
  })
}

describe('BillingSuccessView', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    i18n.global.locale.value = 'en'
    routeQuery.value = { session_id: 'cs_123' }
    getCheckoutSession.mockResolvedValue({ data: {} })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('reconciles the checkout session before redirecting to profile', async () => {
    mountView()
    await flushPromises()

    expect(getCheckoutSession).toHaveBeenCalledWith('cs_123')

    vi.advanceTimersByTime(3500)
    expect(routerReplace).toHaveBeenCalledWith('/profile')
  })

  it('still redirects when Stripe reconciliation fails', async () => {
    getCheckoutSession.mockRejectedValue(new Error('not ready'))

    const wrapper = mountView()
    await flushPromises()

    vi.advanceTimersByTime(3500)
    expect(routerReplace).toHaveBeenCalledWith('/profile')
    expect(wrapper.text()).toContain('We are waiting for the billing update')
  })

  it('keeps Stripe source detail and lets the user retry without cancelling the return', async () => {
    getCheckoutSession
      .mockRejectedValueOnce({ response: { data: { error: 'Checkout session not found' } } })
      .mockResolvedValueOnce({ data: {} })

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Checkout session not found')
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(getCheckoutSession).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Your account is up to date')
    vi.advanceTimersByTime(3500)
    expect(routerReplace).toHaveBeenCalledWith('/profile')
  })

  it('shows a localized missing-session state without calling the verification endpoint', async () => {
    routeQuery.value = {}
    i18n.global.locale.value = 'es'

    const wrapper = mountView()
    await flushPromises()

    expect(getCheckoutSession).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Este enlace de retorno no incluye una sesión de compra.')
    expect(wrapper.text()).toContain('Estamos esperando la actualización de facturación')
  })
})
