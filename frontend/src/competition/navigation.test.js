import { describe, expect, it } from 'vitest'

import { worldCup2026 } from './editions/worldCup2026.js'
import { premierLeague202627 } from './editions/premierLeague202627.js'
import { getCompetitionNavigation } from './navigation.js'

describe('Competition Workspace navigation', () => {
  it('derives exactly the registered World Cup capabilities and canonical targets', () => {
    expect(getCompetitionNavigation(worldCup2026, { locale: 'es' })).toEqual([
      {
        key: 'overview',
        capability: null,
        labelKey: 'navigation.workspace.overview',
        route: {
          name: 'historic-competition-workspace-overview',
          params: { locale: 'es', competitionEditionSlug: 'world-cup-2026' },
        },
      },
      {
        key: 'groups',
        capability: 'groups',
        labelKey: 'navigation.workspace.groups',
        route: {
          name: 'historic-competition-workspace-groups',
          params: { locale: 'es', competitionEditionSlug: 'world-cup-2026' },
        },
      },
      {
        key: 'predict',
        capability: 'predictions',
        labelKey: 'navigation.workspace.predict',
        route: {
          name: 'historic-competition-workspace-predict',
          params: { locale: 'es', competitionEditionSlug: 'world-cup-2026' },
        },
      },
      {
        key: 'bracket',
        capability: 'bracket',
        labelKey: 'navigation.workspace.bracket',
        route: {
          name: 'historic-competition-workspace-bracket',
          params: { locale: 'es', competitionEditionSlug: 'world-cup-2026' },
        },
      },
      {
        key: 'markets',
        capability: 'markets',
        labelKey: 'navigation.workspace.markets',
        route: {
          name: 'historic-competition-workspace-markets',
          params: { locale: 'es', competitionEditionSlug: 'world-cup-2026' },
        },
      },
      {
        key: 'swarm',
        capability: 'swarm',
        labelKey: 'navigation.workspace.swarm',
        route: {
          name: 'historic-competition-workspace-swarm',
          params: { locale: 'es', competitionEditionSlug: 'world-cup-2026' },
        },
      },
    ])
  })

  it('exposes the consumer league table, fixtures, prediction, and market targets', () => {
    expect(getCompetitionNavigation(premierLeague202627, { locale: 'en' }).map(({ key, capability, route }) => ({ key, capability, name: route.name }))).toEqual([
      { key: 'overview', capability: null, name: 'league-workspace-overview' },
      { key: 'table', capability: 'table', name: 'league-workspace-table' },
      { key: 'fixtures', capability: 'fixtures', name: 'league-workspace-fixtures' },
      { key: 'predict', capability: 'predictions', name: 'league-workspace-predict' },
      { key: 'markets', capability: 'markets', name: 'league-workspace-markets' },
    ])
  })
})
