import type { EdgeType, NodeCategory, NodeType } from './canvas.types'

export const CARD_WIDTH = 180
export const CARD_HEIGHT = 64
export const GRID_SIZE = 10
export const MIN_SCALE = 0.25
export const MAX_SCALE = 2.5

export const NODE_CATEGORIES: Record<NodeCategory, { label: string; color: string }> = {
  actor: { label: '参与者', color: '#4A90D9' },
  agent: { label: 'Agent 系统', color: '#34C759' },
  tool: { label: '工具与连接', color: '#00B7C3' },
  data: { label: '数据与知识', color: '#FF9500' },
  aux: { label: '辅助', color: '#8E8E93' },
}

export interface NodeTypeInfo {
  type: NodeType
  label: string
  english: string
  category: NodeCategory
  color: string
  batch: 1 | 2
}

export const NODE_TYPES: NodeTypeInfo[] = [
  { type: 'user', label: '用户', english: 'User', category: 'actor', color: '#4A90D9', batch: 1 },
  { type: 'human_approval', label: '人工审批', english: 'Human Approval', category: 'actor', color: '#14B8A6', batch: 2 },
  { type: 'agent', label: '智能体', english: 'AI Agent', category: 'agent', color: '#34C759', batch: 1 },
  { type: 'orchestrator', label: '编排器', english: 'Orchestrator', category: 'agent', color: '#8B5CF6', batch: 1 },
  { type: 'workflow', label: '工作流', english: 'Workflow', category: 'agent', color: '#A78BFA', batch: 2 },
  { type: 'llm', label: '模型', english: 'LLM', category: 'agent', color: '#6366F1', batch: 1 },
  { type: 'mcp_server', label: 'MCP 服务', english: 'MCP Server', category: 'tool', color: '#00B7C3', batch: 1 },
  { type: 'tool', label: '工具', english: 'Tool', category: 'tool', color: '#2DD4BF', batch: 1 },
  { type: 'external_system', label: '外部系统', english: 'External System', category: 'tool', color: '#0EA5E9', batch: 1 },
  { type: 'knowledge_base', label: '知识库', english: 'Knowledge Base', category: 'data', color: '#F59E0B', batch: 1 },
  { type: 'database', label: '数据库', english: 'Database', category: 'data', color: '#0D9488', batch: 1 },
  { type: 'note', label: '注释', english: 'Note', category: 'aux', color: '#8E8E93', batch: 2 },
]

export const EDGE_TYPES: Array<{ type: EdgeType; label: string; description: string }> = [
  { type: 'call', label: '调用 Call', description: 'Agent → Tool / LLM / MCP' },
  { type: 'data_flow', label: '数据流 Data Flow', description: '数据传递，标注数据名' },
  { type: 'message', label: '消息 / A2A', description: 'Agent ↔ Agent 消息' },
  { type: 'loop', label: '循环 Loop', description: '推理循环回线' },
]

export const EDGE_TYPE_OPTIONS = EDGE_TYPES.map((item) => ({ label: item.label, value: item.type }))

export const EDGE_COLORS: Record<EdgeType, string> = {
  call: '#64748B',
  data_flow: '#F59E0B',
  message: '#8B5CF6',
  loop: '#22C55E',
}
