<template>
  <main class="league-view">
    <header class="page-heading"><p class="eyebrow">{{ t('competitions.league.seasonOverview') }}</p><h1>{{ t(edition.displayNameKey) }}</h1><p>{{ t('competitions.league.overviewDescription') }}</p></header>
    <section v-if="loading" class="state-panel" aria-busy="true"><p>{{ t('competitions.league.loading') }}</p></section>
    <section v-else-if="error" class="state-panel state-error" role="alert"><p>{{ error }}</p><button type="button" @click="loadOverview">{{ t('competitions.league.retry') }}</button></section>
    <template v-else>
      <section class="content-grid"><div class="result-card"><header><h2>{{ t('competitions.league.currentTable') }}</h2><router-link :to="link('table')">{{ t('competitions.league.viewTable') }}</router-link></header><ol><li v-for="row in data.standings.slice(0, 8)" :key="row.teamId"><span>{{ row.position }}</span><strong>{{ row.team.name }}</strong><small>{{ row.points }} {{ t('competitions.league.points') }}</small></li></ol></div><div class="result-card"><header><h2>{{ t('competitions.league.nextFixtures') }}</h2><router-link :to="link('fixtures')">{{ t('competitions.league.viewAll') }}</router-link></header><ul v-if="nextFixtures.length"><li v-for="fixture in nextFixtures" :key="fixture.id"><time class="fixture-date" :datetime="fixture.kickoff"><strong>{{ formatDate(fixture.kickoff) }}</strong><span>{{ formatTime(fixture.kickoff) }}</span></time><strong class="fixture-teams"><span>{{ fixture.homeTeam.name }}</span><span>{{ fixture.awayTeam.name }}</span></strong></li></ul><p v-else>{{ t('competitions.league.noNextFixtures') }}</p></div></section>
      <nav class="league-links"><router-link :to="link('predict')">{{ t('competitions.league.makePrediction') }}</router-link><router-link :to="link('markets')">{{ t('competitions.league.exploreMarkets') }}</router-link></nav>
    </template>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { api } from '../lib/api'
import { getCompetitionEdition } from '../competition/index.js'
import { workspaceLocation } from '../router/workspace.js'
import { leagueApiBase } from '../competition/leagueApi.js'
const { locale, t } = useI18n(); const route = useRoute(); const loading = ref(true); const error = ref(''); const data = ref({ teams: [], fixtures: [], standings: [], evidence: { completedMatches: 0 } }); const edition = computed(() => getCompetitionEdition(route.params.competitionEditionSlug))
const nextFixtures = computed(() => data.value.fixtures.filter((fixture) => fixture.status === 'scheduled' && new Date(fixture.kickoff).getTime() > Date.now()).slice(0, 5))
const link = (area) => workspaceLocation(area, { locale: route.params.locale, competitionEditionSlug: route.params.competitionEditionSlug })
async function loadOverview() { loading.value = true; error.value = ''; try { data.value = (await api.get(leagueApiBase(route.params.competitionEditionSlug))).data } catch (cause) { error.value = cause.response?.data?.error || t('competitions.league.loadFailed') } finally { loading.value = false } }
function formatDate(value) { return new Intl.DateTimeFormat(locale.value, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value)) }
function formatTime(value) { return new Intl.DateTimeFormat(locale.value, { timeStyle: 'short' }).format(new Date(value)) }
onMounted(loadOverview)
</script>

<style scoped>
.league-view { display: grid; gap: var(--space-6); min-width: 0; }.page-heading, .result-card { display: grid; gap: var(--space-3); }.page-heading h1, h2 { font-family: var(--font-family-display); margin: 0; }.page-heading p:last-child { color: var(--color-text-muted); margin: 0; }.eyebrow { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / 1.2 var(--font-family-data); letter-spacing: .08em; margin: 0; text-transform: uppercase; }.state-panel, .result-card { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); padding: var(--space-5); }.state-panel { align-items: center; display: flex; justify-content: space-between; }.state-error { background: var(--color-danger-surface); color: var(--color-danger); }.state-panel p { margin: 0; }button { background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; min-height: var(--control-height-lg); padding: 0 var(--space-3); }.content-grid { display: grid; gap: var(--space-5); grid-template-columns: repeat(2, minmax(0, 1fr)); }.result-card header { align-items: baseline; display: flex; justify-content: space-between; }.result-card header a { color: var(--color-accent); }.result-card ol, .result-card ul { align-content: start; display: grid; gap: var(--space-3); list-style: none; margin: 0; padding: 0; }.result-card li { align-items: center; border-top: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-3); grid-template-columns: 2rem 1fr auto; padding-top: var(--space-3); }.result-card p { color: var(--color-text-muted); }.fixture-date { align-items: start; display: flex; flex-direction: column; gap: .15rem; }.fixture-date strong { color: var(--color-text); font-size: var(--font-size-sm); }.fixture-date span { color: var(--color-text-muted); font-size: var(--font-size-xs); }.league-links { display: flex; flex-wrap: wrap; gap: var(--space-3); }.league-links a { background: var(--color-accent); color: var(--color-accent-contrast); font-weight: var(--font-weight-semibold); padding: var(--space-3) var(--space-4); text-decoration: none; }@media (max-width: 720px) { .content-grid { grid-template-columns: 1fr 1fr; } }@media (max-width: 480px) { .content-grid { grid-template-columns: 1fr; } .league-links a { flex: 1 1 100%; text-align: center; } }
.fixture-teams { display: flex; flex-direction: column; gap: .15rem; }
.fixture-teams span + span { color: var(--color-text-muted); font-size: var(--font-size-sm); }
.content-grid > .result-card:nth-child(2) li { grid-template-columns: 8rem 1fr; }
.fixture-teams span + span { color: inherit; font-size: inherit; }
.fixture-date strong, .fixture-date span { white-space: nowrap; }
</style>
