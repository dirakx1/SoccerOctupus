<template>
  <header class="atlas-page-header">
    <div class="atlas-page-header-copy">
      <p v-if="eyebrow" class="atlas-page-header-eyebrow">{{ eyebrow }}</p>
      <h1>{{ title }}</h1>
      <p v-if="description" class="atlas-page-header-description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="atlas-page-header-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup>
defineProps({
  eyebrow: { type: String, default: '' },
  title: { type: String, required: true },
  description: { type: String, default: '' },
})
</script>

<style scoped>
.atlas-page-header {
  align-items: end;
  border-bottom: var(--border-width-thin) solid var(--color-border);
  display: flex;
  gap: var(--space-8);
  justify-content: space-between;
  padding-bottom: var(--space-6);
}

.atlas-page-header-copy { min-width: 0; }

.atlas-page-header-eyebrow {
  color: var(--color-accent);
  font: var(--font-weight-bold) var(--font-size-xs) / var(--line-height-normal) var(--font-family-data);
  margin: 0 0 var(--space-3);
  text-transform: uppercase;
}

.atlas-page-header h1 {
  font-family: var(--font-family-display);
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-heavy);
  line-height: var(--line-height-tight);
  margin: 0;
  max-width: 18ch;
}

.atlas-page-header-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-md);
  line-height: var(--line-height-relaxed);
  margin: var(--space-4) 0 0;
  max-width: 62ch;
}

.atlas-page-header-actions {
  align-items: end;
  display: flex;
  flex: 0 0 auto;
  gap: var(--space-3);
}

@media (max-width: 640px) {
  .atlas-page-header { align-items: start; flex-direction: column; gap: var(--space-5); }
  .atlas-page-header h1 { font-size: var(--font-size-3xl); }
  .atlas-page-header-actions { align-items: start; }
}
</style>
