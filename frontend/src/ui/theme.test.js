import { describe, expect, it } from 'vitest'

import {
  getEffectiveTheme,
  applyTheme,
  initializeTheme,
  normalizeThemePreference,
  resolveThemePreference,
  THEME_STORAGE_KEY,
} from './theme.js'

describe('theme preference normalization', () => {
  it('normalizes supported preferences', () => {
    expect(normalizeThemePreference(' LIGHT ')).toBe('light')
    expect(normalizeThemePreference('dark')).toBe('dark')
    expect(normalizeThemePreference('system')).toBe('system')
  })

  it('rejects unsupported and missing preferences', () => {
    expect(normalizeThemePreference('sepia')).toBeNull()
    expect(normalizeThemePreference()).toBeNull()
  })
})

describe('theme preference resolution', () => {
  it('prefers explicit valid input, then saved preference, then system', () => {
    expect(resolveThemePreference({ explicitPreference: 'dark', savedPreference: 'light' })).toBe('dark')
    expect(resolveThemePreference({ explicitPreference: 'sepia', savedPreference: 'light' })).toBe('light')
    expect(resolveThemePreference({ explicitPreference: 'sepia', savedPreference: 'invalid' })).toBe('system')
  })

  it('resolves system preference from the current prefers-dark signal', () => {
    expect(getEffectiveTheme('system', { prefersDark: true })).toBe('dark')
    expect(getEffectiveTheme('system', { prefersDark: false })).toBe('light')
    expect(getEffectiveTheme('light', { prefersDark: true })).toBe('light')
  })

  it('applies, persists, and returns the effective theme', () => {
    const attributes = new Map()
    const documentElement = {
      setAttribute: (name, value) => attributes.set(name, value),
      style: { colorScheme: '' },
    }
    const stored = new Map()
    const storage = { setItem: (key, value) => stored.set(key, value) }

    expect(applyTheme('dark', { storage, documentElement })).toEqual({
      preference: 'dark',
      effectiveTheme: 'dark',
    })
    expect(attributes.get('data-theme')).toBe('dark')
    expect(documentElement.style.colorScheme).toBe('dark')
    expect(stored.get('socceroctopus.theme')).toBe('dark')
  })

  it('does not fail when storage or DOM style access is unavailable', () => {
    const attributes = new Map()
    const documentElement = {
      setAttribute: (name, value) => attributes.set(name, value),
      get style() { throw new Error('style unavailable') },
    }
    const storage = { setItem: () => { throw new Error('storage unavailable') } }

    expect(applyTheme('system', {
      prefersDark: true,
      storage,
      documentElement,
    })).toEqual({ preference: 'system', effectiveTheme: 'dark' })
    expect(attributes.get('data-theme')).toBe('dark')
    expect(() => applyTheme('light', { storage, documentElement: undefined })).not.toThrow()
  })

  it('initializes from saved preference before the current system signal', () => {
    const attributes = new Map()
    const documentElement = {
      setAttribute: (name, value) => attributes.set(name, value),
      style: { colorScheme: '' },
    }
    const values = new Map([[THEME_STORAGE_KEY, 'dark']])
    const storage = {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, value),
    }

    expect(initializeTheme({
      storage,
      prefersDark: false,
      documentElement,
    })).toEqual({ preference: 'dark', effectiveTheme: 'dark' })
    expect(attributes.get('data-theme')).toBe('dark')
  })
})
