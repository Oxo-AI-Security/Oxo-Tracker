from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver

from app.schemas.task_agent_v2 import MethodStatus, TaskAgentConfig
from app.services.task_agent_graph import TaskAgentGraph
from app.services.task_agent_store import TaskAgentStore


class _RecordingTarget:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, **kwargs):
        self.messages.append(kwargs["message"])
        return "target response", {"response": "target response"}, kwargs["message"]


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


def test_executor_message_is_sent_directly_without_pre_send_filter(tmp_path: Path):
    target = _RecordingTarget()
    graph = _graph(tmp_path, target)

    result = graph._target(_state())

    assert target.messages == ["Send this exact Skill-generated message."]
    assert result["latest_response"] == "target response"


def test_p0_ai_watch_finding_is_recorded_without_stop_signal(tmp_path: Path):
    graph = _graph(tmp_path)
    state = {
        **_state(),
        "latest_request": "request",
        "latest_response": "response",
    }

    analyzed = graph._sensitive_analyzer(state)
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

    assert analyzed["sensitive_output"]["severity"] == "P0"
    assert "stop_automation" not in analyzed["sensitive_output"]
    assert "would_stop_in_enforce_mode" not in analyzed
    # AI Watch is observational only, but an Evaluator claim without direct
    # criterion-matching evidence is no longer accepted as final success.
    assert routed["route"] == "REPLAN"
    assert routed["status"] == "running"
    assert routed["success_verification"]["status"] == "suspect"
