<template>
  <svg
    v-if="cells.length"
    class="authenticator-qr"
    data-testid="authenticator-qr"
    :viewBox="`0 0 ${size} ${size}`"
    role="img"
    aria-label="Authenticator app setup QR code"
  >
    <rect width="100%" height="100%" fill="#ffffff" />
    <rect
      v-for="cell in cells"
      :key="`${cell.x}-${cell.y}`"
      :x="cell.x"
      :y="cell.y"
      width="1"
      height="1"
      fill="#0a0a1a"
    />
  </svg>
  <div v-else class="qr-unavailable">
    QR code unavailable for this setup key.
  </div>
</template>

<script setup>
import { computed } from 'vue'

import { createQrMatrix } from '../lib/qrCode'

const props = defineProps({
  value: {
    type: String,
    required: true,
  },
})

const quietZone = 4
const matrix = computed(() => createQrMatrix(props.value) || [])
const size = computed(() => (matrix.value.length ? matrix.value.length + quietZone * 2 : 0))
const cells = computed(() => {
  const result = []
  for (let y = 0; y < matrix.value.length; y += 1) {
    for (let x = 0; x < matrix.value.length; x += 1) {
      if (matrix.value[y][x]) {
        result.push({ x: x + quietZone, y: y + quietZone })
      }
    }
  }
  return result
})
</script>

<style scoped>
.authenticator-qr {
  background: #ffffff;
  border-radius: 8px;
  display: block;
  height: 220px;
  image-rendering: pixelated;
  padding: 12px;
  width: 220px;
}

.qr-unavailable {
  background: rgba(15, 52, 96, 0.45);
  border: 1px solid #1f4c7a;
  border-radius: 8px;
  color: #a0aec0;
  font-size: 13px;
  padding: 14px;
}
</style>
