<template>
  <div class="shell">
    <nav class="navbar">
      <div class="brand">
        <span class="logo">🐙</span>
        <span class="title">FifaOctopus</span>
        <span class="subtitle">WC 2026 Swarm Prediction Engine</span>
      </div>
      <div class="nav-links">
        <template v-if="auth.state.signedIn">
          <router-link to="/">Home</router-link>
          <router-link to="/groups">Groups</router-link>
          <router-link to="/predict">Predict Match</router-link>
          <router-link to="/tournament">Tournament</router-link>
          <router-link v-if="auth.state.isAdmin" to="/admin/settings">Admin</router-link>
          <button class="nav-btn" @click="signOut">Sign Out</button>
        </template>
        <template v-else>
          <router-link to="/sign-in">Sign In</router-link>
          <router-link to="/sign-up">Sign Up</router-link>
        </template>
      </div>
    </nav>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useClerk } from '@clerk/vue'
import { useRouter } from 'vue-router'

import { clearAuthState, useAuthState } from './lib/auth'

const auth = useAuthState()
const clerk = useClerk()
const router = useRouter()

async function signOut() {
  await clerk.signOut()
  clearAuthState()
  router.push('/sign-in')
}
</script>

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

.brand { display: flex; align-items: center; gap: 10px; }
.logo { font-size: 28px; }
.title { font-size: 22px; font-weight: 700; color: #e2b714; letter-spacing: 1px; }
.subtitle { font-size: 12px; color: #8888aa; margin-left: 4px; }

.nav-links { display: flex; gap: 24px; }
.nav-links a,
.nav-btn {
  color: #a0aec0;
  background: transparent;
  border: none;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: color 0.2s;
  cursor: pointer;
}
.nav-links a:hover, .nav-links a.router-link-active, .nav-btn:hover { color: #e2b714; }

.content { flex: 1; padding: 32px; max-width: 1200px; margin: 0 auto; width: 100%; }
</style>
