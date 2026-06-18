import { computed, reactive } from 'vue'

const state = reactive({
  loaded: false,
  signedIn: false,
  isAdmin: false,
  user: null,
})

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
}

export function clearAuthState() {
  state.loaded = true
  state.signedIn = false
  state.isAdmin = false
  state.user = null
}
