<template>
  <div class="prob-meter" role="img" :aria-label="meterSummary">
    <div class="meter-labels" aria-hidden="true">
      <span>{{ homeTeam }}</span>
      <span>{{ t('predictions.probabilityMeter.draw') }}</span>
      <span>{{ awayTeam }}</span>
    </div>

    <div class="meter-bar" aria-hidden="true">
      <div class="meter-segment segment-home" :class="{ dominant: outcome === 'home_win' }" :style="{ width: homeWidth }">
        <span v-if="homeWide">{{ percentage(homePct) }}</span>
      </div>
      <div class="meter-segment segment-draw" :class="{ dominant: outcome === 'draw' }" :style="{ width: drawWidth }">
        <span v-if="drawWide">{{ percentage(drawPct) }}</span>
      </div>
      <div class="meter-segment segment-away" :class="{ dominant: outcome === 'away_win' }" :style="{ width: awayWidth }">
        <span v-if="awayWide">{{ percentage(awayPct) }}</span>
      </div>
    </div>

    <div class="meter-percentages" aria-hidden="true">
      <strong :class="{ dominant: outcome === 'home_win' }">{{ percentage(homePct) }}</strong>
      <strong :class="{ dominant: outcome === 'draw' }">{{ percentage(drawPct) }}</strong>
      <strong :class="{ dominant: outcome === 'away_win' }">{{ percentage(awayPct) }}</strong>
    </div>

    <div class="sparkline-wrap" aria-hidden="true">
      <p>{{ t('predictions.probabilityMeter.convergence', { count: agentCount }) }}</p>
      <svg class="sparkline" viewBox="0 0 300 80" preserveAspectRatio="none">
        <line v-for="y in [20, 40, 60]" :key="y" x1="0" :y1="y" x2="300" :y2="y" class="grid-line" />
        <text x="2" y="18">75%</text>
        <text x="2" y="38">50%</text>
        <text x="2" y="58">25%</text>
        <polyline :points="pathPoints(homeSparkline)" class="sparkline-home" />
        <polyline :points="pathPoints(drawSparkline)" class="sparkline-draw" />
        <polyline :points="pathPoints(awaySparkline)" class="sparkline-away" />
        <circle :cx="294" :cy="toY(homePct)" r="2.5" class="sparkline-home-fill" />
        <circle :cx="294" :cy="toY(drawPct)" r="2" class="sparkline-draw-fill" />
        <circle :cx="294" :cy="toY(awayPct)" r="2.5" class="sparkline-away-fill" />
      </svg>
      <div class="sparkline-legend">
        <span><i class="legend-home"></i>{{ homeTeam }}</span>
        <span><i class="legend-draw"></i>{{ t('predictions.probabilityMeter.draw') }}</span>
        <span><i class="legend-away"></i>{{ awayTeam }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  homeTeam: { type: String, required: true },
  awayTeam: { type: String, required: true },
  homePct: { type: Number, required: true },
  drawPct: { type: Number, required: true },
  awayPct: { type: Number, required: true },
  outcome: { type: String, default: '' },
  agentCount: { type: Number, default: 7 },
  agentSeries: { type: Array, default: () => [] },
})

const { locale, t } = useI18n()
const minimumWidth = 0.04
const homeWidth = computed(() => `${Math.max(props.homePct, minimumWidth) * 100}%`)
const drawWidth = computed(() => `${Math.max(props.drawPct, minimumWidth) * 100}%`)
const awayWidth = computed(() => `${Math.max(props.awayPct, minimumWidth) * 100}%`)
const homeWide = computed(() => props.homePct > 0.15)
const drawWide = computed(() => props.drawPct > 0.15)
const awayWide = computed(() => props.awayPct > 0.15)

function percentage(value) {
  return new Intl.NumberFormat(locale.value, {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value)
}

const meterSummary = computed(() => t('predictions.probabilityMeter.summary', {
  homeTeam: props.homeTeam,
  home: percentage(props.homePct),
  draw: percentage(props.drawPct),
  awayTeam: props.awayTeam,
  away: percentage(props.awayPct),
}))

const stepCount = 8
const chartStart = 14
const chartWidth = 280

function buildSparkline(finalValue, series, key) {
  if (series.length > 0) {
    const divisor = Math.max(series.length - 1, 1)
    return series.map((entry, index) => ({
      x: chartStart + (index / divisor) * chartWidth,
      y: entry[key],
    }))
  }

  const points = []
  for (let index = 0; index < stepCount; index += 1) {
    const progress = index / (stepCount - 1)
    const eased = progress * progress * (3 - 2 * progress)
    const base = 0.333 + (finalValue - 0.333) * eased
    const wobble = Math.sin(index * 2.1 + finalValue * 10) * 0.03 * (1 - progress)
    points.push({
      x: chartStart + (index / (stepCount - 1)) * chartWidth,
      y: Math.max(0.01, Math.min(0.99, base + wobble)),
    })
  }
  points[points.length - 1].y = finalValue
  return points
}

const homeSparkline = computed(() => buildSparkline(props.homePct, props.agentSeries, 'home'))
const drawSparkline = computed(() => buildSparkline(props.drawPct, props.agentSeries, 'draw'))
const awaySparkline = computed(() => buildSparkline(props.awayPct, props.agentSeries, 'away'))
const toY = (probability) => 80 - (probability * 70 + 5)
const pathPoints = (series) => series.map((point) => `${point.x.toFixed(1)},${toY(point.y).toFixed(1)}`).join(' ')
</script>

<style scoped>
.prob-meter { display: flex; flex-direction: column; gap: var(--space-2); }
.meter-labels,
.meter-percentages { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.meter-labels { color: var(--color-text-muted); font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); }
.meter-labels span:nth-child(2),
.meter-percentages strong:nth-child(2) { text-align: center; }
.meter-labels span:last-child,
.meter-percentages strong:last-child { text-align: right; }
.meter-bar { display: flex; gap: var(--space-1); height: var(--control-height-md); overflow: hidden; }
.meter-segment { align-items: center; color: var(--color-accent-contrast); display: flex; font: var(--font-weight-bold) var(--font-size-xs) / 1 var(--font-family-data); justify-content: center; min-width: var(--space-2); transition: width var(--duration-slow) var(--easing-emphasized); }
.segment-home { background: var(--color-success); }
.segment-draw { background: var(--color-warning); }
.segment-away { background: var(--color-danger); }
.meter-segment.dominant { outline: var(--border-width-strong) solid var(--color-text); outline-offset: -3px; }
.meter-percentages strong { font: var(--font-weight-heavy) var(--font-size-xl) / var(--line-height-tight) var(--font-family-data); }
.meter-percentages strong:first-child { color: var(--color-success); }
.meter-percentages strong:nth-child(2) { color: var(--color-warning); }
.meter-percentages strong:last-child { color: var(--color-danger); }
.meter-percentages .dominant { color: var(--color-accent); }
.sparkline-wrap { background: var(--color-surface-inset); border: var(--border-width-thin) solid var(--color-border); margin-top: var(--space-2); padding: var(--space-3); }
.sparkline-wrap > p { color: var(--color-text-muted); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); margin: 0 0 var(--space-2); text-transform: uppercase; }
.sparkline { display: block; height: 5rem; width: 100%; }
.sparkline polyline { fill: none; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.5; }
.grid-line { stroke: var(--color-border); stroke-width: 0.5; }
.sparkline text { fill: var(--color-text-subtle); font-size: 7px; }
.sparkline-home { stroke: var(--color-success); }
.sparkline-draw { stroke: var(--color-warning); stroke-dasharray: 3 2; }
.sparkline-away { stroke: var(--color-danger); }
.sparkline-home-fill { fill: var(--color-success); }
.sparkline-draw-fill { fill: var(--color-warning); }
.sparkline-away-fill { fill: var(--color-danger); }
.sparkline-legend { color: var(--color-text-muted); display: flex; flex-wrap: wrap; font-size: var(--font-size-xs); gap: var(--space-4); margin-top: var(--space-2); }
.sparkline-legend i { display: inline-block; height: 3px; margin-right: var(--space-1); vertical-align: middle; width: var(--space-3); }
.legend-home { background: var(--color-success); }
.legend-draw { background: var(--color-warning); }
.legend-away { background: var(--color-danger); }
@media (prefers-reduced-motion: reduce) { .meter-segment { transition: none; } }
</style>
