<template>
  <main class="prediction-page">
    <AtlasPageHeader
      :eyebrow="t('predictions.page.eyebrow', { competition: t(edition.displayNameKey) })"
      :title="t('predictions.page.title')"
      :description="t('predictions.page.description')"
    />

    <section v-if="teamLoading" data-testid="team-loading" class="team-state team-loading" aria-busy="true">
      <div>
        <h2>{{ t('predictions.teams.loading') }}</h2>
        <p>{{ t('predictions.teams.loadingDescription') }}</p>
      </div>
      <div class="selector-skeletons" aria-hidden="true">
        <span></span><span></span><span></span>
      </div>
    </section>

    <section v-else-if="teamError" class="team-state state-error" role="alert">
      <AlertTriangle :size="22" aria-hidden="true" />
      <div>
        <h2>{{ t('predictions.teams.error') }}</h2>
        <p>{{ t('predictions.teams.errorDescription') }}</p>
        <button data-testid="retry-teams" type="button" @click="loadTeams">
          <RotateCcw :size="16" aria-hidden="true" />
          {{ t('predictions.actions.retryTeams') }}
        </button>
      </div>
    </section>

    <section v-else-if="teams.length === 0" class="team-state" aria-live="polite">
      <Inbox :size="22" aria-hidden="true" />
      <div>
        <h2>{{ t('predictions.teams.empty') }}</h2>
        <p>{{ t('predictions.teams.emptyDescription') }}</p>
      </div>
    </section>

    <form v-else class="prediction-form" @submit.prevent="runPrediction">
      <div class="match-selectors">
        <label for="home-team">
          <span>{{ t('predictions.form.homeTeam') }}</span>
          <select
            id="home-team"
            v-model="homeTeam"
            data-testid="home-team"
            :aria-invalid="sameTeam"
            aria-describedby="selection-validation"
          >
            <option value="">{{ t('predictions.form.selectTeam') }}</option>
            <option v-for="team in teams" :key="team.name" :value="team.name">
              {{ team.name }} (ELO {{ integer(team.elo) }})
            </option>
          </select>
        </label>

        <span class="versus" aria-hidden="true">{{ t('predictions.form.versus') }}</span>

        <label for="away-team">
          <span>{{ t('predictions.form.awayTeam') }}</span>
          <select
            id="away-team"
            v-model="awayTeam"
            data-testid="away-team"
            :aria-invalid="sameTeam"
            aria-describedby="selection-validation"
          >
            <option value="">{{ t('predictions.form.selectTeam') }}</option>
            <option v-for="team in teams" :key="team.name" :value="team.name">
              {{ team.name }} (ELO {{ integer(team.elo) }})
            </option>
          </select>
        </label>

        <label for="match-stage" class="stage-select">
          <span>{{ t('predictions.form.stage') }}</span>
          <select id="match-stage" v-model="stage" data-testid="match-stage">
            <option v-for="option in stages" :key="option.value" :value="option.value">
              {{ t(option.labelKey) }}
            </option>
          </select>
        </label>
      </div>

      <div class="form-footer">
        <p id="selection-validation" :class="{ 'is-error': sameTeam }" aria-live="polite">
          {{ validationMessage }}
        </p>
        <button
          data-testid="run-prediction"
          class="run-button"
          type="submit"
          :disabled="!canRun || loading"
        >
          <LoaderCircle v-if="loading" :size="18" class="spin" aria-hidden="true" />
          <Sparkles v-else :size="18" aria-hidden="true" />
          {{ loading ? t('predictions.actions.running') : t('predictions.actions.run') }}
        </button>
      </div>
    </form>

    <section v-if="loading" data-testid="prediction-loading" class="prediction-loading" aria-busy="true">
      <div>
        <h2>{{ t('predictions.run.longRunningTitle') }}</h2>
        <p>{{ t('predictions.run.longRunningDescription') }}</p>
      </div>
      <div class="result-skeleton" aria-hidden="true">
        <span></span><span></span><span></span>
      </div>
    </section>

    <section v-if="runError" class="run-error" role="alert">
      <AlertTriangle :size="22" aria-hidden="true" />
      <div>
        <h2>{{ t('predictions.run.errorTitle') }}</h2>
        <p>{{ runError }}</p>
        <BillingStatusNotice
          v-if="billingHealth?.requires_attention"
          compact
          :health="billingHealth"
          :loading="billingActionLoading"
          @action="openBillingRecovery(route.fullPath, billingHealth)"
        />
        <BillingPlansLink v-else-if="subscriptionRequired" />
      </div>
    </section>

    <article v-if="result" class="prediction-result" :aria-label="t('predictions.result.label')">
      <header class="result-scoreboard">
        <div class="result-team" :class="{ winner: result.outcome === 'home_win' }">{{ result.home_team }}</div>
        <div class="score-block">
          <strong>{{ result.most_likely_score }}</strong>
          <span>{{ t('predictions.result.mostLikelyScore') }}</span>
          <small v-if="result.went_to_penalties">{{ t('predictions.result.afterExtraTime') }}</small>
        </div>
        <div class="result-team result-team-away" :class="{ winner: result.outcome === 'away_win' }">{{ result.away_team }}</div>
      </header>

      <section class="result-section probability-section">
        <ProbMeter
          :home-team="result.home_team"
          :away-team="result.away_team"
          :home-pct="result.home_win_prob"
          :draw-pct="result.draw_prob"
          :away-pct="result.away_win_prob"
          :outcome="result.outcome"
          :agent-count="result.agent_predictions?.length ?? 0"
          :agent-series="agentSeries"
        />
      </section>

      <section class="evidence-strip" :aria-label="t('predictions.result.label')">
        <div>
          <span>{{ t('predictions.result.swarmConfidence') }}</span>
          <strong>{{ percentage(result.overall_confidence) }}</strong>
          <i aria-hidden="true"><b :style="{ width: percentage(result.overall_confidence) }"></b></i>
        </div>
        <div>
          <span>{{ t('predictions.result.expectedGoals') }}</span>
          <strong>{{ decimal(result.predicted_home_goals) }} / {{ decimal(result.predicted_away_goals) }}</strong>
          <small>{{ result.home_team }} / {{ result.away_team }}</small>
        </div>
        <div v-if="topScoreProbability">
          <span>{{ t('predictions.result.mostLikelyScore') }}</span>
          <strong>{{ topScoreProbability.score }} / {{ percentage(topScoreProbability.probability) }}</strong>
          <small>{{ t('predictions.result.scoreProbabilities') }}</small>
        </div>
        <div>
          <span>{{ t('predictions.result.agreement') }}</span>
          <strong>{{ agreementText }}</strong>
        </div>
      </section>

      <section v-if="result.score_probabilities?.length" class="result-section score-probabilities">
        <header><Target :size="19" aria-hidden="true" /><h2>{{ t('predictions.result.scoreProbabilities') }}</h2></header>
        <div class="score-probability-list">
          <div v-for="(score, index) in result.score_probabilities" :key="score.score" :class="{ top: index === 0 }">
            <strong>{{ score.score }}</strong>
            <i aria-hidden="true"><b :style="{ width: scoreBarWidth(score.probability) }"></b></i>
            <span>{{ percentage(score.probability) }}</span>
            <small v-if="index === 0">{{ t('predictions.result.mostLikely') }}</small>
          </div>
        </div>
      </section>

      <div class="analysis-layout">
        <section v-if="result.swarm_consensus" class="result-section narrative-section">
          <header><BrainCircuit :size="19" aria-hidden="true" /><h2>{{ t('predictions.result.consensus') }}</h2></header>
          <p>{{ result.swarm_consensus }}</p>
        </section>
        <section v-if="result.key_factors?.length" class="result-section factors-section">
          <header><ListChecks :size="19" aria-hidden="true" /><h2>{{ t('predictions.result.keyFactors') }}</h2></header>
          <ul><li v-for="factor in result.key_factors" :key="factor">{{ factor }}</li></ul>
        </section>
      </div>

      <section class="result-section agents-section">
        <header><Users :size="19" aria-hidden="true" /><h2>{{ t('predictions.result.agents') }}</h2></header>
        <div class="agent-list">
          <article v-for="agent in result.agent_predictions" :key="agent.agent" class="agent-row">
            <div class="agent-heading">
              <h3>{{ agent.agent }}</h3>
              <span>{{ t('predictions.result.confidence') }} {{ percentage(agent.confidence) }}</span>
            </div>
            <div class="agent-probabilities">
              <span>{{ t('predictions.result.homeShort') }} <strong>{{ percentage(agent.home_win_prob) }}</strong></span>
              <span>{{ t('predictions.result.drawShort') }} <strong>{{ percentage(agent.draw_prob) }}</strong></span>
              <span>{{ t('predictions.result.awayShort') }} <strong>{{ percentage(agent.away_win_prob) }}</strong></span>
              <span>{{ t('predictions.result.predictedScore') }} <strong>{{ agent.predicted_score }}</strong></span>
            </div>
            <p>{{ agent.reasoning }}</p>
          </article>
        </div>
      </section>
    </article>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import {
  AlertTriangle,
  BrainCircuit,
  Inbox,
  ListChecks,
  LoaderCircle,
  RotateCcw,
  Sparkles,
  Target,
  Users,
} from '@lucide/vue'

import AtlasPageHeader from '../ui/patterns/AtlasPageHeader.vue'
import BillingStatusNotice from '../components/BillingStatusNotice.vue'
import BillingPlansLink from '../components/BillingPlansLink.vue'
import ProbMeter from '../components/ProbMeter.vue'
import { getCompetitionEdition, listCompetitionEditions } from '../competition/index.js'
import { useBillingStatus } from '../composables/useBillingStatus'
import { api } from '../lib/api'

const { locale, t } = useI18n()
const route = useRoute()
const defaultEdition = listCompetitionEditions()[0]
const teams = ref([])
const teamLoading = ref(true)
const teamError = ref(false)
const homeTeam = ref('')
const awayTeam = ref('')
const stage = ref('group')
const loading = ref(false)
const result = ref(null)
const runError = ref('')
const subscriptionRequired = ref(false)
const billingHealth = ref(null)
const { actionLoading: billingActionLoading, openBillingRecovery } = useBillingStatus()

const stages = [
  { value: 'group', labelKey: 'predictions.form.stages.group' },
  { value: 'round_of_32', labelKey: 'predictions.form.stages.roundOf32' },
  { value: 'round_of_16', labelKey: 'predictions.form.stages.roundOf16' },
  { value: 'quarter_final', labelKey: 'predictions.form.stages.quarterFinal' },
  { value: 'semi_final', labelKey: 'predictions.form.stages.semiFinal' },
  { value: 'final', labelKey: 'predictions.form.stages.final' },
]
const specializedAgentNames = [
  'Statistical Analysis Agent',
  'Video Intelligence Agent',
  'Recent Form Agent',
  'Tactical Analysis Agent',
]
const billingCodes = ['subscription_required', 'billing_payment_required', 'feature_limit_reached']

const edition = computed(() => getCompetitionEdition(route.params.competitionEditionSlug) || defaultEdition)
const sameTeam = computed(() => Boolean(homeTeam.value && awayTeam.value && homeTeam.value === awayTeam.value))
const canRun = computed(() => Boolean(homeTeam.value && awayTeam.value && !sameTeam.value))
const validationMessage = computed(() => {
  if (sameTeam.value) return t('predictions.validation.differentTeams')
  if (!canRun.value) return t('predictions.validation.selectBoth')
  return ''
})
const topScoreProbability = computed(() => result.value?.score_probabilities?.[0] || null)

function numberFormatter(options) {
  return new Intl.NumberFormat(locale.value, options)
}
const integer = (value) => numberFormatter({ maximumFractionDigits: 0, useGrouping: 'always' }).format(value)
const decimal = (value) => numberFormatter({ minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)
const percentage = (value) => numberFormatter({ style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(value)

async function loadTeams() {
  teamLoading.value = true
  teamError.value = false
  try {
    const response = await api.get('/api/predictions/teams')
    teams.value = Array.isArray(response.data?.teams)
      ? [...response.data.teams].sort((left, right) => Number(right.elo) - Number(left.elo))
      : []
  } catch {
    teams.value = []
    teamError.value = true
  } finally {
    teamLoading.value = false
  }
}

async function runPrediction() {
  if (!canRun.value || loading.value) return
  loading.value = true
  runError.value = ''
  subscriptionRequired.value = false
  billingHealth.value = null
  result.value = null
  try {
    const response = await api.post('/api/predictions/match', {
      home_team: homeTeam.value,
      away_team: awayTeam.value,
      stage: stage.value,
    })
    result.value = response.data
  } catch (error) {
    runError.value = error.response?.data?.error || error.message || t('predictions.run.errorFallback')
    billingHealth.value = error.response?.data?.billing_health || null
    subscriptionRequired.value = billingCodes.includes(error.response?.data?.code)
  } finally {
    loading.value = false
  }
}

function favoredOutcome(agent) {
  if (agent.home_win_prob > agent.draw_prob && agent.home_win_prob > agent.away_win_prob) return 'home_win'
  if (agent.draw_prob >= agent.home_win_prob && agent.draw_prob >= agent.away_win_prob) return 'draw'
  return 'away_win'
}

const specializedAgents = computed(() => {
  const agents = result.value?.agent_predictions ?? []
  const known = agents.filter((agent) => specializedAgentNames.includes(agent.agent))
  return (known.length ? known : agents).slice(0, 4)
})
const agreementCount = computed(() => specializedAgents.value.filter((agent) => favoredOutcome(agent) === result.value?.outcome).length)
const agreementOutcome = computed(() => {
  if (result.value?.outcome === 'home_win') return t('predictions.outcomes.home')
  if (result.value?.outcome === 'draw') return t('predictions.outcomes.draw')
  return t('predictions.outcomes.away')
})
const agreementText = computed(() => t('predictions.result.agreementValue', {
  count: agreementCount.value,
  total: specializedAgents.value.length,
  outcome: agreementOutcome.value,
}))

const agentSeries = computed(() => {
  const agents = result.value?.agent_predictions ?? []
  let home = 0
  let draw = 0
  let away = 0
  return agents.map((agent, index) => {
    home += agent.home_win_prob
    draw += agent.draw_prob
    away += agent.away_win_prob
    return { home: home / (index + 1), draw: draw / (index + 1), away: away / (index + 1) }
  })
})

function scoreBarWidth(probability) {
  const maximum = topScoreProbability.value?.probability || 0
  return maximum > 0 ? `${(probability / maximum) * 100}%` : '0%'
}

onMounted(loadTeams)
</script>

<style scoped>
.prediction-page { display: flex; flex-direction: column; gap: var(--space-8); }
.prediction-form { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); padding: var(--space-6); }
.match-selectors { align-items: end; display: grid; gap: var(--space-4); grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) minmax(11rem, 0.55fr); }
.match-selectors label { color: var(--color-text-muted); display: flex; flex-direction: column; font-size: var(--font-size-sm); gap: var(--space-2); }
.match-selectors label > span { font-weight: var(--font-weight-semibold); }
.match-selectors select { background: var(--color-surface-raised); border: var(--border-width-thin) solid var(--color-border); border-radius: var(--radius-md); color: var(--color-text); font: var(--font-weight-medium) var(--font-size-sm) / var(--line-height-normal) var(--font-family-body); min-height: var(--control-height-lg); padding: 0 var(--space-3); width: 100%; }
.match-selectors select:hover { border-color: var(--color-border-strong); }
.match-selectors select:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 2px; }
.match-selectors select[aria-invalid="true"] { border-color: var(--color-danger); }
.versus { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--control-height-lg) var(--font-family-data); text-transform: uppercase; }
.form-footer { align-items: center; border-top: var(--border-width-thin) solid var(--color-border); display: flex; gap: var(--space-4); justify-content: space-between; margin-top: var(--space-5); padding-top: var(--space-5); }
.form-footer p { color: var(--color-text-muted); font-size: var(--font-size-sm); margin: 0; }
.form-footer p.is-error { color: var(--color-danger); }
.run-button,
.team-state button { align-items: center; background: var(--color-accent); border: 0; border-radius: var(--radius-md); color: var(--color-accent-contrast); cursor: pointer; display: inline-flex; font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); gap: var(--space-2); justify-content: center; min-height: var(--control-height-lg); padding: 0 var(--space-5); }
.run-button:hover:not(:disabled),
.team-state button:hover { background: var(--color-accent-hover); }
.run-button:focus-visible,
.team-state button:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.run-button:disabled { cursor: not-allowed; opacity: 0.55; }

.team-state,
.prediction-loading,
.run-error { align-items: flex-start; background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); display: flex; gap: var(--space-4); padding: var(--space-6); }
.team-state > svg,
.run-error > svg { color: var(--color-accent); flex: 0 0 auto; }
.team-state h2,
.prediction-loading h2,
.run-error h2 { font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0; }
.team-state p,
.prediction-loading p,
.run-error p { color: var(--color-text-muted); line-height: var(--line-height-relaxed); margin: var(--space-2) 0 0; }
.team-state button { margin-top: var(--space-4); }
.state-error,
.run-error { background: var(--color-danger-surface); border-color: var(--color-danger); }
.state-error > svg,
.run-error > svg { color: var(--color-danger); }
.team-loading,
.prediction-loading { display: grid; grid-template-columns: minmax(14rem, 0.8fr) minmax(0, 1.2fr); }
.team-loading > div:first-child,
.prediction-loading > div:first-child { display: grid; gap: var(--space-2); }
.selector-skeletons,
.result-skeleton { display: grid; gap: var(--space-3); }
.selector-skeletons { grid-template-columns: repeat(3, 1fr); }
.selector-skeletons span,
.result-skeleton span { animation: skeleton-pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); display: block; min-height: var(--control-height-lg); }
.result-skeleton span:first-child { height: 4rem; }

.prediction-result { border-top: var(--border-width-strong) solid var(--color-accent); display: flex; flex-direction: column; }
.result-scoreboard { align-items: center; border-bottom: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-5); grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); min-height: 10rem; padding: var(--space-8) var(--space-4); }
.result-team { font-family: var(--font-family-display); font-size: var(--font-size-2xl); font-weight: var(--font-weight-bold); text-align: right; }
.result-team-away { text-align: left; }
.result-team.winner { color: var(--color-accent); }
.score-block { align-items: center; display: flex; flex-direction: column; min-width: 10rem; text-align: center; }
.score-block strong { color: var(--color-accent); font: var(--font-weight-heavy) var(--font-size-4xl) / var(--line-height-tight) var(--font-family-data); }
.score-block span,
.score-block small { color: var(--color-text-muted); font-size: var(--font-size-xs); }
.score-block small { background: var(--color-warning-surface); color: var(--color-warning); margin-top: var(--space-2); padding: var(--space-1) var(--space-2); }
.result-section { border-bottom: var(--border-width-thin) solid var(--color-border); padding: var(--space-6) 0; }
.probability-section { padding-left: var(--space-4); padding-right: var(--space-4); }
.result-section > header { align-items: center; color: var(--color-accent); display: flex; gap: var(--space-2); margin-bottom: var(--space-4); }
.result-section h2 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0; }
.evidence-strip { border-bottom: var(--border-width-thin) solid var(--color-border); border-top: var(--border-width-thin) solid var(--color-border); display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.evidence-strip > div { border-right: var(--border-width-thin) solid var(--color-border); display: flex; flex-direction: column; gap: var(--space-2); min-height: 8rem; padding: var(--space-5); }
.evidence-strip > div:last-child { border-right: 0; }
.evidence-strip span,
.evidence-strip small { color: var(--color-text-muted); font-size: var(--font-size-xs); }
.evidence-strip strong { color: var(--color-accent); font: var(--font-weight-heavy) var(--font-size-lg) / var(--line-height-tight) var(--font-family-data); }
.evidence-strip i,
.score-probability-list i { background: var(--color-surface-inset); display: block; height: var(--space-1); margin-top: auto; overflow: hidden; }
.evidence-strip i b,
.score-probability-list i b { background: var(--color-accent); display: block; height: 100%; }
.score-probability-list { display: flex; flex-direction: column; }
.score-probability-list > div { align-items: center; border-top: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-3); grid-template-columns: 4rem minmax(4rem, 1fr) 5rem 6rem; min-height: var(--control-height-lg); }
.score-probability-list strong,
.score-probability-list span { font-family: var(--font-family-data); font-variant-numeric: tabular-nums; }
.score-probability-list span { color: var(--color-text-muted); text-align: right; }
.score-probability-list small { color: var(--color-accent); font-size: var(--font-size-xs); text-align: right; text-transform: uppercase; }
.score-probability-list .top strong,
.score-probability-list .top span { color: var(--color-accent); }
.analysis-layout { border-bottom: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-8); grid-template-columns: 1.15fr 0.85fr; }
.analysis-layout .result-section { border-bottom: 0; }
.narrative-section p { color: var(--color-text-muted); line-height: var(--line-height-relaxed); margin: 0; }
.factors-section ul { display: flex; flex-direction: column; gap: var(--space-3); list-style: none; margin: 0; padding: 0; }
.factors-section li { border-top: var(--border-width-thin) solid var(--color-border); color: var(--color-text-muted); padding-top: var(--space-3); }
.agent-list { border-top: var(--border-width-thin) solid var(--color-border); }
.agent-row { border-bottom: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-3); padding: var(--space-5) 0; }
.agent-heading { align-items: baseline; display: flex; gap: var(--space-4); justify-content: space-between; }
.agent-heading h3 { font-family: var(--font-family-display); font-size: var(--font-size-md); margin: 0; }
.agent-heading span { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); }
.agent-probabilities { display: flex; flex-wrap: wrap; gap: var(--space-4); }
.agent-probabilities span { color: var(--color-text-muted); font-size: var(--font-size-xs); }
.agent-probabilities strong { color: var(--color-text); font-family: var(--font-family-data); }
.agent-row p { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-relaxed); margin: 0; }
.spin { animation: prediction-spin 0.85s linear infinite; }
@keyframes prediction-spin { to { transform: rotate(360deg); } }
@keyframes skeleton-pulse { 50% { opacity: 0.45; } }

@media (max-width: 900px) {
  .match-selectors { grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); }
  .stage-select { grid-column: 1 / -1; }
  .evidence-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .evidence-strip > div:nth-child(2) { border-right: 0; }
  .evidence-strip > div:nth-child(-n + 2) { border-bottom: var(--border-width-thin) solid var(--color-border); }
}
@media (max-width: 640px) {
  .prediction-form { padding: var(--space-4); }
  .match-selectors { grid-template-columns: 1fr; }
  .versus { line-height: var(--line-height-normal); text-align: center; }
  .stage-select { grid-column: auto; }
  .form-footer { align-items: stretch; flex-direction: column; }
  .run-button { width: 100%; }
  .team-loading,
  .prediction-loading { grid-template-columns: 1fr; }
  .selector-skeletons { grid-template-columns: 1fr; }
  .result-scoreboard { grid-template-columns: 1fr; }
  .result-team,
  .result-team-away { text-align: center; }
  .evidence-strip,
  .analysis-layout { grid-template-columns: 1fr; }
  .evidence-strip > div { border-bottom: var(--border-width-thin) solid var(--color-border); border-right: 0; }
  .score-probability-list > div { grid-template-columns: 3rem minmax(3rem, 1fr) 4.5rem; }
  .score-probability-list small { display: none; }
  .agent-heading { align-items: flex-start; flex-direction: column; gap: var(--space-2); }
}
@media (prefers-reduced-motion: reduce) {
  .spin,
  .selector-skeletons span,
  .result-skeleton span { animation: none; }
}
</style>
