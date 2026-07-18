import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import AboutView from './AboutView.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const RouterLinkStub = {
  props: { to: { type: [String, Object], required: true } },
  template: '<a :href="typeof to === \'string\' ? to : to.path"><slot /></a>',
}

function mountAbout() {
  return mount(AboutView, {
    global: { plugins: [i18n], stubs: { RouterLink: RouterLinkStub } },
  })
}

describe('AboutView', () => {
  beforeEach(() => {
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
  })

  it('preserves product methodology, source, license, and Home-link contracts in an accessible Atlas document', () => {
    const wrapper = mountAbout()

    expect(wrapper.find('main[aria-labelledby="about-title"]').exists()).toBe(true)
    expect(wrapper.find('article').exists()).toBe(true)
    expect(wrapper.text()).toContain('FIFA World Cup 2026')
    expect(wrapper.text()).toContain('Statistical Agent (weight 1.8×)')
    expect(wrapper.find('a[href="https://github.com/dirakx1/SoccerOctupus"]').exists()).toBe(true)
    expect(wrapper.find('a[href="https://www.gnu.org/licenses/agpl-3.0.html"]').exists()).toBe(true)
    expect(wrapper.find('a[href="https://github.com/dirakx1/SoccerOctupus/blob/main/LICENSE"]').exists()).toBe(true)
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toBe('/')
  })

  it('renders Spanish content without changing factual external links or the route contract', () => {
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const wrapper = mountAbout()

    expect(wrapper.text()).toContain('Acerca de SoccerOctopus')
    expect(wrapper.text()).toContain('Copa Mundial de la FIFA 2026')
    expect(wrapper.text()).toContain('Agente estadistico (peso 1.8×)')
    expect(wrapper.find('a[href="https://github.com/dirakx1/SoccerOctupus"]').exists()).toBe(true)
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toBe('/')
  })
})
