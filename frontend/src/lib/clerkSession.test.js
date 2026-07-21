import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  clearAuthState: vi.fn(),
  setAuthPendingState: vi.fn(),
  setAuthState: vi.fn(),
}))
const { apiGet, clearAuthState, setAuthPendingState, setAuthState } = mocks

vi.mock('./api', () => ({
  api: { get: mocks.apiGet },
}))

vi.mock('./auth', () => ({
  clearAuthState: mocks.clearAuthState,
  setAuthPendingState: mocks.setAuthPendingState,
  setAuthState: mocks.setAuthState,
}))

import { activateSessionAndHydrateAuth } from './clerkSession'

function clerkFixture() {
  return { value: { client: { sessions: [] }, session: null } }
}

describe('activateSessionAndHydrateAuth', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('waits for and hydrates the exact requested session', async () => {
    const clerk = clerkFixture()
    const requestedSession = { id: 'sess_requested', getToken: vi.fn().mockResolvedValue('token_requested') }
    const setActive = vi.fn().mockImplementation(async () => {
      setTimeout(() => {
        clerk.value.client.sessions = [requestedSession]
      }, 100)
    })
    apiGet.mockResolvedValue({ data: { id: 'user_1', is_admin: true } })

    const activation = activateSessionAndHydrateAuth({
      clerk,
      setActive,
      sessionId: 'sess_requested',
    })
    await vi.advanceTimersByTimeAsync(100)
    await activation

    expect(requestedSession.getToken).toHaveBeenCalledOnce()
    expect(apiGet).toHaveBeenCalledWith('/api/me', {
      headers: { Authorization: 'Bearer token_requested' },
    })
    expect(setAuthState).toHaveBeenCalledWith({
      signedIn: true,
      isAdmin: true,
      user: { id: 'user_1', is_admin: true },
    })
    expect(clearAuthState).not.toHaveBeenCalled()
  })

  it('keeps the activated session signed in while exact-session hydration catches up', async () => {
    const clerk = clerkFixture()
    const otherSession = { id: 'sess_other', getToken: vi.fn().mockResolvedValue('token_other') }
    clerk.value.client.sessions = [otherSession]
    const setActive = vi.fn().mockResolvedValue(undefined)

    const activation = activateSessionAndHydrateAuth({
      clerk,
      setActive,
      sessionId: 'sess_missing',
    })
    await vi.advanceTimersByTimeAsync(1_000)

    await expect(activation).resolves.toMatchObject({
      hydrated: false,
      error: { message: 'Unable to obtain a token for session sess_missing' },
    })
    expect(otherSession.getToken).not.toHaveBeenCalled()
    expect(apiGet).not.toHaveBeenCalled()
    expect(clearAuthState).not.toHaveBeenCalled()
    expect(setAuthPendingState).toHaveBeenCalledOnce()
    expect(setAuthState).not.toHaveBeenCalled()
  })

  it('does not call /api/me while the exact session has no token', async () => {
    const clerk = clerkFixture()
    const session = { id: 'sess_no_token', getToken: vi.fn().mockResolvedValue(null) }
    clerk.value.client.sessions = [session]
    const setActive = vi.fn().mockResolvedValue(undefined)

    const activation = activateSessionAndHydrateAuth({
      clerk,
      setActive,
      sessionId: 'sess_no_token',
    })
    await vi.advanceTimersByTimeAsync(1_000)

    await expect(activation).resolves.toMatchObject({ hydrated: false })
    expect(session.getToken).toHaveBeenCalledTimes(10)
    expect(apiGet).not.toHaveBeenCalled()
    expect(clearAuthState).not.toHaveBeenCalled()
    expect(setAuthPendingState).toHaveBeenCalledOnce()
    expect(setAuthState).not.toHaveBeenCalled()
  })

  it('keeps a safe signed-in state when /api/me hydration fails', async () => {
    const clerk = clerkFixture()
    const session = { id: 'sess_api_failure', getToken: vi.fn().mockResolvedValue('token_valid') }
    clerk.value.client.sessions = [session]
    const setActive = vi.fn().mockResolvedValue(undefined)
    const error = new Error('request failed')
    apiGet.mockRejectedValue(error)

    await expect(activateSessionAndHydrateAuth({
      clerk,
      setActive,
      sessionId: 'sess_api_failure',
    })).resolves.toMatchObject({
      hydrated: false,
      error,
    })

    expect(clearAuthState).not.toHaveBeenCalled()
    expect(setAuthPendingState).toHaveBeenCalledOnce()
    expect(setAuthState).not.toHaveBeenCalled()
  })

  it('marks failures from setActive as not activated', async () => {
    const clerk = clerkFixture()
    const error = new Error('Clerk rejected the session')
    const setActive = vi.fn().mockRejectedValue(error)

    await expect(activateSessionAndHydrateAuth({
      clerk,
      setActive,
      sessionId: 'sess_rejected',
    })).rejects.toMatchObject({
      code: 'CLERK_SESSION_ACTIVATION_FAILED',
      sessionActivated: false,
      cause: error,
      message: 'Clerk rejected the session',
    })

    expect(clearAuthState).toHaveBeenCalledOnce()
    expect(apiGet).not.toHaveBeenCalled()
  })

  it('hydrates successful auth with the requested session token', async () => {
    const clerk = clerkFixture()
    const session = { id: 'sess_success', getToken: vi.fn().mockResolvedValue('token_success') }
    clerk.value.client.sessions = [session]
    const setActive = vi.fn().mockResolvedValue(undefined)
    apiGet.mockResolvedValue({ data: { id: 'user_success', is_admin: false } })

    await expect(activateSessionAndHydrateAuth({
      clerk,
      setActive,
      sessionId: 'sess_success',
    })).resolves.toEqual({ hydrated: true })

    expect(setActive).toHaveBeenCalledWith({ session: 'sess_success' })
    expect(apiGet).toHaveBeenCalledWith('/api/me', {
      headers: { Authorization: 'Bearer token_success' },
    })
    expect(setAuthState).toHaveBeenCalledWith({
      signedIn: true,
      isAdmin: false,
      user: { id: 'user_success', is_admin: false },
    })
    expect(clearAuthState).not.toHaveBeenCalled()
  })
})
