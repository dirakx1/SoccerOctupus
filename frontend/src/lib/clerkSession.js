import { api } from './api'
import { setAuthState } from './auth'

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function getSessionToken(clerk, sessionId) {
  for (let attempt = 0; attempt < 10; attempt += 1) {
    const clientSessions = clerk.value?.client?.sessions || []
    const activeSession = clerk.value?.session
    const session = clientSessions.find((entry) => entry.id === sessionId) || activeSession
    const token = await session?.getToken?.()

    if (token) return token
    await delay(100)
  }

  return null
}

export async function activateSessionAndHydrateAuth({ clerk, setActive, sessionId }) {
  await setActive({ session: sessionId })

  const token = await getSessionToken(clerk, sessionId)
  const headers = token ? { Authorization: `Bearer ${token}` } : undefined
  const res = await api.get('/api/me', { headers })

  setAuthState({ signedIn: true, isAdmin: res.data.is_admin, user: res.data })
}
