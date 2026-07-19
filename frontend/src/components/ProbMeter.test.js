import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import ProbMeter from './ProbMeter.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const baseProps = {
  homeTeam: 'Brazil',
  awayTeam: 'Germany',
  homePct: 0.624,
  drawPct: 0.211,
  awayPct: 0.165,
  outcome: 'home_win',
  agentCount: 4,
  agentSeries: [
    { home: 0.58, draw: 0.24, away: 0.18 },
    { home: 0.624, draw: 0.211, away: 0.165 },
  ],
}

function mountMeter(props = {}) {
  return mount(ProbMeter, {
    props: { ...baseProps, ...props },
    global: { plugins: [i18n] },
  })
}

describe('ProbMeter', () => {
  beforeEach(() => {
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
  })

  it('renders the existing probability inputs with an accessible localized summary', () => {
    const wrapper = mountMeter()

    expect(wrapper.attributes('role')).toBe('img')
    expect(wrapper.attributes('aria-label')).toContain('Brazil 62.4%')
    expect(wrapper.attributes('aria-label')).toContain('draw 21.1%')
    expect(wrapper.text()).toContain('Swarm convergence · 4 agents')
    expect(wrapper.findAll('polyline')).toHaveLength(3)
  })

  it('formats frontend-owned labels and percentages for Spanish', () => {
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const wrapper = mountMeter()

    expect(wrapper.text()).toContain('Empate')
    expect(wrapper.text()).toContain('Convergencia del enjambre · 4 agentes')
    expect(wrapper.text()).toContain('62,4 %')
  })
})
