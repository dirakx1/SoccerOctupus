<template>
  <section v-if="visible" class="password-policy" data-testid="password-policy" :aria-label="t('passwordPolicy.heading')">
    <div class="policy-header">
      <h3>{{ t('passwordPolicy.heading') }}</h3>
    </div>
    <div
      v-if="showStrengthMeter"
      class="strength-meter"
      data-testid="password-strength-meter"
    >
      <div class="strength-meter-header">
        <span>{{ t('passwordPolicy.strength') }}</span>
        <strong>{{ strengthLabel }}</strong>
      </div>
      <div
        class="strength-track"
        role="progressbar"
        :aria-label="t('passwordPolicy.strength')"
        aria-valuemin="0"
        aria-valuemax="4"
        :aria-valuenow="normalizedStrength"
        :aria-valuetext="strengthLabel"
      >
        <div
          class="strength-fill"
          :class="strengthClass"
          :style="{ width: strengthWidth }"
        />
      </div>
    </div>
    <ul class="policy-list" aria-live="polite">
      <li
        v-for="rule in visibleRules"
        :key="rule.key"
        :class="['policy-rule', `policy-rule-${rule.status}`]"
      >
        <component :is="iconFor(rule.status)" class="policy-icon" :size="16" aria-hidden="true" />
        <span class="policy-rule-copy">
          <span>{{ labelFor(rule) }}</span>
          <span class="sr-only">{{ t(`passwordPolicy.status.${rule.status}`) }}</span>
        </span>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { computed } from "vue";
import { Check, CircleAlert, Info } from '@lucide/vue';
import { useI18n } from 'vue-i18n';

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
const { t, te } = useI18n();

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
  if (typeof strength.value.score !== "number") return t('passwordPolicy.strengthLabels.low');
  if (strength.value.score >= 4) return t('passwordPolicy.strengthLabels.strong');
  if (strength.value.score >= 3) return t('passwordPolicy.strengthLabels.normal');
  return t('passwordPolicy.strengthLabels.low');
});

function iconFor(status) {
  if (status === "pass") return Check;
  if (status === "fail") return CircleAlert;
  return Info;
}

function labelFor(rule) {
  const key = `passwordPolicy.rules.${rule.key}`;
  if (!te(key)) return rule.label;

  if (rule.key === 'require_special_char' && rule.params.allowedCharacters) {
    return t(key, {
      allowedCharacters: t('passwordPolicy.rules.allowedCharacters', {
        characters: rule.params.allowedCharacters,
      }),
    });
  }

  return t(key, rule.params);
}

defineExpose({
  policy: activePolicy,
});
</script>

<style scoped>
.password-policy {
  background: var(--color-surface-inset);
  border: var(--border-width-thin) solid var(--color-border);
  border-left: var(--border-width-strong) solid var(--color-accent);
  padding: var(--space-4);
}

.policy-header {
  align-items: center;
  display: flex;
  gap: var(--space-3);
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.policy-header h3 {
  color: var(--color-text);
  font-family: var(--font-family-display);
  font-size: var(--font-size-md);
  margin: 0;
}

.policy-header small {
  color: var(--color-text-subtle);
  font-size: var(--font-size-xs);
}

.policy-list {
  display: grid;
  gap: var(--space-2);
  list-style: none;
  margin: 0;
  padding: 0;
}

.strength-meter {
  margin-bottom: var(--space-4);
}

.strength-meter-header {
  align-items: center;
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}

.strength-meter-header span {
  color: var(--color-text-muted);
  font-size: var(--font-size-xs);
}

.strength-meter-header strong {
  color: var(--color-text);
  font-family: var(--font-family-data);
  font-size: var(--font-size-xs);
}

.strength-track {
  background: var(--color-surface-raised);
  border: var(--border-width-thin) solid var(--color-border);
  border-radius: var(--radius-sm);
  height: 8px;
  overflow: hidden;
}

.strength-fill {
  border-radius: inherit;
  height: 100%;
  transition:
    width var(--duration-normal) var(--easing-standard),
    background-color var(--duration-normal) var(--easing-standard);
}

.strength-weak {
  background: var(--color-danger);
}

.strength-normal {
  background: var(--color-warning);
}

.strength-strong {
  background: var(--color-success);
}

.policy-rule {
  align-items: flex-start;
  color: var(--color-text-muted);
  display: flex;
  font-size: var(--font-size-sm);
  gap: var(--space-2);
  line-height: var(--line-height-normal);
}

.policy-icon {
  display: block;
  flex: 0 0 auto;
  margin-top: 0.16rem;
}

.policy-rule-pass .policy-icon {
  color: var(--color-success);
}

.policy-rule-fail .policy-icon {
  color: var(--color-danger);
}

.policy-rule-info .policy-icon {
  color: var(--color-information);
}

.policy-rule-copy { min-width: 0; }
.sr-only { height: 1px; margin: -1px; overflow: hidden; padding: 0; position: absolute; width: 1px; clip: rect(0, 0, 0, 0); white-space: nowrap; }

@media (prefers-reduced-motion: reduce) {
  .strength-fill { transition: none; }
}
</style>
