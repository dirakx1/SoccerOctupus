import { describe, expect, it } from 'vitest'

import { userFacingError } from './userFacingError'

describe('userFacingError', () => {
  it('keeps useful provider-neutral messages', () => {
    expect(userFacingError(new Error('Incorrect password'), 'Unable to verify.')).toBe('Incorrect password')
  })

  it('replaces provider-branded messages with neutral copy', () => {
    expect(userFacingError({
      errors: [{ longMessage: 'Clerk could not complete this request.' }],
    }, 'Unable to verify.')).toBe('Unable to verify.')
  })
})
