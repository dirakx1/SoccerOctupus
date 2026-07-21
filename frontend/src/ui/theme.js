export const SUPPORTED_THEME_PREFERENCES = Object.freeze(['light', 'dark', 'system'])
export const DEFAULT_THEME_PREFERENCE = 'system'
export const THEME_STORAGE_KEY = 'socceroctopus.theme'

export function normalizeThemePreference(value) {
  if (typeof value !== 'string') return null

  const preference = value.trim().toLowerCase()
  return SUPPORTED_THEME_PREFERENCES.includes(preference) ? preference : null
}

export function resolveThemePreference({ explicitPreference, savedPreference } = {}) {
  return normalizeThemePreference(explicitPreference)
    || normalizeThemePreference(savedPreference)
    || DEFAULT_THEME_PREFERENCE
}

export function getEffectiveTheme(preference, { prefersDark = false } = {}) {
  const normalized = normalizeThemePreference(preference) || DEFAULT_THEME_PREFERENCE
  if (normalized === 'system') return prefersDark ? 'dark' : 'light'
  return normalized
}

export function applyTheme(preference, {
  prefersDark = false,
  storage,
  documentElement,
} = {}) {
  const normalizedPreference = normalizeThemePreference(preference) || DEFAULT_THEME_PREFERENCE
  const effectiveTheme = getEffectiveTheme(normalizedPreference, { prefersDark })

  try {
    documentElement?.setAttribute('data-theme', effectiveTheme)
  } catch {
    // Theme state still returns safely when the document is unavailable.
  }
  try {
    const style = documentElement?.style
    if (style) style.colorScheme = effectiveTheme
  } catch {
    // Theme state still returns safely when inline styles are unavailable.
  }
  try {
    storage?.setItem(THEME_STORAGE_KEY, normalizedPreference)
  } catch {
    // Theme state still returns safely when storage is blocked.
  }

  return { preference: normalizedPreference, effectiveTheme }
}

function readSavedThemePreference(storage) {
  try {
    return storage?.getItem(THEME_STORAGE_KEY) ?? null
  } catch {
    return null
  }
}

export function initializeTheme({
  explicitPreference,
  storage,
  prefersDark = false,
  documentElement,
} = {}) {
  const preference = resolveThemePreference({
    explicitPreference,
    savedPreference: readSavedThemePreference(storage),
  })

  return applyTheme(preference, { prefersDark, storage, documentElement })
}
