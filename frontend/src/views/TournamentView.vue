<template>
  <div class="tournament-view">
    <h1>🌍 WC 2026 Full Tournament Simulation</h1>
    <p class="subtitle">
      Simulate all 104 matches via Monte Carlo (fast) or the full swarm pipeline.
    </p>

    <div class="controls">
      <label class="toggle-label">
        <input type="checkbox" v-model="useSwarm" />
        Use full swarm (slower — calls all 4 agents per match)
      </label>
      <button class="btn-sim" :disabled="loading" @click="runSim">
        {{ loading ? '⏳ Simulating… this may take a minute' : '▶ Run Tournament Simulation' }}
      </button>
    </div>

    <div v-if="error" class="error-box">
      {{ error }}
      <BillingPlansLink v-if="subscriptionRequired" />
    </div>

    <div v-if="result" class="result-panel">
      <!-- Champion podium -->
      <div class="podium">
        <div class="podium-spot second">
          <div class="medal">🥈</div>
          <div class="podium-team">{{ result.runner_up }}</div>
          <div class="podium-label">Runner-Up</div>
        </div>
        <div class="podium-spot first">
          <div class="medal">🏆</div>
          <div class="podium-team">{{ result.champion }}</div>
          <div class="podium-label">CHAMPION</div>
          <div class="champion-prob">{{ pct(result.champion_probability) }} in final</div>
        </div>
        <div class="podium-spot third">
          <div class="medal">🥉</div>
          <div class="podium-team">{{ result.third_place }}</div>
          <div class="podium-label">3rd Place</div>
        </div>
      </div>

      <!-- Knockout bracket summary -->
      <div class="bracket-section">
        <h2>Knockout Results</h2>
        <div class="matches-list">
          <div
            class="match-item"
            v-for="m in result.knockout_matches"
            :key="m.prediction_id"
          >
            <span class="stage-badge">{{ formatStage(m.stage) }}</span>
            <span class="mt-home" :class="{ winner: m.outcome === 'home_win' }">{{ m.home_team }}</span>
            <span class="score">{{ m.most_likely_score }}</span>
            <span class="mt-away" :class="{ winner: m.outcome === 'away_win' }">{{ m.away_team }}</span>
            <span class="probs">
              H {{ pct(m.home_win_prob) }} / D {{ pct(m.draw_prob) }} / A {{ pct(m.away_win_prob) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Group standings summary -->
      <div class="groups-section">
        <h2>Group Stage Results</h2>
        <div class="groups-grid">
          <div class="group-block" v-for="(standings, g) in result.group_results" :key="g">
            <div class="group-title">Group {{ g }}</div>
            <div
              class="standing-row"
              v-for="(s, idx) in standings"
              :key="s.team"
              :class="{ qualified: idx < 2, third: idx === 2 }"
            >
              <span class="pos">{{ idx + 1 }}</span>
              <span class="sname">{{ s.team }}</span>
              <span class="pts">{{ s.points }}pt</span>
              <span class="gd">{{ s.gd >= 0 ? '+' : '' }}{{ s.gd }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../lib/api'
import BillingPlansLink from '../components/BillingPlansLink.vue'

const useSwarm = ref(false)
const loading = ref(false)
const result = ref(null)
const error = ref('')
const subscriptionRequired = ref(false)

async function runSim() {
  loading.value = true
  error.value = ''
  subscriptionRequired.value = false
  result.value = null
  try {
    const res = await api.post('/api/predictions/tournament', { use_swarm: useSwarm.value })
    result.value = res.data
  } catch (e) {
    error.value = e.response?.data?.error || e.message
    subscriptionRequired.value = e.response?.data?.code === 'subscription_required'
  } finally {
    loading.value = false
  }
}

const pct = v => (v * 100).toFixed(1) + '%'

const STAGE_LABELS = {
  round_of_32: 'R32',
  round_of_16: 'R16',
  quarter_final: 'QF',
  semi_final: 'SF',
  third_place: '3rd',
  final: 'Final',
}
const formatStage = s => STAGE_LABELS[s] || s
</script>

<style scoped>
.tournament-view { display: flex; flex-direction: column; gap: 28px; }
h1 { color: #e2b714; font-size: 26px; }
.subtitle { color: #8888aa; font-size: 14px; }

.controls { display: flex; align-items: center; gap: 24px; }
.toggle-label { display: flex; align-items: center; gap: 8px; color: #a0aec0; font-size: 14px; cursor: pointer; }
.btn-sim {
  background: linear-gradient(135deg, #e2b714, #f6d860);
  color: #0a0a1a; font-weight: 700; font-size: 15px;
  border: none; border-radius: 10px; padding: 12px 28px;
  cursor: pointer;
}
.btn-sim:disabled { opacity: 0.5; cursor: default; }

.error-box { background: #3d1a1a; border: 1px solid #c53030; border-radius: 8px; padding: 14px; color: #fc8181; }

.result-panel { display: flex; flex-direction: column; gap: 32px; }

/* Podium */
.podium { display: flex; align-items: flex-end; justify-content: center; gap: 12px; padding: 32px; background: #16213e; border-radius: 12px; }
.podium-spot { text-align: center; padding: 20px 28px; border-radius: 10px; background: #0f3460; }
.podium-spot.first { background: linear-gradient(135deg, #2d2000, #4a3800); border: 2px solid #e2b714; padding: 28px 36px; }
.podium-spot.second { background: #1a2a3a; }
.podium-spot.third { background: #1a1a2a; }
.medal { font-size: 32px; margin-bottom: 8px; }
.podium-team { font-size: 18px; font-weight: 700; color: #e0e0e0; }
.podium-spot.first .podium-team { font-size: 22px; color: #e2b714; }
.podium-label { font-size: 12px; color: #8888aa; margin-top: 4px; }
.champion-prob { font-size: 13px; color: #e2b714; margin-top: 6px; font-weight: 600; }

/* Bracket */
.bracket-section h2, .groups-section h2 { color: #e2b714; margin-bottom: 16px; font-size: 18px; }
.matches-list { display: flex; flex-direction: column; gap: 8px; }
.match-item {
  display: flex; align-items: center; gap: 12px;
  background: #16213e; border-radius: 8px; padding: 10px 16px;
  font-size: 13px;
}
.stage-badge { background: #0f3460; color: #a0c0ff; border-radius: 4px; padding: 2px 8px; font-weight: 600; min-width: 48px; text-align: center; }
.mt-home { flex: 1; text-align: right; color: #c0c0d0; }
.mt-away { flex: 1; text-align: left; color: #c0c0d0; }
.mt-home.winner, .mt-away.winner { color: #e2b714; font-weight: 700; }
.score { color: #e2b714; font-weight: 700; font-size: 16px; min-width: 40px; text-align: center; }
.probs { color: #6a6a8a; font-size: 11px; min-width: 180px; text-align: right; }

/* Groups */
.groups-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.group-block { background: #16213e; border: 1px solid #0f3460; border-radius: 8px; overflow: hidden; }
.group-title { background: #0f3460; color: #e2b714; font-weight: 700; padding: 8px 12px; font-size: 13px; }
.standing-row { display: flex; align-items: center; gap: 6px; padding: 7px 12px; border-bottom: 1px solid #0f1e35; font-size: 12px; }
.standing-row:last-child { border-bottom: none; }
.standing-row.qualified { background: rgba(46, 160, 67, 0.08); }
.standing-row.third { background: rgba(226, 183, 20, 0.06); }
.pos { color: #6a6a8a; min-width: 14px; }
.sname { flex: 1; color: #e0e0e0; }
.pts { color: #e2b714; font-weight: 600; }
.gd { color: #8888aa; min-width: 30px; text-align: right; }
</style>
