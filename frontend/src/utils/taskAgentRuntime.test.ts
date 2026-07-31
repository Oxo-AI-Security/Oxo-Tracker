import { describe, expect, it } from 'vitest'
import {
  hasPendingTaskAgentReviews,
  isTaskAgentGoalActive,
  isTaskAgentTerminalReady,
  liveTaskAgentElapsedSeconds,
  mapBackendTaskStatus,
  shouldPollTask,
  shouldReleaseGoalComposer,
  taskAgentTerminalFinalizationPhase,
  visibleTaskAgentProgress,
} from './taskAgentRuntime'
import type { TaskAiWatchReview } from '../api/taskAgents'

const review = (
  status: TaskAiWatchReview['status'],
): TaskAiWatchReview => ({
  round_key: 'round-1',
  round: 1,
  status,
  queued_at: '2026-07-29T00:00:00Z',
  summary: '',
})

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

  it('does not finalize while the parent AI Watch review is pending', () => {
    const parent = {
      status: 'succeeded' as const,
      ai_watch_reviews: {
        'round-1': review('analyzing'),
      },
    }
    expect(hasPendingTaskAgentReviews(parent)).toBe(true)
    expect(isTaskAgentTerminalReady(parent)).toBe(false)
    expect(taskAgentTerminalFinalizationPhase(parent)).toBe(
      'waiting_for_parent_review',
    )
  })

  it('waits for terminal child review and archive before summary', () => {
    const parent = {
      status: 'failed' as const,
      ai_watch_reviews: {},
    }
    const child = {
      status: 'stopping' as const,
      ai_watch_reviews: {},
    }
    expect(taskAgentTerminalFinalizationPhase(parent, [child])).toBe(
      'waiting_for_child_archive',
    )
  })

  it('releases terminal chrome only after every review and child settles', () => {
    const parent = {
      status: 'stopped_safety' as const,
      ai_watch_reviews: {
        'round-1': review('complete'),
      },
    }
    const child = {
      status: 'stopped_manual' as const,
      ai_watch_reviews: {
        'round-1': review('complete'),
      },
    }
    expect(isTaskAgentTerminalReady(parent)).toBe(true)
    expect(taskAgentTerminalFinalizationPhase(parent, [child])).toBe(
      'ready_for_summary',
    )
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

  it('never renders 100 percent before verified success', () => {
    expect(visibleTaskAgentProgress(100, 'evaluating', 72)).toBe(99)
    expect(visibleTaskAgentProgress(100, 'paused', 72)).toBe(99)
    expect(visibleTaskAgentProgress(100, 'achieved', 72)).toBe(100)
  })

  it('advances elapsed time locally between slower server snapshots', () => {
    expect(liveTaskAgentElapsedSeconds(20.2, 1_000, 1_700, true)).toBe(20)
    expect(liveTaskAgentElapsedSeconds(20.2, 1_000, 1_800, true)).toBe(21)
    expect(liveTaskAgentElapsedSeconds(20.2, 1_000, 2_800, true)).toBe(22)
    expect(liveTaskAgentElapsedSeconds(20.2, 1_000, 8_000, false)).toBe(20)
  })
})
