import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import PredictView from './PredictView.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const routeState = {
  params: { locale: 'en', competitionEditionSlug: 'world-cup-2026' },
  fullPath: '/en/competitions/world-cup-2026/predict',
}
const billingState = vi.hoisted(() => ({
  actionLoading: { value: false, __v_isRef: true },
  openBillingRecovery: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRoute: () => routeState,
}))

vi.mock('../lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn() },
}))

vi.mock('../composables/useBillingStatus', () => ({
  useBillingStatus: () => billingState,
}))

import { api } from '../lib/api'

const teams = [
  { name: 'Germany', elo: 1880, rank: 7 },
  { name: 'Brazil', elo: 1950, rank: 4 },
  { name: 'Japan', elo: 1780, rank: 15 },
]

const result = {
  prediction_id: 'pred_123',
  home_team: 'Brazil',
  away_team: 'Germany',
  stage: 'quarter_final',
  group: null,
  home_win_prob: 0.624,
  draw_prob: 0.211,
  away_win_prob: 0.165,
  predicted_home_goals: 2.08,
  predicted_away_goals: 1.16,
  most_likely_score: '2-1',
  score_probabilities: [
    { score: '2-1', probability: 0.148 },
    { score: '1-1', probability: 0.121 },
  ],
  outcome: 'home_win',
  went_to_penalties: false,
  overall_confidence: 0.784,
  swarm_consensus: 'Backend-generated English narrative stays verbatim.',
  key_factors: ['Brazil controls midfield', 'Germany presses high'],
  agent_predictions: [
    { agent: 'Statistical Analysis Agent', home_win_prob: 0.7, draw_prob: 0.18, away_win_prob: 0.12, predicted_score: '2-1', confidence: 0.84, reasoning: 'Statistical evidence.' },
    { agent: 'Video Intelligence Agent', home_win_prob: 0.6, draw_prob: 0.22, away_win_prob: 0.18, predicted_score: '2-1', confidence: 0.7, reasoning: 'Video evidence.' },
    { agent: 'Recent Form Agent', home_win_prob: 0.25, draw_prob: 0.25, away_win_prob: 0.5, predicted_score: '1-2', confidence: 0.66, reasoning: 'Form evidence.' },
    { agent: 'Tactical Analysis Agent', home_win_prob: 0.55, draw_prob: 0.25, away_win_prob: 0.2, predicted_score: '2-1', confidence: 0.75, reasoning: 'Tactical evidence.' },
  ],
}

const RouterLinkStub = {
  props: ['to'],
  template: '<a :href="to"><slot /></a>',
}

function mountPredict() {
  return mount(PredictView, {
    global: {
      plugins: [i18n],
      stubs: { RouterLink: RouterLinkStub },
    },
  })
}

async function selectMatch(wrapper, stage = 'quarter_final') {
  await wrapper.find('[data-testid="home-team"]').setValue('Brazil')
  await wrapper.find('[data-testid="away-team"]').setValue('Germany')
  await wrapper.find('[data-testid="match-stage"]').setValue(stage)
}

describe('PredictView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routeState.params.locale = 'en'
    routeState.fullPath = '/en/competitions/world-cup-2026/predict'
    billingState.actionLoading.value = false
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
    api.get.mockResolvedValue({ data: { teams } })
    api.post.mockResolvedValue({ data: result })
  })

  it('loads and sorts teams by descending ELO with localized canonical context', async () => {
    routeState.params.locale = 'es'
    routeState.fullPath = '/es/competitions/world-cup-2026/predict'
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const wrapper = mountPredict()
    await flushPromises()

    expect(api.get).toHaveBeenCalledWith('/api/predictions/teams')
    expect(wrapper.text()).toContain('Lee el partido antes de que empiece.')
    const teamOptions = wrapper.find('[data-testid="home-team"]').findAll('option').slice(1)
    expect(teamOptions.map((option) => option.text())).toEqual([
      'Brazil (ELO 1.950)',
      'Germany (ELO 1.880)',
      'Japan (ELO 1.780)',
    ])
  })

  it('shows stable loading and empty states for the team feed', async () => {
    api.get.mockImplementation(() => new Promise(() => {}))
    const loadingWrapper = mountPredict()
    await loadingWrapper.vm.$nextTick()
    expect(loadingWrapper.find('[data-testid="team-loading"]').attributes('aria-busy')).toBe('true')
    loadingWrapper.unmount()

    api.get.mockResolvedValue({ data: { teams: [] } })
    const emptyWrapper = mountPredict()
    await flushPromises()
    expect(emptyWrapper.text()).toContain('No teams are available.')
  })

  it('shows team-load errors and retries the exact endpoint', async () => {
    api.get.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ data: { teams } })
    const wrapper = mountPredict()
    await flushPromises()
    expect(wrapper.text()).toContain("We couldn't load the team list.")

    await wrapper.find('[data-testid="retry-teams"]').trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenCalledTimes(2)
    expect(wrapper.find('[data-testid="home-team"]').attributes('disabled')).toBeUndefined()
  })

  it('requires two different teams and posts the exact backend payload', async () => {
    const wrapper = mountPredict()
    await flushPromises()
    const runButton = wrapper.find('[data-testid="run-prediction"]')
    expect(runButton.attributes('disabled')).toBeDefined()

    await wrapper.find('[data-testid="home-team"]').setValue('Brazil')
    await wrapper.find('[data-testid="away-team"]').setValue('Brazil')
    expect(wrapper.text()).toContain('Home and away teams must be different.')
    expect(runButton.attributes('disabled')).toBeDefined()

    await wrapper.find('[data-testid="away-team"]').setValue('Germany')
    await wrapper.find('[data-testid="match-stage"]').setValue('quarter_final')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/api/predictions/match', {
      home_team: 'Brazil',
      away_team: 'Germany',
      stage: 'quarter_final',
    })
  })

  it('shows a long-running state and a recoverable match error', async () => {
    let rejectPrediction
    api.post.mockImplementation(() => new Promise((resolve, reject) => { rejectPrediction = reject }))
    const wrapper = mountPredict()
    await flushPromises()
    await selectMatch(wrapper)
    await wrapper.find('form').trigger('submit.prevent')
    expect(wrapper.find('[data-testid="prediction-loading"]').attributes('aria-busy')).toBe('true')

    rejectPrediction(new Error('prediction timeout'))
    await flushPromises()
    expect(wrapper.text()).toContain("We couldn't run this prediction.")
    expect(wrapper.text()).toContain('prediction timeout')
  })

  it('preserves subscription and billing-attention recovery branches', async () => {
    api.post.mockRejectedValueOnce({
      response: { data: { error: 'Active subscription required', code: 'subscription_required' } },
    })
    const subscriptionWrapper = mountPredict()
    await flushPromises()
    await selectMatch(subscriptionWrapper)
    await subscriptionWrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(subscriptionWrapper.find('.billing-plans-link').attributes('href')).toBe('/pricing')
    subscriptionWrapper.unmount()

    const health = {
      state: 'payment_required', severity: 'danger', requires_attention: true,
      action: 'update_payment_method', action_label: 'Pay invoice',
      message: 'Payment is overdue. Pay the invoice to restore access.',
    }
    api.post.mockRejectedValueOnce({
      response: { data: { error: health.message, code: 'billing_payment_required', billing_health: health } },
    })
    const billingWrapper = mountPredict()
    await flushPromises()
    await selectMatch(billingWrapper)
    await billingWrapper.find('form').trigger('submit.prevent')
    await flushPromises()
    await billingWrapper.find('.status-action').trigger('click')
    expect(billingState.openBillingRecovery).toHaveBeenCalledWith(routeState.fullPath, health)
  })

  it('keeps feature-limit errors linked to pricing', async () => {
    api.post.mockRejectedValueOnce({
      response: {
        data: {
          error: 'Match predictions limit reached',
          code: 'feature_limit_reached',
          remaining_count: 0,
          plans_url: '/pricing',
        },
      },
    })
    const wrapper = mountPredict()
    await flushPromises()
    await selectMatch(wrapper)
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('Match predictions limit reached')
    expect(wrapper.find('.billing-plans-link').attributes('href')).toBe('/pricing')
  })

  it('renders every result field, agreement, and backend narrative verbatim', async () => {
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const wrapper = mountPredict()
    await flushPromises()
    await selectMatch(wrapper)
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('2-1')
    expect(text).toContain('62,4 %')
    expect(text).toContain('2,08')
    expect(text).toContain('14,8 %')
    expect(text).toContain('78,4 %')
    expect(text).toContain('3 de 4 agentes favorecen victoria local')
    expect(text).toContain('Backend-generated English narrative stays verbatim.')
    expect(text).toContain('Brazil controls midfield')
    expect(text).toContain('Tactical evidence.')
  })
})
