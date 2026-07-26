import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.hoisted(() => vi.fn())
vi.mock('../lib/api.js', () => ({ api: { get: apiGet } }))

import { i18n } from '../i18n/index.js'
import LeagueFixturesView from './LeagueFixturesView.vue'

const fixtures = [
  {
    id: 1, matchweek: 1, kickoff_at: '2026-08-15T14:00:00+00:00', venue: 'Emirates Stadium',
    status: 'in_progress', source_updated_at: '2026-08-15T14:30:00+00:00',
    home_team: { slug: 'arsenal', display_name: 'Arsenal', score: 2 },
    away_team: { slug: 'liverpool', display_name: 'Liverpool', score: 1 },
  },
  {
    id: 2, matchweek: 1, kickoff_at: '2026-08-16T14:00:00+00:00', venue: null,
    status: 'postponed', source_updated_at: '2026-08-15T14:30:00+00:00',
    home_team: { slug: 'chelsea', display_name: 'Chelsea', score: null },
    away_team: { slug: 'everton', display_name: 'Everton', score: null },
  },
]

function response(overrides = {}) {
  return {
    data: {
      edition: { slug: '2026-27', display_name: 'Premier League 2026-27' },
      filters: { mode: 'upcoming', matchweek: 1, team: null },
      selected_matchweek: 1,
      matchweeks: [1, 2],
      teams: [
        { slug: 'arsenal', display_name: 'Arsenal' },
        { slug: 'liverpool', display_name: 'Liverpool' },
      ],
      fixtures,
      ...overrides,
    },
  }
}

async function mountRouted(query = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:locale/competitions/:competitionSlug/editions/:editionSlug/fixtures', component: LeagueFixturesView, props: true }],
  })
  await router.push({ path: '/en/competitions/premier-league/editions/2026-27/fixtures', query })
  await router.isReady()
  const wrapper = mount(LeagueFixturesView, {
    props: { locale: 'en', competitionSlug: 'premier-league', editionSlug: '2026-27' },
    global: { plugins: [i18n, router] },
  })
  return { router, wrapper }
}

describe('Premier League Fixtures view', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'en'
    apiGet.mockReset()
    apiGet.mockResolvedValue(response())
  })

  it('renders the default Matchweek with live and exceptional states', async () => {
    const { router, wrapper } = await mountRouted()
    await flushPromises()

    expect(apiGet).toHaveBeenCalledWith('/api/competitions/premier-league/editions/2026-27/fixtures', { params: {} })
    expect(wrapper.get('h1').text()).toBe('Premier League 2026-27 Fixtures')
    expect(wrapper.get('[data-testid="fixture-1"]').text()).toContain('Live')
    expect(wrapper.get('[data-testid="fixture-1"]').text()).toContain('2')
    expect(wrapper.get('[data-testid="fixture-2"]').text()).toContain('Postponed')
    expect(wrapper.get('[data-testid="fixtures-updated"]').text()).toContain('Updated')
    expect(router.currentRoute.value.query).toEqual({ matchweek: '1' })
  })

  it('preserves Matchweek, Team, and mode filters in the URL', async () => {
    const { router, wrapper } = await mountRouted({ campaign: 'summer' })
    await flushPromises()

    await wrapper.get('[data-testid="fixtures-matchweek"]').setValue('2')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ campaign: 'summer', matchweek: '2' })
    expect(apiGet).toHaveBeenLastCalledWith(
      '/api/competitions/premier-league/editions/2026-27/fixtures',
      { params: { matchweek: '2' } },
    )

    await wrapper.get('[data-testid="fixtures-team"]').setValue('arsenal')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ campaign: 'summer', matchweek: '2', team: 'arsenal' })

    await wrapper.get('[data-testid="fixtures-mode-results"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ campaign: 'summer', matchweek: '2', team: 'arsenal', mode: 'results' })
  })

  it('shows complete loading, empty, and error states', async () => {
    let resolveRequest
    apiGet.mockReturnValue(new Promise((resolve) => { resolveRequest = resolve }))
    const { router, wrapper } = await mountRouted()
    expect(wrapper.get('[data-testid="fixtures-loading"]').exists()).toBe(true)

    resolveRequest(response({ fixtures: [] }))
    await flushPromises()
    expect(wrapper.get('[data-testid="fixtures-empty"]').text()).toContain('No Fixtures')

    apiGet.mockRejectedValueOnce(new Error('offline'))
    await router.push({ query: { mode: 'results' } })
    await flushPromises()
    expect(wrapper.get('[data-testid="fixtures-error"]').text()).toContain('could not be loaded')
  })
})
