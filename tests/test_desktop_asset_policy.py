from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from app.core.paths import MISPACKAGED_V0_2_1_ASSET_SHA256


PROJECT_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = PROJECT_ROOT / "desktop" / "asset-policy.json"
VERIFIER_PATH = PROJECT_ROOT / "scripts" / "verify_desktop_assets.py"
EXPECTED_USER_ASSETS = {
    "connectors-endpoints/chat.json",
    "connectors-endpoints/quinn-test.json",
    "connectors-endpoints/test-sse.json",
    "prompt-templates/Oxo-quinn-test.json",
    "prompt-templates/Oxo-quinn-test2.json",
    "prompt-templates/Oxo-zi-fu-jian-ge-rao-guo.json",
}


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_desktop_assets", VERIFIER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_personal_test_assets_are_explicitly_excluded() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    assert set(policy["excludedUserAssets"]) == EXPECTED_USER_ASSETS
    assert set(MISPACKAGED_V0_2_1_ASSET_SHA256) == EXPECTED_USER_ASSETS


@pytest.mark.parametrize("relative_path", sorted(EXPECTED_USER_ASSETS))
def test_release_verifier_rejects_personal_asset(
    tmp_path: Path, relative_path: str
) -> None:
    staged = tmp_path / "moonshot-data"
    personal_asset = staged / relative_path
    personal_asset.parent.mkdir(parents=True, exist_ok=True)
    personal_asset.write_text("{}", encoding="utf-8")

    verifier = load_verifier()
    with pytest.raises(RuntimeError, match="Excluded user asset remains"):
        verifier.assert_excluded_paths_absent(staged, [relative_path], "user asset")
