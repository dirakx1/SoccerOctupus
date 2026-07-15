import { describe, expect, it } from 'vitest'

import {
  applyLocale,
  i18n,
  initializeLocale,
  LOCALE_STORAGE_KEY,
} from './index.js'

describe('localization core', () => {
  it('uses Composition API mode with English fallback and namespaced resources', () => {
    expect(i18n.global.locale.value).toBe('en')

    applyLocale('es')

    expect(i18n.mode).toBe('composition')
    expect(i18n.global.fallbackLocale.value).toBe('en')
    expect(i18n.global.t('common.localeName')).toBe('Español')
  })

  it('initializes from a saved preference before browser preferences', () => {
    const values = new Map([[LOCALE_STORAGE_KEY, 'es-ES']])
    const storage = {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, value),
    }
    const documentElement = { lang: 'en' }

    expect(initializeLocale({
      storage,
      browserLocales: ['en-US'],
      documentElement,
    })).toBe('es')
    expect(i18n.global.locale.value).toBe('es')
    expect(documentElement.lang).toBe('es')
  })

  it('initializes safely when browser storage is unavailable', () => {
    const storage = {
      getItem: () => { throw new Error('storage unavailable') },
      setItem: () => { throw new Error('storage unavailable') },
    }
    const documentElement = { lang: 'en' }

    expect(initializeLocale({
      storage,
      browserLocales: ['es-AR'],
      documentElement,
    })).toBe('es')
    expect(i18n.global.locale.value).toBe('es')
    expect(documentElement.lang).toBe('es')
  })
})
