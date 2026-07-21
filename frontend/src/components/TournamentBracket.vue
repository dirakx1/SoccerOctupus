<template>
  <div class="tournament-result">
    <section class="podium-section" :aria-labelledby="podiumHeadingId">
      <div class="result-heading">
        <div>
          <span>{{ t('tournament.result.label') }}</span>
          <h2 :id="podiumHeadingId">{{ t('tournament.result.podium') }}</h2>
        </div>
      </div>

      <div class="podium-summary" data-testid="tournament-podium">
        <article class="podium-place champion-place" data-place="champion">
          <span class="place-rank">01</span>
          <div>
            <p>{{ t('tournament.result.champion') }}</p>
            <strong>{{ result.champion }}</strong>
          </div>
          <div class="champion-probability">
            <span>{{ t('tournament.result.championProbability') }}</span>
            <strong>{{ formatPercent(result.champion_probability) }}</strong>
          </div>
        </article>
        <article class="podium-place" data-place="runner-up">
          <span class="place-rank">02</span>
          <div>
            <p>{{ t('tournament.result.runnerUp') }}</p>
            <strong>{{ result.runner_up }}</strong>
          </div>
        </article>
        <article class="podium-place" data-place="third-place">
          <span class="place-rank">03</span>
          <div>
            <p>{{ t('tournament.result.thirdPlace') }}</p>
            <strong>{{ result.third_place }}</strong>
          </div>
        </article>
      </div>
    </section>

    <section class="bracket-section" :aria-labelledby="bracketHeadingId">
      <div class="result-heading">
        <div>
          <span>{{ t('tournament.result.label') }}</span>
          <h2 :id="bracketHeadingId">{{ t('tournament.result.bracket') }}</h2>
        </div>
      </div>

      <div class="bracket-scroll" tabindex="0" :aria-label="t('tournament.result.bracket')">
        <div class="bracket-grid">
          <section
            v-for="round in rounds"
            :key="round.stage"
            class="bracket-round"
            data-testid="bracket-round"
            :data-stage="round.stage"
          >
            <header>
              <h3>{{ t(round.labelKey) }}</h3>
              <span>{{ t('tournament.rounds.matchCount', round.matches.length, { count: formatInteger(round.matches.length) }) }}</span>
            </header>

            <div class="round-matches">
              <article
                v-for="match in round.matches"
                :key="match.prediction_id"
                class="bracket-match"
                :data-match-id="match.prediction_id"
                :aria-label="matchAriaLabel(match)"
              >
                <div class="match-meta">
                  <span :class="match.is_actual ? 'official-status' : 'predicted-status'">
                    {{ match.is_actual ? t('tournament.match.official') : t('tournament.match.predicted') }}
                  </span>
                  <span>{{ match.most_likely_score }}</span>
                </div>

                <div class="bracket-team" :class="{ winner: isWinner(match, 'home') }">
                  <strong>{{ match.home_team }}</strong>
                  <span v-if="isWinner(match, 'home')" class="winner-label">{{ t('tournament.match.winner') }}</span>
                </div>
                <div class="bracket-team" :class="{ winner: isWinner(match, 'away') }">
                  <strong>{{ match.away_team }}</strong>
                  <span v-if="isWinner(match, 'away')" class="winner-label">{{ t('tournament.match.winner') }}</span>
                </div>

                <p v-if="match.is_actual" class="official-final">{{ t('tournament.match.final') }}</p>
                <p v-else class="match-probabilities">
                  {{ t('tournament.match.probabilities', {
                    homeLabel: t('tournament.match.homeShort'),
                    home: formatPercent(match.home_win_prob),
                    drawLabel: t('tournament.match.drawShort'),
                    draw: formatPercent(match.draw_prob),
                    awayLabel: t('tournament.match.awayShort'),
                    away: formatPercent(match.away_win_prob),
                  }) }}
                </p>
              </article>
            </div>
          </section>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  result: { type: Object, required: true },
})

const { locale, t } = useI18n()
const podiumHeadingId = 'tournament-podium-heading'
const bracketHeadingId = 'tournament-bracket-heading'
const roundOrder = [
  { stage: 'round_of_32', labelKey: 'tournament.rounds.roundOf32' },
  { stage: 'round_of_16', labelKey: 'tournament.rounds.roundOf16' },
  { stage: 'quarter_final', labelKey: 'tournament.rounds.quarterFinal' },
  { stage: 'semi_final', labelKey: 'tournament.rounds.semiFinal' },
  { stage: 'third_place', labelKey: 'tournament.rounds.thirdPlace' },
  { stage: 'final', labelKey: 'tournament.rounds.final' },
]

const rounds = computed(() => {
  const byStage = new Map()
  const matches = Array.isArray(props.result?.knockout_matches) ? props.result.knockout_matches : []
  matches.forEach((match) => {
    if (!byStage.has(match.stage)) byStage.set(match.stage, [])
    byStage.get(match.stage).push(match)
  })
  return roundOrder
    .filter((round) => byStage.has(round.stage))
    .map((round) => ({ ...round, matches: byStage.get(round.stage) }))
})

function formatPercent(value) {
  return new Intl.NumberFormat(locale.value, {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(Number(value) || 0)
}

function formatInteger(value) {
  return new Intl.NumberFormat(locale.value, { maximumFractionDigits: 0 }).format(Number(value) || 0)
}

function isWinner(match, side) {
  return match.outcome === `${side}_win`
}

function matchAriaLabel(match) {
  return t(match.is_actual ? 'tournament.match.officialLabel' : 'tournament.match.predictedLabel', {
    home: match.home_team,
    away: match.away_team,
    score: match.most_likely_score,
  })
}
</script>

<style scoped>
.tournament-result { display: flex; flex-direction: column; gap: var(--space-8); min-width: 0; }
.podium-section, .bracket-section { display: flex; flex-direction: column; gap: var(--space-4); min-width: 0; }
.result-heading { align-items: end; border-bottom: var(--border-width-thin) solid var(--color-border); display: flex; justify-content: space-between; padding-bottom: var(--space-3); }
.result-heading > div { display: flex; flex-direction: column; gap: var(--space-1); }
.result-heading span { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); text-transform: uppercase; }
.result-heading h2 { font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0; }
.podium-summary { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.podium-place { align-items: center; border-top: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-4); grid-template-columns: 2.5rem minmax(0, 1fr); min-height: 6.5rem; padding: var(--space-5); }
.podium-place:last-child { border-left: var(--border-width-thin) solid var(--color-border); }
.champion-place { border-top: 0; grid-column: 1 / -1; grid-template-columns: 2.5rem minmax(0, 1fr) auto; min-height: 8rem; }
.place-rank { color: var(--color-text-subtle); font: var(--font-weight-heavy) var(--font-size-2xl) / 1 var(--font-family-data); }
.podium-place p { color: var(--color-text-muted); font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); margin: 0 0 var(--space-1); text-transform: uppercase; }
.podium-place > div > strong { font-family: var(--font-family-display); font-size: var(--font-size-xl); }
.champion-place > div > strong { color: var(--color-accent); font-size: var(--font-size-2xl); }
.champion-probability { align-items: flex-end; display: flex; flex-direction: column; }
.champion-probability span { color: var(--color-text-muted); font-size: var(--font-size-xs); }
.champion-probability strong { color: var(--color-text); font: var(--font-weight-heavy) var(--font-size-2xl) / 1 var(--font-family-data); margin-top: var(--space-2); }
.bracket-scroll { max-width: 100%; min-width: 0; overflow-x: auto; overscroll-behavior-inline: contain; padding-bottom: var(--space-3); }
.bracket-scroll:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.bracket-grid { display: grid; gap: var(--space-3); grid-auto-columns: 17.5rem; grid-auto-flow: column; min-width: max-content; }
.bracket-round { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); min-width: 0; }
.bracket-round > header { border-bottom: var(--border-width-thin) solid var(--color-border); min-height: 4.75rem; padding: var(--space-4); }
.bracket-round h3 { font-family: var(--font-family-display); font-size: var(--font-size-md); margin: 0; }
.bracket-round > header span { color: var(--color-text-subtle); display: block; font: var(--font-weight-semibold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); margin-top: var(--space-1); }
.round-matches { display: flex; flex-direction: column; gap: var(--space-3); padding: var(--space-3); }
.bracket-match { background: var(--color-surface-raised); border: var(--border-width-thin) solid var(--color-border); min-height: 10.5rem; padding: var(--space-3); }
.match-meta { align-items: center; border-bottom: var(--border-width-thin) solid var(--color-border); display: flex; justify-content: space-between; margin-bottom: var(--space-2); padding-bottom: var(--space-2); }
.match-meta > span { font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); }
.official-status { color: var(--color-success); }
.predicted-status { color: var(--color-information); }
.bracket-team { align-items: center; display: flex; gap: var(--space-2); justify-content: space-between; min-height: 2rem; }
.bracket-team strong { font-size: var(--font-size-sm); }
.bracket-team.winner strong { color: var(--color-success); }
.winner-label { color: var(--color-success); font: var(--font-weight-bold) var(--font-size-xs) / 1 var(--font-family-data); text-transform: uppercase; }
.official-final, .match-probabilities { border-top: var(--border-width-thin) solid var(--color-border); color: var(--color-text-subtle); font: var(--font-weight-semibold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); margin: var(--space-2) 0 0; padding-top: var(--space-2); }
.official-final { color: var(--color-success); }
@media (max-width: 620px) {
  .podium-summary { grid-template-columns: 1fr; }
  .podium-place, .champion-place { grid-column: auto; grid-template-columns: 2rem minmax(0, 1fr); }
  .podium-place:last-child { border-left: 0; }
  .champion-probability { align-items: flex-start; grid-column: 2; }
}
</style>
