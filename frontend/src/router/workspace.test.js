import { describe, expect, it } from 'vitest'

import { workspaceLocaleLocation } from './workspace.js'

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
})
