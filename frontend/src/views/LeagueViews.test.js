import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { applyLocale, i18n } from '../i18n/index.js'
import LeaguePredictView from './LeaguePredictView.vue'
import LeagueMarketsView from './LeagueMarketsView.vue'
import LeagueTableView from './LeagueTableView.vue'
import LeagueFixturesView from './LeagueFixturesView.vue'
import LeagueOverviewView from './LeagueOverviewView.vue'
import LeaguePerformanceView from './LeaguePerformanceView.vue'

const route = { params: { locale: 'en', competitionEditionSlug: 'premier-league' } }
vi.mock('vue-router', () => ({ useRoute: () => route }))
vi.mock('../lib/api', () => ({ api: { get: vi.fn(), post: vi.fn() } }))
import { api } from '../lib/api'

const fixture = { id: 'f1', kickoff: '2099-08-30T14:00:00+00:00', status: 'scheduled', matchweek: 1, homeTeam: { id: '1', name: 'Arsenal' }, awayTeam: { id: '2', name: 'Chelsea' } }
const prediction = {
  modelVersion: 'league-poisson-2026.1', confidence: .6, homeTeam: fixture.homeTeam, awayTeam: fixture.awayTeam,
  likelyScore: { home: 1, away: 0 }, expectedGoals: { home: 1.4, away: .9 }, probabilities: { home: .6, draw: .22, away: .18 },
  scoreProbabilities: [{ score: '1-0', home: 1, away: 0, probability: .2 }], markets: { bothTeamsToScoreYes: .5, over2_5: .4, homeCleanSheet: .45, awayCleanSheet: .25 },
  analysis: { summary: 'Arsenal has the highest baseline outcome probability.', keyFactors: ['Expected goals favor Arsenal.'], signals: [{ name: 'Statistical strength', reason: 'Expected goals favor Arsenal.', sources: ['ESPN'] }] },
  evidence: { providerEvidence: [{ provider: 'FotMob', status: 'admitted', source: 'test', fetchedAt: '2099-08-01T00:00:00Z', reason: 'verified', evidence: { Arsenal: { stats: { rating_team: 7.2 } } } }] },
}

describe('League views', () => {
  beforeEach(() => { vi.clearAllMocks(); applyLocale('en', { storage: window.localStorage, documentElement: document.documentElement }) })

  it('renders the fixture-bound forecast in plain language', async () => {
    api.get.mockResolvedValue({ data: { fixtures: [fixture] } }); api.post.mockResolvedValue({ data: { prediction } })
    const wrapper = mount(LeaguePredictView, { global: { plugins: [i18n] } }); await flushPromises(); await wrapper.find('form').trigger('submit'); await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/api/leagues/active/predict', { fixtureId: 'f1' })
    expect(wrapper.text()).toContain('Read the match before it starts.'); expect(wrapper.text()).toContain('Forecast confidence'); expect(wrapper.text()).toContain('Top scorelines'); expect(wrapper.text()).toContain('Forecast summary'); expect(wrapper.text()).toContain('Model breakdown'); expect(wrapper.text()).toContain('Expected goals favor Arsenal.'); expect(wrapper.text()).not.toContain('FotMob')
  })

  it('selects an upcoming fixture and renders its league market cards', async () => {
    const question = { question_id: 'premier-league-2026-27-f1-home-win', prop_type: 'match_winner', question: 'Will Arsenal beat Chelsea?', yes_probability: .6, no_probability: .4, tags: ['premier-league', '2026-27', 'f1'], pricing: { kalshi_yes_cents: 60, kalshi_no_cents: 40, polymarket_yes_usdc: .6, polymarket_no_usdc: .4 }, resolution: { date: '2099-08-30', criteria: 'ESPN result' } }
    const seasonQuestion = { question_id: 'premier-league-2026-27-1-tournament-winner', prop_type: 'tournament_winner', question: 'Will Arsenal win the Premier League in 2026-27?', yes_probability: .4, no_probability: .6, tags: ['premier-league', '2026-27', '1'], pricing: { kalshi_yes_cents: 40, kalshi_no_cents: 60, polymarket_yes_usdc: .4, polymarket_no_usdc: .6 }, resolution: { date: '2027-05-31', criteria: 'ESPN table' } }
    api.get.mockResolvedValue({ data: { seasonMarkets: [{ team: fixture.homeTeam, championProbability: .4, topFourProbability: .8, relegationProbability: .01 }], seasonQuestions: [seasonQuestion], fixtureMarkets: [{ fixture: 'f1', kickoff: fixture.kickoff, homeTeam: fixture.homeTeam, awayTeam: fixture.awayTeam }] } })
    api.post.mockImplementation((url) => url.endsWith('/season')
      ? Promise.resolve({ data: { seasonMarkets: [{ team: fixture.homeTeam, championProbability: .4, topFourProbability: .8, relegationProbability: .01 }], seasonQuestions: [seasonQuestion] } })
      : Promise.resolve({ data: { fixture, questions: [question] } }))
    const wrapper = mount(LeagueMarketsView, { global: { plugins: [i18n] } }); await flushPromises()
    expect(api.post).not.toHaveBeenCalled(); expect(wrapper.text()).toContain('Choose a fixture, then generate its market questions.'); expect(wrapper.text()).toContain('Prices are reference values for listing formats, not live offers.')
    await wrapper.find('#league-match-panel button').trigger('click')
    expect(api.post).toHaveBeenCalledWith('/api/leagues/active/markets/match', { fixtureId: 'f1' }); await flushPromises(); expect(wrapper.text()).toContain('Will Arsenal beat Chelsea?')
    await wrapper.find('#league-season-tab').trigger('click'); await wrapper.find('#league-season-panel button').trigger('click'); await flushPromises(); expect(api.post).toHaveBeenCalledWith('/api/leagues/active/markets/season'); expect(wrapper.text()).toContain('Will Arsenal win the Premier League in 2026-27?')
    await wrapper.find('#league-season-tab').trigger('click')
    expect(wrapper.find('#league-season-tab').attributes('aria-selected')).toBe('true'); expect(wrapper.find('#league-season-panel').isVisible()).toBe(true); expect(wrapper.find('#league-match-panel').isVisible()).toBe(false)
  })

  it('offers pricing recovery when a league market limit is exhausted', async () => {
    api.get.mockResolvedValue({ data: { fixtureMarkets: [{ fixture: 'f1', kickoff: fixture.kickoff, homeTeam: fixture.homeTeam, awayTeam: fixture.awayTeam }] } })
    api.post.mockRejectedValue({ response: { data: { error: 'Match market limit reached', code: 'feature_limit_reached' } } })
    const wrapper = mount(LeagueMarketsView, { global: { plugins: [i18n] } }); await flushPromises(); await wrapper.find('#league-match-panel button').trigger('click'); await flushPromises()
    expect(wrapper.text()).toContain('Match market limit reached'); expect(wrapper.text()).toContain('View pricing')
  })

  it('renders the current standings without generating a projection', async () => {
    api.get.mockImplementation((url) => url.endsWith('/table')
      ? Promise.resolve({ data: { standings: [{ teamId: '1', position: 1, played: 10, won: 8, drawn: 1, lost: 1, goalsFor: 20, goalsAgainst: 5, goalDifference: 15, points: 25, team: fixture.homeTeam }] } })
      : Promise.resolve({ data: { projection: [{ team: fixture.homeTeam, expectedPoints: 80, expectedPosition: 1.2, likelyPosition: 1, centralFinishingRange: { low: 1, high: 3 }, championProbability: .5, topFourProbability: .8, relegationProbability: .01, positionDistribution: { '1': .5, '2': .3 } }] } }))
    const wrapper = mount(LeagueTableView, { global: { plugins: [i18n] } }); await flushPromises()
    expect(wrapper.text()).toContain('Arsenal'); expect(wrapper.text()).toContain('20'); expect(wrapper.text()).not.toContain('Position distribution'); expect(api.get).toHaveBeenCalledTimes(1)
  })

  it('shows the current league state on the overview', async () => {
    api.get.mockResolvedValue({ data: { teams: [], fixtures: [], standings: [], evidence: { completedMatches: 14, forecast: { sampleSize: 42, status: 'available' } } } })
    const wrapper = mount(LeagueOverviewView, { global: { plugins: [i18n] } }); await flushPromises()
    expect(wrapper.text()).toContain('Premier League 2026–27'); expect(wrapper.text()).toContain('Follow the table'); expect(wrapper.text()).toContain('Current table'); expect(wrapper.text()).toContain('Next fixtures'); expect(wrapper.text()).toContain('Five signals, one league forecast.'); expect(wrapper.text()).not.toContain('Resolved forecast sample available')
  })

  it('shows the provider calibration status from immutable forecast snapshots', async () => {
    api.get.mockResolvedValue({ data: { performance: { snapshots: 12, resolvedSnapshots: 4, accuracy: { correctOutcomeRate: .5, status: 'insufficient' }, baseline: { provider: 'ESPN baseline', weight: 1 }, providers: [{ provider: 'FotMob', snapshots: 4, resolvedSnapshots: 2, statuses: { admitted: 3, unavailable: 1 }, admission: 'collecting', weight: 0 }] } } })
    const wrapper = mount(LeaguePerformanceView, { global: { plugins: [i18n] } }); await flushPromises()
    expect(api.get).toHaveBeenCalledWith('/api/leagues/active/performance'); expect(wrapper.text()).toContain('Model performance'); expect(wrapper.text()).toContain('FotMob'); expect(wrapper.text()).toContain('Collecting evidence')
  })

  it('filters fixtures, groups missing matchweeks by month, and bounds the initial list', async () => {
    const club = (id, name) => ({ id, name })
    const scheduled = Array.from({ length: 31 }, (_, index) => ({ id: `scheduled-${index}`, kickoff: `2099-${index < 15 ? '01' : '02'}-${String((index % 15) + 1).padStart(2, '0')}T14:00:00+00:00`, status: 'scheduled', matchweek: null, homeTeam: club('1', 'Arsenal'), awayTeam: club('2', 'Chelsea') }))
    scheduled.push({ id: 'club-filter', kickoff: '2099-02-20T14:00:00+00:00', status: 'scheduled', matchweek: null, homeTeam: club('3', 'Leeds'), awayTeam: club('2', 'Chelsea') })
    const completed = { id: 'completed', kickoff: '2099-01-01T14:00:00+00:00', status: 'completed', matchweek: null, homeScore: 2, awayScore: 0, homeTeam: club('4', 'Liverpool'), awayTeam: club('1', 'Arsenal') }
    api.get.mockResolvedValue({ data: { fixtures: [completed, ...scheduled] } })
    const wrapper = mount(LeagueFixturesView, { global: { plugins: [i18n] } }); await flushPromises()
    expect(wrapper.findAll('li')).toHaveLength(30); expect(wrapper.findAll('li').some((item) => item.text().includes('Liverpool'))).toBe(false); expect(wrapper.text()).toContain('January 2099'); expect(wrapper.text()).toContain('February 2099'); expect(wrapper.find('button').text()).toContain('Show more')
    await wrapper.find('#fixture-club').setValue('3')
    expect(wrapper.findAll('li')).toHaveLength(1); expect(wrapper.find('li').text()).toContain('Leeds')
  })
})
