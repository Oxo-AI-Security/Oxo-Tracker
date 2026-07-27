import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./http', () => ({
  http: {
    post: vi.fn(),
    get: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import { http } from './http'
import { defaultTaskAgentConfig, taskAgentsApi } from './taskAgents'

const post = vi.mocked(http.post)
const get = vi.mocked(http.get)
const remove = vi.mocked(http.delete)

describe('taskAgentsApi.createTask', () => {
  beforeEach(() => post.mockReset())

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
