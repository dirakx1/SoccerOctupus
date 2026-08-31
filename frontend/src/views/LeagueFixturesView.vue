<template>
  <main class="atlas-fixtures-page">
    <AtlasPageHeader
      :eyebrow="t('competitions.league.fixturesEyebrow', { competition: t(edition.displayNameKey) })"
      :title="t('competitions.league.fixturesTitle')"
      :description="t('competitions.league.fixturesDescription')"
    >
      <template #actions>
        <div class="fixture-stat"><strong>{{ fixtures.length }}</strong><span>{{ t('competitions.league.fixtureCountLabel') }}</span></div>
        <div class="fixture-stat"><strong>{{ completedCount }}</strong><span>{{ t('competitions.league.resultCountLabel') }}</span></div>
      </template>
    </AtlasPageHeader>

    <section v-if="loading" class="fixture-groups fixture-skeleton" aria-busy="true">
      <article v-for="group in 3" :key="group" class="fixture-panel" aria-hidden="true">
        <header><span class="skeleton-line skeleton-fixture-heading" /><span class="skeleton-line skeleton-count" /></header>
        <ul><li v-for="row in 4" :key="row"><span class="skeleton-line" /><span class="skeleton-line" /><span class="skeleton-line" /></li></ul>
      </article>
    </section>

    <section v-else-if="error" class="fixture-state state-error" role="alert">
      <AlertTriangle :size="22" aria-hidden="true" />
      <div><h2>{{ t('competitions.league.fixturesErrorTitle') }}</h2><p>{{ error }}</p><button type="button" @click="loadFixtures"><RotateCcw :size="15" aria-hidden="true" />{{ t('competitions.league.retry') }}</button></div>
    </section>

    <template v-else>
      <section class="fixture-filters" :aria-label="t('competitions.league.fixtureFiltersLabel')">
        <label for="fixture-status">
          <span>{{ t('competitions.league.statusFilter') }}</span>
          <span class="select-field"><select id="fixture-status" v-model="statusFilter"><option value="scheduled">{{ t('competitions.league.upcomingFilter') }}</option><option value="completed">{{ t('competitions.league.resultsFilter') }}</option><option value="all">{{ t('competitions.league.allFilter') }}</option></select><ChevronDown :size="18" aria-hidden="true" /></span>
        </label>
        <label for="fixture-club">
          <span>{{ t('competitions.league.clubFilter') }}</span>
          <span class="select-field"><select id="fixture-club" v-model="clubFilter"><option value="">{{ t('competitions.league.allClubs') }}</option><option v-for="club in clubs" :key="club.id" :value="club.id">{{ club.name }}</option></select><ChevronDown :size="18" aria-hidden="true" /></span>
        </label>
      </section>

      <section v-if="!groups.length" class="fixture-state" aria-live="polite">
        <Inbox :size="22" aria-hidden="true" />
        <div><h2>{{ t('competitions.league.noFixturesTitle') }}</h2><p>{{ t('competitions.league.noFixtures') }}</p></div>
      </section>

      <section v-else class="fixture-groups" :aria-label="t('competitions.league.fixturesTitle')">
        <article v-for="group in groups" :key="group.label" class="fixture-panel">
          <header><div><span>{{ t('competitions.league.matchdayLabel') }}</span><h2>{{ group.label }}</h2></div><strong>{{ group.fixtures.length }}</strong></header>
          <ul>
            <li v-for="fixture in group.fixtures" :key="fixture.id">
              <time :datetime="fixture.kickoff"><strong>{{ formatDate(fixture.kickoff) }}</strong><span>{{ formatTime(fixture.kickoff) }}</span></time>
              <strong class="fixture-teams"><span>{{ fixture.homeTeam.name }}</span><span>{{ fixture.awayTeam.name }}</span></strong>
              <span class="fixture-status" :class="`status-${fixture.status}`">{{ status(fixture) }}</span>
            </li>
          </ul>
        </article>
        <button v-if="hasMore" class="show-more" type="button" @click="visibleLimit += pageSize">{{ t('competitions.league.showMore') }}</button>
      </section>
    </template>
  </main>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { AlertTriangle, ChevronDown, Inbox, RotateCcw } from '@lucide/vue'

import AtlasPageHeader from '../ui/patterns/AtlasPageHeader.vue'
import { getCompetitionEdition } from '../competition/index.js'
import { leagueApiBase } from '../competition/leagueApi.js'
import { api } from '../lib/api'

const { locale, t } = useI18n()
const route = useRoute()
const fixtures = ref([])
const loading = ref(true)
const error = ref('')
const statusFilter = ref('scheduled')
const clubFilter = ref('')
const visibleLimit = ref(30)
const pageSize = 30
const edition = computed(() => getCompetitionEdition(route.params.competitionEditionSlug))
const completedCount = computed(() => fixtures.value.filter((fixture) => fixture.status === 'completed').length)
const clubs = computed(() => {
  const known = new Map()
  for (const fixture of fixtures.value) for (const team of [fixture.homeTeam, fixture.awayTeam]) if (team?.id && !known.has(String(team.id))) known.set(String(team.id), { id: String(team.id), name: team.name })
  return [...known.values()].sort((a, b) => a.name.localeCompare(b.name, locale.value))
})
const filteredFixtures = computed(() => fixtures.value.filter((fixture) => (statusFilter.value === 'all' || fixture.status === statusFilter.value) && (!clubFilter.value || String(fixture.homeTeam?.id) === clubFilter.value || String(fixture.awayTeam?.id) === clubFilter.value)))
const visibleFixtures = computed(() => filteredFixtures.value.slice(0, visibleLimit.value))
const hasMore = computed(() => visibleFixtures.value.length < filteredFixtures.value.length)
const groups = computed(() => {
  const grouped = new Map()
  for (const fixture of visibleFixtures.value) {
    const label = fixture.matchweek != null ? t('competitions.league.matchweek', { week: fixture.matchweek }) : new Intl.DateTimeFormat(locale.value, { month: 'long', year: 'numeric' }).format(new Date(fixture.kickoff))
    if (!grouped.has(label)) grouped.set(label, [])
    grouped.get(label).push(fixture)
  }
  return [...grouped].map(([label, rows]) => ({ label, fixtures: rows }))
})

async function loadFixtures() {
  loading.value = true
  error.value = ''
  try {
    fixtures.value = (await api.get(`${leagueApiBase(route.params.competitionEditionSlug)}/fixtures`)).data.fixtures || []
  } catch (cause) {
    error.value = cause.response?.data?.error || t('competitions.league.loadFailed')
  } finally {
    loading.value = false
  }
}

function formatDate(value) { return new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium' }).format(new Date(value)) }
function formatTime(value) { return new Intl.DateTimeFormat(locale.value, { timeStyle: 'short' }).format(new Date(value)) }
function status(fixture) {
  if (fixture.homeScore != null) return `${fixture.homeScore}–${fixture.awayScore}`
  const key = { scheduled: 'statusScheduled', postponed: 'statusPostponed', cancelled: 'statusCancelled' }[fixture.status]
  return key ? t(`competitions.league.${key}`) : fixture.status
}

watch([statusFilter, clubFilter], () => { visibleLimit.value = pageSize })
watch(() => route.params.competitionEditionSlug, loadFixtures, { immediate: true })
</script>

<style scoped>
.atlas-fixtures-page { display: flex; flex-direction: column; gap: var(--space-6); min-width: 0; }
.fixture-stat { align-items: baseline; border-left: var(--border-width-thin) solid var(--color-border); display: flex; flex-direction: column; gap: var(--space-1); min-width: 5rem; padding-left: var(--space-3); }
.fixture-stat strong { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xl) / var(--line-height-tight) var(--font-family-data); }
.fixture-stat span { color: var(--color-text-muted); font-size: var(--font-size-xs); white-space: nowrap; }
.fixture-filters { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-4); grid-template-columns: repeat(2, minmax(0, 1fr)); padding: var(--space-5); }
.fixture-filters label { color: var(--color-text-muted); display: flex; flex-direction: column; font-size: var(--font-size-sm); gap: var(--space-2); }
.fixture-filters label > span:first-child { font-weight: var(--font-weight-semibold); }
.select-field { display: block; position: relative; }
.select-field select { appearance: none; background: var(--color-surface-raised); border: var(--border-width-thin) solid var(--color-border); border-radius: var(--radius-md); color: var(--color-text); font: var(--font-weight-medium) var(--font-size-sm) / var(--line-height-normal) var(--font-family-body); min-height: var(--control-height-lg); padding: 0 calc(var(--space-4) + 1.5rem) 0 var(--space-3); width: 100%; }
.select-field select:hover { border-color: var(--color-border-strong); }
.select-field select:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 2px; }
.select-field svg { color: var(--color-text-muted); pointer-events: none; position: absolute; right: var(--space-4); top: 50%; transform: translateY(-50%); }
.fixture-groups { display: grid; gap: var(--space-5); }
.fixture-panel { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); min-width: 0; }
.fixture-panel > header { align-items: center; border-bottom: var(--border-width-thin) solid var(--color-border); display: flex; justify-content: space-between; min-height: 4.5rem; padding: var(--space-4) var(--space-5); }
.fixture-panel > header div { display: grid; gap: var(--space-1); }
.fixture-panel > header span { color: var(--color-text-muted); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); text-transform: uppercase; }
.fixture-panel h2 { font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0; }
.fixture-panel > header > strong { color: var(--color-accent); font: var(--font-weight-heavy) var(--font-size-2xl) / var(--line-height-tight) var(--font-family-data); }
.fixture-panel ul { list-style: none; margin: 0; padding: 0 var(--space-5); }
.fixture-panel li { align-items: center; border-bottom: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-5); grid-template-columns: 9rem minmax(0, 1fr) auto; min-height: 5rem; padding: var(--space-3) 0; }
.fixture-panel li:last-child { border-bottom: 0; }
.fixture-panel time, .fixture-teams { align-items: flex-start; display: flex; flex-direction: column; gap: var(--space-1); }
.fixture-panel time strong { color: var(--color-text); font-size: var(--font-size-sm); }
.fixture-panel time span { color: var(--color-text-muted); font-size: var(--font-size-xs); }
.fixture-teams { font-family: var(--font-family-display); font-size: var(--font-size-md); }
.fixture-status { color: var(--color-text-muted); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); text-transform: uppercase; }
.status-completed { color: var(--color-accent); font-size: var(--font-size-md); }
.show-more { background: var(--color-accent); border: 0; border-radius: var(--radius-md); color: var(--color-accent-contrast); cursor: pointer; font-weight: var(--font-weight-bold); justify-self: center; min-height: var(--control-height-lg); padding: 0 var(--space-5); }
.show-more:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.fixture-state { align-items: flex-start; background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); color: var(--color-accent); display: flex; gap: var(--space-4); padding: var(--space-8); }
.fixture-state h2 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0; }
.fixture-state p { color: var(--color-text-muted); line-height: var(--line-height-relaxed); margin: var(--space-2) 0 0; }
.fixture-state button { align-items: center; background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; display: inline-flex; font-weight: var(--font-weight-semibold); gap: var(--space-2); min-height: var(--control-height-lg); margin-top: var(--space-4); padding: 0 var(--space-4); }
.state-error { background: var(--color-danger-surface); border-color: var(--color-danger); color: var(--color-danger); }
.state-error > svg { color: var(--color-danger); }
.fixture-skeleton .fixture-panel > header { gap: var(--space-3); }
.skeleton-line { animation: skeleton-pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); display: block; }
.skeleton-fixture-heading { height: 1.25rem; width: 20%; }
.skeleton-count { height: 1.5rem; width: 2rem; }
.fixture-skeleton li { grid-template-columns: 9rem minmax(0, 1fr) 5rem; }
.fixture-skeleton li span { height: 1rem; }
.fixture-skeleton li span:nth-child(2) { width: 72%; }
@keyframes skeleton-pulse { 50% { opacity: .45; } }
@media (max-width: 720px) { .fixture-filters { grid-template-columns: 1fr; }.fixture-panel li { align-items: start; grid-template-columns: 7rem minmax(0, 1fr) auto; }.fixture-panel ul { padding: 0 var(--space-4); } }
@media (max-width: 520px) { .fixture-panel li { grid-template-columns: minmax(0, 1fr) auto; }.fixture-panel time { grid-column: 1 / -1; }.fixture-state { padding: var(--space-5); }.fixture-skeleton li span:first-child { grid-column: 1 / -1; } }
@media (prefers-reduced-motion: reduce) { .skeleton-line { animation: none; } }
</style>
