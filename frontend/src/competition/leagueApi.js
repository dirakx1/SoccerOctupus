export function leagueApiBase(slug) {
  if (slug === 'premier-league') return '/api/leagues/active'
  const match = /^premier-league-(\d{4}-\d{2})$/.exec(slug || '')
  return match ? `/api/leagues/premier-league/${match[1]}` : '/api/leagues/active'
}
