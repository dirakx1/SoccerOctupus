import { describe, expect, it } from 'vitest'

import {
  getCompetitionEdition,
  listCompetitionEditions,
  supportsCapability,
} from './index.js'

describe('Competition Edition registry', () => {
  it('lists only active editions for the visible competition switcher', () => {
    expect(listCompetitionEditions().map(({ id, slug }) => ({ id, slug }))).toEqual([
      { id: 'premier-league', slug: 'premier-league' },
      { id: 'la-liga', slug: 'la-liga' },
      { id: 'bundesliga', slug: 'bundesliga' },
    ])
  })

  it('keeps the World Cup registered for historical routes', () => {
    expect(getCompetitionEdition('world-cup-2026')).toEqual({
      id: 'fifa-world-cup-2026', competitionId: 'fifa-world-cup', slug: 'world-cup-2026', format: 'group-and-knockout', displayNameKey: 'competitions.editions.worldCup2026.name', capabilities: ['groups', 'predictions', 'bracket', 'markets', 'swarm'],
    })
  })

  it('resolves a Competition Edition by stable slug', () => {
    expect(getCompetitionEdition('world-cup-2026').slug).toBe('world-cup-2026')
    expect(getCompetitionEdition('premier-league')).toEqual(listCompetitionEditions()[0])
    expect(getCompetitionEdition('la-liga-2027-28').competitionId).toBe('la-liga')
    expect(getCompetitionEdition('bundesliga').clubCount).toBe(18)
  })

  it('returns null for blank and unknown Competition Edition slugs', () => {
    expect(getCompetitionEdition('')).toBeNull()
    expect(getCompetitionEdition('   ')).toBeNull()
    expect(getCompetitionEdition('unknown-edition')).toBeNull()
    expect(getCompetitionEdition()).toBeNull()
  })

  it('reports the Competition Capabilities supported by World Cup 2026', () => {
    const edition = getCompetitionEdition('world-cup-2026')

    expect(supportsCapability(edition, 'groups')).toBe(true)
    expect(supportsCapability(edition, 'predictions')).toBe(true)
    expect(supportsCapability(edition, 'bracket')).toBe(true)
    expect(supportsCapability(edition, 'markets')).toBe(true)
  })

  it('returns false for unsupported capabilities and invalid Competition Editions', () => {
    const edition = getCompetitionEdition('world-cup-2026')

    expect(supportsCapability(edition, 'table')).toBe(false)
    expect(supportsCapability(edition, 'fixtures')).toBe(false)
    expect(supportsCapability(edition, '')).toBe(false)
    expect(supportsCapability(edition)).toBe(false)
    expect(supportsCapability(null, 'groups')).toBe(false)
    expect(supportsCapability({ id: 'unknown', slug: 'unknown' }, 'groups')).toBe(false)
  })

  it('does not expose shared registry state to callers', () => {
    const listedEditions = listCompetitionEditions()
    listedEditions[0].id = 'changed'
    listedEditions[0].capabilities.push('table')
    listedEditions.push({ id: 'invented' })

    const resolvedEdition = getCompetitionEdition('world-cup-2026')
    expect(resolvedEdition.id).toBe('fifa-world-cup-2026')
    expect(resolvedEdition.capabilities).toEqual([
      'groups',
      'predictions',
      'bracket',
      'markets',
      'swarm',
    ])
    expect(listCompetitionEditions()).toHaveLength(3)
    expect(supportsCapability(resolvedEdition, 'table')).toBe(false)
  })
})
