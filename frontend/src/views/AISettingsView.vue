<template>
  <div class="ai-settings-shell">
    <section class="ai-settings-head">
      <div class="workspace-title-block">
        <span class="workspace-title-icon workspace-title-icon--settings">
          <n-icon><PulseOutline /></n-icon>
        </span>
        <div class="workspace-title-content">
          <p class="eyebrow">Model runtime</p>
          <h2>AI settings</h2>
          <p>Configure one active model for Oxo Tracker. Provider credentials stay encrypted locally and are revealed only for an explicit copy action.</p>
        </div>
      </div>
      <div v-if="activeCatalog" class="ai-active-summary">
        <span class="ai-live-dot" />
        <div>
          <small>ACTIVE MODEL</small>
          <strong>{{ activeCatalog.label }} · {{ activeConfiguration?.model }}</strong>
        </div>
      </div>
    </section>

    <n-spin :show="loading">
      <div v-if="catalogEntries.length" class="ai-settings-content">
        <section class="ai-provider-section">
          <div class="ai-section-heading">
            <div>
              <span>01</span>
              <div>
                <h3>Select provider</h3>
                <p>Only one provider can be active at a time.</p>
              </div>
            </div>
            <span class="ai-selection-count">1 selected</span>
          </div>

          <div class="ai-provider-grid">
            <button
              v-for="[providerId, provider] in catalogEntries"
              :key="providerId"
              type="button"
              class="ai-provider-card"
              :class="{ active: draft.activeProvider === providerId }"
              @click="selectProvider(providerId)"
            >
              <span class="ai-provider-check">
                <n-icon v-if="draft.activeProvider === providerId"><CheckmarkOutline /></n-icon>
              </span>
              <span class="ai-provider-logo">
                <img :src="provider.logo" :alt="`${provider.label} logo`" />
              </span>
              <span class="ai-provider-copy">
                <strong>{{ provider.label }}</strong>
                <small>{{ provider.company }}</small>
              </span>
              <span v-if="providerSettings(providerId)?.apiKeyConfigured" class="ai-key-badge">Key saved</span>
            </button>
          </div>
        </section>

        <section v-if="selectedCatalog && selectedConfiguration" class="ai-config-panel">
          <div class="ai-config-heading">
            <div class="ai-config-title">
              <span class="ai-provider-logo ai-provider-logo--large">
                <img :src="selectedCatalog.logo" :alt="`${selectedCatalog.label} logo`" />
              </span>
              <div>
                <span>02 · MODEL CONFIGURATION</span>
                <h3>{{ selectedCatalog.label }}</h3>
                <p>{{ selectedCatalog.description }}</p>
              </div>
            </div>
            <span class="ai-provider-state" :class="{ configured: selectedConfiguration.apiKeyConfigured }">
              {{ selectedConfiguration.apiKeyConfigured ? 'Credential ready' : 'Credential required' }}
            </span>
          </div>

          <div class="ai-config-form">
            <label class="ai-field">
              <span>Model</span>
              <n-select
                v-model:value="selectedConfiguration.model"
                :options="modelOptions"
                filterable
                tag
                placeholder="Select or enter a model ID"
              />
              <small>Select a suggested model or type a custom model/deployment ID.</small>
              <span class="ai-model-catalog-meta">
                {{ selectedCatalog.models.length }} curated model IDs · checked {{ formatCatalogDate(selectedCatalog.catalogCheckedAt) }}
                <a v-if="selectedCatalog.catalogUrl" :href="selectedCatalog.catalogUrl" target="_blank" rel="noreferrer">Official catalog</a>
              </span>
            </label>

            <label class="ai-field ai-field--wide">
              <span>Base URL</span>
              <n-input v-model:value="selectedConfiguration.baseUrl" placeholder="https://api.example.com/v1" />
              <small>Use the provider's OpenAI-compatible API root. Do not include <code>/chat/completions</code>.</small>
            </label>

            <div class="ai-field ai-field--wide">
              <span>{{ selectedCatalog.apiKeyLabel }}</span>
              <div v-if="selectedConfiguration.apiKeyConfigured && !editingApiKey" class="ai-key-input-row">
                <n-input
                  :value="selectedConfiguration.apiKeyMasked || '••••••••'"
                  readonly
                  aria-label="Masked saved API key"
                />
                <n-button :loading="copyingKey" @click="copyApiKey">
                  <template #icon><n-icon><CopyOutline /></n-icon></template>
                  Copy
                </n-button>
                <n-button secondary @click="beginApiKeyReplacement">
                  <template #icon><n-icon><CreateOutline /></n-icon></template>
                  Replace
                </n-button>
              </div>
              <div v-else class="ai-key-input-row ai-key-input-row--editing">
                <n-input
                  v-model:value="draftApiKey"
                  type="password"
                  show-password-on="click"
                  placeholder="Enter API key"
                  autocomplete="new-password"
                />
                <n-button v-if="selectedConfiguration.apiKeyConfigured" secondary @click="cancelApiKeyReplacement">Cancel</n-button>
              </div>
              <small v-if="selectedConfiguration.apiKeyConfigured && !editingApiKey">Only a masked preview is shown. Copy retrieves the full key once without storing it in the page.</small>
              <small v-else>{{ selectedConfiguration.apiKeyConfigured ? 'Enter a new key to replace the saved credential.' : 'The key is encrypted with Windows DPAPI before it is written to YAML.' }}</small>
            </div>
          </div>

          <div class="ai-config-footer">
            <div class="ai-footer-info">
              <div class="ai-security-note">
                <n-icon size="20"><ShieldCheckmarkOutline /></n-icon>
                <span><strong>Local & protected</strong>Settings are stored in <code>data/settings/app-settings.yaml</code>. A full key is returned only when you press Copy.</span>
              </div>
              <div v-if="connectionResult" class="ai-connection-result" :class="{ success: connectionResult.ok, failed: !connectionResult.ok }">
                <n-icon><CheckmarkCircleOutline v-if="connectionResult.ok" /><AlertCircleOutline v-else /></n-icon>
                <span><strong>{{ connectionResult.ok ? 'Connection ready' : 'Connection failed' }}</strong>{{ connectionResult.message }} · {{ connectionResult.latencyMs }} ms</span>
              </div>
            </div>
            <div class="ai-config-actions">
              <n-button secondary :loading="testingConnection" :disabled="saving" @click="testConnection">
                <template #icon><n-icon><PulseOutline /></n-icon></template>
                Test connection
              </n-button>
              <n-button secondary :disabled="saving" @click="resetDraft">Reset</n-button>
              <n-button type="primary" :loading="saving" @click="saveSettings">
                <template #icon><n-icon><SaveOutline /></n-icon></template>
                Save & activate
              </n-button>
            </div>
          </div>
        </section>
      </div>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import {
  AlertCircleOutline,
  CheckmarkOutline,
  CheckmarkCircleOutline,
  CopyOutline,
  CreateOutline,
  PulseOutline,
  SaveOutline,
  ShieldCheckmarkOutline,
} from '@vicons/ionicons5'
import { moonshotApi } from '../api/moonshot'
import { useSettingsStore } from '../stores/settings'
import type { AIConnectionTestResult, AIProviderSettings, AISettings } from '../types/moonshot'

const message = useMessage()
const settingsStore = useSettingsStore()
const loading = ref(true)
const saving = ref(false)
const testingConnection = ref(false)
const copyingKey = ref(false)
const editingApiKey = ref(false)
const connectionResult = ref<AIConnectionTestResult | null>(null)
const saved = ref<AISettings | null>(null)
const draftApiKey = ref('')
const draft = reactive({
  activeProvider: '',
  providers: {} as Record<string, AIProviderSettings>,
})

const catalogEntries = computed(() => Object.entries(saved.value?.catalog || {}))
const selectedCatalog = computed(() => saved.value?.catalog[draft.activeProvider])
const selectedConfiguration = computed(() => draft.providers[draft.activeProvider])
const activeCatalog = computed(() => saved.value?.catalog[saved.value.activeProvider])
const activeConfiguration = computed(() => saved.value?.providers[saved.value.activeProvider])
const modelOptions = computed(() => {
  const provider = selectedCatalog.value
  return (provider?.models || []).map((model) => ({
    label: provider?.latestModels?.includes(model) ? `${model}  ·  Latest` : model,
    value: model,
  }))
})

function formatCatalogDate(value: string) {
  if (!value) return 'recently'
  return new Intl.DateTimeFormat('en', { year: 'numeric', month: 'short', day: 'numeric' }).format(new Date(`${value}T00:00:00`))
}

function cloneProviders(providers: Record<string, AIProviderSettings>) {
  return Object.fromEntries(Object.entries(providers).map(([id, value]) => [id, { ...value }]))
}

function applySettings(ai: AISettings) {
  saved.value = ai
  draft.activeProvider = ai.activeProvider
  draft.providers = cloneProviders(ai.providers)
  draftApiKey.value = ''
  editingApiKey.value = false
  connectionResult.value = null
  settingsStore.ai = ai
}

function providerSettings(providerId: string) {
  return draft.providers[providerId]
}

function selectProvider(providerId: string) {
  draft.activeProvider = providerId
  draftApiKey.value = ''
  editingApiKey.value = false
  connectionResult.value = null
}

function resetDraft() {
  if (!saved.value) return
  draft.activeProvider = saved.value.activeProvider
  draft.providers = cloneProviders(saved.value.providers)
  draftApiKey.value = ''
  editingApiKey.value = false
  connectionResult.value = null
}

function beginApiKeyReplacement() {
  draftApiKey.value = ''
  editingApiKey.value = true
}

function cancelApiKeyReplacement() {
  draftApiKey.value = ''
  editingApiKey.value = false
}

async function writeToClipboard(value: string) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(value)
      return
    } catch {
      // Fall through for browsers that deny the async clipboard permission.
    }
  }
  const input = document.createElement('textarea')
  input.value = value
  input.style.position = 'fixed'
  input.style.opacity = '0'
  document.body.appendChild(input)
  input.select()
  const copied = document.execCommand('copy')
  input.remove()
  if (!copied) throw new Error('Clipboard permission was denied')
}

async function copyApiKey() {
  copyingKey.value = true
  let apiKey = ''
  try {
    const response = await moonshotApi.revealAIProviderApiKey(draft.activeProvider)
    apiKey = response.apiKey
    await writeToClipboard(apiKey)
    message.success(`${selectedCatalog.value?.label || 'Provider'} API key copied`)
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Unable to copy API key')
  } finally {
    apiKey = ''
    copyingKey.value = false
  }
}

async function testConnection() {
  const config = selectedConfiguration.value
  if (!config?.model.trim() || !config.baseUrl.trim()) {
    message.warning('Model and Base URL are required')
    return
  }
  if (!config.apiKeyConfigured && !draftApiKey.value.trim()) {
    message.warning('Enter an API key before testing the connection')
    return
  }
  testingConnection.value = true
  connectionResult.value = null
  try {
    const result = await moonshotApi.testAIProviderConnection({
      provider: draft.activeProvider,
      model: config.model.trim(),
      baseUrl: config.baseUrl.trim(),
      apiKey: draftApiKey.value.trim() || undefined,
    })
    connectionResult.value = result
    if (result.ok) message.success(`${selectedCatalog.value?.label || 'Provider'} connection succeeded`)
    else message.error(result.message)
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Unable to test provider connection')
  } finally {
    testingConnection.value = false
  }
}

async function loadSettings() {
  loading.value = true
  try {
    const response = await moonshotApi.getSettings()
    applySettings(response.ai)
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Unable to load AI settings')
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  const config = selectedConfiguration.value
  if (!config?.model.trim() || !config.baseUrl.trim()) {
    message.warning('Model and Base URL are required')
    return
  }
  saving.value = true
  try {
    const response = await moonshotApi.updateSettings({
      ai: {
        activeProvider: draft.activeProvider,
        provider: draft.activeProvider,
        config: {
          model: config.model.trim(),
          baseUrl: config.baseUrl.trim(),
          apiKey: draftApiKey.value.trim() || undefined,
        },
      },
    })
    applySettings(response.ai)
    message.success(`${response.ai.catalog[response.ai.activeProvider]?.label || 'AI model'} is now active`)
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Unable to save AI settings')
  } finally {
    saving.value = false
  }
}

onMounted(loadSettings)
</script>
