import base64
import json

import yaml

from app.services.settings_store import SettingsStore


def protect(value: str) -> str:
    return "test:" + base64.b64encode(value.encode("utf-8")).decode("ascii")


def unprotect(value: str) -> str:
    return base64.b64decode(value.split(":", 1)[1]).decode("utf-8")


def test_settings_migrate_legacy_json_to_yaml(tmp_path):
    yaml_path = tmp_path / "app-settings.yaml"
    legacy_path = tmp_path / "app-settings.json"
    legacy_path.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")

    store = SettingsStore(
        yaml_path, legacy_path=legacy_path, protect=protect, unprotect=unprotect
    )
    settings = store.get()

    assert settings["theme"] == "dark"
    assert settings["ai"]["activeProvider"] == "qwen"
    assert yaml_path.exists()


def test_provider_catalog_includes_current_official_models(tmp_path):
    settings = SettingsStore(
        tmp_path / "app-settings.yaml", protect=protect, unprotect=unprotect
    ).get()
    catalog = settings["ai"]["catalog"]

    assert "qwen3.7-max" in catalog["qwen"]["models"]
    assert "kimi-k3" in catalog["kimi"]["models"]
    assert "gpt-5.6-sol" in catalog["openai"]["models"]
    assert "gemini-3.6-flash" in catalog["gemini"]["models"]
    assert "gpt-5.6-sol" in catalog["azure_openai"]["models"]
    assert all(item["catalogUrl"].startswith("https://") for item in catalog.values())


def test_only_one_provider_is_active_and_secret_is_never_public(tmp_path):
    path = tmp_path / "app-settings.yaml"
    store = SettingsStore(path, protect=protect, unprotect=unprotect)

    public = store.update(
        {
            "ai": {
                "activeProvider": "kimi",
                "provider": "kimi",
                "config": {
                    "model": "kimi-k2.5",
                    "baseUrl": "https://api.moonshot.cn/v1/",
                    "apiKey": "sk-local-secret",
                },
            }
        }
    )

    assert public["ai"]["activeProvider"] == "kimi"
    assert public["ai"]["providers"]["kimi"]["apiKeyConfigured"] is True
    assert public["ai"]["providers"]["kimi"]["apiKeyMasked"] == "sk-l••••••••cret"
    assert "sk-local-secret" not in json.dumps(public)
    assert "sk-local-secret" not in path.read_text(encoding="utf-8")
    assert "sealedApiKey" not in json.dumps(public)

    private = store.get_active_ai_settings()
    assert private == {
        "provider": "kimi",
        "model": "kimi-k2.5",
        "base_url": "https://api.moonshot.cn/v1",
        "api_key": "sk-local-secret",
    }
    assert store.get_provider_api_key("kimi") == "sk-local-secret"


def test_run_scoped_provider_and_model_override_does_not_mutate_active_settings(
    tmp_path,
):
    path = tmp_path / "app-settings.yaml"
    store = SettingsStore(path, protect=protect, unprotect=unprotect)
    store.update(
        {
            "ai": {
                "activeProvider": "openai",
                "provider": "openai",
                "config": {
                    "model": "gpt-5.6-sol",
                    "baseUrl": "https://api.openai.com/v1",
                    "apiKey": "sk-run-secret",
                },
            }
        }
    )

    resolved = store.get_ai_settings("openai", model="gpt-5.6-terra")

    assert resolved == {
        "provider": "openai",
        "model": "gpt-5.6-terra",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-run-secret",
    }
    assert store.get()["ai"]["providers"]["openai"]["model"] == "gpt-5.6-sol"


def test_blank_api_key_keeps_saved_credential(tmp_path):
    path = tmp_path / "app-settings.yaml"
    store = SettingsStore(path, protect=protect, unprotect=unprotect)
    store.update(
        {
            "ai": {
                "activeProvider": "qwen",
                "provider": "qwen",
                "config": {
                    "model": "qwen-max",
                    "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "apiKey": "first-secret",
                },
            }
        }
    )

    store.update(
        {
            "ai": {
                "activeProvider": "qwen",
                "provider": "qwen",
                "config": {
                    "model": "qwen-plus",
                    "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "apiKey": "",
                },
            }
        }
    )

    assert store.get_active_ai_settings()["api_key"] == "first-secret"
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["ai"]["activeProvider"] == "qwen"
