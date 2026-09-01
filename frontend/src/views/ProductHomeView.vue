<template>
  <main class="product-home">
    <section class="product-hero" aria-labelledby="product-home-title">
      <div class="hero-copy">
        <p class="section-label">{{ t('productHome.hero.eyebrow') }}</p>
        <h1 id="product-home-title">{{ t('productHome.hero.title') }}</h1>
        <p class="hero-intro">{{ t('productHome.hero.description') }}</p>
        <div class="hero-actions">
          <router-link class="button button-primary" :to="competitionRoute('premier-league')">
            {{ t('productHome.hero.explore') }}
            <ArrowRight :size="17" aria-hidden="true" />
          </router-link>
          <router-link class="button button-secondary" :to="predictionRoute">
            {{ t('productHome.hero.predict') }}
          </router-link>
        </div>
        <p class="hero-note"><Check :size="15" aria-hidden="true" />{{ t('productHome.hero.freeNote') }}</p>
      </div>

      <aside id="competitions" class="league-board" aria-labelledby="league-board-title">
        <header>
          <p class="section-label">{{ t('productHome.competitions.eyebrow') }}</p>
          <h2 id="league-board-title">{{ t('productHome.competitions.title') }}</h2>
        </header>
        <nav :aria-label="t('productHome.competitions.eyebrow')">
          <router-link
            v-for="(edition, index) in editions"
            :key="edition.slug"
            :to="competitionRoute(edition.slug)"
          >
            <span class="league-number">{{ String(index + 1).padStart(2, '0') }}</span>
            <span class="league-name">
              <small>{{ t(edition.countryKey) }}</small>
              <strong>{{ t(edition.displayNameKey) }}</strong>
            </span>
            <small class="league-format">{{ t('productHome.competitions.format', { clubs: edition.clubCount, matchdays: edition.matchdayCount }) }}</small>
            <ArrowUpRight :size="18" aria-hidden="true" />
          </router-link>
        </nav>
      </aside>
    </section>

    <section id="how-it-works" class="home-section journey-section" aria-labelledby="journey-title">
      <header class="section-heading journey-heading">
        <div>
          <p class="section-label">{{ t('productHome.journey.eyebrow') }}</p>
          <h2 id="journey-title">{{ t('productHome.journey.title') }}</h2>
        </div>
        <p>{{ t('productHome.journey.description') }}</p>
      </header>
      <ol class="journey-list">
        <li v-for="(step, index) in journeySteps" :key="step.key">
          <span>{{ String(index + 1).padStart(2, '0') }}</span>
          <div>
            <h3>{{ t(step.titleKey) }}</h3>
            <p>{{ t(step.descriptionKey) }}</p>
          </div>
          <component :is="step.icon" :size="23" aria-hidden="true" />
        </li>
      </ol>
    </section>

    <section class="home-section pricing-callout" aria-labelledby="pricing-title">
      <div>
        <p class="section-label">{{ t('productHome.pricing.eyebrow') }}</p>
        <h2 id="pricing-title">{{ t('productHome.pricing.title') }}</h2>
        <p>{{ t('productHome.pricing.description') }}</p>
      </div>
      <router-link class="button button-primary" to="/pricing">
        {{ t('productHome.pricing.action') }}
        <ArrowRight :size="17" aria-hidden="true" />
      </router-link>
    </section>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowRight, ArrowUpRight, Check, ChartNoAxesCombined, ListOrdered, ScanSearch, Trophy } from '@lucide/vue'

import { listCompetitionEditions } from '../competition/index.js'
import { workspaceLocation } from '../router/workspace.js'

const { locale, t } = useI18n()
const editions = listCompetitionEditions()

const journeySteps = [
  { key: 'follow', titleKey: 'productHome.journey.follow.title', descriptionKey: 'productHome.journey.follow.description', icon: ListOrdered },
  { key: 'choose', titleKey: 'productHome.journey.choose.title', descriptionKey: 'productHome.journey.choose.description', icon: ScanSearch },
  { key: 'forecast', titleKey: 'productHome.journey.forecast.title', descriptionKey: 'productHome.journey.forecast.description', icon: ChartNoAxesCombined },
  { key: 'season', titleKey: 'productHome.journey.season.title', descriptionKey: 'productHome.journey.season.description', icon: Trophy },
]

const competitionRoute = (slug) => workspaceLocation('overview', {
  locale: locale.value,
  competitionEditionSlug: slug,
})

const predictionRoute = computed(() => workspaceLocation('predict', {
  locale: locale.value,
  competitionEditionSlug: 'premier-league',
}))

</script>

<style scoped>
.product-home { display: flex; flex-direction: column; gap: var(--space-12); }
.product-hero { align-items: stretch; border-bottom: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-8); grid-template-columns: minmax(0, 1.05fr) minmax(22rem, .95fr); min-height: 32rem; padding: var(--space-8) 0 var(--space-12); }
.hero-copy { align-self: center; max-width: 44rem; }
.section-label { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); letter-spacing: .04em; margin: 0 0 var(--space-3); text-transform: uppercase; }
.hero-copy h1 { font-family: var(--font-family-display); font-size: clamp(3.3rem, 7vw, 6.7rem); font-weight: var(--font-weight-heavy); letter-spacing: -.045em; line-height: .9; margin: 0; max-width: 9ch; }
.hero-intro { color: var(--color-text-muted); font-size: var(--font-size-lg); line-height: var(--line-height-relaxed); margin: var(--space-6) 0 0; max-width: 53ch; }
.hero-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-7); }
.button { align-items: center; border: var(--border-width-thin) solid transparent; display: inline-flex; font-weight: var(--font-weight-bold); gap: var(--space-2); justify-content: center; min-height: var(--control-height-lg); padding: 0 var(--space-5); text-decoration: none; }
.button-primary { background: var(--color-accent); color: var(--color-accent-contrast); }
.button-primary:hover { background: var(--color-accent-hover); }
.button-secondary { border-color: var(--color-border-strong); color: var(--color-text); }
.button-secondary:hover { background: var(--color-surface-inset); }
.button:focus-visible, .league-board a:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.hero-note { align-items: center; color: var(--color-text-muted); display: flex; font-size: var(--font-size-xs); gap: var(--space-2); margin: var(--space-4) 0 0; }
.hero-note svg { color: var(--color-accent); }

.league-board { align-self: center; background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); scroll-margin-top: 6rem; }
.league-board header { border-top: var(--border-width-strong) solid var(--color-accent); padding: var(--space-5); }
.league-board header .section-label { margin-bottom: var(--space-2); }
.league-board h2 { font-family: var(--font-family-display); font-size: var(--font-size-2xl); line-height: var(--line-height-tight); margin: 0; }
.league-board nav { border-top: var(--border-width-thin) solid var(--color-border); }
.league-board a { align-items: center; color: var(--color-text); display: grid; gap: var(--space-4); grid-template-columns: 2rem minmax(0, 1fr) auto auto; min-height: 6.5rem; padding: var(--space-4) var(--space-5); text-decoration: none; transition: background-color var(--duration-fast) var(--easing-standard); }
.league-board a + a { border-top: var(--border-width-thin) solid var(--color-border); }
.league-board a:hover { background: var(--color-surface-raised); }
.league-number { color: var(--color-text-subtle); font: var(--font-weight-bold) var(--font-size-xs) / 1 var(--font-family-data); }
.league-name { display: grid; gap: var(--space-1); }
.league-name small { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / 1 var(--font-family-data); text-transform: uppercase; }
.league-name strong { font-family: var(--font-family-display); font-size: var(--font-size-lg); line-height: var(--line-height-tight); }
.league-format { color: var(--color-text-muted); font-size: var(--font-size-xs); white-space: nowrap; }
.league-board a > svg { color: var(--color-accent); }

.home-section { scroll-margin-top: 6rem; }
.section-heading { align-items: end; display: grid; gap: var(--space-8); grid-template-columns: minmax(16rem, .8fr) minmax(0, 1.2fr); margin-bottom: var(--space-6); }
.section-heading h2, .pricing-callout h2 { font-family: var(--font-family-display); font-size: clamp(2.2rem, 5vw, 4.4rem); letter-spacing: -.035em; line-height: .95; margin: 0; }
.section-heading > p { color: var(--color-text-muted); line-height: var(--line-height-relaxed); margin: 0; max-width: 50ch; }

.journey-section { border-top: var(--border-width-thin) solid var(--color-border); padding-top: var(--space-10); }
.journey-list { list-style: none; margin: 0; padding: 0; }
.journey-list li { align-items: start; border-top: var(--border-width-thin) solid var(--color-border); display: grid; gap: var(--space-5); grid-template-columns: 3rem minmax(0, 1fr) auto; padding: var(--space-5) 0; }
.journey-list li:last-child { border-bottom: var(--border-width-thin) solid var(--color-border); }
.journey-list > li > span { color: var(--color-text-subtle); font: var(--font-weight-bold) var(--font-size-xs) / 1 var(--font-family-data); padding-top: .35rem; }
.journey-list h3 { font-family: var(--font-family-display); font-size: var(--font-size-xl); margin: 0; }
.journey-list p { color: var(--color-text-muted); line-height: var(--line-height-relaxed); margin: var(--space-2) 0 0; max-width: 66ch; }
.journey-list svg { color: var(--color-accent); }

.pricing-callout { align-items: center; border-bottom: var(--border-width-thin) solid var(--color-border); border-top: var(--border-width-thin) solid var(--color-border); display: flex; gap: var(--space-8); justify-content: space-between; padding: var(--space-8) 0; }
.pricing-callout h2 { font-size: clamp(2rem, 4vw, 3.7rem); }
.pricing-callout p:last-child { color: var(--color-text-muted); line-height: var(--line-height-relaxed); margin: var(--space-4) 0 0; max-width: 58ch; }
.pricing-callout .button { flex: 0 0 auto; }

@media (max-width: 900px) {
  .product-hero { grid-template-columns: 1fr; }
  .hero-copy h1 { max-width: 11ch; }
  .league-board { width: 100%; }
}
@media (max-width: 640px) {
  .product-home { gap: var(--space-10); }
  .product-hero { min-height: 0; padding-top: var(--space-4); }
  .hero-copy h1 { font-size: 3.6rem; }
  .league-board a { grid-template-columns: 1.7rem minmax(0, 1fr) auto; }
  .league-format { display: none; }
  .section-heading { align-items: start; gap: var(--space-4); grid-template-columns: 1fr; }
  .journey-list li { grid-template-columns: 2.2rem minmax(0, 1fr); }
  .journey-list svg { display: none; }
  .pricing-callout { align-items: flex-start; flex-direction: column; }
}
</style>
