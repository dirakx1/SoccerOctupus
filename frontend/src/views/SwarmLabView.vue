<template>
  <main class="atlas-swarm-page">
    <AtlasPageHeader
      :eyebrow="t('swarmLab.page.eyebrow', { competition: t(edition.displayNameKey) })"
      :title="t('swarmLab.page.title')"
      :description="t('swarmLab.page.description')"
    />

    <div
      class="swarm-tabs"
      role="tablist"
      :aria-label="t('swarmLab.tabs.label')"
      @keydown="onTabKeydown"
    >
      <button
        id="swarm-tab-weights"
        ref="weightsTab"
        type="button"
        role="tab"
        :aria-selected="activeTab === 'weights'"
        aria-controls="swarm-panel-weights"
        :tabindex="activeTab === 'weights' ? 0 : -1"
        @click="selectTab('weights')"
      >
        <SlidersHorizontal :size="16" aria-hidden="true" />
        <span>{{ t('swarmLab.tabs.weights') }}</span>
      </button>
      <button
        id="swarm-tab-graph"
        ref="graphTab"
        type="button"
        role="tab"
        :aria-selected="activeTab === 'graph'"
        aria-controls="swarm-panel-graph"
        :tabindex="activeTab === 'graph' ? 0 : -1"
        @click="selectTab('graph')"
      >
        <Network :size="16" aria-hidden="true" />
        <span>{{ t('swarmLab.tabs.graph') }}</span>
      </button>
    </div>

    <section
      v-show="activeTab === 'weights'"
      id="swarm-panel-weights"
      role="tabpanel"
      aria-labelledby="swarm-tab-weights"
      :tabindex="activeTab === 'weights' ? 0 : -1"
      class="swarm-panel"
    >
      <AgentWeightsPanel />
    </section>

    <section
      v-show="activeTab === 'graph'"
      id="swarm-panel-graph"
      role="tabpanel"
      aria-labelledby="swarm-tab-graph"
      :tabindex="activeTab === 'graph' ? 0 : -1"
      class="swarm-panel"
    >
      <KnowledgeGraphPanel />
    </section>
  </main>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { Network, SlidersHorizontal } from '@lucide/vue'

import AgentWeightsPanel from '../components/swarm/AgentWeightsPanel.vue'
import KnowledgeGraphPanel from '../components/swarm/KnowledgeGraphPanel.vue'
import { getCompetitionEdition, listCompetitionEditions } from '../competition/index.js'
import AtlasPageHeader from '../ui/patterns/AtlasPageHeader.vue'

const { t } = useI18n()
const route = useRoute()
const defaultEdition = listCompetitionEditions()[0]
const edition = computed(() => getCompetitionEdition(route.params.competitionEditionSlug) || defaultEdition)

const activeTab = ref('weights')
const weightsTab = ref(null)
const graphTab = ref(null)

function selectTab(tab, focus = false) {
  activeTab.value = tab
  if (focus) nextTick(() => (tab === 'weights' ? weightsTab.value : graphTab.value)?.focus())
}

function onTabKeydown(event) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  if (event.key === 'Home' || (event.key === 'ArrowLeft' && activeTab.value === 'graph')) selectTab('weights', true)
  else if (event.key === 'End' || (event.key === 'ArrowRight' && activeTab.value === 'weights')) selectTab('graph', true)
  else selectTab(activeTab.value === 'weights' ? 'graph' : 'weights', true)
}
</script>

<style scoped>
.atlas-swarm-page { display: flex; flex-direction: column; gap: var(--space-6); min-width: 0; }
.swarm-tabs { align-items: center; border-bottom: var(--border-width-thin) solid var(--color-border); display: flex; min-height: var(--control-height-lg); }
.swarm-tabs button { align-items: center; align-self: stretch; background: transparent; border: 0; border-bottom: var(--border-width-strong) solid transparent; color: var(--color-text-muted); cursor: pointer; display: inline-flex; font-weight: var(--font-weight-semibold); gap: var(--space-2); min-height: var(--control-height-lg); padding: 0 var(--space-5); }
.swarm-tabs button[aria-selected="true"] { border-bottom-color: var(--color-accent); color: var(--color-text); }
.swarm-tabs button:hover { color: var(--color-text); }
.swarm-tabs button:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.swarm-panel { min-width: 0; }
@media (max-width: 480px) {
  .swarm-tabs button { flex: 1 1 50%; justify-content: center; padding: 0 var(--space-3); }
}
</style>
