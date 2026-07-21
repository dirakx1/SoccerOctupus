import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import BillingStatusNotice from './BillingStatusNotice.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const paymentHealth = {
  state: 'payment_required',
  severity: 'danger',
  requires_attention: true,
  action: 'update_payment_method',
  action_label: 'Pay invoice',
  message: 'Payment is overdue. Pay the invoice to restore access.',
}

function mountNotice(props = {}) {
  return mount(BillingStatusNotice, {
    props: { health: paymentHealth, ...props },
    global: { plugins: [i18n] },
  })
}

describe('BillingStatusNotice', () => {
  beforeEach(() => {
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
  })

  it('preserves visibility and action behavior for billing attention states', async () => {
    const wrapper = mountNotice()

    expect(wrapper.attributes('role')).toBe('status')
    expect(wrapper.text()).toContain('Payment is overdue')
    expect(wrapper.find('button').text()).toContain('Pay invoice')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('action')).toHaveLength(1)
  })

  it('localizes known billing state and action copy while preserving backend fallback messages', () => {
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const localized = mountNotice()
    expect(localized.text()).toContain('El pago está vencido')
    expect(localized.text()).toContain('Pagar factura')

    const fallback = mountNotice({
      health: { severity: 'info', message: 'Custom billing notice' },
    })
    expect(fallback.text()).toContain('Custom billing notice')
  })

  it('keeps loading actions disabled and accessibly labeled', () => {
    const wrapper = mountNotice({ loading: true })

    expect(wrapper.find('button').attributes('disabled')).toBeDefined()
    expect(wrapper.find('button').attributes('aria-label')).toBe('Opening billing')
  })
})
