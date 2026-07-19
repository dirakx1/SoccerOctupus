<template>
  <label class="field secret-field">
    <span>{{ label }}</span>
    <div class="secret-control">
      <input
        :value="modelValue"
        :type="visible ? 'text' : 'password'"
        autocomplete="new-password"
        :placeholder="placeholder"
        @input="updateValue"
      />
      <button
        type="button"
        class="icon-button"
        :aria-label="visible ? hideLabel : showLabel"
        @click="visible = !visible"
      >
        <EyeOff v-if="visible" :size="18" aria-hidden="true" />
        <Eye v-else :size="18" aria-hidden="true" />
      </button>
      <button
        type="button"
        class="icon-button danger"
        :disabled="!configured"
        :aria-label="clearLabel"
        @click="clearKey"
      >
        <X :size="18" aria-hidden="true" />
      </button>
    </div>
    <strong :class="['status-pill', configured ? 'configured' : 'missing']">
      {{ configured ? configuredLabel : notConfiguredLabel }}
    </strong>
  </label>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Eye, EyeOff, X } from '@lucide/vue'

const props = defineProps({
  label: { type: String, required: true },
  modelValue: { type: String, default: '' },
  configured: { type: Boolean, default: false },
  placeholder: { type: String, default: 'Paste a new key to replace' },
  configuredLabel: { type: String, default: 'Configured' },
  notConfiguredLabel: { type: String, default: 'Not configured' },
  showLabel: { type: String, default: 'Show API key' },
  hideLabel: { type: String, default: 'Hide API key' },
  clearLabel: { type: String, default: 'Clear stored API key' },
})

const emit = defineEmits(['update:modelValue', 'clear', 'edit'])
const visible = ref(false)

watch(
  () => props.modelValue,
  (value) => {
    if (!value) visible.value = false
  }
)

function updateValue(event) {
  emit('update:modelValue', event.target.value)
  emit('edit')
}

function clearKey() {
  visible.value = false
  emit('update:modelValue', '')
  emit('clear')
}
</script>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

.secret-control {
  position: relative;
}

input {
  width: 100%;
  background: var(--color-surface-raised);
  color: var(--color-text);
  border: var(--border-width-thin) solid var(--color-border-strong);
  border-radius: var(--radius-md);
  padding: 0 5.5rem 0 var(--space-3);
  font-size: var(--font-size-sm);
  min-height: var(--control-height-lg);
}

input::placeholder { color: var(--color-text-subtle); }

input:focus {
  border-color: var(--color-focus);
  outline: var(--border-width-thin) solid var(--color-focus);
  outline-offset: 2px;
}

.status-pill {
  align-self: flex-start;
  border-radius: var(--radius-md);
  font: var(--font-weight-bold) var(--font-size-xs)/var(--line-height-normal) var(--font-family-data);
  padding: var(--space-1) var(--space-2);
  text-transform: uppercase;
}

.status-pill.configured {
  background: var(--color-success-surface);
  color: var(--color-success);
}

.status-pill.missing {
  background: var(--color-warning-surface);
  color: var(--color-warning);
}

.icon-button {
  position: absolute;
  top: var(--space-2);
  right: 2.75rem;
  width: 2rem;
  height: 2rem;
  background: transparent;
  border: var(--border-width-thin) solid transparent;
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  cursor: pointer;
  display: grid;
  place-items: center;
}

.icon-button.danger {
  right: var(--space-2);
  color: var(--color-danger);
}

.icon-button:hover:not(:disabled),
.icon-button:focus-visible {
  background: var(--color-surface-inset);
  border-color: var(--color-focus);
  outline: var(--border-width-thin) solid var(--color-focus);
  outline-offset: 2px;
}

.icon-button.danger:hover:not(:disabled),
.icon-button.danger:focus-visible {
  background: var(--color-danger-surface);
  border-color: var(--color-danger);
}

.icon-button:disabled {
  color: var(--color-text-subtle);
  cursor: not-allowed;
}

</style>
