<template>
  <section :class="['mc-frame', `mc-${theme}`]" aria-label="Match Centre design concept">
    <div class="mc-browser" aria-hidden="true">
      <span></span><span></span><span></span>
      <small>app.socceroctupus.com / world-cup-2026 / predict</small>
    </div>

    <div class="mc-app">
      <header class="mc-nav">
        <a class="mc-brand" href="#"><span>SO</span> SoccerOctopus</a>
        <nav aria-label="Match Centre navigation">
          <a href="#">Home</a><a href="#">Groups</a><a class="active" href="#">Predict match</a><a href="#">Tournament</a><a href="#">Markets</a>
        </nav>
        <button class="mc-competition" type="button"><i>WC</i><span>World Cup 2026<small>Active competition</small></span><ChevronDown :size="14" /></button>
        <span class="mc-profile">RO</span>
      </header>

      <main>
        <div class="mc-context">
          <span>Prediction / group stage</span>
          <span>Swarm run SO-WC26-1842</span>
        </div>

        <section class="mc-match">
          <div class="mc-team mc-home">
            <span class="mc-team-code">BRA</span>
            <h3>Brazil</h3>
            <p>ELO 1864 · rank #5</p>
          </div>

          <div class="mc-score">
            <p>Most likely score</p>
            <div><strong>2</strong><span>:</span><strong>1</strong></div>
            <small>64.2% home win</small>
          </div>

          <div class="mc-team mc-away">
            <span class="mc-team-code">GER</span>
            <h3>Germany</h3>
            <p>ELO 1788 · rank #11</p>
          </div>
        </section>

        <div class="mc-probability" aria-label="Outcome probabilities">
          <span class="home" style="width: 64.2%"><strong>64.2%</strong><small>Brazil</small></span>
          <span class="draw" style="width: 20.7%"><strong>20.7%</strong><small>Draw</small></span>
          <span class="away" style="width: 15.1%"><strong>15.1%</strong><small>Germany</small></span>
        </div>

        <div class="mc-workspace">
          <section class="mc-consensus">
            <div class="mc-section-head"><span>01</span><div><small>Swarm consensus</small><h4>Why Brazil leads</h4></div></div>
            <p class="mc-summary">Brazil carries the stronger ELO rating and recent form. The tactical agent expects Germany's high defensive line to leave space behind the full-backs.</p>
            <div class="mc-factors">
              <div><span>+</span><p><strong>Recent form</strong> Brazil earned 24 points from its last 10 official matches.</p></div>
              <div><span>+</span><p><strong>Tactical profile</strong> Direct transitions rate well against a high press.</p></div>
              <div><span>+</span><p><strong>Expected goals</strong> The model projects 2.08 xG against Germany's 1.16.</p></div>
            </div>
            <button type="button">Generate market questions <ArrowUpRight :size="15" /></button>
          </section>

          <section class="mc-scores">
            <div class="mc-section-head"><span>02</span><div><small>Poisson model</small><h4>Score probabilities</h4></div></div>
            <div v-for="score in scores" :key="score.label" class="mc-score-row">
              <strong>{{ score.label }}</strong><span><i :style="{ width: score.width }"></i></span><small>{{ score.value }}</small>
            </div>
            <div class="mc-xg"><span>Expected goals</span><strong>2.08 <i>/</i> 1.16</strong></div>
          </section>

          <aside class="mc-agents">
            <div class="mc-section-head"><span>03</span><div><small>Agent breakdown</small><h4>Agreement</h4></div></div>
            <div v-for="agent in agents" :key="agent.name" class="mc-agent-row">
              <span>{{ agent.code }}</span><div><strong>{{ agent.name }}</strong><small>{{ agent.read }}</small></div><b>{{ agent.confidence }}</b>
            </div>
            <div class="mc-confidence"><span>Overall confidence</span><strong>78.4%</strong></div>
          </aside>
        </div>
      </main>
    </div>
  </section>
</template>

<script setup>
import { ArrowUpRight, ChevronDown } from '@lucide/vue'

defineProps({ theme: { type: String, default: 'light' } })

const scores = [
  { label: '2-1', value: '14.8%', width: '100%' },
  { label: '1-0', value: '12.1%', width: '82%' },
  { label: '2-0', value: '10.6%', width: '72%' },
  { label: '1-1', value: '9.4%', width: '64%' },
]

const agents = [
  { code: 'ST', name: 'Statistical', read: 'Brazil win · 2-1', confidence: '84%' },
  { code: 'RF', name: 'Recent form', read: 'Brazil win · 2-0', confidence: '79%' },
  { code: 'TA', name: 'Tactical', read: 'Brazil win · 2-1', confidence: '76%' },
  { code: 'VI', name: 'Video intelligence', read: 'Draw · 1-1', confidence: '63%' },
]
</script>

<style scoped>
.mc-frame {
  --mc-bg: #eeeae1;
  --mc-surface: #f8f5ed;
  --mc-ink: #1a1916;
  --mc-muted: #777268;
  --mc-line: #cec8bb;
  --mc-accent: #bd562f;
  --mc-soft: #e7d4c5;
  background: var(--mc-bg);
  border: 1px solid #d1ccc2;
  border-radius: 8px;
  color: var(--mc-ink);
  overflow: hidden;
}
.mc-frame.mc-dark { --mc-bg: #131311; --mc-surface: #1c1c18; --mc-ink: #f0ede5; --mc-muted: #aaa398; --mc-line: #3a3832; --mc-accent: #db7149; --mc-soft: #4a2d21; border-color: #3a3832; }
.mc-browser { align-items: center; background: color-mix(in srgb, var(--mc-bg) 84%, var(--mc-ink)); display: flex; gap: 6px; height: 30px; padding: 0 13px; }
.mc-browser > span { background: var(--mc-muted); border-radius: 50%; height: 6px; opacity: .55; width: 6px; }
.mc-browser small { color: var(--mc-muted); font: 8px 'SFMono-Regular', Consolas, monospace; margin: 0 auto; }
.mc-app { min-height: 720px; }
.mc-nav { align-items: center; border-bottom: 1px solid var(--mc-line); display: grid; gap: 24px; grid-template-columns: auto 1fr auto auto; min-height: 68px; padding: 0 34px; }
.mc-brand { align-items: center; color: var(--mc-ink); display: inline-flex; font: 800 14px 'Arial Narrow', sans-serif; gap: 9px; text-decoration: none; }
.mc-brand > span { align-items: center; background: var(--mc-ink); color: var(--mc-bg); display: inline-flex; font: 800 9px 'SFMono-Regular', monospace; height: 26px; justify-content: center; width: 26px; }
.mc-nav nav { display: flex; gap: 21px; }
.mc-nav nav a { color: var(--mc-muted); font-size: 10px; font-weight: 700; padding: 29px 0 27px; text-decoration: none; }
.mc-nav nav a.active { box-shadow: inset 0 -3px var(--mc-accent); color: var(--mc-ink); }
.mc-competition { align-items: center; background: transparent; border: 0; color: var(--mc-ink); display: flex; gap: 8px; padding: 0; text-align: left; }
.mc-competition i { align-items: center; background: var(--mc-accent); color: #fff; display: inline-flex; font: normal 800 8px 'SFMono-Regular', monospace; height: 27px; justify-content: center; width: 27px; }
.mc-competition span { display: flex; flex-direction: column; font-size: 10px; font-weight: 800; }.mc-competition small { color: var(--mc-muted); font-size: 8px; font-weight: 500; order: -1; }.mc-competition svg { color: var(--mc-muted); }
.mc-profile { align-items: center; border: 1px solid var(--mc-line); display: inline-flex; font: 700 8px 'SFMono-Regular', monospace; height: 27px; justify-content: center; width: 27px; }
.mc-app main { padding: 0 34px 38px; }
.mc-context { color: var(--mc-muted); display: flex; font: 8px 'SFMono-Regular', Consolas, monospace; justify-content: space-between; letter-spacing: .08em; padding: 18px 0 10px; text-transform: uppercase; }
.mc-match { align-items: end; display: grid; grid-template-columns: 1fr auto 1fr; padding: 23px 3vw 26px; position: relative; }
.mc-match::before { border: 1px solid var(--mc-line); content: ''; inset: 8px 27% 10px; opacity: .55; position: absolute; }
.mc-team { position: relative; z-index: 1; }.mc-away { text-align: right; }.mc-team-code { color: var(--mc-accent); font: 800 11px 'SFMono-Regular', monospace; letter-spacing: .12em; }
.mc-team h3 { font: 800 clamp(38px, 6vw, 72px)/.86 'Arial Narrow', 'Helvetica Neue', sans-serif; letter-spacing: -.06em; margin: 9px 0 11px; }.mc-team p { color: var(--mc-muted); font: 9px 'SFMono-Regular', monospace; margin: 0; }
.mc-score { align-items: center; display: flex; flex-direction: column; min-width: 190px; position: relative; z-index: 1; }.mc-score > p { color: var(--mc-muted); font-size: 9px; margin: 0 0 7px; }.mc-score > div { align-items: center; display: flex; font-family: 'SFMono-Regular', monospace; }.mc-score strong { font-size: 48px; letter-spacing: -.1em; }.mc-score div span { color: var(--mc-accent); font-size: 22px; padding: 0 11px; }.mc-score > small { background: var(--mc-accent); color: #fff; font-size: 8px; font-weight: 800; margin-top: 8px; padding: 6px 8px; text-transform: uppercase; }
.mc-probability { display: flex; height: 48px; overflow: hidden; }.mc-probability > span { align-items: center; display: flex; justify-content: center; min-width: 86px; position: relative; }.mc-probability strong { font: 800 13px 'SFMono-Regular', monospace; }.mc-probability small { font-size: 8px; margin-left: 7px; }.mc-probability .home { background: var(--mc-accent); color: #fff; }.mc-probability .draw { background: var(--mc-soft); color: var(--mc-ink); }.mc-probability .away { background: var(--mc-ink); color: var(--mc-bg); }
.mc-workspace { border-bottom: 1px solid var(--mc-line); display: grid; grid-template-columns: 1.2fr .8fr .85fr; margin-top: 25px; }.mc-workspace > * { border-left: 1px solid var(--mc-line); padding: 20px; }.mc-workspace > *:last-child { border-right: 1px solid var(--mc-line); }
.mc-section-head { align-items: flex-start; display: flex; gap: 10px; margin-bottom: 16px; }.mc-section-head > span { color: var(--mc-accent); font: 800 9px 'SFMono-Regular', monospace; }.mc-section-head small { color: var(--mc-muted); display: block; font-size: 8px; margin-bottom: 4px; text-transform: uppercase; }.mc-section-head h4 { font: 800 18px 'Arial Narrow', sans-serif; letter-spacing: -.035em; margin: 0; }
.mc-summary { font: 600 13px/1.55 'Helvetica Neue', sans-serif; margin: 0 0 17px; max-width: 54ch; }.mc-factors { display: grid; gap: 10px; }.mc-factors > div { display: grid; gap: 7px; grid-template-columns: 16px 1fr; }.mc-factors > div > span { color: var(--mc-accent); font: 800 14px 'SFMono-Regular', monospace; }.mc-factors p { color: var(--mc-muted); font-size: 9px; line-height: 1.45; margin: 0; }.mc-factors strong { color: var(--mc-ink); }.mc-consensus button { align-items: center; background: var(--mc-ink); border: 0; color: var(--mc-bg); display: inline-flex; font-size: 9px; font-weight: 800; gap: 7px; margin-top: 18px; padding: 10px 12px; }.mc-consensus button:hover { background: var(--mc-accent); color: #fff; }
.mc-score-row { align-items: center; display: grid; gap: 8px; grid-template-columns: 28px 1fr 34px; margin-bottom: 13px; }.mc-score-row strong, .mc-score-row small { font: 800 9px 'SFMono-Regular', monospace; }.mc-score-row small { color: var(--mc-muted); text-align: right; }.mc-score-row > span { background: var(--mc-soft); height: 5px; }.mc-score-row i { background: var(--mc-accent); display: block; height: 100%; }.mc-xg { border-top: 1px solid var(--mc-line); display: flex; justify-content: space-between; margin-top: 18px; padding-top: 14px; }.mc-xg span { color: var(--mc-muted); font-size: 8px; }.mc-xg strong { font: 800 11px 'SFMono-Regular', monospace; }.mc-xg i { color: var(--mc-accent); font-style: normal; }
.mc-agent-row { align-items: center; border-bottom: 1px solid var(--mc-line); display: grid; gap: 8px; grid-template-columns: 25px 1fr auto; padding: 9px 0; }.mc-agent-row > span { align-items: center; background: var(--mc-soft); color: var(--mc-accent); display: inline-flex; font: 800 7px 'SFMono-Regular', monospace; height: 22px; justify-content: center; }.mc-agent-row div { display: flex; flex-direction: column; gap: 2px; }.mc-agent-row strong { font-size: 9px; }.mc-agent-row small { color: var(--mc-muted); font-size: 7px; }.mc-agent-row b { font: 800 9px 'SFMono-Regular', monospace; }.mc-confidence { align-items: end; display: flex; justify-content: space-between; padding-top: 17px; }.mc-confidence span { color: var(--mc-muted); font-size: 8px; }.mc-confidence strong { color: var(--mc-accent); font: 800 18px 'SFMono-Regular', monospace; }
@media (max-width: 850px) { .mc-nav { grid-template-columns: auto 1fr auto; }.mc-nav nav { display: none; }.mc-workspace { grid-template-columns: 1fr 1fr; }.mc-agents { grid-column: 1 / -1; }.mc-match { padding-left: 0; padding-right: 0; }.mc-team h3 { font-size: 43px; } }
@media (max-width: 580px) { .mc-nav { gap: 10px; padding: 0 14px; }.mc-competition span, .mc-profile { display: none; }.mc-app main { padding: 0 14px 24px; }.mc-context span:last-child { display: none; }.mc-match { align-items: center; grid-template-columns: 1fr; gap: 17px; text-align: center; }.mc-away { text-align: center; }.mc-score { grid-row: 2; }.mc-match::before { inset: 30% 8px; }.mc-team h3 { font-size: 46px; }.mc-probability strong { font-size: 10px; }.mc-probability small { display: none; }.mc-workspace { grid-template-columns: 1fr; }.mc-workspace > *, .mc-workspace > *:last-child { border: 1px solid var(--mc-line); border-bottom: 0; }.mc-agents { grid-column: auto; } }
</style>
