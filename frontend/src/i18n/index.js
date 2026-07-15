import { createI18n } from 'vue-i18n'

import enCommon from './locales/en/common.json'
import esCommon from './locales/es/common.json'
import {
  applyLocale as applyLocaleToRuntime,
  DEFAULT_LOCALE,
  readSavedLocale,
  resolveLocale,
} from './locale.js'

export {
  DEFAULT_LOCALE,
  LOCALE_STORAGE_KEY,
  normalizeLocale,
  resolveLocale,
  SUPPORTED_LOCALES,
} from './locale.js'

export const i18n = createI18n({
  legacy: false,
  locale: DEFAULT_LOCALE,
  fallbackLocale: DEFAULT_LOCALE,
  messages: {
    en: { common: enCommon },
    es: { common: esCommon },
  },
})

export function applyLocale(locale, { storage, documentElement } = {}) {
  return applyLocaleToRuntime(locale, { i18n, storage, documentElement })
}

export function initializeLocale({
  explicitLocale,
  storage,
  browserLocales = [],
  documentElement,
} = {}) {
  const locale = resolveLocale({
    explicitLocale,
    savedLocale: readSavedLocale(storage),
    browserLocales,
  })

  return applyLocale(locale, { storage, documentElement })
}
