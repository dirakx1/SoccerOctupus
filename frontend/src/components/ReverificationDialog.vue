<template>
  <Teleport to="body">
    <div v-if="workflow?.isOpen?.value" class="reverification-backdrop">
      <form class="reverification-dialog" role="dialog" aria-modal="true" @submit.prevent="workflow.submit">
        <div class="dialog-heading">
          <h2>{{ workflow.title.value }}</h2>
          <p>{{ workflow.copy.value }}</p>
        </div>

        <p v-if="workflow.error.value" class="error-box">{{ workflow.error.value }}</p>

        <label v-if="workflow.strategy.value === 'password'" class="field">
          <span>{{ t('common.reverification.password') }}</span>
          <input
            v-model="workflow.password.value"
            type="password"
            autocomplete="current-password"
            autofocus
            :placeholder="t('common.reverification.passwordPlaceholder')"
          />
        </label>

        <label v-if="workflow.usesVerificationCode.value" class="field">
          <span>{{ workflow.verificationCodeLabel.value }}</span>
          <input
            v-model.trim="workflow.code.value"
            type="text"
            :inputmode="workflow.codeInputMode.value"
            autocomplete="one-time-code"
            autofocus
            :placeholder="workflow.codePlaceholder.value"
          />
        </label>

        <button
          v-if="workflow.canSwitchSecondFactor.value"
          class="btn-link"
          type="button"
          :disabled="workflow.loading.value"
          @click="workflow.switchSecondFactor"
        >
          {{ workflow.alternativeSecondFactorLabel.value }}
        </button>

        <div class="action-row">
          <button class="btn-primary" type="submit" :disabled="workflow.loading.value || !workflow.canSubmit.value">
            {{ workflow.loading.value ? t('common.reverification.verifying') : t('common.reverification.continue') }}
          </button>
          <button class="btn-secondary" type="button" :disabled="workflow.loading.value" @click="workflow.cancel">
            {{ t('common.reverification.cancel') }}
          </button>
        </div>
      </form>
    </div>
  </Teleport>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps({
  workflow: {
    type: Object,
    default: null,
  },
})
</script>

<style scoped>
.reverification-backdrop {
  align-items: center;
  background: rgb(17 21 20 / 68%);
  display: flex;
  inset: 0;
  justify-content: center;
  padding: var(--space-5);
  position: fixed;
  z-index: var(--z-modal);
}

.reverification-dialog {
  background: var(--color-surface-raised);
  border: var(--border-width-thin) solid var(--color-border-strong);
  border-top: var(--border-width-strong) solid var(--color-accent);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  max-width: 420px;
  padding: var(--space-6);
  width: min(100%, 420px);
}

.dialog-heading h2 {
  color: var(--color-text);
  font-family: var(--font-family-display);
  font-size: var(--font-size-2xl);
  margin: 0 0 var(--space-2);
}

.dialog-heading p {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.field span {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
}

input {
  background: var(--color-surface);
  border: var(--border-width-thin) solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  font-size: var(--font-size-sm);
  min-height: var(--control-height-lg);
  padding: 0 var(--space-3);
}

input:focus-visible,
button:focus-visible {
  outline: var(--border-width-strong) solid var(--color-focus);
  outline-offset: 3px;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.btn-primary,
.btn-secondary,
.btn-link {
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  min-height: var(--control-height-lg);
  padding: 0 var(--space-4);
}

.btn-link {
  align-self: flex-start;
  background: transparent;
  border: none;
  color: var(--color-accent);
  min-height: auto;
  padding: 0;
}

.btn-primary {
  background: var(--color-accent);
  border: 0;
  color: var(--color-accent-contrast);
}

.btn-secondary {
  background: var(--color-surface);
  border: var(--border-width-thin) solid var(--color-border-strong);
  color: var(--color-text);
}

button:disabled {
  cursor: default;
  opacity: 0.55;
}

.error-box {
  background: var(--color-danger-surface);
  border: var(--border-width-thin) solid var(--color-danger);
  color: var(--color-danger);
  font-size: var(--font-size-sm);
  padding: var(--space-3);
}
</style>
