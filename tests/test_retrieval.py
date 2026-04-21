"""Retrieval tests — the important one is cross-character isolation."""

from __future__ import annotations

import pytest

from app.services.retrieval_service import (
    KeywordRetrievalService,
    NullRetrievalService,
    _bigrams,
)


def test_bigrams_handle_korean_and_punctuation():
    # Whitespace/punct stripped, same grams regardless of spacing.
    assert _bigrams("안녕!") == _bigrams("안 녕")
    grams = _bigrams("브리오낙스")
    assert "브리" in grams and "리오" in grams and "낙스" in grams


@pytest.mark.asyncio
async def test_null_retriever_returns_empty():
    r = NullRetrievalService()
    assert await r.search("anything", "aria_knight") == []


@pytest.mark.asyncio
async def test_keyword_retriever_finds_aria_lore_for_aria_query():
    r = KeywordRetrievalService()
    hits = await r.search("브리오낙스 이야기 해줘", "aria_knight")
    assert hits, "expected at least one hit for a term that exists in Aria's lore"
    assert any("브리오낙스" in h.text for h in hits)
    assert all(h.source.startswith("aria_knight") for h in hits)


@pytest.mark.asyncio
async def test_cross_character_isolation_zen_query_vs_aria():
    # 'Helixmed' is only in Zen's lore. Asking Aria's retriever must return nothing.
    r = KeywordRetrievalService()
    hits = await r.search("헬릭스메드 이야기", "aria_knight")
    assert hits == []


@pytest.mark.asyncio
async def test_cross_character_isolation_aria_query_vs_nori():
    # '빌슈타트' appears only in Aria's lore.
    r = KeywordRetrievalService()
    hits = await r.search("빌슈타트 고개", "nori_librarian")
    assert hits == []


@pytest.mark.asyncio
async def test_cross_character_isolation_nori_query_vs_zen():
    # '제비꽃' appears only in Nori's lore.
    r = KeywordRetrievalService()
    hits = await r.search("흰 제비꽃", "zen_hacker")
    assert hits == []


@pytest.mark.asyncio
async def test_unknown_character_returns_empty():
    r = KeywordRetrievalService()
    assert await r.search("anything", "ghost_character") == []
