import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import TournamentView from './TournamentView.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const routeState = {
  params: { locale: 'en', competitionEditionSlug: 'world-cup-2026' },
  fullPath: '/en/competitions/world-cup-2026/bracket',
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

const liveResults = {
  total: 2,
  standings: {
    B: [
      { team: 'Japan', played: 2, won: 1, drawn: 1, lost: 0, gf: 4, ga: 2, gd: 2, points: 4 },
      { team: 'Spain', played: 2, won: 1, drawn: 0, lost: 1, gf: 3, ga: 3, gd: 0, points: 3 },
    ],
    A: [
      { team: 'Mexico', played: 1, won: 1, drawn: 0, lost: 0, gf: 2, ga: 1, gd: 1, points: 3 },
    ],
  },
  matches: [
    { group: 'A', home: 'Mexico', away: 'Canada', home_goals: 2, away_goals: 1, date: '2026-06-11' },
    { group: 'B', home: 'Japan', away: 'Spain', home_goals: 2, away_goals: 2, date: '2026-06-12' },
  ],
}

const predictedMatch = (stage, id, home, away, score = '2-1') => ({
  prediction_id: id,
  stage,
  home_team: home,
  away_team: away,
  most_likely_score: score,
  outcome: 'home_win',
  is_actual: false,
  home_win_prob: 0.624,
  draw_prob: 0.2,
  away_win_prob: 0.176,
})

const simulationResult = {
  champion: 'Argentina',
  runner_up: 'Brazil',
  third_place: 'Morocco',
  champion_probability: 0.624,
  knockout_matches: [
    predictedMatch('final', 'pred-final', 'Argentina', 'Brazil'),
    predictedMatch('semi_final', 'pred-semi', 'Argentina', 'France', '1-0'),
    {
      ...predictedMatch('round_of_32', 'actual-r32', 'Mexico', 'Japan', '1-0'),
      is_actual: true,
      home_win_prob: 1,
      draw_prob: 0,
      away_win_prob: 0,
    },
    predictedMatch('third_place', 'pred-third', 'Morocco', 'France', '2-0'),
    predictedMatch('quarter_final', 'pred-quarter', 'Argentina', 'Germany', '3-2'),
    predictedMatch('round_of_16', 'pred-r16', 'Argentina', 'Spain', '2-1'),
  ],
}

const RouterLinkStub = {
  props: ['to'],
  template: '<a :href="to"><slot /></a>',
}

function mountTournament() {
  return mount(TournamentView, {
    global: {
      plugins: [i18n],
      stubs: { RouterLink: RouterLinkStub },
    },
  })
}

describe('TournamentView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routeState.params.locale = 'en'
    routeState.fullPath = '/en/competitions/world-cup-2026/bracket'
    billingState.actionLoading.value = false
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
    api.get.mockResolvedValue({ data: liveResults })
    api.post.mockResolvedValue({ data: simulationResult })
  })

  it('loads exact live results and preserves response order and fields without inferring qualification', async () => {
    const wrapper = mountTournament()
    await flushPromises()

    expect(api.get).toHaveBeenCalledWith('/api/predictions/live-results')
    expect(wrapper.text()).toContain('2 matches played')
    expect(wrapper.text()).toContain('ESPN')

    const groups = wrapper.findAll('[data-testid="live-group"]')
    expect(groups.map((group) => group.attributes('data-group'))).toEqual(['A', 'B'])
    const japanRow = groups[1].findAll('tbody tr')[0]
    expect(japanRow.find('th').text()).toBe('Japan')
    expect(japanRow.findAll('td').map((cell) => cell.text())).toEqual([
      '1', '2', '1', '1', '0', '4', '2', '+2', '4',
    ])

    const matches = wrapper.findAll('[data-testid="live-match"]')
    expect(matches[0].text()).toContain('Mexico')
    expect(matches[0].text()).toContain('Canada')
    expect(matches[0].text()).toContain('Group A')
    expect(matches[0].text()).toContain('2–1')
    expect(matches[0].text()).toContain('2026-06-11')
    expect(wrapper.text()).not.toMatch(/qualified|qualifier/i)
  })

  it('shows stable live loading and empty states', async () => {
    api.get.mockImplementation(() => new Promise(() => {}))
    const loadingWrapper = mountTournament()
    await loadingWrapper.vm.$nextTick()

    expect(loadingWrapper.find('[data-testid="live-loading"]').attributes('aria-busy')).toBe('true')
    expect(loadingWrapper.findAll('.live-skeleton')).toHaveLength(6)
    loadingWrapper.unmount()

    api.get.mockResolvedValue({ data: { total: 0, standings: {}, matches: [] } })
    const emptyWrapper = mountTournament()
    await flushPromises()

    expect(emptyWrapper.text()).toContain('No live tournament data is available yet.')
    expect(emptyWrapper.find('.state-error').exists()).toBe(false)
  })

  it('shows an inline live error and retries the exact endpoint', async () => {
    api.get.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ data: liveResults })
    const wrapper = mountTournament()
    await flushPromises()

    expect(wrapper.find('.state-error').attributes('role')).toBe('alert')
    expect(wrapper.text()).toContain("We couldn't load live tournament results.")

    await wrapper.find('[data-testid="retry-live"]').trigger('click')
    await flushPromises()

    expect(api.get).toHaveBeenCalledTimes(2)
    expect(wrapper.find('.state-error').exists()).toBe(false)
    expect(wrapper.text()).toContain('Mexico')
  })

  it('exposes an accessible tab contract and supports click and arrow-key changes', async () => {
    const wrapper = mountTournament()
    await flushPromises()
    const tabs = wrapper.findAll('[role="tab"]')

    expect(wrapper.find('[role="tablist"]').attributes('aria-label')).toBe('Tournament views')
    expect(tabs[0].attributes('aria-selected')).toBe('true')
    expect(tabs[0].attributes('aria-controls')).toBe('tournament-panel-live')
    expect(tabs[1].attributes('tabindex')).toBe('-1')

    await tabs[1].trigger('click')
    expect(tabs[1].attributes('aria-selected')).toBe('true')
    expect(wrapper.find('#tournament-panel-simulation').isVisible()).toBe(true)

    await tabs[1].trigger('keydown', { key: 'ArrowLeft' })
    expect(tabs[0].attributes('aria-selected')).toBe('true')
    expect(wrapper.find('#tournament-panel-live').isVisible()).toBe(true)
  })

  it('posts the exact simulation payload and renders returned podium and ordered rounds', async () => {
    const wrapper = mountTournament()
    await flushPromises()
    await wrapper.find('#tournament-tab-simulation').trigger('click')

    expect(wrapper.text()).toContain('No simulation has been run.')
    await wrapper.find('[data-testid="swarm-toggle"]').setValue(true)
    await wrapper.find('[data-testid="run-simulation"]').trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/api/predictions/tournament', { use_swarm: true })
    const podium = wrapper.find('[data-testid="tournament-podium"]')
    expect(podium.text()).toContain('Argentina')
    expect(podium.text()).toContain('Brazil')
    expect(podium.text()).toContain('Morocco')
    expect(podium.find('[data-place="champion"]').text()).toContain('62.4%')
    expect(podium.find('[data-place="runner-up"]').text()).not.toContain('%')
    expect(podium.find('[data-place="third-place"]').text()).not.toContain('%')

    const rounds = wrapper.findAll('[data-testid="bracket-round"]')
    expect(rounds.map((round) => round.attributes('data-stage'))).toEqual([
      'round_of_32', 'round_of_16', 'quarter_final', 'semi_final', 'third_place', 'final',
    ])

    const officialMatch = wrapper.find('[data-match-id="actual-r32"]')
    expect(officialMatch.text()).toContain('Official')
    expect(officialMatch.text()).toContain('Final result')
    expect(officialMatch.text()).not.toContain('%')

    const predictedFinal = wrapper.find('[data-match-id="pred-final"]')
    expect(predictedFinal.text()).toContain('Predicted')
    expect(predictedFinal.text()).toContain('H 62.4% / D 20.0% / A 17.6%')
    expect(predictedFinal.text()).toContain('Winner')
  })

  it('shows a stable long-running state and a recoverable simulation error', async () => {
    let rejectSimulation
    api.post.mockImplementation(() => new Promise((resolve, reject) => { rejectSimulation = reject }))
    const wrapper = mountTournament()
    await flushPromises()
    await wrapper.find('#tournament-tab-simulation').trigger('click')
    await wrapper.find('[data-testid="run-simulation"]').trigger('click')

    expect(api.post).toHaveBeenCalledWith('/api/predictions/tournament', { use_swarm: false })
    expect(wrapper.find('[data-testid="simulation-loading"]').attributes('aria-busy')).toBe('true')
    expect(wrapper.text()).toContain('The tournament path is still being calculated.')
    expect(wrapper.find('[data-testid="run-simulation"]').attributes('disabled')).toBeDefined()

    rejectSimulation(new Error('simulation timeout'))
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain("We couldn't run the tournament simulation.")
    expect(wrapper.find('[role="alert"]').text()).toContain('simulation timeout')
  })

  it('preserves subscription, feature-limit, and billing recovery branches', async () => {
    api.post.mockRejectedValueOnce({
      message: 'Request failed with status code 402',
      response: { data: { code: 'subscription_required' } },
    })
    const subscriptionWrapper = mountTournament()
    await flushPromises()
    await subscriptionWrapper.find('#tournament-tab-simulation').trigger('click')
    await subscriptionWrapper.find('[data-testid="run-simulation"]').trigger('click')
    await flushPromises()
    expect(subscriptionWrapper.text()).toContain('An active subscription is required')
    expect(subscriptionWrapper.find('.billing-plans-link').attributes('href')).toBe('/pricing')
    subscriptionWrapper.unmount()

    api.post.mockRejectedValueOnce({ response: { data: { code: 'feature_limit_reached' } } })
    const limitWrapper = mountTournament()
    await flushPromises()
    await limitWrapper.find('#tournament-tab-simulation').trigger('click')
    await limitWrapper.find('[data-testid="run-simulation"]').trigger('click')
    await flushPromises()
    expect(limitWrapper.text()).toContain('limit has been reached')
    expect(limitWrapper.find('.billing-plans-link').attributes('href')).toBe('/pricing')
    limitWrapper.unmount()

    const health = {
      state: 'payment_required',
      severity: 'danger',
      requires_attention: true,
      action: 'update_payment_method',
      action_label: 'Pay invoice',
      message: 'Payment is overdue.',
    }
    api.post.mockRejectedValueOnce({
      response: { data: { code: 'billing_payment_required', billing_health: health } },
    })
    const billingWrapper = mountTournament()
    await flushPromises()
    await billingWrapper.find('#tournament-tab-simulation').trigger('click')
    await billingWrapper.find('[data-testid="run-simulation"]').trigger('click')
    await flushPromises()
    await billingWrapper.find('.status-action').trigger('click')
    expect(billingState.openBillingRecovery).toHaveBeenCalledWith(routeState.fullPath, health)
  })

  it('localizes frontend copy and numeric formatting while preserving source values', async () => {
    routeState.params.locale = 'es'
    routeState.fullPath = '/es/competitions/world-cup-2026/bracket'
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    api.get.mockResolvedValue({ data: { ...liveResults, total: 12345 } })
    const wrapper = mountTournament()
    await flushPromises()

    expect(wrapper.text()).toContain('12.345 partidos jugados')
    expect(wrapper.text()).toContain('ESPN')
    expect(wrapper.text()).toContain('Mexico')
    expect(wrapper.text()).toContain('2026-06-11')

    await wrapper.find('#tournament-tab-simulation').trigger('click')
    await wrapper.find('[data-testid="run-simulation"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Campeón')
    expect(wrapper.text()).toContain('62,4 %')
    expect(wrapper.find('[data-match-id="pred-final"]').text()).toContain('Previsto')
  })
})
