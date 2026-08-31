import { leagueIdentity, listCompetitionEditions, supportsCapability } from '../competition/index.js'
import { DEFAULT_LOCALE, normalizeLocale } from '../i18n/index.js'

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
  swarm: 'competition-workspace-swarm',
})

export const HISTORIC_WORKSPACE_ROUTE_NAMES = Object.freeze({
  overview: 'historic-competition-workspace-overview',
  groups: 'historic-competition-workspace-groups',
  predict: 'historic-competition-workspace-predict',
  bracket: 'historic-competition-workspace-bracket',
  markets: 'historic-competition-workspace-markets',
  swarm: 'historic-competition-workspace-swarm',
})

export const LEAGUE_ROUTE_NAMES = Object.freeze({
  overview: 'league-workspace-overview',
  table: 'league-workspace-table',
  fixtures: 'league-workspace-fixtures',
  predict: 'league-workspace-predict',
  markets: 'league-workspace-markets',
  performance: 'league-workspace-performance',
  swarm: 'league-workspace-swarm',
})

export function workspaceLocation(area = 'overview', {
  locale = DEFAULT_LOCALE,
  competitionEditionSlug = DEFAULT_COMPETITION_EDITION_SLUG,
  query,
  hash,
  historic = false,
} = {}) {
  const names = (historic || competitionEditionSlug === 'world-cup-2026')
    ? HISTORIC_WORKSPACE_ROUTE_NAMES
    : leagueIdentity(competitionEditionSlug)
    ? LEAGUE_ROUTE_NAMES
    : WORKSPACE_ROUTE_NAMES
  const name = names[area]
  if (!name) throw new Error(`Unknown Competition Workspace area: ${area}`)

  return {
    name,
    params: { locale, competitionEditionSlug },
    ...(query ? { query } : {}),
    ...(hash ? { hash } : {}),
  }
}

export function workspaceLocaleLocation(route, locale) {
  const nextLocale = normalizeLocale(locale)
  if (!nextLocale || !route?.name || !route.meta?.competitionWorkspace) return null

  return {
    name: route.name,
    params: { ...route.params, locale: nextLocale },
    query: route.query,
    hash: route.hash,
  }
}

const AREA_CAPABILITIES = Object.freeze({ groups: 'groups', table: 'table', fixtures: 'fixtures', predict: 'predictions', bracket: 'bracket', markets: 'markets', swarm: 'swarm', performance: 'performance' })

export function workspaceSwitchLocation(route, edition) {
  if (!route?.meta?.competitionWorkspace || !edition?.slug) return null
  const area = Object.entries(WORKSPACE_ROUTE_NAMES).find(([, name]) => name === route.name)?.[0]
    || Object.entries(HISTORIC_WORKSPACE_ROUTE_NAMES).find(([, name]) => name === route.name)?.[0]
    || Object.entries(LEAGUE_ROUTE_NAMES).find(([, name]) => name === route.name)?.[0]
    || 'overview'
  const selectedArea = area === 'overview' || supportsCapability(edition, AREA_CAPABILITIES[area]) ? area : 'overview'
  return workspaceLocation(selectedArea, {
    locale: route.params.locale,
    competitionEditionSlug: edition.slug,
    query: route.query,
    hash: route.hash,
    historic: Boolean(route.meta.historicWorkspace && edition.competitionId === 'fifa-world-cup'),
  })
}
