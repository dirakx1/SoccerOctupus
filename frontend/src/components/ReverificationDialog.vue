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
          <span>Password</span>
          <input
            v-model="workflow.password.value"
            type="password"
            autocomplete="current-password"
            autofocus
            placeholder="Enter your password"
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
            {{ workflow.loading.value ? 'Verifying...' : 'Continue' }}
          </button>
          <button class="btn-secondary" type="button" :disabled="workflow.loading.value" @click="workflow.cancel">
            Cancel
          </button>
        </div>
      </form>
    </div>
  </Teleport>
</template>

<script setup>
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
  background: rgba(2, 6, 23, 0.72);
  display: flex;
  inset: 0;
  justify-content: center;
  padding: 20px;
  position: fixed;
  z-index: 1000;
}

.reverification-dialog {
  background: #0a0a1a;
  border: 1px solid #0f3460;
  border-radius: 12px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.45);
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 420px;
  padding: 20px;
  width: min(100%, 420px);
}

.dialog-heading h2 {
  color: #e0e0e0;
  font-size: 18px;
  margin-bottom: 6px;
}

.dialog-heading p {
  color: #a0aec0;
  font-size: 13px;
  line-height: 1.5;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  color: #8888aa;
  font-size: 13px;
}

input {
  background: #050511;
  border: 1px solid #0f3460;
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 14px;
  padding: 12px 14px;
}

input:focus {
  border-color: #e2b714;
  outline: none;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.btn-primary,
.btn-secondary,
.btn-link {
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  min-height: 40px;
  padding: 10px 14px;
}

.btn-link {
  align-self: flex-start;
  background: transparent;
  border: none;
  color: #e2b714;
  min-height: auto;
  padding: 0;
}

.btn-primary {
  background: linear-gradient(135deg, #e2b714, #f6d860);
  border: none;
  color: #0a0a1a;
}

.btn-secondary {
  background: #0f3460;
  border: 1px solid #1f4c7a;
  color: #e0e0e0;
}

button:disabled {
  cursor: default;
  opacity: 0.55;
}

.error-box {
  background: #3d1a1a;
  border: 1px solid #c53030;
  border-radius: 8px;
  color: #fc8181;
  font-size: 13px;
  padding: 12px 14px;
}
</style>
