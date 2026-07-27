<template>
  <div class="cookbook-shell">
    <GlassPanel v-if="mode === 'list'" class="cookbook-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">{{ $t('auto.6f758f353ee3') }}</p>
          <h2>{{ $t('auto.3a27713963ce') }}</h2>
        </div>
        <n-button type="primary" round @click="openCreate">
          <template #icon><n-icon><AddOutline /></n-icon></template> {{ $t('auto.15a3a4d1c492') }} </n-button>
      </div>

      <div class="cookbook-list-grid">
        <section class="cookbook-list-column">
          <n-input v-model:value="search" clearable :placeholder="$t('auto.efc96fcf7df5')">
            <template #prefix><n-icon><SearchOutline /></n-icon></template>
          </n-input>

          <n-scrollbar v-if="filteredCookbooks.length" class="cookbook-list-scrollbar">
            <div class="cookbook-list">
              <button
                v-for="cookbook in filteredCookbooks"
                :key="recordId(cookbook)"
                class="cookbook-list-item"
                :class="{ active: recordId(cookbook) === recordId(activeCookbook) }"
                type="button"
                @click="selectedCookbookId = recordId(cookbook)"
              >
                <span class="row-icon"><n-icon size="22"><BookOutline /></n-icon></span>
                <span class="row-copy">
                  <strong>{{ cookbook.name || cookbook.id }}</strong>
                  <small>{{ cookbook.description || $t('auto.f354c94fcf63') }}</small>
                </span>
              </button>
            </div>
          </n-scrollbar>
          <n-empty v-else :description="$t('auto.896753ffbbf1')" />
        </section>

        <section class="cookbook-detail-column">
          <div v-if="activeCookbook" class="cookbook-detail-card">
            <div class="detail-title-row">
              <h3>
                <n-icon><BookOutline /></n-icon>
                {{ activeCookbook.name || activeCookbook.id }}
              </h3>
              <n-space>
                <n-button secondary round size="small" @click="openEdit(activeCookbook)">{{ $t('auto.5301648dcf6b') }}</n-button>
                <n-popconfirm
                  :positive-text="$t('common.delete')"
                  :negative-text="$t('auto.77dfd2135f4d')"
                  @positive-click="deleteCookbook(activeCookbook)"
                >
                  <template #trigger>
                    <n-button secondary round size="small" type="error">{{ $t('common.delete') }}</n-button>
                  </template> {{ $t('auto.92ff32d81b3d') }} </n-popconfirm>
              </n-space>
            </div>
            <p>{{ activeCookbook.description || $t('auto.f354c94fcf63') }}</p>
            <div class="detail-block">
              <strong>{{ $t('auto.9fb1092f32d4') }}</strong>
              <span>{{ cookbookRecipes(activeCookbook).join(', ') || $t('auto.c6264839dee6') }}</span>
            </div>
            <div class="detail-block">
              <strong>{{ $t('auto.5075485df694') }}</strong>
              <span>{{ cookbookStat(activeCookbook, ['num_of_prompts', 'num_prompts', 'prompts']) }}</span>
            </div>
            <div class="detail-block">
              <strong>{{ $t('auto.1543178e2a3a') }}</strong>
              <span>{{ cookbookStat(activeCookbook, ['num_of_datasets', 'num_datasets', 'datasets']) }}</span>
            </div>
          </div>
          <n-empty v-else :description="$t('auto.35d823a975a7')" />

          <div class="selected-box">
            <p class="eyebrow">{{ $t('auto.124332316fa4') }}</p>
            <strong>{{ activeCookbook ? activeCookbook.name || activeCookbook.id : $t('auto.cf20dd237505') }}</strong>
          </div>
        </section>
      </div>
    </GlassPanel>

    <GlassPanel v-else-if="mode === 'form'" class="cookbook-builder-panel">
      <div class="builder-header">
        <h2>{{ $t('auto.5e253f20ce65') }}</h2>
        <n-button circle quaternary @click="mode = 'list'">
          <template #icon><n-icon><CloseOutline /></n-icon></template>
        </n-button>
      </div>

      <div class="cookbook-form">
        <n-form label-placement="top">
          <n-form-item :label="$t('auto.709a23220f2c')">
            <n-input v-model:value="form.name" :placeholder="$t('auto.fd6558c1dc53')" />
          </n-form-item>
          <n-form-item :label="$t('auto.388de6fa3aa3')">
            <n-input
              v-model:value="form.description"
              type="textarea"
              :placeholder="$t('auto.ce9c524bbcba')"
              :autosize="{ minRows: 4, maxRows: 6 }"
            />
          </n-form-item>
        </n-form>

        <div class="selected-recipes-header">
          <strong>{{ $t('auto.1a44a637b807') }}</strong>
          <n-button secondary round @click="openSelector">
            <template #icon><n-icon><AddOutline /></n-icon></template> {{ $t('auto.8c6097271482') }} </n-button>
        </div>

        <div class="selected-recipes-box">
          <n-tag
            v-for="recipe in selectedRecipeRecords"
            :key="recordId(recipe)"
            closable
            round
            @close="removeRecipe(recordId(recipe))"
          >
            {{ recipe.name || recipe.id }}
          </n-tag>
          <span v-if="!selectedRecipeRecords.length">{{ $t('auto.68db9797d02d') }}</span>
        </div>

        <div class="builder-actions">
          <n-button
            type="primary"
            round
            size="large"
            :loading="submitting"
            :disabled="!form.name.trim() || !form.recipes.length"
            @click="createCookbook"
          >
            {{ editingId ? $t('auto.fcb655450ed8') : $t('auto.5e253f20ce65') }}
          </n-button>
        </div>
      </div>
    </GlassPanel>

    <GlassPanel v-else class="recipe-picker-panel">
      <div class="builder-header">
        <h2>{{ $t('auto.8b0cd7987141') }}</h2>
        <n-button circle quaternary @click="mode = 'form'">
          <template #icon><n-icon><CloseOutline /></n-icon></template>
        </n-button>
      </div>

      <n-input v-model:value="recipeSearch" clearable :placeholder="$t('auto.93095b69ed70')">
        <template #prefix><n-icon><SearchOutline /></n-icon></template>
      </n-input>

      <div class="recipe-picker-grid">
        <n-scrollbar class="recipe-list-scrollbar">
          <div class="recipe-list">
            <button
              v-for="recipe in filteredRecipes"
              :key="recordId(recipe)"
              class="recipe-row"
              :class="{ active: recordId(recipe) === recordId(activeRecipe) }"
              type="button"
              @click="selectedRecipeId = recordId(recipe)"
            >
              <n-checkbox
                class="row-checkbox"
                :checked="form.recipes.includes(recordId(recipe))"
                @click.stop
                @update:checked="toggleRecipe(recipe)"
              />
              <span class="row-icon"><n-icon size="22"><DocumentTextOutline /></n-icon></span>
              <span class="row-copy">
                <strong>{{ recipe.name || recipe.id }}</strong>
                <small>{{ recipe.description || $t('auto.f354c94fcf63') }}</small>
              </span>
            </button>
          </div>
        </n-scrollbar>

        <div class="recipe-detail-card">
          <template v-if="activeRecipe">
            <h3>
              <n-icon><DocumentTextOutline /></n-icon>
              {{ activeRecipe.name || activeRecipe.id }}
            </h3>
            <p>{{ activeRecipe.description || $t('auto.f354c94fcf63') }}</p>
            <div class="detail-block">
              <strong>{{ $t('auto.6ccb60071be8') }}</strong>
              <span>{{ listText(activeRecipe.categories) }}</span>
            </div>
            <div class="detail-block">
              <strong>{{ $t('auto.848eed0fbd54') }}</strong>
              <span>{{ listText(activeRecipe.tags) }}</span>
            </div>
            <div class="detail-block">
              <strong>{{ $t('auto.eea5311d723f') }}</strong>
              <span>{{ recipeStat(activeRecipe, ['num_of_prompts', 'num_prompts', 'prompts']) }}</span>
            </div>
            <div class="detail-block">
              <strong>{{ $t('auto.ddf6a1f0ce8c') }}</strong>
              <span>{{ listText(activeRecipe.metrics) }}</span>
            </div>
          </template>
          <n-empty v-else :description="$t('auto.975c3aae9574')" />
        </div>
      </div>

      <div class="picker-actions">
        <n-button round size="large" @click="mode = 'form'">{{ $t('auto.b52b36b7269f') }}</n-button>
        <n-button type="primary" round size="large" @click="addToCookbook">{{ $t('auto.e2bf3d866a84') }}</n-button>
      </div>
    </GlassPanel>

    <n-modal v-model:show="showSuccess" preset="card" class="cookbook-success-modal" :bordered="false">
      <template #header>{{ $t('auto.0b07c16bea74') }}</template>
      <p>{{ $t('auto.ae28e153fd42') }} {{ createdName }} {{ $t('auto.db460fdde780') }}</p>
      <template #footer>
        <n-space justify="end">
          <n-button round @click="createAnother">{{ $t('auto.6a56d007b2ba') }}</n-button>
          <n-button type="primary" round @click="viewCookbooks">{{ $t('auto.ad321c4bed3f') }}</n-button>
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
  BookOutline,
  CloseOutline,
  DocumentTextOutline,
  SearchOutline,
} from '@vicons/ionicons5'
import GlassPanel from '../components/GlassPanel.vue'
import { moonshotApi } from '../api/moonshot'
import { useMoonshotStore } from '../stores/moonshot'
import type { CookbookRecord, RecipeRecord } from '../types/moonshot'

type Mode = 'list' | 'form' | 'select'

const store = useMoonshotStore()
const message = useMessage()
const mode = ref<Mode>('list')
const search = ref('')
const recipeSearch = ref('')
const selectedCookbookId = ref('')
const selectedRecipeId = ref('')
const editingId = ref('')
const submitting = ref(false)
const showSuccess = ref(false)
const createdName = ref('')

const form = reactive({
  name: '',
  description: '',
  recipes: [] as string[],
})

const filteredCookbooks = computed(() => {
  const keyword = search.value.trim().toLowerCase()
  if (!keyword) return store.cookbooks
  return store.cookbooks.filter((cookbook) =>
    [cookbook.id, cookbook.name, cookbook.description].some((value) =>
      String(value ?? '').toLowerCase().includes(keyword),
    ),
  )
})

const activeCookbook = computed(() => {
  return (
    filteredCookbooks.value.find((cookbook) => recordId(cookbook) === selectedCookbookId.value) ??
    filteredCookbooks.value[0]
  )
})

const filteredRecipes = computed(() => {
  const keyword = recipeSearch.value.trim().toLowerCase()
  if (!keyword) return store.recipes
  return store.recipes.filter((recipe) =>
    [recipe.id, recipe.name, recipe.description, recipe.tags?.join(' ')].some((value) =>
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

const selectedRecipeRecords = computed(() => {
  const selected = new Set(form.recipes)
  return store.recipes.filter((recipe) => selected.has(recordId(recipe)))
})

function recordId(record?: { id?: string; name?: string }) {
  return String(record?.id || record?.name || '')
}

function resetForm() {
  form.name = ''
  form.description = ''
  form.recipes = []
  editingId.value = ''
}

function openCreate() {
  resetForm()
  mode.value = 'form'
}

function openEdit(cookbook: CookbookRecord) {
  editingId.value = recordId(cookbook)
  form.name = cookbook.name || cookbook.id || ''
  form.description = cookbook.description || ''
  form.recipes = [...cookbookRecipes(cookbook)]
  mode.value = 'form'
}

function openSelector() {
  selectedRecipeId.value = form.recipes[0] || recordId(filteredRecipes.value[0])
  mode.value = 'select'
}

function toggleRecipe(recipe: RecipeRecord) {
  const id = recordId(recipe)
  if (!id) return
  if (form.recipes.includes(id)) {
    removeRecipe(id)
    return
  }
  form.recipes.push(id)
}

function removeRecipe(id: string) {
  form.recipes = form.recipes.filter((recipeId) => recipeId !== id)
}

function addToCookbook() {
  mode.value = 'form'
}

async function createCookbook() {
  if (!form.name.trim()) {
    message.warning(translateSource('auto.9f175c08dc0b'))
    return
  }
  if (!form.recipes.length) {
    message.warning(translateSource('auto.543b3f3acf0a'))
    return
  }

  submitting.value = true
  try {
    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      recipes: [...form.recipes],
    }
    if (editingId.value) {
      await moonshotApi.updateCookbook(editingId.value, payload)
      message.success(translateSource('auto.4075650dc8e2'))
      selectedCookbookId.value = editingId.value
      mode.value = 'list'
    } else {
      await moonshotApi.createCookbook(payload)
      createdName.value = form.name.trim()
      showSuccess.value = true
    }
    createdName.value = form.name.trim()
    await store.loadOverview()
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Save cookbook failed')
  } finally {
    submitting.value = false
  }
}

async function deleteCookbook(cookbook: CookbookRecord) {
  const id = recordId(cookbook)
  if (!id) return
  try {
    await moonshotApi.deleteCookbook(id)
    message.success(translateSource('auto.903fd6456f44'))
    selectedCookbookId.value = ''
    await store.loadOverview()
  } catch (err) {
    message.error(err instanceof Error ? err.message : 'Delete cookbook failed')
  }
}

function createAnother() {
  showSuccess.value = false
  openCreate()
}

function viewCookbooks() {
  showSuccess.value = false
  mode.value = 'list'
}

function listText(value?: string[]) {
  return value?.length ? value.join(', ') : '-'
}

function recipeStat(recipe: RecipeRecord, keys: string[]) {
  const stats = recipe.stats ?? {}
  for (const key of keys) {
    const value = stats[key]
    if (Array.isArray(value)) return value.length
    if (value !== undefined && value !== null) return String(value)
  }
  return '-'
}

function cookbookStat(cookbook: CookbookRecord, keys: string[]) {
  const stats = cookbook.stats ?? {}
  for (const key of keys) {
    const value = stats[key]
    if (Array.isArray(value)) return value.length
    if (value !== undefined && value !== null) return String(value)
  }
  return '-'
}

function cookbookRecipes(cookbook: CookbookRecord) {
  return cookbook.recipes ?? []
}
</script>
