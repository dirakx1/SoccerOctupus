import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import BillingSuccessView from './BillingSuccessView.vue'

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

    mountView()
    await flushPromises()

    vi.advanceTimersByTime(3500)
    expect(routerReplace).toHaveBeenCalledWith('/profile')
  })
})
