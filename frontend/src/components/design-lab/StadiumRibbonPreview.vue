<template>
  <section :class="['ribbon-frame', `ribbon-${theme}`]" aria-label="Stadium Ribbon design concept">
    <div class="ribbon-shell">
      <header class="ribbon-nav">
        <a href="#" class="ribbon-brand"><span>SO</span><strong>SoccerOctopus</strong></a>
        <nav><a class="active" href="#">World Cup 2026</a><a href="#">Predict</a><a href="#">Markets</a></nav>
        <button type="button">Switch competition <ChevronDown :size="14" /></button>
      </header>

      <main>
        <section class="ribbon-hero">
          <div class="ribbon-copy"><p>Full tournament simulation</p><h2>The whole tournament,<br /><i>in one sweep.</i></h2><button type="button">Run simulation <ArrowRight :size="15" /></button></div>
          <div class="ribbon-ball" aria-hidden="true"><span>26</span></div>
          <div class="ribbon-summary">
            <div><strong>48</strong><span>teams</span></div><div><strong>12</strong><span>groups</span></div><div><strong>104</strong><span>matches</span></div>
          </div>
        </section>

        <section class="journey">
          <div class="journey-curve curve-one"></div><div class="journey-curve curve-two"></div>
          <div v-for="stop in stops" :key="stop.name" :class="['journey-stop', stop.position]">
            <span>{{ stop.short }}</span><strong>{{ stop.name }}</strong><small>{{ stop.detail }}</small>
          </div>
          <div class="journey-champion"><small>Projected champion</small><strong>Argentina</strong><span>22.8%</span></div>
        </section>

        <section class="ribbon-data">
          <div class="ribbon-groups">
            <h3>Group pulse</h3>
            <div class="group-bubbles">
              <article v-for="group in groups" :key="group.label"><span>{{ group.label }}</span><strong>{{ group.team }}</strong><small>{{ group.stat }}</small></article>
            </div>
            <button type="button">All groups <ArrowUpRight :size="14" /></button>
          </div>
          <div class="ribbon-market">
            <span class="market-label">Tournament futures</span>
            <div class="market-orbit"><strong>22.8%</strong><span>Argentina<br />champion</span></div>
            <div class="market-copy"><h3>Turn a simulation into market questions.</h3><p>Generate champion, finalist, and group qualification contracts for Kalshi and Polymarket.</p><button type="button">Open markets <ArrowRight :size="14" /></button></div>
          </div>
        </section>
      </main>
    </div>
  </section>
</template>

<script setup>
import { ArrowRight, ArrowUpRight, ChevronDown } from '@lucide/vue'

defineProps({ theme: { type: String, default: 'light' } })

const stops = [
  { short: 'G', name: 'Group stage', detail: '12 groups', position: 'stop-one' },
  { short: '32', name: 'Round of 32', detail: '16 matches', position: 'stop-two' },
  { short: '16', name: 'Round of 16', detail: '8 matches', position: 'stop-three' },
  { short: 'QF', name: 'Quarter-finals', detail: '4 matches', position: 'stop-four' },
  { short: 'SF', name: 'Semi-finals', detail: '2 matches', position: 'stop-five' },
]

const groups = [
  { label: 'A', team: 'Mexico', stat: 'ELO 1855' },
  { label: 'C', team: 'Brazil', stat: 'ELO 2050' },
  { label: 'F', team: 'Netherlands', stat: 'ELO 2005' },
  { label: 'H', team: 'Spain', stat: 'ELO 2045' },
]
</script>

<style scoped>
.ribbon-frame { --rb-bg: #e7e7f0; --rb-surface: #f6f5fb; --rb-ink: #201d33; --rb-muted: #737088; --rb-line: rgba(32,29,51,.17); --rb-accent: #4169b1; --rb-accent-deep: #263f78; --rb-soft: rgba(65,105,177,.13); background: var(--rb-bg); border-radius: 34px; box-shadow: 0 34px 85px rgba(48, 55, 94, .2); color: var(--rb-ink); overflow: hidden; padding: 15px; }
.ribbon-frame.ribbon-dark { --rb-bg: #11131d; --rb-surface: #1c1f2c; --rb-ink: #eff0f7; --rb-muted: #a3a7bb; --rb-line: rgba(239,240,247,.15); --rb-accent: #7195d5; --rb-accent-deep: #a9c4f2; --rb-soft: rgba(113,149,213,.15); box-shadow: 0 34px 85px rgba(0,0,0,.42); }
.ribbon-shell { background: var(--rb-surface); border: 1px solid var(--rb-line); border-radius: 24px; min-height: 800px; overflow: hidden; position: relative; }.ribbon-shell::before { background-image: radial-gradient(circle, var(--rb-line) 1px, transparent 1px); background-size: 13px 13px; content: ''; inset: 0; mask-image: linear-gradient(to bottom, rgba(0,0,0,.45), transparent 60%); opacity: .42; pointer-events: none; position: absolute; }
.ribbon-nav { align-items: center; display: grid; gap: 25px; grid-template-columns: auto 1fr auto; min-height: 65px; padding: 0 28px; position: relative; z-index: 4; }.ribbon-brand { align-items: center; color: var(--rb-ink); display: inline-flex; font: 800 14px 'Arial Narrow', sans-serif; gap: 9px; text-decoration: none; }.ribbon-brand span { align-items: center; background: var(--rb-accent); border-radius: 50% 50% 44% 56% / 58% 42% 58% 42%; color: #fff; display: inline-flex; font: 800 8px 'SFMono-Regular', monospace; height: 29px; justify-content: center; transform: rotate(-9deg); width: 29px; }.ribbon-nav nav { display: flex; gap: 22px; justify-content: center; }.ribbon-nav nav a { color: var(--rb-muted); font-size: 10px; font-weight: 700; text-decoration: none; }.ribbon-nav nav a.active { color: var(--rb-accent-deep); }.ribbon-nav > button { align-items: center; background: transparent; border: 1px solid var(--rb-line); border-radius: 999px; color: var(--rb-ink); display: inline-flex; font-size: 9px; font-weight: 800; gap: 7px; padding: 9px 12px; }
.ribbon-hero { min-height: 375px; overflow: hidden; padding: 45px 5.5vw 0; position: relative; }.ribbon-copy { position: relative; z-index: 2; }.ribbon-copy p { color: var(--rb-accent-deep); font: 800 8px 'SFMono-Regular', monospace; letter-spacing: .1em; margin: 0 0 12px; text-transform: uppercase; }.ribbon-copy h2 { font: 800 clamp(48px, 7vw, 86px)/.83 'Arial Narrow', sans-serif; letter-spacing: -.075em; margin: 0; }.ribbon-copy h2 i { color: var(--rb-accent); font-style: italic; }.ribbon-copy button { align-items: center; background: var(--rb-ink); border: 0; border-radius: 999px; color: var(--rb-surface); display: inline-flex; font-size: 9px; font-weight: 800; gap: 7px; margin-top: 24px; padding: 11px 14px; }.ribbon-copy button:hover { background: var(--rb-accent); color: #fff; transform: translateY(-2px); }
.ribbon-ball { align-items: center; background: var(--rb-accent); border-radius: 45% 55% 50% 50% / 60% 42% 58% 40%; display: flex; height: 360px; justify-content: center; position: absolute; right: 5vw; top: 13px; transform: rotate(11deg); width: 360px; }.ribbon-ball::before, .ribbon-ball::after { border: 1px solid rgba(255,255,255,.35); border-radius: 50%; content: ''; position: absolute; }.ribbon-ball::before { inset: 35px -25px; transform: rotate(38deg); }.ribbon-ball::after { inset: -22px 67px; transform: rotate(-27deg); }.ribbon-ball span { color: rgba(255,255,255,.95); font: 900 180px/.8 'Arial Narrow', sans-serif; letter-spacing: -.14em; transform: translateX(-7px) rotate(-11deg); }
.ribbon-summary { align-items: center; backdrop-filter: blur(16px); background: color-mix(in srgb, var(--rb-surface) 78%, transparent); border: 1px solid var(--rb-line); border-radius: 999px; bottom: 33px; display: flex; gap: 28px; padding: 12px 19px; position: absolute; right: 3.5vw; z-index: 2; }.ribbon-summary div { align-items: baseline; display: flex; gap: 5px; }.ribbon-summary strong { color: var(--rb-accent-deep); font: 800 15px 'SFMono-Regular', monospace; }.ribbon-summary span { color: var(--rb-muted); font-size: 8px; }
.journey { background: var(--rb-ink); border-radius: 56% 44% 0 0 / 23% 24% 0 0; color: var(--rb-surface); height: 260px; margin: 0 -6% 0; overflow: hidden; position: relative; }.journey-curve { border: 2px solid color-mix(in srgb, var(--rb-accent) 70%, transparent); border-radius: 50%; height: 310px; position: absolute; width: 125%; }.curve-one { left: -40%; top: 36px; transform: rotate(5deg); }.curve-two { border-color: rgba(255,255,255,.15); right: -47%; top: -110px; transform: rotate(-9deg); }.journey-stop { align-items: center; display: flex; flex-direction: column; position: absolute; text-align: center; z-index: 2; }.journey-stop > span { align-items: center; background: var(--rb-accent); border: 4px solid var(--rb-ink); border-radius: 50%; color: #fff; display: inline-flex; font: 800 8px 'SFMono-Regular', monospace; height: 42px; justify-content: center; width: 42px; }.journey-stop strong { font: 800 10px 'Arial Narrow', sans-serif; margin-top: 6px; }.journey-stop small { color: rgba(255,255,255,.55); font-size: 7px; margin-top: 2px; }.stop-one { left: 10%; top: 92px; }.stop-two { left: 27%; top: 57px; }.stop-three { left: 45%; top: 48px; }.stop-four { left: 63%; top: 72px; }.stop-five { left: 77%; top: 106px; }.journey-champion { align-items: center; background: var(--rb-surface); border-radius: 50%; bottom: -41px; color: var(--rb-ink); display: flex; flex-direction: column; height: 145px; justify-content: flex-start; padding-top: 25px; position: absolute; right: 2%; width: 145px; z-index: 3; }.journey-champion small { color: var(--rb-muted); font-size: 7px; }.journey-champion strong { font: 800 18px 'Arial Narrow', sans-serif; margin: 5px 0; }.journey-champion span { color: var(--rb-accent-deep); font: 800 10px 'SFMono-Regular', monospace; }
.ribbon-data { display: grid; grid-template-columns: 1fr 1fr; min-height: 300px; }.ribbon-data > section { padding: 35px 4vw 40px; }.ribbon-data h3 { font: 800 26px 'Arial Narrow', sans-serif; letter-spacing: -.045em; margin: 0; }.ribbon-groups { background: var(--rb-surface); }.group-bubbles { display: flex; margin: 22px 0 18px; }.group-bubbles article { align-items: center; aspect-ratio: 1; border: 1px solid var(--rb-line); border-radius: 50%; display: flex; flex-direction: column; justify-content: center; margin-left: -8px; min-width: 90px; padding: 10px; text-align: center; transition: transform 240ms cubic-bezier(.16,1,.3,1); width: 22%; }.group-bubbles article:first-child { margin-left: 0; }.group-bubbles article:hover { background: var(--rb-soft); transform: translateY(-7px); z-index: 2; }.group-bubbles span { color: var(--rb-accent-deep); font: 800 8px 'SFMono-Regular', monospace; }.group-bubbles strong { font-size: 9px; margin: 5px 0; }.group-bubbles small { color: var(--rb-muted); font: 7px 'SFMono-Regular', monospace; }.ribbon-groups > button, .market-copy button { align-items: center; background: transparent; border: 0; color: var(--rb-accent-deep); display: inline-flex; font-size: 9px; font-weight: 800; gap: 6px; padding: 0; }
.ribbon-market { background: var(--rb-soft); display: grid; gap: 18px; grid-template-columns: auto 1fr; position: relative; }.market-label { color: var(--rb-accent-deep); font: 800 8px 'SFMono-Regular', monospace; grid-column: 1 / -1; letter-spacing: .08em; text-transform: uppercase; }.market-orbit { align-items: center; border: 1px solid var(--rb-accent); border-radius: 50%; display: flex; flex-direction: column; height: 135px; justify-content: center; position: relative; width: 135px; }.market-orbit::before { border: 1px dashed var(--rb-line); border-radius: 50%; content: ''; inset: -12px; position: absolute; }.market-orbit strong { color: var(--rb-accent-deep); font: 800 20px 'SFMono-Regular', monospace; }.market-orbit span { color: var(--rb-muted); font-size: 8px; line-height: 1.25; margin-top: 6px; text-align: center; }.market-copy { align-self: center; }.market-copy h3 { font-size: 22px; max-width: 12ch; }.market-copy p { color: var(--rb-muted); font-size: 9px; line-height: 1.5; margin: 9px 0 14px; max-width: 34ch; }
@media (prefers-reduced-motion: no-preference) { .ribbon-ball { animation: ball-breathe 6s ease-in-out infinite; }.journey-stop > span { animation: node-pulse 4s ease-in-out infinite; }.journey-stop:nth-of-type(4) > span { animation-delay: -.8s; }.journey-stop:nth-of-type(5) > span { animation-delay: -1.6s; }.journey-stop:nth-of-type(6) > span { animation-delay: -2.4s; } @keyframes ball-breathe { 50% { transform: rotate(6deg) scale(1.025); } } @keyframes node-pulse { 50% { transform: scale(1.08); } } }
@media (max-width: 880px) { .ribbon-nav { grid-template-columns: auto 1fr; }.ribbon-nav nav { display: none; }.ribbon-nav > button { justify-self: end; }.ribbon-ball { height: 300px; opacity: .78; right: -30px; top: 55px; width: 300px; }.ribbon-ball span { font-size: 145px; }.ribbon-copy { max-width: 63%; }.ribbon-summary { right: 20px; }.stop-one { left: 5%; }.stop-two { left: 22%; }.stop-three { left: 40%; }.stop-four { left: 58%; }.stop-five { left: 72%; }.journey-champion { right: -12px; }.ribbon-data { grid-template-columns: 1fr; } }
@media (max-width: 580px) { .ribbon-frame { border-radius: 20px; padding: 8px; }.ribbon-shell { border-radius: 14px; }.ribbon-nav { padding: 0 14px; }.ribbon-nav > button { font-size: 0; padding: 9px; }.ribbon-copy { max-width: 100%; }.ribbon-copy h2 { font-size: 54px; }.ribbon-hero { min-height: 485px; padding-left: 18px; padding-right: 18px; }.ribbon-ball { bottom: 10px; height: 245px; right: -33px; top: auto; width: 245px; }.ribbon-ball span { font-size: 118px; }.ribbon-summary { bottom: 24px; gap: 14px; left: 13px; right: auto; }.journey { border-radius: 58% 42% 0 0 / 12% 12% 0 0; height: 370px; margin-left: -10%; margin-right: -10%; }.journey-stop { transform: scale(.86); }.stop-one { left: 7%; top: 80px; }.stop-two { left: 35%; top: 52px; }.stop-three { left: 65%; top: 72px; }.stop-four { left: 17%; top: 193px; }.stop-five { left: 48%; top: 213px; }.journey-champion { bottom: -26px; right: -3px; }.ribbon-data > section { padding-left: 21px; padding-right: 21px; }.group-bubbles { display: grid; grid-template-columns: repeat(2, 1fr); }.group-bubbles article { margin: -4px 0 0 -4px; min-width: 0; width: 100%; }.ribbon-market { grid-template-columns: 1fr; }.market-orbit { margin: 4px auto; }.market-copy h3 { max-width: none; } }
</style>
