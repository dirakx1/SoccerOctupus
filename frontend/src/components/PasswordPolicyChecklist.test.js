import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import PasswordPolicyChecklist from './PasswordPolicyChecklist.vue'

function dynamicClerk(settings) {
  return {
    __unstable__environment: {
      userSettings: {
        passwordSettings: settings,
      },
    },
  }
}

describe('PasswordPolicyChecklist', () => {
  it('renders fallback rules when Clerk settings are unavailable', () => {
    const wrapper = mount(PasswordPolicyChecklist, {
      props: { password: 'short' },
    })

    expect(wrapper.text()).toContain('Fallback policy')
    expect(wrapper.text()).toContain('At least 8 characters')
    expect(wrapper.text()).toContain('No more than 72 characters')
    expect(wrapper.text()).toContain('Clerk will perform final password checks when you submit')
  })

  it('renders dynamic Clerk min, max, and character-class rules', () => {
    const wrapper = mount(PasswordPolicyChecklist, {
      props: {
        password: 'Abcdef1!',
        clerk: dynamicClerk({
          min_length: 8,
          max_length: 12,
          require_lowercase: true,
          require_uppercase: true,
          require_numbers: true,
          require_special_char: true,
          allowed_special_characters: '!@#',
          disable_hibp: true,
          show_zxcvbn: false,
          min_zxcvbn_strength: 0,
        }),
      },
    })

    expect(wrapper.text()).toContain('Synced from Clerk')
    expect(wrapper.text()).toContain('At least 1 lowercase character')
    expect(wrapper.text()).toContain('At least 1 uppercase character')
    expect(wrapper.text()).toContain('At least 1 number')
    expect(wrapper.text()).toContain('At least 1 special character from !@#')
  })

  it('uses Clerk password strength validation callbacks', async () => {
    const validator = (password, callbacks) => {
      callbacks.onValidation({ strength: { score: password.length > 10 ? 4 : 1 } })
      callbacks.onValidationComplexity(true)
    }

    const wrapper = mount(PasswordPolicyChecklist, {
      props: {
        password: 'long-strong-password',
        validator,
        clerk: dynamicClerk({
          min_length: 8,
          max_length: 72,
          require_lowercase: false,
          require_uppercase: false,
          require_numbers: false,
          require_special_char: false,
          disable_hibp: true,
          show_zxcvbn: true,
          min_zxcvbn_strength: 3,
        }),
      },
    })

    await nextTick()

    expect(wrapper.text()).toContain('Password strength: strong; required score 3')
  })

  it('shows compromised-password checks as Clerk/server-checked info', () => {
    const wrapper = mount(PasswordPolicyChecklist, {
      props: {
        password: 'Abcdef1!',
        clerk: dynamicClerk({
          min_length: 8,
          max_length: 72,
          require_lowercase: false,
          require_uppercase: false,
          require_numbers: false,
          require_special_char: false,
          disable_hibp: false,
          show_zxcvbn: false,
          min_zxcvbn_strength: 0,
        }),
      },
    })

    expect(wrapper.text()).toContain('Not found in known breaches - Clerk checks this on submit')
  })
})
