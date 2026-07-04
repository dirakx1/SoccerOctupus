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
    prepareFirstFactorVerification: vi.fn(),
    verifyWithPasskey: vi.fn(),
    ...overrides,
  }
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
})
