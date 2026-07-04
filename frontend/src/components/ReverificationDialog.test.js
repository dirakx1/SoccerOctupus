import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { computed, ref } from 'vue'

import ReverificationDialog from './ReverificationDialog.vue'

function workflowFixture(overrides = {}) {
  const strategy = ref('password')
  const password = ref('')
  const code = ref('')

  return {
    canSubmit: computed(() => Boolean(password.value || code.value)),
    cancel: vi.fn(),
    code,
    copy: computed(() => 'Enter your password to continue.'),
    error: ref(''),
    isOpen: ref(true),
    loading: ref(false),
    password,
    strategy,
    submit: vi.fn(),
    title: ref('Verify it is you'),
    usesVerificationCode: computed(() => ['email_code', 'phone_code'].includes(strategy.value)),
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
})
