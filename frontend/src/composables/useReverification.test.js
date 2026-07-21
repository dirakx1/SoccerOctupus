import { flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import { isReverificationError, useReverification } from './useReverification'

function reverificationError() {
  return {
    errors: [{ code: 'session_reverification_required', message: 'Reverification required' }],
  }
}

function sessionFixture(overrides = {}) {
  return {
    startVerification: vi.fn().mockResolvedValue({
      status: 'needs_first_factor',
      supportedFirstFactors: [{ strategy: 'password' }],
    }),
    attemptFirstFactorVerification: vi.fn().mockResolvedValue({ status: 'complete' }),
    attemptSecondFactorVerification: vi.fn().mockResolvedValue({ status: 'complete' }),
    prepareFirstFactorVerification: vi.fn(),
    prepareSecondFactorVerification: vi.fn(),
    verifyWithPasskey: vi.fn(),
    ...overrides,
  }
}

function deferred() {
  let resolve
  let reject
  const promise = new Promise((promiseResolve, promiseReject) => {
    resolve = promiseResolve
    reject = promiseReject
  })
  return { promise, resolve, reject }
}

describe('useReverification', () => {
  it('detects Clerk session reverification errors', () => {
    expect(isReverificationError(reverificationError())).toBe(true)
    expect(isReverificationError(new Error('nope'))).toBe(false)
  })

  it('opens a reusable password dialog state and retries the protected action', async () => {
    const session = sessionFixture()
    const workflow = useReverification({ session: ref(session) })
    const protectedAction = vi.fn()
      .mockRejectedValueOnce(reverificationError())
      .mockResolvedValueOnce('done')

    const resultPromise = workflow.runWithReverification(protectedAction, {
      message: 'Enter your password to continue.',
      retryPolicy: 'replay',
    })
    await flushPromises()

    expect(workflow.isOpen.value).toBe(true)
    expect(workflow.strategy.value).toBe('password')
    expect(workflow.copy.value).toBe('Enter your password to continue.')

    workflow.password.value = 'current-pass'
    await workflow.submit()
    await expect(resultPromise).resolves.toBe('done')

    expect(session.startVerification).toHaveBeenCalledWith({ level: 'first_factor' })
    expect(session.attemptFirstFactorVerification).toHaveBeenCalledWith({
      strategy: 'password',
      password: 'current-pass',
    })
    expect(protectedAction).toHaveBeenCalledTimes(2)
    expect(workflow.isOpen.value).toBe(false)
  })

  it('prepares email-code reverification when that is the available first factor', async () => {
    const session = sessionFixture({
      startVerification: vi.fn().mockResolvedValue({
        status: 'needs_first_factor',
        supportedFirstFactors: [{
          strategy: 'email_code',
          emailAddressId: 'email_123',
          safeIdentifier: 'a***@example.com',
        }],
      }),
    })
    const workflow = useReverification({ session: ref(session) })

    const startPromise = workflow.start()
    await flushPromises()

    expect(workflow.isOpen.value).toBe(true)
    expect(workflow.strategy.value).toBe('email_code')
    expect(workflow.copy.value).toContain('a***@example.com')
    expect(session.prepareFirstFactorVerification).toHaveBeenCalledWith({
      strategy: 'email_code',
      emailAddressId: 'email_123',
    })

    workflow.code.value = '123456'
    await workflow.submit()
    await expect(startPromise).resolves.toBeUndefined()
  })

  it('completes password and authenticator code for multi-factor reverification', async () => {
    const session = sessionFixture({
      attemptFirstFactorVerification: vi.fn().mockResolvedValue({
        status: 'needs_second_factor',
        supportedSecondFactors: [{ strategy: 'totp' }, { strategy: 'backup_code' }],
      }),
    })
    const workflow = useReverification({ session: ref(session) })
    const protectedAction = vi.fn()
      .mockRejectedValueOnce(reverificationError())
      .mockResolvedValueOnce('disabled')

    const resultPromise = workflow.runWithReverification(protectedAction, {
      level: 'multi_factor',
      message: 'Enter your password to continue.',
      retryPolicy: 'replay',
    })
    await flushPromises()

    workflow.password.value = 'current-pass'
    await workflow.submit()

    expect(workflow.isOpen.value).toBe(true)
    expect(workflow.strategy.value).toBe('totp')
    expect(workflow.copy.value).toContain('authenticator app')
    expect(workflow.canSwitchSecondFactor.value).toBe(true)
    expect(workflow.alternativeSecondFactorLabel.value).toBe('Use a backup code instead')

    workflow.switchSecondFactor()
    expect(workflow.strategy.value).toBe('backup_code')
    expect(workflow.copy.value).toContain('backup codes')

    workflow.code.value = 'backup-1234'
    await workflow.submit()

    await expect(resultPromise).resolves.toBe('disabled')
    expect(session.startVerification).toHaveBeenCalledWith({ level: 'multi_factor' })
    expect(session.attemptSecondFactorVerification).toHaveBeenCalledWith({
      strategy: 'backup_code',
      code: 'backup-1234',
    })
    expect(protectedAction).toHaveBeenCalledTimes(2)
  })

  it('rejects an overlapped start instead of orphaning the first promise', async () => {
    const firstStart = deferred()
    const session = sessionFixture({
      startVerification: vi.fn()
        .mockReturnValueOnce(firstStart.promise)
        .mockResolvedValueOnce({
          status: 'needs_first_factor',
          supportedFirstFactors: [{ strategy: 'password' }],
        }),
    })
    const workflow = useReverification({ session: ref(session) })

    const firstPromise = workflow.start()
    const secondPromise = workflow.start()

    await expect(firstPromise).rejects.toThrow('superseded')
    await flushPromises()
    expect(workflow.isOpen.value).toBe(true)
    expect(workflow.strategy.value).toBe('password')

    firstStart.resolve({
      status: 'needs_first_factor',
      supportedFirstFactors: [{ strategy: 'email_code', emailAddressId: 'late' }],
    })
    await flushPromises()

    expect(workflow.strategy.value).toBe('password')
    workflow.password.value = 'current-pass'
    await workflow.submit()
    await expect(secondPromise).resolves.toBeUndefined()
  })

  it('contains late SDK results after cancellation', async () => {
    const startCall = deferred()
    const session = sessionFixture({ startVerification: vi.fn().mockReturnValue(startCall.promise) })
    const workflow = useReverification({ session: ref(session) })
    const startPromise = workflow.start()

    workflow.cancel()
    await expect(startPromise).rejects.toThrow('cancelled')

    startCall.resolve({
      status: 'needs_first_factor',
      supportedFirstFactors: [{ strategy: 'password' }],
    })
    await flushPromises()

    expect(workflow.isOpen.value).toBe(false)
    expect(workflow.strategy.value).toBe('')
    expect(workflow.loading.value).toBe(false)
  })

  it('allows one bounded reverify-again attempt when the protected action remains guarded', async () => {
    const session = sessionFixture()
    const protectedAction = vi.fn()
      .mockRejectedValueOnce(reverificationError())
      .mockRejectedValueOnce(reverificationError())
      .mockResolvedValueOnce('done')
    const workflow = useReverification({ session: ref(session) })

    const resultPromise = workflow.runWithReverification(protectedAction, {
      retryPolicy: 'replay',
    })
    resultPromise.catch(() => {})
    await flushPromises()
    workflow.password.value = 'current-pass'
    await workflow.submit()
    await vi.waitFor(() => expect(workflow.isOpen.value).toBe(true))

    workflow.password.value = 'current-pass'
    await workflow.submit()
    await expect(resultPromise).resolves.toBe('done')
    expect(session.startVerification).toHaveBeenCalledTimes(2)
    expect(protectedAction).toHaveBeenCalledTimes(3)
  })

  it('stops reverify-again after the configured bound', async () => {
    const session = sessionFixture()
    const protectedAction = vi.fn().mockRejectedValue(reverificationError())
    const workflow = useReverification({ session: ref(session) })

    const resultPromise = workflow.runWithReverification(protectedAction, {
      maxReverificationAttempts: 1,
      retryPolicy: 'replay',
    })
    await flushPromises()
    workflow.password.value = 'current-pass'
    await workflow.submit()
    await expect(resultPromise).rejects.toEqual(reverificationError())
    expect(session.startVerification).toHaveBeenCalledTimes(1)
    expect(protectedAction).toHaveBeenCalledTimes(2)
  })

  it('supports reconcile policy without replaying a possibly non-idempotent operation', async () => {
    const session = sessionFixture()
    const protectedAction = vi.fn().mockRejectedValueOnce(reverificationError())
    const reconcile = vi.fn().mockResolvedValue('reconciled')
    const workflow = useReverification({ session: ref(session) })

    const resultPromise = workflow.runWithReverification(protectedAction, {
      retryPolicy: { mode: 'reconcile', reconcile },
    })
    await flushPromises()
    workflow.password.value = 'current-pass'
    await workflow.submit()

    await expect(resultPromise).resolves.toBe('reconciled')
    expect(protectedAction).toHaveBeenCalledTimes(1)
    expect(reconcile).toHaveBeenCalledWith({
      attempt: 1,
      operationError: expect.objectContaining({ errors: expect.any(Array) }),
    })
  })

  it('does not replay an operation unless the caller explicitly opts in', async () => {
    const session = sessionFixture()
    const protectedAction = vi.fn().mockRejectedValueOnce(reverificationError())
    const workflow = useReverification({ session: ref(session) })

    const resultPromise = workflow.runWithReverification(protectedAction)
    await flushPromises()
    workflow.password.value = 'current-pass'
    await workflow.submit()

    await expect(resultPromise).rejects.toEqual(reverificationError())
    expect(protectedAction).toHaveBeenCalledTimes(1)
  })

  it('verifies before executing a protected mutation', async () => {
    const session = sessionFixture()
    const protectedAction = vi.fn().mockResolvedValue('done')
    const workflow = useReverification({ session: ref(session) })

    const resultPromise = workflow.runWithReverification(protectedAction, {
      retryPolicy: 'verify_first',
    })
    await flushPromises()

    expect(protectedAction).not.toHaveBeenCalled()
    workflow.password.value = 'current-pass'
    await workflow.submit()

    await expect(resultPromise).resolves.toBe('done')
    expect(protectedAction).toHaveBeenCalledTimes(1)
  })

  it('keeps the dialog open after an invalid password so the user can correct it', async () => {
    const session = sessionFixture({
      attemptFirstFactorVerification: vi.fn().mockRejectedValue(new Error('Incorrect password')),
    })
    const workflow = useReverification({ session: ref(session) })
    const startPromise = workflow.start()
    await flushPromises()

    workflow.password.value = 'wrong-pass'
    await workflow.submit()

    expect(workflow.isOpen.value).toBe(true)
    expect(workflow.error.value).toBe('Incorrect password')
    workflow.cancel()
    await expect(startPromise).rejects.toThrow('cancelled')
  })

  it('settles the protected action when Clerk returns an unusable verification state', async () => {
    const session = sessionFixture({
      attemptFirstFactorVerification: vi.fn().mockResolvedValue({ status: 'needs_first_factor' }),
    })
    const workflow = useReverification({ session: ref(session) })
    const protectedAction = vi.fn().mockRejectedValueOnce(reverificationError())

    const resultPromise = workflow.runWithReverification(protectedAction, {
      retryPolicy: 'replay',
    })
    await flushPromises()
    workflow.password.value = 'current-pass'
    await workflow.submit()

    await expect(resultPromise).rejects.toThrow('Please sign in again')
    expect(workflow.isOpen.value).toBe(false)
  })
})
