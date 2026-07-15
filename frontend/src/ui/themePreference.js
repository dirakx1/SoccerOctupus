import { ref } from 'vue'

import {
  applyTheme,
  DEFAULT_THEME_PREFERENCE,
  getEffectiveTheme,
  normalizeThemePreference,
  THEME_STORAGE_KEY,
} from './theme.js'

function readPreference(storage) {
  try {
    return normalizeThemePreference(storage?.getItem(THEME_STORAGE_KEY)) || DEFAULT_THEME_PREFERENCE
  } catch {
    return DEFAULT_THEME_PREFERENCE
  }
}

function readEffectiveTheme(documentElement, preference, prefersDark) {
  try {
    return normalizeThemePreference(documentElement?.dataset?.theme)
      || getEffectiveTheme(preference, { prefersDark })
  } catch {
    return getEffectiveTheme(preference, { prefersDark })
  }
}

export function useThemePreference({
  storage,
  documentElement,
  prefersDark = false,
} = {}) {
  const preference = ref(readPreference(storage))
  const effectiveTheme = ref(readEffectiveTheme(documentElement, preference.value, prefersDark))

  function setPreference(value) {
    const next = applyTheme(value, { prefersDark, storage, documentElement })
    preference.value = next.preference
    effectiveTheme.value = next.effectiveTheme
    return next
  }

  return { effectiveTheme, preference, setPreference }
}
