<template>
  <div class="ai-settings-shell">
    <section class="ai-settings-head">
      <div class="workspace-title-block">
        <span class="workspace-title-icon workspace-title-icon--settings">
          <n-icon><PulseOutline /></n-icon>
        </span>
        <div class="workspace-title-content">
          <p class="eyebrow">{{ $t('auto.242aa5c54960') }}</p>
          <h2>{{ $t('auto.6dcf51d7630d') }}</h2>
          <p>{{ $t('auto.c3e0e45595fc') }}</p>
        </div>
      </div>
      <div v-if="activeCatalog" class="ai-active-summary">
        <span class="ai-live-dot" />
        <div>
          <small>{{ $t('auto.3592eeeed275') }}</small>
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
                <h3>{{ $t('auto.c7a9e8ea6a4e') }}</h3>
                <p>{{ $t('auto.4a6d8451d5e2') }}</p>
              </div>
            </div>
            <span class="ai-selection-count">{{ $t('auto.dbd388ae9a47') }}</span>
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
              <span v-if="providerSettings(providerId)?.apiKeyConfigured" class="ai-key-badge">{{ $t('auto.1631340bef8f') }}</span>
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
                <span>{{ $t('auto.025381a81c8c') }}</span>
                <h3>{{ selectedCatalog.label }}</h3>
                <p>{{ selectedCatalog.description }}</p>
              </div>
            </div>
            <span class="ai-provider-state" :class="{ configured: selectedConfiguration.apiKeyConfigured }">
              {{ selectedConfiguration.apiKeyConfigured ? $t('auto.33378176a17e') : $t('auto.a5c7a7edaa8a') }}
            </span>
          </div>

          <div class="ai-task-agent-runtime">
            <span><n-icon><SparklesOutline /></n-icon></span>
            <div>
              <strong>{{ $t('auto.cb5e1cfac2d2') }}</strong>
              <small>{{ $t('auto.9c48f85835ba') }}</small>
            </div>
            <div class="ai-task-agent-roles">
              <b>{{ $t('auto.eca1f9189600') }}</b><b>{{ $t('auto.c1f6604b7486') }}</b><b>AI WATCH</b>
            </div>
          </div>

          <div class="ai-config-form">
            <label class="ai-field">
              <span>{{ $t('auto.68c2cc7f0cea') }}</span>
              <n-select
                v-model:value="selectedConfiguration.model"
                :options="modelOptions"
                filterable
                tag
                :placeholder="$t('auto.d35557e32653')"
              />
              <small>{{ $t('auto.945f1be74862') }}</small>
              <span class="ai-model-catalog-meta">
                {{ selectedCatalog.models.length }} {{ $t('auto.39322afbade2') }} {{ formatCatalogDate(selectedCatalog.catalogCheckedAt) }}
                <a v-if="selectedCatalog.catalogUrl" :href="selectedCatalog.catalogUrl" target="_blank" rel="noreferrer">{{ $t('auto.d4d19cf1226d') }}</a>
              </span>
            </label>

            <label class="ai-field ai-field--wide">
              <span>{{ $t('auto.1dbd61f556fe') }}</span>
              <n-input v-model:value="selectedConfiguration.baseUrl" placeholder="https://api.example.com/v1" />
              <small>{{ $t('auto.a0294bd8127d') }} <code>/chat/completions</code>.</small>
            </label>

            <div class="ai-field ai-field--wide">
              <span>{{ selectedCatalog.apiKeyLabel }}</span>
              <div v-if="selectedConfiguration.apiKeyConfigured && !editingApiKey" class="ai-key-input-row">
                <n-input
                  :value="selectedConfiguration.apiKeyMasked || '••••••••'"
                  readonly
                  :aria-label="$t('auto.b362498d4009')"
                />
                <n-button :loading="copyingKey" @click="copyApiKey">
                  <template #icon><n-icon><CopyOutline /></n-icon></template> {{ $t('auto.af74f7c5362a') }} </n-button>
                <n-button secondary @click="beginApiKeyReplacement">
                  <template #icon><n-icon><CreateOutline /></n-icon></template> {{ $t('auto.a7cf7b25a703') }} </n-button>
              </div>
              <div v-else class="ai-key-input-row ai-key-input-row--editing">
                <n-input
                  v-model:value="draftApiKey"
                  type="password"
                  show-password-on="click"
                  :placeholder="$t('auto.4c6bf5d58673')"
                  autocomplete="new-password"
                />
                <n-button v-if="selectedConfiguration.apiKeyConfigured" secondary @click="cancelApiKeyReplacement">{{ $t('auto.77dfd2135f4d') }}</n-button>
              </div>
              <small v-if="selectedConfiguration.apiKeyConfigured && !editingApiKey">{{ $t('auto.6fead441b710') }}</small>
              <small v-else>{{ selectedConfiguration.apiKeyConfigured ? $t('auto.ff69c061614b') : $t('auto.0909bd235b89') }}</small>
            </div>
          </div>

          <div class="ai-config-footer">
            <div class="ai-footer-info">
              <div class="ai-security-note">
                <n-icon size="20"><ShieldCheckmarkOutline /></n-icon>
                <span><strong>{{ $t('auto.3465848e96ad') }}</strong>{{ $t('auto.afd1ffca1cf8') }} <code>data/settings/app-settings.yaml</code>{{ $t('auto.d10789a2924d') }}</span>
              </div>
              <div v-if="connectionResult" class="ai-connection-result" :class="{ success: connectionResult.ok, failed: !connectionResult.ok }">
                <n-icon><CheckmarkCircleOutline v-if="connectionResult.ok" /><AlertCircleOutline v-else /></n-icon>
                <span><strong>{{ connectionResult.ok ? $t('auto.808d7783c25e') : $t('auto.202caaa87055') }}</strong>{{ connectionResult.message }} · {{ connectionResult.latencyMs }} {{ $t('auto.26cc3217be64') }}</span>
              </div>
            </div>
            <div class="ai-config-actions">
              <n-button secondary :loading="testingConnection" :disabled="saving" @click="testConnection">
                <template #icon><n-icon><PulseOutline /></n-icon></template> {{ $t('auto.ccf66f074649') }} </n-button>
              <n-button secondary :disabled="saving" @click="resetDraft">{{ $t('auto.44c57abd888a') }}</n-button>
              <n-button type="primary" :loading="saving" @click="saveSettings">
                <template #icon><n-icon><SaveOutline /></n-icon></template> {{ $t('auto.2baa38e42bf5') }} </n-button>
            </div>
          </div>
        </section>
      </div>
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { translateSource } from '../i18n'

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
  SparklesOutline,
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
    message.warning(translateSource('auto.ca614c00a51e'))
    return
  }
  if (!config.apiKeyConfigured && !draftApiKey.value.trim()) {
    message.warning(translateSource('auto.38fd81d2802f'))
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
    message.warning(translateSource('auto.ca614c00a51e'))
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
