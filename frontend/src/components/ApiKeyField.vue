<template>
  <label class="field secret-field">
    <span>{{ label }}</span>
    <div class="secret-control">
      <input
        :value="modelValue"
        :type="visible ? 'text' : 'password'"
        autocomplete="new-password"
        placeholder="Paste a new key to replace"
        @input="updateValue"
      />
      <button
        type="button"
        class="icon-button"
        :aria-label="visible ? 'Hide API key' : 'Show API key'"
        @click="visible = !visible"
      >
        <svg v-if="visible" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M3 3.8 4.3 2.5l17.2 17.2-1.3 1.3-3-3A10.8 10.8 0 0 1 12 19c-5.4 0-9.3-4.4-10.7-6.2a1.3 1.3 0 0 1 0-1.6A18.2 18.2 0 0 1 6.2 6.1L3 3.8Zm6 5.5a4 4 0 0 0 5.2 5.2L12.7 13A2 2 0 0 1 11 9.3L9 7.2Zm3-4.3c5.4 0 9.3 4.4 10.7 6.2.4.5.4 1.1 0 1.6a18 18 0 0 1-2.4 2.7l-3.1-3.1A5.1 5.1 0 0 0 12 6.9c-.6 0-1.2.1-1.8.3L8.1 5.1A11 11 0 0 1 12 5Z" />
        </svg>
        <svg v-else viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 5c5.4 0 9.3 4.4 10.7 6.2.4.5.4 1.1 0 1.6C21.3 14.6 17.4 19 12 19s-9.3-4.4-10.7-6.2a1.3 1.3 0 0 1 0-1.6C2.7 9.4 6.6 5 12 5Zm0 2c-4.2 0-7.5 3.3-8.8 5 1.3 1.7 4.6 5 8.8 5s7.5-3.3 8.8-5C19.5 10.3 16.2 7 12 7Zm0 2.2a2.8 2.8 0 1 1 0 5.6 2.8 2.8 0 0 1 0-5.6Z" />
        </svg>
      </button>
      <button
        type="button"
        class="icon-button danger"
        :disabled="!configured"
        aria-label="Clear stored API key"
        @click="clearKey"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M6.4 5 5 6.4 10.6 12 5 17.6 6.4 19l5.6-5.6 5.6 5.6 1.4-1.4-5.6-5.6L19 6.4 17.6 5 12 10.6 6.4 5Z" />
        </svg>
      </button>
    </div>
    <strong :class="['status-pill', configured ? 'configured' : 'missing']">
      {{ configured ? 'Configured' : 'Not configured' }}
    </strong>
  </label>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  modelValue: { type: String, default: '' },
  configured: { type: Boolean, default: false },
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
  color: #a0a0bd;
  font-size: 13px;
}

.secret-control {
  position: relative;
}

input {
  width: 100%;
  background: #0a0a1a;
  color: #e0e0e0;
  border: 1px solid #0f3460;
  border-radius: 8px;
  padding: 10px 88px 10px 12px;
  font-size: 14px;
  min-height: 44px;
}

input::placeholder { color: #51516b; }

input:focus {
  border-color: #e2b714;
  outline: none;
}

.status-pill {
  align-self: flex-start;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  padding: 5px 9px;
  text-transform: uppercase;
}

.status-pill.configured {
  background: rgba(46, 160, 67, 0.14);
  color: #9ae6b4;
}

.status-pill.missing {
  background: rgba(226, 183, 20, 0.12);
  color: #f6d860;
}

.icon-button {
  position: absolute;
  top: 6px;
  right: 44px;
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 7px;
  color: #f6d860;
  cursor: pointer;
  display: grid;
  place-items: center;
}

.icon-button.danger {
  right: 8px;
  color: #fc8181;
}

.icon-button:hover:not(:disabled),
.icon-button:focus-visible {
  background: rgba(226, 183, 20, 0.12);
  border-color: rgba(226, 183, 20, 0.35);
  outline: none;
}

.icon-button.danger:hover:not(:disabled),
.icon-button.danger:focus-visible {
  background: rgba(252, 129, 129, 0.1);
  border-color: rgba(252, 129, 129, 0.35);
}

.icon-button:disabled {
  color: #6a6a8a;
  cursor: not-allowed;
}

.icon-button svg {
  width: 18px;
  height: 18px;
  fill: currentColor;
}
</style>
