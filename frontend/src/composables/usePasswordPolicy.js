import { computed, ref, unref, watch } from 'vue'

const FALLBACK_SETTINGS = {
  allowed_special_characters: '',
  disable_hibp: true,
  min_length: 8,
  max_length: 72,
  require_special_char: false,
  require_numbers: false,
  require_uppercase: false,
  require_lowercase: false,
  show_zxcvbn: false,
  min_zxcvbn_strength: 0,
}

function valueOf(source) {
  return typeof source === 'function' ? source() : unref(source)
}

function readPasswordSettings(clerk) {
  const instance = valueOf(clerk)
  return instance?.__unstable__environment?.userSettings?.passwordSettings ||
    instance?.environment?.userSettings?.passwordSettings ||
    instance?.client?.environment?.userSettings?.passwordSettings ||
    null
}

function hasLowercase(value) {
  return /[a-z]/.test(value)
}

function hasUppercase(value) {
  return /[A-Z]/.test(value)
}

function hasNumber(value) {
  return /\d/.test(value)
}

function hasSpecial(value, allowedSpecialCharacters) {
  if (typeof allowedSpecialCharacters === 'string' && allowedSpecialCharacters.length > 0) {
    return Array.from(value).some((character) => allowedSpecialCharacters.includes(character))
  }
  return /[^A-Za-z0-9]/.test(value)
}

function strengthScore(strength) {
  if (typeof strength === 'number') return strength
  if (typeof strength?.score === 'number') return strength.score
  if (typeof strength?.result?.score === 'number') return strength.result.score
  if (typeof strength?.zxcvbn?.score === 'number') return strength.zxcvbn.score
  return null
}

function rule(key, label, passes) {
  return {
    key,
    label,
    status: passes ? 'pass' : 'fail',
  }
}

function infoRule(key, label) {
  return {
    key,
    label,
    status: 'info',
  }
}

function strengthLabel(score) {
  if (score === null) return 'Password strength'
  if (score >= 4) return 'Password strength: strong'
  if (score >= 3) return 'Password strength: normal'
  return 'Password strength: weak'
}

export function usePasswordPolicy({ password, validator, clerk } = {}) {
  const validation = ref(null)
  const complexityValid = ref(null)
  const validationError = ref('')

  const rawSettings = computed(() => readPasswordSettings(clerk))
  const source = computed(() => rawSettings.value ? 'clerk' : 'fallback')
  const settings = computed(() => ({
    ...FALLBACK_SETTINGS,
    ...(rawSettings.value || {}),
  }))

  const passwordValue = computed(() => `${valueOf(password) || ''}`)
  const validatorFn = computed(() => valueOf(validator))

  function validateNow() {
    validation.value = null
    complexityValid.value = null
    validationError.value = ''

    if (!passwordValue.value || typeof validatorFn.value !== 'function') {
      return
    }

    try {
      validatorFn.value(passwordValue.value, {
        onValidation: (result) => {
          validation.value = result || null
        },
        onValidationComplexity: (result) => {
          complexityValid.value = result
        },
      })
    } catch (err) {
      validationError.value = err?.message || 'Password validation is unavailable.'
    }
  }

  watch([passwordValue, validatorFn], validateNow, { immediate: true })

  const strength = computed(() => {
    const score = strengthScore(validation.value?.strength)
    return {
      score,
      label: strengthLabel(score),
    }
  })

  const rules = computed(() => {
    const value = passwordValue.value
    const policy = settings.value
    const minLength = Number(policy.min_length || FALLBACK_SETTINGS.min_length)
    const maxLength = Number(policy.max_length || FALLBACK_SETTINGS.max_length)
    const required = [
      rule('min_length', `At least ${minLength} characters`, value.length >= minLength),
      rule('max_length', `No more than ${maxLength} characters`, value.length <= maxLength),
    ]

    if (policy.require_lowercase) {
      required.push(rule('require_lowercase', 'At least 1 lowercase character', hasLowercase(value)))
    }
    if (policy.require_uppercase) {
      required.push(rule('require_uppercase', 'At least 1 uppercase character', hasUppercase(value)))
    }
    if (policy.require_numbers) {
      required.push(rule('require_numbers', 'At least 1 number', hasNumber(value)))
    }
    if (policy.require_special_char) {
      const suffix = policy.allowed_special_characters
        ? ` from ${policy.allowed_special_characters}`
        : ''
      required.push(rule(
        'require_special_char',
        `At least 1 special character${suffix}`,
        hasSpecial(value, policy.allowed_special_characters),
      ))
    }

    if (policy.show_zxcvbn) {
      const score = strength.value.score
      const minScore = Number(policy.min_zxcvbn_strength || 0)
      required.push(rule('min_zxcvbn_strength', 'Minimum password strength', score !== null && score >= minScore))
    }

    if (policy.disable_hibp === false) {
      required.push(infoRule('hibp', 'Known-breach checks run when you submit'))
    }

    if (source.value === 'fallback') {
      required.push(infoRule('fallback', 'Final password checks run when you submit'))
    }

    if (validationError.value) {
      required.push(infoRule('validation_unavailable', validationError.value))
    }

    return required
  })

  const passesRequiredRules = computed(() => {
    if (complexityValid.value === false) return false
    return rules.value.every((entry) => entry.status !== 'fail')
  })

  return {
    settings,
    rules,
    strength,
    source,
    passesRequiredRules,
    validateNow,
  }
}
