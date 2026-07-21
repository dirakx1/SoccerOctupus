import { describe, expect, it } from 'vitest'

import {
  applyLocale,
  i18n,
  LOCALE_STORAGE_KEY,
  normalizeLocale,
  resolveLocale,
} from './index.js'

describe('normalizeLocale', () => {
  it('normalizes supported regional and case variants to a supported locale', () => {
    expect(normalizeLocale(' ES-mx ')).toBe('es')
    expect(normalizeLocale('en-US')).toBe('en')
  })

  it('rejects missing and unsupported locales', () => {
    expect(normalizeLocale('fr-FR')).toBeNull()
    expect(normalizeLocale()).toBeNull()
  })
})

describe('resolveLocale', () => {
  it('prefers an explicit supported locale', () => {
    expect(resolveLocale({
      explicitLocale: 'es-MX',
      savedLocale: 'en',
      browserLocales: ['en-US'],
    })).toBe('es')
  })

  it('uses the saved preference when the explicit locale is unsupported', () => {
    expect(resolveLocale({
      explicitLocale: 'fr',
      savedLocale: 'es-ES',
      browserLocales: ['en-GB'],
    })).toBe('es')
  })

  it('uses the first supported browser preference after explicit and saved locales', () => {
    expect(resolveLocale({
      explicitLocale: 'fr',
      savedLocale: 'de',
      browserLocales: ['pt-BR', 'es-ES', 'en-US'],
    })).toBe('es')
  })

  it('falls back to English when no candidate is supported', () => {
    expect(resolveLocale({
      explicitLocale: 'fr',
      savedLocale: 'de',
      browserLocales: ['pt-BR'],
    })).toBe('en')
  })
})

describe('applyLocale', () => {
  it('applies, persists, and exposes a supported locale to the document', () => {
    const stored = new Map()
    const storage = { setItem: (key, value) => stored.set(key, value) }
    const documentElement = { lang: 'en' }

    expect(applyLocale('es-MX', { storage, documentElement })).toBe('es')
    expect(i18n.global.locale.value).toBe('es')
    expect(stored.get(LOCALE_STORAGE_KEY)).toBe('es')
    expect(documentElement.lang).toBe('es')
  })
})
