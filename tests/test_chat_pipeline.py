"""End-to-end pipeline tests using the DummyChatService.

These do not verify model quality — they verify that the orchestration
(retrieval → prompt render → chat service) is correctly wired and
returns the documented response contract.
"""

from __future__ import annotations

import pytest

from app.models.schemas import ChatMessage, ChatRequest
from app.services.chat_service import DummyChatService, generate_reply
from app.services.retrieval_service import (
    KeywordRetrievalService,
    NullRetrievalService,
)


@pytest.mark.asyncio
async def test_pipeline_returns_expected_contract(aria):
    req = ChatRequest(
        character_id=aria.id,
        messages=[ChatMessage(role="user", content="안녕!")],
    )
    resp = await generate_reply(
        req, aria,
        chat_service=DummyChatService(),
        retrieval_service=NullRetrievalService(),
        include_prompt=True,
    )
    assert resp.character_id == aria.id
    assert resp.prompt_version == "v1"
    assert resp.model == "dummy"
    assert resp.reply
    assert resp.rendered_system_prompt
    assert resp.rag_hits == []


@pytest.mark.asyncio
async def test_pipeline_rag_on_injects_hits_into_prompt(aria):
    req = ChatRequest(
        character_id=aria.id,
        messages=[ChatMessage(role="user", content="브리오낙스 이야기 해줘.")],
    )
    resp = await generate_reply(
        req, aria,
        chat_service=DummyChatService(),
        retrieval_service=KeywordRetrievalService(),
        include_prompt=True,
    )
    assert resp.rag_hits, "expected RAG hits for a lore-specific query"
    assert "# 참고 자료" in resp.rendered_system_prompt
    # The dummy reply reports rag state so the pipeline is observable without a key.
    assert "RAG: 참고 자료 포함" in resp.reply


@pytest.mark.asyncio
async def test_pipeline_rag_off_leaves_prompt_clean(aria):
    req = ChatRequest(
        character_id=aria.id,
        messages=[ChatMessage(role="user", content="브리오낙스 이야기 해줘.")],
    )
    resp = await generate_reply(
        req, aria,
        chat_service=DummyChatService(),
        retrieval_service=NullRetrievalService(),
        include_prompt=True,
    )
    assert resp.rag_hits == []
    assert "# 참고 자료" not in resp.rendered_system_prompt
    assert "RAG: off" in resp.reply
