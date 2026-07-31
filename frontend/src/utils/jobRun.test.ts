import { describe, expect, it } from 'vitest'
import type { BenchmarkJob } from '../types/moonshot'
import {
  benchmarkJobLoadErrorKind,
  findBenchmarkJob,
  isActiveBenchmarkJob,
  mergeBenchmarkJobSummary,
} from './jobRun'

function benchmarkJob(overrides: Partial<BenchmarkJob> = {}): BenchmarkJob {
  return {
    id: 'Oxo-AI-test-1',
    runner_id: 'Oxo-AI-test-1',
    name: 'Oxo-AI-test-1',
    description: '',
    status: 'running',
    progress: 10,
    created_at: '2026-07-30T00:00:00Z',
    updated_at: '2026-07-30T00:00:00Z',
    request: {
      run_name: 'Oxo-AI-test-1',
      endpoints: ['endpoint'],
      recipes: ['recipe'],
      cookbooks: ['cookbook'],
      description: '',
      prompt_selection_percentage: 100,
      estimated_prompts: 10,
      thread_count: 1,
      random_seed: 0,
      system_prompt: '',
    },
    summary: {
      endpoints: ['endpoint'],
      recipes: ['recipe'],
      cookbooks: ['cookbook'],
      estimated_prompts: 10,
      completed_prompts: 1,
      error_count: 0,
      thread_count: 1,
    },
    errors: [],
    events: [],
    ...overrides,
  }
}

describe('benchmark job run state', () => {
  it('keeps polling every active status, including running jobs with errors', () => {
    expect(isActiveBenchmarkJob('queued')).toBe(true)
    expect(isActiveBenchmarkJob('running')).toBe(true)
    expect(isActiveBenchmarkJob('running_with_errors')).toBe(true)
    expect(isActiveBenchmarkJob('completed_with_errors')).toBe(false)
    expect(isActiveBenchmarkJob('failed')).toBe(false)
  })

  it('classifies load failures for a useful recovery message', () => {
    expect(benchmarkJobLoadErrorKind({ status: 404 })).toBe('notFound')
    expect(benchmarkJobLoadErrorKind({ status: 503 })).toBe('unavailable')
    expect(benchmarkJobLoadErrorKind(new Error('Network Error'))).toBe('unavailable')
    expect(benchmarkJobLoadErrorKind({ status: 422 })).toBe('generic')
  })

  it('finds a newly created run summary without depending on id casing', () => {
    const summary = benchmarkJob()
    expect(findBenchmarkJob([summary], 'oxo-ai-test-1')).toBe(summary)
  })

  it('updates summary progress without discarding loaded interactions', () => {
    const current = benchmarkJob({
      interactions: [{ id: 1, endpoint: 'endpoint', recipe: 'recipe' }],
    })
    const summary = benchmarkJob({
      status: 'completed',
      progress: 100,
      summary: {
        ...current.summary,
        completed_prompts: 10,
      },
    })

    const merged = mergeBenchmarkJobSummary(current, summary)

    expect(merged.status).toBe('completed')
    expect(merged.summary.completed_prompts).toBe(10)
    expect(merged.interactions).toEqual(current.interactions)
  })
})
