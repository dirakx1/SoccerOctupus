import { describe, expect, it } from 'vitest'

import { HISTORIC_WORKSPACE_ROUTE_NAMES, workspaceLocaleLocation, workspaceLocation, workspaceSwitchLocation } from './workspace.js'

describe('Competition Workspace locale location', () => {
  it('preserves the named route, Competition Edition, query, and hash', () => {
    expect(workspaceLocaleLocation({
      name: 'competition-workspace-predict',
      params: { locale: 'en', competitionEditionSlug: 'world-cup-2026' },
      query: { stage: 'group' },
      hash: '#match-form',
      meta: { competitionWorkspace: true },
    }, 'es')).toEqual({
      name: 'competition-workspace-predict',
      params: { locale: 'es', competitionEditionSlug: 'world-cup-2026' },
      query: { stage: 'group' },
      hash: '#match-form',
    })
  })

  it('does not create a localized location for transitional flat routes', () => {
    expect(workspaceLocaleLocation({
      name: undefined,
      params: {},
      query: {},
      hash: '',
      meta: {},
    }, 'es')).toBeNull()
  })

  it('falls back to overview when the target edition lacks the current area', () => {
    const target = workspaceSwitchLocation({
      name: 'competition-workspace-groups',
      params: { locale: 'en', competitionEditionSlug: 'world-cup-2026' },
      query: {}, hash: '', meta: { competitionWorkspace: true },
    }, { id: 'premier-league-2026-27', slug: 'premier-league-2026-27', capabilities: ['table', 'fixtures', 'predictions', 'markets'] })
    expect(target.name).toBe('league-workspace-overview')
  })

  it('keeps an equivalent league area when switching to an edition that supports it', () => {
    const target = workspaceSwitchLocation({
      name: 'league-workspace-table',
      params: { locale: 'en', competitionEditionSlug: 'premier-league-2026-27' },
      query: {}, hash: '', meta: { competitionWorkspace: true },
    }, { id: 'fifa-world-cup-2026', slug: 'world-cup-2026', capabilities: ['groups', 'predictions', 'bracket', 'markets', 'swarm'] })
    expect(target.name).toBe(HISTORIC_WORKSPACE_ROUTE_NAMES.overview)
  })

  it('routes the registered Premier League identity through the active alias', () => {
    expect(workspaceLocation('overview', { locale: 'en', competitionEditionSlug: 'premier-league' })).toEqual({
      name: 'league-workspace-overview',
      params: { locale: 'en', competitionEditionSlug: 'premier-league' },
    })
  })
})
