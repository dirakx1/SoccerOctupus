import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import TwoFactorSettings from './TwoFactorSettings.vue'

function userFixture(overrides = {}) {
  return {
    username: 'alexmorgan',
    totpEnabled: false,
    backupCodeEnabled: false,
    twoFactorEnabled: false,
    createTOTP: vi.fn().mockResolvedValue({
      secret: 'SECRET123',
      uri: 'otpauth://totp/SoccerOctopus:alexmorgan',
    }),
    verifyTOTP: vi.fn().mockResolvedValue({ backupCodes: ['from-verify'] }),
    createBackupCode: vi.fn().mockResolvedValue({ codes: ['code-1', 'code-2'] }),
    disableTOTP: vi.fn().mockResolvedValue({ deleted: true }),
    reload: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  }
}

function sessionFixture(overrides = {}) {
  return {
    startVerification: vi.fn().mockResolvedValue({
      status: 'needs_first_factor',
      supportedFirstFactors: [{ strategy: 'password' }],
    }),
    attemptFirstFactorVerification: vi.fn().mockResolvedValue({ status: 'complete' }),
    prepareFirstFactorVerification: vi.fn(),
    verifyWithPasskey: vi.fn(),
    ...overrides,
  }
}

function findButton(wrapper, text) {
  return wrapper.findAll('button').find((button) => button.text().includes(text))
}

describe('TwoFactorSettings', () => {
  beforeEach(() => {
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:backup-codes'),
      revokeObjectURL: vi.fn(),
    })
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
      configurable: true,
    })
  })

  it('sets up TOTP and shows backup codes once', async () => {
    const user = userFixture()
    const wrapper = mount(TwoFactorSettings, {
      props: { user, isLoaded: true },
    })

    await findButton(wrapper, 'Enable authenticator app').trigger('click')
    await flushPromises()

    expect(user.createTOTP).toHaveBeenCalled()
    expect(wrapper.find('[data-testid="authenticator-qr"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('SECRET123')
    expect(wrapper.html()).not.toContain('otpauth://')

    await findButton(wrapper, 'Use setup key instead').trigger('click')
    expect(wrapper.text()).toContain('SECRET123')
    expect(wrapper.html()).not.toContain('otpauth://')

    await wrapper.find('input[autocomplete="one-time-code"]').setValue('123456')
    await findButton(wrapper, 'Verify and generate backup codes').trigger('click')
    await flushPromises()

    expect(user.verifyTOTP).toHaveBeenCalledWith({ code: '123456' })
    expect(user.createBackupCode).toHaveBeenCalled()
    expect(wrapper.text()).toContain('code-1')
    expect(wrapper.text()).toContain('code-2')

    const doneButton = findButton(wrapper, 'Done')
    expect(doneButton.attributes('disabled')).toBeDefined()

    await wrapper.find('input[type="checkbox"]').setValue(true)
    await doneButton.trigger('click')

    expect(wrapper.find('[data-testid="backup-codes-panel"]').exists()).toBe(false)
  })

  it('regenerates backup codes for an enabled authenticator', async () => {
    const user = userFixture({ totpEnabled: true, backupCodeEnabled: true })
    const wrapper = mount(TwoFactorSettings, {
      props: { user, isLoaded: true },
    })

    await findButton(wrapper, 'Regenerate backup codes').trigger('click')
    await flushPromises()

    expect(user.createBackupCode).toHaveBeenCalled()
    expect(wrapper.text()).toContain('code-1')
  })

  it('reverifies the session before enabling authenticator app when required', async () => {
    const user = userFixture()
    user.createTOTP
      .mockRejectedValueOnce({
        errors: [{ code: 'session_reverification_required', message: 'Reverification required' }],
      })
      .mockResolvedValueOnce({
        secret: 'SECRET123',
        uri: 'otpauth://totp/SoccerOctopus:alexmorgan',
      })
    const session = sessionFixture()
    const wrapper = mount(TwoFactorSettings, {
      props: { user, session, isLoaded: true },
    })

    await findButton(wrapper, 'Enable authenticator app').trigger('click')
    await flushPromises()

    expect(session.startVerification).toHaveBeenCalledWith({ level: 'first_factor' })
    expect(wrapper.text()).toContain('Verify it is you')

    await wrapper.find('input[autocomplete="current-password"]').setValue('current-pass')
    await wrapper.find('form').trigger('submit.prevent')
    await flushPromises()

    expect(session.attemptFirstFactorVerification).toHaveBeenCalledWith({
      strategy: 'password',
      password: 'current-pass',
    })
    expect(user.createTOTP).toHaveBeenCalledTimes(2)
    expect(wrapper.find('[data-testid="authenticator-qr"]').exists()).toBe(true)
  })

  it('disables the authenticator app through Clerk', async () => {
    const user = userFixture({ totpEnabled: true, backupCodeEnabled: true })
    const wrapper = mount(TwoFactorSettings, {
      props: { user, isLoaded: true },
    })

    await findButton(wrapper, 'Disable authenticator app').trigger('click')
    await flushPromises()

    expect(user.disableTOTP).toHaveBeenCalled()
    expect(user.reload).toHaveBeenCalled()
  })

  it('clears generated backup codes from component state', async () => {
    const user = userFixture({ totpEnabled: true, backupCodeEnabled: true })
    const wrapper = mount(TwoFactorSettings, {
      props: { user, isLoaded: true },
    })

    await findButton(wrapper, 'Regenerate backup codes').trigger('click')
    await flushPromises()

    expect(wrapper.vm.backupCodes).toEqual(['code-1', 'code-2'])
    wrapper.unmount()
    expect(wrapper.vm.backupCodes).toEqual([])
  })
})
