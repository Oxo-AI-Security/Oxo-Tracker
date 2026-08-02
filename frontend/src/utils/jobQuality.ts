import type { BenchmarkJob } from '../types/moonshot'

export type ExpectationScoreTone = 'success' | 'strong' | 'warning' | 'danger'

export interface JobExpectationScore {
  percent: number
  matched: number
  total: number
  unexpected: number
  failed: number
  tone: ExpectationScoreTone
}

export function expectationScoreTone(percent: number): ExpectationScoreTone {
  if (percent === 100) return 'success'
  if (percent > 80) return 'strong'
  if (percent >= 60) return 'warning'
  return 'danger'
}

export function calculateJobExpectationScore(job?: BenchmarkJob | null): JobExpectationScore | null {
  if (!job || !['completed', 'completed_with_errors'].includes(job.status)) return null
  const report = job.report_summary
  if (!report) return null

  const total = Math.max(0, Number(report.total_prompts || job.summary.completed_prompts || 0))
  if (!total) return null

  const unexpected = Math.min(total, Math.max(0, Number(report.unexpected_payload_count || 0)))
  const reportFailed = (report.recipe_summaries || []).reduce(
    (sum, recipe) => sum + Math.max(0, Number(recipe.failed_count || 0)),
    0,
  )
  const fallbackFailed = Math.max(0, Number(job.summary.error_count || 0))
  const failed = Math.min(total - unexpected, reportFailed || fallbackFailed)
  const matched = Math.max(0, total - unexpected - failed)
  const percent = Math.max(0, Math.min(100, Math.round((matched / total) * 100)))

  return {
    percent,
    matched,
    total,
    unexpected,
    failed,
    tone: expectationScoreTone(percent),
  }
}
