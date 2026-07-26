<template>
  <main class="league-overview">
    <section v-if="loading" data-testid="league-loading" class="league-state" aria-live="polite">
      <LoaderCircle :size="24" class="spin" aria-hidden="true" />
      <p>{{ t('league.states.loading') }}</p>
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
        <article v-for="preview in otherPreviews" :key="preview" :data-testid="`league-preview-empty-${preview}`">
          <h2>{{ t(`league.previews.${preview}.title`) }}</h2>
          <p>{{ t(`league.previews.${preview}.empty`) }}</p>
        </article>
      </section>
    </template>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ArrowUpRight, CircleAlert, LoaderCircle } from '@lucide/vue'
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
const otherPreviews = ['fixtures', 'results']

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
.league-state { align-items: flex-start; display: flex; flex-direction: column; gap: var(--space-3); min-height: 20rem; justify-content: center; }
.league-state h1, .league-state p { margin: 0; }
.league-state button { background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; min-height: var(--control-height-lg); padding: 0 var(--space-4); }
@media (max-width: 720px) { .league-capabilities, .league-previews { grid-template-columns: 1fr; } .league-capabilities a + a { border-left: 0; border-top: var(--border-width-thin) solid var(--color-border); } .league-heading h1 { font-size: var(--font-size-3xl); } }
</style>
