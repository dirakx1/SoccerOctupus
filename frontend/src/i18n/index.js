import { createI18n } from 'vue-i18n'

import enCommon from './locales/en/common.json'
import enCompetitions from './locales/en/competitions.json'
import enGroups from './locales/en/groups.json'
import enHome from './locales/en/home.json'
import enNavigation from './locales/en/navigation.json'
import esCommon from './locales/es/common.json'
import esCompetitions from './locales/es/competitions.json'
import esGroups from './locales/es/groups.json'
import esHome from './locales/es/home.json'
import esNavigation from './locales/es/navigation.json'
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
    en: { common: enCommon, competitions: enCompetitions, groups: enGroups, home: enHome, navigation: enNavigation },
    es: { common: esCommon, competitions: esCompetitions, groups: esGroups, home: esHome, navigation: esNavigation },
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
