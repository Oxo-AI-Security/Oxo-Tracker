from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
from datetime import UTC, datetime
from pathlib import Path


def safe_spdx_id(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9.-]+", "-", value).strip("-.")
    return normalized or "unknown"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_records() -> list[dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for distribution in importlib.metadata.distributions():
        name = str(distribution.metadata.get("Name") or "unknown")
        key = name.casefold()
        license_value = str(
            distribution.metadata.get("License-Expression")
            or distribution.metadata.get("License")
            or "NOASSERTION"
        ).strip()
        if not license_value or "\n" in license_value or len(license_value) > 200:
            license_value = "NOASSERTION"
        records[key] = {
            "name": name,
            "version": distribution.version,
            "license": license_value,
            "homepage": str(
                distribution.metadata.get("Home-page")
                or distribution.metadata.get("Project-URL")
                or ""
            ),
        }
    return [records[key] for key in sorted(records)]


def generate(version: str, dataset_manifest: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    packages = package_records()
    datasets = json.loads(dataset_manifest.read_text(encoding="utf-8"))["datasets"]

    notice_lines = [
        "Oxo Tracker Third-Party Notices",
        f"Release: {version}",
        "",
        "Python runtime packages",
        "=======================",
    ]
    for package in packages:
        notice_lines.append(
            f"{package['name']} {package['version']} | License: {package['license']}"
        )
        if package["homepage"]:
            notice_lines.append(f"  {package['homepage']}")
    notice_lines.extend(
        [
            "",
            "Moonshot datasets",
            "=================",
            "Dataset hashes are recorded in dataset-manifest.json. Dataset-specific",
            "license and attribution metadata remains embedded in each dataset JSON file.",
            "A legal redistribution review is still required before public release.",
        ]
    )
    (output / "THIRD-PARTY-NOTICES.txt").write_text(
        "\n".join(notice_lines) + "\n",
        encoding="utf-8",
    )

    namespace = f"https://github.com/Oxo-AI-Security/Oxo-Tracker-Releases/spdx/{version}"
    spdx_packages = [
        {
            "SPDXID": f"SPDXRef-Package-{safe_spdx_id(item['name'])}",
            "name": item["name"],
            "versionInfo": item["version"],
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": "NOASSERTION",
            "copyrightText": "NOASSERTION",
        }
        for item in packages
    ]
    spdx_files = [
        {
            "SPDXID": f"SPDXRef-Dataset-{safe_spdx_id(item['id'])}",
            "fileName": f"datasets/{item['file']}",
            "checksums": [{"algorithm": "SHA256", "checksumValue": item["sha256"]}],
            "licenseConcluded": "NOASSERTION",
            "copyrightText": "NOASSERTION",
        }
        for item in datasets
    ]
    document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"Oxo-Tracker-{version}",
        "documentNamespace": namespace,
        "creationInfo": {
            "created": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "creators": ["Tool: Oxo Tracker local release script"],
        },
        "packages": spdx_packages,
        "files": spdx_files,
    }
    (output / "sbom.spdx.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--dataset-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    generate(args.version, args.dataset_manifest, args.output)


if __name__ == "__main__":
    main()
