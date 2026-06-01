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
          <template v-if="selectedEndpoints.length">{{ selectedEndpoints.length }} Endpoint(s) to be tested</template>
          <template v-else>Select the Endpoint(s) to be tested</template>
        </h2>
        <div class="endpoint-filter-row">
          <n-input v-model:value="endpointSearch" clearable class="endpoint-search-input" placeholder="Search endpoints">
            <template #prefix><n-icon><SearchOutline /></n-icon></template>
          </n-input>
          <n-button secondary round @click="router.push('/endpoints')">
            <template #icon><n-icon><AddOutline /></n-icon></template>
            Create New Endpoint
          </n-button>
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
              <n-button secondary round size="small" @click.stop="router.push('/endpoints')">
                <template #icon><n-icon><CreateOutline /></n-icon></template>
                Edit
              </n-button>
              <n-checkbox :checked="selectedEndpoints.includes(endpointId(endpoint))" @click.stop @update:checked="toggleEndpoint(endpoint)" />
            </article>
          </div>
        </n-scrollbar>
        <n-empty v-else class="endpoint-empty-state" description="No endpoints found" />
      </section>

      <section v-else-if="step === 2" class="wizard-body cookbook-test-body">
        <h2>Select the cookbooks you want to run</h2>
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
              <p>{{ cookbook.description || 'No description' }}</p>
              <div v-if="requiresEvaluator(cookbook)" class="additional-requirements">
                Additional Requirements
              </div>
              <small>{{ promptCount(cookbook) }} prompts<br />{{ datasetCount(cookbook) }} datasets</small>
              <button class="cookbook-about-button" type="button" @click.stop="openCookbookAbout(cookbook)">
                About
              </button>
            </article>
          </div>
        </n-scrollbar>
      </section>

      <section v-else-if="step === 3" class="wizard-body run-config-body">
        <h2>Provide these additional requirements</h2>
        <div class="requirements-panel">
          <template v-for="cookbook in requirementCookbooks" :key="cookbookId(cookbook)">
            <section class="requirement-card">
              <div class="evaluator-endpoints-column">
                <h3>
                  <n-icon><BookOutline /></n-icon>
                  {{ cookbook.name || cookbook.id }}
                </h3>
                <p>
                  This cookbook requires connection to evaluator model(s) to help score the tests.
                  Provide access to at least one alternative evaluator model.
                </p>
                <ul>
                  <li v-for="endpoint in requiredEndpointLabels(cookbook)" :key="endpoint">{{ endpoint }}</li>
                </ul>
              </div>
              <div>
                <h4>Connect evaluator models</h4>
                <p>Ensure that Moonshot has access to these endpoints.</p>
                <div v-for="endpoint in requiredEndpoints(cookbook)" :key="endpoint.id" class="evaluator-config-group">
                  <div class="evaluator-card">
                    <n-icon><CubeOutline /></n-icon>
                    <strong>{{ endpoint.label }}</strong>
                    <n-tag size="small" round :type="endpoint.configured ? 'success' : 'warning'">
                      {{ endpoint.configured ? 'Configured' : endpoint.exists ? 'Token required' : 'Missing' }}
                    </n-tag>
                    <n-button secondary round size="small" @click="openEvaluatorConfig(endpoint.id, evaluatorConfigKey(cookbook, endpoint.id))">
                      <template #icon><n-icon><CreateOutline /></n-icon></template>
                      Configure
                    </n-button>
                  </div>
                </div>
              </div>
            </section>

            <div v-if="isCookbookConfigOpen(cookbook)" class="evaluator-config-panel inline">
              <div class="builder-header">
                <h2>Configure {{ configuringEvaluatorId }}</h2>
                <n-button circle quaternary @click="closeEvaluatorConfig">
                  <template #icon><n-icon><CloseOutline /></n-icon></template>
                </n-button>
              </div>
              <n-form label-placement="top">
                <n-form-item label="Name*">
                  <n-input v-model:value="evaluatorForm.name" :disabled="Boolean(configuringEvaluatorId)" />
                </n-form-item>
                <n-form-item label="Connection Type*">
                  <n-select
                    v-model:value="evaluatorForm.connector_type"
                    filterable
                    :options="connectorOptions"
                    placeholder="openai-connector"
                  />
                </n-form-item>
                <n-form-item label="URI">
                  <n-input v-model:value="evaluatorForm.uri" placeholder="URI of the evaluator model endpoint" />
                </n-form-item>
                <n-form-item label="Token*">
                  <n-input v-model:value="evaluatorForm.token" type="password" show-password-on="click" placeholder="YOUR_TOKEN" />
                </n-form-item>
                <n-form-item label="Model*">
                  <n-input v-model:value="evaluatorForm.model" placeholder="gpt-4o" />
                </n-form-item>
                <n-form-item label="Max Calls Per Second*">
                  <n-input-number v-model:value="evaluatorForm.max_calls_per_second" :min="1" />
                </n-form-item>
                <n-form-item label="Max Concurrency*">
                  <n-input-number v-model:value="evaluatorForm.max_concurrency" :min="1" />
                </n-form-item>
                <n-form-item label="Other Parameters*">
                  <n-input
                    v-model:value="evaluatorParamsText"
                    type="textarea"
                    :autosize="{ minRows: 5, maxRows: 8 }"
                  />
                </n-form-item>
              </n-form>
              <div class="endpoint-form-actions">
                <n-button round @click="closeEvaluatorConfig">Cancel</n-button>
                <n-button type="primary" round :loading="savingEvaluator" @click="saveEvaluatorEndpoint">Save</n-button>
              </div>
            </div>
          </template>
        </div>
      </section>

      <section v-else-if="step === 4" class="wizard-body run-config-body">
        <div class="run-config-form">
          <n-form label-placement="top">
            <n-form-item label="Name">
              <n-input v-model:value="runForm.run_name" placeholder="my-facts-about-sg-run" />
            </n-form-item>
            <n-form-item label="Description (optional)">
              <n-input v-model:value="runForm.description" type="textarea" :autosize="{ minRows: 4, maxRows: 6 }" />
            </n-form-item>
            <div class="run-smaller">
              <strong>Run a smaller set</strong>
              <p>Set the prompt count independently for each selected cookbook.</p>
              <div class="cookbook-run-list">
                <article v-for="cookbook in selectedCookbookRecords" :key="cookbookId(cookbook)" class="cookbook-run-card">
                  <div>
                    <strong>{{ cookbook.name || cookbook.id }}</strong>
                    <span>{{ promptCount(cookbook) }} available prompts</span>
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
                    <span>prompts</span>
                  </div>
                </article>
              </div>
              <span>Total prompts that will be run: {{ estimatedPrompts }}</span>
            </div>
            <div class="run-all-row">
              <strong>Run All ({{ totalPrompts }} prompts)</strong>
              <n-switch v-model:value="runAll" @update:value="toggleRunAll" />
            </div>
            <div class="run-smaller thread-tuning">
              <strong>Thread count</strong>
              <p>Controls concurrent model requests for this run. Higher values are faster but may hit provider rate limits.</p>
              <n-slider v-model:value="runForm.thread_count" :min="1" :max="20" :step="1" />
              <b>{{ runForm.thread_count }} threads</b>
            </div>
          </n-form>
        </div>
      </section>

      <section v-else class="wizard-body completed-body">
        <h2>Tests Completed</h2>
        <n-button secondary round @click="router.push('/assets')">See Details</n-button>
        <div class="completion-card">
          <strong>{{ runForm.run_name }}</strong>
          <div class="completion-progress">
            <span>100%</span>
            <n-progress type="line" :percentage="100" :show-indicator="false" color="#3d6dff" />
            <n-button round @click="router.push('/assets')">View Report</n-button>
          </div>
        </div>
        <div class="completion-actions">
          <GlassPanel dense class="completion-tile">
            <n-icon size="34"><ShieldCheckmarkOutline /></n-icon>
            <h3>Discover</h3>
            <p>new vulnerabilities</p>
          </GlassPanel>
          <GlassPanel dense class="completion-tile" @click="router.push('/cookbooks')">
            <n-icon size="34"><BookOutline /></n-icon>
            <h3>Create</h3>
            <p>cookbooks</p>
          </GlassPanel>
          <button class="back-home" type="button" @click="router.push('/')">Back to home -></button>
        </div>
      </section>

      <footer v-if="step < 5" class="wizard-footer">
        <button v-if="step > 1" class="wizard-link" type="button" @click="step -= 1">&lt;- BACK</button>
        <span v-else />
        <button v-if="step < 4" class="wizard-link" type="button" @click="nextStep">NEXT -></button>
        <button v-else class="wizard-link" type="button" :disabled="running" @click="runBenchmark">
          {{ running ? 'RUNNING...' : 'RUN ->' }}
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
            <small>Prompts</small>
            <strong>{{ promptCount(selectedCookbookAbout).toLocaleString() }}</strong>
          </div>
          <div>
            <small>Datasets</small>
            <strong>{{ datasetCount(selectedCookbookAbout).toLocaleString() }}</strong>
          </div>
          <div>
            <small>Recipes</small>
            <strong>{{ cookbookRecipeRecords(selectedCookbookAbout).length.toLocaleString() }}</strong>
          </div>
        </section>

        <section class="cookbook-about-section">
          <h3>Overview</h3>
          <p>{{ selectedCookbookAbout.description || 'No description is available for this cookbook.' }}</p>
        </section>

        <section v-if="cookbookTags(selectedCookbookAbout).length" class="cookbook-about-section">
          <h3>Tags</h3>
          <div class="cookbook-about-tags">
            <n-tag v-for="tag in cookbookTags(selectedCookbookAbout)" :key="tag" round>
              {{ tag }}
            </n-tag>
          </div>
        </section>

        <section class="cookbook-about-section">
          <h3>Included Recipes</h3>
          <div v-if="cookbookRecipeRecords(selectedCookbookAbout).length" class="cookbook-about-recipes">
            <article v-for="recipe in cookbookRecipeRecords(selectedCookbookAbout).slice(0, 8)" :key="String(recipe.id || recipe.name)">
              <strong>{{ recipe.name || recipe.id }}</strong>
              <span>{{ recipe.datasets?.length || 0 }} datasets</span>
            </article>
          </div>
          <p v-else>No recipe metadata is available.</p>
        </section>

        <section v-if="requiresEvaluator(selectedCookbookAbout)" class="cookbook-about-section requirement-highlight">
          <h3>Additional Requirements</h3>
          <p>This cookbook uses evaluator model endpoints to score responses after the target model has answered.</p>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, useNotification } from 'naive-ui'
import {
  AddOutline,
  BookOutline,
  CloseOutline,
  CreateOutline,
  CubeOutline,
  SearchOutline,
  ShieldCheckmarkOutline,
} from '@vicons/ionicons5'
import GlassPanel from '../components/GlassPanel.vue'
import { moonshotApi } from '../api/moonshot'
import { useMoonshotStore } from '../stores/moonshot'
import type { CookbookRecord, EndpointCreatePayload, EndpointRecord, RequiredConfig } from '../types/moonshot'

const store = useMoonshotStore()
const router = useRouter()
const message = useMessage()
const notification = useNotification()
const step = ref(1)
const running = ref(false)
const runAll = ref(false)
const savingEvaluator = ref(false)
const endpointSearch = ref('')
const selectedEndpoints = ref<string[]>([])
const selectedCookbooks = ref<string[]>([])
const cookbookAboutOpen = ref(false)
const selectedCookbookAbout = ref<CookbookRecord | null>(null)
const configuringEvaluatorId = ref('')
const activeEvaluatorConfigKey = ref('')
const evaluatorParamsText = ref('{\n  "timeout": 300,\n  "max_attempts": 3,\n  "temperature": 0.5\n}')
const activeCategory = ref('IMDA Starter Kit')
const cookbookPromptPercentages = reactive<Record<string, number>>({})

function notify(type: 'info' | 'success' | 'warning' | 'error', options: { title: string; content: string }) {
  notification[type]({ ...options, duration: 2000 })
}

const evaluatorForm = reactive<EndpointCreatePayload>({
  name: '',
  connector_type: '',
  uri: '',
  token: '',
  max_calls_per_second: 10,
  max_concurrency: 1,
  model: '',
  params: {},
})

const steps = [
  { key: 'endpoint', label: 'Connect Endpoint', index: 1 },
  { key: 'tests', label: 'Select Tests', index: 2 },
  { key: 'requirements', label: 'Configure Requirements', index: 3 },
  { key: 'run', label: 'Run', index: 4 },
]

const categories = ['IMDA Starter Kit', 'Capability', 'Trust & Safety', 'Others']

const runForm = reactive({
  run_name: `Oxo-AI-test-${new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')}`,
  description: 'getting started',
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
  if (!keyword) return store.endpoints
  return store.endpoints.filter((endpoint) =>
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
  if (requirementCookbooks.value.length) return steps
  return steps.filter((item) => item.key !== 'requirements')
})

const requiredEvaluatorIds = computed(() => {
  const ids = new Set<string>()
  requirementCookbooks.value.forEach((cookbook) => {
    requiredEndpointIds(cookbook).forEach((id) => ids.add(id))
  })
  return [...ids]
})

const missingRequiredEndpointIds = computed(() => {
  return requiredEvaluatorIds.value.filter((id) => !isEndpointConfigured(findEndpointById(id)))
})

const connectorOptions = computed(() =>
  store.connectorTypes.map((type) => ({ label: type, value: type })),
)

onMounted(() => {
  void store.loadOverview()
})

function endpointId(endpoint?: EndpointRecord) {
  return String(endpoint?.id || endpoint?.name || '')
}

function findEndpointById(id: string) {
  return store.endpoints.find((endpoint) => endpointMatchesId(endpoint, id))
}

function endpointMatchesId(endpoint: EndpointRecord, id: string) {
  return endpointId(endpoint) === id || endpoint.id === id || endpoint.name === id
}

function endpointHasToken(endpoint?: EndpointRecord) {
  return typeof endpoint?.token === 'string' && endpoint.token.trim().length > 0
}

function isEndpointConfigured(endpoint?: EndpointRecord) {
  return Boolean(endpoint && endpointHasToken(endpoint))
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
    message.warning('Select at least one endpoint')
    return
  }
  if (step.value === 2 && !selectedCookbooks.value.length) {
    message.warning('Select at least one cookbook')
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
  if (!missingRequiredEndpointIds.value.length) return true
  message.warning(`Please input token for required evaluator endpoint(s): ${missingRequiredEndpointIds.value.join(', ')}`)
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
    message.warning('Please enter run name')
    return
  }
  if (!selectedRecipes.value.length) {
    message.warning('Selected cookbook has no recipes')
    return
  }
  running.value = true
  try {
    notify('info', { title: 'Job starting', content: runForm.run_name.trim() })
    await moonshotApi.runRecipeBenchmark({
      run_name: runForm.run_name.trim(),
      endpoints: selectedEndpoints.value,
      recipes: selectedRecipes.value,
      cookbooks: selectedCookbooks.value,
      cookbook_prompt_selection_percentages: selectedCookbookPercentagesPayload(),
      description: runForm.description,
      prompt_selection_percentage: runForm.prompt_selection_percentage,
      estimated_prompts: estimatedPrompts.value,
      thread_count: runForm.thread_count,
      random_seed: runForm.random_seed,
      system_prompt: runForm.system_prompt,
    }).then((response) => {
      notify('success', { title: 'Job created', content: `Run ${response.runner_id} is now running.` })
      router.push(`/jobs/${encodeURIComponent(response.runner_id)}`)
    })
    await store.loadOverview()
  } catch (error) {
    notify('error', { title: 'Job failed to start', content: error instanceof Error ? error.message : 'Benchmark failed' })
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
  configuringEvaluatorId.value = ''
  activeEvaluatorConfigKey.value = ''
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

function requiredEndpoints(cookbook: CookbookRecord) {
  return requiredEndpointIds(cookbook).map((id) => {
    const endpoint = findEndpointById(id)
    return {
      id,
      label: endpoint?.name || id,
      exists: Boolean(endpoint),
      configured: isEndpointConfigured(endpoint),
    }
  })
}

function requiresEvaluator(cookbook: CookbookRecord) {
  return requiredEndpointIds(cookbook).length > 0
}

function evaluatorConfigKey(cookbook: CookbookRecord, endpointIdValue: string) {
  return `${cookbookId(cookbook)}::${endpointIdValue}`
}

function isCookbookConfigOpen(cookbook: CookbookRecord) {
  return activeEvaluatorConfigKey.value.startsWith(`${cookbookId(cookbook)}::`)
}

function resetEvaluatorForm(id: string, endpoint?: EndpointRecord) {
  configuringEvaluatorId.value = id
  evaluatorForm.name = endpoint?.name || id
  evaluatorForm.connector_type = endpoint?.connector_type || store.connectorTypes[0] || 'openai-connector'
  evaluatorForm.uri = endpoint?.uri || ''
  evaluatorForm.token = endpoint?.token || ''
  evaluatorForm.max_calls_per_second = endpoint?.max_calls_per_second ?? 10
  evaluatorForm.max_concurrency = endpoint?.max_concurrency ?? 1
  evaluatorForm.model = endpoint?.model || ''
  evaluatorForm.params = endpoint?.params || {}
  evaluatorParamsText.value = JSON.stringify(evaluatorForm.params || {
    timeout: 300,
    max_attempts: 3,
    temperature: 0.5,
  }, null, 2)
}

function openEvaluatorConfig(id: string, configKey: string) {
  resetEvaluatorForm(id, findEndpointById(id))
  activeEvaluatorConfigKey.value = configKey
}

function closeEvaluatorConfig() {
  configuringEvaluatorId.value = ''
  activeEvaluatorConfigKey.value = ''
}

async function saveEvaluatorEndpoint() {
  if (!configuringEvaluatorId.value) return
  if (!evaluatorForm.name.trim()) {
    message.warning('Please enter evaluator endpoint name')
    return
  }
  if (!evaluatorForm.connector_type) {
    message.warning('Please select connection type')
    return
  }
  if (!evaluatorForm.token.trim()) {
    message.warning('Token is required')
    return
  }
  if (!evaluatorForm.model.trim()) {
    message.warning('Model is required')
    return
  }

  savingEvaluator.value = true
  try {
    const params = JSON.parse(evaluatorParamsText.value || '{}')
    const payload = {
      ...evaluatorForm,
      name: evaluatorForm.name.trim(),
      uri: evaluatorForm.uri.trim(),
      token: evaluatorForm.token.trim(),
      model: evaluatorForm.model.trim(),
      params,
    }
    const existingEndpoint = findEndpointById(configuringEvaluatorId.value)
    if (existingEndpoint) {
      await moonshotApi.updateEndpoint(endpointId(existingEndpoint), payload)
    } else {
      await moonshotApi.createEndpoint(payload)
    }
    await store.loadOverview()
    closeEvaluatorConfig()
    notify('success', { title: 'Endpoint saved', content: payload.name })
    message.success('Evaluator endpoint saved')
  } catch (error) {
    notify('error', { title: 'Save endpoint failed', content: error instanceof Error ? error.message : 'Save evaluator endpoint failed' })
    message.error(error instanceof Error ? error.message : 'Save evaluator endpoint failed')
  } finally {
    savingEvaluator.value = false
  }
}
</script>
