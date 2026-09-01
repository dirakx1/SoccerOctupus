<template>
  <main class="league-view league-overview">
    <section class="league-hero" aria-labelledby="league-overview-title">
      <div class="league-hero-copy">
        <p class="league-eyebrow">{{ t('competitions.league.overviewHero.eyebrow', { competition: editionName }) }}</p>
        <h1 id="league-overview-title">{{ t(edition.displayNameKey) }}</h1>
        <p class="league-intro">{{ t('competitions.league.overviewHero.description') }}</p>
        <div class="league-scope" :aria-label="t('competitions.league.overviewHero.scopeLabel')">
          <span>{{ t('competitions.league.overviewHero.competition', { country: t(edition.countryKey), competition: editionName }) }}</span>
          <span>{{ t('competitions.league.overviewHero.format', { clubs: edition.clubCount, matchdays: edition.matchdayCount }) }}</span>
        </div>
      </div>
      <div class="league-edition-mark" aria-hidden="true">27</div>
    </section>

    <nav class="workflow-grid" :aria-label="t('competitions.league.overviewActions.label', { competition: editionName })">
      <router-link
        v-for="action in actions"
        :key="action.key"
        :to="action.route"
        class="workflow-card"
      >
        <span>{{ t(action.eyebrowKey) }}</span>
        <strong>{{ t(action.titleKey) }}</strong>
        <small>{{ t(action.descriptionKey) }}</small>
        <ArrowUpRight :size="18" aria-hidden="true" />
      </router-link>
    </nav>

    <section v-if="loading" class="state-panel" aria-busy="true">
      <p>{{ t('competitions.league.loading') }}</p>
    </section>
    <section v-else-if="error" class="state-panel state-error" role="alert">
      <p>{{ error }}</p>
      <button type="button" @click="loadOverview">{{ t('competitions.league.retry') }}</button>
    </section>
    <section v-else class="content-grid">
      <div class="result-card">
        <header>
          <h2>{{ t('competitions.league.currentTable') }}</h2>
          <router-link :to="link('table')">{{ t('competitions.league.viewTable') }}</router-link>
        </header>
        <ol>
          <li v-for="row in data.standings.slice(0, 8)" :key="row.teamId">
            <span>{{ row.position }}</span>
            <strong>{{ row.team.name }}</strong>
            <small>{{ row.points }} {{ t('competitions.league.points') }}</small>
          </li>
        </ol>
      </div>
      <div class="result-card">
        <header>
          <h2>{{ t('competitions.league.nextFixtures') }}</h2>
          <router-link :to="link('fixtures')">{{ t('competitions.league.viewAll') }}</router-link>
        </header>
        <ul v-if="nextFixtures.length">
          <li v-for="fixture in nextFixtures" :key="fixture.id">
            <time class="fixture-date" :datetime="fixture.kickoff">
              <strong>{{ formatDate(fixture.kickoff) }}</strong>
              <span>{{ formatTime(fixture.kickoff) }}</span>
            </time>
            <strong class="fixture-teams">
              <span>{{ fixture.homeTeam.name }}</span>
              <span>{{ fixture.awayTeam.name }}</span>
            </strong>
          </li>
        </ul>
        <p v-else>{{ t('competitions.league.noNextFixtures') }}</p>
      </div>
    </section>

    <section class="model-section" aria-labelledby="league-model-title">
      <header class="model-heading">
        <div>
          <p class="league-eyebrow">{{ t('competitions.league.overviewModel.eyebrow', { competition: editionName }) }}</p>
          <h2 id="league-model-title">{{ t('competitions.league.overviewModel.title') }}</h2>
        </div>
        <p>{{ t('competitions.league.overviewModel.description') }}</p>
      </header>
      <div class="signal-list">
        <article v-for="(signal, index) in modelSignals" :key="signal.key" class="signal-row">
          <span class="signal-index" aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}</span>
          <div class="signal-copy">
            <h3>{{ t(signal.nameKey) }}</h3>
            <p>{{ t(signal.descriptionKey) }}</p>
          </div>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { ArrowUpRight } from '@lucide/vue'

import { api } from '../lib/api'
import { getCompetitionEdition } from '../competition/index.js'
import { leagueApiBase } from '../competition/leagueApi.js'
import { workspaceLocation } from '../router/workspace.js'

const { locale, t } = useI18n()
const route = useRoute()
const loading = ref(true)
const error = ref('')
const data = ref({ teams: [], fixtures: [], standings: [], evidence: { completedMatches: 0 } })
const edition = computed(() => getCompetitionEdition(route.params.competitionEditionSlug))
const editionName = computed(() => t(edition.value.displayNameKey))
const nextFixtures = computed(() => data.value.fixtures
  .filter((fixture) => fixture.status === 'scheduled' && new Date(fixture.kickoff).getTime() > Date.now())
  .slice(0, 5))

const link = (area) => workspaceLocation(area, {
  locale: route.params.locale,
  competitionEditionSlug: route.params.competitionEditionSlug,
})

const actions = computed(() => [
  { key: 'table', eyebrowKey: 'competitions.league.overviewActions.table.eyebrow', titleKey: 'competitions.league.overviewActions.table.title', descriptionKey: 'competitions.league.overviewActions.table.description', route: link('table') },
  { key: 'fixtures', eyebrowKey: 'competitions.league.overviewActions.fixtures.eyebrow', titleKey: 'competitions.league.overviewActions.fixtures.title', descriptionKey: 'competitions.league.overviewActions.fixtures.description', route: link('fixtures') },
  { key: 'predict', eyebrowKey: 'competitions.league.overviewActions.predict.eyebrow', titleKey: 'competitions.league.overviewActions.predict.title', descriptionKey: 'competitions.league.overviewActions.predict.description', route: link('predict') },
  { key: 'markets', eyebrowKey: 'competitions.league.overviewActions.markets.eyebrow', titleKey: 'competitions.league.overviewActions.markets.title', descriptionKey: 'competitions.league.overviewActions.markets.description', route: link('markets') },
])

const modelSignals = [
  { key: 'form', nameKey: 'competitions.league.overviewModel.signals.form.name', descriptionKey: 'competitions.league.overviewModel.signals.form.description' },
  { key: 'context', nameKey: 'competitions.league.overviewModel.signals.context.name', descriptionKey: 'competitions.league.overviewModel.signals.context.description' },
  { key: 'score', nameKey: 'competitions.league.overviewModel.signals.score.name', descriptionKey: 'competitions.league.overviewModel.signals.score.description' },
  { key: 'evidence', nameKey: 'competitions.league.overviewModel.signals.evidence.name', descriptionKey: 'competitions.league.overviewModel.signals.evidence.description' },
  { key: 'season', nameKey: 'competitions.league.overviewModel.signals.season.name', descriptionKey: 'competitions.league.overviewModel.signals.season.description' },
]

async function loadOverview() {
  loading.value = true
  error.value = ''
  try {
    data.value = (await api.get(leagueApiBase(route.params.competitionEditionSlug))).data
  } catch (cause) {
    error.value = cause.response?.data?.error || t('competitions.league.loadFailed')
  } finally {
    loading.value = false
  }
}

function formatDate(value) {
  return new Intl.DateTimeFormat(locale.value, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value))
}

function formatTime(value) {
  return new Intl.DateTimeFormat(locale.value, { timeStyle: 'short' }).format(new Date(value))
}

watch(() => route.params.competitionEditionSlug, loadOverview, { immediate: true })
</script>

<style scoped>
.league-view { display: flex; flex-direction: column; gap: var(--space-12); min-width: 0; }
.league-hero { align-items: center; border-bottom: var(--border-width-thin) solid var(--color-border); display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(12rem, .5fr); min-height: 20rem; overflow: hidden; padding: var(--space-8) 0 var(--space-10); }
.league-hero-copy { position: relative; z-index: 1; }
.league-eyebrow { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); margin: 0 0 var(--space-4); text-transform: uppercase; }
.league-hero h1 { font-family: var(--font-family-display); font-size: var(--font-size-4xl); font-weight: var(--font-weight-heavy); line-height: var(--line-height-tight); margin: 0; max-width: 18ch; }
.league-intro { color: var(--color-text-muted); font-size: var(--font-size-md); line-height: var(--line-height-relaxed); margin: var(--space-5) 0 0; max-width: 58ch; }
.league-scope { display: flex; flex-wrap: wrap; gap: var(--space-2) var(--space-5); margin-top: var(--space-6); }
.league-scope span { border-left: var(--border-width-strong) solid var(--color-accent); font: var(--font-weight-semibold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); padding-left: var(--space-2); }
.league-scope span + span { color: var(--color-text-muted); }
.league-edition-mark { color: var(--color-surface-inset); font-family: var(--font-family-display); font-size: 15rem; font-weight: var(--font-weight-heavy); justify-self: end; line-height: .7; user-select: none; }
.workflow-grid { display: grid; gap: var(--space-2); grid-template-columns: repeat(2, minmax(0, 1fr)); }
.workflow-card { align-content: start; background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); color: var(--color-text); display: grid; gap: var(--space-2); min-height: 8.5rem; padding: var(--space-5); position: relative; text-decoration: none; transition: background-color var(--duration-normal) var(--easing-standard), border-color var(--duration-normal) var(--easing-standard), transform var(--duration-normal) var(--easing-standard); }
.workflow-card:hover { background: var(--color-surface-raised); border-color: var(--color-accent); transform: translateY(-2px); }
.workflow-card:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.workflow-card > span { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); text-transform: uppercase; }
.workflow-card strong { font-family: var(--font-family-display); font-size: var(--font-size-xl); line-height: var(--line-height-tight); }
.workflow-card small { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-normal); max-width: 42ch; }
.workflow-card svg { color: var(--color-accent); position: absolute; right: var(--space-5); top: var(--space-5); }
.state-panel, .result-card { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); padding: var(--space-5); }
.state-panel { align-items: center; display: flex; justify-content: space-between; }
.state-error { background: var(--color-danger-surface); color: var(--color-danger); }
.state-panel p { margin: 0; }
button { background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; min-height: var(--control-height-lg); padding: 0 var(--space-3); }
.content-grid { display: grid; gap: var(--space-5); grid-template-columns: repeat(2, minmax(0, 1fr)); }
.result-card { display: grid; gap: var(--space-3); }
.result-card h2 { font-family: var(--font-family-display); margin: 0; }
.result-card header { align-items: baseline; display: flex; justify-content: space-between; }
.result-card header a { color: var(--color-accent); }
.result-card ol, .result-card ul { align-content: start; display: grid; gap: var(--space-3); list-style: none; margin: 0; padding: 0; }
.result-card li { align-items: center; border-top: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-3); grid-template-columns: 2rem 1fr auto; padding-top: var(--space-3); }
.result-card p { color: var(--color-text-muted); }
.content-grid > .result-card:nth-child(2) li { grid-template-columns: 8rem minmax(0, 1fr); }
.fixture-date, .fixture-teams { align-items: start; display: flex; flex-direction: column; gap: .15rem; }
.fixture-date strong { color: var(--color-text); font-size: var(--font-size-sm); }
.fixture-date span { color: var(--color-text-muted); font-size: var(--font-size-xs); }
.fixture-date strong, .fixture-date span { white-space: nowrap; }
.model-section { border-top: var(--border-width-thin) solid var(--color-border); padding-top: var(--space-8); }
.model-heading { align-items: end; display: grid; gap: var(--space-8); grid-template-columns: minmax(14rem, .8fr) minmax(0, 1.2fr); margin-bottom: var(--space-6); }
.model-heading h2 { font-family: var(--font-family-display); font-size: var(--font-size-2xl); line-height: var(--line-height-tight); margin: 0; }
.model-heading > p { color: var(--color-text-muted); line-height: var(--line-height-relaxed); margin: 0; max-width: 48ch; }
.signal-list { border-top: var(--border-width-thin) solid var(--color-border); }
.signal-row { border-bottom: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-4); grid-template-columns: 2rem minmax(0, 1fr); padding: var(--space-5) 0; }
.signal-index { color: var(--color-text-subtle); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); padding-top: .15rem; }
.signal-copy { max-width: 65rem; }
.signal-copy h3 { font-family: var(--font-family-display); font-size: var(--font-size-lg); margin: 0; }
.signal-copy p { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-relaxed); margin: var(--space-2) 0 0; }
@media (max-width: 760px) { .league-hero { grid-template-columns: minmax(0, 1fr) 7rem; min-height: 0; }.league-edition-mark { font-size: 9rem; } }
@media (max-width: 560px) { .league-view { gap: var(--space-8); }.league-hero { display: block; padding-top: var(--space-4); }.league-hero h1 { font-size: var(--font-size-3xl); }.league-edition-mark { display: none; }.workflow-grid, .content-grid { grid-template-columns: 1fr; }.model-heading { display: block; }.model-heading > p { margin-top: var(--space-4); } }
</style>
