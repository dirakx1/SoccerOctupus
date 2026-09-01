import axios from 'axios'

export const api = axios.create()

let authInterceptorId = null
let authResponseInterceptorId = null

export function installAuthInterceptor(getToken) {
  if (authInterceptorId !== null) {
    api.interceptors.request.eject(authInterceptorId)
  }

  authInterceptorId = api.interceptors.request.use(async (config) => {
    if (config?._authRetried) return config
    const token = await getToken?.()
    if (token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  if (authResponseInterceptorId !== null) {
    api.interceptors.response.eject(authResponseInterceptorId)
  }

  authResponseInterceptorId = api.interceptors.response.use(undefined, async (error) => {
    const config = error?.config
    if (
      error?.response?.status !== 401 ||
      config?._authRetried ||
      config?.url !== '/api/me'
    ) {
      throw error
    }

    const freshToken = await getToken?.({ skipCache: true })
    if (!freshToken) throw error

    config._authRetried = true
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${freshToken}`
    return api.request(config)
  })
}
