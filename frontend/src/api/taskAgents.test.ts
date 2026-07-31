import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./http', () => ({
  http: {
    post: vi.fn(),
    patch: vi.fn(),
    get: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import { http } from './http'
import {
  applyTaskAgentExplorationPreset,
  defaultTaskAgentConfig,
  normalizeTaskAgentConfig,
  taskAgentsApi,
} from './taskAgents'

const post = vi.mocked(http.post)
const patch = vi.mocked(http.patch)
const get = vi.mocked(http.get)
const remove = vi.mocked(http.delete)

describe('taskAgentsApi.createTask', () => {
  beforeEach(() => post.mockReset())

  it('uses bounded task and parent-child family safety defaults', () => {
    const config = defaultTaskAgentConfig()

    expect(config).toMatchObject({
      exploration_intensity: 'deep',
      control_provider: null,
      control_model: null,
      max_rounds: 24,
      max_runtime_seconds: 1800,
      max_input_tokens: 500000,
      max_output_tokens: 100000,
      max_family_rounds: 32,
      max_family_input_tokens: 750000,
      max_family_output_tokens: 150000,
      max_evidence_stall_rounds: 4,
      near_duplicate_threshold: 0.92,
      baseline_scanner_enabled: true,
      baseline_max_probes: 4,
      branch_min_marginal_utility: 0.12,
      branch_stop_no_gain_rounds: 3,
    })
  })

  it('maps exploration intensity to real run budgets', () => {
    const extreme = applyTaskAgentExplorationPreset(
      defaultTaskAgentConfig(),
      'extreme',
    )

    expect(extreme).toMatchObject({
      exploration_intensity: 'extreme',
      max_rounds: 40,
      max_runtime_seconds: 3600,
      max_active_skills: 4,
      max_parallel_branches: 2,
      max_variants_per_technique: 8,
      max_family_rounds: 64,
      baseline_max_probes: 6,
      branch_max_allocated_rounds: 8,
    })
  })

  it('repairs legacy all-null budgets before creating a task', async () => {
    post.mockResolvedValueOnce({ data: { task_id: 'task-migrated-budget' } })
    const legacyConfig = {
      ...defaultTaskAgentConfig(),
      max_rounds: null,
      max_runtime_seconds: null,
      max_input_tokens: null,
      max_output_tokens: null,
      max_estimated_cost: null,
    }

    expect(normalizeTaskAgentConfig(legacyConfig)).toMatchObject({
      max_rounds: 24,
      max_runtime_seconds: 1800,
      max_input_tokens: 500000,
      max_output_tokens: 100000,
    })

    await taskAgentsApi.createTask({
      session_id: 'session-legacy',
      chat_id: 'chat-legacy',
      runner_id: 'runner-legacy',
      goal: 'Map public capabilities',
      history: [],
      config: legacyConfig,
    })

    expect(post.mock.calls[0]?.[1]).toMatchObject({
      config: {
        max_rounds: 24,
        max_runtime_seconds: 1800,
        max_input_tokens: 500000,
        max_output_tokens: 100000,
      },
    })
  })

  it('retries without max_active_skills when a running V2 backend rejects it', async () => {
    const legacyError = Object.assign(
      new Error('config.max_active_skills: Extra inputs are not permitted'),
      { status: 422 },
    )
    post
      .mockRejectedValueOnce(legacyError)
      .mockResolvedValueOnce({ data: { task_id: 'task-legacy-compatible' } })

    const result = await taskAgentsApi.createTask({
      session_id: 'session-1',
      chat_id: 'chat-1',
      runner_id: 'runner-1',
      goal: 'Map public capabilities',
      history: [],
      config: defaultTaskAgentConfig(),
    })

    expect(result.task_id).toBe('task-legacy-compatible')
    expect(post).toHaveBeenCalledTimes(2)
    expect(post.mock.calls[0]?.[1]).toMatchObject({
      config: { max_active_skills: 3 },
    })
    expect(post.mock.calls[1]?.[1]).not.toHaveProperty(
      'config.max_active_skills',
    )
  })

  it('does not hide unrelated validation failures', async () => {
    const validationError = Object.assign(new Error('goal: Field required'), {
      status: 422,
    })
    post.mockRejectedValueOnce(validationError)

    await expect(
      taskAgentsApi.createTask({
        session_id: 'session-1',
        chat_id: 'chat-1',
        runner_id: 'runner-1',
        goal: 'Map public capabilities',
        history: [],
        config: defaultTaskAgentConfig(),
      }),
    ).rejects.toThrow('goal: Field required')
    expect(post).toHaveBeenCalledTimes(1)
  })

  it('removes auto-resume fields for an intermediate legacy backend', async () => {
    const legacyError = Object.assign(
      new Error(
        'config.auto_resume_transient_failures: Extra inputs are not permitted',
      ),
      { status: 422 },
    )
    post
      .mockRejectedValueOnce(legacyError)
      .mockResolvedValueOnce({ data: { task_id: 'task-legacy-auto-resume' } })

    await taskAgentsApi.createTask({
      session_id: 'session-1',
      chat_id: 'chat-1',
      runner_id: 'runner-1',
      goal: 'Map public capabilities',
      history: [],
      config: defaultTaskAgentConfig(),
    })

    expect(post.mock.calls[1]?.[1]).not.toHaveProperty(
      'config.auto_resume_transient_failures',
    )
    expect(post.mock.calls[1]?.[1]).not.toHaveProperty(
      'config.max_auto_resumes',
    )
    expect(post.mock.calls[1]?.[1]).not.toHaveProperty(
      'config.auto_resume_delay_seconds',
    )
  })

  it('removes harness fields for an intermediate legacy backend', async () => {
    const legacyError = Object.assign(
      new Error(
        'config.max_family_rounds: Extra inputs are not permitted',
      ),
      { status: 422 },
    )
    post
      .mockRejectedValueOnce(legacyError)
      .mockResolvedValueOnce({ data: { task_id: 'task-legacy-harness' } })

    await taskAgentsApi.createTask({
      session_id: 'session-1',
      chat_id: 'chat-1',
      runner_id: 'runner-1',
      goal: 'Map public capabilities',
      history: [],
      config: defaultTaskAgentConfig(),
    })

    expect(post.mock.calls[1]?.[1]).not.toHaveProperty(
      'config.max_family_rounds',
    )
    expect(post.mock.calls[1]?.[1]).not.toHaveProperty(
      'config.max_evidence_stall_rounds',
    )
    expect(post.mock.calls[1]?.[1]).not.toHaveProperty(
      'config.near_duplicate_threshold',
    )
  })
})

describe('taskAgentsApi goal records', () => {
  beforeEach(() => {
    get.mockReset()
    remove.mockReset()
  })

  it('loads records for the current target and optional runner alias', async () => {
    get.mockResolvedValueOnce({
      data: [{ memory_id: 'memory-1', goal: 'Reach the goal' }],
    })

    const records = await taskAgentsApi.listSuccessMemories({
      target_key: 'https://example.test/api/chat',
      runner_id: 'runner-1',
      limit: 25,
    })

    expect(records[0]?.memory_id).toBe('memory-1')
    expect(get).toHaveBeenCalledWith(
      '/api/v1/task-agents/success-memories',
      {
        params: {
          target_key: 'https://example.test/api/chat',
          runner_id: 'runner-1',
          limit: 25,
        },
      },
    )
  })

  it('deletes one goal record by its stable identifier', async () => {
    remove.mockResolvedValueOnce({ data: undefined })

    await taskAgentsApi.deleteSuccessMemory('memory/a b')

    expect(remove).toHaveBeenCalledWith(
      '/api/v1/task-agents/success-memories/memory%2Fa%20b',
    )
  })
})

describe('taskAgentsApi parallel branches', () => {
  beforeEach(() => post.mockReset())

  it('adopts a successful child task into its parent task', async () => {
    post.mockResolvedValueOnce({
      data: {
        task_id: 'task-parent',
        status: 'succeeded',
        branch_result: { source_task_id: 'task-child' },
      },
    })

    const result = await taskAgentsApi.adoptBranchSuccess(
      'task/parent',
      'task child',
    )

    expect(result.status).toBe('succeeded')
    expect(post).toHaveBeenCalledWith(
      '/api/v1/task-agents/tasks/task%2Fparent/adopt-success/task%20child',
    )
  })

  it('queues a parent follow-up for one child branch', async () => {
    post.mockResolvedValueOnce({
      data: { task_id: 'task-child', status: 'running' },
    })

    await taskAgentsApi.followUpBranch(
      'task/parent',
      'task child',
      'Test the remaining proof gap.',
    )

    expect(post).toHaveBeenCalledWith(
      '/api/v1/task-agents/tasks/task%2Fparent/branches/task%20child/follow-up',
      { instruction: 'Test the remaining proof gap.' },
    )
  })

  it('stops a low-yield child branch through its parent', async () => {
    post.mockResolvedValueOnce({
      data: { task_id: 'task-child', status: 'stopping' },
    })

    await taskAgentsApi.stopBranch(
      'task/parent',
      'task child',
      'No marginal evidence gain.',
    )

    expect(post).toHaveBeenCalledWith(
      '/api/v1/task-agents/tasks/task%2Fparent/branches/task%20child/stop',
      { reason: 'No marginal evidence gain.' },
    )
  })
})

describe('taskAgentsApi evidence reconciliation', () => {
  beforeEach(() => post.mockReset())

  it('re-adjudicates committed evidence without sending a target message', async () => {
    post.mockResolvedValueOnce({
      data: {
        task_id: 'task/current',
        status: 'succeeded',
        goal_progress: 100,
      },
    })

    const result = await taskAgentsApi.reconcileEvidence('task/current')

    expect(result.status).toBe('succeeded')
    expect(post).toHaveBeenCalledWith(
      '/api/v1/task-agents/tasks/task%2Fcurrent/reconcile-evidence',
    )
  })
})

describe('taskAgentsApi goal editing', () => {
  beforeEach(() => patch.mockReset())

  it('queues a replacement goal for the active task', async () => {
    patch.mockResolvedValueOnce({
      data: {
        task_id: 'task/current',
        status: 'running',
        goal: 'Updated objective',
      },
    })

    const result = await taskAgentsApi.updateGoal(
      'task/current',
      'Updated objective',
    )

    expect(result.goal).toBe('Updated objective')
    expect(patch).toHaveBeenCalledWith(
      '/api/v1/task-agents/tasks/task%2Fcurrent/goal',
      { goal: 'Updated objective' },
    )
  })
})

describe('taskAgentsApi P1 run assets', () => {
  beforeEach(() => {
    post.mockReset()
    get.mockReset()
  })

  it('regrades and replays through explicit offline endpoints', async () => {
    post
      .mockResolvedValueOnce({
        data: {
          regrade_id: 'regrade-1',
          mode: 'offline',
          target_call_count: 0,
        },
      })
      .mockResolvedValueOnce({
        data: {
          replay_id: 'replay-1',
          mode: 'offline',
          target_call_count: 0,
          rounds: [],
        },
      })

    const regrade = await taskAgentsApi.regradeRun('task/a')
    const replay = await taskAgentsApi.replayRun('task/a')

    expect(regrade.target_call_count).toBe(0)
    expect(replay.target_call_count).toBe(0)
    expect(post).toHaveBeenNthCalledWith(
      1,
      '/api/v1/task-agents/tasks/task%2Fa/regrade',
      {},
    )
    expect(post).toHaveBeenNthCalledWith(
      2,
      '/api/v1/task-agents/tasks/task%2Fa/replay',
    )
  })

  it('creates an isolated round fork with an immutable source reference', async () => {
    post.mockResolvedValueOnce({
      data: {
        fork_id: 'fork-1',
        source_unchanged: true,
        round: 4,
        task: { task_id: 'task-fork' },
      },
    })

    const result = await taskAgentsApi.forkRun('task/source', {
      round: 4,
      instruction: 'Explore a different route.',
    })

    expect(result.source_unchanged).toBe(true)
    expect(post).toHaveBeenCalledWith(
      '/api/v1/task-agents/tasks/task%2Fsource/fork',
      { round: 4, instruction: 'Explore a different route.' },
    )
  })

  it('turns a durable Finding into a Regression Case', async () => {
    post
      .mockResolvedValueOnce({
        data: { finding_id: 'finding/a', severity: 'high' },
      })
      .mockResolvedValueOnce({
        data: {
          regression_case_id: 'regression-1',
          finding_id: 'finding/a',
        },
      })

    const finding = await taskAgentsApi.createFinding('task/source')
    const regression = await taskAgentsApi.createRegressionCase(
      finding.finding_id,
    )

    expect(regression.finding_id).toBe('finding/a')
    expect(post).toHaveBeenNthCalledWith(
      2,
      '/api/v1/task-agents/findings/finding%2Fa/regression-cases',
      {},
    )
  })
})
