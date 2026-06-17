<template>
  <div class="prob-meter">
    <!-- Team labels row -->
    <div class="meter-labels">
      <span class="label-home">{{ homeTeam }}</span>
      <span class="label-draw">Draw</span>
      <span class="label-away">{{ awayTeam }}</span>
    </div>

    <!-- Segmented bar -->
    <div class="meter-bar" ref="barEl">
      <div
        class="seg seg-home"
        :style="{ width: homeW }"
        :class="{ dominant: outcome === 'home_win' }"
      >
        <span v-if="homeWide" class="seg-pct">{{ pct(homePct) }}</span>
      </div>
      <div
        class="seg seg-draw"
        :style="{ width: drawW }"
        :class="{ dominant: outcome === 'draw' }"
      >
        <span v-if="drawWide" class="seg-pct">{{ pct(drawPct) }}</span>
      </div>
      <div
        class="seg seg-away"
        :style="{ width: awayW }"
        :class="{ dominant: outcome === 'away_win' }"
      >
        <span v-if="awayWide" class="seg-pct">{{ pct(awayPct) }}</span>
      </div>
    </div>

    <!-- Percentage row below bar -->
    <div class="meter-pcts">
      <span class="pct-home" :class="{ dominant: outcome === 'home_win' }">{{ pct(homePct) }}</span>
      <span class="pct-draw" :class="{ dominant: outcome === 'draw' }">{{ pct(drawPct) }}</span>
      <span class="pct-away" :class="{ dominant: outcome === 'away_win' }">{{ pct(awayPct) }}</span>
    </div>

    <!-- Mini sparkline chart: swarm convergence simulation -->
    <div class="sparkline-wrap">
      <div class="sparkline-title">Swarm convergence · {{ agentCount }} agents</div>
      <svg class="sparkline" viewBox="0 0 300 80" preserveAspectRatio="none">
        <!-- Grid lines -->
        <line x1="0" y1="20" x2="300" y2="20" stroke="#1a2a4a" stroke-width="0.5"/>
        <line x1="0" y1="40" x2="300" y2="40" stroke="#1a2a4a" stroke-width="0.5"/>
        <line x1="0" y1="60" x2="300" y2="60" stroke="#1a2a4a" stroke-width="0.5"/>
        <!-- Y-axis labels -->
        <text x="2" y="18" fill="#3a4a6a" font-size="7">75%</text>
        <text x="2" y="38" fill="#3a4a6a" font-size="7">50%</text>
        <text x="2" y="58" fill="#3a4a6a" font-size="7">25%</text>

        <!-- Home win path -->
        <polyline
          :points="pathPoints(homeSparkline)"
          fill="none"
          stroke="#4ade80"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <!-- Draw path -->
        <polyline
          :points="pathPoints(drawSparkline)"
          fill="none"
          stroke="#fbbf24"
          stroke-width="1.2"
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-dasharray="3 2"
        />
        <!-- Away win path -->
        <polyline
          :points="pathPoints(awaySparkline)"
          fill="none"
          stroke="#f87171"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />

        <!-- End-point dots -->
        <circle :cx="294" :cy="toY(homePct)" r="2.5" fill="#4ade80"/>
        <circle :cx="294" :cy="toY(drawPct)" r="2" fill="#fbbf24"/>
        <circle :cx="294" :cy="toY(awayPct)" r="2.5" fill="#f87171"/>
      </svg>

      <!-- Legend -->
      <div class="sparkline-legend">
        <span><span class="dot home-dot"></span>{{ homeTeam }}</span>
        <span><span class="dot draw-dot dashed"></span>Draw</span>
        <span><span class="dot away-dot"></span>{{ awayTeam }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  homeTeam:  { type: String, required: true },
  awayTeam:  { type: String, required: true },
  homePct:   { type: Number, required: true },  // 0–1
  drawPct:   { type: Number, required: true },
  awayPct:   { type: Number, required: true },
  outcome:   { type: String, default: '' },
  agentCount:{ type: Number, default: 7 },
  // Optional: per-agent probabilities for sparkline (array of {home,draw,away})
  agentSeries: { type: Array, default: () => [] },
})

const pct = v => (v * 100).toFixed(1) + '%'

// Bar segment widths — clamp min to 4% so label is always readable
const MIN_W = 0.04
const homeW = computed(() => Math.max(props.homePct, MIN_W) * 100 + '%')
const drawW = computed(() => Math.max(props.drawPct, MIN_W) * 100 + '%')
const awayW = computed(() => Math.max(props.awayPct, MIN_W) * 100 + '%')

// Only show inline pct when segment is wide enough
const homeWide = computed(() => props.homePct > 0.15)
const drawWide = computed(() => props.drawPct > 0.15)
const awayWide = computed(() => props.awayPct > 0.15)

// Sparkline: simulate convergence from 33/33/33 → final values across N agents
// If agentSeries provided, use it; otherwise simulate
const STEPS = 8
const CHART_X0 = 14   // leave room for y-labels
const CHART_W  = 280

function buildSparkline(finalVal, agentSeries, key) {
  if (agentSeries.length > 0) {
    // Use actual per-agent running average
    return agentSeries.map((s, i) => ({
      x: CHART_X0 + (i / (agentSeries.length - 1)) * CHART_W,
      y: s[key],
    }))
  }
  // Simulate convergence: start at 0.333, drift toward finalVal
  const pts = []
  for (let i = 0; i < STEPS; i++) {
    const t = i / (STEPS - 1)
    // eased interpolation with small random wobble
    const eased = t * t * (3 - 2 * t)
    const base = 0.333 + (finalVal - 0.333) * eased
    // deterministic "wobble" based on position and finalVal
    const wobble = (Math.sin(i * 2.1 + finalVal * 10) * 0.03) * (1 - t)
    pts.push({
      x: CHART_X0 + (i / (STEPS - 1)) * CHART_W,
      y: Math.max(0.01, Math.min(0.99, base + wobble)),
    })
  }
  // Force last point to exact final value
  pts[pts.length - 1].y = finalVal
  return pts
}

const homeSparkline = computed(() =>
  buildSparkline(props.homePct, props.agentSeries, 'home')
)
const drawSparkline = computed(() =>
  buildSparkline(props.drawPct, props.agentSeries, 'draw')
)
const awaySparkline = computed(() =>
  buildSparkline(props.awayPct, props.agentSeries, 'away')
)

// SVG coordinate helpers
const toY = (prob) => 80 - (prob * 70 + 5)  // map 0–1 → y:75→5

function pathPoints(series) {
  return series.map(pt => `${pt.x.toFixed(1)},${toY(pt.y).toFixed(1)}`).join(' ')
}
</script>

<style scoped>
.prob-meter {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* ── Labels ────────────────────────────────────────────────────────────────── */
.meter-labels {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
  color: #a0aec0;
}
.label-draw { color: #6a6a8a; }

/* ── Segmented bar ──────────────────────────────────────────────────────────── */
.meter-bar {
  display: flex;
  height: 36px;
  border-radius: 8px;
  overflow: hidden;
  gap: 2px;
}
.seg {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 4px;
  position: relative;
  overflow: hidden;
}
.seg-home {
  background: linear-gradient(135deg, #166534, #16a34a);
}
.seg-draw {
  background: linear-gradient(135deg, #78350f, #b45309);
}
.seg-away {
  background: linear-gradient(135deg, #7f1d1d, #dc2626);
}

.seg.dominant {
  box-shadow: 0 0 0 2px #e2b714, inset 0 0 12px rgba(255,255,255,0.08);
}

.seg-pct {
  font-size: 13px;
  font-weight: 800;
  color: rgba(255,255,255,0.95);
  white-space: nowrap;
  text-shadow: 0 1px 3px rgba(0,0,0,0.5);
}

/* ── Percentage row ─────────────────────────────────────────────────────────── */
.meter-pcts {
  display: flex;
  justify-content: space-between;
  font-size: 22px;
  font-weight: 800;
  padding: 0 2px;
}
.pct-home { color: #4ade80; }
.pct-draw { color: #fbbf24; }
.pct-away { color: #f87171; }
.pct-home.dominant, .pct-draw.dominant, .pct-away.dominant {
  filter: drop-shadow(0 0 6px currentColor);
}

/* ── Sparkline ──────────────────────────────────────────────────────────────── */
.sparkline-wrap {
  background: #070e1c;
  border: 1px solid #0f1e35;
  border-radius: 8px;
  padding: 10px 12px 8px;
  margin-top: 4px;
}
.sparkline-title {
  font-size: 11px;
  color: #3a4a6a;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.sparkline {
  width: 100%;
  height: 80px;
  display: block;
}
.sparkline-legend {
  display: flex;
  gap: 18px;
  margin-top: 6px;
  font-size: 11px;
  color: #6a6a8a;
}
.dot {
  display: inline-block;
  width: 10px;
  height: 3px;
  border-radius: 2px;
  margin-right: 4px;
  vertical-align: middle;
}
.home-dot { background: #4ade80; }
.draw-dot  { background: #fbbf24; }
.away-dot  { background: #f87171; }
</style>
