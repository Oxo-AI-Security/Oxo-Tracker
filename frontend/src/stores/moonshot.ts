import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { moonshotApi } from '../api/moonshot'
import type {
  CookbookRecord,
  EndpointRecord,
  RecipeRecord,
  PromptTemplateRecord,
  DatasetRecord,
  ResourceRecord,
  RunnerRecord,
  BenchmarkJob,
} from '../types/moonshot'

export const useMoonshotStore = defineStore('moonshot', () => {
  const loading = ref(false)
  const error = ref('')
  const health = ref('unknown')
  const connectorTypes = ref<string[]>([])
  const endpoints = ref<EndpointRecord[]>([])
  const recipes = ref<RecipeRecord[]>([])
  const cookbooks = ref<CookbookRecord[]>([])
  const metrics = ref<ResourceRecord[]>([])
  const promptTemplates = ref<PromptTemplateRecord[]>([])
  const datasets = ref<DatasetRecord[]>([])
  const attackModules = ref<string[]>([])
  const runners = ref<RunnerRecord[]>([])
  const results = ref<ResourceRecord[]>([])
  const jobs = ref<BenchmarkJob[]>([])

  const totalAssets = computed(
    () =>
      endpoints.value.length +
      recipes.value.length +
      cookbooks.value.length +
      metrics.value.length +
      promptTemplates.value.length +
      datasets.value.length +
      attackModules.value.length,
  )

  function upsertJob(job: BenchmarkJob) {
    const index = jobs.value.findIndex((item) => (
      item.id.toLocaleLowerCase() === job.id.toLocaleLowerCase()
      || item.runner_id.toLocaleLowerCase() === job.runner_id.toLocaleLowerCase()
    ))
    if (index >= 0) jobs.value.splice(index, 1, job)
    else jobs.value.unshift(job)
  }

  async function loadOverview() {
    loading.value = true
    error.value = ''
    try {
      const settled = await Promise.allSettled([
        moonshotApi.health(),
        moonshotApi.getConnectorTypes(),
        moonshotApi.getEndpoints(),
        moonshotApi.getRecipes(),
        moonshotApi.getCookbooks(),
        moonshotApi.getMetrics(),
        moonshotApi.getPromptTemplates(),
        moonshotApi.getDatasets(),
        moonshotApi.getAttackModules(),
        moonshotApi.getRunners(),
        moonshotApi.getResults(),
        moonshotApi.getBenchmarkJobs(),
      ])

      const [
        healthData,
        connectorData,
        endpointData,
        recipeData,
        cookbookData,
        metricData,
        promptTemplateData,
        datasetData,
        attackData,
        runnerData,
        resultData,
        jobData,
      ] = settled

      if (healthData.status === 'fulfilled') health.value = healthData.value.status
      if (connectorData.status === 'fulfilled') connectorTypes.value = connectorData.value
      if (endpointData.status === 'fulfilled') endpoints.value = endpointData.value
      if (recipeData.status === 'fulfilled') recipes.value = recipeData.value
      if (cookbookData.status === 'fulfilled') cookbooks.value = cookbookData.value
      if (metricData.status === 'fulfilled') metrics.value = metricData.value
      if (promptTemplateData.status === 'fulfilled') promptTemplates.value = promptTemplateData.value
      if (datasetData.status === 'fulfilled') datasets.value = datasetData.value
      if (attackData.status === 'fulfilled') attackModules.value = attackData.value
      if (runnerData.status === 'fulfilled') runners.value = runnerData.value
      if (resultData.status === 'fulfilled') results.value = resultData.value
      if (jobData.status === 'fulfilled') jobs.value = jobData.value

      const failures = settled.filter((item) => item.status === 'rejected')
      if (failures.length) {
        error.value = `${failures.length} resource request(s) failed. Available data is still shown.`
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Load failed'
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    health,
    connectorTypes,
    endpoints,
    recipes,
    cookbooks,
    metrics,
    promptTemplates,
    datasets,
    attackModules,
    runners,
    results,
    jobs,
    totalAssets,
    upsertJob,
    loadOverview,
  }
})
