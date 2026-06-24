<template>
  <div class="shell">
    <nav class="navbar">
      <router-link to="/" class="brand">
        <span class="logo">🐙</span>
        <span class="title">SoccerOctopus</span>
        <span class="subtitle">WC 2026 Swarm Prediction Engine</span>
      </router-link>
      <div class="nav-links">
        <template v-if="auth.state.signedIn">
          <router-link to="/">Home</router-link>
          <router-link to="/groups">Groups</router-link>
          <router-link to="/predict">Predict Match</router-link>
          <router-link to="/tournament">Tournament</router-link>
          <router-link to="/markets">Markets</router-link>
          <router-link to="/pricing">Pricing</router-link>
          <router-link v-if="auth.state.isAdmin" to="/admin/settings">Admin</router-link>
          <div class="user-menu">
            <button
              class="user-button"
              type="button"
              :aria-expanded="userMenuOpen"
              aria-haspopup="menu"
              @click="toggleUserMenu"
            >
              <img v-if="userAvatarUrl" :src="userAvatarUrl" alt="" />
              <span v-else>{{ userInitials }}</span>
            </button>
            <div v-if="userMenuOpen" class="user-dropdown" role="menu">
              <div class="user-summary">
                <strong>{{ userDisplayName }}</strong>
                <small>{{ userEmail }}</small>
              </div>
              <router-link to="/profile" role="menuitem" @click="closeUserMenu">Profile</router-link>
              <button type="button" role="menuitem" @click="signOut">Sign Out</button>
            </div>
          </div>
        </template>
        <template v-else>
          <router-link to="/">Home</router-link>
          <router-link to="/pricing">Pricing</router-link>
          <router-link to="/sign-in">Sign In</router-link>
          <router-link to="/sign-up">Sign Up</router-link>
        </template>
      </div>
    </nav>
    <main class="content">
      <router-view />
    </main>
    <footer class="footer">
      <span>© 2026 SoccerOctopus — predictions are approximations only, not betting advice.</span>
      <router-link to="/legal">Legal Notice</router-link>
    </footer>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuth, useClerk } from '@clerk/vue'
import { useRouter } from 'vue-router'

import { useCurrentUserProfile } from './composables/useCurrentUserProfile'
import { installAuthInterceptor } from './lib/api'
import { clearAuthState, useAuthState } from './lib/auth'

const auth = useAuthState()
const clerk = useClerk()
const clerkAuth = useAuth()
const router = useRouter()
const userMenuOpen = ref(false)
const {
  avatarUrl: userAvatarUrl,
  displayName: userDisplayName,
  email: userEmail,
  initials: userInitials,
} = useCurrentUserProfile()

installAuthInterceptor(async () => {
  return await clerkAuth.getToken.value?.()
})

async function signOut() {
  closeUserMenu()
  await clerk.value?.signOut()
  clearAuthState()
  router.push('/sign-in')
}

function toggleUserMenu() {
  userMenuOpen.value = !userMenuOpen.value
}

function closeUserMenu() {
  userMenuOpen.value = false
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

.brand { display: flex; align-items: center; gap: 10px; text-decoration: none; cursor: pointer; }
.logo { font-size: 28px; }
.title { font-size: 22px; font-weight: 700; color: #e2b714; letter-spacing: 1px; }
.subtitle { font-size: 12px; color: #8888aa; margin-left: 4px; }

.nav-links { display: flex; align-items: center; gap: 24px; }
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

.user-menu { position: relative; }

.user-button {
  align-items: center;
  background: #0a0a1a;
  border: 1px solid #34506f;
  border-radius: 999px;
  color: #e2b714;
  cursor: pointer;
  display: flex;
  font-size: 13px;
  font-weight: 800;
  height: 36px;
  justify-content: center;
  overflow: hidden;
  width: 36px;
}

.user-button:hover { border-color: #e2b714; }
.user-button img { height: 100%; object-fit: cover; width: 100%; }

.user-dropdown {
  background: #16213e;
  border: 1px solid #0f3460;
  border-radius: 12px;
  box-shadow: 0 18px 40px rgb(0 0 0 / 35%);
  display: flex;
  flex-direction: column;
  min-width: 220px;
  padding: 10px;
  position: absolute;
  right: 0;
  top: calc(100% + 10px);
  z-index: 20;
}

.user-summary {
  border-bottom: 1px solid #0f3460;
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 6px;
  padding: 8px 10px 12px;
}

.user-summary strong { color: #e0e0e0; font-size: 14px; }
.user-summary small { color: #8888aa; font-size: 12px; overflow-wrap: anywhere; }

.user-dropdown a,
.user-dropdown button {
  background: transparent;
  border: none;
  border-radius: 8px;
  color: #a0aec0;
  cursor: pointer;
  font-size: 14px;
  padding: 10px;
  text-align: left;
  text-decoration: none;
}

.user-dropdown a:hover,
.user-dropdown button:hover {
  background: #0f3460;
  color: #e2b714;
}

.content { flex: 1; padding: 32px; max-width: 1200px; margin: 0 auto; width: 100%; }

.footer {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  padding: 16px 32px;
  border-top: 1px solid #0f3460;
  background: #16213e;
  font-size: 12px;
  color: #8888aa;
}
.footer a { color: #a0c0ff; text-decoration: none; }
.footer a:hover { text-decoration: underline; }
</style>
