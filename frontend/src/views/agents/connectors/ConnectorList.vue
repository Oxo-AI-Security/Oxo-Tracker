<template>
  <div class="connector-shell">
    <GlassPanel class="connector-panel connector-directory-panel">
      <div class="section-heading connector-directory-heading">
        <div>
          <p class="eyebrow">{{ $t('auto.3ac31bc5b63c') }}</p>
          <h2>{{ $t('auto.ba3583069d93') }}</h2>
          <span>{{ $t('auto.1c67b7a73be9') }}</span>
        </div>
        <div class="endpoint-heading-actions">
          <n-button secondary round @click="$router.push('/agents')">{{ $t('auto.b52b36b7269f') }}</n-button>
          <n-button type="primary" round @click="$router.push('/agents/connectors/new?connector_type=configurable-app-connector')">
            <template #icon><n-icon><AddOutline /></n-icon></template> {{ $t('auto.2358b858ec11') }} </n-button>
        </div>
      </div>

      <div class="connector-directory-toolbar">
        <n-input v-model:value="search" clearable :placeholder="`Search ${visibleItemCount} ${viewMode === 'custom' ? 'endpoints' : 'connectors'}`">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>
        <div class="connector-directory-count">
          <strong>{{ filteredItemCount }}</strong>
          <span>{{ viewMode === 'custom' ? 'endpoints' : 'connectors' }}</span>
        </div>
      </div>

      <section class="connector-directory-section">
        <div class="connector-directory-section-head">
          <div>
            <p class="eyebrow">{{ viewMode === 'custom' ? $t('auto.74e66f7535d7') : $t('auto.ee7a7c31213e') }}</p>
            <n-button-group class="connector-directory-view-switch">
              <n-button
                round
                :type="viewMode === 'custom' ? 'primary' : 'default'"
                :secondary="viewMode !== 'custom'"
                @click="viewMode = 'custom'"
              > {{ $t('auto.7b394771d7ea') }} </n-button>
              <n-button
                round
                :type="viewMode === 'default' ? 'primary' : 'default'"
                :secondary="viewMode !== 'default'"
                @click="viewMode = 'default'"
              > {{ $t('auto.97a6a7160bf1') }} </n-button>
            </n-button-group>
          </div>
          <n-tag round :type="viewMode === 'custom' ? 'success' : 'info'">
            {{ filteredItemCount }} {{ viewMode === 'custom' ? 'endpoints' : 'types' }}
          </n-tag>
        </div>

        <div v-if="viewMode === 'custom' && filteredCustomEndpoints.length" class="connector-card-grid">
          <article
            v-for="{ endpoint, config, aiJob } in filteredCustomEndpoints"
            :key="endpoint.id"
            class="connector-type-card connector-type-card--custom connector-endpoint-card"
            :class="{
              'connector-endpoint-card--ai-running': aiJob?.status === 'running',
              'connector-endpoint-card--ai-ready': aiJob?.status === 'completed' && !aiJob.consumedAt,
            }"
            role="button"
            tabindex="0"
            :aria-label="`Edit ${endpoint.name || endpoint.id}`"
            @click="editCustomEndpoint(endpoint.id)"
            @keydown.enter="editCustomEndpoint(endpoint.id)"
          >
            <div class="connector-card-top">
              <span class="connector-type-mark connector-type-mark-user">
                {{ initials(endpoint.name || endpoint.id) }}
              </span>
              <n-tag round type="success">{{ protocolLabel(config.params.connector_config.transport) }}</n-tag>
            </div>
            <div v-if="aiJob?.status === 'running'" class="connector-card-ai-status" role="status">
              <span><n-icon><SparklesOutline /></n-icon></span>
              <div><strong>AI 正在生成配置</strong><small>后台分析与响应映射进行中</small></div>
              <i aria-hidden="true"></i>
            </div>
            <div v-else-if="aiJob?.status === 'completed' && !aiJob.consumedAt" class="connector-card-ai-status connector-card-ai-status--ready">
              <span><n-icon><CheckmarkCircleOutline /></n-icon></span>
              <div><strong>AI 配置已生成</strong><small>点击进入并查看生成结果</small></div>
            </div>
            <strong class="connector-card-title">{{ endpoint.name || endpoint.id }}</strong>
            <p>{{ config.description || $t('auto.ac98a487503f') }}</p>
            <dl>
              <div>
                <dt>{{ $t('auto.68c2cc7f0cea') }}</dt>
                <dd>{{ endpoint.model || $t('auto.8cae61b2d3c4') }}</dd>
              </div>
              <div>
                <dt>{{ $t('auto.89ff31225c5f') }}</dt>
                <dd>{{ config.ownerName }}</dd>
              </div>
            </dl>
            <div class="connector-card-foot">
              <small :title="endpoint.uri || ''">{{ endpoint.uri || $t('auto.e92dbd43e4b4') }}</small>
              <span class="connector-card-edit">
                <n-icon><CreateOutline /></n-icon> {{ $t('auto.5301648dcf6b') }} </span>
            </div>
          </article>
        </div>

        <div v-else-if="viewMode === 'default' && filteredDefaultConnectors.length" class="connector-card-grid">
          <article
            v-for="connector in filteredDefaultConnectors"
            :key="connector.id"
            class="connector-type-card"
            role="button"
            tabindex="0"
            @click="$router.push(`/agents/connectors/${encodeURIComponent(connector.id)}`)"
            @keydown.enter="$router.push(`/agents/connectors/${encodeURIComponent(connector.id)}`)"
          >
            <div class="connector-card-top">
              <span class="connector-type-mark">
                {{ initials(connector.name) }}
              </span>
              <n-tag round :type="protocolTag(connector.protocol)">{{ connector.protocol.toUpperCase() }}</n-tag>
            </div>
            <strong class="connector-card-title">{{ connector.name }}</strong>
            <p>{{ connectorDescription(connector) }}</p>
            <dl>
              <div>
                <dt>{{ $t('auto.b71c52711a24') }}</dt>
                <dd>{{ connector.endpointCount || 0 }}</dd>
              </div>
              <div>
                <dt>{{ $t('auto.89ff31225c5f') }}</dt>
                <dd>{{ connector.ownerName }}</dd>
              </div>
            </dl>
            <div class="connector-card-foot">
              <small>{{ sampleUri(connector) }}</small>
            </div>
          </article>
        </div>
        <n-empty v-else :description="viewMode === 'custom' ? $t('auto.e91c6d25d136') : $t('auto.9bf3b128bc6c')">
          <template v-if="viewMode === 'custom'" #extra>
            <n-button type="primary" round @click="$router.push('/agents/connectors/new?connector_type=configurable-app-connector')"> {{ $t('auto.2358b858ec11') }} </n-button>
          </template>
        </n-empty>
      </section>
    </GlassPanel>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButtonGroup } from 'naive-ui'
import { AddOutline, CheckmarkCircleOutline, CreateOutline, SearchOutline, SparklesOutline } from '@vicons/ionicons5'
import { useRouter } from 'vue-router'
import GlassPanel from '../../../components/GlassPanel.vue'
import { CONFIGURABLE_CONNECTOR, connectorService, endpointToConfig } from '../../../services/connectorService'
import { getConnectorAIJob } from '../../../services/connectorAiJobService'
import type { ConnectorListItem, ConnectorProtocol } from '../../../types/connector'

type ConnectorViewMode = 'custom' | 'default'

const router = useRouter()
const connectors = ref<ConnectorListItem[]>([])
const search = ref('')
const viewMode = ref<ConnectorViewMode>('custom')

const defaultConnectors = computed(() => connectors.value.filter((connector) => connector.source !== 'user-created'))
const customEndpoints = computed(() => {
  const connector = connectors.value.find((item) => item.id === CONFIGURABLE_CONNECTOR)
  return (connector?.endpoints || []).map((endpoint) => ({
    endpoint,
    config: endpointToConfig(endpoint),
    aiJob: getConnectorAIJob(endpoint.id),
  }))
})
const filteredCustomEndpoints = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  if (!keyword) return customEndpoints.value
  return customEndpoints.value.filter(({ endpoint, config }) => [
    endpoint.name,
    endpoint.id,
    endpoint.uri,
    endpoint.model,
    config.description,
    config.params.connector_config.transport,
  ]
    .filter(Boolean)
    .some((value) => String(value).toLowerCase().includes(keyword)))
})
const filteredDefaultConnectors = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  if (!keyword) return defaultConnectors.value
  return defaultConnectors.value.filter((connector) => [connector.name, connector.description, connector.uri]
    .filter(Boolean)
    .some((value) => String(value).toLowerCase().includes(keyword)))
})
const visibleItemCount = computed(() => viewMode.value === 'custom' ? customEndpoints.value.length : defaultConnectors.value.length)
const filteredItemCount = computed(() => viewMode.value === 'custom' ? filteredCustomEndpoints.value.length : filteredDefaultConnectors.value.length)

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

function protocolLabel(protocol: ConnectorProtocol) {
  if (protocol === 'websocket') return 'WEBSOCKET'
  return protocol.toUpperCase()
}

function editCustomEndpoint(endpointId: string) {
  router.push(`/agents/connectors/${encodeURIComponent(CONFIGURABLE_CONNECTOR)}/edit?endpointId=${encodeURIComponent(endpointId)}`)
}

function sampleUri(connector: ConnectorListItem) {
  if (!connector.uri || connector.uri === '-') return 'No sample URL'
  return connector.uri
}

function connectorDescription(connector: ConnectorListItem) {
  return connector.description
}
</script>
