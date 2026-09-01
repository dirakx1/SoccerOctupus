<template>
  <main class="prediction-page league-prediction-page">
    <AtlasPageHeader
      :eyebrow="t('competitions.league.predictionEyebrow', { competition: t(edition.displayNameKey) })"
      :title="t('competitions.league.predictionTitle')"
      :description="t('competitions.league.predictionDescription')"
    />

    <section v-if="loadingFixtures" class="prediction-form prediction-form-skeleton" aria-busy="true">
      <div class="selector-skeletons" aria-hidden="true">
        <div class="skeleton-field"><span class="skeleton-line skeleton-label" /><span class="skeleton-line skeleton-select" /></div>
      </div>
      <div class="form-footer" aria-hidden="true"><span class="skeleton-line skeleton-footer-copy" /><span class="skeleton-line skeleton-action" /></div>
    </section>

    <section v-else-if="loadError" class="page-state state-error" role="alert">
      <AlertTriangle :size="22" aria-hidden="true" />
      <div>
        <h2>{{ t('competitions.league.loadFailed') }}</h2>
        <p>{{ loadError }}</p>
        <button type="button" @click="loadFixtures"><RotateCcw :size="16" aria-hidden="true" />{{ t('competitions.league.retry') }}</button>
      </div>
    </section>

    <section v-else-if="!fixtureGroups.length" class="page-state" aria-live="polite">
      <Inbox :size="22" aria-hidden="true" />
      <div><h2>{{ t('competitions.league.noUpcomingTitle') }}</h2><p>{{ t('competitions.league.noUpcoming') }}</p></div>
    </section>

    <form v-else class="prediction-form" @submit.prevent="submit">
      <div class="match-selectors">
        <label for="league-fixture">
          <span>{{ t('competitions.league.fixtureLabel') }}</span>
          <span class="select-field">
            <select id="league-fixture" v-model="fixtureId">
              <optgroup v-for="group in fixtureGroups" :key="group.label" :label="group.label">
                <option v-for="fixture in group.fixtures" :key="fixture.id" :value="fixture.id">
                  {{ fixture.homeTeam.name }} {{ t('competitions.league.versus') }} {{ fixture.awayTeam.name }} · {{ formatKickoff(fixture.kickoff) }}
                </option>
              </optgroup>
            </select>
            <ChevronDown :size="18" aria-hidden="true" />
          </span>
        </label>
      </div>
      <div class="form-footer">
        <p>{{ t('competitions.league.predictionFormHint') }}</p>
        <button class="run-button" type="submit" :disabled="loading || !fixtureId">
          <LoaderCircle v-if="loading" :size="18" class="spin" aria-hidden="true" />
          <Sparkles v-else :size="18" aria-hidden="true" />
          {{ loading ? t('competitions.league.predicting') : t('competitions.league.runPrediction') }}
        </button>
      </div>
    </form>

    <section v-if="loading" class="prediction-loading" aria-busy="true">
      <div><h2>{{ t('competitions.league.predictionLoadingTitle') }}</h2><p>{{ t('competitions.league.predictionLoadingDescription') }}</p></div>
      <div class="result-skeleton" aria-hidden="true"><span /><span /><span /></div>
    </section>

    <section v-if="error" class="run-error" role="alert">
      <AlertTriangle :size="22" aria-hidden="true" />
      <div>
        <h2>{{ t('competitions.league.predictionFailedTitle') }}</h2>
        <p>{{ error }}</p>
        <BillingPlansLink v-if="limitReached" />
      </div>
    </section>

    <article v-if="result" class="prediction-result" :aria-label="t('competitions.league.predictionResult')">
      <header class="result-scoreboard">
        <div class="result-team" :class="{ winner: result.outcome === 'home_win' }">{{ result.homeTeam.name }}</div>
        <div class="score-block">
          <strong>{{ result.likelyScore.home }}–{{ result.likelyScore.away }}</strong>
          <span>{{ t('competitions.league.likelyScore') }}</span>
        </div>
        <div class="result-team result-team-away" :class="{ winner: result.outcome === 'away_win' }">{{ result.awayTeam.name }}</div>
      </header>

      <section class="result-section probability-section">
        <ProbMeter
          :home-team="result.homeTeam.name"
          :away-team="result.awayTeam.name"
          :home-pct="result.probabilities.home"
          :draw-pct="result.probabilities.draw"
          :away-pct="result.probabilities.away"
          :outcome="result.outcome"
          :agent-count="modelSignals.length"
        />
      </section>

      <section class="evidence-strip" :aria-label="t('competitions.league.predictionEvidence')">
        <div>
          <span>{{ t('competitions.league.forecastConfidence') }}</span>
          <strong>{{ percent(result.confidence) }}</strong>
          <i aria-hidden="true"><b :style="{ width: percent(result.confidence) }" /></i>
        </div>
        <div>
          <span>{{ t('competitions.league.expectedGoals') }}</span>
          <strong>{{ decimal(result.expectedGoals.home) }} / {{ decimal(result.expectedGoals.away) }}</strong>
          <small>{{ result.homeTeam.name }} / {{ result.awayTeam.name }}</small>
        </div>
        <div v-if="topScoreProbability">
          <span>{{ t('competitions.league.likelyScore') }}</span>
          <strong>{{ topScoreProbability.score }} / {{ percent(topScoreProbability.probability) }}</strong>
          <small>{{ t('competitions.league.topScorelines') }}</small>
        </div>
        <div>
          <span>{{ t('competitions.league.completedEvidence') }}</span>
          <strong>{{ integer(result.evidence?.completedMatches || 0) }}</strong>
          <small>{{ t('competitions.league.completedEvidenceCaption') }}</small>
        </div>
      </section>

      <section v-if="result.scoreProbabilities?.length" class="result-section score-probabilities">
        <header><Target :size="19" aria-hidden="true" /><h2>{{ t('competitions.league.topScorelines') }}</h2></header>
        <div class="score-probability-list">
          <div v-for="(score, index) in result.scoreProbabilities" :key="score.score" :class="{ top: index === 0 }">
            <strong>{{ score.score }}</strong>
            <i aria-hidden="true"><b :style="{ width: scoreBarWidth(score.probability) }" /></i>
            <span>{{ percent(score.probability) }}</span>
            <small v-if="index === 0">{{ t('competitions.league.mostLikely') }}</small>
          </div>
        </div>
      </section>

      <div v-if="result.analysis" class="analysis-layout">
        <section class="result-section narrative-section">
          <header><BrainCircuit :size="19" aria-hidden="true" /><h2>{{ t('competitions.league.forecastSummary') }}</h2></header>
          <p>{{ result.analysis.summary }}</p>
        </section>
        <section v-if="result.analysis.keyFactors?.length" class="result-section factors-section">
          <header><ListChecks :size="19" aria-hidden="true" /><h2>{{ t('competitions.league.keyFactors') }}</h2></header>
          <ul><li v-for="factor in result.analysis.keyFactors" :key="factor">{{ factor }}</li></ul>
        </section>
      </div>

      <section v-if="modelSignals.length" class="result-section signals-section">
        <header><Users :size="19" aria-hidden="true" /><h2>{{ t('competitions.league.modelBreakdown') }}</h2></header>
        <div class="signal-list">
          <article v-for="signal in modelSignals" :key="signal.name" class="signal-row">
            <div class="signal-heading">
              <h3>{{ signal.name }}</h3>
              <span>{{ signalDirection(signal.direction) }}</span>
            </div>
            <p>{{ signal.reason }}</p>
          </article>
        </div>
      </section>
    </article>
  </main>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { AlertTriangle, BrainCircuit, ChevronDown, Inbox, ListChecks, LoaderCircle, RotateCcw, Sparkles, Target, Users } from '@lucide/vue'

import AtlasPageHeader from '../ui/patterns/AtlasPageHeader.vue'
import BillingPlansLink from '../components/BillingPlansLink.vue'
import ProbMeter from '../components/ProbMeter.vue'
import { getCompetitionEdition } from '../competition/index.js'
import { leagueApiBase } from '../competition/leagueApi.js'
import { api } from '../lib/api'

const { t, locale } = useI18n()
const route = useRoute()
const fixtures = ref([])
const fixtureId = ref('')
const result = ref(null)
const error = ref('')
const loadError = ref('')
const loadingFixtures = ref(true)
const loading = ref(false)
const limitReached = ref(false)

const edition = computed(() => getCompetitionEdition(route.params.competitionEditionSlug))
const futureFixtures = computed(() => fixtures.value.filter((fixture) => fixture.status === 'scheduled' && new Date(fixture.kickoff).getTime() > Date.now()))
const fixtureGroups = computed(() => {
  const groups = new Map()
  for (const fixture of futureFixtures.value) {
    const label = t('competitions.league.matchweek', { week: fixture.matchweek || t('competitions.league.upcoming') })
    if (!groups.has(label)) groups.set(label, [])
    groups.get(label).push(fixture)
  }
  return [...groups].map(([label, grouped]) => ({ label, fixtures: grouped }))
})
const modelSignals = computed(() => result.value?.analysis?.signals || [])
const topScoreProbability = computed(() => result.value?.scoreProbabilities?.[0] || null)

async function loadFixtures() {
  loadingFixtures.value = true
  loadError.value = ''
  error.value = ''
  result.value = null
  try {
    fixtures.value = (await api.get(leagueApiBase(route.params.competitionEditionSlug))).data.fixtures || []
    fixtureId.value = futureFixtures.value[0]?.id || ''
  } catch (cause) {
    loadError.value = cause.response?.data?.error || t('competitions.league.loadFailed')
  } finally {
    loadingFixtures.value = false
  }
}

async function submit() {
  loading.value = true
  error.value = ''
  result.value = null
  limitReached.value = false
  try {
    result.value = (await api.post(`${leagueApiBase(route.params.competitionEditionSlug)}/predict`, { fixtureId: fixtureId.value })).data.prediction
  } catch (cause) {
    error.value = cause.response?.data?.error || t('competitions.league.predictionFailed')
    limitReached.value = cause.response?.data?.code === 'feature_limit_reached'
  } finally {
    loading.value = false
  }
}

function formatKickoff(value) { return new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }
function numberFormatter(options) { return new Intl.NumberFormat(locale.value, options) }
function integer(value) { return numberFormatter({ maximumFractionDigits: 0, useGrouping: true }).format(Number(value) || 0) }
function decimal(value) { return numberFormatter({ minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value) || 0) }
function percent(value) { return numberFormatter({ style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(Number(value) || 0) }
function scoreBarWidth(probability) { return topScoreProbability.value?.probability ? `${(probability / topScoreProbability.value.probability) * 100}%` : '0%' }
function signalDirection(direction) { return t(`competitions.league.signalDirection.${['home', 'away', 'neutral'].includes(direction) ? direction : 'neutral'}`) }

watch(() => route.params.competitionEditionSlug, loadFixtures, { immediate: true })
</script>

<style scoped>
.prediction-page { display: flex; flex-direction: column; gap: var(--space-8); }
.prediction-form { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); padding: var(--space-6); }
.prediction-form-skeleton { pointer-events: none; }
.match-selectors { display: grid; grid-template-columns: minmax(0, 1fr); }
.match-selectors label { color: var(--color-text-muted); display: flex; flex-direction: column; font-size: var(--font-size-sm); gap: var(--space-2); }
.match-selectors label > span { font-weight: var(--font-weight-semibold); }
.select-field { display: block; position: relative; width: 100%; }
.select-field svg { color: var(--color-text-muted); pointer-events: none; position: absolute; right: var(--space-4); top: 50%; transform: translateY(-50%); }
.match-selectors select { appearance: none; background: var(--color-surface-raised); border: var(--border-width-thin) solid var(--color-border); border-radius: var(--radius-md); color: var(--color-text); font: var(--font-weight-medium) var(--font-size-sm) / var(--line-height-normal) var(--font-family-body); min-height: var(--control-height-lg); padding: 0 calc(var(--space-4) + 1.5rem) 0 var(--space-3); width: 100%; }
.match-selectors select:hover { border-color: var(--color-border-strong); }
.match-selectors select:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 2px; }
.form-footer { align-items: center; border-top: var(--border-width-thin) solid var(--color-border); display: flex; gap: var(--space-4); justify-content: space-between; margin-top: var(--space-5); padding-top: var(--space-5); }
.form-footer p { color: var(--color-text-muted); font-size: var(--font-size-sm); margin: 0; }
.run-button, .page-state button { align-items: center; background: var(--color-accent); border: 0; border-radius: var(--radius-md); color: var(--color-accent-contrast); cursor: pointer; display: inline-flex; font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); gap: var(--space-2); justify-content: center; min-height: var(--control-height-lg); padding: 0 var(--space-5); }
.run-button:hover:not(:disabled), .page-state button:hover { background: var(--color-accent-hover); }
.run-button:focus-visible, .page-state button:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.run-button:disabled { cursor: not-allowed; opacity: .55; }
.page-state, .prediction-loading, .run-error { align-items: flex-start; background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); display: flex; gap: var(--space-4); padding: var(--space-6); }
.page-state > svg, .run-error > svg { color: var(--color-accent); flex: 0 0 auto; }
.page-state h2, .prediction-loading h2, .run-error h2 { font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0; }
.page-state p, .prediction-loading p, .run-error p { color: var(--color-text-muted); line-height: var(--line-height-relaxed); margin: var(--space-2) 0 0; }
.page-state button { margin-top: var(--space-4); }
.state-error, .run-error { background: var(--color-danger-surface); border-color: var(--color-danger); }
.state-error > svg, .run-error > svg { color: var(--color-danger); }
.prediction-loading { display: grid; grid-template-columns: minmax(14rem, .8fr) minmax(0, 1.2fr); }
.selector-skeletons, .result-skeleton { display: grid; gap: var(--space-3); }
.skeleton-field { display: flex; flex-direction: column; gap: var(--space-2); }
.skeleton-line, .result-skeleton span { animation: skeleton-pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); display: block; }
.skeleton-label { height: 1rem; width: 20%; }
.skeleton-select { height: var(--control-height-lg); width: 100%; }
.skeleton-footer-copy { height: 1rem; width: 16rem; }
.skeleton-action { height: var(--control-height-lg); width: 12rem; }
.result-skeleton span { min-height: var(--control-height-lg); }
.result-skeleton span:first-child { height: 4rem; }
.prediction-result { border-top: var(--border-width-strong) solid var(--color-accent); display: flex; flex-direction: column; }
.result-scoreboard { align-items: center; border-bottom: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-5); grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); min-height: 10rem; padding: var(--space-8) var(--space-4); }
.result-team { font-family: var(--font-family-display); font-size: var(--font-size-2xl); font-weight: var(--font-weight-bold); text-align: right; }
.result-team-away { text-align: left; }
.result-team.winner { color: var(--color-accent); }
.score-block { align-items: center; display: flex; flex-direction: column; min-width: 10rem; text-align: center; }
.score-block strong { color: var(--color-accent); font: var(--font-weight-heavy) var(--font-size-4xl) / var(--line-height-tight) var(--font-family-data); }
.score-block span { color: var(--color-text-muted); font-size: var(--font-size-xs); }
.result-section { border-bottom: var(--border-width-thin) solid var(--color-border); padding: var(--space-6) 0; }
.probability-section { padding-left: var(--space-4); padding-right: var(--space-4); }
.result-section > header { align-items: center; color: var(--color-accent); display: flex; gap: var(--space-2); margin-bottom: var(--space-4); }
.result-section h2 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0; }
.evidence-strip { border-bottom: var(--border-width-thin) solid var(--color-border); border-top: var(--border-width-thin) solid var(--color-border); display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.evidence-strip > div { border-right: var(--border-width-thin) solid var(--color-border); display: flex; flex-direction: column; gap: var(--space-2); min-height: 8rem; padding: var(--space-5); }
.evidence-strip > div:last-child { border-right: 0; }
.evidence-strip span, .evidence-strip small { color: var(--color-text-muted); font-size: var(--font-size-xs); }
.evidence-strip strong { color: var(--color-accent); font: var(--font-weight-heavy) var(--font-size-lg) / var(--line-height-tight) var(--font-family-data); }
.evidence-strip i, .score-probability-list i { background: var(--color-surface-inset); display: block; height: var(--space-1); margin-top: auto; overflow: hidden; }
.evidence-strip i b, .score-probability-list i b { background: var(--color-accent); display: block; height: 100%; }
.score-probability-list { display: flex; flex-direction: column; }
.score-probability-list > div { align-items: center; border-top: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-3); grid-template-columns: 4rem minmax(4rem, 1fr) 5rem 6rem; min-height: var(--control-height-lg); }
.score-probability-list strong, .score-probability-list span { font-family: var(--font-family-data); font-variant-numeric: tabular-nums; }
.score-probability-list span { color: var(--color-text-muted); text-align: right; }
.score-probability-list small { color: var(--color-accent); font-size: var(--font-size-xs); text-align: right; text-transform: uppercase; }
.score-probability-list .top strong, .score-probability-list .top span { color: var(--color-accent); }
.analysis-layout { border-bottom: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-8); grid-template-columns: 1.15fr .85fr; }
.analysis-layout .result-section { border-bottom: 0; }
.narrative-section p { color: var(--color-text-muted); line-height: var(--line-height-relaxed); margin: 0; }
.factors-section ul { display: flex; flex-direction: column; gap: var(--space-3); list-style: none; margin: 0; padding: 0; }
.factors-section li { border-top: var(--border-width-thin) solid var(--color-border); color: var(--color-text-muted); padding-top: var(--space-3); }
.signal-list { border-top: var(--border-width-thin) solid var(--color-border); }
.signal-row { border-bottom: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-3); padding: var(--space-5) 0; }
.signal-heading { align-items: baseline; display: flex; gap: var(--space-4); justify-content: space-between; }
.signal-heading h3 { font-family: var(--font-family-display); font-size: var(--font-size-md); margin: 0; }
.signal-heading span { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); text-transform: uppercase; }
.signal-row p { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-relaxed); margin: 0; }
.spin { animation: prediction-spin .85s linear infinite; }
@keyframes prediction-spin { to { transform: rotate(360deg); } }
@keyframes skeleton-pulse { 50% { opacity: .45; } }
@media (max-width: 900px) { .evidence-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }.evidence-strip > div:nth-child(2) { border-right: 0; }.evidence-strip > div:nth-child(-n + 2) { border-bottom: var(--border-width-thin) solid var(--color-border); } }
@media (max-width: 640px) { .prediction-form { padding: var(--space-4); }.form-footer { align-items: stretch; flex-direction: column; }.run-button { width: 100%; }.prediction-loading { grid-template-columns: 1fr; }.skeleton-footer-copy, .skeleton-action { width: 100%; }.result-scoreboard { grid-template-columns: 1fr; }.result-team, .result-team-away { text-align: center; }.evidence-strip, .analysis-layout { grid-template-columns: 1fr; }.evidence-strip > div { border-bottom: var(--border-width-thin) solid var(--color-border); border-right: 0; }.score-probability-list > div { grid-template-columns: 3rem minmax(3rem, 1fr) 4.5rem; }.score-probability-list small { display: none; }.signal-heading { align-items: flex-start; flex-direction: column; gap: var(--space-2); } }
@media (prefers-reduced-motion: reduce) { .spin, .skeleton-line, .result-skeleton span { animation: none; } }
</style>
