<template>
  <div v-if="visible" class="password-policy" data-testid="password-policy">
    <div class="policy-header">
      <span>Password requirements</span>
      <small>{{ sourceLabel }}</small>
    </div>
    <ul class="policy-list">
      <li
        v-for="rule in rules"
        :key="rule.key"
        :class="['policy-rule', `policy-rule-${rule.status}`]"
      >
        <span class="policy-icon" aria-hidden="true">{{ iconFor(rule.status) }}</span>
        <span>{{ rule.label }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import { usePasswordPolicy } from '../composables/usePasswordPolicy'

const props = defineProps({
  password: {
    type: String,
    default: '',
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
})

const localPolicy = usePasswordPolicy({
  password: computed(() => props.password),
  validator: computed(() => props.validator),
  clerk: computed(() => props.clerk),
})

const activePolicy = computed(() => props.policy || localPolicy)
const rules = computed(() => activePolicy.value.rules?.value || activePolicy.value.rules || [])
const source = computed(() => activePolicy.value.source?.value || activePolicy.value.source || 'fallback')
const sourceLabel = computed(() => source.value === 'clerk' ? 'Synced from Clerk' : 'Fallback policy')

function iconFor(status) {
  if (status === 'pass') return 'OK'
  if (status === 'fail') return '!'
  return 'i'
}

defineExpose({
  policy: activePolicy,
})
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
