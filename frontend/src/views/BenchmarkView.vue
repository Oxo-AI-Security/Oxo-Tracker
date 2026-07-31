<template>
  <div class="first-test-shell">
    <GlassPanel class="first-test-panel">
      <div class="wizard-top">
        <div v-for="item in visibleSteps" :key="item.key" class="wizard-step" :class="{ active: step >= item.index }">
          <span />
          <strong>{{ item.label }}</strong>
        </div>
        <n-button circle quaternary @click="resetWizard">
          <template #icon><n-icon><CloseOutline /></n-icon></template>
        </n-button>
      </div>

      <section v-if="step === 1" class="wizard-body">
        <h2>
          <template v-if="selectedEndpoints.length">{{ selectedEndpoints.length }} {{ $t('auto.ec814ab2f067') }}</template>
          <template v-else>{{ $t('auto.1ef030ac9123') }}</template>
        </h2>
        <div class="endpoint-filter-row">
          <n-input v-model:value="endpointSearch" clearable class="endpoint-search-input" :placeholder="$t('auto.33e66c40056a')">
            <template #prefix><n-icon><SearchOutline /></n-icon></template>
          </n-input>
          <n-button secondary round @click="router.push('/endpoints')">
            <template #icon><n-icon><AddOutline /></n-icon></template> {{ $t('auto.ece414ae195d') }} </n-button>
        </div>

        <n-scrollbar v-if="filteredEndpoints.length" class="wizard-card-scrollbar">
          <div class="endpoint-select-grid">
            <article
              v-for="endpoint in filteredEndpoints"
              :key="endpointId(endpoint)"
              class="select-card endpoint-select-card"
              :class="{ selected: selectedEndpoints.includes(endpointId(endpoint)) }"
              @click="toggleEndpoint(endpoint)"
            >
              <div class="select-card-title">
                <n-icon><CubeOutline /></n-icon>
                <strong>{{ endpoint.name || endpoint.id }}</strong>
              </div>
              <p>{{ endpoint.created_at ? `Added on ${endpoint.created_at}` : endpoint.connector_type || 'Endpoint' }}</p>
              <n-button secondary round size="small" @click.stop="openEndpointEditor(endpoint)">
                <template #icon><n-icon><CreateOutline /></n-icon></template> {{ $t('auto.5301648dcf6b') }} </n-button>
              <n-checkbox :checked="selectedEndpoints.includes(endpointId(endpoint))" @click.stop @update:checked="toggleEndpoint(endpoint)" />
            </article>
          </div>
        </n-scrollbar>
        <n-empty v-else class="endpoint-empty-state" :description="$t('auto.f9048ed7196e')" />
      </section>

      <section v-else-if="step === 2" class="wizard-body cookbook-test-body">
        <h2>{{ $t('auto.ee50d7a884d7') }}</h2>
        <div class="category-row">
          <button
            v-for="category in categories"
            :key="category"
            type="button"
            :class="{ active: activeCategory === category }"
            @click="activeCategory = category"
          >
            {{ category }}
          </button>
        </div>
        <p class="category-copy">
          {{ categoryDescription }}
        </p>

        <n-scrollbar class="wizard-card-scrollbar cookbook-card-scrollbar">
          <div class="cookbook-test-grid">
            <article
              v-for="cookbook in filteredCookbooks"
              :key="cookbookId(cookbook)"
              class="select-card cookbook-test-card"
              :class="{ selected: selectedCookbooks.includes(cookbookId(cookbook)) }"
              @click="toggleCookbook(cookbook)"
            >
              <div class="select-card-title">
                <n-icon><BookOutline /></n-icon>
                <strong>{{ cookbook.name || cookbook.id }}</strong>
              </div>
              <n-checkbox :checked="selectedCookbooks.includes(cookbookId(cookbook))" @click.stop @update:checked="toggleCookbook(cookbook)" />
              <div class="chip-cloud compact">
                <n-tag v-for="tag in cookbookTags(cookbook).slice(0, 3)" :key="tag" round size="small">{{ tag }}</n-tag>
              </div>
              <p>{{ cookbook.description || $t('auto.f354c94fcf63') }}</p>
              <div v-if="requiresEvaluator(cookbook)" class="additional-requirements"> {{ $t('auto.6a361e2d94b6') }} </div>
              <small>{{ promptCount(cookbook) }} {{ $t('auto.3b5ad64a06ec') }}<br />{{ datasetCount(cookbook) }} {{ $t('auto.061ac740047f') }}</small>
              <button class="cookbook-about-button" type="button" @click.stop="openCookbookAbout(cookbook)"> {{ $t('auto.6b21fb791ac0') }} </button>
            </article>
          </div>
        </n-scrollbar>
      </section>

      <section v-else-if="step === 3" class="wizard-body run-config-body evaluator-step-body">
        <div class="evaluator-step-heading">
          <span><n-icon><SparklesOutline /></n-icon>{{ $t('benchmark.evaluator.eyebrow') }}</span>
          <h2>{{ $t('benchmark.evaluator.title') }}</h2>
          <p>{{ $t('benchmark.evaluator.subtitle') }}</p>
        </div>

        <div class="evaluator-setup-layout">
          <section class="evaluator-requirements-card">
            <header>
              <span class="evaluator-section-icon"><n-icon><BookOutline /></n-icon></span>
              <div>
                <small>{{ $t('benchmark.evaluator.requiredEyebrow') }}</small>
                <h3>{{ $t('benchmark.evaluator.requiredTitle') }}</h3>
                <p>{{ $t('benchmark.evaluator.requiredHint') }}</p>
              </div>
            </header>

            <div class="evaluator-suite-list">
              <article v-for="cookbook in requirementCookbooks" :key="cookbookId(cookbook)">
                <div>
                  <strong>{{ cookbook.name || cookbook.id }}</strong>
                </div>
                <n-tag size="small" round type="info">
                  {{ requiredEndpointIds(cookbook).length }} {{ $t('benchmark.evaluator.endpointCount') }}
                </n-tag>
              </article>
            </div>

            <div class="evaluator-credential-note">
              <n-icon><ShieldCheckmarkOutline /></n-icon>
              <span>
                <strong>{{ $t('benchmark.evaluator.credentialTitle') }}</strong>
                {{ $t('benchmark.evaluator.credentialHint', { count: requiredEvaluatorIds.length }) }}
              </span>
            </div>
          </section>

          <section class="evaluator-picker-card">
            <header class="evaluator-picker-header">
              <span class="evaluator-section-icon evaluator-section-icon--purple"><n-icon><SparklesOutline /></n-icon></span>
              <div>
                <small>{{ $t('benchmark.evaluator.pickerEyebrow') }}</small>
                <h3>{{ $t('benchmark.evaluator.pickerTitle') }}</h3>
                <p>{{ $t('benchmark.evaluator.pickerHint') }}</p>
              </div>
              <span v-if="evaluatorSelectionReady" class="evaluator-ready-badge">
                <n-icon><CheckmarkCircleOutline /></n-icon>
                {{ $t('benchmark.evaluator.ready') }}
              </span>
            </header>

            <div v-if="!configuredEvaluatorProviders.length" class="evaluator-empty-state">
              <span><n-icon><AlertCircleOutline /></n-icon></span>
              <div>
                <strong>{{ $t('benchmark.evaluator.noProviderTitle') }}</strong>
                <p>{{ $t('benchmark.evaluator.noProviderHint') }}</p>
              </div>
              <n-button type="primary" round @click="router.push('/settings/ai')">
                <template #icon><n-icon><SettingsOutline /></n-icon></template>
                {{ $t('benchmark.evaluator.openSettings') }}
              </n-button>
            </div>

            <template v-else>
              <div v-if="configuredEvaluatorProviders.length > 1" class="evaluator-choice-step">
                <div class="evaluator-choice-label">
                  <b>01</b>
                  <span>
                    <strong>{{ $t('benchmark.evaluator.providerTitle') }}</strong>
                    <small>{{ $t('benchmark.evaluator.providerHint') }}</small>
                  </span>
                </div>
                <div class="evaluator-provider-select-shell">
                  <span v-if="selectedEvaluatorCatalog" class="evaluator-provider-logo">
                    <img :src="selectedEvaluatorCatalog.logo" :alt="`${selectedEvaluatorCatalog.label} logo`" />
                  </span>
                  <n-select
                    :value="selectedEvaluatorProvider"
                    class="evaluator-provider-select"
                    :options="evaluatorProviderOptions"
                    :placeholder="$t('benchmark.evaluator.providerPlaceholder')"
                    @update:value="selectEvaluatorProvider"
                  />
                </div>
              </div>

              <div v-else-if="selectedEvaluatorCatalog" class="evaluator-single-provider">
                <span class="evaluator-provider-logo">
                  <img :src="selectedEvaluatorCatalog.logo" :alt="`${selectedEvaluatorCatalog.label} logo`" />
                </span>
                <span>
                  <small>{{ $t('benchmark.evaluator.singleProvider') }}</small>
                  <strong>{{ selectedEvaluatorCatalog.label }}</strong>
                </span>
                <n-tag size="small" round type="success">{{ $t('benchmark.evaluator.configured') }}</n-tag>
              </div>

              <div class="evaluator-choice-step evaluator-model-step">
                <div class="evaluator-choice-label">
                  <b>{{ configuredEvaluatorProviders.length > 1 ? '02' : '01' }}</b>
                  <span>
                    <strong>{{ $t('benchmark.evaluator.modelTitle') }}</strong>
                    <small>{{ $t('benchmark.evaluator.modelHint') }}</small>
                  </span>
                </div>
                <n-select
                  v-model:value="selectedEvaluatorModel"
                  class="evaluator-model-select"
                  :options="evaluatorModelOptions"
                  filterable
                  tag
                  :placeholder="$t('benchmark.evaluator.modelPlaceholder')"
                />
              </div>

              <div v-if="evaluatorSelectionReady && selectedEvaluatorCatalog" class="evaluator-selection-preview">
                <span class="evaluator-provider-logo">
                  <img :src="selectedEvaluatorCatalog.logo" :alt="`${selectedEvaluatorCatalog.label} logo`" />
                </span>
                <span>
                  <small>{{ $t('benchmark.evaluator.selectionLabel', { count: requiredEvaluatorIds.length }) }}</small>
                  <strong>{{ selectedEvaluatorCatalog.label }} · {{ selectedEvaluatorModel }}</strong>
                </span>
                <n-icon><CheckmarkCircleOutline /></n-icon>
              </div>
            </template>
          </section>
        </div>
      </section>

      <section v-else-if="step === 4" class="wizard-body run-config-body">
        <div class="run-config-form">
          <n-form label-placement="top">
            <n-form-item :label="$t('auto.709a23220f2c')">
              <n-input v-model:value="runForm.run_name" placeholder="my-facts-about-sg-run" />
            </n-form-item>
            <n-form-item :label="$t('auto.388de6fa3aa3')">
              <n-input v-model:value="runForm.description" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" />
            </n-form-item>
            <div class="run-smaller">
              <strong>{{ $t('auto.93b705df8fcd') }}</strong>
              <p>{{ $t('auto.4543eb46e828') }}</p>
              <div class="cookbook-run-list">
                <article v-for="cookbook in selectedCookbookRecords" :key="cookbookId(cookbook)" class="cookbook-run-card">
                  <div>
                    <strong>{{ cookbook.name || cookbook.id }}</strong>
                    <span>{{ promptCount(cookbook) }} {{ $t('auto.33f78ec13ef3') }}</span>
                  </div>
                  <n-slider
                    :value="cookbookPercentage(cookbook)"
                    :min="1"
                    :max="100"
                    :step="1"
                    :disabled="runAll"
                    @update:value="updateCookbookPercentage(cookbook, Number($event))"
                  />
                  <div class="cookbook-run-controls">
                    <b>{{ cookbookPercentage(cookbook) }}%</b>
                    <n-input-number
                      :value="cookbookEstimatedPrompts(cookbook)"
                      :min="1"
                      :max="Math.max(1, promptCount(cookbook))"
                      :disabled="runAll"
                      size="small"
                      @update:value="updateCookbookPromptCount(cookbook, Number($event || 1))"
                    />
                    <span>{{ $t('auto.3b5ad64a06ec') }}</span>
                  </div>
                </article>
              </div>
              <span>{{ $t('auto.1550a6a23950') }} {{ estimatedPrompts }}</span>
            </div>
            <div class="run-all-row">
              <strong>{{ $t('auto.f9665ab9024b') }}{{ totalPrompts }} {{ $t('auto.ec6c65695a7e') }}</strong>
              <n-switch v-model:value="runAll" @update:value="toggleRunAll" />
            </div>
            <div class="run-smaller thread-tuning">
              <strong>{{ $t('auto.3d178ecb88e1') }}</strong>
              <p>{{ $t('auto.96164026cc8a') }}</p>
              <n-slider v-model:value="runForm.thread_count" :min="1" :max="20" :step="1" />
              <b>{{ runForm.thread_count }} {{ $t('auto.c91e11a1f2a2') }}</b>
            </div>
          </n-form>
        </div>
      </section>

      <section v-else class="wizard-body completed-body">
        <h2>{{ $t('auto.07ebd0dc9b57') }}</h2>
        <n-button secondary round @click="router.push('/assets')">{{ $t('auto.4fde0bd56a0d') }}</n-button>
        <div class="completion-card">
          <strong>{{ runForm.run_name }}</strong>
          <div class="completion-progress">
            <span>100%</span>
            <n-progress type="line" :percentage="100" :show-indicator="false" color="#3d6dff" />
            <n-button round @click="router.push('/assets')">{{ $t('auto.52bc93f4eb9a') }}</n-button>
          </div>
        </div>
        <div class="completion-actions">
          <GlassPanel dense class="completion-tile">
            <n-icon size="34"><ShieldCheckmarkOutline /></n-icon>
            <h3>{{ $t('auto.4827ea22716a') }}</h3>
            <p>{{ $t('auto.b73c19da98a1') }}</p>
          </GlassPanel>
          <GlassPanel dense class="completion-tile" @click="router.push('/cookbooks')">
            <n-icon size="34"><BookOutline /></n-icon>
            <h3>{{ $t('auto.6e157c5da441') }}</h3>
            <p>{{ $t('auto.b14f77cad843') }}</p>
          </GlassPanel>
          <button class="back-home" type="button" @click="router.push('/')">{{ $t('auto.0a6e143df6d8') }}</button>
        </div>
      </section>

      <footer v-if="step < 5" class="wizard-footer">
        <button v-if="step > 1" class="wizard-link" type="button" @click="step -= 1">{{ $t('auto.29b589877c65') }}</button>
        <span v-else />
        <button v-if="step < 4" class="wizard-link" type="button" @click="nextStep">{{ $t('auto.7b6106b2fb1d') }}</button>
        <button v-else class="wizard-link" type="button" :disabled="running" @click="runBenchmark">
          {{ running ? 'RUNNING...' : $t('auto.b8777457fe3a') }}
        </button>
      </footer>
    </GlassPanel>

    <n-modal
      v-model:show="cookbookAboutOpen"
      preset="card"
      class="cookbook-about-modal"
      :bordered="false"
    >
      <template #header>
        <div class="cookbook-about-header">
          <span>{{ selectedCookbookAbout ? cookbookBucket(selectedCookbookAbout) : 'Cookbook' }}</span>
          <h2>{{ selectedCookbookAbout?.name || selectedCookbookAbout?.id }}</h2>
        </div>
      </template>

      <div v-if="selectedCookbookAbout" class="cookbook-about-body">
        <section class="cookbook-about-summary">
          <div>
            <small>{{ $t('auto.eea5311d723f') }}</small>
            <strong>{{ promptCount(selectedCookbookAbout).toLocaleString() }}</strong>
          </div>
          <div>
            <small>{{ $t('auto.93a7f22476e9') }}</small>
            <strong>{{ datasetCount(selectedCookbookAbout).toLocaleString() }}</strong>
          </div>
          <div>
            <small>{{ $t('auto.9fb1092f32d4') }}</small>
            <strong>{{ cookbookRecipeRecords(selectedCookbookAbout).length.toLocaleString() }}</strong>
          </div>
        </section>

        <section class="cookbook-about-section">
          <h3>{{ $t('auto.0efc2e6be4c2') }}</h3>
          <p>{{ selectedCookbookAbout.description || $t('auto.89f53d9d9037') }}</p>
        </section>

        <section v-if="cookbookTags(selectedCookbookAbout).length" class="cookbook-about-section">
          <h3>{{ $t('auto.848eed0fbd54') }}</h3>
          <div class="cookbook-about-tags">
            <n-tag v-for="tag in cookbookTags(selectedCookbookAbout)" :key="tag" round>
              {{ tag }}
            </n-tag>
          </div>
        </section>

        <section class="cookbook-about-section">
          <h3>{{ $t('auto.a6fce427b3f2') }}</h3>
          <div v-if="cookbookRecipeRecords(selectedCookbookAbout).length" class="cookbook-about-recipes">
            <article v-for="recipe in cookbookRecipeRecords(selectedCookbookAbout).slice(0, 8)" :key="String(recipe.id || recipe.name)">
              <strong>{{ recipe.name || recipe.id }}</strong>
              <span>{{ recipe.datasets?.length || 0 }} {{ $t('auto.061ac740047f') }}</span>
            </article>
          </div>
          <p v-else>{{ $t('auto.ab29891000f5') }}</p>
        </section>

        <section v-if="requiresEvaluator(selectedCookbookAbout)" class="cookbook-about-section requirement-highlight">
          <h3>{{ $t('auto.6a361e2d94b6') }}</h3>
          <p>{{ $t('auto.7759ae9b8eab') }}</p>
          <div class="cookbook-about-tags">
            <n-tag v-for="endpoint in requiredEndpointLabels(selectedCookbookAbout)" :key="endpoint" round type="warning">
              {{ endpoint }}
            </n-tag>
          </div>
        </section>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { translateSource } from '../i18n'

import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useMessage, useNotification } from 'naive-ui'
import {
  AddOutline,
  AlertCircleOutline,
  BookOutline,
  CheckmarkCircleOutline,
  CloseOutline,
  CreateOutline,
  CubeOutline,
  SearchOutline,
  SettingsOutline,
  ShieldCheckmarkOutline,
  SparklesOutline,
} from '@vicons/ionicons5'
import GlassPanel from '../components/GlassPanel.vue'
import { moonshotApi } from '../api/moonshot'
import { CONFIGURABLE_CONNECTOR } from '../services/connectorService'
import { useMoonshotStore } from '../stores/moonshot'
import { useSettingsStore } from '../stores/settings'
import type { CookbookRecord, EndpointRecord, RequiredConfig } from '../types/moonshot'

const store = useMoonshotStore()
const settingsStore = useSettingsStore()
const router = useRouter()
const { t } = useI18n()
const message = useMessage()
const notification = useNotification()
const step = ref(1)
const running = ref(false)
const runAll = ref(false)
const endpointSearch = ref('')
const selectedEndpoints = ref<string[]>([])
const selectedCookbooks = ref<string[]>([])
const cookbookAboutOpen = ref(false)
const selectedCookbookAbout = ref<CookbookRecord | null>(null)
const selectedEvaluatorProvider = ref('')
const selectedEvaluatorModel = ref('')
const activeCategory = ref('IMDA Starter Kit')
const cookbookPromptPercentages = reactive<Record<string, number>>({})

function notify(type: 'info' | 'success' | 'warning' | 'error', options: { title: string; content: string }) {
  notification[type]({ ...options, duration: 2000 })
}

const steps = computed(() => [
  { key: 'endpoint', label: t('auto.af204023eb51'), index: 1 },
  { key: 'tests', label: t('auto.52f491fdd1ad'), index: 2 },
  { key: 'requirements', label: t('auto.d1d328fb841f'), index: 3 },
  { key: 'run', label: t('common.run'), index: 4 },
])

const categories = ['IMDA Starter Kit', 'Capability', 'Trust & Safety', 'Others']

const runForm = reactive({
  run_name: `Oxo-AI-test-${new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')}`,
  description: translateSource('auto.3c7b9417e41a'),
  prompt_selection_percentage: 5,
  thread_count: 4,
  random_seed: 0,
  system_prompt: '',
})

const filteredCookbooks = computed(() => {
  return store.cookbooks.filter((cookbook) => cookbookBucket(cookbook) === activeCategory.value)
})

const filteredEndpoints = computed(() => {
  const keyword = endpointSearch.value.trim().toLowerCase()
  const endpoints = keyword
    ? store.endpoints.filter((endpoint) =>
        [
          endpoint.name,
          endpoint.id,
          endpoint.connector_type,
          endpoint.model,
          endpoint.uri,
        ]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(keyword)),
      )
    : store.endpoints

  return [...endpoints].sort((left, right) => {
    const sourceOrder = Number(isUserCreatedEndpoint(right)) - Number(isUserCreatedEndpoint(left))
    if (sourceOrder) return sourceOrder
    return endpointLabel(left).localeCompare(endpointLabel(right), undefined, {
      numeric: true,
      sensitivity: 'base',
    })
  })
})

const categoryDescription = computed(() => {
  if (activeCategory.value === 'IMDA Starter Kit') {
    return "Includes tests from IMDA's Starter Kit to assess whether a model or application responds to key risks like hallucination, undesirable content, data disclosure and adversarial prompts in a safe and trustworthy manner."
  }
  if (activeCategory.value === 'Trust & Safety') {
    return "Trust & Safety assesses the model's behavior against safety, policy, and risk-focused tests."
  }
  if (activeCategory.value === 'Others') {
    return 'Other cookbooks contain specialized evaluation suites and custom benchmark collections.'
  }
  return "Capability assesses the AI model's ability to perform within the context of the unique requirements and challenges of a particular domain or task."
})

const selectedCookbookRecords = computed(() => {
  const selected = new Set(selectedCookbooks.value)
  return store.cookbooks.filter((cookbook) => selected.has(cookbookId(cookbook)))
})

const selectedRecipes = computed(() => {
  const ids = new Set<string>()
  selectedCookbookRecords.value.forEach((cookbook) => {
    cookbook.recipes?.forEach((recipe) => ids.add(recipe))
  })
  return [...ids]
})

const totalPrompts = computed(() => {
  const total = selectedCookbookRecords.value.reduce((sum, cookbook) => sum + promptCount(cookbook), 0)
  return total || selectedRecipes.value.length
})

const estimatedPrompts = computed(() => {
  const total = selectedCookbookRecords.value.reduce((sum, cookbook) => sum + cookbookEstimatedPrompts(cookbook), 0)
  return Math.max(1, total)
})

const requirementCookbooks = computed(() => {
  return selectedCookbookRecords.value.filter((cookbook) => requiresEvaluator(cookbook))
})

const visibleSteps = computed(() => {
  if (requirementCookbooks.value.length) return steps.value
  return steps.value.filter((item) => item.key !== 'requirements')
})

const requiredEvaluatorIds = computed(() => {
  const ids = new Set<string>()
  requirementCookbooks.value.forEach((cookbook) => {
    requiredEndpointIds(cookbook).forEach((id) => ids.add(id))
  })
  return [...ids]
})

const configuredEvaluatorProviders = computed(() => {
  const settings = settingsStore.ai
  if (!settings) return []
  return Object.entries(settings.providers)
    .filter(([, provider]) => provider.apiKeyConfigured)
    .map(([id, provider]) => ({
      id,
      settings: provider,
      catalog: settings.catalog[id],
    }))
    .filter((provider) => Boolean(provider.catalog))
})

const evaluatorProviderOptions = computed(() =>
  configuredEvaluatorProviders.value.map((provider) => ({
    label: `${provider.catalog.label} · ${provider.catalog.company}`,
    value: provider.id,
  })),
)

const selectedEvaluatorProviderRecord = computed(() =>
  configuredEvaluatorProviders.value.find((provider) => provider.id === selectedEvaluatorProvider.value),
)

const selectedEvaluatorCatalog = computed(() => selectedEvaluatorProviderRecord.value?.catalog)

const evaluatorModelOptions = computed(() => {
  const provider = selectedEvaluatorProviderRecord.value
  if (!provider) return []
  return Array.from(new Set([provider.settings.model, ...(provider.catalog.models || [])].filter(Boolean))).map((model) => ({
    label: provider.catalog.latestModels?.includes(model) ? `${model}  ·  Latest` : model,
    value: model,
  }))
})

const evaluatorSelectionReady = computed(() => Boolean(
  selectedEvaluatorProviderRecord.value
  && selectedEvaluatorModel.value.trim(),
))

watch(configuredEvaluatorProviders, (providers) => {
  if (!providers.length) {
    selectedEvaluatorProvider.value = ''
    selectedEvaluatorModel.value = ''
    return
  }
  const current = providers.find((provider) => provider.id === selectedEvaluatorProvider.value)
  if (current) return
  const activeProvider = providers.find((provider) => provider.id === settingsStore.ai?.activeProvider)
  selectEvaluatorProvider((activeProvider || providers[0]).id)
}, { immediate: true })

onMounted(async () => {
  await store.loadOverview()
  if (!settingsStore.ai) {
    try {
      await settingsStore.loadSettings()
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Unable to load AI settings')
    }
  }
})

function endpointId(endpoint?: EndpointRecord) {
  return String(endpoint?.id || endpoint?.name || '')
}

function endpointLabel(endpoint: EndpointRecord) {
  return String(endpoint.name || endpoint.id || '')
}

function isUserCreatedEndpoint(endpoint: EndpointRecord) {
  return endpoint.connector_type === CONFIGURABLE_CONNECTOR
}

function openEndpointEditor(endpoint: EndpointRecord) {
  const id = endpointId(endpoint)
  if (!id) return
  void router.push({
    path: '/agents',
    query: {
      view: 'endpoints',
      endpointId: id,
      edit: '1',
    },
  })
}

function findEndpointById(id: string) {
  return store.endpoints.find((endpoint) => endpointMatchesId(endpoint, id))
}

function endpointMatchesId(endpoint: EndpointRecord, id: string) {
  return endpointId(endpoint) === id || endpoint.id === id || endpoint.name === id
}

function cookbookId(cookbook?: CookbookRecord) {
  return String(cookbook?.id || cookbook?.name || '')
}

function toggleEndpoint(endpoint: EndpointRecord) {
  const id = endpointId(endpoint)
  if (!id) return
  selectedEndpoints.value = selectedEndpoints.value.includes(id)
    ? selectedEndpoints.value.filter((item) => item !== id)
    : [...selectedEndpoints.value, id]
}

function toggleCookbook(cookbook: CookbookRecord) {
  const id = cookbookId(cookbook)
  if (!id) return
  if (selectedCookbooks.value.includes(id)) {
    selectedCookbooks.value = selectedCookbooks.value.filter((item) => item !== id)
    delete cookbookPromptPercentages[id]
  } else {
    selectedCookbooks.value = [...selectedCookbooks.value, id]
    cookbookPromptPercentages[id] = runAll.value ? 100 : runForm.prompt_selection_percentage
  }
}

function openCookbookAbout(cookbook: CookbookRecord) {
  selectedCookbookAbout.value = cookbook
  cookbookAboutOpen.value = true
}

function cookbookPercentage(cookbook: CookbookRecord) {
  return cookbookPromptPercentages[cookbookId(cookbook)] ?? runForm.prompt_selection_percentage
}

function updateCookbookPercentage(cookbook: CookbookRecord, value: number) {
  const id = cookbookId(cookbook)
  if (!id) return
  cookbookPromptPercentages[id] = Math.max(1, Math.min(100, Math.round(value)))
}

function cookbookEstimatedPrompts(cookbook: CookbookRecord) {
  const total = Math.max(1, promptCount(cookbook))
  return Math.max(1, Math.round((total * cookbookPercentage(cookbook)) / 100))
}

function updateCookbookPromptCount(cookbook: CookbookRecord, value: number) {
  const total = Math.max(1, promptCount(cookbook))
  const count = Math.max(1, Math.min(total, Math.round(value)))
  updateCookbookPercentage(cookbook, Math.max(1, Math.round((count / total) * 100)))
}

function selectedCookbookPercentagesPayload() {
  return selectedCookbookRecords.value.reduce<Record<string, number>>((payload, cookbook) => {
    payload[cookbookId(cookbook)] = cookbookPercentage(cookbook)
    return payload
  }, {})
}

function nextStep() {
  if (step.value === 1 && !selectedEndpoints.value.length) {
    message.warning(translateSource('auto.8f5c9888549d'))
    return
  }
  if (step.value === 2 && !selectedCookbooks.value.length) {
    message.warning(translateSource('auto.db4e736cf8c2'))
    return
  }
  if (step.value === 2 && !requirementCookbooks.value.length) {
    step.value = 4
    return
  }
  if (step.value === 3 && !validateRequiredEvaluatorTokens()) {
    return
  }
  step.value += 1
}

function validateRequiredEvaluatorTokens() {
  if (!requirementCookbooks.value.length || evaluatorSelectionReady.value) return true
  if (!configuredEvaluatorProviders.value.length) {
    message.warning(translateSource('benchmark.evaluator.configureProviderWarning'))
  } else {
    message.warning(translateSource('benchmark.evaluator.selectModelWarning'))
  }
  return false
}

function toggleRunAll(value: boolean) {
  runForm.prompt_selection_percentage = value ? 100 : 5
  selectedCookbookRecords.value.forEach((cookbook) => {
    cookbookPromptPercentages[cookbookId(cookbook)] = value ? 100 : 5
  })
}

async function runBenchmark() {
  if (requirementCookbooks.value.length && !validateRequiredEvaluatorTokens()) {
    step.value = 3
    return
  }
  if (!runForm.run_name.trim()) {
    message.warning(translateSource('auto.4f32d7ac38a6'))
    return
  }
  if (!selectedRecipes.value.length) {
    message.warning(translateSource('auto.eaf727055251'))
    return
  }
  running.value = true
  try {
    notify('info', { title: translateSource('auto.83b11ff4e174'), content: runForm.run_name.trim() })
    const requestPayload = {
      run_name: runForm.run_name.trim(),
      endpoints: selectedEndpoints.value,
      recipes: selectedRecipes.value,
      cookbooks: selectedCookbooks.value,
      evaluator_provider: requirementCookbooks.value.length ? selectedEvaluatorProvider.value : undefined,
      evaluator_model: requirementCookbooks.value.length ? selectedEvaluatorModel.value.trim() : undefined,
      evaluator_endpoints: requiredEvaluatorIds.value,
      cookbook_prompt_selection_percentages: selectedCookbookPercentagesPayload(),
      description: runForm.description,
      prompt_selection_percentage: runForm.prompt_selection_percentage,
      estimated_prompts: estimatedPrompts.value,
      thread_count: runForm.thread_count,
      random_seed: runForm.random_seed,
      system_prompt: runForm.system_prompt,
    }
    const response = await moonshotApi.runRecipeBenchmark(requestPayload)
    const createdAt = new Date().toISOString()
    store.upsertJob({
      id: response.runner_id,
      runner_id: response.runner_id,
      name: requestPayload.run_name,
      description: requestPayload.description,
      status: response.status,
      progress: 0,
      created_at: createdAt,
      updated_at: createdAt,
      started_at: null,
      ended_at: null,
      request: requestPayload,
      outputs: {},
      summary: {
        endpoints: [...requestPayload.endpoints],
        recipes: [...requestPayload.recipes],
        cookbooks: [...requestPayload.cookbooks],
        estimated_prompts: requestPayload.estimated_prompts,
        completed_prompts: 0,
        error_count: 0,
        thread_count: requestPayload.thread_count,
        judge_progress: {
          phase: 'pending',
          completed: 0,
          total: requestPayload.estimated_prompts,
          percentage: 0,
        },
      },
      errors: [],
      events: [{ time: createdAt, level: 'info', message: 'Job created' }],
    })
    notify('success', { title: translateSource('auto.0c4c43c79bd1'), content: `Run ${response.runner_id} is now running.` })
    await router.push(`/jobs/${encodeURIComponent(response.runner_id)}`)
    void store.loadOverview()
  } catch (error) {
    notify('error', { title: translateSource('auto.1686a5d2f668'), content: error instanceof Error ? error.message : 'Benchmark failed' })
    message.error(error instanceof Error ? error.message : 'Benchmark failed')
  } finally {
    running.value = false
  }
}

function resetWizard() {
  step.value = 1
  selectedEndpoints.value = []
  selectedCookbooks.value = []
  Object.keys(cookbookPromptPercentages).forEach((key) => delete cookbookPromptPercentages[key])
}

function cookbookTags(cookbook: CookbookRecord) {
  return cookbook.tags ?? []
}

function promptCount(cookbook: CookbookRecord) {
  return cookbookRecipeRecords(cookbook).reduce((total, recipe) => {
    const datasetPrompts = recipe.stats?.num_of_datasets_prompts
    if (datasetPrompts && typeof datasetPrompts === 'object' && !Array.isArray(datasetPrompts)) {
      return total + Object.values(datasetPrompts).reduce((sum, value) => {
        return sum + (typeof value === 'number' ? value : 0)
      }, 0)
    }
    return total
  }, 0)
}

function datasetCount(cookbook: CookbookRecord) {
  const datasetIds = new Set<string>()
  cookbookRecipeRecords(cookbook).forEach((recipe) => {
    recipe.datasets?.forEach((dataset) => datasetIds.add(dataset))
  })
  return datasetIds.size
}

function cookbookRecipeRecords(cookbook: CookbookRecord) {
  const recipeIds = new Set(cookbook.recipes ?? [])
  return store.recipes.filter((recipe) => recipeIds.has(String(recipe.id || recipe.name || '')))
}

function cookbookBucket(cookbook: CookbookRecord) {
  const categories = cookbook.categories ?? []
  if (categories.includes('IMDA Starter Kit')) return 'IMDA Starter Kit'
  if (categories.includes('Capability')) return 'Capability'
  if (categories.includes('Trust & Safety')) return 'Trust & Safety'
  return 'Others'
}

function requiredEndpointIds(cookbook: CookbookRecord) {
  const ids = new Set(endpointIdsFromRequiredConfig(cookbook.required_config))
  cookbookRecipeRecords(cookbook).forEach((recipe) => {
    endpointIdsFromRequiredConfig(recipe.required_config).forEach((id) => ids.add(id))
    recipe.metrics?.forEach((metricId) => {
      const metric = store.metrics.find((item) => String(item.id || item.name || '') === metricId)
      endpointIdsFromRequiredConfig(metric).forEach((id) => ids.add(id))
    })
  })
  return [...ids]
}

function endpointIdsFromRequiredConfig(config?: RequiredConfig | Record<string, unknown> | null) {
  const ids = new Set<string>()
  if (!config) return []

  const endpoints = config.endpoints
  if (Array.isArray(endpoints)) {
    endpoints.forEach((endpoint) => {
      if (typeof endpoint === 'string' && endpoint) ids.add(endpoint)
    })
  }

  const configurations = config.configurations
  if (configurations && typeof configurations === 'object' && !Array.isArray(configurations)) {
    Object.values(configurations).forEach((value) => {
      if (Array.isArray(value)) {
        value.forEach((endpoint) => {
          if (typeof endpoint === 'string' && endpoint) ids.add(endpoint)
        })
      }
    })
  }

  return [...ids]
}

function requiredEndpointLabels(cookbook: CookbookRecord) {
  return requiredEndpointIds(cookbook).map((id) => {
    const endpoint = findEndpointById(id)
    return endpoint?.name || id
  })
}

function requiresEvaluator(cookbook: CookbookRecord) {
  return requiredEndpointIds(cookbook).length > 0
}

function selectEvaluatorProvider(providerId: string | number | null) {
  const normalizedProviderId = String(providerId || '')
  const provider = configuredEvaluatorProviders.value.find((item) => item.id === normalizedProviderId)
  selectedEvaluatorProvider.value = provider?.id || ''
  selectedEvaluatorModel.value = provider?.settings.model || ''
}
</script>
