import { createApp } from 'vue'
import { clerkPlugin } from '@clerk/vue'

import App from './App.vue'
import { i18n, initializeLocale } from './i18n/index.js'
import { initializeTheme } from './ui/theme.js'
import router from './router/index.js'
import './ui/foundations/tokens.css'
import './ui/foundations/themes.css'

const app = createApp(App)
let browserStorage

try {
  browserStorage = window.localStorage
} catch {
  browserStorage = undefined
}

initializeLocale({
  storage: browserStorage,
  browserLocales: window.navigator?.languages ?? [],
  documentElement: document.documentElement,
})

let prefersDark = false
try {
  prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
} catch {
  prefersDark = false
}

initializeTheme({
  storage: browserStorage,
  prefersDark,
  documentElement: document.documentElement,
})

app.use(clerkPlugin, {
  publishableKey: import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || '',
})

app.use(i18n)
app.use(router).mount('#app')
