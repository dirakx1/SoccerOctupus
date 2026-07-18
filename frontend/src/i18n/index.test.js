import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

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

  it('provides localized shell navigation and Competition Edition labels', () => {
    applyLocale('en')
    expect(i18n.global.t('navigation.workspace.overview')).toBe('Overview')
    expect(i18n.global.t('competitions.editions.worldCup2026.name')).toBe('FIFA World Cup 2026')

    applyLocale('es')
    expect(i18n.global.t('navigation.workspace.overview')).toBe('Resumen')
    expect(i18n.global.t('competitions.editions.worldCup2026.name')).toBe('Copa Mundial de la FIFA 2026')
  })

  it('keeps cookie policy messages namespaced without importing blocker-prone asset paths', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/i18n/index.js'), 'utf8')

    expect(source).not.toContain('/cookiePolicy.json')
    expect(source).toContain('/privacyPreferences.json')
    expect(i18n.global.getLocaleMessage('en').cookiePolicy.title).toBe('Cookie policy')
    expect(i18n.global.getLocaleMessage('es').cookiePolicy.title).toBe('Política de cookies')
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
