<template>
  <main class="markets-page">
    <AtlasPageHeader :eyebrow="t('markets.eyebrow')" :title="t('markets.title')" :description="t('markets.description')">
      <template #actions>
        <div class="platforms" :aria-label="t('markets.platforms')">
          <a href="https://kalshi.com" target="_blank" rel="noopener">Kalshi <ExternalLink :size="13" />
</a>
          <a href="https://polymarket.com" target="_blank" rel="noopener">Polymarket <ExternalLink :size="13" />
</a>
        </div>
      </template>
    </AtlasPageHeader>

    <p class="platform-note"><Info :size="16" />{{ t('markets.platformNote') }}</p>

    <div class="mode-tabs" role="tablist" :aria-label="t('markets.modes.label')">
      <button id="match-tab" type="button" role="tab" :aria-selected="mode === 'match'" aria-controls="match-panel" @click="mode = 'match'">{{ t('markets.modes.match') }}</button>
      <button id="tournament-tab" type="button" role="tab" :aria-selected="mode === 'tournament'" aria-controls="tournament-panel" @click="mode = 'tournament'">{{ t('markets.modes.tournament') }}</button>
    </div>

    <section v-if="mode === 'match'" id="match-panel" role="tabpanel" aria-labelledby="match-tab" class="mode-panel">
      <section v-if="teamLoading" class="market-form market-form-skeleton" data-testid="team-loading" aria-busy="true">
        <p class="sr-only" aria-live="polite">{{ t('markets.teams.loadingTitle') }} {{ t('markets.teams.loadingBody') }}</p>
        <div class="selectors selector-skeletons" aria-hidden="true">
          <div class="skeleton-field"><span class="skeleton-line skeleton-label"></span><span class="skeleton-line skeleton-select"></span></div>
          <span class="skeleton-line skeleton-versus"></span>
          <div class="skeleton-field"><span class="skeleton-line skeleton-label"></span><span class="skeleton-line skeleton-select"></span></div>
          <div class="skeleton-field"><span class="skeleton-line skeleton-label"></span><span class="skeleton-line skeleton-select"></span></div>
        </div>
        <div class="form-footer" aria-hidden="true"><span class="skeleton-line skeleton-footer-copy"></span><span class="skeleton-line skeleton-action"></span></div>
      </section>
      <section v-else-if="teamError" class="state-panel error-panel"><AlertTriangle /><div><h2>{{ t('markets.teams.errorTitle') }}</h2><p>{{ t('markets.teams.errorBody') }}</p><button type="button" data-testid="retry-teams" @click="loadTeams"><RotateCcw :size="16" />{{ t('markets.teams.retry') }}</button></div></section>
      <section v-else-if="!teams.length" class="state-panel"><Inbox /><div><h2>{{ t('markets.teams.emptyTitle') }}</h2><p>{{ t('markets.teams.emptyBody') }}</p></div></section>
      <form v-else class="market-form" @submit.prevent="runMatchMarkets">
        <div class="selectors">
          <label><span>{{ t('markets.form.home') }}</span><span class="select-field"><select v-model="homeTeam" data-testid="home-team" :aria-invalid="sameTeam"><option value="">{{ t('markets.form.select') }}</option><option v-for="team in teams" :key="team.name" :value="team.name">{{ team.name }} (ELO {{ integer(team.elo) }})</option></select><ChevronDown :size="18" aria-hidden="true" /></span></label>
          <span class="versus">{{ t('markets.form.versus') }}</span>
          <label><span>{{ t('markets.form.away') }}</span><span class="select-field"><select v-model="awayTeam" data-testid="away-team" :aria-invalid="sameTeam"><option value="">{{ t('markets.form.select') }}</option><option v-for="team in teams" :key="team.name" :value="team.name">{{ team.name }} (ELO {{ integer(team.elo) }})</option></select><ChevronDown :size="18" aria-hidden="true" /></span></label>
          <label><span>{{ t('markets.form.stage') }}</span><span class="select-field"><select v-model="stage" data-testid="match-stage"><option v-for="item in stages" :key="item.value" :value="item.value">{{ t(item.label) }}</option></select><ChevronDown :size="18" aria-hidden="true" /></span></label>
        </div>
        <div class="form-footer"><p :class="{ 'is-error': sameTeam }">{{ validationMessage }}</p><button type="submit" data-testid="run-match" :disabled="!canRun || matchLoading"><LoaderCircle v-if="matchLoading" class="spin" :size="17" /><Sparkles v-else :size="17" />{{ matchLoading ? t('markets.form.matchLoading') : t('markets.form.matchAction') }}</button></div>
      </form>

      <RunState v-if="matchLoading" :title="t('markets.form.matchLoading')" :body="t('markets.run.working')" />
      <section v-if="matchError" class="run-error" role="alert"><AlertTriangle /><div><h2>{{ t('markets.run.errorTitle') }}</h2><p>{{ matchError }}</p><BillingStatusNotice v-if="matchBillingHealth?.requires_attention" compact :health="matchBillingHealth" :loading="billingActionLoading" @action="openBillingRecovery('/markets', matchBillingHealth)" /><BillingPlansLink v-else-if="matchSubscriptionRequired" /></div></section>

      <template v-if="matchData && !matchLoading">
        <section class="match-summary" aria-labelledby="match-summary-title"><div><span>{{ t('markets.summary.home') }}</span><strong>{{ percentage(matchData.prediction_summary?.home_win_prob) }}</strong></div><div><span>{{ t('markets.summary.draw') }}</span><strong>{{ percentage(matchData.prediction_summary?.draw_prob) }}</strong></div><div><span>{{ t('markets.summary.away') }}</span><strong>{{ percentage(matchData.prediction_summary?.away_win_prob) }}</strong></div><div class="summary-meta"><h2 id="match-summary-title">{{ homeTeam }} / {{ awayTeam }}</h2><p>{{ t('markets.summary.likelyScore') }} <strong>{{ matchData.prediction_summary?.most_likely_score }}</strong> · {{ t('markets.summary.questions', { count: integer(matchData.total_questions) }) }}</p></div></section>
        <FilterBar :items="matchPropTypes" :selected="matchFilter" :count="matchCountByType" @select="matchFilter = $event" />
        <section v-if="filteredMatchQuestions.length" class="question-list"><MarketCard v-for="question in filteredMatchQuestions" :key="question.question_id" :question="question" /></section>
        <EmptyResults v-else />
      </template>
    </section>

    <section v-else id="tournament-panel" role="tabpanel" aria-labelledby="tournament-tab" class="mode-panel">
      <section class="tournament-run"><div><h2>{{ t('markets.modes.tournament') }}</h2><p>{{ t('markets.form.tournamentDescription') }}</p></div><button type="button" data-testid="run-tournament" :disabled="tourneyLoading" @click="runTournamentMarkets"><LoaderCircle v-if="tourneyLoading" class="spin" :size="17" /><Globe2 v-else :size="17" />{{ tourneyLoading ? t('markets.form.tournamentLoading') : t('markets.form.tournamentAction') }}</button></section>
      <RunState v-if="tourneyLoading" :title="t('markets.form.tournamentLoading')" :body="t('markets.run.working')" />
      <section v-if="tourneyError" class="run-error" role="alert"><AlertTriangle /><div><h2>{{ t('markets.run.errorTitle') }}</h2><p>{{ tourneyError }}</p><BillingStatusNotice v-if="tourneyBillingHealth?.requires_attention" compact :health="tourneyBillingHealth" :loading="billingActionLoading" @action="openBillingRecovery('/markets', tourneyBillingHealth)" /><BillingPlansLink v-else-if="tourneySubscriptionRequired" /></div></section>
      <template v-if="tourneyData && !tourneyLoading">
        <section class="champion-summary"><Trophy /><div><span>{{ t('markets.summary.champion') }}</span><h2>{{ tourneyData.simulation?.champion }}</h2><p>{{ t('markets.summary.championProbability', { probability: percentage(tourneyData.simulation?.champion_probability) }) }} · {{ t('markets.summary.futures', { count: integer(tourneyData.total_questions) }) }}</p></div></section>
        <FilterBar :items="tourneyPropTypes" :selected="tourneyFilter" :count="tourneyCountByType" @select="tourneyFilter = $event" />
        <section v-if="showCategorical && categoricalOutcomes.length" class="winner-section"><h2>{{ t('markets.results.winnerTitle') }}</h2><div class="table-wrap"><table><thead><tr><th>{{ t('markets.results.team') }}</th><th>{{ t('markets.results.probability') }}</th><th>{{ t('markets.results.kalshiYes') }}</th><th>{{ t('markets.results.polymarketYes') }}</th><th>{{ t('markets.results.kalshiNo') }}</th></tr></thead><tbody><tr v-for="outcome in categoricalOutcomes" :key="outcome.outcome"><th scope="row">{{ outcome.outcome }}</th><td>{{ percentage(outcome.probability) }}</td><td>{{ cents(outcome.probability * 100) }}</td><td>{{ usdc(outcome.probability) }}</td><td>{{ cents(100 - outcome.probability * 100) }}</td></tr></tbody></table></div></section>
        <section v-if="filteredTourneyQuestions.length" class="question-list"><MarketCard v-for="question in filteredTourneyQuestions" :key="question.question_id" :question="question" /></section>
        <EmptyResults v-if="!filteredTourneyQuestions.length && (!showCategorical || !categoricalOutcomes.length)" />
      </template>
    </section>
  </main>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertTriangle, ChevronDown, ExternalLink, Globe2, Inbox, Info, LoaderCircle, RotateCcw, Sparkles, Trophy } from '@lucide/vue'
import AtlasPageHeader from '../ui/patterns/AtlasPageHeader.vue'
import BillingStatusNotice from '../components/BillingStatusNotice.vue'
import BillingPlansLink from '../components/BillingPlansLink.vue'
import MarketCard from '../components/MarketCard.vue'
import { useBillingStatus } from '../composables/useBillingStatus'
import { api } from '../lib/api'

const { locale, t } = useI18n()
const mode = ref('match'), teams = ref([]), teamLoading = ref(true), teamError = ref(false), homeTeam = ref(''), awayTeam = ref(''), stage = ref('group')
const matchLoading = ref(false), matchError = ref(''), matchData = ref(null), matchFilter = ref('all'), matchSubscriptionRequired = ref(false), matchBillingHealth = ref(null)
const tourneyLoading = ref(false), tourneyError = ref(''), tourneyData = ref(null), tourneyFilter = ref('all'), tourneySubscriptionRequired = ref(false), tourneyBillingHealth = ref(null)
const { actionLoading: billingActionLoading, openBillingRecovery } = useBillingStatus()
const billingCodes = ['subscription_required', 'billing_payment_required', 'feature_limit_reached']
const stages = [{ value:'group',label:'markets.form.stages.group'},{value:'round_of_32',label:'markets.form.stages.roundOf32'},{value:'round_of_16',label:'markets.form.stages.roundOf16'},{value:'quarter_final',label:'markets.form.stages.quarterFinal'},{value:'semi_final',label:'markets.form.stages.semiFinal'},{value:'final',label:'markets.form.stages.final'}]
const matchPropTypes = ['all','match_winner','draw','btts','over_under','clean_sheet','penalties','correct_score'].map(key => ({ key, label: `markets.filters.${({match_winner:'matchWinner',over_under:'overUnder',clean_sheet:'cleanSheet',correct_score:'correctScore'}[key] || key)}` }))
const tourneyPropTypes = ['all','tournament_winner','reach_stage','group_winner','confederation_win','host_nation','penalties'].map(key => ({ key, label: `markets.filters.${({tournament_winner:'tournamentWinner',reach_stage:'reachStage',group_winner:'groupWinner',confederation_win:'confederationWin',host_nation:'hostNation'}[key] || key)}` }))
const sameTeam = computed(() => Boolean(homeTeam.value && awayTeam.value && homeTeam.value === awayTeam.value)), canRun = computed(() => Boolean(homeTeam.value && awayTeam.value && !sameTeam.value))
const validationMessage = computed(() => sameTeam.value ? t('markets.form.differentTeams') : t('markets.form.selectBoth'))
const allMatchQuestions = computed(() => (matchData.value?.questions || []).filter(q => q.market_type === 'binary'))
const filteredMatchQuestions = computed(() => matchFilter.value === 'all' ? allMatchQuestions.value : allMatchQuestions.value.filter(q => q.prop_type === matchFilter.value))
const allTourneyQuestions = computed(() => (tourneyData.value?.questions || []).filter(q => q.market_type === 'binary'))
const filteredTourneyQuestions = computed(() => tourneyFilter.value === 'all' ? allTourneyQuestions.value : allTourneyQuestions.value.filter(q => q.prop_type === tourneyFilter.value))
const categoricalOutcomes = computed(() => (tourneyData.value?.questions || []).find(q => q.market_type === 'categorical')?.outcomes || [])
const showCategorical = computed(() => ['all','tournament_winner'].includes(tourneyFilter.value))
const matchCountByType = key => key === 'all' ? allMatchQuestions.value.length : allMatchQuestions.value.filter(q => q.prop_type === key).length
const tourneyCountByType = key => key === 'all' ? allTourneyQuestions.value.length : allTourneyQuestions.value.filter(q => q.prop_type === key).length
const number = options => new Intl.NumberFormat(locale.value, options), integer = value => number({ maximumFractionDigits:0 }).format(value ?? 0), percentage = value => value == null ? '—' : number({ style:'percent',minimumFractionDigits:1,maximumFractionDigits:1 }).format(value), cents = value => value == null ? '—' : `${number({minimumFractionDigits:1,maximumFractionDigits:1}).format(value)}¢`, usdc = value => value == null ? '—' : number({style:'currency',currency:'USD',minimumFractionDigits:4,maximumFractionDigits:4}).format(value)

const FilterBar = defineComponent({ props:{items:Array,selected:String,count:Function}, emits:['select'], setup(props,{emit}) { return () => h('div',{class:'filter-bar',role:'group','aria-label':t('markets.filters.label')},props.items.map(item=>h('button',{type:'button','aria-pressed':props.selected===item.key,onClick:()=>emit('select',item.key)},[t(item.label),h('span',props.count(item.key))]))) } })
const RunState = defineComponent({ props:{title:String,body:String}, setup(props){return()=>h('section',{class:'state-panel','aria-busy':'true'},[h(LoaderCircle,{class:'spin'}),h('div',[h('h2',props.title),h('p',props.body)])])} })
const EmptyResults = defineComponent({ setup(){return()=>h('section',{class:'state-panel'},[h(Inbox),h('div',[h('h2',t('markets.results.emptyTitle')),h('p',t('markets.results.emptyBody'))])])} })

async function loadTeams(){teamLoading.value=true;teamError.value=false;try{const response=await api.get('/api/predictions/teams');teams.value=Array.isArray(response.data?.teams)?[...response.data.teams].sort((a,b)=>Number(b.elo)-Number(a.elo)):[]}catch{teams.value=[];teamError.value=true}finally{teamLoading.value=false}}
async function runMatchMarkets(){if(!canRun.value||matchLoading.value)return;matchLoading.value=true;matchError.value='';matchData.value=null;matchFilter.value='all';matchSubscriptionRequired.value=false;matchBillingHealth.value=null;try{matchData.value=(await api.post('/api/markets/match',{home_team:homeTeam.value,away_team:awayTeam.value,stage:stage.value})).data}catch(error){matchError.value=error.response?.data?.error||error.message||t('markets.run.errorFallback');matchBillingHealth.value=error.response?.data?.billing_health||null;matchSubscriptionRequired.value=billingCodes.includes(error.response?.data?.code)}finally{matchLoading.value=false}}
async function runTournamentMarkets(){if(tourneyLoading.value)return;tourneyLoading.value=true;tourneyError.value='';tourneyData.value=null;tourneyFilter.value='all';tourneySubscriptionRequired.value=false;tourneyBillingHealth.value=null;try{tourneyData.value=(await api.post('/api/markets/tournament')).data}catch(error){tourneyError.value=error.response?.data?.error||error.message||t('markets.run.errorFallback');tourneyBillingHealth.value=error.response?.data?.billing_health||null;tourneySubscriptionRequired.value=billingCodes.includes(error.response?.data?.code)}finally{tourneyLoading.value=false}}
onMounted(loadTeams)
</script>

<style scoped>
.markets-page,.mode-panel {
 display:flex;
flex-direction:column;
gap:var(--space-7);
 }
.platforms{
display:flex;
gap:var(--space-2)}
.platforms a{
align-items:center;
border:var(--border-width-thin) solid var(--color-border);
color:var(--color-text);
display:inline-flex;
font-size:var(--font-size-xs);
gap:var(--space-2);
min-height:var(--control-height-lg);
padding:var(--space-2) var(--space-3);
text-decoration:none}
.platforms a:hover{
border-color:var(--color-accent);
color:var(--color-accent)}
.platform-note{
align-items:center;
color:var(--color-text-muted);
display:flex;
font-size:var(--font-size-sm);
gap:var(--space-2);
margin:calc(var(--space-4) * -1) 0 0}
.mode-tabs{
border-bottom:var(--border-width-thin) solid var(--color-border);
display:flex}
.mode-tabs button{
background:transparent;
border:0;
border-bottom:var(--border-width-strong) solid transparent;
color:var(--color-text-muted);
cursor:pointer;
font-weight:var(--font-weight-bold);
min-height:var(--control-height-lg);
padding:0 var(--space-5)}
.mode-tabs button[aria-selected="true"]{
border-bottom-color:var(--color-accent);
color:var(--color-accent)}
.mode-tabs button:focus-visible,.market-form button:focus-visible,.tournament-run button:focus-visible,.state-panel button:focus-visible,.filter-bar button:focus-visible{
outline:var(--border-width-strong) solid var(--color-focus);
outline-offset:2px}
.market-form,.tournament-run,.state-panel,.run-error{
background:var(--color-surface);
border:var(--border-width-thin) solid var(--color-border);
padding:var(--space-6)}
.market-form-skeleton { pointer-events: none; }
.skeleton-line { animation: skeleton-pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); display: block; }
.selector-skeletons .skeleton-field { display: flex; flex-direction: column; gap: var(--space-2); }
.skeleton-label { height: 1rem; width: 38%; }
.skeleton-select { height: var(--control-height-lg); width: 100%; }
.skeleton-versus { align-self: end; height: 1rem; margin-bottom: calc((var(--control-height-lg) - 1rem) / 2); width: 2.75rem; }
.skeleton-footer-copy { height: 1rem; width: 16rem; }
.skeleton-action { height: var(--control-height-lg); width: 12rem; }
.selectors{
align-items:end;
display:grid;
gap:var(--space-4);
grid-template-columns:minmax(0,1fr) auto minmax(0,1fr) minmax(10rem,.55fr)}
.selectors label{
color:var(--color-text-muted);
display:flex;
flex-direction:column;
font-size:var(--font-size-sm);
gap:var(--space-2)}
.selectors label>span{
font-weight:var(--font-weight-semibold)}
.select-field{
display:block;
position:relative;
width:100%}
.select-field svg{
color:var(--color-text-muted);
pointer-events:none;
position:absolute;
right:var(--space-4);
top:50%;
transform:translateY(-50%)}
.select-field select{
appearance:none;
background:var(--color-surface-raised);
border:var(--border-width-thin) solid var(--color-border);
border-radius:var(--radius-md);
color:var(--color-text);
min-height:var(--control-height-lg);
padding:0 calc(var(--space-4) + 1.5rem) 0 var(--space-3);
width:100%}
.versus{
color:var(--color-accent);
font:var(--font-weight-bold) var(--font-size-xs)/var(--control-height-lg) var(--font-family-data)}
.form-footer{
align-items:center;
border-top:var(--border-width-thin) solid var(--color-border);
display:flex;
gap:var(--space-4);
justify-content:space-between;
margin-top:var(--space-5);
padding-top:var(--space-5)}
.form-footer p{
color:var(--color-text-muted);
font-size:var(--font-size-sm);
margin:0}
.form-footer p.is-error{
color:var(--color-danger)}
.form-footer button,.tournament-run button,.state-panel button{
align-items:center;
background:var(--color-accent);
border:0;
border-radius:var(--radius-md);
color:var(--color-accent-contrast);
cursor:pointer;
display:inline-flex;
font-weight:var(--font-weight-bold);
gap:var(--space-2);
justify-content:center;
min-height:var(--control-height-lg);
padding:0 var(--space-5)}
button:disabled{
cursor:not-allowed;
opacity:.55}
.state-panel,.run-error{
align-items:flex-start;
display:flex;
gap:var(--space-4)}
.state-panel h2,.run-error h2,.tournament-run h2{
font-family:var(--font-family-display);
font-size:var(--font-size-xl);
margin:0}
.state-panel p,.run-error p,.tournament-run p{
color:var(--color-text-muted);
line-height:var(--line-height-relaxed);
margin:var(--space-2) 0 0}
.state-panel button{
margin-top:var(--space-4)}
.error-panel,.run-error{
background:var(--color-danger-surface);
border-color:var(--color-danger)}
.error-panel>svg,.run-error>svg{
color:var(--color-danger)}
.match-summary{
border-bottom:var(--border-width-thin) solid var(--color-border);
border-top:var(--border-width-strong) solid var(--color-accent);
display:grid;
grid-template-columns:repeat(3,minmax(5rem,.35fr)) minmax(16rem,1.5fr)}
.match-summary>div{
border-right:var(--border-width-thin) solid var(--color-border);
display:flex;
flex-direction:column;
gap:var(--space-2);
padding:var(--space-5)}
.match-summary>div:last-child{
border-right:0}
.match-summary span,.match-summary p{
color:var(--color-text-muted);
font-size:var(--font-size-xs)}
.match-summary strong{
color:var(--color-accent);
font-family:var(--font-family-data)}
.summary-meta h2{
font-family:var(--font-family-display);
font-size:var(--font-size-lg);
margin:0}
.summary-meta p{
margin:0}
.filter-bar{
display:flex;
flex-wrap:wrap;
gap:var(--space-2)}
.filter-bar button{
align-items:center;
background:var(--color-surface);
border:var(--border-width-thin) solid var(--color-border);
color:var(--color-text-muted);
cursor:pointer;
display:flex;
gap:var(--space-2);
min-height:var(--control-height-lg);
padding:0 var(--space-3)}
.filter-bar button[aria-pressed="true"]{
border-color:var(--color-accent);
color:var(--color-accent)}
.filter-bar span{
background:var(--color-surface-inset);
font-family:var(--font-family-data);
padding:var(--space-1) var(--space-2)}
.question-list{
display:grid;
gap:var(--space-4);
grid-template-columns:repeat(2,minmax(0,1fr))}
.tournament-run{
align-items:center;
display:flex;
gap:var(--space-6);
justify-content:space-between}
.tournament-run p{
max-width:60ch}
.champion-summary{
align-items:center;
border-bottom:var(--border-width-thin) solid var(--color-border);
border-top:var(--border-width-strong) solid var(--color-accent);
display:flex;
gap:var(--space-5);
padding:var(--space-6)}
.champion-summary>svg{
color:var(--color-accent)}
.champion-summary span,.champion-summary p{
color:var(--color-text-muted);
font-size:var(--font-size-sm)}
.champion-summary h2{
font-family:var(--font-family-display);
font-size:var(--font-size-2xl);
margin:var(--space-1) 0}
.champion-summary p{
margin:0}
.winner-section{
border:var(--border-width-thin) solid var(--color-border)}
.winner-section h2{
font-family:var(--font-family-display);
font-size:var(--font-size-xl);
margin:0;
padding:var(--space-5)}
.table-wrap{
overflow-x:auto}
table{
border-collapse:collapse;
min-width:48rem;
width:100%}
th,td{
border-top:var(--border-width-thin) solid var(--color-border);
font-size:var(--font-size-sm);
padding:var(--space-3) var(--space-4);
text-align:right}
th:first-child{
text-align:left}
thead th{
color:var(--color-text-muted);
font-size:var(--font-size-xs)}
tbody th{
font-weight:var(--font-weight-semibold)}
tbody td{
font-family:var(--font-family-data);
font-variant-numeric:tabular-nums}
.spin{
animation:market-spin .85s linear infinite}
@keyframes market-spin{
to{
transform:rotate(360deg)}
}
@keyframes skeleton-pulse{
50%{
opacity:.45}
}
.sr-only{border:0;clip:rect(0 0 0 0);height:1px;margin:-1px;overflow:hidden;padding:0;position:absolute;white-space:nowrap;width:1px}

@media(max-width:860px){
.selectors{
grid-template-columns:minmax(0,1fr) auto minmax(0,1fr)}
.selectors label:last-child{
grid-column:1/-1}
.question-list{
grid-template-columns:1fr}
.match-summary{
grid-template-columns:repeat(3,1fr)}
.summary-meta{
grid-column:1/-1;
border-top:var(--border-width-thin) solid var(--color-border)}
}

@media(max-width:640px){
.platforms{
flex-wrap:wrap}
.mode-tabs button{
flex:1;
padding:0 var(--space-2)}
.selectors{
grid-template-columns:1fr}
.selectors label:last-child{
grid-column:auto}
.versus{
text-align:center}
.form-footer,.tournament-run{
align-items:stretch;
flex-direction:column}
.form-footer button,.tournament-run button{
width:100%}
.skeleton-footer-copy,.skeleton-action{
width:100%}
.match-summary{
grid-template-columns:1fr}
.match-summary>div{
border-bottom:var(--border-width-thin) solid var(--color-border);
border-right:0}
.summary-meta{
grid-column:auto;
border-top:0}
}

@media(prefers-reduced-motion:reduce){
.spin,.skeleton-line{
animation:none}
}

</style>
