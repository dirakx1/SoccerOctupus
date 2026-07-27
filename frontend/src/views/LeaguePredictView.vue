<template>
  <main class="league-predict-view">
    <header class="predict-heading">
      <p>{{ t('league.predictions.eyebrow') }}</p>
      <h1>{{ t('league.predictions.title', { edition: data?.edition?.display_name || editionSlug }) }}</h1>
    </header>

    <section v-if="fixturesLoading" data-testid="predictions-loading" class="predict-skeleton" aria-busy="true">
      <span class="skeleton-label"></span>
      <span class="skeleton-select"></span>
      <span class="skeleton-button"></span>
    </section>
    <section v-else-if="fixturesError" class="predict-state" role="alert">
      <h2>{{ t('league.predictions.fixturesErrorTitle') }}</h2>
      <p>{{ t('league.predictions.fixturesError') }}</p>
      <button type="button" @click="loadFixtures">{{ t('league.states.retry') }}</button>
    </section>
    <section v-else class="fixture-picker">
      <label for="fixture-target">{{ t('league.predictions.fixture') }}</label>
      <select id="fixture-target" v-model="fixtureId" data-testid="fixture-target">
        <option value="">{{ t('league.predictions.selectFixture') }}</option>
        <option v-for="fixture in scheduledFixtures" :key="fixture.id" :value="String(fixture.id)">
          {{ fixtureLabel(fixture) }}
        </option>
      </select>
      <button data-testid="reveal-prediction" type="button" :disabled="!fixtureId || revealing" @click="reveal">
        {{ revealing ? t('league.predictions.generating') : t('league.predictions.reveal') }}
      </button>
    </section>

    <section v-if="revealing" data-testid="prediction-generating" class="generation-skeleton" aria-busy="true" aria-live="polite">
      <h2>{{ t('league.predictions.generating') }}</h2>
      <div aria-hidden="true"><span></span><span></span><span></span></div>
    </section>
    <section v-if="revealError" data-testid="prediction-error" class="predict-state prediction-error" role="alert">
      <h2>{{ t(`league.predictions.errors.${revealError}.title`) }}</h2>
      <p>{{ t(`league.predictions.errors.${revealError}.description`) }}</p>
    </section>

    <article v-if="prediction" class="prediction-result">
      <p class="reveal-status">{{ t(`league.predictions.revealStatus.${revealStatus}`) }}</p>
      <header class="scoreboard">
        <strong>{{ prediction.home_team }}</strong>
        <div><b>{{ likelyScore }}</b><span>{{ t('league.predictions.likelyScore') }}</span></div>
        <strong>{{ prediction.away_team }}</strong>
      </header>
      <section class="probabilities" :aria-label="t('league.predictions.probabilities')">
        <div><span>{{ t('league.predictions.homeWin') }}</span><strong>{{ percentage(homeProbability) }}</strong></div>
        <div><span>{{ t('league.predictions.draw') }}</span><strong>{{ percentage(drawProbability) }}</strong></div>
        <div><span>{{ t('league.predictions.awayWin') }}</span><strong>{{ percentage(awayProbability) }}</strong></div>
      </section>
      <dl class="metadata">
        <div><dt>{{ t('league.predictions.confidence') }}</dt><dd>{{ percentage(prediction.confidence ?? prediction.overall_confidence) }}</dd></div>
        <div><dt>{{ t('league.predictions.source') }}</dt><dd>{{ prediction.source || prediction.model_version || '-' }}</dd></div>
        <div><dt>{{ t('league.predictions.sourceUpdated') }}</dt><dd>{{ formatDate(prediction.source_updated_at) }}</dd></div>
        <div><dt>{{ t('league.predictions.generated') }}</dt><dd>{{ formatDate(prediction.generated_at || prediction.created_at) }}</dd></div>
      </dl>
      <section class="agents">
        <div><h2>{{ t('league.predictions.availableAgents') }}</h2><ul><li v-for="agent in availableAgents" :key="agentName(agent)">{{ agentLabel(agent) }}</li></ul></div>
        <div><h2>{{ t('league.predictions.unavailableAgents') }}</h2><ul><li v-for="agent in unavailableAgents" :key="agentName(agent)">{{ agentLabel(agent) }}<span v-if="agent.reason">: {{ agentReason(agent) }}</span></li></ul></div>
      </section>
    </article>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { api } from '../lib/api.js'

const props = defineProps({
  competitionSlug: { type: String, required: true },
  editionSlug: { type: String, required: true },
})
const { locale, t, te } = useI18n()
const data = ref(null)
const fixturesLoading = ref(true)
const fixturesError = ref(false)
const fixtureId = ref('')
const revealing = ref(false)
const prediction = ref(null)
const revealStatus = ref('')
const revealError = ref('')
const scheduledFixtures = computed(() => (data.value?.fixtures || []).filter((fixture) => fixture.status === 'scheduled'))
const homeProbability = computed(() => prediction.value?.outcome_probabilities?.home ?? prediction.value?.home_win_probability ?? prediction.value?.home_win_prob)
const drawProbability = computed(() => prediction.value?.outcome_probabilities?.draw ?? prediction.value?.draw_probability ?? prediction.value?.draw_prob)
const awayProbability = computed(() => prediction.value?.outcome_probabilities?.away ?? prediction.value?.away_win_probability ?? prediction.value?.away_win_prob)
const likelyScore = computed(() => prediction.value?.most_likely_score ?? prediction.value?.likely_score ?? '-')
const availableAgents = computed(() => prediction.value?.agents?.available ?? prediction.value?.available_agents ?? prediction.value?.agent_predictions ?? [])
const unavailableAgents = computed(() => prediction.value?.agents?.unavailable ?? prediction.value?.unavailable_agents ?? [])
const blockedCodes = new Set(['fixture_ineligible', 'fixture_not_eligible', 'prediction_blocked', 'fixture_not_scheduled'])

async function loadFixtures() {
  fixturesLoading.value = true
  fixturesError.value = false
  try {
    const response = await api.get(`/api/competitions/${props.competitionSlug}/editions/${props.editionSlug}/fixtures`, { params: { mode: 'upcoming' } })
    data.value = response.data
  } catch {
    fixturesError.value = true
  } finally {
    fixturesLoading.value = false
  }
}

async function reveal() {
  if (!fixtureId.value || revealing.value) return
  revealing.value = true
  prediction.value = null
  revealError.value = ''
  try {
    const response = await api.post(`/api/competitions/${props.competitionSlug}/editions/${props.editionSlug}/fixtures/${fixtureId.value}/prediction`)
    prediction.value = response.data?.prediction ?? response.data
    revealStatus.value = response.data?.reveal_status ?? 'charged'
  } catch (error) {
    const code = error.response?.data?.code
    revealError.value = code === 'feature_limit_reached' ? 'limit' : blockedCodes.has(code) ? 'blocked' : 'generation'
  } finally {
    revealing.value = false
  }
}

function fixtureLabel(fixture) { return `${fixture.home_team.display_name} vs ${fixture.away_team.display_name}` }
function agentName(agent) { return typeof agent === 'string' ? agent : agent.name || agent.agent }
function agentLabel(agent) { const name = agentName(agent); const key = `league.predictions.agents.${name}`; return te(key) ? t(key) : name }
function agentReason(agent) { const name = agentName(agent); const key = `league.predictions.agentReasons.${name}`; return te(key) ? t(key) : agent.reason }
function percentage(value) { return typeof value === 'number' ? new Intl.NumberFormat(locale.value, { style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(value) : '-' }
function formatDate(value) { return value ? new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '-' }

loadFixtures()
</script>

<style scoped>
.league-predict-view { display: flex; flex-direction: column; gap: var(--space-6); padding: var(--space-8) 0; }
.predict-heading { border-bottom: var(--border-width-thin) solid var(--color-border); padding-bottom: var(--space-6); }
.predict-heading p, .reveal-status { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / 1 var(--font-family-data); margin: 0; text-transform: uppercase; }
.predict-heading h1 { font-family: var(--font-family-display); font-size: var(--font-size-3xl); letter-spacing: 0; margin: var(--space-2) 0 0; }
.fixture-picker { align-items: end; display: grid; gap: var(--space-4); grid-template-columns: minmax(0, 1fr) auto; }
.fixture-picker label { color: var(--color-text-muted); font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); grid-column: 1 / -1; text-transform: uppercase; }
.fixture-picker select { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); color: var(--color-text); min-height: var(--control-height-lg); padding: 0 var(--space-3); }
.fixture-picker button, .predict-state button { background: var(--color-accent); border: 0; color: var(--color-accent-contrast); min-height: var(--control-height-lg); padding: 0 var(--space-5); }
.fixture-picker button:disabled { opacity: .55; }
.prediction-result { border-top: var(--border-width-strong) solid var(--color-accent); display: flex; flex-direction: column; gap: var(--space-5); padding-top: var(--space-4); }
.scoreboard { align-items: center; display: grid; gap: var(--space-5); grid-template-columns: 1fr auto 1fr; padding: var(--space-6) 0; text-align: center; }
.scoreboard > strong { font-family: var(--font-family-display); font-size: var(--font-size-2xl); }
.scoreboard > strong:first-child { text-align: right; }.scoreboard > strong:last-child { text-align: left; }
.scoreboard div { display: flex; flex-direction: column; }.scoreboard b { color: var(--color-accent); font: var(--font-weight-heavy) var(--font-size-4xl) / 1 var(--font-family-data); }.scoreboard span { color: var(--color-text-muted); font-size: var(--font-size-xs); }
.probabilities, .metadata, .agents { border-top: var(--border-width-thin) solid var(--color-border); display: grid; grid-template-columns: repeat(3, 1fr); }
.probabilities div, .metadata div { display: flex; flex-direction: column; gap: var(--space-2); padding: var(--space-5); }.probabilities span, dt { color: var(--color-text-muted); font-size: var(--font-size-xs); }.probabilities strong, dd { font-family: var(--font-family-data); margin: 0; }
.agents { grid-template-columns: 1fr 1fr; gap: var(--space-8); padding-top: var(--space-5); }.agents h2 { font-family: var(--font-family-display); font-size: var(--font-size-lg); }.agents li { color: var(--color-text-muted); margin-bottom: var(--space-2); }
.predict-state { min-height: 14rem; }.prediction-error { background: var(--color-danger-surface); border: var(--border-width-thin) solid var(--color-danger); min-height: auto; padding: var(--space-5); }.prediction-error h2, .prediction-error p { margin: 0; }.prediction-error p { color: var(--color-text-muted); margin-top: var(--space-2); }.predict-skeleton { display: grid; gap: var(--space-3); grid-template-columns: minmax(0, 1fr) 10rem; }.predict-skeleton span { animation: pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); }.skeleton-label { grid-column: 1 / -1; height: var(--font-size-xs); width: 8rem; }.skeleton-select, .skeleton-button { height: var(--control-height-lg); }
.generation-skeleton { border-top: var(--border-width-thin) solid var(--color-border); padding-top: var(--space-5); }.generation-skeleton h2 { font-family: var(--font-family-display); font-size: var(--font-size-xl); }.generation-skeleton div { display: grid; gap: var(--space-3); grid-template-columns: repeat(3, 1fr); }.generation-skeleton span { animation: pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); height: 5rem; }
@keyframes pulse { 50% { opacity: .45; } }
@media (max-width: 640px) { .fixture-picker, .probabilities, .metadata, .agents { grid-template-columns: 1fr; }.scoreboard { gap: var(--space-3); }.scoreboard > strong { font-size: var(--font-size-lg); } }
@media (prefers-reduced-motion: reduce) { .predict-skeleton span, .generation-skeleton span { animation: none; } }
</style>
