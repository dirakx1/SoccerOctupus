<template>
  <main class="atlas-home">
    <section class="home-hero" aria-labelledby="home-title">
      <div class="home-hero-copy">
        <p class="home-eyebrow">{{ t('home.eyebrow') }}</p>
        <h1 id="home-title">{{ t('home.title') }}</h1>
        <p class="home-intro">{{ t('home.intro') }}</p>
        <div class="home-scope" :aria-label="t('home.scopeLabel')">
          <span>{{ t(edition.displayNameKey) }}</span>
          <span>{{ t('home.host') }}</span>
        </div>
      </div>
      <div class="home-edition-mark" aria-hidden="true">26</div>
    </section>

    <nav class="workflow-grid" :aria-label="t('home.actionsLabel')">
      <router-link
        v-for="action in actions"
        :key="action.key"
        :data-testid="`workflow-${action.key}`"
        :to="action.route"
        class="workflow-card"
        :class="`workflow-card-${action.key}`"
      >
        <span>{{ t(action.eyebrowKey) }}</span>
        <strong>{{ t(action.titleKey) }}</strong>
        <small>{{ t(action.descriptionKey) }}</small>
        <ArrowUpRight :size="18" aria-hidden="true" />
      </router-link>
    </nav>

    <section class="swarm-section" aria-labelledby="swarm-title">
      <header class="swarm-heading">
        <div>
          <p class="home-eyebrow">{{ t('home.swarm.eyebrow') }}</p>
          <h2 id="swarm-title">{{ t('home.swarm.title') }}</h2>
        </div>
        <p>{{ t('home.swarm.description') }}</p>
      </header>

      <div class="agent-list">
        <article v-for="(agent, index) in agents" :key="agent.key" class="agent-row">
          <span class="agent-index" aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}</span>
          <div class="agent-copy">
            <div class="agent-title-line">
              <h3>{{ t(agent.nameKey) }}</h3>
              <span v-if="agent.weightKey" class="agent-weight">{{ t(agent.weightKey) }}</span>
            </div>
            <p>{{ t(agent.descriptionKey) }}</p>
            <button
              v-if="agent.modal"
              class="agent-action"
              type="button"
              :aria-label="t('home.swarm.videoAction')"
              @click="openModal(agent.modal)"
            >
              <Video :size="15" aria-hidden="true" />
              <span>{{ t('home.swarm.videoAction') }}</span>
              <ArrowUpRight :size="14" aria-hidden="true" />
            </button>
          </div>
        </article>
      </div>
    </section>

    <VideoAgentModal v-if="activeModal === 'video'" @close="activeModal = null" />
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { ArrowUpRight, Video } from '@lucide/vue'

import VideoAgentModal from '../components/VideoAgentModal.vue'
import { getCompetitionEdition, listCompetitionEditions } from '../competition/index.js'
import { workspaceLocation } from '../router/workspace.js'

const { t } = useI18n()
const route = useRoute()
const activeModal = ref(null)
const defaultEdition = listCompetitionEditions()[0]

const edition = computed(() => (
  getCompetitionEdition(route.params.competitionEditionSlug) || defaultEdition
))
const locale = computed(() => route.params.locale || 'en')
const historic = computed(() => Boolean(route.meta.historicWorkspace))
const actions = computed(() => [
  {
    key: 'groups',
    eyebrowKey: 'home.actions.groups.eyebrow',
    titleKey: 'home.actions.groups.title',
    descriptionKey: 'home.actions.groups.description',
    route: workspaceLocation('groups', { locale: locale.value, competitionEditionSlug: edition.value.slug, historic: historic.value }),
  },
  {
    key: 'predict',
    eyebrowKey: 'home.actions.predict.eyebrow',
    titleKey: 'home.actions.predict.title',
    descriptionKey: 'home.actions.predict.description',
    route: workspaceLocation('predict', { locale: locale.value, competitionEditionSlug: edition.value.slug, historic: historic.value }),
  },
  {
    key: 'bracket',
    eyebrowKey: 'home.actions.bracket.eyebrow',
    titleKey: 'home.actions.bracket.title',
    descriptionKey: 'home.actions.bracket.description',
    route: workspaceLocation('bracket', { locale: locale.value, competitionEditionSlug: edition.value.slug, historic: historic.value }),
  },
  {
    key: 'markets',
    eyebrowKey: 'home.actions.markets.eyebrow',
    titleKey: 'home.actions.markets.title',
    descriptionKey: 'home.actions.markets.description',
    route: workspaceLocation('markets', { locale: locale.value, competitionEditionSlug: edition.value.slug, historic: historic.value }),
  },
])

const agents = [
  { key: 'statistical', nameKey: 'home.agents.statistical.name', descriptionKey: 'home.agents.statistical.description', weightKey: 'home.agents.statistical.weight' },
  { key: 'video', nameKey: 'home.agents.video.name', descriptionKey: 'home.agents.video.description', weightKey: 'home.agents.video.weight', modal: 'video' },
  { key: 'form', nameKey: 'home.agents.form.name', descriptionKey: 'home.agents.form.description', weightKey: 'home.agents.form.weight' },
  { key: 'tactical', nameKey: 'home.agents.tactical.name', descriptionKey: 'home.agents.tactical.description', weightKey: 'home.agents.tactical.weight' },
  { key: 'aggregator', nameKey: 'home.agents.aggregator.name', descriptionKey: 'home.agents.aggregator.description' },
]

function openModal(name) {
  activeModal.value = name
}
</script>

<style scoped>
.atlas-home { display: flex; flex-direction: column; gap: var(--space-12); }

.home-hero {
  align-items: center;
  border-bottom: var(--border-width-thin) solid var(--color-border);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(12rem, 0.7fr);
  min-height: 20rem;
  overflow: hidden;
  padding: var(--space-8) 0 var(--space-10);
  position: relative;
}

.home-hero-copy { position: relative; z-index: 1; }

.home-eyebrow {
  color: var(--color-accent);
  font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data);
  margin: 0 0 var(--space-4);
  text-transform: uppercase;
}

.home-hero h1 {
  font-family: var(--font-family-display);
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-heavy);
  line-height: var(--line-height-tight);
  margin: 0;
  max-width: 12ch;
}

.home-intro {
  color: var(--color-text-muted);
  font-size: var(--font-size-md);
  line-height: var(--line-height-relaxed);
  margin: var(--space-5) 0 0;
  max-width: 58ch;
}

.home-scope {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-5);
  margin-top: var(--space-6);
}

.home-scope span {
  border-left: var(--border-width-strong) solid var(--color-accent);
  color: var(--color-text);
  font: var(--font-weight-semibold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data);
  padding-left: var(--space-2);
}

.home-scope span + span { color: var(--color-text-muted); }

.home-edition-mark {
  color: var(--color-surface-inset);
  font-family: var(--font-family-display);
  font-size: 15rem;
  font-weight: var(--font-weight-heavy);
  line-height: 0.7;
  justify-self: end;
  user-select: none;
}

.workflow-grid {
  display: grid;
  gap: var(--space-2);
  grid-template-columns: 1.15fr 0.85fr 0.85fr;
  grid-template-rows: repeat(2, minmax(7rem, auto));
}

.workflow-card {
  align-content: start;
  background: var(--color-surface);
  border: var(--border-width-thin) solid var(--color-border);
  color: var(--color-text);
  display: grid;
  gap: var(--space-2);
  min-width: 0;
  padding: var(--space-5);
  position: relative;
  text-decoration: none;
  transition: background-color var(--duration-normal) var(--easing-standard), border-color var(--duration-normal) var(--easing-standard), transform var(--duration-normal) var(--easing-standard);
}

.workflow-card-groups { grid-row: 1 / span 2; }
.workflow-card:nth-child(2) { grid-column: 2; grid-row: 1; }
.workflow-card:nth-child(3) { grid-column: 3; grid-row: 1; }
.workflow-card:nth-child(4) { grid-column: 2 / span 2; grid-row: 2; }

.workflow-card:hover {
  background: var(--color-surface-raised);
  border-color: var(--color-accent);
  transform: translateY(-2px);
}

.workflow-card:focus-visible,
.agent-action:focus-visible {
  outline: var(--border-width-strong) solid var(--color-focus);
  outline-offset: 3px;
}

.workflow-card > span {
  color: var(--color-accent);
  font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data);
  text-transform: uppercase;
}

.workflow-card strong {
  font-family: var(--font-family-display);
  font-size: var(--font-size-xl);
  line-height: var(--line-height-tight);
}

.workflow-card small { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-normal); }
.workflow-card svg { color: var(--color-accent); position: absolute; right: var(--space-5); top: var(--space-5); }

.swarm-section { border-top: var(--border-width-thin) solid var(--color-border); padding-top: var(--space-8); }

.swarm-heading {
  align-items: end;
  display: grid;
  gap: var(--space-8);
  grid-template-columns: minmax(14rem, 0.8fr) minmax(0, 1.2fr);
  margin-bottom: var(--space-6);
}

.swarm-heading h2 {
  font-family: var(--font-family-display);
  font-size: var(--font-size-2xl);
  line-height: var(--line-height-tight);
  margin: 0;
}

.swarm-heading > p { color: var(--color-text-muted); line-height: var(--line-height-relaxed); margin: 0; max-width: 48ch; }

.agent-list { border-top: var(--border-width-thin) solid var(--color-border); }

.agent-row {
  border-bottom: var(--border-width-thin) solid var(--color-border);
  display: grid;
  gap: var(--space-4);
  grid-template-columns: 2rem minmax(0, 1fr);
  padding: var(--space-5) 0;
}

.agent-index { color: var(--color-text-subtle); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); padding-top: 0.15rem; }
.agent-copy { max-width: 65rem; }
.agent-title-line { align-items: baseline; display: flex; flex-wrap: wrap; gap: var(--space-3); }
.agent-title-line h3 { font-family: var(--font-family-display); font-size: var(--font-size-lg); margin: 0; }
.agent-weight { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); }
.agent-copy p { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-relaxed); margin: var(--space-2) 0 0; }

.agent-action {
  align-items: center;
  background: transparent;
  border: 0;
  color: var(--color-accent);
  cursor: pointer;
  display: inline-flex;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  gap: var(--space-2);
  margin-top: var(--space-3);
  padding: 0;
}

.agent-action:hover { color: var(--color-accent-hover); }

@media (max-width: 760px) {
  .home-hero { grid-template-columns: minmax(0, 1fr) 7rem; min-height: 0; }
  .home-edition-mark { font-size: 9rem; }
  .workflow-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); grid-template-rows: none; }
  .workflow-card-groups,
  .workflow-card:nth-child(2),
  .workflow-card:nth-child(3),
  .workflow-card:nth-child(4) { grid-column: auto; grid-row: auto; }
}

@media (max-width: 560px) {
  .atlas-home { gap: var(--space-8); }
  .home-hero { display: block; padding-top: var(--space-4); }
  .home-hero h1 { font-size: var(--font-size-3xl); }
  .home-edition-mark { display: none; }
  .workflow-grid { grid-template-columns: 1fr; }
  .swarm-heading { display: block; }
  .swarm-heading > p { margin-top: var(--space-4); }
}
</style>
