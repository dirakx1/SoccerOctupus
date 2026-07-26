<template>
  <main class="league-capability">
    <h1>{{ t(`league.capabilities.${capability}`) }}</h1>
    <p>{{ t('league.states.empty') }}</p>
  </main>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

defineProps({ capability: { type: String, required: true } })
const { t } = useI18n()
</script>

<style scoped>
.league-capability { padding: var(--space-8) 0; }
.league-capability h1 { font-family: var(--font-family-display); }
.league-capability p { color: var(--color-text-muted); }
</style>
