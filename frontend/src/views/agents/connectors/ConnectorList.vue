<template>
  <div class="connector-shell">
    <GlassPanel class="connector-panel connector-directory-panel">
      <div class="section-heading connector-directory-heading">
        <div>
          <p class="eyebrow">Agents / Connector</p>
          <h2>Connector</h2>
          <span>Browse custom connector implementations or built-in system connector types.</span>
        </div>
        <div class="endpoint-heading-actions">
          <n-button secondary round @click="$router.push('/agents')">Back</n-button>
          <n-button type="primary" round @click="$router.push('/agents/connectors/new?connector_type=configurable-app-connector')">
            <template #icon><n-icon><AddOutline /></n-icon></template>
            Configurable App
          </n-button>
        </div>
      </div>

      <div class="connector-directory-toolbar">
        <n-input v-model:value="search" clearable :placeholder="`Search ${visibleConnectors.length} connectors`">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>
        <div class="connector-directory-count">
          <strong>{{ filteredConnectors.length }}</strong>
          <span>connectors</span>
        </div>
      </div>

      <section class="connector-directory-section">
        <div class="connector-directory-section-head">
          <div>
            <p class="eyebrow">{{ viewMode === 'custom' ? 'Custom AI Connectors' : 'System Python Connectors' }}</p>
            <n-button-group class="connector-directory-view-switch">
              <n-button
                round
                :type="viewMode === 'custom' ? 'primary' : 'default'"
                :secondary="viewMode !== 'custom'"
                @click="viewMode = 'custom'"
              >
                Custom Connectors
              </n-button>
              <n-button
                round
                :type="viewMode === 'default' ? 'primary' : 'default'"
                :secondary="viewMode !== 'default'"
                @click="viewMode = 'default'"
              >
                Default Connectors
              </n-button>
            </n-button-group>
          </div>
          <n-tag round :type="viewMode === 'custom' ? 'success' : 'info'">{{ filteredConnectors.length }} types</n-tag>
        </div>

        <div v-if="filteredConnectors.length" class="connector-card-grid">
          <article
            v-for="connector in filteredConnectors"
            :key="connector.id"
            class="connector-type-card"
            :class="{ 'connector-type-card--custom': connector.source === 'user-created' }"
            role="button"
            tabindex="0"
            @click="$router.push(`/agents/connectors/${encodeURIComponent(connector.id)}`)"
            @keydown.enter="$router.push(`/agents/connectors/${encodeURIComponent(connector.id)}`)"
          >
            <div class="connector-card-top">
              <span class="connector-type-mark" :class="{ 'connector-type-mark-user': connector.source === 'user-created' }">
                {{ connector.source === 'user-created' ? 'APP' : initials(connector.name) }}
              </span>
              <n-tag v-if="connector.source === 'user-created'" round type="success">CUSTOM</n-tag>
              <n-tag v-else round :type="protocolTag(connector.protocol)">{{ connector.protocol.toUpperCase() }}</n-tag>
            </div>
            <strong class="connector-card-title">{{ connector.name }}</strong>
            <p>{{ connectorDescription(connector) }}</p>
            <dl>
              <div>
                <dt>Endpoints</dt>
                <dd>{{ connector.endpointCount || 0 }}</dd>
              </div>
              <div>
                <dt>Owner</dt>
                <dd>{{ connector.ownerName }}</dd>
              </div>
            </dl>
            <div class="connector-card-foot">
              <small>{{ connector.source === 'user-created' ? 'HTTP / SSE / WebSocket' : sampleUri(connector) }}</small>
            </div>
          </article>
        </div>
        <n-empty v-else :description="viewMode === 'custom' ? 'No custom connectors found' : 'No default connectors found'" />
      </section>
    </GlassPanel>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { AddOutline, SearchOutline } from '@vicons/ionicons5'
import GlassPanel from '../../../components/GlassPanel.vue'
import { connectorService } from '../../../services/connectorService'
import type { ConnectorListItem, ConnectorProtocol } from '../../../types/connector'

type ConnectorViewMode = 'custom' | 'default'

const connectors = ref<ConnectorListItem[]>([])
const search = ref('')
const viewMode = ref<ConnectorViewMode>('custom')

const customConnectors = computed(() => connectors.value.filter((connector) => connector.source === 'user-created'))
const defaultConnectors = computed(() => connectors.value.filter((connector) => connector.source !== 'user-created'))
const visibleConnectors = computed(() => viewMode.value === 'custom' ? customConnectors.value : defaultConnectors.value)
const filteredConnectors = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  if (!keyword) return visibleConnectors.value
  return visibleConnectors.value.filter((connector) => [connector.name, connector.description, connector.uri]
    .filter(Boolean)
    .some((value) => String(value).toLowerCase().includes(keyword)))
})

onMounted(loadConnectors)

async function loadConnectors() {
  connectors.value = await connectorService.listConnectors()
}

function protocolTag(protocol: ConnectorProtocol) {
  if (protocol === 'http') return 'info'
  if (protocol === 'sse') return 'warning'
  return 'success'
}

function initials(name: string) {
  return name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
}

function sampleUri(connector: ConnectorListItem) {
  if (!connector.uri || connector.uri === '-') return 'No sample URL'
  return connector.uri
}

function connectorDescription(connector: ConnectorListItem) {
  if (connector.source === 'user-created') {
    return 'Shared connector implementation for self-hosted AI applications using HTTP, SSE, or WebSocket.'
  }
  return connector.description
}
</script>
