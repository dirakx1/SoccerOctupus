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
      <div class="field-grid">
        <label class="field">
          <span>LLM base URL</span>
          <input v-model="form.llm_base_url" type="text" />
        </label>
        <label class="field">
          <span>LLM model name</span>
          <input v-model="form.llm_model_name" type="text" />
        </label>
        <label class="field">
          <span>Zep graph ID</span>
          <input v-model="form.zep_graph_id" type="text" />
        </label>
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

      <p class="hint">Secrets remain environment-only and are not editable here.</p>
      <p v-if="error" class="error-box">{{ error }}</p>
      <p v-if="success" class="success-box">{{ success }}</p>

      <div class="actions">
        <button class="btn-save" :disabled="loading">{{ loading ? 'Saving…' : 'Save settings' }}</button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'

import { api } from '../lib/api'

const loading = ref(false)
const error = ref('')
const success = ref('')
const settings = ref(null)
const form = reactive({
  llm_base_url: '',
  llm_model_name: '',
  zep_graph_id: '',
  swarm_parallel_agents: 1,
  swarm_timeout_seconds: 60,
  mc_simulations: 10000,
})

function applySettings(payload) {
  settings.value = payload
  form.llm_base_url = payload.llm_base_url || ''
  form.llm_model_name = payload.llm_model_name || ''
  form.zep_graph_id = payload.zep_graph_id || ''
  form.swarm_parallel_agents = payload.swarm_parallel_agents
  form.swarm_timeout_seconds = payload.swarm_timeout_seconds
  form.mc_simulations = payload.mc_simulations
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
    const res = await api.put('/api/admin/settings', { ...form })
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
.settings-view { display: flex; flex-direction: column; gap: 24px; }

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
}

h1 { color: #e2b714; font-size: 28px; }
.subtitle { color: #8888aa; font-size: 14px; margin-top: 8px; }
.audit { color: #8888aa; font-size: 12px; display: flex; flex-direction: column; gap: 4px; text-align: right; }
.audit strong { color: #e0e0e0; font-size: 13px; }

.settings-panel {
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 12px;
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  color: #8888aa;
  font-size: 13px;
}

input {
  background: #0a0a1a;
  color: #e0e0e0;
  border: 1px solid #0f3460;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
}

.hint {
  color: #6a6a8a;
  font-size: 13px;
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
}
</style>
