import { createApp } from 'vue'
import { clerkPlugin, useAuth } from '@clerk/vue'

import App from './App.vue'
import router from './router/index.js'
import { api, installAuthInterceptor } from './lib/api'
import { clearAuthState, setAuthState } from './lib/auth'

const app = createApp(App)

app.use(clerkPlugin, {
  publishableKey: import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || '',
})

installAuthInterceptor(async () => {
  try {
    const auth = useAuth()
    return await auth.getToken.value?.()
  } catch {
    return null
  }
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true

  try {
    const res = await api.get('/api/me')
    setAuthState({ signedIn: true, isAdmin: res.data.is_admin, user: res.data })
    if (to.meta.admin && !res.data.is_admin) {
      return { path: '/' }
    }
    if ((to.path === '/sign-in' || to.path === '/sign-up') && res.data) {
      return { path: '/' }
    }
    return true
  } catch {
    clearAuthState()
    if (to.meta.public) return true
    return { path: '/sign-in' }
  }
})

app.use(router).mount('#app')
