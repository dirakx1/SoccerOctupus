<template>
  <div class="auth-page">
    <section class="auth-panel">
      <div class="eyebrow">Create account</div>
      <h1>Sign up</h1>
      <p class="subtitle">Join the workspace to run predictions and receive role-based access.</p>
      <SignUp
        path="/sign-up"
        routing="path"
        sign-in-url="/sign-in"
        :appearance="appearance"
      />
    </section>
  </div>
</template>

<script setup>
import { SignUp } from '@clerk/vue'

const appearance = {
  variables: {
    colorPrimary: '#e2b714',
    colorBackground: '#16213e',
    colorInputBackground: '#0a0a1a',
    colorInputText: '#e0e0e0',
    colorText: '#e0e0e0',
    colorTextSecondary: '#8888aa',
    borderRadius: '10px',
  },
}
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

.eyebrow {
  color: #e2b714;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 10px;
}

h1 {
  color: #e0e0e0;
  font-size: 30px;
  margin-bottom: 8px;
}

.subtitle {
  color: #8888aa;
  font-size: 14px;
  margin-bottom: 24px;
}
</style>
