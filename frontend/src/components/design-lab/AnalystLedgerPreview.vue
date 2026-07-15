<template>
  <section :class="['ledger-frame', `ledger-${theme}`]" aria-label="Analyst Ledger design concept">
    <header class="ledger-topbar">
      <a class="ledger-wordmark" href="#"><span>SO</span><strong>SOCCEROCTOPUS</strong></a>
      <span class="ledger-status"><i></i> prediction systems / online</span>
      <nav><a class="active" href="#">Overview</a><a href="#">Groups</a><a href="#">Predict</a><a href="#">Tournament</a><a href="#">Markets</a></nav>
      <button class="ledger-user" type="button">RO <ChevronDown :size="13" /></button>
    </header>

    <main class="ledger-main">
      <div class="ledger-title-row">
        <div><p class="ledger-kicker">Competition 01 / FIFA World Cup 2026</p><h2>Evidence before instinct.</h2><p class="ledger-deck">The current field, the current model, and the evidence behind the next decision.</p></div>
        <button class="ledger-switch" type="button"><span>WC26</span><strong>World Cup 2026</strong><ChevronDown :size="14" /></button>
      </div>

      <div class="ledger-toolbar">
        <span>Workspace: overview</span><span>48 teams / 12 groups / 104 matches</span><button type="button">Run a prediction <ArrowUpRight :size="14" /></button>
      </div>

      <div class="ledger-grid">
        <section class="ledger-table-block">
          <div class="ledger-block-head"><div><span class="ledger-index">A1</span><div><small>World Cup 2026</small><h3>Group strength ledger</h3></div></div><span class="ledger-note">ELO / rank</span></div>
          <div class="table-head"><span>Group</span><span>Team</span><span>ELO</span><span>Rank</span></div>
          <div v-for="row in groupRows" :key="row.group + row.team" class="table-row">
            <span class="group-code">{{ row.group }}</span><strong><i :class="['ledger-crest', row.tone]">{{ row.code }}</i>{{ row.team }}</strong><span>{{ row.elo }}</span><span>#{{ row.rank }}</span>
          </div>
          <button class="ledger-link" type="button">Open all 12 groups <ArrowRight :size="14" /></button>
        </section>

        <section class="ledger-prediction">
          <div class="ledger-block-head"><div><span class="ledger-index">B1</span><div><small>Predict a match</small><h3>Brazil <em>vs.</em> Germany</h3></div></div><span class="ledger-tag">ready</span></div>
          <div class="ledger-inputs"><div><label>Home team</label><strong>Brazil</strong></div><span>:</span><div><label>Away team</label><strong>Germany</strong></div></div>
          <div class="ledger-result"><p>Most likely score</p><strong>2-1</strong><span>Group stage</span></div>
          <div class="ledger-odds"><div><span>H</span><strong>64.2%</strong></div><div><span>D</span><strong>20.7%</strong></div><div><span>A</span><strong>15.1%</strong></div></div>
          <div class="ledger-confidence"><span>Swarm confidence</span><strong>78.4%</strong><i><b></b></i></div>
          <button class="ledger-primary" type="button">View full prediction <ArrowRight :size="14" /></button>
        </section>
      </div>

      <section class="ledger-markets">
        <div class="ledger-block-head"><div><span class="ledger-index">C1</span><div><small>Prediction markets</small><h3>Questions ready to list</h3></div></div><span class="ledger-note">Kalshi / Polymarket</span></div>
        <div class="market-line" v-for="market in markets" :key="market.question"><span>{{ market.kind }}</span><strong>{{ market.question }}</strong><b>{{ market.price }}</b><ArrowUpRight :size="14" /></div>
      </section>

      <section class="ledger-agents">
        <div class="ledger-block-head"><div><span class="ledger-index">D1</span><div><small>Swarm composition</small><h3>Agent inputs</h3></div></div><span class="ledger-note">weights from current portal</span></div>
        <div class="agent-ledger-row" v-for="agent in agents" :key="agent.name"><span>{{ agent.code }}</span><strong>{{ agent.name }}</strong><small>{{ agent.detail }}</small><b>{{ agent.weight }}</b></div>
      </section>
    </main>
  </section>
</template>

<script setup>
import { ArrowRight, ArrowUpRight, ChevronDown } from '@lucide/vue'

defineProps({ theme: { type: String, default: 'light' } })

const groupRows = [
  { group: 'A', team: 'Mexico', code: 'MX', tone: 'green', elo: '1794', rank: '14' },
  { group: 'A', team: 'Japan', code: 'JP', tone: 'red', elo: '1721', rank: '18' },
  { group: 'C', team: 'England', code: 'EN', tone: 'blue', elo: '1872', rank: '4' },
  { group: 'C', team: 'Colombia', code: 'CO', tone: 'yellow', elo: '1810', rank: '12' },
  { group: 'F', team: 'Brazil', code: 'BR', tone: 'green', elo: '1864', rank: '5' },
  { group: 'H', team: 'Argentina', code: 'AR', tone: 'blue', elo: '1912', rank: '1' },
]

const markets = [
  { kind: 'MATCH', question: 'Will Brazil win against Germany?', price: '64.2¢' },
  { kind: 'SCORE', question: 'Will the most likely score be 2-1?', price: '14.8¢' },
  { kind: 'FUTURE', question: 'Will Argentina reach the final?', price: '38.6¢' },
]

const agents = [
  { code: 'ST', name: 'Statistical Agent', detail: 'ELO / Poisson / SofaScore', weight: '1.8×' },
  { code: 'VI', name: 'Video Intelligence Agent', detail: 'YouTube / sentiment', weight: '1.0×' },
  { code: 'RF', name: 'Recent Form Agent', detail: 'last 10 / trajectory', weight: '1.3×' },
  { code: 'TA', name: 'Tactical Agent', detail: 'style matchup matrix', weight: '1.2×' },
  { code: 'AG', name: 'Aggregator Agent', detail: 'consensus / narrative', weight: '-' },
]
</script>

<style scoped>
.ledger-frame { --ld-bg: #ecece6; --ld-surface: #f7f7f1; --ld-ink: #171815; --ld-muted: #74776e; --ld-line: #c9cbc0; --ld-accent: #607b35; --ld-soft: #dce3cc; background: var(--ld-bg); border: 1px solid #c7c9bf; color: var(--ld-ink); }
.ledger-frame.ledger-dark { --ld-bg: #131512; --ld-surface: #1a1d19; --ld-ink: #edf0e8; --ld-muted: #9aa294; --ld-line: #3a4037; --ld-accent: #9bb85a; --ld-soft: #334127; border-color: #3a4037; }
.ledger-topbar { align-items: center; border-bottom: 1px solid var(--ld-line); display: grid; gap: 24px; grid-template-columns: auto auto 1fr auto; min-height: 64px; padding: 0 34px; }.ledger-wordmark { align-items: center; color: var(--ld-ink); display: inline-flex; font: 800 11px 'SFMono-Regular', monospace; gap: 9px; text-decoration: none; }.ledger-wordmark span { align-items: center; background: var(--ld-ink); color: var(--ld-bg); display: inline-flex; font-size: 8px; height: 24px; justify-content: center; width: 24px; }.ledger-status { color: var(--ld-muted); font: 8px 'SFMono-Regular', monospace; text-transform: uppercase; }.ledger-status i { background: var(--ld-accent); border-radius: 50%; display: inline-block; height: 5px; margin-right: 5px; width: 5px; }.ledger-topbar nav { display: flex; gap: 19px; justify-content: center; }.ledger-topbar nav a { color: var(--ld-muted); font-size: 10px; font-weight: 700; text-decoration: none; }.ledger-topbar nav a.active { color: var(--ld-ink); text-decoration: underline; text-decoration-color: var(--ld-accent); text-decoration-thickness: 2px; text-underline-offset: 5px; }.ledger-user { align-items: center; background: transparent; border: 1px solid var(--ld-line); color: var(--ld-ink); display: inline-flex; font: 8px 'SFMono-Regular', monospace; gap: 5px; padding: 7px 8px; }
.ledger-main { margin: auto; max-width: 1180px; padding: 42px 34px 44px; }.ledger-title-row { align-items: end; display: flex; gap: 30px; justify-content: space-between; }.ledger-kicker, .ledger-block-head small { color: var(--ld-accent); font: 800 8px 'SFMono-Regular', monospace; letter-spacing: .1em; margin: 0 0 10px; text-transform: uppercase; }.ledger-title-row h2 { font: 800 clamp(38px, 6vw, 70px)/.9 'Arial Narrow', sans-serif; letter-spacing: -.065em; margin: 0; }.ledger-deck { color: var(--ld-muted); font-size: 12px; line-height: 1.5; margin: 14px 0 0; max-width: 44ch; }.ledger-switch { align-items: center; background: var(--ld-surface); border: 1px solid var(--ld-line); color: var(--ld-ink); display: inline-flex; font-size: 10px; gap: 8px; padding: 9px 10px; }.ledger-switch span { background: var(--ld-accent); color: #fff; font: 800 8px 'SFMono-Regular', monospace; padding: 8px 6px; }.ledger-switch strong { font-size: 10px; }.ledger-toolbar { align-items: center; border-bottom: 1px solid var(--ld-line); border-top: 1px solid var(--ld-line); color: var(--ld-muted); display: flex; font: 8px 'SFMono-Regular', monospace; justify-content: space-between; margin-top: 37px; padding: 11px 0; text-transform: uppercase; }.ledger-toolbar button { align-items: center; background: var(--ld-ink); border: 0; color: var(--ld-bg); display: inline-flex; font: 800 9px 'Helvetica Neue', sans-serif; gap: 6px; padding: 9px 11px; text-transform: none; }.ledger-toolbar button:hover { background: var(--ld-accent); color: #fff; }
.ledger-grid { display: grid; grid-template-columns: 1.25fr .75fr; }.ledger-table-block, .ledger-prediction, .ledger-markets, .ledger-agents { border-bottom: 1px solid var(--ld-line); padding: 25px 0; }.ledger-table-block { padding-right: 25px; }.ledger-prediction { border-left: 1px solid var(--ld-line); padding-left: 25px; }.ledger-block-head { align-items: start; display: flex; justify-content: space-between; margin-bottom: 19px; }.ledger-block-head > div { align-items: start; display: flex; gap: 10px; }.ledger-index { color: var(--ld-accent); font: 800 9px 'SFMono-Regular', monospace; }.ledger-block-head h3 { font: 800 19px 'Arial Narrow', sans-serif; letter-spacing: -.035em; margin: 0; }.ledger-note { color: var(--ld-muted); font: 8px 'SFMono-Regular', monospace; text-transform: uppercase; }
.table-head, .table-row { display: grid; gap: 10px; grid-template-columns: 45px 1fr 55px 42px; }.table-head { border-bottom: 1px solid var(--ld-line); color: var(--ld-muted); font: 8px 'SFMono-Regular', monospace; padding: 0 0 9px; text-transform: uppercase; }.table-row { align-items: center; border-bottom: 1px solid var(--ld-line); min-height: 39px; }.table-row > span { color: var(--ld-muted); font: 9px 'SFMono-Regular', monospace; }.table-row strong { align-items: center; display: flex; font-size: 10px; gap: 7px; }.group-code { color: var(--ld-accent) !important; font-weight: 800 !important; }.ledger-crest { align-items: center; border-radius: 3px; color: #fff; display: inline-flex; font: 800 7px 'SFMono-Regular', monospace; height: 18px; justify-content: center; width: 22px; }.ledger-crest.green { background: #4e7549; }.ledger-crest.red { background: #a8534d; }.ledger-crest.blue { background: #4d6e9d; }.ledger-crest.yellow { background: #a19143; }.ledger-link { align-items: center; background: transparent; border: 0; color: var(--ld-accent); display: inline-flex; font-size: 9px; font-weight: 800; gap: 5px; margin-top: 15px; padding: 0; }
.ledger-tag { background: var(--ld-soft); color: var(--ld-accent); font: 800 8px 'SFMono-Regular', monospace; padding: 6px 7px; text-transform: uppercase; }.ledger-inputs { align-items: end; border-bottom: 1px solid var(--ld-line); display: grid; grid-template-columns: 1fr auto 1fr; padding-bottom: 15px; }.ledger-inputs > div { display: flex; flex-direction: column; gap: 6px; }.ledger-inputs label { color: var(--ld-muted); font-size: 8px; }.ledger-inputs strong { font: 800 18px 'Arial Narrow', sans-serif; }.ledger-inputs > span { color: var(--ld-accent); font: 800 15px 'SFMono-Regular', monospace; padding: 0 11px; }.ledger-result { align-items: center; display: flex; flex-direction: column; padding: 22px 0 16px; }.ledger-result p { color: var(--ld-muted); font-size: 8px; margin: 0 0 5px; }.ledger-result strong { font: 800 43px 'SFMono-Regular', monospace; letter-spacing: -.11em; }.ledger-result span { color: var(--ld-muted); font: 8px 'SFMono-Regular', monospace; margin-top: 6px; text-transform: uppercase; }.ledger-odds { border-bottom: 1px solid var(--ld-line); border-top: 1px solid var(--ld-line); display: grid; grid-template-columns: repeat(3, 1fr); padding: 12px 0; }.ledger-odds div { display: flex; flex-direction: column; gap: 5px; }.ledger-odds div + div { border-left: 1px solid var(--ld-line); padding-left: 12px; }.ledger-odds span { color: var(--ld-muted); font: 800 8px 'SFMono-Regular', monospace; }.ledger-odds strong { font: 800 15px 'SFMono-Regular', monospace; }.ledger-odds div:first-child strong { color: var(--ld-accent); }.ledger-confidence { display: grid; gap: 7px; grid-template-columns: 1fr auto; margin-top: 17px; }.ledger-confidence span { color: var(--ld-muted); font-size: 9px; }.ledger-confidence strong { color: var(--ld-accent); font: 800 15px 'SFMono-Regular', monospace; }.ledger-confidence i { background: var(--ld-soft); grid-column: 1 / -1; height: 4px; }.ledger-confidence b { background: var(--ld-accent); display: block; height: 100%; width: 78.4%; }.ledger-primary { align-items: center; background: var(--ld-accent); border: 0; color: #fff; display: inline-flex; font-size: 9px; font-weight: 800; gap: 6px; margin-top: 20px; padding: 10px 11px; }.ledger-primary:hover { filter: brightness(1.08); }
.ledger-markets { display: grid; grid-template-columns: 1.05fr 1fr; }.ledger-markets .ledger-block-head { grid-row: 1 / span 3; margin: 0; padding-right: 25px; }.market-line { align-items: center; border-bottom: 1px solid var(--ld-line); display: grid; gap: 11px; grid-template-columns: 56px 1fr 45px 14px; min-height: 37px; }.market-line span { color: var(--ld-accent); font: 800 7px 'SFMono-Regular', monospace; }.market-line strong { font-size: 9px; }.market-line b { font: 800 10px 'SFMono-Regular', monospace; text-align: right; }.market-line svg { color: var(--ld-muted); }.ledger-agents { display: grid; grid-template-columns: .65fr 1.35fr; }.ledger-agents .ledger-block-head { grid-row: 1 / span 5; margin: 0; padding-right: 25px; }.agent-ledger-row { align-items: center; border-bottom: 1px solid var(--ld-line); display: grid; gap: 12px; grid-template-columns: 27px 1fr 1.1fr 36px; min-height: 35px; }.agent-ledger-row > span { color: var(--ld-accent); font: 800 8px 'SFMono-Regular', monospace; }.agent-ledger-row strong { font-size: 9px; }.agent-ledger-row small { color: var(--ld-muted); font: 8px 'SFMono-Regular', monospace; }.agent-ledger-row b { font: 800 10px 'SFMono-Regular', monospace; text-align: right; }
@media (max-width: 820px) { .ledger-topbar { grid-template-columns: auto 1fr auto; padding: 0 18px; }.ledger-status, .ledger-topbar nav { display: none; }.ledger-main { padding-left: 18px; padding-right: 18px; }.ledger-grid { grid-template-columns: 1fr; }.ledger-table-block { padding-right: 0; }.ledger-prediction { border-left: 0; padding-left: 0; }.ledger-markets, .ledger-agents { grid-template-columns: 1fr; }.ledger-markets .ledger-block-head, .ledger-agents .ledger-block-head { grid-row: auto; padding-right: 0; }.ledger-title-row { align-items: start; flex-direction: column; }.ledger-switch { align-self: flex-start; } }
@media (max-width: 520px) { .ledger-toolbar { align-items: start; flex-direction: column; gap: 10px; }.ledger-toolbar button { width: 100%; justify-content: center; }.ledger-title-row h2 { font-size: 49px; }.table-head, .table-row { grid-template-columns: 33px 1fr 47px 35px; }.table-row strong { font-size: 9px; }.market-line { grid-template-columns: 46px 1fr 39px 12px; }.market-line strong { font-size: 8px; }.agent-ledger-row { gap: 7px; grid-template-columns: 24px 1fr 34px; }.agent-ledger-row small { display: none; } }
</style>
