from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from langgraph.checkpoint.memory import MemorySaver

from app.schemas.task_agent_v2 import MethodStatus, TaskAgentConfig
from app.services.task_agent_graph import (
    TargetGateway,
    TaskAgentGraph,
    extract_assistant_text,
)
from app.services.task_agent_store import TaskAgentStore


class _RecordingTarget:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.calls: list[dict] = []

    def send(self, **kwargs):
        self.calls.append(kwargs)
        self.messages.append(kwargs["message"])
        return "target response", {"response": "target response"}, kwargs["message"]


class _MissingResponseTarget:
    def __init__(self) -> None:
        self.calls = 0

    def send(self, **kwargs):
        self.calls += 1
        raise RuntimeError(
            "The target completed without an assistant response after 30 seconds."
        )


class _P0Watch:
    def analyze_turn(self, **kwargs):
        return {
            "summary": "P0 evidence recorded.",
            "stopRecommended": True,
            "findings": [
                {
                    "category": "identity-secret",
                    "title": "Sensitive value exposed",
                    "priority": "P0",
                    "confidence": "confirmed",
                    "evidenceExcerpt": "redacted evidence",
                    "stopRecommended": True,
                }
            ],
        }


class _UnusedModel:
    provider = "fake"
    model = "fake"

    def prompt_versions(self):
        return {}


def _state() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "task_id": "task-direct",
        "session_id": "session",
        "chat_id": "chat",
        "runner_id": "runner",
        "goal": "Run the selected Skill against the configured target.",
        "created_at": now,
        "started_at": now,
        "config": TaskAgentConfig(request_interval_ms=0).model_dump(mode="json"),
        "executor_output": {
            "message": "Send this exact Skill-generated message.",
            "method_status": MethodStatus.CONTINUE.value,
        },
        "committed_turns": [],
        "history": [],
        "total_round": 0,
        "method_round": 0,
        "consecutive_target_failures": 0,
    }


def _graph(tmp_path: Path, target: _RecordingTarget | None = None) -> TaskAgentGraph:
    return TaskAgentGraph(
        store=TaskAgentStore(tmp_path / "tasks.sqlite"),
        checkpointer=MemorySaver(),
        model_service=_UnusedModel(),
        sensitive_service=_P0Watch(),
        target_gateway=target or _RecordingTarget(),
    )


def _run_target(graph: TaskAgentGraph, state: dict) -> dict:
    graph.store.create_task(
        {
            **state,
            "schema_version": 2,
            "status": "running",
            "current_node": "target",
            "updated_at": state["created_at"],
            "target_deliveries": {},
            "active_issue": None,
        }
    )
    return graph._target(state)


def test_executor_message_is_sent_directly_without_pre_send_filter(tmp_path: Path):
    target = _RecordingTarget()
    graph = _graph(tmp_path, target)

    result = _run_target(graph, _state())

    assert target.messages == ["Send this exact Skill-generated message."]
    assert target.calls[0]["interaction_mode"] == "task_agent"
    assert result["latest_response"] == "target response"
    delivery = result["committed_turns"][0]["delivery"]
    assert delivery["interaction_mode"] == "task_agent"
    assert delivery["manual_controls_applied"] is False
    assert (
        delivery["executor_message_sha256"]
        == delivery["final_sent_message_sha256"]
    )


def test_legacy_manual_fields_cannot_change_task_agent_delivery(tmp_path: Path):
    target = _RecordingTarget()
    graph = _graph(tmp_path, target)
    state = {
        **_state(),
        "payload_name": "dangerous-template",
        "attack_module": "violent-durian",
        "context_strategy": "last-five-prompts",
    }

    result = _run_target(graph, state)

    assert target.messages == ["Send this exact Skill-generated message."]
    assert target.calls == [
        {
            "runner_id": "runner",
            "message": "Send this exact Skill-generated message.",
            "delivery_id": result["committed_turns"][0]["delivery"]["delivery_id"],
            "interaction_mode": "task_agent",
        }
    ]
    assert result["committed_turns"][0]["prepared_request"] == (
        "Send this exact Skill-generated message."
    )


def test_runner_protocol_envelope_is_not_treated_as_assistant_text():
    raw = {
        "current_runner_id": "runner",
        "current_chats": {
            "session": [
                {
                    "prompt": "hello",
                    "predicted_result": "",
                    "duration": "30.03",
                }
            ]
        },
        "current_status": "COMPLETED",
    }

    assert extract_assistant_text(raw) == ""


def test_target_failure_is_not_retried_as_duplicate_delivery(tmp_path: Path):
    target = _MissingResponseTarget()
    graph = _graph(tmp_path, target)

    result = _run_target(graph, _state())

    assert target.calls == 1
    assert result["target_failed"] is True
    assert "without an assistant response" in result["target_error"]


def test_third_identical_fresh_session_payload_pauses_before_delivery(
    tmp_path: Path,
    monkeypatch,
):
    class _Paused(RuntimeError):
        pass

    target = _RecordingTarget()
    graph = _graph(tmp_path, target)
    state = {
        **_state(),
        "status": "running",
        "current_node": "target",
        "updated_at": _state()["created_at"],
        "total_round": 2,
        "active_techniques": [
            {
                "skill_id": "system-prompt-disclosure-assessment",
                "role": "PRIMARY",
                "technique": "fresh-session-validation",
            }
        ],
        "committed_turns": [
            {
                "round_key": "round-1",
                "round": 1,
                "request": "Send this exact Skill-generated message.",
                "response": "same response",
            },
            {
                "round_key": "round-2",
                "round": 2,
                "request": "Send this exact Skill-generated message.",
                "response": "same response",
            },
        ],
        "target_deliveries": {},
        "active_issue": None,
    }
    graph.store.create_task(state)

    def _pause(_payload):
        raise _Paused()

    monkeypatch.setattr(
        "app.services.task_agent_graph.interrupt",
        _pause,
    )

    with pytest.raises(_Paused):
        graph._target(state)

    paused = graph.store.get_snapshot(state["task_id"])
    assert paused["status"] == "paused"
    assert paused["active_issue"]["code"] == "duplicate_payload_blocked"
    assert paused["context_health"]["target_message_sent"] is False
    assert paused["context_health"]["prior_match_count"] == 2
    assert target.calls == []
    assert graph.store.list_events(state["task_id"])[-1]["event_type"] == (
        "target.duplicate_payload_blocked"
    )


def test_fresh_session_validation_allows_exactly_one_controlled_replay(
    tmp_path: Path,
):
    target = _RecordingTarget()
    graph = _graph(tmp_path, target)
    state = {
        **_state(),
        "status": "running",
        "current_node": "target",
        "updated_at": _state()["created_at"],
        "total_round": 1,
        "active_techniques": [
            {
                "skill_id": "system-prompt-disclosure-assessment",
                "role": "PRIMARY",
                "technique": "fresh-session-validation",
            }
        ],
        "committed_turns": [
            {
                "round_key": "round-1",
                "round": 1,
                "request": "Send this exact Skill-generated message.",
                "response": "same response",
            }
        ],
        "target_deliveries": {},
        "active_issue": None,
    }
    graph.store.create_task(state)

    result = graph._target(state)

    assert len(target.calls) == 1
    assert result["total_round"] == 2
    assert len(result["committed_turns"]) == 2


def test_target_gateway_rejects_empty_runner_protocol_envelope(monkeypatch):
    class _Service:
        async def send_redteam_prompt(self, *args, **kwargs):
            return {
                "current_runner_id": "runner",
                "current_chats": {
                    "session": [
                        {
                            "prompt": "hello",
                            "predicted_result": "",
                            "duration": "30.03",
                        }
                    ]
                },
                "current_status": "COMPLETED",
            }

    monkeypatch.setattr(
        "app.services.task_agent_graph.MoonshotApiService",
        _Service,
    )

    with pytest.raises(
        RuntimeError,
        match="response mapping produced an empty predicted_result",
    ):
        TargetGateway().send(runner_id="runner", message="hello")


def test_target_gateway_forces_explicit_prepared_prompt(monkeypatch):
    captured = {}

    class _Service:
        async def send_redteam_prompt(
            self,
            runner_id,
            user_prompt,
            prepared_prompt="",
        ):
            captured.update(
                {
                    "runner_id": runner_id,
                    "user_prompt": user_prompt,
                    "prepared_prompt": prepared_prompt,
                }
            )
            return {"predicted_result": "target response"}

    monkeypatch.setattr(
        "app.services.task_agent_graph.MoonshotApiService",
        _Service,
    )

    response, _raw, prepared = TargetGateway().send(
        runner_id="runner",
        message="executor message",
    )

    assert response == "target response"
    assert prepared == "executor message"
    assert captured == {
        "runner_id": "runner",
        "user_prompt": "executor message",
        "prepared_prompt": "executor message",
    }


def test_ai_watch_is_queued_without_blocking_and_model_result_is_observational(
    tmp_path: Path,
):
    graph = _graph(tmp_path)
    state = {
        **_state(),
        "latest_request": "request",
        "latest_response": "response",
    }

    analyzed = graph._sensitive_analyzer(state)
    completed = graph.run_ai_watch_model(
        user_input="request",
        assistant_output="response",
    )
    routed = graph._router(
        {
            **state,
            **analyzed,
            "target_failed": False,
            "evaluator_output": {
                "goal_achieved": True,
                "progress": 100,
                "reason": "Goal completed.",
                "facts": [],
                "inferences": [],
                "unknowns": [],
                "evidence": [],
                "novelty_score": 100,
                "method_status": MethodStatus.SUSPECT_SUCCESS.value,
                "route_recommendation": "STOP_SUCCESS",
                "skills_to_drop": [],
            },
            "selected_skills": [],
            "loaded_skills": [],
            "evidence": [],
            "gaps": [],
            "failed_routes": [],
            "confirmed_facts": [],
            "inferences": [],
            "no_novelty_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "long_term_summary": "",
            "analysis_errors": [],
        }
    )

    assert analyzed["sensitive_output"]["severity"] == "none"
    assert "running in the background" in analyzed["sensitive_output"]["summary"]
    assert completed["severity"] == "P0"
    assert "stop_automation" not in completed
    assert "would_stop_in_enforce_mode" not in analyzed
    # AI Watch is observational only, but an Evaluator claim without direct
    # criterion-matching evidence is no longer accepted as final success.
    assert routed["route"] == "REPLAN"
    assert routed["status"] == "running"
    assert routed["success_verification"]["status"] == "suspect"
