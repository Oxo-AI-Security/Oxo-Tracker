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

export type TaskAgentExplorationIntensity =
  | 'light'
  | 'standard'
  | 'deep'
  | 'extreme'

export interface TaskAgentConfig {
  exploration_intensity: TaskAgentExplorationIntensity
  control_provider: string | null
  control_model: string | null
  termination_mode: 'guarded_unbounded' | 'bounded'
  max_rounds: number | null
  request_interval_ms: number
  max_node_retries: number
  auto_resume_transient_failures: boolean
  max_auto_resumes: number
  auto_resume_delay_seconds: number
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
  max_family_rounds: number
  max_family_input_tokens: number
  max_family_output_tokens: number
  max_evidence_stall_rounds: number
  near_duplicate_threshold: number
  baseline_scanner_enabled: boolean
  baseline_max_probes: number
  branch_min_marginal_utility: number
  branch_stop_no_gain_rounds: number
  branch_followup_round_gap: number
  branch_min_allocated_rounds: number
  branch_max_allocated_rounds: number
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
  provenance?: TaskEvidenceProvenance | null
}

export interface TaskEvidenceProvenance {
  schema_version: number
  source:
    | 'target_novel'
    | 'user_echo'
    | 'history_echo'
    | 'memory_echo'
    | 'example_anchored'
    | 'inferred'
    | 'unverified'
  evidence_type: string
  target_origin: boolean
  novel: boolean
  eligible_for_progress: boolean
  eligible_for_success: boolean
  confidence: 'low' | 'medium' | 'high'
  reasons: string[]
  matched_source_hashes: string[]
  classified_at: string
}

export interface TaskAgentCommittedTurn {
  schema_version?: number
  round_key: string
  round: number
  method?: string | null
  skill_id?: string | null
  request: string
  generation_mode?: 'model' | 'baseline_scanner'
  baseline_probe_id?: string | null
  attack_strategy_id?: string | null
  transform_id?: string | null
  prepared_request?: string
  delivery?: {
    schema_version?: number
    delivery_id?: string
    status?: TargetDeliveryStatus
    interaction_mode: 'task_agent'
    manual_controls_applied: false
    idempotency_supported?: boolean
    executor_message_sha256: string
    final_sent_message_sha256: string
  }
  response: string
  raw_response?: unknown
  created_at: string
  ai_watch_status?: 'pending' | 'analyzing' | 'complete' | 'error' | 'cancelled'
  ai_watch_summary?: string
  origin_branch?: {
    task_id: string
    branch_id?: string | null
    branch_index?: number | null
    focus?: string | null
    label?: string | null
  }
  observation_records?: Array<{
    type: 'sensitive_information' | 'goal_outcome' | 'ai_watch_review'
    label: string
    request: string
    response: string
    data: Record<string, unknown>
  }>
}

export interface TaskAiWatchReview {
  schema_version?: number
  round_key: string
  round: number
  status: 'pending' | 'analyzing' | 'complete' | 'error' | 'cancelled'
  attempts?: number
  max_attempts?: number
  next_attempt_at?: string | null
  retryable?: boolean
  queued_at: string
  started_at?: string | null
  completed_at?: string | null
  summary: string
  output?: TaskAgentSnapshot['sensitive_output'] | null
  error?: string | null
}

export type TargetDeliveryStatus =
  | 'PREPARED'
  | 'SENDING'
  | 'DELIVERED'
  | 'AMBIGUOUS'
  | 'NOT_DELIVERED'
  | 'COMMITTED'

export interface TaskAgentIssue {
  component:
    | 'runtime'
    | 'planner'
    | 'executor'
    | 'target'
    | 'evaluator'
    | 'ai_watch'
    | 'storage'
    | 'branch'
  severity: 'info' | 'warning' | 'error' | 'critical'
  code: string
  summary: string
  detail: string
  recoverable: boolean
  delivery_id?: string | null
  retry_at?: string | null
}

export interface TargetDeliveryRecord {
  schema_version: number
  delivery_id: string
  round_key: string
  round: number
  status: TargetDeliveryStatus
  runner_id: string
  message_sha256: string
  message: string
  prepared_request?: string | null
  idempotency_supported: boolean
  transport_receipt?: Record<string, unknown> | null
  response?: string | null
  raw_response?: unknown
  error?: string | null
  prepared_at: string
  sending_at?: string | null
  delivered_at?: string | null
  committed_at?: string | null
  updated_at: string
}

export interface TaskAgentSnapshot {
  schema_version: number
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
  goal_contract?: Record<string, unknown> | null
  attack_spec?: TaskAttackSpec | null
  baseline_scan?: TaskBaselineScan | null
  attack_assets_initialized?: boolean
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
  model_call_counts?: Record<string, number>
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
  ai_watch_reviews?: Record<string, TaskAiWatchReview>
  evidence: TaskAgentEvidence[]
  evidence_ledger: Array<Record<string, unknown>>
  family_metrics: Record<string, unknown>
  evidence_stall_count: number
  gaps: string[]
  committed_turns: TaskAgentCommittedTurn[]
  target_deliveries: Record<string, TargetDeliveryRecord>
  active_issue?: TaskAgentIssue | null
  prompt_versions: Record<string, unknown>
  analysis_errors: string[]
  branch_context?: TaskBranchContext | null
  branch_template?: TaskBranchTemplate | null
  branch_reports: TaskBranchReport[]
  branch_runner_deleted?: boolean
  branch_cleanup?: {
    state?: 'not_applicable' | 'pending' | 'retry_scheduled' | 'complete'
    attempts?: number
    tombstoned?: boolean
    next_retry_at?: string | null
    last_error?: string | null
    completed_at?: string | null
  }
  branch_orchestration?: Record<string, unknown>
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
  scorer_ensemble?: TaskScorerEnsemble | null
  campaign_id?: string | null
  source_manifest_id?: string | null
  fork_origin?: Record<string, unknown> | null
  steering_messages: string[]
  context_health: Record<string, unknown>
  provider?: string | null
  model?: string | null
  error?: string | null
  created_at: string
  updated_at: string
  config: TaskAgentConfig
}

export type TaskScorerVerdictValue = 'pass' | 'fail' | 'abstain' | 'error'

export interface TaskScorerVerdict {
  scorer_id: string
  scorer_kind:
    | 'proof_spec'
    | 'rule_detector'
    | 'vulnerability_scorer'
    | 'llm_judge'
    | 'ai_watch'
    | 'human_review'
  verdict: TaskScorerVerdictValue
  confidence: number
  reason: string
  evidence_ids: string[]
  evidence_type: string
  version: string
}

export interface TaskScorerEnsemble {
  schema_version: number
  ensemble_id: string
  ensemble_version: string
  content_sha256: string
  source: string
  task_id: string
  round_key?: string | null
  round: number
  verdicts: TaskScorerVerdict[]
  conflict: 'none' | 'soft' | 'hard'
  conflict_matrix: Array<Record<string, unknown>>
  final_verdict:
    | 'pending'
    | 'verified'
    | 'suspect'
    | 'rejected'
    | 'needs_review'
  confidence: number
  reason: string
  independent_evidence_types: string[]
  independent_evidence_count: number
  finding_eligible: boolean
  human_review_required: boolean
  scorer_versions: Record<string, string>
  created_at: string
}

export interface TaskRunManifest {
  schema_version: number
  manifest_id: string
  manifest_sha256: string
  generation_sha256: string
  task_id: string
  goal: string
  finalized: boolean
  source_status: string
  turns: TaskAgentCommittedTurn[]
  scorer_ensemble?: TaskScorerEnsemble | null
  recorded_at: string
}

export interface TaskRunReplay {
  replay_id: string
  manifest_id: string
  manifest_sha256: string
  mode: 'offline'
  target_call_count: 0
  rounds: Array<{
    round_key: string
    round: number
    ensemble: TaskScorerEnsemble
  }>
  final_ensemble?: TaskScorerEnsemble | null
  created_at: string
}

export interface TaskRunRegrade {
  regrade_id: string
  manifest_id: string
  manifest_sha256: string
  mode: 'offline'
  target_call_count: 0
  scorer_versions: Record<string, string>
  ensemble: TaskScorerEnsemble
  created_at: string
}

export interface AttackCampaign {
  schema_version: number
  campaign_id: string
  name: string
  description: string
  target_key: string
  owner: string
  status: 'active' | 'paused' | 'completed' | 'archived'
  created_at: string
  updated_at: string
}

export interface AttackFinding {
  schema_version: number
  finding_id: string
  campaign_id: string
  source_task_id: string
  source_manifest_id: string
  source_manifest_sha256: string
  source_round_key: string
  title: string
  vulnerability_id: string
  category: string
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical'
  confidence: number
  status:
    | 'open'
    | 'triaged'
    | 'in_progress'
    | 'fixed'
    | 'accepted'
    | 'false_positive'
    | 'closed'
  owner: string
  fix_version: string
  summary: string
  evidence: Array<Record<string, unknown>>
  scorer_ensemble: TaskScorerEnsemble
  reproduction: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface AttackRegressionCase {
  schema_version: number
  regression_case_id: string
  finding_id: string
  campaign_id: string
  name: string
  status: string
  expected_outcome: 'blocked' | 'detected' | 'no_regression'
  source_manifest_id: string
  source_manifest_sha256: string
  goal: string
  request: string
  expected_signal: string
  scorer_contract: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface TaskRunFork {
  fork_id: string
  source_task_id: string
  source_manifest_id: string
  source_manifest_sha256: string
  source_snapshot_sha256: string
  round: number
  target_call_count_before_fork_task: 0
  source_unchanged: true
  task: TaskAgentSnapshot
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
  allocation_score?: number
  expected_marginal_gain?: number
  estimated_cost_units?: number
  allocated_rounds?: number | null
  allocated_input_tokens?: number | null
  allocated_output_tokens?: number | null
}

export interface TaskBranchTemplate {
  session_name: string
  endpoint_ids: string[]
  runner_args: Record<string, unknown>
}

export interface TaskBranchReport {
  schema_version?: number
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
  rounds?: number
  input_tokens?: number
  output_tokens?: number
  estimated_cost?: number
  model_call_counts?: Record<string, number>
  duration_seconds?: number
  eligible_evidence_count?: number
  evidence_gain?: number
  cost_units?: number
  marginal_efficiency?: number
  parent_control?: 'none' | 'followup' | 'stopped'
  created_at: string
  updated_at: string
}

export interface TaskAttackSpec {
  schema_version: number
  attack_spec_id: string
  immutable: true
  vulnerability: {
    vulnerability_id: string
    category: string
    title: string
    taxonomy: string[]
    severity_hint: 'low' | 'medium' | 'high' | 'critical'
  }
  objective: {
    goal: string
    goal_type: string
    proof_spec: Record<string, unknown>
    success_criteria: string[]
    must_be_target_origin: boolean
    must_be_novel: boolean
  }
  strategies: Array<{
    strategy_id: string
    skill_id: string
    technique_ids: string[]
    stage: 'baseline' | 'adaptive' | 'followup'
    priority: number
    rationale: string
    applicable_transforms: string[]
  }>
  transforms: Array<{
    transform_id: string
    kind: string
    label: string
    deterministic: boolean
    cost_weight: number
  }>
  target: Record<string, unknown>
  scorers: Array<Record<string, unknown>>
}

export interface TaskBaselineScan {
  schema_version: number
  attack_spec_id: string
  dataset_id: string
  dataset_sha256: string
  status: 'pending' | 'running' | 'completed' | 'disabled'
  probes: Array<{
    probe_id: string
    strategy_id: string
    transform_id: string
    message: string
    changed_variable: string
    expected_signal: string
    evidence_criteria: string[]
    proof_requirement_ids: string[]
    estimated_cost_units: number
  }>
  completed_probe_ids: string[]
  skipped_probe_ids: string[]
  max_probes: number
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
  proof_spec_version?: number
  proof_id?: string | null
  requirement_results?: Array<{
    requirement_id: string
    description: string
    required: boolean
    satisfied: boolean
    evidence_ids?: string[]
    observed?: unknown
    required_count?: number
    reason: string
  }>
  coverage?: Record<string, unknown>
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
  exploration_intensity: 'deep',
  control_provider: null,
  control_model: null,
  termination_mode: 'guarded_unbounded',
  max_rounds: 24,
  request_interval_ms: 1200,
  max_node_retries: 2,
  auto_resume_transient_failures: true,
  max_auto_resumes: 2,
  auto_resume_delay_seconds: 15,
  max_consecutive_target_failures: 3,
  max_no_novelty_rounds: 5,
  max_runtime_seconds: 1800,
  max_input_tokens: 500000,
  max_output_tokens: 100000,
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
  max_family_rounds: 32,
  max_family_input_tokens: 750000,
  max_family_output_tokens: 150000,
  max_evidence_stall_rounds: 4,
  near_duplicate_threshold: 0.92,
  baseline_scanner_enabled: true,
  baseline_max_probes: 4,
  branch_min_marginal_utility: 0.12,
  branch_stop_no_gain_rounds: 3,
  branch_followup_round_gap: 2,
  branch_min_allocated_rounds: 2,
  branch_max_allocated_rounds: 6,
})

export interface TaskAgentExplorationPreset {
  max_rounds: number
  max_runtime_seconds: number
  max_input_tokens: number
  max_output_tokens: number
  max_active_skills: number
  max_parallel_branches: number
  max_variants_per_technique: number
  max_family_rounds: number
  max_family_input_tokens: number
  max_family_output_tokens: number
  max_evidence_stall_rounds: number
  baseline_max_probes: number
  branch_min_marginal_utility: number
  branch_stop_no_gain_rounds: number
  branch_followup_round_gap: number
  branch_min_allocated_rounds: number
  branch_max_allocated_rounds: number
}

export const taskAgentExplorationPresets: Record<
  TaskAgentExplorationIntensity,
  TaskAgentExplorationPreset
> = {
  light: {
    max_rounds: 6,
    max_runtime_seconds: 480,
    max_input_tokens: 125000,
    max_output_tokens: 25000,
    max_active_skills: 1,
    max_parallel_branches: 0,
    max_variants_per_technique: 2,
    max_family_rounds: 8,
    max_family_input_tokens: 175000,
    max_family_output_tokens: 35000,
    max_evidence_stall_rounds: 3,
    baseline_max_probes: 1,
    branch_min_marginal_utility: 0.2,
    branch_stop_no_gain_rounds: 2,
    branch_followup_round_gap: 2,
    branch_min_allocated_rounds: 2,
    branch_max_allocated_rounds: 3,
  },
  standard: {
    max_rounds: 12,
    max_runtime_seconds: 900,
    max_input_tokens: 250000,
    max_output_tokens: 50000,
    max_active_skills: 2,
    max_parallel_branches: 1,
    max_variants_per_technique: 3,
    max_family_rounds: 18,
    max_family_input_tokens: 350000,
    max_family_output_tokens: 70000,
    max_evidence_stall_rounds: 4,
    baseline_max_probes: 2,
    branch_min_marginal_utility: 0.16,
    branch_stop_no_gain_rounds: 2,
    branch_followup_round_gap: 2,
    branch_min_allocated_rounds: 2,
    branch_max_allocated_rounds: 4,
  },
  deep: {
    max_rounds: 24,
    max_runtime_seconds: 1800,
    max_input_tokens: 500000,
    max_output_tokens: 100000,
    max_active_skills: 3,
    max_parallel_branches: 2,
    max_variants_per_technique: 6,
    max_family_rounds: 32,
    max_family_input_tokens: 750000,
    max_family_output_tokens: 150000,
    max_evidence_stall_rounds: 4,
    baseline_max_probes: 4,
    branch_min_marginal_utility: 0.12,
    branch_stop_no_gain_rounds: 3,
    branch_followup_round_gap: 2,
    branch_min_allocated_rounds: 2,
    branch_max_allocated_rounds: 6,
  },
  extreme: {
    max_rounds: 40,
    max_runtime_seconds: 3600,
    max_input_tokens: 1000000,
    max_output_tokens: 200000,
    max_active_skills: 4,
    max_parallel_branches: 2,
    max_variants_per_technique: 8,
    max_family_rounds: 64,
    max_family_input_tokens: 1500000,
    max_family_output_tokens: 300000,
    max_evidence_stall_rounds: 6,
    baseline_max_probes: 6,
    branch_min_marginal_utility: 0.09,
    branch_stop_no_gain_rounds: 4,
    branch_followup_round_gap: 3,
    branch_min_allocated_rounds: 3,
    branch_max_allocated_rounds: 8,
  },
}

export const applyTaskAgentExplorationPreset = (
  config: TaskAgentConfig,
  intensity: TaskAgentExplorationIntensity,
): TaskAgentConfig => ({
  ...config,
  ...taskAgentExplorationPresets[intensity],
  exploration_intensity: intensity,
})

export const normalizeTaskAgentConfig = (
  config: TaskAgentConfig,
): TaskAgentConfig => {
  const defaults = defaultTaskAgentConfig()
  const normalized = {
    ...defaults,
    ...config,
  }
  const hasNoTaskBudget = [
    normalized.max_rounds,
    normalized.max_runtime_seconds,
    normalized.max_input_tokens,
    normalized.max_output_tokens,
    normalized.max_estimated_cost,
  ].every((value) => value == null)

  if (hasNoTaskBudget) {
    normalized.max_rounds = defaults.max_rounds
    normalized.max_runtime_seconds = defaults.max_runtime_seconds
    normalized.max_input_tokens = defaults.max_input_tokens
    normalized.max_output_tokens = defaults.max_output_tokens
  }
  return normalized
}

export const taskAgentsApi = {
  async createTask(payload: {
    session_id: string
    chat_id: string
    runner_id: string
    target_key?: string
    goal: string
    endpoint_name?: string
    history: Array<{ role: 'user' | 'assistant'; content: string }>
    branch_context?: TaskBranchContext
    branch_template?: TaskBranchTemplate
    attack_spec?: TaskAttackSpec
    config: TaskAgentConfig
  }) {
    const normalizedPayload = {
      ...payload,
      config: normalizeTaskAgentConfig(payload.config),
    }
    try {
      const { data } = await http.post<TaskAgentSnapshot>(
        '/api/v1/task-agents/tasks',
        normalizedPayload,
      )
      return data
    } catch (error) {
      const requestError = error as ApiRequestError
      const legacyOnlyConfigFields = [
        'exploration_intensity',
        'control_provider',
        'control_model',
        'max_active_skills',
        'auto_resume_transient_failures',
        'max_auto_resumes',
        'auto_resume_delay_seconds',
        'max_family_rounds',
        'max_family_input_tokens',
        'max_family_output_tokens',
        'max_evidence_stall_rounds',
        'near_duplicate_threshold',
        'baseline_scanner_enabled',
        'baseline_max_probes',
        'branch_min_marginal_utility',
        'branch_stop_no_gain_rounds',
        'branch_followup_round_gap',
        'branch_min_allocated_rounds',
        'branch_max_allocated_rounds',
      ]
      const isLegacyConfigRejection =
        requestError.status === 422 &&
        legacyOnlyConfigFields.some((field) =>
          requestError.message.includes(field),
        )
      if (!isLegacyConfigRejection) throw error

      // Rolling-upgrade compatibility: an already-running V2 backend rejects the
      // V3-only field because its Pydantic config forbids unknown properties.
      // Retry without V3-only fields; a restarted V3 backend uses the full request.
      const {
        exploration_intensity: _ignoredExplorationIntensity,
        control_provider: _ignoredControlProvider,
        control_model: _ignoredControlModel,
        max_active_skills: _ignored,
        auto_resume_transient_failures: _ignoredAutoResume,
        max_auto_resumes: _ignoredMaxAutoResumes,
        auto_resume_delay_seconds: _ignoredAutoResumeDelay,
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
        max_family_rounds: _ignoredFamilyRounds,
        max_family_input_tokens: _ignoredFamilyInputTokens,
        max_family_output_tokens: _ignoredFamilyOutputTokens,
        max_evidence_stall_rounds: _ignoredEvidenceStall,
        near_duplicate_threshold: _ignoredNearDuplicate,
        baseline_scanner_enabled: _ignoredBaselineScanner,
        baseline_max_probes: _ignoredBaselineMaxProbes,
        branch_min_marginal_utility: _ignoredBranchMarginalUtility,
        branch_stop_no_gain_rounds: _ignoredBranchStopNoGain,
        branch_followup_round_gap: _ignoredBranchFollowupGap,
        branch_min_allocated_rounds: _ignoredBranchMinRounds,
        branch_max_allocated_rounds: _ignoredBranchMaxRounds,
        ...legacyConfig
      } = normalizedPayload.config
      const { data } = await http.post<TaskAgentSnapshot>('/api/v1/task-agents/tasks', {
        ...normalizedPayload,
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
  async updateGoal(taskId: string, goal: string) {
    const { data } = await http.patch<TaskAgentSnapshot>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(taskId)}/goal`,
      { goal },
    )
    return data
  },
  async adoptBranchSuccess(parentTaskId: string, childTaskId: string) {
    const { data } = await http.post<TaskAgentSnapshot>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(parentTaskId)}/adopt-success/${encodeURIComponent(childTaskId)}`,
    )
    return data
  },
  async followUpBranch(parentTaskId: string, childTaskId: string, instruction: string) {
    const { data } = await http.post<TaskAgentSnapshot>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(parentTaskId)}/branches/${encodeURIComponent(childTaskId)}/follow-up`,
      { instruction },
    )
    return data
  },
  async stopBranch(parentTaskId: string, childTaskId: string, reason = 'Stopped by the parent task') {
    const { data } = await http.post<TaskAgentSnapshot>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(parentTaskId)}/branches/${encodeURIComponent(childTaskId)}/stop`,
      { reason },
    )
    return data
  },
  async reconcileEvidence(taskId: string) {
    const { data } = await http.post<TaskAgentSnapshot>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(taskId)}/reconcile-evidence`,
    )
    return data
  },
  async getRunManifest(taskId: string) {
    const { data } = await http.get<TaskRunManifest>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(taskId)}/manifest`,
    )
    return data
  },
  async replayRun(taskId: string) {
    const { data } = await http.post<TaskRunReplay>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(taskId)}/replay`,
    )
    return data
  },
  async regradeRun(
    taskId: string,
    payload: {
      scorer_versions?: Record<string, string>
      human_review?: {
        decision: 'confirm' | 'reject' | 'needs_more_evidence'
        reviewer?: string
        note?: string
        evidence_ids?: string[]
      }
    } = {},
  ) {
    const { data } = await http.post<TaskRunRegrade>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(taskId)}/regrade`,
      payload,
    )
    return data
  },
  async reviewScorerEnsemble(
    taskId: string,
    payload: {
      decision: 'confirm' | 'reject' | 'needs_more_evidence'
      reviewer?: string
      note?: string
      evidence_ids?: string[]
    },
  ) {
    const { data } = await http.post<TaskAgentSnapshot>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(taskId)}/scorer-review`,
      payload,
    )
    return data
  },
  async forkRun(
    taskId: string,
    payload: { round: number; goal?: string; instruction?: string },
  ) {
    const { data } = await http.post<TaskRunFork>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(taskId)}/fork`,
      payload,
    )
    return data
  },
  async createFinding(taskId: string, campaignId?: string) {
    const { data } = await http.post<AttackFinding>(
      `/api/v1/task-agents/tasks/${encodeURIComponent(taskId)}/findings`,
      campaignId ? { campaign_id: campaignId } : {},
    )
    return data
  },
  async listFindings(
    params: {
      campaign_id?: string
      task_id?: string
      status?: string
      limit?: number
    } = {},
  ) {
    const { data } = await http.get<AttackFinding[]>(
      '/api/v1/task-agents/findings',
      { params },
    )
    return data
  },
  async updateFinding(
    findingId: string,
    payload: Partial<
      Pick<AttackFinding, 'severity' | 'status' | 'owner' | 'fix_version' | 'summary'>
    >,
  ) {
    const { data } = await http.patch<AttackFinding>(
      `/api/v1/task-agents/findings/${encodeURIComponent(findingId)}`,
      payload,
    )
    return data
  },
  async createRegressionCase(
    findingId: string,
    payload: {
      name?: string
      expected_outcome?: 'blocked' | 'detected' | 'no_regression'
    } = {},
  ) {
    const { data } = await http.post<AttackRegressionCase>(
      `/api/v1/task-agents/findings/${encodeURIComponent(findingId)}/regression-cases`,
      payload,
    )
    return data
  },
  async listCampaigns(params: { target_key?: string; limit?: number } = {}) {
    const { data } = await http.get<AttackCampaign[]>(
      '/api/v1/task-agents/campaigns',
      { params },
    )
    return data
  },
  async listRegressionCases(
    params: { campaign_id?: string; finding_id?: string; limit?: number } = {},
  ) {
    const { data } = await http.get<AttackRegressionCase[]>(
      '/api/v1/task-agents/regression-cases',
      { params },
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
