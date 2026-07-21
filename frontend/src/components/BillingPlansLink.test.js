import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import BillingPlansLink from './BillingPlansLink.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const RouterLinkStub = {
  props: ['to'],
  template: '<a :href="to"><slot /></a>',
}

function mountLink() {
  return mount(BillingPlansLink, {
    global: { plugins: [i18n], stubs: { RouterLink: RouterLinkStub } },
  })
}

describe('BillingPlansLink', () => {
  beforeEach(() => {
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
  })

  it('keeps the pricing route and localizes its label', () => {
    const wrapper = mountLink()
    expect(wrapper.find('a').attributes('href')).toBe('/pricing')
    expect(wrapper.text()).toBe('View pricing')

    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    expect(mountLink().text()).toBe('Ver precios')
  })
})
