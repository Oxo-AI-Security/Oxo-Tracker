<template>
  <div class="connector-shell">
    <GlassPanel class="connector-builder-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Agents / Endpoints / App Endpoint</p>
          <h2>{{ editingId ? 'Edit Connector Endpoint' : 'New Connector Endpoint' }}</h2>
          <span>Configure one endpoint under a Moonshot connector type.</span>
        </div>
        <div class="endpoint-heading-actions">
          <n-button v-if="isConfigurableApp" class="connector-ai-button" type="primary" secondary round :loading="aiGenerating" :disabled="permissionDenied" @click="openAIAssistant">
            <template #icon><n-icon><SparklesOutline /></n-icon></template>
            AI Configure
          </n-button>
          <n-button secondary round :disabled="aiGenerating" @click="goBack">Back</n-button>
          <n-button type="primary" round :disabled="!canSave || aiGenerating" @click="saveConnector">Save Endpoint</n-button>
        </div>
      </div>

      <n-alert v-if="permissionDenied" type="error" title="Permission denied">
        This connector endpoint could not be loaded.
      </n-alert>

      <div v-else class="connector-builder-grid" :class="{ 'connector-builder-grid--locked': aiGenerating }" :inert="aiGenerating" :aria-busy="aiGenerating">
        <section class="connector-builder-main">
          <div class="connector-builder-hero">
            <div>
              <p class="eyebrow">Connector type</p>
              <strong>{{ form.connector_type }}</strong>
              <span>Endpoint settings are saved into Moonshot connector-endpoints.</span>
            </div>
            <div v-if="isConfigurableApp" class="connector-template-actions">
              <n-button :type="activeProtocol === 'http' ? 'primary' : 'default'" secondary round @click="loadTemplate('http')">HTTP Template</n-button>
              <n-button :type="activeProtocol === 'sse' ? 'primary' : 'default'" secondary round @click="loadTemplate('sse')">SSE Template</n-button>
              <n-button :type="activeProtocol === 'websocket' ? 'primary' : 'default'" secondary round @click="loadTemplate('websocket')">WebSocket Template</n-button>
            </div>
          </div>

          <section v-if="isConfigurableApp" class="connector-guide-collapse">
            <button type="button" class="connector-guide-toggle" @click="guideOpen = !guideOpen">
              <div class="connector-guide-header">
                <span>Configuration Guide</span>
                <strong>Map a custom AI app into a Connector Endpoint</strong>
              </div>
              <span class="connector-guide-state">{{ guideOpen ? 'Collapse' : 'Expand' }}</span>
            </button>
            <div v-if="guideOpen" class="connector-guide-body">
              <div class="connector-guide-intro">
                <strong>Put the user input into the request, then extract the AI answer from the response.</strong>
                <span>This guide explains the setup flow only. Complete the real configuration in Basic, Auth, Request, Response, and Test.</span>
              </div>
              <div class="connector-example-card connector-guide-steps">
                <div>
                  <b>1</b>
                  <strong>URL</strong>
                  <span>Use a complete endpoint URL, or put the base URL in Request URL and the route in Path.</span>
                  <code>http://10.255.25.153:5000/chat</code>
                </div>
                <div>
                  <b>2</b>
                  <strong>Auth header</strong>
                  <span>Choose Bearer, API Key, Cookie, or add your own static request headers.</span>
                  <code>Authorization: Bearer &lt;token&gt;</code>
                </div>
                <div>
                  <b>3</b>
                  <strong>Request input field</strong>
                  <span>Replace the JSON, form, or query value that receives user input with the prompt token.</span>
                  <pre>{ "message": "{{ promptToken }}", "level": 1, "history": [] }</pre>
                </div>
                <div>
                  <b>4</b>
                  <strong>Response output field</strong>
                  <span>Paste a response sample, select the AI answer value, and generate the output path.</span>
                  <pre>{ "blocked": false, "response": "Hi! How can I assist you today?" }</pre>
                </div>
              </div>
            </div>
          </section>

          <div v-if="!isConfigurableApp" class="connector-form-card connector-default-endpoint-card">
            <div class="connector-default-head">
              <div>
                <p class="eyebrow">Default Connector Endpoint</p>
                <strong>Use Moonshot endpoint fields for this connector type.</strong>
              </div>
              <n-tag round type="info">built-in connector</n-tag>
            </div>
            <n-form label-placement="top">
              <n-form-item label="Name"><n-input v-model:value="form.name" /></n-form-item>
              <div class="connector-inline-fields">
                <n-form-item label="Request URL"><n-input v-model:value="form.uri" placeholder="Leave empty when the connector uses environment defaults" /></n-form-item>
                <n-form-item label="Model"><n-input v-model:value="form.model" placeholder="gpt-4o, qwen-plus, claude..." /></n-form-item>
              </div>
              <n-form-item label="Token / API Key"><n-input v-model:value="form.token" type="password" show-password-on="click" placeholder="Leave empty when using environment variables" /></n-form-item>
              <div class="connector-inline-fields">
                <n-form-item label="Max Calls Per Second"><n-input-number v-model:value="form.max_calls_per_second" :min="1" /></n-form-item>
                <n-form-item label="Max Concurrency"><n-input-number v-model:value="form.max_concurrency" :min="1" /></n-form-item>
              </div>
              <n-form-item label="Params JSON">
                <textarea v-model="defaultParamsText" class="connector-code-textarea" spellcheck="false" @blur="syncDefaultParams" />
              </n-form-item>
            </n-form>
          </div>

          <n-tabs v-else v-model:value="activeTab" type="segment">
            <n-tab-pane name="basic" tab="Basic">
              <div class="connector-form-card">
                <n-form label-placement="top">
                  <n-form-item label="Name"><n-input v-model:value="form.name" /></n-form-item>
                  <n-form-item label="Description"><n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" /></n-form-item>
                  <n-form-item label="Request URL"><n-input v-model:value="form.uri" placeholder="http://10.255.25.153:5000/chat" /></n-form-item>
                  <div class="connector-inline-fields">
                    <n-form-item label="Model / Deployment (optional)"><n-input v-model:value="form.model" placeholder="custom-model" /></n-form-item>
                    <n-form-item label="Timeout (seconds)"><n-input-number v-model:value="form.params.timeout" :min="1" :max="120" /></n-form-item>
                  </div>
                  <div class="connector-inline-fields">
                    <n-form-item label="Max Calls Per Second"><n-input-number v-model:value="form.max_calls_per_second" :min="1" /></n-form-item>
                    <n-form-item label="Max Concurrency"><n-input-number v-model:value="form.max_concurrency" :min="1" /></n-form-item>
                  </div>
                </n-form>
              </div>
            </n-tab-pane>

            <n-tab-pane name="auth" tab="Auth">
              <div class="connector-form-card connector-headers-card">
                <div class="connector-default-head">
                  <div>
                    <p class="eyebrow">Request Headers</p>
                    <strong>Configure authentication and any additional headers sent with every request.</strong>
                  </div>
                  <n-tag round type="info">{{ headerEntries.length }} custom</n-tag>
                </div>
                <section class="connector-auth-panel">
                  <div class="connector-section-heading">
                    <div>
                      <strong>Authentication</strong>
                      <span>Choose one authentication method. Credentials are stored separately from custom headers.</span>
                    </div>
                  </div>
                  <div class="connector-header-presets" aria-label="Authentication presets">
                    <button type="button" :class="{ active: form.params.connector_config.auth.type === 'bearer' }" @click="applyHeaderPreset('bearer')"><strong>Bearer Token</strong><span>Authorization header</span></button>
                    <button type="button" :class="{ active: form.params.connector_config.auth.type === 'api-key' }" @click="applyHeaderPreset('x-api-key')"><strong>API Key</strong><span>x-api-key header</span></button>
                    <button type="button" :class="{ active: form.params.connector_config.auth.type === 'cookie' }" @click="applyHeaderPreset('cookie')"><strong>Cookie</strong><span>Session cookie</span></button>
                  </div>
                  <n-form class="connector-auth-form" label-placement="top">
                    <div class="connector-auth-fields">
                      <n-form-item label="Authentication Type">
                        <n-select
                          :value="form.params.connector_config.auth.type"
                          :options="authOptions"
                          @update:value="setAuthType(String($event))"
                        />
                      </n-form-item>
                      <n-form-item v-if="usesAuthHeader" label="Header Name">
                        <n-input v-model:value="form.params.connector_config.auth.headerName" :placeholder="defaultAuthHeader" />
                      </n-form-item>
                      <n-form-item v-if="form.params.connector_config.auth.type === 'basic'" label="Username">
                        <n-input v-model:value="form.params.connector_config.auth.username" autocomplete="username" />
                      </n-form-item>
                      <n-form-item v-if="form.params.connector_config.auth.type !== 'none'" :label="authSecretLabel">
                        <n-input v-model:value="form.token" type="password" show-password-on="click" autocomplete="new-password" placeholder="Enter credential" />
                      </n-form-item>
                    </div>
                  </n-form>
                </section>

                <section class="connector-custom-headers-panel">
                  <div class="connector-section-heading connector-section-heading-with-count">
                    <div>
                      <strong>Custom Headers</strong>
                      <span>Add fixed metadata such as tenant, version, or tracing headers.</span>
                    </div>
                    <span>{{ headerEntries.length }} configured</span>
                  </div>
                  <n-form class="connector-custom-header-form" label-placement="top">
                    <n-form-item label="Header Name"><n-input v-model:value="customHeaderName" placeholder="x-tenant-id" /></n-form-item>
                    <n-form-item label="Header Value"><n-input v-model:value="customHeaderValue" placeholder="tenant-demo" /></n-form-item>
                    <n-button type="primary" secondary round :disabled="!customHeaderName.trim()" @click="addCustomHeader">Add Header</n-button>
                  </n-form>
                  <div class="connector-header-list">
                    <div class="connector-header-list-head">
                      <strong>Name</strong>
                      <span>Value</span>
                    </div>
                    <div v-if="headerEntries.length" class="connector-header-items">
                      <article v-for="header in headerEntries" :key="header.name">
                        <div>
                          <strong>{{ header.name }}</strong>
                          <n-input
                            v-if="editingHeaderName === header.name"
                            v-model:value="editingHeaderValue"
                            size="small"
                            @blur="saveHeaderEdit"
                            @keyup.enter="saveHeaderEdit"
                            @keyup.esc="cancelHeaderEdit"
                          />
                          <span v-else class="connector-header-editable-value" title="Double-click to edit" @dblclick="startHeaderEdit(header.name, header.value)">{{ header.value }}</span>
                        </div>
                        <n-button quaternary circle size="small" @click="removeHeader(header.name)">x</n-button>
                      </article>
                    </div>
                    <div v-else class="connector-header-empty">
                      <strong>No custom headers yet</strong>
                      <span>Authentication headers are managed above and do not need to be added again.</span>
                    </div>
                  </div>
                </section>
              </div>
            </n-tab-pane>

            <n-tab-pane name="request" tab="Request">
              <div class="connector-form-card connector-mapping-workspace">
                <div class="connector-request-response-grid">
                  <section class="connector-request-column">
                    <template v-if="form.params.connector_config.transport === 'http' && form.params.connector_config.request">
                      <div class="connector-mapping-layout">
                        <div class="connector-mapping-card connector-input-mapping-card">
                          <div class="connector-mapping-head">
                            <div>
                              <p class="eyebrow">Input mapping</p>
                              <strong>{{ httpInputTitle }}</strong>
                            </div>
                            <n-button secondary round size="small" @click="markPromptSelection">Use selected value as input</n-button>
                          </div>
                          <n-form class="connector-mapping-controls" label-placement="top">
                            <div class="connector-inline-fields connector-method-row">
                              <n-form-item label="Method">
                                <n-select
                                  :value="form.params.connector_config.request.method"
                                  :options="methodOptions"
                                  @update:value="setHttpMethod(String($event))"
                                />
                              </n-form-item>
                              <n-form-item v-if="!isHttpGet" label="Body Type">
                                <n-select
                                  :value="form.params.connector_config.request.bodyType"
                                  :options="bodyTypeOptionsWithoutNone"
                                  @update:value="setHttpBodyType(String($event))"
                                />
                              </n-form-item>
                            </div>
                            <n-form-item v-if="!isHttpGet" label="URL Query Params (optional)">
                              <n-input v-model:value="queryParamsText" placeholder="api-version=v1&amp;tenant=demo" @blur="syncQueryParams" />
                            </n-form-item>
                          </n-form>
                          <div
                            v-if="isHttpKeyValueBody"
                            ref="queryParamsRef"
                            class="connector-token-editor"
                            contenteditable="true"
                            spellcheck="false"
                            :data-placeholder="'input=hi&role=user'"
                            v-html="renderPromptTokens(keyValueBodyText)"
                            @click="handleTokenEditorClick"
                            @blur="syncKeyValueEditorAndBody"
                          ></div>
                          <div
                            v-else
                            ref="requestBodyRef"
                            class="connector-token-editor"
                            contenteditable="true"
                            spellcheck="false"
                            v-html="renderPromptTokens(form.params.connector_config.request.bodyTemplate)"
                            @click="handleTokenEditorClick"
                            @blur="syncRequestBodyEditor"
                          ></div>
                        </div>
                      </div>
                    </template>
                    <template v-else-if="form.params.connector_config.transport === 'sse' && form.params.connector_config.stream">
                      <div class="connector-mapping-layout">
                        <div class="connector-mapping-card connector-input-mapping-card">
                          <div class="connector-mapping-head">
                            <div>
                              <p class="eyebrow">Input mapping</p>
                              <strong>{{ streamInputTitle }}</strong>
                            </div>
                            <n-button secondary round size="small" @click="markPromptSelection">Use selected value as input</n-button>
                          </div>
                          <n-form class="connector-mapping-controls" label-placement="top">
                            <div class="connector-inline-fields connector-method-row">
                              <n-form-item label="Method">
                                <n-select :value="form.params.connector_config.stream.method" :options="sseMethodOptions" @update:value="setSseMethod(String($event))" />
                              </n-form-item>
                              <n-form-item v-if="!isSseGet" label="Body Type">
                                <n-select :value="form.params.connector_config.stream.bodyType" :options="bodyTypeOptionsWithoutNone" @update:value="setSseBodyType(String($event))" />
                              </n-form-item>
                            </div>
                            <n-form-item v-if="!isSseGet" label="URL Query Params (optional)">
                              <n-input v-model:value="queryParamsText" placeholder="stream=true&amp;tenant=demo" @blur="syncQueryParams" />
                            </n-form-item>
                          </n-form>
                          <div
                            v-if="isSseKeyValueBody"
                            ref="queryParamsRef"
                            class="connector-token-editor"
                            contenteditable="true"
                            spellcheck="false"
                            :data-placeholder="'input=hi&role=user'"
                            v-html="renderPromptTokens(keyValueBodyText)"
                            @click="handleTokenEditorClick"
                            @blur="syncKeyValueEditorAndBody"
                          ></div>
                          <div
                            v-else
                            ref="requestBodyRef"
                            class="connector-token-editor"
                            contenteditable="true"
                            spellcheck="false"
                            v-html="renderPromptTokens(form.params.connector_config.stream.bodyTemplate || '')"
                            @click="handleTokenEditorClick"
                            @blur="syncRequestBodyEditor"
                          ></div>
                        </div>
                      </div>
                    </template>
                    <template v-else-if="form.params.connector_config.websocket">
                      <div class="connector-mapping-layout">
                        <div class="connector-mapping-card connector-input-mapping-card">
                          <div class="connector-mapping-head">
                            <div>
                              <p class="eyebrow">Input mapping</p>
                              <strong>Paste the WebSocket message payload</strong>
                            </div>
                            <n-button secondary round size="small" @click="markPromptSelection">Use selected value as input</n-button>
                          </div>
                          <n-form class="connector-mapping-controls" label-placement="top">
                            <n-form-item label="URL Query Params">
                              <n-input v-model:value="queryParamsText" placeholder="session=demo&amp;stream=true" @blur="syncQueryParams" />
                            </n-form-item>
                          </n-form>
                          <div
                            ref="requestBodyRef"
                            class="connector-token-editor"
                            contenteditable="true"
                            spellcheck="false"
                            v-html="renderPromptTokens(form.params.connector_config.websocket.messageTemplate)"
                            @click="handleTokenEditorClick"
                            @blur="syncRequestBodyEditor"
                          ></div>
                        </div>
                      </div>
                    </template>
                  </section>

                  <section class="connector-response-column">
                    <div class="connector-mapping-card">
                      <div class="connector-mapping-head">
                        <div>
                          <p class="eyebrow">Output mapping</p>
                          <strong>Paste any response sample and select the answer value</strong>
                        </div>
                        <n-button secondary round size="small" @click="markOutputSelection">Use selected value as output</n-button>
                      </div>
                      <div
                        ref="responseBodyRef"
                        class="connector-token-editor"
                        contenteditable="true"
                        spellcheck="false"
                        v-html="renderOutputTokens(sampleResponse)"
                        @click="handleTokenEditorClick"
                        @blur="syncResponseEditor"
                      ></div>
                    </div>
                  </section>
                </div>
              </div>
            </n-tab-pane>

            <n-tab-pane name="test" tab="Fetch Response">
              <div class="connector-form-card connector-test-card">
                <div class="connector-default-head">
                  <div>
                    <p class="eyebrow">Live Request</p>
                    <strong>Send a real request and load its response into Output Mapping.</strong>
                  </div>
                  <n-tag round :type="activeProtocol === 'websocket' ? 'success' : activeProtocol === 'sse' ? 'warning' : 'info'">{{ activeProtocol.toUpperCase() }}</n-tag>
                </div>
                <n-input v-model:value="testPrompt" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" placeholder="Prompt sent in place of the input token" />
                <n-button type="primary" round :loading="testing" :disabled="!form.uri.trim()" @click="fetchResponse">Fetch Response</n-button>
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
      </div>
    </GlassPanel>

    <n-modal
      v-model:show="aiModalOpen"
      :mask-closable="!aiGenerating"
      :close-on-esc="!aiGenerating"
      transform-origin="center"
    >
      <n-card class="connector-ai-modal" :bordered="false" size="huge" role="dialog" aria-modal="true">
        <div class="connector-ai-modal-head">
          <span class="connector-ai-modal-icon"><n-icon size="24"><SparklesOutline /></n-icon></span>
          <div>
            <p class="eyebrow">AI Connector Setup</p>
            <h3>Generate configuration from request information</h3>
            <span>AI will fill the endpoint, map the input, send a real request, and select the response output.</span>
          </div>
          <n-tag round :type="aiModelConfigured ? 'success' : 'warning'">{{ activeAIModelLabel }}</n-tag>
        </div>

        <n-alert v-if="!aiModelConfigured" type="warning" title="AI model is not ready">
          Configure the active model and API key in Settings &gt; AI settings before generating.
        </n-alert>

        <div class="connector-ai-paste-guide">
          <div>
            <strong>Paste the most complete request information you have</strong>
            <span>Use any format you like—cURL, raw HTTP, JSON, API documentation, or plain-language notes. The format does not matter as long as the information is complete.</span>
          </div>
          <span>{{ aiRequestInfo.length.toLocaleString() }} / 50,000</span>
        </div>
        <n-input
          v-model:value="aiRequestInfo"
          class="connector-ai-request-input"
          type="textarea"
          :rows="13"
          :maxlength="50000"
          :placeholder="AI_REQUEST_PLACEHOLDER"
          :disabled="aiGenerating"
        />

        <div v-if="aiGenerating" class="connector-ai-progress" aria-live="polite">
          <n-spin size="small" />
          <div>
            <strong>AI is configuring and verifying this connector</strong>
            <span>All endpoint settings are locked until analysis, request testing, and response mapping finish.</span>
          </div>
          <div class="connector-ai-progress-steps" aria-hidden="true">
            <span>Analyze request</span><span>Fill fields</span><span>Send request</span><span>Map output</span>
          </div>
        </div>

        <div class="connector-ai-modal-actions">
          <n-button secondary round :disabled="aiGenerating" @click="aiModalOpen = false">Cancel</n-button>
          <n-button class="connector-ai-generate-button" type="primary" round :loading="aiGenerating" :disabled="!canGenerateWithAI" @click="generateWithAI">
            <template #icon><n-icon><SparklesOutline /></n-icon></template>
            {{ aiGenerating ? 'Generating and testing…' : 'Generate Configuration' }}
          </n-button>
        </div>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { NTabPane, NTabs, useMessage, useNotification } from 'naive-ui'
import { SparklesOutline } from '@vicons/ionicons5'
import { useRoute, useRouter } from 'vue-router'
import GlassPanel from '../../../components/GlassPanel.vue'
import { CONFIGURABLE_CONNECTOR, applyTemplate, connectorService, currentUser, defaultConnectorConfig, endpointToConfig } from '../../../services/connectorService'
import type { AuthType, ConnectorAIConfigureResult, ConnectorConfig, ConnectorProtocol, ConnectorTestResult } from '../../../types/connector'
import { useMoonshotStore } from '../../../stores/moonshot'
import { useSettingsStore } from '../../../stores/settings'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const notification = useNotification()
const store = useMoonshotStore()
const settingsStore = useSettingsStore()
const editingId = computed(() => String(route.params.id || ''))
const form = reactive<ConnectorConfig>(defaultConnectorConfig('http'))
const activeTab = ref('basic')
const guideOpen = ref(false)
const permissionDenied = ref(false)
const testing = ref(false)
const aiModalOpen = ref(false)
const aiGenerating = ref(false)
const AI_REQUEST_PLACEHOLDER = `Paste request information in any format. Include as much as possible:

1. Endpoint URL and protocol (HTTP, SSE, or WebSocket)
2. Method, headers, query parameters, authentication, and request body
3. Which value should be replaced by the user's input
4. A safe test input
5. A successful response example and the field containing the answer

Examples: cURL, raw HTTP, JSON, API documentation, or plain-language notes. Any format is fine as long as the information is complete.`
const aiRequestInfo = ref('')
const testPrompt = ref('Hello')
const testResult = ref<ConnectorTestResult | null>(null)
const requestBodyRef = ref<HTMLElement | null>(null)
const queryParamsRef = ref<HTMLElement | null>(null)
const responseBodyRef = ref<HTMLElement | null>(null)
const headersText = ref('{\n  "content-type": "application/json"\n}')
const queryParamsText = ref('{\n  "prompt": "{{ prompt }}"\n}')
const formFieldsText = ref('{\n  "message": "{{ prompt }}"\n}')
const keyValueBodyText = ref('input=hi&role=user')
const defaultParamsText = ref('{}')
const sampleResponse = ref('{\n  "blocked": false,\n  "response": "Hi! How can I assist you today?"\n}')
const outputTokenLabel = ref('response')
const promptToken = '{{ prompt }}'
const customHeaderName = ref('')
const customHeaderValue = ref('')
const editingHeaderName = ref('')
const editingHeaderValue = ref('')
const activeProtocol = computed(() => form.params.connector_config.transport)
const isConfigurableApp = computed(() => form.connector_type === CONFIGURABLE_CONNECTOR)
const activeRequestConfig = computed(() => {
  const config = form.params.connector_config
  if (config.transport === 'http') return config.request
  if (config.transport === 'sse') return config.stream
  return config.websocket
})
const isHttpGet = computed(() => form.params.connector_config.transport === 'http' && form.params.connector_config.request?.method === 'GET')
const isHttpFormBody = computed(() => form.params.connector_config.transport === 'http' && form.params.connector_config.request?.bodyType === 'form')
const isSseGet = computed(() => form.params.connector_config.transport === 'sse' && form.params.connector_config.stream?.method === 'GET')
const isSseFormBody = computed(() => form.params.connector_config.transport === 'sse' && form.params.connector_config.stream?.bodyType === 'form')
const isWebSocket = computed(() => form.params.connector_config.transport === 'websocket')
const isHttpKeyValueBody = computed(() => isHttpGet.value || isHttpFormBody.value)
const isSseKeyValueBody = computed(() => isSseGet.value || isSseFormBody.value)
const isKeyValueEditorActive = computed(() => isHttpKeyValueBody.value || isSseKeyValueBody.value)
const httpInputTitle = computed(() => {
  if (isHttpGet.value) return 'Paste the full URL Query Params'
  if (isHttpFormBody.value) return 'Paste the full Form Body'
  return 'Paste the full request body'
})
const streamInputTitle = computed(() => {
  if (isSseGet.value) return 'Paste the full URL Query Params'
  if (isSseFormBody.value) return 'Paste the full Form Body'
  return 'Paste the full stream request body'
})
const headerEntries = computed(() => Object.entries(parseHeadersText()).map(([name, value]) => ({ name, value })))
const usesAuthHeader = computed(() => ['bearer', 'api-key', 'cookie'].includes(form.params.connector_config.auth.type))
const defaultAuthHeader = computed(() => {
  const type = form.params.connector_config.auth.type
  if (type === 'api-key') return 'x-api-key'
  if (type === 'cookie') return 'Cookie'
  return 'Authorization'
})
const authSecretLabel = computed(() => form.params.connector_config.auth.type === 'basic' ? 'Password' : 'Token / API Key')
const activeAIModelLabel = computed(() => {
  const ai = settingsStore.ai
  if (!ai) return 'Loading AI model…'
  const providerId = ai.activeProvider
  const label = ai.catalog[providerId]?.label || providerId || 'AI model'
  const model = ai.providers[providerId]?.model || ''
  return model ? `${label} · ${model}` : label
})
const aiModelConfigured = computed(() => {
  const ai = settingsStore.ai
  if (!ai) return false
  return Boolean(ai.providers[ai.activeProvider]?.apiKeyConfigured)
})
const canGenerateWithAI = computed(() => (
  !aiGenerating.value
  && aiModelConfigured.value
  && aiRequestInfo.value.trim().length > 20
))

const methodOptions = ['GET', 'POST', 'PUT', 'PATCH'].map((value) => ({ label: value, value }))
const sseMethodOptions = ['GET', 'POST'].map((value) => ({ label: value, value }))
const authOptions = [
  { label: 'None', value: 'none' },
  { label: 'Bearer Token', value: 'bearer' },
  { label: 'API Key', value: 'api-key' },
  { label: 'Cookie', value: 'cookie' },
  { label: 'Basic Auth', value: 'basic' },
]
const bodyTypeOptions = [
  { label: 'JSON body', value: 'json' },
  { label: 'Form body', value: 'form' },
  { label: 'Raw body', value: 'raw' },
  { label: 'No body', value: 'none' },
]
const bodyTypeOptionsWithoutNone = bodyTypeOptions.filter((option) => option.value !== 'none')
const canSave = computed(() => form.name.trim() && (isConfigurableApp.value ? form.uri.trim() : true) && !permissionDenied.value && !aiGenerating.value)

onMounted(async () => {
  const draft = window.sessionStorage.getItem('oxo-connector-draft')
  if (draft && !editingId.value) {
    Object.assign(form, JSON.parse(draft))
    syncAllTextFields()
    window.sessionStorage.removeItem('oxo-connector-draft')
    return
  }
  const connectorType = String(route.query.connector_type || '')
  if (!editingId.value) {
    if (connectorType) form.connector_type = connectorType
    if (connectorType && connectorType !== CONFIGURABLE_CONNECTOR) applyDefaultEndpointTemplate(connectorType)
    syncAllTextFields()
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
  if (form.connector_type !== CONFIGURABLE_CONNECTOR && !endpoint) applyDefaultEndpointTemplate(form.connector_type)
  syncAllTextFields()
})

function setProtocol(protocol: ConnectorProtocol) {
  Object.assign(form, applyTemplate(form, protocol))
  syncAllTextFields()
}

function loadTemplate(protocol: ConnectorProtocol) {
  setProtocol(protocol)
  message.success(`${protocol.toUpperCase()} template loaded`)
}

async function openAIAssistant() {
  if (!settingsStore.ai && !settingsStore.loading) {
    try {
      await settingsStore.loadSettings()
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Unable to load the active AI model.')
    }
  }
  aiModalOpen.value = true
}

async function generateWithAI() {
  if (!canGenerateWithAI.value) {
    if (!aiModelConfigured.value) {
      message.error('Configure the active AI model and API key in Settings > AI settings first.')
    } else {
      message.warning('Paste a real request example before generating the connector configuration.')
    }
    return
  }
  aiGenerating.value = true
  try {
    const result = await connectorService.configureWithAI(aiRequestInfo.value)
    await applyAIConfiguration(result)
    aiModalOpen.value = false
    if (result.status === 'completed') {
      activeTab.value = 'request'
      message.success(`AI configured and verified this endpoint with ${result.model || 'the active model'}.`, {
        duration: 7000,
        closable: true,
      })
    } else {
      notifyAIConfigurationFailure(result)
    }
  } catch (error) {
    notification.error({
      title: 'AI configuration failed',
      content: error instanceof Error ? error.message : 'AI configuration failed. Existing fields were kept.',
      duration: 14000,
      keepAliveOnHover: true,
    })
  } finally {
    aiGenerating.value = false
  }
}

async function applyAIConfiguration(result: ConnectorAIConfigureResult) {
  if (result.config) {
    Object.assign(form, result.config)
    syncAllTextFields()
  }
  testPrompt.value = result.testPrompt || testPrompt.value
  if (result.testResult) {
    testResult.value = result.testResult
    if (result.testResult.rawResponse) {
      const formatted = formatResponseSample(result.testResult.rawResponse)
      const responseConfig = result.config?.params.connector_config.response
      const selected = responseConfig?.selectedText || result.testResult.extractedResponse
      sampleResponse.value = insertGeneratedOutputToken(formatted, selected)
      outputTokenLabel.value = responseConfig?.path?.split('.').at(-1) || 'response'
    }
  }
  await nextTick()
}

function insertGeneratedOutputToken(sample: string, selected: string | undefined) {
  const value = String(selected || '')
  if (!value) return sample
  const directIndex = sample.indexOf(value)
  if (directIndex >= 0) return `${sample.slice(0, directIndex)}{{ output }}${sample.slice(directIndex + value.length)}`
  const encoded = JSON.stringify(value).slice(1, -1)
  const encodedIndex = sample.indexOf(encoded)
  if (encodedIndex >= 0) return `${sample.slice(0, encodedIndex)}{{ output }}${sample.slice(encodedIndex + encoded.length)}`
  return sample
}

function notifyAIConfigurationFailure(result: ConnectorAIConfigureResult) {
  const needs = result.missingInformation.filter(Boolean)
  const detail = needs.length ? ` Needed: ${needs.join(' ')}` : ''
  notification.error({
    title: 'AI configuration needs more information',
    content: `${result.message}${detail}`,
    duration: 14000,
    keepAliveOnHover: true,
  })
}

function setHttpMethod(method: string) {
  const request = form.params.connector_config.request
  if (!request) return
  request.method = method as typeof request.method
  if (method === 'GET') {
    request.bodyType = 'none'
    if (!Object.keys(request.queryParams || {}).length) {
      request.queryParams = { input: 'hi', role: 'user' }
    }
  } else if (request.bodyType === 'none') {
    request.bodyType = 'json'
  }
  syncQueryParamsText()
  syncFormFieldsText()
}

function setHttpBodyType(bodyType: string) {
  const request = form.params.connector_config.request
  if (!request) return
  request.bodyType = bodyType as typeof request.bodyType
  if (bodyType === 'form') {
    request.formFields ||= { input: 'hi', role: 'user' }
    keyValueBodyText.value = toQueryString(request.formFields) || 'input=hi&role=user'
  }
}

function setSseMethod(method: string) {
  const stream = form.params.connector_config.stream
  if (!stream) return
  stream.method = method as typeof stream.method
  if (method === 'GET') {
    stream.bodyType = 'none'
    if (!Object.keys(stream.queryParams || {}).length) {
      stream.queryParams = { input: 'hi', role: 'user' }
    }
  } else if (stream.bodyType === 'none') {
    stream.bodyType = 'json'
  }
  if (method !== 'GET' && !stream.bodyTemplate) stream.bodyTemplate = '{"message":"{{ prompt }}"}'
  syncQueryParamsText()
  syncFormFieldsText()
}

function setSseBodyType(bodyType: string) {
  const stream = form.params.connector_config.stream
  if (!stream) return
  stream.bodyType = bodyType as typeof stream.bodyType
  if (bodyType === 'form') {
    stream.formFields ||= { input: 'hi', role: 'user' }
    keyValueBodyText.value = toQueryString(stream.formFields) || 'input=hi&role=user'
  } else if (!stream.bodyTemplate) {
    stream.bodyTemplate = bodyType === 'raw' ? '{{ prompt }}' : '{"message":"{{ prompt }}"}'
  }
}

function setAuthType(type: string) {
  const auth = form.params.connector_config.auth
  auth.type = type as AuthType
  auth.headerName = type === 'api-key' ? 'x-api-key' : type === 'cookie' ? 'Cookie' : type === 'none' || type === 'basic' ? undefined : 'Authorization'
}

function applyHeaderPreset(kind: 'bearer' | 'x-api-key' | 'cookie') {
  if (kind === 'bearer') {
    setAuthType('bearer')
  }
  if (kind === 'x-api-key') {
    setAuthType('api-key')
  }
  if (kind === 'cookie') {
    setAuthType('cookie')
  }
  message.success('Authentication preset selected. Enter the credential above.')
}

function addCustomHeader() {
  if (!customHeaderName.value.trim()) {
    message.warning('Enter a custom header name first.')
    return
  }
  const headers = parseHeadersText()
  headers[customHeaderName.value.trim()] = customHeaderValue.value
  setHeaders(headers)
  customHeaderName.value = ''
  customHeaderValue.value = ''
}

function removeHeader(name: string) {
  const headers = parseHeadersText()
  delete headers[name]
  setHeaders(headers)
}

function startHeaderEdit(name: string, value: string) {
  editingHeaderName.value = name
  editingHeaderValue.value = value
}

function saveHeaderEdit() {
  if (!editingHeaderName.value) return
  const headers = parseHeadersText()
  headers[editingHeaderName.value] = editingHeaderValue.value
  setHeaders(headers)
  editingHeaderName.value = ''
  editingHeaderValue.value = ''
}

function cancelHeaderEdit() {
  editingHeaderName.value = ''
  editingHeaderValue.value = ''
}

async function saveConnector() {
  if (!canSave.value) return
  if (isConfigurableApp.value) {
    syncEditorFields()
    syncKeyValueBody()
    syncHeaders()
    syncQueryParams()
    syncFormFields()
  } else {
    syncDefaultParams()
  }
  if (isConfigurableApp.value && !validateConnectorConfiguration()) return
  form.source = 'user-created'
  form.ownerId = currentUser.id
  form.ownerName = currentUser.name
  const saved = await connectorService.saveConnector({ ...form, id: form.id })
  await store.loadOverview()
  message.success('Connector endpoint saved')
  router.push(`/agents/connectors/${encodeURIComponent(form.connector_type)}`)
  void saved
}

function goBack() {
  const connectorType = form.connector_type || String(route.query.connector_type || '')
  if (connectorType) router.push(`/agents/connectors/${encodeURIComponent(connectorType)}`)
  else router.push('/agents/connectors')
}

async function fetchResponse() {
  syncEditorFields()
  syncKeyValueBody()
  syncHeaders()
  syncQueryParams()
  syncFormFields()
  if (!validateConnectorConfiguration()) return
  testing.value = true
  try {
    testResult.value = await connectorService.testConnector(form, testPrompt.value)
    if (testResult.value.rawResponse) {
      sampleResponse.value = formatResponseSample(testResult.value.rawResponse)
      outputTokenLabel.value = 'response'
      activeTab.value = 'request'
      message.success('Response loaded into Output Mapping. Select the AI answer value next.')
    } else if (testResult.value.error) {
      message.error(testResult.value.error)
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Failed to fetch response.')
  } finally {
    testing.value = false
  }
}

function validateConnectorConfiguration() {
  const protocol = form.params.connector_config.transport
  let parsedUrl: URL
  try {
    parsedUrl = new URL(form.uri.trim())
  } catch {
    message.error('Enter a complete request URL.')
    activeTab.value = 'basic'
    return false
  }
  const allowedSchemes = protocol === 'websocket' ? ['ws:', 'wss:'] : ['http:', 'https:']
  if (!allowedSchemes.includes(parsedUrl.protocol)) {
    message.error(protocol === 'websocket' ? 'WebSocket URLs must use ws:// or wss://.' : 'HTTP and SSE URLs must use http:// or https://.')
    activeTab.value = 'basic'
    return false
  }

  const auth = form.params.connector_config.auth
  if (auth.type !== 'none' && !form.token.trim()) {
    message.error(auth.type === 'basic' ? 'Enter the Basic Auth password.' : 'Enter the authentication token or API key.')
    activeTab.value = 'auth'
    return false
  }
  if (auth.type === 'basic' && !auth.username?.trim()) {
    message.error('Enter the Basic Auth username.')
    activeTab.value = 'auth'
    return false
  }

  const promptSources: string[] = []
  const requestConfig = activeRequestConfig.value
  if (requestConfig?.queryParams) promptSources.push(...Object.values(requestConfig.queryParams))
  if (requestConfig && 'formFields' in requestConfig && requestConfig.formFields) promptSources.push(...Object.values(requestConfig.formFields))
  if (requestConfig && 'bodyTemplate' in requestConfig && requestConfig.bodyTemplate) promptSources.push(requestConfig.bodyTemplate)
  if (requestConfig && 'messageTemplate' in requestConfig && requestConfig.messageTemplate) promptSources.push(requestConfig.messageTemplate)
  if (!promptSources.some((value) => /\{\{\s*prompt\s*\}\}/.test(String(value)))) {
    message.error('Map {{ prompt }} into the query, form, request body, or WebSocket message before continuing.')
    activeTab.value = 'request'
    return false
  }
  return true
}

function formatResponseSample(raw: string) {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
}

function syncAllTextFields() {
  if (isConfigurableApp.value) {
    syncHeadersText()
    syncQueryParamsText()
    syncFormFieldsText()
  } else {
    syncDefaultParamsText()
  }
}

function syncEditorFields() {
  if (isWebSocket.value) {
    syncKeyValueEditor()
    syncRequestBodyEditor()
  } else if (isKeyValueEditorActive.value) syncKeyValueEditor()
  else syncRequestBodyEditor()
  syncResponseEditor()
}

function applyDefaultEndpointTemplate(connectorType: string) {
  Object.assign(form, {
    ...form,
    connector_type: connectorType,
    uri: '',
    token: '',
    model: '',
    max_calls_per_second: 1,
    max_concurrency: 1,
    params: {} as ConnectorConfig['params'],
  })
}

function syncDefaultParamsText() {
  defaultParamsText.value = JSON.stringify(form.params || {}, null, 2)
}

function syncDefaultParams() {
  try {
    form.params = parseJsonObject(defaultParamsText.value) as unknown as ConnectorConfig['params']
  } catch {
    message.error('Params must be a valid JSON object.')
  }
}

function syncHeadersText() {
  const headers = activeRequestConfig.value?.headers || { 'content-type': 'application/json' }
  headersText.value = JSON.stringify(headers, null, 2)
}

function syncHeaders() {
  if (!activeRequestConfig.value) return
  activeRequestConfig.value.headers = parseHeadersText()
}

function setHeaders(headers: Record<string, string>) {
  headersText.value = JSON.stringify(headers, null, 2)
  syncHeaders()
}

function syncQueryParamsText() {
  const params = activeRequestConfig.value?.queryParams || {}
  queryParamsText.value = toQueryString(params) || (isHttpGet.value || isSseGet.value ? 'input=hi&role=user' : '')
  if (isHttpGet.value || isSseGet.value || isWebSocket.value) keyValueBodyText.value = queryParamsText.value
}

function syncQueryParams() {
  if (!activeRequestConfig.value) return
  try {
    activeRequestConfig.value.queryParams = parseQueryString(queryParamsText.value)
  } catch {
    message.error('Query params must use key=value pairs, for example input=hi&role=user.')
  }
}

function syncFormFieldsText() {
  formFieldsText.value = JSON.stringify(activeFormFields(), null, 2)
  if (isHttpFormBody.value || isSseFormBody.value) keyValueBodyText.value = toQueryString(activeFormFields()) || 'input=hi&role=user'
}

function syncFormFields() {
  if (isHttpFormBody.value || isSseFormBody.value) return
  const carrier = activeRequestConfig.value
  if (!carrier || !('formFields' in carrier)) return
  try {
    carrier.formFields = parseJsonObject(formFieldsText.value)
  } catch {
    message.error('Form fields must be a valid JSON object.')
  }
}

function syncKeyValueBody() {
  if (isHttpGet.value || isSseGet.value || isWebSocket.value) {
    queryParamsText.value = keyValueBodyText.value
    syncQueryParams()
    return
  }
  if (isHttpFormBody.value || isSseFormBody.value) {
    formFieldsText.value = keyValueBodyText.value
    const carrier = activeRequestConfig.value
    if (carrier && 'formFields' in carrier) carrier.formFields = parseQueryString(keyValueBodyText.value)
  }
}

function parseHeadersText() {
  try {
    return parseJsonObject(headersText.value)
  } catch {
    return {}
  }
}

function parseJsonObject(raw: string) {
  const parsed = JSON.parse(raw || '{}')
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {}
  return parsed as Record<string, string>
}

function activeFormFields() {
  const carrier = activeRequestConfig.value
  if (carrier && 'formFields' in carrier) return carrier.formFields || {}
  return {}
}

function markPromptSelection() {
  const target = isKeyValueEditorActive.value ? queryParamsRef.value : requestBodyRef.value
  if (!target) return
  insertPromptToken(target)
  const next = editorText(target)
  if (isKeyValueEditorActive.value) {
    keyValueBodyText.value = next
    syncKeyValueBody()
  } else {
    setActiveBodyTemplate(next)
  }
  message.success('Input value was replaced with a prompt block.')
  requestAnimationFrame(() => target.focus())
}

function toQueryString(params: Record<string, string>) {
  return Object.entries(params)
    .map(([key, value]) => `${key}=${value}`)
    .join('&')
}

function parseQueryString(raw: string) {
  const query = raw.trim().replace(/^\?/, '')
  if (!query) return {}
  return query.split('&').reduce<Record<string, string>>((acc, pair) => {
    const [rawKey, ...rawValue] = pair.split('=')
    const key = decodeURIComponent(rawKey || '').trim()
    if (!key) return acc
    acc[key] = decodeURIComponent(rawValue.join('=') || '')
    return acc
  }, {})
}

function syncKeyValueEditor() {
  const editor = queryParamsRef.value
  if (!editor) return
  keyValueBodyText.value = editorText(editor)
}

function syncKeyValueEditorAndBody() {
  syncKeyValueEditor()
  syncKeyValueBody()
}

function syncRequestBodyEditor() {
  const editor = requestBodyRef.value
  if (!editor) return
  setActiveBodyTemplate(editorText(editor))
}

function syncResponseEditor() {
  const editor = responseBodyRef.value
  if (!editor) return
  sampleResponse.value = editorText(editor)
}

function renderPromptTokens(value: string) {
  return renderTokens(value, 'prompt')
}

function renderOutputTokens(value: string) {
  return renderTokens(value, 'output')
}

function renderTokens(value: string, type: 'prompt' | 'output') {
  const tokenPattern = type === 'prompt' ? /\{\{\s*prompt\s*\}\}/g : /\{\{\s*output\s*\}\}/g
  let cursor = 0
  let html = ''
  for (const match of value.matchAll(tokenPattern)) {
    const index = match.index || 0
    html += escapeHtml(value.slice(cursor, index))
    const label = type === 'output' ? outputTokenLabel.value : inferTokenLabel(value, index)
    html += `<span class="connector-inline-token" data-token="${type}" contenteditable="false">${escapeHtml(label)}<button type="button" data-token-remove="true">x</button></span>`
    cursor = index + match[0].length
  }
  html += escapeHtml(value.slice(cursor))
  return html
}

function inferTokenLabel(value: string, index: number) {
  const before = value.slice(0, index)
  const queryMatch = before.match(/(?:^|[&?])([^=&\s]+)=[^&]*$/)
  if (queryMatch?.[1]) return queryMatch[1]
  const jsonMatch = before.match(/"([^"]+)"\s*:\s*"?\s*$/)
  if (jsonMatch?.[1]) return jsonMatch[1]
  return 'message'
}

function insertPromptToken(editor: HTMLElement) {
  editor.focus()
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0 || !editor.contains(selection.anchorNode)) {
    editor.append(document.createTextNode(promptToken))
    return
  }
  const range = selection.getRangeAt(0)
  range.deleteContents()
  range.insertNode(document.createTextNode(promptToken))
  range.collapse(false)
  selection.removeAllRanges()
  selection.addRange(range)
}

function editorText(editor: HTMLElement) {
  const clone = editor.cloneNode(true) as HTMLElement
  clone.querySelectorAll<HTMLElement>('.connector-inline-token').forEach((token) => {
    const type = token.dataset.token || 'prompt'
    token.replaceWith(document.createTextNode(type === 'output' ? '{{ output }}' : promptToken))
  })
  return clone.innerText.replace(/\u00a0/g, ' ')
}

function handleTokenEditorClick(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.dataset.tokenRemove) return
  const token = target.closest('.connector-inline-token')
  const editor = target.closest('.connector-token-editor') as HTMLElement | null
  if (!token || !editor) return
  const tokenType = (token as HTMLElement).dataset.token
  token.remove()
  if (editor === queryParamsRef.value) {
    syncKeyValueEditor()
    syncKeyValueBody()
  } else if (editor === requestBodyRef.value) {
    syncRequestBodyEditor()
  } else if (editor === responseBodyRef.value) {
    syncResponseEditor()
    if (tokenType === 'output') form.params.connector_config.response.path = ''
  }
}

function escapeHtml(value: string) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

function setActiveBodyTemplate(value: string) {
  const config = form.params.connector_config
  if (config.transport === 'http' && config.request) config.request.bodyTemplate = value
  if (config.transport === 'sse' && config.stream) config.stream.bodyTemplate = value
  if (config.transport === 'websocket' && config.websocket) config.websocket.messageTemplate = value
}

function markOutputSelection() {
  const target = responseBodyRef.value
  if (!target) return
  const selection = window.getSelection()
  const selected = selection && selection.rangeCount > 0 && target.contains(selection.anchorNode)
    ? selection.toString()
    : ''
  if (!selected) {
    message.warning('Select the response value that should be displayed as the model output.')
    return
  }
  const location = inferResponseLocation(sampleResponse.value, selected)
  if (location.type === 'json-path') {
    form.params.connector_config.response.type = 'json-path'
    form.params.connector_config.response.path = location.path
    form.params.connector_config.response.prefix = undefined
    form.params.connector_config.response.suffix = undefined
    form.params.connector_config.response.selectedText = undefined
    outputTokenLabel.value = location.path.split('.').at(-1) || 'response'
    message.success(`Output path set to ${location.path}`)
  } else {
    form.params.connector_config.response.type = 'text-fragment'
    form.params.connector_config.response.path = ''
    form.params.connector_config.response.prefix = location.prefix
    form.params.connector_config.response.suffix = location.suffix
    form.params.connector_config.response.selectedText = selected
    outputTokenLabel.value = inferOutputLabel(sampleResponse.value, selected)
    message.success('Output text fragment was mapped.')
  }
  insertOutputToken(target)
  sampleResponse.value = editorText(target)
}

function insertOutputToken(editor: HTMLElement) {
  editor.focus()
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0 || !editor.contains(selection.anchorNode)) return
  const range = selection.getRangeAt(0)
  range.deleteContents()
  range.insertNode(document.createTextNode('{{ output }}'))
  range.collapse(false)
  selection.removeAllRanges()
  selection.addRange(range)
}

function findJsonPathBySelection(rawJson: string, selected: string) {
  const normalized = selected.trim().replace(/^"|"$/g, '')
  try {
    const parsed = JSON.parse(rawJson)
    return findPath(parsed, normalized)
  } catch {
    for (const line of rawJson.split(/\r?\n/)) {
      if (!line.startsWith('data:')) continue
      const payload = line.slice(5).trim()
      if (!payload || payload === '[DONE]') continue
      try {
        const path = findPath(JSON.parse(payload), normalized)
        if (path) return path
      } catch {
        continue
      }
    }
    return undefined
  }
}

function inferResponseLocation(raw: string, selected: string) {
  const path = findJsonPathBySelection(raw, selected)
  if (path) return { type: 'json-path' as const, path }
  const selectedIndex = raw.indexOf(selected)
  if (selectedIndex < 0) return { type: 'text-fragment' as const, prefix: '', suffix: '', selectedText: selected }
  return {
    type: 'text-fragment' as const,
    prefix: raw.slice(Math.max(0, selectedIndex - 120), selectedIndex),
    suffix: raw.slice(selectedIndex + selected.length, selectedIndex + selected.length + 120),
    selectedText: selected,
  }
}

function inferOutputLabel(raw: string, selected: string) {
  const index = raw.indexOf(selected)
  if (index < 0) return 'response'
  const before = raw.slice(0, index)
  const jsonKey = before.match(/"([^"]+)"\s*:\s*"?\s*$/)
  if (jsonKey?.[1]) return jsonKey[1]
  const htmlTag = before.match(/<([a-zA-Z][\w:-]*)(?:\s[^>]*)?>[^<]*$/)
  if (htmlTag?.[1]) return htmlTag[1]
  return 'response'
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
