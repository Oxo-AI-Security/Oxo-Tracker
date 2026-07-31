import { describe, expect, it } from 'vitest'
import { resolveHistoryViewState } from './historyViewState'

describe('history view state', () => {
  it('does not present an empty state while jobs are still loading', () => {
    expect(resolveHistoryViewState({ loading: true, error: '', jobCount: 0 })).toBe('loading')
  })

  it('keeps cached jobs visible while a refresh is in progress', () => {
    expect(resolveHistoryViewState({ loading: true, error: '', jobCount: 5 })).toBe('list')
  })

  it('separates request failures from a confirmed empty history', () => {
    expect(resolveHistoryViewState({ loading: false, error: 'failed', jobCount: 0 })).toBe('error')
    expect(resolveHistoryViewState({ loading: false, error: '', jobCount: 0 })).toBe('empty')
  })
})
