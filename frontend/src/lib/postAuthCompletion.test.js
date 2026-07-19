import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import {
  clearPostAuthCompletion,
  hasPostAuthCompletion,
  startPostAuthCompletion,
} from './postAuthCompletion'

const STORAGE_KEY = 'socceroctopus.postAuthCompletion'

describe('post-auth completion marker', () => {
  beforeEach(() => window.localStorage.clear())
  afterEach(() => window.localStorage.clear())

  it('survives the provider redirect boundary until completion is consumed', () => {
    startPostAuthCompletion(1_000)

    expect(hasPostAuthCompletion(1_001)).toBe(true)
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe('1000')

    clearPostAuthCompletion()
    expect(hasPostAuthCompletion(1_002)).toBe(false)
  })

  it('clears stale markers so an abandoned provider flow cannot show recovery later', () => {
    startPostAuthCompletion(1_000)

    expect(hasPostAuthCompletion(601_001)).toBe(false)
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull()
  })
})
