<template>
  <div
    v-if="visible"
    class="billing-status"
    :class="[severityClass, { compact }]"
    role="status"
    aria-live="polite"
  >
    <component :is="statusIcon" :size="19" class="status-icon" aria-hidden="true" />
    <span class="message">{{ localizedMessage }}</span>
    <button
      v-if="health.action"
      class="status-action"
      type="button"
      :disabled="loading"
      :aria-label="loading ? t('predictions.billing.opening') : localizedAction"
      @click="emit('action')"
    >
      <LoaderCircle v-if="loading" :size="16" class="spin" aria-hidden="true" />
      <template v-else>
        <span>{{ localizedAction }}</span>
        <ArrowRight :size="16" aria-hidden="true" />
      </template>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { AlertTriangle, ArrowRight, CircleAlert, Info, LoaderCircle } from '@lucide/vue'

const props = defineProps({
  health: { type: Object, default: () => ({}) },
  compact: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['action'])
const { t } = useI18n()

const stateMessageKeys = {
  payment_failed: 'predictions.billing.states.payment_failed',
  payment_required: 'predictions.billing.states.payment_required',
  canceled: 'predictions.billing.states.canceled',
}
const actionLabelKeys = {
  manage_billing: 'predictions.billing.actions.manage_billing',
  update_payment_method: 'predictions.billing.actions.update_payment_method',
  choose_plan: 'predictions.billing.actions.choose_plan',
}

const visible = computed(() => Boolean(props.health?.message && (
  props.health.requires_attention || props.health.severity === 'info'
)))
const severityClass = computed(() => `is-${props.health?.severity || 'info'}`)
const localizedMessage = computed(() => {
  if (props.health?.state === 'healthy' && props.health?.severity === 'info') {
    return t('predictions.billing.states.plan_ending')
  }
  const key = stateMessageKeys[props.health?.state]
  return key ? t(key) : props.health?.message
})
const localizedAction = computed(() => {
  const key = actionLabelKeys[props.health?.action]
  return key ? t(key) : props.health?.action_label
})
const statusIcon = computed(() => {
  if (props.health?.severity === 'danger') return CircleAlert
  if (props.health?.severity === 'warning') return AlertTriangle
  return Info
})
</script>

<style scoped>
.billing-status {
  align-items: center;
  background: var(--color-warning-surface);
  border: var(--border-width-thin) solid var(--color-warning);
  color: var(--color-warning);
  display: flex;
  gap: var(--space-3);
  line-height: var(--line-height-normal);
  padding: var(--space-3) var(--space-4);
}
.billing-status.compact { align-items: flex-start; flex-wrap: wrap; margin-top: var(--space-3); }
.billing-status.is-danger { background: var(--color-danger-surface); border-color: var(--color-danger); color: var(--color-danger); }
.billing-status.is-info { background: var(--color-information-surface); border-color: var(--color-information); color: var(--color-information); }
.status-icon { flex: 0 0 auto; margin-top: var(--space-1); }
.message { flex: 1; min-width: 12rem; }
.status-action {
  align-items: center;
  background: var(--color-surface-raised);
  border: var(--border-width-thin) solid currentColor;
  border-radius: var(--radius-md);
  color: inherit;
  cursor: pointer;
  display: inline-flex;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  gap: var(--space-2);
  justify-content: center;
  min-height: var(--control-height-lg);
  padding: 0 var(--space-3);
}
.status-action:hover:not(:disabled) { background: var(--color-surface); }
.status-action:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
.status-action:disabled { cursor: not-allowed; opacity: 0.65; }
.spin { animation: billing-spin 0.9s linear infinite; }
@keyframes billing-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spin { animation: none; } }
</style>
