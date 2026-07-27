from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)


class TaskAgentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TerminationMode(str, Enum):
    GUARDED_UNBOUNDED = "guarded_unbounded"
    BOUNDED = "bounded"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    STOPPING = "stopping"
    SUCCEEDED = "succeeded"
    STOPPED_SAFETY = "stopped_safety"
    STOPPED_MANUAL = "stopped_manual"
    FAILED = "failed"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    SUSPECT = "suspect"
    VERIFIED = "verified"
    REVOKED = "revoked"


class RouteDecision(str, Enum):
    CONTINUE_METHOD = "CONTINUE_METHOD"
    REPLAN = "REPLAN"
    STOP_SUCCESS = "STOP_SUCCESS"
    STOP_SAFETY = "STOP_SAFETY"
    PAUSE = "PAUSE"


class MethodStatus(str, Enum):
    CONTINUE = "CONTINUE"
    SUSPECT_SUCCESS = "SUSPECT_SUCCESS"
    EXHAUSTED = "EXHAUSTED"
    BLOCKED = "BLOCKED"


class SkillRole(str, Enum):
    PRIMARY = "PRIMARY"
    SUPPORTING = "SUPPORTING"


class SkillRuntimeStatus(str, Enum):
    CONTINUE = "CONTINUE"
    COMPLETED = "COMPLETED"
    EXHAUSTED = "EXHAUSTED"
    BLOCKED = "BLOCKED"


class SkillType(str, Enum):
    DOMAIN = "DOMAIN"
    AUXILIARY = "AUXILIARY"


class ChatMessage(TaskAgentModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: StrictStr = Field(min_length=1, max_length=200_000)
    message_id: StrictStr | None = Field(default=None, max_length=160)
    created_at: datetime | None = None


class TaskAgentConfig(TaskAgentModel):
    termination_mode: TerminationMode = TerminationMode.GUARDED_UNBOUNDED
    max_rounds: StrictInt | None = Field(default=None, ge=1, le=100_000)
    request_interval_ms: StrictInt = Field(default=1_200, ge=0, le=300_000)
    max_node_retries: StrictInt = Field(default=2, ge=0, le=10)
    max_consecutive_target_failures: StrictInt = Field(default=3, ge=1, le=100)
    max_no_novelty_rounds: StrictInt = Field(default=5, ge=1, le=1_000)
    max_runtime_seconds: StrictInt | None = Field(default=None, ge=1)
    max_input_tokens: StrictInt | None = Field(default=None, ge=1)
    max_output_tokens: StrictInt | None = Field(default=None, ge=1)
    max_estimated_cost: StrictFloat | None = Field(default=None, ge=0)
    recent_history_messages: StrictInt = Field(default=16, ge=2, le=100)
    max_prompt_chars: StrictInt = Field(default=90_000, ge=10_000, le=500_000)
    max_active_skills: StrictInt = Field(default=3, ge=1, le=8)
    min_variants_per_technique: StrictInt = Field(default=2, ge=1, le=20)
    max_variants_per_technique: StrictInt = Field(default=6, ge=1, le=50)
    max_technique_stagnation: StrictInt = Field(default=2, ge=1, le=20)
    max_duplicate_variants: StrictInt = Field(default=2, ge=1, le=20)
    success_memory_bonus_variants: StrictInt = Field(default=2, ge=0, le=20)
    max_parallel_branches: StrictInt = Field(default=0, ge=0, le=10)
    branch_spawn_round: StrictInt = Field(default=1, ge=1, le=100)
    branch_stall_novelty_threshold: StrictInt = Field(default=15, ge=0, le=100)
    min_strategy_candidate_score: StrictFloat = Field(default=45, ge=0, le=100)
    min_expected_information_gain: StrictFloat = Field(default=0.08, ge=0, le=1)

    @field_validator("max_rounds")
    @classmethod
    def validate_round_mode(cls, value: int | None, info: Any) -> int | None:
        termination_mode = info.data.get("termination_mode")
        if termination_mode == TerminationMode.BOUNDED and value is None:
            raise ValueError("max_rounds is required when termination_mode is bounded")
        return value

    @model_validator(mode="after")
    def validate_technique_variant_limits(self) -> "TaskAgentConfig":
        if self.min_variants_per_technique > self.max_variants_per_technique:
            raise ValueError(
                "min_variants_per_technique cannot exceed "
                "max_variants_per_technique"
            )
        return self


class TaskBranchContext(TaskAgentModel):
    parent_task_id: StrictStr = Field(min_length=1, max_length=200)
    parent_chat_id: StrictStr = Field(min_length=1, max_length=200)
    branch_id: StrictStr = Field(min_length=1, max_length=200)
    branch_index: StrictInt = Field(ge=1, le=10)
    branch_count: StrictInt = Field(ge=1, le=10)
    focus: StrictStr = Field(min_length=1, max_length=4_000)
    sibling_focuses: list[StrictStr] = Field(default_factory=list, max_length=10)
    fork_round: StrictInt = Field(default=0, ge=0)
    candidate_signature: StrictStr | None = Field(default=None, max_length=500)


class TaskBranchTemplate(TaskAgentModel):
    """Target-session recipe used by the durable backend branch supervisor."""

    session_name: StrictStr = Field(min_length=1, max_length=240)
    endpoint_ids: list[StrictStr] = Field(min_length=1, max_length=20)
    runner_args: dict[str, Any] = Field(default_factory=dict)


class SelectedSkill(TaskAgentModel):
    skill_id: StrictStr = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,79}$")
    role: SkillRole
    priority: StrictInt = Field(ge=1, le=100)
    reason: StrictStr = Field(min_length=1, max_length=2_000)
    selected_techniques: list[StrictStr] = Field(min_length=1, max_length=12)


class LoadedSkill(TaskAgentModel):
    skill_id: StrictStr
    role: SkillRole
    priority: StrictInt
    reason: StrictStr
    selected_techniques: list[StrictStr]
    content: StrictStr
    content_hash: StrictStr = Field(pattern=r"^[a-f0-9]{64}$")
    version: StrictStr
    metadata: dict[str, Any]


class ActiveTechnique(TaskAgentModel):
    skill_id: StrictStr
    role: SkillRole
    technique: StrictStr


class ComposedSkillPlan(TaskAgentModel):
    primary_skill: StrictStr | None = None
    supporting_skills: list[StrictStr] = Field(default_factory=list, max_length=7)
    active_techniques: list[ActiveTechnique] = Field(default_factory=list, max_length=2)
    single_changed_variable: StrictStr = Field(min_length=1, max_length=2_000)
    execution_instruction: StrictStr = Field(min_length=1, max_length=6_000)
    must_not_combine: list[StrictStr] = Field(default_factory=list, max_length=20)
    composition_warnings: list[StrictStr] = Field(default_factory=list, max_length=20)


class AppliedSkill(TaskAgentModel):
    skill_id: StrictStr
    role: SkillRole
    technique: StrictStr


class PromptVariationRecord(TaskAgentModel):
    base_intent: StrictStr = Field(min_length=1, max_length=2_000)
    transformation_family: StrictStr = Field(min_length=1, max_length=160)
    transformation_applied: StrictStr = Field(min_length=1, max_length=2_000)
    changed_variable: StrictStr = Field(min_length=1, max_length=2_000)
    expected_difference: StrictStr = Field(min_length=1, max_length=2_000)
    previous_variant_difference: StrictStr = Field(min_length=1, max_length=2_000)
    scope_preserved: StrictBool


class SkillAssessment(TaskAgentModel):
    skill_id: StrictStr
    technique: StrictStr
    status: SkillRuntimeStatus
    effectiveness: StrictInt = Field(ge=0, le=100)
    new_evidence: list[StrictStr] = Field(default_factory=list, max_length=20)
    remaining_gaps: list[StrictStr] = Field(default_factory=list, max_length=20)
    recommended_next_technique: StrictStr | None = Field(default=None, max_length=160)


class SkillRuntimeState(TaskAgentModel):
    skill_id: StrictStr
    role: SkillRole
    status: SkillRuntimeStatus = SkillRuntimeStatus.CONTINUE
    attempted_techniques: list[StrictStr] = Field(default_factory=list, max_length=100)
    exhausted_techniques: list[StrictStr] = Field(default_factory=list, max_length=100)
    successful_techniques: list[StrictStr] = Field(default_factory=list, max_length=100)
    evidence_ids: list[StrictStr] = Field(default_factory=list, max_length=500)
    novelty_history: list[StrictInt] = Field(default_factory=list, max_length=500)
    last_effectiveness: StrictInt = Field(default=0, ge=0, le=100)
    technique_attempt_counts: dict[StrictStr, StrictInt] = Field(default_factory=dict)
    technique_stagnation_counts: dict[StrictStr, StrictInt] = Field(default_factory=dict)
    technique_best_effectiveness: dict[StrictStr, StrictInt] = Field(default_factory=dict)
    technique_variant_signatures: dict[StrictStr, list[StrictStr]] = Field(default_factory=dict)
    technique_duplicate_counts: dict[StrictStr, StrictInt] = Field(default_factory=dict)


class TechniqueAttempt(TaskAgentModel):
    round: StrictInt = Field(ge=1)
    skill_id: StrictStr
    role: SkillRole
    technique: StrictStr
    changed_variable: StrictStr
    status: SkillRuntimeStatus
    effectiveness: StrictInt = Field(ge=0, le=100)
    novelty_score: StrictInt = Field(default=0, ge=0, le=100)
    response_pattern: StrictStr = Field(default="", max_length=160)
    strategy_lesson: StrictStr = Field(default="", max_length=2_000)
    remaining_gaps: list[StrictStr] = Field(default_factory=list, max_length=20)


class StrategyCandidate(TaskAgentModel):
    candidate_id: StrictStr = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,79}$")
    skill_id: StrictStr
    technique_id: StrictStr
    hypothesis: StrictStr = Field(min_length=1, max_length=2_000)
    adaptation_from_history: StrictStr = Field(min_length=1, max_length=3_000)
    expected_signal: StrictStr = Field(min_length=1, max_length=2_000)
    goal_alignment: StrictInt = Field(ge=0, le=100)
    expected_information_gain: StrictInt = Field(ge=0, le=100)
    response_fit: StrictInt = Field(ge=0, le=100)
    novelty: StrictInt = Field(ge=0, le=100)


class PlannerOutput(TaskAgentModel):
    plan_summary: StrictStr = Field(min_length=1, max_length=4_000)
    method_id: StrictStr = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,79}$")
    method_name: StrictStr = Field(min_length=1, max_length=160)
    rationale: StrictStr = Field(min_length=1, max_length=4_000)
    selected_skills: list[SelectedSkill] = Field(default_factory=list, max_length=8)
    single_changed_variable: StrictStr = Field(min_length=1, max_length=2_000)
    steps: list[StrictStr] = Field(min_length=1, max_length=12)
    success_criteria: list[StrictStr] = Field(min_length=1, max_length=12)
    disconfirming_evidence: list[StrictStr] = Field(default_factory=list, max_length=12)
    expected_information_gain: StrictFloat = Field(ge=0, le=1)
    method_status: MethodStatus = MethodStatus.CONTINUE
    fallback_method: StrictStr | None = Field(default=None, max_length=1_000)
    target_response_analysis: StrictStr = Field(default="", max_length=4_000)
    current_goal_gap: StrictStr = Field(default="", max_length=3_000)
    strategy_candidates: list[StrategyCandidate] = Field(default_factory=list, max_length=6)

    @field_validator("selected_skills", mode="before")
    @classmethod
    def normalize_single_selected_technique(
        cls, value: Any
    ) -> Any:
        if not isinstance(value, list):
            return value
        normalized: list[Any] = []
        for item in value:
            if not isinstance(item, dict):
                normalized.append(item)
                continue
            techniques = item.get("selected_techniques")
            if isinstance(techniques, str) and techniques.strip():
                normalized.append(
                    {**item, "selected_techniques": [techniques]}
                )
                continue
            if isinstance(techniques, dict):
                technique_id = techniques.get("technique_id")
                allowed_keys = {"technique_id", "name", "summary", "stage"}
                if (
                    isinstance(technique_id, str)
                    and technique_id.strip()
                    and set(techniques).issubset(allowed_keys)
                ):
                    normalized.append(
                        {**item, "selected_techniques": [technique_id]}
                    )
                    continue
            normalized.append(item)
        return normalized

    @model_validator(mode="after")
    def validate_skill_roles(self) -> "PlannerOutput":
        if not self.selected_skills:
            return self
        ids = [item.skill_id for item in self.selected_skills]
        if len(ids) != len(set(ids)):
            raise ValueError("selected_skills must not contain duplicate skill IDs")
        primary = [item for item in self.selected_skills if item.role == SkillRole.PRIMARY]
        if len(primary) != 1:
            raise ValueError("selected_skills must contain exactly one PRIMARY Skill")
        priorities = [item.priority for item in self.selected_skills]
        if len(priorities) != len(set(priorities)):
            raise ValueError("selected_skills priorities must be unique")
        return self


class ExecutorDecision(TaskAgentModel):
    """Small semantic contract produced by the Executor model."""

    message: StrictStr = Field(min_length=1, max_length=12_000)
    hypothesis: StrictStr = Field(min_length=1, max_length=2_000)
    adaptation_from_latest_response: StrictStr = Field(
        min_length=1,
        max_length=3_000,
    )
    expected_signal: StrictStr = Field(min_length=1, max_length=2_000)
    method_status: MethodStatus


class ExecutorOutput(TaskAgentModel):
    message: StrictStr = Field(min_length=1, max_length=12_000)
    hypothesis: StrictStr = Field(min_length=1, max_length=2_000)
    adaptation_from_latest_response: StrictStr = Field(
        default="",
        max_length=3_000,
    )
    expected_signal: StrictStr = Field(default="", max_length=2_000)
    applied_skills: list[AppliedSkill] = Field(default_factory=list, max_length=2)
    changed_variable: StrictStr = Field(min_length=1, max_length=2_000)
    payload_variant: StrictStr = Field(min_length=1, max_length=4_000)
    variation_record: PromptVariationRecord | None = None
    expected_observations: list[StrictStr] = Field(min_length=1, max_length=12)
    evidence_criteria: list[StrictStr] = Field(min_length=1, max_length=12)
    method_status: MethodStatus
    skill_status: dict[StrictStr, SkillRuntimeStatus] = Field(default_factory=dict)
    risk_notes: list[StrictStr] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_variation_record(self) -> "ExecutorOutput":
        uses_prompt_variation = any(
            item.skill_id == "prompt-variation-testing"
            for item in self.applied_skills
        )
        if uses_prompt_variation and self.variation_record is None:
            raise ValueError(
                "variation_record is required when prompt-variation-testing is applied"
            )
        if (
            self.variation_record is not None
            and self.variation_record.changed_variable != self.changed_variable
        ):
            raise ValueError(
                "variation_record.changed_variable must match changed_variable"
            )
        if self.variation_record is not None and not self.variation_record.scope_preserved:
            raise ValueError(
                "prompt variations must preserve the experiment scope"
            )
        return self


class EvidenceItem(TaskAgentModel):
    evidence_id: StrictStr = Field(pattern=r"^[A-Za-z0-9._:-]{1,160}$")
    observation: StrictStr = Field(min_length=1, max_length=6_000)
    supports: StrictStr = Field(min_length=1, max_length=2_000)
    strength: Literal["weak", "medium", "strong"]
    request_excerpt: StrictStr | None = Field(default=None, max_length=2_000)
    response_excerpt: StrictStr | None = Field(default=None, max_length=2_000)


class BranchReport(TaskAgentModel):
    report_id: StrictStr = Field(min_length=1, max_length=240)
    parent_task_id: StrictStr = Field(min_length=1, max_length=200)
    child_task_id: StrictStr = Field(min_length=1, max_length=200)
    branch_id: StrictStr = Field(min_length=1, max_length=200)
    branch_index: StrictInt = Field(ge=1, le=10)
    candidate_signature: StrictStr = Field(default="", max_length=500)
    focus: StrictStr = Field(default="", max_length=4_000)
    hypothesis: StrictStr = Field(default="", max_length=4_000)
    actions_tested: list[StrictStr] = Field(default_factory=list, max_length=30)
    observations: list[StrictStr] = Field(default_factory=list, max_length=50)
    new_evidence: list[EvidenceItem] = Field(default_factory=list, max_length=50)
    disconfirmed_assumptions: list[StrictStr] = Field(default_factory=list, max_length=30)
    remaining_gaps: list[StrictStr] = Field(default_factory=list, max_length=30)
    recommended_next_action: StrictStr = Field(default="", max_length=4_000)
    outcome: Literal["running", "succeeded", "failed", "stopped", "exhausted"]
    verification_status: VerificationStatus = VerificationStatus.PENDING
    created_at: datetime
    updated_at: datetime


class ResearchState(TaskAgentModel):
    immutable_goal: StrictStr = Field(min_length=1, max_length=12_000)
    success_criteria: list[StrictStr] = Field(default_factory=list, max_length=30)
    best_evidence: list[EvidenceItem] = Field(default_factory=list, max_length=100)
    unresolved_gaps: list[StrictStr] = Field(default_factory=list, max_length=100)
    current_hypothesis: StrictStr = Field(default="", max_length=4_000)
    open_hypotheses: list[StrictStr] = Field(default_factory=list, max_length=100)
    rejected_hypotheses: list[StrictStr] = Field(default_factory=list, max_length=100)
    tested_actions: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
    branch_reports: list[BranchReport] = Field(default_factory=list, max_length=100)
    decision_log: list[dict[str, Any]] = Field(default_factory=list, max_length=200)
    next_best_actions: list[StrictStr] = Field(default_factory=list, max_length=20)
    steering_directives: list[StrictStr] = Field(default_factory=list, max_length=50)
    stop_reason: StrictStr | None = Field(default=None, max_length=4_000)
    updated_at: datetime


class SuccessVerification(TaskAgentModel):
    status: VerificationStatus = VerificationStatus.PENDING
    reason: StrictStr = Field(default="", max_length=4_000)
    evidence_ids: list[StrictStr] = Field(default_factory=list, max_length=100)
    criterion: StrictStr | None = Field(default=None, max_length=2_000)
    adjudicator: StrictStr = Field(default="deterministic-evidence-gate", max_length=160)
    verified_at: datetime | None = None


class EvaluatorOutput(TaskAgentModel):
    goal_achieved: StrictBool
    progress: StrictInt = Field(ge=0, le=100)
    summary: StrictStr = Field(min_length=1, max_length=5_000)
    facts: list[StrictStr] = Field(default_factory=list, max_length=30)
    inferences: list[StrictStr] = Field(default_factory=list, max_length=30)
    unknowns: list[StrictStr] = Field(default_factory=list, max_length=30)
    counter_evidence: list[StrictStr] = Field(default_factory=list, max_length=30)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=30)
    novelty_score: StrictInt = Field(ge=0, le=100)
    method_status: MethodStatus
    skill_assessments: list[SkillAssessment] = Field(default_factory=list, max_length=8)
    route_recommendation: RouteDecision
    skills_to_continue: list[StrictStr] = Field(default_factory=list, max_length=8)
    skills_to_drop: list[StrictStr] = Field(default_factory=list, max_length=8)
    requires_new_skill_selection: StrictBool = False
    reason: StrictStr = Field(min_length=1, max_length=4_000)
    response_pattern: Literal[
        "refusal",
        "partial-progress",
        "compliant",
        "ambiguous",
        "off-topic",
        "error",
    ] = "ambiguous"
    next_strategy_objective: StrictStr = Field(default="", max_length=3_000)
    strategy_lessons: list[StrictStr] = Field(default_factory=list, max_length=12)


class SensitiveFinding(TaskAgentModel):
    category: StrictStr = Field(min_length=1, max_length=120)
    title: StrictStr = Field(min_length=1, max_length=240)
    severity: Literal["info", "low", "medium", "high", "critical"]
    confidence: Literal["low", "medium", "high"]
    evidence_excerpt: StrictStr = Field(min_length=1, max_length=2_000)


class SensitiveAnalysisOutput(TaskAgentModel):
    findings: list[SensitiveFinding] = Field(default_factory=list, max_length=50)
    summary: StrictStr = Field(default="", max_length=4_000)
    severity: Literal["none", "P0", "P1", "P2", "P3"] = "none"


class TaskCreateRequest(TaskAgentModel):
    session_id: StrictStr = Field(min_length=1, max_length=200)
    chat_id: StrictStr = Field(min_length=1, max_length=200)
    runner_id: StrictStr = Field(min_length=1, max_length=200)
    target_key: StrictStr | None = Field(default=None, max_length=2_000)
    goal: StrictStr = Field(min_length=1, max_length=12_000)
    endpoint_name: StrictStr | None = Field(default=None, max_length=240)
    payload_name: StrictStr | None = Field(default=None, max_length=240)
    attack_module: StrictStr | None = Field(default=None, max_length=240)
    context_strategy: StrictStr | None = Field(default=None, max_length=240)
    history: list[ChatMessage] = Field(default_factory=list, max_length=5_000)
    branch_context: TaskBranchContext | None = None
    branch_template: TaskBranchTemplate | None = None
    config: TaskAgentConfig = Field(default_factory=TaskAgentConfig)


class TaskControlRequest(TaskAgentModel):
    reason: StrictStr | None = Field(default=None, max_length=2_000)


class TaskSteerRequest(TaskAgentModel):
    instruction: StrictStr = Field(min_length=1, max_length=4_000)


class TaskSnapshot(TaskAgentModel):
    task_id: StrictStr
    session_id: StrictStr
    chat_id: StrictStr
    runner_id: StrictStr
    target_key: StrictStr = ""
    status: TaskStatus
    current_node: StrictStr
    route: RouteDecision | None = None
    stop_reason: StrictStr | None = None
    goal: StrictStr
    goal_progress: StrictInt = Field(default=0, ge=0, le=100)
    best_goal_progress: StrictInt = Field(default=0, ge=0, le=100)
    best_turn: dict[str, Any] | None = None
    best_evidence: list[EvidenceItem] = Field(default_factory=list)
    total_round: StrictInt = Field(default=0, ge=0)
    method_round: StrictInt = Field(default=0, ge=0)
    current_method: StrictStr | None = None
    current_skill_id: StrictStr | None = None
    selected_skills: list[SelectedSkill] = Field(default_factory=list)
    loaded_skills: list[LoadedSkill] = Field(default_factory=list)
    composed_skill_plan: ComposedSkillPlan | None = None
    skill_runtime_state: dict[StrictStr, SkillRuntimeState] = Field(default_factory=dict)
    active_techniques: list[ActiveTechnique] = Field(default_factory=list)
    technique_history: list[TechniqueAttempt] = Field(default_factory=list)
    elapsed_seconds: StrictFloat = Field(default=0, ge=0)
    input_tokens: StrictInt = Field(default=0, ge=0)
    output_tokens: StrictInt = Field(default=0, ge=0)
    estimated_cost: StrictFloat = Field(default=0, ge=0)
    latest_request: StrictStr | None = None
    latest_response: StrictStr | None = None
    planner_output: PlannerOutput | None = None
    executor_output: ExecutorOutput | None = None
    evaluator_output: EvaluatorOutput | None = None
    sensitive_output: SensitiveAnalysisOutput | None = None
    ai_watch_result: SensitiveAnalysisOutput | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    gaps: list[StrictStr] = Field(default_factory=list)
    committed_turns: list[dict[str, Any]] = Field(default_factory=list)
    prompt_versions: dict[str, Any] = Field(default_factory=dict)
    analysis_errors: list[StrictStr] = Field(default_factory=list)
    branch_context: TaskBranchContext | None = None
    branch_template: TaskBranchTemplate | None = None
    branch_reports: list[BranchReport] = Field(default_factory=list)
    branch_result: dict[str, Any] | None = None
    research_state: ResearchState | None = None
    success_verification: SuccessVerification | None = None
    steering_messages: list[StrictStr] = Field(default_factory=list)
    context_health: dict[str, Any] = Field(default_factory=dict)
    provider: StrictStr | None = None
    model: StrictStr | None = None
    error: StrictStr | None = None
    created_at: datetime
    updated_at: datetime
    config: TaskAgentConfig


class SkillMetadata(TaskAgentModel):
    version: StrictStr = Field(pattern=r"^\d+\.\d+(?:\.\d+)?$")
    category: StrictStr = Field(min_length=1, max_length=80)
    stage: StrictStr = Field(min_length=1, max_length=80)
    risk_level: Literal["low"]
    skill_type: SkillType
    techniques: list["TechniqueMetadata"] = Field(min_length=1, max_length=50)
    composable_with: list[StrictStr] = Field(default_factory=list, max_length=30)
    conflicts_with: list[StrictStr] = Field(default_factory=list, max_length=30)
    allow_primary: StrictBool
    allow_supporting: StrictBool


class TechniqueMetadata(TaskAgentModel):
    technique_id: StrictStr = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,79}$")
    name: StrictStr = Field(min_length=1, max_length=160)
    summary: StrictStr = Field(min_length=1, max_length=600)
    stage: StrictStr = Field(min_length=1, max_length=80)


class ExecutorSkill(TaskAgentModel):
    name: StrictStr = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,79}$")
    description: StrictStr = Field(min_length=1, max_length=1_000)
    compatibility: Literal["Prompt-only skill. No scripts or executable actions."]
    metadata: SkillMetadata
    body: StrictStr = Field(min_length=1, max_length=64_000)
    enabled: StrictBool = True


class ExecutorSkillCatalogItem(TaskAgentModel):
    name: StrictStr
    description: StrictStr
    compatibility: StrictStr
    metadata: SkillMetadata
    enabled: StrictBool
    updated_at: datetime | None = None


class ExecutorSkillWriteRequest(TaskAgentModel):
    skill: ExecutorSkill


class ExecutorSkillDuplicateRequest(TaskAgentModel):
    new_name: StrictStr = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,79}$")
    description: StrictStr | None = Field(default=None, min_length=1, max_length=1_000)


class SkillValidationResult(TaskAgentModel):
    valid: StrictBool
    errors: list[StrictStr] = Field(default_factory=list)
    warnings: list[StrictStr] = Field(default_factory=list)
    skill: ExecutorSkill | None = None


class WorkflowNode(TaskAgentModel):
    id: StrictStr
    label: StrictStr
    kind: Literal["control", "agent", "safety", "target", "analysis", "router", "terminal"]
    description: StrictStr
    color: StrictStr


class WorkflowEdge(TaskAgentModel):
    source: StrictStr
    target: StrictStr
    label: StrictStr | None = None
    route: RouteDecision | None = None


class WorkflowDefinition(TaskAgentModel):
    version: StrictStr
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
