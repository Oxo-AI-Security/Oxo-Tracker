import type { AgentAssetLayer, SavedAssetLayout } from './assetGraph.types'

const layerOrder: AgentAssetLayer[] = [
  'actor_entry',
  'application',
  'agent_core',
  'ai_knowledge',
  'action_integration',
  'security_governance',
]

export function layoutAssetNodes<T extends { id: string; data?: { layer?: AgentAssetLayer }; position?: { x: number; y: number } }>(
  nodes: T[],
  savedLayout: SavedAssetLayout = {},
  resetLayout = false,
): T[] {
  const buckets = new Map<AgentAssetLayer, T[]>()
  nodes.forEach((node) => {
    const layer = node.data?.layer || 'application'
    buckets.set(layer, [...(buckets.get(layer) || []), node])
  })
  return nodes.map((node) => {
    const saved = !resetLayout ? savedLayout[node.id] : undefined
    if (saved) return { ...node, position: saved }
    const layer = node.data?.layer || 'application'
    const layerIndex = Math.max(0, layerOrder.indexOf(layer))
    const bucket = buckets.get(layer) || []
    const index = bucket.findIndex((item) => item.id === node.id)
    const total = bucket.length
    const yOffset = Math.max(0, 4 - total) * 38
    return {
      ...node,
      position: {
        x: 72 + layerIndex * 330,
        y: 80 + index * 172 + yOffset,
      },
    }
  })
}
