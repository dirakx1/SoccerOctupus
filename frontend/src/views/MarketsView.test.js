import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MarketsView from './MarketsView.vue'
import { applyLocale, i18n } from '../i18n/index.js'

const billingState = vi.hoisted(() => ({ actionLoading: { value: false, __v_isRef: true }, openBillingRecovery: vi.fn() }))
vi.mock('../lib/api', () => ({ api: { get: vi.fn(), post: vi.fn() } }))
vi.mock('../composables/useBillingStatus', () => ({ useBillingStatus: () => billingState }))
import { api } from '../lib/api'

const teams = [{ name: 'Germany', elo: 1880 }, { name: 'Brazil', elo: 1950 }]
const binary = { question_id:'Q-1',market_type:'binary',prop_type:'match_winner',question:'Generated English question remains verbatim.',yes_probability:.6,no_probability:.4,pricing:{kalshi_yes_cents:60,kalshi_no_cents:40,polymarket_yes_usdc:.6,polymarket_no_usdc:.4},resolution:{date:'2026-07-08',criteria:'Generated criteria remains verbatim.'} }
const matchResult = { prediction_summary:{home_win_prob:.6,draw_prob:.2,away_win_prob:.2,most_likely_score:'2-1'},total_questions:2,questions:[binary,{...binary,question_id:'Q-2',prop_type:'draw'}] }
const tournamentResult = { simulation:{champion:'Brazil',champion_probability:.3125},total_questions:3,questions:[{market_type:'categorical',prop_type:'tournament_winner',outcomes:[{outcome:'Brazil',probability:.3125}]},{...binary,question_id:'F-1',prop_type:'reach_stage'}] }
const RouterLinkStub = { props:['to'], template:'<a><slot /></a>' }
const mountMarkets = () => mount(MarketsView, { global:{ plugins:[i18n], stubs:{ RouterLink:RouterLinkStub } } })

describe('MarketsView', () => {
  beforeEach(() => { vi.clearAllMocks(); applyLocale('en',{storage:window.localStorage,documentElement:document.documentElement}); api.get.mockResolvedValue({data:{teams}}); api.post.mockResolvedValue({data:matchResult}) })

  it('loads and sorts teams, and localizes locale-aware ELO values', async () => {
    applyLocale('es',{storage:window.localStorage,documentElement:document.documentElement})
    const wrapper=mountMarkets(); await flushPromises()
    expect(api.get).toHaveBeenCalledWith('/api/predictions/teams')
    expect(wrapper.text()).toContain('Ponle precio a la predicción.')
    expect(wrapper.find('[data-testid="home-team"]').findAll('option').slice(1).map(o=>o.text())).toEqual(['Brazil (ELO 1950)','Germany (ELO 1880)'])
  })

  it('shows loading, empty, error and retry states for teams', async () => {
    api.get.mockImplementation(()=>new Promise(()=>{})); const loading=mountMarkets(); expect(loading.find('[data-testid="team-loading"]').exists()).toBe(true); loading.unmount()
    api.get.mockResolvedValueOnce({data:{teams:[]}}); const empty=mountMarkets(); await flushPromises(); expect(empty.text()).toContain('No teams are available.'); empty.unmount()
    api.get.mockClear(); api.get.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({data:{teams}}); const error=mountMarkets(); await flushPromises(); expect(error.text()).toContain("We couldn't load the team list."); await error.find('[data-testid="retry-teams"]').trigger('click'); await flushPromises(); expect(api.get).toHaveBeenCalledTimes(2)
  })

  it('validates distinct teams and preserves the exact match POST contract', async () => {
    const wrapper=mountMarkets(); await flushPromises(); await wrapper.find('[data-testid="home-team"]').setValue('Brazil'); await wrapper.find('[data-testid="away-team"]').setValue('Brazil'); expect(wrapper.text()).toContain('Home and away teams must be different.'); expect(wrapper.find('[data-testid="run-match"]').attributes('disabled')).toBeDefined()
    await wrapper.find('[data-testid="away-team"]').setValue('Germany'); await wrapper.find('[data-testid="match-stage"]').setValue('quarter_final'); await wrapper.find('form').trigger('submit'); await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/api/markets/match',{home_team:'Brazil',away_team:'Germany',stage:'quarter_final'})
    expect(wrapper.text()).toContain('Generated English question remains verbatim.')
    expect(wrapper.text()).toContain('2 market questions')
  })

  it('keeps a stable match loading state and renders inline run errors', async () => {
    let reject; api.post.mockImplementation(()=>new Promise((_,r)=>{reject=r})); const wrapper=mountMarkets(); await flushPromises(); await wrapper.find('[data-testid="home-team"]').setValue('Brazil'); await wrapper.find('[data-testid="away-team"]').setValue('Germany'); await wrapper.find('form').trigger('submit'); expect(wrapper.text()).toContain('This can take several minutes.')
    reject(new Error('swarm failed')); await flushPromises(); expect(wrapper.text()).toContain('swarm failed')
  })

  it.each(['subscription_required','billing_payment_required','feature_limit_reached'])('shows plan recovery for billing code %s', async code => {
    api.post.mockRejectedValue({response:{data:{code,error:'Upgrade required'}}}); const wrapper=mountMarkets(); await flushPromises(); await wrapper.find('[data-testid="home-team"]').setValue('Brazil'); await wrapper.find('[data-testid="away-team"]').setValue('Germany'); await wrapper.find('form').trigger('submit'); await flushPromises(); expect(wrapper.text()).toContain('View pricing')
  })

  it('filters match questions with selected state and counts', async () => {
    const wrapper=mountMarkets(); await flushPromises(); await wrapper.find('[data-testid="home-team"]').setValue('Brazil'); await wrapper.find('[data-testid="away-team"]').setValue('Germany'); await wrapper.find('form').trigger('submit'); await flushPromises(); const draw=wrapper.findAll('.filter-bar button').find(b=>b.text().includes('Draw')); expect(draw.text()).toContain('1'); await draw.trigger('click'); expect(draw.attributes('aria-pressed')).toBe('true'); expect(wrapper.text()).toContain('Q-2'); expect(wrapper.text()).not.toContain('Q-1')
  })

  it('uses accessible tabs and invokes tournament POST without a body', async () => {
    api.post.mockResolvedValue({data:tournamentResult}); const wrapper=mountMarkets(); await flushPromises(); const tab=wrapper.find('#tournament-tab'); await tab.trigger('click'); expect(tab.attributes('aria-selected')).toBe('true'); await wrapper.find('[data-testid="run-tournament"]').trigger('click'); await flushPromises(); expect(api.post).toHaveBeenCalledWith('/api/markets/tournament'); expect(wrapper.text()).toContain('Brazil'); expect(wrapper.text()).toContain('31.3%'); expect(wrapper.text()).toContain('31.3¢'); expect(wrapper.text()).toContain('$0.3125')
  })
})
