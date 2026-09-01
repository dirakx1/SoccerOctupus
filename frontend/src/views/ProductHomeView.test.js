import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import { applyLocale, i18n } from '../i18n/index.js'
import ProductHomeView from './ProductHomeView.vue'

describe('ProductHomeView', () => {
  beforeEach(() => {
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
  })

  it('introduces the product with direct league entry points', () => {
    const wrapper = mount(ProductHomeView, {
      global: { plugins: [i18n], stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })

    expect(wrapper.text()).toContain('Football predictions you can inspect.')
    expect(wrapper.text()).toContain('Premier League 2026–27')
    expect(wrapper.text()).toContain('La Liga 2026–27')
    expect(wrapper.text()).toContain('Bundesliga 2026–27')
    expect(wrapper.text()).not.toContain('Featured upcoming forecast')
    expect(wrapper.text()).not.toContain('A forecast, not a promise.')
  })
})
