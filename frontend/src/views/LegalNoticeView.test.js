import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import LegalNoticeView from './LegalNoticeView.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const RouterLinkStub = {
  props: { to: { type: [String, Object], required: true } },
  template: '<a :href="typeof to === \'string\' ? to : to.path"><slot /></a>',
}

function mountLegalNotice() {
  return mount(LegalNoticeView, {
    global: {
      plugins: [i18n],
      stubs: { RouterLink: RouterLinkStub },
    },
  })
}

describe('LegalNoticeView', () => {
  beforeEach(() => {
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
  })

  it('renders the complete English notice in a semantic, token-friendly document structure', () => {
    const wrapper = mountLegalNotice()

    expect(wrapper.find('main[aria-labelledby="legal-notice-title"]').exists()).toBe(true)
    expect(wrapper.find('article').exists()).toBe(true)
    expect(wrapper.findAll('article section')).toHaveLength(6)
    expect(wrapper.text()).toContain('Last updated: June 30, 2026')
    expect(wrapper.text()).toContain('Not financial or betting advice')
    expect(wrapper.text()).toContain('not affiliated with, endorsed by, or connected in any form to FIFA')
    expect(wrapper.text()).toContain('You should never bet more than you can afford to lose.')
    expect(wrapper.find('a[href="https://www.begambleaware.org"]').attributes('rel')).toBe('noopener noreferrer')
    expect(wrapper.find('a[href="https://www.ncpgambling.org"]').attributes('target')).toBe('_blank')
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toBe('/')
  })

  it('renders a coherent Spanish notice without losing disclaimer or resource links', () => {
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const wrapper = mountLegalNotice()

    expect(wrapper.text()).toContain('Aviso legal')
    expect(wrapper.text()).toContain('Naturaleza de las predicciones')
    expect(wrapper.text()).toContain('No es asesoramiento financiero ni de apuestas')
    expect(wrapper.text()).toContain('Sin afiliación con FIFA, Kalshi ni Polymarket')
    expect(wrapper.text()).toContain('Nunca deberías apostar más de lo que puedas permitirte perder.')
    expect(wrapper.findAll('article section')).toHaveLength(6)
    expect(wrapper.findAll('a[href^="https://"]')).toHaveLength(2)
  })
})
