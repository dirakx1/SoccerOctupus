import { describe, expect, it } from 'vitest'

import { worldCup2026 } from './editions/worldCup2026.js'
import { getCompetitionNavigation } from './navigation.js'

describe('Competition Workspace navigation', () => {
  it('derives exactly the registered World Cup capabilities and canonical targets', () => {
    expect(getCompetitionNavigation(worldCup2026, { locale: 'es' })).toEqual([
      {
        key: 'overview',
        capability: null,
        labelKey: 'navigation.workspace.overview',
        route: {
          name: 'competition-workspace-overview',
          params: { locale: 'es', competitionEditionSlug: 'world-cup-2026' },
        },
      },
      {
        key: 'groups',
        capability: 'groups',
        labelKey: 'navigation.workspace.groups',
        route: {
          name: 'competition-workspace-groups',
          params: { locale: 'es', competitionEditionSlug: 'world-cup-2026' },
        },
      },
      {
        key: 'predict',
        capability: 'predictions',
        labelKey: 'navigation.workspace.predict',
        route: {
          name: 'competition-workspace-predict',
          params: { locale: 'es', competitionEditionSlug: 'world-cup-2026' },
        },
      },
      {
        key: 'bracket',
        capability: 'bracket',
        labelKey: 'navigation.workspace.bracket',
        route: {
          name: 'competition-workspace-bracket',
          params: { locale: 'es', competitionEditionSlug: 'world-cup-2026' },
        },
      },
      {
        key: 'markets',
        capability: 'markets',
        labelKey: 'navigation.workspace.markets',
        route: {
          name: 'competition-workspace-markets',
          params: { locale: 'es', competitionEditionSlug: 'world-cup-2026' },
        },
      },
    ])
  })
})
