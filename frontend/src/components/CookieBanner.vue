<template>
  <Transition name="slide-up">
    <div v-if="visible" class="cookie-banner" role="dialog" aria-label="Cookie consent">
      <div class="cookie-content">
        <div class="cookie-text">
          <span class="cookie-icon">🍪</span>
          <p>
            We use essential cookies to keep you signed in and optional analytics cookies
            to improve the experience. See our
            <router-link to="/cookie-policy">Cookie Policy</router-link> for details.
          </p>
        </div>
        <div class="cookie-actions">
          <button class="btn-necessary" @click="acceptNecessary">Necessary only</button>
          <button class="btn-accept" @click="acceptAll">Accept all</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const STORAGE_KEY = 'so_cookie_consent'
const visible = ref(false)

onMounted(() => {
  if (!localStorage.getItem(STORAGE_KEY)) {
    visible.value = true
  }
})

function acceptAll() {
  localStorage.setItem(STORAGE_KEY, 'all')
  visible.value = false
}

function acceptNecessary() {
  localStorage.setItem(STORAGE_KEY, 'necessary')
  visible.value = false
}
</script>

<style scoped>
.cookie-banner {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: #16213e;
  border-top: 2px solid #0f3460;
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.5);
  padding: 16px 32px;
}

.cookie-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}

.cookie-text {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.cookie-icon { font-size: 22px; flex-shrink: 0; }

p {
  color: #c0c0d8;
  font-size: 14px;
  line-height: 1.5;
  margin: 0;
}

p a {
  color: #a0c0ff;
  text-decoration: none;
}
p a:hover { text-decoration: underline; }

.cookie-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.btn-necessary {
  padding: 9px 18px;
  background: transparent;
  border: 1px solid #0f3460;
  border-radius: 8px;
  color: #8888aa;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.btn-necessary:hover { border-color: #a0aec0; color: #e0e0e0; }

.btn-accept {
  padding: 9px 20px;
  background: linear-gradient(135deg, #e2b714, #f6d860);
  border: none;
  border-radius: 8px;
  color: #0a0a1a;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn-accept:hover { opacity: 0.88; }

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.3s ease, opacity 0.3s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
</style>
