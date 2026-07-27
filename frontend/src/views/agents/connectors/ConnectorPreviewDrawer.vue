<template>
  <n-drawer :show="show" :width="620" placement="right" @update:show="$emit('update:show', $event)">
    <n-drawer-content v-if="connector" :title="$t('auto.5aa0f18474ef')" closable>
      <div class="connector-preview-drawer">
        <section>
          <p class="eyebrow">{{ $t('auto.09a7b0b98687') }}</p>
          <dl class="connector-preview-grid">
            <div><dt>{{ $t('auto.709a23220f2c') }}</dt><dd>{{ connector.name }}</dd></div>
            <div><dt>{{ $t('auto.1ed77c3f7ffc') }}</dt><dd><span class="connector-protocol-pill">{{ connector.protocol.toUpperCase() }}</span></dd></div>
            <div><dt>{{ $t('auto.89ff31225c5f') }}</dt><dd>{{ connector.ownerName }}</dd></div>
            <div><dt>{{ $t('auto.6da13addb000') }}</dt><dd>{{ connector.source }}</dd></div>
            <div><dt>{{ $t('auto.adf5b7757178') }}</dt><dd>{{ connector.id }}</dd></div>
            <div><dt>{{ $t('auto.b71c52711a24') }}</dt><dd>{{ connector.endpointCount || 0 }}</dd></div>
          </dl>
          <p>{{ connector.description || $t('auto.f354c94fcf63') }}</p>
        </section>

        <section>
          <div class="connector-json-head">
            <p class="eyebrow">{{ $t('auto.35ccab90aae1') }}</p>
            <div class="connector-preview-actions">
              <n-button secondary round size="small" @click="addEndpoint">{{ $t('auto.bfc1935cdb4f') }}</n-button>
              <n-tag round>{{ connector.endpointCount || 0 }} {{ $t('auto.5a537e209151') }}</n-tag>
            </div>
          </div>
          <div v-if="connector.endpoints?.length" class="connector-endpoint-list">
            <article v-for="endpoint in connector.endpoints" :key="endpoint.id" class="connector-endpoint-card">
              <div class="connector-endpoint-main">
                <strong>{{ endpoint.name || endpoint.id }}</strong>
                <span>{{ endpoint.model || $t('auto.8cae61b2d3c4') }}</span>
              </div>
              <small>{{ endpoint.uri || $t('auto.e92dbd43e4b4') }}</small>
              <div class="connector-endpoint-actions">
                <n-button quaternary round size="tiny" @click="editEndpoint(endpoint.id)">{{ $t('auto.5301648dcf6b') }}</n-button>
                <n-button quaternary round size="tiny" @click="duplicateEndpoint(endpoint.id)">{{ $t('auto.972d57379db3') }}</n-button>
                <n-popconfirm
                  :positive-text="$t('common.delete')"
                  :negative-text="$t('auto.77dfd2135f4d')"
                  @positive-click="deleteEndpoint(endpoint.id)"
                >
                  <template #trigger>
                    <n-button quaternary round size="tiny" type="error">{{ $t('common.delete') }}</n-button>
                  </template> {{ $t('auto.b24cea37767b') }} </n-popconfirm>
              </div>
            </article>
          </div>
          <n-empty v-else :description="$t('auto.501cb79d37a9')" />
        </section>

        <section>
          <p class="eyebrow">{{ $t('auto.258ab6cf6656') }}</p>
          <dl class="connector-preview-grid">
            <div><dt>{{ $t('auto.72dc5381324e') }}</dt><dd>{{ connector.config.params.connector_config.auth.type }}</dd></div>
            <div><dt>{{ $t('auto.99ae668a98ca') }}</dt><dd>{{ secretSummary }}</dd></div>
          </dl>
        </section>

        <section>
          <p class="eyebrow">{{ $t('auto.e6bafc838fb4') }}</p>
          <pre>{{ requestConfig }}</pre>
        </section>

        <section>
          <p class="eyebrow">{{ $t('auto.f21cd5c0dc1c') }}</p>
          <pre>{{ responseConfig }}</pre>
        </section>

        <section>
          <div class="connector-json-head">
            <p class="eyebrow">{{ $t('auto.7851cb654218') }}</p>
            <n-button secondary round size="small" @click="copyJson">{{ $t('auto.af74f7c5362a') }}</n-button>
          </div>
          <pre>{{ finalJson }}</pre>
        </section>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup lang="ts">
import { translateSource } from '../../../i18n'

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
  message.success(translateSource('auto.0ad4c5afd450'))
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
  message.success(translateSource('auto.0eb45fe8d30e'))
  emit('changed')
}
</script>
