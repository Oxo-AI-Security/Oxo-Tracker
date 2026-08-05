export type NodeType =
  | 'user'
  | 'human_approval'
  | 'agent'
  | 'orchestrator'
  | 'workflow'
  | 'llm'
  | 'mcp_server'
  | 'tool'
  | 'external_system'
  | 'knowledge_base'
  | 'database'
  | 'note'

export type EdgeType = 'call' | 'data_flow' | 'message' | 'loop'

export type NodeCategory = 'actor' | 'agent' | 'tool' | 'data' | 'aux'

export type Port = 'top' | 'right' | 'bottom' | 'left'

export interface CanvasNode {
  id: string
  type: NodeType
  label: string
  x: number
  y: number
  description?: string
  tags?: string[]
}

export interface CanvasEdge {
  id: string
  source: string
  target: string
  sourcePort?: Port
  targetPort?: Port
  type: EdgeType
  label?: string
}

export interface CanvasViewport {
  panX: number
  panY: number
  scale: number
}

export interface CanvasDiagram {
  nodes: CanvasNode[]
  edges: CanvasEdge[]
  viewport?: CanvasViewport
}
