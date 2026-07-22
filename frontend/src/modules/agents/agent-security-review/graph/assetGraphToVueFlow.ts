import { MarkerType, Position, type Edge, type Node } from '@vue-flow/core'
import type { AgentAssetGraph, SavedAssetLayout } from './assetGraph.types'
import { edgeStyleMap } from './assetEdgeStyles'
import { assetNodePalette } from './assetNodeStyles'

export function assetGraphToVueFlow(graph: AgentAssetGraph, savedLayout: SavedAssetLayout = {}, resetLayout = false): { nodes: Node[]; edges: Edge[] } {
  const connectedIds = new Set<string>()
  graph.relationships.forEach((edge) => {
    connectedIds.add(edge.source)
    connectedIds.add(edge.target)
  })
  const visibleAssets = graph.assets.filter((asset) => asset.status !== 'unknown' || connectedIds.has(asset.id))
  const visibleIds = new Set(visibleAssets.map((asset) => asset.id))
  const visibleRelationships = graph.relationships.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target))

  const layout = workflowLayout(visibleAssets)
  const nodes: Node[] = visibleAssets.map((asset) => {
    const palette = assetNodePalette[asset.asset_type]
    const saved = !resetLayout ? savedLayout[asset.id] : undefined
    const role = workflowRole(asset.asset_type)
    const position = saved || layout.get(asset.id) || { x: 120, y: 160 }
    return {
      id: asset.id,
      type: 'asset',
      targetPosition: role === 'dependency' ? Position.Top : Position.Left,
      sourcePosition: role === 'dependency' ? Position.Top : Position.Right,
      position,
      data: {
        ...asset,
        label: asset.name,
        nodeType: asset.asset_type,
        layer: asset.layer,
        palette,
        workflowRole: role,
        portLabel: portLabel(asset.asset_type),
        subtitle: subtitleForAsset(asset),
      },
    }
  })

  const edges = visibleRelationships.map((edge) => {
    const style = edgeStyleMap[edge.edge_type]
    const isDependency = workflowEdgeIsDependency(edge.edge_type)
    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      sourceHandle: isDependency ? 'bottom' : 'right',
      targetHandle: isDependency ? 'top' : 'left',
      label: edge.label || style.label,
      type: style.type,
      animated: Boolean(style.animated && edge.status !== 'unknown'),
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: style.color,
        width: 18,
        height: 18,
      },
      interactionWidth: 18,
      data: { ...edge, flowType: edge.edge_type },
      style: {
        stroke: style.color,
        strokeWidth: edge.status === 'unknown' ? 1.4 : 2,
        strokeDasharray: style.dashed || edge.status === 'unknown' || isDependency ? '5 6' : undefined,
      },
      labelStyle: { fill: '#cbd5e1', fontSize: 10, fontWeight: 700 },
      labelBgStyle: { fill: 'rgba(24, 24, 27, 0.9)', fillOpacity: 0.9, stroke: 'rgba(148, 163, 184, 0.35)', strokeWidth: 1 },
      labelBgPadding: [6, 4] as [number, number],
      labelBgBorderRadius: 6,
    }
  })

  return { nodes, edges }
}

function workflowLayout(assets: AgentAssetGraph['assets']) {
  const layout = new Map<string, { x: number; y: number }>()
  const groups = {
    entry: assets.filter((asset) => ['actor', 'entry_point', 'input_data', 'frontend'].includes(asset.asset_type)),
    core: assets.filter((asset) => ['agent_orchestrator', 'backend', 'prompt_instruction'].includes(asset.asset_type)),
    route: assets.filter((asset) => ['security_control', 'identity_permission'].includes(asset.asset_type)),
    action: assets.filter((asset) => ['tool_function', 'mcp_server', 'external_system'].includes(asset.asset_type)),
    dependency: assets.filter((asset) => ['llm_model', 'rag_retriever', 'knowledge_base', 'memory'].includes(asset.asset_type)),
  }
  placeColumn(layout, groups.entry, 80, 140, 136)
  placeColumn(layout, groups.core, 390, 118, 132)
  placeColumn(layout, groups.route, 700, 135, 132)
  placeColumn(layout, groups.action, 990, 90, 146)
  placeDependencyArc(layout, groups.dependency, 310, 380, 180)

  assets.forEach((asset, index) => {
    if (!layout.has(asset.id)) {
      layout.set(asset.id, { x: 620 + (index % 3) * 220, y: 420 + Math.floor(index / 3) * 128 })
    }
  })
  return layout
}

function placeColumn(layout: Map<string, { x: number; y: number }>, assets: AgentAssetGraph['assets'], x: number, y: number, gap: number) {
  assets.forEach((asset, index) => {
    layout.set(asset.id, { x, y: y + index * gap })
  })
}

function placeDependencyArc(layout: Map<string, { x: number; y: number }>, assets: AgentAssetGraph['assets'], startX: number, y: number, gap: number) {
  assets.forEach((asset, index) => {
    layout.set(asset.id, { x: startX + index * gap, y: y + (index % 2) * 38 })
  })
}

function workflowRole(assetType: string) {
  if (['llm_model', 'rag_retriever', 'knowledge_base', 'memory'].includes(assetType)) return 'dependency'
  if (['agent_orchestrator', 'backend'].includes(assetType)) return 'agent'
  if (['tool_function', 'mcp_server', 'external_system'].includes(assetType)) return 'action'
  if (['security_control', 'identity_permission'].includes(assetType)) return 'router'
  return 'trigger'
}

function workflowEdgeIsDependency(edgeType: string) {
  return ['prompt_flow', 'retrieval', 'data_access', 'memory_read_write', 'identity_binding', 'control'].includes(edgeType)
}

function portLabel(assetType: string) {
  const labels: Record<string, string> = {
    llm_model: 'Model',
    memory: 'Memory',
    rag_retriever: 'Retriever',
    knowledge_base: 'Knowledge',
    tool_function: 'Tool',
    mcp_server: 'MCP',
    identity_permission: 'Identity',
    security_control: 'Policy',
  }
  return labels[assetType] || ''
}

function subtitleForAsset(asset: AgentAssetGraph['assets'][number]) {
  if (asset.asset_type === 'agent_orchestrator') return 'Tools Agent'
  if (asset.asset_type === 'entry_point') return 'trigger'
  if (asset.asset_type === 'tool_function') return asset.access_mode && asset.access_mode !== 'unknown' ? asset.access_mode : 'function call'
  if (asset.asset_type === 'external_system') return 'external action'
  if (asset.asset_type === 'llm_model') return 'chat model'
  if (asset.asset_type === 'memory') return 'chat memory'
  return asset.status
}
