<template>
  <div class="atlas-auth-layout">
    <aside class="atlas-auth-visual">
      <div class="atlas-auth-copy">
        <slot name="intro" />
      </div>

      <div class="atlas-auth-analysis" aria-hidden="true">
        <div class="analysis-field">
          <span class="analysis-halfway" />
          <span class="analysis-circle" />
          <span class="analysis-box analysis-box-left" />
          <span class="analysis-box analysis-box-right" />
          <span class="analysis-route analysis-route-one" />
          <span class="analysis-route analysis-route-two" />
          <span class="analysis-node analysis-node-one" />
          <span class="analysis-node analysis-node-two" />
          <span class="analysis-node analysis-node-three" />
          <span class="analysis-node analysis-node-four" />
        </div>

        <div class="analysis-card analysis-card-score">
          <span class="analysis-label">SoccerOctopus</span>
          <strong>Match intelligence</strong>
          <span class="analysis-card-rule" />
          <span class="analysis-card-detail">Form, tactics and market signals</span>
        </div>

        <div class="analysis-card analysis-card-stat">
          <span class="analysis-label">Five-agent model</span>
          <strong class="analysis-stat-value">One <small>signal</small></strong>
          <span class="analysis-card-detail">Every competition. Every match.</span>
        </div>
      </div>

      <p class="atlas-auth-footnote">Football intelligence</p>
    </aside>

    <section class="atlas-auth-panel">
      <slot />
    </section>
  </div>
</template>

<style scoped>
.atlas-auth-layout {
  align-items: stretch;
  display: grid;
  gap: clamp(var(--space-10), 5vw, var(--space-20));
  grid-template-columns: minmax(23rem, .72fr) minmax(20rem, 1fr);
  margin: 0 auto;
  max-width: 78rem;
  padding: clamp(var(--space-8), 5vw, var(--space-16)) 0;
}

.atlas-auth-visual {
  background: #17231e;
  border: 0;
  color: #edf4ed;
  display: flex;
  flex-direction: column;
  min-height: min(44rem, calc(100dvh - 8rem));
  overflow: hidden;
  padding: clamp(var(--space-6), 3vw, var(--space-10));
  position: relative;
}

.atlas-auth-visual::before {
  border: 1px solid rgb(183 220 197 / 18%);
  content: '';
  inset: var(--space-4);
  pointer-events: none;
  position: absolute;
}

.atlas-auth-visual::after {
  border-bottom: 1px solid rgb(183 220 197 / 12%);
  border-top: 1px solid rgb(183 220 197 / 12%);
  content: '';
  inset: 28% 0 auto;
  height: 43%;
  pointer-events: none;
  position: absolute;
}

.atlas-auth-copy {
  margin-top: clamp(5rem, 12vh, 8rem);
  max-width: 21rem;
  position: relative;
  z-index: 1;
}

.atlas-auth-copy :deep(h1) {
  color: inherit;
  font-family: var(--font-family-display);
  font-size: clamp(2.6rem, 4vw, 4.5rem);
  line-height: var(--line-height-tight);
  margin: 0;
  text-wrap: balance;
}

.atlas-auth-copy :deep(p) {
  color: rgb(232 242 234 / 76%);
  font-size: var(--font-size-md);
  line-height: var(--line-height-relaxed);
  margin: var(--space-4) 0 0;
  max-width: 18rem;
}

.atlas-auth-analysis {
  bottom: -2.5rem;
  height: 19rem;
  pointer-events: none;
  position: absolute;
  right: -1.5rem;
  width: min(29rem, 88%);
  z-index: 1;
}

.analysis-field {
  border: 1px solid rgb(183 220 197 / 32%);
  height: 13rem;
  left: 0;
  overflow: hidden;
  position: absolute;
  top: 2rem;
  transform: rotate(-8deg);
  width: 20rem;
}

.analysis-halfway { background: rgb(183 220 197 / 32%); height: 1px; left: 50%; position: absolute; top: 0; bottom: 0; width: 1px; }
.analysis-circle { border: 1px solid rgb(183 220 197 / 32%); border-radius: 50%; height: 5.25rem; left: 50%; position: absolute; top: 50%; transform: translate(-50%, -50%); width: 5.25rem; }
.analysis-box { border: 1px solid rgb(183 220 197 / 32%); height: 55%; position: absolute; top: 50%; transform: translateY(-50%); width: 16%; }
.analysis-box-left { border-left: 0; left: 0; }
.analysis-box-right { border-right: 0; right: 0; }
.analysis-route { border-top: 1px solid #a9d6b9; height: 2.8rem; opacity: .8; position: absolute; transform-origin: left center; width: 7rem; }
.analysis-route-one { left: 30%; top: 39%; transform: rotate(-22deg); }
.analysis-route-two { left: 50%; top: 52%; transform: rotate(38deg); width: 5rem; }
.analysis-node { background: #c9e9d2; box-shadow: 0 0 0 3px #17231e; height: .55rem; position: absolute; width: .55rem; }
.analysis-node-one { left: 27%; top: 42%; }
.analysis-node-two { left: 51%; top: 31%; }
.analysis-node-three { left: 72%; top: 61%; }
.analysis-node-four { background: #f2c350; left: 48%; top: 51%; }

.analysis-card {
  background: #f4f1e8;
  box-shadow: 0 16px 30px rgb(5 15 10 / 32%);
  color: #1d2b23;
  display: flex;
  flex-direction: column;
  padding: var(--space-4);
  position: absolute;
}

.analysis-card-score { right: .4rem; top: 0; width: 12rem; }
.analysis-card-stat { bottom: 1rem; left: 1.25rem; width: 9.2rem; }
.analysis-label { color: #617068; font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data); text-transform: uppercase; }
.analysis-card strong { font-family: var(--font-family-display); font-size: var(--font-size-xl); line-height: var(--line-height-tight); margin-top: var(--space-2); }
.analysis-card-rule { background: #c7d2c9; height: 1px; margin: var(--space-3) 0; width: 100%; }
.analysis-card-detail { color: #617068; font-size: var(--font-size-xs); line-height: var(--line-height-normal); }
.analysis-stat-value { align-items: baseline; display: flex; gap: var(--space-2); }
.analysis-stat-value small { color: #617068; font: var(--font-weight-semibold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-body); }

.atlas-auth-footnote {
  color: rgb(232 242 234 / 62%);
  font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data);
  margin: auto 0 0;
  position: relative;
  text-transform: uppercase;
  z-index: 1;
}

.atlas-auth-panel {
  align-self: center;
  min-width: 0;
  padding: clamp(var(--space-4), 2.5vw, var(--space-8));
  width: min(100%, 32rem);
}

@media (max-width: 760px) {
  .atlas-auth-layout { display: block; padding: var(--space-6) 0; }
  .atlas-auth-visual { min-height: auto; padding: var(--space-4) var(--space-5); }
  .atlas-auth-visual::before, .atlas-auth-visual::after, .atlas-auth-copy, .atlas-auth-analysis, .atlas-auth-footnote { display: none; }
  .atlas-auth-panel { margin: var(--space-6) auto 0; padding: 0; }
}

@media (max-width: 420px) {
  .atlas-auth-layout { padding: var(--space-4) 0; }
}

@media (prefers-reduced-motion: reduce) {
  .analysis-node { box-shadow: none; }
}
</style>
