import { describe, expect, it } from 'vitest'
import type { BenchmarkJob } from '../types/moonshot'
import { calculateJobExpectationScore, expectationScoreTone } from './jobQuality'

function completedJob(overrides: Partial<BenchmarkJob> = {}): BenchmarkJob {
  return {
    id: 'job-1',
    runner_id: 'runner-1',
    name: 'Benchmark',
    description: '',
    status: 'completed',
    progress: 100,
    created_at: '',
    updated_at: '',
    request: {
      run_name: 'Expectation score test',
      endpoints: [],
      recipes: [],
      cookbooks: [],
      description: '',
      prompt_selection_percentage: 100,
      estimated_prompts: 10,
      thread_count: 1,
      random_seed: 1,
      system_prompt: '',
    },
    summary: {
      endpoints: [],
      recipes: [],
      cookbooks: [],
      estimated_prompts: 10,
      completed_prompts: 10,
      error_count: 0,
      thread_count: 1,
    },
    errors: [],
    events: [],
    report_summary: {
      id: 'job-1',
      name: 'Benchmark',
      description: '',
      status: 'completed',
      endpoints: [],
      recipes: [],
      cookbooks: [],
      total_prompts: 10,
      recipe_summaries: [],
      unexpected_payload_count: 0,
      unexpected_payloads: [],
      errors: [],
    },
    ...overrides,
  }
}

describe('calculateJobExpectationScore', () => {
  it('returns a green 100 percent score when every payload matches expectations', () => {
    expect(calculateJobExpectationScore(completedJob())).toMatchObject({
      percent: 100,
      matched: 10,
      total: 10,
      tone: 'success',
    })
  })

  it('counts unexpected and failed payloads against the score', () => {
    const job = completedJob()
    job.report_summary!.unexpected_payload_count = 2
    job.report_summary!.recipe_summaries = [{
      id: 'recipe-1',
      total_prompts: 10,
      prompt_count: 9,
      failed_count: 1,
      datasets: [],
      evaluation_summary: [],
      metric_summaries: [],
      grading_scale: {},
    }]
    expect(calculateJobExpectationScore(job)).toMatchObject({
      percent: 70,
      matched: 7,
      unexpected: 2,
      failed: 1,
      tone: 'warning',
    })
  })

  it('does not expose a final score before the job is complete', () => {
    expect(calculateJobExpectationScore(completedJob({ status: 'running' }))).toBeNull()
  })
})

describe('expectationScoreTone', () => {
  it('uses the requested green, purple, orange, and red bands', () => {
    expect(expectationScoreTone(100)).toBe('success')
    expect(expectationScoreTone(90)).toBe('strong')
    expect(expectationScoreTone(80)).toBe('warning')
    expect(expectationScoreTone(60)).toBe('warning')
    expect(expectationScoreTone(59)).toBe('danger')
  })
})
