import { describe, expect, it } from 'vitest'

import { apiErrorMessage } from './http'

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
})
