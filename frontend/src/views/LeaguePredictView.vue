<template>
  <main class="league-view">
    <header class="page-heading">
      <p class="eyebrow">{{ t('competitions.league.predictionEyebrow') }}</p>
      <h1>{{ t('competitions.league.predictionTitle') }}</h1>
      <p>{{ t('competitions.league.predictionDescription') }}</p>
    </header>

    <section v-if="loadingFixtures" class="fixture-form fixture-form-skeleton" aria-busy="true">
      <span class="skeleton-label" aria-hidden="true" />
      <span class="skeleton-select" aria-hidden="true" />
      <span class="skeleton-action" aria-hidden="true" />
    </section>
    <section v-else-if="loadError" class="state-panel state-error" role="alert"><p>{{ loadError }}</p><button type="button" @click="loadFixtures">{{ t('competitions.league.retry') }}</button></section>
    <section v-else-if="!fixtureGroups.length" class="state-panel"><p>{{ t('competitions.league.noUpcoming') }}</p></section>
    <form v-else class="fixture-form" @submit.prevent="submit">
      <label for="league-fixture">{{ t('competitions.league.fixtureLabel') }}</label>
      <span class="select-field"><select id="league-fixture" v-model="fixtureId">
        <optgroup v-for="group in fixtureGroups" :key="group.label" :label="group.label">
          <option v-for="fixture in group.fixtures" :key="fixture.id" :value="fixture.id">{{ fixture.homeTeam.name }} {{ t('competitions.league.versus') }} {{ fixture.awayTeam.name }} · {{ formatKickoff(fixture.kickoff) }}</option>
        </optgroup>
      </select><ChevronDown :size="18" aria-hidden="true" /></span>
      <button type="submit" :disabled="loading || !fixtureId">{{ loading ? t('competitions.league.predicting') : t('competitions.league.runPrediction') }}</button>
    </form>

    <article v-if="loading" class="prediction-result prediction-result-skeleton" aria-busy="true" aria-hidden="true">
      <header class="result-heading"><span class="skeleton-line skeleton-eyebrow" /><span class="skeleton-line skeleton-title" /></header>
      <section class="scoreboard"><div><span class="skeleton-line skeleton-label" /><strong class="skeleton-line skeleton-score" /></div><div><span class="skeleton-line skeleton-label" /><strong class="skeleton-line skeleton-goals" /><small class="skeleton-line skeleton-caption" /></div></section>
      <section class="probability-section"><div v-for="row in 3" :key="row" class="skeleton-probability"><span class="skeleton-line" /><span class="skeleton-line" /></div></section>
      <section class="analysis-grid"><div class="result-card skeleton-panel"><span class="skeleton-line skeleton-panel-title" /><span v-for="row in 4" :key="row" class="skeleton-line skeleton-panel-row" /></div><div class="result-card skeleton-panel"><span class="skeleton-line skeleton-panel-title" /><span v-for="row in 3" :key="row" class="skeleton-line skeleton-panel-row" /></div></section>
    </article>

    <section v-if="error" class="state-panel state-error" role="alert"><p>{{ error }}</p></section>
    <article v-if="result" class="prediction-result" aria-live="polite">
      <header class="result-heading">
        <p class="eyebrow">{{ t('competitions.league.predictionResult') }}</p>
        <h2>{{ result.homeTeam.name }} <span>{{ t('competitions.league.versus') }}</span> {{ result.awayTeam.name }}</h2>
      </header>

      <section class="scoreboard">
        <div><span>{{ t('competitions.league.likelyScore') }}</span><strong>{{ result.likelyScore.home }}–{{ result.likelyScore.away }}</strong></div>
        <div><span>{{ t('competitions.league.expectedGoals') }}</span><strong>{{ result.expectedGoals.home }} / {{ result.expectedGoals.away }}</strong><small>{{ result.homeTeam.name }} / {{ result.awayTeam.name }}</small></div>
      </section>

      <section class="probability-section" :aria-label="t('competitions.league.outcomeProbabilities')">
        <div v-for="outcome in outcomes" :key="outcome.key" class="probability-row">
          <div><span>{{ outcome.label }}</span><strong>{{ percent(result.probabilities[outcome.key]) }}</strong></div>
          <div class="probability-track" role="meter" :aria-label="outcome.label" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="result.probabilities[outcome.key] * 100"><span :style="{ width: `${result.probabilities[outcome.key] * 100}%` }" /></div>
        </div>
      </section>

      <section class="analysis-grid">
        <div class="result-card"><h3>{{ t('competitions.league.topScorelines') }}</h3><ol><li v-for="row in result.scoreProbabilities" :key="row.score"><span>{{ row.score }}</span><strong>{{ percent(row.probability) }}</strong></li></ol></div>
        <div class="result-card"><h3>{{ t('competitions.league.marketSignals') }}</h3><dl><div><dt>{{ t('competitions.league.btts') }}</dt><dd>{{ percent(result.markets.bothTeamsToScoreYes) }}</dd></div><div><dt>{{ t('competitions.league.over25') }}</dt><dd>{{ percent(result.markets.over2_5) }}</dd></div><div><dt>{{ t('competitions.league.cleanSheets') }}</dt><dd>{{ result.homeTeam.name }} {{ percent(result.markets.homeCleanSheet) }} · {{ result.awayTeam.name }} {{ percent(result.markets.awayCleanSheet) }}</dd></div></dl></div>
      </section>

      <section v-if="result.analysis" class="result-card analysis-card"><h3>{{ t('competitions.league.analysis') }}</h3><p>{{ result.analysis.summary }}</p><ul><li v-for="factor in result.analysis.keyFactors" :key="factor">{{ factor }}</li></ul></section>
    </article>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { ChevronDown } from '@lucide/vue'
import { api } from '../lib/api'
import { leagueApiBase } from '../competition/leagueApi.js'

const { t, locale } = useI18n()
const route = useRoute()
const fixtures = ref([])
const fixtureId = ref('')
const result = ref(null)
const error = ref('')
const loadError = ref('')
const loadingFixtures = ref(true)
const loading = ref(false)

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
const outcomes = computed(() => [
  { key: 'home', label: t('competitions.league.home') },
  { key: 'draw', label: t('competitions.league.draw') },
  { key: 'away', label: t('competitions.league.away') },
])
async function loadFixtures() {
  loadingFixtures.value = true
  loadError.value = ''
  try {
    fixtures.value = (await api.get(leagueApiBase(route.params.competitionEditionSlug))).data.fixtures || []
    fixtureId.value = futureFixtures.value[0]?.id || ''
  } catch (cause) {
    loadError.value = cause.response?.data?.error || t('competitions.league.loadFailed')
  } finally { loadingFixtures.value = false }
}
async function submit() {
  loading.value = true; error.value = ''; result.value = null
  try { result.value = (await api.post(`${leagueApiBase(route.params.competitionEditionSlug)}/predict`, { fixtureId: fixtureId.value })).data.prediction }
  catch (cause) { error.value = cause.response?.data?.error || t('competitions.league.predictionFailed') }
  finally { loading.value = false }
}
function formatKickoff(value) { return new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }
function percent(value) { return new Intl.NumberFormat(locale.value, { style: 'percent', maximumFractionDigits: 1 }).format(Number(value) || 0) }
onMounted(loadFixtures)
</script>

<style scoped>
.league-view { display: grid; gap: var(--space-6); min-width: 0; }
.page-heading, .result-heading { display: grid; gap: var(--space-2); }
.page-heading h1, .result-heading h2 { font-family: var(--font-family-display); margin: 0; }
.page-heading p:last-child, .result-heading p:last-child { color: var(--color-text-muted); margin: 0; }
.eyebrow { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / 1.2 var(--font-family-data); letter-spacing: .08em; margin: 0; text-transform: uppercase; }
.fixture-form { align-items: end; display: grid; gap: var(--space-3); grid-template-columns: minmax(0, 1fr) auto; max-width: 56rem; }
.fixture-form label { grid-column: 1 / -1; font-weight: var(--font-weight-semibold); }
select, button { min-height: var(--control-height-lg); padding: 0 var(--space-3); }
.select-field { display: block; position: relative; }
.select-field select { appearance: none; padding-right: calc(var(--space-4) + 1.5rem); width: 100%; }
.select-field svg { color: var(--color-text-muted); pointer-events: none; position: absolute; right: var(--space-4); top: 50%; transform: translateY(-50%); }
.fixture-form-skeleton { align-items: end; }
.fixture-form-skeleton span { animation: skeleton-pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); display: block; }
.fixture-form-skeleton .skeleton-label { grid-column: 1 / -1; height: .9rem; width: 16%; }
.fixture-form-skeleton .skeleton-select { height: var(--control-height-lg); }
.fixture-form-skeleton .skeleton-action { height: var(--control-height-lg); width: 10rem; }
@keyframes skeleton-pulse { 50% { opacity: .45; } }
@media (prefers-reduced-motion: reduce) { .fixture-form-skeleton span { animation: none; } }
button { background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; font-weight: var(--font-weight-semibold); }
button:disabled { cursor: wait; opacity: .6; }
.state-panel, .result-card, .scoreboard { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); padding: var(--space-5); }
.state-panel { align-items: center; display: flex; gap: var(--space-4); justify-content: space-between; }
.state-panel p { margin: 0; }
.state-error { background: var(--color-danger-surface); color: var(--color-danger); }
.prediction-result { display: grid; gap: var(--space-5); max-width: 64rem; }
.scoreboard { display: flex; flex-wrap: wrap; gap: var(--space-8); }
.scoreboard div { display: grid; gap: var(--space-1); }
.scoreboard span, .scoreboard small, dt { color: var(--color-text-muted); font-size: var(--font-size-xs); }
.scoreboard strong { font: var(--font-weight-heavy) var(--font-size-3xl) / 1 var(--font-family-data); }
.probability-section { display: grid; gap: var(--space-3); }
.probability-row > div:first-child { align-items: baseline; display: flex; justify-content: space-between; }
.probability-row strong { font-family: var(--font-family-data); }
.probability-track { background: var(--color-surface-inset); height: .55rem; margin-top: var(--space-2); }
.probability-track span { background: var(--color-accent); display: block; height: 100%; }
.analysis-grid { display: grid; gap: var(--space-5); grid-template-columns: repeat(2, minmax(0, 1fr)); }
.result-card { display: grid; gap: var(--space-4); }
.result-card h3 { font-family: var(--font-family-display); margin: 0; }
.result-card ol, .result-card ul { display: grid; gap: var(--space-2); margin: 0; padding-left: 1.2rem; }
.result-card ol li { display: flex; justify-content: space-between; }
.result-card dl { display: grid; gap: var(--space-3); margin: 0; }
.result-card dl div { display: flex; gap: var(--space-3); justify-content: space-between; }
.result-card dd { font-family: var(--font-family-data); margin: 0; text-align: right; }
.analysis-card p { margin: 0; }
.skeleton-line { animation: skeleton-pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); display: block; }
.prediction-result-skeleton { pointer-events: none; }
.prediction-result-skeleton .result-heading { gap: var(--space-2); }
.skeleton-eyebrow { height: .75rem; width: 7rem; }
.skeleton-title { height: 2rem; width: 18rem; }
.prediction-result-skeleton .scoreboard div { min-width: 12rem; }
.prediction-result-skeleton .skeleton-label { height: .75rem; width: 7rem; }
.skeleton-score { height: 2.5rem; margin-top: var(--space-1); width: 5rem; }
.skeleton-goals { height: 2rem; margin-top: var(--space-1); width: 8rem; }
.skeleton-caption { height: .7rem; margin-top: var(--space-1); width: 9rem; }
.skeleton-probability { display: grid; gap: var(--space-2); }
.skeleton-probability span:first-child { height: .85rem; width: 30%; }
.skeleton-probability span:last-child { height: .55rem; width: 100%; }
.skeleton-panel { gap: var(--space-3); }
.skeleton-panel-title { height: 1.25rem; width: 45%; }
.skeleton-panel-row { height: 1rem; width: 85%; }
.skeleton-panel-row:nth-child(3) { width: 68%; }
.skeleton-panel-row:nth-child(4) { width: 76%; }
@keyframes skeleton-pulse { 50% { opacity: .45; } }
@media (prefers-reduced-motion: reduce) { .skeleton-line { animation: none; } }
@media (max-width: 720px) { .analysis-grid { grid-template-columns: 1fr; } .fixture-form { grid-template-columns: 1fr; } }
</style>
