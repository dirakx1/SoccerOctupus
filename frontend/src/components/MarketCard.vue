<template>
  <div class="market-card" :class="propClass">

    <!-- ── Top row: badge + copy ──────────────────────────────────────── -->
    <div class="card-top">
      <span class="prop-badge" :class="propClass">{{ propIcon }} {{ propLabel }}</span>
      <div class="top-actions">
        <span class="resolve-date">📅 {{ question.resolution?.date }}</span>
        <button class="copy-btn" :class="{ copied }" @click="copyTicker" :title="'Copy ticker: ' + question.question_id">
          {{ copied ? '✓' : '⎘' }}
        </button>
      </div>
    </div>

    <!-- ── Question text ──────────────────────────────────────────────── -->
    <div class="question-text">{{ question.question }}</div>

    <!-- ── Probability bars ───────────────────────────────────────────── -->
    <div class="prob-section">
      <div class="prob-row yes-row">
        <span class="prob-label yes-label">YES</span>
        <div class="bar-bg">
          <div class="bar-fill yes-fill" :style="{ width: yesPct }"></div>
        </div>
        <span class="prob-value yes-value">{{ yesPct }}</span>
      </div>
      <div class="prob-row no-row">
        <span class="prob-label no-label">NO</span>
        <div class="bar-bg">
          <div class="bar-fill no-fill" :style="{ width: noPct }"></div>
        </div>
        <span class="prob-value no-value">{{ noPct }}</span>
      </div>
    </div>

    <!-- ── Platform pricing ───────────────────────────────────────────── -->
    <div class="pricing-row">
      <div class="platform-price kalshi-block">
        <span class="platform-logo">⚡ Kalshi</span>
        <div class="price-pair">
          <span class="yes-price">YES {{ question.pricing?.kalshi_yes_cents?.toFixed(1) }}¢</span>
          <span class="sep">/</span>
          <span class="no-price">NO {{ question.pricing?.kalshi_no_cents?.toFixed(1) }}¢</span>
        </div>
      </div>
      <div class="platform-price poly-block">
        <span class="platform-logo">🔵 Polymarket</span>
        <div class="price-pair">
          <span class="yes-price">${{ question.pricing?.polymarket_yes_usdc?.toFixed(4) }}</span>
          <span class="sep">/</span>
          <span class="no-price">${{ question.pricing?.polymarket_no_usdc?.toFixed(4) }}</span>
        </div>
      </div>
    </div>

    <!-- ── Resolution criteria (collapsed) ───────────────────────────── -->
    <button class="criteria-toggle" @click="showCriteria = !showCriteria">
      {{ showCriteria ? '▲ Hide' : '▼ Resolution criteria' }}
    </button>
    <div v-if="showCriteria" class="criteria-text">
      {{ question.resolution?.criteria }}
    </div>

    <!-- ── Ticker ─────────────────────────────────────────────────────── -->
    <div class="ticker-row">
      <span class="ticker">{{ question.question_id }}</span>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({ question: { type: Object, required: true } })

const showCriteria = ref(false)
const copied       = ref(false)

const yesPct = computed(() =>
  ((props.question.yes_probability ?? 0) * 100).toFixed(1) + '%'
)
const noPct = computed(() =>
  ((props.question.no_probability ?? 0) * 100).toFixed(1) + '%'
)

// ── Prop type metadata ────────────────────────────────────────────────────
const PROP_META = {
  match_winner:       { label: 'Match Winner',   icon: '🏆', cls: 'winner'      },
  draw:               { label: 'Draw',            icon: '🤝', cls: 'draw'        },
  btts:               { label: 'Both Score',      icon: '⚽', cls: 'btts'        },
  over_under:         { label: 'Over/Under',      icon: '📈', cls: 'over'        },
  clean_sheet:        { label: 'Clean Sheet',     icon: '🛡️', cls: 'clean'      },
  penalties:          { label: 'Penalties',       icon: '🥅', cls: 'pens'        },
  correct_score:      { label: 'Exact Score',     icon: '🎯', cls: 'score'       },
  tournament_winner:  { label: 'Champion',        icon: '🏆', cls: 'winner'      },
  reach_stage:        { label: 'Advancement',     icon: '📍', cls: 'advance'     },
  group_winner:       { label: 'Group Winner',    icon: '🏅', cls: 'group'       },
  confederation_win:  { label: 'Confederation',   icon: '🌐', cls: 'conf'        },
  host_nation:        { label: 'Host Nation',     icon: '🏟️', cls: 'host'       },
}

const meta = computed(() => PROP_META[props.question.prop_type] ?? { label: props.question.prop_type, icon: '📊', cls: 'default' })
const propLabel = computed(() => meta.value.label)
const propIcon  = computed(() => meta.value.icon)
const propClass = computed(() => `type-${meta.value.cls}`)

async function copyTicker() {
  try {
    await navigator.clipboard.writeText(props.question.question_id)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1800)
  } catch { /* clipboard not available */ }
}
</script>

<style scoped>
.market-card {
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: border-color 0.15s, transform 0.15s;
}
.market-card:hover { transform: translateY(-2px); border-color: #2a4a7a; }

/* ── Type-based left accent ──────────────────────────────────────────────── */
.market-card.type-winner  { border-left: 3px solid #e2b714; }
.market-card.type-draw    { border-left: 3px solid #60a5fa; }
.market-card.type-btts    { border-left: 3px solid #4ade80; }
.market-card.type-over    { border-left: 3px solid #fb923c; }
.market-card.type-clean   { border-left: 3px solid #2dd4bf; }
.market-card.type-pens    { border-left: 3px solid #f87171; }
.market-card.type-score   { border-left: 3px solid #c084fc; }
.market-card.type-advance { border-left: 3px solid #60a5fa; }
.market-card.type-group   { border-left: 3px solid #4ade80; }
.market-card.type-conf    { border-left: 3px solid #2dd4bf; }
.market-card.type-host    { border-left: 3px solid #fb923c; }

/* ── Top row ─────────────────────────────────────────────────────────────── */
.card-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.top-actions { display: flex; align-items: center; gap: 8px; }

.prop-badge {
  font-size: 11px; font-weight: 700; letter-spacing: 0.4px;
  padding: 3px 10px; border-radius: 10px; white-space: nowrap;
}
.type-winner .prop-badge  { background: #2a2200; color: #e2b714; }
.type-draw   .prop-badge  { background: #0d1f3c; color: #93c5fd; }
.type-btts   .prop-badge  { background: #0a2210; color: #86efac; }
.type-over   .prop-badge  { background: #2a1200; color: #fdba74; }
.type-clean  .prop-badge  { background: #0a2820; color: #5eead4; }
.type-pens   .prop-badge  { background: #2a0a0a; color: #fca5a5; }
.type-score  .prop-badge  { background: #1e0a2a; color: #d8b4fe; }
.type-advance .prop-badge { background: #0d1f3c; color: #93c5fd; }
.type-group  .prop-badge  { background: #0a2210; color: #86efac; }
.type-conf   .prop-badge  { background: #0a2820; color: #5eead4; }
.type-host   .prop-badge  { background: #2a1200; color: #fdba74; }

.resolve-date { font-size: 11px; color: #6a6a8a; white-space: nowrap; }
.copy-btn {
  background: #0f3460; border: 1px solid #1e4a80;
  color: #a0c0ff; border-radius: 6px; padding: 3px 8px;
  font-size: 13px; cursor: pointer; transition: all 0.15s;
}
.copy-btn:hover { background: #1e4a80; }
.copy-btn.copied { background: #0a2210; color: #4ade80; border-color: #22c55e; }

/* ── Question text ───────────────────────────────────────────────────────── */
.question-text {
  font-size: 14px; font-weight: 600; color: #e0e0e0;
  line-height: 1.45; min-height: 40px;
}

/* ── Probability bars ────────────────────────────────────────────────────── */
.prob-section { display: flex; flex-direction: column; gap: 6px; }
.prob-row { display: flex; align-items: center; gap: 8px; }
.prob-label { font-size: 11px; font-weight: 700; min-width: 28px; }
.yes-label { color: #4ade80; }
.no-label  { color: #f87171; }
.bar-bg {
  flex: 1; height: 8px; background: #0a0f1a;
  border-radius: 4px; overflow: hidden;
}
.bar-fill { height: 100%; border-radius: 4px; transition: width 0.5s; }
.yes-fill { background: linear-gradient(90deg, #15803d, #4ade80); }
.no-fill  { background: linear-gradient(90deg, #991b1b, #f87171); }
.prob-value { font-size: 13px; font-weight: 700; min-width: 44px; text-align: right; }
.yes-value { color: #4ade80; }
.no-value  { color: #f87171; }

/* ── Platform pricing ────────────────────────────────────────────────────── */
.pricing-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.platform-price {
  border-radius: 8px; padding: 8px 10px;
  display: flex; flex-direction: column; gap: 4px;
}
.kalshi-block { background: #061a0f; border: 1px solid #166534; }
.poly-block   { background: #061220; border: 1px solid #1d4ed8; }
.platform-logo { font-size: 11px; font-weight: 700; }
.kalshi-block .platform-logo { color: #4ade80; }
.poly-block   .platform-logo { color: #60a5fa; }
.price-pair { display: flex; align-items: center; gap: 4px; font-size: 13px; font-weight: 700; }
.yes-price { color: #e0e0e0; }
.no-price  { color: #8888aa; }
.sep { color: #4a4a6a; }

/* ── Criteria toggle ─────────────────────────────────────────────────────── */
.criteria-toggle {
  background: none; border: none; color: #6a6a8a;
  font-size: 11px; cursor: pointer; text-align: left; padding: 0;
  transition: color 0.15s;
}
.criteria-toggle:hover { color: #a0aec0; }
.criteria-text {
  font-size: 12px; color: #8888aa; line-height: 1.5;
  background: #0f1a2e; border-radius: 6px; padding: 10px 12px;
}

/* ── Ticker ──────────────────────────────────────────────────────────────── */
.ticker-row { border-top: 1px solid #0f1e35; padding-top: 8px; }
.ticker {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 10px; color: #4a4a6a; letter-spacing: 0.5px;
}
</style>
