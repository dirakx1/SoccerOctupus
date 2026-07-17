import { createI18n } from 'vue-i18n'

import enCommon from './locales/en/common.json'
import enCompetitions from './locales/en/competitions.json'
import enGroups from './locales/en/groups.json'
import enHome from './locales/en/home.json'
import enMarkets from './locales/en/markets.json'
import enSignIn from './locales/en/signIn.json'
import enNavigation from './locales/en/navigation.json'
import enOverlays from './locales/en/overlays.json'
import enPredictions from './locales/en/predictions.json'
import enTournament from './locales/en/tournament.json'
import esCommon from './locales/es/common.json'
import esCompetitions from './locales/es/competitions.json'
import esGroups from './locales/es/groups.json'
import esHome from './locales/es/home.json'
import esMarkets from './locales/es/markets.json'
import esSignIn from './locales/es/signIn.json'
import esNavigation from './locales/es/navigation.json'
import esOverlays from './locales/es/overlays.json'
import esPredictions from './locales/es/predictions.json'
import esTournament from './locales/es/tournament.json'
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
    en: { common: enCommon, competitions: enCompetitions, groups: enGroups, home: enHome, markets: enMarkets, navigation: enNavigation, overlays: enOverlays, predictions: enPredictions, signIn: enSignIn, tournament: enTournament },
    es: { common: esCommon, competitions: esCompetitions, groups: esGroups, home: esHome, markets: esMarkets, navigation: esNavigation, overlays: esOverlays, predictions: esPredictions, signIn: esSignIn, tournament: esTournament },
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
