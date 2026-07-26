import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import LeagueOverviewView from './LeagueOverviewView.vue'
import { i18n } from '../i18n/index.js'
import { api } from '../lib/api.js'

vi.mock('../lib/api.js', () => ({ api: { get: vi.fn() } }))

const RouterLinkStub = {
  props: ['to'],
  template: '<a><slot /></a>',
}

function mountView(props = {}) {
  return mount(LeagueOverviewView, {
    props: { locale: 'en', competitionSlug: 'premier-league', ...props },
    global: { plugins: [i18n], stubs: { RouterLink: RouterLinkStub } },
  })
}

describe('LeagueOverviewView', () => {
  beforeEach(() => api.get.mockReset())

  it('renders loading then the edition identity, capabilities, and empty preview states', async () => {
    let resolveRequest
    api.get
      .mockReturnValueOnce(new Promise((resolve) => { resolveRequest = resolve }))
      .mockResolvedValueOnce({ data: {
        source: 'ESPN',
        source_updated_at: '2026-08-20T12:00:00+00:00',
        standings: [
          { position: 1, team: { display_name: 'Arsenal' }, played: 2, goal_difference: 4, points: 6 },
          { position: 2, team: { display_name: 'Liverpool' }, played: 2, goal_difference: 2, points: 4 },
        ],
      } })
    const wrapper = mountView()

    expect(wrapper.get('[data-testid="league-loading"]').attributes('aria-busy')).toBe('true')
    expect(wrapper.findAll('[data-testid="league-loading"] .skeleton-capability')).toHaveLength(4)
    expect(wrapper.findAll('[data-testid="league-loading"] .skeleton-preview')).toHaveLength(3)

    resolveRequest({ data: {
      competition: { slug: 'premier-league', display_name: 'Premier League' },
      edition: {
        slug: '2026-27',
        display_name: 'Premier League 2026-27',
        capabilities: ['table', 'fixtures', 'predictions', 'markets'],
      },
    } })
    await flushPromises()

    expect(wrapper.get('h1').text()).toBe('Premier League 2026-27')
    expect(wrapper.findAll('[data-testid^="league-capability-"]')).toHaveLength(4)
    expect(wrapper.get('[data-testid="league-table-preview"]').text()).toContain('Arsenal')
    expect(wrapper.get('[data-testid="league-table-preview"]').text()).toContain('Updated')
    expect(wrapper.findAll('[data-testid^="league-preview-empty-"]')).toHaveLength(2)
  })

  it('renders a retryable error when the Competition Edition cannot be resolved', async () => {
    api.get.mockRejectedValueOnce(new Error('not found'))
    const wrapper = mountView({ editionSlug: 'not-real' })
    await flushPromises()

    expect(wrapper.get('[data-testid="league-error"]').text()).toContain('could not be loaded')
    api.get.mockResolvedValueOnce({ data: {
      competition: { slug: 'premier-league', display_name: 'Premier League' },
      edition: { slug: '2026-27', display_name: 'Premier League 2026-27', capabilities: [] },
    } }).mockRejectedValueOnce(new Error('not synchronized'))
    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(wrapper.get('h1').text()).toBe('Premier League 2026-27')
  })

  it('shows an explicit empty preview when table data is unavailable', async () => {
    api.get
      .mockResolvedValueOnce({ data: {
        competition: { slug: 'premier-league' },
        edition: { slug: '2026-27', display_name: 'Premier League 2026-27', capabilities: [] },
      } })
      .mockRejectedValueOnce(new Error('not synchronized'))

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.get('[data-testid="league-preview-empty-table"]').text()).toContain('not available')
  })
})
