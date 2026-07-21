<template>
  <section :class="['atlas-frame', `atlas-${theme}`]" aria-label="Tournament Atlas design concept">
    <header class="atlas-nav">
      <a class="atlas-brand" href="#"><span>SO</span><strong>SoccerOctopus</strong></a>
      <div class="atlas-competition"><small>Competition workspace</small><strong>FIFA World Cup 2026</strong></div>
      <nav><a class="active" href="#">Tournament</a><a href="#">Groups</a><a href="#">Predict match</a><a href="#">Markets</a></nav>
      <button class="atlas-user" type="button">RO</button>
    </header>

    <main class="atlas-main">
      <section class="atlas-hero">
        <div class="atlas-hero-copy"><p class="atlas-kicker">Simulation / full tournament</p><h2>From groups<br /><i>to the final.</i></h2><p>Browse live group-stage results or run the full bracket through the swarm. Official results stay locked; only the remaining fixtures move.</p><div class="atlas-actions"><button type="button">Run tournament simulation <ArrowRight :size="15" /></button><span>Monte Carlo · 104-match bracket</span></div></div>
        <div class="atlas-year" aria-hidden="true">26</div>
        <div class="atlas-podium">
          <span class="atlas-podium-label">Latest model projection</span>
          <div class="podium-row"><div class="podium-place second"><small>runner-up</small><strong>France</strong></div><div class="podium-place first"><small>champion</small><strong>Argentina</strong><b>22.8% final win probability</b></div><div class="podium-place third"><small>third place</small><strong>Brazil</strong></div></div>
        </div>
      </section>

      <section class="atlas-bracket">
        <div class="atlas-section-label"><span>01</span><div><small>Knockout path</small><h3>Predicted route to the final</h3></div><span class="atlas-official">official results locked / predicted rounds open</span></div>
        <div class="rounds">
          <div v-for="round in rounds" :key="round.name" class="round"><header><strong>{{ round.name }}</strong><span>{{ round.count }}</span></header><div v-for="match in round.matches" :key="match.home" class="bracket-match"><span :class="{ winner: match.homeWinner }">{{ match.home }}</span><b>{{ match.score }}</b><span :class="{ winner: !match.homeWinner }">{{ match.away }}</span><small>{{ match.state }}</small></div></div>
        </div>
      </section>

      <div class="atlas-lower">
        <section class="atlas-groups">
          <div class="atlas-section-label"><span>02</span><div><small>Group stage</small><h3>Representative standings</h3></div></div>
          <div class="standing-head"><span>Group</span><span>Leader</span><span>Pts</span><span>GD</span></div>
          <div v-for="standing in standings" :key="standing.group" class="standing-line"><strong>{{ standing.group }}</strong><span><i :class="['atlas-crest', standing.tone]">{{ standing.code }}</i>{{ standing.team }}</span><b>{{ standing.points }}</b><small>{{ standing.gd }}</small></div>
          <button class="atlas-link" type="button">Browse all groups <ArrowUpRight :size="14" /></button>
        </section>
        <section class="atlas-markets">
          <div class="atlas-section-label"><span>03</span><div><small>Prediction markets</small><h3>Futures from this simulation</h3></div></div>
          <div class="future-row"><span>Champion</span><strong>Argentina</strong><b>22.8%</b></div><div class="future-row"><span>Reach final</span><strong>Brazil</strong><b>41.4%</b></div><div class="future-row"><span>Win Group A</span><strong>Mexico</strong><b>60.0%</b></div>
          <button class="atlas-link" type="button">Generate futures markets <ArrowUpRight :size="14" /></button>
        </section>
      </div>
    </main>
  </section>
</template>

<script setup>
import { ArrowRight, ArrowUpRight } from '@lucide/vue'

defineProps({ theme: { type: String, default: 'light' } })

const rounds = [
  { name: 'Round of 32', count: '16 matches', matches: [{ home: 'Argentina', away: 'Senegal', score: '2-0', state: 'predicted', homeWinner: true }, { home: 'Brazil', away: 'Australia', score: '2-1', state: 'predicted', homeWinner: true }] },
  { name: 'Quarter finals', count: '4 matches', matches: [{ home: 'Argentina', away: 'Portugal', score: '1-0', state: 'predicted', homeWinner: true }, { home: 'Brazil', away: 'France', score: '2-1', state: 'predicted', homeWinner: true }] },
  { name: 'Semi finals', count: '2 matches', matches: [{ home: 'Argentina', away: 'Brazil', score: '2-1', state: 'predicted', homeWinner: true }, { home: 'Spain', away: 'France', score: '1-0', state: 'predicted', homeWinner: true }] },
  { name: 'Final', count: '1 match', matches: [{ home: 'Argentina', away: 'Spain', score: '2-1', state: 'predicted', homeWinner: true }] },
]

const standings = [
  { group: 'A', team: 'Mexico', code: 'MX', tone: 'green', points: '7', gd: '+4' },
  { group: 'C', team: 'Brazil', code: 'BR', tone: 'green', points: '9', gd: '+6' },
  { group: 'F', team: 'Netherlands', code: 'NL', tone: 'blue', points: '7', gd: '+3' },
  { group: 'H', team: 'Spain', code: 'ES', tone: 'red', points: '9', gd: '+7' },
]
</script>

<style scoped>
.atlas-frame { --at-bg: #eee9df; --at-surface: #f8f4eb; --at-ink: #24201c; --at-muted: #7d736a; --at-line: #d2c7b8; --at-accent: #1f7771; --at-soft: #d8e7e0; background: var(--at-bg); border: 1px solid #d0c6b8; color: var(--at-ink); overflow: hidden; }
.atlas-frame.atlas-dark { --at-bg: #121515; --at-surface: #1b201f; --at-ink: #edf1e9; --at-muted: #9ba39d; --at-line: #3b4641; --at-accent: #6db1a0; --at-soft: #25443e; border-color: #3b4641; }
.atlas-nav { align-items: center; border-bottom: 1px solid var(--at-line); display: grid; gap: 28px; grid-template-columns: auto auto 1fr auto; min-height: 68px; padding: 0 35px; }.atlas-brand { align-items: center; color: var(--at-ink); display: inline-flex; font: 800 14px 'Arial Narrow', sans-serif; gap: 9px; text-decoration: none; }.atlas-brand span { align-items: center; background: var(--at-accent); color: #fff; display: inline-flex; font: 800 9px 'SFMono-Regular', monospace; height: 26px; justify-content: center; width: 26px; }.atlas-competition { border-left: 1px solid var(--at-line); display: flex; flex-direction: column; gap: 4px; padding-left: 18px; }.atlas-competition small { color: var(--at-muted); font-size: 8px; }.atlas-competition strong { font: 800 11px 'SFMono-Regular', monospace; }.atlas-nav nav { display: flex; gap: 22px; justify-content: end; }.atlas-nav nav a { color: var(--at-muted); font-size: 10px; font-weight: 700; text-decoration: none; }.atlas-nav nav a.active { color: var(--at-accent); }.atlas-user { align-items: center; background: var(--at-surface); border: 1px solid var(--at-line); color: var(--at-ink); display: inline-flex; font: 800 8px 'SFMono-Regular', monospace; height: 28px; justify-content: center; width: 28px; }
.atlas-main { margin: auto; max-width: 1220px; padding: 0 35px 44px; }.atlas-hero { border-bottom: 1px solid var(--at-line); display: grid; grid-template-columns: 1fr .9fr; min-height: 300px; overflow: hidden; padding: 46px 0 37px; position: relative; }.atlas-hero-copy { position: relative; z-index: 1; }.atlas-kicker, .atlas-section-label small { color: var(--at-accent); font: 800 8px 'SFMono-Regular', monospace; letter-spacing: .1em; margin: 0 0 13px; text-transform: uppercase; }.atlas-hero h2 { font: 800 clamp(52px, 8vw, 95px)/.82 'Arial Narrow', sans-serif; letter-spacing: -.08em; margin: 0; }.atlas-hero h2 i { color: var(--at-accent); font-style: normal; }.atlas-hero-copy > p:not(.atlas-kicker) { color: var(--at-muted); font-size: 12px; line-height: 1.55; margin: 22px 0 0; max-width: 43ch; }.atlas-actions { align-items: center; display: flex; gap: 14px; margin-top: 24px; }.atlas-actions button { align-items: center; background: var(--at-accent); border: 0; color: #fff; display: inline-flex; font-size: 9px; font-weight: 800; gap: 7px; padding: 11px 13px; }.atlas-actions button:hover { filter: brightness(1.08); }.atlas-actions span { color: var(--at-muted); font: 8px 'SFMono-Regular', monospace; }.atlas-year { align-self: center; color: var(--at-soft); font: 900 270px/.7 'Arial Narrow', sans-serif; letter-spacing: -.15em; margin-left: -35px; user-select: none; }.atlas-podium { align-self: end; background: var(--at-surface); border-left: 1px solid var(--at-line); border-top: 1px solid var(--at-line); bottom: 0; padding: 17px 20px 15px; position: absolute; right: 0; width: 46%; }.atlas-podium-label { color: var(--at-muted); font: 8px 'SFMono-Regular', monospace; text-transform: uppercase; }.podium-row { align-items: end; display: grid; gap: 12px; grid-template-columns: 1fr 1.15fr 1fr; margin-top: 15px; }.podium-place { display: flex; flex-direction: column; gap: 4px; }.podium-place small { color: var(--at-muted); font-size: 8px; }.podium-place strong { font: 800 16px 'Arial Narrow', sans-serif; }.podium-place b { color: var(--at-accent); font: 800 10px 'SFMono-Regular', monospace; }.podium-place.first { border-left: 2px solid var(--at-accent); padding-left: 10px; }
.atlas-section-label { align-items: start; display: flex; gap: 10px; margin-bottom: 18px; }.atlas-section-label > span:first-child { color: var(--at-accent); font: 800 9px 'SFMono-Regular', monospace; }.atlas-section-label h3 { font: 800 20px 'Arial Narrow', sans-serif; letter-spacing: -.035em; margin: 0; }.atlas-official { color: var(--at-muted); font: 8px 'SFMono-Regular', monospace; margin-left: auto; text-align: right; text-transform: uppercase; }.atlas-bracket { border-bottom: 1px solid var(--at-line); padding: 27px 0 32px; }.rounds { display: grid; grid-template-columns: repeat(4, 1fr); gap: 13px; }.round { border-left: 2px solid var(--at-line); padding-left: 11px; }.round:nth-child(4) { border-color: var(--at-accent); }.round header { align-items: baseline; display: flex; justify-content: space-between; margin-bottom: 12px; }.round header strong { font: 800 10px 'SFMono-Regular', monospace; }.round header span { color: var(--at-muted); font: 8px 'SFMono-Regular', monospace; }.bracket-match { background: var(--at-surface); border: 1px solid var(--at-line); display: grid; gap: 5px; grid-template-columns: 1fr auto; margin-bottom: 9px; padding: 9px 10px; position: relative; }.bracket-match::after { background: var(--at-line); content: ''; height: 1px; left: 100%; position: absolute; top: 50%; width: 13px; }.round:last-child .bracket-match::after { display: none; }.bracket-match span { font-size: 10px; }.bracket-match span.winner { color: var(--at-accent); font-weight: 800; }.bracket-match b { font: 800 10px 'SFMono-Regular', monospace; grid-column: 2; grid-row: 1 / span 2; }.bracket-match small { color: var(--at-muted); font: 7px 'SFMono-Regular', monospace; grid-column: 1 / -1; text-transform: uppercase; }
.atlas-lower { display: grid; gap: 35px; grid-template-columns: 1fr 1fr; }.atlas-groups, .atlas-markets { padding-top: 27px; }.standing-head, .standing-line { display: grid; gap: 10px; grid-template-columns: 44px 1fr 40px 40px; }.standing-head { border-bottom: 1px solid var(--at-line); color: var(--at-muted); font: 8px 'SFMono-Regular', monospace; padding-bottom: 9px; text-transform: uppercase; }.standing-line { align-items: center; border-bottom: 1px solid var(--at-line); min-height: 40px; }.standing-line > * { font: 9px 'SFMono-Regular', monospace; }.standing-line strong, .standing-line b { color: var(--at-accent); }.standing-line span { align-items: center; display: flex; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; gap: 7px; }.standing-line small { color: var(--at-muted); }.atlas-crest { align-items: center; border-radius: 3px; color: #fff; display: inline-flex; font: 800 7px 'SFMono-Regular', monospace; height: 18px; justify-content: center; width: 22px; }.atlas-crest.green { background: #4d7654; }.atlas-crest.blue { background: #4c719b; }.atlas-link { align-items: center; background: transparent; border: 0; color: var(--at-accent); display: inline-flex; font-size: 9px; font-weight: 800; gap: 6px; margin-top: 15px; padding: 0; }.future-row { align-items: center; border-bottom: 1px solid var(--at-line); display: grid; gap: 10px; grid-template-columns: 1fr 1fr 55px; min-height: 40px; }.future-row span { color: var(--at-muted); font-size: 9px; }.future-row strong { font-size: 10px; }.future-row b { color: var(--at-accent); font: 800 10px 'SFMono-Regular', monospace; text-align: right; }
@media (max-width: 900px) { .atlas-nav { gap: 14px; grid-template-columns: auto 1fr auto; padding: 0 18px; }.atlas-competition, .atlas-nav nav { display: none; }.atlas-main { padding-left: 18px; padding-right: 18px; }.atlas-hero { grid-template-columns: 1fr; }.atlas-year { position: absolute; right: -10px; top: 55px; }.atlas-podium { width: 72%; }.rounds { gap: 7px; }.bracket-match::after { width: 7px; } }
@media (max-width: 620px) { .atlas-hero { min-height: 490px; padding-top: 34px; }.atlas-hero h2 { font-size: 66px; }.atlas-year { font-size: 205px; top: 110px; }.atlas-podium { width: 100%; }.atlas-actions { align-items: start; flex-direction: column; }.rounds { grid-template-columns: 1fr 1fr; row-gap: 22px; }.round:nth-child(2) { border-color: var(--at-accent); }.round:nth-child(2) .bracket-match::after, .round:nth-child(4) .bracket-match::after { display: none; }.atlas-lower { grid-template-columns: 1fr; gap: 0; }.atlas-official { display: none; } }
</style>
