from __future__ import annotations

import json
import os
import re
import threading
import types
from copy import deepcopy
from typing import Any, Callable, TypeVar, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError

from app.schemas.task_agent_v2 import (
    EvaluatorOutput,
    ExecutorDecision,
    ExecutorOutput,
    PlannerOutput,
)
from app.services.connector_ai_service import ConnectorAIError, ConnectorAIService
from app.services.prompt_registry import PromptAsset, PromptRegistry


OutputModel = TypeVar("OutputModel", bound=BaseModel)
MODEL_INPUT_CHAR_BUDGET = 28_000


class TaskAgentModelError(RuntimeError):
    pass


class RecoverableTaskAgentModelError(TaskAgentModelError):
    """A transient control-model failure that is safe to retry from a checkpoint."""

    def __init__(
        self,
        message: str,
        *,
        role: str,
        attempts: int,
        failure_kind: str = "transient_transport",
    ) -> None:
        super().__init__(message)
        self.role = role
        self.attempts = attempts
        self.failure_kind = failure_kind


class TaskAgentModelService:
    def __init__(
        self,
        *,
        ai_client: ConnectorAIService | None = None,
        prompt_registry: PromptRegistry | None = None,
        settings: dict[str, str] | None = None,
    ) -> None:
        self.ai_client = ai_client or ConnectorAIService(
            settings=settings,
            request_timeout_seconds=75,
            max_tokens=3_000,
            max_connection_attempts=2,
            scheduler_group="task-agent-control",
            scheduler_concurrency=max(
                1,
                min(
                    8,
                    int(os.getenv("ATTACK_AGENT_MODEL_CONCURRENCY", "3")),
                ),
            ),
            scheduler_priority=0,
        )
        self.prompts = prompt_registry or PromptRegistry()
        self._call_state = threading.local()

    @property
    def provider(self) -> str:
        return self.ai_client.provider

    @property
    def model(self) -> str:
        return self.ai_client.model

    def plan(
        self,
        *,
        state_context: dict[str, Any],
        skill_catalog: list[dict[str, Any]],
        goal_contract: dict[str, Any] | None = None,
        retries: int,
    ) -> PlannerOutput:
        payload = {
            "outputSchema": PlannerOutput.model_json_schema(),
            "STRUCTURED_OUTPUT_CONTRACT": _structured_output_contract(),
            "GOAL_CONTRACT": goal_contract or {},
            "SUCCESS_EXPERIENCE_POLICY": _success_experience_policy(
                state_context
            ),
            "skillCatalog": skill_catalog,
            "UNTRUSTED_DATA": state_context,
        }
        return self._call("planner", payload, PlannerOutput, retries)

    def execute(
        self,
        *,
        state_context: dict[str, Any],
        loaded_skills: list[dict[str, Any]],
        composed_skill_plan: dict[str, Any] | None,
        goal_contract: dict[str, Any] | None = None,
        retries: int,
    ) -> ExecutorOutput:
        payload = {
            "outputSchema": ExecutorDecision.model_json_schema(),
            "STRUCTURED_OUTPUT_CONTRACT": _structured_output_contract(),
            "GOAL_CONTRACT": goal_contract or {},
            "SUCCESS_EXPERIENCE_POLICY": _success_experience_policy(
                state_context
            ),
            # Send only the common Skill guidance and the Techniques active in
            # this turn. Unrelated Technique blocks add thousands of tokens and
            # can cause the selected block to be truncated out of the prompt.
            "LOADED_SKILLS": _project_loaded_skills(loaded_skills),
            "COMPOSED_SKILL_PLAN": composed_skill_plan,
            "PRE_SEND_REVIEW": {
                "required": True,
                "historyWindowTurns": 10,
                "instruction": (
                    "Review all recentInteractionRecords and the active loaded "
                    "Skill Techniques before deciding the outgoing message."
                ),
            },
            "UNTRUSTED_DATA": state_context,
        }
        decision = self._call(
            "executor",
            payload,
            ExecutorDecision,
            retries,
            raw_transform=lambda raw: _hydrate_executor_decision(
                raw,
                state_context=state_context,
                composed_skill_plan=composed_skill_plan,
            ),
        )
        return _materialize_executor_output(
            decision,
            state_context=state_context,
            composed_skill_plan=composed_skill_plan,
            goal_contract=goal_contract or {},
        )

    def evaluate(
        self,
        *,
        state_context: dict[str, Any],
        goal_contract: dict[str, Any] | None = None,
        consistency_review: dict[str, Any] | None = None,
        retries: int,
    ) -> EvaluatorOutput:
        payload = {
            "outputSchema": EvaluatorOutput.model_json_schema(),
            "STRUCTURED_OUTPUT_CONTRACT": _structured_output_contract(),
            "GOAL_CONTRACT": goal_contract or {},
            "UNTRUSTED_DATA": state_context,
        }
        if consistency_review:
            payload["CONSISTENCY_REVIEW"] = consistency_review
        return self._call(
            "evaluator",
            payload,
            EvaluatorOutput,
            retries,
            raw_transform=lambda raw: _hydrate_evaluator_output(
                raw,
                state_context=state_context,
            ),
        )

    def prompt_versions(self) -> dict[str, dict[str, str]]:
        return self.prompts.versions()

    def consume_call_metrics(self) -> dict[str, Any]:
        value = getattr(self._call_state, "metrics", {})
        self._call_state.metrics = {}
        return dict(value)

    def _call(
        self,
        role: str,
        payload: dict[str, Any],
        model_type: type[OutputModel],
        retries: int,
        raw_transform: Callable[[Any], Any] | None = None,
    ) -> OutputModel:
        self._call_state.metrics = {}
        prompt = self.prompts.load(role)
        validation_feedback = ""
        transport_feedback = ""
        force_emergency_compaction = False
        attempts = max(1, retries + 1)
        for attempt in range(attempts):
            current_payload = payload
            if validation_feedback:
                current_payload = {
                    **payload,
                    "VALIDATION_ERROR_FROM_PREVIOUS_ATTEMPT": validation_feedback,
                    "repairInstruction": (
                        "Return a corrected object matching outputSchema exactly. "
                        "Every array field must remain a JSON array even when it "
                        "contains zero or one item. Do not add commentary or keys."
                    ),
                }
            if transport_feedback:
                current_payload = {
                    **current_payload,
                    "TRANSIENT_TRANSPORT_ERROR_FROM_PREVIOUS_ATTEMPT": (
                        transport_feedback
                    ),
                    "transportRecoveryInstruction": (
                        "The previous model request failed before a usable response "
                        "was received. Complete the same task from the compacted "
                        "context and return the required object once."
                    ),
                }
            fitted_payload = _fit_model_payload(
                current_payload,
                system_prompt=prompt.content,
                emergency=force_emergency_compaction,
            )
            original_chars = _json_length(current_payload) + len(prompt.content)
            fitted_chars = _json_length(fitted_payload) + len(prompt.content)
            emergency_used = force_emergency_compaction
            current_user_prompt = json.dumps(
                fitted_payload,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            try:
                raw = self._chat_json(
                    prompt.content,
                    current_user_prompt,
                    payload=current_payload,
                )
            except ConnectorAIError as error:
                if _is_transient_model_transport_error(error):
                    if (
                        attempt < attempts - 1
                        and not _should_pause_without_node_retry(error)
                    ):
                        transport_feedback = _compact_transport_error(error)
                        validation_feedback = ""
                        force_emergency_compaction = True
                        continue
                    raise self._recoverable_model_error(
                        role=role,
                        error=error,
                        attempts=attempt + 1,
                        original_chars=original_chars,
                        fitted_chars=fitted_chars,
                        emergency_compaction=emergency_used,
                    ) from error
                if _is_model_output_parse_error(error):
                    transport_feedback = ""
                    validation_feedback = (
                        "The previous response was not a parseable JSON object. "
                        "Return exactly one JSON object matching outputSchema, "
                        "with every required field and no surrounding commentary."
                    )
                    if attempt < attempts - 1:
                        continue
                    raise TaskAgentModelError(
                        f"{role} returned invalid structured output after "
                        f"{attempts} attempt(s): {validation_feedback}"
                    ) from error
                if not _is_input_length_error(error):
                    raise TaskAgentModelError(
                        f"{role} model call failed: {error}"
                    ) from error
                emergency_payload = _fit_model_payload(
                    fitted_payload,
                    system_prompt=prompt.content,
                    emergency=True,
                )
                emergency_used = True
                fitted_chars = (
                    _json_length(emergency_payload) + len(prompt.content)
                )
                emergency_prompt = json.dumps(
                    emergency_payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                try:
                    raw = self._chat_json(
                        prompt.content,
                        emergency_prompt,
                        payload=current_payload,
                    )
                except ConnectorAIError as retry_error:
                    if (
                        _is_transient_model_transport_error(retry_error)
                        and attempt < attempts - 1
                        and not _should_pause_without_node_retry(retry_error)
                    ):
                        transport_feedback = _compact_transport_error(
                            retry_error
                        )
                        validation_feedback = ""
                        force_emergency_compaction = True
                        continue
                    if _is_transient_model_transport_error(retry_error):
                        raise self._recoverable_model_error(
                            role=role,
                            error=retry_error,
                            attempts=attempt + 1,
                            original_chars=original_chars,
                            fitted_chars=fitted_chars,
                            emergency_compaction=True,
                        ) from retry_error
                    raise TaskAgentModelError(
                        f"{role} model call failed after automatic context "
                        f"compaction: {retry_error}"
                    ) from retry_error
            try:
                if raw_transform is not None:
                    raw = raw_transform(raw)
                normalized = _normalize_structured_output(model_type, raw)
                result = model_type.model_validate(normalized)
                usage = (
                    self.ai_client.consume_last_usage()
                    if hasattr(self.ai_client, "consume_last_usage")
                    else {}
                )
                transport = (
                    self.ai_client.consume_last_transport_metrics()
                    if hasattr(self.ai_client, "consume_last_transport_metrics")
                    else {}
                )
                self._call_state.metrics = {
                    "role": role,
                    "attempt": attempt + 1,
                    "input_tokens": int(usage.get("input_tokens") or 0),
                    "output_tokens": int(usage.get("output_tokens") or 0),
                    "total_tokens": int(usage.get("total_tokens") or 0),
                    "original_chars": original_chars,
                    "fitted_chars": fitted_chars,
                    "compacted": fitted_chars < original_chars,
                    "emergency_compaction": emergency_used,
                    "budget_chars": MODEL_INPUT_CHAR_BUDGET,
                    **transport,
                }
                return result
            except ValidationError as error:
                transport_feedback = ""
                validation_feedback = _compact_validation_error(error)
                if attempt == attempts - 1:
                    raise TaskAgentModelError(
                        f"{role} returned invalid structured output after {attempts} attempt(s): "
                        f"{validation_feedback}"
                    ) from error
        raise TaskAgentModelError(f"{role} did not return output")

    def _recoverable_model_error(
        self,
        *,
        role: str,
        error: Exception,
        attempts: int,
        original_chars: int,
        fitted_chars: int,
        emergency_compaction: bool,
    ) -> RecoverableTaskAgentModelError:
        transport = (
            self.ai_client.consume_last_transport_metrics()
            if hasattr(self.ai_client, "consume_last_transport_metrics")
            else {}
        )
        compact_error = _compact_transport_error(error)
        reported_failure_kind = str(
            getattr(error, "failure_kind", None) or ""
        )
        failure_kind = (
            reported_failure_kind
            if reported_failure_kind
            and reported_failure_kind != "provider_error"
            else "transient_transport"
        )
        retry_after_seconds = getattr(error, "retry_after_seconds", None)
        self._call_state.metrics = {
            "role": role,
            "attempt": attempts,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "original_chars": original_chars,
            "fitted_chars": fitted_chars,
            "compacted": fitted_chars < original_chars,
            "emergency_compaction": emergency_compaction,
            "budget_chars": MODEL_INPUT_CHAR_BUDGET,
            "analysis_mode": "recoverable-transport-error",
            "failure_kind": failure_kind,
            "error_message": compact_error,
            "retry_after_seconds": retry_after_seconds,
            **transport,
        }
        return RecoverableTaskAgentModelError(
            f"{role} model call failed after {attempts} attempt(s): "
            f"{compact_error}",
            role=role,
            attempts=attempts,
            failure_kind=failure_kind,
        )

    def _chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        context = payload.get("UNTRUSTED_DATA")
        is_parallel_branch = bool(
            isinstance(context, dict) and context.get("parallelBranch")
        )
        is_background_observation = bool(
            isinstance(context, dict) and context.get("backgroundObservation")
        )
        if isinstance(self.ai_client, ConnectorAIService):
            return self.ai_client._chat_json(
                system_prompt,
                user_prompt,
                # The primary research loop owns the goal and must not sit
                # behind queued speculative branches. Existing calls are not
                # preempted, but the next free slot goes to the primary.
                scheduler_priority=(
                    30
                    if is_background_observation
                    else 20 if is_parallel_branch else 0
                ),
            )
        return self.ai_client._chat_json(system_prompt, user_prompt)


def _is_input_length_error(error: Exception) -> bool:
    detail = str(error).lower()
    return any(
        marker in detail
        for marker in (
            "range of input length",
            "maximum context length",
            "context length",
            "too many tokens",
            "prompt is too long",
            "input length",
        )
    )


def _is_model_output_parse_error(error: Exception) -> bool:
    detail = str(error).lower()
    return any(
        marker in detail
        for marker in (
            "did not return a valid connector configuration",
            "returned an invalid connector configuration object",
        )
    )


def _is_transient_model_transport_error(error: Exception) -> bool:
    if isinstance(error, ConnectorAIError) and error.retryable:
        return True
    detail = str(error).lower()
    if any(
        marker in detail
        for marker in (
            "rejected its api key",
            "invalid api key",
            "authentication failed",
            "unauthorized",
            "forbidden",
            "endpoint or model was not found",
            "model not found",
            "http 400",
            "http 401",
            "http 403",
            "http 404",
            "invalid parameter",
            "range of input length",
            "maximum context length",
        )
    ):
        return False
    return any(
        marker in detail
        for marker in (
            "read operation timed out",
            "timed out",
            "timeout",
            "unable to reach the active ai model",
            "active ai model is busy",
            "queue deadline",
            "rate limited",
            "http 408",
            "http 425",
            "http 429",
            "http 500",
            "http 502",
            "http 503",
            "http 504",
            "connection refused",
            "connection reset",
            "network is unreachable",
            "remote end closed connection",
            "temporary failure",
            "temporarily unavailable",
        )
    )


def _should_pause_without_node_retry(error: Exception) -> bool:
    return str(getattr(error, "failure_kind", "")) in {
        "circuit_open",
        "circuit_half_open",
        "local_queue_timeout",
    }


def _compact_transport_error(error: Exception) -> str:
    return _clip_text(re.sub(r"\s+", " ", str(error)).strip(), 500)


def _fit_model_payload(
    payload: dict[str, Any],
    *,
    system_prompt: str,
    emergency: bool,
) -> dict[str, Any]:
    """Bound model input while preserving the goal, latest evidence, and Skill plan."""

    available = max(
        8_000,
        MODEL_INPUT_CHAR_BUDGET - len(system_prompt),
    )
    if emergency:
        available = max(7_000, int(available * 0.68))
    fitted = deepcopy(payload)
    if _json_length(fitted) <= available:
        return fitted

    context = fitted.get("UNTRUSTED_DATA")
    if isinstance(context, dict):
        fitted["UNTRUSTED_DATA"] = _compact_state_context(
            context,
            emergency=emergency,
        )
    if isinstance(fitted.get("LOADED_SKILLS"), list):
        fitted["LOADED_SKILLS"] = [
            _compact_loaded_skill(item, emergency=emergency)
            for item in fitted["LOADED_SKILLS"]
            if isinstance(item, dict)
        ]
    if isinstance(fitted.get("skillCatalog"), list):
        fitted["skillCatalog"] = [
            _bounded_value(
                item,
                string_limit=900 if emergency else 1_800,
                list_limit=8 if emergency else 16,
            )
            for item in fitted["skillCatalog"]
        ]
    fitted["CONTEXT_BUDGET"] = {
        "compacted": True,
        "mode": "emergency" if emergency else "preflight",
        "instruction": (
            "The immutable goal, latest target turn, strongest evidence, current "
            "plan, and active Skill Techniques were retained. Older repetitive "
            "detail was compacted; do not infer that omitted history never occurred."
        ),
    }
    if _json_length(fitted) <= available:
        return fitted

    # A second deterministic pass targets only untrusted/runtime data. The output
    # schema and goal contract remain intact.
    for key in ("UNTRUSTED_DATA", "LOADED_SKILLS", "skillCatalog"):
        if key in fitted:
            fitted[key] = _bounded_value(
                fitted[key],
                string_limit=500 if emergency else 900,
                list_limit=4 if emergency else 8,
            )
    return fitted


def _compact_state_context(
    context: dict[str, Any],
    *,
    emergency: bool,
) -> dict[str, Any]:
    string_limit = 1_200 if emergency else 2_400
    latest_limit = 4_000 if emergency else 7_000
    recent_limit = 4 if emergency else 8
    compact = {
        key: context.get(key)
        for key in (
            "goal",
            "goalContract",
            "authorization",
            "round",
            "methodRound",
            "maxActiveSkills",
            "parallelBranch",
            "backgroundObservation",
            "currentMethod",
            "selectedSkills",
            "composedSkillPlan",
            "executorReviewRequirement",
            "steeringDirectives",
            "contextHealth",
        )
        if key in context
    }
    compact["recentConversation"] = [
        _bounded_value(item, string_limit=string_limit, list_limit=8)
        for item in (context.get("recentConversation") or [])[-recent_limit:]
    ]
    compact["longTermSummary"] = _clip_text(
        str(context.get("longTermSummary") or ""),
        1_500 if emergency else 3_000,
    )
    for key, limit in (
        ("confirmedFacts", 12),
        ("inferences", 8),
        ("openHypotheses", 8),
        ("failedRoutes", 10),
        ("evidenceIndex", 10),
        ("techniqueHistory", 10),
        ("recentInteractionRecords", 6),
        ("priorSuccessMemories", 3),
    ):
        items = context.get(key) or []
        compact[key] = [
            _bounded_value(
                item,
                string_limit=string_limit,
                list_limit=8,
            )
            for item in items[-(max(2, limit // 2) if emergency else limit):]
        ]
    compact["bestKnownState"] = _bounded_value(
        context.get("bestKnownState") or {},
        string_limit=latest_limit,
        list_limit=10,
    )
    compact["previousEvaluation"] = _bounded_value(
        context.get("previousEvaluation") or {},
        string_limit=string_limit,
        list_limit=8,
    )
    compact["adaptiveStrategyState"] = _bounded_value(
        context.get("adaptiveStrategyState") or {},
        string_limit=string_limit,
        list_limit=8,
    )
    compact["researchState"] = _bounded_value(
        context.get("researchState") or {},
        string_limit=string_limit,
        list_limit=16,
    )
    compact["branchReports"] = _bounded_value(
        context.get("branchReports") or [],
        string_limit=string_limit,
        list_limit=8 if emergency else 16,
    )
    if "plannerOutput" in context:
        compact["plannerOutput"] = _bounded_value(
            context.get("plannerOutput") or {},
            string_limit=string_limit,
            list_limit=12,
        )
    if "skillRuntimeState" in context:
        compact["skillRuntimeState"] = _bounded_value(
            context.get("skillRuntimeState") or {},
            string_limit=800,
            list_limit=12,
        )
    if "skillTechniqueInventory" in context:
        compact["skillTechniqueInventory"] = _bounded_value(
            context.get("skillTechniqueInventory") or [],
            string_limit=1_000,
            list_limit=20,
        )
    latest = context.get("latestTurn")
    if isinstance(latest, dict):
        compact["latestTurn"] = {
            "request": _clip_text(str(latest.get("request") or ""), latest_limit),
            "response": _clip_text(str(latest.get("response") or ""), latest_limit),
        }
    return compact


def _compact_loaded_skill(
    skill: dict[str, Any],
    *,
    emergency: bool,
) -> dict[str, Any]:
    content_limit = 2_500 if emergency else 5_500
    return {
        key: (
            _clip_text(str(value), content_limit)
            if key == "content"
            else _bounded_value(
                value,
                string_limit=900 if emergency else 1_600,
                list_limit=12,
            )
        )
        for key, value in skill.items()
    }


def _bounded_value(
    value: Any,
    *,
    string_limit: int,
    list_limit: int,
) -> Any:
    if isinstance(value, str):
        return _clip_text(value, string_limit)
    if isinstance(value, list):
        selected = value[-list_limit:]
        return [
            _bounded_value(
                item,
                string_limit=string_limit,
                list_limit=list_limit,
            )
            for item in selected
        ]
    if isinstance(value, dict):
        return {
            str(key): _bounded_value(
                item,
                string_limit=string_limit,
                list_limit=list_limit,
            )
            for key, item in value.items()
        }
    return value


def _clip_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    head = max(1, int(limit * 0.65))
    tail = max(1, limit - head - 44)
    return (
        value[:head]
        + "\n[…older/repetitive context compacted…]\n"
        + value[-tail:]
    )


def _json_length(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str))


def _success_experience_policy(
    state_context: dict[str, Any],
) -> dict[str, Any]:
    memories = [
        item
        for item in state_context.get("priorSuccessMemories") or []
        if isinstance(item, dict)
        and str(item.get("successfulInput") or "").strip()
        and str(item.get("successfulOutput") or "").strip()
    ]
    return {
        "active": bool(memories),
        "precedence": "strong-anchor" if memories else "none",
        "availableHistoricalFields": [
            "successfulInput",
            "successfulOutput",
        ],
        "firstAttemptRule": (
            "Use a successfulInput as the base draft and combine it with the "
            "active Skill Technique. Do not restart from a generic baseline."
            if memories
            else "No matching successful input/output pair is available."
        ),
        "laterAttemptRule": (
            "Adapt the successfulInput mechanism using the latest target "
            "response, recent interaction history, and active Skill Technique."
            if memories
            else "Use the normal evidence-driven adaptive strategy."
        ),
        "abandonmentRule": (
            "Abandon the successful mechanism only after the current history "
            "contains direct evidence that it failed or is incompatible."
            if memories
            else "Not applicable."
        ),
    }


def _project_loaded_skills(
    loaded_skills: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Project each loaded Skill to guidance relevant to the active turn."""

    return [
        _project_loaded_skill(item)
        for item in loaded_skills
        if isinstance(item, dict)
    ]


def _project_loaded_skill(skill: dict[str, Any]) -> dict[str, Any]:
    selected = {
        str(item)
        for item in skill.get("selected_techniques") or []
        if str(item).strip()
    }
    content = str(skill.get("content") or "")
    techniques_heading = re.search(
        r"(?mi)^##\s+(?:Techniques|Technique Catalog)\s*$",
        content,
    )
    common = (
        content[: techniques_heading.start()].strip()
        if techniques_heading
        else ""
    )
    blocks: list[str] = []
    for technique_id in selected:
        match = re.search(
            rf"(?ms)^###\s+{re.escape(technique_id)}\s*$"
            r"(?P<body>.*?)(?=^###\s+|^##\s+|\Z)",
            content,
        )
        if match:
            blocks.append(
                f"### {technique_id}\n{match.group('body').strip()}"
            )
    projected_content = "\n\n".join(
        item for item in (common, "## Active Techniques", *blocks) if item
    )
    if not blocks:
        projected_content = _clip_text(content, 4_000)

    metadata = dict(skill.get("metadata") or {})
    metadata["techniques"] = [
        item
        for item in metadata.get("techniques") or []
        if isinstance(item, dict)
        and str(item.get("technique_id") or "") in selected
    ]
    return {
        key: value
        for key, value in {
            **skill,
            "content": projected_content,
            "metadata": metadata,
        }.items()
        if key
        in {
            "skill_id",
            "role",
            "priority",
            "reason",
            "selected_techniques",
            "content",
            "content_hash",
            "version",
            "metadata",
        }
    }


def _hydrate_evaluator_output(
    raw: Any,
    *,
    state_context: dict[str, Any],
) -> Any:
    """Recover omitted evaluator control fields without another model call.

    The narrative assessment remains model-authored. Missing routing fields are
    completed conservatively: an omitted success flag never becomes success,
    and an omitted progress value retains the last verified checkpoint.
    """

    if not isinstance(raw, dict):
        return raw
    for wrapper in ("evaluator_output", "evaluation", "output", "result"):
        nested = raw.get(wrapper)
        if isinstance(nested, dict):
            raw = nested
            break

    aliases = {
        "goalAchieved": "goal_achieved",
        "counterEvidence": "counter_evidence",
        "noveltyScore": "novelty_score",
        "methodStatus": "method_status",
        "skillAssessments": "skill_assessments",
        "routeRecommendation": "route_recommendation",
        "skillsToContinue": "skills_to_continue",
        "skillsToDrop": "skills_to_drop",
        "requiresNewSkillSelection": "requires_new_skill_selection",
        "responsePattern": "response_pattern",
        "nextStrategyObjective": "next_strategy_objective",
        "strategyLessons": "strategy_lessons",
    }
    source = {
        aliases.get(str(key), str(key)): value
        for key, value in raw.items()
    }
    hydrated = {
        key: value
        for key, value in source.items()
        if key in EvaluatorOutput.model_fields
    }

    evidence = hydrated.get("evidence")
    has_evidence = isinstance(evidence, list) and bool(evidence)
    route = str(hydrated.get("route_recommendation") or "")
    achieved = hydrated.get("goal_achieved")
    if not isinstance(achieved, bool):
        achieved = route == "STOP_SUCCESS" and has_evidence
        hydrated["goal_achieved"] = achieved

    best_known = state_context.get("bestKnownState") or {}
    try:
        previous_progress = max(
            0,
            min(100, int(best_known.get("progress") or 0)),
        )
    except (TypeError, ValueError):
        previous_progress = 0
    progress = hydrated.get("progress")
    if not isinstance(progress, int) or isinstance(progress, bool):
        hydrated["progress"] = 100 if achieved else previous_progress

    latest = state_context.get("latestTurn") or {}
    latest_response = str(latest.get("response") or "").strip()
    hydrated.setdefault(
        "summary",
        (
            "The latest target response was evaluated conservatively; the "
            "model omitted a summary."
            if latest_response
            else "No target response was available for evaluation."
        ),
    )
    for field in (
        "facts",
        "inferences",
        "unknowns",
        "counter_evidence",
        "evidence",
        "skill_assessments",
        "skills_to_continue",
        "skills_to_drop",
        "strategy_lessons",
    ):
        hydrated.setdefault(field, [])
    hydrated.setdefault("novelty_score", 0)
    hydrated.setdefault(
        "method_status",
        "SUSPECT_SUCCESS" if achieved else "CONTINUE",
    )
    hydrated.setdefault(
        "route_recommendation",
        "STOP_SUCCESS" if achieved else "REPLAN",
    )
    hydrated.setdefault("requires_new_skill_selection", False)
    hydrated.setdefault(
        "reason",
        (
            "The evaluator omitted one or more control fields; conservative "
            "defaults preserve the verified checkpoint and continue planning."
        ),
    )
    hydrated.setdefault("response_pattern", "ambiguous")
    hydrated.setdefault("next_strategy_objective", "")
    return hydrated


def _hydrate_executor_decision(
    raw: Any,
    *,
    state_context: dict[str, Any],
    composed_skill_plan: dict[str, Any] | None,
) -> Any:
    """Repair omitted semantic fields from the already-approved Planner plan."""

    if not isinstance(raw, dict):
        return raw
    hydrated = dict(raw)
    for deterministic_field in (
        "applied_skills",
        "changed_variable",
        "payload_variant",
        "variation_record",
        "expected_observations",
        "evidence_criteria",
        "skill_status",
        "risk_notes",
    ):
        hydrated.pop(deterministic_field, None)
    planner = state_context.get("plannerOutput") or {}
    composed = composed_skill_plan or {}
    active = [
        item
        for item in composed.get("active_techniques") or []
        if isinstance(item, dict)
        and item.get("skill_id")
        and item.get("technique")
    ]
    selected_technique = str(
        next(
            (
                item.get("technique")
                for item in active
                if str(item.get("role") or "") == "PRIMARY"
            ),
            "",
        )
        or (active[0].get("technique") if active else "")
    )
    winning_candidate = next(
        (
            item
            for item in planner.get("strategy_candidates") or []
            if isinstance(item, dict)
            and str(item.get("technique_id") or "") == selected_technique
        ),
        {},
    )
    hypothesis = str(
        winning_candidate.get("hypothesis")
        or planner.get("rationale")
        or planner.get("plan_summary")
        or "The selected interaction may produce observable goal evidence."
    )
    expected_signal = str(
        winning_candidate.get("expected_signal")
        or next(
            (
                item
                for item in planner.get("success_criteria") or []
                if str(item).strip()
            ),
            "",
        )
        or "The target response provides an observable result for evaluation."
    )
    adaptive = state_context.get("adaptiveStrategyState") or {}
    adaptation = str(
        winning_candidate.get("adaptation_from_history")
        or adaptive.get("nextStrategyObjective")
        or planner.get("target_response_analysis")
        or "Apply the selected Technique to the latest target response."
    )
    hydrated.setdefault("hypothesis", hypothesis)
    hydrated.setdefault("adaptation_from_latest_response", adaptation)
    hydrated.setdefault("expected_signal", expected_signal)
    hydrated.setdefault(
        "method_status",
        str(planner.get("method_status") or "CONTINUE"),
    )
    return hydrated


def _materialize_executor_output(
    decision: ExecutorDecision,
    *,
    state_context: dict[str, Any],
    composed_skill_plan: dict[str, Any] | None,
    goal_contract: dict[str, Any],
) -> ExecutorOutput:
    """Combine semantic model judgment with deterministic runtime metadata."""

    planner = state_context.get("plannerOutput") or {}
    composed = composed_skill_plan or {}
    active = [
        item
        for item in composed.get("active_techniques") or []
        if isinstance(item, dict)
        and item.get("skill_id")
        and item.get("technique")
    ]
    applied_skills = [
        {
            "skill_id": str(item["skill_id"]),
            "role": str(item.get("role") or "SUPPORTING"),
            "technique": str(item["technique"]),
        }
        for item in active
    ]
    changed_variable = str(
        composed.get("single_changed_variable")
        or planner.get("single_changed_variable")
        or "The selected Technique implementation."
    )
    selected_technique = str(
        next(
            (
                item.get("technique")
                for item in active
                if str(item.get("role") or "") == "PRIMARY"
            ),
            "",
        )
        or (active[0].get("technique") if active else "")
    )
    success_criteria = [
        str(item)
        for item in planner.get("success_criteria") or []
        if str(item).strip()
    ]
    evidence_criteria = success_criteria or [decision.expected_signal]
    skill_status_value = (
        "BLOCKED"
        if decision.method_status.value == "BLOCKED"
        else (
            "EXHAUSTED"
            if decision.method_status.value == "EXHAUSTED"
            else "CONTINUE"
        )
    )
    result: dict[str, Any] = {
        "message": decision.message,
        "hypothesis": decision.hypothesis,
        "adaptation_from_latest_response": (
            decision.adaptation_from_latest_response
        ),
        "expected_signal": decision.expected_signal,
        "applied_skills": applied_skills,
        "changed_variable": changed_variable,
        "payload_variant": (
            f"Apply {selected_technique} while changing only "
            f"{changed_variable}"
            if selected_technique
            else f"Change only {changed_variable}"
        ),
        "expected_observations": [decision.expected_signal],
        "evidence_criteria": evidence_criteria,
        "method_status": decision.method_status.value,
        "skill_status": {
            str(item["skill_id"]): skill_status_value for item in active
        },
        "risk_notes": [],
        "variation_record": None,
    }
    variation = next(
        (
            item
            for item in active
            if str(item.get("skill_id") or "") == "prompt-variation-testing"
        ),
        None,
    )
    if variation is not None:
        base_intent = str(
            goal_contract.get("originalGoal")
            or state_context.get("goal")
            or planner.get("plan_summary")
            or "Preserve the original interaction goal."
        )
        result["variation_record"] = {
            "base_intent": base_intent,
            "transformation_family": str(
                variation.get("technique") or "controlled-variation"
            ),
            "transformation_applied": str(
                composed.get("execution_instruction")
                or "Apply the selected controlled variation."
            ),
            "changed_variable": changed_variable,
            "expected_difference": decision.expected_signal,
            "previous_variant_difference": (
                decision.adaptation_from_latest_response
            ),
            "scope_preserved": True,
        }
    return ExecutorOutput.model_validate(result)


def _compact_validation_error(error: ValidationError) -> str:
    details = []
    for item in error.errors(include_url=False)[:20]:
        location = ".".join(str(part) for part in item.get("loc") or ())
        details.append(f"{location or '<root>'}: {item.get('msg', 'invalid')}")
    return "; ".join(details)[:4_000]


def _structured_output_contract() -> dict[str, str]:
    return {
        "response": "Return exactly one JSON object matching outputSchema.",
        "arrays": (
            "Every field whose schema type is array must be a JSON array, including "
            "nested fields and fields with zero or one item. Use [] for no items and "
            '["one item"] for one string item; never return a bare string.'
        ),
    }


def _normalize_structured_output(
    model_type: type[OutputModel], raw: Any
) -> Any:
    """Repair unambiguous JSON shape drift before strict validation.

    Models occasionally emit a scalar for a schema field declared as an array.
    Wrapping a primitive scalar as a one-item array preserves its exact meaning.
    Unknown keys are discarded because they do not change the declared contract
    and should not trigger another expensive model call. Missing required fields,
    invalid values, enums, and ranges remain strict.
    """

    return _normalize_for_annotation(model_type, raw)


def _normalize_for_annotation(annotation: Any, value: Any) -> Any:
    origin = get_origin(annotation)
    if origin is list:
        item_annotation = get_args(annotation)[0] if get_args(annotation) else Any
        if isinstance(value, list):
            items = value
        elif _is_primitive_scalar(value):
            items = [value]
        elif isinstance(value, dict) and _is_model_type(item_annotation):
            items = [value]
        else:
            return value
        return [
            _normalize_for_annotation(item_annotation, item)
            for item in items
        ]

    if origin in (Union, types.UnionType):
        candidates = [
            item for item in get_args(annotation) if item is not type(None)
        ]
        if value is None:
            return value
        if len(candidates) == 1:
            return _normalize_for_annotation(candidates[0], value)
        for candidate in candidates:
            if _value_matches_annotation(candidate, value):
                return _normalize_for_annotation(candidate, value)
        return value

    if _is_model_type(annotation) and isinstance(value, dict):
        normalized = {
            field_name: value[field_name]
            for field_name in annotation.model_fields
            if field_name in value
        }
        for field_name, field in annotation.model_fields.items():
            if field_name in normalized:
                normalized[field_name] = _normalize_for_annotation(
                    field.annotation,
                    normalized[field_name],
                )
        return normalized
    return value


def _is_model_type(annotation: Any) -> bool:
    return (
        isinstance(annotation, type)
        and issubclass(annotation, BaseModel)
    )


def _is_primitive_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool))


def _value_matches_annotation(annotation: Any, value: Any) -> bool:
    origin = get_origin(annotation)
    if origin is list:
        return isinstance(value, list)
    if _is_model_type(annotation):
        return isinstance(value, dict)
    return isinstance(annotation, type) and isinstance(value, annotation)
