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
  const runWithReverification = vi.fn(async (operation) => operation())
  return { runWithReverification, ...overrides }
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
    expect(wrapper.find('.setup-panel').exists()).toBe(true)
    expect(wrapper.find('.security-control-row').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('SECRET123')
    expect(wrapper.html()).not.toContain('otpauth://')

    await findButton(wrapper, 'Use setup key instead').trigger('click')
    expect(wrapper.text()).toContain('SECRET123')
    expect(wrapper.html()).not.toContain('otpauth://')
    expect(wrapper.find('.setup-qr-column .readonly-field').exists()).toBe(false)
    expect(wrapper.find('.setup-confirmation .readonly-field').exists()).toBe(true)

    await wrapper.find('input[autocomplete="one-time-code"]').setValue('123456')
    await findButton(wrapper, 'Verify and continue').trigger('click')
    await flushPromises()

    expect(user.verifyTOTP).toHaveBeenCalledWith({ code: '123456' })
    expect(user.createBackupCode).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('from-verify')
    expect(wrapper.text()).not.toContain('code-1')
    expect(wrapper.text()).not.toContain('code-2')

    const doneButton = findButton(wrapper, 'Done')
    expect(doneButton.attributes('disabled')).toBeDefined()

    await wrapper.find('input[type="checkbox"]').setValue(true)
    await doneButton.trigger('click')

    expect(wrapper.find('[data-testid="backup-codes-panel"]').exists()).toBe(false)
    expect(wrapper.vm.backupCodes).toEqual([])
    expect(wrapper.text()).not.toContain('code-1')
    expect(wrapper.text()).not.toContain('code-2')
  })

  it('renders the authenticator action without redundant status copy', () => {
    const user = userFixture()
    const wrapper = mount(TwoFactorSettings, {
      props: { user, isLoaded: true },
    })

    const row = wrapper.find('.security-control-row')
    expect(row.exists()).toBe(true)
    expect(row.text()).toContain('Authenticator app')
    expect(row.find('button').text()).toContain('Enable authenticator app')
    expect(row.text()).not.toContain('Not enabled')
    expect(row.text()).not.toContain('Two-factor authentication')
  })

  it('regenerates backup codes for an enabled authenticator', async () => {
    const user = userFixture({ totpEnabled: true, backupCodeEnabled: true })
    const reverification = sessionFixture()
    const wrapper = mount(TwoFactorSettings, {
      props: { user, reverification, isLoaded: true },
    })

    await findButton(wrapper, 'Regenerate backup codes').trigger('click')
    await flushPromises()

    expect(user.createBackupCode).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('immediately invalidates every current backup code')

    await findButton(wrapper, 'Generate new codes').trigger('click')
    await flushPromises()

    expect(reverification.runWithReverification).toHaveBeenCalledWith(expect.any(Function), {
      level: 'multi_factor',
      message: 'Enter your password to generate new backup codes.',
      retryPolicy: 'verify_first',
      title: 'Verify it is you',
    })
    expect(user.createBackupCode).toHaveBeenCalled()
    expect(wrapper.text()).toContain('code-1')
  })

  it('does not regenerate backup codes until replacement is confirmed', async () => {
    const user = userFixture({ totpEnabled: true, backupCodeEnabled: true })
    const wrapper = mount(TwoFactorSettings, {
      props: { user, isLoaded: true },
    })

    await findButton(wrapper, 'Regenerate backup codes').trigger('click')

    expect(wrapper.find('[data-testid="backup-regeneration-confirmation"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('invalidates every current backup code')
    expect(user.createBackupCode).not.toHaveBeenCalled()

    await findButton(wrapper, 'Cancel').trigger('click')

    expect(wrapper.find('[data-testid="backup-regeneration-confirmation"]').exists()).toBe(false)
    expect(user.createBackupCode).not.toHaveBeenCalled()
  })

  it('does not report backup-code regeneration as successful when Clerk returns no codes', async () => {
    const user = userFixture({
      totpEnabled: true,
      backupCodeEnabled: true,
      createBackupCode: vi.fn().mockResolvedValue({ codes: [] }),
    })
    const wrapper = mount(TwoFactorSettings, {
      props: { user, reverification: sessionFixture(), isLoaded: true },
    })

    await findButton(wrapper, 'Regenerate backup codes').trigger('click')
    await findButton(wrapper, 'Generate new codes').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('did not return new backup codes')
    expect(wrapper.text()).toContain('Existing codes may have been replaced')
    expect(wrapper.text()).not.toContain('New backup codes generated.')
    expect(wrapper.find('[data-testid="backup-regeneration-confirmation"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="backup-codes-panel"]').exists()).toBe(false)
  })

  it('delegates authenticator setup to the shared reverification workflow', async () => {
    const user = userFixture()
    const reverification = sessionFixture({
      runWithReverification: vi.fn(async (operation, options) => ({
        ...(await operation()),
        options,
      })),
    })
    const wrapper = mount(TwoFactorSettings, {
      props: { user, reverification, isLoaded: true },
    })

    await findButton(wrapper, 'Enable authenticator app').trigger('click')
    await flushPromises()

    expect(reverification.runWithReverification).toHaveBeenCalledWith(expect.any(Function), {
      message: 'Enter your password to continue with authenticator setup.',
      retryPolicy: 'verify_first',
      title: 'Verify it is you',
    })
    expect(wrapper.find('[data-testid="authenticator-qr"]').exists()).toBe(true)
  })

  it('keeps TOTP enabled when fallback backup-code generation fails', async () => {
    const user = userFixture({
      verifyTOTP: vi.fn().mockResolvedValue({ backupCodes: [] }),
      createBackupCode: vi.fn().mockRejectedValue(new Error('Backup service unavailable')),
    })
    const wrapper = mount(TwoFactorSettings, {
      props: { user, isLoaded: true },
    })

    await findButton(wrapper, 'Enable authenticator app').trigger('click')
    await flushPromises()
    await wrapper.find('input[autocomplete="one-time-code"]').setValue('123456')
    await findButton(wrapper, 'Verify and continue').trigger('click')
    await flushPromises()

    expect(user.verifyTOTP).toHaveBeenCalledWith({ code: '123456' })
    expect(user.createBackupCode).toHaveBeenCalledTimes(1)
    expect(wrapper.find('.setup-panel').exists()).toBe(false)
    expect(wrapper.find('.security-control-row').text()).toContain('Regenerate backup codes')
    expect(wrapper.text()).toContain('Authenticator app enabled')
    expect(wrapper.text()).toContain('backup service unavailable')
  })

  it('recovers an already-connected setup retry from Clerk state', async () => {
    const user = userFixture({
      createTOTP: vi.fn().mockRejectedValue(new Error('Authenticator is already connected')),
      reload: vi.fn(async () => {
        user.totpEnabled = true
      }),
    })
    const wrapper = mount(TwoFactorSettings, {
      props: { user, isLoaded: true },
    })

    await findButton(wrapper, 'Enable authenticator app').trigger('click')
    await flushPromises()

    expect(user.reload).toHaveBeenCalled()
    expect(wrapper.find('.setup-panel').exists()).toBe(false)
    expect(wrapper.find('.security-control-row').text()).toContain('Regenerate backup codes')
    expect(wrapper.text()).toContain('already enabled')
  })

  it('reports enable completion separately when reload fails', async () => {
    const user = userFixture({
      reload: vi.fn().mockRejectedValue(new Error('Network unavailable')),
    })
    const wrapper = mount(TwoFactorSettings, {
      props: { user, isLoaded: true },
    })

    await findButton(wrapper, 'Enable authenticator app').trigger('click')
    await flushPromises()
    await wrapper.find('input[autocomplete="one-time-code"]').setValue('123456')
    await findButton(wrapper, 'Verify and continue').trigger('click')
    await flushPromises()

    expect(wrapper.find('.setup-panel').exists()).toBe(false)
    expect(wrapper.find('.security-control-row').text()).toContain('Regenerate backup codes')
    expect(wrapper.text()).toContain('Authenticator app enabled')
    expect(wrapper.text()).toContain('could not be refreshed')
  })

  it('disables the authenticator app through Clerk', async () => {
    const user = userFixture({ totpEnabled: true, backupCodeEnabled: true })
    const reverification = sessionFixture()
    const wrapper = mount(TwoFactorSettings, {
      props: { user, reverification, isLoaded: true },
    })

    await findButton(wrapper, 'Disable authenticator app').trigger('click')
    await flushPromises()

    expect(reverification.runWithReverification).toHaveBeenCalledWith(expect.any(Function), {
      level: 'multi_factor',
      message: 'Enter your password to disable authenticator app sign-in.',
      retryPolicy: 'verify_first',
      title: 'Verify it is you',
    })
    expect(user.disableTOTP).toHaveBeenCalled()
    expect(user.reload).toHaveBeenCalled()
  })

  it('reports disable completion separately when reload fails', async () => {
    const user = userFixture({
      totpEnabled: true,
      backupCodeEnabled: true,
      reload: vi.fn().mockRejectedValue(new Error('Network unavailable')),
    })
    const wrapper = mount(TwoFactorSettings, {
      props: { user, reverification: sessionFixture(), isLoaded: true },
    })

    await findButton(wrapper, 'Disable authenticator app').trigger('click')
    await flushPromises()

    expect(wrapper.find('.security-control-row').text()).toContain('Enable authenticator app')
    expect(wrapper.text()).toContain('Authenticator app disabled')
    expect(wrapper.text()).toContain('could not be refreshed')
  })

  it('reports backup-code generation separately when reload fails', async () => {
    const user = userFixture({
      totpEnabled: true,
      backupCodeEnabled: true,
      reload: vi.fn().mockRejectedValue(new Error('Network unavailable')),
    })
    const wrapper = mount(TwoFactorSettings, {
      props: { user, reverification: sessionFixture(), isLoaded: true },
    })

    await findButton(wrapper, 'Regenerate backup codes').trigger('click')
    await findButton(wrapper, 'Generate new codes').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('New backup codes were generated')
    expect(wrapper.text()).toContain('could not be refreshed')
    expect(wrapper.find('[data-testid="backup-codes-panel"]').exists()).toBe(true)
  })

  it('clears generated backup codes from component state', async () => {
    const user = userFixture({ totpEnabled: true, backupCodeEnabled: true })
    const wrapper = mount(TwoFactorSettings, {
      props: { user, isLoaded: true },
    })

    await findButton(wrapper, 'Regenerate backup codes').trigger('click')
    await flushPromises()

    await findButton(wrapper, 'Generate new codes').trigger('click')
    await flushPromises()

    expect(wrapper.vm.backupCodes).toEqual(['code-1', 'code-2'])
    wrapper.unmount()
    expect(wrapper.vm.backupCodes).toEqual([])
  })
})
