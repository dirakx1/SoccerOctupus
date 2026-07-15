<template>
  <div class="lab-page">
    <header class="lab-header">
      <div class="lab-intro">
        <p class="lab-kicker">SoccerOctopus / design lab</p>
        <h1>One football engine, six directions.</h1>
        <p class="lab-lede">
          Six ways to organize the current portal as it grows beyond the World Cup.
          Every concept uses the same prediction, tournament, group, market, and swarm vocabulary.
        </p>
      </div>

      <div class="lab-controls">
        <span class="control-label">Preview mode</span>
        <div class="segmented" role="group" aria-label="Preview theme">
          <button
            v-for="option in themeOptions"
            :key="option.value"
            type="button"
            :class="{ active: theme === option.value }"
            :aria-pressed="theme === option.value"
            @click="setTheme(option.value)"
          >
            {{ option.label }}
          </button>
        </div>
        <router-link class="back-link" to="/">Back to product <ArrowUpRight :size="15" aria-hidden="true" /></router-link>
      </div>
    </header>

    <section class="direction-heading">
      <span>01</span>
      <div><p>Current study</p><h2>Signal Desk</h2><small>Balanced competition overview · modular · palette-flexible</small></div>
    </section>

    <section class="variant-picker" aria-label="Visual variations">
      <div class="variant-picker-heading">
        <p class="eyebrow">Signal studies</p>
        <p class="variant-count">{{ activeIndex + 1 }} / {{ variants.length }}</p>
      </div>
      <div class="variant-tabs" role="tablist" aria-label="Design variations">
        <button
          v-for="(variant, index) in variants"
          :key="variant.key"
          type="button"
          role="tab"
          :aria-selected="activeVariant === variant.key"
          :class="['variant-tab', { active: activeVariant === variant.key }]"
          @click="activeVariant = variant.key"
        >
          <span class="variant-swatch" :style="{ '--swatch': variant.accent }"></span>
          <span>
            <strong>{{ variant.name }}</strong>
            <small>{{ variant.mood }}</small>
          </span>
        </button>
      </div>
      <p class="variant-description">{{ currentVariant.description }}</p>
    </section>

    <section
      class="mockup-frame"
      :class="[`variant-${activeVariant}`, `mode-${theme}`]"
      aria-label="SoccerOctopus dashboard mockup"
    >
      <div class="browser-bar" aria-hidden="true">
        <span></span><span></span><span></span>
        <div class="browser-address">app.socceroctupus.com / world-cup-2026</div>
      </div>

      <div class="mockup-app">
        <header class="mock-nav">
          <router-link class="mock-brand" to="/">
            <span class="brand-mark">SO</span>
            <span class="brand-name">SoccerOctopus</span>
          </router-link>

          <nav class="mock-links" aria-label="Preview navigation">
            <a class="active" href="#overview">Home</a>
            <a href="#groups">Groups</a>
            <a href="#predict">Predict match</a>
            <a href="#tournament">Tournament</a>
            <a href="#markets">Markets</a>
          </nav>

          <div class="mock-nav-actions">
            <span class="live-status"><span class="live-dot"></span> Models live</span>
            <button class="icon-button" type="button" aria-label="Toggle preview theme" @click="setTheme(theme === 'light' ? 'dark' : 'light')">
              <Sun v-if="theme === 'light'" :size="16" aria-hidden="true" />
              <Moon v-else :size="16" aria-hidden="true" />
            </button>
            <span class="mock-avatar">RO</span>
          </div>
        </header>

        <main class="mock-main" id="overview">
          <div class="competition-heading">
            <div>
              <p class="mock-eyebrow">Current competition / FIFA</p>
              <h2>World Cup <span>2026</span></h2>
              <p class="mock-muted">48 teams across 12 groups · hosted in USA, Canada, and Mexico.</p>
            </div>
            <button class="competition-switch" type="button">
              <span class="switch-mark">WC</span>
              <span><small>Active competition</small><strong>FIFA World Cup 2026</strong></span>
              <ChevronDown :size="16" aria-hidden="true" />
            </button>
          </div>

          <div class="metric-strip" aria-label="Competition summary">
            <div v-for="metric in metrics" :key="metric.label" class="metric">
              <span>{{ metric.label }}</span>
              <strong>{{ metric.value }}</strong>
              <small :class="metric.tone">{{ metric.note }}</small>
            </div>
          </div>

          <div id="markets" class="portal-modules" aria-label="Portal modules">
            <a v-for="module in modules" :key="module.label" :href="module.href" class="module-link">
              <span class="module-kicker">{{ module.kicker }}</span>
              <strong>{{ module.label }}</strong>
              <small>{{ module.detail }}</small>
              <ArrowUpRight :size="14" aria-hidden="true" />
            </a>
          </div>

          <div class="mock-grid">
            <section class="panel groups-panel" id="groups">
              <div class="panel-heading">
                <div>
                  <p class="mock-eyebrow">World Cup 2026</p>
                  <h3>Groups and team strength</h3>
                </div>
                <button class="text-button" type="button">Open groups <ArrowRight :size="15" aria-hidden="true" /></button>
              </div>
              <div class="group-list">
                <div v-for="group in groups" :key="group.label" class="group-row">
                  <div class="group-label"><strong>{{ group.label }}</strong><span>{{ group.teams.length }} teams</span></div>
                  <div class="group-teams">
                    <span v-for="team in group.teams" :key="team.name"><i :class="['crest', team.tone]">{{ team.code }}</i>{{ team.name }} <small>ELO {{ team.elo }}</small></span>
                  </div>
                  <span class="group-rank">#{{ group.teams[0].rank }}</span>
                </div>
              </div>
            </section>

            <section class="panel signal-panel" id="predict">
              <div class="panel-heading">
                <div>
                  <p class="mock-eyebrow">Swarm consensus</p>
                  <h3>Brazil vs. Germany</h3>
                </div>
                <span class="confidence-tag">High confidence</span>
              </div>
              <div class="match-meta"><span>Stage: group</span><span>Home / away selection</span></div>
              <div class="scoreline">
                <div><strong>2</strong><span>Brazil</span></div>
                <span class="score-divider">:</span>
                <div><strong>1</strong><span>Germany</span></div>
              </div>
              <div class="probability-list">
                <div v-for="outcome in outcomes" :key="outcome.label" class="probability-row">
                  <div class="probability-label"><span>{{ outcome.label }}</span><strong>{{ outcome.value }}</strong></div>
                  <div class="probability-track"><span :style="{ width: outcome.value }"></span></div>
                </div>
              </div>
              <p class="signal-note"><Sparkles :size="15" aria-hidden="true" /> Swarm consensus combines ELO, recent form, video intelligence, and tactical profile.</p>
              <button class="primary-button" type="button">Open prediction detail <ArrowRight :size="16" aria-hidden="true" /></button>
            </section>
          </div>

          <section class="panel agent-panel" id="tournament">
            <div class="panel-heading agent-heading">
              <div>
                <p class="mock-eyebrow">How the swarm works</p>
                <h3>Specialised agents behind each prediction</h3>
              </div>
              <span class="updated-label">Aggregator synthesises output</span>
            </div>
            <div class="agent-list">
              <div v-for="agent in agents" :key="agent.name" class="agent-item">
                <span class="agent-index">{{ agent.index }}</span>
                <span class="agent-name">{{ agent.name }}</span>
                <span class="agent-weight">{{ agent.weight }}</span>
                <span class="agent-detail">{{ agent.detail }}</span>
              </div>
            </div>
          </section>
        </main>
      </div>
    </section>

    <section class="more-directions" aria-label="Additional design directions">
      <article class="direction-block">
        <header class="direction-heading">
          <span>02</span>
          <div><p>Prediction first</p><h2>Match Centre</h2><small>Broadcast scale · selected match dominates · narrative evidence below</small></div>
        </header>
        <MatchCentrePreview :theme="theme" />
      </article>

      <article class="direction-block">
        <header class="direction-heading">
          <span>03</span>
          <div><p>Evidence first</p><h2>Analyst Ledger</h2><small>Dense tables · restrained typography · fastest scanning</small></div>
        </header>
        <AnalystLedgerPreview :theme="theme" />
      </article>

      <article class="direction-block">
        <header class="direction-heading">
          <span>04</span>
          <div><p>Competition first</p><h2>Tournament Atlas</h2><small>Editorial scale · bracket journey · strongest World Cup identity</small></div>
        </header>
        <TournamentAtlasPreview :theme="theme" />
      </article>

      <article class="direction-block featured-direction">
        <header class="direction-heading">
          <span>05</span>
          <div><p>Consensus first</p><h2>Swarm Orbit</h2><small>Circular probability field · orbiting agents · curved evidence surface</small></div>
        </header>
        <OrbitalSwarmPreview :theme="theme" />
      </article>

      <article class="direction-block featured-direction">
        <header class="direction-heading">
          <span>06</span>
          <div><p>Journey first</p><h2>Stadium Ribbon</h2><small>Flowing bracket path · sculpted tournament layers · circular market data</small></div>
        </header>
        <StadiumRibbonPreview :theme="theme" />
      </article>
    </section>

    <footer class="lab-footer">
      <p>Choose a layout direction first. Palette, light/dark surfaces, and competition routing can then be refined inside that system.</p>
      <span>Vue mockup · no production data changed</span>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  ArrowRight,
  ArrowUpRight,
  ChevronDown,
  Moon,
  Sparkles,
  Sun,
} from '@lucide/vue'
import AnalystLedgerPreview from '../components/design-lab/AnalystLedgerPreview.vue'
import MatchCentrePreview from '../components/design-lab/MatchCentrePreview.vue'
import OrbitalSwarmPreview from '../components/design-lab/OrbitalSwarmPreview.vue'
import StadiumRibbonPreview from '../components/design-lab/StadiumRibbonPreview.vue'
import TournamentAtlasPreview from '../components/design-lab/TournamentAtlasPreview.vue'

const themeOptions = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
]

const variants = [
  {
    key: 'pitch',
    name: 'Pitch signal',
    mood: 'calm / assured',
    accent: '#3d7c58',
    description: 'A quiet editorial base with a measured field-green signal. Built for long sessions and evidence-first decisions.',
  },
  {
    key: 'amber',
    name: 'Matchday amber',
    mood: 'warm / broadcast',
    accent: '#bc6a32',
    description: 'A warmer, more kinetic read that brings stadium light into the interface without turning every state into a shout.',
  },
  {
    key: 'coral',
    name: 'Referee coral',
    mood: 'sharp / urgent',
    accent: '#c45651',
    description: 'A distinct signal for a product that wants more edge. Semantic error states would use a separate, darker red token.',
  },
  {
    key: 'cobalt',
    name: 'Deep cobalt',
    mood: 'technical / exact',
    accent: '#4968a8',
    description: 'A more analytical direction with cool precision. Restrained surfaces keep it away from the familiar AI-gradient look.',
  },
]

const metrics = [
  { label: 'Teams in field', value: '48', note: '12 groups', tone: 'neutral' },
  { label: 'Bracket matches', value: '104', note: 'Monte Carlo ready', tone: 'positive' },
  { label: 'Prediction output', value: 'H / D / A', note: 'probabilities + score', tone: 'positive' },
  { label: 'Market formats', value: '2', note: 'Kalshi / Polymarket', tone: 'neutral' },
]

const modules = [
  { kicker: 'Browse', label: 'WC 2026 groups', detail: 'Teams, ELO, and rank', href: '#groups' },
  { kicker: 'Analyse', label: 'Predict a match', detail: 'H / D / A + scoreline', href: '#predict' },
  { kicker: 'Simulate', label: 'Full tournament', detail: 'Groups to final bracket', href: '#tournament' },
  { kicker: 'Generate', label: 'Prediction markets', detail: 'Match props and futures', href: '#markets' },
]

const groups = [
  { label: 'Group A', teams: [
    { name: 'Mexico', code: 'MX', tone: 'green', elo: '1855', rank: '18' },
    { name: 'South Korea', code: 'KR', tone: 'red', elo: '1850', rank: '22' },
    { name: 'Czechia', code: 'CZ', tone: 'navy', elo: '1835', rank: '36' },
  ] },
  { label: 'Group C', teams: [
    { name: 'Brazil', code: 'BR', tone: 'green', elo: '2050', rank: '4' },
    { name: 'Morocco', code: 'MA', tone: 'red', elo: '1890', rank: '14' },
    { name: 'Scotland', code: 'SC', tone: 'blue', elo: '1820', rank: '43' },
  ] },
  { label: 'Group F', teams: [
    { name: 'Netherlands', code: 'NL', tone: 'red', elo: '2005', rank: '8' },
    { name: 'Sweden', code: 'SE', tone: 'blue', elo: '1900', rank: '26' },
    { name: 'Japan', code: 'JP', tone: 'red', elo: '1895', rank: '15' },
  ] },
  { label: 'Group H', teams: [
    { name: 'Spain', code: 'ES', tone: 'red', elo: '2045', rank: '3' },
    { name: 'Uruguay', code: 'UY', tone: 'blue', elo: '1925', rank: '19' },
    { name: 'Saudi Arabia', code: 'SA', tone: 'green', elo: '1805', rank: '56' },
  ] },
]

const outcomes = [
  { label: 'Brazil win', value: '64%' },
  { label: 'Draw', value: '21%' },
  { label: 'Germany win', value: '15%' },
]

const agents = [
  { index: '01', name: 'Statistical Agent', weight: '1.8×', detail: 'ELO · Poisson · SofaScore' },
  { index: '02', name: 'Video Intelligence', weight: '1.0×', detail: 'YouTube · sentiment' },
  { index: '03', name: 'Recent Form', weight: '1.3×', detail: 'Last 10 · trajectory' },
  { index: '04', name: 'Tactical Agent', weight: '1.2×', detail: 'Style matchup matrix' },
  { index: '05', name: 'Aggregator Agent', weight: '-', detail: 'Consensus · narrative' },
]

const activeVariant = ref('pitch')
const theme = ref('light')
const currentVariant = computed(() => variants.find((variant) => variant.key === activeVariant.value) || variants[0])
const activeIndex = computed(() => variants.findIndex((variant) => variant.key === activeVariant.value))

function setTheme(value) {
  theme.value = value
  window.localStorage?.setItem('socceroctupus-design-lab-theme', value)
}

onMounted(() => {
  const savedTheme = window.localStorage?.getItem('socceroctupus-design-lab-theme')
  if (savedTheme === 'light' || savedTheme === 'dark') {
    theme.value = savedTheme
    return
  }
  theme.value = window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
})
</script>

<style scoped>
.lab-page {
  --lab-ink: #1c241f;
  --lab-muted: #6d756f;
  --lab-subtle: #8e958f;
  --lab-line: #d8d9d2;
  --lab-bg: #f4f3ee;
  --lab-surface: #fffefa;
  --lab-surface-alt: #eeeee8;
  --lab-accent: #3d7c58;
  --lab-accent-deep: #235c3b;
  --lab-accent-soft: #deeadf;
  --lab-shadow: rgba(33, 48, 38, 0.14);
  color: var(--lab-ink);
  display: flex;
  flex-direction: column;
  gap: 30px;
  margin: -32px;
  min-height: calc(100vh - 64px);
  padding: 56px 32px 40px;
  background: #f8f7f2;
}

.lab-header,
.lab-page > .direction-heading,
.variant-picker,
.mockup-frame,
.more-directions,
.lab-footer {
  margin: 0 auto;
  max-width: 1280px;
  width: 100%;
}

.lab-header {
  align-items: flex-end;
  display: flex;
  gap: 48px;
  justify-content: space-between;
}

.lab-intro { max-width: 740px; }
.lab-kicker,
.eyebrow,
.mock-eyebrow,
.control-label {
  color: var(--lab-accent);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.13em;
  margin: 0 0 10px;
  text-transform: uppercase;
}
.lab-kicker { color: #6a726d; }
.lab-intro h1 {
  color: #192019;
  font-family: 'Arial Narrow', 'Helvetica Neue', sans-serif;
  font-size: clamp(38px, 5vw, 68px);
  font-stretch: condensed;
  font-weight: 800;
  letter-spacing: -0.055em;
  line-height: 0.95;
  margin: 0;
  max-width: 760px;
  text-wrap: balance;
}
.lab-lede { color: #69716b; font-size: 15px; line-height: 1.6; margin: 18px 0 0; max-width: 590px; }

.direction-heading { align-items: flex-start; display: flex; gap: 14px; }
.direction-heading > span { color: #7a817c; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 10px; font-weight: 800; padding-top: 4px; }
.direction-heading p { color: #7a817c; font-size: 9px; font-weight: 800; letter-spacing: .1em; margin: 0 0 4px; text-transform: uppercase; }
.direction-heading h2 { color: #192019; font-family: 'Arial Narrow', 'Helvetica Neue', sans-serif; font-size: 30px; font-weight: 800; letter-spacing: -.045em; line-height: 1; margin: 0; }
.direction-heading small { color: #7a817c; display: block; font-size: 11px; margin-top: 7px; }
.more-directions { display: flex; flex-direction: column; gap: 72px; }
.direction-block { display: flex; flex-direction: column; gap: 18px; }
.direction-block .direction-heading { border-top: 1px solid #d9dad4; padding-top: 18px; }

.lab-controls { align-items: flex-end; display: flex; flex-direction: column; gap: 10px; min-width: 160px; }
.control-label { color: #6a726d; margin: 0; }
.segmented { background: #e4e5de; border-radius: 7px; display: inline-flex; padding: 3px; }
.segmented button {
  background: transparent;
  border: 0;
  border-radius: 5px;
  color: #6c746e;
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  min-width: 64px;
  padding: 8px 12px;
  transition: background 180ms ease, color 180ms ease, transform 180ms ease;
}
.segmented button:hover { color: #1c241f; }
.segmented button:active { transform: translateY(1px); }
.segmented button.active { background: #fffefa; box-shadow: 0 1px 4px rgba(25, 37, 28, 0.12); color: #1c241f; }
.back-link { align-items: center; color: #59635b; display: inline-flex; font-size: 12px; font-weight: 700; gap: 5px; text-decoration: none; }
.back-link:hover { color: #1c241f; }

.variant-picker { border-bottom: 1px solid #d9dad4; border-top: 1px solid #d9dad4; padding: 18px 0 16px; }
.variant-picker-heading { align-items: center; display: flex; justify-content: space-between; }
.variant-picker .eyebrow { color: #6a726d; margin: 0; }
.variant-count { color: #8b928c; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 11px; margin: 0; }
.variant-tabs { display: grid; gap: 10px; grid-template-columns: repeat(4, 1fr); margin-top: 12px; }
.variant-tab {
  align-items: center;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 7px;
  color: #69726c;
  cursor: pointer;
  display: flex;
  gap: 11px;
  padding: 10px 12px;
  text-align: left;
  transition: background 180ms ease, border-color 180ms ease, transform 180ms ease;
}
.variant-tab:hover { background: #eeeee9; transform: translateY(-1px); }
.variant-tab.active { background: #fffefa; border-color: #d4d6cf; box-shadow: 0 3px 10px rgba(27, 39, 30, 0.06); color: #1c241f; }
.variant-swatch { background: var(--swatch); border-radius: 4px; box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.12); flex: 0 0 22px; height: 22px; }
.variant-tab strong { display: block; font-size: 12px; font-weight: 800; }
.variant-tab small { color: #8a918b; display: block; font-size: 11px; margin-top: 2px; }
.variant-description { color: #69726c; font-size: 13px; line-height: 1.5; margin: 14px 0 0; max-width: 660px; }

.mockup-frame { background: var(--lab-bg); border: 1px solid #d7d8d1; border-radius: 10px; box-shadow: 0 20px 48px var(--lab-shadow); overflow: hidden; }
.browser-bar { align-items: center; background: #e8e8e2; display: flex; gap: 6px; height: 30px; padding: 0 13px; }
.browser-bar > span { background: #c2c5be; border-radius: 50%; height: 7px; width: 7px; }
.browser-address { color: #8c938d; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 9px; margin: 0 auto; }
.mockup-app { background: var(--lab-bg); color: var(--lab-ink); min-height: 690px; }
.mock-nav { align-items: center; border-bottom: 1px solid var(--lab-line); display: flex; gap: 42px; min-height: 68px; padding: 0 clamp(20px, 4vw, 48px); }
.mock-brand { align-items: center; color: var(--lab-ink); display: inline-flex; flex-shrink: 0; gap: 9px; text-decoration: none; }
.brand-mark { align-items: center; background: var(--lab-accent); border-radius: 5px; color: #fffefa; display: inline-flex; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 10px; font-weight: 800; height: 26px; justify-content: center; letter-spacing: -0.04em; width: 26px; }
.brand-name { font-family: 'Arial Narrow', 'Helvetica Neue', sans-serif; font-size: 15px; font-weight: 800; letter-spacing: -0.02em; }
.mock-links { display: flex; gap: 25px; }
.mock-links a { border-bottom: 2px solid transparent; color: var(--lab-muted); font-size: 12px; font-weight: 700; padding: 25px 0 23px; text-decoration: none; }
.mock-links a:hover, .mock-links a.active { border-color: var(--lab-accent); color: var(--lab-ink); }
.mock-nav-actions { align-items: center; display: flex; gap: 13px; margin-left: auto; }
.live-status { align-items: center; color: var(--lab-muted); display: inline-flex; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 9px; gap: 6px; text-transform: uppercase; }
.live-dot { background: var(--lab-accent); border-radius: 50%; box-shadow: 0 0 0 3px var(--lab-accent-soft); height: 5px; width: 5px; }
.icon-button { align-items: center; background: transparent; border: 1px solid var(--lab-line); border-radius: 5px; color: var(--lab-muted); cursor: pointer; display: inline-flex; height: 29px; justify-content: center; width: 29px; }
.icon-button:hover { border-color: var(--lab-accent); color: var(--lab-accent); }
.mock-avatar { align-items: center; background: var(--lab-surface-alt); border: 1px solid var(--lab-line); border-radius: 5px; color: var(--lab-muted); display: inline-flex; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 9px; font-weight: 700; height: 29px; justify-content: center; width: 29px; }

.mock-main { margin: 0 auto; max-width: 1150px; padding: 42px clamp(20px, 4vw, 48px) 54px; }
.competition-heading { align-items: flex-end; display: flex; gap: 24px; justify-content: space-between; }
.mock-eyebrow { color: var(--lab-accent); font-size: 9px; margin-bottom: 8px; }
.competition-heading h2 { font-family: 'Arial Narrow', 'Helvetica Neue', sans-serif; font-size: clamp(32px, 4vw, 52px); font-weight: 800; letter-spacing: -0.055em; line-height: 0.95; margin: 0; }
.competition-heading h2 span { color: var(--lab-accent); }
.mock-muted { color: var(--lab-muted); font-size: 12px; line-height: 1.5; margin: 12px 0 0; }
.competition-switch { align-items: center; background: var(--lab-surface); border: 1px solid var(--lab-line); border-radius: 6px; color: var(--lab-ink); cursor: pointer; display: flex; gap: 9px; min-width: 230px; padding: 9px 11px; text-align: left; }
.competition-switch:hover { border-color: var(--lab-accent); }
.switch-mark { align-items: center; background: var(--lab-accent-soft); border-radius: 4px; color: var(--lab-accent-deep); display: inline-flex; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 9px; font-weight: 800; height: 30px; justify-content: center; width: 30px; }
.competition-switch span:nth-child(2) { display: flex; flex: 1; flex-direction: column; gap: 3px; }
.competition-switch small { color: var(--lab-muted); font-size: 9px; }
.competition-switch strong { font-size: 11px; }
.competition-switch svg { color: var(--lab-muted); }

.metric-strip { border-bottom: 1px solid var(--lab-line); border-top: 1px solid var(--lab-line); display: grid; grid-template-columns: repeat(4, 1fr); margin: 40px 0 26px; }
.metric { border-right: 1px solid var(--lab-line); display: flex; flex-direction: column; gap: 4px; min-height: 92px; padding: 15px 18px; }
.metric:first-child { padding-left: 0; }
.metric:last-child { border-right: 0; }
.metric > span { color: var(--lab-muted); font-size: 10px; }
.metric strong { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 24px; letter-spacing: -0.05em; }
.metric small { font-size: 10px; }
.metric small.positive { color: var(--lab-accent); }
.metric small.neutral { color: var(--lab-subtle); }

.portal-modules { display: grid; gap: 8px; grid-template-columns: repeat(4, 1fr); margin-bottom: 18px; }
.module-link { background: var(--lab-surface); border: 1px solid var(--lab-line); border-radius: 6px; color: var(--lab-ink); display: grid; gap: 4px; min-height: 88px; padding: 13px 14px; position: relative; text-decoration: none; transition: border-color 180ms ease, transform 180ms ease, background 180ms ease; }
.module-link:hover { background: var(--lab-surface-alt); border-color: var(--lab-accent); transform: translateY(-1px); }
.module-link svg { color: var(--lab-accent); position: absolute; right: 12px; top: 13px; }
.module-kicker { color: var(--lab-accent); font-size: 9px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }
.module-link strong { font-family: 'Arial Narrow', 'Helvetica Neue', sans-serif; font-size: 15px; letter-spacing: -0.025em; }
.module-link small { color: var(--lab-muted); font-size: 10px; }
.mock-grid { display: grid; gap: 18px; grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr); }
.panel { background: var(--lab-surface); border: 1px solid var(--lab-line); border-radius: 7px; }
.panel-heading { align-items: flex-start; display: flex; gap: 14px; justify-content: space-between; padding: 19px 20px 15px; }
.panel-heading h3 { font-family: 'Arial Narrow', 'Helvetica Neue', sans-serif; font-size: 20px; font-weight: 800; letter-spacing: -0.04em; margin: 0; }
.text-button { align-items: center; background: transparent; border: 0; color: var(--lab-accent); cursor: pointer; display: inline-flex; font-size: 10px; font-weight: 800; gap: 4px; padding: 2px 0; white-space: nowrap; }
.text-button:hover { color: var(--lab-accent-deep); }
.group-list { border-top: 1px solid var(--lab-line); }
.group-row { align-items: center; border-bottom: 1px solid var(--lab-line); display: grid; gap: 11px; grid-template-columns: 64px minmax(0, 1fr) 25px; min-height: 79px; padding: 10px 20px; }
.group-row:last-child { border-bottom: 0; }
.group-row:hover { background: var(--lab-surface-alt); }
.group-label { display: flex; flex-direction: column; gap: 4px; }
.group-label strong { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 10px; }
.group-label span { color: var(--lab-muted); font-size: 9px; }
.group-teams { display: grid; gap: 5px; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.group-teams span { align-items: center; display: flex; font-size: 10px; font-weight: 700; gap: 6px; min-width: 0; }
.group-teams span small { color: var(--lab-muted); font-family: 'SFMono-Regular', Consolas, monospace; font-size: 8px; font-weight: 500; margin-left: auto; }
.group-rank { color: var(--lab-subtle); font-family: 'SFMono-Regular', Consolas, monospace; font-size: 10px; text-align: right; }
.crest { align-items: center; border-radius: 3px; color: #fff; display: inline-flex; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 8px; font-style: normal; font-weight: 800; height: 19px; justify-content: center; width: 23px; }
.crest.green { background: #38775d; }.crest.red { background: #b75b5a; }.crest.blue { background: #4b6eac; }.crest.gold { background: #b98842; }.crest.navy { background: #344e78; }.crest.yellow { background: #ad9d42; }

.signal-panel { padding-bottom: 20px; }
.confidence-tag { background: var(--lab-accent-soft); border-radius: 4px; color: var(--lab-accent-deep); font-size: 9px; font-weight: 800; padding: 6px 7px; white-space: nowrap; }
.match-meta { border-bottom: 1px solid var(--lab-line); color: var(--lab-muted); display: flex; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 9px; justify-content: space-between; padding: 0 20px 14px; text-transform: uppercase; }
.scoreline { align-items: center; display: flex; justify-content: center; padding: 20px 20px 16px; }
.scoreline > div { align-items: center; display: flex; flex-direction: column; gap: 6px; min-width: 88px; }
.scoreline strong { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 40px; letter-spacing: -0.1em; line-height: 0.9; }
.scoreline span:not(.score-divider) { color: var(--lab-muted); font-size: 10px; font-weight: 700; }
.score-divider { color: var(--lab-subtle); font-family: 'SFMono-Regular', Consolas, monospace; font-size: 21px; padding: 0 8px; }
.probability-list { display: flex; flex-direction: column; gap: 11px; padding: 0 20px 15px; }
.probability-label { align-items: center; display: flex; font-size: 10px; justify-content: space-between; margin-bottom: 5px; }
.probability-label span { color: var(--lab-muted); }.probability-label strong { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 10px; }
.probability-track { background: var(--lab-surface-alt); border-radius: 2px; height: 5px; overflow: hidden; }
.probability-track span { background: var(--lab-accent); border-radius: inherit; display: block; height: 100%; }
.probability-row:nth-child(2) .probability-track span { opacity: 0.54; }.probability-row:nth-child(3) .probability-track span { opacity: 0.3; }
.signal-note { align-items: flex-start; background: var(--lab-surface-alt); color: var(--lab-muted); display: flex; font-size: 10px; gap: 7px; line-height: 1.45; margin: 0 20px 17px; padding: 10px 11px; }
.signal-note svg { color: var(--lab-accent); flex-shrink: 0; margin-top: 1px; }
.primary-button { align-items: center; background: var(--lab-accent); border: 0; border-radius: 4px; color: #fffefa; cursor: pointer; display: inline-flex; font-size: 10px; font-weight: 800; gap: 7px; margin: 0 20px; padding: 10px 13px; transition: filter 180ms ease, transform 180ms ease; }
.primary-button:hover { filter: brightness(1.08); transform: translateY(-1px); }.primary-button:active { transform: translateY(1px) scale(0.99); }

.agent-panel { margin-top: 18px; }
.agent-heading { align-items: center; border-bottom: 1px solid var(--lab-line); padding-bottom: 17px; }
.updated-label { color: var(--lab-muted); font-family: 'SFMono-Regular', Consolas, monospace; font-size: 9px; }
.agent-list { display: grid; grid-template-columns: repeat(5, 1fr); }
.agent-item { border-right: 1px solid var(--lab-line); display: grid; gap: 5px; grid-template-columns: 22px 1fr; padding: 15px 16px 17px; }
.agent-item:last-child { border-right: 0; }.agent-index { color: var(--lab-subtle); font-family: 'SFMono-Regular', Consolas, monospace; font-size: 9px; grid-column: 1; grid-row: 1 / span 3; }
.agent-name { color: var(--lab-ink); font-size: 10px; font-weight: 700; grid-column: 2; line-height: 1.2; }.agent-weight { color: var(--lab-accent); font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12px; font-weight: 800; grid-column: 2; }.agent-detail { color: var(--lab-muted); font-size: 8px; grid-column: 2; line-height: 1.3; }

.lab-footer { align-items: flex-start; border-top: 1px solid #d9dad4; color: #707870; display: flex; font-size: 11px; gap: 20px; justify-content: space-between; line-height: 1.5; padding-top: 16px; }
.lab-footer p { margin: 0; max-width: 620px; }.lab-footer span { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 9px; white-space: nowrap; }

/* Each variant changes the signal tokens only; the information architecture stays fixed. */
.variant-amber { --lab-accent: #bc6a32; --lab-accent-deep: #8a451e; --lab-accent-soft: #f0dfd0; }
.variant-coral { --lab-accent: #c45651; --lab-accent-deep: #923c39; --lab-accent-soft: #f1d9d7; }
.variant-cobalt { --lab-accent: #4968a8; --lab-accent-deep: #304e89; --lab-accent-soft: #dce3f1; }
.mode-dark { --lab-ink: #e8ebe5; --lab-muted: #a0a9a0; --lab-subtle: #758078; --lab-line: #343b35; --lab-bg: #111512; --lab-surface: #191e1a; --lab-surface-alt: #222922; --lab-shadow: rgba(0, 0, 0, 0.42); }
.mode-dark .browser-bar { background: #252a25; }.mode-dark .browser-bar > span { background: #515a52; }.mode-dark .lab-intro h1 { color: #edf0e9; }
.mode-dark .segmented { background: #252b26; }.mode-dark .segmented button.active { background: #343b35; color: #edf0e9; }.mode-dark .segmented button:hover { color: #edf0e9; }
.mode-dark .variant-picker, .mode-dark .lab-footer { border-color: #343b35; }.mode-dark .variant-tab:hover, .mode-dark .variant-tab.active { background: #1c221d; border-color: #343b35; }.mode-dark .lab-page { background: #121612; }
.mode-dark .lab-kicker, .mode-dark .lab-lede, .mode-dark .back-link, .mode-dark .control-label, .mode-dark .variant-description { color: #9da69d; }.mode-dark .lab-footer { color: #9da69d; }

@media (max-width: 900px) {
  .lab-page { margin: -16px; padding: 36px 16px 28px; }
  .lab-header { align-items: flex-start; flex-direction: column; gap: 24px; }.lab-controls { align-items: flex-start; }
  .variant-tabs { grid-template-columns: repeat(2, 1fr); }.mock-links { gap: 15px; }.mock-nav { gap: 18px; }.live-status { display: none; }
  .portal-modules { grid-template-columns: repeat(2, 1fr); }.mock-grid { grid-template-columns: 1fr; }.agent-list { grid-template-columns: repeat(3, 1fr); }.agent-item:nth-child(3) { border-right: 0; }.agent-item:nth-child(n + 4) { border-top: 1px solid var(--lab-line); }
}

@media (max-width: 580px) {
  .lab-intro h1 { font-size: 42px; }.variant-tabs { grid-template-columns: 1fr; }.variant-tab { padding: 9px 10px; }
  .mock-nav { flex-wrap: wrap; min-height: 60px; padding: 13px 20px 0; }.mock-links { order: 3; overflow-x: auto; width: 100%; }.mock-links a { padding: 12px 0 13px; }.mock-nav-actions { margin-left: auto; }
  .mock-main { padding-top: 30px; }.competition-heading { align-items: flex-start; flex-direction: column; }.competition-switch { width: 100%; }.metric-strip { grid-template-columns: repeat(2, 1fr); }.metric { border-bottom: 1px solid var(--lab-line); }.metric:nth-child(2) { border-right: 0; }.metric:nth-child(3), .metric:nth-child(4) { border-bottom: 0; }.metric:nth-child(3) { padding-left: 0; }
  .portal-modules { grid-template-columns: 1fr; }.group-row { gap: 8px; grid-template-columns: 48px minmax(0, 1fr) 20px; padding-left: 12px; padding-right: 12px; }.group-teams { grid-template-columns: 1fr; }.group-teams span small { display: none; }.panel-heading { padding-left: 14px; padding-right: 14px; }
  .agent-list { grid-template-columns: repeat(2, 1fr); }.agent-item:nth-child(2) { border-right: 0; }.agent-item:nth-child(3) { border-right: 1px solid var(--lab-line); }.agent-item:nth-child(5) { grid-column: span 2; border-right: 0; }.lab-footer { flex-direction: column; gap: 8px; }.lab-footer span { white-space: normal; }
}
</style>
