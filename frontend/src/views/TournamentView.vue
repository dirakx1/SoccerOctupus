<template>
  <main class="atlas-tournament-page">
    <AtlasPageHeader
      :eyebrow="t('tournament.page.eyebrow', { competition: t(edition.displayNameKey) })"
      :title="t('tournament.page.title')"
      :description="t('tournament.page.description')"
    />

    <div
      class="tournament-tabs"
      role="tablist"
      :aria-label="t('tournament.tabs.label')"
      @keydown="onTabKeydown"
    >
      <button
        id="tournament-tab-live"
        ref="liveTab"
        type="button"
        role="tab"
        :aria-selected="activeTab === 'live'"
        aria-controls="tournament-panel-live"
        :tabindex="activeTab === 'live' ? 0 : -1"
        @click="selectTab('live')"
      >
        <Radio :size="16" aria-hidden="true" />
        <span>{{ t('tournament.tabs.live') }}</span>
      </button>
      <button
        id="tournament-tab-simulation"
        ref="simulationTab"
        type="button"
        role="tab"
        :aria-selected="activeTab === 'simulation'"
        aria-controls="tournament-panel-simulation"
        :tabindex="activeTab === 'simulation' ? 0 : -1"
        @click="selectTab('simulation')"
      >
        <GitBranch :size="16" aria-hidden="true" />
        <span>{{ t('tournament.tabs.simulation') }}</span>
      </button>
    </div>

    <section
      v-show="activeTab === 'live'"
      id="tournament-panel-live"
      role="tabpanel"
      aria-labelledby="tournament-tab-live"
      :tabindex="activeTab === 'live' ? 0 : -1"
      class="tournament-panel"
    >
      <div v-if="liveLoading" class="live-loading" data-testid="live-loading" aria-busy="true">
        <p class="sr-only">{{ t('tournament.live.loadingDescription') }}</p>
        <div v-for="group in loadingGroups" :key="group" class="live-skeleton">
          <div class="skeleton-line skeleton-heading"></div>
          <div v-for="row in 4" :key="row" class="skeleton-line skeleton-row"></div>
        </div>
      </div>

      <div v-else-if="liveError" class="state-panel state-error" role="alert">
        <AlertTriangle :size="22" aria-hidden="true" />
        <div>
          <h2>{{ t('tournament.live.error') }}</h2>
          <p>{{ t('tournament.live.errorDescription') }}</p>
          <button type="button" data-testid="retry-live" @click="loadLiveResults">
            <RotateCcw :size="15" aria-hidden="true" />
            <span>{{ t('tournament.live.retry') }}</span>
          </button>
        </div>
      </div>

      <div v-else-if="isLiveEmpty" class="state-panel" aria-live="polite">
        <Inbox :size="22" aria-hidden="true" />
        <div>
          <h2>{{ t('tournament.live.empty') }}</h2>
          <p>{{ t('tournament.live.emptyDescription') }}</p>
        </div>
      </div>

      <template v-else>
        <header class="live-summary">
          <div>
            <span class="status-label"><Radio :size="14" aria-hidden="true" />{{ t('tournament.live.status') }}</span>
            <strong>{{ t('tournament.live.summary', { count: formatInteger(liveTotal) }) }}</strong>
          </div>
          <p>{{ t('tournament.live.source') }} <strong>ESPN</strong></p>
        </header>

        <section class="live-section" :aria-labelledby="standingsHeadingId">
          <div class="section-heading">
            <h2 :id="standingsHeadingId">{{ t('tournament.live.standings') }}</h2>
            <span>{{ formatInteger(groupEntries.length) }}</span>
          </div>
          <div class="standings-grid">
            <article
              v-for="group in groupEntries"
              :key="group.label"
              class="standings-panel"
              data-testid="live-group"
              :data-group="group.label"
            >
              <header>
                <span>{{ t('tournament.live.group', { group: group.label }) }}</span>
                <strong aria-hidden="true">{{ group.label }}</strong>
              </header>
              <div class="table-scroll">
                <table>
                  <caption class="sr-only">{{ t('tournament.live.groupTable', { group: group.label }) }}</caption>
                  <thead>
                    <tr>
                      <th scope="col">{{ t('tournament.standings.position') }}</th>
                      <th scope="col">{{ t('tournament.standings.team') }}</th>
                      <th v-for="column in standingColumns" :key="column.key" scope="col" class="numeric" :title="t(column.labelKey)">
                        {{ t(column.labelKey) }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(standing, index) in group.teams" :key="standing.team">
                      <td class="position">{{ formatInteger(index + 1) }}</td>
                      <th scope="row">{{ standing.team }}</th>
                      <td v-for="column in standingColumns" :key="column.key" class="numeric data-value">
                        {{ column.key === 'gd' ? formatGoalDifference(standing[column.key]) : formatInteger(standing[column.key]) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </article>
          </div>
        </section>

        <section class="live-section" :aria-labelledby="resultsHeadingId">
          <div class="section-heading">
            <h2 :id="resultsHeadingId">{{ t('tournament.live.results') }}</h2>
            <span>{{ formatInteger(liveMatches.length) }}</span>
          </div>
          <div v-if="liveMatches.length" class="live-matches">
            <article
              v-for="(match, index) in liveMatches"
              :key="`${match.group}-${match.home}-${match.away}-${index}`"
              class="live-match"
              data-testid="live-match"
              :aria-label="t('tournament.live.matchLabel', { group: match.group, home: match.home, away: match.away })"
            >
              <span class="match-stage">{{ t('tournament.live.group', { group: match.group }) }}</span>
              <strong class="home-team" :class="{ winner: Number(match.home_goals) > Number(match.away_goals) }">{{ match.home }}</strong>
              <span class="match-score">{{ formatScore(match.home_goals, match.away_goals) }}</span>
              <strong class="away-team" :class="{ winner: Number(match.away_goals) > Number(match.home_goals) }">{{ match.away }}</strong>
              <time>{{ match.date }}</time>
            </article>
          </div>
          <p v-else class="no-matches">{{ t('tournament.live.noMatches') }}</p>
        </section>
      </template>
    </section>

    <section
      v-show="activeTab === 'simulation'"
      id="tournament-panel-simulation"
      role="tabpanel"
      aria-labelledby="tournament-tab-simulation"
      :tabindex="activeTab === 'simulation' ? 0 : -1"
      class="tournament-panel"
    >
      <div class="simulation-controls">
        <label>
          <input v-model="useSwarm" type="checkbox" data-testid="swarm-toggle" />
          <span><strong>{{ t('tournament.simulation.option') }}</strong>{{ t('tournament.simulation.optionDescription') }}</span>
        </label>
        <button type="button" data-testid="run-simulation" :disabled="loading" @click="runSim">
          <Play :size="16" aria-hidden="true" />
          <span>{{ loading ? t('tournament.simulation.running') : t('tournament.simulation.run') }}</span>
        </button>
      </div>
      <p class="simulation-note">{{ t('tournament.simulation.note') }}</p>

      <div v-if="loading" class="simulation-loading" data-testid="simulation-loading" aria-busy="true">
        <div>
          <LoaderCircle :size="22" aria-hidden="true" />
          <h2>{{ t('tournament.simulation.longRunningTitle') }}</h2>
          <p>{{ t('tournament.simulation.longRunningDescription') }}</p>
        </div>
        <div class="simulation-skeleton">
          <span v-for="block in 6" :key="block"></span>
        </div>
      </div>
      <div v-else-if="error" class="state-panel state-error" role="alert">
        <AlertTriangle :size="22" aria-hidden="true" />
        <div>
          <h2>{{ t('tournament.simulation.error') }}</h2>
          <p>{{ error }}</p>
          <BillingStatusNotice
            v-if="billingHealth?.requires_attention"
            compact
            :health="billingHealth"
            :loading="billingActionLoading"
            @action="openBillingRecovery(route.fullPath, billingHealth)"
          />
          <BillingPlansLink v-else-if="subscriptionRequired" />
        </div>
      </div>
      <TournamentBracket v-else-if="result" :result="result" />
      <div v-else class="state-panel simulation-empty">
        <GitBranch :size="22" aria-hidden="true" />
        <div><h2>{{ t('tournament.simulation.empty') }}</h2><p>{{ t('tournament.simulation.emptyDescription') }}</p></div>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { AlertTriangle, GitBranch, Inbox, LoaderCircle, Play, Radio, RotateCcw } from '@lucide/vue'

import BillingPlansLink from '../components/BillingPlansLink.vue'
import BillingStatusNotice from '../components/BillingStatusNotice.vue'
import TournamentBracket from '../components/TournamentBracket.vue'
import { useBillingStatus } from '../composables/useBillingStatus'
import { getCompetitionEdition, listCompetitionEditions } from '../competition/index.js'
import { api } from '../lib/api'
import AtlasPageHeader from '../ui/patterns/AtlasPageHeader.vue'

const { locale, t } = useI18n()
const route = useRoute()
const defaultEdition = listCompetitionEditions()[0]
const activeTab = ref('live')
const liveTab = ref(null)
const simulationTab = ref(null)
const liveData = ref(null)
const liveLoading = ref(true)
const liveError = ref(false)
const useSwarm = ref(false)
const loading = ref(false)
const error = ref('')
const result = ref(null)
const subscriptionRequired = ref(false)
const billingHealth = ref(null)
const billingCode = ref('')
const loadingGroups = ['A', 'B', 'C', 'D', 'E', 'F']
const standingsHeadingId = 'tournament-live-standings'
const resultsHeadingId = 'tournament-live-results'

const standingColumns = [
  { key: 'played', labelKey: 'tournament.standings.played' },
  { key: 'won', labelKey: 'tournament.standings.won' },
  { key: 'drawn', labelKey: 'tournament.standings.drawn' },
  { key: 'lost', labelKey: 'tournament.standings.lost' },
  { key: 'gf', labelKey: 'tournament.standings.goalsFor' },
  { key: 'ga', labelKey: 'tournament.standings.goalsAgainst' },
  { key: 'gd', labelKey: 'tournament.standings.goalDifference' },
  { key: 'points', labelKey: 'tournament.standings.points' },
]

const edition = computed(() => getCompetitionEdition(route.params.competitionEditionSlug) || defaultEdition)
const groupEntries = computed(() => Object.entries(liveData.value?.standings || {})
  .sort(([left], [right]) => left.localeCompare(right))
  .map(([label, teams]) => ({ label, teams: Array.isArray(teams) ? teams : [] })))
const liveMatches = computed(() => Array.isArray(liveData.value?.matches) ? liveData.value.matches : [])
const liveTotal = computed(() => Number(liveData.value?.total) || 0)
const isLiveEmpty = computed(() => groupEntries.value.length === 0 && liveMatches.value.length === 0)
const { actionLoading: billingActionLoading, openBillingRecovery } = useBillingStatus()

function formatInteger(value) {
  return new Intl.NumberFormat(locale.value, { maximumFractionDigits: 0 }).format(Number(value) || 0)
}

function formatGoalDifference(value) {
  const numeric = Number(value) || 0
  return `${numeric > 0 ? '+' : ''}${formatInteger(numeric)}`
}

function formatScore(home, away) {
  return `${formatInteger(home)}–${formatInteger(away)}`
}

async function loadLiveResults() {
  liveLoading.value = true
  liveError.value = false
  try {
    const response = await api.get('/api/predictions/live-results')
    liveData.value = response.data && typeof response.data === 'object' ? response.data : {}
  } catch {
    liveData.value = null
    liveError.value = true
  } finally {
    liveLoading.value = false
  }
}

function selectTab(tab, focus = false) {
  activeTab.value = tab
  if (focus) nextTick(() => (tab === 'live' ? liveTab.value : simulationTab.value)?.focus())
}

function onTabKeydown(event) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  if (event.key === 'Home' || (event.key === 'ArrowLeft' && activeTab.value === 'simulation')) selectTab('live', true)
  else if (event.key === 'End' || (event.key === 'ArrowRight' && activeTab.value === 'live')) selectTab('simulation', true)
  else selectTab(activeTab.value === 'live' ? 'simulation' : 'live', true)
}

async function runSim() {
  loading.value = true
  error.value = ''
  result.value = null
  subscriptionRequired.value = false
  billingHealth.value = null
  billingCode.value = ''
  try {
    const response = await api.post('/api/predictions/tournament', { use_swarm: useSwarm.value })
    result.value = response.data
  } catch (simulationError) {
    const responseData = simulationError.response?.data || {}
    billingCode.value = responseData.code || ''
    billingHealth.value = responseData.billing_health || null
    subscriptionRequired.value = ['subscription_required', 'billing_payment_required', 'feature_limit_reached'].includes(billingCode.value)
    error.value = responseData.error
      || (billingCode.value ? billingFallback(billingCode.value) : simulationError.message)
      || t('tournament.simulation.errorFallback')
  } finally {
    loading.value = false
  }
}

function billingFallback(code) {
  const fallbackKeys = {
    subscription_required: 'tournament.billing.subscriptionRequired',
    billing_payment_required: 'tournament.billing.paymentRequired',
    feature_limit_reached: 'tournament.billing.featureLimitReached',
  }
  return t(fallbackKeys[code] || 'tournament.simulation.errorFallback')
}

onMounted(loadLiveResults)
</script>

<style scoped>
.atlas-tournament-page { display: flex; flex-direction: column; gap: var(--space-6); min-width: 0; }
.tournament-tabs { align-items: center; border-bottom: var(--border-width-thin) solid var(--color-border); display: flex; min-height: var(--control-height-lg); }
.tournament-tabs button { align-items: center; align-self: stretch; background: transparent; border: 0; border-bottom: var(--border-width-strong) solid transparent; color: var(--color-text-muted); cursor: pointer; display: inline-flex; font-weight: var(--font-weight-semibold); gap: var(--space-2); min-height: var(--control-height-lg); padding: 0 var(--space-5); }
.tournament-tabs button[aria-selected="true"] { border-bottom-color: var(--color-accent); color: var(--color-text); }
.tournament-tabs button:hover { color: var(--color-text); }
.tournament-tabs button:focus-visible, .state-panel button:focus-visible, .simulation-controls button:focus-visible, .simulation-controls input:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.tournament-panel { min-width: 0; }
.live-loading { display: grid; gap: var(--space-4); grid-template-columns: repeat(3, minmax(0, 1fr)); }
.live-skeleton { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); min-height: 15rem; padding: var(--space-5); }
.skeleton-line { animation: skeleton-pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); }
.skeleton-heading { height: 1rem; margin-bottom: var(--space-6); width: 44%; }
.skeleton-row { height: 2.25rem; margin-top: var(--space-2); }
.live-summary { align-items: center; background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); display: flex; justify-content: space-between; padding: var(--space-4) var(--space-5); }
.live-summary > div { align-items: baseline; display: flex; flex-wrap: wrap; gap: var(--space-3); }
.live-summary > div > strong { font-family: var(--font-family-display); font-size: var(--font-size-lg); }
.status-label { align-items: center; color: var(--color-success); display: inline-flex; font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); gap: var(--space-2); text-transform: uppercase; }
.live-summary p { color: var(--color-text-muted); font-size: var(--font-size-xs); margin: 0; }
.live-summary p strong { color: var(--color-text); font-family: var(--font-family-data); }
.live-section { display: flex; flex-direction: column; gap: var(--space-4); margin-top: var(--space-7); }
.section-heading { align-items: baseline; border-bottom: var(--border-width-thin) solid var(--color-border); display: flex; justify-content: space-between; padding-bottom: var(--space-3); }
.section-heading h2 { font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0; }
.section-heading span { color: var(--color-text-subtle); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); }
.standings-grid { display: grid; gap: var(--space-4); grid-template-columns: repeat(2, minmax(0, 1fr)); }
.standings-panel { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); min-width: 0; }
.standings-panel > header { align-items: center; border-bottom: var(--border-width-thin) solid var(--color-border); display: flex; justify-content: space-between; padding: var(--space-3) var(--space-4); }
.standings-panel > header span { color: var(--color-text-muted); font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); text-transform: uppercase; }
.standings-panel > header strong { color: var(--color-accent); font: var(--font-weight-heavy) var(--font-size-xl) / 1 var(--font-family-data); }
.table-scroll { overflow-x: auto; }
table { border-collapse: collapse; min-width: 36rem; width: 100%; }
th, td { border-bottom: var(--border-width-thin) solid var(--color-border); font-size: var(--font-size-xs); padding: var(--space-3); text-align: left; }
thead th { color: var(--color-text-muted); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); text-transform: uppercase; }
tbody tr:last-child th, tbody tr:last-child td { border-bottom: 0; }
tbody th { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); min-width: 8rem; }
.numeric { font-variant-numeric: tabular-nums; text-align: right; }
.position { color: var(--color-text-subtle); font-family: var(--font-family-data); }
.data-value { color: var(--color-text-muted); font-family: var(--font-family-data); }
.live-matches { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); }
.live-match { align-items: center; border-bottom: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-3); grid-template-columns: 5.5rem minmax(6rem, 1fr) 4rem minmax(6rem, 1fr) 7rem; min-height: 3.75rem; padding: var(--space-2) var(--space-4); }
.live-match:last-child { border-bottom: 0; }
.match-stage { color: var(--color-text-subtle); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); text-transform: uppercase; }
.live-match strong { font-size: var(--font-size-sm); }
.home-team { text-align: right; }
.winner { color: var(--color-success); }
.match-score { font: var(--font-weight-heavy) var(--font-size-md) / 1 var(--font-family-data); text-align: center; }
.live-match time { color: var(--color-text-subtle); font: var(--font-weight-medium) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); text-align: right; }
.no-matches, .simulation-note { color: var(--color-text-muted); font-size: var(--font-size-sm); margin: 0; }
.state-panel { align-items: flex-start; background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); color: var(--color-accent); display: flex; gap: var(--space-4); padding: var(--space-8); }
.state-panel h2 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0; }
.state-panel p { color: var(--color-text-muted); line-height: var(--line-height-relaxed); margin: var(--space-2) 0 0; max-width: 52ch; }
.state-error { background: var(--color-danger-surface); color: var(--color-danger); }
.state-panel button { align-items: center; background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; display: inline-flex; font-weight: var(--font-weight-semibold); gap: var(--space-2); min-height: var(--control-height-lg); margin-top: var(--space-4); padding: 0 var(--space-4); }
.simulation-controls { align-items: end; background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); display: flex; gap: var(--space-6); justify-content: space-between; padding: var(--space-5); }
.simulation-controls label { align-items: flex-start; cursor: pointer; display: flex; gap: var(--space-3); }
.simulation-controls input { accent-color: var(--color-accent); height: 1.125rem; margin-top: 0.125rem; width: 1.125rem; }
.simulation-controls label span { color: var(--color-text-muted); display: flex; flex-direction: column; font-size: var(--font-size-xs); gap: var(--space-1); }
.simulation-controls label strong { color: var(--color-text); font-size: var(--font-size-sm); }
.simulation-controls button { align-items: center; background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; display: inline-flex; flex: 0 0 auto; font-weight: var(--font-weight-semibold); gap: var(--space-2); min-height: var(--control-height-lg); padding: 0 var(--space-5); }
.simulation-controls button:disabled { cursor: wait; opacity: 0.62; }
.simulation-note { margin: var(--space-3) 0 var(--space-6); }
.simulation-loading { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-6); grid-template-columns: minmax(14rem, 0.8fr) minmax(20rem, 1.2fr); padding: var(--space-8); }
.simulation-loading > div:first-child { align-items: flex-start; color: var(--color-accent); display: flex; flex-direction: column; gap: var(--space-3); }
.simulation-loading svg { animation: simulation-spin 1s linear infinite; }
.simulation-loading h2 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0; }
.simulation-loading p { color: var(--color-text-muted); line-height: var(--line-height-relaxed); margin: 0; }
.simulation-skeleton { display: grid; gap: var(--space-2); grid-template-columns: repeat(3, minmax(0, 1fr)); }
.simulation-skeleton span { animation: skeleton-pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); min-height: 5.5rem; }
.state-panel :deep(.billing-status), .state-panel :deep(.billing-plans-link) { margin-top: var(--space-4); }
.sr-only { border: 0; clip: rect(0 0 0 0); height: 1px; margin: -1px; overflow: hidden; padding: 0; position: absolute; white-space: nowrap; width: 1px; }
@keyframes skeleton-pulse { 50% { opacity: 0.45; } }
@keyframes simulation-spin { to { transform: rotate(360deg); } }
@media (max-width: 980px) { .standings-grid, .live-loading { grid-template-columns: 1fr; } }
@media (max-width: 720px) {
  .tournament-tabs button { flex: 1 1 50%; justify-content: center; padding: 0 var(--space-3); }
  .live-summary, .simulation-controls { align-items: flex-start; flex-direction: column; gap: var(--space-4); }
  .simulation-loading { grid-template-columns: 1fr; }
  .simulation-controls button { justify-content: center; width: 100%; }
  .live-match { grid-template-columns: 4rem minmax(0, 1fr) 3.5rem minmax(0, 1fr); }
  .live-match time { grid-column: 2 / -1; text-align: left; }
}
@media (max-width: 480px) {
  .tournament-tabs button { font-size: var(--font-size-xs); }
  .live-match { gap: var(--space-2); grid-template-columns: 1fr auto 1fr; padding: var(--space-3); }
  .match-stage { grid-column: 1 / -1; }
  .live-match time { grid-column: 1 / -1; }
  .state-panel { padding: var(--space-5); }
}
@media (prefers-reduced-motion: reduce) { .skeleton-line, .simulation-skeleton span, .simulation-loading svg { animation: none; } }
</style>
