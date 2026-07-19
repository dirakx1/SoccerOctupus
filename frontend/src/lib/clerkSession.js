import { api } from './api'
import { clearAuthState, setAuthPendingState, setAuthState } from './auth'
import { clearPostAuthCompletion, startPostAuthCompletion } from './postAuthCompletion'

export class ClerkSessionActivationError extends Error {
  constructor(message, { cause, sessionActivated }) {
    super(message, { cause })
    this.name = 'ClerkSessionActivationError'
    this.code = 'CLERK_SESSION_ACTIVATION_FAILED'
    this.sessionActivated = sessionActivated
  }
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function getSessionToken(clerk, sessionId) {
  for (let attempt = 0; attempt < 10; attempt += 1) {
    const clientSessions = clerk.value?.client?.sessions || []
    const activeSession = clerk.value?.session
    const session = clientSessions.find((entry) => entry.id === sessionId) ||
      (activeSession?.id === sessionId ? activeSession : null)
    const token = await session?.getToken?.()

    if (token) return token
    await delay(100)
  }

  return null
}

export async function activateSessionAndHydrateAuth({ clerk, setActive, sessionId }) {
  startPostAuthCompletion()

  try {
    await setActive({ session: sessionId })
  } catch (error) {
    clearAuthState()
    clearPostAuthCompletion()
    throw new ClerkSessionActivationError(error?.message || 'Unable to activate your session', {
      cause: error,
      sessionActivated: false,
    })
  }

  try {
    const token = await getSessionToken(clerk, sessionId)
    if (!token) {
      throw new Error(`Unable to obtain a token for session ${sessionId}`)
    }

    const res = await api.get('/api/me', {
      headers: { Authorization: `Bearer ${token}` },
    })

    setAuthState({ signedIn: true, isAdmin: res.data.is_admin, user: res.data })
    clearPostAuthCompletion()
    return { hydrated: true }
  } catch (error) {
    setAuthPendingState()
    return { hydrated: false, error }
  }
}
