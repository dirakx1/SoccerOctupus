import { worldCup2026 } from './editions/worldCup2026.js'

const editions = Object.freeze([worldCup2026])

function copyEdition(edition) {
  return {
    ...edition,
    capabilities: [...edition.capabilities],
  }
}

export function listCompetitionEditions() {
  return editions.map(copyEdition)
}

export function getCompetitionEdition(slug) {
  const edition = editions.find((entry) => entry.slug === slug)
  return edition ? copyEdition(edition) : null
}

export function supportsCapability(edition, capability) {
  if (!edition || typeof capability !== 'string') return false

  const registeredEdition = editions.find((entry) => (
    entry.id === edition.id && entry.slug === edition.slug
  ))

  return registeredEdition?.capabilities.includes(capability) ?? false
}
