import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MarketCard from './MarketCard.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const question = {
  question_id: 'SO-WC26-BRA-GER-WIN', prop_type: 'match_winner', market_type: 'binary',
  question: 'Will Brazil beat Germany?', yes_probability: 0.624, no_probability: 0.376,
  pricing: { kalshi_yes_cents: 62.4, kalshi_no_cents: 37.6, polymarket_yes_usdc: 0.624, polymarket_no_usdc: 0.376 },
  resolution: { date: '2026-07-08', criteria: 'Backend criteria stays exactly as generated.' },
}
const mountCard = (value = question) => mount(MarketCard, { props: { question: value }, global: { plugins: [i18n] } })

describe('MarketCard', () => {
  beforeEach(() => { applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement }); Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: vi.fn().mockResolvedValue() } }) })

  it('renders localized metadata and every contract value with accessible meters', () => {
    const wrapper = mountCard()
    expect(wrapper.text()).toContain('Match winner')
    expect(wrapper.text()).toContain('Will Brazil beat Germany?')
    expect(wrapper.text()).toContain('62.4%')
    expect(wrapper.text()).toContain('62.4¢')
    expect(wrapper.text()).toContain('$0.6240')
    expect(wrapper.text()).toContain('2026-07-08')
    expect(wrapper.text()).toContain('SO-WC26-BRA-GER-WIN')
    expect(wrapper.findAll('[role="meter"]')).toHaveLength(2)
    expect(wrapper.find('[role="meter"]').attributes('aria-valuenow')).toBe('62.4')
  })

  it('falls back safely to an unknown backend prop type', () => {
    expect(mountCard({ ...question, prop_type: 'corner_kicks' }).text()).toContain('corner_kicks')
  })

  it('expands verbatim criteria with aria state', async () => {
    const wrapper = mountCard()
    const button = wrapper.find('.criteria-toggle')
    expect(button.attributes('aria-expanded')).toBe('false')
    await button.trigger('click')
    expect(button.attributes('aria-expanded')).toBe('true')
    expect(wrapper.text()).toContain('Backend criteria stays exactly as generated.')
  })

  it('announces successful and rejected clipboard writes without crashing', async () => {
    const success = mountCard()
    await success.find('.copy-button').trigger('click')
    await Promise.resolve()
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(question.question_id)
    expect(success.text()).toContain('Question ID copied.')

    navigator.clipboard.writeText.mockRejectedValueOnce(new Error('blocked'))
    const failure = mountCard()
    await failure.find('.copy-button').trigger('click')
    await Promise.resolve()
    expect(failure.find('[aria-live="polite"]').text()).toBe('Question ID could not be copied.')
  })
})
