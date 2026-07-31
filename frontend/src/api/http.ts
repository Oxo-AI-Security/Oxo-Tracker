import axios from 'axios'

export interface ApiRequestError extends Error {
  status?: number
  detail?: unknown
}

export function apiErrorMessage(detail: unknown, fallback = 'Request failed') {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (!item || typeof item !== 'object') return ''
        const issue = item as { loc?: unknown; msg?: unknown }
        const location = Array.isArray(issue.loc)
          ? issue.loc
              .filter((part) => part !== 'body')
              .map(String)
              .join('.')
          : ''
        const message = typeof issue.msg === 'string' ? issue.msg : ''
        return [location, message].filter(Boolean).join(': ')
      })
      .filter(Boolean)
    if (messages.length) return messages.join('; ')
  }
  if (detail && typeof detail === 'object') {
    const message = (detail as { message?: unknown }).message
    if (typeof message === 'string' && message.trim()) return message
  }
  return fallback
}

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8001',
  timeout: 300000,
})

let desktopToken = ''

export function configureApiRuntime(baseURL: string, token = '') {
  http.defaults.baseURL = baseURL.replace(/\/$/, '')
  desktopToken = token
}

http.interceptors.request.use((config) => {
  if (desktopToken) {
    config.headers.set('X-Oxo-Desktop-Token', desktopToken)
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail
    const message = apiErrorMessage(detail, error.message || 'Request failed')
    const nextError = new Error(message) as ApiRequestError
    nextError.status = error.response?.status
    nextError.detail = detail
    return Promise.reject(nextError)
  },
)
