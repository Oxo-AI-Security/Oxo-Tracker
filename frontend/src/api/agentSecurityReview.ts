import { http } from './http'
import type { CanvasDiagram } from '../modules/agents/agent-canvas/canvas.types'

export type ReviewProject = {
  projectId: string
  projectName: string
  description: string
  agentType: string
  status: string
  createdAt?: string
  updatedAt?: string
  functionReview?: unknown | null
  riskReview?: unknown | null
  error?: string
}

export type ModelProvider = {
  label: string
  apiKeyLabel: string
  models: Array<{ label: string; value: string }>
  supported: string
}

export const agentSecurityReviewApi = {
  async createProject(payload: { projectName: string; description: string; agentType?: string; provider?: string; modelName?: string; model?: string }) {
    const { data } = await http.post<{ projectId: string }>('/api/v1/agent-security-review/projects', payload)
    return data
  },
  async listProjects() {
    const { data } = await http.get<ReviewProject[]>('/api/v1/agent-security-review/projects')
    return data
  },
  async getProject(projectId: string) {
    const { data } = await http.get<ReviewProject>(`/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}`)
    return data
  },
  async getCanvas(projectId: string) {
    const { data } = await http.get<CanvasDiagram>(`/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}/canvas`)
    return data
  },
  async saveCanvas(projectId: string, canvas: CanvasDiagram) {
    const { data } = await http.put<CanvasDiagram>(`/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}/canvas`, canvas)
    return data
  },
  async deleteProject(projectId: string) {
    const { data } = await http.delete<{ deleted: boolean; projectId: string }>(`/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}`)
    return data
  },
  async saveProjectContext(projectId: string, payload: Partial<ReviewProject> & Record<string, unknown>) {
    const { data } = await http.patch<ReviewProject>(`/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}`, payload)
    return data
  },
  async listModelProviders() {
    const { data } = await http.get<{ providers: Record<string, ModelProvider> }>('/api/v1/agent-security-review/settings/models')
    return data.providers
  },
}
