import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import AdminSettingsView from './AdminSettingsView.vue'

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn(async () => ({
      data: {
        llm_base_url: 'https://api.openai.com/v1',
        llm_model_name: 'gpt-4o',
        zep_graph_id: '',
        swarm_parallel_agents: 5,
        swarm_timeout_seconds: 60,
        mc_simulations: 10000,
        updated_at: '2026-06-11T00:00:00Z',
        updated_by: { email: 'admin@example.com' },
      },
    })),
    put: vi.fn(async (_url, payload) => ({ data: { ...payload, updated_at: '2026-06-11T01:00:00Z', updated_by: { email: 'admin@example.com' } } })),
  },
}))

describe('AdminSettingsView', () => {
  it('loads and saves settings', async () => {
    const wrapper = mount(AdminSettingsView)
    await flushPromises()

    expect(wrapper.text()).toContain('Admin Settings')
    await wrapper.find('input').setValue('https://api.openai.com/v1')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('Settings saved.')
  })
})
