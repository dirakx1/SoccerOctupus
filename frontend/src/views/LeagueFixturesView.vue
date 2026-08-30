<template>
  <main class="league-view">
    <header class="page-heading"><p class="eyebrow">{{ t('competitions.league.fixturesTitle') }}</p><h1>{{ t('competitions.league.fixturesTitle') }}</h1></header>
    <section v-if="loading" class="fixture-groups fixture-skeleton" aria-busy="true">
      <article v-for="group in 3" :key="group" class="fixture-skeleton-group" aria-hidden="true">
        <span class="skeleton-fixture-heading" />
        <ul><li v-for="row in 4" :key="row"><span /><span /><span /></li></ul>
      </article>
    </section>
    <section v-else-if="error" class="state-panel state-error" role="alert"><p>{{ error }}</p><button type="button" @click="loadFixtures">{{ t('competitions.league.retry') }}</button></section>
    <template v-else>
      <section class="filters" :aria-label="t('competitions.league.fixturesTitle')"><label for="fixture-status">{{ t('competitions.league.statusFilter') }}</label><select id="fixture-status" v-model="statusFilter"><option value="scheduled">{{ t('competitions.league.upcomingFilter') }}</option><option value="completed">{{ t('competitions.league.resultsFilter') }}</option><option value="all">{{ t('competitions.league.allFilter') }}</option></select><label for="fixture-club">{{ t('competitions.league.clubFilter') }}</label><select id="fixture-club" v-model="clubFilter"><option value="">{{ t('competitions.league.allClubs') }}</option><option v-for="club in clubs" :key="club.id" :value="club.id">{{ club.name }}</option></select></section>
      <section v-if="!groups.length" class="state-panel"><p>{{ t('competitions.league.noFixtures') }}</p></section>
      <section v-else class="fixture-groups"><article v-for="group in groups" :key="group.label"><h2>{{ group.label }}</h2><ul><li v-for="fixture in group.fixtures" :key="fixture.id"><time>{{ format(fixture.kickoff) }}</time><strong>{{ fixture.homeTeam.name }} {{ t('competitions.league.versus') }} {{ fixture.awayTeam.name }}</strong><span>{{ status(fixture) }}</span></li></ul></article><button v-if="hasMore" type="button" @click="visibleLimit += pageSize">{{ t('competitions.league.showMore') }}</button></section>
    </template>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { api } from '../lib/api'
import { leagueApiBase } from '../competition/leagueApi.js'
const { locale, t } = useI18n(); const route = useRoute(); const fixtures = ref([]); const loading = ref(true); const error = ref(''); const statusFilter = ref('scheduled'); const clubFilter = ref(''); const visibleLimit = ref(30); const pageSize = 30
const clubs = computed(() => { const known = new Map(); for (const fixture of fixtures.value) for (const team of [fixture.homeTeam, fixture.awayTeam]) if (team?.id && !known.has(String(team.id))) known.set(String(team.id), { id: String(team.id), name: team.name }); return [...known.values()].sort((a, b) => a.name.localeCompare(b.name, locale.value)) })
const filteredFixtures = computed(() => fixtures.value.filter((fixture) => (statusFilter.value === 'all' || fixture.status === statusFilter.value) && (!clubFilter.value || String(fixture.homeTeam?.id) === clubFilter.value || String(fixture.awayTeam?.id) === clubFilter.value)))
const visibleFixtures = computed(() => filteredFixtures.value.slice(0, visibleLimit.value))
const hasMore = computed(() => visibleFixtures.value.length < filteredFixtures.value.length)
const groups = computed(() => { const grouped = new Map(); for (const fixture of visibleFixtures.value) { const label = fixture.matchweek != null ? t('competitions.league.matchweek', { week: fixture.matchweek }) : new Intl.DateTimeFormat(locale.value, { month: 'long', year: 'numeric' }).format(new Date(fixture.kickoff)); if (!grouped.has(label)) grouped.set(label, []); grouped.get(label).push(fixture) } return [...grouped].map(([label, rows]) => ({ label, fixtures: rows })) })
async function loadFixtures() { loading.value = true; error.value = ''; try { fixtures.value = (await api.get(`${leagueApiBase(route.params.competitionEditionSlug)}/fixtures`)).data.fixtures || [] } catch (cause) { error.value = cause.response?.data?.error || t('competitions.league.loadFailed') } finally { loading.value = false } }
function format(value) { return new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }
function status(fixture) { if (fixture.homeScore != null) return `${fixture.homeScore}–${fixture.awayScore}`; const key = { scheduled: 'statusScheduled', postponed: 'statusPostponed', cancelled: 'statusCancelled' }[fixture.status]; return key ? t(`competitions.league.${key}`) : fixture.status }
watch([statusFilter, clubFilter], () => { visibleLimit.value = pageSize })
onMounted(loadFixtures)
</script>

<style scoped>
.league-view { display: grid; gap: var(--space-6); min-width: 0; }.page-heading, article { display: grid; gap: var(--space-2); }.page-heading h1, h2 { font-family: var(--font-family-display); margin: 0; }.eyebrow { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / 1.2 var(--font-family-data); letter-spacing: .08em; margin: 0; text-transform: uppercase; }.state-panel { align-items: center; background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); display: flex; justify-content: space-between; padding: var(--space-5); }.state-error { background: var(--color-danger-surface); color: var(--color-danger); }.state-panel p { margin: 0; }.filters { align-items: center; background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); display: flex; flex-wrap: wrap; gap: var(--space-3); padding: var(--space-4); }.filters label { color: var(--color-text-muted); font-size: var(--font-size-xs); }.filters select { min-height: var(--control-height-lg); padding: 0 var(--space-3); }button { background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; min-height: var(--control-height-lg); padding: 0 var(--space-3); }.fixture-groups { display: grid; gap: var(--space-6); }.fixture-groups ul { list-style: none; margin: 0; padding: 0; }.fixture-groups li { align-items: center; border-bottom: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-4); grid-template-columns: 12rem 1fr auto; padding: var(--space-3) 0; }.fixture-groups time, .fixture-groups li span { color: var(--color-text-muted); font-size: var(--font-size-xs); }@media (max-width: 720px) { .fixture-groups li { align-items: start; grid-template-columns: 1fr auto; }.fixture-groups time { grid-column: 1 / -1; } }
.filters select { appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%236f6a63' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E"); background-position: right var(--space-4) center; background-repeat: no-repeat; background-size: 1.125rem; padding-right: calc(var(--space-4) + 1.5rem); }
.fixture-skeleton { gap: var(--space-5); }
.fixture-skeleton-group { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); padding: var(--space-5); }
.skeleton-fixture-heading, .fixture-skeleton li span { animation: skeleton-pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); display: block; }
.skeleton-fixture-heading { height: 1.25rem; margin-bottom: var(--space-4); width: 20%; }
.fixture-skeleton li { grid-template-columns: 12rem 1fr 5rem; }
.fixture-skeleton li span { height: 1rem; }
.fixture-skeleton li span:nth-child(2) { width: 72%; }
@keyframes skeleton-pulse { 50% { opacity: .45; } }
@media (prefers-reduced-motion: reduce) { .skeleton-fixture-heading, .fixture-skeleton li span { animation: none; } }
@media (max-width: 720px) { .fixture-skeleton li { grid-template-columns: 1fr auto; } .fixture-skeleton li span:first-child { grid-column: 1 / -1; } }
</style>
