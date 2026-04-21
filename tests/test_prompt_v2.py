"""Tests that lock the v2 structural choices.

These assertions are not cosmetic — they are the contract that the
prompt linter scores against. If we change v2 structure without
updating both the linter and these tests, the comparison narrative
in docs/prompt-versions.md drifts.
"""

from __future__ import annotations

from app.prompts.character_prompts import render_system_prompt


def test_v2_renders(aria):
    p = render_system_prompt(aria, version="v2")
    assert p
    assert aria.name in p


def test_v2_few_shot_appears_before_personality(aria):
    p = render_system_prompt(aria, version="v2")
    idx_examples = p.find("# 대화 예시")
    idx_personality = p.find("# 성격")
    assert idx_examples != -1 and idx_personality != -1
    assert idx_examples < idx_personality, "v2 must put few-shot above personality"


def test_v2_splits_identity_and_topic_guardrails(aria):
    p = render_system_prompt(aria, version="v2")
    assert "# 정체성 보호" in p
    assert "# 금지 주제" in p
    # v1's merged '# 절대 규칙' header must not appear in v2.
    assert "# 절대 규칙" not in p


def test_v2_has_real_world_handling(aria):
    p = render_system_prompt(aria, version="v2")
    assert "# 현실 세계 질문 처리" in p


def test_v1_still_renders_after_v2_added(aria):
    # Regression: adding v2 must not break v1.
    p = render_system_prompt(aria, version="v1")
    assert "# 절대 규칙" in p
    assert "# 대화 예시" in p
