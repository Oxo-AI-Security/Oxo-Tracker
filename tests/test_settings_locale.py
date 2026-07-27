from pathlib import Path

import pytest

from app.services.settings_store import SettingsStore


def make_store(path: Path) -> SettingsStore:
    return SettingsStore(
        path,
        protect=lambda value: f"sealed:{value}",
        unprotect=lambda value: value.removeprefix("sealed:"),
    )


def test_locale_defaults_to_english_for_new_settings(tmp_path: Path) -> None:
    store = make_store(tmp_path / "app-settings.yaml")

    assert store.get()["locale"] == "en-US"


def test_locale_defaults_to_english_for_legacy_settings(tmp_path: Path) -> None:
    settings_path = tmp_path / "app-settings.yaml"
    settings_path.write_text("theme: dark\n", encoding="utf-8")

    assert make_store(settings_path).get()["locale"] == "en-US"


def test_supported_locale_is_persisted(tmp_path: Path) -> None:
    settings_path = tmp_path / "app-settings.yaml"
    store = make_store(settings_path)

    assert store.update({"locale": "zh-CN"})["locale"] == "zh-CN"
    assert make_store(settings_path).get()["locale"] == "zh-CN"


def test_unsupported_locale_is_rejected(tmp_path: Path) -> None:
    store = make_store(tmp_path / "app-settings.yaml")

    with pytest.raises(ValueError, match="Locale must be en-US or zh-CN"):
        store.update({"locale": "fr-FR"})
