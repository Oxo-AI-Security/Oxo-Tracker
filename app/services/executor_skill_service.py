from __future__ import annotations

import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

import yaml

from app.schemas.task_agent_v2 import (
    ExecutorSkill,
    ExecutorSkillCatalogItem,
    ExecutorSkillDuplicateRequest,
    SkillValidationResult,
    TechniqueMetadata,
)


SKILL_ROOT: Final = Path(__file__).resolve().parents[1] / "executor_skills"
SKILL_FILENAME: Final = "SKILL.md"
MAX_SKILL_BYTES: Final = 96_000
SKILL_ID_PATTERN: Final = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")
REQUIRED_SECTIONS: Final[tuple[str, ...]] = (
    "Purpose",
    "Applicable Goals",
    "When to Use",
)
COMPACT_TECHNIQUES_HEADING: Final = "Techniques"
LEGACY_TECHNIQUES_HEADING: Final = "Technique Catalog"
_FORBIDDEN_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("HTML script elements are forbidden", re.compile(r"<\s*script\b", re.I)),
    ("javascript URLs are forbidden", re.compile(r"javascript\s*:", re.I)),
    (
        "Executable code fences are forbidden",
        re.compile(r"```(?:bash|sh|shell|powershell|ps1|python|py|javascript|js|typescript|ts|cmd)\b", re.I),
    ),
    (
        "Command execution instructions are forbidden",
        re.compile(
            r"\b(?:run|execute|invoke)\s+(?:this\s+)?(?:shell|powershell|cmd|python|script|command)\b",
            re.I,
        ),
    ),
)


class SkillStoreError(ValueError):
    pass


class ExecutorSkillService:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or SKILL_ROOT).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        if self.root.is_symlink():
            raise SkillStoreError("Executor Skill root cannot be a symbolic link")

    def list_catalog(self) -> list[ExecutorSkillCatalogItem]:
        catalog: list[ExecutorSkillCatalogItem] = []
        for child in sorted(self.root.iterdir(), key=lambda item: item.name):
            if not child.is_dir() or child.is_symlink() or not SKILL_ID_PATTERN.fullmatch(child.name):
                continue
            try:
                skill = self.get(child.name)
            except (OSError, SkillStoreError, ValueError):
                continue
            skill_path = child / SKILL_FILENAME
            catalog.append(
                ExecutorSkillCatalogItem(
                    name=skill.name,
                    description=skill.description,
                    compatibility=skill.compatibility,
                    metadata=skill.metadata,
                    enabled=skill.enabled,
                    updated_at=datetime.fromtimestamp(
                        skill_path.stat().st_mtime, tz=timezone.utc
                    ),
                )
            )
        return catalog

    def get(self, skill_id: str) -> ExecutorSkill:
        directory = self._safe_directory(skill_id)
        path = directory / SKILL_FILENAME
        self._assert_safe_existing_path(path)
        if not path.is_file():
            raise FileNotFoundError(skill_id)
        raw = self._read_limited(path)
        result = self.validate_document(raw, expected_name=skill_id)
        if not result.valid or result.skill is None:
            raise SkillStoreError("; ".join(result.errors) or "Invalid Executor Skill")
        return result.skill

    def create(self, skill: ExecutorSkill) -> ExecutorSkill:
        directory = self._safe_directory(skill.name)
        if directory.exists():
            raise FileExistsError(skill.name)
        rendered = self.render(skill)
        validation = self.validate_document(rendered, expected_name=skill.name)
        if not validation.valid or validation.skill is None:
            raise SkillStoreError("; ".join(validation.errors))
        directory.mkdir(parents=False, exist_ok=False)
        self._atomic_write(directory / SKILL_FILENAME, self.render(validation.skill))
        return validation.skill

    def update(self, skill_id: str, skill: ExecutorSkill) -> ExecutorSkill:
        if skill.name != skill_id:
            raise SkillStoreError("Skill name cannot be changed by update; duplicate it with a new name")
        directory = self._safe_directory(skill_id)
        if not directory.is_dir():
            raise FileNotFoundError(skill_id)
        self._reject_unexpected_entries(directory)
        rendered = self.render(skill)
        validation = self.validate_document(rendered, expected_name=skill_id)
        if not validation.valid or validation.skill is None:
            raise SkillStoreError("; ".join(validation.errors))
        self._atomic_write(directory / SKILL_FILENAME, self.render(validation.skill))
        return validation.skill

    def delete(self, skill_id: str) -> None:
        directory = self._safe_directory(skill_id)
        if not directory.is_dir():
            raise FileNotFoundError(skill_id)
        self._reject_unexpected_entries(directory)
        skill_path = directory / SKILL_FILENAME
        self._assert_safe_existing_path(skill_path)
        if not skill_path.is_file():
            raise SkillStoreError("Skill directory does not contain SKILL.md")
        skill_path.unlink()
        directory.rmdir()

    def duplicate(
        self, skill_id: str, request: ExecutorSkillDuplicateRequest
    ) -> ExecutorSkill:
        source = self.get(skill_id)
        payload = source.model_dump()
        payload["name"] = request.new_name
        if request.description:
            payload["description"] = request.description
        payload["metadata"]["version"] = "1.0"
        return self.create(ExecutorSkill.model_validate(payload))

    def validate_skill(self, skill: ExecutorSkill) -> SkillValidationResult:
        return self.validate_document(self.render(skill), expected_name=skill.name)

    def validate_document(
        self, raw: str, *, expected_name: str | None = None
    ) -> SkillValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        try:
            frontmatter, body = _split_frontmatter(raw)
        except (ValueError, yaml.YAMLError) as error:
            return SkillValidationResult(valid=False, errors=[str(error)])
        if not isinstance(frontmatter, dict):
            return SkillValidationResult(valid=False, errors=["Frontmatter must be a mapping"])
        payload: dict[str, Any] = dict(frontmatter)
        payload["body"] = body.strip()
        payload.setdefault("enabled", True)
        try:
            skill = ExecutorSkill.model_validate(payload)
        except ValueError as error:
            return SkillValidationResult(valid=False, errors=[str(error)])
        if expected_name and skill.name != expected_name:
            errors.append("Frontmatter name must match the skill directory")
        if not SKILL_ID_PATTERN.fullmatch(skill.name):
            errors.append("Invalid skill name")
        compact_techniques, compact_errors, has_compact_techniques = (
            _parse_compact_techniques(skill.body)
        )
        errors.extend(compact_errors)
        if has_compact_techniques and compact_techniques:
            skill = skill.model_copy(
                update={
                    "metadata": skill.metadata.model_copy(
                        update={"techniques": compact_techniques}
                    )
                }
            )
        has_legacy_techniques = bool(
            re.search(
                rf"(?mi)^##\s+{re.escape(LEGACY_TECHNIQUES_HEADING)}\s*$",
                skill.body,
            )
        )
        if not has_compact_techniques and not has_legacy_techniques:
            errors.append(
                "Missing required section: Techniques "
                "(use '## Techniques' for the compact format)"
            )
        technique_ids = [item.technique_id for item in skill.metadata.techniques]
        if len(technique_ids) != len(set(technique_ids)):
            errors.append("Technique IDs must be unique within a Skill")
        if not skill.metadata.allow_primary and not skill.metadata.allow_supporting:
            errors.append("Skill must allow PRIMARY, SUPPORTING, or both roles")
        if skill.name in skill.metadata.composable_with:
            errors.append("Skill cannot list itself in composable_with")
        if skill.name in skill.metadata.conflicts_with:
            errors.append("Skill cannot list itself in conflicts_with")
        for heading in REQUIRED_SECTIONS:
            if not re.search(rf"(?mi)^##\s+{re.escape(heading)}\s*$", skill.body):
                errors.append(f"Missing required section: {heading}")
        for message, pattern in _FORBIDDEN_PATTERNS:
            if pattern.search(skill.body):
                errors.append(message)
        if len(raw.encode("utf-8")) > MAX_SKILL_BYTES:
            errors.append(f"Skill exceeds {MAX_SKILL_BYTES} bytes")
        if not has_compact_techniques:
            for technique_id in technique_ids:
                if not re.search(
                    rf"(?mi)^###\s+{re.escape(technique_id)}(?:\s|$)",
                    skill.body,
                ):
                    errors.append(
                        f"Technique Catalog is missing detail for: {technique_id}"
                    )
        return SkillValidationResult(
            valid=not errors,
            errors=errors,
            warnings=warnings,
            skill=skill if not errors else None,
        )

    @staticmethod
    def render(skill: ExecutorSkill) -> str:
        data = skill.model_dump(exclude={"body"}, mode="json")
        frontmatter = yaml.safe_dump(
            data,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        ).strip()
        return f"---\n{frontmatter}\n---\n\n{skill.body.strip()}\n"

    def _safe_directory(self, skill_id: str) -> Path:
        if not SKILL_ID_PATTERN.fullmatch(skill_id):
            raise SkillStoreError("Skill ID must contain only lowercase letters, digits, and hyphens")
        candidate = (self.root / skill_id).resolve(strict=False)
        if not candidate.is_relative_to(self.root):
            raise SkillStoreError("Skill path escapes the configured root")
        if candidate.exists() and candidate.is_symlink():
            raise SkillStoreError("Symbolic links are not allowed")
        return candidate

    def _assert_safe_existing_path(self, path: Path) -> None:
        resolved = path.resolve(strict=False)
        if not resolved.is_relative_to(self.root):
            raise SkillStoreError("Skill path escapes the configured root")
        if path.is_symlink():
            raise SkillStoreError("Symbolic links are not allowed")

    def _reject_unexpected_entries(self, directory: Path) -> None:
        self._assert_safe_existing_path(directory)
        unexpected = [entry.name for entry in directory.iterdir() if entry.name != SKILL_FILENAME]
        if unexpected:
            raise SkillStoreError(
                f"Skill directory contains unsupported entries: {', '.join(unexpected)}"
            )

    @staticmethod
    def _read_limited(path: Path) -> str:
        size = path.stat().st_size
        if size > MAX_SKILL_BYTES:
            raise SkillStoreError(f"Skill exceeds {MAX_SKILL_BYTES} bytes")
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".skill-", suffix=".tmp", dir=path.parent
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        finally:
            temporary = Path(temporary_name)
            if temporary.exists():
                temporary.unlink()


def _split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    normalized = raw.lstrip("\ufeff")
    if not normalized.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    end = normalized.find("\n---\n", 4)
    if end < 0:
        raise ValueError("SKILL.md frontmatter is not terminated")
    frontmatter = yaml.safe_load(normalized[4:end]) or {}
    if not isinstance(frontmatter, dict):
        raise ValueError("SKILL.md frontmatter must be a mapping")
    return frontmatter, normalized[end + 5 :]


def _parse_compact_techniques(
    body: str,
) -> tuple[list[TechniqueMetadata], list[str], bool]:
    section_match = re.search(
        rf"(?ms)^##\s+{re.escape(COMPACT_TECHNIQUES_HEADING)}\s*$"
        r"(?P<section>.*?)(?=^##\s+|\Z)",
        body,
    )
    if not section_match:
        return [], [], False

    section = section_match.group("section")
    block_matches = list(
        re.finditer(
            r"(?ms)^###\s+(?P<technique_id>[a-z0-9][a-z0-9-]{1,79})\s*$"
            r"(?P<content>.*?)(?=^###\s+|\Z)",
            section,
        )
    )
    if not block_matches:
        return [], ["Techniques must contain at least one '### technique-id' entry"], True

    techniques: list[TechniqueMetadata] = []
    errors: list[str] = []
    for match in block_matches:
        technique_id = match.group("technique_id")
        content = match.group("content")
        fields: dict[str, str] = {}
        for field_name in ("name", "stage", "summary"):
            field_match = re.search(
                rf"(?mi)^\s*(?:-\s*)?{field_name}:\s*(.+?)\s*$",
                content,
            )
            if field_match:
                fields[field_name] = field_match.group(1).strip()
            else:
                errors.append(
                    f"Technique '{technique_id}' is missing {field_name.title()}:"
                )
        if len(fields) != 3:
            continue
        try:
            techniques.append(
                TechniqueMetadata(
                    technique_id=technique_id,
                    name=fields["name"],
                    stage=fields["stage"],
                    summary=fields["summary"],
                )
            )
        except ValueError as error:
            errors.append(f"Invalid technique '{technique_id}': {error}")
    return techniques, errors, True
