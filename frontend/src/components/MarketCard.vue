<template>
  <article class="market-card">
    <header class="market-card-header">
      <span class="type-label"><component :is="meta.icon" :size="14" />{{ typeLabel }}</span>
      <span v-if="question.resolution?.date" class="resolve-date">
        <CalendarDays :size="14" />{{ t('markets.card.resolveDate', { date: question.resolution.date }) }}
      </span>
    </header>

    <h3>{{ question.question }}</h3>

    <div class="probabilities">
      <div v-for="answer in probabilityRows" :key="answer.key" class="probability-row">
        <span>{{ answer.label }}</span>
        <div
          class="probability-track"
          role="meter"
          :aria-label="t('markets.card.probability', { answer: answer.label })"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-valuenow="answer.raw * 100"
        ><span :style="{ width: answer.width }" /></div>
        <strong>{{ answer.display }}</strong>
      </div>
    </div>

    <dl class="price-list">
      <div>
        <dt>{{ t('markets.card.kalshiPrices') }}</dt>
        <dd>{{ t('markets.card.yes') }} {{ cents(question.pricing?.kalshi_yes_cents) }} <span>/</span> {{ t('markets.card.no') }} {{ cents(question.pricing?.kalshi_no_cents) }}</dd>
      </div>
      <div>
        <dt>{{ t('markets.card.polymarketPrices') }}</dt>
        <dd>{{ t('markets.card.yes') }} {{ usdc(question.pricing?.polymarket_yes_usdc) }} <span>/</span> {{ t('markets.card.no') }} {{ usdc(question.pricing?.polymarket_no_usdc) }}</dd>
      </div>
    </dl>

    <div v-if="question.resolution?.criteria" class="criteria-block">
      <button
        type="button"
        class="criteria-toggle"
        :aria-expanded="showCriteria"
        :aria-controls="criteriaId"
        @click="showCriteria = !showCriteria"
      >
        <ChevronDown :size="16" :class="{ expanded: showCriteria }" />
        {{ showCriteria ? t('markets.card.hideCriteria') : t('markets.card.showCriteria') }}
      </button>
      <div v-if="showCriteria" :id="criteriaId" class="criteria-text">
        <strong>{{ t('markets.card.criteria') }}</strong>
        <p>{{ question.resolution.criteria }}</p>
      </div>
    </div>

    <footer>
      <div><span>{{ t('markets.card.ticker') }}</span><code>{{ question.question_id }}</code></div>
      <button type="button" class="copy-button" :aria-label="t('markets.card.copy', { id: question.question_id })" @click="copyTicker">
        <Check v-if="copyState === 'success'" :size="16" />
        <Copy v-else :size="16" />
        <span>{{ copyState === 'success' ? t('markets.card.copied') : t('markets.card.copyShort') }}</span>
      </button>
      <p class="sr-only" aria-live="polite">{{ copyMessage }}</p>
    </footer>
  </article>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { CalendarDays, Check, ChevronDown, CircleDollarSign, Copy, Flag, Goal, ShieldCheck, Target, Trophy, TrendingUp, Users } from '@lucide/vue'

const props = defineProps({ question: { type: Object, required: true } })
const { locale, t } = useI18n()
const showCriteria = ref(false)
const copyState = ref('idle')
const criteriaId = `market-criteria-${Math.random().toString(36).slice(2)}`

const PROP_META = {
  match_winner: { label: 'matchWinner', icon: Trophy }, draw: { label: 'draw', icon: Users },
  btts: { label: 'btts', icon: Goal }, over_under: { label: 'overUnder', icon: TrendingUp },
  clean_sheet: { label: 'cleanSheet', icon: ShieldCheck }, penalties: { label: 'penalties', icon: Target },
  correct_score: { label: 'correctScore', icon: Goal }, tournament_winner: { label: 'tournamentWinner', icon: Trophy },
  reach_stage: { label: 'reachStage', icon: Flag }, group_winner: { label: 'groupWinner', icon: Trophy },
  confederation_win: { label: 'confederationWin', icon: CircleDollarSign }, host_nation: { label: 'hostNation', icon: Flag },
}
const meta = computed(() => PROP_META[props.question.prop_type] || { label: null, icon: CircleDollarSign })
const typeLabel = computed(() => meta.value.label ? t(`markets.filters.${meta.value.label}`) : (props.question.prop_type || t('markets.card.unknownType')))

const formatter = (options) => new Intl.NumberFormat(locale.value, options)
const percentage = (value) => formatter({ style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(Number(value) || 0)
const cents = (value) => value == null ? '—' : `${formatter({ minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(value)}¢`
const usdc = (value) => value == null ? '—' : formatter({ style: 'currency', currency: 'USD', minimumFractionDigits: 4, maximumFractionDigits: 4 }).format(value)
const probabilityRows = computed(() => [
  { key: 'yes', label: t('markets.card.yes'), raw: Number(props.question.yes_probability) || 0, width: `${(Number(props.question.yes_probability) || 0) * 100}%`, display: percentage(props.question.yes_probability) },
  { key: 'no', label: t('markets.card.no'), raw: Number(props.question.no_probability) || 0, width: `${(Number(props.question.no_probability) || 0) * 100}%`, display: percentage(props.question.no_probability) },
])
const copyMessage = computed(() => copyState.value === 'success' ? t('markets.card.copied') : copyState.value === 'error' ? t('markets.card.copyFailed') : '')

async function copyTicker() {
  try {
    await navigator.clipboard.writeText(props.question.question_id)
    copyState.value = 'success'
  } catch {
    copyState.value = 'error'
  }
}
</script>

<style scoped>
.market-card { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); display: flex; flex-direction: column; gap: var(--space-5); min-width: 0; padding: var(--space-5); }
.market-card-header { align-items: center; display: flex; flex-wrap: wrap; gap: var(--space-3); justify-content: space-between; }
.type-label, .resolve-date { align-items: center; display: inline-flex; gap: var(--space-2); }
.type-label { background: var(--color-surface-inset); color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); padding: var(--space-2) var(--space-3); text-transform: uppercase; }
.resolve-date { color: var(--color-text-muted); font-size: var(--font-size-xs); }
h3 { font-family: var(--font-family-display); font-size: var(--font-size-lg); line-height: var(--line-height-normal); margin: 0; }
.probabilities { display: flex; flex-direction: column; gap: var(--space-3); }
.probability-row { align-items: center; display: grid; gap: var(--space-3); grid-template-columns: 2.5rem minmax(4rem, 1fr) 4.5rem; }
.probability-row > span { color: var(--color-text-muted); font: var(--font-weight-bold) var(--font-size-xs) / 1 var(--font-family-data); }
.probability-row strong { font-family: var(--font-family-data); font-variant-numeric: tabular-nums; text-align: right; }
.probability-track { background: var(--color-surface-inset); height: var(--space-2); overflow: hidden; }
.probability-track span { background: var(--color-accent); display: block; height: 100%; }
.price-list { border-bottom: var(--border-width-thin) solid var(--color-border); border-top: var(--border-width-thin) solid var(--color-border); margin: 0; }
.price-list > div { align-items: center; display: flex; gap: var(--space-4); justify-content: space-between; min-height: var(--control-height-lg); }
.price-list > div + div { border-top: var(--border-width-thin) solid var(--color-border); }
.price-list dt { color: var(--color-text-muted); font-size: var(--font-size-xs); }
.price-list dd { font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); margin: 0; }
.price-list dd span { color: var(--color-text-subtle); padding: 0 var(--space-1); }
.criteria-toggle, .copy-button { align-items: center; background: transparent; border: 0; color: var(--color-text-muted); cursor: pointer; display: inline-flex; gap: var(--space-2); min-height: var(--control-height-lg); padding: 0; }
.criteria-toggle:hover, .copy-button:hover { color: var(--color-accent); }
.criteria-toggle:focus-visible, .copy-button:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 4px; }
.criteria-toggle svg { transition: transform var(--motion-duration-fast) var(--motion-easing-standard); }
.criteria-toggle svg.expanded { transform: rotate(180deg); }
.criteria-text { background: var(--color-surface-inset); margin-top: var(--space-3); padding: var(--space-4); }
.criteria-text strong { font-size: var(--font-size-xs); }
.criteria-text p { color: var(--color-text-muted); font-size: var(--font-size-sm); line-height: var(--line-height-relaxed); margin: var(--space-2) 0 0; }
footer { align-items: end; display: flex; gap: var(--space-4); justify-content: space-between; }
footer > div { display: flex; flex-direction: column; gap: var(--space-1); min-width: 0; }
footer span { color: var(--color-text-muted); font-size: var(--font-size-xs); }
footer code { color: var(--color-text); font-family: var(--font-family-data); overflow-wrap: anywhere; }
.copy-button { flex: 0 0 auto; }
.sr-only { height: 1px; margin: -1px; overflow: hidden; position: absolute; width: 1px; clip: rect(0, 0, 0, 0); }
@media (max-width: 480px) { .price-list > div, footer { align-items: flex-start; flex-direction: column; padding: var(--space-3) 0; } }
@media (prefers-reduced-motion: reduce) { .criteria-toggle svg { transition: none; } }
</style>
