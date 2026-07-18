<template>
  <main class="cookie-policy-page" aria-labelledby="cookie-policy-title">
    <header class="cookie-policy-intro">
      <p class="atlas-kicker">{{ t('cookiePolicy.eyebrow') }}</p>
      <h1 id="cookie-policy-title">{{ t('cookiePolicy.title') }}</h1>
      <p class="cookie-policy-updated">{{ t('cookiePolicy.updated') }}</p>
      <p class="cookie-policy-summary">{{ t('cookiePolicy.intro') }}</p>
    </header>

    <article class="cookie-policy-document">
      <section class="cookie-policy-section" aria-labelledby="cookie-policy-what">
        <h2 id="cookie-policy-what">{{ t('cookiePolicy.sections.what.title') }}</h2>
        <p>{{ t('cookiePolicy.sections.what.body') }}</p>
      </section>

      <section class="cookie-policy-section" aria-labelledby="cookie-policy-inventory">
        <h2 id="cookie-policy-inventory">{{ t('cookiePolicy.sections.cookies.title') }}</h2>
        <div class="cookie-table-wrap" tabindex="0">
          <table>
            <thead>
              <tr>
                <th scope="col">{{ t('cookiePolicy.table.name') }}</th>
                <th scope="col">{{ t('cookiePolicy.table.type') }}</th>
                <th scope="col">{{ t('cookiePolicy.table.purpose') }}</th>
                <th scope="col">{{ t('cookiePolicy.table.duration') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="cookie in cookies" :key="cookie.key">
                <td class="cookie-name">{{ cookie.name }}</td>
                <td><span class="cookie-type" :class="`cookie-type-${cookie.type}`">{{ t(`cookiePolicy.types.${cookie.type}`) }}</span></td>
                <td>{{ t(`cookiePolicy.cookies.${cookie.key}.purpose`) }}</td>
                <td>{{ t(`cookiePolicy.cookies.${cookie.key}.duration`) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="cookie-policy-section" aria-labelledby="cookie-policy-choices">
        <h2 id="cookie-policy-choices">{{ t('cookiePolicy.sections.choices.title') }}</h2>
        <p>{{ t('cookiePolicy.sections.choices.body') }}</p>
        <p>{{ t('cookiePolicy.sections.choices.resetHelp') }}</p>
        <button class="reset-button" type="button" @click="resetConsent">{{ t('cookiePolicy.sections.choices.reset') }}</button>
      </section>

      <section class="cookie-policy-section" aria-labelledby="cookie-policy-third-party">
        <h2 id="cookie-policy-third-party">{{ t('cookiePolicy.sections.thirdParty.title') }}</h2>
        <p>{{ t('cookiePolicy.sections.thirdParty.body') }}</p>
      </section>

      <section class="cookie-policy-section" aria-labelledby="cookie-policy-browser">
        <h2 id="cookie-policy-browser">{{ t('cookiePolicy.sections.browser.title') }}</h2>
        <p>{{ t('cookiePolicy.sections.browser.body') }}</p>
        <ul class="browser-list">
          <li v-for="browser in browsers" :key="browser.key">
            <a :href="browser.href" target="_blank" rel="noopener noreferrer">{{ t(`cookiePolicy.browsers.${browser.key}`) }}</a>
          </li>
        </ul>
      </section>

      <section class="cookie-policy-section" aria-labelledby="cookie-policy-contact">
        <h2 id="cookie-policy-contact">{{ t('cookiePolicy.sections.contact.title') }}</h2>
        <p>
          {{ t('cookiePolicy.sections.contact.prefix') }}
          <router-link to="/legal">{{ t('cookiePolicy.sections.contact.link') }}</router-link>{{ t('cookiePolicy.sections.contact.suffix') }}
        </p>
      </section>
    </article>

    <footer class="cookie-policy-footer">
      <router-link class="back-link" to="/">
        <ArrowLeft :size="18" aria-hidden="true" />
        <span>{{ t('cookiePolicy.back') }}</span>
      </router-link>
    </footer>
  </main>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { ArrowLeft } from '@lucide/vue'

const STORAGE_KEY = 'so_cookie_consent'
const { t } = useI18n()

const cookies = [
  { key: 'session', name: '__session, __client*', type: 'necessary' },
  { key: 'consent', name: 'so_cookie_consent', type: 'necessary' },
  { key: 'analytics', name: '_ga, _gid', type: 'analytics' },
]

const browsers = [
  { key: 'chrome', href: 'https://support.google.com/chrome/answer/95647' },
  { key: 'firefox', href: 'https://support.mozilla.org/en-US/kb/enable-and-disable-cookies-website-preferences' },
  { key: 'safari', href: 'https://support.apple.com/guide/safari/manage-cookies-sfri11471' },
  { key: 'edge', href: 'https://support.microsoft.com/en-us/microsoft-edge/delete-cookies-in-microsoft-edge' },
]

function resetConsent() {
  localStorage.removeItem(STORAGE_KEY)
  window.location.reload()
}
</script>

<style scoped>
.cookie-policy-page { display: flex; flex-direction: column; gap: var(--space-8); margin: 0 auto; max-width: 60rem; padding: var(--space-10) 0 var(--space-16); }
.atlas-kicker { color: var(--color-accent); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); margin: 0 0 var(--space-3); text-transform: uppercase; }
.cookie-policy-intro { border-bottom: var(--border-width-strong) solid var(--color-border-strong); padding-bottom: var(--space-6); }
.cookie-policy-intro h1 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-4xl); font-weight: var(--font-weight-heavy); line-height: var(--line-height-tight); margin: 0; }
.cookie-policy-updated { color: var(--color-text-subtle); font: var(--font-weight-medium) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); margin: var(--space-4) 0 0; }
.cookie-policy-summary { color: var(--color-text-muted); font-size: var(--font-size-md); line-height: var(--line-height-relaxed); margin: var(--space-4) 0 0; max-width: 62ch; }
.cookie-policy-document { background: var(--color-surface); border: var(--border-width-thin) solid var(--color-border); }
.cookie-policy-section { border-bottom: var(--border-width-thin) solid var(--color-border); padding: var(--space-6); }
.cookie-policy-section:last-child { border-bottom: 0; }
.cookie-policy-section h2 { color: var(--color-text); font-family: var(--font-family-display); font-size: var(--font-size-xl); line-height: var(--line-height-tight); margin: 0; }
.cookie-policy-section p { color: var(--color-text-muted); font-size: var(--font-size-md); line-height: var(--line-height-relaxed); margin: var(--space-3) 0 0; max-width: 66ch; }
.cookie-policy-section a { color: var(--color-accent); font-weight: var(--font-weight-semibold); text-decoration-thickness: 1px; text-underline-offset: 0.18em; }
.cookie-policy-section a:hover { color: var(--color-accent-hover); }
.cookie-table-wrap { border: var(--border-width-thin) solid var(--color-border); margin-top: var(--space-4); overflow-x: auto; }
.cookie-table-wrap:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
table { border-collapse: collapse; color: var(--color-text-muted); font-size: var(--font-size-sm); min-width: 46rem; text-align: left; width: 100%; }
th { background: var(--color-surface-raised); color: var(--color-text-subtle); font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); letter-spacing: 0; text-transform: uppercase; }
th, td { border-bottom: var(--border-width-thin) solid var(--color-border); padding: var(--space-3) var(--space-4); vertical-align: top; }
tbody tr:last-child td { border-bottom: 0; }
th:nth-child(1), td:nth-child(1) { width: 20%; }
th:nth-child(2), td:nth-child(2) { width: 14%; }
th:nth-child(3), td:nth-child(3) { width: 46%; }
.cookie-name { color: var(--color-text); font-family: var(--font-family-data); font-size: var(--font-size-xs); overflow-wrap: anywhere; }
.cookie-type { border: var(--border-width-thin) solid currentColor; display: inline-block; font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); padding: var(--space-1) var(--space-2); }
.cookie-type-necessary { color: var(--color-status-success); }
.cookie-type-analytics { color: var(--color-status-info); }
.reset-button { background: transparent; border: var(--border-width-thin) solid var(--color-border-strong); color: var(--color-text); cursor: pointer; font-family: var(--font-family-body); font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); margin-top: var(--space-4); min-height: var(--control-height-lg); padding: 0 var(--space-4); transition: border-color var(--duration-fast) var(--easing-standard), color var(--duration-fast) var(--easing-standard); }
.reset-button:hover { border-color: var(--color-accent); color: var(--color-accent); }
.reset-button:active { transform: translateY(1px); }
.browser-list { display: grid; gap: var(--space-2); margin: var(--space-4) 0 0; padding-left: var(--space-5); }
.browser-list li { color: var(--color-text-muted); font-size: var(--font-size-md); line-height: var(--line-height-relaxed); }
.cookie-policy-section a:focus-visible,.reset-button:focus-visible,.back-link:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.cookie-policy-footer { border-top: var(--border-width-thin) solid var(--color-border); padding-top: var(--space-5); }
.back-link { align-items: center; color: var(--color-text); display: inline-flex; font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); gap: var(--space-2); min-height: var(--control-height-lg); text-decoration: none; }
.back-link:hover { color: var(--color-accent); }
@media (max-width: 640px) { .cookie-policy-page { gap: var(--space-6); padding: var(--space-6) 0 var(--space-10); }.cookie-policy-intro h1 { font-size: var(--font-size-3xl); }.cookie-policy-section { padding: var(--space-5); }.cookie-policy-section h2 { font-size: var(--font-size-lg); }.cookie-policy-section p,.browser-list li { font-size: var(--font-size-sm); } }
</style>
