import type { BenchmarkJob } from '../types/moonshot'

const ACTIVE_BENCHMARK_JOB_STATUSES = new Set([
  'queued',
  'running',
  'running_with_errors',
])

export type BenchmarkJobLoadErrorKind = 'notFound' | 'unavailable' | 'generic'

export function isActiveBenchmarkJob(status?: string | null) {
  return Boolean(status && ACTIVE_BENCHMARK_JOB_STATUSES.has(status))
}

export function findBenchmarkJob(jobs: BenchmarkJob[], jobId: string) {
  const expected = jobId.toLocaleLowerCase()
  return jobs.find((job) => (
    job.id.toLocaleLowerCase() === expected
    || job.runner_id.toLocaleLowerCase() === expected
  ))
}

export function mergeBenchmarkJobSummary(current: BenchmarkJob | null, summary: BenchmarkJob) {
  if (!current) return summary
  return {
    ...current,
    ...summary,
    interactions: current.interactions,
    interactions_pagination: current.interactions_pagination,
    result: current.result,
  }
}

export function benchmarkJobLoadErrorKind(error: unknown): BenchmarkJobLoadErrorKind {
  if (!error || typeof error !== 'object') return 'generic'

  const status = Number((error as { status?: unknown }).status)
  if (status === 404) return 'notFound'
  if (!status || status >= 500) return 'unavailable'
  return 'generic'
}
