<template>
  <div class="social-buttons">
    <button
      v-for="provider in providers"
      :key="provider.strategy"
      class="btn-social"
      type="button"
      :data-strategy="provider.strategy"
      :disabled="disabled || Boolean(loadingProvider)"
      @click="$emit('select', provider.strategy)"
    >
      <span class="provider-mark" aria-hidden="true">{{ provider.mark }}</span>
      {{ loadingProvider === provider.strategy ? `Opening ${provider.name}...` : `Continue with ${provider.name}` }}
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
</style>
