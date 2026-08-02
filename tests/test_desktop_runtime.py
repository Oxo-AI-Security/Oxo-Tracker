from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.paths import AppPaths, SOURCE_ROOT
from app.main import create_app


def test_app_paths_keep_existing_development_layout(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "OXO_DESKTOP_MODE",
        "OXO_RESOURCE_ROOT",
        "OXO_APP_HOME",
        "OXO_DATA_ROOT",
        "OXO_MOONSHOT_DATA_ROOT",
    ):
        monkeypatch.delenv(name, raising=False)

    paths = AppPaths.from_environment()

    assert paths.desktop_mode is False
    assert paths.source_root == SOURCE_ROOT.resolve()
    assert paths.data_root == (SOURCE_ROOT / "data").resolve()
    assert paths.moonshot_data_root == (SOURCE_ROOT / "data" / "moonshot-data").resolve()


def test_desktop_assets_extract_once_and_preserve_user_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    resource_root = tmp_path / "resources"
    app_home = tmp_path / "user" / "Oxo Tracker"
    resource_root.mkdir()
    with zipfile.ZipFile(resource_root / "moonshot-data.zip", "w") as archive:
        archive.writestr("datasets/example.json", '{"name":"bundled"}')
        archive.writestr("recipes/example.json", '{"name":"recipe"}')

    monkeypatch.setenv("OXO_DESKTOP_MODE", "1")
    monkeypatch.setenv("OXO_RESOURCE_ROOT", str(resource_root))
    monkeypatch.setenv("OXO_APP_HOME", str(app_home))
    paths = AppPaths.from_environment()
    paths.prepare_desktop_assets("1.0.0")

    dataset = paths.moonshot_data_root / "datasets" / "example.json"
    assert dataset.read_text(encoding="utf-8") == '{"name":"bundled"}'
    dataset.write_text('{"name":"user-edit"}', encoding="utf-8")
    paths.prepare_desktop_assets("1.0.1")
    assert dataset.read_text(encoding="utf-8") == '{"name":"user-edit"}'


def test_desktop_asset_upgrade_repairs_old_json_without_losing_user_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    resource_root = tmp_path / "resources"
    app_home = tmp_path / "user" / "Oxo Tracker"
    resource_root.mkdir()
    with zipfile.ZipFile(resource_root / "moonshot-data.zip", "w") as archive:
        archive.writestr("recipes/supported.json", '{"name":"supported"}')

    moonshot_root = app_home / "data" / "moonshot-data"
    endpoint_path = moonshot_root / "connectors-endpoints" / "user-endpoint.json"
    endpoint_path.parent.mkdir(parents=True)
    endpoint_path.write_bytes(b"\xef\xbb\xbf" + b'{"id":"user","token":"preserved"}')
    cookbook_path = moonshot_root / "cookbooks" / "user-cookbook.json"
    cookbook_path.parent.mkdir()
    cookbook_path.write_text(
        '{"recipes":["supported","challenging-toxicity-prompts-completion"]}',
        encoding="utf-8",
    )
    marker_path = moonshot_root / ".oxo-desktop-assets.json"
    marker_path.write_text('{"assetVersion":"0.2.0"}', encoding="utf-8")

    monkeypatch.setenv("OXO_DESKTOP_MODE", "1")
    monkeypatch.setenv("OXO_RESOURCE_ROOT", str(resource_root))
    monkeypatch.setenv("OXO_APP_HOME", str(app_home))
    paths = AppPaths.from_environment()
    paths.prepare_desktop_assets("0.2.1")

    assert not endpoint_path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert endpoint_path.read_text(encoding="utf-8") == '{"id":"user","token":"preserved"}'
    assert cookbook_path.read_text(encoding="utf-8").endswith("\n")
    assert json.loads(cookbook_path.read_text(encoding="utf-8"))["recipes"] == ["supported"]
    assert json.loads(marker_path.read_text(encoding="utf-8"))["assetVersion"] == "0.2.1"


def test_desktop_asset_archive_rejects_path_traversal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    resource_root = tmp_path / "resources"
    app_home = tmp_path / "user"
    resource_root.mkdir()
    with zipfile.ZipFile(resource_root / "moonshot-data.zip", "w") as archive:
        archive.writestr("../escape.txt", "unsafe")
    monkeypatch.setenv("OXO_DESKTOP_MODE", "1")
    monkeypatch.setenv("OXO_RESOURCE_ROOT", str(resource_root))
    monkeypatch.setenv("OXO_APP_HOME", str(app_home))

    with pytest.raises(ValueError, match="Unsafe Moonshot archive member"):
        AppPaths.from_environment().prepare_desktop_assets("1.0.0")
    assert not (tmp_path / "escape.txt").exists()


def test_desktop_api_requires_session_token_and_echoes_health_challenge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OXO_DESKTOP_TOKEN", "expected-session-token")
    with TestClient(create_app()) as client:
        denied = client.get(
            "/health?challenge=nonce",
            headers={"Host": "127.0.0.1"},
        )
        allowed = client.get(
            "/health?challenge=nonce",
            headers={
                "Host": "127.0.0.1",
                "X-Oxo-Desktop-Token": "expected-session-token",
            },
        )

    assert denied.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json() == {"status": "ok", "challenge": "nonce"}


def test_desktop_api_rejects_untrusted_browser_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OXO_DESKTOP_TOKEN", "expected-session-token")
    with TestClient(create_app()) as client:
        response = client.get(
            "/health",
            headers={
                "Host": "127.0.0.1",
                "Origin": "https://attacker.example",
                "X-Oxo-Desktop-Token": "expected-session-token",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid desktop API origin"
