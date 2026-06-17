<template>
  <div class="markets-view">

    <!-- ── Header ──────────────────────────────────────────────────────── -->
    <div class="page-header">
      <div>
        <h1>📈 Prediction Markets</h1>
        <p class="subtitle">
          SoccerOctopus swarm probabilities formatted as ready-to-list contracts
          for <a href="https://kalshi.com" target="_blank" rel="noopener">Kalshi</a> and
          <a href="https://polymarket.com" target="_blank" rel="noopener">Polymarket</a>.
          All prices are fair-value — no bookmaker margin applied.
        </p>
      </div>
      <div class="platform-badges">
        <span class="badge kalshi">Kalshi</span>
        <span class="badge polymarket">Polymarket</span>
      </div>
    </div>

    <!-- ── Mode tabs ────────────────────────────────────────────────────── -->
    <div class="mode-tabs">
      <button :class="['mode-tab', { active: mode === 'match' }]" @click="mode = 'match'">
        ⚽ Match Markets
      </button>
      <button :class="['mode-tab', { active: mode === 'tournament' }]" @click="mode = 'tournament'">
        🌍 Tournament Futures
      </button>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════ -->
    <!-- MATCH MARKETS                                                       -->
    <!-- ══════════════════════════════════════════════════════════════════ -->
    <template v-if="mode === 'match'">
      <div v-if="teamsError" class="error-box">⚠️ {{ teamsError }}</div>
      <div class="form-panel">
        <div class="selectors">
          <div class="select-group">
            <label>Home Team</label>
            <select v-model="homeTeam" :disabled="!teams.length">
              <option value="">{{ teams.length ? '— select —' : 'Loading…' }}</option>
              <option v-for="t in teams" :key="t.name" :value="t.name">
                {{ t.name }} (ELO {{ t.elo }})
              </option>
            </select>
          </div>
          <div class="vs-label">VS</div>
          <div class="select-group">
            <label>Away Team</label>
            <select v-model="awayTeam" :disabled="!teams.length">
              <option value="">{{ teams.length ? '— select —' : 'Loading…' }}</option>
              <option v-for="t in teams" :key="t.name" :value="t.name">
                {{ t.name }} (ELO {{ t.elo }})
              </option>
            </select>
          </div>
          <div class="select-group">
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
        </div>
        <button
          class="btn-run"
          :disabled="!homeTeam || !awayTeam || matchLoading"
          @click="runMatchMarkets"
        >
          {{ matchLoading ? '🐙 Running swarm…' : '📈 Generate Market Questions' }}
        </button>
      </div>

      <div v-if="matchError" class="error-box">{{ matchError }}</div>

      <!-- Match result summary -->
      <div v-if="matchData" class="match-summary">
        <div class="match-teams">
          <span class="team-name">{{ matchData.prediction_summary ? homeTeam : '' }}</span>
          <div class="prob-pills">
            <span class="pill home">H {{ pct(matchData.prediction_summary?.home_win_prob) }}</span>
            <span class="pill draw">D {{ pct(matchData.prediction_summary?.draw_prob) }}</span>
            <span class="pill away">A {{ pct(matchData.prediction_summary?.away_win_prob) }}</span>
          </div>
          <span class="team-name">{{ matchData.prediction_summary ? awayTeam : '' }}</span>
        </div>
        <div class="summary-meta">
          Most likely score: <strong>{{ matchData.prediction_summary?.most_likely_score }}</strong>
          &nbsp;·&nbsp;
          {{ matchData.total_questions }} market questions generated
        </div>
      </div>

      <!-- Prop type filter -->
      <div v-if="matchData" class="filter-bar">
        <button
          v-for="pt in matchPropTypes"
          :key="pt.key"
          :class="['filter-btn', { active: matchFilter === pt.key }]"
          @click="matchFilter = pt.key"
        >
          {{ pt.icon }} {{ pt.label }}
          <span class="count">{{ matchCountByType(pt.key) }}</span>
        </button>
      </div>

      <!-- Question cards -->
      <div v-if="matchData" class="questions-grid">
        <MarketCard
          v-for="q in filteredMatchQuestions"
          :key="q.question_id"
          :question="q"
        />
      </div>
    </template>

    <!-- ══════════════════════════════════════════════════════════════════ -->
    <!-- TOURNAMENT FUTURES                                                  -->
    <!-- ══════════════════════════════════════════════════════════════════ -->
    <template v-else>
      <div class="form-panel tournament-form">
        <p class="form-description">
          Simulates the full 104-match bracket via Monte Carlo and generates
          futures contracts for every team, group, and tournament milestone.
        </p>
        <button class="btn-run" :disabled="tourneyLoading" @click="runTournamentMarkets">
          {{ tourneyLoading ? '⏳ Simulating…' : '🌍 Generate Futures Markets' }}
        </button>
      </div>

      <div v-if="tourneyError" class="error-box">{{ tourneyError }}</div>

      <!-- Champion banner -->
      <div v-if="tourneyData" class="champion-banner">
        <div class="champion-info">
          <span class="trophy">🏆</span>
          <div>
            <div class="champion-name">{{ tourneyData.simulation.champion }}</div>
            <div class="champion-sub">Predicted Champion · {{ pct(tourneyData.simulation.champion_probability) }} final win prob</div>
          </div>
        </div>
        <div class="summary-meta">
          {{ tourneyData.total_questions }} futures contracts generated
        </div>
      </div>

      <!-- Section filters -->
      <div v-if="tourneyData" class="filter-bar">
        <button
          v-for="pt in tourneyPropTypes"
          :key="pt.key"
          :class="['filter-btn', { active: tourneyFilter === pt.key }]"
          @click="tourneyFilter = pt.key"
        >
          {{ pt.icon }} {{ pt.label }}
          <span class="count">{{ tourneyCountByType(pt.key) }}</span>
        </button>
      </div>

      <!-- Categorical winner market -->
      <div
        v-if="tourneyData && (tourneyFilter === 'all' || tourneyFilter === 'tournament_winner')"
        class="categorical-panel"
      >
        <div class="section-title">🏆 Tournament Winner Odds</div>
        <div class="winner-table">
          <div class="winner-row header-row">
            <span>Team</span>
            <span>Probability</span>
            <span>Kalshi YES price</span>
            <span>Polymarket YES</span>
            <span>Kalshi NO price</span>
          </div>
          <div
            v-for="o in categoricalOutcomes"
            :key="o.outcome"
            class="winner-row"
          >
            <span class="team-cell">{{ o.outcome }}</span>
            <span>
              <span class="mini-bar-bg">
                <span class="mini-bar-fill" :style="{ width: (o.probability * 100).toFixed(1) + '%' }"></span>
              </span>
              {{ pct(o.probability) }}
            </span>
            <span class="price-cell kalshi-price">{{ (o.probability * 100).toFixed(1) }}¢</span>
            <span class="price-cell poly-price">${{ o.probability.toFixed(4) }}</span>
            <span class="price-cell no-price">{{ (100 - o.probability * 100).toFixed(1) }}¢</span>
          </div>
        </div>
      </div>

      <!-- Binary question cards -->
      <div v-if="tourneyData" class="questions-grid">
        <MarketCard
          v-for="q in filteredTourneyQuestions"
          :key="q.question_id"
          :question="q"
        />
      </div>
    </template>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import MarketCard from '../components/MarketCard.vue'

// ── State ───────────────────────────────────────────────────────────────────
const mode         = ref('match')
const teams        = ref([])
const teamsError   = ref('')
const homeTeam     = ref('')
const awayTeam     = ref('')
const stage        = ref('group')

const matchLoading = ref(false)
const matchError   = ref('')
const matchData    = ref(null)
const matchFilter  = ref('all')

const tourneyLoading = ref(false)
const tourneyError   = ref('')
const tourneyData    = ref(null)
const tourneyFilter  = ref('all')

// ── Prop type definitions ────────────────────────────────────────────────────
const matchPropTypes = [
  { key: 'all',          icon: '🗂️',  label: 'All'          },
  { key: 'match_winner', icon: '🏆',  label: 'Match Winner' },
  { key: 'draw',         icon: '🤝',  label: 'Draw'         },
  { key: 'btts',         icon: '⚽',  label: 'BTTS'         },
  { key: 'over_under',   icon: '📈',  label: 'Over/Under'   },
  { key: 'clean_sheet',  icon: '🛡️', label: 'Clean Sheet'  },
  { key: 'penalties',    icon: '🥅',  label: 'Penalties'    },
  { key: 'correct_score',icon: '🎯', label: 'Score'        },
]
const tourneyPropTypes = [
  { key: 'all',               icon: '🗂️',  label: 'All'            },
  { key: 'tournament_winner', icon: '🏆',  label: 'Champion'       },
  { key: 'reach_stage',       icon: '📍',  label: 'Advancement'    },
  { key: 'group_winner',      icon: '🏅',  label: 'Group Winners'  },
  { key: 'confederation_win', icon: '🌐',  label: 'Confederation'  },
  { key: 'host_nation',       icon: '🏟️', label: 'Host Nation'    },
  { key: 'penalties',         icon: '🥅',  label: 'Penalties'      },
]

// ── Computed ─────────────────────────────────────────────────────────────────
const allMatchQuestions = computed(() =>
  (matchData.value?.questions ?? []).filter(q => q.market_type === 'binary')
)
const filteredMatchQuestions = computed(() =>
  matchFilter.value === 'all'
    ? allMatchQuestions.value
    : allMatchQuestions.value.filter(q => q.prop_type === matchFilter.value)
)
const matchCountByType = (key) =>
  key === 'all'
    ? allMatchQuestions.value.length
    : allMatchQuestions.value.filter(q => q.prop_type === key).length

const allTourneyQuestions = computed(() =>
  (tourneyData.value?.questions ?? []).filter(q => q.market_type === 'binary')
)
const filteredTourneyQuestions = computed(() =>
  tourneyFilter.value === 'all'
    ? allTourneyQuestions.value
    : allTourneyQuestions.value.filter(q => q.prop_type === tourneyFilter.value)
)
const tourneyCountByType = (key) =>
  key === 'all'
    ? allTourneyQuestions.value.length
    : allTourneyQuestions.value.filter(q => q.prop_type === key).length

const categoricalOutcomes = computed(() => {
  const cats = (tourneyData.value?.questions ?? []).find(q => q.market_type === 'categorical')
  return cats?.outcomes ?? []
})

// ── Methods ──────────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const res = await axios.get('/api/predictions/teams')
    teams.value = res.data.teams
    if (!teams.value?.length) {
      teamsError.value = 'Team list returned empty — backend may not have data.'
    }
  } catch (e) {
    teamsError.value = 'Could not load teams — is the backend running on port 5002?'
  }
})

async function runMatchMarkets() {
  matchLoading.value = true
  matchError.value = ''
  matchData.value = null
  matchFilter.value = 'all'
  try {
    const res = await axios.post('/api/markets/match', {
      home_team: homeTeam.value,
      away_team: awayTeam.value,
      stage: stage.value,
    })
    matchData.value = res.data
  } catch (e) {
    matchError.value = e.response?.data?.error ?? e.message
  } finally {
    matchLoading.value = false
  }
}

async function runTournamentMarkets() {
  tourneyLoading.value = true
  tourneyError.value = ''
  tourneyData.value = null
  tourneyFilter.value = 'all'
  try {
    const res = await axios.post('/api/markets/tournament')
    tourneyData.value = res.data
  } catch (e) {
    tourneyError.value = e.response?.data?.error ?? e.message
  } finally {
    tourneyLoading.value = false
  }
}

const pct = v => v != null ? (v * 100).toFixed(1) + '%' : '—'
</script>

<style scoped>
.markets-view { display: flex; flex-direction: column; gap: 22px; }

/* ── Header ─────────────────────────────────────────────────────────────── */
.page-header {
  display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;
}
h1 { color: #e2b714; font-size: 26px; margin-bottom: 6px; }
.subtitle { color: #8888aa; font-size: 14px; line-height: 1.6; max-width: 620px; }
.subtitle a { color: #a0c0ff; text-decoration: none; }
.subtitle a:hover { text-decoration: underline; }

.platform-badges { display: flex; gap: 8px; flex-shrink: 0; padding-top: 4px; }
.badge {
  padding: 5px 14px; border-radius: 20px;
  font-size: 13px; font-weight: 700; letter-spacing: 0.5px;
}
.badge.kalshi    { background: #0b4d2e; color: #4ade80; border: 1px solid #22c55e; }
.badge.polymarket { background: #0f2d5e; color: #60a5fa; border: 1px solid #3b82f6; }

/* ── Mode tabs ───────────────────────────────────────────────────────────── */
.mode-tabs { display: flex; gap: 0; border-bottom: 2px solid #0f3460; }
.mode-tab {
  padding: 10px 24px; background: transparent; border: none;
  color: #8888aa; font-size: 15px; font-weight: 600; cursor: pointer;
  border-bottom: 3px solid transparent; margin-bottom: -2px;
  transition: color 0.15s, border-color 0.15s;
}
.mode-tab.active { color: #e2b714; border-bottom-color: #e2b714; }
.mode-tab:hover:not(.active) { color: #c0c0d0; }

/* ── Form panel ──────────────────────────────────────────────────────────── */
.form-panel {
  background: #16213e; border: 1px solid #0f3460; border-radius: 12px;
  padding: 24px; display: flex; flex-direction: column; gap: 16px;
}
.selectors { display: grid; grid-template-columns: 1fr auto 1fr 1fr; align-items: end; gap: 16px; }
.select-group { display: flex; flex-direction: column; gap: 6px; }
.select-group label { color: #8888aa; font-size: 13px; }
select {
  background: #0a0a1a; color: #e0e0e0; border: 1px solid #0f3460;
  border-radius: 8px; padding: 9px 12px; font-size: 14px;
}
select:disabled { opacity: 0.5; cursor: not-allowed; }
option { background: #0a0a1a; color: #e0e0e0; }
.vs-label { color: #e2b714; font-size: 18px; font-weight: 700; padding-bottom: 9px; }
.tournament-form { flex-direction: row; align-items: center; justify-content: space-between; }
.form-description { color: #a0aec0; font-size: 14px; max-width: 520px; line-height: 1.5; }
.btn-run {
  background: linear-gradient(135deg, #e2b714, #f6d860);
  color: #0a0a1a; font-weight: 700; font-size: 15px;
  border: none; border-radius: 10px; padding: 12px 28px;
  cursor: pointer; white-space: nowrap; align-self: flex-end;
  transition: opacity 0.2s;
}
.btn-run:disabled { opacity: 0.5; cursor: default; }

/* ── Match summary ───────────────────────────────────────────────────────── */
.match-summary {
  background: #16213e; border: 1px solid #0f3460; border-radius: 10px;
  padding: 16px 20px; display: flex; align-items: center;
  justify-content: space-between; gap: 16px;
}
.match-teams { display: flex; align-items: center; gap: 12px; }
.team-name { font-size: 16px; font-weight: 700; color: #e0e0e0; }
.prob-pills { display: flex; gap: 6px; }
.pill {
  padding: 3px 10px; border-radius: 12px; font-size: 13px; font-weight: 600;
}
.pill.home  { background: #1a3a1a; color: #4ade80; }
.pill.draw  { background: #2a2a10; color: #fbbf24; }
.pill.away  { background: #3a1a1a; color: #f87171; }
.summary-meta { font-size: 13px; color: #8888aa; }
.summary-meta strong { color: #e2b714; }

/* ── Filter bar ──────────────────────────────────────────────────────────── */
.filter-bar { display: flex; flex-wrap: wrap; gap: 8px; }
.filter-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 14px; background: #16213e; border: 1px solid #0f3460;
  border-radius: 20px; color: #8888aa; font-size: 13px; cursor: pointer;
  transition: all 0.15s;
}
.filter-btn:hover { border-color: #e2b714; color: #e0e0e0; }
.filter-btn.active { background: #1e3a10; border-color: #e2b714; color: #e2b714; }
.count {
  background: #0f3460; color: #a0c0ff; border-radius: 10px;
  padding: 0 7px; font-size: 11px; font-weight: 700;
}
.filter-btn.active .count { background: #2a4a10; color: #e2b714; }

/* ── Champion banner ─────────────────────────────────────────────────────── */
.champion-banner {
  background: linear-gradient(135deg, #1e2a00 0%, #2d3800 100%);
  border: 1px solid #e2b714; border-radius: 12px;
  padding: 18px 24px; display: flex; align-items: center; justify-content: space-between;
}
.champion-info { display: flex; align-items: center; gap: 14px; }
.trophy { font-size: 36px; }
.champion-name { font-size: 22px; font-weight: 800; color: #e2b714; }
.champion-sub { font-size: 13px; color: #a0b040; margin-top: 2px; }

/* ── Categorical table ───────────────────────────────────────────────────── */
.categorical-panel {
  background: #16213e; border: 1px solid #0f3460; border-radius: 12px;
  overflow: hidden;
}
.section-title {
  padding: 14px 20px; background: #0f3460;
  color: #e2b714; font-weight: 700; font-size: 15px;
}
.winner-table { padding: 8px 0; }
.winner-row {
  display: grid; grid-template-columns: 2fr 2fr 1fr 1fr 1fr;
  padding: 10px 20px; font-size: 13px; align-items: center; gap: 8px;
  border-bottom: 1px solid #0f1e35;
}
.winner-row:last-child { border-bottom: none; }
.header-row { color: #6a6a8a; font-size: 12px; font-weight: 600; }
.team-cell { font-weight: 600; color: #e0e0e0; }
.mini-bar-bg {
  display: inline-block; width: 80px; height: 6px;
  background: #0f1e35; border-radius: 3px; overflow: hidden; vertical-align: middle;
  margin-right: 8px;
}
.mini-bar-fill { display: block; height: 100%; background: #e2b714; border-radius: 3px; }
.price-cell { font-weight: 700; }
.kalshi-price { color: #4ade80; }
.poly-price   { color: #60a5fa; }
.no-price     { color: #f87171; }

/* ── Questions grid ──────────────────────────────────────────────────────── */
.questions-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 14px;
}

/* ── Error ───────────────────────────────────────────────────────────────── */
.error-box {
  background: #3d1a1a; border: 1px solid #c53030;
  border-radius: 8px; padding: 14px; color: #fc8181; font-size: 14px;
}
</style>
