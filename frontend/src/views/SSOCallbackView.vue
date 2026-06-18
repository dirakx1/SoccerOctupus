<template>
  <div class="auth-page">
    <section class="auth-panel callback-panel">
      <div class="spinner" aria-hidden="true" />
      <h1>Completing sign-in</h1>
      <p class="subtitle">Securely finishing your Google authentication.</p>

      <AuthenticateWithRedirectCallback
        sign-in-force-redirect-url="/"
        sign-up-force-redirect-url="/"
        sign-in-fallback-redirect-url="/"
        sign-up-fallback-redirect-url="/"
        sign-in-url="/sign-in"
        sign-up-url="/sign-up"
      />
      <div id="clerk-captcha" />
    </section>
  </div>
</template>

<script setup>
import { AuthenticateWithRedirectCallback } from '@clerk/vue'
</script>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  padding: 48px 0;
}

.auth-panel {
  width: min(100%, 520px);
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 12px;
  padding: 32px;
}

.callback-panel {
  align-items: center;
  display: flex;
  flex-direction: column;
  text-align: center;
}

.spinner {
  animation: spin 0.8s linear infinite;
  border: 3px solid #0f3460;
  border-top-color: #e2b714;
  border-radius: 999px;
  height: 36px;
  margin-bottom: 18px;
  width: 36px;
}

h1 {
  color: #e0e0e0;
  font-size: 28px;
  margin-bottom: 8px;
}

.subtitle {
  color: #8888aa;
  font-size: 14px;
  margin-bottom: 8px;
}

#clerk-captcha {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
