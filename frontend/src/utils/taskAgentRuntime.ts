import type { TaskAgentSnapshot } from '../api/taskAgents'

export type TaskAgentUiStatus =
  | 'idle'
  | 'planning'
  | 'executing'
  | 'sending'
  | 'evaluating'
  | 'paused'
  | 'achieved'
  | 'stopped'
  | 'error'

export const terminalTaskAgentStatuses = new Set<TaskAgentSnapshot['status']>([
  'succeeded',
  'stopped_safety',
  'stopped_manual',
  'failed',
])

export function mapBackendTaskStatus(
  snapshot: Pick<TaskAgentSnapshot, 'status' | 'current_node'>,
): TaskAgentUiStatus {
  if (snapshot.status === 'succeeded') return 'achieved'
  if (snapshot.status === 'stopped_safety' || snapshot.status === 'stopped_manual') return 'stopped'
  if (snapshot.status === 'failed') return 'error'
  if (snapshot.status === 'paused' || snapshot.status === 'pausing') return 'paused'
  if (snapshot.current_node === 'executor') return 'executing'
  if (snapshot.current_node === 'target') return 'sending'
  if (
    ['analysis_parallel', 'sensitive_analyzer', 'evaluator', 'router'].includes(
      snapshot.current_node,
    )
  ) {
    return 'evaluating'
  }
  return 'planning'
}

export function shouldPollTask(snapshot: Pick<TaskAgentSnapshot, 'status'>) {
  return !terminalTaskAgentStatuses.has(snapshot.status)
}

export function isTaskAgentGoalActive(
  goal: string | null | undefined,
  status: TaskAgentUiStatus | null | undefined,
) {
  return Boolean(goal) && [
    'planning',
    'executing',
    'sending',
    'evaluating',
    'paused',
  ].includes(status || 'idle')
}

export function shouldReleaseGoalComposer(snapshot: Pick<TaskAgentSnapshot, 'status'>) {
  return snapshot.status === 'succeeded'
}

export function liveTaskAgentElapsedSeconds(
  baseSeconds: number | null | undefined,
  syncedAtMs: number | null | undefined,
  nowMs: number,
  isActive: boolean,
) {
  const normalizedBase =
    Number.isFinite(Number(baseSeconds)) && Number(baseSeconds) > 0
      ? Number(baseSeconds)
      : 0
  const normalizedSync = Number(syncedAtMs)
  if (!isActive || !Number.isFinite(normalizedSync) || normalizedSync <= 0) {
    return Math.floor(normalizedBase)
  }
  const localDeltaSeconds = Math.max(0, nowMs - normalizedSync) / 1000
  return Math.floor(normalizedBase + localDeltaSeconds)
}
