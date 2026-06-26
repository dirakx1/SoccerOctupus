import { createApp } from 'vue'
import { clerkPlugin } from '@clerk/vue'

import App from './App.vue'
import router from './router/index.js'

const app = createApp(App)

app.use(clerkPlugin, {
  publishableKey: import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || '',
})

app.use(router).mount('#app')
