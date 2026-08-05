<template>
  <div class="connector-shell">
    <GlassPanel class="connector-builder-panel" :class="{ 'connector-builder-panel--ai-generating': aiGenerating }">
      <div class="section-heading">
        <div>
          <p class="eyebrow">{{ $t('auto.e9215b5d7bc9') }}</p>
          <h2>{{ editingId ? $t('auto.5b2d286ab27f') : $t('auto.3a50517fa1b3') }}</h2>
        </div>
        <div class="endpoint-heading-actions">
          <n-button v-if="isConfigurableApp" class="connector-ai-button" type="primary" secondary round :loading="aiGenerating" :disabled="permissionDenied" @click="openAIAssistant">
            <template #icon><n-icon><SparklesOutline /></n-icon></template> {{ $t('auto.153f90c699c4') }} </n-button>
          <n-button secondary round @click="goBack">{{ $t('auto.b52b36b7269f') }}</n-button>
          <n-button type="primary" round :disabled="!canSave || aiGenerating" @click="saveConnector">{{ $t('auto.924a634371f5') }}</n-button>
        </div>
      </div>

      <section v-if="aiGenerating" class="connector-ai-workbench-status" role="status" aria-live="polite">
        <span class="connector-ai-workbench-status__orb" aria-hidden="true">
          <n-icon><SparklesOutline /></n-icon>
        </span>
        <div class="connector-ai-workbench-status__copy">
          <p>AI CONFIGURATION IN PROGRESS</p>
          <strong>正在分析、组装并验证端点配置</strong>
          <span>任务已在后台运行；您可以离开此页面，完成后返回即可继续编辑。</span>
        </div>
        <div class="connector-ai-workbench-status__steps" aria-hidden="true">
          <span>解析请求</span><i></i><span>验证响应</span><i></i><span>生成映射</span>
        </div>
        <n-tag round type="info">后台生成中</n-tag>
      </section>

      <n-alert v-if="permissionDenied" type="error" :title="$t('auto.d016004473e0')"> {{ $t('auto.3733a93841a4') }} </n-alert>

      <div v-else class="connector-builder-grid" :class="{ 'connector-builder-grid--locked': aiGenerating }" :inert="aiGenerating" :aria-busy="aiGenerating">
        <section class="connector-builder-main">
          <div class="connector-builder-hero">
            <div>
              <p class="eyebrow">{{ $t('auto.cbf56f96dd38') }}</p>
              <strong>{{ form.connector_type }}</strong>
            </div>
            <div v-if="isConfigurableApp" class="connector-template-actions">
              <n-button :type="activeProtocol === 'http' ? 'primary' : 'default'" secondary round @click="loadTemplate('http')">{{ $t('auto.f63532ff1093') }}</n-button>
              <n-button :type="activeProtocol === 'sse' ? 'primary' : 'default'" secondary round @click="loadTemplate('sse')">{{ $t('auto.0852774752dd') }}</n-button>
              <n-button :type="activeProtocol === 'websocket' ? 'primary' : 'default'" secondary round @click="loadTemplate('websocket')">{{ $t('auto.4642e8d5fd02') }}</n-button>
            </div>
          </div>

          <section v-if="isConfigurableApp" class="connector-guide-collapse">
            <button type="button" class="connector-guide-toggle" @click="guideOpen = !guideOpen">
              <div class="connector-guide-header">
                <span>{{ $t('auto.b36efa76cb30') }}</span>
                <strong>{{ $t('auto.9b94bcfe8e39') }}</strong>
              </div>
              <span class="connector-guide-state">{{ guideOpen ? 'Collapse' : 'Expand' }}</span>
            </button>
            <div v-if="guideOpen" class="connector-guide-body">
              <div class="connector-guide-intro">
                <strong>{{ $t('auto.8a8909c294be') }}</strong>
                <span>{{ $t('auto.ed4c0b0dbc8a') }}</span>
              </div>
              <div class="connector-example-card connector-guide-steps">
                <div>
                  <b>1</b>
                  <strong>URL</strong>
                  <span>{{ $t('auto.d42c1e886657') }}</span>
                  <code>http://10.255.25.153:5000/chat</code>
                </div>
                <div>
                  <b>2</b>
                  <strong>{{ $t('auto.081e8f274703') }}</strong>
                  <span>{{ $t('auto.d935c22a9606') }}</span>
                  <code>Authorization: Bearer &lt;token&gt;</code>
                </div>
                <div>
                  <b>3</b>
                  <strong>{{ $t('auto.a83199228b48') }}</strong>
                  <span>{{ $t('auto.e7e18d0b326c') }}</span>
                  <pre>{ "message": "{{ promptToken }}", "level": 1, "history": [] }</pre>
                </div>
                <div>
                  <b>4</b>
                  <strong>{{ $t('auto.6ac61baf5f41') }}</strong>
                  <span>{{ $t('auto.b9237ff04796') }}</span>
                  <pre>{ "blocked": false, "response": "Hi! How can I assist you today?" }</pre>
                </div>
              </div>
            </div>
          </section>

          <div v-if="!isConfigurableApp" class="connector-form-card connector-default-endpoint-card">
            <div class="connector-default-head">
              <div>
                <p class="eyebrow">{{ $t('auto.991f1723e4b2') }}</p>
                <strong>{{ $t('auto.ec630dbf7d41') }}</strong>
              </div>
              <n-tag round type="info">{{ $t('auto.e1c80d499dd8') }}</n-tag>
            </div>
            <n-form label-placement="top">
              <n-form-item :label="$t('auto.709a23220f2c')"><n-input v-model:value="form.name" /></n-form-item>
              <div class="connector-inline-fields">
                <n-form-item :label="$t('auto.befd91c237b2')"><n-input v-model:value="form.uri" :placeholder="$t('auto.0f3999f2e7ed')" /></n-form-item>
                <n-form-item :label="$t('auto.68c2cc7f0cea')"><n-input v-model:value="form.model" :placeholder="$t('auto.dfc36c695564')" /></n-form-item>
              </div>
              <n-form-item :label="$t('auto.c648d52cb89e')"><n-input v-model:value="form.token" type="password" show-password-on="click" :placeholder="$t('auto.b3b9750ceb01')" /></n-form-item>
              <div class="connector-inline-fields">
                <n-form-item :label="$t('auto.79a345713380')"><n-input-number v-model:value="form.max_calls_per_second" :min="1" /></n-form-item>
                <n-form-item :label="$t('auto.2749013e6731')"><n-input-number v-model:value="form.max_concurrency" :min="1" /></n-form-item>
              </div>
              <n-form-item :label="$t('auto.f24f76edb117')">
                <textarea v-model="defaultParamsText" class="connector-code-textarea" spellcheck="false" @blur="syncDefaultParams" />
              </n-form-item>
            </n-form>
          </div>

          <n-tabs v-else v-model:value="activeTab" type="segment">
            <n-tab-pane name="basic" tab="Basic">
              <div class="connector-form-card">
                <n-form label-placement="top">
                  <n-form-item :label="$t('auto.709a23220f2c')"><n-input v-model:value="form.name" /></n-form-item>
                  <n-form-item :label="$t('auto.55f8ebc805e6')"><n-input v-model:value="form.description" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" /></n-form-item>
                  <n-form-item :label="$t('auto.befd91c237b2')"><n-input v-model:value="form.uri" placeholder="http://10.255.25.153:5000/chat" /></n-form-item>
                  <div class="connector-inline-fields">
                    <n-form-item :label="$t('auto.f47d901be446')"><n-input v-model:value="form.model" :placeholder="$t('auto.293f623bf8a4')" /></n-form-item>
                    <n-form-item :label="$t('auto.e4ea98243df8')"><n-input-number v-model:value="form.params.timeout" :min="1" :max="120" /></n-form-item>
                  </div>
                  <div class="connector-inline-fields">
                    <n-form-item :label="$t('auto.79a345713380')"><n-input-number v-model:value="form.max_calls_per_second" :min="1" /></n-form-item>
                    <n-form-item :label="$t('auto.2749013e6731')"><n-input-number v-model:value="form.max_concurrency" :min="1" /></n-form-item>
                  </div>
                </n-form>
              </div>
            </n-tab-pane>

            <n-tab-pane name="headers" tab="Headers">
              <div class="connector-form-card connector-headers-card">
                <div class="connector-default-head">
                  <div>
                    <p class="eyebrow">{{ $t('auto.8a9b75d51b30') }}</p>
                    <strong>{{ $t('auto.dc75625b3a60') }}</strong>
                  </div>
                  <n-tag round type="info">{{ headerEntries.length }} {{ $t('auto.f9ac14b63a75') }}</n-tag>
                </div>
                <section class="connector-custom-headers-panel">
                  <div class="connector-section-heading connector-section-heading-with-count">
                    <div>
                      <strong>{{ $t('auto.081e8f274703') }}</strong>
                      <span>{{ $t('auto.1b13817dce1b') }}</span>
                    </div>
                    <span>{{ headerEntries.length }} {{ $t('auto.3be9f957f29f') }}</span>
                  </div>
                  <n-form class="connector-custom-header-form" label-placement="top">
                    <n-form-item :label="$t('auto.37d8ce784d80')"><n-input v-model:value="customHeaderName" placeholder="x-tenant-id" /></n-form-item>
                    <n-form-item :label="$t('auto.f6169e2ce081')">
                      <n-input
                        v-model:value="customHeaderValue"
                        :type="isSensitiveHeaderName(customHeaderName) ? 'password' : 'text'"
                        show-password-on="click"
                        :placeholder="$t('auto.88cea605f1c9')"
                      />
                    </n-form-item>
                    <n-button type="primary" secondary round :disabled="!customHeaderName.trim()" @click="addCustomHeader">{{ $t('auto.42b949077d2f') }}</n-button>
                  </n-form>
                  <div class="connector-header-list">
                    <div class="connector-header-list-head">
                      <strong>{{ $t('auto.709a23220f2c') }}</strong>
                      <span>{{ $t('auto.8dce170de238') }}</span>
                    </div>
                    <div v-if="headerEntries.length" class="connector-header-items">
                      <article v-for="header in headerEntries" :key="header.name">
                        <div>
                          <strong>{{ header.name }}</strong>
                          <n-input
                            v-if="editingHeaderName === header.name"
                            v-model:value="editingHeaderValue"
                            size="small"
                            :type="isSensitiveHeaderName(header.name) ? 'password' : 'text'"
                            show-password-on="click"
                            @blur="saveHeaderEdit"
                            @keyup.enter="saveHeaderEdit"
                            @keyup.esc="cancelHeaderEdit"
                          />
                          <span v-else class="connector-header-editable-value" :title="$t('auto.1b1ef72c442d')" @dblclick="startHeaderEdit(header.name, header.value)">{{ displayHeaderValue(header.name, header.value) }}</span>
                        </div>
                        <n-button quaternary circle size="small" @click="removeHeader(header.name)">x</n-button>
                      </article>
                    </div>
                    <div v-else class="connector-header-empty">
                      <strong>{{ $t('auto.c4b7b31826f5') }}</strong>
                      <span>{{ $t('auto.e14070d86453') }}</span>
                    </div>
                  </div>
                </section>
              </div>
            </n-tab-pane>

            <n-tab-pane name="request" tab="Request">
              <div class="connector-form-card connector-mapping-workspace">
                <section class="connector-fetch-card">
                  <div class="connector-fetch-card__head">
                    <div>
                      <p class="eyebrow">{{ $t('auto.b782e1c19f1c') }}</p>
                      <strong>{{ $t('auto.3d9c9a2eebad') }}</strong>
                    </div>
                    <n-tag round :type="activeProtocol === 'websocket' ? 'success' : activeProtocol === 'sse' ? 'warning' : 'info'">{{ activeProtocol.toUpperCase() }}</n-tag>
                  </div>

                  <div class="connector-fetch-row">
                    <n-input
                      v-model:value="testPrompt"
                      :placeholder="$t('auto.07ff42b04dae')"
                      @keyup.enter="fetchResponse"
                    />
                    <n-button type="primary" round :loading="testing" :disabled="!form.uri.trim()" @click="fetchResponse">{{ $t('auto.30d4276ab288') }}</n-button>
                  </div>

                  <div v-if="testResult" class="connector-test-result connector-test-result--compact">
                    <div class="connector-test-result__summary">
                      <n-tag :type="testResult.status === 'success' ? 'success' : 'error'" round size="small">{{ testResult.status }}</n-tag>
                      <span>{{ testResult.duration }}{{ $t('auto.26cc3217be64') }}</span>
                      <span v-if="testResult.rawResponse" class="connector-test-result__destination">{{ $t('auto.c0246c09f896') }}</span>
                    </div>

                    <button
                      type="button"
                      class="connector-request-preview-toggle"
                      :aria-expanded="requestPreviewOpen"
                      @click="requestPreviewOpen = !requestPreviewOpen"
                    >
                      <span>
                        <n-icon><CodeSlashOutline /></n-icon> {{ $t('auto.c8a14f4451e9') }} </span>
                      <n-icon class="connector-request-preview-toggle__chevron" :class="{ 'is-open': requestPreviewOpen }"><ChevronDownOutline /></n-icon>
                    </button>
                    <pre v-if="requestPreviewOpen" class="connector-request-preview-code">{{ testResult.requestPreview }}</pre>

                    <div v-if="testResult.error" class="connector-test-error">
                      <strong>{{ $t('auto.7f2f6a15cf8d') }}</strong>
                      <pre>{{ testResult.error }}</pre>
                    </div>
                  </div>
                </section>

                <div class="connector-request-response-grid">
                  <section class="connector-request-column">
                    <template v-if="form.params.connector_config.transport === 'http' && form.params.connector_config.request">
                      <div class="connector-mapping-layout">
                        <div class="connector-mapping-card connector-input-mapping-card">
                          <div class="connector-mapping-head">
                            <div>
                              <p class="eyebrow">{{ $t('auto.e48882e558ed') }}</p>
                              <strong>{{ httpInputTitle }}</strong>
                            </div>
                            <n-button class="connector-selection-action" secondary round size="small" @mousedown.prevent @click="markPromptSelection">
                              <template #icon><n-icon><LocateOutline /></n-icon></template>
                              {{ $t('auto.bf958ba7624d') }}
                            </n-button>
                          </div>
                          <n-form class="connector-mapping-controls" label-placement="top">
                            <div class="connector-inline-fields connector-method-row">
                              <n-form-item :label="$t('auto.88306943fea7')">
                                <n-select
                                  :value="form.params.connector_config.request.method"
                                  :options="methodOptions"
                                  @update:value="setHttpMethod(String($event))"
                                />
                              </n-form-item>
                              <n-form-item v-if="!isHttpGet" :label="$t('auto.d6b23a46b95c')">
                                <n-select
                                  :value="form.params.connector_config.request.bodyType"
                                  :options="bodyTypeOptionsWithoutNone"
                                  @update:value="setHttpBodyType(String($event))"
                                />
                              </n-form-item>
                            </div>
                            <n-form-item v-if="!isHttpGet" :label="$t('auto.cd760ea4ed59')">
                              <n-input v-model:value="queryParamsText" :placeholder="$t('auto.31f59de7b939')" @blur="syncQueryParams" />
                            </n-form-item>
                          </n-form>
                          <div
                            v-if="isHttpKeyValueBody"
                            ref="queryParamsRef"
                            class="connector-token-editor"
                            contenteditable="true"
                            spellcheck="false"
                            :data-placeholder="keyValueBodyPlaceholder"
                            v-html="renderPromptTokens(keyValueBodyText)"
                            @click="handleTokenEditorClick"
                            @pointerup="rememberInputSelection"
                            @keyup="rememberInputSelection"
                            @input="handleInputEditorInput"
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
                            @pointerup="rememberInputSelection"
                            @keyup="rememberInputSelection"
                            @input="handleInputEditorInput"
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
                              <p class="eyebrow">{{ $t('auto.e48882e558ed') }}</p>
                              <strong>{{ streamInputTitle }}</strong>
                            </div>
                            <n-button class="connector-selection-action" secondary round size="small" @mousedown.prevent @click="markPromptSelection">
                              <template #icon><n-icon><LocateOutline /></n-icon></template>
                              {{ $t('auto.bf958ba7624d') }}
                            </n-button>
                          </div>
                          <n-form class="connector-mapping-controls" label-placement="top">
                            <div class="connector-inline-fields connector-method-row">
                              <n-form-item :label="$t('auto.88306943fea7')">
                                <n-select :value="form.params.connector_config.stream.method" :options="sseMethodOptions" @update:value="setSseMethod(String($event))" />
                              </n-form-item>
                              <n-form-item v-if="!isSseGet" :label="$t('auto.d6b23a46b95c')">
                                <n-select :value="form.params.connector_config.stream.bodyType" :options="bodyTypeOptionsWithoutNone" @update:value="setSseBodyType(String($event))" />
                              </n-form-item>
                            </div>
                            <n-form-item v-if="!isSseGet" :label="$t('auto.cd760ea4ed59')">
                              <n-input v-model:value="queryParamsText" :placeholder="$t('auto.4b7cab170e06')" @blur="syncQueryParams" />
                            </n-form-item>
                          </n-form>
                          <div
                            v-if="isSseKeyValueBody"
                            ref="queryParamsRef"
                            class="connector-token-editor"
                            contenteditable="true"
                            spellcheck="false"
                            :data-placeholder="keyValueBodyPlaceholder"
                            v-html="renderPromptTokens(keyValueBodyText)"
                            @click="handleTokenEditorClick"
                            @pointerup="rememberInputSelection"
                            @keyup="rememberInputSelection"
                            @input="handleInputEditorInput"
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
                            @pointerup="rememberInputSelection"
                            @keyup="rememberInputSelection"
                            @input="handleInputEditorInput"
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
                              <p class="eyebrow">{{ $t('auto.e48882e558ed') }}</p>
                              <strong>{{ $t('auto.1c45f755ae96') }}</strong>
                            </div>
                            <n-button class="connector-selection-action" secondary round size="small" @mousedown.prevent @click="markPromptSelection">
                              <template #icon><n-icon><LocateOutline /></n-icon></template>
                              {{ $t('auto.bf958ba7624d') }}
                            </n-button>
                          </div>
                          <n-form class="connector-mapping-controls" label-placement="top">
                            <n-form-item :label="$t('auto.471b4c7c17f0')">
                              <n-input v-model:value="queryParamsText" :placeholder="$t('auto.a09bfc8688a7')" @blur="syncQueryParams" />
                            </n-form-item>
                          </n-form>
                          <div
                            ref="requestBodyRef"
                            class="connector-token-editor"
                            contenteditable="true"
                            spellcheck="false"
                            v-html="renderPromptTokens(form.params.connector_config.websocket.messageTemplate)"
                            @click="handleTokenEditorClick"
                            @pointerup="rememberInputSelection"
                            @keyup="rememberInputSelection"
                            @input="handleInputEditorInput"
                            @blur="syncRequestBodyEditor"
                          ></div>
                        </div>
                      </div>
                    </template>
                  </section>

                  <section class="connector-response-column">
                    <div
                      ref="outputMappingRef"
                      class="connector-mapping-card connector-output-mapping-card"
                      :class="{
                        'has-fetched-response': Boolean(testResult?.rawResponse),
                        'has-stream-preview': hasSsePreview,
                      }"
                    >
                      <div class="connector-mapping-head">
                        <div>
                          <p class="eyebrow">{{ $t('auto.76968653c994') }}</p>
                          <strong>{{ outputMappingTitle }}</strong>
                        </div>
                        <div class="connector-output-actions">
                          <n-tag v-if="testResult?.rawResponse" type="success" round size="small">{{ $t('auto.8e8bc0ca4aa7') }}</n-tag>
                          <n-button v-if="hasSsePreview" secondary round size="small" @click="streamDetailsOpen = true">
                            <template #icon><n-icon><ListOutline /></n-icon></template> {{ $t('auto.b1552353cb01') }} </n-button>
                          <n-button class="connector-selection-action" secondary round size="small" @mousedown.prevent @click="markOutputSelection">
                            <template #icon><n-icon><CheckmarkCircleOutline /></n-icon></template>
                            {{ $t('auto.39caadf5acae') }}
                          </n-button>
                        </div>
                      </div>
                      <div v-if="hasSsePreview" class="connector-stream-summary">
                        <div class="connector-stream-summary__metrics">
                          <n-tag round size="small" type="info">{{ sseResponsePreview?.events.length }} {{ $t('auto.e05f338ff3b5') }}</n-tag>
                          <n-tag round size="small" type="success">{{ sseResponsePreview?.parsedEventCount }} {{ $t('auto.840fa3c3debd') }}</n-tag>
                          <n-tag v-if="sseResponsePreview?.terminalEventCount" round size="small">
                            {{ sseResponsePreview.terminalEventCount }} {{ $t('auto.00853bff9822') }} </n-tag>
                        </div>
                        <span>{{ $t('auto.3f73c018b30a') }}</span>
                      </div>
                      <div
                        ref="responseBodyRef"
                        class="connector-token-editor"
                        contenteditable="true"
                        spellcheck="false"
                        v-html="renderOutputTokens(sampleResponse)"
                        @click="handleTokenEditorClick"
                        @pointerup="rememberOutputSelection"
                        @keyup="rememberOutputSelection"
                        @input="handleOutputEditorInput"
                        @blur="syncResponseEditor"
                      ></div>
                    </div>
                  </section>
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
            <p class="eyebrow">{{ $t('auto.87a35dafc388') }}</p>
            <h3>{{ $t('auto.9ab49b4159f7') }}</h3>
            <span>{{ $t('auto.52b62df95b89') }}</span>
          </div>
          <n-tag round :type="aiModelConfigured ? 'success' : 'warning'">{{ activeAIModelLabel }}</n-tag>
        </div>

        <n-alert v-if="!aiModelConfigured" type="warning" :title="$t('auto.15ad4f14af55')"> {{ $t('auto.79261d73956d') }} </n-alert>

        <div class="connector-ai-paste-guide">
          <div>
            <strong>{{ $t('auto.fd34ce1faa71') }}</strong>
            <span>{{ $t('auto.f3fb42c11b49') }}</span>
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
            <strong>{{ $t('auto.1916373551d8') }}</strong>
            <span>{{ $t('auto.892d6a4a57bc') }}</span>
          </div>
          <div class="connector-ai-progress-steps" aria-hidden="true">
            <span>{{ $t('auto.42229167b686') }}</span><span>{{ $t('auto.0bd2518f8424') }}</span><span>{{ $t('auto.a89d64179469') }}</span><span>{{ $t('auto.c4eb86d403e1') }}</span>
          </div>
        </div>

        <div class="connector-ai-modal-actions">
          <n-button secondary round :disabled="aiGenerating" @click="aiModalOpen = false">{{ $t('auto.77dfd2135f4d') }}</n-button>
          <n-button class="connector-ai-generate-button" type="primary" round :loading="aiGenerating" :disabled="!canGenerateWithAI" @click="generateWithAI">
            <template #icon><n-icon><SparklesOutline /></n-icon></template>
            {{ aiGenerating ? $t('auto.b42504a45a6a') : $t('auto.db1b7f338318') }}
          </n-button>
        </div>
      </n-card>
    </n-modal>

    <n-modal v-model:show="streamDetailsOpen" transform-origin="center">
      <n-card class="connector-stream-modal" :bordered="false" size="huge" role="dialog" aria-modal="true">
        <div class="connector-stream-modal__head">
          <span class="connector-stream-modal__icon"><n-icon size="22"><ListOutline /></n-icon></span>
          <div>
            <p class="eyebrow">{{ $t('auto.eb4947c2a6ea') }}</p>
            <h3>{{ $t('auto.4b442080782e') }}</h3>
            <span>{{ $t('auto.3b11116673b8') }}</span>
          </div>
          <n-button quaternary circle :aria-label="$t('auto.500d2ad55d7f')" @click="streamDetailsOpen = false">
            <template #icon><n-icon><CloseOutline /></n-icon></template>
          </n-button>
        </div>

        <div class="connector-stream-modal__stats">
          <div><strong>{{ sseResponsePreview?.events.length || 0 }}</strong><span>{{ $t('auto.65939a4f425f') }}</span></div>
          <div><strong>{{ sseResponsePreview?.parsedEventCount || 0 }}</strong><span>{{ $t('auto.9f87239b24c1') }}</span></div>
          <div><strong>{{ sseResponsePreview?.plainEventCount || 0 }}</strong><span>{{ $t('auto.7f8b899acc82') }}</span></div>
          <div><strong>{{ sseResponsePreview?.terminalEventCount || 0 }}</strong><span>{{ $t('auto.cb1bb31276e8') }}</span></div>
        </div>

        <n-tabs type="line" animated>
          <n-tab-pane name="events" tab="Parsed events">
            <div class="connector-stream-event-list">
              <article v-for="event in sseResponsePreview?.events" :key="event.index" class="connector-stream-event">
                <header>
                  <div>
                    <span class="connector-stream-event__index">{{ event.index }}</span>
                    <strong>{{ event.event }}</strong>
                  </div>
                  <div class="connector-stream-event__meta">
                    <n-tag v-if="event.terminal" round size="small" type="warning">{{ $t('auto.a1f52cdcb3f2') }}</n-tag>
                    <n-tag v-else-if="event.parsedData !== undefined" round size="small" type="success">JSON</n-tag>
                    <n-tag v-else round size="small">{{ $t('auto.c3328c39b0e2') }}</n-tag>
                    <span v-if="event.id">{{ $t('auto.a078622f8db4') }} {{ event.id }}</span>
                    <span v-if="event.retry">{{ $t('auto.1fd7e461fef0') }} {{ event.retry }}</span>
                  </div>
                </header>
                <pre>{{ formatSseEventData(event) }}</pre>
              </article>
            </div>
          </n-tab-pane>
          <n-tab-pane name="raw" tab="Raw response">
            <div class="connector-stream-raw-head">
              <span>{{ $t('auto.8375816c99ec') }}</span>
              <n-button secondary round size="small" @click="copyRawStream">
                <template #icon><n-icon><CopyOutline /></n-icon></template> {{ $t('auto.b96670edc2f8') }} </n-button>
            </div>
            <pre class="connector-stream-raw">{{ sseResponsePreview?.raw }}</pre>
          </n-tab-pane>
        </n-tabs>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { translateSource } from '../../../i18n'

import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { NTabPane, NTabs, useMessage, useNotification } from 'naive-ui'
import { CheckmarkCircleOutline, ChevronDownOutline, CloseOutline, CodeSlashOutline, CopyOutline, ListOutline, LocateOutline, SparklesOutline } from '@vicons/ionicons5'
import { useRoute, useRouter } from 'vue-router'
import GlassPanel from '../../../components/GlassPanel.vue'
import { CONFIGURABLE_CONNECTOR, applyTemplate, connectorService, currentUser, defaultConnectorConfig, endpointToConfig, migrateConnectorProtocol, normalizePromptMessageTemplate } from '../../../services/connectorService'
import { getConnectorAIJob, markConnectorAIJobConsumed, startConnectorAIJob } from '../../../services/connectorAiJobService'
import type { ConnectorAIConfigureResult, ConnectorConfig, ConnectorProtocol, ConnectorTestResult } from '../../../types/connector'
import { useMoonshotStore } from '../../../stores/moonshot'
import { useSettingsStore } from '../../../stores/settings'
import { buildSseResponsePreview, formatSseEventData } from '../../../utils/sseResponse'
import type { SseResponsePreview } from '../../../utils/sseResponse'
import { parseJsonDocuments } from '../../../utils/responseExtractor'

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
const requestPreviewOpen = ref(false)
const aiModalOpen = ref(false)
const builderReady = ref(false)
const applyingAIResult = ref(false)
const handledAIJobId = ref('')
const AI_REQUEST_PLACEHOLDER = `Paste request information in any format. Include as much as possible:

1. Endpoint URL and protocol (HTTP, SSE, or WebSocket)
2. Method, all request headers (including Authorization, API keys, or Cookie), query parameters, and request body
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
const outputMappingRef = ref<HTMLElement | null>(null)
const headersText = ref('{\n  "content-type": "application/json"\n}')
const queryParamsText = ref('{\n  "prompt": "{{ prompt }}"\n}')
const formFieldsText = ref('{\n  "message": "{{ prompt }}"\n}')
const keyValueBodyText = ref('input=hi&role=user')
const defaultParamsText = ref('{}')
const DEFAULT_SAMPLE_RESPONSE = '{\n  "blocked": false,\n  "response": "Hi! How can I assist you today?"\n}'
const sampleResponse = ref(DEFAULT_SAMPLE_RESPONSE)
const sseResponsePreview = ref<SseResponsePreview | null>(null)
const streamDetailsOpen = ref(false)
const outputTokenLabel = ref('response')
const promptToken = '{{ prompt }}'
type SavedEditorSelection = { editor: HTMLElement; range: Range }
let savedInputSelection: SavedEditorSelection | null = null
let savedOutputSelection: SavedEditorSelection | null = null
const customHeaderName = ref('')
const customHeaderValue = ref('')
const editingHeaderName = ref('')
const editingHeaderValue = ref('')
const activeProtocol = computed(() => form.params.connector_config.transport)
const currentEndpointId = computed(() => String(route.query.endpointId || ''))
const aiJobKey = computed(() => currentEndpointId.value || `draft:${String(route.query.connector_type || form.connector_type || CONFIGURABLE_CONNECTOR)}`)
const activeAIJob = computed(() => getConnectorAIJob(aiJobKey.value))
const aiGenerating = computed(() => activeAIJob.value?.status === 'running' || applyingAIResult.value)
const hasSsePreview = computed(() => activeProtocol.value === 'sse' && Boolean(sseResponsePreview.value?.events.length))
const outputMappingTitle = computed(() => (
  hasSsePreview.value
    ? 'Select the final answer field from the merged stream JSON'
    : 'Paste any response sample and select the answer value'
))
const isConfigurableApp = computed(() => form.connector_type === CONFIGURABLE_CONNECTOR)
const activeRequestConfig = computed(() => {
  const config = form.params.connector_config
  if (config.transport === 'http') return config.request
  if (config.transport === 'sse') return config.stream
  return config.websocket
})
const isHttpGet = computed(() => form.params.connector_config.transport === 'http' && form.params.connector_config.request?.method === 'GET')
const isHttpFormBody = computed(() => form.params.connector_config.transport === 'http' && form.params.connector_config.request?.bodyType === 'form')
const isHttpMultipartBody = computed(() => form.params.connector_config.transport === 'http' && form.params.connector_config.request?.bodyType === 'multipart')
const isSseGet = computed(() => form.params.connector_config.transport === 'sse' && form.params.connector_config.stream?.method === 'GET')
const isSseFormBody = computed(() => form.params.connector_config.transport === 'sse' && form.params.connector_config.stream?.bodyType === 'form')
const isSseMultipartBody = computed(() => form.params.connector_config.transport === 'sse' && form.params.connector_config.stream?.bodyType === 'multipart')
const isWebSocket = computed(() => form.params.connector_config.transport === 'websocket')
const isMultipartBody = computed(() => isHttpMultipartBody.value || isSseMultipartBody.value)
const isHttpKeyValueBody = computed(() => isHttpGet.value || isHttpFormBody.value || isHttpMultipartBody.value)
const isSseKeyValueBody = computed(() => isSseGet.value || isSseFormBody.value || isSseMultipartBody.value)
const isKeyValueEditorActive = computed(() => isHttpKeyValueBody.value || isSseKeyValueBody.value)
const keyValueBodyPlaceholder = computed(() => isMultipartBody.value ? '{\n  "message": "{{ prompt }}"\n}' : 'input=hi&role=user')
const httpInputTitle = computed(() => {
  if (isHttpGet.value) return 'Paste the full URL Query Params'
  if (isHttpMultipartBody.value) return 'Configure multipart form-data fields as JSON'
  if (isHttpFormBody.value) return 'Paste the full Form Body'
  return 'Paste the full request body'
})
const streamInputTitle = computed(() => {
  if (isSseGet.value) return 'Paste the full URL Query Params'
  if (isSseMultipartBody.value) return 'Configure multipart form-data fields as JSON'
  if (isSseFormBody.value) return 'Paste the full Form Body'
  return 'Paste the full stream request body'
})
const headerEntries = computed(() => Object.entries(parseHeadersText()).map(([name, value]) => ({ name, value })))
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
const bodyTypeOptions = [
  { label: translateSource('auto.05ae0b33808b'), value: 'json' },
  { label: translateSource('auto.27fed83377a0'), value: 'form' },
  { label: 'Multipart form-data', value: 'multipart' },
  { label: translateSource('auto.38de4727d19e'), value: 'raw' },
  { label: translateSource('auto.0621557856e0'), value: 'none' },
]
const bodyTypeOptionsWithoutNone = bodyTypeOptions.filter((option) => option.value !== 'none')
const canSave = computed(() => form.name.trim() && (isConfigurableApp.value ? form.uri.trim() : true) && !permissionDenied.value && !aiGenerating.value)

onMounted(async () => {
  try {
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
      message.error(translateSource('auto.3a8ba6524410'))
      return
    }
    const endpointId = currentEndpointId.value
    const endpoint = endpointId ? connector.endpoints?.find((item) => item.id === endpointId) : undefined
    if (endpointId && !endpoint) {
      permissionDenied.value = true
      message.error(translateSource('auto.0ae7c5427163'))
      return
    }
    Object.assign(form, endpoint ? endpointToConfig(endpoint) : connector.config)
    if (form.connector_type !== CONFIGURABLE_CONNECTOR && !endpoint) applyDefaultEndpointTemplate(form.connector_type)
    syncAllTextFields()
  } finally {
    builderReady.value = true
  }
})

watch(
  () => [builderReady.value, activeAIJob.value?.id, activeAIJob.value?.status] as const,
  async ([ready, jobId, status]) => {
    const job = activeAIJob.value
    if (!ready || !job || !jobId || status === 'running' || handledAIJobId.value === jobId) return
    handledAIJobId.value = jobId
    if (job.result) {
      applyingAIResult.value = true
      try {
        await applyAIConfiguration(job.result)
        if (job.result.status === 'completed') {
          activeTab.value = 'request'
          message.success(`AI configured and verified this endpoint with ${job.result.model || 'the active model'}.`, {
            duration: 7000,
            closable: true,
          })
        } else {
          notifyAIConfigurationFailure(job.result)
        }
      } finally {
        applyingAIResult.value = false
        markConnectorAIJobConsumed(aiJobKey.value)
      }
      return
    }
    notification.error({
      title: translateSource('auto.c4f696a040a2'),
      content: job.error || 'AI configuration failed. Existing fields were kept.',
      duration: 14000,
      keepAliveOnHover: true,
    })
    markConnectorAIJobConsumed(aiJobKey.value)
  },
  { immediate: true },
)

function setProtocol(protocol: ConnectorProtocol) {
  Object.assign(form, applyTemplate(form, protocol))
  sseResponsePreview.value = null
  streamDetailsOpen.value = false
  requestPreviewOpen.value = false
  testResult.value = null
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

function generateWithAI() {
  if (!canGenerateWithAI.value) {
    if (!aiModelConfigured.value) {
      message.error(translateSource('auto.0080cf9d127b'))
    } else {
      message.warning(translateSource('auto.a1001773bb41'))
    }
    return
  }
  const requestInformation = aiRequestInfo.value.trim()
  aiModalOpen.value = false
  handledAIJobId.value = ''
  void startConnectorAIJob({
    key: aiJobKey.value,
    endpointId: currentEndpointId.value || undefined,
    endpointName: form.name || currentEndpointId.value || 'New endpoint',
    requestInformation,
  })
  message.info('AI 配置已在后台开始生成，当前端点已锁定。')
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
      const formatted = prepareResponseSample(result.testResult.rawResponse)
      const responseConfig = result.config?.params.connector_config.response
      const selected = responseConfig?.selectedText || result.testResult.extractedResponse
      sampleResponse.value = insertGeneratedOutputToken(formatted, selected)
      form.params.connector_config.response.sampleResponse = sampleResponse.value
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
    title: translateSource('auto.9fefd008e9dd'),
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
  syncBodyTypeContentType(bodyType)
  if (bodyType === 'form' || bodyType === 'multipart') {
    request.formFields ||= { input: 'hi', role: 'user' }
    keyValueBodyText.value = bodyType === 'multipart'
      ? JSON.stringify(request.formFields, null, 2)
      : toQueryString(request.formFields) || 'input=hi&role=user'
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
  syncBodyTypeContentType(bodyType)
  if (bodyType === 'form' || bodyType === 'multipart') {
    stream.formFields ||= { input: 'hi', role: 'user' }
    keyValueBodyText.value = bodyType === 'multipart'
      ? JSON.stringify(stream.formFields, null, 2)
      : toQueryString(stream.formFields) || 'input=hi&role=user'
  } else if (!stream.bodyTemplate) {
    stream.bodyTemplate = bodyType === 'raw' ? '{{ prompt }}' : '{"message":"{{ prompt }}"}'
  }
}

function syncBodyTypeContentType(bodyType: string) {
  const carrier = activeRequestConfig.value
  if (!carrier) return
  carrier.headers ||= {}
  const headerName = Object.keys(carrier.headers).find((name) => name.toLowerCase() === 'content-type') || 'content-type'
  const contentTypes: Record<string, string> = {
    json: 'application/json',
    form: 'application/x-www-form-urlencoded',
    multipart: 'multipart/form-data',
    raw: 'text/plain; charset=utf-8',
  }
  const contentType = contentTypes[bodyType]
  if (contentType) carrier.headers[headerName] = contentType
  syncHeadersText()
}

function addCustomHeader() {
  if (!customHeaderName.value.trim()) {
    message.warning(translateSource('auto.942b2b0b00bc'))
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

function isSensitiveHeaderName(name: string) {
  return ['authorization', 'proxy-authorization', 'cookie', 'set-cookie', 'x-api-key', 'api-key', 'x-auth-token']
    .includes(name.trim().toLowerCase())
}

function displayHeaderValue(name: string, value: string) {
  if (!isSensitiveHeaderName(name)) return value
  const scheme = value.trim().match(/^([A-Za-z][A-Za-z0-9_-]*)\s+/)?.[1]
  return scheme ? `${scheme} ••••••••` : '••••••••'
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
  message.success(translateSource('auto.41b6b9983229'))
  if (form.connector_type === CONFIGURABLE_CONNECTOR) router.push('/agents/connectors')
  else router.push(`/agents/connectors/${encodeURIComponent(form.connector_type)}`)
  void saved
}

function goBack() {
  const connectorType = form.connector_type || String(route.query.connector_type || '')
  if (connectorType === CONFIGURABLE_CONNECTOR) router.push('/agents/connectors')
  else if (connectorType) router.push(`/agents/connectors/${encodeURIComponent(connectorType)}`)
  else router.push('/agents/connectors')
}

async function fetchResponse() {
  syncEditorFields()
  syncKeyValueBody()
  syncHeaders()
  syncQueryParams()
  syncFormFields()
  const uriProtocol = protocolOverrideFromUri(form.uri, activeProtocol.value)
  if (uriProtocol && uriProtocol !== activeProtocol.value) {
    switchProtocolPreservingConfiguration(uriProtocol)
    message.info(`${uriProtocol === 'websocket' ? 'WebSocket' : 'HTTP'} URL detected. The connector type was updated automatically.`)
  }
  if (!validateConnectorConfiguration()) return
  testing.value = true
  requestPreviewOpen.value = false
  try {
    testResult.value = await connectorService.testConnector(form, testPrompt.value)
    if (testResult.value.rawResponse) {
      const detectedProtocol = testResult.value.detectedTransport
      if (detectedProtocol && detectedProtocol !== activeProtocol.value) {
        switchProtocolPreservingConfiguration(detectedProtocol)
        message.info(`${detectedProtocol === 'sse' ? 'SSE stream' : detectedProtocol.toUpperCase()} response detected. The connector type was updated automatically.`)
      }
      sampleResponse.value = prepareResponseSample(testResult.value.rawResponse)
      form.params.connector_config.response.sampleResponse = sampleResponse.value
      outputTokenLabel.value = 'response'
      form.params.connector_config.response.path = ''
      form.params.connector_config.response.type =
        activeProtocol.value === 'sse' && sseResponsePreview.value?.mode === 'event-data'
          ? 'event-data'
          : 'json-path'
      form.params.connector_config.response.selectedText = undefined
      form.params.connector_config.response.prefix = undefined
      form.params.connector_config.response.suffix = undefined
      activeTab.value = 'request'
      await nextTick()
      outputMappingRef.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      message.success(
        hasSsePreview.value
          ? `${sseResponsePreview.value?.events.length || 0} stream events were merged. Select the final answer field next.`
          : 'Response loaded into Output Mapping. Select the AI answer value next.',
      )
    } else if (testResult.value.error) {
      message.error(testResult.value.error)
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Failed to fetch response.')
  } finally {
    testing.value = false
  }
}

function switchProtocolPreservingConfiguration(protocol: ConnectorProtocol) {
  Object.assign(form, migrateConnectorProtocol(form, protocol))
  sseResponsePreview.value = null
  streamDetailsOpen.value = false
  syncAllTextFields()
}

function protocolOverrideFromUri(uri: string, currentProtocol: ConnectorProtocol): ConnectorProtocol | null {
  try {
    const scheme = new URL(uri.trim()).protocol.toLowerCase()
    if (scheme === 'ws:' || scheme === 'wss:') return 'websocket'
    if (currentProtocol === 'websocket' && (scheme === 'http:' || scheme === 'https:')) return 'http'
  } catch {
    return null
  }
  return null
}

function validateConnectorConfiguration() {
  const protocol = form.params.connector_config.transport
  let parsedUrl: URL
  try {
    parsedUrl = new URL(form.uri.trim())
  } catch {
    message.error(translateSource('auto.455634071858'))
    activeTab.value = 'basic'
    return false
  }
  const allowedSchemes = protocol === 'websocket' ? ['ws:', 'wss:'] : ['http:', 'https:']
  if (!allowedSchemes.includes(parsedUrl.protocol)) {
    message.error(protocol === 'websocket' ? 'WebSocket URLs must use ws:// or wss://.' : 'HTTP and SSE URLs must use http:// or https://.')
    activeTab.value = 'basic'
    return false
  }

  const promptSources: string[] = []
  const requestConfig = activeRequestConfig.value
  if (requestConfig?.queryParams) promptSources.push(...Object.values(requestConfig.queryParams))
  if (requestConfig && 'formFields' in requestConfig && requestConfig.formFields) promptSources.push(...Object.values(requestConfig.formFields))
  if (requestConfig && 'bodyTemplate' in requestConfig && requestConfig.bodyTemplate) promptSources.push(requestConfig.bodyTemplate)
  if (requestConfig && 'messageTemplate' in requestConfig && requestConfig.messageTemplate) promptSources.push(requestConfig.messageTemplate)
  if (!promptSources.some((value) => /\{\{\s*prompt\s*\}\}/.test(String(value)))) {
    message.error(translateSource('auto.89cb50e8fdc6'))
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

function prepareResponseSample(raw: string) {
  if (activeProtocol.value !== 'sse') {
    sseResponsePreview.value = null
    streamDetailsOpen.value = false
    return formatResponseSample(raw)
  }
  sseResponsePreview.value = buildSseResponsePreview(raw)
  return sseResponsePreview.value.mergedSample
}

async function copyRawStream() {
  const raw = sseResponsePreview.value?.raw || ''
  if (!raw) return
  try {
    await navigator.clipboard.writeText(raw)
    message.success(translateSource('auto.5afe24276c35'))
  } catch {
    message.error(translateSource('auto.e9e82803ae11'))
  }
}

function syncAllTextFields() {
  if (isConfigurableApp.value) {
    syncHeadersText()
    syncQueryParamsText()
    syncFormFieldsText()
    restoreResponseMappingSample()
  } else {
    syncDefaultParamsText()
  }
}

function restoreResponseMappingSample() {
  const response = form.params.connector_config.response
  sampleResponse.value = response.sampleResponse || DEFAULT_SAMPLE_RESPONSE
  if (response.type === 'event-data' && !response.path) {
    outputTokenLabel.value = 'data'
    return
  }
  const pathLabel = response.path?.split('.').filter(Boolean).at(-1)
  if (pathLabel) {
    outputTokenLabel.value = pathLabel
    return
  }
  const selected = response.selectedText || ''
  const rawSample = selected ? sampleResponse.value.replace(/\{\{\s*output\s*\}\}/, selected) : sampleResponse.value
  outputTokenLabel.value = selected ? inferOutputLabel(rawSample, selected) : 'response'
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
    message.error(translateSource('auto.e3fa3a1e0363'))
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
    message.error(translateSource('auto.8d33a3c1c416'))
  }
}

function syncFormFieldsText() {
  formFieldsText.value = JSON.stringify(activeFormFields(), null, 2)
  if (isMultipartBody.value) keyValueBodyText.value = formFieldsText.value
  else if (isHttpFormBody.value || isSseFormBody.value) keyValueBodyText.value = toQueryString(activeFormFields()) || 'input=hi&role=user'
}

function syncFormFields() {
  if (isHttpFormBody.value || isSseFormBody.value || isMultipartBody.value) return
  const carrier = activeRequestConfig.value
  if (!carrier || !('formFields' in carrier)) return
  try {
    carrier.formFields = parseJsonObject(formFieldsText.value)
  } catch {
    message.error(translateSource('auto.b284b0142020'))
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
    return
  }
  if (isMultipartBody.value) {
    formFieldsText.value = keyValueBodyText.value
    const carrier = activeRequestConfig.value
    if (carrier && 'formFields' in carrier) {
      try {
        carrier.formFields = parseJsonObject(keyValueBodyText.value)
      } catch {
        message.error(translateSource('auto.b284b0142020'))
      }
    }
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
  const selectedTemplate = editorText(target)
  const next = isKeyValueEditorActive.value ? selectedTemplate : normalizePromptMessageTemplate(selectedTemplate)
  if (isKeyValueEditorActive.value) {
    keyValueBodyText.value = next
    syncKeyValueBody()
  } else {
    setActiveBodyTemplate(next)
    if (next !== selectedTemplate) {
      target.innerHTML = renderPromptTokens(next)
      message.info(translateSource('auto.23ff01bafbc7'))
    }
  }
  message.success(translateSource('auto.e654a813b649'))
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
  form.params.connector_config.response.sampleResponse = sampleResponse.value
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

function rememberInputSelection(event: Event) {
  rememberEditorSelection(event.currentTarget as HTMLElement, 'input')
}

function rememberOutputSelection(event: Event) {
  rememberEditorSelection(event.currentTarget as HTMLElement, 'output')
}

function handleInputEditorInput(event: Event) {
  rememberInputSelection(event)
  const editor = event.currentTarget as HTMLElement
  if (editor === queryParamsRef.value) syncKeyValueEditorAndBody()
  else syncRequestBodyEditor()
}

function handleOutputEditorInput(event: Event) {
  rememberOutputSelection(event)
  syncResponseEditor()
}

function rememberEditorSelection(editor: HTMLElement, kind: 'input' | 'output') {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0 || !selectionInsideEditor(selection, editor)) return
  const saved = { editor, range: selection.getRangeAt(0).cloneRange() }
  if (kind === 'input') savedInputSelection = saved
  else savedOutputSelection = saved
}

function selectionInsideEditor(selection: Selection, editor: HTMLElement) {
  return Boolean(selection.anchorNode && selection.focusNode && editor.contains(selection.anchorNode) && editor.contains(selection.focusNode))
}

function editorRange(editor: HTMLElement, saved: SavedEditorSelection | null) {
  const selection = window.getSelection()
  if (selection?.rangeCount && selectionInsideEditor(selection, editor)) return selection.getRangeAt(0).cloneRange()
  if (saved?.editor === editor && editor.contains(saved.range.startContainer) && editor.contains(saved.range.endContainer)) return saved.range.cloneRange()
  const range = document.createRange()
  range.selectNodeContents(editor)
  range.collapse(false)
  return range
}

function applyEditorRange(editor: HTMLElement, range: Range, kind: 'input' | 'output') {
  editor.focus()
  const selection = window.getSelection()
  selection?.removeAllRanges()
  selection?.addRange(range)
  const saved = { editor, range: range.cloneRange() }
  if (kind === 'input') savedInputSelection = saved
  else savedOutputSelection = saved
}

function insertPromptToken(editor: HTMLElement) {
  const range = editorRange(editor, savedInputSelection)
  range.deleteContents()
  const token = document.createTextNode(promptToken)
  range.insertNode(token)
  range.setStartAfter(token)
  range.collapse(true)
  applyEditorRange(editor, range, 'input')
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
  const rawSample = editorText(target)
  sampleResponse.value = rawSample
  const range = editorRange(target, savedOutputSelection)
  const selected = range.toString()
  if (!selected) {
    message.warning(translateSource('auto.c20511988f83'))
    return
  }
  const location = inferResponseLocation(rawSample, selected)
  if (activeProtocol.value === 'sse' && sseResponsePreview.value?.mode === 'event-data') {
    form.params.connector_config.response.type = 'event-data'
    form.params.connector_config.response.path = ''
    form.params.connector_config.response.prefix = undefined
    form.params.connector_config.response.suffix = undefined
    form.params.connector_config.response.selectedText = undefined
    outputTokenLabel.value = 'data'
    message.success(translateSource('auto.f3bc88da378c'))
  } else if (location.type === 'json-path') {
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
    outputTokenLabel.value = inferOutputLabel(rawSample, selected)
    message.success(translateSource('auto.eb5c696fb628'))
  }
  insertOutputToken(target, range)
  syncResponseEditor()
}

function insertOutputToken(editor: HTMLElement, range: Range) {
  range.deleteContents()
  const token = document.createTextNode('{{ output }}')
  range.insertNode(token)
  range.setStartAfter(token)
  range.collapse(true)
  applyEditorRange(editor, range, 'output')
}

function findJsonPathBySelection(rawJson: string, selected: string) {
  const normalized = selected.trim().replace(/^"|"$/g, '')
  for (const parsed of [...parseJsonDocuments(rawJson)].reverse()) {
    const path = findPath(parsed, normalized)
    if (path) return path
  }
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
