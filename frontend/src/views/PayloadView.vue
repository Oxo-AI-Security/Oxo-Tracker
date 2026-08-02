<template>
  <div class="payload-shell">
    <GlassPanel v-if="section === 'menu'" class="payload-panel">
      <div class="section-heading payload-page-heading">
        <div class="workspace-title-block">
          <span class="workspace-title-icon workspace-title-icon--payload">
            <n-icon><BookOutline /></n-icon>
          </span>
          <div class="workspace-title-content">
            <p class="eyebrow">{{ $t('auto.b5aa4e7dabf9') }}</p>
            <h2>{{ $t('auto.c515a6c5e9b1') }}</h2>
            <span>{{ $t('auto.0e1d4c4432ab') }}</span>
          </div>
        </div>
        <div class="payload-page-summary" :aria-label="$t('auto.09e7f8104e33')">
          <strong>{{ payloadSummary.total }}</strong>
          <span>{{ $t('auto.161aa8f365ec') }} {{ payloadFlowItems.length }} {{ $t('auto.1f7c8fe348bd') }}</span>
        </div>
      </div>

      <section class="payload-pipeline" :aria-label="$t('auto.19b7ae596a08')">
        <div
          v-for="item in payloadFlowItems"
          :key="item.key"
          class="payload-pipeline-step"
          :class="`payload-pipeline-step--${item.key}`"
        >
          <span class="payload-pipeline-node">{{ item.step }}</span>
          <span>
            <strong>{{ item.stage }}</strong>
            <small>{{ item.name }}</small>
          </span>
        </div>
      </section>

      <div class="payload-option-grid payload-option-grid--relationship">
        <RouterLink
          v-for="item in payloadMenuItems"
          :key="item.path"
          :to="item.path"
          class="payload-option-card payload-option-card--overview"
          :class="`payload-option-card--${item.key}`"
        >
          <span class="payload-overview-top">
            <span class="payload-option-head">
              <span class="payload-option-icon">
                <n-icon size="26"><component :is="item.icon" /></n-icon>
              </span>
              <span>
                <small>{{ item.role }}</small>
                <strong>{{ item.name }}</strong>
              </span>
            </span>
            <span class="payload-option-count">{{ item.count }}</span>
          </span>

          <span class="payload-card-description">{{ item.description }}</span>

          <span class="payload-card-path">
            <span>
              <b>{{ $t('auto.b568d47f2e24') }}</b>
              {{ item.consumes }}
            </span>
            <n-icon size="18"><ArrowForwardOutline /></n-icon>
            <span>
              <b>{{ $t('auto.4bed336194a9') }}</b>
              {{ item.produces }}
            </span>
          </span>

          <span class="payload-card-relation">{{ item.relationship }}</span>
        </RouterLink>
      </div>
    </GlassPanel>

    <div v-else class="stack">
      <n-button class="payload-back-button" secondary round @click="$router.push('/payload')"> {{ $t('auto.39356ae14c43') }} </n-button>
      <GlassPanel v-if="section === 'prompt-templates'" class="prompt-template-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">{{ $t('auto.eb94962502e0') }}</p>
            <h2>{{ $t('auto.7c0b0f2ffbc4') }}</h2>
          </div>
          <div class="endpoint-heading-actions">
            <n-tag round type="info">{{ store.promptTemplates.length }} {{ $t('auto.86761b63a7bd') }}</n-tag>
            <n-button type="primary" round @click="openTemplateModal">
              <template #icon><n-icon><AddOutline /></n-icon></template> {{ $t('auto.dcfa46211223') }} </n-button>
          </div>
        </div>

        <div class="prompt-template-layout">
          <section class="prompt-template-list-column">
            <div class="recipe-list-toolbar">
              <n-input v-model:value="templateSearch" clearable :placeholder="$t('auto.51b47d1c9ad4')">
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
                  <small>{{ template.description || template.template || $t('auto.f354c94fcf63') }}</small>
                </span>
                <n-tag :type="isOxoTemplate(template) ? 'success' : 'default'" round size="small">
                  {{ isOxoTemplate(template) ? 'Oxo' : $t('auto.6b0c36de2782') }}
                </n-tag>
              </button>
            </n-scrollbar>
            <n-empty v-else :description="$t('auto.ec1491b13bf9')" />
          </section>

          <section class="prompt-template-detail-card">
            <template v-if="activePromptTemplate">
              <div class="detail-title-row">
                <h3>
                  <n-icon><NewspaperOutline /></n-icon>
                  {{ activePromptTemplate.name || activePromptTemplate.id }}
                </h3>
                <div class="prompt-template-detail-actions">
                  <n-button
                    secondary
                    round
                    size="small"
                    type="primary"
                    :disabled="!isOxoTemplate(activePromptTemplate)"
                    @click="openEditTemplateModal(activePromptTemplate)"
                  >
                    <template #icon><n-icon><CreateOutline /></n-icon></template> {{ $t('auto.5301648dcf6b') }} </n-button>
                  <n-popconfirm :positive-text="$t('common.delete')" :negative-text="$t('auto.77dfd2135f4d')" @positive-click="deletePromptTemplate(activePromptTemplate)">
                    <template #trigger>
                      <n-button secondary round size="small" type="error" :disabled="!isOxoTemplate(activePromptTemplate)">
                        {{ $t('common.delete') }}
                      </n-button>
                    </template> {{ $t('auto.87c972803b2a') }} </n-popconfirm>
                </div>
              </div>
              <p>{{ activePromptTemplate.description || $t('auto.f354c94fcf63') }}</p>
              <dl class="prompt-template-meta">
                <div>
                  <dt>ID</dt>
                  <dd>{{ activePromptTemplate.id || '-' }}</dd>
                </div>
                <div>
                  <dt>{{ $t('auto.4651a34e4df9') }}</dt>
                  <dd>{{ isOxoTemplate(activePromptTemplate) ? $t('auto.feab81149b3c') : $t('auto.6b0c36de2782') }}</dd>
                </div>
              </dl>
              <div class="detail-block template-preview-block">
                <div class="template-preview-heading">
                  <strong>{{ $t('auto.3ec1ae061c27') }}</strong>
                  <n-button secondary round size="small" @click="openFullTemplate(activePromptTemplate)"> {{ $t('auto.9869e506c38f') }} </n-button>
                </div>
                <div class="template-render-card template-render-card-compact">
                  <template v-for="(part, index) in renderTemplateParts(activePromptTemplate.template || '')" :key="index">
                    <span v-if="part.type === 'text'">{{ part.value }}</span>
                    <b v-else class="prompt-token-block" v-text="PROMPT_LABEL"></b>
                  </template>
                </div>
              </div>
            </template>
            <n-empty v-else :description="$t('auto.bf024765572e')" />
          </section>
        </div>
      </GlassPanel>
      <ResourceTable
        v-else
        eyebrow="Prompt corpus"
        :title="$t('auto.061ac740047f')"
        :rows="store.datasets"
        :preferred-keys="['id', 'name', 'description', 'num_of_dataset_prompts']"
      />
    </div>

    <n-modal v-model:show="templateModalOpen" preset="card" class="prompt-template-modal" :bordered="false">
      <template #header>
        <div class="prompt-template-modal-title">
          <span>{{ isEditingTemplate ? $t('auto.14c7104fd282') : $t('auto.4ca8eee042d4') }}</span>
          <small>
            {{ isEditingTemplate
              ? $t('auto.a4de0115b1ca')
              : $t('auto.ae145af668b3') }}
          </small>
        </div>
      </template>
      <div class="prompt-template-modal-body">
        <section class="prompt-template-form">
          <section class="prompt-template-form-card">
            <p class="eyebrow">{{ $t('auto.7e5a975b6add') }}</p>
            <n-form label-placement="top">
              <n-form-item :label="$t('auto.709a23220f2c')">
                <n-input v-model:value="templateForm.name" :placeholder="$t('auto.53b34a42a23e')" />
              </n-form-item>
              <n-form-item :label="$t('auto.55f8ebc805e6')">
                <n-input
                  v-model:value="templateForm.description"
                  type="textarea"
                  :autosize="{ minRows: 3, maxRows: 5 }"
                  :placeholder="$t('auto.a269ffcb2d04')"
                />
              </n-form-item>
            </n-form>
          </section>
          <div class="template-block-editor">
            <div class="template-editor-head">
              <div>
                <strong>{{ $t('auto.d929b9f3646a') }}</strong>
                <small>{{ $t('auto.e965c4b128af') }}</small>
              </div>
              <n-button
                secondary
                round
                size="small"
                :disabled="templateBlocks.some((block) => block.type === 'prompt')"
                @click="insertPromptBlock"
              > {{ $t('auto.8a11547d1295') }} </n-button>
            </div>
            <div class="template-block-list">
              <template v-for="(block, index) in templateBlocks" :key="block.id">
                <n-input
                  v-if="block.type === 'text'"
                  v-model:value="block.value"
                  type="textarea"
                  :autosize="{ minRows: 2, maxRows: 8 }"
                  :placeholder="$t('auto.13f2e8c438b7')"
                />
                <div v-else class="template-editor-token">
                  <span v-text="PROMPT_LABEL"></span>
                  <n-button quaternary circle size="tiny" @click="removeTemplateBlock(index)">
                    <template #icon><n-icon><CloseOutline /></n-icon></template>
                  </n-button>
                </div>
              </template>
            </div>
          </div>
        </section>
        <aside class="prompt-template-live-preview">
          <p class="eyebrow">{{ $t('auto.f1fbb2b43dca') }}</p>
          <div class="template-render-card">
            <template v-for="(part, index) in renderTemplateParts(templateBody)" :key="index">
              <span v-if="part.type === 'text'">{{ part.value }}</span>
              <b v-else class="prompt-token-block" v-text="PROMPT_LABEL"></b>
            </template>
          </div>
          <small>
            {{ isEditingTemplate
              ? $t('auto.d94dabc1c4d0')
              : $t('auto.8c5b4acb3a00') }}
          </small>
        </aside>
      </div>
      <template #footer>
        <div class="modal-footer-actions">
          <n-button round @click="templateModalOpen = false">{{ $t('auto.77dfd2135f4d') }}</n-button>
          <n-button type="primary" round :loading="templateSubmitting" :disabled="!canSubmitTemplate" @click="submitPromptTemplate">
            {{ isEditingTemplate ? $t('auto.fa2984b367b8') : $t('auto.e48e66854662') }}
          </n-button>
        </div>
      </template>
    </n-modal>

    <n-modal v-model:show="templatePreviewModalOpen" preset="card" class="prompt-template-full-modal" :bordered="false">
      <template #header>{{ templatePreviewTitle }}</template>
      <div class="template-render-card template-render-card-full">
        <template v-for="(part, index) in renderTemplateParts(templatePreviewBody)" :key="index">
          <span v-if="part.type === 'text'">{{ part.value }}</span>
          <b v-else class="prompt-token-block" v-text="PROMPT_LABEL"></b>
        </template>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { translateSource } from '../i18n'

import { computed, reactive, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  AddOutline,
  ArrowForwardOutline,
  BookOutline,
  CloseOutline,
  CreateOutline,
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
const PROMPT_LABEL = 'Prompt'
const selectedTemplateId = ref('')
const templateSearch = ref('')
const templateScope = ref<'all' | 'oxo'>('all')
const templateModalOpen = ref(false)
const templatePreviewModalOpen = ref(false)
const templatePreviewTitle = ref('')
const templatePreviewBody = ref('')
const templateSubmitting = ref(false)
const editingTemplateId = ref('')
const templateForm = reactive({ name: '', description: '' })
const templateBlocks = ref<Array<{ id: string; type: 'text' | 'prompt'; value: string }>>([])

const templateScopeOptions = [
  { label: translateSource('auto.0bba114cc6d7'), value: 'all' },
  { label: translateSource('auto.84ed8f3d1c5a'), value: 'oxo' },
]

const section = computed(() => {
  if (route.path.endsWith('/prompt-templates')) return 'prompt-templates'
  if (route.path.endsWith('/datasets')) return 'datasets'
  return 'menu'
})

const payloadMenuItems = computed(() => [
  {
    key: 'datasets',
    step: '01',
    stage: translateSource('payloadFlow.datasets.stage'),
    role: translateSource('payloadFlow.datasets.role'),
    name: translateSource('payloadFlow.datasets.name'),
    description: translateSource('auto.c86a81e0b006'),
    analysis: translateSource('payloadFlow.datasets.analysis'),
    relationship: translateSource('payloadFlow.datasets.relationship'),
    consumes: translateSource('payloadFlow.datasets.consumes'),
    produces: translateSource('payloadFlow.datasets.produces'),
    icon: FileTrayStackedOutline,
    path: '/payload/datasets',
    count: store.datasets.length,
  },
  {
    key: 'prompt-templates',
    step: '02',
    stage: translateSource('payloadFlow.templates.stage'),
    role: translateSource('payloadFlow.templates.role'),
    name: translateSource('payloadFlow.templates.name'),
    description: translateSource('auto.be7aecdb05f8'),
    analysis: translateSource('payloadFlow.templates.analysis'),
    relationship: translateSource('payloadFlow.templates.relationship'),
    consumes: translateSource('payloadFlow.templates.consumes'),
    produces: translateSource('payloadFlow.templates.produces'),
    icon: NewspaperOutline,
    path: '/payload/prompt-templates',
    count: store.promptTemplates.length,
  },
  {
    key: 'recipes',
    step: '03',
    stage: translateSource('payloadFlow.recipes.stage'),
    role: translateSource('payloadFlow.recipes.role'),
    name: translateSource('payloadFlow.recipes.name'),
    description: translateSource('auto.1e0591fd8d99'),
    analysis: translateSource('payloadFlow.recipes.analysis'),
    relationship: translateSource('payloadFlow.recipes.relationship'),
    consumes: translateSource('payloadFlow.recipes.consumes'),
    produces: translateSource('payloadFlow.recipes.produces'),
    icon: DocumentTextOutline,
    path: '/payload/recipes',
    count: store.recipes.length,
  },
  {
    key: 'cookbooks',
    step: '04',
    stage: translateSource('payloadFlow.cookbooks.stage'),
    role: translateSource('payloadFlow.cookbooks.role'),
    name: translateSource('payloadFlow.cookbooks.name'),
    description: translateSource('auto.87c0fef2b7e4'),
    analysis: translateSource('payloadFlow.cookbooks.analysis'),
    relationship: translateSource('payloadFlow.cookbooks.relationship'),
    consumes: translateSource('payloadFlow.cookbooks.consumes'),
    produces: translateSource('payloadFlow.cookbooks.produces'),
    icon: BookOutline,
    path: '/payload/cookbooks',
    count: store.cookbooks.length,
  },
])

const payloadFlowItems = computed(() => payloadMenuItems.value)

const payloadSummary = computed(() => ({
  total: store.datasets.length + store.promptTemplates.length + store.recipes.length + store.cookbooks.length,
}))

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

const isEditingTemplate = computed(() => Boolean(editingTemplateId.value))
const canSubmitTemplate = computed(() => Boolean(templateForm.name.trim()) && templateBody.value.includes(PROMPT_TOKEN))

function templateId(template?: PromptTemplateRecord) {
  return String(template?.id || template?.name || '')
}

function isOxoTemplate(template?: PromptTemplateRecord) {
  return templateId(template).startsWith('Oxo-')
}

function openTemplateModal() {
  editingTemplateId.value = ''
  templateForm.name = ''
  templateForm.description = ''
  templateBlocks.value = [{ id: `block-${Date.now()}`, type: 'text', value: '' }]
  templateModalOpen.value = true
}

function openEditTemplateModal(template: PromptTemplateRecord) {
  const id = templateId(template)
  if (!id || !isOxoTemplate(template)) return
  editingTemplateId.value = id
  templateForm.name = String(template.name || '')
  templateForm.description = String(template.description || '')
  templateBlocks.value = createTemplateBlocks(String(template.template || PROMPT_TOKEN))
  templateModalOpen.value = true
}

function insertPromptBlock() {
  if (templateBlocks.value.some((block) => block.type === 'prompt')) return
  const promptBlock = { id: `block-${Date.now()}-prompt`, type: 'prompt' as const, value: PROMPT_TOKEN }
  if (!templateBlocks.value.length || templateBlocks.value.every((block) => block.type === 'text' && !block.value.trim())) {
    templateBlocks.value = [
      promptBlock,
      { id: `block-${Date.now()}-text`, type: 'text', value: '' },
    ]
    return
  }
  templateBlocks.value.push(
    promptBlock,
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
  if (!templateBlocks.value.length) {
    templateBlocks.value = [{ id: `block-${Date.now()}-text`, type: 'text', value: '' }]
  }
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

function createTemplateBlocks(value: string) {
  const now = Date.now()
  const parts = renderTemplateParts(value)
  if (!parts.length) return [{ id: `block-${now}-text`, type: 'text' as const, value: '' }]
  return parts.map((part, index) => ({
    id: `block-${now}-${index}`,
    type: part.type as 'text' | 'prompt',
    value: part.type === 'prompt' ? PROMPT_TOKEN : part.value,
  }))
}

async function submitPromptTemplate() {
  if (!canSubmitTemplate.value) return
  templateSubmitting.value = true
  const wasEditing = isEditingTemplate.value
  try {
    const payload = {
      name: templateForm.name.trim(),
      description: templateForm.description.trim(),
      template: templateBody.value,
    }
    const id = wasEditing
      ? editingTemplateId.value
      : await moonshotApi.createPromptTemplate(payload)
    if (wasEditing) await moonshotApi.updatePromptTemplate(id, payload)
    await store.loadOverview()
    selectedTemplateId.value = id
    templateModalOpen.value = false
    editingTemplateId.value = ''
    message.success(wasEditing ? 'Prompt template updated' : 'Prompt template created')
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Save prompt template failed')
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
    message.success(translateSource('auto.289363f25c67'))
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Delete prompt template failed')
  }
}
</script>
