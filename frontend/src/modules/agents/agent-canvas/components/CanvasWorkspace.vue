<template>
  <div class="canvas-workspace">
    <div class="canvas-toolbar">
      <div class="canvas-toolbar__brand">
        <span class="canvas-toolbar__logo" />
        <span class="canvas-toolbar__title">AI Agent 无限画布</span>
        <span class="canvas-toolbar__divider" />
        <span class="canvas-toolbar__subtitle">基础组件库</span>
      </div>

      <div class="canvas-toolbar__tools">
        <button
          type="button"
          class="canvas-tool-btn"
          :class="{ active: toolMode === 'select' }"
          title="选择"
          @click="toolMode = 'select'"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 4l6.5 14 2-6.5L19 9.5z" />
          </svg>
        </button>
        <button
          type="button"
          class="canvas-tool-btn"
          :class="{ active: toolMode === 'hand' }"
          title="抓手"
          @click="toolMode = 'hand'"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8 12V5a1.5 1.5 0 0 1 3 0v6M11 11V4a1.5 1.5 0 0 1 3 0v7M14 11V6a1.5 1.5 0 0 1 3 0v7" />
            <path d="M8 11V8.5a1.5 1.5 0 0 1 3 0" />
            <path d="M8 13.5 5.6 11.2a1.6 1.6 0 0 0-2.3 2.3l4 4.1A6 6 0 0 0 11.5 20h2.8a6 6 0 0 0 5.1-2.8l1.8-3a1.7 1.7 0 0 0-3-1.7L17 14.5" />
          </svg>
        </button>
      </div>

      <div class="canvas-toolbar__actions">
        <n-button size="small" secondary round @click="loadSample">加载示例</n-button>
        <n-button size="small" secondary round :loading="saving" @click="saveCanvas">保存</n-button>
        <n-button size="small" secondary round @click="exportPng">导出 PNG</n-button>
        <n-button size="small" secondary round :disabled="!selectedId" @click="deleteSelected">删除</n-button>
      </div>

      <div class="canvas-toolbar__zoom">
        <button type="button" class="canvas-tool-btn" title="缩小" @click="zoomBy(-0.1)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M6 12h12" />
          </svg>
        </button>
        <span class="canvas-zoom-label">{{ Math.round(viewport.scale * 100) }}%</span>
        <button type="button" class="canvas-tool-btn" title="放大" @click="zoomBy(0.1)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M12 6v12M6 12h12" />
          </svg>
        </button>
        <button type="button" class="canvas-tool-btn" title="适应画布" @click="fitView">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" />
          </svg>
        </button>
      </div>
    </div>

    <div class="canvas-body">
      <button
        type="button"
        class="canvas-palette-toggle"
        :class="{ active: !paletteCollapsed }"
        title="组件库"
        @click="paletteCollapsed = !paletteCollapsed"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 6l6 6-6 6" />
        </svg>
      </button>
      <aside class="canvas-palette" :class="{ collapsed: paletteCollapsed }">
        <div class="canvas-palette__head">
          <span class="canvas-palette__title">Component Library</span>
          <button type="button" class="canvas-palette__collapse" title="折叠组件库" @click="paletteCollapsed = true">‹</button>
        </div>
        <div class="canvas-palette__search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
            <circle cx="11" cy="11" r="6" />
            <path d="M20 20l-3.5-3.5" />
          </svg>
          <input v-model="searchQuery" type="text" placeholder="Search components..." />
        </div>
        <div class="canvas-palette__list">
          <button
            v-for="item in filteredTypes"
            :key="item.type"
            type="button"
            class="canvas-palette__item"
            draggable="true"
            @dragstart="onPaletteDragStart($event, item.type)"
            @click="addNode(item.type)"
          >
            <span class="canvas-palette__index">{{ numberedIndex(item.type) }}</span>
            <span class="canvas-palette__swatch" :style="{ background: item.color }">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="#fff"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
                v-html="NODE_ICON_MARKUP[item.type]"
              />
            </span>
            <span class="canvas-palette__copy">
              <strong>{{ item.english }}</strong>
              <small>{{ item.label }}</small>
            </span>
            <span class="canvas-palette__drag">⠿</span>
          </button>
          <div v-if="!filteredTypes.length" class="canvas-palette__empty">没有匹配的组件</div>
        </div>
      </aside>

      <div
        ref="canvasShellRef"
        class="canvas-stage"
        :class="{ 'canvas-stage--drag-over': dragOver }"
        @dragenter.prevent="dragDepth += 1"
        @dragover.prevent
        @dragleave.prevent="dragDepth = Math.max(0, dragDepth - 1)"
        @drop.prevent="onDrop"
      >
        <svg
          ref="svgRef"
          class="canvas-svg"
          :class="{ 'canvas-svg--hand': toolMode === 'hand' }"
          @wheel.prevent="onWheel"
          @contextmenu.prevent="onContextMenu"
          @pointerdown="onStagePointerDown"
          @pointermove="onStagePointerMove"
          @pointerup="onStagePointerUp"
          @pointercancel="onStagePointerUp"
          @pointerleave="onStagePointerUp"
        >
          <defs>
            <pattern id="canvas-dot-grid" width="22" height="22" patternUnits="userSpaceOnUse">
              <circle cx="1.2" cy="1.2" r="1.2" class="canvas-grid-dot" />
            </pattern>
            <marker id="arrow-call" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748B" />
            </marker>
            <marker id="arrow-data_flow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#F59E0B" />
            </marker>
            <marker id="arrow-message" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#8B5CF6" />
            </marker>
            <marker id="arrow-loop" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#22C55E" />
            </marker>
          </defs>
          <g :transform="`translate(${viewport.panX} ${viewport.panY}) scale(${viewport.scale})`" style="will-change: transform">
            <rect
              :x="gridBounds.x"
              :y="gridBounds.y"
              :width="gridBounds.w"
              :height="gridBounds.h"
              fill="url(#canvas-dot-grid)"
            />

            <g v-for="edge in edges" :key="edge.id">
              <path
                :d="edgePath(edge)"
                class="canvas-edge"
                :class="[`canvas-edge--${edge.type}`, { selected: selectedId === edge.id }]"
                :stroke="EDGE_COLORS[edge.type]"
                :marker-end="`url(#arrow-${edge.type})`"
                @click.stop="select(edge.id, 'edge')"
              />
              <g
                v-if="edge.label"
                :transform="`translate(${edgeMidpoint(edge).x} ${edgeMidpoint(edge).y})`"
                class="canvas-edge-label"
              >
                <rect x="-52" y="-11" width="104" height="22" rx="6" class="canvas-edge-label__bg" />
                <text text-anchor="middle" dominant-baseline="middle" class="canvas-edge-label__text">{{ edge.label }}</text>
              </g>
            </g>

            <g
              v-for="node in nodes"
              :key="node.id"
              :transform="`translate(${node.x} ${node.y})`"
              :data-node-id="node.id"
              class="canvas-node"
              :class="{ selected: selectedId === node.id }"
              @pointerdown.stop="startNodeDrag($event, node)"
              @pointerenter="hoveredNodeId = node.id"
              @pointerleave="hoveredNodeId = null"
              @click.stop="select(node.id, 'node')"
            >
              <rect x="-90" y="-32" width="180" height="64" rx="12" class="canvas-node__card" />
              <rect x="-90" y="-32" width="180" height="64" rx="12" :fill="nodeColor(node.type)" class="canvas-node__tint" />
              <rect x="-80" y="-22" width="32" height="32" rx="9" :fill="nodeColor(node.type)" class="canvas-node__icon" />
              <rect x="-80" y="-22" width="32" height="32" rx="9" class="canvas-node__icon-ring" />
              <g
                transform="translate(-76 -18)"
                stroke="#fff"
                fill="none"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                v-html="NODE_ICON_MARKUP[node.type]"
              />
              <text x="-36" y="-5" class="canvas-node__label">{{ node.label || nodeEnglish(node.type) }}</text>
              <text x="-36" y="13" class="canvas-node__subtitle">{{ nodeChinese(node.type) }}</text>
              <g v-if="selectedId === node.id" class="canvas-node__handles">
                <rect x="-95" y="-37" width="9" height="9" rx="2" class="canvas-node__handle" />
                <rect x="86" y="-37" width="9" height="9" rx="2" class="canvas-node__handle" />
                <rect x="-95" y="28" width="9" height="9" rx="2" class="canvas-node__handle" />
                <rect x="86" y="28" width="9" height="9" rx="2" class="canvas-node__handle" />
              </g>
              <g v-for="port in PORTS" :key="port" class="canvas-port" :class="{ visible: hoveredNodeId === node.id || selectedId === node.id }">
                <circle
                  :cx="portLocalX(port)"
                  :cy="portLocalY(port)"
                  r="4"
                  class="canvas-port__dot"
                  :style="{ stroke: nodeColor(node.type) }"
                  @pointerdown.stop="startPortDrag($event, node, port)"
                  @click.stop
                />
              </g>
            </g>

            <path v-if="tempEdge" :d="tempEdgePath" class="canvas-edge canvas-edge--temp" />
            <path v-if="tempTarget" :d="tempTargetPath" class="canvas-edge canvas-edge--target-hint" />
          </g>
        </svg>

        <div class="canvas-status">
          <span>节点 {{ nodes.length }}</span>
          <span>连线 {{ edges.length }}</span>
          <span>缩放 {{ Math.round(viewport.scale * 100) }}%</span>
        </div>

        <div
          v-if="contextMenu.visible"
          class="canvas-context-menu"
          :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
          @pointerdown.stop
          @contextmenu.prevent
        >
          <div v-if="contextMenu.nodeId" class="canvas-context-menu__delete" @click="deleteFromContextMenu">
            删除节点
          </div>
          <div v-if="contextMenu.nodeId" class="canvas-context-menu__divider" />
          <div class="canvas-context-menu__title">创建节点</div>
          <button
            v-for="item in NODE_TYPES"
            :key="item.type"
            type="button"
            class="canvas-context-menu__item"
            @click="createNodeFromMenu(item.type)"
          >
            <span class="canvas-context-menu__swatch" :style="{ background: item.color }">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="#fff"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
                v-html="NODE_ICON_MARKUP[item.type]"
              />
            </span>
            <span>{{ item.english }} · {{ item.label }}</span>
          </button>
        </div>
      </div>

      <aside class="canvas-props" :class="{ collapsed: propsCollapsed }">
        <div class="canvas-props__head">
          <span class="canvas-props__title">Properties</span>
          <button type="button" class="canvas-props__close" title="关闭属性面板" @click="closeProps">×</button>
        </div>

        <template v-if="selectedNode">
          <div class="canvas-props__summary">
            <span class="canvas-props__summary-icon" :style="{ background: nodeColor(selectedNode.type) }">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="#fff"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
                v-html="NODE_ICON_MARKUP[selectedNode.type]"
              />
            </span>
            <strong>{{ selectedNode.label || nodeEnglish(selectedNode.type) }}</strong>
            <span class="canvas-props__selected-badge">Selected</span>
          </div>

          <div class="canvas-props__section-title">General</div>
          <div class="canvas-props__field">
            <label>Name</label>
            <n-input v-model:value="selectedNode.label" size="small" placeholder="节点名称" />
          </div>
          <div class="canvas-props__field">
            <label>Type</label>
            <n-select v-model:value="selectedNode.type" size="small" :options="nodeTypeOptions" />
          </div>
          <div class="canvas-props__field">
            <label>Description</label>
            <n-input
              v-model:value="selectedNode.description"
              type="textarea"
              size="small"
              show-count
              :maxlength="500"
              :autosize="{ minRows: 3, maxRows: 6 }"
              placeholder="节点说明"
            />
          </div>

          <div class="canvas-props__section-title">Connections</div>
          <div class="canvas-props__connections">
            <div v-for="row in connectionSummary" :key="row.label" class="canvas-props__connection-row">
              <span class="canvas-props__dot" :style="{ background: row.color }" />
              <span>{{ row.label }}</span>
              <b>{{ row.count }}</b>
            </div>
            <div v-if="!connectionSummary.length" class="canvas-props__connection-empty">暂无连线</div>
          </div>

          <div class="canvas-props__section-title">Tags</div>
          <div class="canvas-props__tags">
            <span v-for="(tag, index) in nodeTags(selectedNode)" :key="tag" class="canvas-props__tag">
              {{ tag }}
              <button type="button" @click="removeTag(index)">×</button>
            </span>
            <span class="canvas-props__tag-add">
              <input v-model="tagInput" type="text" placeholder="+" @keydown.enter.prevent="addTag" @blur="addTag" />
            </span>
          </div>

          <div class="canvas-props__section-title">Settings</div>
          <div class="canvas-props__field">
            <label>位置</label>
            <div class="canvas-props__position">
              <span>x: {{ Math.round(selectedNode.x) }}</span>
              <span>y: {{ Math.round(selectedNode.y) }}</span>
            </div>
          </div>
          <n-button size="small" type="error" secondary round block @click="deleteSelected">删除节点</n-button>
        </template>

        <template v-else-if="selectedEdge">
          <div class="canvas-props__summary">
            <strong>Connection</strong>
            <span class="canvas-props__selected-badge">Selected</span>
          </div>
          <div class="canvas-props__section-title">General</div>
          <div class="canvas-props__field">
            <label>Type</label>
            <n-select v-model:value="selectedEdge.type" size="small" :options="EDGE_TYPE_OPTIONS" />
          </div>
          <div class="canvas-props__field">
            <label>标签（数据名 / 协议）</label>
            <n-input v-model:value="selectedEdge.label" size="small" placeholder="如：MCP / A2A / 检索结果" />
          </div>
          <div class="canvas-props__field">
            <label>连接</label>
            <div class="canvas-props__position">
              <span>{{ nodeById(selectedEdge.source)?.label || selectedEdge.source }}</span>
              <span>→</span>
              <span>{{ nodeById(selectedEdge.target)?.label || selectedEdge.target }}</span>
            </div>
          </div>
          <n-button size="small" type="error" secondary round block @click="deleteSelected">删除连线</n-button>
        </template>

        <div v-else class="canvas-props__empty">
          <div class="canvas-props__empty-icon">✦</div>
          <p>点击节点或连线查看并编辑属性</p>
          <small>拖拽端口可创建连线 · 滚轮缩放 · 空白拖拽平移</small>
        </div>
      </aside>

      <button
        type="button"
        class="canvas-props-toggle"
        :class="{ active: !propsCollapsed }"
        title="属性面板"
        @click="toggleProps"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M15 6l-6 6 6 6" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useMessage } from 'naive-ui'
import { agentSecurityReviewApi, type ReviewProject } from '../../../../api/agentSecurityReview'
import { NODE_ICON_MARKUP } from '../canvas.icons'
import {
  CARD_HEIGHT,
  CARD_WIDTH,
  EDGE_COLORS,
  EDGE_TYPE_OPTIONS,
  EDGE_TYPES,
  GRID_SIZE,
  MAX_SCALE,
  MIN_SCALE,
  NODE_TYPES,
} from '../canvas.config'
import type { CanvasDiagram, CanvasEdge, CanvasNode, NodeType, Port } from '../canvas.types'

const props = defineProps<{ project: ReviewProject | null }>()
const message = useMessage()

const PORTS: Port[] = ['top', 'right', 'bottom', 'left']

const nodes = ref<CanvasNode[]>([])
const edges = ref<CanvasEdge[]>([])
const viewport = reactive({ panX: 0, panY: 0, scale: 1 })
const selectedId = ref<string | null>(null)
const selectedKind = ref<'node' | 'edge' | null>(null)
const hoveredNodeId = ref<string | null>(null)
const saving = ref(false)
const toolMode = ref<'select' | 'hand'>('select')
const searchQuery = ref('')
const tagInput = ref('')
const shellSize = reactive({ w: 800, h: 500 })
const paletteCollapsed = ref(true)
const propsCollapsed = ref(true)
const dragDepth = ref(0)
const contextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  worldX: 0,
  worldY: 0,
  nodeId: null as string | null,
})

const canvasShellRef = ref<HTMLDivElement | null>(null)
const svgRef = ref<SVGSVGElement | null>(null)

type Interaction = 'none' | 'pan' | 'node-drag' | 'edge-drag'
const interaction = ref<Interaction>('none')
const panStart = reactive({ x: 0, y: 0, panX: 0, panY: 0 })
const nodeDrag = reactive<{ id: string; startX: number; startY: number; nodeX: number; nodeY: number }>({
  id: '',
  startX: 0,
  startY: 0,
  nodeX: 0,
  nodeY: 0,
})
const edgeDrag = reactive<{ sourceId: string; sourcePort: Port; tx: number; ty: number }>({
  sourceId: '',
  sourcePort: 'right',
  tx: 0,
  ty: 0,
})
const tempTarget = ref<{ nodeId: string; port: Port | null } | null>(null)

const nodesById = computed(() => new Map(nodes.value.map((node) => [node.id, node])))
const selectedNode = computed(() => (selectedKind.value === 'node' ? nodesById.value.get(selectedId.value || '') || null : null))
const selectedEdge = computed(() => (selectedKind.value === 'edge' ? edges.value.find((edge) => edge.id === selectedId.value) || null : null))
const dragOver = computed(() => dragDepth.value > 0)
const gridBounds = computed(() => {
  return {
    x: -viewport.panX / viewport.scale,
    y: -viewport.panY / viewport.scale,
    w: shellSize.w / viewport.scale,
    h: shellSize.h / viewport.scale,
  }
})
const tempEdge = computed(() => (interaction.value === 'edge-drag' ? edgeDrag : null))
const tempEdgePath = computed(() => {
  if (interaction.value !== 'edge-drag') return ''
  const source = nodesById.value.get(edgeDrag.sourceId)
  if (!source) return ''
  return bezierPath(portX(edgeDrag.sourcePort, source), portY(edgeDrag.sourcePort, source), edgeDrag.tx, edgeDrag.ty)
})
const tempTargetPath = computed(() => {
  if (!tempTarget.value) return ''
  const node = nodesById.value.get(tempTarget.value.nodeId)
  if (!node) return ''
  const source = nodesById.value.get(edgeDrag.sourceId)
  const sx = source ? portX(edgeDrag.sourcePort, source) : edgeDrag.tx
  const sy = source ? portY(edgeDrag.sourcePort, source) : edgeDrag.ty
  if (tempTarget.value.port) {
    return bezierPath(sx, sy, portX(tempTarget.value.port, node), portY(tempTarget.value.port, node))
  }
  const point = boundaryPoint(sx, sy, node)
  return bezierPath(sx, sy, point.x, point.y)
})

const filteredTypes = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return NODE_TYPES
  return NODE_TYPES.filter(
    (item) => item.english.toLowerCase().includes(query) || item.label.toLowerCase().includes(query),
  )
})
const nodeTypeOptions = NODE_TYPES.map((item) => ({ label: `${item.english} · ${item.label}`, value: item.type }))
const connectionSummary = computed(() => {
  const nodeId = selectedId.value
  if (!nodeId) return []
  const counts = new Map<string, { outgoing: number; incoming: number; self: number }>()
  EDGE_TYPES.forEach((item) => counts.set(item.type, { outgoing: 0, incoming: 0, self: 0 }))
  edges.value.forEach((edge) => {
    const item = counts.get(edge.type)
    if (!item) return
    if (edge.source === nodeId && edge.target === nodeId) item.self += 1
    else if (edge.source === nodeId) item.outgoing += 1
    else if (edge.target === nodeId) item.incoming += 1
  })
  return EDGE_TYPES.filter((item) => {
    const countsForType = counts.get(item.type)!
    return countsForType.outgoing + countsForType.incoming + countsForType.self > 0
  }).map((item) => {
    const countsForType = counts.get(item.type)!
    const parts: string[] = []
    if (countsForType.outgoing) parts.push(`${countsForType.outgoing} outgoing`)
    if (countsForType.incoming) parts.push(`${countsForType.incoming} incoming`)
    if (countsForType.self) parts.push(`${countsForType.self} self`)
    return { label: `${item.label} (${parts.join(', ')})`, count: countsForType.outgoing + countsForType.incoming + countsForType.self, color: EDGE_COLORS[item.type] }
  })
})

function numberedIndex(type: NodeType) {
  return NODE_TYPES.findIndex((item) => item.type === type) + 1
}
function nodeColor(type: NodeType) {
  return NODE_TYPES.find((item) => item.type === type)?.color || '#8E8E93'
}
function nodeEnglish(type: NodeType) {
  return NODE_TYPES.find((item) => item.type === type)?.english || type
}
function nodeChinese(type: NodeType) {
  return NODE_TYPES.find((item) => item.type === type)?.label || type
}
function nodeById(id: string) {
  return nodesById.value.get(id) || null
}
function nodeTags(node: CanvasNode) {
  if (!node.tags) node.tags = []
  return node.tags
}

function portX(port: Port, node: CanvasNode) {
  if (port === 'left') return node.x - CARD_WIDTH / 2
  if (port === 'right') return node.x + CARD_WIDTH / 2
  return node.x
}
function portY(port: Port, node: CanvasNode) {
  if (port === 'top') return node.y - CARD_HEIGHT / 2
  if (port === 'bottom') return node.y + CARD_HEIGHT / 2
  return node.y
}
function portLocalX(port: Port) {
  if (port === 'left') return -CARD_WIDTH / 2
  if (port === 'right') return CARD_WIDTH / 2
  return 0
}
function portLocalY(port: Port) {
  if (port === 'top') return -CARD_HEIGHT / 2
  if (port === 'bottom') return CARD_HEIGHT / 2
  return 0
}

function bezierPath(sx: number, sy: number, tx: number, ty: number) {
  const dx = tx - sx
  const dy = ty - sy
  if (Math.abs(dx) >= Math.abs(dy)) {
    const bend = Math.max(36, Math.abs(dx) * 0.48)
    return `M ${sx} ${sy} C ${sx + bend} ${sy}, ${tx - bend} ${ty}, ${tx} ${ty}`
  }
  const bend = Math.max(36, Math.abs(dy) * 0.48)
  return `M ${sx} ${sy} C ${sx} ${sy + bend}, ${tx} ${ty - bend}, ${tx} ${ty}`
}

function edgePath(edge: CanvasEdge) {
  const source = nodesById.value.get(edge.source)
  const target = nodesById.value.get(edge.target)
  if (!source || !target) return ''
  if (edge.source === edge.target) {
    const r = 36
    return `M ${source.x} ${source.y - CARD_HEIGHT / 2} C ${source.x + r * 2} ${source.y - CARD_HEIGHT / 2 - r}, ${source.x + r * 2} ${source.y + CARD_HEIGHT / 2 + r}, ${source.x} ${source.y + CARD_HEIGHT / 2}`
  }
  let sx: number
  let sy: number
  if (edge.sourcePort) {
    sx = portX(edge.sourcePort, source)
    sy = portY(edge.sourcePort, source)
  } else {
    const point = boundaryPoint(target.x, target.y, source)
    sx = point.x
    sy = point.y
  }
  let tx: number
  let ty: number
  if (edge.targetPort) {
    tx = portX(edge.targetPort, target)
    ty = portY(edge.targetPort, target)
  } else {
    const point = boundaryPoint(sx, sy, target)
    tx = point.x
    ty = point.y
  }
  return bezierPath(sx, sy, tx, ty)
}

function edgeMidpoint(edge: CanvasEdge) {
  const source = nodesById.value.get(edge.source)
  const target = nodesById.value.get(edge.target)
  if (!source || !target) return { x: 0, y: 0 }
  return { x: (source.x + target.x) / 2, y: (source.y + target.y) / 2 - 12 }
}

function boundaryPoint(fromX: number, fromY: number, node: CanvasNode) {
  const dx = node.x - fromX
  const dy = node.y - fromY
  const halfW = CARD_WIDTH / 2
  const halfH = CARD_HEIGHT / 2
  if (dx === 0 && dy === 0) return { x: node.x + halfW, y: node.y }
  let t = 1
  if (dx !== 0) t = Math.min(t, 1 - halfW / Math.abs(dx))
  if (dy !== 0) t = Math.min(t, 1 - halfH / Math.abs(dy))
  t = Math.max(t, 0)
  return { x: fromX + dx * t, y: fromY + dy * t }
}

function toWorld(event: MouseEvent) {
  const rect = svgRef.value!.getBoundingClientRect()
  const sx = event.clientX - rect.left
  const sy = event.clientY - rect.top
  return { x: (sx - viewport.panX) / viewport.scale, y: (sy - viewport.panY) / viewport.scale }
}

function select(id: string, kind: 'node' | 'edge') {
  selectedId.value = id
  selectedKind.value = kind
  propsCollapsed.value = false
}
function clearSelection() {
  selectedId.value = null
  selectedKind.value = null
  propsCollapsed.value = true
}
function closeProps() {
  propsCollapsed.value = true
  clearSelection()
}

function toggleProps() {
  if (propsCollapsed.value) {
    propsCollapsed.value = false
  } else {
    closeProps()
  }
}

function closeContextMenu() {
  contextMenu.visible = false
  contextMenu.nodeId = null
}

function onContextMenu(event: MouseEvent) {
  const stage = canvasShellRef.value
  if (!stage) return
  const rect = stage.getBoundingClientRect()
  const world = toWorld(event)
  const target = event.target as Element
  const nodeElement = target.closest('.canvas-node') as SVGGElement | null
  contextMenu.nodeId = nodeElement?.dataset.nodeId || null
  if (contextMenu.nodeId) select(contextMenu.nodeId, 'node')
  contextMenu.worldX = world.x
  contextMenu.worldY = world.y
  contextMenu.x = Math.min(Math.max(0, event.clientX - rect.left), rect.width - 224)
  contextMenu.y = Math.min(Math.max(0, event.clientY - rect.top), rect.height - 320)
  contextMenu.visible = true
}

function createNodeFromMenu(type: NodeType) {
  addNodeAt(type, contextMenu.worldX, contextMenu.worldY)
  closeContextMenu()
}

function deleteFromContextMenu() {
  if (contextMenu.nodeId) {
    selectedId.value = contextMenu.nodeId
    selectedKind.value = 'node'
    deleteSelected()
  }
  closeContextMenu()
}

function addNode(type: NodeType) {
  const shell = canvasShellRef.value
  if (!shell) return
  const count = nodes.value.length
  const centerX = (shell.clientWidth / 2 - viewport.panX) / viewport.scale
  const centerY = (shell.clientHeight / 2 - viewport.panY) / viewport.scale
  addNodeAt(type, centerX + ((count % 6) * 30 - 75), centerY + (Math.floor(count / 6) % 4) * 28 - 42)
}

function addNodeAt(type: NodeType, worldX: number, worldY: number) {
  const node: CanvasNode = {
    id: `node_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    type,
    label: '',
    x: Math.round(worldX / GRID_SIZE) * GRID_SIZE,
    y: Math.round(worldY / GRID_SIZE) * GRID_SIZE,
    description: '',
    tags: [],
  }
  nodes.value.push(node)
  select(node.id, 'node')
}

function onPaletteDragStart(event: DragEvent, type: NodeType) {
  event.dataTransfer?.setData('text/plain', type)
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'copy'
}

function onDrop(event: DragEvent) {
  dragDepth.value = 0
  const type = event.dataTransfer?.getData('text/plain') as NodeType | ''
  if (!type || !NODE_TYPES.some((item) => item.type === type)) return
  const world = toWorld(event)
  addNodeAt(type, world.x, world.y)
}

function startNodeDrag(event: PointerEvent, node: CanvasNode) {
  closeContextMenu()
  if (toolMode.value === 'hand') {
    startPanFromEvent(event)
    return
  }
  event.preventDefault()
  interaction.value = 'node-drag'
  capturePointer(event)
  nodeDrag.id = node.id
  nodeDrag.startX = event.clientX
  nodeDrag.startY = event.clientY
  nodeDrag.nodeX = node.x
  nodeDrag.nodeY = node.y
  select(node.id, 'node')
}

function startPortDrag(event: PointerEvent, node: CanvasNode, port: Port) {
  closeContextMenu()
  if (toolMode.value === 'hand') return
  event.preventDefault()
  interaction.value = 'edge-drag'
  capturePointer(event)
  edgeDrag.sourceId = node.id
  edgeDrag.sourcePort = port
  edgeDrag.tx = node.x
  edgeDrag.ty = node.y
  tempTarget.value = null
}

function capturePointer(event: PointerEvent) {
  const svg = svgRef.value
  if (!svg) return
  try {
    svg.setPointerCapture(event.pointerId)
  } catch {
    // Pointer may already be released; ignore.
  }
}

function startPanFromEvent(event: PointerEvent) {
  event.preventDefault()
  interaction.value = 'pan'
  capturePointer(event)
  panStart.x = event.clientX
  panStart.y = event.clientY
  panStart.panX = viewport.panX
  panStart.panY = viewport.panY
  clearSelection()
}

function findPortAt(clientX: number, clientY: number, excludeId: string) {
  const svg = svgRef.value
  if (!svg) return null
  const rect = svg.getBoundingClientRect()
  const sx = clientX - rect.left
  const sy = clientY - rect.top
  const threshold = 14
  let best: { nodeId: string; port: Port; distance: number } | null = null
  for (const node of nodes.value) {
    if (node.id === excludeId) continue
    for (const port of PORTS) {
      const px = portX(port, node) * viewport.scale + viewport.panX
      const py = portY(port, node) * viewport.scale + viewport.panY
      const dx = px - sx
      const dy = py - sy
      const distance = Math.hypot(dx, dy)
      if (distance <= threshold && (!best || distance < best.distance)) {
        best = { nodeId: node.id, port, distance }
      }
    }
  }
  return best ? { nodeId: best.nodeId, port: best.port } : null
}

function findDropTarget(clientX: number, clientY: number, excludeId: string) {
  const portHit = findPortAt(clientX, clientY, excludeId)
  if (portHit) return { nodeId: portHit.nodeId, port: portHit.port }
  const svg = svgRef.value
  if (!svg) return null
  const rect = svg.getBoundingClientRect()
  const worldX = (clientX - rect.left - viewport.panX) / viewport.scale
  const worldY = (clientY - rect.top - viewport.panY) / viewport.scale
  for (const node of nodes.value) {
    if (node.id === excludeId) continue
    if (Math.abs(worldX - node.x) <= CARD_WIDTH / 2 && Math.abs(worldY - node.y) <= CARD_HEIGHT / 2) {
      return { nodeId: node.id, port: null }
    }
  }
  return null
}

function onStagePointerDown(event: PointerEvent) {
  closeContextMenu()
  if (interaction.value !== 'none' || event.button !== 0) return
  const target = event.target as Element
  if (toolMode.value === 'select' && target.closest('.canvas-node, .canvas-port, .canvas-edge')) return
  startPanFromEvent(event)
}

function onStagePointerMove(event: PointerEvent) {
  if (interaction.value === 'pan') {
    viewport.panX = panStart.panX + (event.clientX - panStart.x)
    viewport.panY = panStart.panY + (event.clientY - panStart.y)
    return
  }
  if (interaction.value === 'node-drag') {
    const node = nodesById.value.get(nodeDrag.id)
    if (!node) return
    const dx = (event.clientX - nodeDrag.startX) / viewport.scale
    const dy = (event.clientY - nodeDrag.startY) / viewport.scale
    node.x = Math.round((nodeDrag.nodeX + dx) / GRID_SIZE) * GRID_SIZE
    node.y = Math.round((nodeDrag.nodeY + dy) / GRID_SIZE) * GRID_SIZE
    return
  }
  if (interaction.value === 'edge-drag') {
    const world = toWorld(event)
    edgeDrag.tx = world.x
    edgeDrag.ty = world.y
    tempTarget.value = findDropTarget(event.clientX, event.clientY, edgeDrag.sourceId)
  }
}

function onStagePointerUp() {
  if (interaction.value === 'edge-drag') {
    if (tempTarget.value) {
      const source = edgeDrag.sourceId
      const target = tempTarget.value
      edges.value.push({
        id: `edge_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
        source,
        target: target.nodeId,
        sourcePort: edgeDrag.sourcePort,
        targetPort: target.port || undefined,
        type: 'call',
        label: '',
      })
    }
    tempTarget.value = null
  }
  interaction.value = 'none'
}

function deleteSelected() {
  if (!selectedId.value) return
  if (selectedKind.value === 'node') {
    const id = selectedId.value
    nodes.value = nodes.value.filter((node) => node.id !== id)
    edges.value = edges.value.filter((edge) => edge.source !== id && edge.target !== id)
  } else if (selectedKind.value === 'edge') {
    edges.value = edges.value.filter((edge) => edge.id !== selectedId.value)
  }
  clearSelection()
}

function addTag() {
  const node = selectedNode.value
  const value = tagInput.value.trim()
  if (!node || !value) {
    tagInput.value = ''
    return
  }
  if (!node.tags) node.tags = []
  if (!node.tags.includes(value)) node.tags.push(value)
  tagInput.value = ''
}
function removeTag(index: number) {
  const node = selectedNode.value
  if (!node?.tags) return
  node.tags.splice(index, 1)
}

function onWheel(event: WheelEvent) {
  closeContextMenu()
  zoomAt(event.deltaY < 0 ? 1.1 : 1 / 1.1, event.clientX, event.clientY)
}
function zoomAt(factor: number, clientX: number, clientY: number) {
  const svg = svgRef.value
  if (!svg) return
  const rect = svg.getBoundingClientRect()
  const sx = clientX - rect.left
  const sy = clientY - rect.top
  const next = Math.min(MAX_SCALE, Math.max(MIN_SCALE, viewport.scale * factor))
  const k = next / viewport.scale
  viewport.panX = sx - (sx - viewport.panX) * k
  viewport.panY = sy - (sy - viewport.panY) * k
  viewport.scale = next
}
function zoomBy(delta: number) {
  const shell = canvasShellRef.value
  if (!shell) return
  const rect = shell.getBoundingClientRect()
  zoomAt(1 + delta, rect.left + rect.width / 2, rect.top + rect.height / 2)
}
function fitView() {
  const shell = canvasShellRef.value
  if (!shell) return
  if (!nodes.value.length) {
    viewport.panX = 0
    viewport.panY = 0
    viewport.scale = 1
    return
  }
  const xs = nodes.value.map((node) => node.x)
  const ys = nodes.value.map((node) => node.y)
  const minX = Math.min(...xs) - CARD_WIDTH / 2 - 30
  const maxX = Math.max(...xs) + CARD_WIDTH / 2 + 30
  const minY = Math.min(...ys) - CARD_HEIGHT / 2 - 30
  const maxY = Math.max(...ys) + CARD_HEIGHT / 2 + 30
  const width = Math.max(maxX - minX, 100)
  const height = Math.max(maxY - minY, 100)
  viewport.scale = Math.min(1.25, Math.max(0.25, Math.min(shell.clientWidth / width, shell.clientHeight / height)))
  viewport.panX = shell.clientWidth / 2 - ((minX + maxX) / 2) * viewport.scale
  viewport.panY = shell.clientHeight / 2 - ((minY + maxY) / 2) * viewport.scale
}

function loadSample() {
  const base: CanvasNode[] = [
    { id: 'n_user', type: 'user', label: 'User', x: 0, y: -300, description: '流程起点，产生输入', tags: [] },
    { id: 'n_agent', type: 'agent', label: 'AI Agent', x: -40, y: -40, description: 'Main AI agent responsible for understanding user intent, planning, reasoning, and orchestrating tools and data sources to accomplish tasks.', tags: ['main', 'active'] },
    { id: 'n_orchestrator', type: 'orchestrator', label: 'Orchestrator', x: -330, y: -180, description: '', tags: [] },
    { id: 'n_workflow', type: 'workflow', label: 'Workflow', x: -340, y: 0, description: '', tags: [] },
    { id: 'n_llm', type: 'llm', label: 'LLM', x: 250, y: -190, description: '', tags: [] },
    { id: 'n_mcp', type: 'mcp_server', label: 'MCP Server', x: 250, y: -40, description: '', tags: [] },
    { id: 'n_tool', type: 'tool', label: 'Tool', x: 460, y: -40, description: '', tags: [] },
    { id: 'n_external', type: 'external_system', label: 'External System', x: 680, y: -40, description: '', tags: [] },
    { id: 'n_db', type: 'database', label: 'Database', x: 680, y: 150, description: '', tags: [] },
    { id: 'n_kb', type: 'knowledge_base', label: 'Knowledge Base', x: -250, y: 150, description: '', tags: [] },
    { id: 'n_human', type: 'human_approval', label: 'Human Approval', x: 250, y: 180, description: '', tags: [] },
    {
      id: 'n_note',
      type: 'note',
      label: 'Note',
      x: 560,
      y: -260,
      description: 'Main agent uses RAG from Knowledge Base, calls tools via MCP Server, and stores results in External System + Database. Loop enables iterative reasoning until completion.',
      tags: [],
    },
  ]
  const sampleEdges: CanvasEdge[] = [
    { id: 'e1', source: 'n_user', target: 'n_agent', type: 'call', label: '' },
    { id: 'e2', source: 'n_orchestrator', target: 'n_workflow', type: 'message', label: 'A2A' },
    { id: 'e3', source: 'n_orchestrator', target: 'n_agent', type: 'message', label: 'A2A' },
    { id: 'e4', source: 'n_workflow', target: 'n_agent', type: 'message', label: 'A2A' },
    { id: 'e5', source: 'n_agent', target: 'n_llm', type: 'loop', label: 'Loop' },
    { id: 'e6', source: 'n_agent', target: 'n_mcp', type: 'call', label: 'MCP' },
    { id: 'e7', source: 'n_mcp', target: 'n_tool', type: 'call', label: '' },
    { id: 'e8', source: 'n_tool', target: 'n_external', type: 'call', label: '' },
    { id: 'e9', source: 'n_external', target: 'n_db', type: 'data_flow', label: 'Store / Sync' },
    { id: 'e10', source: 'n_kb', target: 'n_agent', type: 'data_flow', label: 'RAG / Context' },
    { id: 'e11', source: 'n_agent', target: 'n_human', type: 'message', label: '' },
    { id: 'e12', source: 'n_human', target: 'n_tool', type: 'message', label: '' },
  ]
  nodes.value = base
  edges.value = sampleEdges
  clearSelection()
  fitView()
  message.success('已加载示例架构')
}

async function loadCanvas() {
  if (!props.project) return
  try {
    const canvas = await agentSecurityReviewApi.getCanvas(props.project.projectId)
    const hasNodes = Boolean(canvas.nodes?.length)
    if (hasNodes) {
      nodes.value = canvas.nodes
      edges.value = canvas.edges || []
    } else {
      nodes.value = [
        { id: 'seed_user', type: 'user', label: 'User', x: -190, y: 0, description: '', tags: [] },
        { id: 'seed_agent', type: 'agent', label: 'AI Agent', x: 190, y: 0, description: '', tags: [] },
      ]
      edges.value = [
        {
          id: 'seed_edge',
          source: 'seed_user',
          target: 'seed_agent',
          sourcePort: 'right',
          targetPort: 'left',
          type: 'call',
          label: '',
        },
      ]
    }
    if (canvas.viewport && hasNodes) {
      viewport.panX = canvas.viewport.panX || 0
      viewport.panY = canvas.viewport.panY || 0
      viewport.scale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, canvas.viewport.scale || 1))
    } else {
      fitView()
    }
    clearSelection()
  } catch {
    nodes.value = []
    edges.value = []
    fitView()
  }
}

async function saveCanvas() {
  if (!props.project) return
  saving.value = true
  try {
    const canvas: CanvasDiagram = {
      nodes: nodes.value,
      edges: edges.value,
      viewport: { panX: viewport.panX, panY: viewport.panY, scale: viewport.scale },
    }
    await agentSecurityReviewApi.saveCanvas(props.project.projectId, canvas)
    message.success('画布已保存')
  } catch (err) {
    message.error(err instanceof Error ? err.message : '保存失败')
  } finally {
    saving.value = false
  }
}

function exportPng() {
  const svg = svgRef.value
  if (!svg) return
  const width = svg.clientWidth
  const height = svg.clientHeight
  if (!width || !height) return
  const clone = svg.cloneNode(true) as SVGSVGElement
  clone.setAttribute('width', String(width))
  clone.setAttribute('height', String(height))
  clone.setAttribute('font-family', 'Inter, ui-sans-serif, system-ui, sans-serif')
  const inlineRules: Array<[string, string[]]> = [
    ['.canvas-node__card', ['fill', 'stroke', 'stroke-width']],
    ['.canvas-node__tint', ['fill', 'opacity']],
    ['.canvas-node__icon-ring', ['stroke', 'stroke-width']],
    ['.canvas-node__label', ['fill', 'font-size', 'font-weight']],
    ['.canvas-node__subtitle', ['fill', 'font-size']],
    ['.canvas-node__handle', ['fill', 'stroke']],
    ['.canvas-node__tag-bg', ['fill']],
    ['.canvas-node__tag-text', ['fill', 'font-size']],
    ['.canvas-edge', ['stroke-width']],
    ['.canvas-edge-label__bg', ['fill', 'stroke']],
    ['.canvas-edge-label__text', ['fill', 'font-size']],
    ['.canvas-port__dot', ['fill', 'stroke']],
    ['.canvas-grid-dot', ['fill']],
  ]
  const liveElements = svg
  for (const [selector, props] of inlineRules) {
    const liveMatches = Array.from(liveElements.querySelectorAll(selector))
    const cloneMatches = Array.from(clone.querySelectorAll(selector))
    liveMatches.forEach((element, index) => {
      const target = cloneMatches[index]
      if (!target) return
      const computed = getComputedStyle(element)
      props.forEach((prop) => {
        const value = computed.getPropertyValue(prop)
        if (value) target.setAttribute(prop, value)
      })
    })
  }
  const background = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
  background.setAttribute('width', '100%')
  background.setAttribute('height', '100%')
  background.setAttribute('fill', document.documentElement.dataset.theme === 'dark' ? '#0f172a' : '#f4f8ff')
  clone.insertBefore(background, clone.firstChild)
  const xml = new XMLSerializer().serializeToString(clone)
  const blob = new Blob([xml], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const image = new Image()
  image.onload = () => {
    const canvas = document.createElement('canvas')
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.fillStyle = document.documentElement.dataset.theme === 'dark' ? '#0f172a' : '#f4f8ff'
      ctx.fillRect(0, 0, width, height)
      ctx.drawImage(image, 0, 0)
      const link = document.createElement('a')
      link.href = canvas.toDataURL('image/png')
      link.download = `${props.project?.projectName || 'canvas'}.png`
      link.click()
    }
    URL.revokeObjectURL(url)
  }
  image.src = url
}

function onKeyDown(event: KeyboardEvent) {
  const target = event.target as HTMLElement
  if (target.closest('input, textarea, select, .n-select')) return
  if (event.key === 'Escape') {
    closeContextMenu()
    return
  }
  if (event.key === 'Delete' || event.key === 'Backspace') {
    deleteSelected()
  }
}

function updateShellSize() {
  const shell = canvasShellRef.value
  if (!shell) return
  shellSize.w = shell.clientWidth
  shellSize.h = shell.clientHeight
}

function onWindowResize() {
  updateShellSize()
}

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
  window.addEventListener('resize', onWindowResize)
  updateShellSize()
  void loadCanvas()
})

watch(
  () => props.project?.projectId,
  () => {
    void loadCanvas()
  },
)

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('resize', onWindowResize)
})
</script>

<style>
:root {
  --canvas-stage-bg: rgba(248, 251, 255, 0.8);
  --canvas-grid-dot: rgba(71, 120, 190, 0.2);
  --canvas-card-bg: rgba(255, 255, 255, 0.96);
  --canvas-card-border: rgba(45, 103, 171, 0.18);
  --canvas-text: #142033;
  --canvas-text-2: #40516c;
  --canvas-text-3: #7b8ba3;
  --canvas-panel-bg: rgba(255, 255, 255, 0.74);
  --canvas-panel-border: rgba(45, 103, 171, 0.16);
  --canvas-accent: #4a90d9;
  --canvas-hover: rgba(74, 144, 217, 0.08);
  --canvas-label-bg: rgba(255, 255, 255, 0.92);
}

:root[data-theme='dark'] {
  --canvas-stage-bg: rgba(13, 20, 35, 0.7);
  --canvas-grid-dot: rgba(148, 178, 220, 0.16);
  --canvas-card-bg: #223049;
  --canvas-card-border: rgba(194, 205, 225, 0.24);
  --canvas-text: #f4f7fb;
  --canvas-text-2: #c8d2e3;
  --canvas-text-3: #9faec4;
  --canvas-panel-bg: rgba(28, 41, 63, 0.84);
  --canvas-panel-border: rgba(194, 205, 225, 0.18);
  --canvas-accent: #a78bfa;
  --canvas-hover: rgba(167, 139, 250, 0.12);
  --canvas-label-bg: rgba(34, 48, 73, 0.94);
}

.canvas-workspace {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: calc(100vh - 320px);
  min-height: 420px;
}

.canvas-toolbar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px 12px;
  background: var(--canvas-panel-bg);
  border: 1px solid var(--canvas-panel-border);
  border-radius: 12px;
  backdrop-filter: blur(18px);
}

.canvas-toolbar__brand {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.canvas-toolbar__logo {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  border-radius: 6px;
  background: linear-gradient(135deg, #4a90d9, #8b5cf6);
  clip-path: polygon(50% 0, 100% 100%, 0 100%);
}

.canvas-toolbar__title {
  font-size: 13px;
  font-weight: 700;
  color: var(--canvas-text);
  white-space: nowrap;
}

.canvas-toolbar__divider {
  width: 1px;
  height: 14px;
  background: var(--canvas-panel-border);
}

.canvas-toolbar__subtitle {
  font-size: 12px;
  color: var(--canvas-text-3);
  white-space: nowrap;
}

.canvas-toolbar__tools,
.canvas-toolbar__actions,
.canvas-toolbar__zoom {
  display: flex;
  align-items: center;
  gap: 5px;
}

.canvas-toolbar__actions {
  margin-left: auto;
}

.canvas-tool-btn {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  padding: 0;
  color: var(--canvas-text-2);
  cursor: pointer;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  transition: background 0.14s ease, border-color 0.14s ease, color 0.14s ease;
}

.canvas-tool-btn svg {
  width: 16px;
  height: 16px;
}

.canvas-tool-btn:hover {
  color: var(--canvas-text);
  background: var(--canvas-hover);
}

.canvas-tool-btn.active {
  color: var(--canvas-accent);
  background: var(--canvas-hover);
  border-color: rgba(139, 92, 246, 0.45);
  border-color: color-mix(in srgb, var(--canvas-accent) 45%, transparent);
}

.canvas-zoom-label {
  min-width: 44px;
  text-align: center;
  font-size: 12px;
  color: var(--canvas-text-2);
  font-variant-numeric: tabular-nums;
}

.canvas-body {
  display: flex;
  flex: 1;
  min-height: 0;
  gap: 10px;
}

.canvas-palette {
  width: 226px;
  flex-shrink: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--canvas-panel-bg);
  border: 1px solid var(--canvas-panel-border);
  border-radius: 12px;
  backdrop-filter: blur(18px);
  transition:
    width 0.28s cubic-bezier(0.4, 0, 0.2, 1),
    border-width 0.28s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.2s ease;
}

.canvas-palette.collapsed {
  width: 0;
  border-width: 0;
  opacity: 0;
}

.canvas-palette,
.canvas-props {
  scrollbar-width: thin;
  scrollbar-gutter: stable;
  scrollbar-color: rgba(139, 92, 246, 0.32) transparent;
  scrollbar-color: color-mix(in srgb, var(--canvas-accent) 34%, transparent) transparent;
}

.canvas-palette::-webkit-scrollbar,
.canvas-props::-webkit-scrollbar {
  width: 6px;
}

.canvas-palette::-webkit-scrollbar-track,
.canvas-props::-webkit-scrollbar-track {
  background: transparent;
}

.canvas-palette::-webkit-scrollbar-thumb,
.canvas-props::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(139, 92, 246, 0.3);
  background: color-mix(in srgb, var(--canvas-accent) 32%, transparent);
}

.canvas-palette::-webkit-scrollbar-thumb:hover,
.canvas-props::-webkit-scrollbar-thumb:hover {
  background: rgba(139, 92, 246, 0.45);
  background: color-mix(in srgb, var(--canvas-accent) 48%, transparent);
}

.canvas-palette-toggle {
  display: grid;
  place-items: center;
  width: 28px;
  flex-shrink: 0;
  padding: 0;
  color: var(--canvas-text-3);
  cursor: pointer;
  background: var(--canvas-panel-bg);
  border: 1px solid var(--canvas-panel-border);
  border-radius: 10px;
  backdrop-filter: blur(18px);
  transition: color 0.14s ease, background 0.14s ease;
}

.canvas-palette-toggle svg {
  width: 16px;
  height: 16px;
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}

.canvas-palette-toggle.active svg {
  transform: rotate(180deg);
}

.canvas-palette-toggle:hover {
  color: var(--canvas-accent);
  background: var(--canvas-hover);
}

.canvas-palette__collapse {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  padding: 0;
  font-size: 16px;
  line-height: 1;
  color: var(--canvas-text-3);
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 6px;
}

.canvas-palette__collapse:hover {
  color: var(--canvas-text);
  background: var(--canvas-hover);
}

.canvas-palette__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 12px 8px;
}

.canvas-palette__title {
  font-size: 13px;
  font-weight: 700;
  color: var(--canvas-text);
}

.canvas-palette__dots {
  font-size: 12px;
  color: var(--canvas-text-3);
  letter-spacing: 1px;
}

.canvas-palette__search {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0 12px 10px;
  padding: 7px 9px;
  color: var(--canvas-text-3);
  background: var(--canvas-stage-bg);
  border: 1px solid var(--canvas-panel-border);
  border-radius: 9px;
}

.canvas-palette__search svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.canvas-palette__search input {
  width: 100%;
  min-width: 0;
  padding: 0;
  font-size: 12px;
  color: var(--canvas-text);
  background: transparent;
  border: 0;
  outline: none;
}

.canvas-palette__search input::placeholder {
  color: var(--canvas-text-3);
}

.canvas-palette__list {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px 12px;
}

.canvas-palette__item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  margin: 5px 0;
  padding: 7px 8px;
  text-align: left;
  cursor: pointer;
  color: var(--canvas-text);
  background: var(--canvas-card-bg);
  border: 1px solid var(--canvas-panel-border);
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.06);
  transition: background 0.14s ease, border-color 0.14s ease, transform 0.14s ease;
}

.canvas-palette__item:hover {
  background: var(--canvas-hover);
  border-color: rgba(139, 92, 246, 0.45);
  border-color: color-mix(in srgb, var(--canvas-accent) 45%, transparent);
  transform: translateX(2px);
}

.canvas-palette__index {
  width: 15px;
  flex-shrink: 0;
  font-size: 11px;
  color: var(--canvas-text-3);
  font-variant-numeric: tabular-nums;
}

.canvas-palette__swatch {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  border-radius: 8px;
}

.canvas-palette__swatch svg {
  width: 18px;
  height: 18px;
}

.canvas-palette__copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.canvas-palette__copy strong {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
}

.canvas-palette__copy small {
  overflow: hidden;
  font-size: 10.5px;
  color: var(--canvas-text-3);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.canvas-palette__drag {
  font-size: 13px;
  color: var(--canvas-text-3);
  opacity: 0.7;
}

.canvas-palette__empty {
  padding: 16px 0;
  font-size: 12px;
  text-align: center;
  color: var(--canvas-text-3);
}

.canvas-stage {
  position: relative;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  background: var(--canvas-stage-bg);
  border: 1px solid var(--canvas-panel-border);
  border-radius: 12px;
  backdrop-filter: blur(18px);
}

.canvas-stage--drag-over {
  outline: 2px dashed var(--canvas-accent);
  outline-offset: -2px;
}

.canvas-svg {
  display: block;
  width: 100%;
  height: 100%;
  cursor: grab;
  user-select: none;
  touch-action: none;
}

.canvas-svg:active {
  cursor: grabbing;
}

.canvas-svg--hand {
  cursor: grab;
}

.canvas-grid-dot {
  fill: var(--canvas-grid-dot);
}

.canvas-node {
  cursor: grab;
  filter: drop-shadow(0 2px 5px rgba(15, 23, 42, 0.18));
  transition: filter 0.16s ease;
}

.canvas-node:active {
  cursor: grabbing;
}

.canvas-node.selected {
  filter: drop-shadow(0 2px 5px rgba(15, 23, 42, 0.18)) drop-shadow(0 0 12px rgba(139, 92, 246, 0.3));
}

.canvas-node__card {
  fill: var(--canvas-card-bg);
  stroke: var(--canvas-card-border);
  stroke-width: 1;
  transition: stroke 0.15s ease;
}

.canvas-node:hover .canvas-node__card {
  stroke: rgba(139, 92, 246, 0.45);
  stroke: color-mix(in srgb, var(--canvas-accent) 45%, transparent);
}

.canvas-node.selected .canvas-node__card {
  stroke: var(--canvas-accent);
  stroke-width: 2;
}

.canvas-node__tint {
  opacity: 0.08;
  pointer-events: none;
}

:root[data-theme='dark'] .canvas-node__tint {
  opacity: 0.15;
}

.canvas-node__icon {
  opacity: 1;
}

.canvas-node__icon-ring {
  fill: none;
  stroke: rgba(255, 255, 255, 0.55);
  stroke-width: 1.2;
  pointer-events: none;
}

.canvas-node__label {
  font-size: 13px;
  font-weight: 650;
  fill: var(--canvas-text);
  pointer-events: none;
}

.canvas-node__subtitle {
  font-size: 11px;
  fill: var(--canvas-text-3);
  pointer-events: none;
}

.canvas-node__handle {
  fill: var(--canvas-card-bg);
  stroke: var(--canvas-accent);
  stroke-width: 1.5;
}

.canvas-port {
  pointer-events: none;
}

.canvas-port__dot {
  fill: var(--canvas-card-bg);
  stroke: var(--canvas-text-3);
  stroke-width: 1.5;
  opacity: 0;
  pointer-events: all;
  cursor: crosshair;
  transition: opacity 0.14s ease;
}

.canvas-port.visible .canvas-port__dot {
  opacity: 1;
}

.canvas-port__dot:hover {
  stroke: var(--canvas-accent);
  stroke-width: 2.5;
}

.canvas-edge {
  fill: none;
  stroke-width: 1.8;
  cursor: pointer;
  transition: stroke-width 0.14s ease;
}

.canvas-edge:hover,
.canvas-edge.selected {
  stroke-width: 2.6;
}

.canvas-edge--message {
  stroke-dasharray: 7 5;
}

.canvas-edge--temp {
  stroke: var(--canvas-accent);
  stroke-width: 2;
  stroke-dasharray: 6 4;
  pointer-events: none;
}

.canvas-edge--target-hint {
  stroke: var(--canvas-accent);
  stroke-width: 2.2;
  opacity: 0.55;
  pointer-events: none;
}

.canvas-edge-label {
  pointer-events: none;
}

.canvas-edge-label__bg {
  fill: var(--canvas-label-bg);
  stroke: var(--canvas-panel-border);
  stroke-width: 1;
}

.canvas-edge-label__text {
  font-size: 10px;
  font-weight: 600;
  fill: var(--canvas-text-2);
}

.canvas-status {
  position: absolute;
  right: 12px;
  bottom: 12px;
  display: flex;
  gap: 12px;
  padding: 5px 10px;
  font-size: 11.5px;
  color: var(--canvas-text-2);
  background: var(--canvas-panel-bg);
  border: 1px solid var(--canvas-panel-border);
  border-radius: 999px;
  backdrop-filter: blur(14px);
  pointer-events: none;
}

.canvas-context-menu {
  position: absolute;
  z-index: 20;
  width: 212px;
  max-height: 310px;
  overflow-y: auto;
  padding: 6px;
  background: var(--canvas-panel-bg);
  border: 1px solid var(--canvas-panel-border);
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.22);
  backdrop-filter: blur(20px);
  scrollbar-width: thin;
  scrollbar-color: rgba(139, 92, 246, 0.32) transparent;
}

.canvas-context-menu::-webkit-scrollbar {
  width: 6px;
}

.canvas-context-menu::-webkit-scrollbar-track {
  background: transparent;
}

.canvas-context-menu::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(139, 92, 246, 0.3);
}

.canvas-context-menu__title {
  padding: 6px 8px 4px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--canvas-text-3);
}

.canvas-context-menu__delete {
  padding: 7px 9px;
  font-size: 12px;
  font-weight: 600;
  color: #ef4444;
  cursor: pointer;
  border-radius: 8px;
}

.canvas-context-menu__delete:hover {
  background: rgba(239, 68, 68, 0.1);
}

.canvas-context-menu__divider {
  height: 1px;
  margin: 4px 6px;
  background: var(--canvas-panel-border);
}

.canvas-context-menu__item {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 6px 8px;
  font-size: 12px;
  text-align: left;
  color: var(--canvas-text-2);
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 8px;
}

.canvas-context-menu__item:hover {
  color: var(--canvas-text);
  background: var(--canvas-hover);
}

.canvas-context-menu__swatch {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  border-radius: 6px;
}

.canvas-context-menu__swatch svg {
  width: 14px;
  height: 14px;
}

.canvas-props {
  width: 244px;
  flex-shrink: 0;
  min-width: 0;
  padding: 12px;
  overflow-y: auto;
  background: var(--canvas-panel-bg);
  border: 1px solid var(--canvas-panel-border);
  border-radius: 12px;
  backdrop-filter: blur(18px);
  transition:
    width 0.28s cubic-bezier(0.4, 0, 0.2, 1),
    border-width 0.28s cubic-bezier(0.4, 0, 0.2, 1),
    opacity 0.2s ease;
}

.canvas-props.collapsed {
  width: 0;
  border-width: 0;
  opacity: 0;
  overflow: hidden;
}

.canvas-props-toggle {
  display: grid;
  place-items: center;
  width: 28px;
  flex-shrink: 0;
  padding: 0;
  color: var(--canvas-text-3);
  cursor: pointer;
  background: var(--canvas-panel-bg);
  border: 1px solid var(--canvas-panel-border);
  border-radius: 10px;
  backdrop-filter: blur(18px);
  transition: color 0.14s ease, background 0.14s ease;
}

.canvas-props-toggle svg {
  width: 16px;
  height: 16px;
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}

.canvas-props-toggle.active svg {
  transform: rotate(180deg);
}

.canvas-props-toggle:hover {
  color: var(--canvas-accent);
  background: var(--canvas-hover);
}

.canvas-props__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.canvas-props__title {
  font-size: 13px;
  font-weight: 700;
  color: var(--canvas-text);
}

.canvas-props__close {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  padding: 0;
  font-size: 15px;
  line-height: 1;
  color: var(--canvas-text-3);
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 6px;
}

.canvas-props__close:hover {
  color: var(--canvas-text);
  background: var(--canvas-hover);
}

.canvas-props__summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  margin-bottom: 10px;
  border-bottom: 1px solid var(--canvas-panel-border);
}

.canvas-props__summary strong {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  font-size: 13px;
  font-weight: 700;
  color: var(--canvas-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.canvas-props__summary-icon {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  border-radius: 7px;
}

.canvas-props__summary-icon svg {
  width: 16px;
  height: 16px;
}

.canvas-props__selected-badge {
  padding: 2px 8px;
  font-size: 10px;
  font-weight: 600;
  color: #16a34a;
  background: rgba(34, 197, 94, 0.16);
  border-radius: 999px;
  white-space: nowrap;
}

.canvas-props__section-title {
  margin: 12px 0 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--canvas-text-3);
}

.canvas-props__field {
  margin-bottom: 11px;
}

.canvas-props__field label {
  display: block;
  margin-bottom: 5px;
  font-size: 11px;
  font-weight: 600;
  color: var(--canvas-text-3);
}

.canvas-props__position {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 11.5px;
  color: var(--canvas-text-3);
  font-variant-numeric: tabular-nums;
}

.canvas-props__connections {
  overflow: hidden;
  background: var(--canvas-stage-bg);
  border: 1px solid var(--canvas-panel-border);
  border-radius: 9px;
}

.canvas-props__connection-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 9px;
  font-size: 11.5px;
  color: var(--canvas-text-2);
}

.canvas-props__connection-row + .canvas-props__connection-row {
  border-top: 1px solid var(--canvas-panel-border);
}

.canvas-props__connection-row b {
  margin-left: auto;
  font-size: 11px;
  color: var(--canvas-text-3);
}

.canvas-props__connection-empty {
  padding: 10px;
  font-size: 11.5px;
  text-align: center;
  color: var(--canvas-text-3);
}

.canvas-props__dot {
  width: 8px;
  height: 8px;
  flex-shrink: 0;
  border-radius: 50%;
}

.canvas-props__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.canvas-props__tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--canvas-text-2);
  background: var(--canvas-hover);
  border: 1px solid var(--canvas-panel-border);
  border-radius: 999px;
}

.canvas-props__tag button {
  display: grid;
  place-items: center;
  width: 14px;
  height: 14px;
  padding: 0;
  font-size: 12px;
  line-height: 1;
  color: var(--canvas-text-3);
  cursor: pointer;
  background: transparent;
  border: 0;
}

.canvas-props__tag-add input {
  width: 52px;
  padding: 3px 6px;
  font-size: 11px;
  color: var(--canvas-text);
  background: var(--canvas-stage-bg);
  border: 1px dashed var(--canvas-panel-border);
  border-radius: 999px;
  outline: none;
}

.canvas-props__tag-add input:focus {
  border-color: var(--canvas-accent);
}

.canvas-props__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 100%;
  min-height: 240px;
  text-align: center;
  color: var(--canvas-text-3);
}

.canvas-props__empty-icon {
  font-size: 26px;
  color: var(--canvas-accent);
  opacity: 0.75;
}

.canvas-props__empty p {
  margin: 0;
  font-size: 12.5px;
  color: var(--canvas-text-2);
}

.canvas-props__empty small {
  font-size: 11px;
  line-height: 1.6;
}
</style>
