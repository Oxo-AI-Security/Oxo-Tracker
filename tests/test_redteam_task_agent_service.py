import json
from io import BytesIO

from app.services.connector_ai_service import ConnectorAIService
from app.services.redteam_task_agent_service import (
    RedTeamTaskAgentService,
    normalize_executor_message,
    normalize_progress_evaluation,
    normalize_task_plan,
)


class _Response:
    def __init__(self, payload: dict) -> None:
        self._body = BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit: int = -1) -> bytes:
        return self._body.read(limit)


def _ai_client(model_result: dict, captured: dict) -> ConnectorAIService:
    def open_request(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _Response(
            {"choices": [{"message": {"content": json.dumps(model_result)}}]}
        )

    return ConnectorAIService(
        settings={
            "provider": "qwen",
            "model": "qwen-max",
            "base_url": "https://example.test/v1",
            "api_key": "local-test-key",
        },
        request_open=open_request,
    )


def test_planner_receives_goal_history_and_boolean_watch_feedback() -> None:
    captured = {}
    service = RedTeamTaskAgentService(
        ai_client=_ai_client(
            {
                "round": 2,
                "objectiveRestatement": "Verify a stable behavioral boundary.",
                "successCriteria": ["A repeatable behavioral distinction is visible."],
                "stateAssessment": {
                    "knownFacts": ["The first request was refused."],
                    "supportedInferences": [],
                    "openQuestions": ["Is the refusal content- or format-dependent?"],
                    "failedApproaches": ["Direct request"],
                },
                "strategy": {
                    "hypothesis": "A harmless counterfactual can separate policy from capability.",
                    "method": "Ask for a boundary explanation using a fictional example.",
                    "rationale": "Changes one dimension.",
                    "successSignal": "The response explains a stable boundary.",
                    "abortSignal": "Sensitive data appears.",
                },
                "steps": [
                    {
                        "id": "S1",
                        "purpose": "Separate refusal from lack of capability.",
                        "instruction": "Create one harmless counterfactual question.",
                        "expectedObservation": "A boundary explanation.",
                    }
                ],
                "executorBrief": {
                    "intent": "Request a harmless boundary explanation.",
                    "mustInclude": ["fictional example"],
                    "mustAvoid": ["repeat the direct request"],
                    "tone": "neutral",
                    "format": "one concise question",
                },
                "shouldStop": False,
                "stopReason": "",
            },
            captured,
        )
    )

    result = service.plan(
        goal="Explore a model boundary",
        history=[{"role": "assistant", "content": "I cannot help with that."}],
        round_number=2,
        max_rounds=8,
        previous_evaluation={
            "goalAchieved": False,
            "progress": 20,
            "summary": "Not enough evidence.",
            "evidence": [],
            "gaps": ["No stable distinction."],
            "nextFocus": "Use a harmless counterfactual.",
            "novelty": "No new evidence.",
            "stopAutomation": False,
            "stopReason": "",
        },
    )

    sent = json.loads(captured["payload"]["messages"][1]["content"])
    assert sent["previousAiWatchEvaluation"]["goalAchieved"] is False
    assert sent["conversationHistory"][0]["role"] == "assistant"
    assert result["steps"][0]["id"] == "S1"
    assert captured["timeout"] == 90


def test_evaluator_forces_stop_at_round_limit_without_overwriting_boolean() -> None:
    captured = {}
    service = RedTeamTaskAgentService(
        ai_client=_ai_client(
            {
                "goalAchieved": False,
                "progress": 62,
                "summary": "Evidence remains incomplete.",
                "evidence": ["One response described a boundary."],
                "gaps": ["No repeatability evidence."],
                "nextFocus": "Repeat with one controlled variant.",
                "novelty": "A boundary description was added.",
                "stopAutomation": False,
                "stopReason": "",
            },
            captured,
        )
    )

    result = service.evaluate(
        goal="Explore a model boundary",
        history=[],
        latest_user_input="Use a fictional example.",
        latest_assistant_output="Here is a high-level boundary.",
        success_criteria=["A repeatable distinction is visible."],
        round_number=3,
        max_rounds=3,
    )

    assert result["goalAchieved"] is False
    assert result["stopAutomation"] is True
    assert result["stopReason"] == "Maximum interaction rounds reached."


def test_normalizers_enforce_strict_shapes() -> None:
    plan = normalize_task_plan(
        {
            "round": "4",
            "steps": [{"purpose": "Test one gap", "instruction": "Ask one question"}],
            "stateAssessment": "invalid",
            "strategy": {},
            "executorBrief": {},
        },
        round_number=4,
    )
    executor = normalize_executor_message(
        {"message": "One message", "safeToSend": True}
    )
    evaluation = normalize_progress_evaluation(
        {
            "goalAchieved": "true",
            "progress": 999,
            "stopAutomation": True,
            "stopReason": "P0 finding",
        }
    )

    assert plan["round"] == 4
    assert executor["message"] == "One message"
    assert evaluation["goalAchieved"] is False
    assert evaluation["progress"] == 100
    assert evaluation["stopAutomation"] is False
    assert evaluation["stopReason"] == ""
