const STORAGE_KEY = 'socceroctopus.postAuthCompletion'
const MAX_AGE_MS = 10 * 60 * 1000

function getStorage() {
  try {
    return window.localStorage
  } catch {
    return undefined
  }
}

export function startPostAuthCompletion(now = Date.now()) {
  try {
    getStorage()?.setItem(STORAGE_KEY, String(now))
    return true
  } catch {
    return false
  }
}

export function hasPostAuthCompletion(now = Date.now()) {
  try {
    const rawValue = getStorage()?.getItem(STORAGE_KEY)
    if (rawValue === null || rawValue === undefined) return false
    const startedAt = Number(rawValue)
    if (!Number.isFinite(startedAt) || now - startedAt < 0 || now - startedAt > MAX_AGE_MS) {
      clearPostAuthCompletion()
      return false
    }
    return true
  } catch {
    return false
  }
}

export function clearPostAuthCompletion() {
  try {
    getStorage()?.removeItem(STORAGE_KEY)
  } catch {
    // Session activation can still continue when browser storage is unavailable.
  }
}
