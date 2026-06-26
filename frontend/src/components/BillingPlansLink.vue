<template>
  <router-link class="billing-plans-link" to="/pricing">
    <span>Pricing</span>
    <BadgeDollarSign :size="18" aria-hidden="true" />
  </router-link>
</template>

<script setup>
import { BadgeDollarSign } from '@lucide/vue'
</script>

<style scoped>
.billing-plans-link {
  align-items: center;
  border: 1px solid rgb(246 216 96 / 45%);
  border-radius: 8px;
  color: #f6d860;
  display: inline-flex;
  font-weight: 800;
  gap: 7px;
  min-height: 34px;
  justify-content: center;
  margin-left: 10px;
  padding: 0 10px;
  text-decoration: none;
  vertical-align: middle;
}

.billing-plans-link:hover {
  background: rgb(246 216 96 / 12%);
  border-color: #f6d860;
}
</style>
