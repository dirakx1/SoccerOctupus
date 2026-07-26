import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { i18n } from '../i18n/index.js'
import { api } from '../lib/api.js'
import LeagueTableView from './LeagueTableView.vue'

vi.mock('../lib/api.js', () => ({ api: { get: vi.fn() } }))

const standings = [
  { position: 1, team: { display_name: 'Arsenal', abbreviation: 'ARS' }, played: 2, won: 2, drawn: 0, lost: 0, goals_for: 5, goals_against: 1, goal_difference: 4, points: 6 },
  { position: 2, team: { display_name: 'Liverpool', abbreviation: 'LIV' }, played: 2, won: 1, drawn: 1, lost: 0, goals_for: 3, goals_against: 1, goal_difference: 2, points: 4 },
]

function mountView() {
  return mount(LeagueTableView, {
    props: { competitionSlug: 'premier-league', editionSlug: '2026-27' },
    global: { plugins: [i18n] },
  })
}

describe('LeagueTableView', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'en'
    api.get.mockReset()
  })

  it('renders loading then every authoritative table statistic and freshness', async () => {
    let resolveRequest
    api.get.mockReturnValueOnce(new Promise((resolve) => { resolveRequest = resolve }))
    const wrapper = mountView()
    expect(wrapper.get('[data-testid="league-table-loading"]').attributes('aria-busy')).toBe('true')
    expect(wrapper.findAll('[data-testid="league-table-loading"] .skeleton-table-row')).toHaveLength(10)
    expect(wrapper.findAll('[data-testid="league-table-loading"] .skeleton-cell')).toHaveLength(40)

    resolveRequest({ data: {
      edition: { display_name: 'Premier League 2026-27' },
      source: 'ESPN',
      source_updated_at: '2026-08-20T12:00:00+00:00',
      stale: true,
      standings,
    } })
    await flushPromises()

    expect(wrapper.get('h1').text()).toBe('Premier League 2026-27')
    expect(wrapper.findAll('tbody tr')).toHaveLength(2)
    expect(wrapper.get('tbody').text()).toContain('Arsenal')
    expect(wrapper.get('tbody').text()).toContain('5')
    expect(wrapper.get('[data-testid="league-table-source"]').text()).toContain('ESPN')
    expect(wrapper.get('[data-testid="league-table-stale"]').text()).toContain('may be out of date')
  })

  it('renders explicit empty and retryable unavailable states', async () => {
    api.get.mockResolvedValueOnce({ data: {
      edition: { display_name: 'Premier League 2026-27' },
      source: 'ESPN', source_updated_at: '2026-08-20T12:00:00+00:00', stale: false, standings: [],
    } })
    const empty = mountView()
    await flushPromises()
    expect(empty.get('[data-testid="league-table-empty"]').text()).toContain('No standings')

    api.get.mockRejectedValueOnce(new Error('unavailable'))
    const error = mountView()
    await flushPromises()
    expect(error.get('[data-testid="league-table-error"]').text()).toContain('could not be loaded')
    expect(error.get('button').text()).toBe('Try again')
  })
})
