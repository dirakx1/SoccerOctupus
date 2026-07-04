<template>
  <div
    v-if="svg"
    class="authenticator-qr"
    data-testid="authenticator-qr"
    role="img"
    aria-label="Authenticator app setup QR code"
    v-html="svg"
  />
  <div v-else class="qr-unavailable">
    QR code unavailable for this setup key.
  </div>
</template>

<script setup>
import QRCode from 'qrcode'
import { ref, watch } from 'vue'

const props = defineProps({
  value: {
    type: String,
    required: true,
  },
})

const svg = ref('')

watch(
  () => props.value,
  async (value) => {
    if (!value) {
      svg.value = ''
      return
    }

    try {
      svg.value = await QRCode.toString(value, {
        type: 'svg',
        errorCorrectionLevel: 'M',
        margin: 4,
        color: {
          dark: '#0a0a1aff',
          light: '#ffffffff',
        },
      })
    } catch {
      svg.value = ''
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.authenticator-qr {
  background: #ffffff;
  border-radius: 8px;
  display: block;
  height: 220px;
  image-rendering: pixelated;
  overflow: hidden;
  padding: 12px;
  width: 220px;
}

.authenticator-qr :deep(svg) {
  display: block;
  height: 100%;
  width: 100%;
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
