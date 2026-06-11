<template>
  <div class="shell">
    <nav class="navbar">
      <router-link to="/" class="brand">
        <span class="logo">🐙</span>
        <span class="title">SoccerOctopus</span>
        <span class="subtitle">WC 2026 Swarm Prediction Engine</span>
      </router-link>
      <div class="nav-links">
        <router-link to="/">Home</router-link>
        <router-link to="/groups">Groups</router-link>
        <router-link to="/predict">Predict Match</router-link>
        <router-link to="/tournament">Tournament</router-link>
        <router-link to="/markets">📈 Markets</router-link>
      </div>
    </nav>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.shell { min-height: 100vh; display: flex; flex-direction: column; }

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 32px;
  background: linear-gradient(90deg, #1a1a2e 0%, #16213e 100%);
  border-bottom: 2px solid #0f3460;
}

.brand { display: flex; align-items: center; gap: 10px; text-decoration: none; cursor: pointer; }
.logo { font-size: 28px; }
.title { font-size: 22px; font-weight: 700; color: #e2b714; letter-spacing: 1px; }
.subtitle { font-size: 12px; color: #8888aa; margin-left: 4px; }

.nav-links { display: flex; gap: 24px; }
.nav-links a {
  color: #a0aec0;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: color 0.2s;
}
.nav-links a:hover, .nav-links a.router-link-active { color: #e2b714; }

.content { flex: 1; padding: 32px; max-width: 1200px; margin: 0 auto; width: 100%; }
</style>
