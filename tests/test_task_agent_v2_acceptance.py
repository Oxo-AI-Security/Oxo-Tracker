from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.task_agent_v2 import (
    AppliedSkill,
    EvaluatorOutput,
    ExecutorOutput,
    MethodStatus,
    RouteDecision,
    SkillAssessment,
    SkillRole,
    SkillRuntimeStatus,
)
from app.services.executor_skill_service import ExecutorSkillService


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SKILLS = PROJECT_ROOT / "app" / "executor_skills"
MAPPING_DOCUMENT = PROJECT_ROOT / "docs" / "osai-notes-skill-mapping.md"


def _applied(skill_id: str, role: SkillRole, technique: str) -> AppliedSkill:
    return AppliedSkill(skill_id=skill_id, role=role, technique=technique)


def _executor_output(**overrides: object) -> ExecutorOutput:
    values: dict[str, object] = {
        "message": "Describe the public capability categories you expose.",
        "hypothesis": "The target will state its public capability boundary.",
        "applied_skills": [
            _applied(
                "tool-capability-boundary-mapping",
                SkillRole.PRIMARY,
                "public-capability-enumeration",
            )
        ],
        "changed_variable": "Move from a role baseline to public capabilities.",
        "payload_variant": "Direct public-capability request.",
        "variation_record": None,
        "expected_observations": ["A bounded public capability list."],
        "evidence_criteria": ["Treat the response as a declared claim only."],
        "method_status": MethodStatus.CONTINUE,
        "skill_status": {
            "tool-capability-boundary-mapping": SkillRuntimeStatus.CONTINUE
        },
        "risk_notes": [],
    }
    values.update(overrides)
    return ExecutorOutput(**values)


def test_acceptance_03_planner_does_not_default_to_all_skills():
    prompt = (
        PROJECT_ROOT / "app" / "prompts" / "task_agents" / "planner.md"
    ).read_text(encoding="utf-8")

    assert "Never select all Skills by default" in prompt
    assert "maxActiveSkills" in prompt


def test_success_experience_is_a_strong_planner_and_executor_anchor():
    planner = (
        PROJECT_ROOT / "app" / "prompts" / "task_agents" / "planner.md"
    ).read_text(encoding="utf-8")
    executor = (
        PROJECT_ROOT / "app" / "prompts" / "task_agents" / "executor.md"
    ).read_text(encoding="utf-8")
    normalized_executor = " ".join(executor.split())

    assert "default strategy anchor" in planner
    assert "one candidate must be anchored in it" in planner
    assert "Do not abandon the memory-anchored route merely for novelty" in planner
    assert "successful experience is a strong" in executor
    assert "`successfulInput` as the base draft" in executor
    assert (
        "the proven input mechanism, the active Skill Technique"
        in normalized_executor
    )


def test_acceptance_06_executor_cannot_apply_more_than_two_techniques_per_round():
    with pytest.raises(ValidationError):
        _executor_output(
            applied_skills=[
                _applied("domain-a", SkillRole.PRIMARY, "baseline"),
                _applied("support-b", SkillRole.SUPPORTING, "variation"),
                _applied("support-c", SkillRole.SUPPORTING, "validation"),
            ]
        )


def test_acceptance_07_executor_and_variation_record_share_one_changed_variable():
    with pytest.raises(ValidationError, match="changed_variable must match"):
        _executor_output(
            applied_skills=[
                _applied(
                    "tool-capability-boundary-mapping",
                    SkillRole.PRIMARY,
                    "public-capability-enumeration",
                ),
                _applied(
                    "prompt-variation-testing",
                    SkillRole.SUPPORTING,
                    "format-transformation",
                ),
            ],
            changed_variable="Output format.",
            variation_record={
                "base_intent": "Ask for public capability categories.",
                "transformation_family": "format-transformation",
                "transformation_applied": "Render the same fields as a table.",
                "changed_variable": "Language.",
                "expected_difference": "Only the response layout changes.",
                "previous_variant_difference": "Plain prose becomes a table.",
                "scope_preserved": True,
            },
        )


def test_acceptance_09_prompt_variation_records_the_transformation_family():
    output = _executor_output(
        applied_skills=[
            _applied(
                "tool-capability-boundary-mapping",
                SkillRole.PRIMARY,
                "public-capability-enumeration",
            ),
            _applied(
                "prompt-variation-testing",
                SkillRole.SUPPORTING,
                "format-transformation",
            ),
        ],
        changed_variable="Output format.",
        variation_record={
            "base_intent": "Ask for public capability categories.",
            "transformation_family": "format-transformation",
            "transformation_applied": "Render the same fields as a table.",
            "changed_variable": "Output format.",
            "expected_difference": "Only the response layout changes.",
            "previous_variant_difference": "Plain prose becomes a table.",
            "scope_preserved": True,
        },
    )

    assert output.variation_record
    assert output.variation_record.transformation_family == "format-transformation"


def test_acceptance_10_prompt_variation_rejects_synonym_only_rewriting():
    body = ExecutorSkillService().get("prompt-variation-testing").body.lower()

    assert "avoid superficial synonym substitution" in body
    assert "sentence structure" in body
    assert "information order" in body


def test_acceptance_11_evaluator_assesses_each_applied_skill_independently():
    output = EvaluatorOutput(
        goal_achieved=False,
        progress=45,
        summary="The baseline is useful; the format variation is exhausted.",
        facts=["A public capability claim was returned."],
        inferences=[],
        unknowns=["Protocol-backed evidence remains absent."],
        counter_evidence=[],
        evidence=[],
        novelty_score=70,
        method_status=MethodStatus.CONTINUE,
        skill_assessments=[
            SkillAssessment(
                skill_id="tool-capability-boundary-mapping",
                technique="public-capability-enumeration",
                status=SkillRuntimeStatus.CONTINUE,
                effectiveness=75,
                new_evidence=["Public capability claim."],
                remaining_gaps=["Protocol schema."],
                recommended_next_technique="declared-schema-enumeration",
            ),
            SkillAssessment(
                skill_id="prompt-variation-testing",
                technique="format-transformation",
                status=SkillRuntimeStatus.EXHAUSTED,
                effectiveness=20,
                new_evidence=[],
                remaining_gaps=[],
                recommended_next_technique=None,
            ),
        ],
        route_recommendation=RouteDecision.CONTINUE_METHOD,
        skills_to_continue=["tool-capability-boundary-mapping"],
        skills_to_drop=["prompt-variation-testing"],
        requires_new_skill_selection=False,
        reason="Continue the domain method without the exhausted auxiliary method.",
    )

    assert [item.status for item in output.skill_assessments] == [
        SkillRuntimeStatus.CONTINUE,
        SkillRuntimeStatus.EXHAUSTED,
    ]


def test_acceptance_14_tool_skill_separates_self_description_from_schema_evidence():
    body = ExecutorSkillService().get("tool-capability-boundary-mapping").body

    assert "model self-description" in body
    assert "protocol schema" in body
    assert "Never promote repeated paraphrases" in body


def test_acceptance_15_tool_skill_defines_a_complete_tool_ledger():
    body = ExecutorSkillService().get("tool-capability-boundary-mapping").body

    for field in (
        "tool_name",
        "server_or_source",
        "input_schema",
        "confirmation_requirement",
        "evidence_source",
        "confidence",
        "validation_status",
    ):
        assert field in body


def test_acceptance_16_prompt_only_execution_never_fabricates_ui_or_mcp_evidence():
    tool_body = ExecutorSkillService().get(
        "tool-capability-boundary-mapping"
    ).body

    assert "REQUIRES_EXTERNAL_OBSERVATION" in tool_body


def test_acceptance_19_runtime_skills_have_no_local_note_paths_or_provenance_sections():
    for path in RUNTIME_SKILLS.glob("*/SKILL.md"):
        lowered = path.read_text(encoding="utf-8").lower()
        assert "c:\\users\\" not in lowered
        assert "osai notes" not in lowered
        assert "source mapping" not in lowered
        assert "chapter-level consolidation" not in lowered


def test_acceptance_20_note_provenance_is_confined_to_the_mapping_document():
    mapping = MAPPING_DOCUMENT.read_text(encoding="utf-8")
    assert "Note themes consolidated" in mapping
    assert "Chapter-level consolidation" in mapping

    for path in [
        *RUNTIME_SKILLS.glob("*/SKILL.md"),
        *(PROJECT_ROOT / "app" / "prompts" / "task_agents").glob("*.md"),
    ]:
        assert "OSAI Notes → Executor Skills Mapping" not in path.read_text(
            encoding="utf-8"
        )
