<template>
  <main class="about-page" aria-labelledby="about-title">
    <header class="about-intro">
      <p class="atlas-kicker">{{ t('about.eyebrow') }}</p>
      <h1 id="about-title">{{ t('about.title') }}</h1>
      <p>{{ t('about.intro') }}</p>
    </header>

    <article class="about-document">
      <section class="about-section" aria-labelledby="about-what">
        <h2 id="about-what">{{ t('about.sections.what.title') }}</h2>
        <p>{{ t('about.sections.what.body') }}</p>
      </section>

      <section v-for="section in listSections" :key="section.key" class="about-section" :aria-labelledby="`about-${section.key}`">
        <h2 :id="`about-${section.key}`">{{ t(`about.sections.${section.key}.title`) }}</h2>
        <ul>
          <li v-for="item in tm(`about.sections.${section.key}.items`)" :key="item">
            <template v-if="section.key === 'agents'">
              <strong>{{ item.split('|')[0] }}</strong>{{ ' - ' }}{{ item.split('|')[1] }}
            </template>
            <template v-else>{{ item }}</template>
          </li>
        </ul>
      </section>

      <section class="about-section" aria-labelledby="about-open-source">
        <h2 id="about-open-source">{{ t('about.sections.openSource.title') }}</h2>
        <p>{{ t('about.sections.openSource.intro') }}</p>
        <p><a class="repository-link" href="https://github.com/dirakx1/SoccerOctupus" target="_blank" rel="noopener noreferrer">{{ t('about.sections.openSource.repository') }}<ExternalLink :size="15" aria-hidden="true" /></a></p>
        <p>{{ t('about.sections.openSource.licensePrefix') }} <a href="https://www.gnu.org/licenses/agpl-3.0.html" target="_blank" rel="noopener noreferrer">{{ t('about.sections.openSource.license') }}</a>. {{ t('about.sections.openSource.copyright') }}</p>
        <p>{{ t('about.sections.openSource.termsPrefix') }} <a href="https://github.com/dirakx1/SoccerOctupus/blob/main/LICENSE" target="_blank" rel="noopener noreferrer">{{ t('about.sections.openSource.termsLink') }}</a> {{ t('about.sections.openSource.termsSuffix') }}</p>
      </section>
    </article>

    <footer class="about-footer">
      <router-link class="back-link" to="/"><ArrowLeft :size="18" aria-hidden="true" /><span>{{ t('about.back') }}</span></router-link>
    </footer>
  </main>
</template>

<script setup>
import { ArrowLeft, ExternalLink } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

const { t, tm } = useI18n()
const listSections = [{ key: 'stack' }, { key: 'agents' }, { key: 'sources' }]
</script>

<style scoped>
.about-page { display: flex; flex-direction: column; gap: var(--space-8); margin: 0 auto; max-width: 52rem; padding: var(--space-10) 0 var(--space-16); }
.atlas-kicker { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); margin: 0 0 var(--space-3); text-transform: uppercase; }
.about-intro { border-bottom: var(--border-width-strong) solid var(--color-border-strong); padding-bottom: var(--space-6); }
.about-intro h1 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-4xl); font-weight: var(--font-weight-heavy); line-height: var(--line-height-tight); margin: 0; }
.about-intro > p:last-child { color: var(--color-text-muted); font-size: var(--font-size-md); line-height: var(--line-height-relaxed); margin: var(--space-4) 0 0; max-width: 62ch; }
.about-document { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); }
.about-section { border-bottom: var(--border-width-thin) solid var(--color-border); padding: var(--space-6); }
.about-section:last-child { border-bottom: 0; }
.about-section h2 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-xl); line-height: var(--line-height-tight); margin: 0; }
.about-section p,.about-section li { color: var(--color-text-muted); font-size: var(--font-size-md); line-height: var(--line-height-relaxed); }
.about-section p { margin: var(--space-3) 0 0; max-width: 66ch; }
.about-section ul { display: grid; gap: var(--space-3); list-style: none; margin: var(--space-4) 0 0; padding: 0; }
.about-section li { border-left: var(--border-width-strong) solid var(--color-border-strong); padding-left: var(--space-3); }
.about-section li strong { color: var(--color-text); font-weight: var(--font-weight-bold); }
.about-section a { color: var(--color-accent); font-weight: var(--font-weight-semibold); text-decoration-thickness: 1px; text-underline-offset: 0.18em; }
.about-section a:hover { color: var(--color-accent-hover); }
.repository-link { align-items: center; display: inline-flex; gap: var(--space-2); }
.about-section a:focus-visible,.back-link:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.about-footer { border-top: var(--border-width-thin) solid var(--color-border); padding-top: var(--space-5); }
.back-link { align-items: center; color: var(--color-text); display: inline-flex; font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); gap: var(--space-2); min-height: var(--control-height-lg); text-decoration: none; }
.back-link:hover { color: var(--color-accent); }
@media (max-width: 640px) { .about-page { gap: var(--space-6); padding: var(--space-6) 0 var(--space-10); }.about-intro h1 { font-size: var(--font-size-3xl); }.about-section { padding: var(--space-5); }.about-section h2 { font-size: var(--font-size-lg); }.about-section p,.about-section li { font-size: var(--font-size-sm); } }
</style>
