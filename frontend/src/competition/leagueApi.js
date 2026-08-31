import { leagueIdentity } from './index.js'

export function leagueApiBase(slug) {
  const identity = leagueIdentity(slug)
  if (!identity) return '/api/leagues/premier-league/active'
  return identity.season
    ? `/api/leagues/${identity.competition}/${identity.season}`
    : `/api/leagues/${identity.competition}/active`
}
