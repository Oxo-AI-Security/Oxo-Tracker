export const agentAssetTypes = [
  'actor',
  'entry_point',
  'input_data',
  'frontend',
  'backend',
  'agent_orchestrator',
  'prompt_instruction',
  'llm_model',
  'rag_retriever',
  'knowledge_base',
  'memory',
  'mcp_server',
  'tool_function',
  'external_system',
  'identity_permission',
  'security_control',
] as const

export type AgentAssetType = (typeof agentAssetTypes)[number]

export const agentAssetLayers = [
  'actor_entry',
  'application',
  'agent_core',
  'ai_knowledge',
  'action_integration',
  'security_governance',
] as const

export type AgentAssetLayer = (typeof agentAssetLayers)[number]

export const agentAssetEdgeTypes = [
  'input_flow',
  'api_call',
  'prompt_flow',
  'retrieval',
  'tool_call',
  'data_access',
  'identity_binding',
  'control',
  'memory_read_write',
  'external_integration',
] as const

export type AgentAssetEdgeType = (typeof agentAssetEdgeTypes)[number]

export type AgentAssetStatus = 'present' | 'inferred' | 'unknown'

export type MissingQuestion = {
  id: string
  asset_type: AgentAssetType
  question: string
  reason: string
  impact: 'low' | 'medium' | 'high'
}

export type AgentAssetNode = {
  id: string
  name: string
  asset_type: AgentAssetType
  layer: AgentAssetLayer
  status: AgentAssetStatus
  description?: string
  owner?: string
  source_evidence?: string[]
  data_handled?: string[]
  permissions?: string[]
  access_mode?: 'read' | 'write' | 'read_write' | 'execute' | 'unknown'
  risk_hint?: 'low' | 'medium' | 'high' | 'unknown'
  requires_approval?: boolean
  metadata?: Record<string, unknown>
}

export type AgentAssetEdge = {
  id: string
  source: string
  target: string
  edge_type: AgentAssetEdgeType
  label?: string
  description?: string
  data_flow?: string[]
  auth_context?: string
  status?: AgentAssetStatus
}

export type AgentAssetGraph = {
  version: string
  graph_type: 'agent_asset_flow'
  project_name: string
  summary: string
  completeness: {
    score: number
    status: 'sufficient' | 'partial' | 'insufficient'
    missing_asset_types: AgentAssetType[]
    missing_questions: MissingQuestion[]
  }
  assets: AgentAssetNode[]
  relationships: AgentAssetEdge[]
}

export type SavedAssetLayout = Record<string, { x: number; y: number }>
