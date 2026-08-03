from pathlib import Path

import pytest

from app.services.settings_store import SettingsStore


def make_store(path: Path) -> SettingsStore:
    return SettingsStore(
        path,
        protect=lambda value: f"sealed:{value}",
        unprotect=lambda value: value.removeprefix("sealed:"),
    )


def test_ui_scale_defaults_to_100_for_new_and_legacy_settings(tmp_path: Path) -> None:
    new_store = make_store(tmp_path / "new-settings.yaml")
    legacy_path = tmp_path / "legacy-settings.yaml"
    legacy_path.write_text("theme: dark\n", encoding="utf-8")

    assert new_store.get()["uiScale"] == 100
    assert make_store(legacy_path).get()["uiScale"] == 100


def test_supported_ui_scale_is_persisted(tmp_path: Path) -> None:
    settings_path = tmp_path / "app-settings.yaml"
    store = make_store(settings_path)

    assert store.update({"uiScale": 80})["uiScale"] == 80
    assert make_store(settings_path).get()["uiScale"] == 80


@pytest.mark.parametrize("value", [75, 120, True, "80"])
def test_unsupported_ui_scale_is_rejected(tmp_path: Path, value: object) -> None:
    store = make_store(tmp_path / "app-settings.yaml")

    with pytest.raises(ValueError, match="UI scale must be one of"):
        store.update({"uiScale": value})
