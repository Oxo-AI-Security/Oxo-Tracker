from __future__ import annotations

import base64
import ctypes
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import yaml

from app.core.paths import DATA_ROOT


SETTINGS_DIR = DATA_ROOT / "settings"
SETTINGS_FILE = SETTINGS_DIR / "app-settings.yaml"
LEGACY_SETTINGS_FILE = SETTINGS_DIR / "app-settings.json"

PROVIDER_CATALOG: dict[str, dict[str, Any]] = {
    "qwen": {
        "label": "Qwen",
        "company": "Alibaba Cloud",
        "description": "Qwen models through the DashScope OpenAI-compatible API.",
        "apiKeyLabel": "DashScope API Key",
        "logo": "/provider-logos/qwen.svg",
        "defaultModel": "qwen3.7-max",
        "defaultBaseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "catalogUrl": "https://help.aliyun.com/en/model-studio/text-generation-model/",
        "catalogCheckedAt": "2026-07-22",
        "latestModels": ["qwen3.7-max", "qwen3.7-plus", "qwen3.6-flash"],
        "models": [
            "qwen3.7-max",
            "qwen3.7-plus",
            "qwen3.6-flash",
            "qwen3.6-plus",
            "qwen3.6-max-preview",
            "qwen3.5-plus",
            "qwen3.5-flash",
            "qwen3.5-397b-a17b",
            "qwen3.5-122b-a10b",
            "qwen3.5-35b-a3b",
            "qwen3.5-27b",
            "qwen3-max",
            "qwen3-235b-a22b",
            "qwen3-32b",
            "qwen3-30b-a3b",
            "qwen3-14b",
            "qwen3-8b",
            "qwen-max",
            "qwen-plus-latest",
            "qwen-plus",
            "qwen-turbo",
            "qwen-long",
        ],
    },
    "kimi": {
        "label": "Kimi",
        "company": "Moonshot AI",
        "description": "Kimi and Moonshot models through the compatible chat API.",
        "apiKeyLabel": "Moonshot API Key",
        "logo": "/provider-logos/kimi.svg",
        "defaultModel": "kimi-k3",
        "defaultBaseUrl": "https://api.moonshot.cn/v1",
        "catalogUrl": "https://platform.kimi.com/docs/api/models-overview",
        "catalogCheckedAt": "2026-07-22",
        "latestModels": ["kimi-k3", "kimi-k2.7-code", "kimi-k2.6"],
        "models": [
            "kimi-k3",
            "kimi-k2.7-code",
            "kimi-k2.7-code-highspeed",
            "kimi-k2.6",
            "kimi-k2.5",
            "moonshot-v1-128k-vision-preview",
            "moonshot-v1-128k",
            "moonshot-v1-32k",
            "moonshot-v1-8k",
        ],
    },
    "deepseek": {
        "label": "DeepSeek",
        "company": "DeepSeek AI",
        "description": "DeepSeek models through the OpenAI-compatible API.",
        "apiKeyLabel": "DeepSeek API Key",
        "logo": "/provider-logos/deepseek.svg",
        "defaultModel": "deepseek-v4-flash",
        "defaultBaseUrl": "https://api.deepseek.com",
        "catalogUrl": "https://api-docs.deepseek.com/quick_start/pricing/",
        "catalogCheckedAt": "2026-08-01",
        "latestModels": ["deepseek-v4-flash", "deepseek-v4-pro"],
        "models": [
            "deepseek-v4-flash",
            "deepseek-v4-pro",
        ],
    },
    "openai": {
        "label": "ChatGPT",
        "company": "OpenAI",
        "description": "GPT models through the OpenAI API.",
        "apiKeyLabel": "OpenAI API Key",
        "logo": "/provider-logos/openai.svg",
        "defaultModel": "gpt-5.6-sol",
        "defaultBaseUrl": "https://api.openai.com/v1",
        "catalogUrl": "https://developers.openai.com/api/docs/models",
        "catalogCheckedAt": "2026-07-22",
        "latestModels": ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"],
        "models": [
            "gpt-5.6-sol",
            "gpt-5.6",
            "gpt-5.6-terra",
            "gpt-5.6-luna",
            "gpt-5.5",
            "gpt-5.4",
            "gpt-5.4-pro",
            "gpt-5.4-mini",
            "gpt-5.4-nano",
            "gpt-5.2",
            "gpt-5.1",
            "gpt-5",
            "gpt-5-mini",
            "gpt-5-nano",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "gpt-4o",
            "gpt-4o-mini",
        ],
    },
    "gemini": {
        "label": "Gemini",
        "company": "Google",
        "description": "Gemini models through Google's OpenAI-compatible endpoint.",
        "apiKeyLabel": "Gemini API Key",
        "logo": "/provider-logos/gemini.svg",
        "defaultModel": "gemini-3.6-flash",
        "defaultBaseUrl": "https://generativelanguage.googleapis.com/v1beta/openai",
        "catalogUrl": "https://ai.google.dev/gemini-api/docs/models",
        "catalogCheckedAt": "2026-07-22",
        "latestModels": ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"],
        "models": [
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-pro-preview",
            "gemini-3.1-flash-lite",
            "gemini-3-flash-preview",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
        ],
    },
    "azure_openai": {
        "label": "Azure OpenAI",
        "company": "Microsoft Azure",
        "description": "Your Azure-hosted OpenAI deployment and endpoint.",
        "apiKeyLabel": "Azure OpenAI API Key",
        "logo": "/provider-logos/azure-openai.svg",
        "defaultModel": "gpt-5.6-sol",
        "defaultBaseUrl": "https://YOUR-RESOURCE.openai.azure.com/openai/v1",
        "catalogUrl": "https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure",
        "catalogCheckedAt": "2026-07-22",
        "latestModels": ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"],
        "models": [
            "gpt-chat-latest",
            "gpt-5.6-sol",
            "gpt-5.6-terra",
            "gpt-5.6-luna",
            "gpt-5.5",
            "gpt-5.4",
            "gpt-5.4-pro",
            "gpt-5.4-mini",
            "gpt-5.4-nano",
            "gpt-5.3-chat",
            "gpt-5.3-codex",
            "gpt-5.2",
            "gpt-5.2-chat",
            "gpt-5.2-codex",
            "gpt-5.1",
            "gpt-5",
            "gpt-5-mini",
            "gpt-5-nano",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4o",
            "gpt-4o-mini",
        ],
    },
}


def _default_settings() -> dict[str, Any]:
    return {
        "theme": "light",
        "locale": "en-US",
        "ai": {
            "activeProvider": "qwen",
            "providers": {
                provider_id: {
                    "model": provider["defaultModel"],
                    "baseUrl": provider["defaultBaseUrl"],
                    "sealedApiKey": "",
                }
                for provider_id, provider in PROVIDER_CATALOG.items()
            },
        },
    }


class SecretProtectionError(RuntimeError):
    pass


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _windows_dpapi(data: bytes, *, decrypt: bool) -> bytes:
    buffer = ctypes.create_string_buffer(data)
    source = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    result = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if decrypt:
        ok = crypt32.CryptUnprotectData(
            ctypes.byref(source), None, None, None, None, 0, ctypes.byref(result)
        )
    else:
        ok = crypt32.CryptProtectData(
            ctypes.byref(source), "Oxo Tracker", None, None, None, 0, ctypes.byref(result)
        )
    if not ok:
        raise SecretProtectionError(f"Windows DPAPI failed with error {ctypes.get_last_error()}")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree(result.pbData)


def protect_secret(value: str) -> str:
    if os.name != "nt":
        raise SecretProtectionError("Secure API key persistence requires Windows DPAPI")
    sealed = _windows_dpapi(value.encode("utf-8"), decrypt=False)
    return "dpapi:" + base64.urlsafe_b64encode(sealed).decode("ascii")


def unprotect_secret(value: str) -> str:
    try:
        scheme, payload = value.split(":", 1)
        if scheme != "dpapi" or os.name != "nt":
            raise SecretProtectionError(f"Unsupported secret protection scheme: {scheme}")
        raw = _windows_dpapi(base64.urlsafe_b64decode(payload.encode("ascii")), decrypt=True)
        return raw.decode("utf-8")
    except SecretProtectionError:
        raise
    except Exception as error:
        raise SecretProtectionError("Stored API key could not be decrypted") from error


class SettingsStore:
    def __init__(
        self,
        path: Path = SETTINGS_FILE,
        *,
        legacy_path: Path | None = None,
        protect: Callable[[str], str] = protect_secret,
        unprotect: Callable[[str], str] = unprotect_secret,
    ) -> None:
        self.path = path
        self.legacy_path = legacy_path if legacy_path is not None else (
            LEGACY_SETTINGS_FILE if path == SETTINGS_FILE else path.with_suffix(".json")
        )
        self._protect = protect
        self._unprotect = unprotect
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            legacy = self._read_legacy()
            settings = self._normalize(legacy)
            self._write(settings)
            return settings
        try:
            loaded = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            loaded = {}
        return self._normalize(loaded if isinstance(loaded, dict) else {})

    def _read_legacy(self) -> dict[str, Any]:
        if not self.legacy_path or not self.legacy_path.exists():
            return {}
        try:
            loaded = json.loads(self.legacy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return loaded if isinstance(loaded, dict) else {}

    def _normalize(self, settings: dict[str, Any]) -> dict[str, Any]:
        normalized = _default_settings()
        if settings.get("theme") in {"light", "dark"}:
            normalized["theme"] = settings["theme"]
        if settings.get("locale") in {"en-US", "zh-CN"}:
            normalized["locale"] = settings["locale"]

        source_ai = settings.get("ai") if isinstance(settings.get("ai"), dict) else {}
        active = source_ai.get("activeProvider")
        if active in PROVIDER_CATALOG:
            normalized["ai"]["activeProvider"] = active

        source_providers = source_ai.get("providers")
        if not isinstance(source_providers, dict):
            return normalized
        for provider_id in PROVIDER_CATALOG:
            source = source_providers.get(provider_id)
            if not isinstance(source, dict):
                continue
            target = normalized["ai"]["providers"][provider_id]
            if str(source.get("model") or "").strip():
                target["model"] = str(source["model"]).strip()
            if str(source.get("baseUrl") or "").strip():
                target["baseUrl"] = str(source["baseUrl"]).strip().rstrip("/")
            if str(source.get("sealedApiKey") or "").strip():
                target["sealedApiKey"] = str(source["sealedApiKey"]).strip()
        return normalized

    def _write(self, settings: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            yaml.safe_dump(settings, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        temporary.replace(self.path)

    def get(self) -> dict[str, Any]:
        return self._public(self._read())

    def _public(self, settings: dict[str, Any]) -> dict[str, Any]:
        public = deepcopy(settings)
        for provider in public["ai"]["providers"].values():
            sealed = provider.pop("sealedApiKey", "")
            provider["apiKeyConfigured"] = bool(sealed)
            provider["apiKeyMasked"] = ""
            if sealed:
                try:
                    provider["apiKeyMasked"] = self._mask_secret(self._unprotect(sealed))
                except (OSError, ValueError, SecretProtectionError):
                    provider["apiKeyMasked"] = "••••••••"
        public["ai"]["catalog"] = deepcopy(PROVIDER_CATALOG)
        return public

    @staticmethod
    def _mask_secret(value: str) -> str:
        if not value:
            return ""
        if len(value) <= 4:
            return "•" * len(value)
        if len(value) <= 10:
            return f"{value[:2]}••••••{value[-2:]}"
        return f"{value[:4]}••••••••{value[-4:]}"

    @staticmethod
    def _validate_base_url(value: str) -> str:
        cleaned = value.strip().rstrip("/")
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Base URL must be a valid HTTP or HTTPS URL")
        return cleaned

    def save(self, settings: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize(settings)
        self._write(normalized)
        return self._public(normalized)

    def update(self, changes: dict[str, Any]) -> dict[str, Any]:
        current = self._read()
        if "theme" in changes:
            if changes["theme"] not in {"light", "dark"}:
                raise ValueError("Theme must be light or dark")
            current["theme"] = changes["theme"]
        if "locale" in changes:
            if changes["locale"] not in {"en-US", "zh-CN"}:
                raise ValueError("Locale must be en-US or zh-CN")
            current["locale"] = changes["locale"]

        ai_changes = changes.get("ai")
        if isinstance(ai_changes, dict):
            active = str(ai_changes.get("activeProvider") or "").strip()
            if active:
                if active not in PROVIDER_CATALOG:
                    raise ValueError("Unsupported AI provider")
                current["ai"]["activeProvider"] = active

            provider_id = str(ai_changes.get("provider") or active or "").strip()
            config = ai_changes.get("config")
            if config is not None:
                if provider_id not in PROVIDER_CATALOG or not isinstance(config, dict):
                    raise ValueError("A valid AI provider configuration is required")
                target = current["ai"]["providers"][provider_id]
                model = str(config.get("model") or "").strip()
                base_url = str(config.get("baseUrl") or "").strip()
                if not model:
                    raise ValueError("Model is required")
                if not base_url:
                    raise ValueError("Base URL is required")
                target["model"] = model
                target["baseUrl"] = self._validate_base_url(base_url)
                api_key = str(config.get("apiKey") or "").strip()
                if api_key:
                    target["sealedApiKey"] = self._protect(api_key)

        self._write(current)
        return self._public(current)

    def get_active_ai_settings(self) -> dict[str, str]:
        """Return the one active model configuration for trusted backend consumers."""
        settings = self._read()
        provider_id = settings["ai"]["activeProvider"]
        return self.get_ai_settings(provider_id, settings=settings)

    def get_ai_settings(
        self,
        provider_id: str,
        *,
        model: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """Resolve one configured provider for a trusted run-scoped consumer."""
        if provider_id not in PROVIDER_CATALOG:
            raise ValueError("Unsupported AI provider")
        current = settings or self._read()
        provider = current["ai"]["providers"][provider_id]
        resolved_model = str(model or provider["model"]).strip()
        if not resolved_model:
            raise ValueError("Model is required")
        api_key = self.get_provider_api_key(provider_id, settings=current)
        if not api_key:
            raise ValueError(
                f"No API key is configured for provider {provider_id}"
            )
        return {
            "provider": provider_id,
            "model": resolved_model,
            "base_url": str(provider["baseUrl"]),
            "api_key": api_key,
        }

    def get_provider_api_key(
        self, provider_id: str, *, settings: dict[str, Any] | None = None
    ) -> str:
        """Decrypt one provider credential for an explicit trusted consumer action."""
        if provider_id not in PROVIDER_CATALOG:
            raise ValueError("Unsupported AI provider")
        current = settings or self._read()
        sealed = str(current["ai"]["providers"][provider_id].get("sealedApiKey") or "")
        return self._unprotect(sealed) if sealed else ""
