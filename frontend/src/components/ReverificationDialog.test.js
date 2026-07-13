import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { computed, ref } from 'vue'

import ReverificationDialog from './ReverificationDialog.vue'

function workflowFixture(overrides = {}) {
  const strategy = ref('password')
  const password = ref('')
  const code = ref('')

  return {
    alternativeSecondFactorLabel: computed(() => ''),
    canSubmit: computed(() => Boolean(password.value || code.value)),
    canSwitchSecondFactor: computed(() => false),
    cancel: vi.fn(),
    code,
    codeInputMode: computed(() => 'numeric'),
    codePlaceholder: computed(() => '123456'),
    copy: computed(() => 'Enter your password to continue.'),
    error: ref(''),
    isOpen: ref(true),
    loading: ref(false),
    password,
    strategy,
    submit: vi.fn(),
    switchSecondFactor: vi.fn(),
    title: ref('Verify it is you'),
    usesVerificationCode: computed(() => ['email_code', 'phone_code'].includes(strategy.value)),
    verificationCodeLabel: computed(() => 'Verification code'),
    ...overrides,
  }
}

describe('ReverificationDialog', () => {
  it('collects password input and submits the shared workflow', async () => {
    const workflow = workflowFixture()
    const wrapper = mount(ReverificationDialog, {
      props: { workflow },
      global: { stubs: { Teleport: true } },
    })

    expect(wrapper.text()).toContain('Verify it is you')
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()

    await wrapper.find('input[autocomplete="current-password"]').setValue('current-pass')
    await wrapper.find('form').trigger('submit.prevent')

    expect(workflow.password.value).toBe('current-pass')
    expect(workflow.submit).toHaveBeenCalled()
    wrapper.unmount()
  })

  it('renders code input for email and phone verification strategies', async () => {
    const workflow = workflowFixture({
      strategy: ref('email_code'),
      copy: computed(() => 'Enter the code sent to a***@example.com to continue.'),
      usesVerificationCode: computed(() => true),
    })
    const wrapper = mount(ReverificationDialog, {
      props: { workflow },
      global: { stubs: { Teleport: true } },
    })

    expect(wrapper.text()).toContain('a***@example.com')
    await wrapper.find('input[autocomplete="one-time-code"]').setValue('123456')

    expect(workflow.code.value).toBe('123456')
    wrapper.unmount()
  })

  it('renders authenticator code copy for second-factor verification', () => {
    const workflow = workflowFixture({
      strategy: ref('totp'),
      copy: computed(() => 'Enter the 6-digit code from your authenticator app to continue.'),
      usesVerificationCode: computed(() => true),
      verificationCodeLabel: computed(() => 'Authenticator code'),
    })
    const wrapper = mount(ReverificationDialog, {
      props: { workflow },
      global: { stubs: { Teleport: true } },
    })

    expect(wrapper.text()).toContain('authenticator app')
    expect(wrapper.text()).toContain('Authenticator code')
    expect(wrapper.find('input[autocomplete="one-time-code"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('switches from authenticator code to a backup code', async () => {
    const switchSecondFactor = vi.fn()
    const workflow = workflowFixture({
      alternativeSecondFactorLabel: computed(() => 'Use a backup code instead'),
      canSwitchSecondFactor: computed(() => true),
      codeInputMode: computed(() => 'numeric'),
      copy: computed(() => 'Enter the 6-digit code from your authenticator app to continue.'),
      strategy: ref('totp'),
      switchSecondFactor,
      usesVerificationCode: computed(() => true),
      verificationCodeLabel: computed(() => 'Authenticator code'),
    })
    const wrapper = mount(ReverificationDialog, {
      props: { workflow },
      global: { stubs: { Teleport: true } },
    })

    await wrapper.get('button.btn-link').trigger('click')
    expect(switchSecondFactor).toHaveBeenCalled()
    wrapper.unmount()
  })
})
