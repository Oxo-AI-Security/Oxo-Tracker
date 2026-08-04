import base64

import pytest

from app.integrations.moonshot.api_adapter import MoonshotApiAdapter


@pytest.fixture
def adapter() -> MoonshotApiAdapter:
    return object.__new__(MoonshotApiAdapter)


@pytest.mark.parametrize(
    "module_id",
    [
        "charswap_attack",
        "colloquial_wordswap_attack",
        "homoglyph_attack",
        "homoglyph_v2_attack",
        "insert_punctuation_attack",
        "job_role_generator",
        "malicious_question_generator",
        "payload_mask_attack",
        "sample_attack_module",
        "sg_sentence_generator",
        "textbugger_attack",
        "textfooler_attack",
        "toxic_sentence_generator",
        "violent_durian",
        "base64_attack",
    ],
)
def test_supported_attack_modules_transform_the_prompt(adapter: MoonshotApiAdapter, module_id: str):
    prompt = "Please explain robust prompt handling with several English words"

    assert adapter._apply_attack_preview(prompt, module_id) != prompt


def test_base64_attack_encodes_utf8(adapter: MoonshotApiAdapter):
    prompt = "中文 prompt 🚀"

    encoded = adapter._apply_attack_preview(prompt, "base64_attack")

    assert base64.b64decode(encoded).decode("utf-8") == prompt


def test_homoglyph_attack_uses_lookalike_unicode(adapter: MoonshotApiAdapter):
    transformed = adapter._apply_attack_preview("Please compare access", "homoglyph_attack")

    assert transformed != "Please compare access"
    assert "а" in transformed
    assert ord("а") == 0x0430


def test_textbugger_is_not_a_noop(adapter: MoonshotApiAdapter):
    prompt = "Please explain several robust English phrases"

    transformed = adapter._apply_attack_preview(prompt, "textbugger_attack")

    assert transformed != prompt
    assert "Pl ease" in transformed


def test_unknown_attack_keeps_prompt(adapter: MoonshotApiAdapter):
    assert adapter._apply_attack_preview("hello", "unknown_attack") == "hello"
