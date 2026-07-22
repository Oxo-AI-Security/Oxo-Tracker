import axios from 'axios'

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8001',
  timeout: 300000,
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail
    const message = typeof detail === 'string' ? detail : error.message
    const nextError = new Error(message || 'Request failed') as Error & { status?: number }
    nextError.status = error.response?.status
    return Promise.reject(nextError)
  },
)
