<template>
  <div class="agent-review-shell">
    <GlassPanel class="agent-review-panel">
      <div class="section-heading agent-review-heading">
        <div>
          <p class="eyebrow">{{ $t('auto.43da21552eb6') }}</p>
          <h2>{{ $t('auto.a70f44e843d1') }}</h2>
          <p class="agent-review-subtitle"> {{ $t('auto.76aa86bcc8bc') }} </p>
        </div>
        <div class="endpoint-heading-actions">
          <n-button v-if="project" secondary round @click="closeProject">{{ $t('auto.59994914bf39') }}</n-button>
          <n-button secondary round @click="loadProjects">{{ $t('auto.56e3badc4e6c') }}</n-button>
          <n-button v-if="!project" type="primary" round @click="openProjectSetup()">
            <template #icon><n-icon><AddOutline /></n-icon></template> {{ $t('auto.1cab4431f333') }}
          </n-button>
        </div>
      </div>

      <n-alert v-if="error" type="error" closable class="agent-review-alert" @close="error = ''">
        {{ error }}
      </n-alert>

      <section v-if="!project" class="agent-review-projects-page">
        <div class="agent-review-project-library">
          <div class="agent-review-projects-title">
            <div>
              <p class="eyebrow">{{ $t('auto.53e890d5f0ff') }}</p>
              <h3>{{ $t('auto.92d1cd06ba73') }}</h3>
              <span>{{ projects.length }} {{ $t('auto.cd690384be3b') }}</span>
            </div>
          </div>
          <div v-if="projects.length" class="agent-review-option-grid">
            <button
              v-for="item in projects"
              :key="item.projectId"
              type="button"
              class="agent-review-option-card"
              @click="selectProject(item.projectId)"
            >
              <span class="agent-review-option-icon">{{ projectInitial(item.projectName) }}</span>
              <span class="agent-review-option-copy">
                <strong>{{ item.projectName }}</strong>
                <small>{{ projectCardDescription(item) }}</small>
              </span>
              <span class="agent-review-option-type">{{ item.agentType }}</span>
              <span class="agent-review-option-status" :class="{ running: isProjectBusy(item) }">
                <n-spin v-if="isProjectBusy(item)" size="small" />
                {{ projectStatusLabel(item.status) }}
              </span>
              <span class="agent-review-option-time">{{ formatTime(item.updatedAt || item.createdAt || '') }}</span>
            </button>
          </div>
          <n-empty v-else :description="$t('auto.dc94303f94ff')">
            <template #extra>
              <n-button type="primary" round @click="openProjectSetup()">{{ $t('auto.52c4594c8d31') }}</n-button>
            </template>
          </n-empty>
        </div>
      </section>

      <CanvasWorkspace v-else :project="project" />

      <n-modal v-model:show="projectSetupOpen" preset="card" :title="$t('auto.307abfd2ef51')" class="agent-review-setup-modal">
        <n-form label-placement="top" class="agent-review-form">
          <n-form-item :label="$t('auto.5f950764df30')">
            <n-input v-model:value="setup.projectName" :placeholder="$t('auto.d08e2bccb5c5')" />
          </n-form-item>
          <n-form-item :label="$t('auto.55f8ebc805e6')">
            <n-input v-model:value="setup.description" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" />
          </n-form-item>
        </n-form>
        <template #footer>
          <div class="agent-review-actions">
            <n-button type="primary" round @click="createProject">{{ $t('auto.1cab4431f333') }}</n-button>
          </div>
        </template>
      </n-modal>
    </GlassPanel>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { AddOutline } from '@vicons/ionicons5'
import { useMessage } from 'naive-ui'
import GlassPanel from '../../components/GlassPanel.vue'
import { translateSource } from '../../i18n'
import { agentSecurityReviewApi, type ReviewProject } from '../../api/agentSecurityReview'
import CanvasWorkspace from '../../modules/agents/agent-canvas/components/CanvasWorkspace.vue'

const message = useMessage()
const projects = ref<ReviewProject[]>([])
const project = ref<ReviewProject | null>(null)
const error = ref('')
const projectSetupOpen = ref(false)
const setup = reactive({
  projectName: '',
  description: '',
})

async function loadProjects(quiet = false) {
  if (!quiet) error.value = ''
  try {
    projects.value = await agentSecurityReviewApi.listProjects()
  } catch (err) {
    setError(err)
  }
}

async function selectProject(projectId: string) {
  error.value = ''
  try {
    project.value = await agentSecurityReviewApi.getProject(projectId)
    if (isErrorStatus(project.value.status) && project.value.error) {
      error.value = cleanJobError(project.value.error)
    }
  } catch (err) {
    setError(err)
  }
}

function openProjectSetup() {
  error.value = ''
  setup.projectName = ''
  setup.description = ''
  projectSetupOpen.value = true
}

async function createProject() {
  if (!setup.projectName.trim()) {
    message.warning(translateSource('auto.d7792c0b2ea7'))
    return
  }
  try {
    const created = await agentSecurityReviewApi.createProject({
      projectName: setup.projectName.trim(),
      description: setup.description,
    })
    projectSetupOpen.value = false
    await loadProjects()
    await selectProject(created.projectId)
    message.success(translateSource('auto.76556f09a383'))
  } catch (err) {
    setError(err)
  }
}

function closeProject() {
  project.value = null
  void loadProjects()
}

function isBusyStatus(status?: string) {
  const value = String(status || '').toLowerCase()
  return value === 'asset_review_running'
    || value === 'asset_review_gap_check_running'
    || value === 'asset_review_assets_running'
    || value === 'asset_review_capabilities_running'
    || value === 'asset_review_graph_running'
    || value.includes('reviewing functions')
    || value.includes('risk_reviewing')
    || value.includes('risk reviewing')
}

function isErrorStatus(status?: string) {
  return String(status || '').toLowerCase() === 'error'
}

function isProjectBusy(item: ReviewProject) {
  return isBusyStatus(item.status)
}

function projectStatusLabel(status?: string) {
  const value = String(status || '').toLowerCase()
  if (value === 'review_cancelled') return 'Review Cancelled'
  if (value.includes('gap_check')) return 'Checking Coverage'
  if (value.includes('assets')) return 'Generating Asset Inventory'
  if (value.includes('capabilities')) return 'Generating Capabilities'
  if (value.includes('graph')) return 'Generating Function Flow'
  if (isBusyStatus(status)) return 'Reviewing assets'
  if (isErrorStatus(status)) return 'Failed'
  const labels: Record<string, string> = {
    draft: 'Draft',
    materials_uploaded: 'Materials Uploaded',
    asset_review_completed: 'Asset Review Completed',
    missing_info_required: 'Missing Info Required',
    missing_info_answered: 'Missing Info Answered',
    function_map_ready: 'Function Map Ready',
    risk_map_ready: 'Risk Map Ready',
  }
  if (labels[value]) return labels[value]
  if (!status) return 'Draft'
  return status.replace(/([a-z])([A-Z])/g, '$1 $2')
}

function projectCardDescription(item: ReviewProject) {
  if (isProjectBusy(item)) return 'AI review is running in the background. You can leave this page and come back later.'
  if (item.functionReview && !item.riskReview) return 'Asset review and function map are ready. Complete blockers before risk mapping.'
  if (item.riskReview) return 'Risk overlay and report are available for review.'
  return item.description || 'Prepare materials and run the first asset review.'
}

function projectInitial(value: string) {
  return (value || 'A').trim().slice(0, 1).toUpperCase()
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleString() : ''
}

function setError(err: unknown) {
  const raw = err instanceof Error ? err.message : 'Request failed'
  error.value = cleanJobError(raw.replace(/Gemini 3 Pro via model id\s+/g, 'Gemini model id '))
  message.error(error.value)
}

function cleanJobError(value: string) {
  const raw = String(value || '').trim()
  if (!raw) return ''
  const jsonStart = raw.indexOf('{')
  if (jsonStart >= 0) {
    try {
      const parsed = JSON.parse(raw.slice(jsonStart))
      const messageText = parsed?.error?.message || parsed?.message
      const statusText = parsed?.error?.status || parsed?.status
      if (messageText) return statusText ? `${statusText}: ${messageText}` : messageText
    } catch {
      // Fall through to readable raw text.
    }
  }
  return raw.replace(/\s+/g, ' ')
}

onMounted(() => {
  void loadProjects()
})
</script>
