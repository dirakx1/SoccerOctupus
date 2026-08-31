import { worldCup2026 } from './editions/worldCup2026.js'
import { premierLeague202627 } from './editions/premierLeague202627.js'
import { laLiga202627 } from './editions/laLiga202627.js'
import { bundesliga202627 } from './editions/bundesliga202627.js'

const leagueEditions = Object.freeze([premierLeague202627, laLiga202627, bundesliga202627])
const editions = Object.freeze([worldCup2026, ...leagueEditions])
const visibleEditions = Object.freeze([
  // worldCup2026 remains registered for historical routes, but is intentionally hidden from the active switcher.
  ...leagueEditions,
])

const leagueNames = Object.freeze({
  'premier-league': 'Premier League',
  'la-liga': 'La Liga',
  bundesliga: 'Bundesliga',
})

export function leagueIdentity(slug) {
  if (typeof slug !== 'string') return null
  const match = /^(premier-league|la-liga|bundesliga)(?:-(\d{4}-\d{2}))?$/.exec(slug)
  return match ? { competition: match[1], season: match[2] || null } : null
}

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
  const league = leagueIdentity(slug)
  if (league) {
    const registered = leagueEditions.find((entry) => entry.competitionId === league.competition)
    return {
      id: slug,
      competitionId: league.competition,
      slug,
      format: 'league',
      displayName: `${leagueNames[league.competition]}${league.season ? ` ${league.season}` : ''}`,
      displayNameKey: registered.displayNameKey,
      countryKey: registered.countryKey,
      clubCount: registered.clubCount,
      matchdayCount: registered.matchdayCount,
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
  return Boolean(leagueIdentity(edition.slug)) && ['table', 'fixtures', 'predictions', 'markets'].includes(capability)
}
