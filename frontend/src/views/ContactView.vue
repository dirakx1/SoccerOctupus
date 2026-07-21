<template>
  <main class="contact-page" aria-labelledby="contact-title">
    <header class="contact-intro">
      <p class="atlas-kicker">{{ t('contact.eyebrow') }}</p>
      <h1 id="contact-title">{{ t('contact.title') }}</h1>
      <p>{{ t('contact.intro') }}</p>
    </header>

    <section class="contact-support" aria-labelledby="contact-support-title">
      <div>
        <h2 id="contact-support-title">{{ t('contact.support.title') }}</h2>
        <p>{{ t('contact.support.body') }}</p>
      </div>
      <a class="contact-email" href="mailto:support@socceroctupus.co">support@socceroctupus.co</a>
    </section>

    <footer class="contact-footer">
      <router-link class="back-link" to="/">
        <ArrowLeft :size="18" aria-hidden="true" />
        <span>{{ t('contact.back') }}</span>
      </router-link>
    </footer>
  </main>
</template>

<script setup>
import { ArrowLeft } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<style scoped>
.contact-page { display: flex; flex-direction: column; gap: var(--space-8); margin: 0 auto; max-width: 52rem; padding: var(--space-10) 0 var(--space-16); }
.contact-intro { border-bottom: var(--border-width-strong) solid var(--color-border-strong); padding-bottom: var(--space-6); }
.atlas-kicker { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); margin: 0 0 var(--space-3); text-transform: uppercase; }
.contact-intro h1 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-4xl); font-weight: var(--font-weight-heavy); line-height: var(--line-height-tight); margin: 0; }
.contact-intro > p:last-child { color: var(--color-text-muted); font-size: var(--font-size-md); line-height: var(--line-height-relaxed); margin: var(--space-4) 0 0; max-width: 62ch; }
.contact-support { align-items: flex-start; background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); display: flex; gap: var(--space-6); justify-content: space-between; padding: var(--space-6); }
.contact-support h2 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-xl); line-height: var(--line-height-tight); margin: 0; }
.contact-support p { color: var(--color-text-muted); font-size: var(--font-size-md); line-height: var(--line-height-relaxed); margin: var(--space-3) 0 0; max-width: 45ch; }
.contact-email { align-items: center; border: var(--border-width-thin) solid var(--color-border-strong); color: var(--color-text); display: inline-flex; flex: 0 0 auto; font-family: var(--font-family-data); font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); min-height: var(--control-height-lg); padding: 0 var(--space-4); text-decoration: none; transition: border-color var(--duration-fast) var(--easing-standard), color var(--duration-fast) var(--easing-standard), transform var(--duration-fast) var(--easing-standard); }
.contact-email:hover { border-color: var(--color-accent); color: var(--color-accent); }
.contact-email:active { transform: translateY(1px); }
.contact-footer { border-top: var(--border-width-thin) solid var(--color-border); padding-top: var(--space-5); }
.back-link { align-items: center; color: var(--color-text); display: inline-flex; font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); gap: var(--space-2); min-height: var(--control-height-lg); text-decoration: none; }
.back-link:hover { color: var(--color-accent); }
.contact-email:focus-visible,.back-link:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
@media (max-width: 640px) { .contact-page { gap: var(--space-6); padding: var(--space-6) 0 var(--space-10); }.contact-intro h1 { font-size: var(--font-size-3xl); }.contact-intro > p:last-child,.contact-support p { font-size: var(--font-size-sm); }.contact-support { flex-direction: column; gap: var(--space-5); padding: var(--space-5); }.contact-support h2 { font-size: var(--font-size-lg); }.contact-email { width: 100%; } }
</style>
