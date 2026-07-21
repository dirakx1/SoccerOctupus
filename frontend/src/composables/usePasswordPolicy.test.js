import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import { usePasswordPolicy } from './usePasswordPolicy'

function specialRule(policy) {
  return policy.rules.value.find((rule) => rule.key === 'require_special_char')
}

function clerkWithPasswordSettings(passwordSettings) {
  return {
    __unstable__environment: {
      userSettings: { passwordSettings },
    },
  }
}

describe('usePasswordPolicy', () => {
  it('accepts a special character from Clerk allowed_special_characters', () => {
    const policy = usePasswordPolicy({
      password: ref('Abcdef1!'),
      clerk: clerkWithPasswordSettings({
        min_length: 8,
        max_length: 72,
        require_special_char: true,
        allowed_special_characters: '!@#',
      }),
    })

    expect(specialRule(policy)).toMatchObject({ status: 'pass' })
  })

  it('rejects a non-alphanumeric character outside Clerk allowed_special_characters', () => {
    const policy = usePasswordPolicy({
      password: ref('Abcdef1$'),
      clerk: clerkWithPasswordSettings({
        min_length: 8,
        max_length: 72,
        require_special_char: true,
        allowed_special_characters: '!@#',
      }),
    })

    expect(specialRule(policy)).toMatchObject({ status: 'fail' })
  })

  it('uses the generic special-character fallback without an allowlist', () => {
    const policy = usePasswordPolicy({
      password: ref('Abcdef1$'),
      clerk: clerkWithPasswordSettings({
        min_length: 8,
        max_length: 72,
        require_special_char: true,
      }),
    })

    expect(specialRule(policy)).toMatchObject({ status: 'pass' })
  })
})
