import { afterEach, describe, expect, it, vi } from 'vitest'
import axios from 'axios'

import { api, installAuthInterceptor } from './api'

describe('API auth interceptor', () => {
  afterEach(() => {
    api.defaults.adapter = undefined
  })

  it('refreshes the token once after a /api/me 401', async () => {
    const getToken = vi.fn()
      .mockImplementationOnce(() => Promise.resolve('stale-token'))
      .mockImplementationOnce(() => Promise.resolve('fresh-token'))
      .mockResolvedValue('stale-token')
    let attempts = 0
    api.defaults.adapter = async (config) => {
      attempts += 1
      if (attempts === 1) {
        throw new axios.AxiosError('unauthorized', 'ERR_BAD_REQUEST', config, null, {
          status: 401,
          config,
          headers: {},
          data: {},
          statusText: 'Unauthorized',
        })
      }
      expect(config.headers.Authorization).toBe('Bearer fresh-token')
      return { config, data: { ok: true }, headers: {}, status: 200, statusText: 'OK' }
    }
    installAuthInterceptor(getToken)

    await expect(api.get('/api/me')).resolves.toMatchObject({ data: { ok: true } })
    expect(getToken).toHaveBeenNthCalledWith(2, { skipCache: true })
    expect(attempts).toBe(2)
  })

  it('does not retry a second 401 or unrelated endpoint', async () => {
    const getToken = vi.fn().mockResolvedValue('token')
    api.defaults.adapter = async (config) => {
      throw new axios.AxiosError('unauthorized', 'ERR_BAD_REQUEST', config, null, {
        status: 401,
        config,
        headers: {},
        data: {},
        statusText: 'Unauthorized',
      })
    }
    installAuthInterceptor(getToken)

    await expect(api.get('/api/me')).rejects.toMatchObject({ response: { status: 401 } })
    await expect(api.get('/api/profile')).rejects.toMatchObject({ response: { status: 401 } })
    expect(getToken).toHaveBeenCalledTimes(3)
    expect(getToken.mock.calls.filter(([options]) => options?.skipCache)).toHaveLength(1)
  })
})
