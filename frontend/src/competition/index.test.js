import { describe, expect, it } from 'vitest'

import {
  getCompetitionEdition,
  listCompetitionEditions,
  supportsCapability,
} from './index.js'

describe('Competition Edition registry', () => {
  it('lists the registered World Cup 2026 edition', () => {
    expect(listCompetitionEditions()).toEqual(expect.arrayContaining([
      expect.objectContaining({
        id: 'fifa-world-cup-2026',
        slug: 'world-cup-2026',
      }),
    ]))
  })

  it('describes the World Cup edition using stable domain identifiers and current capabilities', () => {
    expect(listCompetitionEditions()[0]).toEqual({
      id: 'fifa-world-cup-2026',
      competitionId: 'fifa-world-cup',
      slug: 'world-cup-2026',
      format: 'group-and-knockout',
      displayNameKey: 'competitions.editions.worldCup2026.name',
      capabilities: ['groups', 'predictions', 'bracket', 'markets', 'swarm'],
    })
  })

  it('resolves a Competition Edition by stable slug', () => {
    expect(getCompetitionEdition('world-cup-2026')).toEqual(listCompetitionEditions()[0])
    expect(getCompetitionEdition('premier-league')).toEqual(listCompetitionEditions()[1])
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
    expect(listCompetitionEditions()).toHaveLength(2)
    expect(supportsCapability(resolvedEdition, 'table')).toBe(false)
  })
})
