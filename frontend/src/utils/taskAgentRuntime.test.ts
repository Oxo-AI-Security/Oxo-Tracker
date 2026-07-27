import { describe, expect, it } from 'vitest'
import {
  isTaskAgentGoalActive,
  mapBackendTaskStatus,
  shouldPollTask,
  shouldReleaseGoalComposer,
} from './taskAgentRuntime'

describe('persistent Task Agent UI state', () => {
  it('maps graph nodes to visible phases without a round limit', () => {
    expect(mapBackendTaskStatus({ status: 'running', current_node: 'planner' })).toBe('planning')
    expect(mapBackendTaskStatus({ status: 'running', current_node: 'executor' })).toBe('executing')
    expect(mapBackendTaskStatus({ status: 'running', current_node: 'target' })).toBe('sending')
    expect(mapBackendTaskStatus({ status: 'running', current_node: 'analysis_parallel' })).toBe(
      'evaluating',
    )
  })

  it('keeps paused tasks visible and polls only non-terminal tasks', () => {
    expect(mapBackendTaskStatus({ status: 'paused', current_node: 'executor' })).toBe('paused')
    expect(shouldPollTask({ status: 'paused' })).toBe(true)
    expect(shouldPollTask({ status: 'succeeded' })).toBe(false)
    expect(shouldPollTask({ status: 'stopped_manual' })).toBe(false)
  })

  it('uses differentiated success, safety stop, and failure states', () => {
    expect(mapBackendTaskStatus({ status: 'succeeded', current_node: 'router' })).toBe('achieved')
    expect(mapBackendTaskStatus({ status: 'stopped_safety', current_node: 'router' })).toBe('stopped')
    expect(mapBackendTaskStatus({ status: 'failed', current_node: 'failed' })).toBe('error')
  })

  it('locks the composer only while a goal is actually in progress', () => {
    expect(isTaskAgentGoalActive('test a target', 'planning')).toBe(true)
    expect(isTaskAgentGoalActive('test a target', 'paused')).toBe(true)
    expect(isTaskAgentGoalActive('test a target', 'error')).toBe(false)
    expect(isTaskAgentGoalActive('test a target', 'stopped')).toBe(false)
    expect(isTaskAgentGoalActive('', 'planning')).toBe(false)
  })

  it('returns the composer to goal entry only after success', () => {
    expect(shouldReleaseGoalComposer({ status: 'succeeded' })).toBe(true)
    expect(shouldReleaseGoalComposer({ status: 'running' })).toBe(false)
    expect(shouldReleaseGoalComposer({ status: 'paused' })).toBe(false)
    expect(shouldReleaseGoalComposer({ status: 'stopped_safety' })).toBe(false)
  })
})
