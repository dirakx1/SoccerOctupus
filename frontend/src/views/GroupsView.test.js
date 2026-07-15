import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import GroupsView from './GroupsView.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const routeState = {
  params: {
    locale: 'en',
    competitionEditionSlug: 'world-cup-2026',
  },
}

vi.mock('vue-router', () => ({
  useRoute: () => routeState,
}))

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn(),
  },
}))

import { api } from '../lib/api'

const groupsResponse = {
  groups: {
    B: [
      { team: 'Lower ELO', elo: 1700, rank: 30 },
      { team: 'Higher ELO', elo: 1900, rank: 8 },
    ],
    A: [
      { team: 'Alpha', elo: 1800, rank: 12 },
    ],
  },
}

function mountGroups() {
  return mount(GroupsView, {
    global: { plugins: [i18n] },
  })
}

describe('GroupsView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    routeState.params.locale = 'en'
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
    api.get.mockResolvedValue({ data: groupsResponse })
  })

  it('loads the groups endpoint, sorts teams by descending ELO, and counts response data', async () => {
    const wrapper = mountGroups()
    await flushPromises()

    expect(api.get).toHaveBeenCalledWith('/api/predictions/groups')
    expect(wrapper.text()).toContain('2 groups')
    expect(wrapper.text()).toContain('3 teams')
    const firstGroupRows = wrapper.findAll('.group-panel')[0].findAll('tbody tr')
    expect(firstGroupRows[0].text()).toContain('Alpha')
    const secondGroupRows = wrapper.findAll('.group-panel')[1].findAll('tbody tr')
    expect(secondGroupRows[0].text()).toContain('Higher ELO')
    expect(secondGroupRows[1].text()).toContain('Lower ELO')
  })

  it('shows a loading skeleton while the group request is pending', async () => {
    api.get.mockImplementation(() => new Promise(() => {}))
    const wrapper = mountGroups()
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[aria-busy="true"]').exists()).toBe(true)
    expect(wrapper.findAll('.group-panel-skeleton')).toHaveLength(4)
  })

  it('shows a useful empty state when the response contains no groups', async () => {
    api.get.mockResolvedValue({ data: { groups: {} } })
    const wrapper = mountGroups()
    await flushPromises()

    expect(wrapper.text()).toContain('No group data is available yet.')
    expect(wrapper.find('.groups-state-error').exists()).toBe(false)
  })

  it('shows an inline error and retries the request', async () => {
    api.get
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce({ data: groupsResponse })
    const wrapper = mountGroups()
    await flushPromises()

    expect(wrapper.find('.groups-state-error').exists()).toBe(true)
    expect(wrapper.text()).toContain("We couldn't load groups.")

    await wrapper.find('.groups-state-error button').trigger('click')
    await flushPromises()

    expect(api.get).toHaveBeenCalledTimes(2)
    expect(wrapper.find('.groups-state-error').exists()).toBe(false)
    expect(wrapper.text()).toContain('Higher ELO')
  })

  it('localizes the page copy for Spanish', async () => {
    routeState.params.locale = 'es'
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const wrapper = mountGroups()
    await flushPromises()

    expect(wrapper.text()).toContain('El campo, ordenado por señal.')
    expect(wrapper.text()).toContain('2 grupos')
    expect(wrapper.text()).toContain('Clasificación del grupo A')
  })
})
