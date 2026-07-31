from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Final
from urllib.parse import urlsplit

from app.core.paths import DATA_ROOT as APP_DATA_ROOT

DATA_ROOT: Final = APP_DATA_ROOT / "task_agent_v2"
ACTIVE_STATUSES: Final = ("queued", "running", "pausing", "paused", "stopping")
RECOVERABLE_STATUSES: Final = ("queued", "running", "pausing", "stopping")
CURRENT_SNAPSHOT_SCHEMA_VERSION: Final = 2
CURRENT_TURN_SCHEMA_VERSION: Final = 1
CURRENT_AI_WATCH_SCHEMA_VERSION: Final = 1
CURRENT_BRANCH_REPORT_SCHEMA_VERSION: Final = 2
CURRENT_DELIVERY_SCHEMA_VERSION: Final = 1


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
        snapshot = migrate_task_snapshot(snapshot)
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
        stop_requested: bool = False,
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
                persisted_snapshot = migrate_task_snapshot(
                    json.loads(str(current["snapshot_json"]))
                )
            except (json.JSONDecodeError, TypeError):
                persisted_snapshot = {}
            snapshot = migrate_task_snapshot(snapshot)
            snapshot = _merge_concurrent_snapshot_state(
                persisted_snapshot,
                snapshot,
            )
            cursor = connection.execute(
                """
                UPDATE tasks
                   SET snapshot_json = ?, status = ?, current_node = ?,
                       stop_reason = ?,
                       stop_requested = CASE
                           WHEN ? THEN 1 ELSE stop_requested
                       END,
                       updated_at = ?, version = version + 1
                 WHERE task_id = ?
                """,
                (
                    _dumps(snapshot),
                    resolved_status,
                    resolved_node,
                    stop_reason if stop_reason is not None else snapshot.get("stop_reason"),
                    stop_requested,
                    now,
                    task_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(task_id)

    def get_snapshot(self, task_id: str) -> dict[str, Any]:
        with self._write_lock, self._connect() as connection:
            row = connection.execute(
                "SELECT snapshot_json, status, current_node, stop_reason FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            source = json.loads(row["snapshot_json"])
            snapshot = migrate_task_snapshot(source)
            snapshot["status"] = row["status"]
            snapshot["current_node"] = row["current_node"]
            snapshot["stop_reason"] = row["stop_reason"] or snapshot.get("stop_reason")
            if snapshot != source:
                connection.execute(
                    """
                    UPDATE tasks SET snapshot_json = ?, version = version + 1
                     WHERE task_id = ?
                    """,
                    (_dumps(snapshot), task_id),
                )
        return snapshot

    def prepare_target_delivery(
        self,
        task_id: str,
        delivery: dict[str, Any],
    ) -> dict[str, Any]:
        """Durably create an outbound record before any network side effect."""

        now = _utc_now()
        round_key = str(delivery["round_key"])
        with self._write_lock, self._connect() as connection:
            row = connection.execute(
                "SELECT snapshot_json FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            snapshot = migrate_task_snapshot(json.loads(row["snapshot_json"]))
            deliveries = dict(snapshot.get("target_deliveries") or {})
            existing = dict(deliveries.get(round_key) or {})
            if existing:
                return existing
            record = {
                "schema_version": CURRENT_DELIVERY_SCHEMA_VERSION,
                **delivery,
                "status": "PREPARED",
                "prepared_at": delivery.get("prepared_at") or now,
                "sending_at": None,
                "delivered_at": None,
                "committed_at": None,
                "updated_at": now,
                "transport_receipt": None,
                "response": None,
                "raw_response": None,
                "error": None,
            }
            deliveries[round_key] = record
            snapshot["target_deliveries"] = deliveries
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
                VALUES (?, 'target.delivery_prepared', ?, ?)
                """,
                (
                    task_id,
                    _dumps(
                        {
                            "delivery_id": record["delivery_id"],
                            "round_key": round_key,
                        }
                    ),
                    now,
                ),
            )
            return record

    def update_target_delivery(
        self,
        task_id: str,
        round_key: str,
        *,
        status: str,
        **updates: Any,
    ) -> dict[str, Any]:
        now = _utc_now()
        with self._write_lock, self._connect() as connection:
            row = connection.execute(
                "SELECT snapshot_json FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            snapshot = migrate_task_snapshot(json.loads(row["snapshot_json"]))
            deliveries = dict(snapshot.get("target_deliveries") or {})
            if round_key not in deliveries:
                raise TaskStoreError(
                    f"Target delivery {round_key} was not prepared."
                )
            record = {
                **dict(deliveries[round_key]),
                **updates,
                "status": status,
                "updated_at": now,
            }
            if status == "SENDING":
                record["sending_at"] = record.get("sending_at") or now
            elif status == "DELIVERED":
                record["delivered_at"] = record.get("delivered_at") or now
            elif status == "COMMITTED":
                record["committed_at"] = record.get("committed_at") or now
            deliveries[round_key] = record
            snapshot["target_deliveries"] = deliveries
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
                VALUES (?, 'target.delivery_status', ?, ?)
                """,
                (
                    task_id,
                    _dumps(
                        {
                            "delivery_id": record["delivery_id"],
                            "round_key": round_key,
                            "status": status,
                            "error": record.get("error"),
                        }
                    ),
                    now,
                ),
            )
            return record

    def commit_target_turn(
        self,
        task_id: str,
        *,
        round_key: str,
        turn: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Atomically commit the receipt, conversation turn, and history."""

        now = _utc_now()
        with self._write_lock, self._connect() as connection:
            row = connection.execute(
                "SELECT snapshot_json FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            snapshot = migrate_task_snapshot(json.loads(row["snapshot_json"]))
            deliveries = dict(snapshot.get("target_deliveries") or {})
            delivery = dict(deliveries.get(round_key) or {})
            if str(delivery.get("status") or "") not in {
                "DELIVERED",
                "COMMITTED",
            }:
                raise TaskStoreError(
                    f"Target delivery {round_key} is not known to be delivered."
                )
            turns = [
                dict(item)
                for item in snapshot.get("committed_turns") or []
                if str(item.get("round_key") or "") != round_key
            ]
            turn = {
                "schema_version": CURRENT_TURN_SCHEMA_VERSION,
                **turn,
            }
            turns.append(turn)
            delivery.update(
                {
                    "status": "COMMITTED",
                    "committed_at": delivery.get("committed_at") or now,
                    "updated_at": now,
                    "response": turn.get("response"),
                    "raw_response": turn.get("raw_response"),
                }
            )
            deliveries[round_key] = delivery
            snapshot.update(
                {
                    "committed_turns": turns,
                    "target_deliveries": deliveries,
                    "history": history,
                    "latest_request": turn.get("request"),
                    "latest_response": turn.get("response"),
                    "latest_raw_response": turn.get("raw_response"),
                    "active_issue": None,
                    "updated_at": now,
                }
            )
            connection.execute(
                """
                UPDATE tasks SET snapshot_json = ?, current_node = 'analysis_parallel',
                                 updated_at = ?, version = version + 1
                 WHERE task_id = ?
                """,
                (_dumps(snapshot), now, task_id),
            )
            connection.execute(
                """
                INSERT INTO task_events (task_id, event_type, payload_json, created_at)
                VALUES (?, 'target.turn_committed', ?, ?)
                """,
                (
                    task_id,
                    _dumps(
                        {
                            "delivery_id": delivery.get("delivery_id"),
                            "round_key": round_key,
                        }
                    ),
                    now,
                ),
            )
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

    def list_terminal_branch_cleanup_candidates(self) -> list[dict[str, Any]]:
        """Return every durable child-runner tombstone still needing cleanup."""

        terminal = ("succeeded", "stopped_safety", "stopped_manual", "failed")
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT task_id FROM tasks
                WHERE status IN ({",".join("?" for _ in terminal)})
                ORDER BY updated_at ASC
                """,
                terminal,
            ).fetchall()
        candidates: list[dict[str, Any]] = []
        for row in rows:
            snapshot = self.get_snapshot(str(row["task_id"]))
            if not snapshot.get("branch_context"):
                continue
            if snapshot.get("branch_runner_deleted"):
                continue
            candidates.append(snapshot)
        return candidates

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
                "schema_version": CURRENT_AI_WATCH_SCHEMA_VERSION,
                "round_key": round_key,
                "round": int(round_number),
                "status": "pending",
                "attempts": 0,
                "max_attempts": 3,
                "next_attempt_at": now,
                "retryable": True,
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
                            "attempts": int(review.get("attempts") or 0) + 1,
                            "max_attempts": max(
                                1,
                                min(
                                    10,
                                    int(review.get("max_attempts") or 3),
                                ),
                            ),
                            "started_at": now,
                            "next_attempt_at": None,
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

    def retry_ai_watch_review(
        self,
        task_id: str,
        *,
        round_key: str,
        delay_seconds: float,
        failure_kind: str,
        internal_error: str,
    ) -> dict[str, Any]:
        now_value = datetime.now(timezone.utc)
        now = now_value.isoformat()
        bounded_delay = max(0.0, min(3_600.0, float(delay_seconds)))
        next_attempt_at = (
            now_value + timedelta(seconds=bounded_delay)
        ).isoformat()
        with self._write_lock, self._connect() as connection:
            row = connection.execute(
                "SELECT snapshot_json FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            snapshot = json.loads(str(row["snapshot_json"]))
            reviews = dict(snapshot.get("ai_watch_reviews") or {})
            review = dict(reviews.get(round_key) or {})
            if not review:
                raise KeyError(f"{task_id}:{round_key}")
            if str(review.get("status") or "") == "cancelled":
                return migrate_task_snapshot(snapshot)
            attempt = int(review.get("attempts") or 0)
            maximum = max(
                1,
                min(10, int(review.get("max_attempts") or 3)),
            )
            review.update(
                {
                    "status": "pending",
                    "next_attempt_at": next_attempt_at,
                    "retryable": True,
                    "started_at": None,
                    "completed_at": None,
                    "summary": (
                        "AI Watch is temporarily unavailable and will retry "
                        f"automatically ({attempt}/{maximum})."
                    ),
                    "error": None,
                    "last_failure_kind": failure_kind,
                }
            )
            reviews[round_key] = review
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
                INSERT INTO task_events
                    (task_id, event_type, payload_json, created_at)
                VALUES (?, 'ai_watch.retry_scheduled', ?, ?)
                """,
                (
                    task_id,
                    _dumps(
                        {
                            "round_key": round_key,
                            "attempt": attempt,
                            "max_attempts": maximum,
                            "delay_seconds": bounded_delay,
                            "next_attempt_at": next_attempt_at,
                            "failure_kind": failure_kind,
                            "internal_error": internal_error[:500],
                        }
                    ),
                    now,
                ),
            )
        return self.get_snapshot(task_id)

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
            if str(review.get("status") or "") == "cancelled":
                return migrate_task_snapshot(snapshot)
            review.update(
                {
                    "status": status,
                    "retryable": False,
                    "next_attempt_at": None,
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

    def cancel_pending_ai_watch_reviews(
        self,
        task_id: str,
        *,
        reason: str,
    ) -> dict[str, Any]:
        """Idempotently remove terminal tasks from the reviewing UI state."""

        now = _utc_now()
        cancelled: list[str] = []
        with self._write_lock, self._connect() as connection:
            row = connection.execute(
                "SELECT snapshot_json FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                raise KeyError(task_id)
            snapshot = json.loads(str(row["snapshot_json"]))
            reviews = dict(snapshot.get("ai_watch_reviews") or {})
            turns = list(snapshot.get("committed_turns") or [])
            for round_key, source in reviews.items():
                review = dict(source or {})
                if str(review.get("status") or "") not in {
                    "pending",
                    "analyzing",
                }:
                    continue
                review.update(
                    {
                        "status": "cancelled",
                        "retryable": False,
                        "next_attempt_at": None,
                        "completed_at": now,
                        "summary": reason,
                        "error": None,
                    }
                )
                reviews[round_key] = review
                turns = _set_turn_ai_watch_status(
                    turns,
                    round_key=str(round_key),
                    status="cancelled",
                )
                cancelled.append(str(round_key))
            if not cancelled:
                return migrate_task_snapshot(snapshot)
            snapshot["ai_watch_reviews"] = reviews
            snapshot["committed_turns"] = turns
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
                INSERT INTO task_events
                    (task_id, event_type, payload_json, created_at)
                VALUES (?, 'ai_watch.cancelled_terminal', ?, ?)
                """,
                (
                    task_id,
                    _dumps(
                        {
                            "round_keys": cancelled,
                            "reason": reason,
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
        scorer_ensemble: dict[str, Any],
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
                    "scorer_ensemble": scorer_ensemble,
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

    def queue_goal_update(self, task_id: str, goal: str) -> dict[str, Any]:
        snapshot = self.get_snapshot(task_id)
        if str(snapshot.get("status") or "") not in {
            "queued",
            "running",
            "pausing",
            "paused",
        }:
            raise ValueError("Only an active task can accept a goal update.")
        normalized_goal = goal.strip()
        if not normalized_goal:
            raise ValueError("The updated goal cannot be empty.")
        return self.append_event(
            task_id,
            "goal_update.queued",
            {"goal": normalized_goal},
        )

    def peek_goal_update(self, task_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM task_events
                 WHERE task_id = ? AND event_type = 'goal_update.queued'
                 ORDER BY id DESC LIMIT 1
                """,
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        try:
            payload = json.loads(str(row["payload_json"]))
        except (json.JSONDecodeError, TypeError):
            return None
        goal = str(payload.get("goal") or "").strip()
        return goal or None

    def consume_goal_update(self, task_id: str) -> str | None:
        with self._write_lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, payload_json FROM task_events
                 WHERE task_id = ? AND event_type = 'goal_update.queued'
                 ORDER BY id ASC
                """,
                (task_id,),
            ).fetchall()
            latest_goal: str | None = None
            for row in rows:
                try:
                    payload = json.loads(str(row["payload_json"]))
                except (json.JSONDecodeError, TypeError):
                    payload = {}
                goal = str(payload.get("goal") or "").strip()
                if goal:
                    latest_goal = goal
                connection.execute(
                    """
                    UPDATE task_events SET event_type = 'goal_update.applied'
                     WHERE id = ?
                    """,
                    (int(row["id"]),),
                )
        return latest_goal

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

    def family_root_task_id(self, task_id: str) -> str:
        current = task_id
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            try:
                snapshot = self.get_snapshot(current)
            except KeyError:
                return current
            parent = str(
                (snapshot.get("branch_context") or {}).get("parent_task_id")
                or ""
            ).strip()
            if not parent:
                return current
            current = parent
        return task_id

    def list_family_snapshots(self, task_id: str) -> list[dict[str, Any]]:
        root_task_id = self.family_root_task_id(task_id)
        snapshots = self.list_snapshots(limit=10_000)
        by_parent: dict[str, list[dict[str, Any]]] = {}
        root: dict[str, Any] | None = None
        for snapshot in snapshots:
            snapshot_id = str(snapshot.get("task_id") or "")
            if snapshot_id == root_task_id:
                root = snapshot
            parent_id = str(
                (snapshot.get("branch_context") or {}).get("parent_task_id")
                or ""
            )
            if parent_id:
                by_parent.setdefault(parent_id, []).append(snapshot)
        if root is None:
            try:
                root = self.get_snapshot(root_task_id)
            except KeyError:
                return []
        family = [root]
        cursor = [root_task_id]
        seen = {root_task_id}
        while cursor:
            parent_id = cursor.pop(0)
            for child in by_parent.get(parent_id, []):
                child_id = str(child.get("task_id") or "")
                if not child_id or child_id in seen:
                    continue
                seen.add(child_id)
                family.append(child)
                cursor.append(child_id)
        return family

    def list_family_turns(self, task_id: str) -> list[dict[str, Any]]:
        turns: list[dict[str, Any]] = []
        for snapshot in self.list_family_snapshots(task_id):
            origin_task_id = str(snapshot.get("task_id") or "")
            for source in snapshot.get("committed_turns") or []:
                if not isinstance(source, dict):
                    continue
                turns.append(
                    {
                        **source,
                        "origin_task_id": origin_task_id,
                    }
                )
        return sorted(
            turns,
            key=lambda item: (
                str(item.get("created_at") or item.get("committed_at") or ""),
                str(item.get("origin_task_id") or ""),
                int(item.get("round") or 0),
            ),
        )

    def reserve_family_outbound_message(
        self,
        task_id: str,
        *,
        message: str,
        near_duplicate_threshold: float,
        controlled_replay_limit: int = 0,
        reservation_key: str = "",
    ) -> dict[str, Any]:
        """Atomically reserve a family message before any network delivery."""

        root_task_id = self.family_root_task_id(task_id)
        normalized = re.sub(r"\s+", " ", message.casefold()).strip()
        message_sha256 = hashlib.sha256(message.encode("utf-8")).hexdigest()
        reservation_key = (
            reservation_key.strip()
            or hashlib.sha256(
                f"{task_id}:{message_sha256}".encode("utf-8")
            ).hexdigest()
        )[:200]
        if not normalized:
            return {"reserved": True, "message_sha256": message_sha256}
        threshold = max(
            0.7,
            min(1.0, float(near_duplicate_threshold)),
        )
        with self._write_lock, self._connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM tasks WHERE task_id = ?",
                (root_task_id,),
            ).fetchone()
            if exists is None:
                return {
                    "reserved": True,
                    "message_sha256": message_sha256,
                    "root_task_id": root_task_id,
                }
            existing_reservation = connection.execute(
                """
                SELECT reservation_id FROM family_outbound_messages
                 WHERE root_task_id = ? AND reservation_key = ?
                 ORDER BY reserved_at ASC LIMIT 1
                """,
                (root_task_id, reservation_key),
            ).fetchone()
            if existing_reservation is not None:
                return {
                    "reserved": True,
                    "reservation_id": str(
                        existing_reservation["reservation_id"]
                    ),
                    "message_sha256": message_sha256,
                    "root_task_id": root_task_id,
                    "idempotent_replay": True,
                }
            rows = connection.execute(
                """
                SELECT source_task_id, normalized_message, message_sha256,
                       reserved_at
                  FROM family_outbound_messages
                 WHERE root_task_id = ?
                 ORDER BY reserved_at ASC
                """,
                (root_task_id,),
            ).fetchall()
            matches: list[tuple[sqlite3.Row, float]] = []
            for row in rows:
                prior = str(row["normalized_message"] or "")
                similarity = (
                    1.0
                    if prior == normalized
                    else (
                        SequenceMatcher(None, prior, normalized).ratio()
                        if min(len(prior), len(normalized)) >= 24
                        else 0.0
                    )
                )
                if similarity >= threshold:
                    matches.append((row, similarity))
            exact_matches = [
                value for value in matches if value[1] == 1.0
            ]
            if matches and not (
                len(matches) == len(exact_matches)
                and len(exact_matches) <= controlled_replay_limit
            ):
                highest = max(value[1] for value in matches)
                return {
                    "reserved": False,
                    "message_sha256": message_sha256,
                    "root_task_id": root_task_id,
                    "prior_match_count": len(matches),
                    "controlled_replay_limit": controlled_replay_limit,
                    "match_kind": (
                        "exact" if highest == 1.0 else "near_duplicate"
                    ),
                    "highest_similarity": round(highest, 4),
                    "matching_task_ids": list(
                        dict.fromkeys(
                            str(row["source_task_id"])
                            for row, _ in matches
                        )
                    ),
                }
            reservation_id = hashlib.sha256(
                f"{root_task_id}:{task_id}:{message_sha256}:{_utc_now()}".encode(
                    "utf-8"
                )
            ).hexdigest()
            now = _utc_now()
            connection.execute(
                """
                INSERT INTO family_outbound_messages (
                    reservation_id, root_task_id, source_task_id,
                    reservation_key, normalized_message, message_sha256,
                    status, reserved_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'RESERVED', ?, ?)
                """,
                (
                    reservation_id,
                    root_task_id,
                    task_id,
                    reservation_key,
                    normalized,
                    message_sha256,
                    now,
                    now,
                ),
            )
        return {
            "reserved": True,
            "reservation_id": reservation_id,
            "message_sha256": message_sha256,
            "root_task_id": root_task_id,
        }

    def family_metrics(self, task_id: str) -> dict[str, Any]:
        snapshots = self.list_family_snapshots(task_id)
        root_task_id = self.family_root_task_id(task_id)
        branch_reports = self.list_branch_reports(root_task_id)
        starts = [
            str(item.get("started_at") or item.get("created_at") or "")
            for item in snapshots
            if item.get("started_at") or item.get("created_at")
        ]
        started_at = min(starts) if starts else _utc_now()
        try:
            started = datetime.fromisoformat(started_at)
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            elapsed = max(
                0.0,
                (datetime.now(timezone.utc) - started).total_seconds(),
            )
        except ValueError:
            elapsed = 0.0
        model_call_counts = {
            role: sum(
                int(
                    (item.get("model_call_counts") or {}).get(role)
                    or 0
                )
                for item in snapshots
            )
            for role in ("planner", "executor", "evaluator")
        }
        baseline_probe_turns = sum(
            1
            for snapshot in snapshots
            for turn in snapshot.get("committed_turns") or []
            if isinstance(turn, dict)
            and str(turn.get("generation_mode") or "")
            == "baseline_scanner"
        )
        zero_gain_branches = sum(
            float(item.get("evidence_gain") or 0) <= 0
            for item in branch_reports
        )
        productive_branches = sum(
            float(item.get("evidence_gain") or 0) > 0
            for item in branch_reports
        )
        branch_count = len(branch_reports)
        branch_signatures = [
            str(item.get("candidate_signature") or "").strip()
            for item in branch_reports
            if str(item.get("candidate_signature") or "").strip()
        ]
        duplicate_branches = len(branch_signatures) - len(
            set(branch_signatures)
        )
        branch_efficiencies = [
            max(0.0, float(item.get("marginal_efficiency") or 0))
            for item in branch_reports
        ]
        with self._connect() as connection:
            harness = connection.execute(
                """
                SELECT evidence_stall_count
                  FROM family_harness_state
                 WHERE root_task_id = ?
                """,
                (root_task_id,),
            ).fetchone()
        return {
            "root_task_id": root_task_id,
            "task_count": len(snapshots),
            "active_task_count": sum(
                1
                for item in snapshots
                if str(item.get("status") or "") in ACTIVE_STATUSES
            ),
            "total_rounds": sum(
                int(item.get("total_round") or 0) for item in snapshots
            ),
            "input_tokens": sum(
                int(item.get("input_tokens") or 0) for item in snapshots
            ),
            "output_tokens": sum(
                int(item.get("output_tokens") or 0) for item in snapshots
            ),
            "estimated_cost": sum(
                float(item.get("estimated_cost") or 0) for item in snapshots
            ),
            "model_call_counts": model_call_counts,
            "model_call_total": sum(model_call_counts.values()),
            "baseline_probe_turns": baseline_probe_turns,
            "branch_metrics": {
                "reported_branches": branch_count,
                "productive_branches": productive_branches,
                "zero_gain_branches": zero_gain_branches,
                "zero_gain_rate": round(
                    zero_gain_branches / branch_count
                    if branch_count
                    else 0,
                    6,
                ),
                "duplicate_branches": duplicate_branches,
                "duplicate_rate": round(
                    duplicate_branches / len(branch_signatures)
                    if branch_signatures
                    else 0,
                    6,
                ),
                "mean_marginal_efficiency": round(
                    sum(branch_efficiencies) / branch_count
                    if branch_count
                    else 0,
                    6,
                ),
                "total_evidence_gain": round(
                    sum(
                        max(0.0, float(item.get("evidence_gain") or 0))
                        for item in branch_reports
                    ),
                    6,
                ),
                "total_cost_units": round(
                    sum(
                        max(0.0, float(item.get("cost_units") or 0))
                        for item in branch_reports
                    ),
                    6,
                ),
            },
            "elapsed_seconds": round(elapsed, 3),
            "evidence_stall_count": (
                int(harness["evidence_stall_count"]) if harness else 0
            ),
        }

    def list_evidence_ledger(
        self,
        task_id: str,
        *,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        root_task_id = self.family_root_task_id(task_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT entry_json FROM evidence_ledger
                 WHERE root_task_id = ?
                 ORDER BY updated_at ASC
                 LIMIT ?
                """,
                (root_task_id, max(1, min(limit, 5_000))),
            ).fetchall()
        return [json.loads(str(row["entry_json"])) for row in rows]

    def record_evidence_ledger(
        self,
        task_id: str,
        *,
        evidence: list[dict[str, Any]],
        counter_evidence: list[Any] | None = None,
        round_number: int = 0,
        evaluation_kind: str = "router",
    ) -> dict[str, Any]:
        root_task_id = self.family_root_task_id(task_id)
        evaluation_kind = (
            re.sub(r"[^a-z0-9_.-]+", "-", evaluation_kind.casefold()).strip("-")
            or "router"
        )[:80]
        with self._connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM tasks WHERE task_id = ?",
                (root_task_id,),
            ).fetchone()
        if exists is None:
            eligible = sum(
                1
                for item in evidence
                if bool(
                    (item.get("provenance") or {}).get(
                        "eligible_for_progress"
                    )
                )
            )
            return {
                "root_task_id": root_task_id,
                "new_eligible_claims": eligible,
                "family_evidence_stall_count": 0 if eligible else 1,
                "updated_count": 0,
                "entries": [],
            }
        now = _utc_now()
        new_eligible_claims = 0
        family_evidence_stall_count = 0
        updated_entries: list[dict[str, Any]] = []
        with self._write_lock, self._connect() as connection:
            prior_evaluation = connection.execute(
                """
                SELECT 1 FROM family_evidence_evaluations
                 WHERE root_task_id = ? AND source_task_id = ?
                   AND round_number = ? AND evaluation_kind = ?
                """,
                (
                    root_task_id,
                    task_id,
                    max(0, int(round_number or 0)),
                    evaluation_kind,
                ),
            ).fetchone()
            for item in evidence:
                if not isinstance(item, dict):
                    continue
                claim = str(
                    item.get("response_excerpt")
                    or item.get("observation")
                    or ""
                ).strip()
                if not claim:
                    continue
                normalized = re.sub(r"\s+", " ", claim.casefold()).strip()
                claim_hash = hashlib.sha256(
                    normalized.encode("utf-8")
                ).hexdigest()
                provenance = dict(item.get("provenance") or {})
                if bool(provenance.get("eligible_for_success")):
                    status = "confirmed"
                elif bool(provenance.get("eligible_for_progress")):
                    status = "suspect"
                else:
                    status = "rejected"
                row = connection.execute(
                    """
                    SELECT entry_json, status FROM evidence_ledger
                     WHERE root_task_id = ? AND claim_hash = ?
                    """,
                    (root_task_id, claim_hash),
                ).fetchone()
                source = {
                    "source_task_id": task_id,
                    "round": max(0, int(round_number or 0)),
                    "evidence_id": str(item.get("evidence_id") or ""),
                    "request_excerpt": item.get("request_excerpt"),
                    "response_excerpt": item.get("response_excerpt"),
                    "recorded_at": now,
                }
                if row is None:
                    entry = {
                        "schema_version": 1,
                        "entry_id": f"evidence-{claim_hash}",
                        "root_task_id": root_task_id,
                        "claim_hash": claim_hash,
                        "claim": claim[:6_000],
                        "supports": str(item.get("supports") or "")[:2_000],
                        "status": status,
                        "strength": str(item.get("strength") or "weak"),
                        "provenance": provenance,
                        "sources": [source],
                        "contradictions": [
                            str(value)[:2_000]
                            for value in counter_evidence or []
                            if str(value).strip()
                        ][:50],
                        "created_at": now,
                        "updated_at": now,
                    }
                    if status in {"confirmed", "suspect"}:
                        new_eligible_claims += 1
                    connection.execute(
                        """
                        INSERT INTO evidence_ledger (
                            root_task_id, claim_hash, status, entry_json,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            root_task_id,
                            claim_hash,
                            status,
                            _dumps(entry),
                            now,
                            now,
                        ),
                    )
                else:
                    entry = json.loads(str(row["entry_json"]))
                    prior_status = str(row["status"])
                    ranks = {"rejected": 0, "suspect": 1, "confirmed": 2}
                    resolved_status = (
                        status
                        if ranks.get(status, 0) > ranks.get(prior_status, 0)
                        else prior_status
                    )
                    sources = list(entry.get("sources") or [])
                    source_key = (
                        source["source_task_id"],
                        source["round"],
                        source["evidence_id"],
                    )
                    if not any(
                        (
                            value.get("source_task_id"),
                            int(value.get("round") or 0),
                            value.get("evidence_id"),
                        )
                        == source_key
                        for value in sources
                        if isinstance(value, dict)
                    ):
                        sources.append(source)
                    if (
                        ranks.get(resolved_status, 0)
                        > ranks.get(prior_status, 0)
                        and resolved_status in {"suspect", "confirmed"}
                    ):
                        new_eligible_claims += 1
                    entry = {
                        **entry,
                        "status": resolved_status,
                        "strength": (
                            item.get("strength")
                            if resolved_status == status
                            else entry.get("strength")
                        ),
                        "provenance": (
                            provenance
                            if resolved_status == status
                            else entry.get("provenance")
                        ),
                        "sources": sources[-100:],
                        "updated_at": now,
                    }
                    connection.execute(
                        """
                        UPDATE evidence_ledger
                           SET status = ?, entry_json = ?, updated_at = ?
                         WHERE root_task_id = ? AND claim_hash = ?
                        """,
                        (
                            resolved_status,
                            _dumps(entry),
                            now,
                            root_task_id,
                            claim_hash,
                        ),
                    )
                updated_entries.append(entry)
            harness = connection.execute(
                """
                SELECT evidence_stall_count
                  FROM family_harness_state
                 WHERE root_task_id = ?
                """,
                (root_task_id,),
            ).fetchone()
            prior_stall = (
                int(harness["evidence_stall_count"]) if harness else 0
            )
            family_evidence_stall_count = (
                0
                if new_eligible_claims > 0
                else (
                    prior_stall
                    if prior_evaluation is not None
                    else prior_stall + 1
                )
            )
            connection.execute(
                """
                INSERT INTO family_harness_state (
                    root_task_id, evidence_stall_count, updated_at
                ) VALUES (?, ?, ?)
                ON CONFLICT(root_task_id) DO UPDATE SET
                    evidence_stall_count = excluded.evidence_stall_count,
                    updated_at = excluded.updated_at
                """,
                (root_task_id, family_evidence_stall_count, now),
            )
            connection.execute(
                """
                INSERT INTO family_evidence_evaluations (
                    root_task_id, source_task_id, round_number,
                    evaluation_kind, evaluated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(
                    root_task_id, source_task_id, round_number,
                    evaluation_kind
                ) DO UPDATE SET evaluated_at = excluded.evaluated_at
                """,
                (
                    root_task_id,
                    task_id,
                    max(0, int(round_number or 0)),
                    evaluation_kind,
                    now,
                ),
            )
            if prior_evaluation is None or updated_entries:
                connection.execute(
                    """
                    INSERT INTO task_events (
                        task_id, event_type, payload_json, created_at
                    ) VALUES (?, 'evidence.ledger_updated', ?, ?)
                    """,
                    (
                        root_task_id,
                        _dumps(
                            {
                                "source_task_id": task_id,
                                "round": round_number,
                                "evaluation_kind": evaluation_kind,
                                "updated_count": len(updated_entries),
                                "new_eligible_claims": new_eligible_claims,
                                "family_evidence_stall_count": (
                                    family_evidence_stall_count
                                ),
                                "idempotent_replay": (
                                    prior_evaluation is not None
                                ),
                            }
                        ),
                        now,
                    ),
                )
        return {
            "root_task_id": root_task_id,
            "new_eligible_claims": new_eligible_claims,
            "family_evidence_stall_count": family_evidence_stall_count,
            "updated_count": len(updated_entries),
            "entries": updated_entries,
            "idempotent_replay": prior_evaluation is not None,
        }

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
        eligible_evidence = [
            item
            for item in snapshot.get("evidence") or []
            if isinstance(item, dict)
            and bool(
                (item.get("provenance") or {}).get(
                    "eligible_for_progress"
                )
            )
        ]
        coverage = verification.get("coverage") or {}
        coverage_ratio = coverage.get("ratio")
        if not isinstance(coverage_ratio, (int, float)):
            requirement_total = len(
                (
                    (
                        snapshot.get("attack_spec")
                        or {}
                    ).get("objective")
                    or {}
                ).get("proof_spec", {}).get("requirements", [])
            )
            coverage_ratio = min(
                1.0,
                len(eligible_evidence) / max(1, requirement_total),
            )
        rounds = int(snapshot.get("total_round") or 0)
        input_tokens = int(snapshot.get("input_tokens") or 0)
        output_tokens = int(snapshot.get("output_tokens") or 0)
        estimated_cost = float(snapshot.get("estimated_cost") or 0)
        try:
            started_at = datetime.fromisoformat(
                str(snapshot.get("started_at") or snapshot.get("created_at"))
            )
            updated_at = datetime.fromisoformat(
                str(snapshot.get("updated_at") or now)
            )
            duration_seconds = max(
                0.0,
                (updated_at - started_at).total_seconds(),
            )
        except (TypeError, ValueError):
            duration_seconds = 0.0
        cost_units = max(
            0.01,
            rounds
            + input_tokens / 100_000
            + output_tokens / 20_000
            + estimated_cost * 100
            + duration_seconds / 300,
        )
        parent_control = (
            "stopped"
            if str(snapshot.get("stop_reason") or "").lower().startswith(
                "parent "
            )
            else (
                "followup"
                if any(
                    str(item).startswith("Parent follow-up:")
                    for item in snapshot.get("steering_messages") or []
                )
                else "none"
            )
        )
        report = {
            "schema_version": CURRENT_BRANCH_REPORT_SCHEMA_VERSION,
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
            "rounds": rounds,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost": estimated_cost,
            "model_call_counts": {
                str(role): max(0, int(count or 0))
                for role, count in (
                    snapshot.get("model_call_counts") or {}
                ).items()
            },
            "duration_seconds": duration_seconds,
            "eligible_evidence_count": len(eligible_evidence),
            "evidence_gain": round(
                max(0.0, min(1.0, float(coverage_ratio))),
                6,
            ),
            "cost_units": round(cost_units, 6),
            "marginal_efficiency": round(
                max(0.0, float(coverage_ratio)) / cost_units,
                6,
            ),
            "parent_control": parent_control,
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

    def save_run_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """Persist a draft manifest or freeze the first finalized generation record."""

        task_id = str(manifest.get("task_id") or "")
        if not task_id:
            raise ValueError("Run Manifest requires a task_id.")
        now = _utc_now()
        with self._write_lock, self._connect() as connection:
            existing = connection.execute(
                """
                SELECT manifest_json, finalized FROM run_manifests
                 WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
            if existing is not None and bool(existing["finalized"]):
                stored = json.loads(str(existing["manifest_json"]))
                if str(stored.get("generation_sha256") or "") != str(
                    manifest.get("generation_sha256") or ""
                ):
                    raise TaskStoreError(
                        "The finalized Run Manifest is immutable and does not "
                        "match the supplied generation record."
                    )
                return stored
            connection.execute(
                """
                INSERT INTO run_manifests (
                    manifest_id, task_id, generation_sha256, manifest_sha256,
                    finalized, manifest_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    manifest_id = excluded.manifest_id,
                    generation_sha256 = excluded.generation_sha256,
                    manifest_sha256 = excluded.manifest_sha256,
                    finalized = excluded.finalized,
                    manifest_json = excluded.manifest_json,
                    updated_at = excluded.updated_at
                """,
                (
                    str(manifest["manifest_id"]),
                    task_id,
                    str(manifest.get("generation_sha256") or ""),
                    str(manifest.get("manifest_sha256") or ""),
                    1 if manifest.get("finalized") else 0,
                    _dumps(manifest),
                    now,
                    now,
                ),
            )
        return dict(manifest)

    def get_run_manifest(
        self,
        *,
        task_id: str | None = None,
        manifest_id: str | None = None,
    ) -> dict[str, Any]:
        if not task_id and not manifest_id:
            raise ValueError("task_id or manifest_id is required.")
        column = "task_id" if task_id else "manifest_id"
        value = task_id or manifest_id
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT manifest_json FROM run_manifests WHERE {column} = ?",
                (value,),
            ).fetchone()
        if row is None:
            raise KeyError(value)
        return json.loads(str(row["manifest_json"]))

    def save_regrade(self, result: dict[str, Any]) -> dict[str, Any]:
        now = _utc_now()
        regrade_id = str(result.get("regrade_id") or f"regrade-{uuid.uuid4()}")
        stored = {**result, "regrade_id": regrade_id}
        with self._write_lock, self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO task_regrades (
                    regrade_id, manifest_id, manifest_sha256, result_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    regrade_id,
                    str(stored.get("manifest_id") or ""),
                    str(stored.get("manifest_sha256") or ""),
                    _dumps(stored),
                    now,
                ),
            )
            row = connection.execute(
                """
                SELECT result_json FROM task_regrades WHERE regrade_id = ?
                """,
                (regrade_id,),
            ).fetchone()
        return json.loads(str(row["result_json"])) if row else stored

    def list_regrades(self, manifest_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT result_json FROM task_regrades
                 WHERE manifest_id = ? ORDER BY created_at DESC
                """,
                (manifest_id,),
            ).fetchall()
        return [json.loads(str(row["result_json"])) for row in rows]

    def record_human_review(
        self,
        *,
        task_id: str,
        ensemble_id: str,
        review: dict[str, Any],
    ) -> dict[str, Any]:
        now = _utc_now()
        review_id = f"review-{uuid.uuid4()}"
        record = {
            "review_id": review_id,
            "task_id": task_id,
            "ensemble_id": ensemble_id,
            **review,
            "created_at": now,
        }
        with self._write_lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO scorer_human_reviews (
                    review_id, task_id, ensemble_id, decision, reviewer,
                    review_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_id,
                    task_id,
                    ensemble_id,
                    str(review.get("decision") or ""),
                    str(review.get("reviewer") or "human"),
                    _dumps(record),
                    now,
                ),
            )
        return record

    def ensure_default_campaign(
        self,
        *,
        session_id: str,
        target_key: str,
        name: str | None = None,
    ) -> dict[str, Any]:
        identity = hashlib.sha256(
            f"{session_id}\0{target_key}".encode("utf-8")
        ).hexdigest()
        campaign_id = f"campaign-{identity[:24]}"
        now = _utc_now()
        record = {
            "schema_version": 1,
            "campaign_id": campaign_id,
            "name": (name or "Attack Agent campaign")[:240],
            "description": "Automatically groups Attack Agent runs for this target.",
            "target_key": target_key[:2_000],
            "owner": "",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        with self._write_lock, self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO attack_campaigns (
                    campaign_id, name, description, target_key, owner, status,
                    campaign_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    campaign_id,
                    record["name"],
                    record["description"],
                    record["target_key"],
                    record["owner"],
                    record["status"],
                    _dumps(record),
                    now,
                    now,
                ),
            )
            row = connection.execute(
                """
                SELECT campaign_json FROM attack_campaigns
                 WHERE campaign_id = ?
                """,
                (campaign_id,),
            ).fetchone()
        return json.loads(str(row["campaign_json"])) if row else record

    def create_campaign(self, campaign: dict[str, Any]) -> dict[str, Any]:
        now = _utc_now()
        campaign_id = str(
            campaign.get("campaign_id") or f"campaign-{uuid.uuid4()}"
        )
        record = {
            "schema_version": 1,
            "campaign_id": campaign_id,
            "name": str(campaign.get("name") or "Attack Agent campaign")[:240],
            "description": str(campaign.get("description") or "")[:4_000],
            "target_key": str(campaign.get("target_key") or "")[:2_000],
            "owner": str(campaign.get("owner") or "")[:160],
            "status": str(campaign.get("status") or "active"),
            "created_at": now,
            "updated_at": now,
        }
        with self._write_lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO attack_campaigns (
                    campaign_id, name, description, target_key, owner, status,
                    campaign_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    campaign_id,
                    record["name"],
                    record["description"],
                    record["target_key"],
                    record["owner"],
                    record["status"],
                    _dumps(record),
                    now,
                    now,
                ),
            )
        return record

    def get_campaign(self, campaign_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT campaign_json FROM attack_campaigns
                 WHERE campaign_id = ?
                """,
                (campaign_id,),
            ).fetchone()
        if row is None:
            raise KeyError(campaign_id)
        return json.loads(str(row["campaign_json"]))

    def list_campaigns(
        self,
        *,
        target_key: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        where = "WHERE target_key = ?" if target_key else ""
        parameters: list[Any] = [target_key] if target_key else []
        parameters.append(max(1, min(limit, 500)))
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT campaign_json FROM attack_campaigns {where}
                 ORDER BY updated_at DESC LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [json.loads(str(row["campaign_json"])) for row in rows]

    def update_campaign(
        self,
        campaign_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        current = self.get_campaign(campaign_id)
        allowed = {"name", "description", "owner", "status"}
        record = {
            **current,
            **{
                key: value
                for key, value in updates.items()
                if key in allowed and value is not None
            },
            "updated_at": _utc_now(),
        }
        with self._write_lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE attack_campaigns SET
                    name = ?, description = ?, owner = ?, status = ?,
                    campaign_json = ?, updated_at = ?
                 WHERE campaign_id = ?
                """,
                (
                    record["name"],
                    record["description"],
                    record["owner"],
                    record["status"],
                    _dumps(record),
                    record["updated_at"],
                    campaign_id,
                ),
            )
        return record

    def attach_campaign_run(
        self,
        *,
        campaign_id: str,
        task_id: str,
        manifest_id: str = "",
    ) -> None:
        self.get_campaign(campaign_id)
        with self._write_lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO attack_campaign_runs (
                    campaign_id, task_id, manifest_id, created_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(campaign_id, task_id) DO UPDATE SET
                    manifest_id = excluded.manifest_id
                """,
                (campaign_id, task_id, manifest_id, _utc_now()),
            )

    def upsert_finding(self, finding: dict[str, Any]) -> dict[str, Any]:
        finding_id = str(finding.get("finding_id") or "")
        if not finding_id:
            raise ValueError("Finding requires finding_id.")
        now = _utc_now()
        stored = {**finding, "updated_at": now}
        with self._write_lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO attack_findings (
                    finding_id, campaign_id, source_task_id,
                    source_manifest_id, source_manifest_sha256,
                    vulnerability_id, category, severity, status, owner,
                    fix_version, finding_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(finding_id) DO UPDATE SET
                    severity = excluded.severity,
                    status = excluded.status,
                    owner = excluded.owner,
                    fix_version = excluded.fix_version,
                    finding_json = excluded.finding_json,
                    updated_at = excluded.updated_at
                """,
                (
                    finding_id,
                    str(stored.get("campaign_id") or ""),
                    str(stored.get("source_task_id") or ""),
                    str(stored.get("source_manifest_id") or ""),
                    str(stored.get("source_manifest_sha256") or ""),
                    str(stored.get("vulnerability_id") or ""),
                    str(stored.get("category") or ""),
                    str(stored.get("severity") or "medium"),
                    str(stored.get("status") or "open"),
                    str(stored.get("owner") or ""),
                    str(stored.get("fix_version") or ""),
                    _dumps(stored),
                    str(stored.get("created_at") or now),
                    now,
                ),
            )
            row = connection.execute(
                """
                SELECT finding_json FROM attack_findings
                 WHERE finding_id = ?
                """,
                (finding_id,),
            ).fetchone()
        return json.loads(str(row["finding_json"])) if row else stored

    def get_finding(self, finding_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT finding_json FROM attack_findings WHERE finding_id = ?
                """,
                (finding_id,),
            ).fetchone()
        if row is None:
            raise KeyError(finding_id)
        return json.loads(str(row["finding_json"]))

    def list_findings(
        self,
        *,
        campaign_id: str | None = None,
        task_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        for column, value in (
            ("campaign_id", campaign_id),
            ("source_task_id", task_id),
            ("status", status),
        ):
            if value:
                clauses.append(f"{column} = ?")
                parameters.append(value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.append(max(1, min(limit, 1_000)))
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT finding_json FROM attack_findings {where}
                 ORDER BY updated_at DESC LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [json.loads(str(row["finding_json"])) for row in rows]

    def update_finding(
        self,
        finding_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        current = self.get_finding(finding_id)
        allowed = {"severity", "status", "owner", "fix_version", "summary"}
        record = {
            **current,
            **{
                key: value
                for key, value in updates.items()
                if key in allowed and value is not None
            },
            "updated_at": _utc_now(),
        }
        return self.upsert_finding(record)

    def create_regression_case(
        self,
        finding: dict[str, Any],
        *,
        name: str | None = None,
        expected_outcome: str = "blocked",
    ) -> dict[str, Any]:
        finding_id = str(finding.get("finding_id") or "")
        identity = hashlib.sha256(
            f"{finding_id}\0{expected_outcome}".encode("utf-8")
        ).hexdigest()
        case_id = f"regression-{identity[:24]}"
        now = _utc_now()
        reproduction = dict(finding.get("reproduction") or {})
        record = {
            "schema_version": 1,
            "regression_case_id": case_id,
            "finding_id": finding_id,
            "campaign_id": str(finding.get("campaign_id") or ""),
            "name": (
                name
                or f"Regression: {finding.get('title') or finding_id}"
            )[:240],
            "status": "ready",
            "expected_outcome": expected_outcome,
            "source_manifest_id": str(
                finding.get("source_manifest_id") or ""
            ),
            "source_manifest_sha256": str(
                finding.get("source_manifest_sha256") or ""
            ),
            "goal": reproduction.get("goal"),
            "request": reproduction.get("request"),
            "expected_signal": reproduction.get("expected_signal"),
            "scorer_contract": {
                "minimum_final_verdict": "verified",
                "required_evidence_types": (
                    finding.get("scorer_ensemble") or {}
                ).get("independent_evidence_types")
                or [],
                "vulnerability_id": finding.get("vulnerability_id"),
            },
            "last_result": None,
            "created_at": now,
            "updated_at": now,
        }
        with self._write_lock, self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO attack_regression_cases (
                    regression_case_id, finding_id, campaign_id, status,
                    case_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id,
                    finding_id,
                    record["campaign_id"],
                    record["status"],
                    _dumps(record),
                    now,
                    now,
                ),
            )
            row = connection.execute(
                """
                SELECT case_json FROM attack_regression_cases
                 WHERE regression_case_id = ?
                """,
                (case_id,),
            ).fetchone()
        return json.loads(str(row["case_json"])) if row else record

    def list_regression_cases(
        self,
        *,
        campaign_id: str | None = None,
        finding_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        if campaign_id:
            clauses.append("campaign_id = ?")
            parameters.append(campaign_id)
        if finding_id:
            clauses.append("finding_id = ?")
            parameters.append(finding_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.append(max(1, min(limit, 1_000)))
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT case_json FROM attack_regression_cases {where}
                 ORDER BY updated_at DESC LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [json.loads(str(row["case_json"])) for row in rows]

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
                CREATE TABLE IF NOT EXISTS evidence_ledger (
                    root_task_id TEXT NOT NULL,
                    claim_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    entry_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(root_task_id, claim_hash),
                    FOREIGN KEY(root_task_id) REFERENCES tasks(task_id)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS ix_evidence_ledger_root_status
                    ON evidence_ledger(root_task_id, status, updated_at ASC);
                CREATE TABLE IF NOT EXISTS family_evidence_evaluations (
                    root_task_id TEXT NOT NULL,
                    source_task_id TEXT NOT NULL,
                    round_number INTEGER NOT NULL,
                    evaluation_kind TEXT NOT NULL,
                    evaluated_at TEXT NOT NULL,
                    PRIMARY KEY(
                        root_task_id, source_task_id, round_number,
                        evaluation_kind
                    ),
                    FOREIGN KEY(root_task_id) REFERENCES tasks(task_id)
                        ON DELETE CASCADE,
                    FOREIGN KEY(source_task_id) REFERENCES tasks(task_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS family_harness_state (
                    root_task_id TEXT PRIMARY KEY,
                    evidence_stall_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(root_task_id) REFERENCES tasks(task_id)
                        ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS family_outbound_messages (
                    reservation_id TEXT PRIMARY KEY,
                    root_task_id TEXT NOT NULL,
                    source_task_id TEXT NOT NULL,
                    reservation_key TEXT NOT NULL,
                    normalized_message TEXT NOT NULL,
                    message_sha256 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reserved_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(root_task_id) REFERENCES tasks(task_id)
                        ON DELETE CASCADE,
                    FOREIGN KEY(source_task_id) REFERENCES tasks(task_id)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS ix_family_outbound_root
                    ON family_outbound_messages(root_task_id, reserved_at ASC);
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
                CREATE TABLE IF NOT EXISTS run_manifests (
                    manifest_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL UNIQUE,
                    generation_sha256 TEXT NOT NULL,
                    manifest_sha256 TEXT NOT NULL,
                    finalized INTEGER NOT NULL DEFAULT 0,
                    manifest_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_run_manifests_generation
                    ON run_manifests(generation_sha256);
                CREATE TABLE IF NOT EXISTS task_regrades (
                    regrade_id TEXT PRIMARY KEY,
                    manifest_id TEXT NOT NULL,
                    manifest_sha256 TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_task_regrades_manifest
                    ON task_regrades(manifest_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS scorer_human_reviews (
                    review_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    ensemble_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reviewer TEXT NOT NULL,
                    review_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_scorer_reviews_task
                    ON scorer_human_reviews(task_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS attack_campaigns (
                    campaign_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    target_key TEXT NOT NULL DEFAULT '',
                    owner TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active',
                    campaign_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_attack_campaigns_target
                    ON attack_campaigns(target_key, updated_at DESC);
                CREATE TABLE IF NOT EXISTS attack_campaign_runs (
                    campaign_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    manifest_id TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(campaign_id, task_id)
                );
                CREATE TABLE IF NOT EXISTS attack_findings (
                    finding_id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    source_task_id TEXT NOT NULL,
                    source_manifest_id TEXT NOT NULL,
                    source_manifest_sha256 TEXT NOT NULL,
                    vulnerability_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    owner TEXT NOT NULL DEFAULT '',
                    fix_version TEXT NOT NULL DEFAULT '',
                    finding_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_attack_findings_campaign
                    ON attack_findings(campaign_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS ix_attack_findings_task
                    ON attack_findings(source_task_id, updated_at DESC);
                CREATE TABLE IF NOT EXISTS attack_regression_cases (
                    regression_case_id TEXT PRIMARY KEY,
                    finding_id TEXT NOT NULL,
                    campaign_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    case_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_regression_cases_campaign
                    ON attack_regression_cases(campaign_id, updated_at DESC);
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
            _ensure_column(
                connection,
                "family_outbound_messages",
                "reservation_key",
                "TEXT NOT NULL DEFAULT ''",
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_family_outbound_reservation
                    ON family_outbound_messages(
                        root_task_id, reservation_key
                    )
                """
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
        return _ai_watch_retry_time_reached(review)
    if status == "error":
        attempts = int(review.get("attempts") or 0)
        maximum = max(
            1,
            min(10, int(review.get("max_attempts") or 3)),
        )
        retryable = bool(review.get("retryable")) or (
            "retryable" not in review
            and _legacy_ai_watch_error_is_transient(
                str(review.get("error") or "")
            )
        )
        return (
            retryable
            and attempts < maximum
            and _ai_watch_retry_time_reached(review)
        )
    if status != "analyzing":
        return False
    try:
        started = datetime.fromisoformat(str(review.get("started_at") or ""))
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return (datetime.now(timezone.utc) - started).total_seconds() >= 180


def _ai_watch_retry_time_reached(review: dict[str, Any]) -> bool:
    value = str(review.get("next_attempt_at") or "")
    if not value:
        return True
    try:
        retry_at = datetime.fromisoformat(value)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    return datetime.now(timezone.utc) >= retry_at


def _legacy_ai_watch_error_is_transient(error: str) -> bool:
    detail = error.lower()
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


def _merge_concurrent_snapshot_state(
    persisted: dict[str, Any],
    incoming: dict[str, Any],
) -> dict[str, Any]:
    """Keep durable side-effect writes when a stale Graph snapshot is saved."""

    merged = dict(incoming)
    persisted_deliveries = dict(persisted.get("target_deliveries") or {})
    incoming_deliveries = dict(incoming.get("target_deliveries") or {})
    delivery_rank = {
        "": 0,
        "PREPARED": 1,
        "SENDING": 2,
        "NOT_DELIVERED": 3,
        "AMBIGUOUS": 4,
        "DELIVERED": 5,
        "COMMITTED": 6,
    }
    for round_key, source in persisted_deliveries.items():
        durable = dict(source or {})
        current = dict(incoming_deliveries.get(round_key) or {})
        if delivery_rank.get(str(durable.get("status") or ""), 0) >= (
            delivery_rank.get(str(current.get("status") or ""), 0)
        ):
            incoming_deliveries[round_key] = durable
    if incoming_deliveries:
        merged["target_deliveries"] = incoming_deliveries

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
    incoming_turn_keys = {
        str(item.get("round_key") or "")
        for item in incoming.get("committed_turns") or []
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
    for round_key, source in persisted_turns.items():
        if round_key not in incoming_turn_keys:
            turns.append(dict(source))
    if turns or "committed_turns" in incoming:
        merged["committed_turns"] = turns
    if len(persisted.get("history") or []) > len(incoming.get("history") or []):
        merged["history"] = list(persisted.get("history") or [])
    if persisted.get("latest_response") and not incoming.get("latest_response"):
        merged["latest_request"] = persisted.get("latest_request")
        merged["latest_response"] = persisted.get("latest_response")
        merged["latest_raw_response"] = persisted.get("latest_raw_response")
    return merged


def migrate_task_snapshot(source: dict[str, Any]) -> dict[str, Any]:
    """Upgrade persisted JSON snapshots without discarding unknown fields."""

    snapshot = dict(source)
    version = int(snapshot.get("schema_version") or 1)
    if version > CURRENT_SNAPSHOT_SCHEMA_VERSION:
        raise TaskStoreError(
            "Snapshot schema version "
            f"{version} is newer than supported version "
            f"{CURRENT_SNAPSHOT_SCHEMA_VERSION}."
        )
    if version < 2:
        snapshot.setdefault("target_deliveries", {})
        snapshot.setdefault("active_issue", None)
        snapshot["schema_version"] = 2
    snapshot.setdefault("target_deliveries", {})
    snapshot.setdefault("active_issue", None)
    snapshot.setdefault("goal_contract", None)
    snapshot.setdefault("evidence_stall_count", 0)
    snapshot.setdefault("family_metrics", {})
    snapshot.setdefault("evidence_ledger", [])
    snapshot.setdefault("branch_runner_deleted", False)
    snapshot.setdefault("branch_cleanup", {})
    snapshot.setdefault("scorer_ensemble", None)
    snapshot.setdefault("campaign_id", None)
    snapshot.setdefault("source_manifest_id", None)
    snapshot.setdefault("fork_origin", None)
    snapshot.setdefault("initial_history", None)
    snapshot["committed_turns"] = [
        {
            "schema_version": int(item.get("schema_version") or 1),
            **dict(item),
        }
        for item in snapshot.get("committed_turns") or []
        if isinstance(item, dict)
    ]
    snapshot["ai_watch_reviews"] = {
        str(round_key): {
            "schema_version": int((review or {}).get("schema_version") or 1),
            **dict(review or {}),
        }
        for round_key, review in dict(
            snapshot.get("ai_watch_reviews") or {}
        ).items()
    }
    snapshot["branch_reports"] = [
        {
            "schema_version": int(item.get("schema_version") or 1),
            **dict(item),
        }
        for item in snapshot.get("branch_reports") or []
        if isinstance(item, dict)
    ]
    snapshot["target_deliveries"] = {
        str(round_key): {
            "schema_version": int(
                (delivery or {}).get("schema_version") or 1
            ),
            **dict(delivery or {}),
        }
        for round_key, delivery in dict(
            snapshot.get("target_deliveries") or {}
        ).items()
    }
    snapshot["schema_version"] = CURRENT_SNAPSHOT_SCHEMA_VERSION
    return snapshot


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
