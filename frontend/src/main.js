import { createApp } from 'vue'
import { clerkPlugin } from '@clerk/vue'

import App from './App.vue'
import { i18n, initializeLocale } from './i18n/index.js'
import router from './router/index.js'

const app = createApp(App)
let localeStorage

try {
  localeStorage = window.localStorage
} catch {
  localeStorage = undefined
}

initializeLocale({
  storage: localeStorage,
  browserLocales: window.navigator?.languages ?? [],
  documentElement: document.documentElement,
})

app.use(clerkPlugin, {
  publishableKey: import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || '',
})

app.use(i18n)
app.use(router).mount('#app')
