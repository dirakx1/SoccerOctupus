<template>
  <div class="graph-panel">
    <!-- Controls -->
    <header class="graph-header">
      <div>
        <h2>{{ t('swarmLab.graph.heading') }}</h2>
        <p>{{ t('swarmLab.graph.description') }}</p>
      </div>
      <span
        v-if="mode"
        class="mode-badge"
        :class="mode === 'zep_graph' ? 'badge-live' : 'badge-static'"
      >
        {{ mode === 'zep_graph' ? t('swarmLab.graph.modeLive') : t('swarmLab.graph.modeStatic') }}
      </span>
    </header>

    <div class="graph-controls">
      <div class="search-row">
        <input
          v-model="teamSearch"
          type="search"
          class="search-input"
          :placeholder="t('swarmLab.graph.search')"
          :aria-label="t('swarmLab.graph.search')"
          @keydown.enter="applyFilter"
        />
        <button type="button" class="btn-filter" @click="applyFilter">
          <Search :size="14" aria-hidden="true" />
          <span>{{ t('swarmLab.graph.searchButton') }}</span>
        </button>
        <button v-if="activeFilter" type="button" class="btn-clear" @click="clearFilter">
          <X :size="14" aria-hidden="true" />
          <span>{{ t('swarmLab.graph.clearFilter') }}</span>
        </button>
      </div>
      <div class="graph-stats" aria-live="polite">
        <span>{{ t('swarmLab.graph.nodes', { count: displayNodes.length }) }}</span>
        <span>·</span>
        <span>{{ t('swarmLab.graph.edges', { count: displayLinks.length }) }}</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="state-panel graph-loading" aria-busy="true">
      <LoaderCircle :size="22" class="spin" aria-hidden="true" />
      <p>{{ t('swarmLab.graph.loading') }}</p>
    </div>

    <!-- Error -->
    <div v-else-if="loadError" class="state-panel state-error" role="alert">
      <AlertTriangle :size="22" aria-hidden="true" />
      <div>
        <h3>{{ t('swarmLab.graph.errorLoad') }}</h3>
        <button type="button" @click="load()">
          <RotateCcw :size="14" aria-hidden="true" />
          {{ t('swarmLab.graph.retry') }}
        </button>
      </div>
    </div>

    <!-- Empty after filter -->
    <div v-else-if="displayNodes.length === 0 && activeFilter" class="state-panel" role="status">
      <Network :size="22" aria-hidden="true" />
      <p>{{ t('swarmLab.graph.noResults') }}</p>
    </div>

    <!-- Graph canvas -->
    <div
      v-else
      ref="canvasWrap"
      class="graph-canvas-wrap"
      :aria-label="t('swarmLab.graph.heading')"
    >
      <svg
        ref="svgEl"
        class="graph-svg"
        :viewBox="`0 0 ${W} ${H}`"
        preserveAspectRatio="xMidYMid meet"
        @wheel.prevent="onWheel"
        @mousedown="onBgMousedown"
        @mousemove="onMousemove"
        @mouseup="onMouseup"
        @mouseleave="onMouseup"
      >
        <g :transform="svgTransform">
          <!-- Edge layer -->
          <line
            v-for="(link, i) in displayLinks"
            :key="i"
            class="graph-edge"
            :x1="link.source.x"
            :y1="link.source.y"
            :x2="link.target.x"
            :y2="link.target.y"
          />

          <!-- Node layer -->
          <g
            v-for="node in displayNodes"
            :key="node.id"
            class="graph-node"
            :transform="`translate(${node.x ?? 0},${node.y ?? 0})`"
            :aria-label="node.label"
            @mousedown.stop="onNodeMousedown(node, $event)"
            @mouseenter="hoverNode = node"
            @mouseleave="hoverNode = null"
          >
            <circle
              :r="nodeRadius(node)"
              :fill="nodeColor(node)"
              :stroke="hoverNode?.id === node.id ? 'var(--color-accent)' : nodeStroke(node)"
              stroke-width="1.5"
            />
            <text
              v-if="nodeRadius(node) >= 14 || hoverNode?.id === node.id"
              class="node-label"
              dy="0.35em"
              text-anchor="middle"
            >{{ shortLabel(node.label) }}</text>
          </g>
        </g>
      </svg>

      <!-- Floating tooltip -->
      <div
        v-if="hoverNode"
        class="graph-tooltip"
        :style="tooltipStyle"
        role="tooltip"
        aria-live="polite"
      >
        <strong>{{ hoverNode.label }}</strong>
        <span class="tooltip-type">{{ hoverNode.type }}</span>
      </div>

      <p class="drag-hint">{{ t('swarmLab.graph.dragHint') }}</p>
    </div>

    <!-- Legend -->
    <div v-if="!loading && !loadError && displayNodes.length > 0" class="graph-legend" :aria-label="t('swarmLab.graph.legend')">
      <span v-for="(color, type) in NODE_COLORS" :key="type" class="legend-item">
        <span class="legend-swatch" :style="{ background: color }"></span>
        {{ type }}
      </span>
    </div>
  </div>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  shallowRef,
  watch,
} from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertTriangle, LoaderCircle, Network, RotateCcw, Search, X } from '@lucide/vue'
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
} from 'd3-force'
import { api } from '../../lib/api'

const { t } = useI18n()

// Canvas dimensions (intrinsic SVG coordinate space)
const W = 900
const H = 580

const NODE_COLORS = {
  team: 'var(--color-accent)',
  group: '#6b7280',
  match: '#a16207',
  player: '#0ea5e9',
  coach: '#7c3aed',
}

// State
const loading = ref(true)
const loadError = ref(false)
const teamSearch = ref('')
const activeFilter = ref('')
const mode = ref('')
const displayNodes = shallowRef([])
const displayLinks = shallowRef([])
const hoverNode = ref(null)

// Zoom / pan
const scale = ref(1)
const tx = ref(0)
const ty = ref(0)
const svgTransform = computed(() => `translate(${tx.value},${ty.value}) scale(${scale.value})`)

// Interaction refs
const svgEl = ref(null)
const canvasWrap = ref(null)
const draggingNode = ref(null)
const panning = ref(false)
const panStart = ref({ x: 0, y: 0, tx: 0, ty: 0 })
const tooltipStyle = ref({})

// d3 simulation (not reactive — mutated in place)
let simulation = null
let simNodes = []
let simLinks = []
let tickCount = 0

function nodeRadius(node) {
  if (node.type === 'group') return 20
  if (node.type === 'team') return 14
  return 8
}

function nodeColor(node) {
  return NODE_COLORS[node.type] || '#94a3b8'
}

function nodeStroke(node) {
  return node.type === 'team' ? 'var(--color-accent)' : 'var(--color-border)'
}

function shortLabel(label) {
  if (!label) return ''
  return label.length > 12 ? label.slice(0, 11) + '…' : label
}

// Map screen coords → SVG graph coords
function toGraphCoords(clientX, clientY) {
  const rect = svgEl.value.getBoundingClientRect()
  const svgX = ((clientX - rect.left) / rect.width) * W
  const svgY = ((clientY - rect.top) / rect.height) * H
  return {
    x: (svgX - tx.value) / scale.value,
    y: (svgY - ty.value) / scale.value,
  }
}

function startSimulation(nodes, links) {
  if (simulation) simulation.stop()

  // Seed positions in a circle so nodes don't start at origin
  const cx = W / 2
  const cy = H / 2
  nodes.forEach((n, i) => {
    if (n.x === undefined) {
      const angle = (i / nodes.length) * 2 * Math.PI
      n.x = cx + Math.cos(angle) * 200
      n.y = cy + Math.sin(angle) * 200
    }
  })

  simNodes = nodes
  simLinks = links

  simulation = forceSimulation(simNodes)
    .force('link', forceLink(simLinks).id((d) => d.id).distance(70).strength(0.6))
    .force('charge', forceManyBody().strength(-280))
    .force('center', forceCenter(cx, cy).strength(0.05))
    .force('collide', forceCollide().radius((d) => nodeRadius(d) + 4))
    .alphaDecay(0.03)
    .on('tick', () => {
      tickCount++
      if (tickCount % 2 !== 0) return
      // Trigger Vue re-render by replacing shallowRef value with same array
      // (shallowRef tracks object identity, so we swap)
      displayNodes.value = [...simNodes]
      displayLinks.value = [...simLinks]
    })
}

async function load(team) {
  loading.value = true
  loadError.value = false
  hoverNode.value = null
  try {
    const url = team ? `/api/predictions/graph/data?team=${encodeURIComponent(team)}` : '/api/predictions/graph/data'
    const res = await api.get(url)
    const data = res.data
    mode.value = data.mode || ''

    // Build node/link arrays for d3 (plain objects, not proxied)
    const nodes = (data.nodes || []).map((n) => ({ ...n }))
    const linkIndex = new Set(nodes.map((n) => n.id))
    const links = (data.edges || [])
      .filter((e) => linkIndex.has(e.source) && linkIndex.has(e.target))
      .map((e) => ({ source: e.source, target: e.target, name: e.name }))

    startSimulation(nodes, links)

    // Reset viewport
    scale.value = 1
    tx.value = 0
    ty.value = 0
    tickCount = 0
  } catch {
    loadError.value = true
    displayNodes.value = []
    displayLinks.value = []
  } finally {
    loading.value = false
  }
}

function applyFilter() {
  const q = teamSearch.value.trim()
  activeFilter.value = q
  load(q || undefined)
}

function clearFilter() {
  teamSearch.value = ''
  activeFilter.value = ''
  load()
}

// Zoom on scroll
function onWheel(event) {
  const factor = event.deltaY < 0 ? 1.12 : 0.88
  const newScale = Math.min(5, Math.max(0.15, scale.value * factor))
  // Zoom toward mouse cursor
  const rect = svgEl.value.getBoundingClientRect()
  const mx = ((event.clientX - rect.left) / rect.width) * W
  const my = ((event.clientY - rect.top) / rect.height) * H
  tx.value = mx - (mx - tx.value) * (newScale / scale.value)
  ty.value = my - (my - ty.value) * (newScale / scale.value)
  scale.value = newScale
}

// Pan (background drag)
function onBgMousedown(event) {
  if (event.button !== 0) return
  panning.value = true
  panStart.value = { x: event.clientX, y: event.clientY, tx: tx.value, ty: ty.value }
}

// Node drag
function onNodeMousedown(node, event) {
  if (event.button !== 0) return
  draggingNode.value = node
  // Fix node position so force doesn't push it
  node.fx = node.x
  node.fy = node.y
  simulation?.alphaTarget(0.2).restart()
}

function onMousemove(event) {
  // Update tooltip position
  if (hoverNode.value) {
    const wrap = canvasWrap.value?.getBoundingClientRect()
    if (wrap) {
      tooltipStyle.value = {
        left: `${event.clientX - wrap.left + 14}px`,
        top: `${event.clientY - wrap.top - 10}px`,
      }
    }
  }

  if (draggingNode.value) {
    const coords = toGraphCoords(event.clientX, event.clientY)
    draggingNode.value.fx = coords.x
    draggingNode.value.fy = coords.y
    return
  }

  if (panning.value) {
    const rect = svgEl.value.getBoundingClientRect()
    const scaleX = W / rect.width
    const scaleY = H / rect.height
    tx.value = panStart.value.tx + (event.clientX - panStart.value.x) * scaleX
    ty.value = panStart.value.ty + (event.clientY - panStart.value.y) * scaleY
  }
}

function onMouseup() {
  if (draggingNode.value) {
    draggingNode.value.fx = null
    draggingNode.value.fy = null
    draggingNode.value = null
    simulation?.alphaTarget(0)
  }
  panning.value = false
}

onMounted(() => load())
onBeforeUnmount(() => simulation?.stop())
</script>

<style scoped>
.graph-panel { display: flex; flex-direction: column; gap: var(--space-5); }
.graph-header { align-items: flex-start; display: flex; gap: var(--space-4); justify-content: space-between; }
.graph-header h2 { font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0 0 var(--space-1); }
.graph-header p { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-relaxed); margin: 0; max-width: 60ch; }
.mode-badge { align-self: flex-start; border: var(--border-width-thin) solid var(--color-border); flex-shrink: 0; font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); padding: var(--space-1) var(--space-2); text-transform: uppercase; white-space: nowrap; }
.badge-live { border-color: var(--color-success); color: var(--color-success); }
.badge-static { color: var(--color-text-subtle); }
.graph-controls { align-items: center; display: flex; flex-wrap: wrap; gap: var(--space-4); justify-content: space-between; }
.search-row { align-items: center; display: flex; gap: var(--space-2); flex-wrap: wrap; }
.search-input { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); color: var(--color-text); font-size: var(--font-size-sm); min-height: var(--control-height-md); min-width: 18rem; padding: 0 var(--space-3); }
.search-input:focus { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 2px; }
.btn-filter { align-items: center; background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; display: inline-flex; font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); gap: var(--space-1); min-height: var(--control-height-md); padding: 0 var(--space-3); }
.btn-clear { align-items: center; background: transparent; border: var(--border-width-thin) solid var(--color-border); color: var(--color-text-muted); cursor: pointer; display: inline-flex; font-size: var(--font-size-sm); gap: var(--space-1); min-height: var(--control-height-md); padding: 0 var(--space-3); }
.btn-filter:focus-visible, .btn-clear:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 2px; }
.graph-stats { color: var(--color-text-subtle); display: flex; font: var(--font-weight-bold) var(--font-size-xs) / 1 var(--font-family-data); gap: var(--space-2); white-space: nowrap; }
.graph-canvas-wrap { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); position: relative; user-select: none; }
.graph-svg { cursor: grab; display: block; height: auto; max-height: 68vh; width: 100%; }
.graph-svg:active { cursor: grabbing; }
.graph-edge { pointer-events: none; stroke: var(--color-border); stroke-width: 1; }
.graph-node { cursor: grab; }
.graph-node:active { cursor: grabbing; }
.node-label { fill: var(--color-accent-contrast, #fff); font: var(--font-weight-semibold) 9px / 1 var(--font-family-data); pointer-events: none; }
.graph-tooltip { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); box-shadow: 0 4px 12px rgb(0 0 0 / 0.15); display: flex; flex-direction: column; gap: var(--space-1); max-width: 18rem; padding: var(--space-2) var(--space-3); pointer-events: none; position: absolute; z-index: 10; }
.graph-tooltip strong { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); }
.tooltip-type { color: var(--color-text-subtle); font: var(--font-weight-bold) var(--font-size-xs) / 1 var(--font-family-data); text-transform: uppercase; }
.drag-hint { bottom: var(--space-3); color: var(--color-text-subtle); font-size: var(--font-size-xs); margin: 0; position: absolute; right: var(--space-4); }
.graph-legend { align-items: center; display: flex; flex-wrap: wrap; gap: var(--space-4); }
.legend-item { align-items: center; color: var(--color-text-muted); display: flex; font-size: var(--font-size-xs); gap: var(--space-2); text-transform: capitalize; }
.legend-swatch { border-radius: 50%; display: inline-block; height: 10px; width: 10px; }
.state-panel { align-items: center; background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); color: var(--color-accent); display: flex; gap: var(--space-4); min-height: 20rem; padding: var(--space-8); }
.state-error { background: var(--color-danger-surface); color: var(--color-danger); }
.state-panel h3 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-lg); margin: 0 0 var(--space-3); }
.state-panel button { align-items: center; background: var(--color-accent); border: 0; color: var(--color-accent-contrast); cursor: pointer; display: inline-flex; font-weight: var(--font-weight-semibold); gap: var(--space-2); min-height: var(--control-height-md); padding: 0 var(--space-4); }
.graph-loading { flex-direction: column; justify-content: center; }
.graph-loading p { color: var(--color-text-muted); font-size: var(--font-size-sm); margin: 0; }
@keyframes spin { to { transform: rotate(360deg); } }
.spin { animation: spin 1.2s linear infinite; }
@media (max-width: 640px) {
  .graph-header { flex-direction: column; }
  .search-input { min-width: 100%; }
  .search-row { width: 100%; }
  .graph-controls { flex-direction: column; align-items: flex-start; }
}
</style>
