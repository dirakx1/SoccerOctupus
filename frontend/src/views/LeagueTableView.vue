<template>
  <main class="league-view">
    <header class="page-heading"><p class="eyebrow">{{ t('competitions.league.currentTable') }}</p><h1>{{ t('competitions.league.tableTitle') }}</h1></header>
    <section v-if="loading" class="table-card table-skeleton" aria-busy="true">
      <div class="skeleton-table-heading" aria-hidden="true"><span /><span /></div>
      <div v-for="row in 10" :key="row" class="skeleton-table-row" aria-hidden="true"><span /><span /><span /><span /></div>
    </section>
    <section v-else-if="error" class="state-panel state-error" role="alert"><p>{{ error }}</p><button type="button" @click="loadTable">{{ t('competitions.league.retry') }}</button></section>
    <section v-else class="table-card"><table><thead><tr><th scope="col">#</th><th scope="col">{{ t('competitions.league.club') }}</th><th scope="col">{{ t('competitions.league.played') }}</th><th scope="col">{{ t('competitions.league.won') }}</th><th scope="col">{{ t('competitions.league.drawn') }}</th><th scope="col">{{ t('competitions.league.lost') }}</th><th scope="col">{{ t('competitions.league.goalsFor') }}</th><th scope="col">{{ t('competitions.league.goalsAgainst') }}</th><th scope="col">{{ t('competitions.league.goalDifference') }}</th><th scope="col">{{ t('competitions.league.points') }}</th></tr></thead><tbody><tr v-for="row in rows" :key="row.teamId"><td>{{ row.position }}</td><th scope="row">{{ row.team.name }}</th><td>{{ row.played }}</td><td>{{ row.won }}</td><td>{{ row.drawn }}</td><td>{{ row.lost }}</td><td>{{ row.goalsFor }}</td><td>{{ row.goalsAgainst }}</td><td>{{ row.goalDifference }}</td><td><strong>{{ row.points }}</strong></td></tr></tbody></table></section>

  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { api } from '../lib/api'
import { leagueApiBase } from '../competition/leagueApi.js'

const { t } = useI18n()
const route = useRoute()
const rows = ref([]); const loading = ref(true); const error = ref('')
async function loadTable() {
  loading.value = true; error.value = ''
  try { rows.value = (await api.get(`${leagueApiBase(route.params.competitionEditionSlug)}/table`)).data.standings || [] }
  catch (cause) { error.value = cause.response?.data?.error || t('competitions.league.loadFailed') }
  finally { loading.value = false }
}
onMounted(loadTable)
</script>

<style scoped>
.league-view { display: grid; gap: var(--space-6); min-width: 0; }.page-heading { display: grid; gap: var(--space-2); }.page-heading h1, h2, h3 { font-family: var(--font-family-display); margin: 0; }.eyebrow { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / 1.2 var(--font-family-data); letter-spacing: .08em; margin: 0; text-transform: uppercase; }.state-panel, .table-card, .projection-card { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); padding: var(--space-5); }.state-panel { align-items: center; display: flex; justify-content: space-between; }.state-error, .projection-error { background: var(--color-danger-surface); color: var(--color-danger); }.state-panel p, .projection-error { margin: 0; }button, select { min-height: var(--control-height-lg); padding: 0 var(--space-3); }button { background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; font-weight: var(--font-weight-semibold); }table { border-collapse: collapse; min-width: 54rem; text-align: left; width: 100%; }th, td { border-bottom: var(--border-width-thin) solid var(--color-border); padding: var(--space-3) var(--space-2); }th { font-size: var(--font-size-xs); text-transform: uppercase; }.table-card { overflow-x: auto; }.projection-card { display: grid; gap: var(--space-4); }.projection-card header { align-items: start; display: flex; justify-content: space-between; }.projection-card header span { color: var(--color-text-muted); font-size: var(--font-size-xs); }.projection-summary { display: grid; gap: var(--space-3); grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 0; }.projection-summary div { border-top: var(--border-width-thin) solid var(--color-border); padding-top: var(--space-2); }.projection-summary dt { color: var(--color-text-muted); font-size: var(--font-size-xs); }.projection-summary dd { font: var(--font-weight-bold) var(--font-size-lg) / 1.2 var(--font-family-data); margin: var(--space-1) 0 0; }.position-distribution { display: grid; gap: var(--space-2); grid-template-columns: repeat(7, minmax(0, 1fr)); list-style: none; margin: 0; padding: 0; }.position-distribution li { display: grid; gap: var(--space-1); text-align: center; }.position-distribution i { background: var(--color-surface-inset); height: .45rem; }.position-distribution b { background: var(--color-accent); display: block; height: 100%; }.position-distribution strong { font: var(--font-weight-semibold) var(--font-size-xs) / 1 var(--font-family-data); }@media (max-width: 720px) { .projection-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }.position-distribution { grid-template-columns: repeat(5, minmax(0, 1fr)); } }
.select-field { display: block; position: relative; }
.select-field select { appearance: none; padding-right: calc(var(--space-4) + 1.5rem); width: 100%; }
.select-field svg { color: var(--color-text-muted); pointer-events: none; position: absolute; right: var(--space-4); top: 50%; transform: translateY(-50%); }
.projection-card select { appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%236f6a63' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E"); background-position: right var(--space-4) center; background-repeat: no-repeat; background-size: 1.125rem; padding-right: calc(var(--space-4) + 1.5rem); width: 100%; }
.table-skeleton { display: grid; gap: var(--space-3); }
.projection-card > header > span { display: none; }
.skeleton-table-heading, .skeleton-table-row { align-items: center; display: grid; gap: var(--space-3); grid-template-columns: 3rem 1fr repeat(2, 5rem); }
.skeleton-table-heading { border-bottom: var(--border-width-thin) solid var(--color-border); padding-bottom: var(--space-3); }
.skeleton-table-heading span, .skeleton-table-row span, .projection-placeholder span { animation: skeleton-pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); display: block; }
.skeleton-table-heading span { height: .7rem; }
.skeleton-table-heading span:last-child { grid-column: 2; width: 35%; }
.skeleton-table-row { border-bottom: var(--border-width-thin) solid var(--color-border); min-height: 2.75rem; }
.skeleton-table-row span { height: .9rem; }
.skeleton-table-row span:nth-child(2) { width: 70%; }
.projection-placeholder { display: grid; gap: var(--space-4); grid-template-columns: repeat(3, minmax(0, 1fr)); }
.projection-placeholder span { min-height: 5rem; }
@keyframes skeleton-pulse { 50% { opacity: .45; } }
@media (prefers-reduced-motion: reduce) { .skeleton-table-heading span, .skeleton-table-row span, .projection-placeholder span { animation: none; } }
</style>
