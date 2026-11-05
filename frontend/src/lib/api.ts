import axios from 'axios'
import toast from 'react-hot-toast'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1'

export const api = axios.create({
  baseURL: API_URL,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshing: Promise<string | null> | null = null

async function refreshAccess(): Promise<string | null> {
  const refresh = localStorage.getItem('refresh')
  if (!refresh) return null
  try {
    const { data } = await axios.post(`${API_URL}/auth/refresh/`, { refresh })
    localStorage.setItem('access', data.access)
    return data.access as string
  } catch {
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
    return null
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config as (typeof error.config & { _retry?: boolean }) | undefined
    if (error.response?.status === 401 && original && !original._retry) {
      original._retry = true
      refreshing ??= refreshAccess().finally(() => {
        refreshing = null
      })
      const token = await refreshing
      if (token) {
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      }
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    const detail =
      error.response?.data?.detail ||
      error.response?.data?.errors ||
      error.message
    if (typeof detail === 'string' && original?.method !== 'get') {
      toast.error(detail)
    }
    return Promise.reject(error)
  },
)

export function unwrapList<T>(data: T[] | { results: T[] }): T[] {
  return Array.isArray(data) ? data : data.results
}