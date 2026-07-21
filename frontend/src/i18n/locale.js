export const SUPPORTED_LOCALES = Object.freeze(['en', 'es'])
export const DEFAULT_LOCALE = 'en'
export const LOCALE_STORAGE_KEY = 'socceroctopus.locale'

export function normalizeLocale(value) {
  if (typeof value !== 'string') return null

  const language = value.trim().toLowerCase().split(/[-_]/, 1)[0]
  return SUPPORTED_LOCALES.includes(language) ? language : null
}

export function resolveLocale({ explicitLocale, savedLocale, browserLocales = [] } = {}) {
  return normalizeLocale(explicitLocale)
    || normalizeLocale(savedLocale)
    || browserLocales.map(normalizeLocale).find(Boolean)
    || DEFAULT_LOCALE
}

export function applyLocale(locale, { i18n, storage, documentElement }) {
  const resolvedLocale = normalizeLocale(locale) || DEFAULT_LOCALE

  i18n.global.locale.value = resolvedLocale
  if (documentElement) documentElement.lang = resolvedLocale
  try {
    storage?.setItem(LOCALE_STORAGE_KEY, resolvedLocale)
  } catch {
    // Localization must remain usable when browser storage is blocked.
  }

  return resolvedLocale
}

export function readSavedLocale(storage) {
  try {
    return storage?.getItem(LOCALE_STORAGE_KEY) ?? null
  } catch {
    return null
  }
}
