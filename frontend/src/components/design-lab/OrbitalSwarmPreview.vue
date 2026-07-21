<template>
  <section :class="['orbit-frame', `orbit-${theme}`]" aria-label="Swarm Orbit design concept">
    <header class="orbit-nav">
      <a href="#" class="orbit-brand"><span>SO</span><strong>SoccerOctopus</strong></a>
      <nav><a href="#">Home</a><a href="#">Groups</a><a class="active" href="#">Predict</a><a href="#">Tournament</a><a href="#">Markets</a></nav>
      <button type="button" class="orbit-competition"><i>WC</i><span>World Cup 2026</span><ChevronDown :size="14" /></button>
      <span class="orbit-avatar">RO</span>
    </header>

    <main class="orbit-main">
      <div class="orbit-heading">
        <p>Swarm prediction</p>
        <h2>Brazil <i>meets</i> Germany</h2>
        <button type="button">Change match <ArrowUpRight :size="14" /></button>
      </div>

      <section class="orbit-stage">
        <div class="team-name home"><span>BRA</span><strong>Brazil</strong><small>ELO 1864 / rank 5</small></div>
        <div class="team-name away"><span>GER</span><strong>Germany</strong><small>ELO 1788 / rank 11</small></div>

        <div class="agent-orbit" aria-label="Swarm agents">
          <div class="orbit-path"></div>
          <div v-for="agent in agents" :key="agent.code" :class="['agent-satellite', agent.position]">
            <span>{{ agent.code }}</span><strong>{{ agent.name }}</strong><small>{{ agent.weight }}</small>
          </div>

          <div class="consensus-ring">
            <div class="consensus-core">
              <span>Most likely</span>
              <strong>2:1</strong>
              <small>78.4% confidence</small>
            </div>
          </div>
        </div>

        <div class="orbit-outcomes">
          <div><span>Brazil win</span><strong>64.2%</strong></div>
          <div><span>Draw</span><strong>20.7%</strong></div>
          <div><span>Germany win</span><strong>15.1%</strong></div>
        </div>
      </section>

      <section class="orbit-insight">
        <div class="insight-lead"><span>Swarm consensus</span><h3>Four signals point home.</h3><p>Brazil's ELO edge, recent form, and tactical fit outweigh a cautious video signal.</p></div>
        <div class="insight-wave">
          <article><strong>2.08</strong><span>Brazil expected goals</span></article>
          <article><strong>1.16</strong><span>Germany expected goals</span></article>
          <article><strong>14.8%</strong><span>2-1 score probability</span></article>
        </div>
        <button type="button" class="orbit-action">Open full analysis <ArrowRight :size="15" /></button>
      </section>
    </main>
  </section>
</template>

<script setup>
import { ArrowRight, ArrowUpRight, ChevronDown } from '@lucide/vue'

defineProps({ theme: { type: String, default: 'light' } })

const agents = [
  { code: 'ST', name: 'Statistical', weight: '1.8x', position: 'satellite-one' },
  { code: 'VI', name: 'Video', weight: '1.0x', position: 'satellite-two' },
  { code: 'RF', name: 'Recent form', weight: '1.3x', position: 'satellite-three' },
  { code: 'TA', name: 'Tactical', weight: '1.2x', position: 'satellite-four' },
]
</script>

<style scoped>
.orbit-frame {
  --or-bg: #dfe6dc;
  --or-surface: rgba(247, 249, 243, .82);
  --or-ink: #183027;
  --or-muted: #66766c;
  --or-line: rgba(24, 48, 39, .18);
  --or-accent: #de5e42;
  --or-accent-ink: #8d2d1e;
  --or-soft: rgba(222, 94, 66, .14);
  background:
    radial-gradient(circle at 50% 40%, transparent 0 20%, rgba(255,255,255,.28) 20.2% 20.5%, transparent 20.7% 33%, rgba(24,48,39,.08) 33.2% 33.5%, transparent 33.7%),
    var(--or-bg);
  border-radius: 30px;
  box-shadow: 0 30px 80px rgba(38, 60, 48, .2);
  color: var(--or-ink);
  min-height: 790px;
  overflow: hidden;
  padding: 16px;
  position: relative;
}
.orbit-frame.orbit-dark { --or-bg: #101a16; --or-surface: rgba(28, 40, 34, .84); --or-ink: #edf2e9; --or-muted: #9aac9f; --or-line: rgba(237, 242, 233, .16); --or-accent: #ec7256; --or-accent-ink: #ffac97; --or-soft: rgba(236, 114, 86, .15); box-shadow: 0 30px 80px rgba(0,0,0,.38); }
.orbit-frame::before { border: 1px solid var(--or-line); border-radius: 50%; content: ''; height: 880px; left: 50%; pointer-events: none; position: absolute; top: -540px; transform: translateX(-50%); width: 1180px; }
.orbit-nav { align-items: center; backdrop-filter: blur(18px); background: var(--or-surface); border: 1px solid var(--or-line); border-radius: 999px; box-shadow: inset 0 1px rgba(255,255,255,.35); display: grid; gap: 24px; grid-template-columns: auto 1fr auto auto; min-height: 54px; padding: 0 12px 0 15px; position: relative; z-index: 3; }
.orbit-brand { align-items: center; color: var(--or-ink); display: inline-flex; font: 800 13px 'Arial Narrow', sans-serif; gap: 8px; text-decoration: none; }.orbit-brand span { align-items: center; background: var(--or-accent); border-radius: 50%; color: #fff; display: inline-flex; font: 800 8px 'SFMono-Regular', monospace; height: 28px; justify-content: center; width: 28px; }
.orbit-nav nav { display: flex; gap: 23px; justify-content: center; }.orbit-nav nav a { color: var(--or-muted); font-size: 10px; font-weight: 700; text-decoration: none; }.orbit-nav nav a.active { color: var(--or-accent-ink); }
.orbit-competition { align-items: center; background: transparent; border: 0; color: var(--or-ink); display: inline-flex; font-size: 9px; font-weight: 800; gap: 7px; }.orbit-competition i { align-items: center; background: var(--or-soft); border-radius: 50%; color: var(--or-accent-ink); display: inline-flex; font: normal 800 7px 'SFMono-Regular', monospace; height: 25px; justify-content: center; width: 25px; }.orbit-avatar { align-items: center; border: 1px solid var(--or-line); border-radius: 50%; display: inline-flex; font: 800 8px 'SFMono-Regular', monospace; height: 31px; justify-content: center; width: 31px; }
.orbit-main { margin: auto; max-width: 1180px; padding: 35px 26px 0; }.orbit-heading { align-items: end; display: grid; grid-template-columns: 1fr auto; position: relative; z-index: 2; }.orbit-heading p { color: var(--or-accent-ink); font: 800 9px 'SFMono-Regular', monospace; grid-column: 1 / -1; letter-spacing: .08em; margin: 0 0 7px; text-transform: uppercase; }.orbit-heading h2 { font: 800 clamp(39px, 5vw, 64px)/.9 'Arial Narrow', sans-serif; letter-spacing: -.055em; margin: 0; }.orbit-heading h2 i { color: var(--or-accent); font-style: italic; }.orbit-heading button { align-items: center; background: transparent; border: 0; color: var(--or-ink); display: inline-flex; font-size: 9px; font-weight: 800; gap: 6px; padding: 8px 0; }
.orbit-stage { min-height: 430px; position: relative; }.team-name { display: flex; flex-direction: column; position: absolute; top: 145px; z-index: 2; }.team-name.home { left: 2%; }.team-name.away { align-items: flex-end; right: 2%; }.team-name > span { color: var(--or-accent-ink); font: 800 9px 'SFMono-Regular', monospace; letter-spacing: .14em; }.team-name strong { font: 800 clamp(30px, 4vw, 52px)/.9 'Arial Narrow', sans-serif; letter-spacing: -.05em; margin: 6px 0 8px; }.team-name small { color: var(--or-muted); font: 8px 'SFMono-Regular', monospace; }
.agent-orbit { height: 410px; left: 50%; position: absolute; top: 1px; transform: translateX(-50%); width: 410px; }.orbit-path { border: 1px dashed var(--or-line); border-radius: 50%; inset: 39px; position: absolute; }.orbit-path::before, .orbit-path::after { border: 1px solid var(--or-line); border-radius: 50%; content: ''; position: absolute; }.orbit-path::before { inset: 48px; }.orbit-path::after { inset: 92px; }
.consensus-ring { align-items: center; background: conic-gradient(var(--or-accent) 0 64.2%, color-mix(in srgb, var(--or-accent) 42%, transparent) 64.2% 84.9%, color-mix(in srgb, var(--or-ink) 23%, transparent) 84.9% 100%); border-radius: 50%; display: flex; inset: 94px; justify-content: center; padding: 12px; position: absolute; }.consensus-core { align-items: center; background: var(--or-bg); border: 1px solid var(--or-line); border-radius: 50%; display: flex; flex-direction: column; inset: 12px; justify-content: center; position: absolute; }.consensus-core span, .consensus-core small { color: var(--or-muted); font-size: 8px; }.consensus-core strong { font: 800 47px 'SFMono-Regular', monospace; letter-spacing: -.11em; margin: 7px 0; }
.agent-satellite { align-items: center; backdrop-filter: blur(12px); background: var(--or-surface); border: 1px solid var(--or-line); border-radius: 50%; display: flex; flex-direction: column; height: 82px; justify-content: center; position: absolute; width: 82px; z-index: 2; }.agent-satellite > span { color: var(--or-accent-ink); font: 800 8px 'SFMono-Regular', monospace; }.agent-satellite strong { font-size: 8px; margin: 4px 0 2px; }.agent-satellite small { color: var(--or-muted); font: 7px 'SFMono-Regular', monospace; }.satellite-one { left: 12px; top: 163px; }.satellite-two { left: 164px; top: 0; }.satellite-three { right: 8px; top: 163px; }.satellite-four { bottom: 0; left: 164px; }
.orbit-outcomes { bottom: 4px; display: flex; gap: 38px; left: 50%; position: absolute; transform: translateX(-50%); white-space: nowrap; }.orbit-outcomes div { align-items: center; display: flex; flex-direction: column; gap: 3px; }.orbit-outcomes span { color: var(--or-muted); font-size: 8px; }.orbit-outcomes strong { font: 800 12px 'SFMono-Regular', monospace; }.orbit-outcomes div:first-child strong { color: var(--or-accent-ink); }
.orbit-insight { align-items: end; background: var(--or-surface); border: 1px solid var(--or-line); border-radius: 160px 160px 0 0; display: grid; gap: 35px; grid-template-columns: 1.1fr 1fr auto; margin: 0 -42px; min-height: 190px; padding: 48px 68px 30px; position: relative; }.insight-lead > span { color: var(--or-accent-ink); font: 800 8px 'SFMono-Regular', monospace; text-transform: uppercase; }.insight-lead h3 { font: 800 24px 'Arial Narrow', sans-serif; letter-spacing: -.04em; margin: 7px 0; }.insight-lead p { color: var(--or-muted); font-size: 9px; line-height: 1.5; margin: 0; max-width: 38ch; }.insight-wave { display: grid; gap: 11px; grid-template-columns: repeat(3, 1fr); }.insight-wave article { align-items: center; aspect-ratio: 1; border: 1px solid var(--or-line); border-radius: 50%; display: flex; flex-direction: column; justify-content: center; text-align: center; }.insight-wave strong { color: var(--or-accent-ink); font: 800 12px 'SFMono-Regular', monospace; }.insight-wave span { color: var(--or-muted); font-size: 7px; line-height: 1.25; margin-top: 5px; max-width: 10ch; }.orbit-action { align-items: center; background: var(--or-ink); border: 0; border-radius: 999px; color: var(--or-bg); display: inline-flex; font-size: 9px; font-weight: 800; gap: 6px; padding: 12px 15px; white-space: nowrap; }.orbit-action:hover { background: var(--or-accent); color: #fff; transform: translateY(-2px); }
@media (prefers-reduced-motion: no-preference) { .agent-satellite { animation: orbit-float 4.5s ease-in-out infinite; }.agent-satellite:nth-of-type(3) { animation-delay: -.7s; }.agent-satellite:nth-of-type(4) { animation-delay: -1.4s; }.agent-satellite:nth-of-type(5) { animation-delay: -2.1s; }.consensus-ring { animation: consensus-enter 800ms cubic-bezier(.16,1,.3,1) both; } @keyframes orbit-float { 50% { transform: translateY(-6px); } } @keyframes consensus-enter { from { opacity: 0; transform: scale(.82); } } }
@media (max-width: 850px) { .orbit-nav { grid-template-columns: auto 1fr auto; }.orbit-nav nav { display: none; }.orbit-stage { min-height: 510px; }.team-name { top: 365px; }.team-name.home { left: 12%; }.team-name.away { right: 12%; }.orbit-insight { border-radius: 90px 90px 0 0; grid-template-columns: 1fr 1fr; padding-left: 45px; padding-right: 45px; }.orbit-action { grid-column: 1 / -1; justify-self: start; } }
@media (max-width: 580px) { .orbit-frame { border-radius: 18px; padding: 9px; }.orbit-nav { gap: 8px; padding-left: 10px; }.orbit-competition span, .orbit-avatar { display: none; }.orbit-main { padding: 28px 9px 0; }.orbit-heading { grid-template-columns: 1fr; }.orbit-heading h2 { font-size: 43px; }.orbit-heading button { justify-self: start; margin-top: 9px; }.agent-orbit { height: 330px; transform: translateX(-50%) scale(.78); transform-origin: top center; width: 410px; }.orbit-stage { min-height: 440px; }.team-name { top: 285px; }.team-name strong { font-size: 32px; }.team-name small { display: none; }.orbit-outcomes { bottom: 18px; gap: 19px; }.orbit-insight { border-radius: 60px 60px 0 0; grid-template-columns: 1fr; margin: 0 -18px; padding: 38px 27px 26px; }.insight-wave { max-width: 310px; }.orbit-action { grid-column: auto; } }
</style>
