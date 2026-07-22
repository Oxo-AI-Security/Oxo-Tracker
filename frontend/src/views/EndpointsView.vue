<template>
  <div class="endpoint-shell">
    <GlassPanel v-if="mode === 'menu'" class="endpoint-panel agents-home-panel">
      <section class="agents-home-hero">
        <div class="agents-home-copy workspace-title-block">
          <span class="workspace-title-icon workspace-title-icon--agents">
            <n-icon><ShieldCheckmarkOutline /></n-icon>
          </span>
          <div class="workspace-title-content">
            <p class="eyebrow">Agent workspace</p>
            <h2>Audit and red-team AI applications</h2>
            <p>
              Run design-time risk reviews for AI features, or open adversarial testing sessions against live target endpoints.
            </p>
          </div>
        </div>
        <dl class="agents-home-metrics">
          <div>
            <dt>Targets</dt>
            <dd>{{ store.endpoints.length }}</dd>
          </div>
          <div>
            <dt>Sessions</dt>
            <dd>{{ redTeamSessions.length }}</dd>
          </div>
          <div>
            <dt>Connectors</dt>
            <dd>{{ connectorCount }}</dd>
          </div>
        </dl>
      </section>

      <section class="agents-workbench-grid" aria-label="Primary agent workspaces">
        <RouterLink class="agents-workbench-card agents-workbench-card--audit" to="/agents/security-review">
          <span class="agents-workbench-card__topline">
            <span class="agents-workbench-icon">
              <n-icon size="28"><ShieldCheckmarkOutline /></n-icon>
            </span>
            <span class="agents-workbench-badge">Risk audit</span>
          </span>
          <span class="agents-workbench-copy">
            <strong>Agent Security Review</strong>
            <small>Audit AI feature risk from design documents, prompts, tools, diagrams, screenshots, and architecture notes.</small>
          </span>
          <span class="agents-workbench-steps">
            <span>Materials</span>
            <span>Capability map</span>
            <span>Risk map</span>
          </span>
          <span class="agents-workbench-action">Open review workspace</span>
        </RouterLink>

        <button class="agents-workbench-card agents-workbench-card--red" type="button" @click="mode = 'sessions'">
          <span class="agents-workbench-card__topline">
            <span class="agents-workbench-icon">
              <n-icon size="28"><ChatboxEllipsesOutline /></n-icon>
            </span>
            <span class="agents-workbench-badge">{{ redTeamSessions.length }} saved</span>
          </span>
          <span class="agents-workbench-copy">
            <strong>Red Team Sessions</strong>
            <small>Help testers run adversarial conversations with payloads, attack modules, clean comparison, and session history.</small>
          </span>
          <span class="agents-workbench-steps">
            <span>Target</span>
            <span>Payload</span>
            <span>Compare</span>
          </span>
          <span class="agents-workbench-action">Open testing workspace</span>
        </button>
      </section>

      <section class="agents-infra-section">
        <div class="agents-infra-heading">
          <div>
            <p class="eyebrow">Configuration layer</p>
            <h3>Targets and connectors</h3>
          </div>
          <span>Used by audits, evaluations, and red-team sessions</span>
        </div>

        <div class="agents-infra-grid">
          <button class="agents-infra-card agents-infra-card--targets" type="button" @click="mode = 'list'">
            <span class="agents-infra-icon">
              <n-icon size="22"><CubeOutline /></n-icon>
            </span>
            <span>
              <strong>Endpoints</strong>
              <small>Create and maintain target model or application endpoints.</small>
            </span>
            <b>{{ store.endpoints.length }}</b>
          </button>

          <RouterLink class="agents-infra-card agents-infra-card--connectors" to="/agents/connectors">
            <span class="agents-infra-icon">
              <n-icon size="22"><CubeOutline /></n-icon>
            </span>
            <span>
              <strong>Connector</strong>
              <small>Configure custom AI app protocols, auth, request mapping, and response extraction.</small>
            </span>
            <b>{{ connectorCount }}</b>
          </RouterLink>
        </div>
      </section>
    </GlassPanel>

    <GlassPanel v-else-if="mode === 'list'" class="endpoint-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Model agents</p>
          <h2>Agents</h2>
        </div>
        <div class="endpoint-heading-actions">
          <n-button secondary round @click="mode = 'menu'">Back</n-button>
          <n-button class="red-test-button" round @click="openSessionWizard()">
            <template #icon><n-icon><ShieldCheckmarkOutline /></n-icon></template>
            Add Red Team Test
          </n-button>
          <n-button secondary round @click="openCustomEndpointCreate">
            <template #icon><n-icon><AddOutline /></n-icon></template>
            Create App Endpoint
          </n-button>
          <n-button type="primary" round @click="openCreate">
            <template #icon><n-icon><AddOutline /></n-icon></template>
            Create New Endpoint
          </n-button>
        </div>
      </div>

      <div class="endpoint-grid">
        <n-scrollbar v-if="store.endpoints.length" class="endpoint-list-scrollbar">
          <div class="endpoint-list">
            <button
              v-for="endpoint in store.endpoints"
              :key="endpointId(endpoint)"
              class="endpoint-list-item"
              :class="{ active: endpointId(endpoint) === endpointId(activeEndpoint) }"
              type="button"
              @click="selectedEndpointId = endpointId(endpoint)"
            >
              <span class="row-icon"><n-icon size="22"><CubeOutline /></n-icon></span>
              <span class="row-copy">
                <strong>{{ endpoint.name || endpoint.id }}</strong>
                <small>Type {{ endpoint.connector_type || '-' }}</small>
              </span>
              <time>{{ endpoint.created_at ? `Added on ${endpoint.created_at}` : '' }}</time>
            </button>
          </div>
        </n-scrollbar>
        <n-empty v-else description="No endpoints configured" />

        <section class="endpoint-detail-card">
          <template v-if="activeEndpoint">
            <div class="endpoint-detail-title">
              <h3>
                <n-icon><CubeOutline /></n-icon>
                {{ activeEndpoint.name || activeEndpoint.id }}
              </h3>
              <n-popconfirm positive-text="Delete" negative-text="Cancel" @positive-click="deleteEndpoint(activeEndpoint)">
                <template #trigger>
                  <n-button secondary round size="small" type="error">Delete</n-button>
                </template>
                Delete this endpoint?
              </n-popconfirm>
            </div>
            <div class="endpoint-detail-list">
              <div><strong>Type</strong><span>{{ activeEndpoint.connector_type || '-' }}</span></div>
              <div><strong>URI</strong><span>{{ activeEndpoint.uri || 'Not set' }}</span></div>
              <div><strong>Token</strong><span>{{ activeEndpoint.token ? '**********' : 'Not set' }}</span></div>
              <div><strong>Model</strong><span>{{ activeEndpoint.model || 'None' }}</span></div>
              <div>
                <strong>Max number of calls per second</strong>
                <span>{{ activeEndpoint.max_calls_per_second ?? '-' }}</span>
              </div>
              <div><strong>Max concurrency</strong><span>{{ activeEndpoint.max_concurrency ?? '-' }}</span></div>
              <div>
                <strong>Parameters</strong>
                <pre>{{ formatParams(activeEndpoint.params) }}</pre>
              </div>
            </div>
            <div class="endpoint-detail-actions">
              <n-button class="red-test-button" round size="large" @click="openSessionWizard(activeEndpoint)">
                <template #icon><n-icon><ShieldCheckmarkOutline /></n-icon></template>
                Red Team Test
              </n-button>
              <n-button type="primary" round size="large" @click="openEdit(activeEndpoint)">
                Edit Endpoint
              </n-button>
            </div>
          </template>
          <n-empty v-else description="Select an endpoint to inspect" />
        </section>
      </div>
    </GlassPanel>

    <GlassPanel v-else-if="mode === 'sessions'" class="endpoint-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Stored red team work</p>
          <h2>Red Team Sessions</h2>
        </div>
        <div class="endpoint-heading-actions">
          <n-button secondary round @click="mode = 'menu'">Back</n-button>
          <n-button type="primary" round @click="openSessionWizard()">
            <template #icon><n-icon><AddOutline /></n-icon></template>
            New Session
          </n-button>
        </div>
      </div>

      <div v-if="redTeamSessions.length" class="red-session-grid">
        <article v-for="session in redTeamSessions" :key="session.id" class="red-session-card">
          <div class="red-session-card-head">
            <span><n-icon><ChatboxEllipsesOutline /></n-icon></span>
            <strong>{{ session.name }}</strong>
          </div>
          <p>{{ session.description || 'No description' }}</p>
          <dl>
            <div><dt>Endpoint</dt><dd>{{ session.endpointName }}</dd></div>
            <div><dt>Payload</dt><dd>{{ labelOrNone(session.payloadId) }}</dd></div>
            <div><dt>Attack</dt><dd>{{ labelOrNone(session.attackModule) }}</dd></div>
          </dl>
          <div class="red-session-actions">
            <n-button secondary round size="small" @click="deleteSession(session.id)">Delete</n-button>
            <n-button type="primary" round size="small" @click="openChat(session)">Open Chat</n-button>
          </div>
        </article>
      </div>
      <n-empty v-else description="No stored sessions yet">
        <template #extra>
          <n-button type="primary" round @click="openSessionWizard()">Create Red Team Session</n-button>
        </template>
      </n-empty>
    </GlassPanel>

    <GlassPanel v-else-if="mode === 'session-wizard'" class="first-test-panel red-wizard-panel">
      <div class="wizard-top red-wizard-top">
        <div v-for="item in redSteps" :key="item.index" class="wizard-step" :class="{ active: redStep >= item.index }">
          <span />
          <strong>{{ item.label }}</strong>
        </div>
        <n-button circle quaternary @click="mode = 'sessions'">
          <template #icon><n-icon><CloseOutline /></n-icon></template>
        </n-button>
      </div>

      <section v-if="redStep === 1" class="wizard-body red-wizard-body">
        <h2>Connect Endpoint</h2>
        <p class="red-wizard-copy">Choose the target model or application endpoint for this red-team session.</p>
        <div class="endpoint-filter-row">
          <n-input v-model:value="endpointSearch" clearable class="endpoint-search-input" placeholder="Search endpoints">
            <template #prefix><n-icon><SearchOutline /></n-icon></template>
          </n-input>
          <n-button secondary round @click="openCreate">Create Endpoint</n-button>
        </div>
        <n-scrollbar v-if="filteredEndpoints.length" class="wizard-card-scrollbar">
          <div class="endpoint-select-grid red-select-grid">
            <article
              v-for="endpoint in filteredEndpoints"
              :key="endpointId(endpoint)"
              class="select-card endpoint-select-card"
              :class="{ selected: sessionForm.endpointId === endpointId(endpoint) }"
              @click="selectSessionEndpoint(endpoint)"
            >
              <div class="select-card-title">
                <n-icon><CubeOutline /></n-icon>
                <strong>{{ endpoint.name || endpoint.id }}</strong>
              </div>
              <p>{{ endpoint.connector_type || endpoint.model || 'Endpoint' }}</p>
              <n-checkbox :checked="sessionForm.endpointId === endpointId(endpoint)" @click.stop @update:checked="selectSessionEndpoint(endpoint)" />
            </article>
          </div>
        </n-scrollbar>
        <n-empty v-else description="No endpoints found" />
      </section>

      <section v-else-if="redStep === 2" class="wizard-body red-wizard-body">
        <h2>Set Optional Utilities</h2>
        <p class="red-wizard-copy">Select a payload wrapper and an attack module. You can still switch both inside chat.</p>
        <div class="red-utility-layout">
          <section class="red-utility-panel">
            <div class="red-utility-heading">
              <n-icon><DocumentTextOutline /></n-icon>
              <strong>Payload</strong>
            </div>
            <n-select
              v-model:value="sessionForm.payloadId"
              clearable
              filterable
              :options="payloadOptions"
              placeholder="No payload selected"
            />
          </section>

          <section class="red-utility-panel">
            <div class="red-utility-heading">
              <n-icon><ShieldCheckmarkOutline /></n-icon>
              <strong>Attack Modules</strong>
            </div>
            <n-scrollbar class="red-module-scrollbar">
              <div class="red-module-grid">
                <button
                  v-for="module in attackModuleOptions"
                  :key="module.value"
                  class="red-module-card"
                  :class="{ selected: sessionForm.attackModule === module.value }"
                  type="button"
                  @click="sessionForm.attackModule = module.value"
                >
                  <span><n-icon><CubeOutline /></n-icon>{{ module.label }}</span>
                  <small>{{ attackModuleDescription(module.value) }}</small>
                </button>
              </div>
            </n-scrollbar>
          </section>

          <section class="red-utility-panel">
            <div class="red-utility-heading">
              <n-icon><TimeOutline /></n-icon>
              <strong>Context Strategy</strong>
            </div>
            <n-select v-model:value="sessionForm.contextStrategy" :options="contextOptions" />
          </section>
        </div>
      </section>

      <section v-else class="wizard-body red-wizard-body red-start-body">
        <h2>Before you start...</h2>
        <div class="red-session-form">
          <n-form label-placement="top">
            <n-form-item label="Name">
              <n-input v-model:value="sessionForm.name" placeholder="session-001" />
            </n-form-item>
            <n-form-item label="Description (optional)">
              <n-input
                v-model:value="sessionForm.description"
                type="textarea"
                placeholder="Describe this session. E.g., purpose of the session"
                :autosize="{ minRows: 4, maxRows: 6 }"
              />
            </n-form-item>
          </n-form>
          <n-button type="primary" round size="large" @click="createRedTeamSession">Run</n-button>
        </div>
      </section>

      <footer class="wizard-footer">
        <button v-if="redStep > 1" class="wizard-link" type="button" @click="redStep -= 1">&lt;- BACK</button>
        <span v-else />
        <button v-if="redStep < 3" class="wizard-link" type="button" @click="nextRedStep">NEXT -></button>
        <span v-else />
      </footer>
    </GlassPanel>

    <section v-else-if="activeSession && activeChat" class="red-chat-shell">
      <header class="red-chat-topbar">
        <div>
          <p class="eyebrow">Red team session</p>
          <h2>{{ activeSession.endpointName }}</h2>
        </div>
        <div class="endpoint-heading-actions">
          <n-button secondary round @click="clearActiveChat">Clear</n-button>
          <n-button secondary round @click="toggleBaselineChat">
            {{ activeChat.compareEnabled ? 'Hide Compare' : 'Compare' }}
          </n-button>
          <n-button secondary round @click="mode = 'sessions'">Sessions</n-button>
          <n-button circle quaternary @click="mode = 'sessions'">
            <template #icon><n-icon><CloseOutline /></n-icon></template>
          </n-button>
        </div>
      </header>

      <div class="red-chat-layout">
        <aside class="red-chat-sidebar">
          <section class="red-history-pane">
            <div class="red-sidebar-heading">
              <strong>Chats</strong>
              <n-button quaternary size="tiny" @click="clearActiveChat">Clear</n-button>
            </div>
            <n-scrollbar class="red-history-scrollbar">
              <div
                v-for="chat in chatHistoryThreads"
                :key="chat.id"
                class="red-history-item"
                :class="{ active: chat.id === activeChat.id }"
              >
                <button type="button" @click="openChatThread(chat.id)">
                  <strong>{{ chat.title }}</strong>
                  <small>{{ chatPreview(chat) }}</small>
                </button>
                <n-button quaternary circle size="tiny" @click="deleteChatThread(chat.id)">
                  <template #icon><n-icon><CloseOutline /></n-icon></template>
                </n-button>
              </div>
            </n-scrollbar>
          </section>

          <section class="red-config-pane">
            <strong>{{ activeSession.endpointName }}</strong>
            <span>{{ activeSession.description || 'Adversarial conversation workspace' }}</span>
            <div class="red-chat-control">
              <label>Payload</label>
              <div class="red-select-create-row">
                <n-select
                  :value="activeSession.payloadId"
                  clearable
                  filterable
                  :options="payloadOptions"
                  placeholder="None"
                  @update:value="updateActiveSession('payloadId', String($event || ''))"
                />
                <n-button secondary circle title="Create prompt template" @click="openTemplateModal">
                  <template #icon><n-icon><AddOutline /></n-icon></template>
                </n-button>
              </div>
            </div>
            <div class="red-chat-control">
              <label>Attack Module</label>
              <n-select
                :value="activeSession.attackModule"
                clearable
                filterable
                :options="attackModuleOptions"
                placeholder="None"
                @update:value="updateActiveSession('attackModule', String($event || ''))"
              />
            </div>
            <div class="red-chat-control">
              <label>Context Strategy</label>
              <n-select
                :value="activeSession.contextStrategy"
                :options="contextOptions"
                @update:value="updateActiveSession('contextStrategy', String($event || 'none'))"
              />
            </div>
          </section>
        </aside>

        <main class="red-chat-main">
          <div class="red-chat-columns" :class="{ comparing: activeChat.compareEnabled }">
            <section class="red-chat-column">
              <div class="red-column-title">
                <strong>With payload</strong>
                <small>{{ labelOrNone(activeSession.payloadId) }} / {{ labelOrNone(activeSession.attackModule) }}</small>
              </div>
              <n-scrollbar ref="chatScrollbarRef" class="red-chat-scrollbar">
                <div class="red-chat-thread">
                  <article class="red-chat-message assistant">
                    <span>{{ activeSession.endpointName }}</span>
                    <p>Session is ready. Select a payload or attack module, then send a prompt to record this red-team turn.</p>
                  </article>
                  <article
                    v-for="chat in activeChat.messages"
                    :key="chat.id"
                    class="red-chat-message"
                    :class="[chat.role, chat.status]"
                  >
                    <span>{{ chat.role === 'user' ? 'You' : activeSession.endpointName }}</span>
                    <p v-if="chat.status === 'pending'" class="red-chat-waiting" aria-label="Waiting for answer">
                      <i></i><i></i><i></i>
                    </p>
                    <p v-else>{{ chat.role === 'assistant' ? displayAssistantContent(chat.content) : chat.content }}</p>
                  </article>
                </div>
              </n-scrollbar>
            </section>

            <section v-if="activeChat.compareEnabled" class="red-chat-column clean">
              <div class="red-column-title">
                <strong>Clean chat</strong>
                <small>No payload / no attack module</small>
              </div>
              <n-scrollbar ref="baselineScrollbarRef" class="red-chat-scrollbar">
                <div class="red-chat-thread">
                  <article class="red-chat-message assistant">
                    <span>{{ activeSession.endpointName }}</span>
                    <p>Clean comparison is ready. Messages here are sent without payload or attack transformations.</p>
                  </article>
                  <article
                    v-for="chat in activeChat.baselineMessages || []"
                    :key="chat.id"
                    class="red-chat-message"
                    :class="[chat.role, chat.status]"
                  >
                    <span>{{ chat.role === 'user' ? 'You' : activeSession.endpointName }}</span>
                    <p v-if="chat.status === 'pending'" class="red-chat-waiting" aria-label="Waiting for answer">
                      <i></i><i></i><i></i>
                    </p>
                    <p v-else>{{ chat.role === 'assistant' ? displayAssistantContent(chat.content) : chat.content }}</p>
                  </article>
                </div>
              </n-scrollbar>
            </section>
          </div>

          <form class="red-chat-composer" @submit.prevent="sendChatPrompt">
            <section v-if="chatPrompt.trim()" class="red-prepared-preview">
              <div class="red-prepared-preview-head">
                <div>
                  <span>Final prompt preview</span>
                  <small>Payload and attack module applied</small>
                </div>
                <div>
                  <n-tag size="small" round>{{ labelOrNone(activeSession.payloadId) }}</n-tag>
                  <n-tag size="small" round>{{ labelOrNone(activeSession.attackModule) }}</n-tag>
                  <button type="button" @click="previewModalOpen = true">Expand</button>
                </div>
              </div>
              <pre>{{ compactPreparedPromptPreview }}</pre>
            </section>
            <label class="red-input-label" for="red-chat-input">Your input</label>
            <textarea
              id="red-chat-input"
              v-model="chatPrompt"
              rows="3"
              placeholder="Message the target endpoint..."
              @keydown="handleComposerKeydown"
            />
            <div>
              <small>Enter to send / Shift+Enter for newline</small>
              <n-button type="primary" round attr-type="submit" :loading="chatSending" :disabled="!chatPrompt.trim()">
                Send
              </n-button>
            </div>
          </form>
        </main>
      </div>
    </section>

    <n-modal v-model:show="previewModalOpen" preset="card" class="red-preview-modal" title="Final prompt">
      <div class="red-preview-modal-body">
        <div class="red-preview-summary">
          <span><b>Payload</b>{{ activeSession ? labelOrNone(activeSession.payloadId) : 'None' }}</span>
          <span><b>Attack Module</b>{{ activeSession ? labelOrNone(activeSession.attackModule) : 'None' }}</span>
        </div>
        <pre>{{ preparedPromptPreview }}</pre>
      </div>
    </n-modal>

    <n-modal v-model:show="templateModalOpen" preset="card" class="prompt-template-modal" :bordered="false">
      <template #header>
        <div class="prompt-template-modal-title">
          <span>Create Prompt Template</span>
          <small>Compose a reusable wrapper around the prompt block.</small>
        </div>
      </template>
      <div class="prompt-template-modal-body">
        <section class="prompt-template-form">
          <section class="prompt-template-form-card">
            <p class="eyebrow">Identity</p>
            <n-form label-placement="top">
              <n-form-item label="Name">
                <n-input v-model:value="templateForm.name" placeholder="Safety answer wrapper" />
              </n-form-item>
              <n-form-item label="Description">
                <n-input
                  v-model:value="templateForm.description"
                  type="textarea"
                  :autosize="{ minRows: 3, maxRows: 5 }"
                  placeholder="Describe when this wrapper should be used"
                />
              </n-form-item>
            </n-form>
          </section>
          <div class="template-block-editor">
            <div class="template-editor-head">
              <div>
                <strong>Template body</strong>
                <small>Use text blocks before or after the prompt block.</small>
              </div>
              <n-button secondary round size="small" @click="insertPromptBlock">
                Insert prompt block
              </n-button>
            </div>
            <div class="template-block-list">
              <template v-for="(block, index) in templateBlocks" :key="block.id">
                <n-input
                  v-if="block.type === 'text'"
                  v-model:value="block.value"
                  type="textarea"
                  :autosize="{ minRows: 2, maxRows: 8 }"
                  placeholder="Write template text here"
                />
                <div v-else class="template-editor-token">
                  <span v-text="PROMPT_TOKEN"></span>
                  <n-button quaternary circle size="tiny" @click="removeTemplateBlock(index)">
                    <template #icon><n-icon><CloseOutline /></n-icon></template>
                  </n-button>
                </div>
              </template>
            </div>
          </div>
        </section>
        <aside class="prompt-template-live-preview">
          <p class="eyebrow">Preview</p>
          <div class="template-render-card">
            <template v-for="(part, index) in renderTemplateParts(templateBody)" :key="index">
              <span v-if="part.type === 'text'">{{ part.value }}</span>
              <b v-else class="prompt-token-block" v-text="PROMPT_TOKEN"></b>
            </template>
          </div>
          <small>Saved ID will start with Oxo- and can be selected as Payload.</small>
        </aside>
      </div>
      <template #footer>
        <div class="modal-footer-actions">
          <n-button round @click="templateModalOpen = false">Cancel</n-button>
          <n-button type="primary" round :loading="templateSubmitting" :disabled="!canCreateTemplate" @click="createPromptTemplate">
            Create Template
          </n-button>
        </div>
      </template>
    </n-modal>

    <GlassPanel v-if="mode === 'form-basic' || mode === 'form-advanced'" class="endpoint-form-panel">
      <div class="builder-header">
        <h2>{{ editingId ? 'Edit Endpoint' : 'Create New Endpoint' }}</h2>
        <n-button circle quaternary @click="mode = 'list'">
          <template #icon><n-icon><CloseOutline /></n-icon></template>
        </n-button>
      </div>

      <div v-if="mode === 'form-basic'" class="endpoint-form-layout">
        <n-form label-placement="top">
          <n-form-item label="Name*">
            <n-input v-model:value="form.name" placeholder="Demo Endpoint" />
          </n-form-item>
          <n-form-item label="Connection Type*">
            <n-select
              v-model:value="form.connector_type"
              filterable
              :options="connectorOptions"
              placeholder="openai-connector"
            />
          </n-form-item>
          <n-form-item label="URI">
            <n-input v-model:value="form.uri" placeholder="URI of the remote model endpoint" />
          </n-form-item>
          <n-form-item label="Token">
            <n-input v-model:value="form.token" type="password" show-password-on="click" placeholder="YOUR_TOKEN" />
          </n-form-item>
          <button class="more-configs" type="button" @click="mode = 'form-advanced'">More Configs</button>
        </n-form>

        <div class="endpoint-form-actions">
          <n-button round size="large" @click="mode = 'list'">Cancel</n-button>
          <n-button type="primary" round size="large" :loading="submitting" @click="submitEndpoint">Save</n-button>
        </div>
      </div>

      <div v-else class="endpoint-form-layout">
        <n-form label-placement="top">
          <n-form-item label="Model">
            <n-input v-model:value="form.model" placeholder="gpt-4o-mini" />
          </n-form-item>
          <n-form-item label="Max Calls Per Second">
            <n-input-number v-model:value="form.max_calls_per_second" :min="1" />
          </n-form-item>
          <n-form-item label="Max Concurrency">
            <n-input-number v-model:value="form.max_concurrency" :min="1" />
          </n-form-item>
          <n-form-item label="Other Parameters*">
            <n-input v-model:value="paramsText" type="textarea" :autosize="{ minRows: 8, maxRows: 12 }" />
          </n-form-item>
        </n-form>

        <div class="endpoint-form-actions">
          <n-button round size="large" @click="mode = 'form-basic'">Back</n-button>
          <n-button type="primary" round size="large" :loading="submitting" @click="submitEndpoint">OK</n-button>
        </div>
      </div>
    </GlassPanel>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  AddOutline,
  ChatboxEllipsesOutline,
  CloseOutline,
  CubeOutline,
  DocumentTextOutline,
  SearchOutline,
  ShieldCheckmarkOutline,
  TimeOutline,
} from '@vicons/ionicons5'
import GlassPanel from '../components/GlassPanel.vue'
import { moonshotApi } from '../api/moonshot'
import { CONFIGURABLE_CONNECTOR, connectorService } from '../services/connectorService'
import { useMoonshotStore } from '../stores/moonshot'
import type { EndpointCreatePayload, EndpointRecord } from '../types/moonshot'

type EndpointMode = 'menu' | 'list' | 'sessions' | 'session-wizard' | 'chat' | 'form-basic' | 'form-advanced'
type ChatRole = 'user' | 'assistant'

interface RedTeamMessage {
  id: string
  role: ChatRole
  content: string
  createdAt: string
  status?: 'pending' | 'typing' | 'done' | 'error'
}

interface RedTeamChatThread {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messages: RedTeamMessage[]
  baselineMessages: RedTeamMessage[]
  compareEnabled: boolean
}

interface RedTeamSession {
  id: string
  name: string
  description: string
  endpointId: string
  endpointName: string
  payloadId: string
  attackModule: string
  contextStrategy: string
  createdAt: string
  updatedAt: string
  chats: RedTeamChatThread[]
  messages?: RedTeamMessage[]
  baselineMessages?: RedTeamMessage[]
  compareEnabled?: boolean
}

interface PreparedPrompt {
  original_prompt: string
  templated_prompt: string
  prepared_prompt: string
  prompt_template: string
  attack_module: string
}

const RED_TEAM_SESSION_KEY = 'oxo-red-team-sessions'
const PROMPT_TOKEN = '{{ prompt }}'

const store = useMoonshotStore()
const message = useMessage()
const route = useRoute()
const router = useRouter()
const mode = ref<EndpointMode>(route.query.view === 'endpoints' ? 'list' : 'menu')
const selectedEndpointId = ref('')
const editingId = ref('')
const submitting = ref(false)
const endpointSearch = ref('')
const redStep = ref(1)
const activeSessionId = ref('')
const activeChatId = ref('')
const chatPrompt = ref('')
const chatSending = ref(false)
const previewModalOpen = ref(false)
const templateModalOpen = ref(false)
const templateSubmitting = ref(false)
const chatScrollbarRef = ref<{ scrollTo: (options: { top: number; behavior?: ScrollBehavior }) => void } | null>(null)
const baselineScrollbarRef = ref<{ scrollTo: (options: { top: number; behavior?: ScrollBehavior }) => void } | null>(null)
const redTeamSessions = ref<RedTeamSession[]>([])
const connectorCount = ref(0)
const templateBlocks = ref<Array<{ id: string; type: 'text' | 'prompt'; value: string }>>([])
const paramsText = ref('{\n  "timeout": 300,\n  "max_attempts": 3,\n  "temperature": 0.5\n}')

const form = reactive<EndpointCreatePayload>({
  name: '',
  connector_type: '',
  uri: '',
  token: '',
  max_calls_per_second: 10,
  max_concurrency: 1,
  model: '',
  params: {},
})

const sessionForm = reactive({
  name: '',
  description: '',
  endpointId: '',
  endpointName: '',
  payloadId: '',
  attackModule: '',
  contextStrategy: 'none',
})

const templateForm = reactive({
  name: '',
  description: '',
})

const redSteps = [
  { label: 'Connect Endpoint', index: 1 },
  { label: 'Set Optional Utilities', index: 2 },
  { label: 'Start Red Teaming', index: 3 },
]

const contextOptions = [
  { label: 'None', value: 'none' },
  { label: 'Last 5 prompts', value: 'last-5-prompts' },
  { label: 'Full conversation', value: 'full-conversation' },
]

const connectorOptions = computed(() =>
  store.connectorTypes.map((type) => ({ label: type, value: type })),
)

const payloadOptions = computed(() =>
  store.promptTemplates.map((template) => ({
    label: template.name || template.id || 'Unnamed template',
    value: String(template.id || template.name || ''),
  })).filter((item) => item.value),
)

const attackModuleOptions = computed(() =>
  store.attackModules.map((module) => ({ label: humanizeId(module), value: module })),
)

const activeEndpoint = computed(() => {
  return (
    store.endpoints.find((endpoint) => endpointId(endpoint) === selectedEndpointId.value) ??
    store.endpoints[0]
  )
})

const filteredEndpoints = computed(() => {
  const keyword = endpointSearch.value.trim().toLowerCase()
  if (!keyword) return store.endpoints
  return store.endpoints.filter((endpoint) =>
    [endpoint.name, endpoint.id, endpoint.connector_type, endpoint.model, endpoint.uri]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(keyword)),
  )
})

const activeSession = computed(() => redTeamSessions.value.find((session) => session.id === activeSessionId.value))

const activeChat = computed(() => activeSession.value?.chats.find((chat) => chat.id === activeChatId.value))

const chatHistoryThreads = computed(() =>
  (activeSession.value?.chats || []).filter((chat) => hasChatMessages(chat)),
)

const preparedPromptPreview = computed(() => {
  const session = activeSession.value
  if (!session) return chatPrompt.value
  return preparePromptLocally(chatPrompt.value, session.payloadId, session.attackModule).prepared_prompt
})

const compactPreparedPromptPreview = computed(() => {
  const lines = preparedPromptPreview.value.split(/\r?\n/)
  const visible = lines.slice(0, 5).join('\n')
  if (lines.length <= 5 && preparedPromptPreview.value.length <= 520) return visible
  return `${visible}\n...`
})

const templateBody = computed(() =>
  templateBlocks.value
    .map((block) => (block.type === 'prompt' ? PROMPT_TOKEN : block.value))
    .join(''),
)

const canCreateTemplate = computed(() => templateForm.name.trim() && templateBody.value.includes(PROMPT_TOKEN))

onMounted(() => {
  void loadSessions()
  void loadConnectorCount()
})

async function loadConnectorCount() {
  connectorCount.value = (await connectorService.listConnectors()).length
}

function endpointId(endpoint?: EndpointRecord) {
  return String(endpoint?.id || endpoint?.name || '')
}

function resetForm() {
  editingId.value = ''
  form.name = ''
  form.connector_type = store.connectorTypes[0] || ''
  form.uri = ''
  form.token = ''
  form.max_calls_per_second = 10
  form.max_concurrency = 1
  form.model = ''
  form.params = {}
  paramsText.value = '{\n  "timeout": 300,\n  "max_attempts": 3,\n  "temperature": 0.5\n}'
}

function openCreate() {
  resetForm()
  mode.value = 'form-basic'
}

function openCustomEndpointCreate() {
  void router.push(`/agents/connectors/new?connector_type=${encodeURIComponent(CONFIGURABLE_CONNECTOR)}`)
}

function openEdit(endpoint: EndpointRecord) {
  if (endpoint.connector_type === CONFIGURABLE_CONNECTOR) {
    void router.push(`/agents/connectors/${encodeURIComponent(CONFIGURABLE_CONNECTOR)}/edit?endpointId=${encodeURIComponent(endpointId(endpoint))}`)
    return
  }
  editingId.value = endpointId(endpoint)
  form.name = endpoint.name || endpoint.id || ''
  form.connector_type = endpoint.connector_type || store.connectorTypes[0] || ''
  form.uri = endpoint.uri || ''
  form.token = endpoint.token || ''
  form.max_calls_per_second = endpoint.max_calls_per_second ?? 10
  form.max_concurrency = endpoint.max_concurrency ?? 1
  form.model = endpoint.model || ''
  form.params = endpoint.params || {}
  paramsText.value = formatParams(endpoint.params)
  mode.value = 'form-basic'
}

async function submitEndpoint() {
  if (!form.name.trim()) {
    message.warning('Please enter endpoint name')
    return
  }
  if (!form.connector_type) {
    message.warning('Please select connection type')
    return
  }

  submitting.value = true
  try {
    const params = JSON.parse(paramsText.value || '{}')
    const payload = {
      ...form,
      name: form.name.trim(),
      uri: form.uri.trim(),
      token: form.token.trim(),
      model: form.model.trim(),
      params,
    }
    if (editingId.value) {
      await moonshotApi.updateEndpoint(editingId.value, payload)
      message.success('Endpoint updated')
      selectedEndpointId.value = editingId.value
    } else {
      const id = await moonshotApi.createEndpoint(payload)
      message.success('Endpoint created')
      selectedEndpointId.value = id || form.name.trim()
    }
    await store.loadOverview()
    mode.value = 'list'
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Save endpoint failed')
  } finally {
    submitting.value = false
  }
}

async function deleteEndpoint(endpoint: EndpointRecord) {
  const id = endpointId(endpoint)
  if (!id) return
  try {
    await moonshotApi.deleteEndpoint(id)
    message.success('Endpoint deleted')
    selectedEndpointId.value = ''
    await store.loadOverview()
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Delete endpoint failed')
  }
}

function formatParams(params?: Record<string, unknown>) {
  return JSON.stringify(params || {}, null, 2)
}

function openSessionWizard(endpoint?: EndpointRecord) {
  redStep.value = 1
  sessionForm.name = `red-team-${new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')}`
  sessionForm.description = ''
  sessionForm.endpointId = ''
  sessionForm.endpointName = ''
  sessionForm.payloadId = payloadOptions.value[0]?.value || ''
  sessionForm.attackModule = attackModuleOptions.value[0]?.value || ''
  sessionForm.contextStrategy = 'none'
  endpointSearch.value = ''
  if (endpoint) selectSessionEndpoint(endpoint)
  mode.value = 'session-wizard'
}

function selectSessionEndpoint(endpoint: EndpointRecord) {
  sessionForm.endpointId = endpointId(endpoint)
  sessionForm.endpointName = endpoint.name || endpoint.id || sessionForm.endpointId
}

function createEmptyChatThread(session: RedTeamSession, now = new Date().toISOString()): RedTeamChatThread {
  return {
    id: `chat-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    title: `${session.endpointName || session.name} ${new Date().toLocaleString()}`,
    createdAt: now,
    updatedAt: now,
    messages: [],
    baselineMessages: [],
    compareEnabled: false,
  }
}

function nextRedStep() {
  if (redStep.value === 1 && !sessionForm.endpointId) {
    message.warning('Select an endpoint first')
    return
  }
  redStep.value += 1
}

async function createRedTeamSession() {
  if (!sessionForm.endpointId) {
    redStep.value = 1
    message.warning('Select an endpoint first')
    return
  }
  if (!sessionForm.name.trim()) {
    message.warning('Please enter session name')
    return
  }

  const now = new Date().toISOString()
  let sessionId = `rt-${Date.now()}`
  try {
    const remote = await moonshotApi.createRedTeamSession({
      name: sessionForm.name.trim(),
      description: sessionForm.description.trim(),
      endpoints: [sessionForm.endpointId],
      runner_args: {
        prompt_template: sessionForm.payloadId,
        attack_module: sessionForm.attackModule,
        context_strategy: moonshotContextStrategy(sessionForm.contextStrategy),
        cs_num_of_prev_prompts: sessionForm.contextStrategy === 'last-5-prompts' ? 5 : 0,
        metric: '',
        system_prompt: '',
      },
    })
    sessionId = remote.runner_id || sessionId
  } catch (error) {
    message.warning(error instanceof Error ? `Session saved locally: ${error.message}` : 'Session saved locally')
  }
  const session: RedTeamSession = {
    id: sessionId,
    name: sessionForm.name.trim(),
    description: sessionForm.description.trim(),
    endpointId: sessionForm.endpointId,
    endpointName: sessionForm.endpointName,
    payloadId: sessionForm.payloadId,
    attackModule: sessionForm.attackModule,
    contextStrategy: sessionForm.contextStrategy,
    createdAt: now,
    updatedAt: now,
    chats: [],
  }
  session.chats = [createEmptyChatThread(session, now)]
  redTeamSessions.value = [session, ...redTeamSessions.value]
  persistSessions()
  openChat(session)
  message.success('Red team session created')
}

function openChat(session: RedTeamSession) {
  activeSessionId.value = session.id
  if (!session.chats.length) session.chats.push(createEmptyChatThread(session))
  activeChatId.value = session.chats[0].id
  chatPrompt.value = ''
  mode.value = 'chat'
}

function openChatThread(chatId: string) {
  activeChatId.value = chatId
  chatPrompt.value = ''
}

async function deleteSession(id: string) {
  redTeamSessions.value = redTeamSessions.value.filter((session) => session.id !== id)
  if (activeSessionId.value === id) {
    const fallback = redTeamSessions.value[0]
    if (fallback) {
      openChat(fallback)
    } else {
      activeSessionId.value = ''
      activeChatId.value = ''
      mode.value = 'sessions'
    }
  }
  persistSessions()
  try {
    await moonshotApi.deleteLocalRedTeamSession(id)
  } catch {
    // Local browser state is already updated; backend persistence can recover on next save.
  }
  message.success('Session deleted')
}

function deleteChatThread(chatId: string) {
  const session = activeSession.value
  if (!session) return
  session.chats = session.chats.filter((chat) => chat.id !== chatId)
  if (!session.chats.length) session.chats.push(createEmptyChatThread(session))
  if (activeChatId.value === chatId) activeChatId.value = session.chats[0].id
  session.updatedAt = new Date().toISOString()
  persistSessions()
}

async function ensureRemoteSession(session: RedTeamSession) {
  if (!session.id.startsWith('rt-')) return session.id
  try {
    const remote = await moonshotApi.createRedTeamSession({
      name: session.name,
      description: session.description,
      endpoints: [session.endpointId],
      runner_args: {
        prompt_template: session.payloadId,
        attack_module: '',
        context_strategy: moonshotContextStrategy(session.contextStrategy),
        cs_num_of_prev_prompts: session.contextStrategy === 'last-5-prompts' ? 5 : 0,
        metric: '',
        system_prompt: '',
      },
    })
    session.id = remote.runner_id || session.id
    activeSessionId.value = session.id
    persistSessions()
    return session.id
  } catch (error) {
    void error
    return ''
  }
}

async function updateActiveSession(field: 'payloadId' | 'attackModule' | 'contextStrategy', value: string) {
  const session = activeSession.value
  if (!session) return
  session[field] = value
  session.updatedAt = new Date().toISOString()
  persistSessions()
  if (session.id.startsWith('rt-')) return
  try {
    if (field === 'payloadId') {
      await moonshotApi.updateSessionPromptTemplate(session.id, value)
    } else if (field === 'attackModule') {
      await moonshotApi.updateSessionAttackModule(session.id, value)
    } else {
      await moonshotApi.updateSessionContextStrategy(session.id, moonshotContextStrategy(value))
    }
  } catch (error) {
    message.warning(error instanceof Error ? error.message : 'Session option was saved locally only')
  }
}

async function sendChatPrompt() {
  const session = activeSession.value
  const chat = activeChat.value
  const prompt = chatPrompt.value.trim()
  if (!session || !chat || !prompt) return

  let prepared = preparePromptLocally(prompt, session.payloadId, session.attackModule)
  try {
    prepared = await moonshotApi.prepareRedTeamPrompt({
      prompt,
      prompt_template: session.payloadId,
      attack_module: session.attackModule,
    })
  } catch {
    // Keep the UI responsive if the backend preview endpoint is not available yet.
  }

  const runnerId = await ensureRemoteSession(session)
  if (!runnerId) {
    message.error('Unable to create Moonshot session. Prompt was not sent.')
    return
  }

  const now = new Date().toISOString()
  const primaryAssistantId = `msg-${Date.now()}-assistant`
  const primaryAssistant: RedTeamMessage = {
    id: primaryAssistantId,
    role: 'assistant',
    content: '',
    createdAt: new Date().toISOString(),
    status: 'pending',
  }
  chat.messages.push({
    id: `msg-${Date.now()}`,
    role: 'user',
    content: prepared.prepared_prompt,
    createdAt: now,
    status: 'done',
  })
  chat.messages.push(primaryAssistant)

  let baselineAssistant: RedTeamMessage | null = null
  if (chat.compareEnabled) {
    const baselineAssistantId = `msg-${Date.now()}-baseline-assistant`
    baselineAssistant = {
      id: baselineAssistantId,
      role: 'assistant',
      content: '',
      createdAt: new Date().toISOString(),
      status: 'pending',
    }
    chat.baselineMessages.push({
      id: `msg-${Date.now()}-baseline`,
      role: 'user',
      content: prompt,
      createdAt: now,
      status: 'done',
    })
    chat.baselineMessages.push(baselineAssistant)
  }

  chatPrompt.value = ''
  chatSending.value = true
  chat.updatedAt = now
  session.updatedAt = now
  persistSessions()
  await scrollChatToBottom()

  const sendPrimary = sendPromptToMessage(runnerId, prompt, prepared.prepared_prompt, primaryAssistant.id)
  const sendBaseline = baselineAssistant
    ? sendPromptToMessage(runnerId, prompt, prompt, baselineAssistant.id)
    : Promise.resolve()

  await Promise.allSettled([sendPrimary, sendBaseline])
  chatSending.value = false
  session.updatedAt = new Date().toISOString()
  persistSessions()
  await scrollChatToBottom()
}

async function sendPromptToMessage(runnerId: string, userPrompt: string, preparedPrompt: string, messageId: string) {
  try {
    const response = await moonshotApi.sendRedTeamPrompt(runnerId, userPrompt, preparedPrompt)
    void typeAssistantMessage(messageId, stringifyResponse(response))
  } catch (error) {
    updateRedTeamMessage(messageId, {
      status: 'error',
      content: error instanceof Error ? `Oxo Tracker request failed: ${error.message}` : 'Oxo Tracker request failed.',
    })
    message.error(error instanceof Error ? error.message : 'Send prompt failed')
  }
}

function handleComposerKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return
  event.preventDefault()
  void sendChatPrompt()
}

async function scrollChatToBottom() {
  await nextTick()
  chatScrollbarRef.value?.scrollTo({ top: Number.MAX_SAFE_INTEGER, behavior: 'smooth' })
  baselineScrollbarRef.value?.scrollTo({ top: Number.MAX_SAFE_INTEGER, behavior: 'smooth' })
}

async function typeAssistantMessage(messageId: string, text: string) {
  updateRedTeamMessage(messageId, { status: 'typing', content: '' })
  const normalized = text || 'No response content.'
  let content = ''
  for (const char of normalized) {
    content += char
    updateRedTeamMessage(messageId, { content })
    if (content.length % 3 === 0 || char === '\n') {
      await scrollChatToBottom()
    }
    await new Promise((resolve) => window.setTimeout(resolve, char === '\n' ? 24 : 10))
  }
  updateRedTeamMessage(messageId, { status: 'done', content })
  persistSessions()
  await scrollChatToBottom()
}

function updateRedTeamMessage(messageId: string, patch: Partial<RedTeamMessage>) {
  for (const session of redTeamSessions.value) {
    for (const chat of session.chats) {
      const groups = [chat.messages, chat.baselineMessages]
      for (const group of groups) {
        const index = group.findIndex((messageItem) => messageItem.id === messageId)
        if (index >= 0) {
          group[index] = { ...group[index], ...patch }
          chat.updatedAt = new Date().toISOString()
          session.updatedAt = chat.updatedAt
          return
        }
      }
    }
  }
}

async function loadSessions() {
  try {
    const sessions = await moonshotApi.getLocalRedTeamSessions()
    redTeamSessions.value = normalizeSessions(sessions)
    if (redTeamSessions.value.length) return
  } catch {
    // Fall back to the old browser cache for existing local sessions.
  }
  try {
    redTeamSessions.value = normalizeSessions(JSON.parse(window.localStorage.getItem(RED_TEAM_SESSION_KEY) || '[]'))
  } catch {
    redTeamSessions.value = []
  }
}

function persistSessions() {
  window.localStorage.setItem(RED_TEAM_SESSION_KEY, JSON.stringify(redTeamSessions.value))
  for (const session of redTeamSessions.value) {
    void moonshotApi.saveLocalRedTeamSession(session.id, session)
  }
}

function normalizeSessions(value: unknown): RedTeamSession[] {
  if (!Array.isArray(value)) return []
  return value
    .filter((item): item is RedTeamSession => !!item && typeof item === 'object' && 'id' in item)
    .map((session) => {
      const migratedChat: RedTeamChatThread | null =
        Array.isArray(session.messages) && session.messages.length
          ? {
              id: `chat-${session.id}`,
              title: session.name || session.endpointName || 'Chat',
              createdAt: session.createdAt,
              updatedAt: session.updatedAt,
              messages: session.messages,
              baselineMessages: Array.isArray(session.baselineMessages) ? session.baselineMessages : [],
              compareEnabled: Boolean(session.compareEnabled),
            }
          : null
      const chats = Array.isArray(session.chats)
        ? session.chats.map((chat) => ({
            ...chat,
            messages: Array.isArray(chat.messages) ? chat.messages : [],
            baselineMessages: Array.isArray(chat.baselineMessages) ? chat.baselineMessages : [],
            compareEnabled: Boolean(chat.compareEnabled),
          }))
        : []
      return {
        ...session,
        chats: chats.length ? chats : migratedChat ? [migratedChat] : [createEmptyChatThread(session)],
        messages: [],
        baselineMessages: [],
        compareEnabled: false,
      }
    })
}

function hasChatMessages(chat: RedTeamChatThread) {
  return Boolean((chat.messages || []).length || (chat.baselineMessages || []).length)
}

function clearActiveChat() {
  const session = activeSession.value
  const chat = activeChat.value
  if (!session || !chat) return

  const now = new Date().toISOString()
  if (!hasChatMessages(chat)) {
    session.updatedAt = now
    persistSessions()
    return
  }

  const newChat = createEmptyChatThread(session, now)
  newChat.compareEnabled = chat.compareEnabled
  session.chats = [newChat, ...session.chats]
  session.updatedAt = now
  activeChatId.value = newChat.id
  chatPrompt.value = ''
  persistSessions()
  void scrollChatToBottom()
}

function toggleBaselineChat() {
  const session = activeSession.value
  const chat = activeChat.value
  if (!session || !chat) return
  chat.compareEnabled = !chat.compareEnabled
  session.updatedAt = new Date().toISOString()
  persistSessions()
}

function openTemplateModal() {
  templateForm.name = ''
  templateForm.description = ''
  templateBlocks.value = [{ id: `block-${Date.now()}`, type: 'text', value: '' }]
  templateModalOpen.value = true
}

function insertPromptBlock() {
  templateBlocks.value.push(
    { id: `block-${Date.now()}-prompt`, type: 'prompt', value: PROMPT_TOKEN },
    { id: `block-${Date.now()}-text`, type: 'text', value: '' },
  )
}

function removeTemplateBlock(index: number) {
  const previous = templateBlocks.value[index - 1]
  const next = templateBlocks.value[index + 1]
  if (templateBlocks.value[index]?.type === 'prompt' && previous?.type === 'text' && next?.type === 'text') {
    previous.value = `${previous.value}${next.value}`
    templateBlocks.value.splice(index, 2)
    return
  }
  templateBlocks.value.splice(index, 1)
}

function renderTemplateParts(value: string) {
  return value
    .split(/(\{\{\s*prompt\s*\}\})/g)
    .filter(Boolean)
    .map((part) => (/\{\{\s*prompt\s*\}\}/.test(part) ? { type: 'prompt', value: part } : { type: 'text', value: part }))
}

async function createPromptTemplate() {
  const session = activeSession.value
  if (!canCreateTemplate.value) return
  templateSubmitting.value = true
  try {
    const id = await moonshotApi.createPromptTemplate({
      name: templateForm.name.trim(),
      description: templateForm.description.trim(),
      template: templateBody.value,
    })
    await store.loadOverview()
    if (session) {
      await updateActiveSession('payloadId', id)
    }
    templateModalOpen.value = false
    message.success('Prompt template created')
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Create prompt template failed')
  } finally {
    templateSubmitting.value = false
  }
}

function chatPreview(chat: RedTeamChatThread) {
  const last = [...(chat.messages || []), ...(chat.baselineMessages || [])]
    .filter((item) => item.role === 'user' || item.role === 'assistant')
    .at(-1)
  return last?.content ? displayAssistantContent(last.content).slice(0, 64) : 'New chat'
}

function humanizeId(value: string) {
  return value
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function labelOrNone(value?: string) {
  if (!value) return 'None'
  const payload = payloadOptions.value.find((item) => item.value === value)
  const attack = attackModuleOptions.value.find((item) => item.value === value)
  return payload?.label || attack?.label || humanizeId(value)
}

function preparePromptLocally(prompt: string, promptTemplate: string, attackModule: string): PreparedPrompt {
  const templatedPrompt = applyPromptTemplate(prompt, promptTemplate)
  return {
    original_prompt: prompt,
    templated_prompt: templatedPrompt,
    prepared_prompt: applyAttackPreview(templatedPrompt, attackModule),
    prompt_template: promptTemplate,
    attack_module: attackModule,
  }
}

function applyPromptTemplate(prompt: string, promptTemplate: string) {
  const template = store.promptTemplates.find((item) => String(item.id || item.name || '') === promptTemplate)?.template
  if (!template) return prompt
  return template
    .replaceAll('{{ prompt }}', prompt)
    .replaceAll('{{prompt}}', prompt)
    .replaceAll('{prompt}', prompt)
}

function applyAttackPreview(prompt: string, attackModule: string) {
  const attackId = attackModule.toLowerCase()
  if (!attackId) return prompt
  if (attackId.includes('charswap') || attackId.includes('char_swap')) {
    return prompt.replace(/\b([A-Za-z]{4,})\b/, (word) => swapMiddleChars(word))
  }
  if (attackId.includes('punctuation')) {
    return prompt.replace(/\b(\w)/g, '.$1')
  }
  if (attackId.includes('mask')) {
    let remaining = Math.max(1, Math.min(8, Math.floor(prompt.length / 8)))
    return prompt.replace(/[A-Za-z]/g, (letter) => {
      if (remaining <= 0) return letter
      remaining -= 1
      return '_'
    })
  }
  if (attackId.includes('homoglyph')) {
    const table: Record<string, string> = { a: 'а', e: 'е', o: 'ο', p: 'р', c: 'с', x: 'х' }
    return prompt.replace(/[aeopcx]/g, (letter) => table[letter] || letter)
  }
  if (attackId.includes('textbugger') || attackId.includes('fooler')) {
    return prompt.replace(/\b([A-Za-z]{5,})\b/, (word) => `${word.slice(0, -1)}${word.at(-1)}`)
  }
  return prompt
}

function swapMiddleChars(word: string) {
  if (word.length < 4) return word
  const letters = word.split('')
  const second = letters[1]
  letters[1] = letters[2]
  letters[2] = second
  return letters.join('')
}

function attackModuleDescription(value: string) {
  const name = value.toLowerCase()
  if (name.includes('punctuation')) return 'Adds punctuation perturbations to probe prompt robustness.'
  if (name.includes('mask')) return 'Masks payload content and asks the model to recover missing information.'
  if (name.includes('homoglyph')) return 'Uses visually similar characters to test adversarial text handling.'
  if (name.includes('question')) return 'Generates malicious or risky question variants for the session.'
  if (name.includes('bugger')) return 'Applies typo and text mutation strategies to the base prompt.'
  return 'Optional utility that transforms prompts during red-team testing.'
}

function moonshotContextStrategy(value: string) {
  if (value === 'last-5-prompts') return 'last_n_prompts'
  if (value === 'full-conversation') return 'all_prompts'
  return ''
}

function stringifyResponse(response: unknown): string {
  if (typeof response === 'string') return response
  if (Array.isArray(response)) {
    return response
      .map((item) => stringifyResponse(item))
      .filter(Boolean)
      .join('\n\n')
  }
  if (response && typeof response === 'object') {
    return extractAssistantText(response) || 'No response content.'
  }
  return String(response ?? '')
}

function displayAssistantContent(content: string) {
  const trimmed = content.trim()
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) return content
  try {
    return extractAssistantText(JSON.parse(trimmed)) || content
  } catch {
    return content
  }
}

function extractAssistantText(value: unknown): string {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    for (let index = value.length - 1; index >= 0; index -= 1) {
      const extracted = extractAssistantText(value[index])
      if (extracted) return extracted
    }
    return ''
  }
  if (!value || typeof value !== 'object') return ''

  const record = value as Record<string, unknown>
  for (const key of ['predicted_result', 'response', 'answer', 'message', 'content', 'output', 'result']) {
    const candidate = record[key]
    if (typeof candidate === 'string' && candidate.trim()) return candidate
  }

  const currentChats = record.current_chats
  if (currentChats && typeof currentChats === 'object') {
    const chatGroups = Object.values(currentChats as Record<string, unknown>)
    for (let groupIndex = chatGroups.length - 1; groupIndex >= 0; groupIndex -= 1) {
      const extracted = extractAssistantText(chatGroups[groupIndex])
      if (extracted) return extracted
    }
  }

  return extractAssistantText(record.root)
}
</script>
