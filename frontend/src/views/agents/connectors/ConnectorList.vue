<template>
  <div class="connector-shell">
    <GlassPanel class="connector-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Agents / Connector</p>
          <h2>Connector</h2>
          <span>Manage configurable connectors for HTTP, SSE, and WebSocket based AI applications.</span>
        </div>
        <div class="endpoint-heading-actions">
          <n-button secondary round @click="$router.push('/agents')">Back</n-button>
          <n-button type="primary" round @click="$router.push('/agents/connectors/new')">
            <template #icon><n-icon><AddOutline /></n-icon></template>
            New Endpoint
          </n-button>
        </div>
      </div>

      <div class="connector-toolbar">
        <n-input v-model:value="search" clearable placeholder="Search connectors">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>
        <n-select v-model:value="protocolFilter" :options="protocolOptions" />
        <n-select v-model:value="sourceFilter" :options="sourceOptions" />
      </div>

      <n-data-table :columns="columns" :data="filteredConnectors" :bordered="false" />
    </GlassPanel>

    <ConnectorPreviewDrawer v-model:show="previewOpen" :connector="previewConnector" @changed="loadConnectors" />
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { NButton, NDropdown, NSpace, NTag } from 'naive-ui'
import { AddOutline, SearchOutline } from '@vicons/ionicons5'
import { useRouter } from 'vue-router'
import GlassPanel from '../../../components/GlassPanel.vue'
import { connectorService, currentUser } from '../../../services/connectorService'
import type { ConnectorListItem, ConnectorProtocol } from '../../../types/connector'
import ConnectorPreviewDrawer from './ConnectorPreviewDrawer.vue'

const router = useRouter()
const connectors = ref<ConnectorListItem[]>([])
const search = ref('')
const protocolFilter = ref<'all' | ConnectorProtocol>('all')
const sourceFilter = ref<'all' | 'built-in' | 'me' | 'others'>('all')
const previewOpen = ref(false)
const previewConnector = ref<ConnectorListItem | null>(null)

const protocolOptions = [
  { label: 'All protocols', value: 'all' },
  { label: 'HTTP', value: 'http' },
  { label: 'SSE', value: 'sse' },
  { label: 'WebSocket', value: 'websocket' },
]

const sourceOptions = [
  { label: 'All sources', value: 'all' },
  { label: 'Built-in', value: 'built-in' },
  { label: 'Created by me', value: 'me' },
  { label: 'Created by others', value: 'others' },
]

const filteredConnectors = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  return connectors.value.filter((connector) => {
    if (protocolFilter.value !== 'all' && connector.protocol !== protocolFilter.value) return false
    if (sourceFilter.value === 'built-in' && connector.source !== 'built-in') return false
    if (sourceFilter.value === 'me' && connector.ownerId !== currentUser.id) return false
    if (sourceFilter.value === 'others' && (connector.source !== 'user-created' || connector.ownerId === currentUser.id)) return false
    if (!keyword) return true
    return [connector.name, connector.description, connector.uri, connector.ownerName]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(keyword))
  })
})

const columns = [
  { title: 'Connector', key: 'name', minWidth: 240 },
  { title: 'Protocol', key: 'protocol', render: (row: ConnectorListItem) => h(NTag, { round: true, type: protocolTag(row.protocol) }, { default: () => row.protocol.toUpperCase() }) },
  { title: 'Connector Endpoints', key: 'endpointCount', render: (row: ConnectorListItem) => h(NTag, { round: true, type: row.endpointCount ? 'success' : 'default' }, { default: () => `${row.endpointCount || 0}` }) },
  { title: 'Sample Target URL', key: 'uri', ellipsis: { tooltip: true } },
  { title: 'Owner', key: 'ownerName' },
  { title: 'Source', key: 'source', render: (row: ConnectorListItem) => h(NTag, { round: true, type: sourceTag(row) }, { default: () => sourceLabel(row) }) },
  { title: 'Updated At', key: 'updatedAt', render: (row: ConnectorListItem) => new Date(row.updatedAt).toLocaleString() },
  { title: 'Actions', key: 'actions', width: 156, render: renderActions },
]

onMounted(loadConnectors)

async function loadConnectors() {
  connectors.value = await connectorService.listConnectors()
}

function renderActions(row: ConnectorListItem) {
  return h(NSpace, { size: 6, wrap: false, class: 'connector-row-actions' }, {
    default: () => [
      h(NButton, { size: 'small', secondary: true, round: true, onClick: () => preview(row) }, { default: () => 'Manage' }),
      h(NDropdown, {
        trigger: 'click',
        options: [
          { label: 'Add endpoint', key: 'add' },
          { label: 'Duplicate first endpoint', key: 'duplicate' },
        ],
        onSelect: (key: string) => key === 'add' ? addEndpoint(row) : duplicate(row),
      }, {
        default: () => h(NButton, { size: 'small', quaternary: true, round: true }, { default: () => 'More' }),
      }),
    ],
  })
}

function preview(row: ConnectorListItem) {
  previewConnector.value = row
  previewOpen.value = true
}

function addEndpoint(row: ConnectorListItem) {
  router.push(`/agents/connectors/new?connector_type=${encodeURIComponent(row.id)}`)
}

function duplicate(row: ConnectorListItem) {
  window.sessionStorage.setItem('oxo-connector-draft', JSON.stringify(connectorService.duplicateConnector(row)))
  router.push('/agents/connectors/new?duplicate=1')
}

function protocolTag(protocol: ConnectorProtocol) {
  if (protocol === 'http') return 'info'
  if (protocol === 'sse') return 'warning'
  return 'success'
}

function sourceTag(row: ConnectorListItem) {
  if (row.source === 'built-in') return 'info'
  if (row.ownerId === currentUser.id) return 'success'
  return 'default'
}

function sourceLabel(row: ConnectorListItem) {
  if (row.source === 'built-in') return 'built-in'
  return row.ownerId === currentUser.id ? 'created by me' : 'created by others'
}
</script>
