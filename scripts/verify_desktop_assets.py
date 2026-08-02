from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any


BANNED_IMPORTS = {
    "bert_score",
    "cv2",
    "flair",
    "nudenet",
    "onnxruntime",
    "sentence_transformers",
    "spacy",
    "tensorflow",
    "textattack",
    "torch",
    "torchmetrics",
    "torchvision",
    "transformers",
}
SAFE_SECRET_PLACEHOLDERS = {
    "",
    "Use environment variables!",
    "your h2ogpte api key",
    "flageval_judgemodel",
    "ollama",
}
SENSITIVE_KEYS = {"token", "api_key", "apikey", "password", "secret", "authorization"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dataset_manifest(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "id": path.stem,
            "file": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted((root / "datasets").glob("*.json"))
    ]


def imported_top_levels(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    return imports


def walk_sensitive_values(value: Any, location: str = "root") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}"
            normalized = re.sub(r"[^a-z]", "", str(key).lower())
            if normalized in {item.replace("_", "") for item in SENSITIVE_KEYS}:
                if isinstance(child, str) and child not in SAFE_SECRET_PLACEHOLDERS:
                    findings.append(child_location)
            else:
                findings.extend(walk_sensitive_values(child, child_location))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(walk_sensitive_values(child, f"{location}[{index}]"))
    return findings


def verify(source: Path, staged: Path, policy_path: Path, manifest_path: Path) -> None:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    source_manifest = dataset_manifest(source)
    staged_manifest = dataset_manifest(staged)
    expected_count = int(policy["datasetExpectedCount"])
    if len(source_manifest) != expected_count:
        raise RuntimeError(
            f"Source dataset count is {len(source_manifest)}; expected {expected_count}"
        )
    if source_manifest != staged_manifest:
        raise RuntimeError("Staged Moonshot datasets do not exactly match the approved source set")

    for relative in policy["excludedAssets"]:
        if (staged / relative).exists():
            raise RuntimeError(f"Unsupported local-model asset remains: {relative}")
    for name in policy["excludedRecipes"]:
        if (staged / "recipes" / name).exists():
            raise RuntimeError(f"Unsupported local-model recipe remains: {name}")

    available_recipe_ids = {path.stem for path in (staged / "recipes").glob("*.json")}
    for cookbook_path in (staged / "cookbooks").glob("*.json"):
        cookbook = json.loads(cookbook_path.read_text(encoding="utf-8-sig"))
        recipe_ids = cookbook.get("recipes", []) or []
        missing_recipe_ids = sorted(set(recipe_ids) - available_recipe_ids)
        if missing_recipe_ids:
            raise RuntimeError(
                f"Cookbook {cookbook_path.name} references recipes not shipped in the desktop archive: "
                f"{missing_recipe_ids}"
            )
        if not recipe_ids:
            raise RuntimeError(f"Cookbook {cookbook_path.name} has no shippable recipes")

    for json_path in staged.rglob("*.json"):
        with json_path.open("rb") as handle:
            if handle.read(3) == b"\xef\xbb\xbf":
                raise RuntimeError(
                    f"Staged JSON contains a UTF-8 BOM unsupported by Moonshot: "
                    f"{json_path.relative_to(staged)}"
                )

    removed_ids = {Path(item).stem for item in policy["excludedAssets"]}
    for recipe_path in (staged / "recipes").glob("*.json"):
        payload = json.loads(recipe_path.read_text(encoding="utf-8-sig"))
        serialized = json.dumps(payload, ensure_ascii=False)
        referenced = sorted(identifier for identifier in removed_ids if identifier in serialized)
        if referenced:
            raise RuntimeError(
                f"Recipe {recipe_path.name} still references excluded assets: {referenced}"
            )

    for folder in ("connectors", "metrics", "attack-modules"):
        for path in (staged / folder).glob("*.py"):
            blocked = sorted(imported_top_levels(path) & BANNED_IMPORTS)
            if blocked:
                raise RuntimeError(f"{path.relative_to(staged)} imports banned runtime(s): {blocked}")

    for path in (staged / "connectors-endpoints").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        findings = walk_sensitive_values(payload)
        if findings:
            raise RuntimeError(
                f"Connector endpoint {path.name} contains non-placeholder secret fields: {findings}"
            )

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "datasetCount": len(staged_manifest),
                "datasets": staged_manifest,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--staged", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    verify(
        args.source.resolve(),
        args.staged.resolve(),
        args.policy.resolve(),
        args.manifest.resolve(),
    )


if __name__ == "__main__":
    main()
