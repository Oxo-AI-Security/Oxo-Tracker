<template>
  <div class="connector-shell">
    <GlassPanel class="connector-panel connector-endpoints-panel">
      <div class="section-heading connector-endpoints-heading">
        <div>
          <p class="eyebrow">{{ $t('auto.e0e697daa96d') }}</p>
          <h2>{{ connector?.name || $t('auto.35ccab90aae1') }}</h2>
          <span>{{ connector?.description || $t('auto.7ccfcd5c4b01') }}</span>
        </div>
        <div class="endpoint-heading-actions">
          <n-button secondary round @click="$router.push('/agents/connectors')">{{ $t('auto.b52b36b7269f') }}</n-button>
          <n-button type="primary" round :disabled="!connector" @click="addEndpoint">
            <template #icon><n-icon><AddOutline /></n-icon></template> {{ $t('auto.2358b858ec11') }} </n-button>
        </div>
      </div>

      <n-alert v-if="loadError" type="error" :title="$t('auto.64666508d39d')"> {{ $t('auto.153089d188c1') }} </n-alert>

      <template v-else-if="connector">
        <div class="connector-endpoints-summary">
          <article>
            <dt>{{ $t('auto.adf5b7757178') }}</dt>
            <dd>{{ connector.id }}</dd>
          </article>
          <article>
            <dt>{{ $t('auto.6da13addb000') }}</dt>
            <dd>{{ connector.source === 'built-in' ? $t('auto.ccd61990d7d2') : $t('auto.ef6691805d41') }}</dd>
          </article>
          <article>
            <dt>{{ $t('auto.b71c52711a24') }}</dt>
            <dd>{{ connector.endpointCount || 0 }}</dd>
          </article>
          <article>
            <dt>{{ $t('auto.f2f8570ddd7b') }}</dt>
            <dd>{{ new Date(connector.updatedAt).toLocaleString() }}</dd>
          </article>
        </div>

        <section class="connector-endpoints-workspace">
          <div class="connector-endpoint-list-head">
            <div>
              <p class="eyebrow">{{ $t('auto.03849cb31586') }}</p>
              <h3>{{ connector.endpointCount || 0 }} {{ $t('auto.d39d941ddf44') }}</h3>
            </div>
            <n-button secondary round size="small" @click="addEndpoint">{{ $t('auto.bfc1935cdb4f') }}</n-button>
          </div>

          <div v-if="connector.endpoints?.length" class="connector-endpoint-table">
            <article v-for="endpoint in connector.endpoints" :key="endpoint.id" class="connector-endpoint-row">
              <div class="connector-endpoint-name">
                <strong>{{ endpoint.name || endpoint.id }}</strong>
                <span>{{ endpoint.id }}</span>
              </div>
              <div class="connector-endpoint-target">
                <dt>{{ $t('auto.b7d8a4de2bb4') }}</dt>
                <dd>{{ endpoint.uri || $t('auto.e92dbd43e4b4') }}</dd>
              </div>
              <div class="connector-endpoint-target">
                <dt>{{ $t('auto.68c2cc7f0cea') }}</dt>
                <dd>{{ endpoint.model || $t('auto.8cae61b2d3c4') }}</dd>
              </div>
              <div class="connector-endpoint-meta">
                <n-tag round :type="endpoint.token ? 'success' : 'default'">{{ endpoint.token ? $t('auto.a5f0b0653237') : $t('auto.a38dd7c75585') }}</n-tag>
                <small>{{ endpoint.created_date ? new Date(endpoint.created_date).toLocaleString() : $t('auto.acb6273ecab9') }}</small>
              </div>
              <div class="connector-endpoint-actions">
                <n-button secondary round size="small" @click="editEndpoint(endpoint.id)">{{ $t('auto.5301648dcf6b') }}</n-button>
                <n-button secondary round size="small" @click="duplicateEndpoint(endpoint.id)">{{ $t('auto.972d57379db3') }}</n-button>
                <n-popconfirm :positive-text="$t('common.delete')" :negative-text="$t('auto.77dfd2135f4d')" @positive-click="deleteEndpoint(endpoint.id)">
                  <template #trigger>
                    <n-button secondary round size="small" type="error">{{ $t('common.delete') }}</n-button>
                  </template> {{ $t('auto.b24cea37767b') }} </n-popconfirm>
              </div>
            </article>
          </div>

          <n-empty v-else :description="$t('auto.4a9a9d325f26')">
            <template #extra>
              <n-button type="primary" round @click="addEndpoint">{{ $t('auto.2358b858ec11') }}</n-button>
            </template>
          </n-empty>
        </section>
      </template>
    </GlassPanel>
  </div>
</template>

<script setup lang="ts">
import { translateSource } from '../../../i18n'

import { onMounted, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { AddOutline } from '@vicons/ionicons5'
import { useRoute, useRouter } from 'vue-router'
import GlassPanel from '../../../components/GlassPanel.vue'
import { CONFIGURABLE_CONNECTOR, connectorService, endpointToConfig } from '../../../services/connectorService'
import type { ConnectorListItem } from '../../../types/connector'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const connector = ref<ConnectorListItem | null>(null)
const loadError = ref(false)

onMounted(loadConnector)

async function loadConnector() {
  loadError.value = false
  const connectorId = String(route.params.id || '')
  if (connectorId === CONFIGURABLE_CONNECTOR) {
    await router.replace('/agents/connectors')
    return
  }
  connector.value = await connectorService.getConnector(connectorId) || null
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
  message.success(translateSource('auto.0eb45fe8d30e'))
  await loadConnector()
}
</script>
