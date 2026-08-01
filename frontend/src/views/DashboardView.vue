<template>
  <div class="dashboard-grid dashboard-command-center">
    <section class="hero-band dashboard-overview">
      <div class="hero-copy dashboard-overview__copy">
        <div class="dashboard-hero-message">
          <div class="dashboard-title-row">
            <h2 class="dashboard-brand-title">
              <img class="dashboard-brand-title__mark" :src="oxoLogoMark" alt="Oxo" />
              <span class="dashboard-brand-title__name">Tracker</span>
              <span class="dashboard-brand-title__accent">{{ $t('auto.a2391118c814') }}</span>
            </h2>
            <span class="dashboard-health-pill" :class="store.health === 'ok' ? 'is-success' : 'is-warning'">
              <span class="dashboard-health-pill__dot" />
              {{ healthLabel }}
            </span>
          </div>
        </div>

        <div class="dashboard-hero-actions">
          <n-button type="primary" round @click="go('/benchmark')">
            <template #icon><n-icon><PlayCircleOutline /></n-icon></template> {{ $t('auto.0cc0a3c58092') }} </n-button>
          <n-button secondary round @click="go('/agents')"> {{ $t('auto.93286e82b3e7') }} <template #icon><n-icon><ArrowForwardOutline /></n-icon></template>
          </n-button>
        </div>

        <div class="dashboard-overview__meta">
          <button
            v-for="item in heroStats"
            :key="item.label"
            type="button"
            :class="item.tone"
            @click="go(item.path)"
          >
            <strong>{{ item.value }}</strong>
            <span>{{ item.label }}</span>
          </button>
        </div>
        <div class="dashboard-evaluation-flow" :aria-label="$t('auto.ed70bcc3ec84')">
          <article
            v-for="stage in evaluationFlow"
            :key="stage.label"
            :class="stage.tone"
            role="button"
            tabindex="0"
            @click="go(stage.path)"
            @keyup.enter="go(stage.path)"
          >
            <div class="dashboard-stage-head">
              <span class="dashboard-stage-dot" />
              <span>{{ stage.label }}</span>
            </div>
            <strong>{{ stage.value }}</strong>
            <small>{{ stage.hint }}</small>
          </article>
        </div>
      </div>
      <aside class="dashboard-overview__status" :aria-label="$t('auto.1de2026cd37a')">
        <button
          v-for="card in statusCards"
          :key="card.label"
          type="button"
          class="dashboard-status-card"
          :class="card.tone"
          @click="go(card.path)"
        >
          <span class="dashboard-status-icon">
            <n-icon size="20"><component :is="card.icon" /></n-icon>
          </span>
          <span class="dashboard-status-copy">
            <small>{{ card.label }}</small>
            <strong>{{ card.value }}</strong>
            <em>{{ card.hint }}</em>
          </span>
          <span
            v-if="card.progress !== undefined"
            class="dashboard-status-meter"
            aria-hidden="true"
          >
            <span :style="{ width: `${card.progress}%`, backgroundColor: card.color }" />
          </span>
        </button>
      </aside>
    </section>

    <div class="metric-grid">
      <MetricCard
        v-for="metric in metricCards"
        :key="metric.label"
        :class="`metric-card--${metric.tone}`"
        :label="metric.label"
        :value="metric.value"
        :hint="metric.hint"
        :icon="metric.icon"
        role="button"
        tabindex="0"
        @click="go(metric.path)"
        @keyup.enter="go(metric.path)"
      />
    </div>

    <GlassPanel class="wide-panel dashboard-inventory-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">{{ $t('auto.f83f304269b7') }}</p>
          <h2>{{ $t('auto.764cfef3dbd6') }}</h2>
          <span class="dashboard-section-copy">{{ $t('auto.0b31e177e2e2') }}</span>
        </div>
        <div class="dashboard-readiness-badge">
          <strong>{{ readinessScore }}%</strong>
          <span>{{ $t('auto.75c0533730ca') }}</span>
        </div>
      </div>
      <div class="inventory-bars">
        <div
          v-for="item in inventory"
          :key="item.label"
          class="inventory-row"
          role="button"
          tabindex="0"
          @click="go(item.path)"
          @keyup.enter="go(item.path)"
        >
          <span>{{ item.label }}</span>
          <n-progress
            type="line"
            :percentage="item.percent"
            :show-indicator="false"
            :color="item.color"
          />
          <strong>{{ item.value }}</strong>
        </div>
      </div>
      <div class="dashboard-signal-grid">
        <article
          v-for="signal in readinessSignals"
          :key="signal.label"
          role="button"
          tabindex="0"
          @click="go(signal.path)"
          @keyup.enter="go(signal.path)"
        >
          <span>{{ signal.label }}</span>
          <strong>{{ signal.value }}</strong>
        </article>
      </div>
    </GlassPanel>

    <GlassPanel class="action-panel dashboard-cookbook-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">{{ $t('auto.a5668d82a6af') }}</p>
          <h2>{{ $t('auto.b1f87c13d22a') }}</h2>
          <span class="dashboard-section-copy">{{ $t('auto.c5e87685d36d') }}</span>
        </div>
        <span class="dashboard-panel-icon">
          <n-icon size="22"><LayersOutline /></n-icon>
        </span>
      </div>
      <p class="action-copy"> {{ $t('auto.e34a322b0ffd') }} </p>
      <div class="dashboard-cookbook-summary">
        <article role="button" tabindex="0" @click="go('/payload/cookbooks')" @keyup.enter="go('/payload/cookbooks')">
          <span>{{ $t('auto.b4e883d3f0f5') }}</span>
          <strong>{{ store.cookbooks.length }}</strong>
        </article>
        <article role="button" tabindex="0" @click="go('/payload/recipes')" @keyup.enter="go('/payload/recipes')">
          <span>{{ $t('auto.9fb1092f32d4') }}</span>
          <strong>{{ store.recipes.length }}</strong>
        </article>
      </div>
      <n-button type="primary" round @click="$router.push('/cookbooks')">
        <template #icon><n-icon><BookOutline /></n-icon></template> {{ $t('auto.8c6097271482') }} </n-button>
    </GlassPanel>

    <GlassPanel class="dashboard-running-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">{{ $t('auto.f1d16117039b') }}</p>
          <h2>{{ $t('auto.90e52bd11234') }}</h2>
          <span class="dashboard-section-copy">{{ $t('auto.4f2c47aef26d') }}</span>
        </div>
        <n-button secondary round size="small" @click="$router.push('/benchmark')">
          <template #icon><n-icon><PlayCircleOutline /></n-icon></template> {{ $t('auto.e90380fee41d') }} </n-button>
      </div>
      <n-list v-if="activeJobs.length">
        <n-list-item v-for="job in activeJobs" :key="job.id">
          <div
            class="dashboard-job-row"
            role="button"
            tabindex="0"
            @click="go(`/jobs/${job.id}`)"
            @keyup.enter="go(`/jobs/${job.id}`)"
          >
            <n-thing :title="job.name" :description="`${job.summary.completed_prompts} / ${job.summary.estimated_prompts || '-'} prompts`">
              <template #avatar>
                <n-icon size="22"><RadioButtonOnOutline /></n-icon>
              </template>
            </n-thing>
            <n-progress
              class="dashboard-job-progress"
              type="line"
              :percentage="jobProgress(job)"
              :show-indicator="false"
              color="#7c3aed"
            />
            <n-button secondary round size="small" @click.stop="$router.push(`/jobs/${job.id}`)">{{ $t('auto.dc3decbb9384') }}</n-button>
          </div>
        </n-list-item>
      </n-list>
      <n-empty v-else :description="$t('auto.4ce624630f29')">
        <template #extra>
          <n-button secondary round @click="$router.push('/benchmark')">
            <template #icon><n-icon><PlayCircleOutline /></n-icon></template> {{ $t('auto.5acc3de3f87c') }} </n-button>
        </template>
      </n-empty>
    </GlassPanel>
  </div>
</template>

<script setup lang="ts">
import { translateSource } from '../i18n'

import { computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowForwardOutline,
  BookOutline,
  CheckmarkCircleOutline,
  CubeOutline,
  DocumentTextOutline,
  LibraryOutline,
  LayersOutline,
  PlayCircleOutline,
  PulseOutline,
  RadioButtonOnOutline,
  ShieldCheckmarkOutline,
  SpeedometerOutline,
} from '@vicons/ionicons5'
import GlassPanel from '../components/GlassPanel.vue'
import MetricCard from '../components/MetricCard.vue'
import oxoLogoMark from '../assets/oxo-logo-mark.png'
import { useMoonshotStore } from '../stores/moonshot'

const store = useMoonshotStore()
const router = useRouter()

const healthLabel = computed(() => (
  store.health === 'ok'
    ? translateSource('dashboard.operational')
    : translateSource('dashboard.needsReview')
))

const heroStats = computed(() => [
  { label: translateSource('dashboard.trackedAssets'), value: store.totalAssets, path: '/payload', tone: 'is-primary' },
  { label: translateSource('dashboard.attackModules'), value: store.attackModules.length, path: '/agents', tone: 'is-neutral' },
  { label: translateSource('dashboard.activeExecutions'), value: activeJobs.value.length, path: executionRoute.value, tone: 'is-neutral' },
])

const metricCards = computed(() => [
  { label: translateSource('dashboard.endpoints'), value: store.endpoints.length, hint: translateSource('auto.d234acb5d45b'), icon: CubeOutline, path: '/agents', tone: 'violet' },
  { label: translateSource('dashboard.recipes'), value: store.recipes.length, hint: translateSource('auto.e9d090fce6d7'), icon: DocumentTextOutline, path: '/payload/recipes', tone: 'cyan' },
  { label: translateSource('dashboard.cookbooks'), value: store.cookbooks.length, hint: translateSource('auto.de989574990d'), icon: LibraryOutline, path: '/payload/cookbooks', tone: 'green' },
  { label: translateSource('auto.2c953374a7b3'), value: store.attackModules.length, hint: translateSource('auto.9f2fd1154e8d'), icon: ShieldCheckmarkOutline, path: '/agents', tone: 'amber' },
])

const inventory = computed(() => {
  const values = [
    { label: translateSource('dashboard.datasets'), value: store.datasets.length, path: '/payload/datasets', color: '#7c3aed' },
    { label: translateSource('dashboard.metrics'), value: store.metrics.length, path: '/benchmark', color: '#0284c7' },
    { label: translateSource('dashboard.connectors'), value: store.connectorTypes.length, path: '/agents/connectors', color: '#16a34a' },
    { label: translateSource('dashboard.results'), value: store.results.length, path: '/history', color: '#f59e0b' },
  ]
  const max = Math.max(...values.map((item) => item.value), 1)
  return values.map((item) => ({ ...item, percent: Math.max(6, Math.round((item.value / max) * 100)) }))
})

const activeJobs = computed(() => store.jobs.filter((job) => ['queued', 'running'].includes(job.status)))

const executionRoute = computed(() => activeJobs.value[0] ? `/jobs/${activeJobs.value[0].id}` : '/history')

const readinessScore = computed(() => {
  const checks = [
    store.health === 'ok',
    store.endpoints.length > 0,
    store.recipes.length > 0,
    store.cookbooks.length > 0,
    store.datasets.length > 0,
    store.metrics.length > 0,
  ]
  return Math.round((checks.filter(Boolean).length / checks.length) * 100)
})

const statusCards = computed(() => [
  {
    label: translateSource('auto.d7fe0239bb1a'),
    value: healthLabel.value,
    hint: translateSource('dashboard.serviceResponse', { status: store.health }),
    path: '/settings',
    icon: store.health === 'ok' ? CheckmarkCircleOutline : ShieldCheckmarkOutline,
    tone: store.health === 'ok' ? 'is-success' : 'is-warning',
    color: '#16a34a',
  },
  {
    label: translateSource('auto.041f08dbc430'),
    value: `${readinessScore.value}%`,
    hint: translateSource('auto.d29e8a1eafde'),
    path: '/benchmark',
    icon: SpeedometerOutline,
    tone: 'is-brand',
    progress: readinessScore.value,
    color: '#7c3aed',
  },
  {
    label: translateSource('dashboard.activeExecutions'),
    value: activeJobs.value.length,
    hint: translateSource('dashboard.totalRuns', { count: store.jobs.length }),
    path: executionRoute.value,
    icon: PulseOutline,
    tone: activeJobs.value.length ? 'is-live' : 'is-muted',
    color: '#0284c7',
  },
])

const readinessSignals = computed(() => [
  { label: translateSource('auto.69ba249d0c70'), value: store.promptTemplates.length, path: '/payload/prompt-templates' },
  { label: translateSource('dashboard.runners'), value: store.runners.length, path: '/benchmark' },
  { label: translateSource('dashboard.results'), value: store.results.length, path: '/history' },
])

const evaluationFlow = computed(() => [
  { label: translateSource('dashboard.targets'), value: store.endpoints.length, hint: translateSource('auto.49ea0431b96e'), path: '/agents', tone: 'is-violet' },
  { label: translateSource('dashboard.coverage'), value: store.recipes.length, hint: translateSource('auto.7a35b61269e2'), path: '/payload/recipes', tone: 'is-cyan' },
  { label: translateSource('dashboard.suites'), value: store.cookbooks.length, hint: translateSource('auto.5139fed70dc3'), path: '/payload/cookbooks', tone: 'is-green' },
  { label: translateSource('dashboard.evidence'), value: store.results.length, hint: translateSource('auto.56c87f2714bf'), path: '/history', tone: 'is-amber' },
])

function go(path: string) {
  router.push(path)
}

function jobProgress(job: { summary: { completed_prompts: number; estimated_prompts?: number } }) {
  const estimated = job.summary.estimated_prompts || 0
  if (!estimated) return 8
  return Math.min(100, Math.round((job.summary.completed_prompts / estimated) * 100))
}
</script>
