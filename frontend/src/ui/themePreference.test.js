import { describe, expect, it } from 'vitest'

import { THEME_STORAGE_KEY } from './theme.js'
import { useThemePreference } from './themePreference.js'

describe('theme preference control', () => {
  it('exposes, applies, and persists preference and effective theme changes', () => {
    const values = new Map([[THEME_STORAGE_KEY, 'system']])
    const storage = {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, value),
    }
    const attributes = new Map([['data-theme', 'dark']])
    const documentElement = {
      dataset: { theme: 'dark' },
      setAttribute: (name, value) => {
        attributes.set(name, value)
        if (name === 'data-theme') documentElement.dataset.theme = value
      },
      style: { colorScheme: 'dark' },
    }

    const theme = useThemePreference({ storage, documentElement, prefersDark: true })

    expect(theme.preference.value).toBe('system')
    expect(theme.effectiveTheme.value).toBe('dark')

    expect(theme.setPreference('light')).toEqual({ preference: 'light', effectiveTheme: 'light' })
    expect(theme.preference.value).toBe('light')
    expect(theme.effectiveTheme.value).toBe('light')
    expect(values.get(THEME_STORAGE_KEY)).toBe('light')
    expect(attributes.get('data-theme')).toBe('light')
    expect(documentElement.style.colorScheme).toBe('light')
  })
})
