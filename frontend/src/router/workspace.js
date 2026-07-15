import { listCompetitionEditions } from '../competition/index.js'
import { DEFAULT_LOCALE } from '../i18n/index.js'

const [defaultCompetitionEdition] = listCompetitionEditions()

if (!defaultCompetitionEdition) {
  throw new Error('At least one Competition Edition is required for workspace routing')
}

export const DEFAULT_COMPETITION_EDITION_SLUG = defaultCompetitionEdition.slug

export const WORKSPACE_ROUTE_NAMES = Object.freeze({
  overview: 'competition-workspace-overview',
  groups: 'competition-workspace-groups',
  predict: 'competition-workspace-predict',
  bracket: 'competition-workspace-bracket',
  markets: 'competition-workspace-markets',
})

export function workspaceLocation(area = 'overview', {
  locale = DEFAULT_LOCALE,
  competitionEditionSlug = DEFAULT_COMPETITION_EDITION_SLUG,
  query,
  hash,
} = {}) {
  const name = WORKSPACE_ROUTE_NAMES[area]
  if (!name) throw new Error(`Unknown Competition Workspace area: ${area}`)

  return {
    name,
    params: { locale, competitionEditionSlug },
    ...(query ? { query } : {}),
    ...(hash ? { hash } : {}),
  }
}
