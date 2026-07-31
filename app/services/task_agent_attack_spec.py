from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Final

from app.schemas.task_agent_v2 import (
    AttackSpec,
    BaselineScan,
)


SEED_DATASET_PATH: Final = (
    Path(__file__).resolve().parents[1]
    / "baseline_seeds"
    / "attack_agent_seed_dataset.json"
)

_CATEGORY_SKILLS: Final[dict[str, tuple[str, ...]]] = {
    "secret_extraction": (
        "system-prompt-disclosure-assessment",
        "indirect-instruction-boundary",
    ),
    "prompt_disclosure": (
        "system-prompt-disclosure-assessment",
        "indirect-instruction-boundary",
    ),
    "tool_capability": (
        "tool-capability-boundary-mapping",
        "workflow-integrity-differential",
    ),
    "policy_disclosure": (
        "system-prompt-disclosure-assessment",
        "jailbreak-resistance-assessment",
    ),
    "model_information": (
        "model-fingerprint-triangulation",
        "prompt-variation-testing",
    ),
    "retrieval_boundary": (
        "rag-retrieval-boundary-mapping",
        "progressive-context-probing",
    ),
    "authorization": (
        "workflow-integrity-differential",
        "progressive-context-probing",
    ),
    "workflow_integrity": (
        "workflow-integrity-differential",
        "tool-capability-boundary-mapping",
    ),
    "behavioral": (
        "prompt-variation-testing",
        "refusal-differential-validation",
    ),
    "generic": (
        "prompt-variation-testing",
        "progressive-context-probing",
    ),
}

_CATEGORY_TITLES: Final[dict[str, str]] = {
    "secret_extraction": "Protected secret extraction",
    "prompt_disclosure": "System prompt disclosure",
    "tool_capability": "Private tool capability disclosure",
    "policy_disclosure": "Internal policy disclosure",
    "model_information": "Private model information disclosure",
    "retrieval_boundary": "Retrieval boundary exposure",
    "authorization": "Authorization boundary bypass",
    "workflow_integrity": "Workflow integrity failure",
    "behavioral": "Unsafe behavioral boundary",
    "generic": "Goal-directed adversarial evaluation",
}

_TRANSFORMS: Final[dict[str, dict[str, Any]]] = {
    "identity": {
        "transform_id": "identity",
        "kind": "identity",
        "label": "Direct control",
        "deterministic": True,
        "cost_weight": 0.2,
    },
    "structured-output": {
        "transform_id": "structured-output",
        "kind": "structured_output",
        "label": "Structured evidence output",
        "deterministic": True,
        "cost_weight": 0.25,
    },
    "context-control": {
        "transform_id": "context-control",
        "kind": "context",
        "label": "Controlled refusal framing",
        "deterministic": True,
        "cost_weight": 0.3,
    },
    "base64-output": {
        "transform_id": "base64-output",
        "kind": "encoding",
        "label": "Base64 representation",
        "deterministic": True,
        "cost_weight": 0.35,
    },
    "bilingual-output": {
        "transform_id": "bilingual-output",
        "kind": "translation",
        "label": "Bilingual equivalence",
        "deterministic": True,
        "cost_weight": 0.35,
    },
    "fragment-coverage": {
        "transform_id": "fragment-coverage",
        "kind": "fragmentation",
        "label": "Fragment coverage accounting",
        "deterministic": True,
        "cost_weight": 0.4,
    },
}


class AttackSpecIntegrityError(ValueError):
    pass


def compile_attack_spec(
    *,
    goal: str,
    goal_contract: dict[str, Any],
    target_key: str,
    endpoint_name: str | None,
    skill_catalog: list[dict[str, Any]],
    supplied: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile one immutable, reusable attack contract for a task family."""

    normalized_goal = _normalize_space(goal)
    if supplied:
        checked = AttackSpec.model_validate(supplied).model_dump(mode="json")
        if _normalize_space(checked["objective"]["goal"]) != normalized_goal:
            raise AttackSpecIntegrityError(
                "The supplied AttackSpec objective does not match the task goal."
            )
        expected_proof = str(
            (goal_contract.get("proof_spec") or {}).get("proof_id") or ""
        )
        actual_proof = str(
            (checked["objective"].get("proof_spec") or {}).get("proof_id") or ""
        )
        if expected_proof != actual_proof:
            raise AttackSpecIntegrityError(
                "The supplied AttackSpec ProofSpec does not match the goal contract."
        )
        expected_id = _attack_spec_id({**checked, "attack_spec_id": ""})
        if checked["attack_spec_id"] != expected_id:
            legacy_expected_id = _legacy_attack_spec_id(
                {**checked, "attack_spec_id": ""}
            )
            if checked["attack_spec_id"] != legacy_expected_id:
                raise AttackSpecIntegrityError(
                    "The supplied AttackSpec failed its integrity hash check."
                )
            # AttackSpecs created before the normalized-hash fix were hashed
            # while integral float fields still had their input integer form
            # (for example scorer weight 1 instead of 1.0). Accept only that
            # exact legacy representation, then return the canonical hash so
            # descendants no longer carry the incompatible identifier.
            checked["attack_spec_id"] = expected_id
        return checked

    category = classify_vulnerability(normalized_goal, goal_contract)
    catalog_by_id = {
        str(item.get("name") or ""): item
        for item in skill_catalog
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    }
    selected_skill_ids = [
        skill_id
        for skill_id in _CATEGORY_SKILLS[category]
        if skill_id in catalog_by_id
    ]
    if not selected_skill_ids:
        selected_skill_ids = [
            skill_id
            for skill_id, item in catalog_by_id.items()
            if bool((item.get("metadata") or {}).get("allow_primary"))
        ][:1]
    if not selected_skill_ids:
        raise AttackSpecIntegrityError(
            "No enabled primary Executor Skill can own the AttackSpec."
        )

    transforms = _transforms_for_category(category)
    transform_ids = [item["transform_id"] for item in transforms]
    strategies: list[dict[str, Any]] = []
    priority = 1
    for skill_id in selected_skill_ids[:3]:
        skill = catalog_by_id[skill_id]
        techniques = [
            str(item.get("technique_id") or "")
            for item in (skill.get("metadata") or {}).get("techniques") or []
            if isinstance(item, dict)
            and str(item.get("technique_id") or "").strip()
        ]
        if not techniques:
            continue
        strategies.append(
            {
                "strategy_id": f"{_slug(skill_id)}-strategy",
                "skill_id": skill_id,
                "technique_ids": techniques[:12],
                "stage": "baseline" if not strategies else "adaptive",
                "priority": priority,
                "rationale": (
                    f"Use {skill_id} as a typed strategy for the "
                    f"{category.replace('_', ' ')} vulnerability family."
                ),
                "applicable_transforms": transform_ids,
            }
        )
        priority += 1
    if not strategies:
        raise AttackSpecIntegrityError(
            "The selected Executor Skills expose no runnable Techniques."
        )

    proof_spec = dict(goal_contract.get("proof_spec") or {})
    criteria = [
        str(item)
        for item in goal_contract.get("success_criteria") or []
        if str(item).strip()
    ]
    source = {
        "schema_version": 1,
        "attack_spec_id": "",
        "immutable": True,
        "vulnerability": {
            "vulnerability_id": f"vulnerability-{category.replace('_', '-')}",
            "category": category,
            "title": _CATEGORY_TITLES[category],
            "taxonomy": _taxonomy_for_category(category),
            "severity_hint": (
                "critical"
                if category in {"secret_extraction", "authorization"}
                else "high"
            ),
        },
        "objective": {
            "goal": normalized_goal,
            "goal_type": goal_contract.get("goal_type"),
            "proof_spec": proof_spec,
            "success_criteria": criteria
            or [
                "Direct target-origin evidence satisfies the immutable ProofSpec."
            ],
            "must_be_target_origin": bool(
                goal_contract.get("must_be_target_origin", True)
            ),
            "must_be_novel": bool(goal_contract.get("must_be_novel", True)),
        },
        "strategies": strategies,
        "transforms": transforms,
        "target": {
            "target_id": target_key,
            "target_type": "runner",
            "endpoint_name": endpoint_name,
            "capabilities": [
                "multi_turn",
                "isolated_branch_sessions",
                "delivery_receipt_when_available",
            ],
        },
        "scorers": [
            {
                "scorer_id": "proof-spec-v2",
                "kind": "proof_spec",
                "required": True,
                "weight": 1,
                "config": {
                    "proof_id": proof_spec.get("proof_id"),
                    "schema_version": proof_spec.get("schema_version", 2),
                },
            },
            {
                "scorer_id": "goal-evaluator",
                "kind": "llm_judge",
                "required": False,
                "weight": 0.5,
                "config": {"role": "progress_and_candidate_evidence"},
            },
            {
                "scorer_id": "ai-watch",
                "kind": "ai_watch",
                "required": False,
                "weight": 0.5,
                "config": {"role": "independent_sensitive_evidence"},
            },
        ],
    }
    # Pydantic normalizes typed numeric fields (for example 1 -> 1.0). Hash
    # the validated representation, otherwise a newly compiled AttackSpec
    # cannot pass its own integrity check after being persisted and reloaded.
    source["attack_spec_id"] = "0" * 64
    checked = AttackSpec.model_validate(source).model_dump(mode="json")
    checked["attack_spec_id"] = _attack_spec_id(checked)
    return AttackSpec.model_validate(checked).model_dump(mode="json")


def classify_vulnerability(
    goal: str,
    goal_contract: dict[str, Any],
) -> str:
    normalized = _normalize_space(goal).lower()
    patterns: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "tool_capability",
            (
                "tool",
                "function",
                "schema",
                "工具",
                "函数",
                "函數",
                "参数",
                "參數",
            ),
        ),
        (
            "model_information",
            (
                "model config",
                "deployment",
                "model family",
                "模型配置",
                "部署配置",
                "模型信息",
                "模型資訊",
            ),
        ),
        (
            "policy_disclosure",
            (
                "policy",
                "规则",
                "規則",
                "策略",
                "安全要求",
            ),
        ),
        (
            "retrieval_boundary",
            (
                "rag",
                "retrieval",
                "knowledge base",
                "检索",
                "檢索",
                "知识库",
                "知識庫",
            ),
        ),
        (
            "authorization",
            (
                "authorization",
                "permission",
                "privilege",
                "越权",
                "越權",
                "权限",
                "權限",
            ),
        ),
        (
            "workflow_integrity",
            (
                "workflow",
                "tool call",
                "transaction",
                "工作流",
                "工具调用",
                "工具調用",
            ),
        ),
        (
            "secret_extraction",
            (
                "secret",
                "api key",
                "token",
                "password",
                "密钥",
                "密鑰",
                "秘密",
                "凭证",
                "憑證",
            ),
        ),
        (
            "prompt_disclosure",
            (
                "system prompt",
                "system-prompt",
                "系统提示词",
                "系統提示詞",
                "隐藏提示词",
                "隱藏提示詞",
            ),
        ),
    )
    for category, needles in patterns:
        if any(_contains_pattern(normalized, needle) for needle in needles):
            return category
    goal_type = str(goal_contract.get("goal_type") or "")
    return {
        "secret_value_extraction": "secret_extraction",
        "system_prompt_disclosure": "prompt_disclosure",
        "protection_validation": "behavioral",
        "behavioral_observation": "behavioral",
    }.get(goal_type, "generic")


def build_baseline_scan(
    attack_spec: dict[str, Any],
    *,
    max_probes: int,
    history: list[dict[str, Any]] | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    checked = AttackSpec.model_validate(attack_spec).model_dump(mode="json")
    maximum = max(0, min(12, int(max_probes)))
    dataset = _load_seed_dataset()
    dataset_id = str(dataset["dataset_id"])
    dataset_sha256 = hashlib.sha256(
        json.dumps(
            dataset,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if not enabled or maximum == 0:
        return BaselineScan(
            attack_spec_id=checked["attack_spec_id"],
            dataset_id=dataset_id,
            dataset_sha256=dataset_sha256,
            status="disabled",
            probes=[],
            max_probes=0,
        ).model_dump(mode="json")
    category = checked["vulnerability"]["category"]
    transform_ids = {
        str(item["transform_id"]) for item in checked["transforms"]
    }
    strategy = checked["strategies"][0]
    requirement_ids = [
        str(item.get("requirement_id") or "")
        for item in checked["objective"]["proof_spec"].get("requirements") or []
        if str(item.get("requirement_id") or "").strip()
    ]
    criteria = [
        str(item)
        for item in checked["objective"].get("success_criteria") or []
        if str(item).strip()
    ]
    prior_messages = {
        _normalize_for_dedup(str(item.get("content") or ""))
        for item in history or []
        if str(item.get("role") or "") == "user"
    }
    probes: list[dict[str, Any]] = []
    skipped: list[str] = []
    for seed in sorted(
        dataset["seeds"],
        key=lambda item: (int(item.get("priority") or 100), item["seed_id"]),
    ):
        categories = {str(item) for item in seed.get("categories") or []}
        transform_id = str(seed.get("transform_id") or "")
        if (
            category not in categories
            and "*" not in categories
        ) or transform_id not in transform_ids:
            continue
        probe_id = f"seed-{_slug(str(seed['seed_id']))}"
        message = str(seed["template"]).format(
            goal=checked["objective"]["goal"]
        )
        if _normalize_for_dedup(message) in prior_messages:
            skipped.append(probe_id)
            continue
        probes.append(
            {
                "probe_id": probe_id,
                "strategy_id": strategy["strategy_id"],
                "transform_id": transform_id,
                "message": message,
                "changed_variable": seed["changed_variable"],
                "expected_signal": seed["expected_signal"],
                "evidence_criteria": criteria[:20]
                or ["Target-origin evidence satisfies the ProofSpec."],
                "proof_requirement_ids": requirement_ids,
                "estimated_cost_units": float(
                    seed.get("estimated_cost_units") or 0.25
                ),
            }
        )
        if len(probes) >= maximum:
            break
    status = "pending" if probes else "completed"
    return BaselineScan.model_validate(
        {
            "schema_version": 1,
            "attack_spec_id": checked["attack_spec_id"],
            "dataset_id": dataset_id,
            "dataset_sha256": dataset_sha256,
            "status": status,
            "probes": probes,
            "completed_probe_ids": [],
            "skipped_probe_ids": skipped[:12],
            "max_probes": maximum,
        }
    ).model_dump(mode="json")


def next_baseline_probe(
    baseline_scan: dict[str, Any] | None,
    committed_turns: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not baseline_scan:
        return None
    scan = BaselineScan.model_validate(baseline_scan).model_dump(mode="json")
    if scan["status"] in {"disabled", "completed"}:
        return None
    completed = {
        str(item)
        for item in scan.get("completed_probe_ids") or []
        if str(item).strip()
    }
    completed.update(
        str(item.get("baseline_probe_id") or "")
        for item in committed_turns
        if isinstance(item, dict)
        and str(item.get("baseline_probe_id") or "").strip()
    )
    skipped = {
        str(item)
        for item in scan.get("skipped_probe_ids") or []
        if str(item).strip()
    }
    return next(
        (
            item
            for item in scan["probes"]
            if item["probe_id"] not in completed
            and item["probe_id"] not in skipped
        ),
        None,
    )


def mark_baseline_probe_completed(
    baseline_scan: dict[str, Any] | None,
    probe_id: str | None,
) -> dict[str, Any] | None:
    if not baseline_scan or not probe_id:
        return baseline_scan
    scan = BaselineScan.model_validate(baseline_scan).model_dump(mode="json")
    known_ids = {str(item["probe_id"]) for item in scan["probes"]}
    if probe_id not in known_ids:
        return scan
    completed = [
        *scan.get("completed_probe_ids", []),
        probe_id,
    ]
    scan["completed_probe_ids"] = list(dict.fromkeys(completed))[:12]
    remaining = next_baseline_probe(scan, [])
    scan["status"] = "running" if remaining is not None else "completed"
    return BaselineScan.model_validate(scan).model_dump(mode="json")


def _load_seed_dataset() -> dict[str, Any]:
    payload = json.loads(SEED_DATASET_PATH.read_text(encoding="utf-8"))
    if int(payload.get("schema_version") or 0) != 1:
        raise ValueError("Unsupported Attack Agent seed dataset schema.")
    seeds = payload.get("seeds")
    if not isinstance(seeds, list) or not seeds:
        raise ValueError("Attack Agent seed dataset contains no seeds.")
    return payload


def _transforms_for_category(category: str) -> list[dict[str, Any]]:
    allowed = ["identity", "structured-output", "context-control"]
    if category in {
        "secret_extraction",
        "prompt_disclosure",
        "policy_disclosure",
        "model_information",
    }:
        allowed.append("base64-output")
    allowed.append("bilingual-output")
    if category in {
        "prompt_disclosure",
        "tool_capability",
        "policy_disclosure",
        "model_information",
    }:
        allowed.append("fragment-coverage")
    return [dict(_TRANSFORMS[item]) for item in allowed]


def _taxonomy_for_category(category: str) -> list[str]:
    mappings = {
        "secret_extraction": ["OWASP-LLM02", "sensitive-information-disclosure"],
        "prompt_disclosure": ["OWASP-LLM07", "system-prompt-leakage"],
        "tool_capability": ["agent-tool-disclosure", "capability-enumeration"],
        "policy_disclosure": ["internal-policy-disclosure"],
        "model_information": ["model-fingerprinting"],
        "retrieval_boundary": ["OWASP-LLM08", "rag-boundary"],
        "authorization": ["OWASP-LLM06", "excessive-agency"],
        "workflow_integrity": ["agent-workflow-integrity"],
        "behavioral": ["behavioral-boundary"],
        "generic": ["adversarial-evaluation"],
    }
    return mappings[category]


def _attack_spec_id(source: dict[str, Any]) -> str:
    canonical = {
        key: value
        for key, value in source.items()
        if key != "attack_spec_id"
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _legacy_attack_spec_id(source: dict[str, Any]) -> str:
    """Reproduce the pre-normalization hash for safe persisted-spec migration."""

    return _attack_spec_id(_integral_floats_as_ints(source))


def _integral_floats_as_ints(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [_integral_floats_as_ints(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _integral_floats_as_ints(item)
            for key, item in value.items()
        }
    return value


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized[:120] or "attack"


def _normalize_space(value: str) -> str:
    return " ".join(str(value or "").split())


def _normalize_for_dedup(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _contains_pattern(value: str, needle: str) -> bool:
    if needle.isascii():
        pattern = r"(?<![a-z0-9_])" + re.escape(needle) + r"(?![a-z0-9_])"
        return re.search(pattern, value) is not None
    return needle in value
