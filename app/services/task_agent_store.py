from __future__ import annotations

import json
import re
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final
from urllib.parse import urlsplit


DATA_ROOT: Final = Path("data") / "task_agent_v2"
ACTIVE_STATUSES: Final = ("queued", "running", "pausing", "paused", "stopping")
RECOVERABLE_STATUSES: Final = ("queued", "running", "pausing", "stopping")


class TaskStoreError(RuntimeError):
    pass


class ActiveTaskExistsError(TaskStoreError):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"An active task already exists for this chat: {task_id}")
        self.task_id = task_id


class TaskAgentStore:
    def __init__(self, path: Path | None = None) -> None:
        root = DATA_ROOT
        root.mkdir(parents=True, exist_ok=True)
        self.path = (path or root / "tasks.sqlite").resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.RLock()
        self._initialize()

    def create_task(self, snapshot: dict[str, Any]) -> None:
        now = _utc_now()
        with self._write_lock, self._connect() as connection:
            existing = connection.execute(
                f"""
                SELECT task_id FROM tasks
                WHERE session_id = ? AND chat_id = ?
                  AND status IN ({",".join("?" for _ in ACTIVE_STATUSES)})
                ORDER BY updated_at DESC LIMIT 1
                """,
                (
                    snapshot["session_id"],
                    snapshot["chat_id"],
                    *ACTIVE_STATUSES,
                ),
            ).fetchone()
            if existing:
                raise ActiveTaskExistsError(str(existing["task_id"]))
            connection.execute(
                """
                INSERT INTO tasks (
                    task_id, session_id, chat_id, runner_id, status, current_node,
                    snapshot_json, pause_requested, stop_requested, stop_reason,
                    created_at, updated_at, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, NULL, ?, ?, 1)
                """,
                (
                    snapshot["task_id"],
                    snapshot["session_id"],
                    snapshot["chat_id"],
                    snapshot["runner_id"],
                    snapshot.get("status", "queued"),
                    snapshot.get("current_node", "queued"),
                    _dumps(snapshot),
                    now,
                    now,
                ),
            )

    def save_snapshot(
        self,
        task_id: str,
        snapshot: dict[str, Any],
        *,
        status: str | None = None,
        current_node: str | None = None,
        stop_reason: str | None = None,
    ) -> None:
        now = _utc_now()
        resolved_status = status or str(snapshot.get("status") or "running")
        resolved_node = current_node or str(snapshot.get("current_node") or "")
        with self._write_lock, self._connect() as connection:
            current = connection.execute(
                "SELECT status, snapshot_json FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if current is None:
                raise KeyError(task_id)
            verification = snapshot.get("success_verification") or {}
            allow_revocation = (
                str(verification.get("status") or "") == "revoked"
            )
            if (
                str(current["status"]) == "succeeded"
                and resolved_status != "succeeded"
                and not allow_revocation
            ):
                return
            try:
                persisted_snapshot = json.loads(
                    str(current["snapshot_json"])
                )
            except (json.JSONDecodeError, TypeError):
                persisted_snapshot = {}
            snapshot = _merge_async_ai_watch_state(
                persisted_snapshot,
                snapshot,
            )
            cursor = connection.execute(
                """
                UPDATE tasks
                   SET snapshot_json = ?, status = ?, current_node = ?,
                       stop_reason = ?, updated_at = ?, version = version + 1
                 WHERE task_id = ?
                """,
                (
                    _dumps(snapshot),
                    resolved_status,
                    resolved_node,
                    stop_reason if stop_reason is not None else snapshot.get("stop_reason"),
                    now,
                    task_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(task_id)

    def get_snapshot(self, task_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT snapshot_json, status, current_node, stop_reason FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if row is None:
            raise KeyError(task_id)
        snapshot = json.loads(row["snapshot_json"])
        snapshot["status"] = row["status"]
        snapshot["current_node"] = row["current_node"]
        snapshot["stop_reason"] = row["stop_reason"] or snapshot.get("stop_reason")
        return snapshot

    def list_snapshots(
        self,
        *,
        session_id: str | None = None,
        chat_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        if session_id:
            clauses.append("session_id = ?")
            parameters.append(session_id)
        if chat_id:
            clauses.append("chat_id = ?")
            parameters.append(chat_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.append(max(1, min(limit, 500)))
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT task_id FROM tasks {where}
                ORDER BY updated_at DESC LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [self.get_snapshot(str(row["task_id"])) for row in rows]

    def list_recoverable_task_ids(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT task_id FROM tasks
                WHERE status IN ({",".join("?" for _ in RECOVERABLE_STATUSES)})
                ORDER BY updated_at ASC
                """,
                RECOVERABLE_STATUSES,
            ).fetchall()
        return [str(row["task_id"]) for row in rows]

    def request_pause(self, task_id: str) -> None:
        self._set_control(task_id, pause=True, status="pausing")

    def clear_pause(self, task_id: str) -> None:
        now = _utc_now()
        with self._write_lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                   SET pause_requested = 0, status = 'running', updated_at = ?,
                       version = version + 1
                 WHERE task_id = ?
                """,
                (now, task_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(task_id)

    def request_stop(self, task_id: str, reason: str | None = None) -> None:
        self._set_control(task_id, stop=True, status="stopping", reason=reason)

    def control_flags(self, task_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT pause_requested, stop_requested, stop_reason, status
                  FROM tasks WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
        if row is None:
            raise KeyError(task_id)
        return {
            "pause_requested": bool(row["pause_requested"]),
            "stop_requested": bool(row["stop_requested"]),
            "stop_reason": row["stop_reason"],
            "status": row["status"],
        }

    def mark_paused(self, task_id: str, snapshot: dict[str, Any]) -> None:
        snapshot = {**snapshot, "status": "paused"}
        self.save_snapshot(task_id, snapshot, status="paused")

    def acquire_lease(self, task_id: str, owner: str, ttl_seconds: int = 120) -> bool:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=max(10, ttl_seconds))
        with self._write_lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                   SET lease_owner = ?, lease_until = ?, updated_at = ?
                 WHERE task_id = ?
                   AND (lease_owner IS NULL OR lease_owner = ? OR lease_until < ?)
                """,
                (
                    owner,
                    expires.isoformat(),
                    now.isoformat(),
                    task_id,
                    owner,
                    now.isoformat(),
                ),
            )
            return cursor.rowcount == 1

    def renew_lease(self, task_id: str, owner: str, ttl_seconds: int = 120) -> bool:
        expires = datetime.now(timezone.utc) + timedelta(seconds=max(10, ttl_seconds))
        with self._write_lock, self._connect() as connection:
            cursor = connection.execute(
                "UPDATE tasks SET lease_until = ? WHERE task_id = ? AND lease_owner = ?",
                (expires.isoformat(), task_id, owner),
            )
            return cursor.rowcount == 1

    def release_lease(self, task_id: str, owner: str) -> None:
        with self._write_lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE tasks SET lease_owner = NULL, lease_until = NULL
                 WHERE task_id = ? AND lease_owner = ?
                """,
                (task_id, owner),
            )

    def append_trace(self, task_id: str, trace: dict[str, Any]) -> None:
        with self._write_lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO traces (
                    task_id, round_number, node, attempt, started_at, finished_at,
                    latency_ms, trace_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    int(trace.get("round") or 0),
                    str(trace.get("node") or ""),
                    int(trace.get("attempt") or 1),
                    trace.get("started_at"),
                    trace.get("finished_at"),
                    float(trace.get("latency_ms") or 0),
                    _dumps(trace),
                ),
            )

    def append_event(
        self,
        task_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        now = _utc_now()
        with self._write_lock, self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO task_events (task_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, event_type, _dumps(payload), now),
            )
            event_id = int(cursor.lastrowid)
        return {
            "event_id": event_id,
            "task_id": task_id,
            "event_type": event_type,
            "payload": payload,
            "created_at": now,
        }

    def queue_ai_watch_review(
        self,
        task_id: str,
        *,
        round_key: str,
        round_number: int,
        user_input: str,
        assistant_output: str,
    ) -> bool:
        now = _utc_now()
        with self._write_lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT snapshot_json FROM tasks WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            snapshot = json.loads(str(row["snapshot_json"]))
            reviews = dict(snapshot.get("ai_watch_reviews") or {})
            existing = reviews.get(round_key) or {}
            if str(existing.get("status") or "") in {
                "pending",
                "analyzing",
                "complete",
            }:
                return False
            reviews[round_key] = {
                "round_key": round_key,
                "round": int(round_number),
                "status": "pending",
                "user_input": user_input,
                "assistant_output": assistant_output,
                "queued_at": now,
                "started_at": None,
                "completed_at": None,
                "summary": "AI Watch model review is queued.",
                "output": None,
                "error": None,
            }
            snapshot["ai_watch_reviews"] = reviews
            snapshot["committed_turns"] = _set_turn_ai_watch_status(
                snapshot.get("committed_turns") or [],
                round_key=round_key,
                status="pending",
            )
            connection.execute(
                """
                UPDATE tasks SET snapshot_json = ?, updated_at = ?,
                                 version = version + 1
                 WHERE task_id = ?
                """,
                (_dumps(snapshot), now, task_id),
            )
            connection.execute(
                """
                INSERT INTO task_events (task_id, event_type, payload_json, created_at)
                VALUES (?, 'ai_watch.queued', ?, ?)
                """,
                (
                    task_id,
                    _dumps(
                        {
                            "round_key": round_key,
                            "round": int(round_number),
                        }
                    ),
                    now,
                ),
            )
        return True

    def claim_pending_ai_watch_reviews(
        self,
        *,
        limit: int = 2,
    ) -> list[dict[str, Any]]:
        now = _utc_now()
        claimed: list[dict[str, Any]] = []
        maximum = max(1, min(int(limit), 16))
        with self._write_lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT task_id, snapshot_json FROM tasks
                 ORDER BY updated_at ASC
                """
            ).fetchall()
            for row in rows:
                if len(claimed) >= maximum:
                    break
                task_id = str(row["task_id"])
                snapshot = json.loads(str(row["snapshot_json"]))
                reviews = dict(snapshot.get("ai_watch_reviews") or {})
                changed = False
                for round_key, source in sorted(
                    reviews.items(),
                    key=lambda item: int(
                        (item[1] or {}).get("round") or 0
                    ),
                ):
                    if len(claimed) >= maximum:
                        break
                    review = dict(source or {})
                    if not _ai_watch_review_is_claimable(review):
                        continue
                    review.update(
                        {
                            "status": "analyzing",
                            "started_at": now,
                            "summary": "AI Watch model is reviewing this turn.",
                            "error": None,
                        }
                    )
                    reviews[round_key] = review
                    claimed.append(
                        {
                            "task_id": task_id,
                            **review,
                        }
                    )
                    changed = True
                if not changed:
                    continue
                snapshot["ai_watch_reviews"] = reviews
                for review in claimed:
                    if review.get("task_id") != task_id:
                        continue
                    snapshot["committed_turns"] = _set_turn_ai_watch_status(
                        snapshot.get("committed_turns") or [],
                        round_key=str(review["round_key"]),
                        status="analyzing",
                    )
                connection.execute(
                    """
                    UPDATE tasks SET snapshot_json = ?, updated_at = ?,
                                     version = version + 1
                     WHERE task_id = ?
                    """,
                    (_dumps(snapshot), now, task_id),
                )
        return claimed

    def complete_ai_watch_review(
        self,
        task_id: str,
        *,
        round_key: str,
        output: dict[str, Any] | None,
        error: str | None = None,
    ) -> dict[str, Any]:
        now = _utc_now()
        status = "error" if error else "complete"
        with self._write_lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT snapshot_json FROM tasks WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            snapshot = json.loads(str(row["snapshot_json"]))
            reviews = dict(snapshot.get("ai_watch_reviews") or {})
            review = dict(reviews.get(round_key) or {})
            if not review:
                raise KeyError(f"{task_id}:{round_key}")
            review.update(
                {
                    "status": status,
                    "completed_at": now,
                    "summary": (
                        str((output or {}).get("summary") or "")
                        if output
                        else f"AI Watch model review failed: {error}"
                    ),
                    "output": output,
                    "error": error,
                }
            )
            reviews[round_key] = review
            snapshot["ai_watch_reviews"] = reviews
            snapshot["committed_turns"] = _complete_turn_ai_watch_review(
                snapshot.get("committed_turns") or [],
                round_key=round_key,
                status=status,
                output=output,
                error=error,
            )
            if output is not None:
                snapshot["sensitive_output"] = output
                snapshot["ai_watch_result"] = output
            if error:
                snapshot["analysis_errors"] = [
                    *list(snapshot.get("analysis_errors") or []),
                    f"ai_watch[{round_key}]: {error}",
                ][-100:]
            connection.execute(
                """
                UPDATE tasks SET snapshot_json = ?, updated_at = ?,
                                 version = version + 1
                 WHERE task_id = ?
                """,
                (_dumps(snapshot), now, task_id),
            )
            connection.execute(
                """
                INSERT INTO task_events (task_id, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    task_id,
                    f"ai_watch.{status}",
                    _dumps(
                        {
                            "round_key": round_key,
                            "round": int(review.get("round") or 0),
                            "summary": review["summary"],
                            "finding_count": len(
                                (output or {}).get("findings") or []
                            ),
                            "error": error,
                        }
                    ),
                    now,
                ),
            )
        return self.get_snapshot(task_id)

    def promote_ai_watch_success(
        self,
        task_id: str,
        *,
        round_key: str,
        evaluator: dict[str, Any],
        verification: dict[str, Any],
    ) -> dict[str, Any]:
        """Atomically promote a model-reviewed turn without sending again."""

        now = _utc_now()
        with self._write_lock, self._connect() as connection:
            row = connection.execute(
                "SELECT status, snapshot_json FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            snapshot = json.loads(str(row["snapshot_json"]))
            if str(row["status"]) == "succeeded":
                return snapshot
            reviews = dict(snapshot.get("ai_watch_reviews") or {})
            review = dict(reviews.get(round_key) or {})
            if str(review.get("status") or "") != "complete":
                raise ValueError("AI Watch review is not complete.")
            turn = next(
                (
                    item
                    for item in snapshot.get("committed_turns") or []
                    if str(item.get("round_key") or "") == round_key
                ),
                None,
            )
            if not turn:
                raise ValueError("The reviewed turn is no longer available.")
            turns = _replace_turn_goal_outcome(
                snapshot.get("committed_turns") or [],
                round_key=round_key,
                evaluator=evaluator,
            )
            evidence = list(evaluator.get("evidence") or [])
            snapshot.update(
                {
                    "status": "succeeded",
                    "current_node": "router",
                    "route": "STOP_SUCCESS",
                    "stop_reason": (
                        "AI Watch completed its background model review and "
                        "verified target-origin evidence for the current goal."
                    ),
                    "goal_progress": 100,
                    "best_goal_progress": 100,
                    "latest_request": turn.get("request"),
                    "latest_response": turn.get("response"),
                    "evaluator_output": evaluator,
                    "sensitive_output": review.get("output"),
                    "ai_watch_result": review.get("output"),
                    "success_verification": verification,
                    "committed_turns": turns,
                    "best_evidence": _merge_evidence_records(
                        snapshot.get("best_evidence") or [],
                        evidence,
                    ),
                    "evidence": _merge_evidence_records(
                        snapshot.get("evidence") or [],
                        evidence,
                    ),
                    "best_turn": {
                        "round": int(turn.get("round") or 0),
                        "method": turn.get("method"),
                        "skillId": turn.get("skill_id"),
                        "activeTechniques": turn.get("active_techniques") or [],
                        "request": turn.get("request"),
                        "response": turn.get("response"),
                        "progress": 100,
                        "summary": evaluator.get("summary"),
                    },
                    "updated_at": now,
                }
            )
            connection.execute(
                """
                UPDATE tasks
                   SET snapshot_json = ?, status = 'succeeded',
                       current_node = 'router', stop_requested = 1,
                       stop_reason = ?, updated_at = ?, version = version + 1
                 WHERE task_id = ?
                """,
                (
                    _dumps(snapshot),
                    snapshot["stop_reason"],
                    now,
                    task_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO task_events (task_id, event_type, payload_json, created_at)
                VALUES (?, 'ai_watch.goal_reconciled', ?, ?)
                """,
                (
                    task_id,
                    _dumps(
                        {
                            "round_key": round_key,
                            "round": int(turn.get("round") or 0),
                            "verification": verification,
                        }
                    ),
                    now,
                ),
            )
        return self.get_snapshot(task_id)

    def list_events(
        self,
        task_id: str,
        *,
        after_id: int = 0,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, event_type, payload_json, created_at
                  FROM task_events
                 WHERE task_id = ? AND id > ?
                 ORDER BY id ASC LIMIT ?
                """,
                (task_id, max(0, after_id), max(1, min(limit, 5_000))),
            ).fetchall()
        return [
            {
                "event_id": int(row["id"]),
                "task_id": task_id,
                "event_type": str(row["event_type"]),
                "payload": json.loads(str(row["payload_json"])),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

    def queue_steering(self, task_id: str, instruction: str) -> dict[str, Any]:
        snapshot = self.get_snapshot(task_id)
        if str(snapshot.get("status") or "") not in ACTIVE_STATUSES:
            raise ValueError("Only an active task can accept steering.")
        return self.append_event(
            task_id,
            "steering.queued",
            {"instruction": instruction.strip()},
        )

    def consume_steering(self, task_id: str) -> list[str]:
        with self._write_lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, payload_json FROM task_events
                 WHERE task_id = ? AND event_type = 'steering.queued'
                 ORDER BY id ASC
                """,
                (task_id,),
            ).fetchall()
            instructions: list[str] = []
            for row in rows:
                try:
                    payload = json.loads(str(row["payload_json"]))
                except (json.JSONDecodeError, TypeError):
                    payload = {}
                instruction = str(payload.get("instruction") or "").strip()
                if instruction:
                    instructions.append(instruction)
                connection.execute(
                    """
                    UPDATE task_events SET event_type = 'steering.applied'
                     WHERE id = ?
                    """,
                    (int(row["id"]),),
                )
        return instructions

    def list_traces(self, task_id: str, limit: int = 1_000) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT trace_json FROM traces WHERE task_id = ?
                ORDER BY id ASC LIMIT ?
                """,
                (task_id, max(1, min(limit, 10_000))),
            ).fetchall()
        return [json.loads(row["trace_json"]) for row in rows]

    def record_skill_usage(self, skill_id: str, task_id: str, outcome: str) -> None:
        with self._write_lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO skill_usage (skill_id, task_id, outcome, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (skill_id, task_id, outcome, _utc_now()),
            )

    def list_child_snapshots(self, parent_task_id: str) -> list[dict[str, Any]]:
        children = []
        for snapshot in self.list_snapshots(limit=500):
            branch = snapshot.get("branch_context") or {}
            if str(branch.get("parent_task_id") or "") == parent_task_id:
                children.append(snapshot)
        return children

    def record_branch_report(self, snapshot: dict[str, Any]) -> dict[str, Any] | None:
        branch = snapshot.get("branch_context") or {}
        parent_task_id = str(branch.get("parent_task_id") or "").strip()
        child_task_id = str(snapshot.get("task_id") or "").strip()
        branch_id = str(branch.get("branch_id") or "").strip()
        if not parent_task_id or not child_task_id or not branch_id:
            return None
        evaluator = snapshot.get("evaluator_output") or {}
        status = str(snapshot.get("status") or "")
        verification = snapshot.get("success_verification") or {}
        outcome = {
            "succeeded": "succeeded",
            "failed": "failed",
            "stopped_manual": "stopped",
            "stopped_safety": "exhausted",
        }.get(status, "running")
        turns = [
            item
            for item in snapshot.get("committed_turns") or []
            if isinstance(item, dict)
        ]
        actions = [
            str(item.get("request") or "")[:4_000]
            for item in turns[-20:]
            if str(item.get("request") or "").strip()
        ]
        observations = [
            str(item.get("response") or "")[:4_000]
            for item in turns[-20:]
            if str(item.get("response") or "").strip()
        ]
        disconfirmed = [
            str(item)
            for item in [
                *(evaluator.get("counter_evidence") or []),
                *(snapshot.get("failed_routes") or []),
            ]
            if str(item).strip()
        ][-30:]
        now = _utc_now()
        report = {
            "report_id": f"branch-report-{child_task_id}",
            "parent_task_id": parent_task_id,
            "child_task_id": child_task_id,
            "branch_id": branch_id,
            "branch_index": int(branch.get("branch_index") or 1),
            "candidate_signature": str(
                branch.get("candidate_signature") or ""
            )[:500],
            "focus": str(branch.get("focus") or "")[:4_000],
            "hypothesis": str(
                (snapshot.get("executor_output") or {}).get("hypothesis")
                or (snapshot.get("planner_output") or {}).get("rationale")
                or branch.get("focus")
                or ""
            )[:4_000],
            "actions_tested": actions,
            "observations": observations,
            "new_evidence": list(snapshot.get("evidence") or [])[-50:],
            "disconfirmed_assumptions": disconfirmed,
            "remaining_gaps": [
                str(item)[:2_000]
                for item in (
                    evaluator.get("unknowns")
                    or snapshot.get("gaps")
                    or []
                )
                if str(item).strip()
            ][-30:],
            "recommended_next_action": str(
                evaluator.get("next_strategy_objective")
                or evaluator.get("reason")
                or snapshot.get("stop_reason")
                or ""
            )[:4_000],
            "outcome": outcome,
            "verification_status": str(
                verification.get("status") or "pending"
            ),
            "created_at": str(snapshot.get("created_at") or now),
            "updated_at": now,
        }
        with self._write_lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO branch_reports (
                    report_id, parent_task_id, child_task_id, branch_id,
                    candidate_signature, report_json, outcome, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(child_task_id) DO UPDATE SET
                    candidate_signature = excluded.candidate_signature,
                    report_json = excluded.report_json,
                    outcome = excluded.outcome,
                    updated_at = excluded.updated_at
                """,
                (
                    report["report_id"],
                    parent_task_id,
                    child_task_id,
                    branch_id,
                    report["candidate_signature"],
                    _dumps(report),
                    outcome,
                    report["created_at"],
                    now,
                ),
            )
        self.append_event(parent_task_id, "branch.reported", report)
        return report

    def list_branch_reports(self, parent_task_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT report_json FROM branch_reports
                 WHERE parent_task_id = ?
                 ORDER BY updated_at ASC
                """,
                (parent_task_id,),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            try:
                item = json.loads(str(row["report_json"]))
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(item, dict):
                result.append(item)
        return result

    def record_success_memory(
        self,
        snapshot: dict[str, Any],
        *,
        default_status: str = "verified",
    ) -> dict[str, Any] | None:
        # Parallel branches are temporary implementation details. Only the
        # adopted parent trajectory should become reusable success experience.
        if snapshot.get("branch_context"):
            return None

        turns = [
            item
            for item in snapshot.get("committed_turns") or []
            if isinstance(item, dict)
            and str(item.get("request") or "").strip()
            and str(item.get("response") or "").strip()
        ]
        if not turns:
            return None
        final_turn = turns[-1]
        task_id = str(snapshot.get("task_id") or "").strip()
        if not task_id:
            return None
        target_key = normalize_target_key(
            str(snapshot.get("target_key") or snapshot.get("runner_id") or "")
        )
        goal = str(snapshot.get("goal") or "").strip()
        evaluator = snapshot.get("evaluator_output") or {}
        verification = snapshot.get("success_verification") or {}
        memory_status = str(
            verification.get("status") or default_status
        )
        evidence_ids = [
            str(item)
            for item in verification.get("evidence_ids") or []
            if str(item).strip()
        ]
        verification_reason = str(
            verification.get("reason")
            or evaluator.get("reason")
            or evaluator.get("summary")
            or ""
        )[:4_000]
        strategy_summary = str(
            evaluator.get("summary")
            or evaluator.get("reason")
            or snapshot.get("long_term_summary")
            or "Goal achieved."
        )[:4_000]
        active = final_turn.get("active_techniques") or []
        technique = ", ".join(
            str(item.get("technique") or "")
            for item in active
            if isinstance(item, dict) and item.get("technique")
        )
        trajectory = [
            {
                "round": int(item.get("round") or index + 1),
                "method": item.get("method"),
                "skill_id": item.get("skill_id"),
                "active_techniques": item.get("active_techniques") or [],
                "changed_variable": item.get("changed_variable"),
                "request": str(item.get("request") or "")[:50_000],
                "response": str(item.get("response") or "")[:50_000],
            }
            for index, item in enumerate(turns[-10:])
        ]
        now = _utc_now()
        achieved_at = str(
            snapshot.get("completed_at")
            or snapshot.get("updated_at")
            or now
        )
        memory_id = f"memory-{task_id}"
        with self._write_lock, self._connect() as connection:
            tombstone = connection.execute(
                """
                SELECT 1 FROM success_memory_tombstones
                 WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
            if tombstone is not None:
                return None
            connection.execute(
                """
                INSERT INTO success_memories (
                    memory_id, task_id, target_key, runner_id, endpoint_name, goal,
                    goal_normalized, final_input, final_output, strategy_summary,
                    technique, round_count, trajectory_json, status,
                    evidence_json, evaluator_version, target_fingerprint,
                    verification_reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    target_key = excluded.target_key,
                    runner_id = excluded.runner_id,
                    endpoint_name = excluded.endpoint_name,
                    goal = excluded.goal,
                    goal_normalized = excluded.goal_normalized,
                    final_input = excluded.final_input,
                    final_output = excluded.final_output,
                    strategy_summary = excluded.strategy_summary,
                    technique = excluded.technique,
                    round_count = excluded.round_count,
                    trajectory_json = excluded.trajectory_json,
                    status = excluded.status,
                    evidence_json = excluded.evidence_json,
                    evaluator_version = excluded.evaluator_version,
                    target_fingerprint = excluded.target_fingerprint,
                    verification_reason = excluded.verification_reason,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at
                """,
                (
                    memory_id,
                    task_id,
                    target_key,
                    str(snapshot.get("runner_id") or ""),
                    str(snapshot.get("endpoint_name") or ""),
                    goal,
                    _normalize_goal(goal),
                    str(final_turn.get("request") or "")[:50_000],
                    str(final_turn.get("response") or "")[:50_000],
                    strategy_summary,
                    technique[:500],
                    int(snapshot.get("total_round") or len(turns)),
                    _dumps(trajectory),
                    memory_status,
                    _dumps(evidence_ids),
                    str(
                        (snapshot.get("prompt_versions") or {})
                        .get("evaluator", {})
                        .get("version", "")
                    ),
                    str(snapshot.get("target_key") or snapshot.get("runner_id") or ""),
                    verification_reason,
                    achieved_at,
                    now,
                ),
            )
        return self.get_success_memory(memory_id)

    def get_success_memory(self, memory_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM success_memories WHERE memory_id = ?",
                (memory_id,),
            ).fetchone()
        if row is None:
            raise KeyError(memory_id)
        return _success_memory_from_row(row)

    def list_success_memories(
        self,
        *,
        target_key: str,
        runner_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        normalized_target = normalize_target_key(target_key)
        normalized_runner = str(runner_id or "").strip()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM success_memories
                 WHERE target_key = ?
                    OR (? <> '' AND runner_id = ?)
                 ORDER BY created_at DESC
                 LIMIT ?
                """,
                (
                    normalized_target,
                    normalized_runner,
                    normalized_runner,
                    max(1, min(limit, 500)),
                ),
            ).fetchall()
        return [_success_memory_from_row(row) for row in rows]

    def find_relevant_success_memories(
        self,
        *,
        target_key: str,
        runner_id: str | None = None,
        goal: str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        candidates = self.list_success_memories(
            target_key=target_key,
            runner_id=runner_id,
            limit=100,
        )
        ranked = sorted(
            (
                (_goal_similarity(goal, str(item.get("goal") or "")), item)
                for item in candidates
                if str(item.get("status") or "") == "verified"
            ),
            key=lambda pair: -pair[0],
        )
        relevant: list[dict[str, Any]] = []
        for similarity, item in ranked:
            if similarity < 0.18:
                continue
            relevant.append(
                {
                    "successfulInput": str(item["final_input"])[:3_000],
                    "successfulOutput": str(item["final_output"])[:3_000],
                }
            )
            if len(relevant) >= max(1, min(limit, 10)):
                break
        return relevant

    def delete_success_memory(self, memory_id: str) -> None:
        with self._write_lock, self._connect() as connection:
            row = connection.execute(
                "SELECT task_id FROM success_memories WHERE memory_id = ?",
                (memory_id,),
            ).fetchone()
            if row is None:
                raise KeyError(memory_id)
            connection.execute(
                """
                INSERT INTO success_memory_tombstones (task_id, deleted_at)
                VALUES (?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    deleted_at = excluded.deleted_at
                """,
                (str(row["task_id"]), _utc_now()),
            )
            cursor = connection.execute(
                "DELETE FROM success_memories WHERE memory_id = ?",
                (memory_id,),
            )
            if cursor.rowcount != 1:
                raise KeyError(memory_id)

    def set_success_memory_status(
        self,
        memory_id: str,
        status: str,
        *,
        reason: str = "",
    ) -> dict[str, Any]:
        if status not in {"suspect", "verified", "revoked"}:
            raise ValueError("Invalid success memory status.")
        now = _utc_now()
        with self._write_lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE success_memories
                   SET status = ?, verification_reason = ?,
                       revoked_at = CASE WHEN ? = 'revoked' THEN ? ELSE NULL END,
                       updated_at = ?
                 WHERE memory_id = ?
                """,
                (status, reason[:4_000], status, now, now, memory_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(memory_id)
        return self.get_success_memory(memory_id)

    def backfill_success_memories(self) -> int:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT tasks.snapshot_json
                  FROM tasks
                  LEFT JOIN success_memories
                    ON success_memories.task_id = tasks.task_id
                  LEFT JOIN success_memory_tombstones
                    ON success_memory_tombstones.task_id = tasks.task_id
                 WHERE tasks.status = 'succeeded'
                   AND success_memories.task_id IS NULL
                   AND success_memory_tombstones.task_id IS NULL
                 ORDER BY tasks.updated_at ASC
                """
            ).fetchall()
        recorded = 0
        for row in rows:
            try:
                snapshot = json.loads(str(row["snapshot_json"]))
                if self.record_success_memory(
                    snapshot,
                    default_status="suspect",
                ):
                    recorded += 1
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        return recorded

    def stats(self) -> dict[str, Any]:
        with self._connect() as connection:
            statuses = connection.execute(
                "SELECT status, COUNT(*) AS count FROM tasks GROUP BY status"
            ).fetchall()
            skills = connection.execute(
                """
                SELECT skill_id, COUNT(*) AS uses,
                       SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) AS successes
                  FROM skill_usage GROUP BY skill_id ORDER BY uses DESC
                """
            ).fetchall()
        return {
            "tasksByStatus": {str(row["status"]): int(row["count"]) for row in statuses},
            "skillUsage": [
                {
                    "skillId": str(row["skill_id"]),
                    "uses": int(row["uses"]),
                    "successes": int(row["successes"] or 0),
                }
                for row in skills
            ],
        }

    def _set_control(
        self,
        task_id: str,
        *,
        pause: bool = False,
        stop: bool = False,
        status: str,
        reason: str | None = None,
    ) -> None:
        now = _utc_now()
        with self._write_lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                   SET pause_requested = CASE WHEN ? THEN 1 ELSE pause_requested END,
                       stop_requested = CASE WHEN ? THEN 1 ELSE stop_requested END,
                       status = ?, stop_reason = COALESCE(?, stop_reason),
                       updated_at = ?, version = version + 1
                 WHERE task_id = ?
                """,
                (pause, stop, status, reason, now, task_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(task_id)

    def _initialize(self) -> None:
        with self._write_lock, self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    runner_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_node TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    pause_requested INTEGER NOT NULL DEFAULT 0,
                    stop_requested INTEGER NOT NULL DEFAULT 0,
                    stop_reason TEXT,
                    lease_owner TEXT,
                    lease_until TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1
                );
                CREATE INDEX IF NOT EXISTS ix_tasks_session_chat
                    ON tasks(session_id, chat_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks(status);
                CREATE TABLE IF NOT EXISTS traces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    round_number INTEGER NOT NULL,
                    node TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    latency_ms REAL NOT NULL,
                    trace_json TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS ix_traces_task ON traces(task_id, id);
                CREATE TABLE IF NOT EXISTS skill_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS success_memories (
                    memory_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL UNIQUE,
                    target_key TEXT NOT NULL,
                    runner_id TEXT NOT NULL DEFAULT '',
                    endpoint_name TEXT NOT NULL DEFAULT '',
                    goal TEXT NOT NULL,
                    goal_normalized TEXT NOT NULL,
                    final_input TEXT NOT NULL,
                    final_output TEXT NOT NULL,
                    strategy_summary TEXT NOT NULL DEFAULT '',
                    technique TEXT NOT NULL DEFAULT '',
                    round_count INTEGER NOT NULL DEFAULT 0,
                    trajectory_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'suspect',
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    evaluator_version TEXT NOT NULL DEFAULT '',
                    target_fingerprint TEXT NOT NULL DEFAULT '',
                    verification_reason TEXT NOT NULL DEFAULT '',
                    revoked_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS ix_success_memories_target
                    ON success_memories(target_key, created_at DESC);
                CREATE TABLE IF NOT EXISTS success_memory_tombstones (
                    task_id TEXT PRIMARY KEY,
                    deleted_at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS branch_reports (
                    report_id TEXT PRIMARY KEY,
                    parent_task_id TEXT NOT NULL,
                    child_task_id TEXT NOT NULL UNIQUE,
                    branch_id TEXT NOT NULL,
                    candidate_signature TEXT NOT NULL DEFAULT '',
                    report_json TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(parent_task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
                    FOREIGN KEY(child_task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS ix_branch_reports_parent
                    ON branch_reports(parent_task_id, updated_at ASC);
                CREATE TABLE IF NOT EXISTS task_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS ix_task_events_task
                    ON task_events(task_id, id ASC);
                """
            )
            for name, definition in (
                ("status", "TEXT NOT NULL DEFAULT 'suspect'"),
                ("evidence_json", "TEXT NOT NULL DEFAULT '[]'"),
                ("evaluator_version", "TEXT NOT NULL DEFAULT ''"),
                ("target_fingerprint", "TEXT NOT NULL DEFAULT ''"),
                ("verification_reason", "TEXT NOT NULL DEFAULT ''"),
                ("revoked_at", "TEXT"),
            ):
                _ensure_column(
                    connection,
                    "success_memories",
                    name,
                    definition,
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        return connection


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_column(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    columns = {
        str(row["name"])
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        connection.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=_json_default)


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def _set_turn_ai_watch_status(
    turns: list[dict[str, Any]],
    *,
    round_key: str,
    status: str,
) -> list[dict[str, Any]]:
    updated: list[dict[str, Any]] = []
    for source in turns:
        turn = dict(source)
        if str(turn.get("round_key") or "") == round_key:
            turn["ai_watch_status"] = status
        updated.append(turn)
    return updated


def _ai_watch_review_is_claimable(review: dict[str, Any]) -> bool:
    status = str(review.get("status") or "")
    if status == "pending":
        return True
    if status != "analyzing":
        return False
    try:
        started = datetime.fromisoformat(str(review.get("started_at") or ""))
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return (datetime.now(timezone.utc) - started).total_seconds() >= 180


def _complete_turn_ai_watch_review(
    turns: list[dict[str, Any]],
    *,
    round_key: str,
    status: str,
    output: dict[str, Any] | None,
    error: str | None,
) -> list[dict[str, Any]]:
    updated: list[dict[str, Any]] = []
    for source in turns:
        turn = dict(source)
        if str(turn.get("round_key") or "") != round_key:
            updated.append(turn)
            continue
        turn["ai_watch_status"] = status
        turn["ai_watch_summary"] = (
            str((output or {}).get("summary") or "")
            if output
            else f"AI Watch model review failed: {error}"
        )
        records = [
            dict(item)
            for item in turn.get("observation_records") or []
            if not (
                str(item.get("type") or "") in {
                    "sensitive_information",
                    "ai_watch_review",
                }
                and str((item.get("data") or {}).get("_ai_watch_round_key") or "")
                == round_key
            )
        ]
        if output:
            for finding in output.get("findings") or []:
                if not isinstance(finding, dict):
                    continue
                records.append(
                    {
                        "type": "sensitive_information",
                        "label": str(
                            finding.get("category")
                            or finding.get("title")
                            or "Sensitive information"
                        ),
                        "request": turn.get("request"),
                        "response": turn.get("response"),
                        "data": {
                            **finding,
                            "_ai_watch_round_key": round_key,
                        },
                    }
                )
        records.append(
            {
                "type": "ai_watch_review",
                "label": "AI Watch model review",
                "request": turn.get("request"),
                "response": turn.get("response"),
                "data": {
                    "_ai_watch_round_key": round_key,
                    "status": status,
                    "summary": turn["ai_watch_summary"],
                    "error": error,
                },
            }
        )
        turn["observation_records"] = records
        updated.append(turn)
    return updated


def _merge_async_ai_watch_state(
    persisted: dict[str, Any],
    incoming: dict[str, Any],
) -> dict[str, Any]:
    """Keep background review writes when a stale Graph snapshot is saved."""

    merged = dict(incoming)
    persisted_reviews = dict(persisted.get("ai_watch_reviews") or {})
    incoming_reviews = dict(incoming.get("ai_watch_reviews") or {})
    review_rank = {
        "": 0,
        "pending": 1,
        "analyzing": 2,
        "error": 3,
        "complete": 4,
    }
    for round_key, source in persisted_reviews.items():
        persisted_review = dict(source or {})
        current = dict(incoming_reviews.get(round_key) or {})
        if review_rank.get(str(persisted_review.get("status") or ""), 0) >= (
            review_rank.get(str(current.get("status") or ""), 0)
        ):
            incoming_reviews[round_key] = persisted_review
    if incoming_reviews:
        merged["ai_watch_reviews"] = incoming_reviews

    persisted_turns = {
        str(item.get("round_key") or ""): item
        for item in persisted.get("committed_turns") or []
        if item.get("round_key")
    }
    turns: list[dict[str, Any]] = []
    for source in incoming.get("committed_turns") or []:
        turn = dict(source)
        old = persisted_turns.get(str(turn.get("round_key") or ""))
        if old:
            if old.get("ai_watch_status"):
                turn["ai_watch_status"] = old["ai_watch_status"]
            if old.get("ai_watch_summary"):
                turn["ai_watch_summary"] = old["ai_watch_summary"]
            async_records = [
                dict(item)
                for item in old.get("observation_records") or []
                if str(item.get("type") or "") in {
                    "sensitive_information",
                    "ai_watch_review",
                }
                and (item.get("data") or {}).get("_ai_watch_round_key")
            ]
            turn["observation_records"] = _merge_observation_records(
                turn.get("observation_records") or [],
                async_records,
            )
        turns.append(turn)
    if turns or "committed_turns" in incoming:
        merged["committed_turns"] = turns
    return merged


def _merge_observation_records(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in [*left, *right]:
        if not isinstance(item, dict):
            continue
        key = _dumps(
            {
                "type": item.get("type"),
                "label": item.get("label"),
                "data": item.get("data"),
            }
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(dict(item))
    return merged


def _replace_turn_goal_outcome(
    turns: list[dict[str, Any]],
    *,
    round_key: str,
    evaluator: dict[str, Any],
) -> list[dict[str, Any]]:
    updated: list[dict[str, Any]] = []
    for source in turns:
        turn = dict(source)
        if str(turn.get("round_key") or "") != round_key:
            updated.append(turn)
            continue
        records = [
            dict(item)
            for item in turn.get("observation_records") or []
            if str(item.get("type") or "") != "goal_outcome"
        ]
        records.append(
            {
                "type": "goal_outcome",
                "label": "Goal evaluator",
                "request": turn.get("request"),
                "response": turn.get("response"),
                "data": {
                    **evaluator,
                    "route": "STOP_SUCCESS",
                },
            }
        )
        turn["observation_records"] = records
        updated.append(turn)
    return updated


def _merge_evidence_records(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in [*left, *right]:
        if not isinstance(item, dict):
            continue
        key = str(item.get("evidence_id") or _dumps(item))
        if key in seen:
            continue
        seen.add(key)
        merged.append(dict(item))
    return merged[:500]


def normalize_target_key(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    try:
        parsed = urlsplit(cleaned)
        if not parsed.scheme or not parsed.hostname:
            return cleaned
        host = parsed.hostname.lower()
        port = f":{parsed.port}" if parsed.port else ""
        path = parsed.path.rstrip("/") or "/"
        return f"{parsed.scheme.lower()}://{host}{port}{path}"
    except ValueError:
        return cleaned


def _normalize_goal(value: str) -> str:
    return " ".join(value.lower().split())


def _goal_features(value: str) -> set[str]:
    normalized = _normalize_goal(value)
    tokens = {
        token
        for token in re.findall(r"[\w-]{2,}", normalized, flags=re.UNICODE)
        if token
    }
    compact = re.sub(r"\s+", "", normalized)
    if any("\u4e00" <= char <= "\u9fff" for char in compact):
        tokens.update(
            compact[index : index + 2]
            for index in range(max(0, len(compact) - 1))
        )
    return tokens


def _goal_similarity(left: str, right: str) -> float:
    left_normalized = _normalize_goal(left)
    right_normalized = _normalize_goal(right)
    if not left_normalized or not right_normalized:
        return 0.0
    if left_normalized == right_normalized:
        return 1.0
    left_features = _goal_features(left_normalized)
    right_features = _goal_features(right_normalized)
    union = left_features | right_features
    return len(left_features & right_features) / len(union) if union else 0.0


def _success_memory_from_row(row: sqlite3.Row) -> dict[str, Any]:
    try:
        trajectory = json.loads(str(row["trajectory_json"] or "[]"))
    except (json.JSONDecodeError, TypeError):
        trajectory = []
    try:
        evidence_ids = json.loads(str(row["evidence_json"] or "[]"))
    except (json.JSONDecodeError, TypeError, IndexError):
        evidence_ids = []
    return {
        "memory_id": str(row["memory_id"]),
        "task_id": str(row["task_id"]),
        "target_key": str(row["target_key"]),
        "runner_id": str(row["runner_id"]),
        "endpoint_name": str(row["endpoint_name"]),
        "goal": str(row["goal"]),
        "final_input": str(row["final_input"]),
        "final_output": str(row["final_output"]),
        "strategy_summary": str(row["strategy_summary"]),
        "technique": str(row["technique"]),
        "round_count": int(row["round_count"]),
        "trajectory": trajectory if isinstance(trajectory, list) else [],
        "status": str(row["status"] or "suspect"),
        "evidence_ids": evidence_ids if isinstance(evidence_ids, list) else [],
        "evaluator_version": str(row["evaluator_version"] or ""),
        "target_fingerprint": str(row["target_fingerprint"] or ""),
        "verification_reason": str(row["verification_reason"] or ""),
        "revoked_at": row["revoked_at"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }
