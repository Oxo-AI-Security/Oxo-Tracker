import type { AgentAssetEdgeType } from './assetGraph.types'

export const edgeStyleMap: Record<AgentAssetEdgeType, { label: string; color: string; type: 'smoothstep' | 'straight' | 'bezier'; animated?: boolean; dashed?: boolean }> = {
  input_flow: { label: 'Input', color: '#0ea5e9', type: 'smoothstep' },
  api_call: { label: 'API', color: '#2563eb', type: 'smoothstep' },
  prompt_flow: { label: 'Prompt', color: '#7c3aed', type: 'bezier', animated: true },
  retrieval: { label: 'Retrieval', color: '#d97706', type: 'smoothstep' },
  tool_call: { label: 'Tool Call', color: '#16a34a', type: 'smoothstep', animated: true },
  data_access: { label: 'Data Access', color: '#0891b2', type: 'smoothstep' },
  identity_binding: { label: 'Identity', color: '#64748b', type: 'straight', dashed: true },
  control: { label: 'Control', color: '#dc2626', type: 'straight', dashed: true },
  memory_read_write: { label: 'Memory', color: '#9333ea', type: 'bezier' },
  external_integration: { label: 'External', color: '#ea580c', type: 'smoothstep' },
}
