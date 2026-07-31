export type HistoryViewState = 'loading' | 'error' | 'list' | 'empty'

export function resolveHistoryViewState(options: {
  loading: boolean
  error: string
  jobCount: number
}): HistoryViewState {
  if (options.jobCount > 0) return 'list'
  if (options.loading) return 'loading'
  if (options.error) return 'error'
  return 'empty'
}
