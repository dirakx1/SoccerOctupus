<template>
  <main class="league-table-view">
    <section v-if="loading" data-testid="league-table-loading" class="table-skeleton" aria-busy="true">
      <header class="skeleton-table-heading" aria-hidden="true">
        <div><span class="skeleton-line skeleton-eyebrow"></span><span class="skeleton-line skeleton-title"></span></div>
        <div><span class="skeleton-line skeleton-source"></span><span class="skeleton-line skeleton-updated"></span></div>
      </header>
      <div class="skeleton-table" aria-hidden="true">
        <div class="skeleton-table-labels"><span v-for="column in 10" :key="column" class="skeleton-line"></span></div>
        <div v-for="row in 10" :key="row" class="skeleton-table-row">
          <span class="skeleton-line skeleton-cell skeleton-position"></span>
          <span class="skeleton-line skeleton-cell skeleton-team"></span>
          <span class="skeleton-line skeleton-cell skeleton-stat"></span>
          <span class="skeleton-line skeleton-cell skeleton-stat"></span>
        </div>
      </div>
    </section>
    <section v-else-if="error" data-testid="league-table-error" class="table-state" role="alert">
      <CircleAlert :size="24" aria-hidden="true" />
      <h1>{{ t('league.table.errorTitle') }}</h1>
      <p>{{ t('league.table.error') }}</p>
      <button type="button" @click="loadTable">{{ t('league.states.retry') }}</button>
    </section>
    <template v-else-if="table">
      <header class="table-heading">
        <div>
          <p>{{ t('league.table.eyebrow') }}</p>
          <h1>{{ table.edition.display_name }}</h1>
        </div>
        <p data-testid="league-table-source">
          {{ t('league.table.source', { source: table.source }) }}<br>
          <small>{{ t('league.table.updated', { date: formatDate(table.source_updated_at) }) }}</small>
        </p>
      </header>
      <FreshnessDisclosure :freshness="table.freshness" @retry="loadTable" />
      <p v-if="!table.freshness && table.stale" data-testid="league-table-stale" class="legacy-stale" role="status">
        {{ t('league.table.stale') }}
      </p>
      <section v-if="!table.standings.length" data-testid="league-table-empty" class="table-state">
        <p>{{ t('league.table.empty') }}</p>
      </section>
      <div v-else class="table-scroll">
        <table>
          <thead><tr>
            <th v-for="column in columns" :key="column.key" scope="col" :class="column.className">
              <abbr v-if="column.short" :title="t(column.label)">{{ t(column.short) }}</abbr>
              <span v-else>{{ t(column.label) }}</span>
            </th>
          </tr></thead>
          <tbody><tr v-for="row in table.standings" :key="row.team.slug">
            <td>{{ row.position }}</td><th scope="row">{{ row.team.display_name }}</th>
            <td>{{ row.played }}</td><td>{{ row.won }}</td><td>{{ row.drawn }}</td><td>{{ row.lost }}</td>
            <td>{{ row.goals_for }}</td><td>{{ row.goals_against }}</td><td>{{ signed(row.goal_difference) }}</td><td class="points">{{ row.points }}</td>
          </tr></tbody>
        </table>
      </div>
    </template>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { CircleAlert } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { api } from '../lib/api.js'
import FreshnessDisclosure from '../components/FreshnessDisclosure.vue'

const props = defineProps({
  competitionSlug: { type: String, required: true },
  editionSlug: { type: String, required: true },
})
const { locale, t } = useI18n()
const table = ref(null)
const loading = ref(true)
const error = ref(false)
const columns = [
  { key: 'position', label: 'league.table.columns.position', short: 'league.table.abbreviations.position' },
  { key: 'team', label: 'league.table.columns.team' },
  { key: 'played', label: 'league.table.columns.played', short: 'league.table.abbreviations.played' },
  { key: 'won', label: 'league.table.columns.won', short: 'league.table.abbreviations.won' },
  { key: 'drawn', label: 'league.table.columns.drawn', short: 'league.table.abbreviations.drawn' },
  { key: 'lost', label: 'league.table.columns.lost', short: 'league.table.abbreviations.lost' },
  { key: 'goalsFor', label: 'league.table.columns.goalsFor', short: 'league.table.abbreviations.goalsFor' },
  { key: 'goalsAgainst', label: 'league.table.columns.goalsAgainst', short: 'league.table.abbreviations.goalsAgainst' },
  { key: 'goalDifference', label: 'league.table.columns.goalDifference', short: 'league.table.abbreviations.goalDifference' },
  { key: 'points', label: 'league.table.columns.points', short: 'league.table.abbreviations.points' },
]

async function loadTable() {
  loading.value = true
  error.value = false
  try {
    const { data } = await api.get(`/api/competitions/${props.competitionSlug}/editions/${props.editionSlug}/table`)
    table.value = data
  } catch {
    table.value = null
    error.value = true
  } finally {
    loading.value = false
  }
}

function formatDate(value) {
  return new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function signed(value) { return value > 0 ? `+${value}` : value }

onMounted(loadTable)
</script>

<style scoped>
.league-table-view { display: flex; flex-direction: column; gap: var(--space-6); padding: var(--space-8) 0; }
.table-heading { align-items: flex-end; border-bottom: var(--border-width-thin) solid var(--color-border); display: flex; justify-content: space-between; padding-bottom: var(--space-6); }
.table-heading p { color: var(--color-text-muted); margin: 0; }
.table-heading div > p { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / 1 var(--font-family-data); text-transform: uppercase; }
.table-heading h1 { font-family: var(--font-family-display); font-size: var(--font-size-3xl); letter-spacing: 0; margin: var(--space-2) 0 0; }
.table-heading > p { text-align: right; }
.legacy-stale { background: var(--color-warning-surface); border-left: var(--border-width-strong) solid var(--color-warning); margin: 0; padding: var(--space-3); }
.table-scroll { overflow-x: auto; }
table { border-collapse: collapse; min-width: 48rem; width: 100%; }
th, td { border-bottom: var(--border-width-thin) solid var(--color-border); height: 3.25rem; padding: 0 var(--space-3); text-align: right; }
thead th { color: var(--color-text-muted); font: var(--font-weight-bold) var(--font-size-xs) / 1 var(--font-family-data); text-transform: uppercase; }
th:nth-child(2), tbody th { text-align: left; }
tbody th { font-weight: var(--font-weight-semibold); }
.points { font-weight: var(--font-weight-heavy); }
.table-state { align-items: flex-start; display: flex; flex-direction: column; gap: var(--space-3); min-height: 20rem; justify-content: center; }
.table-state h1, .table-state p { margin: 0; }
.table-state button { background: var(--color-accent); border: 0; color: var(--color-accent-contrast); min-height: var(--control-height-lg); padding: 0 var(--space-4); }
.table-skeleton { display: flex; flex-direction: column; gap: var(--space-6); padding: var(--space-8) 0; }
.skeleton-line { animation: skeleton-pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); display: block; }
.skeleton-table-heading { align-items: flex-end; border-bottom: var(--border-width-thin) solid var(--color-border); display: flex; justify-content: space-between; padding-bottom: var(--space-6); }
.skeleton-table-heading > div { display: flex; flex-direction: column; gap: var(--space-2); }
.skeleton-table-heading > div:last-child { align-items: flex-end; }
.skeleton-eyebrow { height: .75rem; width: 10rem; }
.skeleton-title { height: 2.25rem; width: 22rem; }
.skeleton-source { height: 1rem; width: 9rem; }
.skeleton-updated { height: .75rem; width: 12rem; }
.skeleton-table { min-width: 48rem; overflow: hidden; }
.skeleton-table-labels { border-bottom: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-4); grid-template-columns: 2rem minmax(12rem, 1fr) repeat(8, 2rem); height: 3.25rem; padding: 0 var(--space-3); }
.skeleton-table-labels .skeleton-line { align-self: center; height: .7rem; }
.skeleton-table-row { align-items: center; border-bottom: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-4); grid-template-columns: 2rem minmax(12rem, 1fr) 3rem 3rem; height: 3.25rem; padding: 0 var(--space-3); }
.skeleton-cell { height: .85rem; }
.skeleton-position { width: 1rem; }
.skeleton-team { max-width: 12rem; width: 58%; }
.skeleton-stat { justify-self: end; width: 1.5rem; }
@keyframes skeleton-pulse { 50% { opacity: .45; } }
@media (max-width: 720px) { .table-heading, .skeleton-table-heading { align-items: flex-start; flex-direction: column; gap: var(--space-3); } .table-heading > p { text-align: left; } .skeleton-table-heading > div:last-child { align-items: flex-start; } .skeleton-title { max-width: 22rem; width: 78vw; } .table-skeleton { overflow-x: hidden; } }
@media (prefers-reduced-motion: reduce) { .skeleton-line { animation: none; } }
</style>
