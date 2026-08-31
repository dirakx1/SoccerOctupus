<template>
  <main class="atlas-table-page">
    <AtlasPageHeader
      :eyebrow="t('competitions.league.tableEyebrow', { competition: t(edition.displayNameKey) })"
      :title="t('competitions.league.tableTitle')"
      :description="t('competitions.league.tableDescriptionGeneric', { competition: t(edition.displayNameKey) })"
    >
      <template #actions>
        <div class="table-stat"><strong>{{ rows.length }}</strong><span>{{ t('competitions.league.clubCountLabel') }}</span></div>
        <div class="table-stat"><strong>{{ completedMatches }}</strong><span>{{ t('competitions.league.completedCountLabel') }}</span></div>
      </template>
    </AtlasPageHeader>

    <section v-if="loading" class="standings-panel table-skeleton" aria-busy="true">
      <div class="skeleton-table-heading" aria-hidden="true"><span /><span /></div>
      <div v-for="row in 10" :key="row" class="skeleton-table-row" aria-hidden="true"><span /><span /><span /><span /></div>
    </section>

    <section v-else-if="error" class="table-state state-error" role="alert">
      <AlertTriangle :size="22" aria-hidden="true" />
      <div>
        <h2>{{ t('competitions.league.tableErrorTitle') }}</h2>
        <p>{{ error }}</p>
        <button type="button" @click="loadTable"><RotateCcw :size="15" aria-hidden="true" />{{ t('competitions.league.retry') }}</button>
      </div>
    </section>

    <section v-else-if="!rows.length" class="table-state" aria-live="polite">
      <Inbox :size="22" aria-hidden="true" />
      <div><h2>{{ t('competitions.league.tableEmptyTitle') }}</h2><p>{{ t('competitions.league.tableEmptyDescription') }}</p></div>
    </section>

    <section v-else class="standings-panel" :aria-label="t('competitions.league.tableTitle')">
      <div class="table-wrap">
        <table>
          <thead><tr><th scope="col">#</th><th scope="col">{{ t('competitions.league.club') }}</th><th scope="col">{{ t('competitions.league.played') }}</th><th scope="col">{{ t('competitions.league.won') }}</th><th scope="col">{{ t('competitions.league.drawn') }}</th><th scope="col">{{ t('competitions.league.lost') }}</th><th scope="col">{{ t('competitions.league.goalsFor') }}</th><th scope="col">{{ t('competitions.league.goalsAgainst') }}</th><th scope="col">{{ t('competitions.league.goalDifference') }}</th><th scope="col">{{ t('competitions.league.points') }}</th></tr></thead>
          <tbody><tr v-for="row in rows" :key="row.teamId"><td class="position">{{ row.position }}</td><th scope="row">{{ row.team.name }}</th><td>{{ row.played }}</td><td>{{ row.won }}</td><td>{{ row.drawn }}</td><td>{{ row.lost }}</td><td>{{ row.goalsFor }}</td><td>{{ row.goalsAgainst }}</td><td>{{ signed(row.goalDifference) }}</td><td class="points"><strong>{{ row.points }}</strong></td></tr></tbody>
        </table>
      </div>
      <footer><span>{{ t('competitions.league.tableUpdatedFromResults') }}</span><router-link :to="fixturesLocation">{{ t('competitions.league.viewResults') }}</router-link></footer>
    </section>
  </main>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { AlertTriangle, Inbox, RotateCcw } from '@lucide/vue'

import AtlasPageHeader from '../ui/patterns/AtlasPageHeader.vue'
import { getCompetitionEdition } from '../competition/index.js'
import { leagueApiBase } from '../competition/leagueApi.js'
import { workspaceLocation } from '../router/workspace.js'
import { api } from '../lib/api'

const { t } = useI18n()
const route = useRoute()
const rows = ref([])
const loading = ref(true)
const error = ref('')
const edition = computed(() => getCompetitionEdition(route.params.competitionEditionSlug))
const completedMatches = computed(() => Math.round(rows.value.reduce((total, row) => total + Number(row.played || 0), 0) / 2))
const fixturesLocation = computed(() => workspaceLocation('fixtures', { locale: route.params.locale, competitionEditionSlug: route.params.competitionEditionSlug }))

async function loadTable() {
  loading.value = true
  error.value = ''
  try {
    rows.value = (await api.get(`${leagueApiBase(route.params.competitionEditionSlug)}/table`)).data.standings || []
  } catch (cause) {
    error.value = cause.response?.data?.error || t('competitions.league.loadFailed')
  } finally {
    loading.value = false
  }
}

function signed(value) { return Number(value) > 0 ? `+${value}` : value }

watch(() => route.params.competitionEditionSlug, loadTable, { immediate: true })
</script>

<style scoped>
.atlas-table-page { display: flex; flex-direction: column; gap: var(--space-6); min-width: 0; }
.table-stat { align-items: baseline; border-left: var(--border-width-thin) solid var(--color-border); display: flex; flex-direction: column; gap: var(--space-1); min-width: 5rem; padding-left: var(--space-3); }
.table-stat strong { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xl) / var(--line-height-tight) var(--font-family-data); }
.table-stat span { color: var(--color-text-muted); font-size: var(--font-size-xs); white-space: nowrap; }
.standings-panel { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); min-width: 0; }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; min-width: 54rem; text-align: left; width: 100%; }
th, td { border-bottom: var(--border-width-thin) solid var(--color-border); font-size: var(--font-size-sm); padding: var(--space-3) var(--space-4); }
thead th { color: var(--color-text-muted); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); text-transform: uppercase; }
thead th:not(:nth-child(2)), tbody td { text-align: right; }
tbody tr:last-child th, tbody tr:last-child td { border-bottom: 0; }
tbody th { font-weight: var(--font-weight-semibold); }
.position { color: var(--color-text-subtle); font-family: var(--font-family-data); width: 2.5rem; }
.points { color: var(--color-accent); font-family: var(--font-family-data); font-variant-numeric: tabular-nums; }
.standings-panel footer { align-items: center; border-top: var(--border-width-thin) solid var(--color-border); color: var(--color-text-muted); display: flex; font-size: var(--font-size-xs); gap: var(--space-4); justify-content: space-between; padding: var(--space-4); }
.standings-panel footer a { color: var(--color-accent); font-weight: var(--font-weight-semibold); }
.table-state { align-items: flex-start; background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); color: var(--color-accent); display: flex; gap: var(--space-4); padding: var(--space-8); }
.table-state h2 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0; }
.table-state p { color: var(--color-text-muted); line-height: var(--line-height-relaxed); margin: var(--space-2) 0 0; }
.table-state button { align-items: center; background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; display: inline-flex; font-weight: var(--font-weight-semibold); gap: var(--space-2); min-height: var(--control-height-lg); margin-top: var(--space-4); padding: 0 var(--space-4); }
.state-error { background: var(--color-danger-surface); border-color: var(--color-danger); color: var(--color-danger); }
.state-error > svg { color: var(--color-danger); }
.table-skeleton { display: grid; gap: var(--space-3); padding: var(--space-5); }
.skeleton-table-heading, .skeleton-table-row { align-items: center; display: grid; gap: var(--space-3); grid-template-columns: 3rem 1fr repeat(2, 5rem); }
.skeleton-table-heading { border-bottom: var(--border-width-thin) solid var(--color-border); padding-bottom: var(--space-3); }
.skeleton-table-heading span, .skeleton-table-row span { animation: skeleton-pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); display: block; height: .9rem; }
.skeleton-table-heading span:last-child { grid-column: 2; width: 35%; }
.skeleton-table-row { border-bottom: var(--border-width-thin) solid var(--color-border); min-height: 2.75rem; }
.skeleton-table-row span:nth-child(2) { width: 70%; }
@keyframes skeleton-pulse { 50% { opacity: .45; } }
@media (max-width: 640px) { .standings-panel footer { align-items: flex-start; flex-direction: column; }.table-state { padding: var(--space-5); } }
@media (prefers-reduced-motion: reduce) { .skeleton-table-heading span, .skeleton-table-row span { animation: none; } }
</style>
