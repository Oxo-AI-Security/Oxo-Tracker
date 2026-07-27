import { http, type ApiRequestError } from './http'

export type TaskAgentRuntimeStatus =
  | 'queued'
  | 'running'
  | 'pausing'
  | 'paused'
  | 'stopping'
  | 'succeeded'
  | 'stopped_safety'
  | 'stopped_manual'
  | 'failed'

export interface TaskAgentConfig {
  termination_mode: 'guarded_unbounded' | 'bounded'
  max_rounds: number | null
  request_interval_ms: number
  max_node_retries: number
  max_consecutive_target_failures: number
  max_no_novelty_rounds: number
  max_runtime_seconds: number | null
  max_input_tokens: number | null
  max_output_tokens: number | null
  max_estimated_cost: number | null
  recent_history_messages: number
  max_prompt_chars: number
  max_active_skills: number
  min_variants_per_technique: number
  max_variants_per_technique: number
  max_technique_stagnation: number
  max_duplicate_variants: number
  success_memory_bonus_variants: number
  max_parallel_branches: number
  branch_spawn_round: number
  branch_stall_novelty_threshold: number
  min_strategy_candidate_score: number
  min_expected_information_gain: number
}

export type SkillRole = 'PRIMARY' | 'SUPPORTING'
export type SkillRuntimeStatus = 'CONTINUE' | 'COMPLETED' | 'EXHAUSTED' | 'BLOCKED'

export interface SelectedTaskSkill {
  skill_id: string
  role: SkillRole
  priority: number
  reason: string
  selected_techniques: string[]
}

export interface ActiveTechnique {
  skill_id: string
  role: SkillRole
  technique: string
}

export interface ComposedSkillPlan {
  primary_skill?: string | null
  supporting_skills: string[]
  active_techniques: ActiveTechnique[]
  single_changed_variable: string
  execution_instruction: string
  must_not_combine: string[]
  composition_warnings: string[]
}

export interface SkillRuntimeState {
  skill_id: string
  role: SkillRole
  status: SkillRuntimeStatus
  attempted_techniques: string[]
  exhausted_techniques: string[]
  successful_techniques: string[]
  evidence_ids: string[]
  novelty_history: number[]
  last_effectiveness: number
  technique_attempt_counts: Record<string, number>
  technique_stagnation_counts: Record<string, number>
  technique_best_effectiveness: Record<string, number>
  technique_variant_signatures: Record<string, string[]>
  technique_duplicate_counts: Record<string, number>
}

export interface TaskAgentEvidence {
  evidence_id: string
  observation: string
  supports: string
  strength: 'weak' | 'medium' | 'strong'
  request_excerpt?: string | null
  response_excerpt?: string | null
}

export interface TaskAgentCommittedTurn {
  round_key: string
  round: number
  method?: string | null
  skill_id?: string | null
  request: string
  prepared_request?: string
  response: string
  raw_response?: unknown
  created_at: string
  origin_branch?: {
    task_id: string
    branch_id?: string | null
    branch_index?: number | null
    focus?: string | null
    label?: string | null
  }
  observation_records?: Array<{
    type: 'sensitive_information' | 'goal_outcome'
    label: string
    request: string
    response: string
    data: Record<string, unknown>
  }>
}

export interface TaskAgentSnapshot {
  task_id: string
  session_id: string
  chat_id: string
  runner_id: string
  target_key: string
  status: TaskAgentRuntimeStatus
  current_node: string
  route?: 'CONTINUE_METHOD' | 'REPLAN' | 'STOP_SUCCESS' | 'STOP_SAFETY' | 'PAUSE' | null
  stop_reason?: string | null
  goal: string
  goal_progress: number
  best_goal_progress: number
  best_turn?: Record<string, unknown> | null
  best_evidence: TaskAgentEvidence[]
  total_round: number
  method_round: number
  current_method?: string | null
  current_skill_id?: string | null
  selected_skills: SelectedTaskSkill[]
  loaded_skills: Array<SelectedTaskSkill & { content_hash: string; version: string }>
  composed_skill_plan?: ComposedSkillPlan | null
  skill_runtime_state: Record<string, SkillRuntimeState>
  active_techniques: ActiveTechnique[]
  technique_history: Array<
    ActiveTechnique & {
      round: number
      changed_variable: string
      status: SkillRuntimeStatus
      effectiveness: number
    }
  >
  elapsed_seconds: number
  input_tokens: number
  output_tokens: number
  estimated_cost: number
  latest_request?: string | null
  latest_response?: string | null
  planner_output?: Record<string, unknown> | null
  executor_output?: Record<string, unknown> | null
  evaluator_output?: Record<string, unknown> | null
  sensitive_output?: {
    findings: Array<Record<string, unknown>>
    summary: string
    severity: 'none' | 'P0' | 'P1' | 'P2' | 'P3'
  } | null
  ai_watch_result?: TaskAgentSnapshot['sensitive_output']
  evidence: TaskAgentEvidence[]
  gaps: string[]
  committed_turns: TaskAgentCommittedTurn[]
  prompt_versions: Record<string, unknown>
  analysis_errors: string[]
  branch_context?: TaskBranchContext | null
  branch_template?: TaskBranchTemplate | null
  branch_reports: TaskBranchReport[]
  branch_result?: {
    source_task_id: string
    source_chat_id?: string | null
    source_runner_id?: string | null
    branch_id?: string | null
    branch_index?: number | null
    focus?: string | null
    adopted_turn_count?: number
    adopted_at?: string
  } | null
  research_state?: TaskResearchState | null
  success_verification?: TaskSuccessVerification | null
  steering_messages: string[]
  context_health: Record<string, unknown>
  provider?: string | null
  model?: string | null
  error?: string | null
  created_at: string
  updated_at: string
  config: TaskAgentConfig
}

export interface TaskBranchContext {
  parent_task_id: string
  parent_chat_id: string
  branch_id: string
  branch_index: number
  branch_count: number
  focus: string
  sibling_focuses: string[]
  fork_round: number
  candidate_signature?: string | null
}

export interface TaskBranchTemplate {
  session_name: string
  endpoint_ids: string[]
  runner_args: Record<string, unknown>
}

export interface TaskBranchReport {
  report_id: string
  parent_task_id: string
  child_task_id: string
  branch_id: string
  branch_index: number
  candidate_signature: string
  focus: string
  hypothesis: string
  actions_tested: string[]
  observations: string[]
  new_evidence: TaskAgentEvidence[]
  disconfirmed_assumptions: string[]
  remaining_gaps: string[]
  recommended_next_action: string
  outcome: 'running' | 'succeeded' | 'failed' | 'stopped' | 'exhausted'
  verification_status: 'pending' | 'suspect' | 'verified' | 'revoked'
  created_at: string
  updated_at: string
}

export interface TaskResearchState {
  immutable_goal: string
  success_criteria: string[]
  best_evidence: TaskAgentEvidence[]
  unresolved_gaps: string[]
  current_hypothesis: string
  open_hypotheses: string[]
  rejected_hypotheses: string[]
  tested_actions: Array<Record<string, unknown>>
  branch_reports: TaskBranchReport[]
  decision_log: Array<Record<string, unknown>>
  next_best_actions: string[]
  steering_directives: string[]
  stop_reason?: string | null
  updated_at: string
}

export interface TaskSuccessVerification {
  status: 'pending' | 'suspect' | 'verified' | 'revoked'
  reason: string
  evidence_ids: string[]
  criterion?: string | null
  adjudicator: string
  verified_at?: string | null
}

export interface ExecutorSkillMetadata {
  version: string
  category: string
  stage: string
  risk_level: 'low'
  skill_type: 'DOMAIN' | 'AUXILIARY'
  techniques: Array<{
    technique_id: string
    name: string
    summary: string
    stage: string
  }>
  composable_with: string[]
  conflicts_with: string[]
  allow_primary: boolean
  allow_supporting: boolean
}

export interface ExecutorSkillCatalogItem {
  name: string
  description: string
  compatibility: string
  metadata: ExecutorSkillMetadata
  enabled: boolean
  updated_at?: string | null
}

export interface ExecutorSkill extends ExecutorSkillCatalogItem {
  body: string
}

export interface WorkflowDefinition {
  version: string
  nodes: Array<{
    id: string
    label: string
    kind: 'control' | 'agent' | 'safety' | 'target' | 'analysis' | 'router' | 'terminal'
    description: string
    color: string
  }>
  edges: Array<{
    source: string
    target: string
    label?: string | null
    route?: string | null
  }>
}

export interface TaskSuccessMemory {
  memory_id: string
  task_id: string
  target_key: string
  runner_id: string
  endpoint_name: string
  goal: string
  final_input: string
  final_output: string
  strategy_summary: string
  technique: string
  round_count: number
  trajectory: Array<{
    round: number
    method?: string | null
    skill_id?: string | null
    active_techniques?: ActiveTechnique[]
    changed_variable?: string | null
    request: string
    response: string
  }>
  status: 'suspect' | 'verified' | 'revoked'
  evidence_ids: string[]
  evaluator_version: string
  target_fingerprint: string
  verification_reason: string
  revoked_at?: string | null
  created_at: string
  updated_at: string
}

export const defaultTaskAgentConfig = (): TaskAgentConfig => ({
  termination_mode: 'guarded_unbounded',
  max_rounds: null,
  request_interval_ms: 1200,
  max_node_retries: 2,
  max_consecutive_target_failures: 3,
  max_no_novelty_rounds: 5,
  max_runtime_seconds: null,
  max_input_tokens: null,
  max_output_tokens: null,
  max_estimated_cost: null,
  recent_history_messages: 16,
  max_prompt_chars: 90000,
  max_active_skills: 3,
  min_variants_per_technique: 2,
  max_variants_per_technique: 6,
  max_technique_stagnation: 2,
  max_duplicate_variants: 2,
  success_memory_bonus_variants: 2,
  max_parallel_branches: 0,
  branch_spawn_round: 1,
  branch_stall_novelty_threshold: 15,
  min_strategy_candidate_score: 45,
  min_expected_information_gain: 0.08,
})

export const taskAgentsApi = {
  async createTask(payload: {
    session_id: string
    chat_id: string
    runner_id: string
    target_key?: string
    goal: string
    endpoint_name?: string
    payload_name?: string
    attack_module?: string
    context_strategy?: string
    history: Array<{ role: 'user' | 'assistant'; content: string }>
    branch_context?: TaskBranchContext
    branch_template?: TaskBranchTemplate
    config: TaskAgentConfig
  }) {
    try {
      const { data } = await http.post<TaskAgentSnapshot>('/api/v1/task-agents/tasks', payload)
      return data
    } catch (error) {
      const requestError = error as ApiRequestError
      const isLegacyConfigRejection =
        requestError.status === 422 &&
        requestError.message.includes('max_active_skills')
      if (!isLegacyConfigRejection) throw error

      // Rolling-upgrade compatibility: an already-running V2 backend rejects the
      // V3-only field because its Pydantic config forbids unknown properties.
      // Retry without V3-only fields; a restarted V3 backend uses the full request.
      const {
        max_active_skills: _ignored,
        min_variants_per_technique: _ignoredMinVariants,
        max_variants_per_technique: _ignoredMaxVariants,
        max_technique_stagnation: _ignoredStagnation,
        max_duplicate_variants: _ignoredDuplicateVariants,
        success_memory_bonus_variants: _ignoredMemoryBonus,
        max_parallel_branches: _ignoredParallelBranches,
        branch_spawn_round: _ignoredBranchSpawnRound,
        branch_stall_novelty_threshold: _ignoredBranchNovelty,
        min_strategy_candidate_score: _ignoredCandidateScore,
        min_expected_information_gain: _ignoredInformationGain,
        ...legacyConfig
      } = payload.config
      const { data } = await http.post<TaskAgentSnapshot>('/api/v1/task-agents/tasks', {
        ...payload,
        config: legacyConfig,
      })
      return data
    }
  },
  async listTasks(params: { session_id?: string; chat_id?: string } = {}) {
    const { data } = await http.get<TaskAgentSnapshot[]>('/api/v1/task-agents/tasks', { params })
    return data
  },
  async getTask(taskId: string) {
    const { data } = await http.get<TaskAgentSnapshot>(`/api/v1/task-agents/tasks/${encodeURIComponent(taskId)}`)
    return data
  },
  async pauseTask(taskId: string) {
    const { data } = await http.post<TaskAgentSnapshot>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(taskId)}/pause`,
    )
    return data
  },
  async resumeTask(taskId: string) {
    const { data } = await http.post<TaskAgentSnapshot>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(taskId)}/resume`,
    )
    return data
  },
  async stopTask(taskId: string, reason = 'Stopped by user') {
    const { data } = await http.post<TaskAgentSnapshot>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(taskId)}/stop`,
      { reason },
    )
    return data
  },
  async steerTask(taskId: string, instruction: string) {
    const { data } = await http.post<TaskAgentSnapshot>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(taskId)}/steer`,
      { instruction },
    )
    return data
  },
  async adoptBranchSuccess(parentTaskId: string, childTaskId: string) {
    const { data } = await http.post<TaskAgentSnapshot>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(parentTaskId)}/adopt-success/${encodeURIComponent(childTaskId)}`,
    )
    return data
  },
  async reconcileEvidence(taskId: string) {
    const { data } = await http.post<TaskAgentSnapshot>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(taskId)}/reconcile-evidence`,
    )
    return data
  },
  async listBranchReports(taskId: string) {
    const { data } = await http.get<TaskBranchReport[]>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(taskId)}/branch-reports`,
    )
    return data
  },
  async getWorkflow() {
    const { data } = await http.get<WorkflowDefinition>('/api/v1/task-agents/workflow')
    return data
  },
  async listSuccessMemories(params: { target_key: string; runner_id?: string; limit?: number }) {
    const { data } = await http.get<TaskSuccessMemory[]>(
      '/api/v1/task-agents/success-memories',
      { params },
    )
    return data
  },
  async deleteSuccessMemory(memoryId: string) {
    await http.delete(
      `/api/v1/task-agents/success-memories/${encodeURIComponent(memoryId)}`,
    )
  },
  async listSkills() {
    const { data } = await http.get<ExecutorSkillCatalogItem[]>('/api/v1/task-agents/skills')
    return data
  },
  async getSkill(skillId: string) {
    const { data } = await http.get<ExecutorSkill>(`/api/v1/task-agents/skills/${encodeURIComponent(skillId)}`)
    return data
  },
  async createSkill(skill: ExecutorSkill) {
    const { data } = await http.post<ExecutorSkill>('/api/v1/task-agents/skills', { skill })
    return data
  },
  async updateSkill(skillId: string, skill: ExecutorSkill) {
    const { data } = await http.put<ExecutorSkill>(
      `/api/v1/task-agents/skills/${encodeURIComponent(skillId)}`,
      { skill },
    )
    return data
  },
  async deleteSkill(skillId: string) {
    await http.delete(`/api/v1/task-agents/skills/${encodeURIComponent(skillId)}`)
  },
  async duplicateSkill(skillId: string, newName: string) {
    const { data } = await http.post<ExecutorSkill>(
      `/api/v1/task-agents/skills/${encodeURIComponent(skillId)}/duplicate`,
      { new_name: newName },
    )
    return data
  },
  async validateSkill(skill: ExecutorSkill) {
    const { data } = await http.post<{
      valid: boolean
      errors: string[]
      warnings: string[]
      skill?: ExecutorSkill | null
    }>('/api/v1/task-agents/skills/validate', { skill })
    return data
  },
}
