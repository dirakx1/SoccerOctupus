import { createI18n } from 'vue-i18n'

import enCommon from './locales/en/common.json'
import enAdminSettings from './locales/en/adminSettings.json'
import enAbout from './locales/en/about.json'
import enBillingSuccess from './locales/en/billingSuccess.json'
import enCompetitions from './locales/en/competitions.json'
import enContact from './locales/en/contact.json'
import enCookiePolicy from './locales/en/cookiePolicy.json'
import enGroups from './locales/en/groups.json'
import enHome from './locales/en/home.json'
import enLegal from './locales/en/legal.json'
import enMarkets from './locales/en/markets.json'
import enSignIn from './locales/en/signIn.json'
import enSignUp from './locales/en/signUp.json'
import enNavigation from './locales/en/navigation.json'
import enOauthCallback from './locales/en/oauthCallback.json'
import enOverlays from './locales/en/overlays.json'
import enPasswordRecovery from './locales/en/passwordRecovery.json'
import enPricing from './locales/en/pricing.json'
import enProfile from './locales/en/profile.json'
import enPredictions from './locales/en/predictions.json'
import enTournament from './locales/en/tournament.json'
import enUsernameContinuation from './locales/en/usernameContinuation.json'
import esCommon from './locales/es/common.json'
import esAdminSettings from './locales/es/adminSettings.json'
import esAbout from './locales/es/about.json'
import esBillingSuccess from './locales/es/billingSuccess.json'
import esCompetitions from './locales/es/competitions.json'
import esContact from './locales/es/contact.json'
import esCookiePolicy from './locales/es/cookiePolicy.json'
import esGroups from './locales/es/groups.json'
import esHome from './locales/es/home.json'
import esLegal from './locales/es/legal.json'
import esMarkets from './locales/es/markets.json'
import esSignIn from './locales/es/signIn.json'
import esSignUp from './locales/es/signUp.json'
import esNavigation from './locales/es/navigation.json'
import esOauthCallback from './locales/es/oauthCallback.json'
import esOverlays from './locales/es/overlays.json'
import esPasswordRecovery from './locales/es/passwordRecovery.json'
import esPricing from './locales/es/pricing.json'
import esProfile from './locales/es/profile.json'
import esPredictions from './locales/es/predictions.json'
import esTournament from './locales/es/tournament.json'
import esUsernameContinuation from './locales/es/usernameContinuation.json'
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
    en: { about: enAbout, adminSettings: enAdminSettings, billingSuccess: enBillingSuccess, common: enCommon, competitions: enCompetitions, contact: enContact, cookiePolicy: enCookiePolicy, groups: enGroups, home: enHome, legal: enLegal, markets: enMarkets, navigation: enNavigation, oauthCallback: enOauthCallback, overlays: enOverlays, passwordRecovery: enPasswordRecovery, predictions: enPredictions, pricing: enPricing, profile: enProfile, signIn: enSignIn, signUp: enSignUp, tournament: enTournament, usernameContinuation: enUsernameContinuation },
    es: { about: esAbout, adminSettings: esAdminSettings, billingSuccess: esBillingSuccess, common: esCommon, competitions: esCompetitions, contact: esContact, cookiePolicy: esCookiePolicy, groups: esGroups, home: esHome, legal: esLegal, markets: esMarkets, navigation: esNavigation, oauthCallback: esOauthCallback, overlays: esOverlays, passwordRecovery: esPasswordRecovery, predictions: esPredictions, pricing: esPricing, profile: esProfile, signIn: esSignIn, signUp: esSignUp, tournament: esTournament, usernameContinuation: esUsernameContinuation },
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
