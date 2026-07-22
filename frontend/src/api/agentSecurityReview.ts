import { http } from './http'
import type { AgentAssetGraph, SavedAssetLayout } from '../modules/agents/agent-security-review/graph/assetGraph.types'

export type ReviewProject = {
  projectId: string
  projectName: string
  description: string
  agentType: string
  status: string
  createdAt?: string
  updatedAt?: string
  materials: ReviewMaterial[]
  manualInputs: ManualInputs
  missingAnswers: Record<string, string>
  functionReview?: FunctionReview | null
  functionMap: FlowGraph
  assetGraph?: AgentAssetGraph | null
  assetLayout?: SavedAssetLayout
  riskReview?: RiskReview | null
  riskMap: FlowGraph
  reportMarkdown?: string
  settings?: Record<string, unknown>
  error?: string
}

export type ModelProvider = {
  label: string
  apiKeyLabel: string
  models: Array<{ label: string; value: string }>
  supported: string
}

export type ReviewMaterial = {
  fileId: string
  fileName: string
  tag: string
  contentType: string
  extension: string
  size: number
  uploadedAt: string
  extractionSupported: boolean
  extractionNote?: string
}

export type ManualInputs = {
  systemPrompt: string
  toolList: string
  ragSource: string
  apiEndpointDescription: string
  extraNotes: string
}

export type DimensionCoverage = {
  dimension_id: string
  dimension_name: string
  dimension_zh_name: string
  status: 'present' | 'partial' | 'missing' | 'unknown' | 'not_applicable' | 'high_risk'
  coverage_score: number
  confidence: number
  summary: string
  detected_assets: AssetItem[]
  detected_items: string[]
  missing_fields: string[]
  evidence: EvidenceItem[]
  related_capability_ids: string[]
  related_graph_node_ids: string[]
  unanswered_question_count: number
  potential_risk_hints: string[]
}

export type AssetItem = {
  asset_id: string
  asset_type: string
  name: string
  description: string
  properties: Record<string, unknown>
  source_dimension_id: string
  confidence: number
  risk_level: 'none' | 'low' | 'medium' | 'high' | 'critical' | 'unknown'
}

export type EvidenceItem = {
  evidence_id: string
  source_type: 'uploaded_file' | 'manual_input' | 'image' | 'inferred'
  source_name: string
  excerpt: string
  confidence: number
}

export type MissingQuestion = {
  id: string
  dimension_id: string
  asset_type?: string
  related_capability_ids: string[]
  related_asset_ids: string[]
  priority: 'critical' | 'high' | 'medium' | 'low'
  question: string
  reason: string
  answer_type: 'text' | 'single_choice' | 'multi_choice' | 'boolean'
  options?: string[]
  answer?: string | string[] | boolean
  blocks_risk_mapping: boolean
}

export type FlowNodeData = {
  label: string
  nodeType: string
  description: string
  riskSeverity?: string
  risks?: string[]
  [key: string]: unknown
}

export type FlowGraph = {
  nodes: Array<{ id: string; type?: string; position: { x: number; y: number }; data: FlowNodeData }>
  edges: Array<{ id: string; source: string; target: string; label?: string; data?: Record<string, unknown> }>
}

export type FunctionReview = {
  projectId: string
  projectName: string
  review_stage?: 'asset_review'
  schema_version?: string
  overall_confidence?: number
  project_summary?: Record<string, unknown>
  coverage_matrix?: DimensionCoverage[]
  summary: string
  confidence: number
  features: Array<{
    id: string
    name: string
    mapped_dimensions?: string[]
    related_asset_ids?: string[]
    status?: 'present' | 'partial' | 'inferred'
    description: string
    trigger: string
    inputs: string[]
    outputs: string[]
    components: string[]
    tools?: Array<Record<string, unknown>>
    rag?: Record<string, unknown>
    file_or_image_processing?: Record<string, unknown>
    flow_next?: string[]
    external_systems?: string[]
    data_assets?: string[]
    permissions?: string[]
    dependencies?: string[]
    evidence?: string[]
    missing_fields?: string[]
  }>
  relationships?: Array<{ id: string; source: string; target: string; type: string; label: string }>
  asset_graph_nodes?: Array<Record<string, unknown>>
  asset_graph_edges?: Array<Record<string, unknown>>
  components: Array<Record<string, unknown>>
  capabilities: Array<Record<string, unknown>>
  dataFlows: Array<Record<string, unknown>>
  assumptions: Array<Record<string, unknown>>
  missingInformation: Array<{ id: string; question: string; reason: string }>
  missing_questions?: MissingQuestion[]
  agentAssetGraph?: AgentAssetGraph
  vueFlow: FlowGraph
}

export type RiskReview = {
  projectId: string
  summary: string
  risks: Array<{
    id: string
    title: string
    severity: 'critical' | 'high' | 'medium' | 'low'
    category: string
    location: { nodes: string[]; edges: string[] }
    description: string
    impact: string
    recommendation: string
  }>
  vueFlow: FlowGraph
  reportMarkdown: string
}

export const defaultManualInputs: ManualInputs = {
  systemPrompt: '',
  toolList: '',
  ragSource: '',
  apiEndpointDescription: '',
  extraNotes: '',
}

export const agentSecurityReviewApi = {
  async createProject(payload: { projectName: string; description: string; agentType: string; provider?: string; modelName?: string; model?: string }) {
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
  async deleteProject(projectId: string) {
    const { data } = await http.delete<{ deleted: boolean; projectId: string }>(`/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}`)
    return data
  },
  async saveProjectContext(projectId: string, payload: Partial<ReviewProject> & { functionMap?: FlowGraph; provider?: string; modelName?: string; model?: string; temperature?: number }) {
    const { data } = await http.patch<ReviewProject>(`/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}`, payload)
    return data
  },
  async uploadMaterials(projectId: string, files: File[], tag: string) {
    const form = new FormData()
    files.forEach((file) => form.append('files', file))
    form.append('tag', tag)
    const { data } = await http.post<{ materials: ReviewMaterial[] }>(
      `/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}/materials`,
      form,
    )
    return data
  },
  async deleteMaterial(projectId: string, fileId: string) {
    const { data } = await http.delete(`/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}/materials/${encodeURIComponent(fileId)}`)
    return data
  },
  materialFileUrl(projectId: string, fileId: string) {
    const path = `/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}/materials/${encodeURIComponent(fileId)}/file`
    return new URL(path, http.defaults.baseURL).toString()
  },
  async previewMaterial(projectId: string, fileId: string) {
    const { data } = await http.get<string>(
      `/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}/materials/${encodeURIComponent(fileId)}/preview`,
      { responseType: 'text' },
    )
    return data
  },
  async saveGeminiApiKey(apiKey: string) {
    const { data } = await http.post<{ geminiApiKeyConfigured: boolean }>('/api/v1/agent-security-review/settings/gemini', { apiKey })
    return data
  },
  async testGemini() {
    const { data } = await http.post<{ ok: boolean; model: string }>('/api/v1/agent-security-review/settings/gemini/test')
    return data
  },
  async listModelProviders() {
    const { data } = await http.get<{ providers: Record<string, ModelProvider> }>('/api/v1/agent-security-review/settings/models')
    return data.providers
  },
  async saveProviderApiKey(provider: string, apiKey: string) {
    const { data } = await http.post<{ apiKeyConfigured: boolean; provider: string }>('/api/v1/agent-security-review/settings/api-key', { provider, apiKey })
    return data
  },
  async testProvider(provider: string, modelName: string) {
    const { data } = await http.post<{ ok: boolean; provider: string; modelId: string }>('/api/v1/agent-security-review/settings/test', { provider, modelName })
    return data
  },
  async startFunctionReview(projectId: string, payload: { manualInputs: ManualInputs; missingAnswers: Record<string, string> }) {
    const { data } = await http.post<ReviewProject>(`/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}/function-review`, payload)
    return data
  },
  async cancelReview(projectId: string) {
    const { data } = await http.post<ReviewProject>(`/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}/review/cancel`)
    return data
  },
  async saveFunctionMap(projectId: string, graph: FlowGraph) {
    const { data } = await http.put<FlowGraph>(`/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}/function-map`, graph)
    return data
  },
  async updateFunctionMap(projectId: string, payload: { manualInputs: ManualInputs; missingAnswers: Record<string, string>; functionMap: FlowGraph; mode?: 'direct' | 'review_again' }) {
    const { data } = await http.post<ReviewProject>(`/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}/function-map/update`, payload)
    return data
  },
  async generateRiskMap(projectId: string, payload: { manualInputs: ManualInputs; missingAnswers: Record<string, string>; functionMap: FlowGraph }) {
    const { data } = await http.post<ReviewProject>(`/api/v1/agent-security-review/projects/${encodeURIComponent(projectId)}/risk-review`, payload)
    return data
  },
}
