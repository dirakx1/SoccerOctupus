import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.hoisted(() => vi.fn())
const apiPost = vi.hoisted(() => vi.fn())
vi.mock('../lib/api.js', () => ({ api: { get: apiGet, post: apiPost } }))

import { i18n } from '../i18n/index.js'
import LeaguePredictView from './LeaguePredictView.vue'

const fixtures = [
  {
    id: 41,
    matchweek: 1,
    kickoff_at: '2026-08-15T14:00:00+00:00',
    status: 'scheduled',
    home_team: { display_name: 'Arsenal' },
    away_team: { display_name: 'Liverpool' },
  },
  {
    id: 42,
    matchweek: 1,
    kickoff_at: '2026-08-16T14:00:00+00:00',
    status: 'completed',
    home_team: { display_name: 'Chelsea' },
    away_team: { display_name: 'Everton' },
  },
]

function fixturesResponse(overrides = {}) {
  return {
    data: {
      edition: { slug: '2026-27', display_name: 'Premier League 2026-27' },
      fixtures,
      ...overrides,
    },
  }
}

async function mountRouted(locale = 'en') {
  i18n.global.locale.value = locale
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{
      path: '/:locale/competitions/:competitionSlug/editions/:editionSlug/predict',
      component: LeaguePredictView,
      props: true,
    }],
  })
  await router.push(`/${locale}/competitions/premier-league/editions/2026-27/predict`)
  await router.isReady()
  const wrapper = mount(LeaguePredictView, {
    props: { competitionSlug: 'premier-league', editionSlug: '2026-27' },
    global: { plugins: [i18n, router] },
  })
  return { router, wrapper }
}

describe('Premier League Predictions routed view', () => {
  beforeEach(() => {
    apiGet.mockReset()
    apiPost.mockReset()
    apiGet.mockResolvedValue(fixturesResponse())
  })

  it('loads scheduled Fixtures and reveals the selected internal Fixture ID', async () => {
    apiPost.mockResolvedValue({
      data: {
        reveal_status: 'charged',
        prediction: {
          home_team: 'Arsenal',
          away_team: 'Liverpool',
          outcome_probabilities: { home: 0.52, draw: 0.26, away: 0.22 },
          likely_score: '2-1',
          confidence: 0.74,
          source: 'ESPN club match history',
          generated_at: '2026-08-14T10:30:00+00:00',
          agents: {
            available: ['statistical', 'form'],
            unavailable: [{ agent: 'video', reason: 'No genuine club video input' }],
          },
        },
      },
    })
    const { wrapper } = await mountRouted()
    await flushPromises()

    expect(apiGet).toHaveBeenCalledWith(
      '/api/competitions/premier-league/editions/2026-27/fixtures',
      { params: { mode: 'upcoming' } },
    )
    expect(wrapper.get('[data-testid="fixture-target"]').findAll('option')).toHaveLength(2)
    expect(wrapper.text()).toContain('Arsenal vs Liverpool')
    expect(wrapper.text()).not.toContain('Chelsea vs Everton')

    await wrapper.get('[data-testid="fixture-target"]').setValue('41')
    await wrapper.get('[data-testid="reveal-prediction"]').trigger('click')
    await flushPromises()

    expect(apiPost).toHaveBeenCalledWith(
      '/api/competitions/premier-league/editions/2026-27/fixtures/41/prediction',
    )
    expect(wrapper.text()).toContain('2-1')
    expect(wrapper.text()).toContain('52.0%')
    expect(wrapper.text()).toContain('Charged reveal')
  })

  it('shows generation progress and a free reopen with Spanish prediction details', async () => {
    let resolvePrediction
    apiPost.mockReturnValue(new Promise((resolve) => { resolvePrediction = resolve }))
    const { wrapper } = await mountRouted('es')
    await flushPromises()

    await wrapper.get('[data-testid="fixture-target"]').setValue('41')
    await wrapper.get('[data-testid="reveal-prediction"]').trigger('click')
    expect(wrapper.get('[data-testid="prediction-generating"]').text()).toContain('Generando predicción')

    resolvePrediction({
      data: {
        reveal_status: 'reopened',
        prediction: {
          home_team: 'Arsenal', away_team: 'Liverpool',
          home_win_prob: 0.5, draw_prob: 0.3, away_win_prob: 0.2,
          likely_score: '1-0', overall_confidence: 0.68,
          model_version: 'baseline-v2', created_at: '2026-08-14T10:30:00+00:00',
          available_agents: [{ name: 'Agente estadístico' }],
          unavailable_agents: [{ agent: 'Agente de vídeo', reason: 'Sin datos del club' }],
        },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Reapertura gratuita')
    expect(wrapper.text()).toContain('Resultado más probable')
    expect(wrapper.text()).toContain('68,0 %')
    expect(wrapper.text()).toContain('Agentes disponibles')
    expect(wrapper.text()).toContain('Agente estadístico')
    expect(wrapper.text()).toContain('Agente de vídeo: Sin datos del club')
  })

  it('renders the server-authoritative feature limit without a prediction', async () => {
    apiPost.mockRejectedValue({ response: { data: { code: 'feature_limit_reached' } } })
    const { wrapper } = await mountRouted()
    await flushPromises()

    await wrapper.get('[data-testid="fixture-target"]').setValue('41')
    await wrapper.get('[data-testid="reveal-prediction"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="prediction-error"]').text()).toContain('Prediction limit reached')
    expect(wrapper.find('.prediction-result').exists()).toBe(false)
    expect(wrapper.get('[data-testid="fixture-target"]').element.value).toBe('41')
  })

  it('renders a Spanish blocked state when the server rejects Fixture eligibility', async () => {
    apiPost.mockRejectedValue({ response: { data: { code: 'fixture_ineligible' } } })
    const { wrapper } = await mountRouted('es')
    await flushPromises()

    await wrapper.get('[data-testid="fixture-target"]').setValue('41')
    await wrapper.get('[data-testid="reveal-prediction"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="prediction-error"]').text()).toContain('Partido no elegible')
    expect(wrapper.get('[data-testid="prediction-error"]').text()).toContain('No se realizó ningún cargo')
    expect(wrapper.find('.reveal-status').exists()).toBe(false)
  })

  it('allows the same Fixture to retry after prediction generation fails', async () => {
    apiPost
      .mockRejectedValueOnce({ response: { data: { code: 'prediction_generation_failed' } } })
      .mockResolvedValueOnce({
        data: {
          reveal_status: 'charged',
          prediction: {
            home_team: 'Arsenal', away_team: 'Liverpool',
            home_win_probability: 0.4, draw_probability: 0.3, away_win_probability: 0.3,
            most_likely_score: '1-1', confidence: 0.6,
          },
        },
      })
    const { wrapper } = await mountRouted()
    await flushPromises()

    await wrapper.get('[data-testid="fixture-target"]').setValue('41')
    await wrapper.get('[data-testid="reveal-prediction"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="prediction-error"]').text()).toContain('Prediction could not be generated')
    expect(wrapper.get('[data-testid="prediction-error"]').text()).toContain('No reveal was charged')

    await wrapper.get('[data-testid="reveal-prediction"]').trigger('click')
    await flushPromises()
    expect(apiPost).toHaveBeenCalledTimes(2)
    expect(wrapper.find('[data-testid="prediction-error"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('1-1')
  })
})
