import { createApp } from 'vue'
import { clerkPlugin } from '@clerk/vue'

import App from './App.vue'
import router from './router/index.js'
import { api } from './lib/api'
import { clearAuthState, setAuthState } from './lib/auth'

router.beforeEach(async (to) => {
  try {
    const res = await api.get('/api/me')
    setAuthState({ signedIn: true, isAdmin: res.data.is_admin, user: res.data })

    if (to.path === '/sign-in' || to.path === '/sign-up') {
      return { path: '/' }
    }

    if (to.meta.admin && !res.data.is_admin) {
      return { path: '/' }
    }

    return true
  } catch {
    clearAuthState()
    if (to.meta.public) return true
    return { path: '/sign-in' }
  }
})

const app = createApp(App)

app.use(clerkPlugin, {
  publishableKey: import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || '',
})

app.use(router).mount('#app')
