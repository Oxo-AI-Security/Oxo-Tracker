import { describe, expect, it, vi } from 'vitest'
import { connectorService, defaultConnectorConfig } from './connectorService'
import { getConnectorAIJob, startConnectorAIJob } from './connectorAiJobService'

describe('connector AI background jobs', () => {
  it('exposes a running state immediately and completes in the background', async () => {
    let resolveResult!: (value: Awaited<ReturnType<typeof connectorService.configureWithAI>>) => void
    const deferred = new Promise<Awaited<ReturnType<typeof connectorService.configureWithAI>>>((resolve) => {
      resolveResult = resolve
    })
    vi.spyOn(connectorService, 'configureWithAI').mockReturnValueOnce(deferred)
    const key = `endpoint-${Date.now()}`

    const pending = startConnectorAIJob({
      key,
      endpointId: key,
      endpointName: 'Endpoint',
      requestInformation: 'POST https://example.test/chat',
    })

    expect(getConnectorAIJob(key)?.status).toBe('running')

    resolveResult({
      status: 'completed',
      stage: 'completed',
      message: 'Configured',
      missingInformation: [],
      config: defaultConnectorConfig('http'),
      testPrompt: 'Hello',
      provider: 'test',
      model: 'test-model',
    })
    await pending

    expect(getConnectorAIJob(key)?.status).toBe('completed')
    expect(getConnectorAIJob(key)?.finishedAt).toEqual(expect.any(Number))
  })
})
