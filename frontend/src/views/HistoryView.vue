<template>
  <div class="history-shell">
    <GlassPanel class="history-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Testing history</p>
          <h2>Benchmark runs</h2>
        </div>
        <n-button type="primary" round @click="router.push('/benchmark')">
          <template #icon><n-icon><AddOutline /></n-icon></template>
          Start New Run
        </n-button>
      </div>

      <div v-if="jobs.length" class="history-grid">
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
              <small>{{ item.description || 'No description' }}</small>
            </span>
            <n-tag size="small" round :type="tagType(item.status)">{{ item.status }}</n-tag>
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
                <template #icon><n-icon><EyeOutline /></n-icon></template>
                Details
              </n-button>
              <n-popconfirm
                positive-text="Delete"
                negative-text="Cancel"
                @positive-click="deleteSelectedJob"
              >
                <template #trigger>
                  <n-button secondary round type="error" :loading="deleting">
                    <template #icon><n-icon><TrashOutline /></n-icon></template>
                    Delete
                  </n-button>
                </template>
                Delete this report and its stored run files?
              </n-popconfirm>
            </n-space>
          </div>
          <p>{{ selectedJob.description || 'No description' }}</p>
          <div class="job-stat-grid">
            <div>
              <span>Status</span>
              <strong>{{ selectedJob.status }}</strong>
            </div>
            <div>
              <span>Progress</span>
              <strong>{{ selectedJob.progress }}%</strong>
            </div>
            <div>
              <span>Prompts</span>
              <strong>{{ selectedJob.summary.completed_prompts }} / {{ selectedJob.summary.estimated_prompts || '-' }}</strong>
            </div>
            <div>
              <span>Errors</span>
              <strong>{{ selectedJob.summary.error_count }}</strong>
            </div>
          </div>
          <div class="detail-block">
            <strong>Model Endpoints</strong>
            <span>{{ selectedJob.summary.endpoints.join(', ') }}</span>
          </div>
          <div class="detail-block">
            <strong>Cookbooks</strong>
            <span>{{ selectedJob.summary.cookbooks.join(', ') || 'No cookbook metadata captured' }}</span>
          </div>
          <div class="detail-block">
            <strong>Recipes</strong>
            <span>{{ selectedJob.summary.recipes.join(', ') }}</span>
          </div>
        </section>
      </div>

      <n-empty v-else description="No benchmark runs yet" />
    </GlassPanel>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { AddOutline, EyeOutline, TimeOutline, TrashOutline } from '@vicons/ionicons5'
import { useMessage, useNotification } from 'naive-ui'
import GlassPanel from '../components/GlassPanel.vue'
import { moonshotApi } from '../api/moonshot'
import type { BenchmarkJob } from '../types/moonshot'

const router = useRouter()
const message = useMessage()
const notification = useNotification()
const jobs = ref<BenchmarkJob[]>([])
const selectedId = ref('')
const deleting = ref(false)

function notify(type: 'success' | 'warning' | 'error', options: { title: string; content: string }) {
  notification[type]({ ...options, duration: 2000 })
}

const selectedJob = computed(() => jobs.value.find((job) => job.id === selectedId.value) ?? jobs.value[0])

function tagType(status: string) {
  if (status === 'completed') return 'success'
  if (status === 'completed_with_errors') return 'warning'
  if (status === 'failed') return 'error'
  return 'info'
}

async function loadJobs() {
  jobs.value = await moonshotApi.getBenchmarkJobs()
  if (!jobs.value.find((job) => job.id === selectedId.value)) {
    selectedId.value = jobs.value[0]?.id ?? ''
  }
}

async function deleteSelectedJob() {
  if (!selectedJob.value) return
  deleting.value = true
  try {
    const result = await moonshotApi.deleteBenchmarkJob(selectedJob.value.id)
    if (result.deleted) {
      notify('success', { title: 'Report deleted', content: selectedJob.value.name })
      message.success('Report deleted')
    } else {
      notify('warning', { title: 'Report partially deleted', content: 'Some files are still locked by a running process.' })
      message.warning('Report partially deleted. Some files are still locked by a running process.')
    }
    selectedId.value = ''
    await loadJobs()
  } catch (error) {
    notify('error', { title: 'Delete failed', content: error instanceof Error ? error.message : 'Delete failed' })
    message.error(error instanceof Error ? error.message : 'Delete failed')
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  await loadJobs()
})
</script>
