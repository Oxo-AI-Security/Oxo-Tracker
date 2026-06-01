<template>
  <n-drawer :show="show" :width="620" placement="right" @update:show="$emit('update:show', $event)">
    <n-drawer-content v-if="connector" title="Connector Preview" closable>
      <div class="connector-preview-drawer">
        <section>
          <p class="eyebrow">Basic Info</p>
          <dl class="connector-preview-grid">
            <div><dt>Name</dt><dd>{{ connector.name }}</dd></div>
            <div><dt>Protocol</dt><dd><span class="connector-protocol-pill">{{ connector.protocol.toUpperCase() }}</span></dd></div>
            <div><dt>Owner</dt><dd>{{ connector.ownerName }}</dd></div>
            <div><dt>Source</dt><dd>{{ connector.source }}</dd></div>
            <div><dt>Connector Type</dt><dd>{{ connector.id }}</dd></div>
            <div><dt>Endpoints</dt><dd>{{ connector.endpointCount || 0 }}</dd></div>
          </dl>
          <p>{{ connector.description || 'No description' }}</p>
        </section>

        <section>
          <div class="connector-json-head">
            <p class="eyebrow">Connector Endpoints</p>
            <div class="connector-preview-actions">
              <n-button secondary round size="small" @click="addEndpoint">Add endpoint</n-button>
              <n-tag round>{{ connector.endpointCount || 0 }} total</n-tag>
            </div>
          </div>
          <div v-if="connector.endpoints?.length" class="connector-endpoint-list">
            <article v-for="endpoint in connector.endpoints" :key="endpoint.id" class="connector-endpoint-card">
              <div class="connector-endpoint-main">
                <strong>{{ endpoint.name || endpoint.id }}</strong>
                <span>{{ endpoint.model || 'No model' }}</span>
              </div>
              <small>{{ endpoint.uri || 'No target URL' }}</small>
              <div class="connector-endpoint-actions">
                <n-button quaternary round size="tiny" @click="editEndpoint(endpoint.id)">Edit</n-button>
                <n-button quaternary round size="tiny" @click="duplicateEndpoint(endpoint.id)">Duplicate</n-button>
                <n-popconfirm
                  positive-text="Delete"
                  negative-text="Cancel"
                  @positive-click="deleteEndpoint(endpoint.id)"
                >
                  <template #trigger>
                    <n-button quaternary round size="tiny" type="error">Delete</n-button>
                  </template>
                  Delete this connector endpoint?
                </n-popconfirm>
              </div>
            </article>
          </div>
          <n-empty v-else description="No connector endpoints yet. Create one from the builder." />
        </section>

        <section>
          <p class="eyebrow">Auth Summary</p>
          <dl class="connector-preview-grid">
            <div><dt>Auth Type</dt><dd>{{ connector.config.params.connector_config.auth.type }}</dd></div>
            <div><dt>Secret Reference</dt><dd>{{ secretSummary }}</dd></div>
          </dl>
        </section>

        <section>
          <p class="eyebrow">Request Config</p>
          <pre>{{ requestConfig }}</pre>
        </section>

        <section>
          <p class="eyebrow">Response Extract Config</p>
          <pre>{{ responseConfig }}</pre>
        </section>

        <section>
          <div class="connector-json-head">
            <p class="eyebrow">Final JSON Config Preview</p>
            <n-button secondary round size="small" @click="copyJson">Copy</n-button>
          </div>
          <pre>{{ finalJson }}</pre>
        </section>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useMessage } from 'naive-ui'
import { useRouter } from 'vue-router'
import { connectorService, endpointToConfig } from '../../../services/connectorService'
import type { ConnectorListItem } from '../../../types/connector'

const props = defineProps<{ show: boolean; connector?: ConnectorListItem | null }>()
const emit = defineEmits<{ 'update:show': [value: boolean]; changed: [] }>()
const router = useRouter()
const message = useMessage()

const requestConfig = computed(() => JSON.stringify(props.connector?.config.params.connector_config.request || props.connector?.config.params.connector_config.stream || props.connector?.config.params.connector_config.websocket || {}, null, 2))
const responseConfig = computed(() => JSON.stringify(props.connector?.config.params.connector_config.response || {}, null, 2))
const secretSummary = computed(() => props.connector?.config.params.connector_config.auth.secretRef || (props.connector?.config.token ? 'Configured secret (hidden)' : 'None'))
const maskedConfig = computed(() => {
  if (!props.connector?.config) return {}
  return {
    ...props.connector.config,
    token: props.connector.config.token ? '********' : '',
  }
})
const finalJson = computed(() => JSON.stringify(maskedConfig.value, null, 2))

async function copyJson() {
  await navigator.clipboard.writeText(finalJson.value)
  message.success('Connector JSON copied')
}

function addEndpoint() {
  if (!props.connector) return
  emit('update:show', false)
  router.push(`/agents/connectors/new?connector_type=${encodeURIComponent(props.connector.id)}`)
}

function editEndpoint(endpointId: string) {
  if (!props.connector) return
  emit('update:show', false)
  router.push(`/agents/connectors/${encodeURIComponent(props.connector.id)}/edit?endpointId=${encodeURIComponent(endpointId)}`)
}

function duplicateEndpoint(endpointId: string) {
  const endpoint = props.connector?.endpoints?.find((item) => item.id === endpointId)
  if (!endpoint) return
  const draft = endpointToConfig(endpoint)
  draft.id = undefined
  draft.name = `Copy of ${endpoint.name || endpoint.id}`
  window.sessionStorage.setItem('oxo-connector-draft', JSON.stringify(draft))
  emit('update:show', false)
  router.push('/agents/connectors/new?duplicate=1')
}

async function deleteEndpoint(endpointId: string) {
  await connectorService.deleteConnector(endpointId)
  message.success('Connector endpoint deleted')
  emit('changed')
}
</script>
