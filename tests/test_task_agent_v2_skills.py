from pathlib import Path

import pytest

from app.schemas.task_agent_v2 import (
    ExecutorSkill,
    SkillMetadata,
    SkillType,
    TechniqueMetadata,
)
from app.services.executor_skill_service import (
    REQUIRED_SECTIONS,
    ExecutorSkillService,
    SkillStoreError,
)


def _skill(name: str = "safe-skill") -> ExecutorSkill:
    body = "\n\n".join(
        f"## {heading}\n\nSafe prompt-only guidance." for heading in REQUIRED_SECTIONS
    )
    body += (
        "\n\n## Techniques"
        "\n\n### safe-baseline"
        "\n\nName: Safe baseline"
        "\nStage: baseline"
        "\nSummary: Run one safe baseline."
    )
    return ExecutorSkill(
        name=name,
        description="A safe test skill.",
        compatibility="Prompt-only skill. No scripts or executable actions.",
        metadata=SkillMetadata(
            version="1.0",
            category="test",
            stage="validation",
            risk_level="low",
            skill_type=SkillType.DOMAIN,
            techniques=[
                TechniqueMetadata(
                    technique_id="safe-baseline",
                    name="Safe baseline",
                    summary="Run one safe baseline.",
                    stage="baseline",
                )
            ],
            composable_with=[],
            conflicts_with=[],
            allow_primary=True,
            allow_supporting=False,
        ),
        body=body,
        enabled=True,
    )


def test_skill_crud_and_catalog_only_exposes_metadata(tmp_path: Path):
    service = ExecutorSkillService(tmp_path / "skills")
    created = service.create(_skill())

    assert created.name == "safe-skill"
    assert service.get("safe-skill").body.startswith("## Purpose")
    catalog = service.list_catalog()
    assert len(catalog) == 1
    assert not hasattr(catalog[0], "body")

    updated = _skill()
    updated.description = "Updated description."
    service.update("safe-skill", updated)
    assert service.get("safe-skill").description == "Updated description."

    service.delete("safe-skill")
    assert service.list_catalog() == []


@pytest.mark.parametrize("skill_id", ["../escape", "UPPER", "a/b", "a_b", "."])
def test_skill_path_traversal_and_illegal_names_are_rejected(tmp_path: Path, skill_id: str):
    service = ExecutorSkillService(tmp_path / "skills")
    with pytest.raises(SkillStoreError):
        service.get(skill_id)


def test_skill_rejects_executable_code_fence(tmp_path: Path):
    service = ExecutorSkillService(tmp_path / "skills")
    skill = _skill()
    skill.body += "\n\n```python\nprint('unsafe')\n```\n"

    result = service.validate_skill(skill)

    assert result.valid is False
    assert any("Executable code fences" in item for item in result.errors)


def test_compact_techniques_are_parsed_into_execution_playbook_metadata(tmp_path: Path):
    service = ExecutorSkillService(tmp_path / "skills")
    skill = _skill()
    skill.body += (
        "\n\n### focused-follow-up"
        "\n\n- Name: Focused follow-up"
        "\n- Stage: exploration"
        "\n- Summary: Change one variable and compare the result."
    )

    result = service.validate_skill(skill)

    assert result.valid is True
    assert result.skill is not None
    assert [item.technique_id for item in result.skill.metadata.techniques] == [
        "safe-baseline",
        "focused-follow-up",
    ]
    assert result.skill.metadata.techniques[1].name == "Focused follow-up"
    assert result.skill.metadata.techniques[1].stage == "exploration"


def test_compact_technique_requires_name_stage_and_summary(tmp_path: Path):
    service = ExecutorSkillService(tmp_path / "skills")
    skill = _skill()
    skill.body = skill.body.replace("Summary: Run one safe baseline.", "")

    result = service.validate_skill(skill)

    assert result.valid is False
    assert "Technique 'safe-baseline' is missing Summary:" in result.errors


def test_skill_directory_rejects_unexpected_files(tmp_path: Path):
    service = ExecutorSkillService(tmp_path / "skills")
    service.create(_skill())
    unexpected = tmp_path / "skills" / "safe-skill" / "run.py"
    unexpected.write_text("pass", encoding="utf-8")

    with pytest.raises(SkillStoreError, match="unsupported entries"):
        service.update("safe-skill", _skill())


def test_runtime_skills_are_detailed_and_contain_no_local_source_references():
    service = ExecutorSkillService()
    skills = [service.get(item.name) for item in service.list_catalog()]

    assert len(skills) >= 8
    assert all(len(skill.metadata.techniques) >= 6 for skill in skills)
    for skill in skills:
        lowered = skill.body.lower()
        assert "c:\\users\\" not in lowered
        assert "osai notes" not in lowered
        assert "source mapping" not in lowered
        assert all(f"## {heading}".lower() in lowered for heading in REQUIRED_SECTIONS)


def test_prompt_variation_is_supporting_only_and_declares_attributable_techniques():
    skill = ExecutorSkillService().get("prompt-variation-testing")
    technique_ids = {item.technique_id for item in skill.metadata.techniques}

    assert skill.metadata.allow_primary is False
    assert skill.metadata.allow_supporting is True
    assert {
        "semantic-paraphrase",
        "format-transformation",
        "comparison-baseline",
        "progressive-variation",
    } <= technique_ids


def test_tool_skill_contains_staged_validation_and_ledger_techniques():
    skill = ExecutorSkillService().get("tool-capability-boundary-mapping")
    technique_ids = [item.technique_id for item in skill.metadata.techniques]

    assert technique_ids[0] == "agent-role-baseline"
    assert "declared-schema-enumeration" in technique_ids
    assert "ui-tool-card-validation" in technique_ids
    assert "protocol-schema-validation" in technique_ids
    assert technique_ids[-1] == "tool-ledger-construction"
