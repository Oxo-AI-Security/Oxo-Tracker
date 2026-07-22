<template>
  <div class="connector-shell">
    <GlassPanel class="connector-panel connector-endpoints-panel">
      <div class="section-heading connector-endpoints-heading">
        <div>
          <p class="eyebrow">Agents / Connector Endpoints</p>
          <h2>{{ connector?.name || 'Connector Endpoints' }}</h2>
          <span>{{ connector?.description || 'Manage endpoint JSON records under this connector type.' }}</span>
        </div>
        <div class="endpoint-heading-actions">
          <n-button secondary round @click="$router.push('/agents/connectors')">Back</n-button>
          <n-button type="primary" round :disabled="!connector" @click="addEndpoint">
            <template #icon><n-icon><AddOutline /></n-icon></template>
            New Endpoint
          </n-button>
        </div>
      </div>

      <n-alert v-if="loadError" type="error" title="Connector not found">
        The connector type could not be loaded.
      </n-alert>

      <template v-else-if="connector">
        <div class="connector-endpoints-summary">
          <article>
            <dt>Connector Type</dt>
            <dd>{{ connector.id }}</dd>
          </article>
          <article>
            <dt>Source</dt>
            <dd>{{ connector.source === 'built-in' ? 'Default connector' : 'Configurable App' }}</dd>
          </article>
          <article>
            <dt>Endpoints</dt>
            <dd>{{ connector.endpointCount || 0 }}</dd>
          </article>
          <article>
            <dt>Updated</dt>
            <dd>{{ new Date(connector.updatedAt).toLocaleString() }}</dd>
          </article>
        </div>

        <section class="connector-endpoints-workspace">
          <div class="connector-endpoint-list-head">
            <div>
              <p class="eyebrow">Endpoint Records</p>
              <h3>{{ connector.endpointCount || 0 }} configured endpoints</h3>
            </div>
            <n-button secondary round size="small" @click="addEndpoint">Add endpoint</n-button>
          </div>

          <div v-if="connector.endpoints?.length" class="connector-endpoint-table">
            <article v-for="endpoint in connector.endpoints" :key="endpoint.id" class="connector-endpoint-row">
              <div class="connector-endpoint-name">
                <strong>{{ endpoint.name || endpoint.id }}</strong>
                <span>{{ endpoint.id }}</span>
              </div>
              <div class="connector-endpoint-target">
                <dt>Target URL</dt>
                <dd>{{ endpoint.uri || 'No target URL' }}</dd>
              </div>
              <div class="connector-endpoint-target">
                <dt>Model</dt>
                <dd>{{ endpoint.model || 'No model' }}</dd>
              </div>
              <div class="connector-endpoint-meta">
                <n-tag round :type="endpoint.token ? 'success' : 'default'">{{ endpoint.token ? 'token set' : 'no token' }}</n-tag>
                <small>{{ endpoint.created_date ? new Date(endpoint.created_date).toLocaleString() : 'No date' }}</small>
              </div>
              <div class="connector-endpoint-actions">
                <n-button secondary round size="small" @click="editEndpoint(endpoint.id)">Edit</n-button>
                <n-button secondary round size="small" @click="duplicateEndpoint(endpoint.id)">Duplicate</n-button>
                <n-popconfirm positive-text="Delete" negative-text="Cancel" @positive-click="deleteEndpoint(endpoint.id)">
                  <template #trigger>
                    <n-button secondary round size="small" type="error">Delete</n-button>
                  </template>
                  Delete this connector endpoint?
                </n-popconfirm>
              </div>
            </article>
          </div>

          <n-empty v-else description="No endpoints yet. Add one to make this connector available to runs.">
            <template #extra>
              <n-button type="primary" round @click="addEndpoint">New Endpoint</n-button>
            </template>
          </n-empty>
        </section>
      </template>
    </GlassPanel>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { useRoute, useRouter } from 'vue-router'
import GlassPanel from '../../../components/GlassPanel.vue'
import { connectorService, endpointToConfig } from '../../../services/connectorService'
import type { ConnectorListItem } from '../../../types/connector'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const connector = ref<ConnectorListItem | null>(null)
const loadError = ref(false)

onMounted(loadConnector)

async function loadConnector() {
  loadError.value = false
  connector.value = await connectorService.getConnector(String(route.params.id || '')) || null
  if (!connector.value) loadError.value = true
}

function addEndpoint() {
  if (!connector.value) return
  router.push(`/agents/connectors/new?connector_type=${encodeURIComponent(connector.value.id)}`)
}

function editEndpoint(endpointId: string) {
  if (!connector.value) return
  router.push(`/agents/connectors/${encodeURIComponent(connector.value.id)}/edit?endpointId=${encodeURIComponent(endpointId)}`)
}

function duplicateEndpoint(endpointId: string) {
  const endpoint = connector.value?.endpoints?.find((item) => item.id === endpointId)
  if (!endpoint) return
  const draft = endpointToConfig(endpoint)
  draft.id = undefined
  draft.name = `Copy of ${endpoint.name || endpoint.id}`
  window.sessionStorage.setItem('oxo-connector-draft', JSON.stringify(draft))
  router.push('/agents/connectors/new?duplicate=1')
}

async function deleteEndpoint(endpointId: string) {
  await connectorService.deleteConnector(endpointId)
  message.success('Connector endpoint deleted')
  await loadConnector()
}
</script>
