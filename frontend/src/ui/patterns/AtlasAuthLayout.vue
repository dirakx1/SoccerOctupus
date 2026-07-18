<template>
  <div class="atlas-auth-layout">
    <aside class="atlas-auth-visual">
      <div class="atlas-auth-brand">
        <img src="/favicon.svg" alt="" aria-hidden="true" />
        <span>SoccerOctopus</span>
      </div>

      <div class="atlas-auth-copy">
        <slot name="intro" />
      </div>

      <div class="atlas-auth-pitch" aria-hidden="true">
        <span class="pitch-centre-line" />
        <span class="pitch-centre-circle" />
        <span class="pitch-box pitch-box-top" />
        <span class="pitch-box pitch-box-bottom" />
        <span class="pitch-marker pitch-marker-one" />
        <span class="pitch-marker pitch-marker-two" />
        <span class="pitch-marker pitch-marker-three" />
      </div>

      <p class="atlas-auth-footnote">FIFA World Cup 2026</p>
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
  gap: var(--space-8);
  grid-template-columns: minmax(19rem, .85fr) minmax(20rem, 1fr);
  margin: 0 auto;
  max-width: 72rem;
  padding: var(--space-10) 0;
}

.atlas-auth-visual {
  background: var(--color-surface-inset);
  border: var(--border-width-thin) solid var(--color-border);
  display: flex;
  flex-direction: column;
  min-height: 37rem;
  overflow: hidden;
  padding: var(--space-7);
  position: relative;
}

.atlas-auth-brand {
  align-items: center;
  color: var(--color-text);
  display: inline-flex;
  font-family: var(--font-family-display);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-heavy);
  gap: var(--space-3);
  position: relative;
  z-index: 1;
}

.atlas-auth-brand img { height: 2rem; width: 2rem; }

.atlas-auth-copy {
  margin-top: auto;
  max-width: 19rem;
  position: relative;
  z-index: 1;
}

.atlas-auth-copy :deep(h1) {
  color: var(--color-text);
  font-family: var(--font-family-display);
  font-size: var(--font-size-5xl);
  line-height: var(--line-height-tight);
  margin: 0;
}

.atlas-auth-copy :deep(p) {
  color: var(--color-text-muted);
  font-size: var(--font-size-md);
  line-height: var(--line-height-relaxed);
  margin: var(--space-4) 0 0;
}

.atlas-auth-pitch {
  border: var(--border-width-thin) solid var(--color-border-strong);
  inset: 6.8rem var(--space-7) 7.75rem;
  opacity: .72;
  position: absolute;
}

.pitch-centre-line { background: var(--color-border-strong); height: var(--border-width-thin); left: 0; position: absolute; right: 0; top: 50%; }
.pitch-centre-circle { border: var(--border-width-thin) solid var(--color-border-strong); border-radius: 50%; height: 7.25rem; left: 50%; position: absolute; top: 50%; transform: translate(-50%, -50%); width: 7.25rem; }
.pitch-box { border: var(--border-width-thin) solid var(--color-border-strong); height: 4.75rem; left: 50%; position: absolute; transform: translateX(-50%); width: 55%; }
.pitch-box-top { border-top: 0; top: 0; }
.pitch-box-bottom { border-bottom: 0; bottom: 0; }
.pitch-marker { background: var(--color-accent); border-radius: 50%; box-shadow: 0 0 0 3px var(--color-surface-inset); height: .55rem; position: absolute; width: .55rem; }
.pitch-marker-one { left: 28%; top: 26%; }
.pitch-marker-two { right: 23%; top: 50%; }
.pitch-marker-three { bottom: 22%; left: 42%; }

.atlas-auth-footnote {
  color: var(--color-text-subtle);
  font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data);
  margin: var(--space-6) 0 0;
  position: relative;
  text-transform: uppercase;
  z-index: 1;
}

.atlas-auth-panel {
  align-self: center;
  background: var(--color-surface);
  border: var(--border-width-thin) solid var(--color-border);
  min-width: 0;
  padding: var(--space-8);
}

@media (max-width: 760px) {
  .atlas-auth-layout { display: block; padding: var(--space-6) 0; }
  .atlas-auth-visual { display: none; }
  .atlas-auth-panel { padding: var(--space-5); }
}

@media (max-width: 420px) {
  .atlas-auth-panel { padding: var(--space-4); }
}

@media (prefers-reduced-motion: reduce) {
  .pitch-marker { box-shadow: none; }
}
</style>
