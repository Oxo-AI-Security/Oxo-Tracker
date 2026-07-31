from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from app.schemas.task_agent_v2 import TaskCreateRequest, TaskStatus
from app.services.executor_skill_service import ExecutorSkillService
from app.services.moonshot_api_service import MoonshotApiService
from app.services.settings_store import SettingsStore
from app.services.task_agent_attack_spec import (
    build_baseline_scan,
    compile_attack_spec,
)
from app.services.task_agent_graph import (
    ManualTaskStop,
    TaskAgentGraph,
    _adjudicate_claimed_success,
)
from app.services.task_agent_harness import compile_goal_contract
from app.services.task_agent_assets import (
    build_finding_from_run,
    build_run_manifest,
    build_scorer_ensemble,
    initial_history_from_snapshot,
    regrade_run_manifest,
    replay_run_manifest,
)
from app.services.task_agent_store import (
    DATA_ROOT,
    TaskAgentStore,
    normalize_target_key,
)


CHECKPOINT_PATH: Final = DATA_ROOT / "checkpoints.sqlite"
TERMINAL_STATUSES: Final = {
    TaskStatus.SUCCEEDED.value,
    TaskStatus.STOPPED_SAFETY.value,
    TaskStatus.STOPPED_MANUAL.value,
    TaskStatus.FAILED.value,
}
logger = logging.getLogger(__name__)

EXPLORATION_PRESETS: Final[dict[str, dict[str, Any]]] = {
    "light": {
        "max_rounds": 6,
        "max_runtime_seconds": 480,
        "max_input_tokens": 125_000,
        "max_output_tokens": 25_000,
        "max_active_skills": 1,
        "max_parallel_branches": 0,
        "max_variants_per_technique": 2,
        "max_family_rounds": 8,
        "max_family_input_tokens": 175_000,
        "max_family_output_tokens": 35_000,
        "max_evidence_stall_rounds": 3,
        "baseline_max_probes": 1,
        "branch_min_marginal_utility": 0.2,
        "branch_stop_no_gain_rounds": 2,
        "branch_followup_round_gap": 2,
        "branch_min_allocated_rounds": 2,
        "branch_max_allocated_rounds": 3,
    },
    "standard": {
        "max_rounds": 12,
        "max_runtime_seconds": 900,
        "max_input_tokens": 250_000,
        "max_output_tokens": 50_000,
        "max_active_skills": 2,
        "max_parallel_branches": 1,
        "max_variants_per_technique": 3,
        "max_family_rounds": 18,
        "max_family_input_tokens": 350_000,
        "max_family_output_tokens": 70_000,
        "max_evidence_stall_rounds": 4,
        "baseline_max_probes": 2,
        "branch_min_marginal_utility": 0.16,
        "branch_stop_no_gain_rounds": 2,
        "branch_followup_round_gap": 2,
        "branch_min_allocated_rounds": 2,
        "branch_max_allocated_rounds": 4,
    },
    "deep": {
        "max_rounds": 24,
        "max_runtime_seconds": 1_800,
        "max_input_tokens": 500_000,
        "max_output_tokens": 100_000,
        "max_active_skills": 3,
        "max_parallel_branches": 2,
        "max_variants_per_technique": 6,
        "max_family_rounds": 32,
        "max_family_input_tokens": 750_000,
        "max_family_output_tokens": 150_000,
        "max_evidence_stall_rounds": 4,
        "baseline_max_probes": 4,
        "branch_min_marginal_utility": 0.12,
        "branch_stop_no_gain_rounds": 3,
        "branch_followup_round_gap": 2,
        "branch_min_allocated_rounds": 2,
        "branch_max_allocated_rounds": 6,
    },
    "extreme": {
        "max_rounds": 40,
        "max_runtime_seconds": 3_600,
        "max_input_tokens": 1_000_000,
        "max_output_tokens": 200_000,
        "max_active_skills": 4,
        "max_parallel_branches": 2,
        "max_variants_per_technique": 8,
        "max_family_rounds": 64,
        "max_family_input_tokens": 1_500_000,
        "max_family_output_tokens": 300_000,
        "max_evidence_stall_rounds": 6,
        "baseline_max_probes": 6,
        "branch_min_marginal_utility": 0.09,
        "branch_stop_no_gain_rounds": 4,
        "branch_followup_round_gap": 3,
        "branch_min_allocated_rounds": 3,
        "branch_max_allocated_rounds": 8,
    },
}


class TaskPreflightError(ValueError):
    """A task-start validation failure that occurs before durable mutation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class TaskAgentRuntime:
    def __init__(
        self,
        *,
        store: TaskAgentStore | None = None,
        checkpoint_path: Path | None = None,
        graph: TaskAgentGraph | None = None,
    ) -> None:
        self.store = store or TaskAgentStore()
        self.store.backfill_success_memories()
        self.owner = f"runtime-{uuid.uuid4()}"
        self.max_workers = max(
            1,
            min(32, int(os.getenv("TASK_AGENT_MAX_WORKERS", "8"))),
        )
        self.control_model_concurrency = max(
            1,
            min(
                16,
                int(os.getenv("ATTACK_AGENT_MODEL_CONCURRENCY", "3")),
            ),
        )
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="task-agent",
        )
        self.ai_watch_max_workers = max(
            1,
            min(8, int(os.getenv("AI_WATCH_BACKGROUND_WORKERS", "2"))),
        )
        self._ai_watch_executor = ThreadPoolExecutor(
            max_workers=self.ai_watch_max_workers,
            thread_name_prefix="ai-watch",
        )
        self._ai_watch_futures: set[Future[Any]] = set()
        self._ai_watch_lock = threading.RLock()
        self._threads: dict[str, Future[Any]] = {}
        self._threads_lock = threading.RLock()
        self._branch_cleanup_lock = threading.RLock()
        self._closed = False
        self._maintenance_stop = threading.Event()
        self._checkpoint_connection: sqlite3.Connection | None = None
        self._owns_graph = graph is None
        if graph is None:
            resolved = (checkpoint_path or CHECKPOINT_PATH).resolve()
            resolved.parent.mkdir(parents=True, exist_ok=True)
            self._checkpoint_connection = sqlite3.connect(
                resolved,
                check_same_thread=False,
                timeout=30,
            )
            self._checkpoint_connection.execute("PRAGMA journal_mode=WAL")
            self._checkpoint_connection.execute("PRAGMA busy_timeout=30000")
            checkpointer = SqliteSaver(self._checkpoint_connection)
            checkpointer.setup()
            self.graph_service = TaskAgentGraph(
                store=self.store,
                checkpointer=checkpointer,
            )
        else:
            self.graph_service = graph
        self._maintenance_thread = threading.Thread(
            target=self._maintenance_loop,
            name="task-agent-supervisor",
            daemon=True,
        )
        self._maintenance_thread.start()

    def create(self, request: TaskCreateRequest) -> dict[str, Any]:
        resolved_config = self._preflight(request)
        task_id = f"task-{uuid.uuid4()}"
        now = datetime.now(timezone.utc).isoformat()
        target_key = normalize_target_key(request.target_key or request.runner_id)
        campaign = (
            self.store.get_campaign(request.campaign_id)
            if request.campaign_id
            else self.store.ensure_default_campaign(
                session_id=request.session_id,
                target_key=target_key,
                name=(
                    f"{request.endpoint_name} Attack Agent"
                    if request.endpoint_name
                    else "Attack Agent campaign"
                ),
            )
        )
        success_memories = self.store.find_relevant_success_memories(
            target_key=target_key,
            runner_id=request.runner_id,
            goal=request.goal,
            limit=3,
        )
        goal_contract = compile_goal_contract(request.goal)
        skill_service = getattr(self.graph_service, "skill_service", None)
        catalog_service = (
            skill_service
            if skill_service is not None
            else ExecutorSkillService()
        )
        skill_catalog = [
            item.model_dump(mode="json")
            for item in catalog_service.list_catalog()
            if item.enabled
        ]
        attack_spec = compile_attack_spec(
            goal=request.goal,
            goal_contract=goal_contract,
            target_key=target_key,
            endpoint_name=request.endpoint_name,
            skill_catalog=skill_catalog,
            supplied=(
                request.attack_spec.model_dump(mode="json")
                if request.attack_spec
                else None
            ),
        )
        baseline_scan = build_baseline_scan(
            attack_spec,
            max_probes=int(resolved_config.get("baseline_max_probes") or 0),
            history=[
                message.model_dump(mode="json")
                for message in request.history
            ],
            enabled=(
                bool(resolved_config.get("baseline_scanner_enabled", True))
                and request.branch_context is None
            ),
        )
        state: dict[str, Any] = {
            "schema_version": 2,
            "task_id": task_id,
            "session_id": request.session_id,
            "chat_id": request.chat_id,
            "runner_id": request.runner_id,
            "target_key": target_key,
            "goal": request.goal,
            "goal_contract": goal_contract,
            "attack_spec": attack_spec,
            "baseline_scan": baseline_scan,
            "attack_assets_initialized": True,
            "endpoint_name": request.endpoint_name,
            "history": [
                message.model_dump(mode="json")
                for message in request.history
            ],
            "initial_history": [
                message.model_dump(mode="json")
                for message in request.history
            ],
            "branch_context": (
                request.branch_context.model_dump(mode="json")
                if request.branch_context
                else None
            ),
            "branch_template": (
                _sanitize_task_agent_branch_template(
                    request.branch_template.model_dump(mode="json")
                )
                if request.branch_template
                else None
            ),
            "branch_reports": [],
            "branch_result": None,
            "branch_runner_deleted": False,
            "branch_cleanup": {
                "state": (
                    "pending"
                    if request.branch_context
                    else "not_applicable"
                ),
                "attempts": 0,
                "tombstoned": bool(request.branch_context),
                "next_retry_at": None,
                "last_error": None,
                "completed_at": None,
            },
            "branch_orchestration": {
                "schema_version": 2,
                "policy": "marginal-evidence-gain-per-cost",
                "last_decision": None,
                "updated_at": now,
            },
            "config": resolved_config,
            "status": TaskStatus.QUEUED.value,
            "current_node": "queued",
            "route": None,
            "stop_reason": None,
            "created_at": now,
            "updated_at": now,
            "started_at": now,
            "total_round": 0,
            "method_round": 0,
            "goal_progress": 0,
            "best_goal_progress": 0,
            "low_value_streak": 0,
            "evidence_stall_count": 0,
            "best_turn": None,
            "best_evidence": [],
            "goal_primary_skill_id": None,
            "goal_success_criteria": [],
            "execution_blocked_reason": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost": 0.0,
            "model_call_counts": {
                "planner": 0,
                "executor": 0,
                "evaluator": 0,
            },
            "committed_turns": [],
            "target_deliveries": {},
            "active_issue": None,
            "evidence": [],
            "evidence_ledger": [],
            "family_metrics": {},
            "gaps": [],
            "analysis_errors": [],
            "selected_skills": [],
            "loaded_skills": [],
            "composed_skill_plan": None,
            "skill_runtime_state": {},
            "active_techniques": [],
            "technique_history": [],
            "ai_watch_result": None,
            "ai_watch_reviews": {},
            "success_memories": success_memories,
            "research_state": {
                "immutable_goal": request.goal,
                "success_criteria": [],
                "best_evidence": [],
                "unresolved_gaps": [],
                "current_hypothesis": "",
                "open_hypotheses": [],
                "rejected_hypotheses": [],
                "tested_actions": [],
                "branch_reports": [],
                "decision_log": [],
                "next_best_actions": [],
                "steering_directives": [],
                "stop_reason": None,
                "updated_at": now,
            },
            "success_verification": {
                "status": "pending",
                "reason": "No success claim has been adjudicated.",
                "evidence_ids": [],
                "criterion": None,
                "proof_spec_version": int(
                    goal_contract["proof_spec"]["schema_version"]
                ),
                "proof_id": goal_contract["proof_spec"]["proof_id"],
                "requirement_results": [],
                "coverage": {},
                "adjudicator": "deterministic-proof-gate-v2",
                "verified_at": None,
            },
            "scorer_ensemble": None,
            "campaign_id": str(campaign["campaign_id"]),
            "source_manifest_id": request.source_manifest_id,
            "fork_origin": request.fork_origin,
            "steering_messages": [],
            "context_health": {},
        }
        self.store.create_task(state)
        self.store.attach_campaign_run(
            campaign_id=str(campaign["campaign_id"]),
            task_id=task_id,
        )
        self._launch(task_id, initial_state=state)
        return self.get(task_id)

    def get_run_manifest(self, task_id: str) -> dict[str, Any]:
        try:
            stored = self.store.get_run_manifest(task_id=task_id)
        except KeyError:
            stored = None
        if stored is not None and bool(stored.get("finalized")):
            return stored
        snapshot = self.store.get_snapshot(task_id)
        manifest = build_run_manifest(snapshot)
        return self.store.save_run_manifest(manifest)

    def replay(self, task_id: str) -> dict[str, Any]:
        manifest = self.get_run_manifest(task_id)
        if not manifest.get("finalized"):
            raise ValueError("Replay requires a finalized Run Manifest.")
        result = replay_run_manifest(manifest)
        self.store.append_event(
            task_id,
            "run.offline_replayed",
            {
                "replay_id": result["replay_id"],
                "manifest_id": manifest["manifest_id"],
                "target_call_count": 0,
            },
        )
        return result

    def regrade(
        self,
        task_id: str,
        *,
        scorer_versions: dict[str, str] | None = None,
        human_review: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        manifest = self.get_run_manifest(task_id)
        if not manifest.get("finalized"):
            raise ValueError("Regrade requires a finalized Run Manifest.")
        result = regrade_run_manifest(
            manifest,
            scorer_versions=scorer_versions,
            human_review=human_review,
        )
        stored = self.store.save_regrade(result)
        self.store.append_event(
            task_id,
            "run.offline_regraded",
            {
                "regrade_id": stored["regrade_id"],
                "manifest_id": manifest["manifest_id"],
                "target_call_count": 0,
                "final_verdict": (
                    stored.get("ensemble") or {}
                ).get("final_verdict"),
            },
        )
        return stored

    def review_scorer_ensemble(
        self,
        task_id: str,
        review: dict[str, Any],
    ) -> dict[str, Any]:
        snapshot = self.store.get_snapshot(task_id)
        if str(snapshot.get("status") or "") not in {
            *TERMINAL_STATUSES,
            TaskStatus.PAUSED.value,
        }:
            raise ValueError(
                "Human scorer review requires a paused or terminal run."
            )
        current = dict(snapshot.get("scorer_ensemble") or {})
        ensemble = build_scorer_ensemble(
            snapshot,
            verification=dict(snapshot.get("success_verification") or {}),
            human_review=review,
            source="human_review",
        )
        self.store.record_human_review(
            task_id=task_id,
            ensemble_id=str(
                current.get("ensemble_id") or ensemble["ensemble_id"]
            ),
            review=review,
        )
        updated = {
            **snapshot,
            "scorer_ensemble": ensemble,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.store.save_snapshot(
            task_id,
            updated,
            status=str(snapshot.get("status") or TaskStatus.RUNNING.value),
            current_node=str(snapshot.get("current_node") or "router"),
        )
        self.store.append_event(
            task_id,
            "scorer.human_reviewed",
            {
                "decision": review.get("decision"),
                "reviewer": review.get("reviewer"),
                "final_verdict": ensemble["final_verdict"],
            },
        )
        return public_task_snapshot(updated, self.graph_service)

    def create_finding(
        self,
        task_id: str,
        *,
        campaign_id: str | None = None,
    ) -> dict[str, Any]:
        snapshot = self.store.get_snapshot(task_id)
        manifest = self.get_run_manifest(task_id)
        if not manifest.get("finalized"):
            raise ValueError("Finding creation requires a finalized Run Manifest.")
        ensemble = dict(snapshot.get("scorer_ensemble") or {})
        if not ensemble:
            ensemble = build_scorer_ensemble(snapshot, source="finding_creation")
        resolved_campaign_id = str(
            campaign_id or snapshot.get("campaign_id") or ""
        )
        if not resolved_campaign_id:
            campaign = self.store.ensure_default_campaign(
                session_id=str(snapshot.get("session_id") or ""),
                target_key=str(snapshot.get("target_key") or ""),
            )
            resolved_campaign_id = str(campaign["campaign_id"])
        else:
            self.store.get_campaign(resolved_campaign_id)
        finding = build_finding_from_run(
            snapshot,
            manifest,
            ensemble,
            campaign_id=resolved_campaign_id,
        )
        stored = self.store.upsert_finding(finding)
        self.store.attach_campaign_run(
            campaign_id=resolved_campaign_id,
            task_id=task_id,
            manifest_id=str(manifest["manifest_id"]),
        )
        self.store.append_event(
            task_id,
            "finding.persisted",
            {
                "finding_id": stored["finding_id"],
                "campaign_id": resolved_campaign_id,
                "severity": stored["severity"],
            },
        )
        return stored

    def fork_from_round(
        self,
        task_id: str,
        *,
        round_number: int,
        goal: str | None = None,
        instruction: str | None = None,
    ) -> dict[str, Any]:
        source = self.store.get_snapshot(task_id)
        manifest = self.get_run_manifest(task_id)
        turns = list(manifest.get("turns") or [])
        if round_number < 0 or round_number > len(turns):
            raise ValueError(
                f"Fork round must be between 0 and {len(turns)}."
            )
        template = dict(source.get("branch_template") or {})
        endpoint_ids = list(template.get("endpoint_ids") or [])
        if not endpoint_ids:
            raise ValueError(
                "This run has no isolated target-session template for a safe fork."
            )
        source_snapshot_sha = _stable_snapshot_hash(source)
        fork_id = f"fork-{uuid.uuid4()}"
        remote = MoonshotApiService().create_redteam_session(
            name=(
                f"{template.get('session_name') or 'Attack Agent'} · "
                f"Fork R{round_number}"
            )[:240],
            endpoints=endpoint_ids,
            description=(
                f"Offline-manifest fork of {task_id} at round {round_number}."
            ),
            runner_args=_sanitize_task_agent_runner_args(
                dict(template.get("runner_args") or {})
            ),
        )
        runner_id = str(remote.get("runner_id") or "")
        if not runner_id:
            raise RuntimeError("Fork target runner creation returned no runner_id.")
        history = [
            dict(item)
            for item in (
                manifest.get("initial_history")
                or initial_history_from_snapshot(source)
            )
            if isinstance(item, dict)
        ]
        for turn in turns[:round_number]:
            history.extend(
                [
                    {"role": "user", "content": str(turn.get("request") or "")},
                    {
                        "role": "assistant",
                        "content": str(turn.get("response") or ""),
                    },
                ]
            )
        focus = (
            instruction
            or f"Continue from the evidence boundary after round {round_number}."
        )
        try:
            forked = self.create(
                TaskCreateRequest.model_validate(
                    {
                        "session_id": str(source.get("session_id") or ""),
                        "chat_id": f"fork-chat-{uuid.uuid4()}",
                        "runner_id": runner_id,
                        "target_key": str(source.get("target_key") or ""),
                        "goal": goal or str(source.get("goal") or ""),
                        "endpoint_name": source.get("endpoint_name"),
                        "history": history,
                        "branch_context": {
                            "parent_task_id": task_id,
                            "parent_chat_id": str(source.get("chat_id") or ""),
                            "branch_id": fork_id,
                            "branch_index": 1,
                            "branch_count": 1,
                            "focus": focus,
                            "sibling_focuses": [],
                            "fork_round": round_number,
                            "candidate_signature": f"manual-fork-r{round_number}",
                            "allocation_score": 100,
                            "expected_marginal_gain": 1,
                            "estimated_cost_units": 1,
                        },
                        "branch_template": template,
                        "campaign_id": source.get("campaign_id"),
                        "source_manifest_id": manifest.get("manifest_id"),
                        "fork_origin": {
                            "fork_id": fork_id,
                            "source_task_id": task_id,
                            "source_manifest_id": manifest.get("manifest_id"),
                            "source_manifest_sha256": manifest.get(
                                "manifest_sha256"
                            ),
                            "round": round_number,
                            "source_snapshot_sha256": source_snapshot_sha,
                            "instruction": instruction,
                        },
                        "attack_spec": source.get("attack_spec"),
                        "config": source.get("config") or {},
                    }
                )
            )
        except Exception:
            try:
                MoonshotApiService().delete_redteam_session(runner_id)
            except Exception:
                logger.exception("Unable to clean up failed fork runner %s", runner_id)
            raise
        after_hash = _stable_snapshot_hash(self.store.get_snapshot(task_id))
        if after_hash != source_snapshot_sha:
            raise RuntimeError("Fork mutated the source Run; refusing unsafe result.")
        self.store.append_event(
            task_id,
            "run.forked",
            {
                "fork_id": fork_id,
                "child_task_id": forked["task_id"],
                "round": round_number,
                "source_snapshot_sha256": source_snapshot_sha,
            },
        )
        return {
            "fork_id": fork_id,
            "source_task_id": task_id,
            "source_manifest_id": manifest["manifest_id"],
            "source_manifest_sha256": manifest["manifest_sha256"],
            "source_snapshot_sha256": source_snapshot_sha,
            "round": round_number,
            "target_call_count_before_fork_task": 0,
            "source_unchanged": True,
            "task": forked,
        }

    def _preflight(self, request: TaskCreateRequest) -> dict[str, Any]:
        """Validate the complete run contract before a task or child exists."""

        started = datetime.now(timezone.utc)
        config = request.config.model_dump(mode="json")
        intensity = str(config.get("exploration_intensity") or "")
        preset = EXPLORATION_PRESETS.get(intensity)
        if preset is None:
            raise TaskPreflightError(
                "invalid_exploration_intensity",
                "The selected exploration intensity is unsupported.",
            )
        # Exploration intensity is the single public effort control. Keeping
        # the mapping on the server prevents stale clients from accidentally
        # requesting a different branch or budget profile under the same label.
        config.update(preset)
        branch = request.branch_context
        if branch is not None:
            allocation_limits = {
                "max_rounds": branch.allocated_rounds,
                "max_input_tokens": branch.allocated_input_tokens,
                "max_output_tokens": branch.allocated_output_tokens,
            }
            for key, allocated in allocation_limits.items():
                if allocated is None:
                    continue
                configured = config.get(key)
                config[key] = (
                    int(allocated)
                    if configured is None
                    else min(int(configured), int(allocated))
                )
        if not any(
            config.get(key) is not None
            for key in (
                "max_rounds",
                "max_runtime_seconds",
                "max_input_tokens",
                "max_output_tokens",
                "max_estimated_cost",
            )
        ):
            raise TaskPreflightError(
                "missing_budget",
                "At least one runtime, round, token, or cost budget is required.",
            )

        provider = str(config.get("control_provider") or "").strip()
        model = str(config.get("control_model") or "").strip()
        try:
            if provider and model:
                SettingsStore().get_ai_settings(provider, model=model)
            else:
                default_model = getattr(
                    self.graph_service,
                    "model_service",
                    None,
                )
                if not str(getattr(default_model, "provider", "") or ""):
                    raise ValueError("No control provider is available")
                if not str(getattr(default_model, "model", "") or ""):
                    raise ValueError("No control model is available")
        except (OSError, ValueError) as error:
            raise TaskPreflightError(
                "invalid_control_model",
                f"Control model configuration is not ready: {error}",
            ) from error

        if self._owns_graph:
            moonshot = MoonshotApiService()
            try:
                runner = moonshot.read_runner(request.runner_id)
            except Exception as error:
                raise TaskPreflightError(
                    "target_runner_unavailable",
                    "The selected target runner is unavailable.",
                ) from error
            if not runner:
                raise TaskPreflightError(
                    "target_runner_unavailable",
                    "The selected target runner does not exist.",
                )
            for endpoint_id in (
                request.branch_template.endpoint_ids
                if request.branch_template
                else []
            ):
                try:
                    endpoint = moonshot.read_endpoint(endpoint_id)
                except Exception as error:
                    raise TaskPreflightError(
                        "connector_unavailable",
                        "A configured branch connector is unavailable.",
                    ) from error
                if not endpoint:
                    raise TaskPreflightError(
                        "connector_unavailable",
                        "A configured branch connector does not exist.",
                    )

        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        if elapsed >= 2:
            logger.warning(
                "Task Agent preflight exceeded the 2-second target: %.3fs",
                elapsed,
            )
        return config

    def get(self, task_id: str) -> dict[str, Any]:
        snapshot = self.store.get_snapshot(task_id)
        pending_goal = self.store.peek_goal_update(task_id)
        if pending_goal:
            snapshot = {**snapshot, "goal": pending_goal}
        return public_task_snapshot(snapshot, self.graph_service)

    def list(
        self,
        *,
        session_id: str | None = None,
        chat_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        snapshots = self.store.list_snapshots(
            session_id=session_id,
            chat_id=chat_id,
            limit=limit,
        )
        results: list[dict[str, Any]] = []
        for item in snapshots:
            pending_goal = self.store.peek_goal_update(str(item["task_id"]))
            if pending_goal:
                item = {**item, "goal": pending_goal}
            results.append(public_task_snapshot(item, self.graph_service))
        return results

    def adopt_branch_success(
        self,
        parent_task_id: str,
        child_task_id: str,
    ) -> dict[str, Any]:
        parent = self.store.get_snapshot(parent_task_id)
        child = self.store.get_snapshot(child_task_id)
        branch_context = child.get("branch_context") or {}
        if str(branch_context.get("parent_task_id") or "") != parent_task_id:
            raise ValueError("The child task does not belong to this parent task.")
        if str(child.get("status") or "") != TaskStatus.SUCCEEDED.value:
            raise ValueError("Only a successful child task can be adopted.")
        child_verification = child.get("success_verification") or {}
        if str(child_verification.get("status") or "") != "verified":
            raise ValueError(
                "Only a deterministically verified child success can be adopted."
            )
        if str(parent.get("session_id") or "") != str(child.get("session_id") or ""):
            raise ValueError("Parent and child tasks must belong to the same session.")
        now = datetime.now(timezone.utc).isoformat()
        parent_turns = list(parent.get("committed_turns") or [])
        child_turns = list(child.get("committed_turns") or [])
        existing_keys = {
            str(item.get("round_key") or "")
            for item in parent_turns
            if isinstance(item, dict)
        }
        adopted_turns: list[dict[str, Any]] = []
        next_round = int(parent.get("total_round") or 0)
        branch_label = (
            str(branch_context.get("focus") or "").strip()
            or f"Parallel branch {branch_context.get('branch_index') or 1}"
        )
        for item in child_turns:
            if not isinstance(item, dict):
                continue
            original_key = str(item.get("round_key") or "")
            adopted_key = f"{child_task_id}:{original_key or len(adopted_turns) + 1}"
            if adopted_key in existing_keys:
                continue
            next_round += 1
            adopted_turns.append(
                {
                    **item,
                    "round_key": adopted_key,
                    "round": next_round,
                    "origin_branch": {
                        "task_id": child_task_id,
                        "branch_id": branch_context.get("branch_id"),
                        "branch_index": branch_context.get("branch_index"),
                        "focus": branch_context.get("focus"),
                        "label": branch_label,
                    },
                }
            )

        merged_evidence = _merge_snapshot_evidence(
            parent.get("evidence") or [],
            child.get("evidence") or [],
        )
        merged_best_evidence = _merge_snapshot_evidence(
            parent.get("best_evidence") or [],
            child.get("best_evidence") or [],
        )
        merged_turns = [*parent_turns, *adopted_turns]
        latest_child_turn = (
            next(
                (
                    item
                    for item in reversed(adopted_turns)
                    if isinstance(item, dict)
                ),
                {},
            )
            if adopted_turns
            else {}
        )
        parent_candidate = {
            **parent,
            "latest_request": (
                child.get("latest_request")
                or latest_child_turn.get("request")
            ),
            "latest_response": (
                child.get("latest_response")
                or latest_child_turn.get("response")
            ),
            "latest_raw_response": child.get("latest_raw_response"),
            "evaluator_output": child.get("evaluator_output"),
            "sensitive_output": child.get("sensitive_output"),
            "ai_watch_result": (
                child.get("ai_watch_result")
                or child.get("sensitive_output")
            ),
            "evidence": merged_evidence,
            "best_evidence": merged_best_evidence,
            "committed_turns": merged_turns,
        }
        parent_verification = _adjudicate_claimed_success(
            parent_candidate,
            dict(child.get("evaluator_output") or {}),
        )
        if str(parent_verification.get("status") or "") != "verified":
            missing = (
                parent_verification.get("coverage")
                or parent_verification.get("reason")
            )
            self.store.append_event(
                parent_task_id,
                "branch.milestone_rejected_as_family_success",
                {
                    "child_task_id": child_task_id,
                    "child_proof_id": child_verification.get("proof_id"),
                    "parent_proof_id": parent_verification.get("proof_id"),
                    "missing": missing,
                },
            )
            raise ValueError(
                "The child reached a local milestone, but the parent "
                "ProofSpec is not fully covered."
            )

        adopted = {
            **parent,
            "status": TaskStatus.SUCCEEDED.value,
            "current_node": "router",
            "route": "STOP_SUCCESS",
            "stop_reason": (
                f"Objective reached by temporary parallel branch "
                f"{branch_context.get('branch_index') or 1}."
            ),
            "goal_progress": 100,
            "best_goal_progress": 100,
            "best_turn": child.get("best_turn") or parent.get("best_turn"),
            "best_evidence": merged_best_evidence,
            "total_round": next_round,
            "latest_request": child.get("latest_request"),
            "latest_response": child.get("latest_response"),
            "planner_output": child.get("planner_output"),
            "executor_output": child.get("executor_output"),
            "evaluator_output": child.get("evaluator_output"),
            "sensitive_output": child.get("sensitive_output"),
            "ai_watch_result": child.get("ai_watch_result")
            or child.get("sensitive_output"),
            "evidence": merged_evidence,
            "gaps": child.get("gaps") or [],
            "committed_turns": merged_turns,
            "branch_result": {
                "source_task_id": child_task_id,
                "source_chat_id": child.get("chat_id"),
                "source_runner_id": child.get("runner_id"),
                "branch_id": branch_context.get("branch_id"),
                "branch_index": branch_context.get("branch_index"),
                "focus": branch_context.get("focus"),
                "adopted_turn_count": len(adopted_turns),
                "adopted_at": now,
            },
            "branch_reports": self.store.list_branch_reports(parent_task_id),
            "research_state": {
                **(parent.get("research_state") or {}),
                "best_evidence": merged_best_evidence,
                "branch_reports": self.store.list_branch_reports(parent_task_id),
                "stop_reason": (
                    f"Verified objective reached by branch "
                    f"{branch_context.get('branch_index') or 1}."
                ),
                "updated_at": now,
            },
            "success_verification": parent_verification,
            "updated_at": now,
        }
        self.store.save_snapshot(
            parent_task_id,
            adopted,
            status=TaskStatus.SUCCEEDED.value,
            current_node="router",
            stop_reason=adopted["stop_reason"],
            stop_requested=True,
        )
        adopted = self._finalize_attack_assets(adopted)
        try:
            self.store.record_success_memory(adopted)
        except Exception:
            logger.exception(
                "Unable to record adopted success memory for task %s",
                parent_task_id,
            )
        self._stop_running_children(adopted)
        return public_task_snapshot(adopted, self.graph_service)

    def reconcile_existing_evidence(self, task_id: str) -> dict[str, Any]:
        """Re-evaluate already committed evidence without sending a target message."""

        snapshot = self.store.get_snapshot(task_id)
        if str(snapshot.get("status") or "") == TaskStatus.SUCCEEDED.value:
            return public_task_snapshot(snapshot, self.graph_service)
        if self._is_running(task_id):
            raise ValueError(
                "Stop or wait for the active task before reconciling existing evidence."
            )
        evaluator, changed = self.graph_service.reconcile_goal_evidence(snapshot)
        if not changed:
            raise ValueError(
                "Existing evidence did not satisfy the deterministic "
                "goal-consistency promotion requirements."
            )
        routed = self.graph_service._router(
            {
                **snapshot,
                "evaluator_output": evaluator,
            }
        )
        if str(routed.get("route") or "") != "STOP_SUCCESS":
            raise ValueError("Re-adjudication did not produce a success route.")
        now = datetime.now(timezone.utc).isoformat()
        reconciled = {
            **snapshot,
            **routed,
            "status": TaskStatus.SUCCEEDED.value,
            "current_node": "router",
            "error": None,
            "updated_at": now,
        }
        self.store.save_snapshot(
            task_id,
            reconciled,
            status=TaskStatus.SUCCEEDED.value,
            current_node="router",
            stop_reason=reconciled.get("stop_reason"),
        )
        reconciled = self._finalize_attack_assets(reconciled)
        self.store.append_trace(
            task_id,
            {
                "task_id": task_id,
                "round": int(reconciled.get("total_round") or 0),
                "node": "evidence_reconciliation",
                "attempt": 1,
                "started_at": now,
                "finished_at": now,
                "route": "STOP_SUCCESS",
                "output_summary": {
                    "goal_achieved": True,
                    "progress": 100,
                    "target_message_sent": False,
                },
            },
        )
        try:
            self.store.record_success_memory(reconciled)
        except Exception:
            logger.exception(
                "Unable to record reconciled success memory for task %s",
                task_id,
            )
        return public_task_snapshot(reconciled, self.graph_service)

    def pause(self, task_id: str) -> dict[str, Any]:
        snapshot = self.store.get_snapshot(task_id)
        if snapshot.get("status") in TERMINAL_STATUSES:
            return public_task_snapshot(snapshot, self.graph_service)
        self.store.request_pause(task_id)
        return self.get(task_id)

    def resume(self, task_id: str) -> dict[str, Any]:
        snapshot = self.store.get_snapshot(task_id)
        if snapshot.get("status") != TaskStatus.PAUSED.value:
            raise ValueError("Only a paused task can be resumed")
        self.store.clear_pause(task_id)
        self._launch(task_id, resume=True)
        return self.get(task_id)

    def stop(self, task_id: str, reason: str | None = None) -> dict[str, Any]:
        snapshot = self.store.get_snapshot(task_id)
        if not snapshot.get("branch_context"):
            self._stop_running_children(snapshot)
        if snapshot.get("status") in TERMINAL_STATUSES:
            return public_task_snapshot(snapshot, self.graph_service)
        self.store.request_stop(task_id, reason or "Stopped by user")
        if snapshot.get("status") == TaskStatus.PAUSED.value or not self._is_running(task_id):
            final = {
                **snapshot,
                "status": TaskStatus.STOPPED_MANUAL.value,
                "current_node": "stopped",
                "stop_reason": reason or "Stopped by user",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.store.save_snapshot(
                task_id,
                final,
                status=TaskStatus.STOPPED_MANUAL.value,
                current_node="stopped",
                stop_reason=final["stop_reason"],
            )
            self.store.cancel_pending_ai_watch_reviews(
                task_id,
                reason="AI Watch review was cancelled because the task stopped.",
            )
            final = self._finalize_attack_assets(
                self.store.get_snapshot(task_id)
            )
        return self.get(task_id)

    def steer(self, task_id: str, instruction: str) -> dict[str, Any]:
        self.store.queue_steering(task_id, instruction)
        return self.get(task_id)

    def follow_up_branch(
        self,
        parent_task_id: str,
        child_task_id: str,
        instruction: str,
    ) -> dict[str, Any]:
        child = self._owned_child(parent_task_id, child_task_id)
        self.store.queue_steering(child_task_id, instruction)
        self.store.append_event(
            parent_task_id,
            "branch.followup_queued",
            {
                "child_task_id": child_task_id,
                "instruction": instruction[:4_000],
                "parent_round": int(
                    self.store.get_snapshot(parent_task_id).get("total_round")
                    or 0
                ),
                "source": "manual",
            },
        )
        return self.get(child_task_id)

    def stop_branch(
        self,
        parent_task_id: str,
        child_task_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        self._owned_child(parent_task_id, child_task_id)
        return self.stop(
            child_task_id,
            reason or "Stopped by the parent task.",
        )

    def _owned_child(
        self,
        parent_task_id: str,
        child_task_id: str,
    ) -> dict[str, Any]:
        self.store.get_snapshot(parent_task_id)
        child = self.store.get_snapshot(child_task_id)
        branch = child.get("branch_context") or {}
        if str(branch.get("parent_task_id") or "") != parent_task_id:
            raise ValueError("The child task does not belong to this parent task.")
        return child

    def update_goal(self, task_id: str, goal: str) -> dict[str, Any]:
        normalized_goal = goal.strip()
        if not normalized_goal:
            raise ValueError("The updated goal cannot be empty.")
        snapshot = self.store.get_snapshot(task_id)
        if not snapshot.get("branch_context"):
            for child in self.store.list_child_snapshots(task_id):
                if str(child.get("status") or "") in TERMINAL_STATUSES:
                    continue
                try:
                    self.stop(
                        str(child["task_id"]),
                        "Parent goal changed; this specialist will be rebuilt.",
                    )
                except (KeyError, ValueError):
                    pass
        self.store.queue_goal_update(task_id, normalized_goal)
        return self.get(task_id)

    def recover(self) -> list[str]:
        self._retry_pending_branch_cleanup()
        recovered: list[str] = []
        for task_id in self.store.list_recoverable_task_ids():
            if self._launch(task_id, recovery=True):
                recovered.append(task_id)
        return recovered

    def shutdown(self) -> None:
        self._closed = True
        self._maintenance_stop.set()
        self._maintenance_thread.join(timeout=2)
        with self._threads_lock:
            live = list(self._threads.values())
        self._executor.shutdown(wait=False, cancel_futures=True)
        self._ai_watch_executor.shutdown(wait=False, cancel_futures=True)
        if not any(future.running() for future in live) and self._checkpoint_connection:
            self._checkpoint_connection.close()
            self._checkpoint_connection = None

    def _launch(
        self,
        task_id: str,
        *,
        initial_state: dict[str, Any] | None = None,
        resume: bool = False,
        recovery: bool = False,
    ) -> bool:
        with self._threads_lock:
            existing = self._threads.get(task_id)
            if existing and not existing.done():
                return False
            if self._closed:
                raise RuntimeError("Task Agent runtime is shutting down")
            future = self._executor.submit(
                self._run,
                task_id=task_id,
                initial_state=initial_state,
                resume=resume,
                recovery=recovery,
            )
            self._threads[task_id] = future
            return True

    def _run(
        self,
        *,
        task_id: str,
        initial_state: dict[str, Any] | None,
        resume: bool,
        recovery: bool,
    ) -> None:
        if not self.store.acquire_lease(task_id, self.owner, ttl_seconds=600):
            return
        config = {
            "configurable": {"thread_id": task_id},
            # This is a technical runaway guard, not a business round limit.
            "recursion_limit": 1_000_000,
        }
        try:
            input_value: Any
            if resume:
                input_value = Command(resume=True)
            elif recovery:
                checkpoint = self.graph_service.graph.get_state(config)
                input_value = None if checkpoint.values else self.store.get_snapshot(task_id)
            else:
                input_value = initial_state or self.store.get_snapshot(task_id)
            result = self.graph_service.graph.invoke(input_value, config=config)
            interrupts = result.get("__interrupt__") if isinstance(result, dict) else None
            if interrupts:
                paused = {
                    **self.store.get_snapshot(task_id),
                    **{key: value for key, value in result.items() if key != "__interrupt__"},
                    "status": TaskStatus.PAUSED.value,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                self.store.mark_paused(task_id, paused)
                return
            if not isinstance(result, dict):
                raise RuntimeError("Task graph returned an invalid final state")
            final_status = str(result.get("status") or TaskStatus.FAILED.value)
            if final_status not in TERMINAL_STATUSES:
                final_status = (
                    TaskStatus.SUCCEEDED.value
                    if result.get("route") == "STOP_SUCCESS"
                    else TaskStatus.STOPPED_SAFETY.value
                )
            final = {
                **result,
                "status": final_status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.store.save_snapshot(
                task_id,
                final,
                status=final_status,
                current_node=str(final.get("current_node") or "router"),
                stop_reason=final.get("stop_reason"),
            )
            if final_status == TaskStatus.SUCCEEDED.value:
                try:
                    self.store.record_success_memory(final)
                except Exception:
                    logger.exception(
                        "Unable to record success memory for task %s",
                        task_id,
                    )
        except ManualTaskStop as error:
            snapshot = self.store.get_snapshot(task_id)
            final = {
                **snapshot,
                "status": TaskStatus.STOPPED_MANUAL.value,
                "current_node": "stopped",
                "stop_reason": str(error),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.store.save_snapshot(
                task_id,
                final,
                status=TaskStatus.STOPPED_MANUAL.value,
                current_node="stopped",
                stop_reason=str(error),
            )
        except Exception as error:
            snapshot = self.store.get_snapshot(task_id)
            final = {
                **snapshot,
                "status": TaskStatus.FAILED.value,
                "current_node": "failed",
                "error": str(error)[:2_000],
                "active_issue": {
                    "component": "runtime",
                    "severity": "critical",
                    "code": "runtime_unhandled_failure",
                    "summary": "Task Agent runtime stopped unexpectedly.",
                    "detail": str(error)[:2_000],
                    "recoverable": False,
                    "delivery_id": None,
                    "retry_at": None,
                },
                "stop_reason": "Task Agent runtime failed.",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.store.save_snapshot(
                task_id,
                final,
                status=TaskStatus.FAILED.value,
                current_node="failed",
                stop_reason=final["stop_reason"],
            )
        finally:
            try:
                terminal = self.store.get_snapshot(task_id)
                if str(terminal.get("status") or "") in TERMINAL_STATUSES:
                    terminal = self.store.cancel_pending_ai_watch_reviews(
                        task_id,
                        reason=(
                            "AI Watch review was cancelled because the task "
                            "already reached a terminal state."
                        ),
                    )
                    if terminal.get("branch_context"):
                        self._finalize_branch_task(terminal)
                    else:
                        self._stop_running_children(terminal)
                    terminal = self._finalize_attack_assets(
                        self.store.get_snapshot(task_id)
                    )
            except Exception:
                logger.exception("Unable to finalize terminal task %s", task_id)
            self.store.release_lease(task_id, self.owner)
            with self._threads_lock:
                current = self._threads.get(task_id)
                if current is not None:
                    self._threads.pop(task_id, None)

    def _maintenance_loop(self) -> None:
        # A restart immediately compensates durable child-runner tombstones,
        # while normal task supervision retains its established polling cadence.
        try:
            self._retry_pending_branch_cleanup()
        except Exception:
            logger.exception("Task Agent startup cleanup sweep failed")
        while not self._maintenance_stop.wait(1.5):
            try:
                self._renew_live_leases()
                self._resume_recoverable_tasks()
                self._dispatch_ai_watch_reviews()
                self._supervise_branches()
                self._retry_pending_branch_cleanup()
            except Exception:
                logger.exception("Task Agent supervisor iteration failed")

    def _dispatch_ai_watch_reviews(self) -> None:
        with self._ai_watch_lock:
            self._ai_watch_futures = {
                future
                for future in self._ai_watch_futures
                if not future.done()
            }
            available = self.ai_watch_max_workers - len(
                self._ai_watch_futures
            )
        if available <= 0:
            return
        for review in self.store.claim_pending_ai_watch_reviews(
            limit=available,
        ):
            future = self._ai_watch_executor.submit(
                self._run_ai_watch_review,
                review,
            )
            with self._ai_watch_lock:
                self._ai_watch_futures.add(future)

    def _run_ai_watch_review(self, review: dict[str, Any]) -> None:
        task_id = str(review.get("task_id") or "")
        round_key = str(review.get("round_key") or "")
        if not task_id or not round_key:
            return
        try:
            output = self.graph_service.run_ai_watch_model(
                user_input=str(review.get("user_input") or ""),
                assistant_output=str(review.get("assistant_output") or ""),
            )
            self.store.complete_ai_watch_review(
                task_id,
                round_key=round_key,
                output=output,
            )
        except Exception as error:
            attempt = int(review.get("attempts") or 1)
            maximum = max(
                1,
                min(10, int(review.get("max_attempts") or 3)),
            )
            if _is_retryable_ai_watch_error(error) and attempt < maximum:
                retry_after = max(
                    0.0,
                    min(
                        3_600.0,
                        float(
                            getattr(error, "retry_after_seconds", None)
                            or 0.0
                        ),
                    ),
                )
                delay = max(
                    retry_after,
                    min(60.0, float(2 ** max(1, attempt))),
                )
                logger.warning(
                    "AI Watch review %s:%s failed transiently on attempt "
                    "%s/%s; retrying in %.1fs: %s",
                    task_id,
                    round_key,
                    attempt,
                    maximum,
                    delay,
                    error,
                )
                try:
                    self.store.retry_ai_watch_review(
                        task_id,
                        round_key=round_key,
                        delay_seconds=delay,
                        failure_kind=str(
                            getattr(error, "failure_kind", None)
                            or "transient_analysis"
                        ),
                        internal_error=str(error),
                    )
                except Exception:
                    logger.exception(
                        "Unable to schedule AI Watch retry for %s:%s",
                        task_id,
                        round_key,
                    )
                return
            logger.exception(
                "AI Watch background review failed permanently for %s:%s "
                "after %s attempt(s)",
                task_id,
                round_key,
                attempt,
            )
            public_error = (
                "AI Watch is temporarily unavailable after automatic "
                "retries. The Attack Agent result remains valid."
                if _is_retryable_ai_watch_error(error)
                else (
                    "AI Watch could not complete this optional review. "
                    "The Attack Agent result remains valid."
                )
            )
            try:
                self.store.complete_ai_watch_review(
                    task_id,
                    round_key=round_key,
                    output=None,
                    error=public_error,
                )
            except Exception:
                logger.exception(
                    "Unable to persist AI Watch failure for %s:%s",
                    task_id,
                    round_key,
                )
            return
        try:
            promoted = self.graph_service.reconcile_async_ai_watch_review(
                task_id,
                round_key,
            )
            if promoted:
                try:
                    self.store.record_success_memory(promoted)
                except Exception:
                    logger.exception(
                        "Unable to record AI Watch promoted success for %s",
                        task_id,
                    )
        except Exception as error:
            logger.exception(
                "AI Watch goal reconciliation failed for %s:%s",
                task_id,
                round_key,
            )
            self.store.append_event(
                task_id,
                "ai_watch.reconciliation_error",
                {
                    "round_key": round_key,
                    "error": str(error)[:2_000],
                },
            )
        finally:
            try:
                terminal = self.store.get_snapshot(task_id)
                if (
                    str(terminal.get("status") or "") in TERMINAL_STATUSES
                    and not _has_pending_ai_watch_reviews(terminal)
                ):
                    if terminal.get("branch_context"):
                        self._finalize_branch_task(terminal)
                    else:
                        self._stop_running_children(terminal)
                    self._finalize_attack_assets(
                        self.store.get_snapshot(task_id)
                    )
            except Exception:
                logger.exception(
                    "Unable to finalize post-review task %s",
                    task_id,
                )

    def _finalize_attack_assets(
        self,
        snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        """Freeze the run and preserve security assets independently of chat."""

        task_id = str(snapshot.get("task_id") or "")
        if not task_id:
            return snapshot
        ensemble = dict(snapshot.get("scorer_ensemble") or {})
        if not ensemble:
            ensemble = build_scorer_ensemble(
                snapshot,
                source="terminal_finalization",
            )
        candidate = {**snapshot, "scorer_ensemble": ensemble}
        manifest = self.store.save_run_manifest(
            build_run_manifest(candidate, finalized=True)
        )
        campaign_id = str(snapshot.get("campaign_id") or "")
        if not campaign_id:
            campaign = self.store.ensure_default_campaign(
                session_id=str(snapshot.get("session_id") or ""),
                target_key=str(snapshot.get("target_key") or ""),
            )
            campaign_id = str(campaign["campaign_id"])
        self.store.attach_campaign_run(
            campaign_id=campaign_id,
            task_id=task_id,
            manifest_id=str(manifest["manifest_id"]),
        )
        updated = {
            **candidate,
            "campaign_id": campaign_id,
            "source_manifest_id": str(manifest["manifest_id"]),
        }
        self.store.save_snapshot(
            task_id,
            updated,
            status=str(snapshot.get("status") or TaskStatus.FAILED.value),
            current_node=str(snapshot.get("current_node") or "router"),
            stop_reason=snapshot.get("stop_reason"),
        )
        if bool(ensemble.get("finding_eligible")):
            finding = build_finding_from_run(
                updated,
                manifest,
                ensemble,
                campaign_id=campaign_id,
            )
            self.store.upsert_finding(finding)
        return updated

    def _renew_live_leases(self) -> None:
        with self._threads_lock:
            task_ids = [
                task_id
                for task_id, future in self._threads.items()
                if not future.done()
            ]
        for task_id in task_ids:
            self.store.renew_lease(
                task_id,
                self.owner,
                ttl_seconds=120,
            )

    def _resume_recoverable_tasks(self) -> None:
        now = datetime.now(timezone.utc)
        for snapshot in self.store.list_snapshots(limit=500):
            if str(snapshot.get("status") or "") != TaskStatus.PAUSED.value:
                continue
            health = snapshot.get("context_health") or {}
            if (
                str(health.get("analysis_mode") or "")
                != "recoverable-pause"
                or bool(health.get("target_message_sent"))
            ):
                continue
            config = snapshot.get("config") or {}
            if not bool(config.get("auto_resume_transient_failures", True)):
                continue
            task_id = str(snapshot.get("task_id") or "")
            if not task_id or self._is_running(task_id):
                continue
            events = self.store.list_events(task_id, limit=5_000)
            attempts = sum(
                1
                for event in events
                if event.get("event_type") == "executor.auto_resume_started"
            )
            maximum = max(
                0,
                min(10, int(config.get("max_auto_resumes", 2))),
            )
            if attempts >= maximum:
                if not any(
                    event.get("event_type")
                    == "executor.auto_resume_exhausted"
                    for event in events
                ):
                    self.store.append_event(
                        task_id,
                        "executor.auto_resume_exhausted",
                        {
                            "attempts": attempts,
                            "max_auto_resumes": maximum,
                            "manual_resume_available": True,
                        },
                    )
                continue
            configured_delay = max(
                0.0,
                min(
                    3_600.0,
                    float(config.get("auto_resume_delay_seconds", 15.0)),
                ),
            )
            provider_retry_after = max(
                0.0,
                min(
                    3_600.0,
                    float(health.get("retry_after_seconds") or 0.0),
                ),
            )
            delay = max(configured_delay, provider_retry_after)
            eligible_at = _parse_datetime(
                str(snapshot.get("updated_at") or "")
            ) + timedelta(seconds=delay)
            if now < eligible_at:
                continue
            self.store.clear_pause(task_id)
            self.store.append_event(
                task_id,
                "executor.auto_resume_started",
                {
                    "attempt": attempts + 1,
                    "max_auto_resumes": maximum,
                    "paused_at": snapshot.get("updated_at"),
                    "delay_seconds": delay,
                    "target_message_sent": False,
                },
            )
            if not self._launch(task_id, resume=True):
                self.store.mark_paused(task_id, snapshot)

    def _supervise_branches(self) -> None:
        for parent in self.store.list_snapshots(limit=500):
            if parent.get("branch_context"):
                continue
            status = str(parent.get("status") or "")
            if status in TERMINAL_STATUSES:
                if _has_pending_ai_watch_reviews(parent):
                    continue
                self._stop_running_children(parent)
                continue
            if status not in {
                TaskStatus.QUEUED.value,
                TaskStatus.RUNNING.value,
                TaskStatus.PAUSING.value,
                TaskStatus.PAUSED.value,
                TaskStatus.STOPPING.value,
            }:
                continue
            self._maybe_spawn_branches(parent)

    def _maybe_spawn_branches(self, parent: dict[str, Any]) -> None:
        config = parent.get("config") or {}
        family = self.store.family_metrics(str(parent["task_id"]))
        if _family_budget_near_limit(config, family):
            return
        baseline_scan = parent.get("baseline_scan") or {}
        if (
            str(baseline_scan.get("status") or "")
            in {"pending", "running"}
            or str(parent.get("current_method") or "").startswith("baseline-")
        ):
            # Finish the cheap, deterministic control probes before allocating
            # model concurrency and family budget to adaptive child branches.
            return
        maximum = max(0, min(10, int(config.get("max_parallel_branches") or 0)))
        maximum = min(
            maximum,
            max(0, self.control_model_concurrency - 1),
        )
        template = parent.get("branch_template") or {}
        if (
            maximum <= 0
            or not template
            or int(parent.get("total_round") or 0)
            < int(config.get("branch_spawn_round") or 1)
            or not parent.get("evaluator_output")
        ):
            return
        children = self.store.list_child_snapshots(str(parent["task_id"]))
        active = [
            item
            for item in children
            if str(item.get("status") or "") not in TERMINAL_STATUSES
        ]
        self._manage_active_branches(parent, active)
        active_global_branches = sum(
            1
            for item in self.store.list_snapshots(limit=500)
            if item.get("branch_context")
            and str(item.get("status") or "") not in TERMINAL_STATUSES
        )
        global_branch_capacity = max(
            0,
            self.control_model_concurrency - 1 - active_global_branches,
        )
        available = min(
            max(0, maximum - len(active)),
            global_branch_capacity,
        )
        if not available:
            return
        reports = self.store.list_branch_reports(str(parent["task_id"]))
        seen = {
            str(
                (item.get("branch_context") or {}).get("candidate_signature")
                or ""
            )
            for item in children
        }
        seen.update(
            str(item.get("candidate_signature") or "") for item in reports
        )
        candidates = _rank_branch_candidates(parent, seen, reports)
        if not candidates:
            return
        evaluator = parent.get("evaluator_output") or {}
        progress = int(
            parent.get("best_goal_progress")
            or parent.get("goal_progress")
            or 0
        )
        novelty = int(evaluator.get("novelty_score") or 0)
        pattern = str(evaluator.get("response_pattern") or "")
        stalled = (
            pattern in {"refusal", "off-topic", "error"}
            or novelty <= int(config.get("branch_stall_novelty_threshold") or 15)
        )
        desired = 3 if stalled and progress < 60 else 2 if progress < 85 else 1
        minimum_utility = float(
            config.get("branch_min_marginal_utility") or 0
        )
        candidates = [
            item
            for item in candidates
            if float(item.get("marginal_utility") or 0) >= minimum_utility
        ]
        if not candidates:
            self.store.append_event(
                str(parent["task_id"]),
                "branch.spawn_skipped",
                {
                    "reason": "no_candidate_above_marginal_utility",
                    "minimum_utility": minimum_utility,
                    "family_metrics": family,
                },
            )
            return
        for offset, candidate in enumerate(
            candidates[: min(available, desired)],
            start=1,
        ):
            try:
                self._spawn_branch(parent, candidate, offset, maximum)
            except Exception:
                logger.exception(
                    "Unable to spawn branch for parent task %s",
                    parent.get("task_id"),
                )

    def _spawn_branch(
        self,
        parent: dict[str, Any],
        candidate: dict[str, Any],
        offset: int,
        branch_count: int,
    ) -> None:
        template = parent.get("branch_template") or {}
        branch_id = f"branch-{uuid.uuid4()}"
        runner_suffix = branch_id[-12:]
        remote = MoonshotApiService().create_redteam_session(
            (
                f"{template.get('session_name') or parent.get('session_id')} "
                f"attack agent branch {offset} {runner_suffix}"
            )[:240],
            [str(item) for item in template.get("endpoint_ids") or []],
            f"Durable Task Agent branch for {parent.get('chat_id')}",
            _sanitize_task_agent_runner_args(
                dict(template.get("runner_args") or {})
            ),
        )
        runner_id = str(remote.get("runner_id") or "")
        if not runner_id:
            raise RuntimeError("Branch target runner creation returned no runner_id.")
        config = {
            **(parent.get("config") or {}),
            "max_parallel_branches": 0,
        }
        allocation = _branch_budget_allocation(parent, candidate)
        request = TaskCreateRequest.model_validate(
            {
                "session_id": parent["session_id"],
                "chat_id": f"chat-{branch_id}",
                "runner_id": runner_id,
                "target_key": parent.get("target_key"),
                "goal": parent["goal"],
                "endpoint_name": parent.get("endpoint_name"),
                "history": parent.get("history") or [],
                "branch_context": {
                    "parent_task_id": parent["task_id"],
                    "parent_chat_id": parent["chat_id"],
                    "branch_id": branch_id,
                    "branch_index": _next_branch_index(
                        self.store.list_child_snapshots(str(parent["task_id"]))
                    ),
                    "branch_count": min(10, branch_count),
                    "focus": candidate["focus"],
                    "sibling_focuses": [],
                    "fork_round": int(parent.get("total_round") or 0),
                    "candidate_signature": candidate["signature"],
                    "allocation_score": float(candidate.get("score") or 0),
                    "expected_marginal_gain": float(
                        candidate.get("marginal_gain") or 0
                    ),
                    "estimated_cost_units": float(
                        candidate.get("estimated_cost_units") or 1
                    ),
                    "allocated_rounds": allocation["rounds"],
                    "allocated_input_tokens": allocation["input_tokens"],
                    "allocated_output_tokens": allocation["output_tokens"],
                },
                "attack_spec": parent.get("attack_spec"),
                "config": config,
            }
        )
        try:
            child = self.create(request)
        except Exception:
            MoonshotApiService().delete_redteam_session(runner_id)
            raise
        self.store.append_event(
            str(parent["task_id"]),
            "branch.spawned",
            {
                "child_task_id": child["task_id"],
                "branch_id": branch_id,
                "candidate_signature": candidate["signature"],
                "focus": candidate["focus"],
                "allocation": allocation,
                "marginal_gain": float(candidate.get("marginal_gain") or 0),
                "estimated_cost_units": float(
                    candidate.get("estimated_cost_units") or 1
                ),
                "marginal_utility": float(
                    candidate.get("marginal_utility") or 0
                ),
            },
        )

    def _manage_active_branches(
        self,
        parent: dict[str, Any],
        active: list[dict[str, Any]],
    ) -> None:
        if not active:
            return
        config = parent.get("config") or {}
        stop_rounds = int(config.get("branch_stop_no_gain_rounds") or 3)
        followup_gap = int(config.get("branch_followup_round_gap") or 2)
        parent_round = int(parent.get("total_round") or 0)
        parent_gap = str(
            (parent.get("evaluator_output") or {}).get(
                "next_strategy_objective"
            )
            or (parent.get("evaluator_output") or {}).get("reason")
            or next(iter(parent.get("gaps") or []), "")
        ).strip()
        for child in active:
            child_id = str(child.get("task_id") or "")
            if not child_id:
                continue
            branch = child.get("branch_context") or {}
            child_rounds = int(child.get("total_round") or 0)
            eligible = _eligible_evidence_count(child)
            stall = int(child.get("evidence_stall_count") or 0)
            if child_rounds >= stop_rounds and stall >= stop_rounds and eligible == 0:
                try:
                    self.stop(
                        child_id,
                        (
                            "Parent stopped this branch because its marginal "
                            "evidence gain remained zero for the configured window."
                        ),
                    )
                    self.store.append_event(
                        str(parent["task_id"]),
                        "branch.stopped_by_parent",
                        {
                            "child_task_id": child_id,
                            "child_rounds": child_rounds,
                            "evidence_stall_count": stall,
                            "eligible_evidence_count": eligible,
                            "source": "automatic",
                        },
                    )
                except (KeyError, ValueError):
                    pass
                continue
            if (
                not parent_gap
                or parent_round - int(branch.get("fork_round") or 0)
                < followup_gap
                or child_rounds == 0
                or stall == 0
                or _has_parent_followup_for_round(
                    self.store,
                    child_id,
                    parent_round,
                )
            ):
                continue
            instruction = (
                "Parent follow-up: preserve the immutable goal and redirect the "
                f"next attempt toward this unresolved gap: {parent_gap}"
            )[:4_000]
            try:
                self.store.queue_steering(child_id, instruction)
                self.store.append_event(
                    child_id,
                    "branch.parent_followup",
                    {
                        "parent_task_id": parent["task_id"],
                        "parent_round": parent_round,
                        "instruction": instruction,
                    },
                )
                self.store.append_event(
                    str(parent["task_id"]),
                    "branch.followup_queued",
                    {
                        "child_task_id": child_id,
                        "parent_round": parent_round,
                        "instruction": instruction,
                        "source": "automatic",
                    },
                )
            except (KeyError, ValueError):
                continue

    def _finalize_branch_task(self, child: dict[str, Any]) -> None:
        report = self.store.record_branch_report(child)
        if report is None:
            return
        parent_task_id = str(report["parent_task_id"])
        if (
            str(child.get("status") or "") == TaskStatus.SUCCEEDED.value
            and str(
                (child.get("success_verification") or {}).get("status") or ""
            )
            == "verified"
        ):
            try:
                self.adopt_branch_success(parent_task_id, str(child["task_id"]))
            except (KeyError, ValueError):
                logger.exception(
                    "Unable to adopt verified branch %s",
                    child.get("task_id"),
                )
                self._delete_branch_runner(child)
        else:
            self._delete_branch_runner(child)

    def _stop_running_children(self, parent: dict[str, Any]) -> None:
        for child in self.store.list_child_snapshots(str(parent["task_id"])):
            if str(child.get("status") or "") not in TERMINAL_STATUSES:
                try:
                    self.stop(
                        str(child["task_id"]),
                        "Parent task reached a terminal state.",
                    )
                except (KeyError, ValueError):
                    pass
            else:
                self._delete_branch_runner(child)

    def _delete_branch_runner(self, child: dict[str, Any]) -> None:
        task_id = str(child.get("task_id") or "")
        if not task_id:
            return
        with self._branch_cleanup_lock:
            try:
                current = self.store.get_snapshot(task_id)
            except KeyError:
                return
            runner_id = str(current.get("runner_id") or "")
            if not runner_id or current.get("branch_runner_deleted"):
                return
            previous = dict(current.get("branch_cleanup") or {})
            attempts = int(previous.get("attempts") or 0) + 1
            now = datetime.now(timezone.utc)
            already_missing = False
            try:
                result = MoonshotApiService().delete_redteam_session(
                    runner_id
                )
                if (
                    isinstance(result, dict)
                    and result.get("runner_deleted") is False
                ):
                    raise RuntimeError(
                        "The runner backend did not confirm runner deletion."
                    )
            except Exception as error:
                detail = str(error).lower()
                already_missing = any(
                    marker in detail
                    for marker in (
                        "does not exist",
                        "no runners found",
                        "runner file does not exist",
                        "unable to load runner because the runner file",
                    )
                )
                if not already_missing:
                    delay = min(300, 2 ** min(attempts, 8))
                    next_retry = now + timedelta(seconds=delay)
                    updated = {
                        **current,
                        "branch_runner_deleted": False,
                        "branch_cleanup": {
                            "state": "retry_scheduled",
                            "attempts": attempts,
                            "tombstoned": True,
                            "next_retry_at": next_retry.isoformat(),
                            "last_error": str(error)[:1_000],
                            "completed_at": None,
                        },
                        "updated_at": now.isoformat(),
                    }
                    self.store.save_snapshot(
                        task_id,
                        updated,
                        status=str(
                            current.get("status")
                            or TaskStatus.STOPPED_MANUAL.value
                        ),
                        current_node=str(
                            current.get("current_node") or "stopped"
                        ),
                        stop_reason=current.get("stop_reason"),
                    )
                    self.store.append_event(
                        task_id,
                        "branch.cleanup_retry_scheduled",
                        {
                            "runner_id": runner_id,
                            "attempt": attempts,
                            "delay_seconds": delay,
                            "next_retry_at": next_retry.isoformat(),
                            "error": str(error)[:1_000],
                        },
                    )
                    logger.warning(
                        "Branch runner %s cleanup attempt %s failed; "
                        "retry scheduled in %ss: %s",
                        runner_id,
                        attempts,
                        delay,
                        error,
                    )
                    return
                logger.info(
                    "Branch runner %s was already absent; marking cleanup complete.",
                    runner_id,
                )
            updated = {
                **current,
                "branch_runner_deleted": True,
                "branch_cleanup": {
                    "state": "complete",
                    "attempts": attempts,
                    "tombstoned": True,
                    "next_retry_at": None,
                    "last_error": None,
                    "completed_at": now.isoformat(),
                },
                "updated_at": now.isoformat(),
            }
            self.store.save_snapshot(
                task_id,
                updated,
                status=str(
                    current.get("status")
                    or TaskStatus.STOPPED_MANUAL.value
                ),
                current_node=str(
                    current.get("current_node") or "stopped"
                ),
                stop_reason=current.get("stop_reason"),
            )
            self.store.append_event(
                task_id,
                "branch.cleanup_completed",
                {
                    "runner_id": runner_id,
                    "attempts": attempts,
                    "already_missing": already_missing,
                },
            )

    def _retry_pending_branch_cleanup(self) -> None:
        now = datetime.now(timezone.utc)
        for child in self.store.list_terminal_branch_cleanup_candidates():
            cleanup = dict(child.get("branch_cleanup") or {})
            retry_at_raw = str(cleanup.get("next_retry_at") or "")
            if retry_at_raw and _parse_datetime(retry_at_raw) > now:
                continue
            self._delete_branch_runner(child)

    def _is_running(self, task_id: str) -> bool:
        with self._threads_lock:
            future = self._threads.get(task_id)
            return bool(future and not future.done())


_runtime: TaskAgentRuntime | None = None
_runtime_lock = threading.Lock()


def get_task_agent_runtime() -> TaskAgentRuntime:
    global _runtime
    with _runtime_lock:
        if _runtime is None:
            _runtime = TaskAgentRuntime()
        return _runtime


def shutdown_task_agent_runtime() -> None:
    global _runtime
    with _runtime_lock:
        runtime = _runtime
        _runtime = None
    if runtime is not None:
        runtime.shutdown()


def public_task_snapshot(
    state: dict[str, Any],
    graph_service: TaskAgentGraph | None = None,
) -> dict[str, Any]:
    started = _parse_datetime(str(state.get("started_at") or state.get("created_at") or ""))
    status = str(state.get("status") or TaskStatus.QUEUED.value)
    finished = (
        _parse_datetime(str(state.get("updated_at") or ""))
        if status in TERMINAL_STATUSES
        else datetime.now(timezone.utc)
    )
    elapsed = max(0.0, (finished - started).total_seconds())
    public_issue = _public_task_issue(state.get("active_issue"))
    public_error = state.get("error")
    if public_issue:
        public_error = None
    elif status == TaskStatus.FAILED.value and public_error:
        public_error = (
            "Task Agent stopped because the runtime encountered an internal "
            "error. Check the server trace for provider details."
        )
    store = getattr(graph_service, "store", None) if graph_service else None
    task_id = str(state.get("task_id") or "")
    evidence_ledger = state.get("evidence_ledger") or []
    family_metrics = state.get("family_metrics") or {}
    if store is not None and task_id:
        evidence_ledger = store.list_evidence_ledger(task_id)
        family_metrics = store.family_metrics(task_id)
    return {
        "schema_version": int(state.get("schema_version") or 2),
        "task_id": str(state.get("task_id") or ""),
        "session_id": str(state.get("session_id") or ""),
        "chat_id": str(state.get("chat_id") or ""),
        "runner_id": str(state.get("runner_id") or ""),
        "target_key": str(
            state.get("target_key") or state.get("runner_id") or ""
        ),
        "status": status,
        "current_node": str(state.get("current_node") or "queued"),
        "route": state.get("route"),
        "stop_reason": state.get("stop_reason"),
        "goal": str(state.get("goal") or ""),
        "goal_contract": state.get("goal_contract"),
        "attack_spec": state.get("attack_spec"),
        "baseline_scan": state.get("baseline_scan"),
        "attack_assets_initialized": bool(
            state.get("attack_assets_initialized", False)
        ),
        "goal_progress": int(state.get("goal_progress") or 0),
        "best_goal_progress": int(
            state.get("best_goal_progress")
            or state.get("goal_progress")
            or 0
        ),
        "best_turn": state.get("best_turn"),
        "best_evidence": state.get("best_evidence") or [],
        "total_round": int(state.get("total_round") or 0),
        "method_round": int(state.get("method_round") or 0),
        "current_method": state.get("current_method"),
        "current_skill_id": state.get("current_skill_id"),
        "selected_skills": state.get("selected_skills") or [],
        "loaded_skills": state.get("loaded_skills") or [],
        "composed_skill_plan": state.get("composed_skill_plan"),
        "skill_runtime_state": state.get("skill_runtime_state") or {},
        "active_techniques": state.get("active_techniques") or [],
        "technique_history": state.get("technique_history") or [],
        "elapsed_seconds": round(elapsed, 2),
        "input_tokens": int(state.get("input_tokens") or 0),
        "output_tokens": int(state.get("output_tokens") or 0),
        "estimated_cost": float(state.get("estimated_cost") or 0),
        "model_call_counts": state.get("model_call_counts") or {},
        "latest_request": state.get("latest_request"),
        "latest_response": state.get("latest_response"),
        "planner_output": state.get("planner_output"),
        "executor_output": state.get("executor_output"),
        "evaluator_output": state.get("evaluator_output"),
        "sensitive_output": state.get("sensitive_output"),
        "ai_watch_result": state.get("ai_watch_result") or state.get("sensitive_output"),
        "ai_watch_reviews": state.get("ai_watch_reviews") or {},
        "evidence": state.get("evidence") or [],
        "evidence_ledger": evidence_ledger,
        "family_metrics": family_metrics,
        "evidence_stall_count": int(
            state.get("evidence_stall_count") or 0
        ),
        "gaps": state.get("gaps") or [],
        "committed_turns": state.get("committed_turns") or [],
        "target_deliveries": state.get("target_deliveries") or {},
        "active_issue": public_issue,
        "prompt_versions": state.get("prompt_versions") or {},
        "analysis_errors": state.get("analysis_errors") or [],
        "branch_context": state.get("branch_context"),
        "branch_template": state.get("branch_template"),
        "branch_reports": state.get("branch_reports")
        or (
            graph_service.store.list_branch_reports(str(state.get("task_id") or ""))
            if (
                graph_service
                and getattr(graph_service, "store", None)
                and state.get("task_id")
            )
            else []
        ),
        "branch_result": state.get("branch_result"),
        "branch_runner_deleted": bool(
            state.get("branch_runner_deleted", False)
        ),
        "branch_cleanup": state.get("branch_cleanup") or {},
        "branch_orchestration": state.get("branch_orchestration") or {},
        "research_state": state.get("research_state"),
        "success_verification": state.get("success_verification"),
        "scorer_ensemble": state.get("scorer_ensemble"),
        "campaign_id": state.get("campaign_id"),
        "source_manifest_id": state.get("source_manifest_id"),
        "fork_origin": state.get("fork_origin"),
        "steering_messages": state.get("steering_messages") or [],
        "context_health": state.get("context_health") or {},
        "provider": (
            (state.get("config") or {}).get("control_provider")
            or (
                graph_service.model_service.provider
                if graph_service
                else None
            )
        ),
        "model": (
            (state.get("config") or {}).get("control_model")
            or (
                graph_service.model_service.model
                if graph_service
                else None
            )
        ),
        "error": public_error,
        "created_at": state.get("created_at"),
        "updated_at": state.get("updated_at"),
        "config": state.get("config") or {},
    }


def _public_task_issue(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    issue = dict(value)
    code = str(issue.get("code") or "")
    public_details = {
        "executor_transient_unavailable": (
            "The task is checkpointed before target delivery and may be "
            "resumed without duplicating a target message."
        ),
        "target_delivery_ambiguous": (
            "The transport cannot prove whether the target received the "
            "message, so automatic resend was blocked."
        ),
        "target_delivered_without_response": (
            "The target delivery is confirmed, but no response is available. "
            "Automatic resend was blocked."
        ),
        "duplicate_payload_blocked": (
            "The payload matched an existing exact or near-duplicate family "
            "request and did not represent a new variant. The task paused "
            "before another target request."
        ),
        "runtime_unhandled_failure": (
            "The task stopped safely. Provider diagnostics remain available "
            "in server traces."
        ),
    }
    issue["detail"] = public_details.get(
        code,
        str(issue.get("detail") or "")[:500],
    )
    return issue


def _family_budget_near_limit(
    config: dict[str, Any],
    metrics: dict[str, Any],
) -> bool:
    """Avoid opening a new branch when the family has little budget left."""

    checks = (
        ("max_family_rounds", "total_rounds"),
        ("max_family_input_tokens", "input_tokens"),
        ("max_family_output_tokens", "output_tokens"),
    )
    for budget_key, metric_key in checks:
        budget = config.get(budget_key)
        if budget is None:
            continue
        if float(metrics.get(metric_key) or 0) >= float(budget) * 0.85:
            return True
    return False


def _sanitize_task_agent_runner_args(
    _runner_args: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return a runner configuration that cannot apply manual-chat controls."""
    return {
        "prompt_template": "",
        "attack_module": "",
        "context_strategy": "",
        "cs_num_of_prev_prompts": 0,
        "metric": "",
        "system_prompt": "",
    }


def _is_retryable_ai_watch_error(error: Exception) -> bool:
    if bool(getattr(error, "retryable", False)):
        return True
    detail = str(error).lower()
    return any(
        marker in detail
        for marker in (
            "timed out",
            "timeout",
            "rate limited",
            "http 408",
            "http 425",
            "http 429",
            "http 500",
            "http 502",
            "http 503",
            "http 504",
            "connection reset",
            "temporarily unavailable",
            "unable to reach the active ai model",
        )
    )


def _sanitize_task_agent_branch_template(
    template: dict[str, Any],
) -> dict[str, Any]:
    return {
        **template,
        "runner_args": _sanitize_task_agent_runner_args(
            template.get("runner_args")
            if isinstance(template.get("runner_args"), dict)
            else {}
        ),
    }


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _has_pending_ai_watch_reviews(state: dict[str, Any]) -> bool:
    return any(
        str((review or {}).get("status") or "") in {"pending", "analyzing"}
        for review in (state.get("ai_watch_reviews") or {}).values()
    )


def _merge_snapshot_evidence(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in [*left, *right]:
        if not isinstance(item, dict):
            continue
        key = str(
            item.get("evidence_id")
            or item.get("observation")
            or item
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged[:500]


def _stable_snapshot_hash(snapshot: dict[str, Any]) -> str:
    """Hash source-run semantics while ignoring unrelated supervisor metadata."""

    payload = {
        "task_id": snapshot.get("task_id"),
        "goal": snapshot.get("goal"),
        "goal_contract": snapshot.get("goal_contract"),
        "attack_spec": snapshot.get("attack_spec"),
        "status": snapshot.get("status"),
        "total_round": snapshot.get("total_round"),
        "committed_turns": snapshot.get("committed_turns") or [],
        "success_verification": snapshot.get("success_verification"),
        "scorer_ensemble": snapshot.get("scorer_ensemble"),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _rank_branch_candidates(
    parent: dict[str, Any],
    seen: set[str],
    reports: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    planner = parent.get("planner_output") or {}
    config = parent.get("config") or {}
    minimum = float(config.get("min_strategy_candidate_score") or 45)
    prior_reports = [
        item for item in reports or [] if isinstance(item, dict)
    ]
    ranked: list[dict[str, Any]] = []
    for item in planner.get("strategy_candidates") or []:
        if not isinstance(item, dict):
            continue
        signature = "|".join(
            [
                str(item.get("skill_id") or ""),
                str(item.get("technique_id") or ""),
                " ".join(
                    str(item.get("hypothesis") or "").lower().split()
                ),
            ]
        )[:500]
        if not signature.strip("|") or signature in seen:
            continue
        score = (
            0.35 * float(item.get("goal_alignment") or 0)
            + 0.30 * float(item.get("expected_information_gain") or 0)
            + 0.20 * float(item.get("response_fit") or 0)
            + 0.15 * float(item.get("novelty") or 0)
        )
        if score < minimum:
            continue
        skill_id = str(item.get("skill_id") or "")
        technique_id = str(item.get("technique_id") or "")
        related = [
            report
            for report in prior_reports
            if str(report.get("candidate_signature") or "").startswith(
                f"{skill_id}|{technique_id}|"
            )
        ]
        expected_gain = max(
            0.0,
            min(
                1.0,
                float(item.get("expected_information_gain") or 0) / 100,
            ),
        )
        observed_gains = [
            max(0.0, min(1.0, float(report.get("evidence_gain") or 0)))
            for report in related
        ]
        smoothed_gain = (
            2 * expected_gain + sum(observed_gains)
        ) / (2 + len(observed_gains))
        novelty_discount = 1 / (1 + 0.5 * len(related))
        marginal_gain = max(
            0.0,
            min(1.0, smoothed_gain * novelty_discount),
        )
        observed_costs = [
            max(0.01, float(report.get("cost_units") or 1))
            for report in related
        ]
        estimated_cost_units = (
            sum(observed_costs) / len(observed_costs)
            if observed_costs
            else max(0.01, float(item.get("estimated_cost_units") or 1))
        )
        marginal_utility = marginal_gain / estimated_cost_units
        focus = "\n".join(
            value
            for value in (
                (
                    f"{item.get('candidate_id') or 'candidate'}: "
                    f"{item.get('skill_id') or 'goal-skill'} / "
                    f"{item.get('technique_id') or 'technique'}"
                ),
                str(item.get("hypothesis") or ""),
                (
                    "Adapt from history: "
                    f"{item.get('adaptation_from_history')}"
                    if item.get("adaptation_from_history")
                    else ""
                ),
                (
                    f"Expected signal: {item.get('expected_signal')}"
                    if item.get("expected_signal")
                    else ""
                ),
            )
            if value
        )[:4_000]
        ranked.append(
            {
                "signature": signature,
                "focus": focus,
                "score": score,
                "skill_id": skill_id,
                "technique_id": technique_id,
                "marginal_gain": round(marginal_gain, 6),
                "estimated_cost_units": round(estimated_cost_units, 6),
                "marginal_utility": round(marginal_utility, 6),
                "related_report_count": len(related),
            }
        )
    return sorted(
        ranked,
        key=lambda item: (
            -item["marginal_utility"],
            -item["score"],
            item["signature"],
        ),
    )


def _branch_budget_allocation(
    parent: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, int]:
    config = parent.get("config") or {}
    minimum = int(config.get("branch_min_allocated_rounds") or 2)
    maximum = int(config.get("branch_max_allocated_rounds") or 8)
    utility = max(0.0, float(candidate.get("marginal_utility") or 0))
    normalized = utility / (1 + utility)
    rounds = round(minimum + (maximum - minimum) * normalized)
    rounds = max(minimum, min(maximum, rounds))
    parent_rounds = max(1, int(config.get("max_rounds") or maximum))
    input_budget = max(1, int(config.get("max_input_tokens") or 1))
    output_budget = max(1, int(config.get("max_output_tokens") or 1))
    share = max(0.1, min(0.5, rounds / parent_rounds))
    return {
        "rounds": rounds,
        "input_tokens": max(1, int(input_budget * share)),
        "output_tokens": max(1, int(output_budget * share)),
    }


def _eligible_evidence_count(snapshot: dict[str, Any]) -> int:
    ledger = [
        item
        for item in snapshot.get("evidence_ledger") or []
        if isinstance(item, dict)
    ]
    ledger_count = sum(
        str(item.get("status") or "") == "confirmed"
        and bool((item.get("provenance") or {}).get("eligible_for_progress"))
        for item in ledger
    )
    if ledger_count:
        return ledger_count
    return sum(
        bool((item.get("provenance") or {}).get("eligible_for_progress"))
        for item in snapshot.get("evidence") or []
        if isinstance(item, dict)
    )


def _has_parent_followup_for_round(
    store: TaskAgentStore,
    child_task_id: str,
    parent_round: int,
) -> bool:
    events = store.list_events(child_task_id, limit=200)
    return any(
        str(item.get("event_type") or "") == "branch.parent_followup"
        and int((item.get("payload") or {}).get("parent_round") or -1)
        == parent_round
        for item in events
    )


def _next_branch_index(children: list[dict[str, Any]]) -> int:
    used = {
        int((item.get("branch_context") or {}).get("branch_index") or 0)
        for item in children
    }
    return next((index for index in range(1, 11) if index not in used), 10)
