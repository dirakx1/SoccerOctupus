import { computed, reactive } from 'vue'

import { api } from './api'

const AUTH_REFRESH_TTL_MS = 60_000

const state = reactive({
  loaded: false,
  signedIn: false,
  isAdmin: false,
  user: null,
  refreshedAt: 0,
})

let refreshPromise = null

export function useAuthState() {
  return {
    state,
    isLoaded: computed(() => state.loaded),
    isSignedIn: computed(() => state.signedIn),
    isAdmin: computed(() => state.isAdmin),
  }
}

export function setAuthState(payload) {
  state.loaded = true
  state.signedIn = Boolean(payload?.signedIn)
  state.isAdmin = Boolean(payload?.isAdmin)
  state.user = payload?.user || null
  state.refreshedAt = Date.now()
}

export function clearAuthState() {
  state.loaded = true
  state.signedIn = false
  state.isAdmin = false
  state.user = null
  state.refreshedAt = Date.now()
}

export function setAuthPendingState() {
  state.loaded = false
  state.signedIn = false
  state.isAdmin = false
  state.user = null
  state.refreshedAt = 0
}

export function authStateIsFresh(now = Date.now()) {
  return state.loaded && state.signedIn && now - state.refreshedAt < AUTH_REFRESH_TTL_MS
}

export async function refreshAuthState({ force = false } = {}) {
  if (!force && authStateIsFresh()) {
    return state.user
  }

  if (refreshPromise) {
    return refreshPromise
  }

  refreshPromise = api.get('/api/me')
    .then((res) => {
      setAuthState({ signedIn: true, isAdmin: res.data.is_admin, user: res.data })
      return state.user
    })
    .catch((err) => {
      clearAuthState()
      throw err
    })
    .finally(() => {
      refreshPromise = null
    })

  return refreshPromise
}
