<template>
  <div class="predict-view">
    <h1>⚡ Predict a Match</h1>
    <p class="subtitle">Select two teams and run the full swarm prediction pipeline.</p>

    <div class="form-panel">
      <div class="selectors">
        <div class="select-group">
          <label>Home Team</label>
          <select v-model="homeTeam">
            <option value="">— select —</option>
            <option v-for="t in teams" :key="t.name" :value="t.name">
              {{ t.name }} (ELO {{ t.elo }})
            </option>
          </select>
        </div>
        <div class="vs-label">VS</div>
        <div class="select-group">
          <label>Away Team</label>
          <select v-model="awayTeam">
            <option value="">— select —</option>
            <option v-for="t in teams" :key="t.name" :value="t.name">
              {{ t.name }} (ELO {{ t.elo }})
            </option>
          </select>
        </div>
      </div>

      <div class="stage-row">
        <label>Stage</label>
        <select v-model="stage">
          <option value="group">Group Stage</option>
          <option value="round_of_32">Round of 32</option>
          <option value="round_of_16">Round of 16</option>
          <option value="quarter_final">Quarter Final</option>
          <option value="semi_final">Semi Final</option>
          <option value="final">Final</option>
        </select>
      </div>

      <button class="btn-predict" :disabled="!homeTeam || !awayTeam || loading" @click="runPrediction">
        {{ loading ? '🐙 Swarm running…' : '🚀 Run Swarm Prediction' }}
      </button>
    </div>

    <!-- Error -->
    <div v-if="error" class="error-box">{{ error }}</div>

    <!-- Result -->
    <div v-if="result" class="result-panel">
      <div class="match-header">
        <div class="team home-team">{{ result.home_team }}</div>
        <div class="score-block">
          <div class="score">{{ result.most_likely_score }}</div>
          <div class="score-label">Most Likely Score</div>
        </div>
        <div class="team away-team">{{ result.away_team }}</div>
      </div>

      <div class="probs-row">
        <div class="prob-block" :class="{ winner: result.outcome === 'home_win' }">
          <div class="prob-pct">{{ pct(result.home_win_prob) }}</div>
          <div class="prob-label">{{ result.home_team }} Win</div>
        </div>
        <div class="prob-block" :class="{ winner: result.outcome === 'draw' }">
          <div class="prob-pct">{{ pct(result.draw_prob) }}</div>
          <div class="prob-label">Draw</div>
        </div>
        <div class="prob-block" :class="{ winner: result.outcome === 'away_win' }">
          <div class="prob-pct">{{ pct(result.away_win_prob) }}</div>
          <div class="prob-label">{{ result.away_team }} Win</div>
        </div>
      </div>

      <!-- Confidence bar -->
      <div class="confidence-row">
        <span>Swarm Confidence</span>
        <div class="bar-bg">
          <div class="bar-fill" :style="{ width: pct(result.overall_confidence) }"></div>
        </div>
        <span>{{ pct(result.overall_confidence) }}</span>
      </div>

      <!-- Narrative -->
      <div v-if="result.swarm_consensus" class="narrative">
        <h3>🐙 Swarm Consensus</h3>
        <p>{{ result.swarm_consensus }}</p>
      </div>

      <!-- Key factors -->
      <div v-if="result.key_factors?.length" class="key-factors">
        <h3>🔑 Key Factors</h3>
        <ul>
          <li v-for="f in result.key_factors" :key="f">{{ f }}</li>
        </ul>
      </div>

      <!-- Agent breakdown -->
      <div class="agents-breakdown">
        <h3>🤖 Agent Breakdown</h3>
        <div class="agent-row" v-for="a in result.agent_predictions" :key="a.agent">
          <div class="agent-name">{{ a.agent }}</div>
          <div class="agent-probs">
            <span class="hw">H {{ pct(a.home_win_prob) }}</span>
            <span class="dr">D {{ pct(a.draw_prob) }}</span>
            <span class="aw">A {{ pct(a.away_win_prob) }}</span>
            <span class="sc">{{ a.predicted_score }}</span>
            <span class="conf">conf {{ pct(a.confidence) }}</span>
          </div>
          <div class="agent-reasoning">{{ a.reasoning }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../lib/api'

const teams = ref([])
const homeTeam = ref('')
const awayTeam = ref('')
const stage = ref('group')
const loading = ref(false)
const result = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    const res = await api.get('/api/predictions/teams')
    teams.value = res.data.teams
  } catch (e) {
    error.value = 'Could not load team list — is the backend running?'
  }
})

async function runPrediction() {
  if (!homeTeam.value || !awayTeam.value) return
  loading.value = true
  error.value = ''
  result.value = null
  try {
    const res = await api.post('/api/predictions/match', {
      home_team: homeTeam.value,
      away_team: awayTeam.value,
      stage: stage.value,
    })
    result.value = res.data
  } catch (e) {
    error.value = e.response?.data?.error || e.message
  } finally {
    loading.value = false
  }
}

const pct = v => (v * 100).toFixed(1) + '%'
</script>

<style scoped>
.predict-view { display: flex; flex-direction: column; gap: 28px; }
h1 { color: #e2b714; font-size: 28px; }
.subtitle { color: #8888aa; font-size: 14px; }

.form-panel {
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 12px;
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.selectors { display: grid; grid-template-columns: 1fr auto 1fr; align-items: end; gap: 16px; }
.select-group { display: flex; flex-direction: column; gap: 6px; }
.select-group label { color: #8888aa; font-size: 13px; }
select {
  background: #0a0a1a;
  color: #e0e0e0;
  border: 1px solid #0f3460;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
}
.vs-label { color: #e2b714; font-size: 20px; font-weight: 700; padding-bottom: 10px; }

.stage-row { display: flex; align-items: center; gap: 16px; }
.stage-row label { color: #8888aa; font-size: 13px; min-width: 48px; }
.stage-row select { flex: 0 0 220px; }

.btn-predict {
  background: linear-gradient(135deg, #e2b714, #f6d860);
  color: #0a0a1a;
  font-weight: 700;
  font-size: 16px;
  border: none;
  border-radius: 10px;
  padding: 14px 32px;
  cursor: pointer;
  transition: opacity 0.2s;
}
.btn-predict:disabled { opacity: 0.5; cursor: default; }

.error-box { background: #3d1a1a; border: 1px solid #c53030; border-radius: 8px; padding: 14px; color: #fc8181; }

.result-panel { background: #16213e; border: 1px solid #0f3460; border-radius: 12px; padding: 28px; display: flex; flex-direction: column; gap: 24px; }

.match-header { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; text-align: center; gap: 16px; }
.team { font-size: 22px; font-weight: 700; color: #e0e0e0; }
.home-team { text-align: right; }
.away-team { text-align: left; }
.score-block { text-align: center; }
.score { font-size: 40px; font-weight: 800; color: #e2b714; }
.score-label { font-size: 11px; color: #8888aa; }

.probs-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.prob-block { text-align: center; background: #0f3460; border-radius: 10px; padding: 16px; border: 2px solid transparent; }
.prob-block.winner { border-color: #e2b714; background: #1e3a5f; }
.prob-pct { font-size: 28px; font-weight: 800; color: #e2b714; }
.prob-label { font-size: 12px; color: #a0aec0; margin-top: 4px; }

.confidence-row { display: flex; align-items: center; gap: 12px; font-size: 13px; color: #a0aec0; }
.bar-bg { flex: 1; height: 8px; background: #0a0a1a; border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; background: linear-gradient(90deg, #e2b714, #f6d860); border-radius: 4px; transition: width 0.6s; }

.narrative, .key-factors { background: #0f1a2e; border-radius: 8px; padding: 16px 20px; }
.narrative h3, .key-factors h3 { color: #e2b714; font-size: 15px; margin-bottom: 10px; }
.narrative p { color: #c0c0d0; font-size: 14px; line-height: 1.6; }
.key-factors ul { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.key-factors li { color: #c0c0d0; font-size: 14px; padding-left: 16px; position: relative; }
.key-factors li::before { content: '→'; position: absolute; left: 0; color: #e2b714; }

.agents-breakdown h3 { color: #e2b714; font-size: 15px; margin-bottom: 12px; }
.agent-row { background: #0f1a2e; border-radius: 8px; padding: 14px 16px; margin-bottom: 10px; }
.agent-name { font-size: 13px; font-weight: 600; color: #a0c0e0; margin-bottom: 6px; }
.agent-probs { display: flex; gap: 12px; font-size: 13px; margin-bottom: 6px; flex-wrap: wrap; }
.hw { color: #68d391; } .dr { color: #fbd38d; } .aw { color: #fc8181; }
.sc { color: #e2b714; font-weight: 700; }
.conf { color: #8888aa; }
.agent-reasoning { font-size: 12px; color: #6a6a8a; line-height: 1.5; }
</style>
