<template>
  <main class="admin-settings-page" aria-labelledby="admin-settings-title">
    <header class="admin-settings-header">
      <div class="header-copy">
        <p class="atlas-kicker">{{ t('adminSettings.eyebrow') }}</p>
        <h1 id="admin-settings-title">{{ t('adminSettings.title') }}</h1>
        <p>{{ t('adminSettings.subtitle') }}</p>
      </div>
      <div v-if="settings?.updated_at" class="audit">
        <span>{{ t('adminSettings.updated') }}</span>
        <strong>{{ settings.updated_at }}</strong>
        <small v-if="settings.updated_by">{{ settings.updated_by.email }}</small>
      </div>
    </header>

    <form class="settings-panel" @submit.prevent="save">
      <section class="settings-section" aria-labelledby="llm-heading">
        <div>
          <p class="section-index">01</p>
          <h2 id="llm-heading">{{ t('adminSettings.sections.llm.title') }}</h2>
          <p class="hint">{{ t('adminSettings.sections.llm.copy') }}</p>
        </div>
        <div class="field-grid">
          <label class="field">
            <span>{{ t('adminSettings.fields.llmBaseUrl') }}</span>
            <input v-model="form.llm_base_url" type="text" />
          </label>
          <label class="field">
            <span>{{ t('adminSettings.fields.llmModelName') }}</span>
            <input v-model="form.llm_model_name" type="text" />
          </label>
          <ApiKeyField
            v-model="secretForm.llm_api_key"
            :label="t('adminSettings.fields.llmKey')"
            :configured="isConfigured(secretByKey.llm_api_key)"
            :placeholder="t('adminSettings.keyPlaceholder')"
            :configured-label="t('adminSettings.configured')"
            :not-configured-label="t('adminSettings.notConfigured')"
            :show-label="t('adminSettings.showKey')"
            :hide-label="t('adminSettings.hideKey')"
            :clear-label="t('adminSettings.clearKey')"
            @edit="markSecretEdited(secretByKey.llm_api_key)"
            @clear="clearSecret(secretByKey.llm_api_key)"
          />
        </div>
      </section>

      <section class="settings-section" aria-labelledby="zep-heading">
        <div>
          <p class="section-index">02</p>
          <h2 id="zep-heading">{{ t('adminSettings.sections.zep.title') }}</h2>
          <p class="hint">{{ t('adminSettings.sections.zep.copy') }}</p>
        </div>
        <div class="field-grid">
          <label class="field">
            <span>{{ t('adminSettings.fields.zepGraphId') }}</span>
            <input v-model="form.zep_graph_id" type="text" />
          </label>
          <ApiKeyField
            v-model="secretForm.zep_api_key"
            :label="t('adminSettings.fields.zepKey')"
            :configured="isConfigured(secretByKey.zep_api_key)"
            :placeholder="t('adminSettings.keyPlaceholder')"
            :configured-label="t('adminSettings.configured')"
            :not-configured-label="t('adminSettings.notConfigured')"
            :show-label="t('adminSettings.showKey')"
            :hide-label="t('adminSettings.hideKey')"
            :clear-label="t('adminSettings.clearKey')"
            @edit="markSecretEdited(secretByKey.zep_api_key)"
            @clear="clearSecret(secretByKey.zep_api_key)"
          />
        </div>
      </section>

      <section class="settings-section" aria-labelledby="youtube-heading">
        <div>
          <p class="section-index">03</p>
          <h2 id="youtube-heading">{{ t('adminSettings.sections.youtube.title') }}</h2>
          <p class="hint">{{ t('adminSettings.sections.youtube.copy') }}</p>
        </div>
        <div class="field-grid">
          <ApiKeyField
            v-model="secretForm.youtube_api_key"
            :label="t('adminSettings.fields.youtubeKey')"
            :configured="isConfigured(secretByKey.youtube_api_key)"
            :placeholder="t('adminSettings.keyPlaceholder')"
            :configured-label="t('adminSettings.configured')"
            :not-configured-label="t('adminSettings.notConfigured')"
            :show-label="t('adminSettings.showKey')"
            :hide-label="t('adminSettings.hideKey')"
            :clear-label="t('adminSettings.clearKey')"
            @edit="markSecretEdited(secretByKey.youtube_api_key)"
            @clear="clearSecret(secretByKey.youtube_api_key)"
          />
        </div>
      </section>

      <section class="settings-section" aria-labelledby="opta-heading">
        <div>
          <p class="section-index">04</p>
          <h2 id="opta-heading">{{ t('adminSettings.sections.opta.title') }}</h2>
          <p class="hint">{{ t('adminSettings.sections.opta.copy') }}</p>
        </div>
        <div class="field-grid">
          <label class="field">
            <span>{{ t('adminSettings.fields.optaBaseUrl') }}</span>
            <input v-model="form.opta_base_url" type="text" />
          </label>
          <ApiKeyField
            v-model="secretForm.opta_api_key"
            :label="t('adminSettings.fields.optaKey')"
            :configured="isConfigured(secretByKey.opta_api_key)"
            :placeholder="t('adminSettings.keyPlaceholder')"
            :configured-label="t('adminSettings.configured')"
            :not-configured-label="t('adminSettings.notConfigured')"
            :show-label="t('adminSettings.showKey')"
            :hide-label="t('adminSettings.hideKey')"
            :clear-label="t('adminSettings.clearKey')"
            @edit="markSecretEdited(secretByKey.opta_api_key)"
            @clear="clearSecret(secretByKey.opta_api_key)"
          />
        </div>
      </section>

      <section class="settings-section" aria-labelledby="execution-heading">
        <div>
          <p class="section-index">05</p>
          <h2 id="execution-heading">{{ t('adminSettings.sections.execution.title') }}</h2>
          <p class="hint">{{ t('adminSettings.sections.execution.copy') }}</p>
        </div>
        <div class="field-grid">
          <label class="field">
            <span>{{ t('adminSettings.fields.parallelAgents') }}</span>
            <input v-model.number="form.swarm_parallel_agents" type="number" min="1" max="7" />
          </label>
          <label class="field">
            <span>{{ t('adminSettings.fields.timeoutSeconds') }}</span>
            <input v-model.number="form.swarm_timeout_seconds" type="number" min="1" />
          </label>
          <label class="field">
            <span>{{ t('adminSettings.fields.simulations') }}</span>
            <input v-model.number="form.mc_simulations" type="number" min="1" />
          </label>
        </div>
      </section>

      <section class="settings-section" aria-labelledby="limits-heading">
        <div class="section-header">
          <div>
            <p class="section-index">06</p>
            <h2 id="limits-heading">{{ t('adminSettings.sections.limits.title') }}</h2>
            <p class="hint">{{ t('adminSettings.sections.limits.copy') }}</p>
          </div>
          <button class="btn-save" type="button" :disabled="featureLimitLoading" @click="saveFeatureLimits">
            {{ featureLimitLoading ? t('adminSettings.saving') : t('adminSettings.saveLimits') }}
          </button>
        </div>
        <div class="limit-table">
          <div class="limit-head">
            <span>{{ t('adminSettings.feature') }}</span>
            <span v-for="tier in limitTiers" :key="tier">{{ tierLabel(tier) }}</span>
          </div>
          <div v-for="feature in featureLimitFeatures" :key="feature.feature_key" class="limit-row">
            <span>{{ feature.label }}</span>
            <label v-for="tier in limitTiers" :key="`${tier}-${feature.feature_key}`" class="limit-input">
              <input
                v-model="featureLimitForm[tier][feature.feature_key]"
                type="number"
                min="0"
                :placeholder="tier === 'free' ? '0' : t('adminSettings.unlimited')"
              />
            </label>
          </div>
        </div>
        <p v-if="featureLimitError" class="error-box">{{ featureLimitError }}</p>
        <p v-if="featureLimitSuccess" class="success-box">{{ featureLimitSuccess }}</p>
      </section>

      <p v-if="error" class="error-box">{{ error }}</p>
      <p v-if="success" class="success-box">{{ success }}</p>

      <div class="actions">
        <button class="btn-save" :disabled="loading">{{ loading ? t('adminSettings.saving') : t('adminSettings.save') }}</button>
      </div>
    </form>
  </main>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import ApiKeyField from '../components/ApiKeyField.vue'
import { api } from '../lib/api'

const { t } = useI18n()

const loading = ref(false)
const featureLimitLoading = ref(false)
const error = ref('')
const success = ref('')
const featureLimitError = ref('')
const featureLimitSuccess = ref('')
const settings = ref(null)
const limitTiers = ['free', 'basic', 'pro']
const featureLimitFeatures = ref([])
const featureLimitForm = reactive({
  free: {},
  basic: {},
  pro: {},
})
const form = reactive({
  llm_base_url: '',
  llm_model_name: '',
  zep_graph_id: '',
  opta_base_url: '',
  swarm_parallel_agents: 1,
  swarm_timeout_seconds: 60,
  mc_simulations: 10000,
})
const secretForm = reactive({
  llm_api_key: '',
  zep_api_key: '',
  youtube_api_key: '',
  opta_api_key: '',
})
const clearFlags = reactive({
  clear_llm_api_key: false,
  clear_zep_api_key: false,
  clear_youtube_api_key: false,
  clear_opta_api_key: false,
})
const secrets = [
  { key: 'llm_api_key', configured: 'llm_api_key_configured', clear: 'clear_llm_api_key' },
  { key: 'zep_api_key', configured: 'zep_api_key_configured', clear: 'clear_zep_api_key' },
  { key: 'youtube_api_key', configured: 'youtube_api_key_configured', clear: 'clear_youtube_api_key' },
  { key: 'opta_api_key', configured: 'opta_api_key_configured', clear: 'clear_opta_api_key' },
]
const secretByKey = computed(() => Object.fromEntries(secrets.map((secret) => [secret.key, secret])))

function tierLabel(tier) {
  return t(`adminSettings.tiers.${tier}`, tier)
}

function applySettings(payload) {
  settings.value = payload
  form.llm_base_url = payload.llm_base_url || ''
  form.llm_model_name = payload.llm_model_name || ''
  form.zep_graph_id = payload.zep_graph_id || ''
  form.opta_base_url = payload.opta_base_url || ''
  form.swarm_parallel_agents = payload.swarm_parallel_agents
  form.swarm_timeout_seconds = payload.swarm_timeout_seconds
  form.mc_simulations = payload.mc_simulations
  for (const secret of secrets) {
    secretForm[secret.key] = ''
    clearFlags[secret.clear] = false
  }
}

function applyFeatureLimits(payload) {
  featureLimitFeatures.value = payload.features || []
  for (const tier of limitTiers) {
    featureLimitForm[tier] = {}
    const tierLimits = payload.tiers?.[tier] || {}
    for (const feature of featureLimitFeatures.value) {
      const value = tierLimits[feature.feature_key]
      featureLimitForm[tier][feature.feature_key] = value == null ? '' : String(value)
    }
  }
}

function isConfigured(secret) {
  if (clearFlags[secret.clear]) return false
  return Boolean(settings.value?.[secret.configured])
}

function clearSecret(secret) {
  secretForm[secret.key] = ''
  clearFlags[secret.clear] = true
}

function markSecretEdited(secret) {
  if (secretForm[secret.key].trim()) {
    clearFlags[secret.clear] = false
  }
}

function buildPayload() {
  const payload = { ...form }
  for (const secret of secrets) {
    const value = secretForm[secret.key].trim()
    if (value) payload[secret.key] = value
    if (clearFlags[secret.clear]) payload[secret.clear] = true
  }
  return payload
}

function buildFeatureLimitPayload() {
  const policies = []
  for (const tier of limitTiers) {
    for (const feature of featureLimitFeatures.value) {
      const rawValue = featureLimitForm[tier][feature.feature_key]
      policies.push({
        tier,
        feature_key: feature.feature_key,
        limit_count: rawValue === '' || rawValue == null ? null : Number(rawValue),
      })
    }
  }
  return { policies }
}

onMounted(async () => {
  try {
    const res = await api.get('/api/admin/settings')
    applySettings(res.data)
  } catch (err) {
    error.value = err.response?.data?.error || t('adminSettings.errors.load')
  }

  try {
    const res = await api.get('/api/admin/feature-limits')
    applyFeatureLimits(res.data)
  } catch (err) {
    featureLimitError.value = err.response?.data?.error || t('adminSettings.errors.loadLimits')
  }
})

async function save() {
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    const res = await api.put('/api/admin/settings', buildPayload())
    applySettings(res.data)
    success.value = t('adminSettings.success')
  } catch (err) {
    error.value = err.response?.data?.error || t('adminSettings.errors.save')
  } finally {
    loading.value = false
  }
}

async function saveFeatureLimits() {
  featureLimitLoading.value = true
  featureLimitError.value = ''
  featureLimitSuccess.value = ''
  try {
    const res = await api.put('/api/admin/feature-limits', buildFeatureLimitPayload())
    applyFeatureLimits(res.data)
    featureLimitSuccess.value = t('adminSettings.limitsSaved')
  } catch (err) {
    featureLimitError.value = err.response?.data?.error || t('adminSettings.errors.saveLimits')
  } finally {
    featureLimitLoading.value = false
  }
}
</script>

<style scoped>
.admin-settings-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: var(--space-8) 0 var(--space-12);
}

.admin-settings-header {
  align-items: end;
  border-bottom: var(--border-width-strong) solid var(--color-border-strong);
  display: flex;
  justify-content: space-between;
  gap: var(--space-6);
  padding-bottom: var(--space-6);
}

.atlas-kicker,.section-index { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs)/var(--line-height-normal) var(--font-family-data); margin: 0 0 var(--space-2); }
.header-copy h1 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-4xl); font-weight: var(--font-weight-heavy); line-height: var(--line-height-tight); margin: 0; }
.header-copy > p:last-child { color: var(--color-text-muted); font-size: var(--font-size-md); line-height: var(--line-height-relaxed); margin: var(--space-3) 0 0; max-width: 48rem; }
.audit { color: var(--color-text-subtle); display: flex; flex: 0 0 auto; flex-direction: column; font: var(--font-weight-medium) var(--font-size-xs)/var(--line-height-normal) var(--font-family-data); gap: var(--space-1); text-align: right; }
.audit strong { color: var(--color-text); font-size: var(--font-size-sm); }

.settings-panel {
  background: var(--color-surface);
  border: var(--border-width-thin) solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}

.limit-table {
  border: var(--border-width-thin) solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.limit-head,
.limit-row {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: minmax(160px, 1fr) repeat(3, minmax(90px, 120px));
  padding: var(--space-3) var(--space-4);
}

.limit-head {
  background: var(--color-surface-inset);
  color: var(--color-text-subtle);
  font: var(--font-weight-bold) var(--font-size-xs)/var(--line-height-normal) var(--font-family-data);
  text-transform: uppercase;
}

.limit-row {
  align-items: center;
  border-top: var(--border-width-thin) solid var(--color-border);
  color: var(--color-text);
  font-size: var(--font-size-sm);
}

.limit-input input {
  width: 100%;
}

.section-header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  align-items: flex-start;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4) var(--space-5);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.field span {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.wide-field { grid-column: 1 / -1; }

input {
  background: var(--color-surface-raised);
  color: var(--color-text);
  border: var(--border-width-thin) solid var(--color-border-strong);
  border-radius: var(--radius-md);
  padding: 0 var(--space-3);
  font-size: var(--font-size-sm);
  min-height: var(--control-height-lg);
}

input::placeholder { color: var(--color-text-subtle); }

input:focus {
  border-color: var(--color-focus);
  outline: var(--border-width-thin) solid var(--color-focus);
  outline-offset: 2px;
}

.hint {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
  margin: 0;
  max-width: 66ch;
}

.settings-section {
  border-top: var(--border-width-thin) solid var(--color-border);
  padding-top: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.settings-section:first-child { border-top: 0; padding-top: 0; }

.settings-section h2 {
  color: var(--color-text);
  font-family: var(--font-family-display);
  font-size: var(--font-size-2xl);
  line-height: var(--line-height-tight);
  margin: 0 0 var(--space-2);
}

.error-box, .success-box {
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-normal);
  margin: 0;
  padding: var(--space-3) var(--space-4);
}

.error-box {
  background: var(--color-danger-surface);
  border: var(--border-width-thin) solid var(--color-danger);
  color: var(--color-danger);
}

.success-box {
  background: var(--color-success-surface);
  border: var(--border-width-thin) solid var(--color-success);
  color: var(--color-success);
}

.actions { display: flex; justify-content: flex-end; }

.btn-save {
  background: var(--color-accent);
  border: var(--border-width-thin) solid var(--color-accent);
  border-radius: var(--radius-md);
  color: var(--color-accent-contrast);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  min-height: var(--control-height-lg);
  padding: 0 var(--space-5);
  cursor: pointer;
  white-space: nowrap;
}

.btn-save:hover:not(:disabled) { background: var(--color-accent-hover); border-color: var(--color-accent-hover); }
.btn-save:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.btn-save:disabled { cursor: default; opacity: .55; }

@media (max-width: 720px) {
  .admin-settings-page { padding-top: var(--space-6); }
  .settings-panel { padding: var(--space-5); }

  .field-grid {
    grid-template-columns: 1fr;
  }

  .admin-settings-header {
    align-items: start;
    flex-direction: column;
  }

  .audit {
    text-align: left;
  }

  .section-header {
    flex-direction: column;
    align-items: stretch;
  }

  .section-header .btn-save { width: 100%; }
  .limit-table { overflow-x: auto; }
  .limit-head,.limit-row { min-width: 33rem; }
}
</style>
