const STORAGE_KEY = 'socceroctopus.postAuthRedirect'

function isLocalPath(path) {
  return typeof path === 'string' && path.startsWith('/') && !path.startsWith('//')
}

export function setPostAuthRedirect(path) {
  if (!isLocalPath(path)) return false
  window.localStorage?.setItem(STORAGE_KEY, path)
  return true
}

export function peekPostAuthRedirect() {
  const value = window.localStorage?.getItem(STORAGE_KEY)
  return isLocalPath(value) ? value : null
}

export function consumePostAuthRedirect() {
  const value = peekPostAuthRedirect()
  window.localStorage?.removeItem(STORAGE_KEY)
  return value
}
