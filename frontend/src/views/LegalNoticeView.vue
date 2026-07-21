<template>
  <main class="legal-notice-page" aria-labelledby="legal-notice-title">
    <header class="legal-notice-intro">
      <p class="atlas-kicker">{{ t('legal.eyebrow') }}</p>
      <h1 id="legal-notice-title">{{ t('legal.title') }}</h1>
      <p class="legal-notice-updated">{{ t('legal.updated') }}</p>
      <p class="legal-notice-summary">{{ t('legal.intro') }}</p>
    </header>

    <article class="legal-notice-document">
      <section v-for="section in contentSections" :key="section.key" class="legal-notice-section" :aria-labelledby="`legal-${section.key}`">
        <h2 :id="`legal-${section.key}`">{{ t(`legal.sections.${section.key}.title`) }}</h2>
        <p>{{ t(`legal.sections.${section.key}.body`) }}</p>
      </section>

      <section class="legal-notice-section" aria-labelledby="legal-responsible">
        <h2 id="legal-responsible">{{ t('legal.sections.responsible.title') }}</h2>
        <p>
          {{ t('legal.sections.responsible.prefix') }}
          <a href="https://www.begambleaware.org" target="_blank" rel="noopener noreferrer">{{ t('legal.resources.begambleaware') }}</a>
          {{ ' ' }}{{ t('legal.sections.responsible.between') }}{{ ' ' }}
          <a href="https://www.ncpgambling.org" target="_blank" rel="noopener noreferrer">{{ t('legal.resources.ncpg') }}</a>{{ t('legal.sections.responsible.suffix') }}
        </p>
      </section>
    </article>

    <footer class="legal-notice-footer">
      <router-link class="back-link" to="/">
        <ArrowLeft :size="18" aria-hidden="true" />
        <span>{{ t('legal.back') }}</span>
      </router-link>
    </footer>
  </main>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { ArrowLeft } from '@lucide/vue'

const { t } = useI18n()

const contentSections = [
  { key: 'predictions' },
  { key: 'advice' },
  { key: 'liability' },
  { key: 'regulations' },
  { key: 'affiliation' },
]
</script>

<style scoped>
.legal-notice-page { display: flex; flex-direction: column; gap: var(--space-8); margin: 0 auto; max-width: 52rem; padding: var(--space-10) 0 var(--space-16); }
.atlas-kicker { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); margin: 0 0 var(--space-3); text-transform: uppercase; }
.legal-notice-intro { border-bottom: var(--border-width-strong) solid var(--color-border-strong); padding-bottom: var(--space-6); }
.legal-notice-intro h1 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-4xl); font-weight: var(--font-weight-heavy); line-height: var(--line-height-tight); margin: 0; }
.legal-notice-updated { color: var(--color-text-subtle); font: var(--font-weight-medium) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); margin: var(--space-4) 0 0; }
.legal-notice-summary { color: var(--color-text-muted); font-size: var(--font-size-md); line-height: var(--line-height-relaxed); margin: var(--space-4) 0 0; max-width: 62ch; }
.legal-notice-document { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); }
.legal-notice-section { border-bottom: var(--border-width-thin) solid var(--color-border); padding: var(--space-6); }
.legal-notice-section:last-child { border-bottom: 0; }
.legal-notice-section h2 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-xl); line-height: var(--line-height-tight); margin: 0; }
.legal-notice-section p { color: var(--color-text-muted); font-size: var(--font-size-md); line-height: var(--line-height-relaxed); margin: var(--space-3) 0 0; max-width: 66ch; }
.legal-notice-section a { color: var(--color-accent); font-weight: var(--font-weight-semibold); text-decoration-thickness: 1px; text-underline-offset: 0.18em; }
.legal-notice-section a:hover { color: var(--color-accent-hover); }
.legal-notice-section a:focus-visible,.back-link:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.legal-notice-footer { border-top: var(--border-width-thin) solid var(--color-border); padding-top: var(--space-5); }
.back-link { align-items: center; color: var(--color-text); display: inline-flex; font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); gap: var(--space-2); min-height: var(--control-height-lg); text-decoration: none; }
.back-link:hover { color: var(--color-accent); }
@media (max-width: 640px) { .legal-notice-page { gap: var(--space-6); padding: var(--space-6) 0 var(--space-10); }.legal-notice-intro h1 { font-size: var(--font-size-3xl); }.legal-notice-section { padding: var(--space-5); }.legal-notice-section h2 { font-size: var(--font-size-lg); }.legal-notice-section p { font-size: var(--font-size-sm); } }
</style>
