import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import Home from './Home.vue'
import { applyLocale, i18n } from '../i18n/index.js'
import { workspaceLocation } from '../router/workspace.js'

const routeState = {
  params: {
    locale: 'en',
    competitionEditionSlug: 'world-cup-2026',
  },
}

vi.mock('vue-router', () => ({
  useRoute: () => routeState,
}))

const RouterLinkStub = {
  props: {
    to: { type: [String, Object], required: true },
  },
  template: '<a :href="typeof to === \'string\' ? to : to.name"><slot /></a>',
}

const VideoModalStub = {
  template: '<div data-testid="video-modal" />',
}

function mountHome() {
  return mount(Home, {
    global: {
      plugins: [i18n],
      stubs: {
        RouterLink: RouterLinkStub,
        VideoAgentModal: VideoModalStub,
      },
    },
  })
}

describe('Home', () => {
  beforeEach(() => {
    routeState.params.locale = 'en'
    applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement })
  })

  it('renders the Atlas home content and canonical workflow locations', () => {
    const wrapper = mountHome()

    expect(wrapper.text()).toContain('SoccerOctopus')
    expect(wrapper.text()).toContain('FIFA World Cup 2026')
    expect(wrapper.text()).toContain('Statistical agent')
    expect(wrapper.text()).not.toContain('🐙')

    const workflowLinks = wrapper.findAllComponents(RouterLinkStub)
    expect(workflowLinks.map((link) => link.props('to'))).toEqual([
      workspaceLocation('groups', { locale: 'en', competitionEditionSlug: 'world-cup-2026' }),
      workspaceLocation('predict', { locale: 'en', competitionEditionSlug: 'world-cup-2026' }),
      workspaceLocation('bracket', { locale: 'en', competitionEditionSlug: 'world-cup-2026' }),
      workspaceLocation('markets', { locale: 'en', competitionEditionSlug: 'world-cup-2026' }),
    ])
    expect(wrapper.findAll('[data-testid^="workflow-"]')).toHaveLength(4)
  })

  it('localizes workflow and swarm copy for Spanish', () => {
    routeState.params.locale = 'es'
    applyLocale('es', { storage: window.localStorage, documentElement: document.documentElement })
    const wrapper = mountHome()

    expect(wrapper.text()).toContain('Cada partido, un atlas.')
    expect(wrapper.text()).toContain('Grupos')
    expect(wrapper.text()).toContain('Agente estadístico')
  })

  it('opens the video evidence modal from an accessible button', async () => {
    const wrapper = mountHome()
    const trigger = wrapper.find('.agent-action')

    expect(trigger.element.tagName).toBe('BUTTON')
    expect(trigger.attributes('aria-label')).toBe('View video intelligence evidence')
    await trigger.trigger('click')

    expect(wrapper.find('[data-testid="video-modal"]').exists()).toBe(true)
  })
})
