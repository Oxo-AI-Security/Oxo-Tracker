import type { AgentAssetType } from './assetGraph.types'

export const assetNodePalette: Record<AgentAssetType, { label: string; icon: string; className: string }> = {
  actor: { label: 'Actor', icon: 'U', className: 'asset-type-actor' },
  entry_point: { label: 'Entry', icon: 'IN', className: 'asset-type-entry_point' },
  input_data: { label: 'Input Data', icon: 'D', className: 'asset-type-input_data' },
  frontend: { label: 'Frontend', icon: 'UI', className: 'asset-type-frontend' },
  backend: { label: 'Backend', icon: 'API', className: 'asset-type-backend' },
  agent_orchestrator: { label: 'Agent Core', icon: 'A', className: 'asset-type-agent_orchestrator' },
  prompt_instruction: { label: 'Prompt', icon: 'P', className: 'asset-type-prompt_instruction' },
  llm_model: { label: 'LLM', icon: 'M', className: 'asset-type-llm_model' },
  rag_retriever: { label: 'Retriever', icon: 'R', className: 'asset-type-rag_retriever' },
  knowledge_base: { label: 'Knowledge', icon: 'KB', className: 'asset-type-knowledge_base' },
  memory: { label: 'Memory', icon: 'MEM', className: 'asset-type-memory' },
  mcp_server: { label: 'MCP', icon: 'MCP', className: 'asset-type-mcp_server' },
  tool_function: { label: 'Tool', icon: 'T', className: 'asset-type-tool_function' },
  external_system: { label: 'External', icon: 'EXT', className: 'asset-type-external_system' },
  identity_permission: { label: 'Identity', icon: 'ID', className: 'asset-type-identity_permission' },
  security_control: { label: 'Control', icon: 'C', className: 'asset-type-security_control' },
}
