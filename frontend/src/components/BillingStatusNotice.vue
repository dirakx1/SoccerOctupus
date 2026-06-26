<template>
  <div v-if="visible" class="billing-status" :class="[severityClass, { compact }]">
    <component :is="statusIcon" :size="18" class="status-icon" aria-hidden="true" />
    <span class="message">{{ health.message }}</span>
    <button
      v-if="health.action"
      class="status-action"
      type="button"
      :disabled="loading"
      :aria-label="loading ? 'Opening billing' : health.action_label"
      @click="$emit('action')"
    >
      <LoaderCircle v-if="loading" :size="16" class="spin" aria-hidden="true" />
      <template v-else>
        <span>{{ health.action_label }}</span>
        <ArrowRight :size="16" aria-hidden="true" />
      </template>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { AlertTriangle, ArrowRight, CircleAlert, Info, LoaderCircle } from '@lucide/vue'

const props = defineProps({
  health: {
    type: Object,
    default: () => ({}),
  },
  compact: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['action'])

const visible = computed(() => Boolean(props.health?.message && (props.health.requires_attention || props.health.severity === 'info')))
const severityClass = computed(() => `is-${props.health?.severity || 'info'}`)
const statusIcon = computed(() => {
  if (props.health?.severity === 'danger') return CircleAlert
  if (props.health?.severity === 'warning') return AlertTriangle
  return Info
})
</script>

<style scoped>
.billing-status {
  align-items: center;
  background: #201d12;
  border: 1px solid rgb(246 216 96 / 45%);
  border-radius: 8px;
  color: #f6d860;
  display: flex;
  gap: 10px;
  line-height: 1.45;
  padding: 12px 14px;
}

.billing-status.compact {
  align-items: flex-start;
  flex-wrap: wrap;
  margin-top: 10px;
}

.billing-status.is-danger {
  background: #3d1a1a;
  border-color: #c53030;
  color: #fc8181;
}

.billing-status.is-info {
  background: #122033;
  border-color: #34506f;
  color: #a0c0ff;
}

.status-icon { flex: 0 0 auto; margin-top: 1px; }
.message { flex: 1; min-width: 180px; }

.status-action {
  align-items: center;
  background: rgb(246 216 96 / 12%);
  border: 1px solid currentColor;
  border-radius: 8px;
  color: inherit;
  cursor: pointer;
  display: inline-flex;
  font-size: 13px;
  font-weight: 800;
  gap: 6px;
  justify-content: center;
  min-height: 34px;
  padding: 0 10px;
}

.status-action:disabled { cursor: default; opacity: 0.7; }
.spin { animation: spin 0.9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
