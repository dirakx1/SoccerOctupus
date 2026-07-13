<template>
  <div class="legal">
    <h1>Cookie Policy</h1>
    <p class="updated">Last updated: June 2026</p>

    <section>
      <h2>1. What Are Cookies</h2>
      <p>
        Cookies are small text files stored in your browser when you visit a website.
        They help the site remember your preferences, keep you signed in, and understand
        how people use the platform. SoccerOctopus uses a minimal set of cookies to
        provide a functioning service.
      </p>
    </section>

    <section>
      <h2>2. Cookies We Use</h2>

      <div class="cookie-table">
        <div class="table-header">
          <span>Name / Prefix</span>
          <span>Type</span>
          <span>Purpose</span>
          <span>Duration</span>
        </div>

        <div class="table-row">
          <span class="mono">__session, __client*</span>
          <span class="badge necessary">Necessary</span>
          <span>Authentication — keeps you signed in and identifies your session securely.</span>
          <span>Session / up to 1 year</span>
        </div>

        <div class="table-row">
          <span class="mono">so_cookie_consent</span>
          <span class="badge necessary">Necessary</span>
          <span>Stores your cookie consent choice so we don't show the banner again.</span>
          <span>1 year</span>
        </div>

        <div class="table-row">
          <span class="mono">_ga, _gid</span>
          <span class="badge analytics">Analytics</span>
          <span>Google Analytics — helps us understand which pages are visited and how the swarm engine is used. Only set if you consent to analytics cookies.</span>
          <span>Up to 2 years</span>
        </div>
      </div>
    </section>

    <section>
      <h2>3. Your Choices</h2>
      <p>
        When you first visit SoccerOctopus you are shown a cookie banner. You can choose
        to accept <strong>all cookies</strong> (including analytics) or
        <strong>necessary only</strong> (authentication + consent storage only).
      </p>
      <p>
        You can withdraw or change your consent at any time by clearing your browser's
        local storage for this site, or by clicking the button below:
      </p>
      <button class="btn-reset" @click="resetConsent">Reset cookie preferences</button>
    </section>

    <section>
      <h2>4. Third-Party Cookies</h2>
      <p>
        Authentication is provided by an external authentication service, which may set
        cookies as part of the sign-in flow. These cookies are strictly necessary
        to operate the service. Contact us if you need more information about the
        authentication service's privacy practices.
      </p>
    </section>

    <section>
      <h2>5. Browser Controls</h2>
      <p>
        All major browsers let you block or delete cookies in their settings.
        Note that blocking necessary cookies will prevent sign-in from working.
        Links to browser guidance:
      </p>
      <ul>
        <li><a href="https://support.google.com/chrome/answer/95647" target="_blank" rel="noopener">Google Chrome</a></li>
        <li><a href="https://support.mozilla.org/en-US/kb/enable-and-disable-cookies-website-preferences" target="_blank" rel="noopener">Mozilla Firefox</a></li>
        <li><a href="https://support.apple.com/guide/safari/manage-cookies-sfri11471" target="_blank" rel="noopener">Apple Safari</a></li>
        <li><a href="https://support.microsoft.com/en-us/microsoft-edge/delete-cookies-in-microsoft-edge" target="_blank" rel="noopener">Microsoft Edge</a></li>
      </ul>
    </section>

    <section>
      <h2>6. Contact</h2>
      <p>
        Questions about this policy can be directed to the SoccerOctopus team via
        the <router-link to="/legal">Legal Notice</router-link> page.
      </p>
    </section>

    <div class="back">
      <router-link to="/">← Back to Home</router-link>
    </div>
  </div>
</template>

<script setup>
const STORAGE_KEY = 'so_cookie_consent'

function resetConsent() {
  localStorage.removeItem(STORAGE_KEY)
  window.location.reload()
}
</script>

<style scoped>
.legal {
  max-width: 760px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

h1 { color: #e2b714; font-size: 28px; }

.updated { color: #8888aa; font-size: 13px; margin-top: -20px; }

section {
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 10px;
  padding: 22px 26px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

h2 { color: #a0c0ff; font-size: 16px; font-weight: 700; }

p { color: #c0c0d8; font-size: 14px; line-height: 1.7; margin: 0; }
p strong { color: #e0e0e0; }

a { color: #a0c0ff; text-decoration: none; }
a:hover { text-decoration: underline; }

ul { margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 6px; }
ul li { color: #c0c0d8; font-size: 14px; line-height: 1.6; }

/* Cookie table */
.cookie-table {
  border: 1px solid #0f3460;
  border-radius: 8px;
  overflow: hidden;
  font-size: 13px;
}

.table-header {
  display: grid;
  grid-template-columns: 2fr 1fr 3fr 1.5fr;
  gap: 12px;
  padding: 10px 16px;
  background: #0f3460;
  color: #6a6a8a;
  font-size: 12px;
  font-weight: 600;
}

.table-row {
  display: grid;
  grid-template-columns: 2fr 1fr 3fr 1.5fr;
  gap: 12px;
  padding: 12px 16px;
  border-top: 1px solid #0f1e35;
  align-items: start;
  color: #c0c0d8;
}

.mono {
  font-family: monospace;
  color: #e0e0e0;
  word-break: break-all;
  font-size: 12px;
}

.badge {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 700;
  width: fit-content;
}
.badge.necessary  { background: #1a3a1a; color: #4ade80; }
.badge.analytics  { background: #0f2d5e; color: #60a5fa; }

.btn-reset {
  align-self: flex-start;
  padding: 9px 18px;
  background: transparent;
  border: 1px solid #0f3460;
  border-radius: 8px;
  color: #8888aa;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.btn-reset:hover { border-color: #e2b714; color: #e2b714; }

.back { font-size: 14px; }
.back a { color: #e2b714; }
</style>
