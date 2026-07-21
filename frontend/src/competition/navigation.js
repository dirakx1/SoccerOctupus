import { supportsCapability } from './index.js'
import { workspaceLocation } from '../router/workspace.js'

const NAVIGATION_DEFINITIONS = Object.freeze([
  { key: 'overview', capability: null, labelKey: 'navigation.workspace.overview' },
  { key: 'groups', capability: 'groups', labelKey: 'navigation.workspace.groups' },
  { key: 'predict', capability: 'predictions', labelKey: 'navigation.workspace.predict' },
  { key: 'bracket', capability: 'bracket', labelKey: 'navigation.workspace.bracket' },
  { key: 'markets', capability: 'markets', labelKey: 'navigation.workspace.markets' },
])

export function getCompetitionNavigation(edition, {
  locale,
  query,
  hash,
} = {}) {
  if (!edition || typeof edition.slug !== 'string') return []

  return NAVIGATION_DEFINITIONS
    .filter(({ capability }) => !capability || supportsCapability(edition, capability))
    .map(({ key, capability, labelKey }) => ({
      key,
      capability,
      labelKey,
      route: workspaceLocation(key, {
        locale,
        competitionEditionSlug: edition.slug,
        query,
        hash,
      }),
    }))
}
