import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
})

export const TOKEN_STORAGE_KEY = 'openoncall_token'

export function setAuthToken(token: string | null) {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
    apiClient.defaults.headers.common.Authorization = `Token ${token}`
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    delete apiClient.defaults.headers.common.Authorization
  }
}

// Re-apply a stored token on page load, before any component mounts.
const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY)
if (storedToken) {
  apiClient.defaults.headers.common.Authorization = `Token ${storedToken}`
}
