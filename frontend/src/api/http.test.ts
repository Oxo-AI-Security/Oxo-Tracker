import { describe, expect, it } from 'vitest'

import { apiErrorMessage, configureApiRuntime, http } from './http'

describe('apiErrorMessage', () => {
  it('renders FastAPI validation locations instead of a generic 422 message', () => {
    expect(
      apiErrorMessage([
        {
          type: 'extra_forbidden',
          loc: ['body', 'config', 'max_active_skills'],
          msg: 'Extra inputs are not permitted',
        },
      ]),
    ).toBe('config.max_active_skills: Extra inputs are not permitted')
  })

  it('uses structured API messages and a fallback', () => {
    expect(apiErrorMessage({ message: 'Active task already exists' })).toBe(
      'Active task already exists',
    )
    expect(apiErrorMessage(undefined, 'Network Error')).toBe('Network Error')
  })

  it('applies the sidecar URL and session token at runtime', async () => {
    configureApiRuntime('http://127.0.0.1:49152/', 'desktop-session')
    const response = await http.get('/health', {
      adapter: async (config) => ({
        config,
        data: {},
        headers: {},
        status: 200,
        statusText: 'OK',
      }),
    })
    expect(http.defaults.baseURL).toBe('http://127.0.0.1:49152')
    expect(response.config.headers.get('X-Oxo-Desktop-Token')).toBe('desktop-session')
    configureApiRuntime('http://127.0.0.1:8001')
  })
})
