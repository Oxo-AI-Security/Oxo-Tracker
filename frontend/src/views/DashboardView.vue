<template>
  <div class="dashboard-grid dashboard-command-center">
    <section class="hero-band dashboard-overview">
      <div class="hero-copy dashboard-overview__copy">
        <div class="dashboard-hero-kicker-row">
          <div class="dashboard-hero-kicker">
            <span class="dashboard-hero-kicker__icon">
              <n-icon><SparklesOutline /></n-icon>
            </span>
            <span>
              <small>AI security operations</small>
              <strong>Workspace command center</strong>
            </span>
          </div>
          <span class="dashboard-health-pill" :class="store.health === 'ok' ? 'is-success' : 'is-warning'">
            <span class="dashboard-health-pill__dot" />
            {{ healthLabel }}
          </span>
        </div>

        <div class="dashboard-hero-message">
          <h2>Oxo Tracker <span>Center</span></h2>
          <p class="dashboard-overview__lead">
            See your targets, test coverage, red-team assets, and execution readiness in one
            connected AI security workspace.
          </p>
        </div>

        <div class="dashboard-hero-actions">
          <n-button type="primary" round @click="go('/benchmark')">
            <template #icon><n-icon><PlayCircleOutline /></n-icon></template>
            Run security test
          </n-button>
          <n-button secondary round @click="go('/agents')">
            Review agent workspace
            <template #icon><n-icon><ArrowForwardOutline /></n-icon></template>
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
        <div class="dashboard-evaluation-flow" aria-label="Evaluation pipeline overview">
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
      <aside class="dashboard-overview__status" aria-label="Workspace status">
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
          <p class="eyebrow">Operational readiness</p>
          <h2>Testing inventory</h2>
          <span class="dashboard-section-copy">Coverage assets available for repeatable model checks.</span>
        </div>
        <div class="dashboard-readiness-badge">
          <strong>{{ readinessScore }}%</strong>
          <span>ready</span>
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
          <p class="eyebrow">Custom test suites</p>
          <h2>Create cookbooks</h2>
          <span class="dashboard-section-copy">Package recipe coverage into reusable suites.</span>
        </div>
        <span class="dashboard-panel-icon">
          <n-icon size="22"><LayersOutline /></n-icon>
        </span>
      </div>
      <p class="action-copy">
        Combine recipes into repeatable evaluation suites for regression, safety tuning, and
        targeted model checks.
      </p>
      <div class="dashboard-cookbook-summary">
        <article role="button" tabindex="0" @click="go('/payload/cookbooks')" @keyup.enter="go('/payload/cookbooks')">
          <span>Suites</span>
          <strong>{{ store.cookbooks.length }}</strong>
        </article>
        <article role="button" tabindex="0" @click="go('/payload/recipes')" @keyup.enter="go('/payload/recipes')">
          <span>Recipes</span>
          <strong>{{ store.recipes.length }}</strong>
        </article>
      </div>
      <n-button type="primary" round @click="$router.push('/cookbooks')">
        <template #icon><n-icon><BookOutline /></n-icon></template>
        Select Recipes
      </n-button>
    </GlassPanel>

    <GlassPanel class="dashboard-running-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Running jobs</p>
          <h2>Execution context</h2>
          <span class="dashboard-section-copy">Live runs, prompt progress, and result traceability.</span>
        </div>
        <n-button secondary round size="small" @click="$router.push('/benchmark')">
          <template #icon><n-icon><PlayCircleOutline /></n-icon></template>
          Run Test
        </n-button>
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
            <n-button secondary round size="small" @click.stop="$router.push(`/jobs/${job.id}`)">Details</n-button>
          </div>
        </n-list-item>
      </n-list>
      <n-empty v-else description="No running jobs">
        <template #extra>
          <n-button secondary round @click="$router.push('/benchmark')">
            <template #icon><n-icon><PlayCircleOutline /></n-icon></template>
            Launch benchmark
          </n-button>
        </template>
      </n-empty>
    </GlassPanel>
  </div>
</template>

<script setup lang="ts">
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
  SparklesOutline,
} from '@vicons/ionicons5'
import GlassPanel from '../components/GlassPanel.vue'
import MetricCard from '../components/MetricCard.vue'
import { useMoonshotStore } from '../stores/moonshot'

const store = useMoonshotStore()
const router = useRouter()

const healthLabel = computed(() => store.health === 'ok' ? 'Operational' : 'Needs review')

const heroStats = computed(() => [
  { label: 'tracked assets', value: store.totalAssets, path: '/payload', tone: 'is-primary' },
  { label: 'attack modules', value: store.attackModules.length, path: '/agents', tone: 'is-neutral' },
  { label: 'active executions', value: activeJobs.value.length, path: executionRoute.value, tone: 'is-neutral' },
])

const metricCards = computed(() => [
  { label: 'Endpoints', value: store.endpoints.length, hint: 'available targets', icon: CubeOutline, path: '/agents', tone: 'violet' },
  { label: 'Recipes', value: store.recipes.length, hint: 'benchmark flows', icon: DocumentTextOutline, path: '/payload/recipes', tone: 'cyan' },
  { label: 'Cookbooks', value: store.cookbooks.length, hint: 'test suites', icon: LibraryOutline, path: '/payload/cookbooks', tone: 'green' },
  { label: 'Attack Modules', value: store.attackModules.length, hint: 'red-team tools', icon: ShieldCheckmarkOutline, path: '/agents', tone: 'amber' },
])

const inventory = computed(() => {
  const values = [
    { label: 'Datasets', value: store.datasets.length, path: '/payload/datasets', color: '#7c3aed' },
    { label: 'Metrics', value: store.metrics.length, path: '/benchmark', color: '#0284c7' },
    { label: 'Connectors', value: store.connectorTypes.length, path: '/agents/connectors', color: '#16a34a' },
    { label: 'Results', value: store.results.length, path: '/history', color: '#f59e0b' },
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
    label: 'Platform health',
    value: healthLabel.value,
    hint: `${store.health} service response`,
    path: '/settings',
    icon: store.health === 'ok' ? CheckmarkCircleOutline : ShieldCheckmarkOutline,
    tone: store.health === 'ok' ? 'is-success' : 'is-warning',
    color: '#16a34a',
  },
  {
    label: 'Readiness score',
    value: `${readinessScore.value}%`,
    hint: 'inventory checks passing',
    path: '/benchmark',
    icon: SpeedometerOutline,
    tone: 'is-brand',
    progress: readinessScore.value,
    color: '#7c3aed',
  },
  {
    label: 'Active executions',
    value: activeJobs.value.length,
    hint: `${store.jobs.length} total runs indexed`,
    path: executionRoute.value,
    icon: PulseOutline,
    tone: activeJobs.value.length ? 'is-live' : 'is-muted',
    color: '#0284c7',
  },
])

const readinessSignals = computed(() => [
  { label: 'Prompt templates', value: store.promptTemplates.length, path: '/payload/prompt-templates' },
  { label: 'Runners', value: store.runners.length, path: '/benchmark' },
  { label: 'Results', value: store.results.length, path: '/history' },
])

const evaluationFlow = computed(() => [
  { label: 'Targets', value: store.endpoints.length, hint: 'Endpoints ready', path: '/agents', tone: 'is-violet' },
  { label: 'Coverage', value: store.recipes.length, hint: 'Recipes mapped', path: '/payload/recipes', tone: 'is-cyan' },
  { label: 'Suites', value: store.cookbooks.length, hint: 'Cookbooks built', path: '/payload/cookbooks', tone: 'is-green' },
  { label: 'Evidence', value: store.results.length, hint: 'Results captured', path: '/history', tone: 'is-amber' },
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
