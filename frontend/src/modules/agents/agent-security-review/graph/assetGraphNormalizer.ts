import { agentAssetTypes, type AgentAssetEdge, type AgentAssetGraph, type AgentAssetLayer, type AgentAssetNode, type AgentAssetStatus, type AgentAssetType } from './assetGraph.types'
import { emptyAssetGraph, isAgentAssetEdgeType, isAgentAssetLayer, isAgentAssetType } from './assetGraph.schema'

const defaultLayerByType: Record<AgentAssetType, AgentAssetLayer> = {
  actor: 'actor_entry',
  entry_point: 'actor_entry',
  input_data: 'actor_entry',
  frontend: 'application',
  backend: 'application',
  agent_orchestrator: 'agent_core',
  prompt_instruction: 'agent_core',
  llm_model: 'ai_knowledge',
  rag_retriever: 'ai_knowledge',
  knowledge_base: 'ai_knowledge',
  memory: 'ai_knowledge',
  mcp_server: 'action_integration',
  tool_function: 'action_integration',
  external_system: 'action_integration',
  identity_permission: 'security_governance',
  security_control: 'security_governance',
}

const defaultNameByType: Record<AgentAssetType, string> = {
  actor: 'Unknown Actor',
  entry_point: 'Unknown Entry Point',
  input_data: 'Unknown Input Data',
  frontend: 'Unknown Frontend',
  backend: 'Unknown Backend',
  agent_orchestrator: 'Unknown Agent Orchestrator',
  prompt_instruction: 'Unknown Prompt Instruction',
  llm_model: 'Unknown LLM Model',
  rag_retriever: 'Unknown RAG Retriever',
  knowledge_base: 'Unknown Knowledge Base',
  memory: 'Unknown Memory',
  mcp_server: 'Unknown MCP Server',
  tool_function: 'Unknown Tool Function',
  external_system: 'Unknown External System',
  identity_permission: 'Unknown Identity / Permission',
  security_control: 'Unknown Security Control',
}

export function normalizeAssetGraph(input: unknown, projectName = 'Agent Security Review'): AgentAssetGraph {
  const raw = typeof input === 'object' && input ? input as Partial<AgentAssetGraph> : emptyAssetGraph(projectName)
  const graph = emptyAssetGraph(projectName)
  graph.version = String(raw.version || '1.0')
  graph.project_name = String(raw.project_name || projectName)
  graph.summary = String(raw.summary || '')
  const seen = new Set<string>()
  const assets: AgentAssetNode[] = []

  for (const item of Array.isArray(raw.assets) ? raw.assets : []) {
    if (!item || typeof item !== 'object') continue
    const asset = item as Partial<AgentAssetNode>
    if (!isAgentAssetType(asset.asset_type)) continue
    const baseId = stableId(asset.id || `${asset.asset_type}-${asset.name || assets.length + 1}`)
    const id = uniqueId(baseId, seen)
    seen.add(id)
    const layer = isAgentAssetLayer(asset.layer) ? asset.layer : defaultLayerByType[asset.asset_type]
    assets.push({
      id,
      name: String(asset.name || defaultNameByType[asset.asset_type]),
      asset_type: asset.asset_type,
      layer,
      status: asset.status === 'present' || asset.status === 'inferred' || asset.status === 'unknown' ? asset.status : 'unknown',
      description: typeof asset.description === 'string' ? asset.description : '',
      owner: typeof asset.owner === 'string' ? asset.owner : '',
      source_evidence: asStringList(asset.source_evidence),
      data_handled: asStringList(asset.data_handled),
      permissions: asStringList(asset.permissions),
      access_mode: asset.access_mode === 'read' || asset.access_mode === 'write' || asset.access_mode === 'read_write' || asset.access_mode === 'execute' || asset.access_mode === 'unknown' ? asset.access_mode : 'unknown',
      risk_hint: asset.risk_hint === 'low' || asset.risk_hint === 'medium' || asset.risk_hint === 'high' || asset.risk_hint === 'unknown' ? asset.risk_hint : 'unknown',
      requires_approval: Boolean(asset.requires_approval),
      metadata: asset.metadata && typeof asset.metadata === 'object' ? asset.metadata : {},
    })
  }

  const presentTypes = new Set(assets.map((asset) => asset.asset_type))
  for (const assetType of agentAssetTypes) {
    if (!presentTypes.has(assetType)) {
      const id = uniqueId(`unknown-${assetType}`, seen)
      seen.add(id)
      assets.push({
        id,
        name: defaultNameByType[assetType],
        asset_type: assetType,
        layer: defaultLayerByType[assetType],
        status: 'unknown',
        description: 'Not found in the uploaded materials. Ask the project owner to confirm.',
        source_evidence: [],
        data_handled: [],
        permissions: [],
        access_mode: 'unknown',
        risk_hint: 'unknown',
        requires_approval: false,
        metadata: {},
      })
    }
  }

  const assetIds = new Set(assets.map((asset) => asset.id))
  graph.assets = assets
  const relationships: AgentAssetEdge[] = (Array.isArray(raw.relationships) ? raw.relationships : [])
    .filter((edge) => edge && typeof edge === 'object')
    .map((edge, index) => {
      const item = edge as Record<string, unknown>
      const status: AgentAssetStatus = item.status === 'present' || item.status === 'inferred' || item.status === 'unknown' ? item.status : 'unknown'
      return {
        id: stableId(item.id || `edge-${index + 1}`),
        source: String(item.source || ''),
        target: String(item.target || ''),
        edge_type: isAgentAssetEdgeType(item.edge_type) ? item.edge_type : 'input_flow',
        label: typeof item.label === 'string' ? item.label : '',
        description: typeof item.description === 'string' ? item.description : '',
        data_flow: asStringList(item.data_flow),
        auth_context: typeof item.auth_context === 'string' ? item.auth_context : '',
        status,
      }
    })
    .filter((edge) => assetIds.has(edge.source) && assetIds.has(edge.target) && edge.source !== edge.target)
  graph.relationships = relationships

  const completeness = raw.completeness || graph.completeness
  graph.completeness = {
    score: clampScore(Number(completeness.score || 0)),
    status: completeness.status === 'sufficient' || completeness.status === 'partial' || completeness.status === 'insufficient' ? completeness.status : 'insufficient',
    missing_asset_types: (Array.isArray(completeness.missing_asset_types) ? completeness.missing_asset_types : []).filter(isAgentAssetType),
    missing_questions: (Array.isArray(completeness.missing_questions) ? completeness.missing_questions : []).filter((item) => item && typeof item === 'object').map((item, index) => {
      const question = item as Record<string, unknown>
      return {
        id: String(question.id || `asset-mq-${index + 1}`),
        asset_type: isAgentAssetType(question.asset_type) ? question.asset_type : 'agent_orchestrator',
        question: String(question.question || ''),
        reason: String(question.reason || ''),
        impact: question.impact === 'low' || question.impact === 'medium' || question.impact === 'high' ? question.impact : 'medium',
      }
    }),
  }
  return graph
}

function asStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean) : []
}

function stableId(value: unknown): string {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'asset'
}

function uniqueId(base: string, seen: Set<string>) {
  if (!seen.has(base)) return base
  let index = 2
  while (seen.has(`${base}-${index}`)) index += 1
  return `${base}-${index}`
}

function clampScore(value: number) {
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Math.min(100, value > 1 ? value : value * 100))
}
