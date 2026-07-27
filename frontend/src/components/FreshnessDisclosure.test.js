import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { describe, expect, it } from 'vitest'

import FreshnessDisclosure from './FreshnessDisclosure.vue'
import en from '../i18n/locales/en/league.json'
import es from '../i18n/locales/es/league.json'

function render(status, locale = 'en', retryable = false) {
  return mount(FreshnessDisclosure, {
    props: { freshness: { status, retryable, source: 'ESPN' } },
    global: { plugins: [createI18n({ legacy: false, locale, messages: { en: { league: en }, es: { league: es } } })] },
  })
}

describe('FreshnessDisclosure', () => {
  it.each(['refreshing', 'stale', 'hard_stale'])('discloses the %s state', (status) => {
    expect(render(status).get(`[data-testid="freshness-${status}"]`).text()).toBeTruthy()
  })

  it('localizes the warning and emits retry', async () => {
    const wrapper = render('hard_stale', 'es', true)
    expect(wrapper.text()).toContain('demasiado antiguos')
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })
})
