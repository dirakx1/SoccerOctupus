import axios from 'axios'

export const api = axios.create()

export function installAuthInterceptor(getToken) {
  api.interceptors.request.use(async (config) => {
    const token = await getToken?.()
    if (token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })
}
