<template>
  <main class="fixtures-view">
    <section v-if="loading" data-testid="fixtures-loading" class="fixtures-state" aria-busy="true">
      <LoaderCircle class="spin" :size="24" aria-hidden="true" />
      <p>{{ t('league.fixtures.loading') }}</p>
    </section>
    <section v-else-if="error" data-testid="fixtures-error" class="fixtures-state" role="alert">
      <CircleAlert :size="24" aria-hidden="true" />
      <h1>{{ t('league.fixtures.errorTitle') }}</h1>
      <p>{{ t('league.fixtures.error') }}</p>
      <button data-testid="fixtures-retry" type="button" @click="loadFixtures">{{ t('league.states.retry') }}</button>
    </section>
    <template v-else-if="data">
      <header class="fixtures-heading">
        <div>
          <p>{{ t('league.fixtures.eyebrow') }}</p>
          <h1>{{ t('league.fixtures.title', { edition: data.edition.display_name }) }}</h1>
        </div>
        <small v-if="latestUpdate" data-testid="fixtures-updated">
          {{ t('league.table.updated', { date: formatDate(latestUpdate) }) }}
        </small>
      </header>

      <section class="fixtures-controls" :aria-label="t('league.fixtures.filters')">
        <div class="mode-control">
          <button
            data-testid="fixtures-mode-upcoming"
            type="button"
            :aria-pressed="mode === 'upcoming'"
            @click="setQuery('mode', 'upcoming')"
          >{{ t('league.fixtures.upcoming') }}</button>
          <button
            data-testid="fixtures-mode-results"
            type="button"
            :aria-pressed="mode === 'results'"
            @click="setQuery('mode', 'results')"
          >{{ t('league.fixtures.results') }}</button>
        </div>
        <label>
          <span>{{ t('league.fixtures.matchweek') }}</span>
          <select data-testid="fixtures-matchweek" :value="selectedMatchweek" @change="setQuery('matchweek', $event.target.value)">
            <option value="">{{ t('league.fixtures.allMatchweeks') }}</option>
            <option v-for="matchweek in data.matchweeks" :key="matchweek" :value="matchweek">
              {{ t('league.fixtures.matchweekNumber', { number: matchweek }) }}
            </option>
          </select>
        </label>
        <label>
          <span>{{ t('league.fixtures.team') }}</span>
          <select data-testid="fixtures-team" :value="team" @change="setQuery('team', $event.target.value)">
            <option value="">{{ t('league.fixtures.allTeams') }}</option>
            <option v-for="entry in data.teams" :key="entry.slug" :value="entry.slug">{{ entry.display_name }}</option>
          </select>
        </label>
      </section>

      <section v-if="!data.fixtures.length" data-testid="fixtures-empty" class="fixtures-state">
        <CalendarX :size="24" aria-hidden="true" />
        <p>{{ t('league.fixtures.empty') }}</p>
      </section>
      <section v-else class="matchweek-list" :aria-label="t('league.fixtures.list')">
        <article v-for="fixture in data.fixtures" :key="fixture.id" :data-testid="`fixture-${fixture.id}`">
          <header>
            <span>{{ fixture.matchweek
              ? t('league.fixtures.matchweekNumber', { number: fixture.matchweek })
              : t('league.fixtures.matchweekPending') }}</span>
            <time :datetime="fixture.kickoff_at">{{ formatDate(fixture.kickoff_at) }}</time>
            <strong :class="`status status-${fixture.status}`">{{ t(`league.fixtures.status.${fixture.status}`) }}</strong>
          </header>
          <div class="fixture-team"><span>{{ fixture.home_team.display_name }}</span><b>{{ score(fixture.home_team.score) }}</b></div>
          <div class="fixture-team"><span>{{ fixture.away_team.display_name }}</span><b>{{ score(fixture.away_team.score) }}</b></div>
          <footer>{{ fixture.venue || t('league.fixtures.venuePending') }}</footer>
        </article>
      </section>
    </template>
  </main>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { CalendarX, CircleAlert, LoaderCircle } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

import { api } from '../lib/api.js'

const props = defineProps({
  competitionSlug: { type: String, required: true },
  editionSlug: { type: String, required: true },
})
const { locale, t } = useI18n()
const route = useRoute()
const router = useRouter()
const data = ref(null)
const loading = ref(true)
const error = ref(false)
const mode = computed(() => route.query.mode === 'results' ? 'results' : 'upcoming')
const selectedMatchweek = computed(() => route.query.matchweek || data.value?.selected_matchweek || '')
const team = computed(() => route.query.team || '')
const latestUpdate = computed(() => data.value?.fixtures
  .map((fixture) => fixture.source_updated_at)
  .filter(Boolean)
  .sort()
  .at(-1))

async function loadFixtures() {
  loading.value = true
  error.value = false
  const params = {}
  if (route.query.mode) params.mode = route.query.mode
  if (route.query.matchweek) params.matchweek = route.query.matchweek
  if (route.query.team) params.team = route.query.team
  try {
    const response = await api.get(
      `/api/competitions/${props.competitionSlug}/editions/${props.editionSlug}/fixtures`,
      { params },
    )
    data.value = response.data
    if (!route.query.matchweek && data.value.selected_matchweek) {
      await router.replace({
        query: { ...route.query, matchweek: String(data.value.selected_matchweek) },
      })
    }
  } catch {
    data.value = null
    error.value = true
  } finally {
    loading.value = false
  }
}

function setQuery(key, value) {
  const query = { ...route.query }
  if (key === 'mode' && value === 'upcoming') delete query[key]
  else if (value) query[key] = String(value)
  else delete query[key]
  return router.push({ query })
}

function formatDate(value) {
  return new Intl.DateTimeFormat(locale.value, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function score(value) { return value ?? '-' }

watch(() => route.query, loadFixtures, { immediate: true })
</script>

<style scoped>
.fixtures-view { display: flex; flex-direction: column; gap: var(--space-6); padding: var(--space-8) 0; }
.fixtures-heading { align-items: flex-end; border-bottom: var(--border-width-thin) solid var(--color-border); display: flex; justify-content: space-between; padding-bottom: var(--space-6); }
.fixtures-heading p { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / 1 var(--font-family-data); margin: 0; text-transform: uppercase; }
.fixtures-heading h1 { font-family: var(--font-family-display); font-size: var(--font-size-3xl); letter-spacing: 0; margin: var(--space-2) 0 0; }
.fixtures-heading small { color: var(--color-text-muted); }
.fixtures-controls { align-items: end; display: grid; gap: var(--space-4); grid-template-columns: auto minmax(9rem, 12rem) minmax(11rem, 16rem); }
.fixtures-controls label { color: var(--color-text-muted); display: flex; flex-direction: column; font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); gap: var(--space-2); text-transform: uppercase; }
.fixtures-controls select { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); color: var(--color-text); min-height: var(--control-height-md); padding: 0 var(--space-3); }
.mode-control { border: var(--border-width-thin) solid var(--color-border); display: flex; }
.mode-control button { background: transparent; border: 0; color: var(--color-text-muted); min-height: var(--control-height-md); padding: 0 var(--space-4); }
.mode-control button + button { border-left: var(--border-width-thin) solid var(--color-border); }
.mode-control button[aria-pressed="true"] { background: var(--color-text); color: var(--color-surface); }
.matchweek-list { display: grid; gap: var(--space-4); grid-template-columns: repeat(2, minmax(0, 1fr)); }
.matchweek-list article { border-top: var(--border-width-strong) solid var(--color-text); padding: var(--space-3) 0; }
.matchweek-list article header { align-items: center; color: var(--color-text-muted); display: grid; font-size: var(--font-size-xs); gap: var(--space-3); grid-template-columns: auto 1fr auto; margin-bottom: var(--space-4); }
.matchweek-list time { text-align: center; }
.status { color: var(--color-text); font-family: var(--font-family-data); text-transform: uppercase; }
.status-in_progress { color: var(--color-danger); }
.status-postponed, .status-suspended, .status-abandoned, .status-unknown { color: var(--color-warning); }
.fixture-team { align-items: center; border-top: var(--border-width-thin) solid var(--color-border); display: flex; font-size: var(--font-size-lg); justify-content: space-between; min-height: 3.25rem; }
.fixture-team b { font-family: var(--font-family-data); }
.matchweek-list footer { color: var(--color-text-muted); font-size: var(--font-size-sm); padding-top: var(--space-3); }
.fixtures-state { align-items: flex-start; display: flex; flex-direction: column; gap: var(--space-3); justify-content: center; min-height: 18rem; }
.fixtures-state h1, .fixtures-state p { margin: 0; }
.fixtures-state button { background: var(--color-accent); border: 0; color: var(--color-accent-contrast); min-height: var(--control-height-lg); padding: 0 var(--space-4); }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 720px) { .fixtures-heading { align-items: flex-start; flex-direction: column; gap: var(--space-3); } .fixtures-controls, .matchweek-list { grid-template-columns: 1fr; } .mode-control button { flex: 1; } }
@media (prefers-reduced-motion: reduce) { .spin { animation: none; } }
</style>
