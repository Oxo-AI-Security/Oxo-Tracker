import {
  agentAssetEdgeTypes,
  agentAssetLayers,
  agentAssetTypes,
  type AgentAssetEdgeType,
  type AgentAssetGraph,
  type AgentAssetLayer,
  type AgentAssetType,
} from './assetGraph.types'

export const assetTypeSet = new Set<string>(agentAssetTypes)
export const assetLayerSet = new Set<string>(agentAssetLayers)
export const edgeTypeSet = new Set<string>(agentAssetEdgeTypes)

export function isAgentAssetType(value: unknown): value is AgentAssetType {
  return assetTypeSet.has(String(value))
}

export function isAgentAssetLayer(value: unknown): value is AgentAssetLayer {
  return assetLayerSet.has(String(value))
}

export function isAgentAssetEdgeType(value: unknown): value is AgentAssetEdgeType {
  return edgeTypeSet.has(String(value))
}

export function emptyAssetGraph(projectName = 'Agent Security Review'): AgentAssetGraph {
  return {
    version: '1.0',
    graph_type: 'agent_asset_flow',
    project_name: projectName,
    summary: '',
    completeness: {
      score: 0,
      status: 'insufficient',
      missing_asset_types: [...agentAssetTypes],
      missing_questions: [],
    },
    assets: [],
    relationships: [],
  }
}
