import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import AdminSettingsView from './AdminSettingsView.vue'

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn(),
    put: vi.fn(),
  },
}))

import { api } from '../lib/api'

const settingsResponse = {
        llm_base_url: 'https://api.openai.com/v1',
        llm_model_name: 'gpt-4o',
        zep_graph_id: '',
        opta_base_url: 'https://api.performfeeds.com/soccerdata',
        swarm_parallel_agents: 5,
  swarm_timeout_seconds: 60,
  mc_simulations: 10000,
  llm_api_key_configured: true,
  zep_api_key_configured: false,
  youtube_api_key_configured: true,
  opta_api_key_configured: false,
  updated_at: '2026-06-11T00:00:00Z',
  updated_by: { email: 'admin@example.com' },
}

function setupApi() {
  api.get.mockResolvedValue({ data: settingsResponse })
  api.put.mockImplementation(async (_url, payload) => ({
    data: {
      ...settingsResponse,
      ...payload,
      llm_api_key_configured: payload.clear_llm_api_key ? false : settingsResponse.llm_api_key_configured,
      youtube_api_key_configured: payload.clear_youtube_api_key ? false : settingsResponse.youtube_api_key_configured,
      updated_at: '2026-06-11T01:00:00Z',
    },
  }))
}

describe('AdminSettingsView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupApi()
  })

  it('loads and saves settings', async () => {
    const wrapper = mount(AdminSettingsView)
    await flushPromises()

    expect(wrapper.text()).toContain('Admin Settings')
    await wrapper.find('input').setValue('https://api.openai.com/v1')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('Settings saved.')
  })

  it('renders secret statuses with empty password fields', async () => {
    const wrapper = mount(AdminSettingsView)
    await flushPromises()

    expect(wrapper.text()).toContain('Configured')
    expect(wrapper.text()).toContain('Not configured')
    const passwordInputs = wrapper.findAll('input[type="password"]')
    expect(passwordInputs).toHaveLength(4)
    expect(passwordInputs.every((input) => input.element.value === '')).toBe(true)
  })

  it('sends a new API key when typed', async () => {
    const wrapper = mount(AdminSettingsView)
    await flushPromises()

    await wrapper.findAll('input[type="password"]')[1].setValue('new-zep-key')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(api.put).toHaveBeenCalledWith('/api/admin/settings', expect.objectContaining({ zep_api_key: 'new-zep-key' }))
  })

  it('does not send blank secret placeholders', async () => {
    const wrapper = mount(AdminSettingsView)
    await flushPromises()

    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    const payload = api.put.mock.calls[0][1]
    expect(payload.llm_api_key).toBeUndefined()
    expect(payload.youtube_api_key).toBeUndefined()
  })

  it('sends clear flags for configured keys', async () => {
    const wrapper = mount(AdminSettingsView)
    await flushPromises()

    const clearButtons = wrapper.findAll('button[aria-label="Clear stored API key"]')
    await clearButtons[0].trigger('click')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(api.put).toHaveBeenCalledWith('/api/admin/settings', expect.objectContaining({ clear_llm_api_key: true }))
  })
})
