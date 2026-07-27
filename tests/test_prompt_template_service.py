import pytest

from app.services.moonshot_api_service import MoonshotApiService


class _PromptTemplateAdapter:
    def __init__(self) -> None:
        self.updated: tuple[str, dict] | None = None

    def update_prompt_template_record(self, template_id: str, payload: dict) -> bool:
        self.updated = (template_id, payload)
        return True


def test_update_prompt_template_preserves_id_and_normalizes_fields() -> None:
    adapter = _PromptTemplateAdapter()
    service = MoonshotApiService(adapter=adapter)  # type: ignore[arg-type]

    result = service.update_prompt_template_record(
        "Oxo-safety-wrapper",
        {
            "name": "  Safety wrapper  ",
            "description": "  Updated description  ",
            "template": "  Before {{ prompt }} after  ",
        },
    )

    assert result is True
    assert adapter.updated == (
        "Oxo-safety-wrapper",
        {
            "name": "Safety wrapper",
            "description": "Updated description",
            "template": "Before {{ prompt }} after",
        },
    )


def test_update_prompt_template_rejects_builtin_template() -> None:
    service = MoonshotApiService(adapter=_PromptTemplateAdapter())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Only Oxo prompt templates can be edited"):
        service.update_prompt_template_record(
            "built-in-template",
            {"name": "Built in", "template": "{{ prompt }}"},
        )


def test_update_prompt_template_requires_prompt_block() -> None:
    service = MoonshotApiService(adapter=_PromptTemplateAdapter())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="must include"):
        service.update_prompt_template_record(
            "Oxo-safety-wrapper",
            {"name": "Safety wrapper", "template": "No prompt block"},
        )
