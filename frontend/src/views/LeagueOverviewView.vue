<template>
  <main class="league-overview">
    <section v-if="loading" data-testid="league-loading" class="overview-skeleton" aria-busy="true">
      <header class="skeleton-heading" aria-hidden="true">
        <span class="skeleton-line skeleton-eyebrow"></span>
        <span class="skeleton-line skeleton-title"></span>
        <span class="skeleton-line skeleton-subtitle"></span>
      </header>
      <div class="skeleton-capabilities" aria-hidden="true">
        <span v-for="item in 4" :key="item" class="skeleton-capability"><i class="skeleton-line"></i></span>
      </div>
      <div class="skeleton-previews" aria-hidden="true">
        <article v-for="preview in 3" :key="preview" class="skeleton-preview">
          <span class="skeleton-line skeleton-preview-title"></span>
          <span v-for="row in preview === 1 ? 5 : 2" :key="row" class="skeleton-line skeleton-preview-row"></span>
        </article>
      </div>
    </section>

    <section v-else-if="error" data-testid="league-error" class="league-state" role="alert">
      <CircleAlert :size="24" aria-hidden="true" />
      <h1>{{ t('league.states.errorTitle') }}</h1>
      <p>{{ t('league.states.error') }}</p>
      <button type="button" @click="loadEdition">{{ t('league.states.retry') }}</button>
    </section>

    <template v-else-if="edition">
      <header class="league-heading">
        <p>{{ t('league.eyebrow') }}</p>
        <h1>{{ edition.display_name }}</h1>
        <span>{{ t('league.publicOverview') }}</span>
      </header>

      <nav class="league-capabilities" :aria-label="t('league.capabilityNavigation')">
        <router-link
          v-for="capability in edition.capabilities"
          :key="capability"
          :data-testid="`league-capability-${capability}`"
          :to="capabilityLocation(capability)"
        >
          <span>{{ t(`league.capabilities.${capability}`) }}</span>
          <ArrowUpRight :size="17" aria-hidden="true" />
        </router-link>
      </nav>

      <section class="league-previews" :aria-label="t('league.previews.label')">
        <article v-if="tablePreview" data-testid="league-table-preview" class="table-preview">
          <header>
            <h2>{{ t('league.previews.table.title') }}</h2>
            <small>{{ t('league.table.updated', { date: formatDate(tablePreview.source_updated_at) }) }}</small>
          </header>
          <ol>
            <li v-for="row in tablePreview.standings" :key="row.team.slug">
              <span>{{ row.position }}</span>
              <strong>{{ row.team.display_name }}</strong>
              <span>{{ row.points }} {{ t('league.table.pointsShort') }}</span>
            </li>
          </ol>
        </article>
        <article v-else data-testid="league-preview-empty-table">
          <h2>{{ t('league.previews.table.title') }}</h2>
          <p>{{ t('league.previews.table.empty') }}</p>
        </article>
        <article
          v-for="preview in otherPreviews"
          :key="preview.key"
          :data-testid="fixturePreview?.[preview.dataKey]?.length ? `league-${preview.key}-preview` : `league-preview-empty-${preview.key}`"
          class="fixture-preview"
        >
          <h2>{{ t(`league.previews.${preview.key}.title`) }}</h2>
          <ul v-if="fixturePreview?.[preview.dataKey]?.length">
            <li v-for="fixture in fixturePreview[preview.dataKey]" :key="fixture.id">
              <small>{{ formatDate(fixture.kickoff_at) }}</small>
              <span>
                <strong>{{ fixture.home_team.display_name }}</strong>
                <b v-if="preview.key === 'results'">{{ fixture.home_team.score }}-{{ fixture.away_team.score }}</b>
                <i v-else>{{ t('league.previews.fixtures.versus') }}</i>
                <strong>{{ fixture.away_team.display_name }}</strong>
              </span>
            </li>
          </ul>
          <p v-else>{{ t(`league.previews.${preview.key}.empty`) }}</p>
        </article>
      </section>
    </template>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ArrowUpRight, CircleAlert } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

import { api } from '../lib/api.js'
import { leagueWorkspaceLocation } from '../router/workspace.js'

const props = defineProps({
  locale: { type: String, required: true },
  competitionSlug: { type: String, required: true },
  editionSlug: { type: String, default: '' },
})
const { t } = useI18n()
const edition = ref(null)
const error = ref(false)
const loading = ref(true)
const tablePreview = ref(null)
const fixturePreview = ref(null)
const otherPreviews = [
  { key: 'fixtures', dataKey: 'upcoming' },
  { key: 'results', dataKey: 'results' },
]

async function loadEdition() {
  loading.value = true
  error.value = false
  try {
    const suffix = props.editionSlug ? `/editions/${props.editionSlug}` : ''
    const response = await api.get(`/api/competitions/${props.competitionSlug}${suffix}`)
    edition.value = response.data.edition
    try {
      const preview = await api.get(
        `/api/competitions/${props.competitionSlug}/editions/${edition.value.slug}/table/preview`
      )
      tablePreview.value = Array.isArray(preview.data?.standings)
        && !Number.isNaN(Date.parse(preview.data?.source_updated_at))
        ? preview.data
        : null
    } catch {
      tablePreview.value = null
    }
    try {
      const preview = await api.get(
        `/api/competitions/${props.competitionSlug}/editions/${edition.value.slug}/fixtures/preview`
      )
      fixturePreview.value = preview.data
    } catch {
      fixturePreview.value = null
    }
  } catch {
    edition.value = null
    error.value = true
  } finally {
    loading.value = false
  }
}

function formatDate(value) {
  return new Intl.DateTimeFormat(props.locale, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function capabilityLocation(capability) {
  return leagueWorkspaceLocation(capability === 'predictions' ? 'predict' : capability, {
    locale: props.locale,
    competitionSlug: props.competitionSlug,
    editionSlug: edition.value.slug,
  })
}

onMounted(loadEdition)
</script>

<style scoped>
.league-overview { display: flex; flex-direction: column; gap: var(--space-10); padding: var(--space-8) 0; }
.league-heading { border-bottom: var(--border-width-thin) solid var(--color-border); padding-bottom: var(--space-8); }
.league-heading p { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); margin: 0 0 var(--space-3); text-transform: uppercase; }
.league-heading h1 { font-family: var(--font-family-display); font-size: var(--font-size-4xl); letter-spacing: 0; margin: 0 0 var(--space-4); }
.league-heading span { color: var(--color-text-muted); }
.league-capabilities { border-bottom: var(--border-width-thin) solid var(--color-border); border-top: var(--border-width-thin) solid var(--color-border); display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.league-capabilities a { align-items: center; color: var(--color-text); display: flex; font-weight: var(--font-weight-semibold); justify-content: space-between; min-height: 4.5rem; padding: 0 var(--space-4); text-decoration: none; }
.league-capabilities a + a { border-left: var(--border-width-thin) solid var(--color-border); }
.league-capabilities a:hover { background: var(--color-surface-inset); color: var(--color-accent); }
.league-previews { display: grid; gap: var(--space-6); grid-template-columns: repeat(3, minmax(0, 1fr)); }
.league-previews article { border-top: var(--border-width-strong) solid var(--color-text); padding-top: var(--space-4); }
.league-previews h2 { font-family: var(--font-family-display); font-size: var(--font-size-lg); margin: 0 0 var(--space-3); }
.league-previews p { color: var(--color-text-muted); margin: 0; }
.table-preview header { align-items: baseline; display: flex; justify-content: space-between; }
.table-preview small { color: var(--color-text-muted); }
.table-preview ol { list-style: none; margin: 0; padding: 0; }
.table-preview li { align-items: center; border-top: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-3); grid-template-columns: 2rem 1fr auto; min-height: 2.75rem; }
.fixture-preview ul { list-style: none; margin: 0; padding: 0; }
.fixture-preview li { border-top: var(--border-width-thin) solid var(--color-border); padding: var(--space-3) 0; }
.fixture-preview li small { color: var(--color-text-muted); display: block; margin-bottom: var(--space-2); }
.fixture-preview li span { align-items: center; display: grid; gap: var(--space-2); grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); }
.fixture-preview li strong:last-child { text-align: right; }
.fixture-preview li b { font-family: var(--font-family-data); }
.fixture-preview li i { color: var(--color-text-muted); font-style: normal; }
.league-state { align-items: flex-start; display: flex; flex-direction: column; gap: var(--space-3); min-height: 20rem; justify-content: center; }
.league-state h1, .league-state p { margin: 0; }
.league-state button { background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; min-height: var(--control-height-lg); padding: 0 var(--space-4); }
.overview-skeleton { display: flex; flex-direction: column; gap: var(--space-10); padding: var(--space-8) 0; }
.skeleton-line { animation: skeleton-pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); display: block; }
.skeleton-heading { border-bottom: var(--border-width-thin) solid var(--color-border); display: flex; flex-direction: column; gap: var(--space-3); padding-bottom: var(--space-8); }
.skeleton-eyebrow { height: .75rem; width: 8rem; }
.skeleton-title { height: 3rem; max-width: 28rem; width: 58%; }
.skeleton-subtitle { height: 1rem; width: 11rem; }
.skeleton-capabilities { border-bottom: var(--border-width-thin) solid var(--color-border); border-top: var(--border-width-thin) solid var(--color-border); display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.skeleton-capability { align-items: center; display: flex; min-height: 4.5rem; padding: 0 var(--space-4); }
.skeleton-capability + .skeleton-capability { border-left: var(--border-width-thin) solid var(--color-border); }
.skeleton-capability .skeleton-line { height: 1rem; width: 54%; }
.skeleton-previews { display: grid; gap: var(--space-6); grid-template-columns: repeat(3, minmax(0, 1fr)); }
.skeleton-preview { border-top: var(--border-width-strong) solid var(--color-border); display: flex; flex-direction: column; gap: var(--space-3); padding-top: var(--space-4); }
.skeleton-preview-title { height: 1.25rem; margin-bottom: var(--space-2); width: 48%; }
.skeleton-preview-row { height: 1rem; width: 88%; }
.skeleton-preview-row:nth-child(3n) { width: 68%; }
@keyframes skeleton-pulse { 50% { opacity: .45; } }
@media (max-width: 720px) { .league-capabilities, .league-previews, .skeleton-capabilities, .skeleton-previews { grid-template-columns: 1fr; } .league-capabilities a + a, .skeleton-capability + .skeleton-capability { border-left: 0; border-top: var(--border-width-thin) solid var(--color-border); } .league-heading h1 { font-size: var(--font-size-3xl); } .skeleton-title { width: 82%; } }
@media (prefers-reduced-motion: reduce) { .skeleton-line { animation: none; } }
</style>
