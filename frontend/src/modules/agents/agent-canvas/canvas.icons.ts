import type { NodeType } from './canvas.types'

// 24x24 viewBox 白色 SVG 路径底稿（来自 research/Agent security review.md §5.3.4）
export const NODE_ICON_MARKUP: Record<NodeType, string> = {
  user: '<circle cx="12" cy="7" r="4"/><path d="M4 21c0-5 3.6-9 8-9s8 4 8 9"/>',
  human_approval:
    '<circle cx="8" cy="7" r="3.5"/><path d="M2.5 20c0-3.2 2.5-5.5 5.5-5.5s5.5 2.3 5.5 5.5"/><path d="M16.5 13l2 2 3.5-4.5"/>',
  agent:
    '<rect x="5" y="9" width="14" height="11" rx="3"/><path d="M12 9V6 M12 6l-3-3 M12 6l3-3"/><circle cx="9.5" cy="13.5" r="1"/><circle cx="14.5" cy="13.5" r="1"/><path d="M9 17h6"/>',
  orchestrator:
    '<circle cx="12" cy="12" r="3"/><path d="M12 4v4 M12 16v4 M4 12h4 M16 12h4"/><circle cx="12" cy="4" r="1.5"/><circle cx="12" cy="20" r="1.5"/><circle cx="4" cy="12" r="1.5"/><circle cx="20" cy="12" r="1.5"/>',
  workflow:
    '<circle cx="5" cy="12" r="2.5"/><circle cx="12" cy="5" r="2.5"/><circle cx="12" cy="19" r="2.5"/><circle cx="19" cy="12" r="2.5"/><path d="M7 10.5L10 6.5 M7 13.5L10 17.5 M14 6.5L17 10.5 M14 17.5L17 13.5"/>',
  llm:
    '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M8 5V3 M16 5V3 M8 19v2 M16 19v2"/><circle cx="7" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="17" cy="12" r="1"/>',
  mcp_server:
    '<rect x="4" y="2" width="16" height="20" rx="2"/><circle cx="12" cy="6" r="1.5"/><circle cx="12" cy="10" r="1.5"/><circle cx="12" cy="14" r="1.5"/>',
  tool:
    '<circle cx="12" cy="12" r="4"/><path d="M12 2v3 M12 19v3 M2 12h3 M19 12h3"/><path d="M5.6 5.6l2.1 2.1 M16.3 16.3l2.1 2.1"/><path d="M18.4 5.6l-2.1 2.1 M7.7 16.3l-2.1 2.1"/>',
  external_system:
    '<path d="M7 18h9a4 4 0 0 0 .6-7.9A5.5 5.5 0 0 0 6 9.5 4.5 4.5 0 0 0 7 18z"/>',
  knowledge_base:
    '<path d="M4 4h7l1 1 1-1h7v14H4z"/><path d="M6 2h5l1 1 1-1h5v12H6z"/>',
  database:
    '<ellipse cx="12" cy="6" rx="8" ry="2.5"/><path d="M4 6v12c0 1.4 3.6 2.5 8 2.5s8-1.1 8-2.5V6"/><path d="M4 12c0 1.4 3.6 2.5 8 2.5s8-1.1 8-2.5"/>',
  note: '<path d="M16 3H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h7l5 4V5a2 2 0 0 0-1-2z"/>',
}
