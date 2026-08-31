import { worldCup2026 } from './editions/worldCup2026.js'
import { premierLeague202627 } from './editions/premierLeague202627.js'

const editions = Object.freeze([worldCup2026, premierLeague202627])
const visibleEditions = Object.freeze([
  // worldCup2026 remains registered for historical routes, but is intentionally hidden from the active switcher.
  premierLeague202627,
])

function copyEdition(edition) {
  return {
    ...edition,
    capabilities: [...edition.capabilities],
  }
}

export function listCompetitionEditions() {
  return visibleEditions.map(copyEdition)
}

export function getCompetitionEdition(slug) {
  const edition = editions.find((entry) => entry.slug === slug)
  if (edition) return copyEdition(edition)
  if (typeof slug === 'string' && /^premier-league(?:-\d{4}-\d{2})?$/.test(slug)) {
    return {
      id: slug,
      competitionId: 'premier-league',
      slug,
      format: 'league',
      displayName: slug === 'premier-league' ? 'Premier League' : slug.replace('premier-league-', 'Premier League '),
      displayNameKey: 'competitions.premierLeague.name',
      capabilities: ['table', 'fixtures', 'predictions', 'markets'],
    }
  }
  return null
}

export function supportsCapability(edition, capability) {
  if (!edition || typeof capability !== 'string') return false

  const registeredEdition = editions.find((entry) => (
    entry.id === edition.id && entry.slug === edition.slug
  ))

  if (registeredEdition) return registeredEdition.capabilities.includes(capability)
  return /^premier-league(?:-\d{4}-\d{2})?$/.test(edition.slug) && ['table', 'fixtures', 'predictions', 'markets'].includes(capability)
}
