from __future__ import annotations

import pytest

from app.schemas.benchmark import BenchmarkRecipeRequest
from app.services.benchmark_service import BenchmarkService


class _SettingsStore:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def get_ai_settings(
        self,
        provider_id: str,
        *,
        model: str | None = None,
    ) -> dict[str, str]:
        self.calls.append((provider_id, model))
        return {
            "provider": provider_id,
            "model": str(model),
            "base_url": "https://api.example.test/v1",
            "api_key": "stored-secret",
        }


class _MoonshotApiService:
    def __init__(self) -> None:
        self.updated: list[tuple[str, dict]] = []
        self.created: list[dict] = []

    def get_all_endpoint(self) -> list[dict]:
        return [
            {
                "id": "judge-one",
                "name": "Judge One",
                "connector_type": "openai-connector",
                "uri": "",
                "token": "",
                "model": "old-model",
                "max_calls_per_second": 2,
                "max_concurrency": 3,
                "params": {
                    "timeout": 120,
                    "system_prompt": "Keep the evaluator rubric.",
                },
            },
            {
                "id": "judge-two",
                "name": "Judge Two",
                "connector_type": "openai-connector",
                "uri": "https://old.example.test/v1",
                "token": "old-secret",
                "model": "old-model",
                "max_calls_per_second": 4,
                "max_concurrency": 2,
                "params": {
                    "timeout": 90,
                    "system_prompt": "Keep the second evaluator rubric.",
                },
            },
        ]

    def update_endpoint(self, endpoint_id: str, payload: dict) -> bool:
        self.updated.append((endpoint_id, payload))
        return True

    def create_endpoint(self, payload: dict) -> str:
        self.created.append(payload)
        return payload["name"]


def _request(**overrides: object) -> BenchmarkRecipeRequest:
    payload: dict[str, object] = {
        "run_name": "selection-test",
        "endpoints": ["target"],
        "recipes": ["recipe"],
        "cookbooks": ["cookbook"],
        "evaluator_provider": "qwen",
        "evaluator_model": "qwen-plus",
        "evaluator_endpoints": ["judge-one"],
    }
    payload.update(overrides)
    return BenchmarkRecipeRequest(**payload)


def test_configure_evaluator_endpoints_reuses_saved_provider_secret() -> None:
    settings = _SettingsStore()
    moonshot_api = _MoonshotApiService()
    service = BenchmarkService(
        moonshot_client=object(),
        job_store=object(),
        settings_store=settings,
        moonshot_api_service=moonshot_api,
    )

    service._configure_evaluator_endpoints(_request())

    assert settings.calls == [("qwen", "qwen-plus")]
    assert len(moonshot_api.updated) == 1
    endpoint_id, payload = moonshot_api.updated[0]
    assert endpoint_id == "judge-one"
    assert payload["uri"] == "https://api.example.test/v1"
    assert payload["token"] == "stored-secret"
    assert payload["model"] == "qwen-plus"
    assert payload["max_calls_per_second"] == 2
    assert payload["max_concurrency"] == 3
    assert payload["params"]["system_prompt"] == "Keep the evaluator rubric."


def test_configure_evaluator_endpoints_applies_one_model_to_every_required_evaluator() -> None:
    settings = _SettingsStore()
    moonshot_api = _MoonshotApiService()
    service = BenchmarkService(
        moonshot_client=object(),
        job_store=object(),
        settings_store=settings,
        moonshot_api_service=moonshot_api,
    )

    service._configure_evaluator_endpoints(
        _request(
            evaluator_endpoints=[
                "judge-one",
                "judge-two",
                "judge-missing",
                "judge-one",
            ]
        )
    )

    assert settings.calls == [("qwen", "qwen-plus")]
    assert [endpoint_id for endpoint_id, _ in moonshot_api.updated] == [
        "judge-one",
        "judge-two",
    ]
    assert len(moonshot_api.created) == 1
    configured_payloads = [
        *(payload for _, payload in moonshot_api.updated),
        *moonshot_api.created,
    ]
    assert {payload["model"] for payload in configured_payloads} == {"qwen-plus"}
    assert {payload["uri"] for payload in configured_payloads} == {
        "https://api.example.test/v1"
    }
    assert {payload["token"] for payload in configured_payloads} == {
        "stored-secret"
    }
    assert moonshot_api.updated[1][1]["params"]["system_prompt"] == (
        "Keep the second evaluator rubric."
    )
    assert moonshot_api.created[0]["name"] == "judge-missing"


def test_evaluator_selection_requires_provider_and_model() -> None:
    service = BenchmarkService(
        moonshot_client=object(),
        job_store=object(),
        settings_store=_SettingsStore(),
        moonshot_api_service=_MoonshotApiService(),
    )

    with pytest.raises(ValueError, match="provider and model"):
        service._resolve_evaluator_settings(
            _request(evaluator_provider=None, evaluator_model=None)
        )
