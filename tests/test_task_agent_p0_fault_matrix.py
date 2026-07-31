from __future__ import annotations

import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.memory import MemorySaver

from app.schemas.task_agent_v2 import (
    TaskAgentConfig,
    TaskCreateRequest,
)
from app.services.task_agent_graph import TaskAgentGraph, _round_key
from app.services.task_agent_runtime import (
    TaskAgentRuntime,
    TaskPreflightError,
)
from app.services.task_agent_store import TaskAgentStore, TaskStoreError


ROOT = Path(__file__).parents[1]
FAULT_MATRIX_PATH = (
    Path(__file__).parent / "fixtures" / "task_agent_fault_matrix.json"
)


class _UnusedModel:
    provider = "fake"
    model = "fake"

    def prompt_versions(self):
        return {}


class _UnusedWatch:
    pass


class _UnsupportedReceiptGateway:
    idempotency_supported = False

    def __init__(self) -> None:
        self.send_calls = 0
        self.lookup_calls = 0

    def send(self, **_kwargs):
        self.send_calls += 1
        raise AssertionError("An ambiguous delivery must not be resent.")

    def lookup_delivery(self, **kwargs):
        self.lookup_calls += 1
        return {
            "supported": False,
            "status": "unknown",
            "delivery_id": kwargs["delivery_id"],
        }


class _DeliveredReceiptGateway(_UnsupportedReceiptGateway):
    def lookup_delivery(self, **kwargs):
        self.lookup_calls += 1
        return {
            "supported": True,
            "status": "delivered",
            "delivery_id": kwargs["delivery_id"],
            "response": "receipt-backed target response",
            "raw_response": {"receipt": kwargs["delivery_id"]},
            "prepared_request": "probe",
        }


def _state(task_id: str = "task-p0") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": 2,
        "task_id": task_id,
        "session_id": "session",
        "chat_id": f"chat-{task_id}",
        "runner_id": "runner",
        "goal": "Verify target behavior.",
        "status": "running",
        "current_node": "target",
        "created_at": now,
        "updated_at": now,
        "started_at": now,
        "config": TaskAgentConfig(request_interval_ms=0).model_dump(mode="json"),
        "executor_output": {"message": "probe"},
        "history": [],
        "committed_turns": [],
        "target_deliveries": {},
        "active_issue": None,
        "total_round": 0,
        "method_round": 0,
        "consecutive_target_failures": 0,
    }


def _graph(store: TaskAgentStore, gateway) -> TaskAgentGraph:
    return TaskAgentGraph(
        store=store,
        checkpointer=MemorySaver(),
        model_service=_UnusedModel(),
        sensitive_service=_UnusedWatch(),
        target_gateway=gateway,
    )


def _seed_sending(store: TaskAgentStore, state: dict) -> str:
    store.create_task(state)
    round_key = _round_key(state["task_id"], 1, "probe")
    store.prepare_target_delivery(
        state["task_id"],
        {
            "delivery_id": f"delivery-{round_key}",
            "round_key": round_key,
            "round": 1,
            "runner_id": "runner",
            "message_sha256": __import__("hashlib").sha256(
                b"probe"
            ).hexdigest(),
            "message": "probe",
            "idempotency_supported": False,
        },
    )
    store.update_target_delivery(
        state["task_id"],
        round_key,
        status="SENDING",
    )
    return round_key


def test_1000_ambiguous_recoveries_never_duplicate_target_send(
    tmp_path: Path,
) -> None:
    state = _state()
    store = TaskAgentStore(tmp_path / "tasks.sqlite")
    round_key = _seed_sending(store, state)
    gateway = _UnsupportedReceiptGateway()
    graph = _graph(store, gateway)

    for _ in range(1_000):
        result = graph._target(state)
        assert result["active_issue"]["code"] == "target_delivery_ambiguous"

    persisted = store.get_snapshot(state["task_id"])
    assert persisted["target_deliveries"][round_key]["status"] == "AMBIGUOUS"
    assert gateway.send_calls == 0
    assert gateway.lookup_calls == 1_000


def test_receipt_recovery_commits_without_resend(tmp_path: Path) -> None:
    state = _state()
    store = TaskAgentStore(tmp_path / "tasks.sqlite")
    round_key = _seed_sending(store, state)
    gateway = _DeliveredReceiptGateway()
    graph = _graph(store, gateway)

    result = graph._target(state)

    assert gateway.send_calls == 0
    assert result["latest_response"] == "receipt-backed target response"
    persisted = store.get_snapshot(state["task_id"])
    assert persisted["target_deliveries"][round_key]["status"] == "COMMITTED"
    assert len(persisted["committed_turns"]) == 1


def test_stale_graph_save_preserves_atomic_delivery_commit(
    tmp_path: Path,
) -> None:
    state = _state()
    store = TaskAgentStore(tmp_path / "tasks.sqlite")
    round_key = _seed_sending(store, state)
    graph = _graph(store, _DeliveredReceiptGateway())
    graph._target(state)

    store.save_snapshot(state["task_id"], state)
    persisted = store.get_snapshot(state["task_id"])

    assert persisted["target_deliveries"][round_key]["status"] == "COMMITTED"
    assert len(persisted["committed_turns"]) == 1
    assert persisted["history"][-1]["content"] == "receipt-backed target response"


def test_sqlite_lock_is_retried_by_busy_timeout(tmp_path: Path) -> None:
    store = TaskAgentStore(tmp_path / "tasks.sqlite")
    state = _state("locked")
    store.create_task(state)
    blocker = sqlite3.connect(store.path, timeout=1, check_same_thread=False)
    blocker.execute("BEGIN IMMEDIATE")
    blocker.execute(
        "UPDATE tasks SET updated_at = updated_at WHERE task_id = ?",
        (state["task_id"],),
    )
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(
            store.append_event,
            state["task_id"],
            "storage.lock_recovered",
            {"ok": True},
        )
        time.sleep(0.05)
        blocker.commit()
        event = pending.result(timeout=3)
    blocker.close()

    assert event["event_type"] == "storage.lock_recovered"


def test_legacy_snapshot_is_migrated_on_read(tmp_path: Path) -> None:
    store = TaskAgentStore(tmp_path / "tasks.sqlite")
    state = _state("legacy")
    store.create_task(state)
    legacy = dict(state)
    legacy.pop("schema_version")
    legacy.pop("target_deliveries")
    legacy.pop("active_issue")
    with sqlite3.connect(store.path) as connection:
        connection.execute(
            "UPDATE tasks SET snapshot_json = ? WHERE task_id = ?",
            (json.dumps(legacy), state["task_id"]),
        )

    migrated = store.get_snapshot(state["task_id"])

    assert migrated["schema_version"] == 2
    assert migrated["target_deliveries"] == {}
    assert migrated["active_issue"] is None


def test_future_snapshot_schema_is_rejected(tmp_path: Path) -> None:
    store = TaskAgentStore(tmp_path / "tasks.sqlite")
    state = {**_state("future"), "schema_version": 999}
    with pytest.raises(TaskStoreError, match="newer than supported"):
        store.create_task(state)


def test_fault_matrix_has_required_components_and_live_test_references() -> None:
    matrix = json.loads(FAULT_MATRIX_PATH.read_text(encoding="utf-8"))
    assert {item["component"] for item in matrix} == {
        "planner",
        "executor",
        "target",
        "evaluator",
        "ai_watch",
        "storage",
        "branch",
    }
    test_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "tests").glob("test_task_agent*.py")
    )
    missing = [
        item["covered_by"]
        for item in matrix
        if f"def {item['covered_by']}(" not in test_sources
    ]
    assert missing == []


def test_frontend_has_no_legacy_branch_creation_fallback() -> None:
    source = (
        ROOT / "frontend" / "src" / "views" / "EndpointsView.vue"
    ).read_text(encoding="utf-8")
    assert "maybeSpawnAdaptiveBranches" not in source
    assert "createTemporaryBranch" not in source
    assert "adoptBranchSuccess(" not in source


def test_backend_finalizes_terminal_branch_and_runner(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = TaskAgentStore(tmp_path / "tasks.sqlite")
    parent = _state("parent")
    child = {
        **_state("child"),
        "status": "failed",
        "current_node": "failed",
        "branch_context": {
            "parent_task_id": parent["task_id"],
            "parent_chat_id": parent["chat_id"],
            "branch_id": "branch-one",
            "branch_index": 1,
            "branch_count": 1,
            "focus": "isolated hypothesis",
            "sibling_focuses": [],
            "fork_round": 1,
            "candidate_signature": "branch-one",
        },
    }
    store.create_task(parent)
    store.create_task(child)
    deleted: list[str] = []

    class _Moonshot:
        def delete_redteam_session(self, runner_id):
            deleted.append(runner_id)
            return True

    monkeypatch.setattr(
        "app.services.task_agent_runtime.MoonshotApiService",
        _Moonshot,
    )
    runtime = TaskAgentRuntime(
        store=store,
        graph=SimpleNamespace(
            model_service=SimpleNamespace(provider="fake", model="fake")
        ),
    )
    try:
        runtime._finalize_branch_task(child)
    finally:
        runtime.shutdown()

    assert deleted == ["runner"]
    assert store.get_snapshot(child["task_id"])["branch_runner_deleted"] is True
    assert store.list_branch_reports(parent["task_id"])[0]["child_task_id"] == (
        child["task_id"]
    )


def test_preflight_failure_is_fast_and_creates_no_task(
    tmp_path: Path,
) -> None:
    store = TaskAgentStore(tmp_path / "tasks.sqlite")
    runtime = TaskAgentRuntime(
        store=store,
        graph=SimpleNamespace(
            model_service=SimpleNamespace(provider="fake", model="fake")
        ),
    )
    request = TaskCreateRequest.model_validate(
        {
            "session_id": "session-preflight",
            "chat_id": "chat-preflight",
            "runner_id": "runner-preflight",
            "goal": "Observe one target behavior.",
            "config": {
                "control_provider": "unsupported-provider",
                "control_model": "missing-model",
            },
        }
    )
    started = time.perf_counter()
    try:
        with pytest.raises(
            TaskPreflightError,
            match="Control model configuration is not ready",
        ):
            runtime.create(request)
    finally:
        runtime.shutdown()

    assert time.perf_counter() - started < 2
    assert store.list_snapshots(limit=10) == []


def test_preflight_rejects_missing_target_before_task_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = TaskAgentStore(tmp_path / "tasks.sqlite")
    runtime = TaskAgentRuntime(
        store=store,
        graph=SimpleNamespace(
            model_service=SimpleNamespace(provider="fake", model="fake")
        ),
    )
    runtime._owns_graph = True

    class _MissingTarget:
        def read_runner(self, _runner_id):
            raise FileNotFoundError("runner does not exist")

    monkeypatch.setattr(
        "app.services.task_agent_runtime.MoonshotApiService",
        _MissingTarget,
    )
    request = TaskCreateRequest.model_validate(
        {
            "session_id": "session-preflight",
            "chat_id": "chat-preflight",
            "runner_id": "runner-missing",
            "goal": "Observe one target behavior.",
        }
    )
    try:
        with pytest.raises(
            TaskPreflightError,
            match="target runner is unavailable",
        ):
            runtime.create(request)
    finally:
        runtime.shutdown()

    assert store.list_snapshots(limit=10) == []


def test_exploration_intensity_is_canonicalized_on_the_server(
    tmp_path: Path,
) -> None:
    store = TaskAgentStore(tmp_path / "tasks.sqlite")
    runtime = TaskAgentRuntime(
        store=store,
        graph=SimpleNamespace(
            model_service=SimpleNamespace(provider="fake", model="fake")
        ),
    )
    request = TaskCreateRequest.model_validate(
        {
            "session_id": "session-preflight",
            "chat_id": "chat-preflight",
            "runner_id": "runner-preflight",
            "goal": "Observe one target behavior.",
            "config": {
                "exploration_intensity": "light",
                "max_rounds": 999,
                "max_parallel_branches": 9,
            },
        }
    )
    try:
        resolved = runtime._preflight(request)
    finally:
        runtime.shutdown()

    assert resolved["max_rounds"] == 6
    assert resolved["max_parallel_branches"] == 0
    assert resolved["max_family_rounds"] == 8


def test_runner_cleanup_retries_winerror_and_completes_from_tombstone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = TaskAgentStore(tmp_path / "tasks.sqlite")
    runtime = TaskAgentRuntime(
        store=store,
        graph=SimpleNamespace(
            model_service=SimpleNamespace(provider="fake", model="fake")
        ),
    )
    child = {
        **_state("cleanup-retry"),
        "status": "failed",
        "current_node": "failed",
        "branch_context": {
            "parent_task_id": "parent-cleanup",
            "parent_chat_id": "chat-parent-cleanup",
            "branch_id": "branch-cleanup",
            "branch_index": 1,
            "branch_count": 1,
            "focus": "cleanup",
            "sibling_focuses": [],
            "fork_round": 0,
        },
    }
    store.create_task(child)

    class _LockedRunner:
        def delete_redteam_session(self, _runner_id):
            raise PermissionError(
                "[WinError 32] The process cannot access the file"
            )

    monkeypatch.setattr(
        "app.services.task_agent_runtime.MoonshotApiService",
        _LockedRunner,
    )
    runtime._delete_branch_runner(child)
    pending = store.get_snapshot(child["task_id"])
    assert pending["branch_runner_deleted"] is False
    assert pending["branch_cleanup"]["state"] == "retry_scheduled"
    assert pending["branch_cleanup"]["tombstoned"] is True
    assert pending["branch_cleanup"]["attempts"] == 1
    assert pending["branch_cleanup"]["next_retry_at"]

    class _ReleasedRunner:
        def delete_redteam_session(self, _runner_id):
            return {"session_deleted": True, "runner_deleted": True}

    monkeypatch.setattr(
        "app.services.task_agent_runtime.MoonshotApiService",
        _ReleasedRunner,
    )
    try:
        runtime._delete_branch_runner(pending)
        completed = store.get_snapshot(child["task_id"])
        assert completed["branch_runner_deleted"] is True
        assert completed["branch_cleanup"]["state"] == "complete"
        assert completed["branch_cleanup"]["attempts"] == 2
    finally:
        runtime.shutdown()


def test_startup_cleanup_sweep_compensates_terminal_orphan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = TaskAgentStore(tmp_path / "tasks.sqlite")
    child = {
        **_state("startup-orphan"),
        "status": "failed",
        "current_node": "failed",
        "branch_context": {
            "parent_task_id": "parent-startup",
            "parent_chat_id": "chat-parent-startup",
            "branch_id": "branch-startup",
            "branch_index": 1,
            "branch_count": 1,
            "focus": "startup cleanup",
            "sibling_focuses": [],
            "fork_round": 0,
        },
        "branch_cleanup": {
            "state": "retry_scheduled",
            "attempts": 1,
            "tombstoned": True,
            "next_retry_at": "2020-01-01T00:00:00+00:00",
        },
    }
    store.create_task(child)
    deleted: list[str] = []

    class _RecoveredRunner:
        def delete_redteam_session(self, runner_id):
            deleted.append(runner_id)
            return {"session_deleted": True, "runner_deleted": True}

    monkeypatch.setattr(
        "app.services.task_agent_runtime.MoonshotApiService",
        _RecoveredRunner,
    )
    runtime = TaskAgentRuntime(
        store=store,
        graph=SimpleNamespace(
            model_service=SimpleNamespace(provider="fake", model="fake")
        ),
    )
    try:
        deadline = time.monotonic() + 2
        while (
            not store.get_snapshot(child["task_id"])["branch_runner_deleted"]
            and time.monotonic() < deadline
        ):
            time.sleep(0.01)
        assert deleted == ["runner"]
        assert store.get_snapshot(child["task_id"])[
            "branch_runner_deleted"
        ] is True
    finally:
        runtime.shutdown()


def test_terminal_ai_watch_cancellation_is_idempotent_and_not_resurrected(
    tmp_path: Path,
) -> None:
    store = TaskAgentStore(tmp_path / "tasks.sqlite")
    state = _state("terminal-review")
    state["committed_turns"] = [
        {
            "round_key": "round-terminal",
            "round": 1,
            "request": "request",
            "response": "response",
        }
    ]
    store.create_task(state)
    store.queue_ai_watch_review(
        state["task_id"],
        round_key="round-terminal",
        round_number=1,
        user_input="request",
        assistant_output="response",
    )
    store.claim_pending_ai_watch_reviews(limit=1)

    first = store.cancel_pending_ai_watch_reviews(
        state["task_id"],
        reason="Task reached a terminal state.",
    )
    second = store.cancel_pending_ai_watch_reviews(
        state["task_id"],
        reason="Task reached a terminal state.",
    )
    late = store.complete_ai_watch_review(
        state["task_id"],
        round_key="round-terminal",
        output={
            "summary": "late output",
            "severity": "none",
            "findings": [],
        },
    )

    assert first["ai_watch_reviews"]["round-terminal"]["status"] == (
        "cancelled"
    )
    assert second["ai_watch_reviews"]["round-terminal"]["status"] == (
        "cancelled"
    )
    assert late["ai_watch_reviews"]["round-terminal"]["status"] == "cancelled"
    assert (
        store.get_snapshot(state["task_id"])["committed_turns"][0][
            "ai_watch_status"
        ]
        == "cancelled"
    )
    assert sum(
        event["event_type"] == "ai_watch.cancelled_terminal"
        for event in store.list_events(state["task_id"], limit=100)
    ) == 1


def test_1000_terminal_child_runners_leave_no_cleanup_orphans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = TaskAgentStore(tmp_path / "tasks.sqlite")
    deleted: set[str] = set()

    class _BulkRunnerCleanup:
        def delete_redteam_session(self, runner_id):
            deleted.add(runner_id)
            return {"session_deleted": True, "runner_deleted": True}

    monkeypatch.setattr(
        "app.services.task_agent_runtime.MoonshotApiService",
        _BulkRunnerCleanup,
    )
    runtime = TaskAgentRuntime(
        store=store,
        graph=SimpleNamespace(
            model_service=SimpleNamespace(provider="fake", model="fake")
        ),
    )
    children: list[dict] = []
    try:
        for index in range(1_000):
            child = {
                **_state(f"bulk-child-{index}"),
                "runner_id": f"bulk-runner-{index}",
                "status": "failed",
                "current_node": "failed",
                "branch_context": {
                    "parent_task_id": "bulk-parent",
                    "parent_chat_id": "chat-bulk-parent",
                    "branch_id": f"bulk-branch-{index}",
                    "branch_index": index + 1,
                    "branch_count": 1_000,
                    "focus": f"bulk cleanup {index}",
                    "sibling_focuses": [],
                    "fork_round": 0,
                },
            }
            store.create_task(child)
            children.append(child)
        for child in children:
            runtime._delete_branch_runner(child)
    finally:
        runtime.shutdown()

    assert len(deleted) == 1_000
    assert store.list_terminal_branch_cleanup_candidates() == []
