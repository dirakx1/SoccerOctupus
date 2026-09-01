<template>
  <main class="league-view">
    <header class="page-heading"><p class="eyebrow">{{ t('competitions.league.performanceEyebrow') }}</p><h1>{{ t('competitions.league.performanceTitle') }}</h1><p>{{ t('competitions.league.performanceDescription') }}</p></header>
    <section v-if="loading" class="state-panel" aria-busy="true"><p>{{ t('competitions.league.loading') }}</p></section>
    <section v-else-if="error" class="state-panel state-error" role="alert"><p>{{ error }}</p><button type="button" @click="loadPerformance">{{ t('competitions.league.retry') }}</button></section>
    <template v-else>
      <section class="stats-grid"><div><span>{{ t('competitions.league.performanceSnapshots') }}</span><strong>{{ data.snapshots }}</strong></div><div><span>{{ t('competitions.league.performanceResolved') }}</span><strong>{{ data.resolvedSnapshots }}</strong></div><div><span>{{ t('competitions.league.performanceAccuracy') }}</span><strong>{{ percent(data.accuracy?.correctOutcomeRate) }}</strong></div><div><span>{{ t('competitions.league.performanceStatus') }}</span><strong class="status">{{ admission(data.accuracy?.status) }}</strong></div></section>
      <section class="result-card"><header><h2>{{ t('competitions.league.performanceFoundation') }}</h2><strong>{{ data.baseline?.provider }}</strong></header><p>{{ t('competitions.league.performanceFoundationDetail', { weight: data.baseline?.weight || 0 }) }}</p></section>
      <section class="result-card"><header><h2>{{ t('competitions.league.performanceProviders') }}</h2><span>{{ t('competitions.league.performanceProviderDescription') }}</span></header><div class="table-scroll"><table><thead><tr><th>{{ t('competitions.league.performanceProvider') }}</th><th>{{ t('competitions.league.performanceSnapshots') }}</th><th>{{ t('competitions.league.performanceResolved') }}</th><th>{{ t('competitions.league.performanceAvailability') }}</th><th>{{ t('competitions.league.performanceAdmission') }}</th></tr></thead><tbody><tr v-for="provider in data.providers" :key="provider.provider"><th>{{ provider.provider }}</th><td>{{ provider.snapshots }}</td><td>{{ provider.resolvedSnapshots }}</td><td>{{ availability(provider.statuses) }}</td><td><span class="badge">{{ admission(provider.admission) }}</span></td></tr></tbody></table></div></section>
    </template>
  </main>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { api } from '../lib/api'
import { leagueApiBase } from '../competition/leagueApi.js'

const { t } = useI18n(); const route = useRoute(); const loading = ref(true); const error = ref(''); const data = ref({ snapshots: 0, resolvedSnapshots: 0, accuracy: {}, baseline: {}, providers: [] })
const percent = (value) => value == null ? '—' : new Intl.NumberFormat(route.params.locale, { style: 'percent', maximumFractionDigits: 1 }).format(value)
const admission = (value) => t(`competitions.league.performanceAdmission${String(value || 'not-collected').replace(/(^|-)([a-z])/g, (_, __, letter) => letter.toUpperCase())}`)
const availability = (statuses = {}) => Object.entries(statuses).map(([status, count]) => `${status}: ${count}`).join(' · ') || '—'
async function loadPerformance() { loading.value = true; error.value = ''; try { data.value = (await api.get(`${leagueApiBase(route.params.competitionEditionSlug)}/performance`)).data.performance } catch (cause) { error.value = cause.response?.data?.error || t('competitions.league.loadFailed') } finally { loading.value = false } }
watch(() => route.params.competitionEditionSlug, loadPerformance, { immediate: true })
</script>

<style scoped>
.league-view { display: grid; gap: var(--space-6); min-width: 0; }.page-heading, .result-card { display: grid; gap: var(--space-3); }.page-heading h1, h2 { font-family: var(--font-family-display); margin: 0; }.page-heading p:last-child, .result-card p, .result-card header span { color: var(--color-text-muted); margin: 0; }.eyebrow { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / 1.2 var(--font-family-data); letter-spacing: .08em; margin: 0; text-transform: uppercase; }.state-panel, .stats-grid > div, .result-card { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); padding: var(--space-5); }.state-panel { align-items: center; display: flex; justify-content: space-between; }.state-error { background: var(--color-danger-surface); color: var(--color-danger); }.stats-grid { display: grid; gap: var(--space-4); grid-template-columns: repeat(4, minmax(0, 1fr)); }.stats-grid > div { display: grid; gap: var(--space-2); }.stats-grid span { color: var(--color-text-muted); font-size: var(--font-size-xs); }.stats-grid strong { font: var(--font-weight-heavy) var(--font-size-2xl) / 1 var(--font-family-data); }.status { font-size: var(--font-size-lg) !important; }.result-card header { align-items: baseline; display: flex; gap: var(--space-3); justify-content: space-between; }.table-scroll { overflow-x: auto; }table { border-collapse: collapse; min-width: 42rem; text-align: left; width: 100%; }th, td { border-bottom: var(--border-width-thin) solid var(--color-border); padding: var(--space-3) var(--space-2); }.badge { background: var(--color-surface-raised); border: var(--border-width-thin) solid var(--color-border); font-size: var(--font-size-xs); padding: var(--space-1) var(--space-2); }button { background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; min-height: var(--control-height-lg); padding: 0 var(--space-3); }@media (max-width: 720px) { .stats-grid { grid-template-columns: 1fr 1fr; } }@media (max-width: 480px) { .stats-grid { grid-template-columns: 1fr; } }
</style>
