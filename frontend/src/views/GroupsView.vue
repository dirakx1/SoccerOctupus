<template>
  <main class="atlas-groups-page">
    <AtlasPageHeader
      :eyebrow="t('groups.eyebrow', { competition: t(edition.displayNameKey) })"
      :title="t('groups.title')"
    >
      <template #actions>
        <div class="groups-count" aria-live="polite">
          <strong>{{ groupCount }}</strong>
          <span>{{ t('groups.groupCountLabel') }}</span>
        </div>
        <div class="groups-count">
          <strong>{{ teamCount }}</strong>
          <span>{{ t('groups.teamCountLabel') }}</span>
        </div>
      </template>
    </AtlasPageHeader>

    <p class="groups-description">
      {{ t('groups.description', { teamCount, groupCount, host: t('home.host') }) }}
    </p>

    <section v-if="loading" class="groups-grid" :aria-label="t('groups.loading')" aria-busy="true">
      <p class="sr-only">{{ t('groups.loadingDescription') }}</p>
      <article v-for="group in loadingGroups" :key="group" class="group-panel group-panel-skeleton">
        <div class="skeleton-line skeleton-group-heading"></div>
        <div v-for="row in 4" :key="row" class="skeleton-line skeleton-team-row"></div>
      </article>
    </section>

    <section v-else-if="error" class="groups-state groups-state-error" role="alert">
      <AlertTriangle :size="22" aria-hidden="true" />
      <div>
        <h2>{{ t('groups.error') }}</h2>
        <p>{{ t('groups.errorDescription') }}</p>
        <button type="button" @click="loadGroups">
          <RotateCcw :size="15" aria-hidden="true" />
          <span>{{ t('groups.retry') }}</span>
        </button>
      </div>
    </section>

    <section v-else-if="groupCount === 0" class="groups-state" aria-live="polite">
      <Inbox :size="22" aria-hidden="true" />
      <div>
        <h2>{{ t('groups.empty') }}</h2>
        <p>{{ t('groups.emptyDescription') }}</p>
      </div>
    </section>

    <section v-else class="groups-grid" :aria-label="t('groups.title')">
      <article v-for="group in groupEntries" :key="group.label" class="group-panel">
        <header class="group-panel-header">
          <div>
            <span class="group-kicker">{{ t('groups.groupLabel', { group: group.label }) }}</span>
            <strong>{{ group.teams.length }} {{ t('groups.teamCountLabel') }}</strong>
          </div>
          <span class="group-code" aria-hidden="true">{{ group.label }}</span>
        </header>
        <div class="table-wrap">
          <table>
            <caption class="sr-only">{{ t('groups.tableLabel', { group: group.label }) }}</caption>
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">{{ t('groups.teamLabel') }}</th>
                <th scope="col" class="numeric">{{ t('groups.eloLabel') }}</th>
                <th scope="col" class="numeric">{{ t('groups.rankLabel') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(team, index) in group.teams" :key="team.team">
                <td class="position">{{ index + 1 }}</td>
                <th scope="row">{{ team.team }}</th>
                <td class="numeric data-value">{{ team.elo }}</td>
                <td class="numeric data-value">#{{ team.rank }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { AlertTriangle, Inbox, RotateCcw } from '@lucide/vue'

import AtlasPageHeader from '../ui/patterns/AtlasPageHeader.vue'
import { getCompetitionEdition, listCompetitionEditions } from '../competition/index.js'
import { api } from '../lib/api'

const { t } = useI18n()
const route = useRoute()
const defaultEdition = listCompetitionEditions()[0]
const groups = ref({})
const loading = ref(true)
const error = ref(false)
const loadingGroups = ['A', 'B', 'C', 'D']

const edition = computed(() => (
  getCompetitionEdition(route.params.competitionEditionSlug) || defaultEdition
))
const groupEntries = computed(() => Object.entries(groups.value)
  .sort(([left], [right]) => left.localeCompare(right))
  .map(([label, teams]) => ({
    label,
    teams: [...(Array.isArray(teams) ? teams : [])].sort((left, right) => Number(right.elo) - Number(left.elo)),
  })))
const groupCount = computed(() => groupEntries.value.length)
const teamCount = computed(() => groupEntries.value.reduce((total, group) => total + group.teams.length, 0))

async function loadGroups() {
  loading.value = true
  error.value = false
  try {
    const response = await api.get('/api/predictions/groups')
    groups.value = response.data?.groups && typeof response.data.groups === 'object'
      ? response.data.groups
      : {}
  } catch {
    groups.value = {}
    error.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadGroups)
</script>

<style scoped>
.atlas-groups-page { display: flex; flex-direction: column; gap: var(--space-6); }

.groups-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-md);
  line-height: var(--line-height-relaxed);
  margin: 0;
}

.groups-count {
  align-items: baseline;
  border-left: var(--border-width-thin) solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 4.25rem;
  padding-left: var(--space-3);
}

.groups-count strong { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xl) / var(--line-height-tight) var(--font-family-data); }
.groups-count span { color: var(--color-text-muted); font-size: var(--font-size-xs); }

.groups-grid { display: grid; gap: var(--space-4); grid-template-columns: repeat(3, minmax(0, 1fr)); }

.group-panel {
  background: var(--color-surface);
  border: var(--border-width-thin) solid var(--color-border);
  min-width: 0;
}

.group-panel-header {
  align-items: start;
  border-bottom: var(--border-width-thin) solid var(--color-border);
  display: flex;
  justify-content: space-between;
  min-height: 4.5rem;
  padding: var(--space-4) var(--space-5);
}

.group-panel-header > div { display: flex; flex-direction: column; gap: var(--space-2); }
.group-kicker { color: var(--color-text-muted); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); text-transform: uppercase; }
.group-panel-header strong { font-family: var(--font-family-display); font-size: var(--font-size-md); }
.group-code { color: var(--color-accent); font: var(--font-weight-heavy) var(--font-size-2xl) / var(--line-height-tight) var(--font-family-data); }

.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; min-width: 18rem; width: 100%; }
th, td { border-bottom: var(--border-width-thin) solid var(--color-border); font-size: var(--font-size-sm); min-height: 2.5rem; padding: var(--space-3) var(--space-4); text-align: left; }
thead th { color: var(--color-text-muted); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); text-transform: uppercase; }
tbody tr:last-child th, tbody tr:last-child td { border-bottom: 0; }
tbody th { font-weight: var(--font-weight-semibold); }
.numeric { text-align: right; }
.position { color: var(--color-text-subtle); font-family: var(--font-family-data); width: 2rem; }
.data-value { color: var(--color-text-muted); font-family: var(--font-family-data); font-size: var(--font-size-xs); }

.groups-state {
  align-items: flex-start;
  background: var(--color-surface);
  border: var(--border-width-thin) solid var(--color-border);
  color: var(--color-accent);
  display: flex;
  gap: var(--space-4);
  padding: var(--space-8);
}

.groups-state h2 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0; }
.groups-state p { color: var(--color-text-muted); line-height: var(--line-height-relaxed); margin: var(--space-2) 0 0; max-width: 48ch; }
.groups-state button { align-items: center; background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; display: inline-flex; font-weight: var(--font-weight-semibold); gap: var(--space-2); min-height: var(--control-height-md); margin-top: var(--space-4); padding: 0 var(--space-4); }
.groups-state button:hover { background: var(--color-accent-hover); }
.groups-state button:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }

.group-panel-skeleton { min-height: 16rem; padding: var(--space-5); }
.skeleton-line { animation: skeleton-pulse 1.4s ease-in-out infinite; background: var(--color-surface-inset); }
.skeleton-group-heading { height: 1rem; margin-bottom: var(--space-6); width: 46%; }
.skeleton-team-row { height: 2.35rem; margin-top: var(--space-2); width: 100%; }

.sr-only { border: 0; clip: rect(0 0 0 0); height: 1px; margin: -1px; overflow: hidden; padding: 0; position: absolute; white-space: nowrap; width: 1px; }

@keyframes skeleton-pulse { 50% { opacity: 0.45; } }

@media (max-width: 980px) { .groups-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 620px) {
  .groups-grid { grid-template-columns: 1fr; }
  .groups-state { padding: var(--space-5); }
}
@media (prefers-reduced-motion: reduce) { .skeleton-line { animation: none; } }
</style>
