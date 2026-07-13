<template>
  <div v-if="visible" class="password-policy" data-testid="password-policy">
    <div class="policy-header">
      <span>Password requirements</span>
    </div>
    <div
      v-if="showStrengthMeter"
      class="strength-meter"
      data-testid="password-strength-meter"
    >
      <div class="strength-meter-header">
        <span>Password strength</span>
        <strong>{{ strengthLabel }}</strong>
      </div>
      <div class="strength-track" aria-hidden="true">
        <div
          class="strength-fill"
          :class="strengthClass"
          :style="{ width: strengthWidth }"
        />
      </div>
    </div>
    <ul class="policy-list">
      <li
        v-for="rule in visibleRules"
        :key="rule.key"
        :class="['policy-rule', `policy-rule-${rule.status}`]"
      >
        <span class="policy-icon" aria-hidden="true">{{
          iconFor(rule.status)
        }}</span>
        <span>{{ rule.label }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed } from "vue";

import { usePasswordPolicy } from "../composables/usePasswordPolicy";

const props = defineProps({
  password: {
    type: String,
    default: "",
  },
  validator: {
    type: Function,
    default: null,
  },
  clerk: {
    type: Object,
    default: null,
  },
  policy: {
    type: Object,
    default: null,
  },
  visible: {
    type: Boolean,
    default: true,
  },
});

const localPolicy = usePasswordPolicy({
  password: computed(() => props.password),
  validator: computed(() => props.validator),
  clerk: computed(() => props.clerk),
});

const activePolicy = computed(() => props.policy || localPolicy);
const rules = computed(
  () => activePolicy.value.rules?.value || activePolicy.value.rules || [],
);
const visibleRules = computed(() =>
  rules.value.filter((rule) => rule.key !== "min_zxcvbn_strength"),
);
const settings = computed(
  () => activePolicy.value.settings?.value || activePolicy.value.settings || {},
);
const strength = computed(
  () =>
    activePolicy.value.strength?.value ||
    activePolicy.value.strength || { score: null },
);
const showStrengthMeter = computed(() => Boolean(settings.value.show_zxcvbn));
const normalizedStrength = computed(() => {
  if (typeof strength.value.score !== "number") return 0;
  return Math.max(0, Math.min(4, strength.value.score));
});
const strengthWidth = computed(
  () => `${((normalizedStrength.value + 1) / 5) * 100}%`,
);
const strengthClass = computed(() => {
  if (typeof strength.value.score !== "number") return "strength-weak";
  if (strength.value.score >= 4) return "strength-strong";
  if (strength.value.score >= 3) return "strength-normal";
  return "strength-weak";
});
const strengthLabel = computed(() => {
  if (typeof strength.value.score !== "number") return "Low";
  if (strength.value.score >= 4) return "Strong";
  if (strength.value.score >= 3) return "Normal";
  return "Low";
});

function iconFor(status) {
  if (status === "pass") return "OK";
  if (status === "fail") return "!";
  return "i";
}

defineExpose({
  policy: activePolicy,
});
</script>

<style scoped>
.password-policy {
  background: #0a0a1a;
  border: 1px solid #0f3460;
  border-radius: 8px;
  padding: 12px 14px;
}

.policy-header {
  align-items: center;
  display: flex;
  gap: 12px;
  justify-content: space-between;
  margin-bottom: 8px;
}

.policy-header span {
  color: #e0e0e0;
  font-size: 13px;
  font-weight: 700;
}

.policy-header small {
  color: #8888aa;
  font-size: 11px;
}

.policy-list {
  display: grid;
  gap: 6px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.strength-meter {
  margin-bottom: 10px;
}

.strength-meter-header {
  align-items: center;
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}

.strength-meter-header span {
  color: #a0aec0;
  font-size: 12px;
}

.strength-meter-header strong {
  color: #e0e0e0;
  font-size: 12px;
}

.strength-track {
  background: #050511;
  border: 1px solid #0f3460;
  border-radius: 999px;
  height: 8px;
  overflow: hidden;
}

.strength-fill {
  border-radius: inherit;
  height: 100%;
  transition:
    width 160ms ease,
    background-color 160ms ease;
}

.strength-weak {
  background: #ef4444;
}

.strength-normal {
  background: #f59e0b;
}

.strength-strong {
  background: #22c55e;
}

.policy-rule {
  align-items: flex-start;
  color: #a0aec0;
  display: flex;
  font-size: 12px;
  gap: 8px;
  line-height: 1.4;
}

.policy-icon {
  border-radius: 999px;
  display: inline-flex;
  flex: 0 0 auto;
  font-size: 10px;
  font-weight: 800;
  justify-content: center;
  min-width: 18px;
  padding: 1px 4px;
}

.policy-rule-pass .policy-icon {
  background: #123322;
  color: #9ae6b4;
}

.policy-rule-fail .policy-icon {
  background: #3d1a1a;
  color: #fc8181;
}

.policy-rule-info .policy-icon {
  background: #0f3460;
  color: #c0c0d0;
}
</style>
