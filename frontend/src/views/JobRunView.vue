<template>
  <div class="job-shell">
    <GlassPanel class="job-hero-panel">
      <div class="job-hero-copy">
        <p class="eyebrow">{{ $t('auto.a1cc90458b81') }}</p>
        <h2>{{ heading }}</h2>
        <p>{{ job?.description || $t('auto.f354c94fcf63') }}</p>
        <div v-if="canPreviewReport" class="job-hero-actions">
          <n-button type="primary" round @click="reportOpen = true"> {{ $t('auto.2632041f3c44') }} </n-button>
          <n-button tag="a" :href="reportDownloadUrl" secondary round>
            <template #icon><n-icon><DownloadOutline /></n-icon></template> {{ $t('auto.a479c9c34e87') }} </n-button>
        </div>
      </div>
      <div class="job-status-card">
        <div>
          <span>{{ $t('auto.bae7d5be7082') }}</span>
          <strong>{{ job?.status || 'loading' }}</strong>
        </div>
        <n-progress
          type="line"
          :percentage="progress"
          :show-indicator="false"
          :color="progressColor"
        />
        <b>{{ progress }}%</b>
        <div v-if="isJudgePhase" class="judge-progress">
          <div>
            <span>{{ $t('auto.46658a448ebf') }}</span>
            <strong>{{ judgeProgressLabel }}</strong>
          </div>
          <n-progress
            type="line"
            :percentage="judgeProgressPercent"
            :show-indicator="false"
            color="linear-gradient(90deg, #47d7ff, #8b5cf6, #7c3aed)"
          />
          <i v-if="judgeProgressIsPending" aria-hidden="true"></i>
        </div>
      </div>
    </GlassPanel>

    <div v-if="job" class="job-grid">
      <GlassPanel class="job-side-panel">
        <div class="section-heading compact-heading">
          <div class="job-detail-title">
            <p class="eyebrow">{{ $t('auto.e6487ca72b41') }}</p>
            <n-ellipsis :tooltip="{ placement: 'top' }">
              <h2>{{ job.name }}</h2>
            </n-ellipsis>
          </div>
          <div class="job-action-row">
            <n-button secondary round @click="router.push('/history')">
              <template #icon><n-icon><TimeOutline /></n-icon></template> {{ $t('auto.90ccd6497400') }} </n-button>
            <n-button v-if="canPause" secondary round type="warning" :loading="pausing" @click="pauseJob">
              <template #icon><n-icon><PauseCircleOutline /></n-icon></template> {{ $t('auto.781961bc81c2') }} </n-button>
            <n-button v-if="canResume" secondary round type="primary" :loading="resuming" @click="resumeJob">
              <template #icon><n-icon><PlayCircleOutline /></n-icon></template> {{ $t('auto.2e02623966f9') }} </n-button>
            <n-popconfirm
              v-if="canDeleteFromDetails"
              :positive-text="$t('common.delete')"
              :negative-text="$t('auto.77dfd2135f4d')"
              @positive-click="deleteJob"
            >
              <template #trigger>
                <n-button secondary round type="error" :loading="deleting">
                  <template #icon><n-icon><TrashOutline /></n-icon></template>
                  {{ $t('common.delete') }}
                </n-button>
              </template> {{ $t('auto.8f5403844420') }} </n-popconfirm>
          </div>
        </div>

        <div class="job-stat-grid">
          <div>
            <span>{{ $t('auto.eea5311d723f') }}</span>
            <strong>{{ job.summary.completed_prompts }} / {{ job.summary.estimated_prompts || '-' }}</strong>
          </div>
          <div>
            <span>{{ $t('auto.805e86a8cbf6') }}</span>
            <strong>{{ job.summary.error_count }}</strong>
          </div>
          <div>
            <span>{{ $t('auto.faa9e7e7ef5a') }}</span>
            <strong>{{ formatDate(job.started_at || job.created_at) }}</strong>
          </div>
          <div>
            <span>{{ $t('auto.f2f8570ddd7b') }}</span>
            <strong>{{ formatDate(job.updated_at) }}</strong>
          </div>
          <div>
            <span>{{ $t('auto.bb12e8aaaecc') }}</span>
            <strong>{{ job.summary.thread_count || job.request.thread_count || 1 }}</strong>
          </div>
          <div>
            <span>{{ $t('auto.3044d4f6c438') }}</span>
            <strong>{{ etaLabel }}</strong>
          </div>
        </div>

        <section v-if="canResume" class="job-thread-panel">
          <div>
            <p class="eyebrow">{{ $t('auto.67d7ec2d39fd') }}</p>
            <strong>{{ threadCount }} {{ $t('auto.c91e11a1f2a2') }}</strong>
          </div>
          <n-slider v-model:value="threadCount" :min="1" :max="20" :step="1" />
          <n-button secondary round :loading="savingThreads" @click="saveThreadCount"> {{ $t('auto.3fc0f93671a2') }} </n-button>
        </section>

        <section class="job-chip-section">
          <p class="eyebrow">{{ $t('auto.b71c52711a24') }}</p>
          <div class="job-chip-cloud">
            <n-tag v-for="endpoint in job.summary.endpoints" :key="endpoint" round>
              {{ endpointLabel(endpoint) }}
            </n-tag>
          </div>
        </section>

        <section class="job-chip-section">
          <p class="eyebrow">{{ $t('auto.3a27713963ce') }}</p>
          <div class="job-chip-cloud">
            <n-tag v-for="cookbook in job.summary.cookbooks" :key="cookbook" round>
              {{ cookbookLabel(cookbook) }}
            </n-tag>
            <span v-if="!job.summary.cookbooks.length">{{ $t('auto.e4621fc1547b') }}</span>
          </div>
        </section>

        <section v-if="job.errors.length" class="job-errors">
          <p class="eyebrow">{{ $t('auto.805e86a8cbf6') }}</p>
          <n-scrollbar class="job-error-scrollbar">
            <div v-for="(error, index) in job.errors.slice(0, 40)" :key="index" class="job-error-line">
              {{ error }}
            </div>
          </n-scrollbar>
        </section>
      </GlassPanel>

      <GlassPanel class="job-main-panel">
        <div class="section-heading compact-heading prompt-trace-heading">
          <div class="prompt-trace-title">
            <p class="eyebrow">{{ $t('auto.f5104fb7f327') }}</p>
            <h2>{{ $t('auto.421b14c83c64') }}</h2>
            <span>{{ interactionRangeLabel }}</span>
          </div>
          <div class="prompt-trace-toolbar">
            <div class="trace-count">
              <strong>{{ interactionTotal }}</strong>
              <span>{{ interactionFilterLabel }}</span>
            </div>
            <div class="prompt-trace-spacer" />
            <div class="prompt-trace-actions">
              <n-select
                v-if="cookbookFilterOptions.length > 2"
                v-model:value="cookbookFilter"
                size="small"
                class="cookbook-filter-select"
                :options="cookbookFilterOptions"
                @update:value="changeTraceFilters"
              />
              <n-select
                v-model:value="interactionFilter"
                size="small"
                class="trace-type-filter-select"
                :options="interactionFilterOptions"
                @update:value="changeTraceFilters"
              />
              <n-button secondary circle :aria-label="$t('auto.d8274c187f9f')" @click="loadJob">
                <template #icon><n-icon><RefreshOutline /></n-icon></template>
              </n-button>
            </div>
          </div>
        </div>

        <n-scrollbar v-if="interactions.length" class="interaction-scrollbar">
          <article v-for="item in interactions" :key="item.id" class="interaction-card">
            <header>
              <div class="interaction-title">
                <strong>{{ item.endpoint || 'endpoint' }}</strong>
                <n-tag v-if="item.trace_status === 'error'" size="small" round type="error">{{ $t('auto.7f2f6a15cf8d') }}</n-tag>
              </div>
              <span>{{ item.recipe }} / {{ item.dataset }} #{{ item.prompt_index }}</span>
            </header>
            <div class="trace-block">
              <b>{{ $t('auto.b568d47f2e24') }}</b>
              <pre>{{ item.input }}</pre>
            </div>
            <div class="trace-grid">
              <div class="trace-block">
                <b>{{ $t('auto.6ac87f344682') }}</b>
                <pre>{{ item.expected || $t('auto.eea4d26a1e58') }}</pre>
                <small v-if="item.expected_raw && item.expected_raw !== item.expected">{{ $t('auto.fab2f9b4bf4c') }} {{ item.expected_raw }}</small>
              </div>
              <div class="trace-block">
                <b>{{ $t('auto.6e617e4fc9da') }}</b>
                <pre>{{ formatResponse(item.response) }}</pre>
              </div>
            </div>
            <div v-if="item.evaluator" class="trace-evaluator">
              <div class="trace-evaluator-summary">
                <b>{{ $t('auto.46658a448ebf') }}</b>
                <n-tag size="small" round :type="evaluatorTagType(item.evaluator.acceptable_status)">
                  {{ evaluatorStatusLabel(item.evaluator.acceptable_status) }}
                </n-tag>
                <span v-if="item.evaluator.refusal">{{ $t('auto.01eab9a98fed') }} {{ item.evaluator.refusal }}</span>
                <span v-if="item.evaluator.metric_id">{{ item.evaluator.metric_id }}</span>
              </div>
              <pre v-if="item.evaluator.judge_response">{{ item.evaluator.judge_response }}</pre>
            </div>
          </article>
        </n-scrollbar>
        <n-empty v-else :description="$t('auto.b12c76ace33c')" />
        <div v-if="interactionTotal > interactionPageSize" class="interaction-pagination">
          <n-pagination
            v-model:page="interactionPage"
            :page-size="interactionPageSize"
            :item-count="interactionTotal"
            @update:page="loadJob"
          />
        </div>
      </GlassPanel>
    </div>

    <GlassPanel v-else class="job-loading-panel">
      <n-spin size="large" />
    </GlassPanel>

    <n-modal
      v-model:show="reportOpen"
      preset="card"
      class="report-modal"
      :title="$t('auto.fa5781733976')"
      :bordered="false"
    >
      <template #header-extra>
        <n-button v-if="job" tag="a" :href="reportDownloadUrl" type="primary" round>
          <template #icon><n-icon><DownloadOutline /></n-icon></template> {{ $t('auto.a479c9c34e87') }} </n-button>
      </template>

      <article v-if="job?.report_summary" class="report-document">
        <header class="report-document-header">
          <div class="report-watermark">OXO TRACKER</div>
          <h1>{{ $t('auto.fa5781733976') }}</h1>
          <p>{{ job.report_summary.name }}</p>
        </header>

        <section class="report-summary-grid report-summary-grid-light">
          <div>
            <span>{{ $t('auto.e61a7638ef1f') }}</span>
            <strong>{{ job.report_summary.endpoints.join(', ') || '-' }}</strong>
          </div>
          <div>
            <span>{{ $t('auto.7cd79ace2b8b') }}</span>
            <strong>{{ job.report_summary.total_prompts || job.summary.completed_prompts }}</strong>
          </div>
          <div>
            <span>{{ $t('auto.9bbd73fee563') }}</span>
            <strong>{{ job.report_summary.start_time || formatDate(job.started_at) }}</strong>
          </div>
          <div>
            <span>{{ $t('auto.100dba762b33') }}</span>
            <strong>{{ job.report_summary.end_time || formatDate(job.ended_at) }}</strong>
          </div>
        </section>

        <section class="report-section">
          <h2>{{ $t('auto.3713e807935f') }}</h2>
          <div class="report-area-cards">
            <article v-for="cookbook in reportCookbooks" :key="cookbook.id" class="report-area-card">
              <span>{{ $t('auto.ae28e153fd42') }}</span>
              <strong>{{ cookbook.label }}</strong>
              <small>{{ cookbook.recipeCount }} {{ $t('auto.055f9add6221') }} {{ cookbook.datasetCount }} {{ $t('auto.061ac740047f') }}</small>
            </article>
            <div class="report-area-card legend-card">
              <span>{{ $t('auto.f14ec1a8bc89') }}</span>
              <div class="legend-lines">
                <p><b>Q</b> {{ $t('auto.7af58fdf276c') }}</p>
                <p><b>C</b> {{ $t('auto.181815c67a93') }}</p>
                <p><b>T</b> {{ $t('auto.080deb21dd81') }}</p>
              </div>
            </div>
          </div>
        </section>

        <section class="report-section">
          <h2>{{ $t('auto.6b68e59f7cb9') }}</h2>
          <details class="report-rating-guide">
            <summary>{{ $t('auto.98219d0f51bb') }}</summary>
            <div class="rating-guide-body">
              <p> {{ $t('auto.fe431736920e') }} </p>
              <div class="rating-guide-grid">
                <div v-for="guide in ratingGuides" :key="guide.grade">
                  <strong>{{ guide.grade }}</strong>
                  <p><b>{{ $t('auto.455348d1c29e') }}</b> {{ guide.quality }}</p>
                  <p><b>{{ $t('auto.e2d310aa1bd8') }}</b> {{ guide.capability }}</p>
                  <p><b>{{ $t('auto.c25f6c205b8c') }}</b> {{ guide.safety }}</p>
                </div>
              </div>
            </div>
          </details>
          <article v-for="recipe in job.report_summary.recipe_summaries" :key="recipe.id" class="report-recipe-section">
            <header>
              <div>
                <h3>{{ recipe.id }}</h3>
                <span>
                  {{ recipe.prompt_count }} {{ $t('auto.8f75a2be1401') }}<span v-if="recipe.failed_count"> / {{ recipe.failed_count }} {{ $t('auto.5f5f8758f5f2') }}</span>
                  / {{ recipe.datasets.length }} {{ $t('auto.061ac740047f') }} </span>
              </div>
              <div class="report-grade-list">
                <n-tag
                  v-for="evaluation in recipe.evaluation_summary"
                  :key="`${recipe.id}-${evaluation.model_id}`"
                  round
                  :type="gradeTagType(evaluation.grade || evaluation.overall_grade)"
                >
                  {{ evaluation.model_id || 'model' }}: {{ evaluation.grade || evaluation.overall_grade || '-' }}
                </n-tag>
              </div>
            </header>
            <div class="report-dataset-list">
              <n-tag v-for="dataset in recipe.datasets" :key="`${recipe.id}-${dataset}`" round>
                {{ dataset }}
              </n-tag>
            </div>
            <div v-if="recipe.metric_summaries?.length" class="report-judge-grid">
              <div v-for="metric in recipe.metric_summaries" :key="`${recipe.id}-${metric.metric_id}`">
                <span>{{ metric.metric_id || $t('auto.46658a448ebf') }}</span>
                <strong>{{ formatPercent(metric.acceptable_rate) }} {{ $t('auto.cab5b6e0a675') }}</strong>
                <small> {{ $t('auto.9525ae1781bb') }} {{ metric.safe ?? 0 }} {{ $t('auto.cac13757a19e') }} {{ metric.unsafe ?? 0 }} {{ $t('auto.2d72a3b7a732') }} {{ metric.refused ?? 0 }} {{ $t('auto.e7ee50d06df2') }} {{ metric.unknown ?? 0 }}
                </small>
              </div>
            </div>
            <div
              v-if="Object.keys(recipe.grading_scale || {}).length"
              class="report-rating-scale"
              :class="{ 'has-marker': Boolean(gradeMarkerStyle(recipe)) }"
              :style="gradeMarkerStyle(recipe)"
            >
              <div v-for="item in gradeScale(recipe.grading_scale)" :key="`${recipe.id}-${item.grade}`">
                <span>{{ item.grade }}</span>
                <b>{{ item.range }}</b>
              </div>
            </div>
          </article>
        </section>

        <section class="report-section">
          <div class="report-section-title">
            <h2>{{ $t('auto.cddd3a13ac50') }}</h2>
            <n-tag round :type="job.report_summary.unexpected_payload_count ? 'warning' : 'success'">
              {{ job.report_summary.unexpected_payload_count }} {{ $t('auto.2739bb260ce4') }} </n-tag>
          </div>
          <div v-if="job.report_summary.unexpected_payloads.length" class="unexpected-list">
            <article
              v-for="payload in job.report_summary.unexpected_payloads.slice(0, 20)"
              :key="`${payload.recipe_id}-${payload.prompt_index}-${payload.dataset_id}`"
              class="unexpected-card"
            >
              <header>
                <strong>{{ payload.model_id || 'model' }}</strong>
                <span>{{ payload.recipe_id }} / {{ payload.dataset_id }} #{{ payload.prompt_index }}</span>
              </header>
              <div class="unexpected-grid">
                <div>
                  <b>{{ $t('auto.6ac87f344682') }}</b>
                  <pre>{{ payload.expected || '-' }}</pre>
                  <small v-if="payload.expected_raw && payload.expected_raw !== payload.expected">{{ $t('auto.fab2f9b4bf4c') }} {{ payload.expected_raw }}</small>
                </div>
                <div>
                  <b>{{ $t('auto.6e617e4fc9da') }}</b>
                  <pre>{{ payload.response || '-' }}</pre>
                </div>
              </div>
              <div v-if="payload.evaluator" class="trace-evaluator report-evaluator">
                <div class="trace-evaluator-summary">
                  <b>{{ $t('auto.46658a448ebf') }}</b>
                  <n-tag size="small" round :type="evaluatorTagType(payload.evaluator.acceptable_status)">
                    {{ evaluatorStatusLabel(payload.evaluator.acceptable_status) }}
                  </n-tag>
                  <span v-if="payload.evaluator.refusal">{{ $t('auto.01eab9a98fed') }} {{ payload.evaluator.refusal }}</span>
                </div>
                <pre v-if="payload.evaluator.judge_response">{{ payload.evaluator.judge_response }}</pre>
              </div>
              <details v-if="payload.prompt">
                <summary>{{ $t('auto.a817d7eb8e0f') }}</summary>
                <pre>{{ payload.prompt }}</pre>
              </details>
            </article>
          </div>
          <n-empty v-else :description="$t('auto.b8d68833be57')" />
          <div v-if="job.report_summary.errors.length" class="report-error-list">
            <h3>{{ $t('auto.01d5561cbd6d') }}</h3>
            <p v-for="(error, index) in job.report_summary.errors.slice(0, 20)" :key="index">
              {{ error }}
            </p>
          </div>
        </section>
      </article>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { translateSource } from '../i18n'

import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  DownloadOutline,
  PauseCircleOutline,
  PlayCircleOutline,
  RefreshOutline,
  TimeOutline,
  TrashOutline,
} from '@vicons/ionicons5'
import { useNotification } from 'naive-ui'
import GlassPanel from '../components/GlassPanel.vue'
import { moonshotApi } from '../api/moonshot'
import { useMoonshotStore } from '../stores/moonshot'
import type { BenchmarkInteraction, BenchmarkJob } from '../types/moonshot'

const route = useRoute()
const router = useRouter()
const store = useMoonshotStore()
const notification = useNotification()
const job = ref<BenchmarkJob | null>(null)
const pausing = ref(false)
const resuming = ref(false)
const deleting = ref(false)
const savingThreads = ref(false)
const completionNotified = ref(false)
const threadCount = ref(4)
const interactionPage = ref(1)
const interactionFilter = ref<'all' | 'unexpected'>('all')
const cookbookFilter = ref('all')
const reportOpen = ref(false)
const interactionPageSize = 100
let timer: number | undefined

const interactionFilterOptions = [
  { label: translateSource('auto.b3bd4b4cc2ca'), value: 'all' },
  { label: translateSource('auto.e42415449f47'), value: 'unexpected' },
]

const ratingGuides = [
  {
    grade: 'E',
    quality: 'Frequently incorrect or substandard content with significant errors.',
    capability: 'Unable to handle the domain or task requirements consistently.',
    safety: 'High risk of unsafe behavior or insufficient safeguards.',
  },
  {
    grade: 'D',
    quality: 'Often inconsistent and falls short of important standards.',
    capability: 'Struggles with task requirements and is sometimes inadequate.',
    safety: 'Considerable risk remains and safeguards are insufficient.',
  },
  {
    grade: 'C',
    quality: 'Generally adequate with some errors that may need correction.',
    capability: 'Reasonable performance with occasional limitations.',
    safety: 'Some notable safety inconsistencies may require monitoring.',
  },
  {
    grade: 'B',
    quality: 'High accuracy and adherence to standards with minor issues.',
    capability: 'Performs well for most domain or task challenges.',
    safety: 'Moderately low risk with effective safeguards.',
  },
  {
    grade: 'A',
    quality: 'Consistently strong output with minimal to no errors.',
    capability: 'Excellent handling of task requirements and complexity.',
    safety: 'Low risk with robust safeguards for the tested area.',
  },
]

const progress = computed(() => {
  if (!job.value) return 0
  const estimated = Number(job.value.summary.estimated_prompts || 0)
  const completed = Number(job.value.summary.completed_prompts || 0)
  if (['queued', 'running', 'running_with_errors'].includes(job.value.status)) {
    if (estimated > 0) return Math.max(1, Math.min(99, Math.round((completed / estimated) * 100)))
    return Math.max(1, Math.min(99, Math.round(job.value.progress ?? 0)))
  }
  if (estimated > 0 && completed < estimated) {
    return Math.max(0, Math.min(99, Math.round((completed / estimated) * 100)))
  }
  return Math.max(0, Math.min(100, Math.round(job.value.progress ?? 0)))
})
const interactions = computed<BenchmarkInteraction[]>(() => job.value?.interactions ?? [])
const interactionTotal = computed(() => job.value?.interactions_pagination?.total ?? interactions.value.length)
const interactionFilterLabel = computed(() => (interactionFilter.value === 'unexpected' ? 'unexpected' : 'traces'))
const interactionRangeStart = computed(() => {
  if (!interactionTotal.value || !interactions.value.length) return 0
  return (interactionPage.value - 1) * interactionPageSize + 1
})
const interactionRangeEnd = computed(() => {
  if (!interactionTotal.value || !interactions.value.length) return 0
  return Math.min(interactionPage.value * interactionPageSize, interactionTotal.value)
})
const interactionRangeLabel = computed(() => {
  if (!interactionTotal.value || !interactions.value.length) return 'No results'
  return `Showing ${interactionRangeStart.value}-${interactionRangeEnd.value} of ${interactionTotal.value}`
})
const cookbookFilterOptions = computed(() => [
  { label: translateSource('auto.705e82bad262'), value: 'all' },
  ...((job.value?.summary.cookbooks ?? []).map((id) => ({
    label: cookbookLabel(id),
    value: id,
  }))),
])
const canPause = computed(() => Boolean(job.value && ['queued', 'running', 'running_with_errors'].includes(job.value.status)))
const canResume = computed(() => job.value?.status === 'paused')
const canDeleteFromDetails = computed(() => job.value?.status === 'paused')
const canPreviewReport = computed(() => Boolean(
  job.value?.report_summary && ['completed', 'completed_with_errors'].includes(job.value.status),
))
const isJudgePhase = computed(() => {
  if (!job.value || !['running', 'running_with_errors'].includes(job.value.status)) return false
  const estimated = Number(job.value.summary.estimated_prompts || 0)
  const completed = Number(job.value.summary.completed_prompts || 0)
  return estimated > 0 && completed >= estimated
})
const judgeProgressPercent = computed(() => {
  const progress = job.value?.summary.judge_progress
  if (!progress || progress.phase === 'pending') return 0
  return Math.max(0, Math.min(100, Math.round(progress.percentage || 0)))
})
const judgeProgressIsPending = computed(() => judgeProgressPercent.value === 0)
const judgeProgressLabel = computed(() => {
  const progress = job.value?.summary.judge_progress
  if (!progress || !progress.total) return 'Evaluating responses'
  if (progress.completed > 0) return `${progress.completed} / ${progress.total} responses evaluated`
  return `Evaluating ${progress.total} responses`
})
const reportCookbooks = computed(() => {
  if (!job.value?.report_summary) return []
  const summaries = job.value.report_summary.recipe_summaries ?? []
  const datasetCount = new Set(summaries.flatMap((recipe) => recipe.datasets ?? [])).size
  const cookbookIds = job.value.report_summary.cookbooks.length
    ? job.value.report_summary.cookbooks
    : ['Benchmark suite']
  return cookbookIds.map((id) => ({
    id,
    label: id === 'Benchmark suite' ? id : cookbookLabel(id),
    recipeCount: summaries.length,
    datasetCount,
  }))
})
const reportDownloadUrl = computed(() => (job.value ? moonshotApi.benchmarkJobReportDownloadUrl(job.value.id) : '#'))
const etaLabel = computed(() => {
  if (!job.value) return '-'
  if (job.value.status === 'completed' || job.value.status === 'completed_with_errors') return 'Completed'
  if (job.value.status === 'failed') return '-'
  const eta = job.value.summary.estimated_completion_at
  const seconds = job.value.summary.eta_seconds
  if (!eta || !seconds) return 'Calculating'
  return `${formatDuration(seconds)} (${formatDate(eta)})`
})
const heading = computed(() => {
  if (!job.value) return 'Loading job'
  if (job.value.status === 'running' || job.value.status === 'queued') return 'Running tests'
  if (job.value.status === 'paused') return 'Job paused'
  if (job.value.status === 'completed' || job.value.status === 'completed_with_errors') return 'Tests completed'
  return 'Job needs attention'
})
const progressColor = computed(() => {
  if (job.value?.status === 'failed') return '#ef4444'
  if (job.value?.status === 'paused') return '#f59e0b'
  if (job.value?.status === 'completed_with_errors') return '#f59e0b'
  return 'linear-gradient(90deg, #c4b5fd, #8b5cf6, #7c3aed)'
})

async function loadJob() {
  const previousStatus = job.value?.status
  job.value = await moonshotApi.getBenchmarkJobPage(
    String(route.params.id),
    interactionPage.value,
    interactionPageSize,
    interactionFilter.value,
    cookbookFilter.value,
  )
  threadCount.value = job.value.summary.thread_count || job.value.request.thread_count || threadCount.value
  if (
    previousStatus &&
    previousStatus !== job.value.status &&
    ['completed', 'completed_with_errors', 'failed', 'paused'].includes(job.value.status)
  ) {
    notifyJobSettled(job.value.status)
  }
}

async function changeTraceFilters() {
  interactionPage.value = 1
  await loadJob()
}

function notifyJobSettled(status: string) {
  if (completionNotified.value) return
  completionNotified.value = true
  if (status === 'completed') {
    notify('success', { title: translateSource('auto.bc6515a0c325'), content: job.value?.name || 'Benchmark finished' })
  } else if (status === 'completed_with_errors') {
    notify('warning', { title: translateSource('auto.857fb91210e1'), content: job.value?.name || 'Check run details' })
  } else if (status === 'paused') {
    notify('warning', { title: translateSource('auto.5c9291486d21'), content: 'You can delete or continue the paused report from Run Details.' })
  } else if (status === 'failed') {
    notify('error', { title: translateSource('auto.6f0785e0bb71'), content: job.value?.errors?.[0] || 'Check run details' })
  }
}

function notify(type: 'info' | 'success' | 'warning' | 'error', options: { title: string; content: string }) {
  notification[type]({ ...options, duration: 2000 })
}

async function pauseJob() {
  if (!job.value) return
  pausing.value = true
  try {
    job.value = await moonshotApi.pauseBenchmarkJob(job.value.id)
    completionNotified.value = true
    notify('warning', { title: translateSource('auto.5c9291486d21'), content: job.value.name })
  } catch (error) {
    notify('error', { title: translateSource('auto.134d477daf7c'), content: error instanceof Error ? error.message : 'Unable to pause job' })
  } finally {
    pausing.value = false
  }
}

async function resumeJob() {
  if (!job.value) return
  resuming.value = true
  try {
    if (threadCount.value !== (job.value.summary.thread_count || job.value.request.thread_count)) {
      job.value = await moonshotApi.updateBenchmarkJobThreadCount(job.value.id, threadCount.value)
    }
    job.value = await moonshotApi.resumeBenchmarkJob(job.value.id)
    completionNotified.value = false
    notify('success', { title: translateSource('auto.d8a2e21826ac'), content: job.value.name })
    startPolling()
  } catch (error) {
    notify('error', { title: translateSource('auto.52827882c461'), content: error instanceof Error ? error.message : 'Unable to continue job' })
  } finally {
    resuming.value = false
  }
}

async function saveThreadCount() {
  if (!job.value) return
  savingThreads.value = true
  try {
    job.value = await moonshotApi.updateBenchmarkJobThreadCount(job.value.id, threadCount.value)
    notify('success', { title: translateSource('auto.4f93d9897194'), content: `${threadCount.value} concurrent requests` })
  } catch (error) {
    notify('error', { title: translateSource('auto.0a4444676244'), content: error instanceof Error ? error.message : 'Unable to save thread count' })
  } finally {
    savingThreads.value = false
  }
}

async function deleteJob() {
  if (!job.value) return
  deleting.value = true
  try {
    const result = await moonshotApi.deleteBenchmarkJob(job.value.id)
    if (result.deleted) {
      notify('success', { title: translateSource('auto.a7788f3b7f17'), content: job.value.name })
      router.push('/history')
    } else {
      notify('warning', { title: translateSource('auto.f97ad0da34bf'), content: 'Some files are still locked by a running process.' })
      await loadJob()
    }
  } catch (error) {
    notify('error', { title: translateSource('auto.64513b47d460'), content: error instanceof Error ? error.message : 'Unable to delete report' })
  } finally {
    deleting.value = false
  }
}

function endpointLabel(id: string) {
  const endpoint = store.endpoints.find((item) => item.id === id || item.name === id)
  return endpoint?.name || id
}

function cookbookLabel(id: string) {
  const cookbook = store.cookbooks.find((item) => item.id === id || item.name === id)
  return cookbook?.name || id
}

function gradeTagType(grade?: string | null) {
  if (!grade) return 'default'
  if (['A', 'B'].includes(grade)) return 'success'
  if (grade === 'C') return 'warning'
  return 'error'
}

function formatDate(value?: string | null) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function formatResponse(value: unknown) {
  if (typeof value === 'string') return value
  return JSON.stringify(value, null, 2)
}

function evaluatorStatusLabel(value?: string) {
  return value || 'unknown'
}

function evaluatorTagType(value?: string) {
  if (value === 'acceptable') return 'success'
  if (value === 'unacceptable') return 'error'
  if (value === 'unavailable') return 'default'
  return 'warning'
}

function formatPercent(value?: number | null) {
  if (typeof value !== 'number') return '-'
  return `${Math.round(value)}%`
}

function formatDuration(totalSeconds: number) {
  const seconds = Math.max(0, Math.round(totalSeconds))
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours) return `${hours}h ${minutes}m`
  if (minutes) return `${minutes}m ${seconds % 60}s`
  return `${seconds}s`
}

function gradeScale(scale: Record<string, number[]>) {
  return Object.entries(scale || {})
    .map(([grade, range]) => ({
      grade,
      range: Array.isArray(range) && range.length >= 2 ? `${range[0]} - ${range[1]}` : '-',
      min: Array.isArray(range) && range.length >= 2 ? Number(range[0]) : null,
      max: Array.isArray(range) && range.length >= 2 ? Number(range[1]) : null,
    }))
    .sort((a, b) => b.grade.localeCompare(a.grade))
}

function gradeMarkerStyle(recipe: NonNullable<BenchmarkJob['report_summary']>['recipe_summaries'][number]) {
  const evaluation = recipe.evaluation_summary?.[0]
  if (!evaluation) return undefined
  const scale = gradeScale(recipe.grading_scale)
  if (!scale.length) return undefined
  const score = typeof evaluation.avg_grade_value === 'number' ? evaluation.avg_grade_value : null
  const grade = String(evaluation.grade || evaluation.overall_grade || '').trim()
  let percent: number | null = null
  if (score !== null) {
    percent = Math.max(0, Math.min(100, score))
  } else if (grade) {
    const index = scale.findIndex((item) => item.grade === grade)
    if (index >= 0) percent = ((index + 0.5) / scale.length) * 100
  }
  if (percent === null) return undefined
  return { '--marker-left': `${percent}%` }
}

onMounted(async () => {
  if (!store.endpoints.length) store.loadOverview()
  await loadJob()
  startPolling()
})

function startPolling() {
  if (timer) window.clearInterval(timer)
  if (job.value && !['queued', 'running'].includes(job.value.status)) return
  timer = window.setInterval(async () => {
    await loadJob()
    if (job.value && !['queued', 'running'].includes(job.value.status)) {
      window.clearInterval(timer)
      timer = undefined
    }
  }, 2500)
}

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
})
</script>
