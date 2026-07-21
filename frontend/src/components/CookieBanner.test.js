import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import CookieBanner from './CookieBanner.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const RouterLinkStub = {
  props: ['to'],
  template: '<a :href="to"><slot /></a>',
}

const originalLocalStorageDescriptor = Object.getOwnPropertyDescriptor(window, 'localStorage')

function mountBanner() {
  return mount(CookieBanner, {
    global: {
      plugins: [i18n],
      stubs: { RouterLink: RouterLinkStub },
    },
  })
}

describe('CookieBanner', () => {
  beforeEach(() => {
    if (originalLocalStorageDescriptor) {
      Object.defineProperty(window, 'localStorage', originalLocalStorageDescriptor)
    }
    window.localStorage.clear()
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
  })

  afterEach(() => {
    if (originalLocalStorageDescriptor) {
      Object.defineProperty(window, 'localStorage', originalLocalStorageDescriptor)
    }
  })

  it('shows localized consent controls until a choice is stored', async () => {
    const wrapper = mountBanner()
    await flushPromises()

    const dialog = wrapper.find('[role="dialog"]')
    expect(dialog.exists()).toBe(true)
    expect(dialog.attributes('aria-label')).toBe('Cookie preferences')
    expect(wrapper.text()).toContain('Cookie Policy')
    expect(wrapper.find('a').attributes('href')).toBe('/cookie-policy')
  })

  it('stays hidden when consent is already stored', async () => {
    window.localStorage.setItem('so_cookie_consent', 'necessary')
    const wrapper = mountBanner()
    await flushPromises()

    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it.each([
    ['Necessary only', 'necessary'],
    ['Accept all', 'all'],
  ])('stores %s consent and dismisses the banner', async (label, storedValue) => {
    const wrapper = mountBanner()
    await flushPromises()

    const button = wrapper.findAll('button').find((candidate) => candidate.text() === label)
    await button.trigger('click')

    expect(window.localStorage.getItem('so_cookie_consent')).toBe(storedValue)
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it('remains usable when localStorage is blocked', async () => {
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      get() {
        throw new Error('blocked')
      },
    })

    const wrapper = mountBanner()
    await flushPromises()
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true)

    await wrapper.findAll('button')[0].trigger('click')
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it('renders Spanish copy', async () => {
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const wrapper = mountBanner()
    await flushPromises()

    expect(wrapper.text()).toContain('Usamos cookies esenciales')
    expect(wrapper.text()).toContain('Solo necesarias')
    expect(wrapper.find('[role="dialog"]').attributes('aria-label')).toBe('Preferencias de cookies')
  })
})
