<template>
  <div class="social-buttons">
    <button
      v-for="provider in providers"
      :key="provider.strategy"
      :class="['btn-social', { 'btn-social-atlas': appearance === 'atlas' }]"
      type="button"
      :data-strategy="provider.strategy"
      :disabled="disabled || Boolean(loadingProvider)"
      @click="$emit('select', provider.strategy)"
    >
      <span class="provider-mark" aria-hidden="true">{{ provider.mark }}</span>
      {{ loadingProvider === provider.strategy ? labels.opening(provider.name) : labels.continueWith(provider.name) }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  disabled: {
    type: Boolean,
    default: false,
  },
  loadingProvider: {
    type: String,
    default: '',
  },
  appearance: { type: String, default: 'legacy' },
  labels: {
    type: Object,
    default: () => ({
      continueWith: (name) => `Continue with ${name}`,
      opening: (name) => `Opening ${name}...`,
    }),
  },
})

defineEmits(['select'])

const providers = [
  { name: 'Google', mark: 'G', strategy: 'oauth_google' },
  { name: 'X', mark: 'X', strategy: 'oauth_x' },
]
</script>

<style scoped>
.social-buttons {
  display: grid;
  gap: 10px;
}

.btn-social {
  align-items: center;
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  color: #1f2937;
  cursor: pointer;
  display: flex;
  font-size: 15px;
  font-weight: 700;
  gap: 10px;
  justify-content: center;
  padding: 12px 20px;
  transition: opacity 0.2s, transform 0.2s;
}

.btn-social:hover:not(:disabled) {
  transform: translateY(-1px);
}

.btn-social:disabled {
  cursor: default;
  opacity: 0.55;
}

.provider-mark {
  align-items: center;
  color: #2563eb;
  display: inline-flex;
  font-size: 17px;
  font-weight: 800;
  height: 20px;
  justify-content: center;
  width: 20px;
}

.btn-social-atlas {
  background: var(--color-surface-raised);
  border-color: var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  min-height: var(--control-height-lg);
  padding: 0 var(--space-4);
  transition: background-color var(--duration-fast) var(--easing-standard), border-color var(--duration-fast) var(--easing-standard), color var(--duration-fast) var(--easing-standard);
}

.btn-social-atlas:hover:not(:disabled) {
  background: var(--color-surface-inset);
  border-color: var(--color-accent);
  transform: none;
}

.btn-social-atlas:focus-visible {
  outline: var(--border-width-strong) solid var(--color-focus);
  outline-offset: 3px;
}

.btn-social-atlas .provider-mark { color: var(--color-accent); }
</style>
