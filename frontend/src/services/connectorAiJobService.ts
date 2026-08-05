import { reactive } from 'vue'
import { connectorService } from './connectorService'
import type { ConnectorAIConfigureResult } from '../types/connector'

export type ConnectorAIJobStatus = 'running' | 'completed' | 'partial' | 'error'

export interface ConnectorAIJob {
  id: string
  key: string
  endpointId?: string
  endpointName: string
  requestInformation: string
  status: ConnectorAIJobStatus
  startedAt: number
  finishedAt?: number
  consumedAt?: number
  result?: ConnectorAIConfigureResult
  error?: string
}

interface StartConnectorAIJobOptions {
  key: string
  endpointId?: string
  endpointName: string
  requestInformation: string
}

const jobs = reactive<Record<string, ConnectorAIJob>>({})
const pendingJobs = new Map<string, Promise<ConnectorAIJob>>()

export function getConnectorAIJob(key: string) {
  return jobs[key]
}

export function startConnectorAIJob(options: StartConnectorAIJobOptions) {
  const existing = jobs[options.key]
  if (existing?.status === 'running') {
    return pendingJobs.get(options.key) || Promise.resolve(existing)
  }

  const job = reactive<ConnectorAIJob>({
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    key: options.key,
    endpointId: options.endpointId,
    endpointName: options.endpointName,
    requestInformation: options.requestInformation,
    status: 'running',
    startedAt: Date.now(),
  })
  jobs[options.key] = job

  const promise = connectorService.configureWithAI(options.requestInformation)
    .then((result) => {
      job.result = result
      job.status = result.status
      job.finishedAt = Date.now()
      return job
    })
    .catch((error: unknown) => {
      job.status = 'error'
      job.error = error instanceof Error ? error.message : 'AI configuration failed.'
      job.finishedAt = Date.now()
      return job
    })
    .finally(() => {
      pendingJobs.delete(options.key)
    })

  pendingJobs.set(options.key, promise)
  return promise
}

export function markConnectorAIJobConsumed(key: string) {
  const job = jobs[key]
  if (job) job.consumedAt = Date.now()
}
