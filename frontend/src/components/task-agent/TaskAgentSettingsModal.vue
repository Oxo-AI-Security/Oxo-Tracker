<template>
  <n-modal
    :show="show"
    preset="card"
    class="task-agent-settings-modal"
    :title="$t('auto.d1e1e743383c')"
    :style="{ width: 'min(1180px, 94vw)', height: 'min(780px, 92vh)' }"
    :mask-closable="true"
    @update:show="$emit('update:show', $event)"
  >
    <NTabs v-model:value="tab" type="line" animated>
      <NTabPane name="skills" tab="Executor Skills">
        <div class="task-skill-layout">
          <aside class="task-skill-catalog">
            <div class="task-skill-tools">
              <n-input v-model:value="search" clearable :placeholder="$t('auto.502b0d6570a8')" />
              <n-select v-model:value="category" clearable :options="categoryOptions" :placeholder="$t('auto.060be00f4f26')" />
              <n-button
                type="primary"
                round
                :title="$t('auto.db3a7ea0fe76')"
                @click="newSkill"
              > {{ $t('auto.87098559f386') }} </n-button>
              <label class="task-skill-limit">
                <span>
                  <b>{{ $t('auto.2cad77d889a6') }}</b>
                  <small>{{ $t('auto.88d3288ae3c8') }}</small>
                </span>
                <n-input-number v-model:value="maxActiveSkillsModel" :min="1" :max="8" size="small" />
              </label>
              <small v-if="showingBundledTemplates" class="task-skill-fallback-note"> {{ $t('auto.daa6bfb5199e') }} </small>
            </div>
            <n-scrollbar class="task-skill-list">
              <button
                v-for="skill in filteredSkills"
                :key="skill.name"
                type="button"
                :class="{ active: skill.name === selectedSkillId, disabled: !skill.enabled }"
                @click="selectSkill(skill.name)"
              >
                <span class="task-skill-list-icon">{{ skill.name.slice(0, 1).toUpperCase() }}</span>
                <span class="task-skill-list-copy">
                  <span class="task-skill-list-title">
                    <strong>{{ skill.name }}</strong>
                    <i :class="skill.metadata.skill_type.toLowerCase()">{{ skill.metadata.skill_type }}</i>
                  </span>
                  <small>{{ skill.description }}</small>
                  <em>{{ skill.metadata.techniques.length }} {{ $t('auto.3dbcef9da296') }} {{ roleSummary(skill) }}</em>
                </span>
              </button>
            </n-scrollbar>
          </aside>

          <section class="task-skill-editor">
            <template v-if="draft">
              <header class="task-skill-hero">
                <span class="task-skill-hero-icon">{{ draft.name.slice(0, 1).toUpperCase() }}</span>
                <div class="task-skill-hero-copy">
                  <div class="task-skill-hero-label">
                    <span>{{ draft.metadata.skill_type }} SKILL</span>
                    <i>v{{ draft.metadata.version }}</i>
                    <i>{{ draft.metadata.stage }}</i>
                  </div>
                  <h3>{{ draft.name || $t('auto.1dac688e44c5') }}</h3>
                  <p>{{ draft.description || $t('auto.29e3f4448481') }}</p>
                </div>
                <div class="task-skill-hero-status">
                  <span :class="{ enabled: draft.enabled }">
                    <i />
                    {{ draft.enabled ? 'Active' : 'Disabled' }}
                  </span>
                  <small>{{ draft.metadata.techniques.length }} {{ $t('auto.d0975e67a95c') }}</small>
                </div>
              </header>

              <n-scrollbar class="task-skill-editor-scroll">
                <div class="task-skill-editor-content">
                  <section class="task-skill-section task-skill-basics">
                    <header class="task-skill-section-heading">
                      <div>
                        <small>{{ $t('auto.d58214ccdde5') }}</small>
                        <h4>{{ $t('auto.bf1be2b7ad07') }}</h4>
                      </div>
                      <p>{{ $t('auto.0c22b09aa9c7') }}</p>
                    </header>
                    <div class="task-skill-editor-grid">
                      <n-form-item :label="$t('auto.828f421d095e')" class="task-skill-id-field">
                        <n-input v-model:value="draft.name" :disabled="selectedSkillIsPersisted" placeholder="lowercase-hyphen-id" />
                      </n-form-item>
                      <n-form-item :label="$t('auto.2da600bf9404')">
                        <n-input v-model:value="draft.metadata.version" placeholder="1.0" />
                      </n-form-item>
                      <n-form-item :label="$t('auto.31891d5149ae')">
                        <n-select
                          v-model:value="draft.metadata.skill_type"
                          :options="[
                            { label: 'Domain', value: 'DOMAIN' },
                            { label: 'Auxiliary', value: 'AUXILIARY' },
                          ]"
                        />
                      </n-form-item>
                      <n-form-item :label="$t('auto.a3c686e711e4')" class="task-skill-wide-field">
                        <n-input v-model:value="draft.metadata.category" />
                      </n-form-item>
                      <n-form-item :label="$t('auto.ca6d0e3aaa7d')" class="task-skill-wide-field">
                        <n-input v-model:value="draft.metadata.stage" />
                      </n-form-item>
                    </div>
                    <n-form-item :label="$t('auto.55f8ebc805e6')" class="task-skill-description-field">
                      <n-input v-model:value="draft.description" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" />
                    </n-form-item>
                  </section>

                  <section class="task-skill-section task-skill-composition">
                    <header class="task-skill-section-heading">
                      <div>
                        <small>{{ $t('auto.e86095ada61d') }}</small>
                        <h4>{{ $t('auto.29e92d0920ff') }}</h4>
                      </div>
                      <p>{{ $t('auto.4c28391b0f7d') }}</p>
                    </header>
                    <div class="task-skill-composition-grid">
                      <div class="task-skill-role-panel">
                        <span class="task-skill-panel-label">{{ $t('auto.b940470029b5') }}</span>
                        <label :class="{ selected: draft.metadata.allow_primary }">
                          <n-checkbox v-model:checked="draft.metadata.allow_primary" />
                          <span>
                            <strong>{{ $t('auto.a9a96ec01949') }}</strong>
                            <small>{{ $t('auto.6f59924e30f7') }}</small>
                          </span>
                        </label>
                        <label :class="{ selected: draft.metadata.allow_supporting }">
                          <n-checkbox v-model:checked="draft.metadata.allow_supporting" />
                          <span>
                            <strong>{{ $t('auto.8c846b6abbf0') }}</strong>
                            <small>{{ $t('auto.76f985f3e3e7') }}</small>
                          </span>
                        </label>
                      </div>
                      <div class="task-skill-relations">
                        <div>
                          <span class="task-skill-panel-label">{{ $t('auto.bbd40532703b') }}</span>
                          <p>{{ draft.metadata.composable_with.join(', ') || $t('auto.cfac60d645b8') }}</p>
                        </div>
                        <div>
                          <span class="task-skill-panel-label">{{ $t('auto.1603c237467b') }}</span>
                          <p>{{ draft.metadata.conflicts_with.join(', ') || $t('auto.ecf5add00af7') }}</p>
                        </div>
                      </div>
                    </div>
                  </section>

                  <section class="task-skill-section task-skill-techniques">
                    <header class="task-skill-section-heading">
                      <div>
                        <small>{{ $t('auto.a287f8f178d7') }}</small>
                        <h4>{{ draft.metadata.techniques.length }} {{ $t('auto.0b4b058a048f') }}</h4>
                      </div>
                      <p>{{ $t('auto.268c2e1fa104') }}</p>
                    </header>
                    <div class="task-technique-list">
                      <article
                        v-for="(technique, techniqueIndex) in draft.metadata.techniques"
                        :key="technique.technique_id"
                      >
                        <span class="task-technique-index">{{ String(techniqueIndex + 1).padStart(2, '0') }}</span>
                        <div>
                          <span class="task-technique-stage">{{ technique.stage }}</span>
                          <strong>{{ technique.technique_id }}</strong>
                          <p>{{ technique.summary }}</p>
                        </div>
                      </article>
                    </div>
                  </section>

                  <section class="task-skill-section task-skill-manual">
                    <header class="task-skill-section-heading">
                      <div>
                        <small>{{ $t('auto.019c5e96034f') }}</small>
                        <h4>SKILL.md</h4>
                      </div>
                      <p>{{ $t('auto.9013e889a1ee') }}</p>
                    </header>
                    <n-form-item class="task-skill-body-field">
                      <n-input
                        v-model:value="draft.body"
                        type="textarea"
                        class="task-skill-body"
                        :autosize="false"
                        :rows="14"
                        :placeholder="$t('auto.8d1851851d3e')"
                      />
                    </n-form-item>
                  </section>

                  <div v-if="validation" class="task-skill-validation" :class="{ invalid: !validation.valid }">
                    <strong>{{ validation.valid ? $t('auto.d6ddaba3c8c1') : $t('auto.08b7b9da9ce6') }}</strong>
                    <span v-for="item in validation.errors" :key="item">{{ item }}</span>
                    <span v-for="item in validation.warnings" :key="item">{{ item }}</span>
                  </div>
                </div>
              </n-scrollbar>

              <div class="task-skill-actions">
                <div class="task-skill-enabled-control">
                  <n-switch v-model:value="draft.enabled" />
                  <div>
                    <strong>{{ draft.enabled ? $t('auto.b7b93b80f300') : $t('auto.06754b1f03ab') }}</strong>
                    <small>{{ draft.enabled ? $t('auto.a763e64e10cb') : $t('auto.80386df61f14') }}</small>
                  </div>
                </div>
                <span />
                <n-button round :loading="saving" @click="validateDraft">{{ $t('auto.6752f198b564') }}</n-button>
                <n-button v-if="selectedSkillId" round @click="duplicateSelected">
                  {{ selectedSkillIsPersisted ? 'Duplicate' : $t('auto.94960788c935') }}
                </n-button>
                <n-popconfirm
                  v-if="selectedSkillIsPersisted"
                  :positive-text="$t('common.delete')"
                  :negative-text="$t('auto.77dfd2135f4d')"
                  @positive-click="deleteSelected"
                >
                  <template #trigger><n-button round type="error" secondary>{{ $t('common.delete') }}</n-button></template>
                  {{ $t('common.delete') }} {{ selectedSkillId }}{{ $t('auto.0a8d7b08e038') }} </n-popconfirm>
                <n-button type="primary" round :loading="saving" @click="saveDraft">
                  {{ selectedSkillIsTemplate ? $t('auto.a1a02fe7db3b') : $t('auto.a2120fec36f6') }}
                </n-button>
              </div>
            </template>
            <n-empty v-else :description="$t('auto.4b205eb7eaa1')" />
          </section>
        </div>
      </NTabPane>
      <NTabPane
        v-if="false"
        name="parallel"
        tab="Parallel Search"
      >
        <section class="parallel-search-shell">
          <header class="parallel-search-hero">
            <span class="parallel-search-icon">⑂</span>
            <div>
              <small>ISOLATED CHILD CHATS</small>
              <h3>并行子聊天</h3>
              <p>
                Attack Agent 会在主路线受阻且存在多个高价值候选策略时，
                创建上下文隔离的临时子聊天并行尝试。
              </p>
            </div>
            <span class="parallel-search-state">
              {{ maxChildChatsModel > 0 ? 'Enabled' : 'Disabled' }}
            </span>
          </header>

          <div class="parallel-search-content">
            <section class="parallel-search-limit">
              <div>
                <small>CONCURRENCY CAP</small>
                <h4>最大临时子聊天</h4>
                <p>
                  这是并发上限，不是每次固定创建数量。Planner 会根据候选策略、
                  历史进展和重复程度决定是否分叉。设置为 0 可关闭。
                </p>
              </div>
              <n-input-number
                v-model:value="maxChildChatsModel"
                :min="0"
                :max="10"
                size="large"
              />
            </section>

            <div class="parallel-search-rules">
              <article>
                <span>01</span>
                <div>
                  <strong>独立上下文</strong>
                  <p>每个子聊天使用独立 Target runner，不会污染主聊天或兄弟分支。</p>
                </div>
              </article>
              <article>
                <span>02</span>
                <div>
                  <strong>智能分叉</strong>
                  <p>只为评分较高且彼此不同的候选策略创建分支，不机械占满上限。</p>
                </div>
              </article>
              <article>
                <span>03</span>
                <div>
                  <strong>成功采纳</strong>
                  <p>成功轨迹写回主任务并标记来源；其他临时子聊天随后自动清理。</p>
                </div>
              </article>
              <article>
                <span>04</span>
                <div>
                  <strong>失败回收</strong>
                  <p>未达到目标的子聊天和远端 runner 自动删除，主路线继续运行。</p>
                </div>
              </article>
            </div>

            <aside class="parallel-search-note">
              <strong>成本提示</strong>
              <span>
                并发可以缩短等待时间，但模型请求与 Token 使用量会随实际创建的子聊天增加。
              </span>
            </aside>
          </div>
        </section>
      </NTabPane>
      <NTabPane name="records" tab="Goal Records">
        <section class="goal-memory-shell">
          <header class="goal-memory-hero">
            <div class="goal-memory-hero-icon">✓</div>
            <div class="goal-memory-hero-copy">
              <small>SUCCESSFUL TRAJECTORY MEMORY</small>
              <h3>Goal Records</h3>
              <p>
                Proven inputs and outputs from this target are reused as
                strategy evidence in future Attack Agent runs.
              </p>
            </div>
            <div class="goal-memory-target">
              <span>CURRENT TARGET</span>
              <strong>{{ targetDisplay }}</strong>
              <small>{{ successMemories.length }} successful record{{ successMemories.length === 1 ? '' : 's' }}</small>
            </div>
            <n-button
              circle
              secondary
              :loading="memoriesLoading"
              title="Refresh records"
              @click="loadSuccessMemories"
            >
              ↻
            </n-button>
          </header>

          <n-spin :show="memoriesLoading" class="goal-memory-loading">
            <n-scrollbar class="goal-memory-scroll">
              <div v-if="successMemories.length" class="goal-memory-list">
                <details
                  v-for="memory in successMemories"
                  :key="memory.memory_id"
                  class="goal-memory-card"
                >
                  <summary>
                    <span class="goal-memory-check">✓</span>
                    <div>
                      <small>GOAL ACHIEVED</small>
                      <h4>{{ memory.goal }}</h4>
                    </div>
                    <div class="goal-memory-meta">
                      <span>{{ memory.round_count }} rounds</span>
                      <span v-if="memory.technique">{{ memory.technique }}</span>
                      <time>{{ formatMemoryTime(memory.created_at) }}</time>
                    </div>
                    <n-popconfirm
                      positive-text="Delete"
                      negative-text="Cancel"
                      @positive-click="deleteSuccessMemory(memory.memory_id)"
                    >
                      <template #trigger>
                        <n-button
                          circle
                          quaternary
                          type="error"
                          :loading="deletingMemoryId === memory.memory_id"
                          title="Delete this record"
                          @click.stop
                        >
                          ×
                        </n-button>
                      </template>
                      Delete this successful goal record?
                    </n-popconfirm>
                    <span class="goal-memory-chevron">⌄</span>
                  </summary>

                  <div class="goal-memory-io">
                    <section>
                      <span><i>↑</i> SUCCESSFUL INPUT</span>
                      <p>{{ memory.final_input }}</p>
                    </section>
                    <section>
                      <span><i>↓</i> TARGET OUTPUT</span>
                      <p>{{ memory.final_output }}</p>
                    </section>
                  </div>
                </details>
              </div>
              <div v-else class="goal-memory-empty">
                <span>✦</span>
                <h4>No successful records yet</h4>
                <p>
                  When Attack Agent reaches a goal on this target, its decisive
                  input and output will appear here automatically.
                </p>
              </div>
            </n-scrollbar>
          </n-spin>
        </section>
      </NTabPane>
      <NTabPane name="workflow" tab="Workflow">
        <TaskAgentWorkflowGraph
          :definition="workflow"
          :current-node="currentNode"
          :current-route="currentRoute"
        />
      </NTabPane>
    </NTabs>
  </n-modal>
</template>

<script setup lang="ts">
import { translateSource } from '../../i18n'

import { computed, ref, watch } from 'vue'
import { NTabPane, NTabs, useMessage } from 'naive-ui'
import {
  taskAgentsApi,
  type ExecutorSkill,
  type ExecutorSkillCatalogItem,
  type TaskSuccessMemory,
  type WorkflowDefinition,
} from '../../api/taskAgents'
import {
  getBundledExecutorSkill,
  listBundledExecutorSkills,
} from '../../data/bundledExecutorSkills'
import { parseCompactExecutorTechniques } from '../../utils/executorSkillMarkdown'
import TaskAgentWorkflowGraph from './TaskAgentWorkflowGraph.vue'

const props = withDefaults(
  defineProps<{
    show: boolean
    currentNode?: string | null
    currentRoute?: string | null
    maxActiveSkills?: number
    maxChildChats?: number
    targetKey?: string
    runnerId?: string
    targetLabel?: string
  }>(),
  {
    currentNode: null,
    currentRoute: null,
    maxActiveSkills: 3,
    maxChildChats: 3,
    targetKey: '',
    runnerId: '',
    targetLabel: '',
  },
)

const emit = defineEmits<{
  'update:show': [value: boolean]
  'update:maxActiveSkills': [value: number]
  'update:maxChildChats': [value: number]
}>()

const message = useMessage()
const tab = ref('skills')
const search = ref('')
const category = ref<string | null>(null)
const skills = ref<ExecutorSkillCatalogItem[]>([])
const workflow = ref<WorkflowDefinition | null>(null)
const selectedSkillId = ref('')
const draft = ref<ExecutorSkill | null>(null)
const saving = ref(false)
const validation = ref<{ valid: boolean; errors: string[]; warnings: string[] } | null>(null)
const showingBundledTemplates = ref(false)
const successMemories = ref<TaskSuccessMemory[]>([])
const memoriesLoading = ref(false)
const deletingMemoryId = ref('')
const persistedSkillIds = ref<Set<string>>(new Set())
const selectedSkillIsPersisted = computed(
  () => Boolean(selectedSkillId.value) && persistedSkillIds.value.has(selectedSkillId.value),
)
const selectedSkillIsTemplate = computed(
  () => Boolean(selectedSkillId.value) && !selectedSkillIsPersisted.value,
)
const maxActiveSkillsModel = computed({
  get: () => props.maxActiveSkills,
  set: (value: number | null) => {
    if (value == null || !Number.isFinite(value)) return
    emit('update:maxActiveSkills', Math.min(8, Math.max(1, Math.round(value))))
  },
})
const maxChildChatsModel = computed({
  get: () => props.maxChildChats,
  set: (value: number | null) => {
    if (value == null || !Number.isFinite(value)) return
    emit('update:maxChildChats', Math.min(10, Math.max(0, Math.round(value))))
  },
})
const categoryOptions = computed(() =>
  [...new Set(skills.value.map((skill) => skill.metadata.category))].map((value) => ({ label: value, value })),
)
const targetDisplay = computed(
  () => props.targetLabel || compactTarget(props.targetKey) || 'No target selected',
)

const filteredSkills = computed(() => {
  const query = search.value.trim().toLowerCase()
  return skills.value.filter(
    (skill) =>
      (!category.value || skill.metadata.category === category.value) &&
      (!query || `${skill.name} ${skill.description}`.toLowerCase().includes(query)),
  )
})

function roleSummary(skill: ExecutorSkillCatalogItem) {
  if (skill.metadata.allow_primary && skill.metadata.allow_supporting) return 'Primary / Supporting'
  if (skill.metadata.allow_primary) return 'Primary'
  return 'Supporting'
}

watch(
  () => props.show,
  (shown) => {
    if (shown) void load()
  },
)

watch(
  () => props.targetKey,
  () => {
    successMemories.value = []
    if (props.show && tab.value === 'records') void loadSuccessMemories()
  },
)

watch(tab, (nextTab) => {
  if (nextTab === 'records') void loadSuccessMemories()
})

watch(
  () => draft.value?.body,
  (body) => {
    if (!draft.value || !body) return
    const techniques = parseCompactExecutorTechniques(body)
    if (techniques.length) draft.value.metadata.techniques = techniques
  },
)

async function load() {
  try {
    const [remoteSkills, remoteWorkflow] = await Promise.all([
      taskAgentsApi.listSkills(),
      taskAgentsApi.getWorkflow(),
    ])
    persistedSkillIds.value = new Set(remoteSkills.map((skill) => skill.name))
    showingBundledTemplates.value = remoteSkills.length === 0
    skills.value = remoteSkills.length
      ? remoteSkills
      : listBundledExecutorSkills()
    workflow.value = remoteWorkflow
    void loadSuccessMemories()
    const nextSkillId = skills.value.some((skill) => skill.name === selectedSkillId.value)
      ? selectedSkillId.value
      : skills.value[0]?.name
    if (nextSkillId) await selectSkill(nextSkillId)
    else {
      selectedSkillId.value = ''
      draft.value = null
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Unable to load Attack Agent settings')
  }
}

async function loadSuccessMemories() {
  if (!props.targetKey) {
    successMemories.value = []
    return
  }
  memoriesLoading.value = true
  try {
    successMemories.value = await taskAgentsApi.listSuccessMemories({
      target_key: props.targetKey,
      runner_id: props.runnerId || undefined,
      limit: 100,
    })
  } catch (error) {
    message.error(
      error instanceof Error ? error.message : 'Unable to load goal records',
    )
  } finally {
    memoriesLoading.value = false
  }
}

async function deleteSuccessMemory(memoryId: string) {
  deletingMemoryId.value = memoryId
  try {
    await taskAgentsApi.deleteSuccessMemory(memoryId)
    successMemories.value = successMemories.value.filter(
      (memory) => memory.memory_id !== memoryId,
    )
    message.success('Goal record deleted')
  } catch (error) {
    message.error(
      error instanceof Error ? error.message : 'Unable to delete goal record',
    )
  } finally {
    deletingMemoryId.value = ''
  }
}

function compactTarget(value: string) {
  try {
    const url = new URL(value)
    return `${url.host}${url.pathname === '/' ? '' : url.pathname}`
  } catch {
    return value
  }
}

function formatMemoryTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

async function selectSkill(skillId: string) {
  selectedSkillId.value = skillId
  validation.value = null
  if (!persistedSkillIds.value.has(skillId)) {
    draft.value = getBundledExecutorSkill(skillId)
    return
  }
  try {
    draft.value = await taskAgentsApi.getSkill(skillId)
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Unable to load skill')
  }
}

function newSkill() {
  selectedSkillId.value = ''
  validation.value = null
  draft.value = {
    name: '',
    description: '',
    compatibility: 'Prompt-only skill. No scripts or executable actions.',
    metadata: {
      version: '1.0',
      category: 'custom',
      stage: 'exploration',
      risk_level: 'low',
      skill_type: 'DOMAIN',
      techniques: [
        {
          technique_id: 'safe-baseline',
          name: 'Safe baseline',
          summary: 'Establish one safe, attributable baseline.',
          stage: 'baseline',
        },
      ],
      composable_with: [],
      conflicts_with: [],
      allow_primary: true,
      allow_supporting: false,
    },
    enabled: true,
    body: [
      '## Purpose',
      '',
      'Describe what this Skill helps the Executor accomplish.',
      '',
      '## Applicable Goals',
      '',
      '- Describe a goal that should select this Skill.',
      '',
      '## When to Use',
      '',
      'Describe the conditions in which the Executor should apply it.',
      '',
      '## Techniques',
      '',
      '### safe-baseline',
      'Name: Safe baseline',
      'Stage: baseline',
      'Summary: Establish one attributable baseline before changing a variable.',
      '',
    ].join('\n'),
  }
}

async function validateDraft() {
  if (!draft.value) return false
  saving.value = true
  try {
    const result = await taskAgentsApi.validateSkill(draft.value)
    validation.value = result
    if (result.valid && result.skill) draft.value = result.skill
    return result.valid
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Skill validation failed')
    return false
  } finally {
    saving.value = false
  }
}

async function saveDraft() {
  if (!draft.value || !(await validateDraft())) return
  saving.value = true
  try {
    const saved = selectedSkillIsPersisted.value
      ? await taskAgentsApi.updateSkill(selectedSkillId.value, draft.value)
      : await taskAgentsApi.createSkill(draft.value)
    message.success(`${saved.name} saved`)
    selectedSkillId.value = saved.name
    await load()
    await selectSkill(saved.name)
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Unable to save skill')
  } finally {
    saving.value = false
  }
}

async function duplicateSelected() {
  if (!selectedSkillId.value || !draft.value) return
  const newName = `${selectedSkillId.value}-copy`
  try {
    const created = selectedSkillIsPersisted.value
      ? await taskAgentsApi.duplicateSkill(selectedSkillId.value, newName)
      : await taskAgentsApi.createSkill({
          ...draft.value,
          name: newName,
          metadata: {
            ...draft.value.metadata,
            version: '1.0',
            techniques: draft.value.metadata.techniques.map((technique) => ({ ...technique })),
            composable_with: [...draft.value.metadata.composable_with],
            conflicts_with: [...draft.value.metadata.conflicts_with],
          },
        })
    message.success(`${created.name} created`)
    await load()
    await selectSkill(created.name)
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Unable to duplicate skill')
  }
}

async function deleteSelected() {
  if (!selectedSkillId.value || !selectedSkillIsPersisted.value) return
  try {
    await taskAgentsApi.deleteSkill(selectedSkillId.value)
    message.success(translateSource('auto.70e73523b47e'))
    selectedSkillId.value = ''
    draft.value = null
    await load()
  } catch (error) {
    message.error(error instanceof Error ? error.message : 'Unable to delete skill')
  }
}
</script>

<style scoped>
.task-skill-layout { display: grid; grid-template-columns: minmax(280px, .78fr) minmax(0, 1.7fr); gap: 18px; height: min(620px, calc(92vh - 142px)); min-height: 0; overflow: hidden; }
.task-skill-catalog { display: flex; min-height: 0; flex-direction: column; border: 1px solid rgba(139,92,246,.16); border-radius: 17px; overflow: hidden; background: linear-gradient(180deg,rgba(250,248,255,.96),rgba(247,250,255,.92)); box-shadow: inset 0 1px 0 rgba(255,255,255,.9); }
.task-skill-tools { display: grid; grid-template-columns: 1fr 140px; gap: 8px; padding: 12px; border-bottom: 1px solid rgba(139,92,246,.12); background: rgba(255,255,255,.72); }
.task-skill-tools > button { grid-column: 1 / -1; }
.task-skill-limit { display: flex; grid-column: 1 / -1; align-items: center; justify-content: space-between; gap: 10px; padding: 9px 10px; color: #334155; background: rgba(245,243,255,.8); border: 1px solid rgba(139,92,246,.12); border-radius: 11px; }
.task-skill-limit > span { display: grid; gap: 1px; }
.task-skill-limit b { font-size: 10px; }
.task-skill-limit small { color: #7c8294; font-size: 8px; }
.task-skill-limit :deep(.n-input-number) { width: 72px; }
.task-skill-fallback-note { grid-column: 1 / -1; padding: 0 3px; color: #b45309; font-size: 8px; font-weight: 800; letter-spacing: .02em; }
.task-skill-list { flex: 1; min-height: 0; }
.task-skill-list button { position: relative; width: calc(100% - 12px); display: grid; grid-template-columns: 34px minmax(0,1fr); gap: 10px; align-items: start; margin: 6px; text-align: left; border: 1px solid transparent; background: rgba(255,255,255,.58); padding: 11px; cursor: pointer; color: inherit; border-radius: 13px; transition: transform .16s ease,background .16s ease,border-color .16s ease,box-shadow .16s ease; }
.task-skill-list button::after { position: absolute; top: 12px; right: 10px; width: 6px; height: 6px; content: ""; background: #22c55e; border: 2px solid #fff; border-radius: 50%; box-shadow: 0 0 0 1px rgba(34,197,94,.16); }
.task-skill-list button.disabled::after { background: #94a3b8; }
.task-skill-list button:hover { background: #fff; border-color: rgba(139,92,246,.18); transform: translateY(-1px); box-shadow: 0 8px 18px rgba(91,72,153,.08); }
.task-skill-list button.active { background: linear-gradient(135deg,#f4efff,#f5f9ff); border-color: rgba(124,58,237,.28); box-shadow: 0 9px 22px rgba(109,40,217,.11),inset 3px 0 0 #7c3aed; }
.task-skill-list-icon { display: grid; width: 32px; height: 32px; place-items: center; color: #6d28d9; font-size: 11px; font-weight: 900; background: linear-gradient(135deg,#ede9fe,#e7f3ff); border: 1px solid rgba(139,92,246,.16); border-radius: 10px; }
.task-skill-list button.active .task-skill-list-icon { color: #fff; background: linear-gradient(135deg,#8b5cf6,#6366f1); box-shadow: 0 6px 14px rgba(109,40,217,.2); }
.task-skill-list-copy { display: grid; min-width: 0; gap: 4px; padding-right: 6px; }
.task-skill-list-title { display: flex; min-width: 0; gap: 7px; align-items: center; }
.task-skill-list-title strong { min-width: 0; }
.task-skill-list-title i { flex: 0 0 auto; padding: 2px 5px; color: #2563eb; font-size: 7px; font-style: normal; font-weight: 900; background: #eff6ff; border-radius: 999px; }
.task-skill-list-title i.auxiliary { color: #7c3aed; background: #f5f3ff; }
.task-skill-list button strong { overflow: hidden; color: #334155; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.task-skill-list button small { display: -webkit-box; overflow: hidden; color: #64748b; font-size: 10px; line-height: 1.4; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.task-skill-list button em { overflow: hidden; color: #8b5cf6; font-size: 8px; font-style: normal; font-weight: 800; text-overflow: ellipsis; white-space: nowrap; }
.task-skill-editor { display: grid; grid-template-rows: auto minmax(0,1fr) auto; min-width: 0; min-height: 0; overflow: hidden; border: 1px solid rgba(139,92,246,.14); border-radius: 17px; background: #f8faff; box-shadow: 0 14px 34px rgba(63,46,107,.06); }
.task-skill-hero { display: grid; grid-template-columns: 42px minmax(0,1fr) auto; gap: 13px; align-items: center; padding: 14px 16px; border-bottom: 1px solid rgba(139,92,246,.12); background: linear-gradient(115deg,rgba(255,255,255,.98),rgba(248,245,255,.96) 55%,rgba(240,249,255,.95)); }
.task-skill-hero-icon { display: grid; width: 42px; height: 42px; place-items: center; color: #fff; font-size: 15px; font-weight: 900; background: linear-gradient(145deg,#8b5cf6,#6366f1); border-radius: 13px; box-shadow: 0 8px 18px rgba(109,40,217,.22); }
.task-skill-hero-copy { min-width: 0; }
.task-skill-hero-label { display: flex; gap: 6px; align-items: center; margin-bottom: 2px; }
.task-skill-hero-label span { color: #7c3aed; font-size: 8px; font-weight: 900; letter-spacing: .1em; }
.task-skill-hero-label i { padding: 2px 6px; color: #64748b; font-size: 8px; font-style: normal; font-weight: 800; background: rgba(255,255,255,.78); border: 1px solid rgba(148,163,184,.18); border-radius: 999px; }
.task-skill-hero h3 { overflow: hidden; margin: 0; color: #172033; font-size: 16px; line-height: 1.35; text-overflow: ellipsis; white-space: nowrap; }
.task-skill-hero p { overflow: hidden; margin: 3px 0 0; color: #64748b; font-size: 10px; line-height: 1.4; text-overflow: ellipsis; white-space: nowrap; }
.task-skill-hero-status { display: grid; justify-items: end; gap: 4px; }
.task-skill-hero-status > span { display: flex; gap: 6px; align-items: center; padding: 5px 9px; color: #64748b; font-size: 9px; font-weight: 900; background: #f8fafc; border: 1px solid rgba(148,163,184,.2); border-radius: 999px; }
.task-skill-hero-status > span i { width: 6px; height: 6px; background: #94a3b8; border-radius: 50%; }
.task-skill-hero-status > span.enabled { color: #047857; background: #ecfdf5; border-color: #a7f3d0; }
.task-skill-hero-status > span.enabled i { background: #22c55e; box-shadow: 0 0 0 3px rgba(34,197,94,.1); }
.task-skill-hero-status small { color: #94a3b8; font-size: 9px; }
.task-skill-editor-scroll { min-height: 0; }
.task-skill-editor-content { display: grid; gap: 12px; padding: 14px 16px 22px; }
.task-skill-section { padding: 14px; background: rgba(255,255,255,.92); border: 1px solid rgba(148,163,184,.16); border-radius: 14px; box-shadow: 0 5px 16px rgba(57,48,94,.035); }
.task-skill-section-heading { display: flex; gap: 18px; align-items: end; justify-content: space-between; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid rgba(148,163,184,.13); }
.task-skill-section-heading > div { display: grid; gap: 2px; }
.task-skill-section-heading small, .task-skill-panel-label { color: #7c3aed; font-size: 8px; font-weight: 900; letter-spacing: .09em; }
.task-skill-section-heading h4 { margin: 0; color: #27364f; font-size: 13px; line-height: 1.3; }
.task-skill-section-heading > p { max-width: 360px; margin: 0; color: #94a3b8; font-size: 9px; text-align: right; }
.task-skill-editor-grid { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 10px; }
.task-skill-editor-grid .task-skill-id-field { grid-column: span 2; }
.task-skill-editor-grid .task-skill-wide-field { grid-column: span 2; }
.task-skill-description-field { margin-bottom: 0; }
.task-skill-editor :deep(.n-form-item-label) { color: #475569; font-size: 10px; font-weight: 800; }
.task-skill-editor :deep(.n-form-item) { margin-bottom: 10px; }
.task-skill-editor :deep(.n-input), .task-skill-editor :deep(.n-base-selection) { --n-border-radius: 9px !important; }
.parallel-search-shell { height: min(620px, calc(92vh - 142px)); overflow: auto; border: 1px solid rgba(139,92,246,.15); border-radius: 18px; background: linear-gradient(145deg,#fbfaff,#f5f9ff); }
.parallel-search-hero { display: grid; grid-template-columns: 54px minmax(0,1fr) auto; gap: 16px; align-items: center; padding: 24px; border-bottom: 1px solid rgba(139,92,246,.12); background: linear-gradient(115deg,#fff,rgba(245,243,255,.9),rgba(239,249,255,.86)); }
.parallel-search-icon { display: grid; width: 54px; height: 54px; place-items: center; color: #fff; font-size: 24px; font-weight: 900; background: linear-gradient(145deg,#8b5cf6,#4f46e5); border-radius: 17px; box-shadow: 0 12px 24px rgba(109,40,217,.2); }
.parallel-search-hero small,.parallel-search-limit small { color: #7c3aed; font-size: 9px; font-weight: 900; letter-spacing: .11em; }
.parallel-search-hero h3 { margin: 3px 0; color: #172033; font-size: 21px; }
.parallel-search-hero p { max-width: 680px; margin: 0; color: #64748b; font-size: 12px; line-height: 1.6; }
.parallel-search-state { padding: 7px 11px; color: #047857; font-size: 10px; font-weight: 900; background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 999px; }
.parallel-search-content { display: grid; gap: 16px; padding: 22px; }
.parallel-search-limit { display: grid; grid-template-columns: minmax(0,1fr) 130px; gap: 24px; align-items: center; padding: 20px; background: rgba(255,255,255,.9); border: 1px solid rgba(139,92,246,.14); border-radius: 16px; box-shadow: 0 9px 22px rgba(70,55,120,.05); }
.parallel-search-limit h4 { margin: 4px 0; color: #27364f; font-size: 15px; }
.parallel-search-limit p { max-width: 720px; margin: 0; color: #64748b; font-size: 11px; line-height: 1.6; }
.parallel-search-limit :deep(.n-input-number) { width: 130px; }
.parallel-search-rules { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 12px; }
.parallel-search-rules article { display: grid; grid-template-columns: 38px minmax(0,1fr); gap: 12px; padding: 17px; background: rgba(255,255,255,.78); border: 1px solid rgba(148,163,184,.15); border-radius: 14px; }
.parallel-search-rules article > span { display: grid; width: 36px; height: 36px; place-items: center; color: #7c3aed; font-size: 10px; font-weight: 900; background: #f5f3ff; border-radius: 11px; }
.parallel-search-rules strong { color: #334155; font-size: 12px; }
.parallel-search-rules p { margin: 5px 0 0; color: #64748b; font-size: 10px; line-height: 1.55; }
.parallel-search-note { display: flex; gap: 10px; align-items: center; padding: 13px 15px; color: #92400e; font-size: 10px; background: #fffbeb; border: 1px solid #fde68a; border-radius: 12px; }
.parallel-search-note strong { flex: 0 0 auto; }
.task-skill-composition-grid { display: grid; grid-template-columns: minmax(250px,.85fr) minmax(0,1.15fr); gap: 12px; }
.task-skill-role-panel { display: grid; gap: 7px; }
.task-skill-role-panel > label { display: grid; grid-template-columns: auto minmax(0,1fr); gap: 9px; align-items: center; padding: 9px 10px; border: 1px solid rgba(148,163,184,.15); border-radius: 11px; background: #fbfcff; transition: border-color .15s ease,background .15s ease; }
.task-skill-role-panel > label.selected { border-color: rgba(124,58,237,.22); background: linear-gradient(110deg,#faf7ff,#f7fbff); }
.task-skill-role-panel label > span { display: grid; gap: 1px; }
.task-skill-role-panel strong { color: #334155; font-size: 10px; text-transform: capitalize; }
.task-skill-role-panel small { color: #94a3b8; font-size: 8px; }
.task-skill-relations { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.task-skill-relations > div { min-width: 0; padding: 10px 11px; background: linear-gradient(135deg,#f8fafc,#fbfaff); border: 1px solid rgba(148,163,184,.14); border-radius: 11px; }
.task-skill-relations p { display: -webkit-box; overflow: hidden; margin: 7px 0 0; color: #475569; font-size: 9px; line-height: 1.45; -webkit-box-orient: vertical; -webkit-line-clamp: 3; }
.task-skill-techniques .task-skill-section-heading { margin-bottom: 8px; }
.task-technique-list { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.task-technique-list article { display: grid; grid-template-columns: 30px minmax(0,1fr); gap: 9px; min-width: 0; padding: 10px; background: linear-gradient(135deg,#fbfdff,#faf8ff); border: 1px solid rgba(148,163,184,.16); border-radius: 11px; }
.task-technique-index { display: grid; width: 28px; height: 28px; place-items: center; color: #7c3aed; font-size: 9px; font-weight: 900; background: #f3efff; border: 1px solid rgba(139,92,246,.15); border-radius: 9px; }
.task-technique-list article > div { display: grid; min-width: 0; grid-template-columns: auto minmax(0,1fr); gap: 3px 7px; align-items: center; }
.task-technique-stage { justify-self: start; padding: 2px 6px; color: #047857; font-size: 7px; font-weight: 900; text-transform: uppercase; background: #ecfdf5; border-radius: 999px; }
.task-technique-list article strong { overflow: hidden; color: #334155; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.task-technique-list article p { display: -webkit-box; grid-column: 1 / -1; overflow: hidden; margin: 2px 0 0; color: #64748b; font-size: 8px; line-height: 1.4; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.task-skill-manual { padding-bottom: 10px; }
.task-skill-body-field { min-height: 0; margin-bottom: 0 !important; }
.task-skill-body-field :deep(.n-form-item-blank) { min-height: 0; }
.task-skill-body { height: 260px; min-height: 260px; }
.task-skill-body :deep(.n-input-wrapper), .task-skill-body :deep(.n-input__textarea) { height: 100%; }
.task-skill-body :deep(.n-input-wrapper) { padding: 12px 14px; background: #fbfcff; border-radius: 11px; }
.task-skill-body :deep(textarea) { height: 100% !important; color: #334155; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 11px; line-height: 1.65; }
.task-skill-validation { display: grid; gap: 3px; padding: 10px 13px; border-radius: 12px; color: #166534; background: #f0fdf4; }
.task-skill-validation.invalid { color: #991b1b; background: #fef2f2; }
.task-skill-validation span { font-size: 12px; }
.task-skill-actions { display: grid; grid-template-columns: auto 1fr repeat(4, auto); gap: 8px; align-items: center; padding: 11px 14px; border-top: 1px solid rgba(139,92,246,.12); background: rgba(255,255,255,.96); box-shadow: 0 -8px 20px rgba(67,56,110,.035); }
.task-skill-enabled-control { display: flex; gap: 9px; align-items: center; }
.task-skill-enabled-control > div { display: grid; gap: 1px; }
.task-skill-enabled-control strong { color: #334155; font-size: 10px; }
.task-skill-enabled-control small { color: #94a3b8; font-size: 8px; }
.goal-memory-shell { display: grid; grid-template-rows: auto minmax(0,1fr); height: min(620px,calc(92vh - 142px)); min-height: 0; overflow: hidden; border: 1px solid rgba(124,58,237,.14); border-radius: 18px; background: linear-gradient(145deg,#f8f7ff 0%,#f7fbff 55%,#f4fbf9 100%); box-shadow: 0 18px 42px rgba(67,56,110,.07); }
.goal-memory-hero { position: relative; display: grid; grid-template-columns: 48px minmax(0,1fr) minmax(180px,auto) auto; gap: 14px; align-items: center; padding: 17px 18px; overflow: hidden; border-bottom: 1px solid rgba(124,58,237,.11); background: linear-gradient(115deg,rgba(255,255,255,.98),rgba(248,245,255,.96) 58%,rgba(236,253,245,.82)); }
.goal-memory-hero::after { position: absolute; right: 80px; bottom: -70px; width: 200px; height: 130px; content: ""; pointer-events: none; background: radial-gradient(circle,rgba(52,211,153,.13),transparent 68%); }
.goal-memory-hero-icon { display: grid; width: 46px; height: 46px; place-items: center; color: #fff; font-size: 21px; font-weight: 900; background: linear-gradient(145deg,#8b5cf6,#6366f1); border-radius: 15px; box-shadow: 0 9px 22px rgba(109,40,217,.23); }
.goal-memory-hero-copy { min-width: 0; }
.goal-memory-hero-copy small { color: #7c3aed; font-size: 10px; font-weight: 900; letter-spacing: .12em; }
.goal-memory-hero-copy h3 { margin: 2px 0 3px; color: #182235; font-size: 20px; line-height: 1.25; }
.goal-memory-hero-copy p { max-width: 570px; margin: 0; color: #64748b; font-size: 13px; line-height: 1.5; }
.goal-memory-target { z-index: 1; display: grid; min-width: 175px; max-width: 260px; gap: 2px; padding: 9px 12px; background: rgba(255,255,255,.72); border: 1px solid rgba(148,163,184,.16); border-radius: 12px; }
.goal-memory-target span { color: #8b5cf6; font-size: 9px; font-weight: 900; letter-spacing: .1em; }
.goal-memory-target strong { overflow: hidden; color: #334155; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.goal-memory-target small { color: #94a3b8; font-size: 11px; }
.goal-memory-loading, .goal-memory-scroll { min-height: 0; height: 100%; }
.goal-memory-loading :deep(.n-spin-content) { height: 100%; }
.goal-memory-list { display: grid; gap: 12px; padding: 16px 17px 24px; }
.goal-memory-card { overflow: hidden; background: rgba(255,255,255,.9); border: 1px solid rgba(139,92,246,.13); border-radius: 15px; box-shadow: 0 8px 24px rgba(65,52,103,.055); }
.goal-memory-card > summary { display: grid; grid-template-columns: 36px minmax(0,1fr) auto auto auto; gap: 11px; align-items: center; padding: 14px 15px; list-style: none; cursor: pointer; background: linear-gradient(110deg,#fbfaff,#f8fbff 70%,#f1fdf8); }
.goal-memory-card > summary::-webkit-details-marker { display: none; }
.goal-memory-card[open] > summary { border-bottom: 1px solid rgba(148,163,184,.12); }
.goal-memory-check { display: grid; width: 30px; height: 30px; place-items: center; color: #047857; font-size: 14px; font-weight: 900; background: #d1fae5; border: 1px solid #a7f3d0; border-radius: 10px; }
.goal-memory-card > summary > div:nth-child(2) { min-width: 0; }
.goal-memory-card > summary small { color: #059669; font-size: 9px; font-weight: 900; letter-spacing: .1em; }
.goal-memory-card h4 { overflow: hidden; margin: 2px 0 0; color: #28364d; font-size: 14px; line-height: 1.45; text-overflow: ellipsis; white-space: nowrap; }
.goal-memory-meta { display: flex; max-width: 340px; flex-wrap: wrap; gap: 5px; justify-content: flex-end; align-items: center; }
.goal-memory-meta span, .goal-memory-meta time { padding: 4px 8px; color: #64748b; font-size: 10px; font-style: normal; font-weight: 700; background: #fff; border: 1px solid rgba(148,163,184,.16); border-radius: 999px; }
.goal-memory-chevron { color: #7c3aed; font-size: 19px; line-height: 1; transition: transform .18s ease; }
.goal-memory-card[open] .goal-memory-chevron { transform: rotate(180deg); }
.goal-memory-io { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 14px 15px 16px; }
.goal-memory-io section { min-width: 0; padding: 13px 14px; background: linear-gradient(140deg,#fbf9ff,#f7f8ff); border: 1px solid rgba(139,92,246,.13); border-radius: 12px; }
.goal-memory-io section:last-child { background: linear-gradient(140deg,#f7fbff,#f2fcf8); border-color: rgba(16,185,129,.14); }
.goal-memory-io section > span { display: flex; gap: 6px; align-items: center; color: #7c3aed; font-size: 10px; font-weight: 900; letter-spacing: .08em; }
.goal-memory-io section:last-child > span { color: #047857; }
.goal-memory-io i { font-size: 12px; font-style: normal; }
.goal-memory-io p { max-height: 180px; margin: 9px 0 0; overflow: auto; color: #34445e; font-family: ui-monospace,SFMono-Regular,Consolas,monospace; font-size: 12px; line-height: 1.65; overflow-wrap: anywhere; white-space: pre-wrap; }
.goal-memory-empty { display: grid; height: 100%; min-height: 330px; place-content: center; justify-items: center; padding: 28px; text-align: center; }
.goal-memory-empty > span { display: grid; width: 54px; height: 54px; place-items: center; color: #fff; font-size: 23px; background: linear-gradient(145deg,#a78bfa,#6366f1); border-radius: 18px; box-shadow: 0 11px 25px rgba(109,40,217,.18); }
.goal-memory-empty h4 { margin: 14px 0 4px; color: #334155; font-size: 14px; }
.goal-memory-empty p { max-width: 410px; margin: 0; color: #94a3b8; font-size: 10px; line-height: 1.55; }
@media (max-width: 900px) {
  .task-skill-layout { grid-template-columns: 1fr; overflow: auto; }
  .task-skill-catalog { min-height: 280px; }
  .task-skill-editor-grid { grid-template-columns: 1fr 1fr; }
  .task-skill-composition-grid, .task-technique-list { grid-template-columns: 1fr; }
  .goal-memory-hero { grid-template-columns: 42px minmax(0,1fr) auto; }
  .goal-memory-target { grid-column: 1 / -1; max-width: none; }
  .goal-memory-io { grid-template-columns: 1fr; }
  .goal-memory-card > summary { grid-template-columns: 36px minmax(0,1fr) auto auto; }
  .goal-memory-meta { grid-column: 2 / -1; justify-content: flex-start; }
}
:global(.task-agent-settings-modal .n-card__content) { min-height: 0; overflow: hidden; }
:global(.task-agent-settings-modal .n-tabs) { height: 100%; }
:global(.task-agent-settings-modal .n-tabs-pane-wrapper) { min-height: 0; }
:global(.task-agent-settings-modal .n-tab-pane) { height: min(620px, calc(92vh - 142px)); max-height: min(620px, calc(92vh - 142px)); overflow: hidden; }
</style>
