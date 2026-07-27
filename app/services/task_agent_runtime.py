from __future__ import annotations

import logging
import os
import sqlite3
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from app.schemas.task_agent_v2 import TaskCreateRequest, TaskStatus
from app.services.moonshot_api_service import MoonshotApiService
from app.services.task_agent_graph import ManualTaskStop, TaskAgentGraph
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
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="task-agent",
        )
        self._threads: dict[str, Future[Any]] = {}
        self._threads_lock = threading.RLock()
        self._closed = False
        self._maintenance_stop = threading.Event()
        self._checkpoint_connection: sqlite3.Connection | None = None
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
        task_id = f"task-{uuid.uuid4()}"
        now = datetime.now(timezone.utc).isoformat()
        target_key = normalize_target_key(request.target_key or request.runner_id)
        success_memories = self.store.find_relevant_success_memories(
            target_key=target_key,
            runner_id=request.runner_id,
            goal=request.goal,
            limit=3,
        )
        state: dict[str, Any] = {
            "task_id": task_id,
            "session_id": request.session_id,
            "chat_id": request.chat_id,
            "runner_id": request.runner_id,
            "target_key": target_key,
            "goal": request.goal,
            "endpoint_name": request.endpoint_name,
            "payload_name": request.payload_name,
            "attack_module": request.attack_module,
            "context_strategy": request.context_strategy,
            "history": [message.model_dump(mode="json") for message in request.history],
            "branch_context": (
                request.branch_context.model_dump(mode="json")
                if request.branch_context
                else None
            ),
            "branch_template": (
                request.branch_template.model_dump(mode="json")
                if request.branch_template
                else None
            ),
            "branch_reports": [],
            "branch_result": None,
            "config": request.config.model_dump(mode="json"),
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
            "best_turn": None,
            "best_evidence": [],
            "goal_primary_skill_id": None,
            "goal_success_criteria": [],
            "execution_blocked_reason": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost": 0.0,
            "committed_turns": [],
            "evidence": [],
            "gaps": [],
            "analysis_errors": [],
            "selected_skills": [],
            "loaded_skills": [],
            "composed_skill_plan": None,
            "skill_runtime_state": {},
            "active_techniques": [],
            "technique_history": [],
            "ai_watch_result": None,
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
                "adjudicator": "deterministic-evidence-gate-v2",
                "verified_at": None,
            },
            "steering_messages": [],
            "context_health": {},
        }
        self.store.create_task(state)
        self._launch(task_id, initial_state=state)
        return self.get(task_id)

    def get(self, task_id: str) -> dict[str, Any]:
        return public_task_snapshot(self.store.get_snapshot(task_id), self.graph_service)

    def list(
        self,
        *,
        session_id: str | None = None,
        chat_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return [
            public_task_snapshot(item, self.graph_service)
            for item in self.store.list_snapshots(
                session_id=session_id,
                chat_id=chat_id,
                limit=limit,
            )
        ]

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
        verification = child.get("success_verification") or {}
        if str(verification.get("status") or "") != "verified":
            raise ValueError(
                "Only a deterministically verified child success can be adopted."
            )
        if str(parent.get("session_id") or "") != str(child.get("session_id") or ""):
            raise ValueError("Parent and child tasks must belong to the same session.")

        self.store.request_stop(
            parent_task_id,
            "A parallel child branch reached the objective.",
        )
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
            "committed_turns": [*parent_turns, *adopted_turns],
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
            "success_verification": verification,
            "updated_at": now,
        }
        self.store.save_snapshot(
            parent_task_id,
            adopted,
            status=TaskStatus.SUCCEEDED.value,
            current_node="router",
            stop_reason=adopted["stop_reason"],
        )
        try:
            self.store.record_success_memory(adopted)
        except Exception:
            logger.exception(
                "Unable to record adopted success memory for task %s",
                parent_task_id,
            )
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
        return self.get(task_id)

    def steer(self, task_id: str, instruction: str) -> dict[str, Any]:
        self.store.queue_steering(task_id, instruction)
        return self.get(task_id)

    def recover(self) -> list[str]:
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
                if (
                    terminal.get("branch_context")
                    and str(terminal.get("status") or "") in TERMINAL_STATUSES
                ):
                    self._finalize_branch_task(terminal)
            except Exception:
                logger.exception("Unable to finalize branch task %s", task_id)
            self.store.release_lease(task_id, self.owner)
            with self._threads_lock:
                current = self._threads.get(task_id)
                if current is not None:
                    self._threads.pop(task_id, None)

    def _maintenance_loop(self) -> None:
        while not self._maintenance_stop.wait(1.5):
            try:
                self._renew_live_leases()
                self._supervise_branches()
            except Exception:
                logger.exception("Task Agent supervisor iteration failed")

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

    def _supervise_branches(self) -> None:
        for parent in self.store.list_snapshots(limit=500):
            if parent.get("branch_context"):
                continue
            status = str(parent.get("status") or "")
            if status in TERMINAL_STATUSES:
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
        maximum = max(0, min(10, int(config.get("max_parallel_branches") or 0)))
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
        available = max(0, maximum - len(active))
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
        candidates = _rank_branch_candidates(parent, seen)
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
        remote = MoonshotApiService().create_redteam_session(
            (
                f"{template.get('session_name') or parent.get('session_id')} "
                f"· branch {offset}"
            )[:240],
            [str(item) for item in template.get("endpoint_ids") or []],
            f"Durable Task Agent branch for {parent.get('chat_id')}",
            dict(template.get("runner_args") or {}),
        )
        runner_id = str(remote.get("runner_id") or "")
        if not runner_id:
            raise RuntimeError("Branch target runner creation returned no runner_id.")
        branch_id = f"branch-{uuid.uuid4()}"
        config = {
            **(parent.get("config") or {}),
            "max_parallel_branches": 0,
        }
        request = TaskCreateRequest.model_validate(
            {
                "session_id": parent["session_id"],
                "chat_id": f"chat-{branch_id}",
                "runner_id": runner_id,
                "target_key": parent.get("target_key"),
                "goal": parent["goal"],
                "endpoint_name": parent.get("endpoint_name"),
                "payload_name": parent.get("payload_name"),
                "attack_module": parent.get("attack_module"),
                "context_strategy": parent.get("context_strategy"),
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
                },
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
            },
        )

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
        runner_id = str(child.get("runner_id") or "")
        if not runner_id or child.get("branch_runner_deleted"):
            return
        try:
            MoonshotApiService().delete_redteam_session(runner_id)
            updated = {
                **child,
                "branch_runner_deleted": True,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.store.save_snapshot(
                str(child["task_id"]),
                updated,
                status=str(child.get("status") or TaskStatus.STOPPED_MANUAL.value),
                current_node=str(child.get("current_node") or "stopped"),
                stop_reason=child.get("stop_reason"),
            )
        except Exception:
            logger.exception("Unable to delete branch runner %s", runner_id)

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
    elapsed = max(0.0, (datetime.now(timezone.utc) - started).total_seconds())
    return {
        "task_id": str(state.get("task_id") or ""),
        "session_id": str(state.get("session_id") or ""),
        "chat_id": str(state.get("chat_id") or ""),
        "runner_id": str(state.get("runner_id") or ""),
        "target_key": str(
            state.get("target_key") or state.get("runner_id") or ""
        ),
        "status": str(state.get("status") or TaskStatus.QUEUED.value),
        "current_node": str(state.get("current_node") or "queued"),
        "route": state.get("route"),
        "stop_reason": state.get("stop_reason"),
        "goal": str(state.get("goal") or ""),
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
        "latest_request": state.get("latest_request"),
        "latest_response": state.get("latest_response"),
        "planner_output": state.get("planner_output"),
        "executor_output": state.get("executor_output"),
        "evaluator_output": state.get("evaluator_output"),
        "sensitive_output": state.get("sensitive_output"),
        "ai_watch_result": state.get("ai_watch_result") or state.get("sensitive_output"),
        "evidence": state.get("evidence") or [],
        "gaps": state.get("gaps") or [],
        "committed_turns": state.get("committed_turns") or [],
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
        "research_state": state.get("research_state"),
        "success_verification": state.get("success_verification"),
        "steering_messages": state.get("steering_messages") or [],
        "context_health": state.get("context_health") or {},
        "provider": graph_service.model_service.provider if graph_service else None,
        "model": graph_service.model_service.model if graph_service else None,
        "error": state.get("error"),
        "created_at": state.get("created_at"),
        "updated_at": state.get("updated_at"),
        "config": state.get("config") or {},
    }


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


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


def _rank_branch_candidates(
    parent: dict[str, Any],
    seen: set[str],
) -> list[dict[str, Any]]:
    planner = parent.get("planner_output") or {}
    config = parent.get("config") or {}
    minimum = float(config.get("min_strategy_candidate_score") or 45)
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
            }
        )
    return sorted(ranked, key=lambda item: (-item["score"], item["signature"]))


def _next_branch_index(children: list[dict[str, Any]]) -> int:
    used = {
        int((item.get("branch_context") or {}).get("branch_index") or 0)
        for item in children
    }
    return next((index for index in range(1, 11) if index not in used), 10)
