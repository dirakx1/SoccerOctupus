<template>
  <div class="freshness-slot">
    <div
      v-if="freshness && freshness.status !== 'fresh'"
      :class="['freshness', `freshness-${freshness.status}`]"
      :data-testid="`freshness-${freshness.status}`"
      role="status"
      :aria-live="freshness.status === 'refreshing' ? 'polite' : 'assertive'"
    >
      <RefreshCw v-if="freshness.status === 'refreshing'" :size="18" aria-hidden="true" />
      <TriangleAlert v-else :size="18" aria-hidden="true" />
      <span>{{ t(`league.freshness.${freshness.status}`, { source: freshness.source }) }}</span>
      <button v-if="freshness.retryable" type="button" @click="$emit('retry')">
        {{ t('league.freshness.retry') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { RefreshCw, TriangleAlert } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

defineProps({ freshness: { type: Object, default: null } })
defineEmits(['retry'])
const { t } = useI18n()
</script>

<style scoped>
.freshness-slot { min-height: var(--control-height-lg); }
.freshness { align-items: center; background: var(--color-warning-surface); border-left: var(--border-width-strong) solid var(--color-warning); display: flex; gap: var(--space-2); min-height: var(--control-height-lg); padding: var(--space-3); }
.freshness-refreshing { background: var(--color-surface-inset); border-color: var(--color-accent); }
.freshness-hard_stale { border-color: var(--color-danger); }
.freshness button { background: transparent; border: var(--border-width-thin) solid currentColor; color: inherit; margin-left: auto; min-height: var(--control-height-md); padding: 0 var(--space-3); }
</style>
