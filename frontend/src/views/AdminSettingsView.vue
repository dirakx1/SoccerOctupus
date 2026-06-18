<template>
  <div class="settings-view">
    <div class="page-header">
      <div>
        <h1>Admin Settings</h1>
        <p class="subtitle">Manage shared runtime model preferences for the app.</p>
      </div>
      <div v-if="settings?.updated_at" class="audit">
        <span>Last updated</span>
        <strong>{{ settings.updated_at }}</strong>
        <small v-if="settings.updated_by">{{ settings.updated_by.email }}</small>
      </div>
    </div>

    <form class="settings-panel" @submit.prevent="save">
      <section class="settings-section" aria-labelledby="llm-heading">
        <div>
          <h2 id="llm-heading">LLM provider</h2>
          <p class="hint">Controls narrative synthesis and any OpenAI-compatible model endpoint.</p>
        </div>
        <div class="field-grid">
          <label class="field">
            <span>LLM base URL</span>
            <input v-model="form.llm_base_url" type="text" />
          </label>
          <label class="field">
            <span>LLM model name</span>
            <input v-model="form.llm_model_name" type="text" />
          </label>
          <ApiKeyField
            v-model="secretForm.llm_api_key"
            :label="secretByKey.llm_api_key.label"
            :configured="isConfigured(secretByKey.llm_api_key)"
            @edit="markSecretEdited(secretByKey.llm_api_key)"
            @clear="clearSecret(secretByKey.llm_api_key)"
          />
        </div>
      </section>

      <section class="settings-section" aria-labelledby="zep-heading">
        <div>
          <h2 id="zep-heading">Zep knowledge graph</h2>
          <p class="hint">Stores the graph connection used by agents for shared football context.</p>
        </div>
        <div class="field-grid">
          <label class="field">
            <span>Zep graph ID</span>
            <input v-model="form.zep_graph_id" type="text" />
          </label>
          <ApiKeyField
            v-model="secretForm.zep_api_key"
            :label="secretByKey.zep_api_key.label"
            :configured="isConfigured(secretByKey.zep_api_key)"
            @edit="markSecretEdited(secretByKey.zep_api_key)"
            @clear="clearSecret(secretByKey.zep_api_key)"
          />
        </div>
      </section>

      <section class="settings-section" aria-labelledby="youtube-heading">
        <div>
          <h2 id="youtube-heading">YouTube data</h2>
          <p class="hint">Powers video momentum and tactical analysis signals. Keys are encrypted at rest and never returned after save.</p>
        </div>
        <div class="field-grid">
          <ApiKeyField
            v-model="secretForm.youtube_api_key"
            :label="secretByKey.youtube_api_key.label"
            :configured="isConfigured(secretByKey.youtube_api_key)"
            @edit="markSecretEdited(secretByKey.youtube_api_key)"
            @clear="clearSecret(secretByKey.youtube_api_key)"
          />
        </div>
      </section>

      <section class="settings-section" aria-labelledby="opta-heading">
        <div>
          <h2 id="opta-heading">Opta data</h2>
          <p class="hint">Controls Stats Perform player-quality data for squad depth and benchmark fallbacks.</p>
        </div>
        <div class="field-grid">
          <label class="field">
            <span>Opta base URL</span>
            <input v-model="form.opta_base_url" type="text" />
          </label>
          <ApiKeyField
            v-model="secretForm.opta_api_key"
            :label="secretByKey.opta_api_key.label"
            :configured="isConfigured(secretByKey.opta_api_key)"
            @edit="markSecretEdited(secretByKey.opta_api_key)"
            @clear="clearSecret(secretByKey.opta_api_key)"
          />
        </div>
      </section>

      <section class="settings-section" aria-labelledby="execution-heading">
        <div>
          <h2 id="execution-heading">Execution tuning</h2>
          <p class="hint">Controls swarm concurrency, request deadline, and tournament simulation depth.</p>
        </div>
        <div class="field-grid">
          <label class="field">
            <span>Swarm parallel agents</span>
            <input v-model.number="form.swarm_parallel_agents" type="number" min="1" max="7" />
          </label>
          <label class="field">
            <span>Swarm timeout seconds</span>
            <input v-model.number="form.swarm_timeout_seconds" type="number" min="1" />
          </label>
          <label class="field">
            <span>Monte Carlo simulations</span>
            <input v-model.number="form.mc_simulations" type="number" min="1" />
          </label>
        </div>
      </section>

      <p v-if="error" class="error-box">{{ error }}</p>
      <p v-if="success" class="success-box">{{ success }}</p>

      <div class="actions">
        <button class="btn-save" :disabled="loading">{{ loading ? 'Saving…' : 'Save settings' }}</button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import ApiKeyField from '../components/ApiKeyField.vue'
import { api } from '../lib/api'

const loading = ref(false)
const error = ref('')
const success = ref('')
const settings = ref(null)
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
  { key: 'llm_api_key', label: 'LLM API key', configured: 'llm_api_key_configured', clear: 'clear_llm_api_key' },
  { key: 'zep_api_key', label: 'Zep API key', configured: 'zep_api_key_configured', clear: 'clear_zep_api_key' },
  { key: 'youtube_api_key', label: 'YouTube API key', configured: 'youtube_api_key_configured', clear: 'clear_youtube_api_key' },
  { key: 'opta_api_key', label: 'Opta API key', configured: 'opta_api_key_configured', clear: 'clear_opta_api_key' },
]
const secretByKey = computed(() => Object.fromEntries(secrets.map((secret) => [secret.key, secret])))

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

onMounted(async () => {
  try {
    const res = await api.get('/api/admin/settings')
    applySettings(res.data)
  } catch (err) {
    error.value = err.response?.data?.error || 'Could not load settings.'
  }
})

async function save() {
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    const res = await api.put('/api/admin/settings', buildPayload())
    applySettings(res.data)
    success.value = 'Settings saved.'
  } catch (err) {
    error.value = err.response?.data?.error || 'Could not save settings.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.settings-view {
  display: flex;
  flex-direction: column;
  gap: 28px;
  max-width: 1180px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
}

h1 { color: #e2b714; font-size: 30px; letter-spacing: -0.02em; }
.subtitle { color: #a0a0bd; font-size: 15px; margin-top: 8px; }
.audit { color: #8888aa; font-size: 12px; display: flex; flex-direction: column; gap: 4px; text-align: right; }
.audit strong { color: #e0e0e0; font-size: 13px; }

.settings-panel {
  background: #111a33;
  border: 1px solid #17436e;
  border-radius: 16px;
  padding: 32px 36px;
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px 22px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  color: #a0a0bd;
  font-size: 13px;
}

.wide-field { grid-column: 1 / -1; }

input {
  background: #0a0a1a;
  color: #e0e0e0;
  border: 1px solid #0f3460;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
  min-height: 44px;
}

input::placeholder { color: #51516b; }

input:focus {
  border-color: #e2b714;
  outline: none;
}

.hint {
  color: #8f8fac;
  font-size: 13px;
  margin-top: 6px;
}

.settings-section {
  border-top: 1px solid #17436e;
  padding-top: 26px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.settings-section:first-child { border-top: 0; padding-top: 0; }

.settings-section h2 {
  color: #e2b714;
  font-size: 20px;
  margin-bottom: 6px;
}

.error-box, .success-box {
  border-radius: 8px;
  padding: 12px 14px;
  font-size: 13px;
}

.error-box {
  background: #3d1a1a;
  border: 1px solid #c53030;
  color: #fc8181;
}

.success-box {
  background: rgba(46, 160, 67, 0.12);
  border: 1px solid rgba(46, 160, 67, 0.35);
  color: #9ae6b4;
}

.actions { display: flex; justify-content: flex-end; }

.btn-save {
  background: linear-gradient(135deg, #e2b714, #f6d860);
  color: #0a0a1a;
  font-weight: 700;
  border: none;
  border-radius: 10px;
  padding: 12px 24px;
  cursor: pointer;
  min-width: 150px;
}

@media (max-width: 720px) {
  .settings-panel {
    padding: 24px;
  }

  .field-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }

  .audit {
    text-align: left;
  }
}
</style>
