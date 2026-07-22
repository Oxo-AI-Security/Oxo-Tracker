export type ResourceRecord = Record<string, unknown>

export interface RequiredConfig {
  endpoints?: string[]
  configurations?: Record<string, string[]>
}

export interface EndpointRecord {
  id?: string
  name?: string
  connector_type?: string
  token?: string
  uri?: string
  model?: string
  max_calls_per_second?: number
  max_concurrency?: number
  params?: Record<string, unknown>
  created_at?: string
}

export interface RecipeRecord {
  id?: string
  name?: string
  description?: string
  tags?: string[]
  categories?: string[]
  datasets?: string[]
  prompt_templates?: string[]
  metrics?: string[]
  grading_scale?: Record<string, number[]>
  stats?: Record<string, unknown>
  required_config?: RequiredConfig | null
}

export interface PromptTemplateRecord {
  id?: string
  name?: string
  description?: string
  template?: string
}

export interface DatasetExample {
  id?: string
  input: string
  target: string
}

export interface DatasetRecord {
  id?: string
  name?: string
  description?: string
  reference?: string
  license?: string
  num_of_dataset_prompts?: number
  created_date?: string
  examples?: DatasetExample[]
}

export interface CookbookRecord {
  id?: string
  name?: string
  description?: string
  tags?: string[]
  categories?: string[]
  recipes?: string[]
  stats?: Record<string, unknown>
  required_config?: RequiredConfig | null
}

export interface RunnerRecord {
  id?: string
  name?: string
  description?: string
  endpoints?: string[]
  database_file?: string
}

export interface BenchmarkRecipeRequest {
  run_name: string
  endpoints: string[]
  recipes: string[]
  cookbooks: string[]
  cookbook_prompt_selection_percentages?: Record<string, number>
  description: string
  prompt_selection_percentage: number
  estimated_prompts: number
  thread_count: number
  random_seed: number
  system_prompt: string
}

export interface BenchmarkRunResponse {
  runner_id: string
  status: string
}

export interface BenchmarkInteraction {
  id: number
  endpoint?: string
  recipe?: string
  dataset?: string
  prompt_template?: string
  prompt_index?: number
  input?: string
  expected?: string
  expected_label?: string
  expected_raw?: string
  response?: unknown
  unexpected?: boolean
  trace_status?: string
  evaluator?: {
    metric_id?: string
    labels?: string[]
    acceptable_status?: string
    refusal?: string
    judge_response?: string
    success_status?: string
  } | null
  duration?: string
  system_prompt?: string
}

export interface BenchmarkJob {
  id: string
  runner_id: string
  name: string
  description: string
  status: string
  progress: number
  created_at: string
  updated_at: string
  started_at?: string | null
  ended_at?: string | null
  request: BenchmarkRecipeRequest
  outputs?: Record<string, string | null>
  summary: {
    endpoints: string[]
    recipes: string[]
    cookbooks: string[]
    estimated_prompts: number
    completed_prompts: number
    error_count: number
    thread_count: number
    eta_seconds?: number | null
    estimated_completion_at?: string | null
    judge_progress?: {
      phase: 'pending' | 'evaluating' | 'completed'
      completed: number
      total: number
      percentage: number
    }
  }
  errors: string[]
  events: Array<{ time: string; level: string; message: string }>
  interactions?: BenchmarkInteraction[]
  interactions_pagination?: {
    page: number
    page_size: number
    total: number
    filter?: string
    cookbook_filter?: string
  }
  report_summary?: BenchmarkReportSummary
  result?: Record<string, unknown>
}

export interface BenchmarkReportSummary {
  id: string
  name: string
  description: string
  status: string
  endpoints: string[]
  recipes: string[]
  cookbooks: string[]
  start_time?: string | null
  end_time?: string | null
  duration?: number | null
  total_prompts: number
  recipe_summaries: Array<{
    id: string
    total_prompts: number
    prompt_count: number
    failed_count?: number
    datasets: string[]
    evaluation_summary: Array<{
      model_id?: string
      num_of_prompts?: number
      avg_grade_value?: number
      grade?: string | null
      overall_grade?: string | null
    }>
    metric_summaries?: Array<{
      metric_id?: string
      safe?: number
      unsafe?: number
      refused?: number
      nonrefused?: number
      unknown?: number
      acceptable_rate?: number | null
      refused_rate?: number | null
    }>
    grading_scale: Record<string, number[]>
  }>
  unexpected_payload_count: number
  unexpected_payloads: Array<{
    recipe_id?: string
    model_id?: string
    dataset_id?: string
    prompt_template_id?: string
    prompt_index?: number
    prompt?: string
    expected?: string
    expected_raw?: string
    response?: string
    evaluator?: {
      metric_id?: string
      labels?: string[]
      acceptable_status?: string
      refusal?: string
      judge_response?: string
      success_status?: string
    } | null
  }>
  errors: string[]
}

export interface AIProviderCatalogItem {
  label: string
  company: string
  description: string
  apiKeyLabel: string
  logo: string
  defaultModel: string
  defaultBaseUrl: string
  catalogUrl: string
  catalogCheckedAt: string
  latestModels: string[]
  models: string[]
}

export interface AIProviderSettings {
  model: string
  baseUrl: string
  apiKeyConfigured: boolean
  apiKeyMasked: string
}

export interface AISettings {
  activeProvider: string
  providers: Record<string, AIProviderSettings>
  catalog: Record<string, AIProviderCatalogItem>
}

export interface AIConnectionTestResult {
  ok: boolean
  provider: string
  model: string
  statusCode: number
  latencyMs: number
  modelAvailable: boolean
  message: string
}

export interface AppSettings {
  theme: 'light' | 'dark'
  ai: AISettings
}

export interface AppSettingsUpdate {
  theme?: AppSettings['theme']
  ai?: {
    activeProvider: string
    provider?: string
    config?: {
      model: string
      baseUrl: string
      apiKey?: string
    }
  }
}

export interface EndpointCreatePayload {
  name: string
  connector_type: string
  uri: string
  token: string
  max_calls_per_second: number
  max_concurrency: number
  model: string
  params: Record<string, unknown>
}

export type EndpointUpdatePayload = Partial<EndpointCreatePayload>

export interface CookbookCreatePayload {
  name: string
  description: string
  recipes: string[]
}

export type CookbookUpdatePayload = Partial<CookbookCreatePayload>

export interface RecipeCreatePayload {
  name: string
  description: string
  tags: string[]
  categories: string[]
  datasets: string[]
  prompt_templates: string[]
  metrics: string[]
  grading_scale: Record<string, number[]>
}

export type RecipeUpdatePayload = Partial<RecipeCreatePayload>

export interface DatasetCreatePayload {
  name: string
  description: string
  reference: string
  license: string
  examples: DatasetExample[]
}

export type DatasetUpdatePayload = DatasetCreatePayload
