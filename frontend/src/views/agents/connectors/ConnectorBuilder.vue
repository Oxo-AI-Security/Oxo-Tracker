<template>
  <div class="connector-shell">
    <GlassPanel class="connector-builder-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Agents / Connector Builder</p>
          <h2>{{ editingId ? 'Edit Connector Endpoint' : 'New Connector Endpoint' }}</h2>
          <span>Configure one endpoint under a Moonshot connector type.</span>
        </div>
        <div class="endpoint-heading-actions">
          <n-button secondary round @click="$router.push('/agents/connectors')">Back</n-button>
          <n-button type="primary" round :disabled="!canSave" @click="saveConnector">Save Endpoint</n-button>
        </div>
      </div>

      <n-alert v-if="permissionDenied" type="error" title="Permission denied">
        This connector endpoint could not be loaded.
      </n-alert>

      <div v-else class="connector-builder-grid">
        <section class="connector-builder-main">
          <div class="connector-builder-hero">
            <div>
              <p class="eyebrow">Connector type</p>
              <strong>{{ form.connector_type }}</strong>
              <span>Endpoint settings are saved into Moonshot connector-endpoints.</span>
            </div>
            <div class="connector-template-actions">
              <n-button :type="activeProtocol === 'http' ? 'primary' : 'default'" secondary round @click="loadTemplate('http')">HTTP Template</n-button>
              <n-button :type="activeProtocol === 'sse' ? 'primary' : 'default'" secondary round @click="loadTemplate('sse')">SSE Template</n-button>
              <n-button :type="activeProtocol === 'websocket' ? 'primary' : 'default'" secondary round @click="loadTemplate('websocket')">WebSocket Template</n-button>
            </div>
          </div>

          <n-collapse :expanded-names="exampleOpen" class="connector-example-collapse" @update:expanded-names="exampleOpen = Array.isArray($event) ? $event : [$event]">
            <n-collapse-item title="Example: connect a custom /chat API" name="example">
              <div class="connector-example-card">
                <div>
                  <strong>URL</strong>
                  <span>Use the complete request URL.</span>
                  <code>http://10.255.25.153:5000/chat</code>
                </div>
                <div>
                  <strong>Auth header</strong>
                  <span>Add a preset or custom header if the app needs auth.</span>
                  <code>Authorization: Bearer &lt;token&gt;</code>
                </div>
                <div>
                  <strong>Request input field</strong>
                  <span>Select the value that should receive user input and replace it.</span>
                  <pre>{ "message": "{{ promptToken }}", "level": 1, "history": [] }</pre>
                </div>
                <div>
                  <strong>Response output field</strong>
                  <span>Select the model answer value to create the output path.</span>
                  <pre>{ "blocked": false, "response": "Hi! How can I assist you today?" }</pre>
                </div>
              </div>
            </n-collapse-item>
          </n-collapse>

          <n-tabs v-model:value="activeTab" type="segment">
            <n-tab-pane name="basic" tab="Basic">
              <div class="connector-form-card">
                <n-form label-placement="top">
                  <n-form-item label="Name"><n-input v-model:value="form.name" /></n-form-item>
                  <n-form-item label="Description"><n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" /></n-form-item>
                  <n-form-item label="Protocol">
                    <n-segmented
                      :value="form.params.connector_config.transport"
                      :options="protocolOptions"
                      @update:value="setProtocol(String($event) as ConnectorProtocol)"
                    />
                  </n-form-item>
                  <n-form-item label="Request URL"><n-input v-model:value="form.uri" placeholder="http://10.255.25.153:5000/chat" /></n-form-item>
                  <n-form-item label="Model"><n-input v-model:value="form.model" /></n-form-item>
                </n-form>
              </div>
            </n-tab-pane>

            <n-tab-pane name="auth" tab="Auth">
              <div class="connector-form-card">
                <n-form label-placement="top">
                  <n-form-item label="Auth Type"><n-select v-model:value="form.params.connector_config.auth.type" :options="authOptions" /></n-form-item>
                  <n-form-item label="Token / API Key"><n-input v-model:value="form.token" type="password" show-password-on="click" placeholder="Paste a token if this endpoint needs one" /></n-form-item>
                  <n-form-item label="Header presets">
                    <n-space>
                      <n-button secondary round size="small" @click="applyHeaderPreset('bearer')">Authorization: Bearer</n-button>
                      <n-button secondary round size="small" @click="applyHeaderPreset('x-api-key')">x-api-key</n-button>
                      <n-button secondary round size="small" @click="applyHeaderPreset('cookie')">Cookie</n-button>
                    </n-space>
                  </n-form-item>
                  <div class="connector-inline-fields">
                    <n-form-item label="Custom Header Name"><n-input v-model:value="customHeaderName" placeholder="x-custom-token" /></n-form-item>
                    <n-form-item label="Custom Header Value"><n-input v-model:value="customHeaderValue" placeholder="secret or static value" /></n-form-item>
                  </div>
                  <n-button secondary round size="small" @click="addCustomHeader">Add custom header</n-button>
                  <n-form-item label="Request Headers">
                    <textarea
                      v-model="headersText"
                      class="connector-code-textarea connector-code-textarea-small"
                      spellcheck="false"
                      @blur="syncHeaders"
                    />
                  </n-form-item>
                </n-form>
              </div>
            </n-tab-pane>

            <n-tab-pane name="request" tab="Request">
              <div class="connector-form-card">
                <template v-if="form.params.connector_config.transport === 'http' && form.params.connector_config.request">
                  <div class="connector-mapping-layout">
                    <n-form label-placement="top">
                      <div class="connector-inline-fields connector-method-row">
                        <n-form-item label="Method"><n-select v-model:value="form.params.connector_config.request.method" :options="methodOptions" /></n-form-item>
                      </div>
                    </n-form>
                    <div class="connector-mapping-card">
                      <div class="connector-mapping-head">
                        <div>
                          <p class="eyebrow">Input mapping</p>
                          <strong>Paste the full request body</strong>
                        </div>
                        <n-button secondary round size="small" @click="markPromptSelection">Use selected value as input</n-button>
                      </div>
                      <textarea
                        ref="requestBodyRef"
                        v-model="form.params.connector_config.request.bodyTemplate"
                        class="connector-code-textarea"
                        spellcheck="false"
                      />
                      <div v-if="hasPromptToken" class="connector-mapped-preview">
                        <span>Input is mapped to</span>
                        <button type="button" class="connector-token-chip" @click="removePromptToken">{{ promptToken }} <b>×</b></button>
                      </div>
                      <div class="connector-token-preview">
                        <span>User input token</span>
                        <code>{{ promptToken }}</code>
                      </div>
                    </div>
                  </div>
                </template>
                <template v-else-if="form.params.connector_config.transport === 'sse' && form.params.connector_config.stream">
                  <n-form label-placement="top">
                    <n-form-item label="Stream Path"><n-input v-model:value="form.params.connector_config.stream.path" /></n-form-item>
                    <n-form-item label="Event Field"><n-input v-model:value="form.params.connector_config.stream.eventField" /></n-form-item>
                    <n-form-item label="Data Prefix"><n-input v-model:value="form.params.connector_config.stream.dataPrefix" /></n-form-item>
                  </n-form>
                </template>
                <template v-else-if="form.params.connector_config.websocket">
                  <n-form label-placement="top">
                    <n-form-item label="WebSocket Path"><n-input v-model:value="form.params.connector_config.websocket.path" /></n-form-item>
                    <n-form-item label="Message Template"><n-input v-model:value="form.params.connector_config.websocket.messageTemplate" type="textarea" :autosize="{ minRows: 6, maxRows: 12 }" /></n-form-item>
                    <n-form-item label="Response Field"><n-input v-model:value="form.params.connector_config.websocket.responseMessageField" /></n-form-item>
                  </n-form>
                </template>
              </div>
            </n-tab-pane>

            <n-tab-pane name="response" tab="Response">
              <div class="connector-form-card">
                <div class="connector-mapping-card">
                  <div class="connector-mapping-head">
                    <div>
                      <p class="eyebrow">Output mapping</p>
                      <strong>Paste a sample response and select the value to display</strong>
                    </div>
                    <n-button secondary round size="small" @click="markOutputSelection">Use selected value as output</n-button>
                  </div>
                  <textarea
                    ref="responseBodyRef"
                    v-model="sampleResponse"
                    class="connector-code-textarea"
                    spellcheck="false"
                  />
                  <div v-if="form.params.connector_config.response.path" class="connector-mapped-preview">
                    <span>Output is read from</span>
                    <button type="button" class="connector-token-chip" @click="clearOutputPath">{{ form.params.connector_config.response.path }} <b>×</b></button>
                  </div>
                </div>
                <n-form label-placement="top" class="connector-output-fields">
                  <n-form-item label="Extract Type"><n-select v-model:value="form.params.connector_config.response.type" :options="extractOptions" /></n-form-item>
                  <n-form-item label="Output Path"><n-input v-model:value="form.params.connector_config.response.path" placeholder="$.response" /></n-form-item>
                  <n-form-item label="Fallback Path"><n-input v-model:value="form.params.connector_config.response.fallbackPath" /></n-form-item>
                </n-form>
              </div>
            </n-tab-pane>

            <n-tab-pane name="test" tab="Test">
              <div class="connector-form-card connector-test-card">
                <n-input v-model:value="testPrompt" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" placeholder="Test prompt" />
                <n-button type="primary" round :loading="testing" @click="testConnector">Test Connection</n-button>
                <div v-if="testResult" class="connector-test-result">
                  <n-tag :type="testResult.status === 'success' ? 'success' : 'error'" round>{{ testResult.status }}</n-tag>
                  <span>{{ testResult.duration }}ms</span>
                  <strong>Request Preview</strong><pre>{{ testResult.requestPreview }}</pre>
                  <strong>Raw Response</strong><pre>{{ testResult.rawResponse }}</pre>
                  <strong>Extracted Response</strong><pre>{{ testResult.extractedResponse }}</pre>
                  <strong v-if="testResult.error">Error</strong><pre v-if="testResult.error">{{ testResult.error }}</pre>
                </div>
              </div>
            </n-tab-pane>
          </n-tabs>
        </section>

        <aside class="connector-json-preview">
          <div class="connector-json-head">
            <p class="eyebrow">JSON Preview</p>
            <n-button secondary round size="small" @click="copyJson">Copy</n-button>
          </div>
          <pre>{{ jsonPreview }}</pre>
        </aside>
      </div>
    </GlassPanel>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'
import GlassPanel from '../../../components/GlassPanel.vue'
import { applyTemplate, connectorService, currentUser, defaultConnectorConfig, endpointToConfig } from '../../../services/connectorService'
import type { ConnectorConfig, ConnectorProtocol, ConnectorTestResult } from '../../../types/connector'
import { useMoonshotStore } from '../../../stores/moonshot'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const store = useMoonshotStore()
const editingId = computed(() => String(route.params.id || ''))
const form = reactive<ConnectorConfig>(defaultConnectorConfig('http'))
const activeTab = ref('basic')
const exampleOpen = ref<Array<string | number>>([])
const permissionDenied = ref(false)
const testing = ref(false)
const testPrompt = ref('Hello')
const testResult = ref<ConnectorTestResult | null>(null)
const requestBodyRef = ref<HTMLTextAreaElement | null>(null)
const responseBodyRef = ref<HTMLTextAreaElement | null>(null)
const headersText = ref('{\n  "content-type": "application/json"\n}')
const sampleResponse = ref('{\n  "blocked": false,\n  "response": "Hi! How can I assist you today?"\n}')
const promptToken = '{{ prompt }}'
const customHeaderName = ref('')
const customHeaderValue = ref('')
const activeProtocol = computed(() => form.params.connector_config.transport)
const hasPromptToken = computed(() => Boolean(form.params.connector_config.request?.bodyTemplate.includes(promptToken)))

const protocolOptions = [
  { label: 'HTTP', value: 'http' },
  { label: 'SSE', value: 'sse' },
  { label: 'WebSocket', value: 'websocket' },
]
const authOptions = [
  { label: 'None', value: 'none' },
  { label: 'Bearer Token', value: 'bearer' },
  { label: 'API Key', value: 'api-key' },
  { label: 'Cookie', value: 'cookie' },
  { label: 'Basic', value: 'basic' },
]
const methodOptions = ['GET', 'POST', 'PUT', 'PATCH'].map((value) => ({ label: value, value }))
const extractOptions = [
  { label: 'JSON Path', value: 'json-path' },
  { label: 'Text', value: 'text' },
  { label: 'Event Data', value: 'event-data' },
]
const canSave = computed(() => form.name.trim() && form.uri.trim() && !permissionDenied.value)
const jsonPreview = computed(() => JSON.stringify(form, null, 2))

onMounted(async () => {
  const draft = window.sessionStorage.getItem('oxo-connector-draft')
  if (draft && !editingId.value) {
    Object.assign(form, JSON.parse(draft))
    syncHeadersText()
    window.sessionStorage.removeItem('oxo-connector-draft')
    return
  }
  const connectorType = String(route.query.connector_type || '')
  if (!editingId.value) {
    if (connectorType) form.connector_type = connectorType
    syncHeadersText()
    return
  }
  const connector = await connectorService.getConnector(editingId.value)
  if (!connector) {
    permissionDenied.value = true
    message.error('Connector type was not found.')
    return
  }
  const endpointId = String(route.query.endpointId || '')
  const endpoint = endpointId ? connector.endpoints?.find((item) => item.id === endpointId) : undefined
  if (endpointId && !endpoint) {
    permissionDenied.value = true
    message.error('Connector endpoint was not found.')
    return
  }
  Object.assign(form, endpoint ? endpointToConfig(endpoint) : connector.config)
  syncHeadersText()
})

function setProtocol(protocol: ConnectorProtocol) {
  Object.assign(form, applyTemplate(form, protocol))
}

function loadTemplate(protocol: ConnectorProtocol) {
  setProtocol(protocol)
  syncHeadersText()
  message.success(`${protocol.toUpperCase()} template loaded`)
}

function applyHeaderPreset(kind: 'bearer' | 'x-api-key' | 'cookie') {
  const headers = parseHeadersText()
  if (kind === 'bearer') {
    form.params.connector_config.auth.type = 'bearer'
    form.params.connector_config.auth.headerName = 'Authorization'
    headers.Authorization = form.token ? `Bearer ${form.token}` : 'Bearer <token>'
  }
  if (kind === 'x-api-key') {
    form.params.connector_config.auth.type = 'api-key'
    form.params.connector_config.auth.headerName = 'x-api-key'
    headers['x-api-key'] = form.token || '<api-key>'
  }
  if (kind === 'cookie') {
    form.params.connector_config.auth.type = 'cookie'
    form.params.connector_config.auth.headerName = 'Cookie'
    headers.Cookie = form.token || 'session=<token>'
  }
  headersText.value = JSON.stringify(headers, null, 2)
  syncHeaders()
}

function addCustomHeader() {
  if (!customHeaderName.value.trim()) {
    message.warning('Enter a custom header name first.')
    return
  }
  const headers = parseHeadersText()
  headers[customHeaderName.value.trim()] = customHeaderValue.value
  headersText.value = JSON.stringify(headers, null, 2)
  customHeaderName.value = ''
  customHeaderValue.value = ''
  syncHeaders()
}

async function saveConnector() {
  if (!canSave.value) return
  syncHeaders()
  form.source = 'user-created'
  form.ownerId = currentUser.id
  form.ownerName = currentUser.name
  const saved = await connectorService.saveConnector({ ...form, id: form.id })
  await store.loadOverview()
  message.success('Connector endpoint saved')
  router.push(`/agents/connectors`)
  void saved
}

async function testConnector() {
  syncHeaders()
  testing.value = true
  try {
    testResult.value = await connectorService.testConnector(form, testPrompt.value)
  } finally {
    testing.value = false
  }
}

async function copyJson() {
  await navigator.clipboard.writeText(jsonPreview.value)
  message.success('Connector JSON copied')
}

function syncHeadersText() {
  const headers = form.params.connector_config.request?.headers || { 'content-type': 'application/json' }
  headersText.value = JSON.stringify(headers, null, 2)
}

function syncHeaders() {
  if (!form.params.connector_config.request) return
  try {
    form.params.connector_config.request.headers = parseHeadersText()
  } catch {
    message.error('Headers must be a valid JSON object.')
  }
}

function parseHeadersText() {
  const parsed = JSON.parse(headersText.value || '{}')
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {}
  return parsed as Record<string, string>
}

function markPromptSelection() {
  const target = requestBodyRef.value
  const request = form.params.connector_config.request
  if (!target || !request) return
  const start = target.selectionStart
  const end = target.selectionEnd
  if (start === end) {
    message.warning('Select the request value that should receive the user prompt.')
    return
  }
  request.bodyTemplate = `${request.bodyTemplate.slice(0, start)}{{ prompt }}${request.bodyTemplate.slice(end)}`
  message.success('Input value was replaced with a prompt block.')
  requestAnimationFrame(() => target.focus())
}

function removePromptToken() {
  const request = form.params.connector_config.request
  if (!request) return
  request.bodyTemplate = request.bodyTemplate.replace(promptToken, '')
}

function markOutputSelection() {
  const target = responseBodyRef.value
  if (!target) return
  const selected = sampleResponse.value.slice(target.selectionStart, target.selectionEnd)
  if (!selected) {
    message.warning('Select the response value that should be displayed as the model output.')
    return
  }
  const path = findJsonPathBySelection(sampleResponse.value, selected)
  if (!path) {
    message.error('Could not map the selection to a JSON field. Select a complete value such as the response text.')
    return
  }
  form.params.connector_config.response.type = 'json-path'
  form.params.connector_config.response.path = path
  message.success(`Output path set to ${path}`)
}

function clearOutputPath() {
  form.params.connector_config.response.path = ''
}

function findJsonPathBySelection(rawJson: string, selected: string) {
  const normalized = selected.trim().replace(/^"|"$/g, '')
  try {
    const parsed = JSON.parse(rawJson)
    return findPath(parsed, normalized)
  } catch {
    return undefined
  }
}

function findPath(value: unknown, selected: string, path = '$'): string | undefined {
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value) === selected || String(value).includes(selected) ? path : undefined
  }
  if (Array.isArray(value)) {
    for (let index = 0; index < value.length; index += 1) {
      const found = findPath(value[index], selected, `${path}.${index}`)
      if (found) return found
    }
  }
  if (value && typeof value === 'object') {
    for (const [key, child] of Object.entries(value)) {
      const found = findPath(child, selected, `${path}.${key}`)
      if (found) return found
    }
  }
  return undefined
}
</script>
