<template>
  <div class="payload-shell">
    <GlassPanel v-if="section === 'menu'" class="payload-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Payload library</p>
          <h2>Payload</h2>
        </div>
      </div>

      <div class="payload-option-grid">
        <RouterLink v-for="item in payloadItems" :key="item.path" :to="item.path" class="payload-option-card">
          <span class="payload-option-head">
            <span class="payload-option-icon">
              <n-icon size="26"><component :is="item.icon" /></n-icon>
            </span>
            <strong>{{ item.name }}</strong>
          </span>
          <small>{{ item.description }}</small>
          <span class="payload-option-count">{{ item.count }}</span>
        </RouterLink>
      </div>
    </GlassPanel>

    <div v-else class="stack">
      <n-button class="payload-back-button" secondary round @click="$router.push('/payload')">
        Back to Payload
      </n-button>
      <GlassPanel v-if="section === 'prompt-templates'" class="prompt-template-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Prompt wrappers</p>
            <h2>Prompt Templates</h2>
          </div>
          <div class="endpoint-heading-actions">
            <n-tag round type="info">{{ store.promptTemplates.length }} records</n-tag>
            <n-button type="primary" round @click="openTemplateModal">
              <template #icon><n-icon><AddOutline /></n-icon></template>
              New Template
            </n-button>
          </div>
        </div>

        <div class="prompt-template-layout">
          <section class="prompt-template-list-column">
            <div class="recipe-list-toolbar">
              <n-input v-model:value="templateSearch" clearable placeholder="Search prompt templates">
                <template #prefix><n-icon><SearchOutline /></n-icon></template>
              </n-input>
              <n-select v-model:value="templateScope" :options="templateScopeOptions" />
            </div>
            <n-scrollbar v-if="filteredPromptTemplates.length" class="prompt-template-scrollbar">
              <button
                v-for="template in filteredPromptTemplates"
                :key="templateId(template)"
                class="recipe-row prompt-template-row"
                :class="{ active: templateId(template) === templateId(activePromptTemplate) }"
                type="button"
                @click="selectedTemplateId = templateId(template)"
              >
                <span class="row-icon"><n-icon size="22"><NewspaperOutline /></n-icon></span>
                <span class="row-copy">
                  <strong>{{ template.name || template.id }}</strong>
                  <small>{{ template.description || template.template || 'No description' }}</small>
                </span>
                <n-tag :type="isOxoTemplate(template) ? 'success' : 'default'" round size="small">
                  {{ isOxoTemplate(template) ? 'Oxo' : 'Built in' }}
                </n-tag>
              </button>
            </n-scrollbar>
            <n-empty v-else description="No prompt templates found" />
          </section>

          <section class="prompt-template-detail-card">
            <template v-if="activePromptTemplate">
              <div class="detail-title-row">
                <h3>
                  <n-icon><NewspaperOutline /></n-icon>
                  {{ activePromptTemplate.name || activePromptTemplate.id }}
                </h3>
                <n-popconfirm positive-text="Delete" negative-text="Cancel" @positive-click="deletePromptTemplate(activePromptTemplate)">
                  <template #trigger>
                    <n-button secondary round size="small" type="error" :disabled="!isOxoTemplate(activePromptTemplate)">
                      Delete
                    </n-button>
                  </template>
                  Delete this Oxo prompt template?
                </n-popconfirm>
              </div>
              <p>{{ activePromptTemplate.description || 'No description' }}</p>
              <dl class="prompt-template-meta">
                <div>
                  <dt>ID</dt>
                  <dd>{{ activePromptTemplate.id || '-' }}</dd>
                </div>
                <div>
                  <dt>Scope</dt>
                  <dd>{{ isOxoTemplate(activePromptTemplate) ? 'My template' : 'Built in' }}</dd>
                </div>
              </dl>
              <div class="detail-block template-preview-block">
                <div class="template-preview-heading">
                  <strong>Template</strong>
                  <n-button secondary round size="small" @click="openFullTemplate(activePromptTemplate)">
                    Expand
                  </n-button>
                </div>
                <div class="template-render-card template-render-card-compact">
                  <template v-for="(part, index) in renderTemplateParts(activePromptTemplate.template || '')" :key="index">
                    <span v-if="part.type === 'text'">{{ part.value }}</span>
                    <b v-else class="prompt-token-block" v-text="PROMPT_TOKEN"></b>
                  </template>
                </div>
              </div>
            </template>
            <n-empty v-else description="Select a prompt template" />
          </section>
        </div>
      </GlassPanel>
      <ResourceTable
        v-else
        eyebrow="Prompt corpus"
        title="datasets"
        :rows="store.datasets"
        :preferred-keys="['id', 'name', 'description', 'num_of_dataset_prompts']"
      />
    </div>

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
          <small>Saved ID will start with Oxo- and can be deleted later.</small>
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

    <n-modal v-model:show="templatePreviewModalOpen" preset="card" class="prompt-template-full-modal" :bordered="false">
      <template #header>{{ templatePreviewTitle }}</template>
      <div class="template-render-card template-render-card-full">
        <template v-for="(part, index) in renderTemplateParts(templatePreviewBody)" :key="index">
          <span v-if="part.type === 'text'">{{ part.value }}</span>
          <b v-else class="prompt-token-block" v-text="PROMPT_TOKEN"></b>
        </template>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  AddOutline,
  BookOutline,
  CloseOutline,
  DocumentTextOutline,
  FileTrayStackedOutline,
  NewspaperOutline,
  SearchOutline,
} from '@vicons/ionicons5'
import GlassPanel from '../components/GlassPanel.vue'
import ResourceTable from '../components/ResourceTable.vue'
import { moonshotApi } from '../api/moonshot'
import { useMoonshotStore } from '../stores/moonshot'
import type { PromptTemplateRecord } from '../types/moonshot'

const store = useMoonshotStore()
const route = useRoute()
const message = useMessage()
const PROMPT_TOKEN = '{{ prompt }}'
const selectedTemplateId = ref('')
const templateSearch = ref('')
const templateScope = ref<'all' | 'oxo'>('all')
const templateModalOpen = ref(false)
const templatePreviewModalOpen = ref(false)
const templatePreviewTitle = ref('')
const templatePreviewBody = ref('')
const templateSubmitting = ref(false)
const templateForm = reactive({ name: '', description: '' })
const templateBlocks = ref<Array<{ id: string; type: 'text' | 'prompt'; value: string }>>([])

const templateScopeOptions = [
  { label: 'All templates', value: 'all' },
  { label: 'My templates', value: 'oxo' },
]

const section = computed(() => {
  if (route.path.endsWith('/prompt-templates')) return 'prompt-templates'
  if (route.path.endsWith('/datasets')) return 'datasets'
  return 'menu'
})

const payloadItems = computed(() => [
  {
    name: 'Cookbooks',
    description: 'Group recipes into reusable evaluation suites for benchmark runs.',
    icon: BookOutline,
    path: '/payload/cookbooks',
    count: store.cookbooks.length,
  },
  {
    name: 'Recipes',
    description: 'Browse existing recipes and create or edit Oxo-owned benchmark recipes.',
    icon: DocumentTextOutline,
    path: '/payload/recipes',
    count: store.recipes.length,
  },
  {
    name: 'Prompt Templates',
    description: 'Inspect prompt wrappers used to format datasets before model evaluation.',
    icon: NewspaperOutline,
    path: '/payload/prompt-templates',
    count: store.promptTemplates.length,
  },
  {
    name: 'datasets',
    description: 'Review prompt corpora that supply inputs and expected answers to recipes.',
    icon: FileTrayStackedOutline,
    path: '/payload/datasets',
    count: store.datasets.length,
  },
])

const filteredPromptTemplates = computed(() => {
  const keyword = templateSearch.value.trim().toLowerCase()
  return store.promptTemplates.filter((template) => {
    if (templateScope.value === 'oxo' && !isOxoTemplate(template)) return false
    if (!keyword) return true
    return [template.id, template.name, template.description, template.template]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(keyword))
  })
})

const activePromptTemplate = computed(() => {
  return filteredPromptTemplates.value.find((template) => templateId(template) === selectedTemplateId.value) ?? filteredPromptTemplates.value[0]
})

const templateBody = computed(() =>
  templateBlocks.value
    .map((block) => (block.type === 'prompt' ? '{{ prompt }}' : block.value))
    .join(''),
)

const canCreateTemplate = computed(() => templateForm.name.trim() && templateBody.value.includes('{{ prompt }}'))

function templateId(template?: PromptTemplateRecord) {
  return String(template?.id || template?.name || '')
}

function isOxoTemplate(template?: PromptTemplateRecord) {
  return templateId(template).startsWith('Oxo-')
}

function openTemplateModal() {
  templateForm.name = ''
  templateForm.description = ''
  templateBlocks.value = [{ id: `block-${Date.now()}`, type: 'text', value: '' }]
  templateModalOpen.value = true
}

function insertPromptBlock() {
  templateBlocks.value.push(
    { id: `block-${Date.now()}-prompt`, type: 'prompt', value: '{{ prompt }}' },
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

function openFullTemplate(template: PromptTemplateRecord) {
  templatePreviewTitle.value = template.name || template.id || 'Prompt Template'
  templatePreviewBody.value = template.template || ''
  templatePreviewModalOpen.value = true
}

function renderTemplateParts(value: string) {
  return value.split(/(\{\{\s*prompt\s*\}\})/g)
    .filter(Boolean)
    .map((part) => (/\{\{\s*prompt\s*\}\}/.test(part) ? { type: 'prompt', value: part } : { type: 'text', value: part }))
}

async function createPromptTemplate() {
  if (!canCreateTemplate.value) return
  templateSubmitting.value = true
  try {
    const id = await moonshotApi.createPromptTemplate({
      name: templateForm.name.trim(),
      description: templateForm.description.trim(),
      template: templateBody.value,
    })
    await store.loadOverview()
    selectedTemplateId.value = id
    templateModalOpen.value = false
    message.success('Prompt template created')
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Create prompt template failed')
  } finally {
    templateSubmitting.value = false
  }
}

async function deletePromptTemplate(template: PromptTemplateRecord) {
  const id = templateId(template)
  if (!id || !isOxoTemplate(template)) return
  try {
    await moonshotApi.deletePromptTemplate(id)
    await store.loadOverview()
    selectedTemplateId.value = ''
    message.success('Prompt template deleted')
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Delete prompt template failed')
  }
}
</script>
