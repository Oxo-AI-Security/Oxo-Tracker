<template>
  <div class="recipe-admin-shell">
    <GlassPanel v-if="mode === 'list'" class="recipe-admin-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">{{ $t('auto.88dc644205a2') }}</p>
          <h2>{{ $t('auto.9fb1092f32d4') }}</h2>
        </div>
        <n-button type="primary" round @click="openCreate">
          <template #icon><n-icon><AddOutline /></n-icon></template> {{ $t('auto.6f82911d7813') }} </n-button>
      </div>

      <div class="recipe-admin-grid">
        <section class="recipe-admin-list-column">
          <div class="recipe-list-toolbar">
            <n-input v-model:value="search" clearable :placeholder="$t('auto.93095b69ed70')">
              <template #prefix><n-icon><SearchOutline /></n-icon></template>
            </n-input>
            <n-select v-model:value="recipeScope" :options="recipeScopeOptions" />
          </div>
          <n-scrollbar v-if="filteredRecipes.length" class="recipe-list-scrollbar">
            <div class="recipe-list">
              <button
                v-for="recipe in filteredRecipes"
                :key="recordId(recipe)"
                class="recipe-row recipe-view-row"
                :class="{ active: recordId(recipe) === recordId(activeRecipe) }"
                type="button"
                @click="selectedRecipeId = recordId(recipe)"
              >
                <span class="row-icon"><n-icon size="22"><DocumentTextOutline /></n-icon></span>
                <span class="row-copy">
                  <strong>{{ recipe.name || recipe.id }}</strong>
                  <small>{{ recipe.description || $t('auto.f354c94fcf63') }}</small>
                </span>
                <n-tag :type="isOxoRecipe(recipe) ? 'success' : 'default'" round size="small">
                  {{ isOxoRecipe(recipe) ? 'Editable' : $t('auto.601dcc1c87c3') }}
                </n-tag>
              </button>
            </div>
          </n-scrollbar>
          <n-empty v-else :description="$t('auto.7d55957b5dda')" />
        </section>

        <section class="recipe-detail-card recipe-admin-detail">
          <template v-if="activeRecipe">
            <div class="detail-title-row">
              <h3>
                <n-icon><DocumentTextOutline /></n-icon>
                {{ activeRecipe.name || activeRecipe.id }}
              </h3>
              <n-space>
                <n-button secondary round size="small" :disabled="!isOxoRecipe(activeRecipe)" @click="openEdit(activeRecipe)"> {{ $t('auto.5301648dcf6b') }} </n-button>
                <n-popconfirm :positive-text="$t('common.delete')" :negative-text="$t('auto.77dfd2135f4d')" @positive-click="deleteRecipe(activeRecipe)">
                  <template #trigger>
                    <n-button secondary round size="small" type="error" :disabled="!isOxoRecipe(activeRecipe)">
                      {{ $t('common.delete') }}
                    </n-button>
                  </template> {{ $t('auto.d3273e3410a0') }} </n-popconfirm>
              </n-space>
            </div>
            <p>{{ activeRecipe.description || $t('auto.f354c94fcf63') }}</p>
            <div class="detail-block">
              <strong>{{ $t('auto.93a7f22476e9') }}</strong>
              <span>{{ listText(activeRecipe.datasets) }}</span>
            </div>
            <div class="detail-block">
              <strong>{{ $t('auto.ddf6a1f0ce8c') }}</strong>
              <div class="mini-resource-list">
                <article v-for="metric in selectedMetricRecords(activeRecipe.metrics)" :key="resourceId(metric)">
                  <b>{{ resourceName(metric) }}</b>
                  <span>{{ resourceDescription(metric) }}</span>
                </article>
                <span v-if="!hasMeaningfulIds(activeRecipe.metrics)">-</span>
              </div>
            </div>
            <div class="detail-block">
              <strong>{{ $t('auto.7c0b0f2ffbc4') }}</strong>
              <div class="mini-resource-list">
                <article v-for="template in selectedPromptTemplateRecords(activeRecipe.prompt_templates)" :key="recordId(template)">
                  <b>{{ template.name || template.id }}</b>
                  <span>{{ template.description || $t('auto.f354c94fcf63') }}</span>
                  <pre>{{ template.template || $t('auto.e5193414c910') }}</pre>
                </article>
                <span v-if="!hasMeaningfulIds(activeRecipe.prompt_templates)">-</span>
              </div>
            </div>
          </template>
          <n-empty v-else :description="$t('auto.9fd03241327c')" />
        </section>
      </div>
    </GlassPanel>

    <GlassPanel v-else class="recipe-form-panel">
      <div class="builder-header">
        <h2>{{ editingId ? $t('auto.838f93ac4be2') : $t('auto.6f82911d7813') }}</h2>
        <n-button circle quaternary @click="mode = 'list'">
          <template #icon><n-icon><CloseOutline /></n-icon></template>
        </n-button>
      </div>

      <div class="recipe-form-layout">
        <n-form class="recipe-form-main" label-placement="top">
          <section class="recipe-form-section">
            <p class="eyebrow">{{ $t('auto.a6da18c76164') }}</p>
            <n-form-item>
              <template #label><span class="required-label">{{ $t('auto.709a23220f2c') }} <b>*</b></span></template>
              <n-input v-model:value="form.name" :placeholder="$t('auto.2daa01146493')" />
            </n-form-item>
            <n-form-item :label="$t('auto.55f8ebc805e6')">
              <n-input
                v-model:value="form.description"
                type="textarea"
                :autosize="{ minRows: 4, maxRows: 6 }"
                :placeholder="$t('auto.3c24535c5649')"
              />
            </n-form-item>
          </section>

          <section class="recipe-form-section">
            <p class="eyebrow">{{ $t('auto.eccb48dcda56') }}</p>
            <n-form-item>
              <template #label><span class="required-label">{{ $t('auto.93a7f22476e9') }} <b>*</b></span></template>
              <button class="resource-select-card" type="button" @click="openResourcePicker('datasets')">
                <span>
                  <strong>{{ selectedDatasetRecords.length ? `${selectedDatasetRecords.length} datasets selected` : $t('auto.3ad7265f12cc') }}</strong>
                  <small>{{ selectedDatasetRecords.map(resourceName).join(', ') || $t('auto.ce3de94db8d4') }}</small>
                </span>
                <n-button secondary round size="small" @click.stop="openResourcePicker('datasets')">{{ $t('auto.2f3b5c55bc27') }}</n-button>
              </button>
            </n-form-item>
          </section>
        </n-form>

        <aside class="recipe-form-side">
          <section class="recipe-form-section">
            <p class="eyebrow">{{ $t('auto.d3d447cca64a') }}</p>
            <n-form-item>
              <template #label><span class="required-label">{{ $t('auto.ddf6a1f0ce8c') }} <b>*</b></span></template>
              <button class="resource-select-card" type="button" @click="openResourcePicker('metrics')">
                <span>
                  <strong>{{ selectedMetricRecords(form.metric)[0] ? resourceName(selectedMetricRecords(form.metric)[0]) : $t('auto.87ad54544bd1') }}</strong>
                  <small>{{ $t('auto.d8049e76e09e') }}</small>
                </span>
                <n-button secondary round size="small" @click.stop="openResourcePicker('metrics')">{{ $t('auto.2f3b5c55bc27') }}</n-button>
              </button>
            </n-form-item>
            <n-form-item :label="$t('auto.7c0b0f2ffbc4')">
              <button class="resource-select-card" type="button" @click="openResourcePicker('prompt_templates')">
                <span>
                  <strong>{{ selectedPromptTemplateRecords(form.prompt_template)[0]?.name || selectedPromptTemplateRecords(form.prompt_template)[0]?.id || $t('auto.9c15964cd63e') }}</strong>
                  <small>{{ $t('auto.36658e3d8b4a') }}</small>
                </span>
                <n-button secondary round size="small" @click.stop="openResourcePicker('prompt_templates')">{{ $t('auto.2f3b5c55bc27') }}</n-button>
              </button>
            </n-form-item>
          </section>

          <section class="recipe-form-section">
            <p class="eyebrow">{{ $t('auto.2228985493d9') }}</p>
            <n-form-item :label="$t('auto.848eed0fbd54')">
              <div class="tag-editor">
                <div class="tag-input-row">
                  <n-input
                    v-model:value="tagDraft"
                    :placeholder="$t('auto.a5d789137792')"
                    @keyup.enter="addTag(tagDraft)"
                  />
                  <n-button secondary round @click="addTag(tagDraft)">{{ $t('auto.61cc55aa0453') }}</n-button>
                </div>
                <div class="tag-chip-row">
                  <n-tag v-for="tag in form.tags" :key="tag" closable round @close="removeTag(tag)">
                    {{ tag }}
                  </n-tag>
                  <span v-if="!form.tags.length">{{ $t('auto.5e58be75332f') }}</span>
                </div>
                <div v-if="commonTags.length" class="tag-suggestion-row">
                  <button v-for="tag in commonTags" :key="tag" type="button" @click="addTag(tag)">
                    {{ tag }}
                  </button>
                </div>
              </div>
            </n-form-item>
            <n-form-item :label="$t('auto.6ccb60071be8')">
              <div class="category-choice-row">
                <button
                  v-for="category in categoryOptions"
                  :key="category"
                  class="category-choice-button"
                  :class="{ active: form.category === category }"
                  type="button"
                  @click="form.category = category"
                >
                  {{ category }}
                </button>
              </div>
            </n-form-item>
          </section>
        </aside>
      </div>

      <div class="recipe-helper-grid">
        <section class="recipe-preview-panel">
          <p class="eyebrow">{{ $t('auto.7cd37a4fc6be') }}</p>
          <article v-for="metric in selectedMetricRecords(form.metric)" :key="resourceId(metric)" class="helper-card">
            <strong>{{ resourceName(metric) }}</strong>
            <span>{{ resourceDescription(metric) }}</span>
          </article>
          <n-empty v-if="!form.metric" :description="$t('auto.87ad54544bd1')" />
        </section>
        <section class="recipe-preview-panel">
          <p class="eyebrow">{{ $t('auto.ea0aa8b2837c') }}</p>
          <article v-for="template in selectedPromptTemplateRecords(form.prompt_template)" :key="recordId(template)" class="helper-card">
            <strong>{{ template.name || template.id }}</strong>
            <span>{{ template.description || $t('auto.f354c94fcf63') }}</span>
            <pre>{{ template.template || $t('auto.e5193414c910') }}</pre>
          </article>
          <n-empty v-if="!form.prompt_template" :description="$t('auto.9c15964cd63e')" />
        </section>
      </div>

      <div class="builder-actions">
        <n-button round size="large" @click="mode = 'list'">{{ $t('auto.77dfd2135f4d') }}</n-button>
        <n-button
          type="primary"
          round
          size="large"
          :loading="submitting"
          :disabled="!canSubmit"
          @click="saveRecipe"
        >
          {{ editingId ? $t('auto.48153eb81ba1') : $t('auto.6f82911d7813') }}
        </n-button>
      </div>
    </GlassPanel>

    <n-modal v-model:show="resourcePickerOpen" preset="card" class="resource-picker-modal" :bordered="false">
      <template #header>{{ resourcePickerTitle }}</template>
      <div class="resource-picker-shell">
        <n-input v-model:value="resourceSearch" clearable :placeholder="`Search ${resourcePickerTitle.toLowerCase()}`">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>

        <n-scrollbar class="resource-picker-scrollbar">
          <div class="resource-picker-list">
            <article
              v-for="item in filteredPickerItems"
              :key="item.id"
              class="resource-picker-row"
              :class="{ selected: isPickerItemSelected(item.id) }"
            >
              <button class="resource-picker-preview" type="button" @click="toggleExpandedResource(item.id)">
                <span>
                  <strong>{{ item.name }}</strong>
                  <small>{{ item.description }}</small>
                </span>
                <n-icon><ChevronDownOutline v-if="expandedResourceId !== item.id" /><ChevronUpOutline v-else /></n-icon>
              </button>
              <div v-if="expandedResourceId === item.id" class="resource-picker-detail">
                <dl>
                  <div>
                    <dt>ID</dt>
                    <dd>{{ item.id }}</dd>
                  </div>
                  <div v-for="detail in item.details" :key="detail.label">
                    <dt>{{ detail.label }}</dt>
                    <dd>
                      <pre v-if="detail.multiline">{{ detail.value }}</pre>
                      <span v-else>{{ detail.value }}</span>
                    </dd>
                  </div>
                </dl>
              </div>
              <div class="resource-picker-actions">
                <n-button
                  v-if="pickerKind !== 'datasets' && isPickerItemSelected(item.id)"
                  secondary
                  round
                  size="small"
                  @click="clearPickerSelection"
                > {{ $t('auto.719ea396ad92') }} </n-button>
                <n-button
                  :type="isPickerItemSelected(item.id) ? 'primary' : 'default'"
                  round
                  size="small"
                  @click="togglePickerSelection(item.id)"
                >
                  {{ isPickerItemSelected(item.id) ? 'Selected' : 'Select' }}
                </n-button>
              </div>
            </article>
            <n-empty v-if="!filteredPickerItems.length" :description="$t('auto.f33b195dddfc')" />
          </div>
        </n-scrollbar>
      </div>
      <template #footer>
        <n-space justify="end">
          <n-button round @click="resourcePickerOpen = false">{{ $t('auto.e9b450d14bc2') }}</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { translateSource } from '../i18n'

import { computed, reactive, ref } from 'vue'
import { useMessage } from 'naive-ui'
import {
  AddOutline,
  ChevronDownOutline,
  ChevronUpOutline,
  CloseOutline,
  DocumentTextOutline,
  SearchOutline,
} from '@vicons/ionicons5'
import GlassPanel from '../components/GlassPanel.vue'
import { moonshotApi } from '../api/moonshot'
import { useMoonshotStore } from '../stores/moonshot'
import type { RecipeRecord, ResourceRecord } from '../types/moonshot'

type Mode = 'list' | 'form'
type ResourcePickerKind = 'datasets' | 'metrics' | 'prompt_templates'
type PickerItem = {
  id: string
  name: string
  description: string
  details: Array<{ label: string; value: string; multiline?: boolean }>
}

const store = useMoonshotStore()
const message = useMessage()
const mode = ref<Mode>('list')
const search = ref('')
const recipeScope = ref<'all' | 'mine'>('all')
const selectedRecipeId = ref('')
const editingId = ref('')
const submitting = ref(false)
const resourcePickerOpen = ref(false)
const pickerKind = ref<ResourcePickerKind>('datasets')
const resourceSearch = ref('')
const expandedResourceId = ref('')
const tagDraft = ref('')

const recipeScopeOptions = [
  { label: translateSource('auto.39e2ef7a56ee'), value: 'all' },
  { label: translateSource('auto.092ea0b5ff34'), value: 'mine' },
]

const categoryOptions = ['Trust & Safety', 'Capability', 'Others']

const defaultGradingScale = {
  A: [80, 100],
  B: [60, 79],
  C: [40, 59],
  D: [20, 39],
  E: [0, 19],
}

const form = reactive({
  name: '',
  description: '',
  tags: [] as string[],
  category: 'Others',
  datasets: [] as string[],
  prompt_template: null as string | null,
  metric: null as string | null,
  grading_scale: { ...defaultGradingScale } as Record<string, number[]>,
})

const filteredRecipes = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  const scopedRecipes =
    recipeScope.value === 'mine' ? store.recipes.filter((recipe) => isOxoRecipe(recipe)) : store.recipes
  if (!keyword) return scopedRecipes
  return scopedRecipes.filter((recipe) =>
    [recipe.id, recipe.name, recipe.description, recipe.datasets?.join(' '), recipe.metrics?.join(' ')].some((value) =>
      String(value ?? '').toLowerCase().includes(keyword),
    ),
  )
})

const activeRecipe = computed(() => {
  return (
    filteredRecipes.value.find((recipe) => recordId(recipe) === selectedRecipeId.value) ??
    filteredRecipes.value[0]
  )
})

const selectedDatasetRecords = computed(() => {
  const selected = new Set(form.datasets)
  return store.datasets.filter((dataset) => selected.has(resourceId(dataset)))
})

const resourcePickerTitle = computed(() => {
  if (pickerKind.value === 'datasets') return 'Datasets'
  if (pickerKind.value === 'metrics') return 'Metrics'
  return 'Prompt Templates'
})

const pickerItems = computed<PickerItem[]>(() => {
  if (pickerKind.value === 'datasets') {
    return store.datasets.map((dataset) => ({
      id: resourceId(dataset),
      name: resourceName(dataset),
      description: resourceDescription(dataset),
      details: resourceDetails(dataset, ['id', 'name', 'description']),
    }))
  }
  if (pickerKind.value === 'metrics') {
    return store.metrics.map((metric) => ({
      id: resourceId(metric),
      name: resourceName(metric),
      description: resourceDescription(metric),
      details: resourceDetails(metric, ['id', 'name', 'description']),
    }))
  }
  return store.promptTemplates.map((template) => ({
    id: recordId(template),
    name: template.name || template.id || 'Unnamed',
    description: template.description || 'No description',
    details: [
      { label: 'Description', value: template.description || 'No description' },
      { label: 'Template', value: template.template || 'No template body', multiline: true },
    ],
  }))
})

const filteredPickerItems = computed(() => {
  const keyword = resourceSearch.value.trim().toLowerCase()
  if (!keyword) return pickerItems.value
  return pickerItems.value.filter((item) =>
    [item.id, item.name, item.description].some((value) => value.toLowerCase().includes(keyword)),
  )
})

const canSubmit = computed(() => {
  return form.name.trim().length > 0 && form.datasets.length > 0 && Boolean(form.metric)
})

const commonTags = computed(() => {
  const counts = new Map<string, number>()
  for (const recipe of store.recipes) {
    for (const tag of recipe.tags ?? []) {
      if (!tag || form.tags.includes(tag)) continue
      counts.set(tag, (counts.get(tag) ?? 0) + 1)
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, 6)
    .map(([tag]) => tag)
})

function recordId(record?: { id?: string; name?: string }) {
  return String(record?.id || record?.name || '')
}

function resourceId(record: ResourceRecord) {
  return String(record.id || record.name || '')
}

function resourceName(record: ResourceRecord) {
  return String(record.name || record.id || 'Unnamed')
}

function resourceDescription(record: ResourceRecord) {
  return String(record.description || 'No description')
}

function resourceDetails(record: ResourceRecord, omittedKeys: string[] = []) {
  const omitted = new Set(omittedKeys)
  return Object.entries(record)
    .filter(([key, value]) => !omitted.has(key) && value !== undefined && value !== null && value !== '')
    .slice(0, 8)
    .map(([key, value]) => {
      const isComplex = typeof value === 'object'
      return {
        label: key,
        value: isComplex ? JSON.stringify(value, null, 2) : String(value),
        multiline: isComplex || String(value).length > 90,
      }
    })
}

function isOxoRecipe(recipe?: RecipeRecord) {
  return Boolean(recipe?.id?.startsWith('Oxo-'))
}

function listText(value?: string[]) {
  const visible = (value ?? []).filter(Boolean)
  return visible.length ? visible.join(', ') : '-'
}

function hasMeaningfulIds(value?: string[]) {
  return Boolean(value?.some(Boolean))
}

function selectedMetricRecords(value: string | string[] | null | undefined = []) {
  const ids = Array.isArray(value) ? value : value ? [value] : []
  const selected = new Set(ids)
  return store.metrics.filter((metric) => selected.has(resourceId(metric)))
}

function selectedPromptTemplateRecords(value: string | string[] | null | undefined = []) {
  const ids = Array.isArray(value) ? value : value ? [value] : []
  const selected = new Set(ids)
  return store.promptTemplates.filter((template) => selected.has(recordId(template)))
}

function openResourcePicker(kind: ResourcePickerKind) {
  pickerKind.value = kind
  resourceSearch.value = ''
  expandedResourceId.value = ''
  resourcePickerOpen.value = true
}

function toggleExpandedResource(id: string) {
  expandedResourceId.value = expandedResourceId.value === id ? '' : id
}

function isPickerItemSelected(id: string) {
  if (pickerKind.value === 'datasets') return form.datasets.includes(id)
  if (pickerKind.value === 'metrics') return form.metric === id
  return form.prompt_template === id
}

function togglePickerSelection(id: string) {
  if (pickerKind.value === 'datasets') {
    if (form.datasets.includes(id)) {
      form.datasets = form.datasets.filter((datasetId) => datasetId !== id)
      return
    }
    form.datasets.push(id)
    return
  }
  if (pickerKind.value === 'metrics') {
    form.metric = form.metric === id ? null : id
    return
  }
  form.prompt_template = form.prompt_template === id ? null : id
}

function clearPickerSelection() {
  if (pickerKind.value === 'metrics') form.metric = null
  if (pickerKind.value === 'prompt_templates') form.prompt_template = null
}

function addTag(value: string) {
  const tag = value.trim()
  if (!tag || form.tags.includes(tag)) return
  form.tags.push(tag)
  tagDraft.value = ''
}

function removeTag(tag: string) {
  form.tags = form.tags.filter((item) => item !== tag)
}

function resetForm() {
  form.name = ''
  form.description = ''
  form.tags = []
  form.category = 'Others'
  form.datasets = []
  form.prompt_template = null
  form.metric = null
  form.grading_scale = { ...defaultGradingScale }
  editingId.value = ''
}

function openCreate() {
  resetForm()
  mode.value = 'form'
}

function openEdit(recipe: RecipeRecord) {
  if (!isOxoRecipe(recipe)) return
  editingId.value = recordId(recipe)
  form.name = recipe.name || 'Oxo '
  form.description = recipe.description || ''
  form.tags = [...(recipe.tags ?? [])]
  form.category = categoryOptions.includes(recipe.categories?.[0] ?? '') ? recipe.categories?.[0] ?? 'Others' : 'Others'
  form.datasets = [...(recipe.datasets ?? [])]
  form.prompt_template = recipe.prompt_templates?.find(Boolean) ?? null
  form.metric = recipe.metrics?.find(Boolean) ?? null
  form.grading_scale = { ...((recipe.grading_scale as Record<string, number[]> | undefined) ?? defaultGradingScale) }
  mode.value = 'form'
}

async function saveRecipe() {
  if (!canSubmit.value) {
    message.warning(translateSource('auto.cac548403930'))
    return
  }

  submitting.value = true
  try {
    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      tags: [...form.tags],
      categories: [form.category],
      datasets: [...form.datasets],
      prompt_templates: form.prompt_template ? [form.prompt_template] : [],
      metrics: form.metric ? [form.metric] : [],
      grading_scale: form.grading_scale,
    }
    if (editingId.value) {
      await moonshotApi.updateRecipe(editingId.value, payload)
      selectedRecipeId.value = editingId.value
      message.success(translateSource('auto.3094807841f0'))
    } else {
      const id = await moonshotApi.createRecipe(payload)
      selectedRecipeId.value = id
      message.success(translateSource('auto.c02f02f9913b'))
    }
    await store.loadOverview()
    mode.value = 'list'
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Save recipe failed')
  } finally {
    submitting.value = false
  }
}

async function deleteRecipe(recipe: RecipeRecord) {
  if (!isOxoRecipe(recipe)) return
  const id = recordId(recipe)
  if (!id) return
  try {
    await moonshotApi.deleteRecipe(id)
    selectedRecipeId.value = ''
    message.success(translateSource('auto.68bed00856d9'))
    await store.loadOverview()
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Delete recipe failed')
  }
}
</script>
