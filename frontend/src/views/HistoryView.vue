<template>
  <div class="history-shell">
    <GlassPanel class="history-panel">
      <div class="section-heading">
        <div class="workspace-title-block">
          <span class="workspace-title-icon workspace-title-icon--history">
            <n-icon><TimeOutline /></n-icon>
          </span>
          <div class="workspace-title-content">
            <p class="eyebrow">{{ $t('auto.bf807ce36860') }}</p>
            <h2>{{ $t('auto.356251b4e064') }}</h2>
            <span>{{ $t('auto.55e71bbaecb2') }}</span>
          </div>
        </div>
        <n-button type="primary" round @click="router.push('/benchmark')">
          <template #icon><n-icon><AddOutline /></n-icon></template> {{ $t('auto.0f84f5f5d160') }} </n-button>
      </div>

      <div v-if="historyState === 'loading'" class="history-state-panel" role="status" aria-live="polite">
        <n-spin size="medium" />
        <div>
          <strong>{{ $t('historyRun.loading.title') }}</strong>
          <span>{{ $t('historyRun.loading.description') }}</span>
        </div>
      </div>

      <div v-else-if="historyState === 'error'" class="history-state-panel history-state-panel--error" role="alert">
        <span class="history-state-icon" aria-hidden="true">
          <n-icon><AlertCircleOutline /></n-icon>
        </span>
        <div>
          <strong>{{ $t('historyRun.error.title') }}</strong>
          <span>{{ loadError }}</span>
        </div>
        <n-button secondary round :loading="initialLoading" @click="retryLoadJobs">
          <template #icon><n-icon><RefreshOutline /></n-icon></template>
          {{ $t('historyRun.error.retry') }}
        </n-button>
      </div>

      <div v-else-if="historyState === 'list'" class="history-grid">
        <n-scrollbar class="history-list-scrollbar">
          <button
            v-for="item in jobs"
            :key="item.id"
            class="history-row"
            :class="{ active: item.id === selectedId }"
            type="button"
            @click="selectedId = item.id"
          >
            <n-icon size="22"><TimeOutline /></n-icon>
            <span>
              <strong>{{ item.name }}</strong>
              <small>{{ item.description || $t('auto.f354c94fcf63') }}</small>
            </span>
            <n-tag size="small" round :type="tagType(item.status)">{{ statusLabel(item.status) }}</n-tag>
          </button>
        </n-scrollbar>

        <section v-if="selectedJob" class="history-detail">
          <div class="detail-title-row">
            <h3>
              <n-icon><TimeOutline /></n-icon>
              {{ selectedJob.name }}
            </h3>
            <n-space>
              <n-button secondary round @click="router.push(`/jobs/${selectedJob.id}`)">
                <template #icon><n-icon><EyeOutline /></n-icon></template> {{ $t('auto.dc3decbb9384') }} </n-button>
              <n-popconfirm
                :positive-text="$t('common.delete')"
                :negative-text="$t('auto.77dfd2135f4d')"
                @positive-click="deleteSelectedJob"
              >
                <template #trigger>
                  <n-button secondary round type="error" :loading="deleting">
                    <template #icon><n-icon><TrashOutline /></n-icon></template>
                    {{ $t('common.delete') }}
                  </n-button>
                </template> {{ $t('auto.1242c2439388') }} </n-popconfirm>
            </n-space>
          </div>
          <p>{{ selectedJob.description || $t('auto.f354c94fcf63') }}</p>
          <div class="job-stat-grid">
            <div>
              <span>{{ $t('auto.bae7d5be7082') }}</span>
              <strong>{{ statusLabel(selectedJob.status) }}</strong>
            </div>
            <div>
              <span>{{ $t('auto.1b90271d66cf') }}</span>
              <strong>{{ selectedJob.progress }}%</strong>
            </div>
            <div>
              <span>{{ $t('auto.eea5311d723f') }}</span>
              <strong>{{ selectedJob.summary.completed_prompts }} / {{ selectedJob.summary.estimated_prompts || '-' }}</strong>
            </div>
            <div>
              <span>{{ $t('auto.805e86a8cbf6') }}</span>
              <strong>{{ selectedJob.summary.error_count }}</strong>
            </div>
          </div>
          <div class="detail-block">
            <strong>{{ $t('auto.2c7a56bbe6df') }}</strong>
            <span>{{ selectedJob.summary.endpoints.join(', ') }}</span>
          </div>
          <div class="detail-block">
            <strong>{{ $t('auto.3a27713963ce') }}</strong>
            <span>{{ selectedJob.summary.cookbooks.join(', ') || $t('auto.e4621fc1547b') }}</span>
          </div>
          <div class="detail-block">
            <strong>{{ $t('auto.9fb1092f32d4') }}</strong>
            <span>{{ selectedJob.summary.recipes.join(', ') }}</span>
          </div>
        </section>
      </div>

      <n-empty v-else :description="$t('auto.0863ca796eb4')" />
    </GlassPanel>
  </div>
</template>

<script setup lang="ts">
import { translateSource } from '../i18n'

import { computed, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import {
  AddOutline,
  AlertCircleOutline,
  EyeOutline,
  RefreshOutline,
  TimeOutline,
  TrashOutline,
} from '@vicons/ionicons5'
import { useMessage, useNotification } from 'naive-ui'
import GlassPanel from '../components/GlassPanel.vue'
import { moonshotApi } from '../api/moonshot'
import { useMoonshotStore } from '../stores/moonshot'
import { benchmarkJobLoadErrorKind } from '../utils/jobRun'
import { resolveHistoryViewState } from '../utils/historyViewState'

const router = useRouter()
const { t } = useI18n()
const message = useMessage()
const notification = useNotification()
const store = useMoonshotStore()
const { jobs } = storeToRefs(store)
const selectedId = ref('')
const deleting = ref(false)
const initialLoading = ref(!jobs.value.length)
const loadError = ref('')

function notify(type: 'success' | 'warning' | 'error', options: { title: string; content: string }) {
  notification[type]({ ...options, duration: 2000 })
}

const selectedJob = computed(() => jobs.value.find((job) => job.id === selectedId.value) ?? jobs.value[0])
const historyState = computed(() => resolveHistoryViewState({
  loading: initialLoading.value,
  error: loadError.value,
  jobCount: jobs.value.length,
}))

function tagType(status: string) {
  if (status === 'completed') return 'success'
  if (status === 'completed_with_errors') return 'warning'
  if (status === 'failed') return 'error'
  return 'info'
}

function statusLabel(status: string) {
  const keys: Record<string, string> = {
    queued: 'jobRun.status.queued',
    running: 'jobRun.status.running',
    running_with_errors: 'jobRun.status.runningWithErrors',
    paused: 'jobRun.status.paused',
    completed: 'jobRun.status.completed',
    completed_with_errors: 'jobRun.status.completedWithErrors',
    failed: 'jobRun.status.failed',
  }
  return keys[status] ? t(keys[status]) : status
}

async function loadJobs() {
  if (!jobs.value.length) initialLoading.value = true
  try {
    store.jobs = await moonshotApi.getBenchmarkJobs()
    loadError.value = ''
  } catch (error) {
    const errorKind = benchmarkJobLoadErrorKind(error)
    loadError.value = t(`historyRun.error.${errorKind}`)
  } finally {
    initialLoading.value = false
  }
}

async function retryLoadJobs() {
  await loadJobs()
}

async function deleteSelectedJob() {
  if (!selectedJob.value) return
  deleting.value = true
  try {
    const result = await moonshotApi.deleteBenchmarkJob(selectedJob.value.id)
    if (result.deleted) {
      notify('success', { title: translateSource('auto.a7788f3b7f17'), content: selectedJob.value.name })
      message.success(translateSource('auto.a7788f3b7f17'))
    } else {
      notify('warning', { title: translateSource('auto.f97ad0da34bf'), content: 'Some files are still locked by a running process.' })
      message.warning(translateSource('auto.956a95e55cd5'))
    }
    selectedId.value = ''
    await loadJobs()
  } catch (error) {
    notify('error', { title: translateSource('auto.64513b47d460'), content: error instanceof Error ? error.message : 'Delete failed' })
    message.error(error instanceof Error ? error.message : 'Delete failed')
  } finally {
    deleting.value = false
  }
}

watch(jobs, (nextJobs) => {
  if (!nextJobs.find((job) => job.id === selectedId.value)) {
    selectedId.value = nextJobs[0]?.id ?? ''
  }
}, { immediate: true })

onMounted(() => {
  void loadJobs()
})
</script>
