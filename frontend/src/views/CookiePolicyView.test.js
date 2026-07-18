import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import CookiePolicyView from './CookiePolicyView.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const RouterLinkStub = {
  props: { to: { type: [String, Object], required: true } },
  template: '<a :href="typeof to === \'string\' ? to : to.path"><slot /></a>',
}

function mountCookiePolicy() {
  return mount(CookiePolicyView, {
    global: {
      plugins: [i18n],
      stubs: { RouterLink: RouterLinkStub },
    },
  })
}

describe('CookiePolicyView', () => {
  beforeEach(() => {
    window.localStorage.clear()
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
  })

  it('renders the complete cookie inventory and consent reset in a semantic Atlas document', () => {
    const wrapper = mountCookiePolicy()

    expect(wrapper.find('main[aria-labelledby="cookie-policy-title"]').exists()).toBe(true)
    expect(wrapper.find('article').exists()).toBe(true)
    expect(wrapper.findAll('article section')).toHaveLength(6)
    expect(wrapper.findAll('tbody tr')).toHaveLength(3)
    expect(wrapper.text()).toContain('__session, __client*')
    expect(wrapper.text()).toContain('so_cookie_consent')
    expect(wrapper.text()).toContain('Only set if you consent to analytics cookies.')
    expect(wrapper.find('button').text()).toBe('Reset cookie preferences')
    expect(wrapper.find('a[href="https://support.google.com/chrome/answer/95647"]').attributes('rel')).toBe('noopener noreferrer')
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toBe('/legal')
  })

  it('renders Spanish policy content without changing the consent storage key contract', () => {
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const wrapper = mountCookiePolicy()

    expect(wrapper.text()).toContain('Política de cookies')
    expect(wrapper.text()).toContain('Cookies que usamos')
    expect(wrapper.text()).toContain('so_cookie_consent')
    expect(wrapper.text()).toContain('Solo se establece si aceptas las cookies analíticas.')
    expect(wrapper.find('button').text()).toBe('Restablecer preferencias de cookies')
    expect(wrapper.findAll('a[href^="https://"]')).toHaveLength(4)
  })
})
