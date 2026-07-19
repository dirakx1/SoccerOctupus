<template>
  <router-link class="billing-plans-link" to="/pricing">
    <span>{{ t('predictions.billing.pricing') }}</span>
    <BadgeDollarSign :size="18" aria-hidden="true" />
  </router-link>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { BadgeDollarSign } from '@lucide/vue'

const { t } = useI18n()
</script>

<style scoped>
.billing-plans-link {
  align-items: center;
  border: var(--border-width-thin) solid var(--color-warning);
  border-radius: var(--radius-md);
  color: var(--color-warning);
  display: inline-flex;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  gap: var(--space-2);
  justify-content: center;
  min-height: var(--control-height-lg);
  padding: 0 var(--space-3);
  text-decoration: none;
  vertical-align: middle;
}
.billing-plans-link:hover { background: var(--color-warning-surface); }
.billing-plans-link:focus-visible { outline: var(--border-width-strong) solid var(--color-focus); outline-offset: 3px; }
</style>
