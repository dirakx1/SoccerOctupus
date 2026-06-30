<template>
  <div class="tournament-view">
    <h1>🌍 WC 2026 Full Tournament</h1>
    <p class="subtitle">Browse real group-stage results or simulate the full bracket.</p>

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab-btn" :class="{ active: activeTab === 'groups' }" @click="activeTab = 'groups'">
        🏟 Group Stage
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'rounds' }" @click="activeTab = 'rounds'">
        ⚔️ Rounds
      </button>
    </div>

    <!-- ── GROUP STAGE TAB ──────────────────────────────────────────────────── -->
    <template v-if="activeTab === 'groups'">
      <div v-if="liveLoading" class="loading">Loading live results…</div>
      <div v-else-if="liveError" class="error-box">{{ liveError }}</div>
      <template v-else>
        <p class="live-meta">
          {{ liveData?.total ?? 0 }} match{{ liveData?.total !== 1 ? 'es' : '' }} played · sourced from ESPN
        </p>

        <!-- Standings grid -->
        <div class="groups-grid" v-if="liveData?.standings">
          <div class="group-block" v-for="(teams, g) in liveData.standings" :key="g">
            <div class="group-title">Group {{ g }}</div>
            <div
              class="standing-row"
              v-for="(s, idx) in teams"
              :key="s.team"
              :class="{ qualified: idx < 2, third: idx === 2 }"
            >
              <span class="pos">{{ idx + 1 }}</span>
              <span class="sname">{{ s.team }}</span>
              <span class="standing-stats">{{ s.played }}G {{ s.won }}W {{ s.drawn }}D {{ s.lost }}L</span>
              <span class="pts">{{ s.points }}pt</span>
              <span class="gd">{{ s.gd >= 0 ? '+' : '' }}{{ s.gd }}</span>
            </div>
          </div>
        </div>

        <!-- Match results list -->
        <div class="section-header">Results</div>
        <div v-if="liveData?.matches?.length" class="matches-list">
          <div class="match-item" v-for="(m, i) in liveData.matches" :key="i">
            <span class="stage-badge">Grp {{ m.group }}</span>
            <span class="mt-home" :class="{ winner: m.home_goals > m.away_goals }">{{ m.home }}</span>
            <span class="score">{{ m.home_goals }}–{{ m.away_goals }}</span>
            <span class="mt-away" :class="{ winner: m.away_goals > m.home_goals }">{{ m.away }}</span>
            <span class="match-date">{{ m.date }}</span>
          </div>
        </div>
        <p v-else class="no-matches">No matches played yet.</p>
      </template>
    </template>

    <!-- ── ROUNDS TAB ──────────────────────────────────────────────────────── -->
    <template v-if="activeTab === 'rounds'">
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
        <BillingStatusNotice
          v-if="billingHealth?.requires_attention"
          compact
          :health="billingHealth"
          :loading="billingActionLoading"
          @action="openBillingRecovery('/tournament', billingHealth)"
        />
        <BillingPlansLink v-else-if="subscriptionRequired" />
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

        <!-- Knockout rounds -->
        <div v-for="round in knockoutRounds" :key="round.stage" class="round-section">
          <div class="round-header">
            <span class="round-label">{{ round.label }}</span>
            <span class="round-count">{{ round.matches.length }} match{{ round.matches.length !== 1 ? 'es' : '' }}</span>
          </div>
          <div class="matches-list">
            <div class="match-item" v-for="m in round.matches" :key="m.prediction_id">
              <span class="mt-home" :class="{ winner: m.outcome === 'home_win' }">{{ m.home_team }}</span>
              <span class="score">{{ m.most_likely_score }}</span>
              <span class="mt-away" :class="{ winner: m.outcome === 'away_win' }">{{ m.away_team }}</span>
              <span class="probs">H {{ pct(m.home_win_prob) }} / D {{ pct(m.draw_prob) }} / A {{ pct(m.away_win_prob) }}</span>
            </div>
          </div>
        </div>
      </div>

      <p v-else-if="!loading && !error" class="hint">Run a simulation to see the knockout bracket.</p>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../lib/api'
import BillingStatusNotice from '../components/BillingStatusNotice.vue'
import BillingPlansLink from '../components/BillingPlansLink.vue'
import { useBillingStatus } from '../composables/useBillingStatus'

// ── Tabs ──────────────────────────────────────────────────────────────────────
const activeTab = ref('groups')

// ── Live group-stage results ──────────────────────────────────────────────────
const liveData = ref(null)
const liveLoading = ref(true)
const liveError = ref('')

onMounted(async () => {
  try {
    const res = await api.get('/api/predictions/live-results')
    liveData.value = res.data
  } catch (e) {
    liveError.value = 'Could not load live results — is the backend running?'
  } finally {
    liveLoading.value = false
  }
})

// ── Simulation ────────────────────────────────────────────────────────────────
const useSwarm = ref(false)
const loading = ref(false)
const result = ref(null)
const error = ref('')
const subscriptionRequired = ref(false)
const billingHealth = ref(null)
const {
  actionLoading: billingActionLoading,
  openBillingRecovery,
} = useBillingStatus()

async function runSim() {
  loading.value = true
  error.value = ''
  subscriptionRequired.value = false
  billingHealth.value = null
  result.value = null
  try {
    const res = await api.post('/api/predictions/tournament', { use_swarm: useSwarm.value })
    result.value = res.data
  } catch (e) {
    error.value = e.response?.data?.error || e.message
    billingHealth.value = e.response?.data?.billing_health || null
    subscriptionRequired.value = ['subscription_required', 'billing_payment_required', 'feature_limit_reached'].includes(e.response?.data?.code)
  } finally {
    loading.value = false
  }
}

const pct = v => (v * 100).toFixed(1) + '%'

// ── Knockout bracket organized by round ───────────────────────────────────────
const ROUND_ORDER = [
  { stage: 'round_of_32',   label: 'Round of 32' },
  { stage: 'round_of_16',   label: 'Round of 16' },
  { stage: 'quarter_final', label: 'Quarter Finals' },
  { stage: 'semi_final',    label: 'Semi Finals' },
  { stage: 'third_place',   label: '3rd Place Play-off' },
  { stage: 'final',         label: 'Final' },
]

const knockoutRounds = computed(() => {
  if (!result.value) return []
  const byStage = {}
  for (const m of result.value.knockout_matches) {
    if (!byStage[m.stage]) byStage[m.stage] = []
    byStage[m.stage].push(m)
  }
  return ROUND_ORDER
    .filter(r => byStage[r.stage]?.length)
    .map(r => ({ ...r, matches: byStage[r.stage] }))
})
</script>

<style scoped>
.tournament-view { display: flex; flex-direction: column; gap: 24px; }
h1 { color: #e2b714; font-size: 26px; }
.subtitle { color: #8888aa; font-size: 14px; margin-top: -16px; }

/* ── Tabs ──────────────────────────────────────────────────────────────────── */
.tabs {
  display: flex;
  gap: 8px;
  border-bottom: 2px solid #0f3460;
  padding-bottom: 0;
}
.tab-btn {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: #8888aa;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: -2px;
  padding: 10px 20px;
  transition: color 0.2s, border-color 0.2s;
}
.tab-btn:hover { color: #e0e0e0; }
.tab-btn.active { color: #e2b714; border-bottom-color: #e2b714; }

/* ── Group Stage tab ───────────────────────────────────────────────────────── */
.loading { color: #a0aec0; }
.live-meta { color: #6a6a8a; font-size: 12px; margin-top: -8px; }

.groups-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.group-block { background: #16213e; border: 1px solid #0f3460; border-radius: 8px; overflow: hidden; }
.group-title { background: #0f3460; color: #e2b714; font-weight: 700; padding: 8px 12px; font-size: 13px; }
.standing-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border-bottom: 1px solid #0f1e35;
  font-size: 12px;
}
.standing-row:last-child { border-bottom: none; }
.standing-row.qualified { background: rgba(46, 160, 67, 0.08); }
.standing-row.third { background: rgba(226, 183, 20, 0.06); }
.pos { color: #6a6a8a; min-width: 14px; }
.sname { flex: 1; color: #e0e0e0; }
.standing-stats { color: #4a5a7a; font-size: 10px; white-space: nowrap; }
.pts { color: #e2b714; font-weight: 600; }
.gd { color: #8888aa; min-width: 30px; text-align: right; }

.section-header {
  color: #e2b714;
  font-size: 16px;
  font-weight: 700;
  border-left: 3px solid #e2b714;
  padding-left: 10px;
}

.matches-list { display: flex; flex-direction: column; gap: 6px; }
.match-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #16213e;
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 13px;
}
.stage-badge {
  background: #0f3460;
  color: #a0c0ff;
  border-radius: 4px;
  padding: 2px 8px;
  font-weight: 600;
  min-width: 52px;
  text-align: center;
  font-size: 11px;
  flex-shrink: 0;
}
.mt-home { flex: 1; text-align: right; color: #c0c0d0; }
.mt-away { flex: 1; text-align: left; color: #c0c0d0; }
.mt-home.winner, .mt-away.winner { color: #e2b714; font-weight: 700; }
.score { color: #e2b714; font-weight: 700; font-size: 16px; min-width: 40px; text-align: center; flex-shrink: 0; }
.match-date { color: #4a5a7a; font-size: 11px; min-width: 80px; text-align: right; flex-shrink: 0; }
.no-matches { color: #6a6a8a; font-size: 14px; }

/* ── Rounds tab ────────────────────────────────────────────────────────────── */
.controls { display: flex; align-items: center; gap: 24px; }
.toggle-label { display: flex; align-items: center; gap: 8px; color: #a0aec0; font-size: 14px; cursor: pointer; }
.btn-sim {
  background: linear-gradient(135deg, #e2b714, #f6d860);
  color: #0a0a1a;
  font-weight: 700;
  font-size: 15px;
  border: none;
  border-radius: 10px;
  padding: 12px 28px;
  cursor: pointer;
}
.btn-sim:disabled { opacity: 0.5; cursor: default; }

.error-box { background: #3d1a1a; border: 1px solid #c53030; border-radius: 8px; padding: 14px; color: #fc8181; }
.hint { color: #6a6a8a; font-size: 14px; }

.result-panel { display: flex; flex-direction: column; gap: 28px; }

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

/* Rounds */
.round-section { display: flex; flex-direction: column; gap: 8px; }
.round-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-left: 3px solid #e2b714;
  padding-left: 10px;
}
.round-label { color: #e2b714; font-size: 16px; font-weight: 700; }
.round-count { color: #6a6a8a; font-size: 12px; }

.probs { color: #6a6a8a; font-size: 11px; min-width: 180px; text-align: right; flex-shrink: 0; }

/* ── Responsive ────────────────────────────────────────────────────────────── */
@media (max-width: 900px) {
  .groups-grid { grid-template-columns: repeat(2, 1fr); }
  .standing-stats { display: none; }
}
@media (max-width: 768px) {
  .controls { flex-direction: column; align-items: flex-start; gap: 12px; }
  .btn-sim { width: 100%; }
  .podium { flex-direction: column; align-items: center; gap: 12px; padding: 20px 12px; }
  .podium-spot { width: 100%; max-width: 280px; }
  .match-item { flex-wrap: wrap; gap: 6px; }
  .probs { min-width: unset; width: 100%; text-align: left; }
  .match-date { min-width: unset; }
  .mt-home { text-align: left; }
  h1 { font-size: 20px; }
}
@media (max-width: 480px) {
  .groups-grid { grid-template-columns: 1fr; }
  .tab-btn { padding: 8px 12px; font-size: 13px; }
}
</style>
