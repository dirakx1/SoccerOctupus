import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

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
  it('renders loading then the edition identity, capabilities, and empty preview states', async () => {
    let resolveRequest
    api.get.mockReturnValueOnce(new Promise((resolve) => { resolveRequest = resolve }))
    const wrapper = mountView()

    expect(wrapper.get('[data-testid="league-loading"]').text()).toContain('Loading')

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
    expect(wrapper.findAll('[data-testid^="league-preview-empty-"]')).toHaveLength(3)
  })

  it('renders a retryable error when the Competition Edition cannot be resolved', async () => {
    api.get.mockRejectedValueOnce(new Error('not found'))
    const wrapper = mountView({ editionSlug: 'not-real' })
    await flushPromises()

    expect(wrapper.get('[data-testid="league-error"]').text()).toContain('could not be loaded')
    api.get.mockResolvedValueOnce({ data: {
      competition: { slug: 'premier-league', display_name: 'Premier League' },
      edition: { slug: '2026-27', display_name: 'Premier League 2026-27', capabilities: [] },
    } })
    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(wrapper.get('h1').text()).toBe('Premier League 2026-27')
  })
})
