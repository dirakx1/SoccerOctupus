import axios from 'axios'

export const api = axios.create()

let authInterceptorId = null

export function installAuthInterceptor(getToken) {
  if (authInterceptorId !== null) {
    api.interceptors.request.eject(authInterceptorId)
  }

  authInterceptorId = api.interceptors.request.use(async (config) => {
    const token = await getToken?.()
    if (token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })
}
