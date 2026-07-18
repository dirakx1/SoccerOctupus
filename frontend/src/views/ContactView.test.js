import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import ContactView from './ContactView.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const RouterLinkStub = {
  props: { to: { type: [String, Object], required: true } },
  template: '<a :href="typeof to === \'string\' ? to : to.path"><slot /></a>',
}

function mountContact() {
  return mount(ContactView, {
    global: {
      plugins: [i18n],
      stubs: { RouterLink: RouterLinkStub },
    },
  })
}

describe('ContactView', () => {
  beforeEach(() => {
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
  })

  it('renders the existing support mail link and Home return in an accessible Atlas structure', () => {
    const wrapper = mountContact()

    expect(wrapper.find('main[aria-labelledby="contact-title"]').exists()).toBe(true)
    expect(wrapper.find('section[aria-labelledby="contact-support-title"]').exists()).toBe(true)
    expect(wrapper.find('a[href="mailto:support@socceroctupus.co"]').text()).toBe('support@socceroctupus.co')
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toBe('/')
    expect(wrapper.text()).toContain('Contact SoccerOctopus')
  })

  it('renders Spanish support content without changing the mail or navigation contract', () => {
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const wrapper = mountContact()

    expect(wrapper.text()).toContain('Contacta con SoccerOctopus')
    expect(wrapper.text()).toContain('Escribenos con los detalles relevantes')
    expect(wrapper.find('a[href="mailto:support@socceroctupus.co"]').exists()).toBe(true)
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toBe('/')
  })
})
