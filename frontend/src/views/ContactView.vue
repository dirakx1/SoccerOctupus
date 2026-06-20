<template>
  <div class="legal">
    <h1>Contact</h1>

    <section>
      <h2>Support</h2>
      <p>
        Contact support:
        <a href="mailto:support@socceroctupus.co">support@socceroctupus.co</a>
      </p>
    </section>

    <div class="back">
      <router-link to="/">← Back to Home</router-link>
    </div>
  </div>
</template>

<style scoped>
.legal {
  max-width: 760px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

h1 { color: #e2b714; font-size: 28px; }

section {
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 10px;
  padding: 22px 26px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

h2 { color: #a0c0ff; font-size: 16px; font-weight: 700; }

p { color: #c0c0d8; font-size: 14px; line-height: 1.7; margin: 0; }

a { color: #a0c0ff; text-decoration: none; }
a:hover { text-decoration: underline; }

.back { font-size: 14px; }
.back a { color: #e2b714; }
</style>
