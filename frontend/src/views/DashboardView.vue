<template>
  <div class="dashboard-grid">
    <section class="hero-band">
      <div class="hero-copy">
        <p class="eyebrow">Moonshot-native orchestration</p>
        <h2>
        <n-gradient-text gradient="linear-gradient(90deg, #c4b5fd, #8b5cf6, #7c3aed)">
            AI evaluation command center
          </n-gradient-text>
        </h2>
        <p>
          Monitor model endpoints, benchmark recipes, red-team modules, and run history from a
          single secure operations surface.
        </p>
      </div>
      <div class="signal-orbit">
        <span />
        <span />
        <span />
      </div>
    </section>

    <div class="metric-grid">
      <MetricCard label="Endpoints" :value="store.endpoints.length" hint="available targets" :icon="CubeOutline" />
      <MetricCard label="Recipes" :value="store.recipes.length" hint="benchmark flows" :icon="DocumentTextOutline" />
      <MetricCard label="Cookbooks" :value="store.cookbooks.length" hint="test suites" :icon="LibraryOutline" />
      <MetricCard label="Attack Modules" :value="store.attackModules.length" hint="red-team tools" :icon="ShieldCheckmarkOutline" />
    </div>

    <GlassPanel class="action-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Custom test suites</p>
          <h2>Create cookbooks</h2>
        </div>
      </div>
      <p class="action-copy">
        Combine the most relevant recipes into repeatable evaluation suites for regression,
        safety tuning, and targeted model checks.
      </p>
      <n-button type="primary" round @click="$router.push('/cookbooks')">
        <template #icon><n-icon><BookOutline /></n-icon></template>
        Select Recipes
      </n-button>
    </GlassPanel>

    <GlassPanel class="wide-panel">
      <div class="section-heading">
        <div>
          <p class="eyebrow">Operational readiness</p>
          <h2>Testing inventory</h2>
        </div>
        <n-tag :type="store.health === 'ok' ? 'success' : 'warning'" :bordered="false">
          {{ store.health }}
        </n-tag>
      </div>
      <div class="inventory-bars">
        <div v-for="item in inventory" :key="item.label" class="inventory-row">
          <span>{{ item.label }}</span>
          <n-progress
            type="line"
            :percentage="item.percent"
            :show-indicator="false"
            color="linear-gradient(90deg, #c4b5fd, #8b5cf6, #7c3aed)"
          />
          <strong>{{ item.value }}</strong>
        </div>
      </div>
    </GlassPanel>

    <GlassPanel>
      <div class="section-heading">
        <div>
          <p class="eyebrow">Running jobs</p>
          <h2>Execution context</h2>
        </div>
      </div>
      <n-list v-if="activeJobs.length">
        <n-list-item v-for="job in activeJobs" :key="job.id">
          <div class="dashboard-job-row">
            <n-thing :title="job.name" :description="`${job.summary.completed_prompts} / ${job.summary.estimated_prompts || '-'} prompts`">
              <template #avatar>
                <n-icon size="22"><RadioButtonOnOutline /></n-icon>
              </template>
            </n-thing>
            <n-button secondary round size="small" @click="$router.push(`/jobs/${job.id}`)">Details</n-button>
          </div>
        </n-list-item>
      </n-list>
      <n-empty v-else description="No running jobs" />
    </GlassPanel>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  BookOutline,
  CubeOutline,
  DocumentTextOutline,
  LibraryOutline,
  RadioButtonOnOutline,
  ShieldCheckmarkOutline,
} from '@vicons/ionicons5'
import GlassPanel from '../components/GlassPanel.vue'
import MetricCard from '../components/MetricCard.vue'
import { useMoonshotStore } from '../stores/moonshot'

const store = useMoonshotStore()

const inventory = computed(() => {
  const values = [
    { label: 'Datasets', value: store.datasets.length },
    { label: 'Metrics', value: store.metrics.length },
    { label: 'Connectors', value: store.connectorTypes.length },
    { label: 'Results', value: store.results.length },
  ]
  const max = Math.max(...values.map((item) => item.value), 1)
  return values.map((item) => ({ ...item, percent: Math.max(6, Math.round((item.value / max) * 100)) }))
})

const activeJobs = computed(() => store.jobs.filter((job) => ['queued', 'running'].includes(job.status)))
</script>
