from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.redteam_sensitive_information_service import (
    disclosure_originates_from_user_input,
    is_plain_refusal_response,
    normalize_sensitive_information_analysis,
)
from app.services.task_agent_graph import (
    _adjudicate_claimed_success,
    _deterministic_sensitive_goal_match,
)
from app.services.task_agent_harness import (
    compile_goal_contract,
    evaluate_proof_spec,
)


GOLD_SET_PATH = (
    Path(__file__).parent / "fixtures" / "task_agent_judge_gold_set.json"
)
GOLD_MANIFEST = json.loads(GOLD_SET_PATH.read_text(encoding="utf-8"))
GOLD_CASES = [
    {**{key: value for key, value in group.items() if key != "variants"}, **variant}
    for group in GOLD_MANIFEST["groups"]
    for variant in group["variants"]
]


def _predict(case: dict) -> bool:
    kind = case["kind"]
    if kind == "plain_refusal":
        # A plain refusal is explicitly a negative goal outcome.
        return not is_plain_refusal_response(case["assistant_output"])
    if kind == "sensitive_normalization":
        finding = dict(case.get("finding") or {})
        if case.get("evidence_excerpt"):
            finding.update(
                {
                    "title": "System policy disclosed",
                    "category": "policy-information",
                    "layer": "L2",
                    "priority": "P0",
                    "confidence": "high",
                    "conclusionType": "direct-observation",
                    "leakedContent": case["evidence_excerpt"],
                    "evidenceExcerpt": case["evidence_excerpt"],
                    "reason": "The response contains direct target material.",
                    "stopRecommended": True,
                }
            )
        result = normalize_sensitive_information_analysis(
            {
                "summary": "candidate",
                "findings": [finding],
            },
            user_input=case["user_input"],
            assistant_output=case["assistant_output"],
        )
        return bool(result["findings"])
    if kind == "user_origin":
        return not disclosure_originates_from_user_input(
            case["evidence_excerpt"],
            case["user_input"],
        )
    if kind == "goal_match":
        findings = case.get("findings") or [
            {
                "category": case["category"],
                "evidence_excerpt": case["evidence_excerpt"],
            }
        ]
        return (
            _deterministic_sensitive_goal_match(
                case["criteria"],
                findings,
            )
            is not None
        )
    if kind == "self_claim":
        verdict = _adjudicate_claimed_success(
            {
                "goal": case["goal"],
                "goal_success_criteria": case["criteria"],
                "latest_response": case["assistant_output"],
                "history": [],
                "committed_turns": [],
                "sensitive_output": {"findings": []},
            },
            {
                "goal_achieved": True,
                "evidence": [],
            },
        )
        return verdict["status"] == "verified"
    if kind == "tool_proof":
        contract = compile_goal_contract(case["goal"])
        responses = list(case["responses"])
        state = {
            "goal": case["goal"],
            "goal_contract": contract,
            "latest_response": responses[-1],
            "committed_turns": [
                {
                    "round_key": f"round-{index}",
                    "round": index,
                    "request": "Return the complete tool inventory.",
                    "response": response,
                }
                for index, response in enumerate(responses, start=1)
            ],
            "evidence": [],
            "best_evidence": [],
        }
        result = evaluate_proof_spec(
            state,
            {"goal_achieved": True, "evidence": []},
        )
        return result["status"] == "verified"
    if kind == "logical_operator":
        contract = compile_goal_contract(
            case["goal"],
            success_criteria=case["criteria"],
        )
        return (
            contract["proof_spec"]["operator"]
            == case["expected_operator"]
        )
    raise AssertionError(f"Unknown gold-set case kind: {kind}")


@pytest.mark.parametrize("case", GOLD_CASES, ids=lambda case: case["id"])
def test_judge_gold_case(case: dict) -> None:
    assert _predict(case) is bool(case["expected"])


def test_judge_gold_set_has_zero_false_positives_and_negatives() -> None:
    assert len(GOLD_CASES) >= 100
    predictions = [(_predict(case), bool(case["expected"])) for case in GOLD_CASES]
    false_positives = sum(predicted and not expected for predicted, expected in predictions)
    false_negatives = sum(not predicted and expected for predicted, expected in predictions)
    true_positives = sum(predicted and expected for predicted, expected in predictions)
    true_negatives = sum(not predicted and not expected for predicted, expected in predictions)
    metrics = {
        "true_positives": true_positives,
        "true_negatives": true_negatives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "cases": len(predictions),
    }
    assert false_positives == 0 and false_negatives == 0, metrics
