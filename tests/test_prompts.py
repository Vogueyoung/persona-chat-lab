from __future__ import annotations

import pytest

from app.models.schemas import RetrievalHit
from app.prompts.character_prompts import available_versions, render_system_prompt


def test_prompt_contains_required_sections(aria):
    p = render_system_prompt(aria)
    for section in ("# 역할", "# 성격", "# 말투/스타일", "# 톤 조절", "# 절대 규칙"):
        assert section in p, f"missing section: {section}"


def test_prompt_embeds_character_identity(nori):
    p = render_system_prompt(nori)
    assert nori.name in p
    assert nori.title in p


def test_rag_section_only_when_hits(aria):
    p_no = render_system_prompt(aria, rag_hits=[])
    assert "# 참고 자료" not in p_no
    hits = [RetrievalHit(text="설빛검이라 불린다.", source="aria_knight.md", score=2.0)]
    p_yes = render_system_prompt(aria, rag_hits=hits)
    assert "# 참고 자료" in p_yes
    assert "설빛검" in p_yes


def test_unknown_version_raises(aria):
    with pytest.raises(ValueError):
        render_system_prompt(aria, version="v99")


def test_available_versions_non_empty():
    assert available_versions()
