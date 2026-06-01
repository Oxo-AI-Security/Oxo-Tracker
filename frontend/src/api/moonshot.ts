import { http } from './http'
import type {
  BenchmarkRecipeRequest,
  BenchmarkJob,
  BenchmarkRunResponse,
  CookbookRecord,
  CookbookCreatePayload,
  CookbookUpdatePayload,
  EndpointCreatePayload,
  EndpointUpdatePayload,
  EndpointRecord,
  RecipeRecord,
  RecipeCreatePayload,
  RecipeUpdatePayload,
  ResourceRecord,
  PromptTemplateRecord,
  DatasetRecord,
  DatasetCreatePayload,
  DatasetUpdatePayload,
  RunnerRecord,
  AppSettings,
} from '../types/moonshot'

export const moonshotApi = {
  async health() {
    const { data } = await http.get<{ status: string }>('/health')
    return data
  },
  async getConnectorTypes() {
    const { data } = await http.get<string[]>('/api/v1/moonshot/connectors/types')
    return data
  },
  async getEndpoints() {
    const { data } = await http.get<EndpointRecord[]>('/api/v1/moonshot/endpoints')
    return data
  },
  async createEndpoint(payload: EndpointCreatePayload) {
    const { data } = await http.post<string>('/api/v1/moonshot/endpoints', payload)
    return data
  },
  async updateEndpoint(id: string, payload: EndpointUpdatePayload) {
    const { data } = await http.patch<boolean>(`/api/v1/moonshot/endpoints/${encodeURIComponent(id)}`, payload)
    return data
  },
  async deleteEndpoint(id: string) {
    const { data } = await http.delete<boolean>(`/api/v1/moonshot/endpoints/${encodeURIComponent(id)}`)
    return data
  },
  async testConnector(config: unknown, testPrompt: string) {
    const { data } = await http.post<{
      status: 'success' | 'error'
      duration: number
      requestPreview: string
      rawResponse: string
      extractedResponse: string
      error?: string
    }>('/api/v1/moonshot/connectors/test', { config, test_prompt: testPrompt })
    return data
  },
  async getRecipes() {
    const { data } = await http.get<RecipeRecord[]>('/api/v1/moonshot/recipes')
    return data
  },
  async createRecipe(payload: RecipeCreatePayload) {
    const { data } = await http.post<string>('/api/v1/moonshot/recipes', payload)
    return data
  },
  async updateRecipe(id: string, payload: RecipeUpdatePayload) {
    const { data } = await http.patch<boolean>(`/api/v1/moonshot/recipes/${encodeURIComponent(id)}`, payload)
    return data
  },
  async deleteRecipe(id: string) {
    const { data } = await http.delete<boolean>(`/api/v1/moonshot/recipes/${encodeURIComponent(id)}`)
    return data
  },
  async getCookbooks() {
    const { data } = await http.get<CookbookRecord[]>('/api/v1/moonshot/cookbooks')
    return data
  },
  async createCookbook(payload: CookbookCreatePayload) {
    const { data } = await http.post<string>('/api/v1/moonshot/cookbooks', payload)
    return data
  },
  async updateCookbook(id: string, payload: CookbookUpdatePayload) {
    const { data } = await http.patch<boolean>(`/api/v1/moonshot/cookbooks/${encodeURIComponent(id)}`, payload)
    return data
  },
  async deleteCookbook(id: string) {
    const { data } = await http.delete<boolean>(`/api/v1/moonshot/cookbooks/${encodeURIComponent(id)}`)
    return data
  },
  async getMetrics() {
    const { data } = await http.get<ResourceRecord[]>('/api/v1/moonshot/metrics')
    return data
  },
  async getPromptTemplates() {
    const { data } = await http.get<PromptTemplateRecord[]>('/api/v1/moonshot/prompt-templates')
    return data
  },
  async createPromptTemplate(payload: { name: string; description: string; template: string }) {
    const { data } = await http.post<string>('/api/v1/moonshot/prompt-templates', payload)
    return data
  },
  async deletePromptTemplate(id: string) {
    const { data } = await http.delete<boolean>(`/api/v1/moonshot/prompt-templates/${encodeURIComponent(id)}`)
    return data
  },
  async getDatasets() {
    const { data } = await http.get<DatasetRecord[]>('/api/v1/moonshot/datasets')
    return data
  },
  async getDataset(id: string, limit = 25) {
    const { data } = await http.get<DatasetRecord>(`/api/v1/moonshot/datasets/${encodeURIComponent(id)}`, {
      params: { limit },
    })
    return data
  },
  async createDataset(payload: DatasetCreatePayload) {
    const { data } = await http.post<string>('/api/v1/moonshot/datasets', payload)
    return data
  },
  async updateDataset(id: string, payload: DatasetUpdatePayload) {
    const { data } = await http.patch<boolean>(`/api/v1/moonshot/datasets/${encodeURIComponent(id)}`, payload)
    return data
  },
  async deleteDataset(id: string) {
    const { data } = await http.delete<boolean>(`/api/v1/moonshot/datasets/${encodeURIComponent(id)}`)
    return data
  },
  async getAttackModules() {
    const { data } = await http.get<string[]>('/api/v1/moonshot/attack-modules')
    return data
  },
  async createRedTeamSession(payload: {
    name: string
    description: string
    endpoints: string[]
    runner_args: Record<string, unknown>
  }) {
    const { data } = await http.post<{ runner_id: string; name: string; description: string; endpoints: string[] }>(
      '/api/v1/moonshot/redteam/sessions',
      payload,
    )
    return data
  },
  async prepareRedTeamPrompt(payload: {
    prompt: string
    prompt_template: string
    attack_module: string
  }) {
    const { data } = await http.post<{
      original_prompt: string
      templated_prompt: string
      prepared_prompt: string
      prompt_template: string
      attack_module: string
    }>('/api/v1/moonshot/redteam/prepare-prompt', payload)
    return data
  },
  async sendRedTeamPrompt(runnerId: string, userPrompt: string, preparedPrompt = '') {
    const { data } = await http.post<unknown>(
      `/api/v1/moonshot/redteam/sessions/${encodeURIComponent(runnerId)}/prompt`,
      { user_prompt: userPrompt, prepared_prompt: preparedPrompt },
    )
    return data
  },
  async getLocalRedTeamSessions() {
    const { data } = await http.get<unknown[]>('/api/v1/moonshot/redteam/local-sessions')
    return data
  },
  async saveLocalRedTeamSession(sessionId: string, payload: unknown) {
    const { data } = await http.put<{ saved: boolean; session_id: string }>(
      `/api/v1/moonshot/redteam/local-sessions/${encodeURIComponent(sessionId)}`,
      payload,
    )
    return data
  },
  async deleteLocalRedTeamSession(sessionId: string) {
    const { data } = await http.delete<{ deleted: boolean; session_id: string }>(
      `/api/v1/moonshot/redteam/local-sessions/${encodeURIComponent(sessionId)}`,
    )
    return data
  },
  async updateSessionAttackModule(runnerId: string, attackModuleId: string) {
    const { data } = await http.patch<boolean>(
      `/api/v1/moonshot/sessions/${encodeURIComponent(runnerId)}/attack-module`,
      { attack_module_id: attackModuleId },
    )
    return data
  },
  async updateSessionPromptTemplate(runnerId: string, promptTemplate: string) {
    const { data } = await http.patch<boolean>(
      `/api/v1/moonshot/sessions/${encodeURIComponent(runnerId)}/prompt-template`,
      { prompt_template: promptTemplate },
    )
    return data
  },
  async updateSessionContextStrategy(runnerId: string, contextStrategy: string) {
    const { data } = await http.patch<boolean>(
      `/api/v1/moonshot/sessions/${encodeURIComponent(runnerId)}/context-strategy`,
      { context_strategy: contextStrategy },
    )
    return data
  },
  async getRunners() {
    const { data } = await http.get<RunnerRecord[]>('/api/v1/moonshot/runners')
    return data
  },
  async getResults() {
    const { data } = await http.get<ResourceRecord[]>('/api/v1/moonshot/results')
    return data
  },
  async runRecipeBenchmark(payload: BenchmarkRecipeRequest) {
    const { data } = await http.post<BenchmarkRunResponse>('/api/v1/benchmarks/recipes', payload)
    return data
  },
  async getBenchmarkJobs() {
    const { data } = await http.get<BenchmarkJob[]>('/api/v1/benchmarks/jobs')
    return data
  },
  async getBenchmarkJob(id: string) {
    const { data } = await http.get<BenchmarkJob>(`/api/v1/benchmarks/jobs/${encodeURIComponent(id)}`)
    return data
  },
  async getBenchmarkJobPage(id: string, page = 1, pageSize = 100, interactionFilter = 'all', cookbookFilter = 'all') {
    const { data } = await http.get<BenchmarkJob>(`/api/v1/benchmarks/jobs/${encodeURIComponent(id)}`, {
      params: {
        interactions_page: page,
        interactions_page_size: pageSize,
        interaction_filter: interactionFilter,
        cookbook_filter: cookbookFilter,
      },
    })
    return data
  },
  async pauseBenchmarkJob(id: string) {
    const { data } = await http.post<BenchmarkJob>(`/api/v1/benchmarks/jobs/${encodeURIComponent(id)}/pause`)
    return data
  },
  async resumeBenchmarkJob(id: string) {
    const { data } = await http.post<BenchmarkJob>(`/api/v1/benchmarks/jobs/${encodeURIComponent(id)}/resume`)
    return data
  },
  async updateBenchmarkJobThreadCount(id: string, threadCount: number) {
    const { data } = await http.patch<BenchmarkJob>(
      `/api/v1/benchmarks/jobs/${encodeURIComponent(id)}/thread-count`,
      { thread_count: threadCount },
    )
    return data
  },
  benchmarkJobReportDownloadUrl(id: string) {
    const path = `/api/v1/benchmarks/jobs/${encodeURIComponent(id)}/report/download`
    return new URL(path, http.defaults.baseURL).toString()
  },
  async deleteBenchmarkJob(id: string) {
    const { data } = await http.delete<{ deleted: boolean; job_id: string; files: string[]; locked_files?: string[] }>(
      `/api/v1/benchmarks/jobs/${encodeURIComponent(id)}`,
    )
    return data
  },
  async getSettings() {
    const { data } = await http.get<AppSettings>('/api/v1/settings')
    return data
  },
  async updateSettings(payload: Partial<AppSettings>) {
    const { data } = await http.patch<AppSettings>('/api/v1/settings', payload)
    return data
  },
}
