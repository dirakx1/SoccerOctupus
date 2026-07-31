<template>
  <div class="weights-panel">
    <div v-if="loadError" class="state-panel state-error" role="alert">
      <AlertTriangle :size="22" aria-hidden="true" />
      <div>
        <h2>{{ t('swarmLab.weights.errorLoad') }}</h2>
        <button type="button" @click="load">
          <RotateCcw :size="15" aria-hidden="true" />
          <span>{{ t('swarmLab.weights.retry') }}</span>
        </button>
      </div>
    </div>

    <template v-else>
      <header class="weights-header">
        <div>
          <h2>{{ t('swarmLab.weights.heading') }}</h2>
          <p>{{ t('swarmLab.weights.description') }}</p>
        </div>
        <span
          class="config-badge"
          :class="isCustomized ? 'badge-customized' : 'badge-default'"
        >
          {{ isCustomized ? t('swarmLab.weights.customizedBadge') : t('swarmLab.weights.defaultBadge') }}
        </span>
      </header>

      <div v-if="saveError" class="save-error" role="alert">{{ t('swarmLab.weights.errorSave') }}</div>
      <div v-else-if="savedNotice" class="save-notice" role="status">{{ t('swarmLab.weights.savedNotice') }}</div>
      <div v-else-if="resetNotice" class="save-notice" role="status">{{ t('swarmLab.weights.resetNotice') }}</div>
      <div v-else-if="isDirty" class="unsaved-notice" role="status">
        <AlertCircle :size="14" aria-hidden="true" />
        {{ t('swarmLab.weights.unsavedNotice') }}
      </div>

      <ul class="agent-list" aria-label="agents">
        <li
          v-for="agent in agents"
          :key="agent.key"
          class="agent-row"
          :class="{ 'agent-muted': localWeights[agent.key] === 0 }"
        >
          <div class="agent-meta">
            <strong class="agent-name">{{ agent.name }}</strong>
            <p class="agent-desc">{{ agent.description }}</p>
          </div>

          <div class="agent-controls">
            <div class="slider-row">
              <span class="range-label">{{ t('swarmLab.weights.minLabel') }}</span>
              <input
                :id="`weight-${agent.key}`"
                type="range"
                :min="agent.min"
                :max="agent.max"
                :step="0.1"
                :value="localWeights[agent.key]"
                :aria-label="agent.name"
                :aria-valuetext="`${localWeights[agent.key].toFixed(1)}×`"
                @input="onSlider(agent.key, $event.target.value)"
              />
              <span class="range-label">{{ t('swarmLab.weights.maxLabel') }}</span>
            </div>

            <div class="influence-row">
              <span class="influence-label">{{ t('swarmLab.weights.influenceLabel') }}</span>
              <div class="influence-bar-track" aria-hidden="true">
                <div
                  class="influence-bar-fill"
                  :style="{ width: `${(localWeights[agent.key] / agent.max) * 100}%` }"
                ></div>
              </div>
              <span class="weight-value">{{ localWeights[agent.key].toFixed(1) }}×</span>
            </div>
          </div>
        </li>
      </ul>

      <div class="weights-actions">
        <button
          type="button"
          class="btn-primary"
          :disabled="saving || !isDirty"
          @click="save"
        >
          <Save :size="15" aria-hidden="true" />
          <span>{{ saving ? t('swarmLab.weights.saving') : t('swarmLab.weights.save') }}</span>
        </button>
        <button
          type="button"
          class="btn-secondary"
          :disabled="resetting"
          @click="reset"
        >
          <RotateCcw :size="15" aria-hidden="true" />
          <span>{{ resetting ? t('swarmLab.weights.resetting') : t('swarmLab.weights.reset') }}</span>
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertCircle, AlertTriangle, RotateCcw, Save } from '@lucide/vue'
import { api } from '../../lib/api'

const { t } = useI18n()

const agents = ref([])
const localWeights = reactive({})
const savedWeights = reactive({})
const isCustomized = ref(false)
const loadError = ref(false)
const saveError = ref(false)
const savedNotice = ref(false)
const resetNotice = ref(false)
const saving = ref(false)
const resetting = ref(false)

const isDirty = computed(() =>
  agents.value.some((a) => localWeights[a.key] !== savedWeights[a.key])
)

function applyConfig(data) {
  agents.value = data.agents
  isCustomized.value = data.customized
  for (const a of data.agents) {
    localWeights[a.key] = a.current
    savedWeights[a.key] = a.current
  }
}

async function load() {
  loadError.value = false
  try {
    const res = await api.get('/api/predictions/swarm-config')
    applyConfig(res.data)
  } catch {
    loadError.value = true
  }
}

function onSlider(key, raw) {
  localWeights[key] = Math.round(parseFloat(raw) * 10) / 10
  savedNotice.value = false
  resetNotice.value = false
  saveError.value = false
}

async function save() {
  saving.value = true
  saveError.value = false
  savedNotice.value = false
  try {
    const weights = {}
    for (const a of agents.value) weights[a.key] = localWeights[a.key]
    const res = await api.put('/api/predictions/swarm-config', { weights })
    applyConfig(res.data)
    savedNotice.value = true
    setTimeout(() => { savedNotice.value = false }, 4000)
  } catch {
    saveError.value = true
  } finally {
    saving.value = false
  }
}

async function reset() {
  resetting.value = true
  saveError.value = false
  resetNotice.value = false
  try {
    const res = await api.delete('/api/predictions/swarm-config')
    applyConfig(res.data)
    resetNotice.value = true
    setTimeout(() => { resetNotice.value = false }, 4000)
  } catch {
    saveError.value = true
  } finally {
    resetting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.weights-panel { display: flex; flex-direction: column; gap: var(--space-6); }
.weights-header { align-items: flex-start; display: flex; gap: var(--space-4); justify-content: space-between; }
.weights-header h2 { font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0 0 var(--space-1); }
.weights-header p { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-relaxed); margin: 0; max-width: 56ch; }
.config-badge { align-self: flex-start; border: var(--border-width-thin) solid var(--color-border); flex-shrink: 0; font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); padding: var(--space-1) var(--space-2); text-transform: uppercase; white-space: nowrap; }
.badge-customized { border-color: var(--color-accent); color: var(--color-accent); }
.badge-default { color: var(--color-text-subtle); }
.save-notice { background: var(--color-success-surface, color-mix(in srgb, var(--color-success) 12%, transparent)); border: var(--border-width-thin) solid var(--color-success); color: var(--color-success); font-size: var(--font-size-sm); padding: var(--space-3) var(--space-4); }
.save-error { background: var(--color-danger-surface); border: var(--border-width-thin) solid var(--color-danger); color: var(--color-danger); font-size: var(--font-size-sm); padding: var(--space-3) var(--space-4); }
.unsaved-notice { align-items: center; color: var(--color-text-muted); display: flex; font-size: var(--font-size-xs); gap: var(--space-2); }
.agent-list { display: flex; flex-direction: column; gap: 0; list-style: none; margin: 0; padding: 0; border: var(--border-width-thin) solid var(--color-border); }
.agent-row { background: var(--color-surface); border-bottom: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-6); grid-template-columns: minmax(14rem, 0.9fr) minmax(18rem, 1.1fr); padding: var(--space-5); transition: opacity 0.15s; }
.agent-row:last-child { border-bottom: 0; }
.agent-muted { opacity: 0.55; }
.agent-name { display: block; font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); margin-bottom: var(--space-1); }
.agent-desc { color: var(--color-text-muted); font-size: var(--font-size-xs); line-height: var(--line-height-relaxed); margin: 0; }
.agent-controls { display: flex; flex-direction: column; gap: var(--space-3); justify-content: center; }
.slider-row { align-items: center; display: flex; gap: var(--space-2); }
.slider-row input[type="range"] { accent-color: var(--color-accent); flex: 1; }
.range-label { color: var(--color-text-subtle); font: var(--font-weight-bold) var(--font-size-xs) / 1 var(--font-family-data); min-width: 2.5rem; }
.range-label:last-child { text-align: right; }
.influence-row { align-items: center; display: flex; gap: var(--space-3); }
.influence-label { color: var(--color-text-subtle); font: var(--font-weight-bold) var(--font-size-xs) / 1 var(--font-family-data); text-transform: uppercase; white-space: nowrap; }
.influence-bar-track { background: var(--color-surface-inset); flex: 1; height: 4px; overflow: hidden; }
.influence-bar-fill { background: var(--color-accent); height: 100%; transition: width 0.1s; }
.weight-value { color: var(--color-text); font: var(--font-weight-bold) var(--font-size-sm) / 1 var(--font-family-data); min-width: 2.5rem; text-align: right; }
.weights-actions { display: flex; gap: var(--space-3); }
.btn-primary { align-items: center; background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; display: inline-flex; font-weight: var(--font-weight-semibold); gap: var(--space-2); min-height: var(--control-height-lg); padding: 0 var(--space-5); }
.btn-primary:disabled { cursor: not-allowed; opacity: 0.5; }
.btn-secondary { align-items: center; background: transparent; border: var(--border-width-thin) solid var(--color-border); color: var(--color-text); cursor: pointer; display: inline-flex; font-weight: var(--font-weight-semibold); gap: var(--space-2); min-height: var(--control-height-lg); padding: 0 var(--space-5); }
.btn-secondary:disabled { cursor: not-allowed; opacity: 0.5; }
.btn-primary:focus-visible, .btn-secondary:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.state-panel { align-items: flex-start; background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); color: var(--color-danger); display: flex; gap: var(--space-4); padding: var(--space-8); }
.state-error { background: var(--color-danger-surface); }
.state-panel h2 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0 0 var(--space-4); }
.state-panel button { align-items: center; background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; display: inline-flex; font-weight: var(--font-weight-semibold); gap: var(--space-2); min-height: var(--control-height-lg); padding: 0 var(--space-4); }
@media (max-width: 820px) {
  .agent-row { grid-template-columns: 1fr; gap: var(--space-4); }
  .weights-header { flex-direction: column; }
}
@media (max-width: 480px) {
  .weights-actions { flex-direction: column; }
  .btn-primary, .btn-secondary { justify-content: center; width: 100%; }
}
</style>
